"""Bounded RFC 3161 timestamp-token verifier (diagnostic only).

The TSA root certificate fingerprint and verification clock are supplied by the
caller and are NOT authenticated by this module. No revocation freshness,
institutional TSA designation, external custody, or production eligibility is
established. Tokens and certificates in tests are synthetic.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from asn1crypto import cms, tsp, x509 as asn1_x509
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, ed448, padding, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID

MAX_TOKEN_BYTES = 4 * 1024 * 1024
MAX_CERTIFICATES = 8
MAX_CERTIFICATE_BYTES = 64 * 1024
MAX_CHAIN_DEPTH = 6
_SHA = {
    "sha256": hashes.SHA256,
    "sha384": hashes.SHA384,
    "sha512": hashes.SHA512,
}
_HEX256 = re.compile(r"[0-9a-f]{64}\Z")

_UNSUPPORTED_PATH_EXTENSION_OIDS = frozenset({
    x509.ExtensionOID.NAME_CONSTRAINTS,
    x509.ExtensionOID.CERTIFICATE_POLICIES,
    x509.ExtensionOID.POLICY_MAPPINGS,
    x509.ExtensionOID.POLICY_CONSTRAINTS,
    x509.ExtensionOID.INHIBIT_ANY_POLICY,
})


@dataclass(frozen=True, slots=True)
class RFC3161Inspection:
    token_sha256: str
    message_imprint_algorithm: str
    message_imprint_hex: str
    gen_time_utc: datetime
    serial_number: int
    policy_oid: str
    accuracy_microseconds: int | None
    ordering: bool
    tsa_certificate_sha256: str
    tsa_root_certificate_sha256: str
    certificate_chain_length: int
    nonce_verified: bool
    trust_anchor_source: str
    verification_clock_source: str
    revocation_status: str
    provenance_status: str


def _hash_algorithm(name: object):
    if type(name) is not str or name not in _SHA:
        raise ValueError("RFC3161 digest must be SHA-256, SHA-384, or SHA-512")
    return _SHA[name]()


def _verify_signature(public_key, signature: bytes, payload: bytes, algorithm, digest):
    try:
        if isinstance(public_key, rsa.RSAPublicKey):
            if algorithm != "rsassa_pkcs1v15":
                raise ValueError("CMS RSA signature algorithm must be rsassa_pkcs1v15")
            public_key.verify(signature, payload, padding.PKCS1v15(), digest)
        elif isinstance(public_key, ec.EllipticCurvePublicKey):
            if algorithm != "ecdsa":
                raise ValueError("CMS EC signature algorithm must be ecdsa")
            public_key.verify(signature, payload, ec.ECDSA(digest))
        elif isinstance(public_key, ed25519.Ed25519PublicKey):
            if algorithm != "ed25519":
                raise ValueError("CMS Ed25519 signature algorithm is mismatched")
            public_key.verify(signature, payload)
        elif isinstance(public_key, ed448.Ed448PublicKey):
            if algorithm != "ed448":
                raise ValueError("CMS Ed448 signature algorithm is mismatched")
            public_key.verify(signature, payload)
        else:
            raise ValueError("unsupported CMS signer public-key algorithm")
    except InvalidSignature as exc:
        raise ValueError("RFC3161 CMS signature verification failed") from exc


def _verify_certificate_signature(cert: x509.Certificate, issuer_key) -> None:
    params = cert.signature_algorithm_parameters
    digest = cert.signature_hash_algorithm
    if digest is not None and digest.name not in _SHA:
        raise ValueError("certificate chain uses an unsupported or weak digest")
    if isinstance(issuer_key, rsa.RSAPublicKey):
        if params is None:
            params = padding.PKCS1v15()
        if digest is None:
            raise ValueError("RSA certificate signature has no digest algorithm")
        issuer_key.verify(cert.signature, cert.tbs_certificate_bytes, params, digest)
    elif isinstance(issuer_key, ec.EllipticCurvePublicKey):
        if digest is None:
            raise ValueError("EC certificate signature has no digest algorithm")
        if params is None:
            params = ec.ECDSA(digest)
        issuer_key.verify(cert.signature, cert.tbs_certificate_bytes, params)
    elif isinstance(issuer_key, (ed25519.Ed25519PublicKey, ed448.Ed448PublicKey)):
        issuer_key.verify(cert.signature, cert.tbs_certificate_bytes)
    else:
        raise ValueError("unsupported certificate issuer public-key algorithm")


def _valid_at(cert: x509.Certificate, instant: datetime, label: str) -> None:
    if not (cert.not_valid_before_utc <= instant <= cert.not_valid_after_utc):
        raise ValueError(f"{label} certificate is not valid at timestamp genTime")


def _reject_unsupported_path_extensions(
    cert: x509.Certificate, label: str
) -> None:
    for extension in cert.extensions:
        if extension.oid in _UNSUPPORTED_PATH_EXTENSION_OIDS:
            raise ValueError(
                f"{label} certificate uses unsupported RFC 5280 path extension "
                f"{extension.oid.dotted_string}"
            )


def _reject_unhandled_critical_extensions(
    cert: x509.Certificate, label: str, handled_oids: frozenset
) -> None:
    for extension in cert.extensions:
        if extension.critical and extension.oid not in handled_oids:
            raise ValueError(
                f"{label} certificate contains an unhandled critical extension "
                f"{extension.oid.dotted_string}"
            )


def _require_ca(cert: x509.Certificate, label: str) -> None:
    _reject_unsupported_path_extensions(cert, label)
    _reject_unhandled_critical_extensions(
        cert,
        label,
        frozenset({
            x509.ExtensionOID.BASIC_CONSTRAINTS,
            x509.ExtensionOID.KEY_USAGE,
        }),
    )
    try:
        bc = cert.extensions.get_extension_for_class(x509.BasicConstraints)
        ku = cert.extensions.get_extension_for_class(x509.KeyUsage)
    except x509.ExtensionNotFound as exc:
        raise ValueError(f"{label} certificate lacks CA constraints or key usage") from exc
    if not bc.critical or not ku.critical:
        raise ValueError(f"{label} CA constraints and key usage must be critical")
    if not bc.value.ca or not ku.value.key_cert_sign:
        raise ValueError(f"{label} certificate is not authorized to sign certificates")
    try:
        cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage)
    except x509.ExtensionNotFound:
        pass
    else:
        raise ValueError(
            f"{label} CA certificate contains unsupported extended-key-usage path constraints"
        )


def _require_tsa_leaf(cert: x509.Certificate) -> None:
    _reject_unsupported_path_extensions(cert, "TSA signer")
    _reject_unhandled_critical_extensions(
        cert,
        "TSA signer",
        frozenset({
            x509.ExtensionOID.BASIC_CONSTRAINTS,
            x509.ExtensionOID.KEY_USAGE,
            x509.ExtensionOID.EXTENDED_KEY_USAGE,
        }),
    )
    try:
        basic_constraints = cert.extensions.get_extension_for_class(x509.BasicConstraints)
    except x509.ExtensionNotFound:
        basic_constraints = None
    if basic_constraints is not None and basic_constraints.value.ca:
        raise ValueError("TSA signer certificate must not be a CA certificate")
    try:
        eku_ext = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage)
        ku_ext = cert.extensions.get_extension_for_class(x509.KeyUsage)
    except x509.ExtensionNotFound as exc:
        raise ValueError("TSA signer certificate lacks required EKU or key usage") from exc
    if not eku_ext.critical or tuple(eku_ext.value) != (ExtendedKeyUsageOID.TIME_STAMPING,):
        raise ValueError("TSA signer certificate must have critical timeStamping-only EKU")
    if not ku_ext.value.digital_signature:
        raise ValueError("TSA signer certificate must permit digital signatures")
    if ku_ext.value.key_cert_sign:
        raise ValueError("TSA signer certificate must not assert keyCertSign")


def _build_chain(
    leaf: x509.Certificate,
    intermediates: tuple[x509.Certificate, ...],
    root: x509.Certificate,
    gen_time: datetime,
) -> tuple[x509.Certificate, ...]:
    chain = [leaf]
    remaining = list(intermediates)
    current = leaf
    for _ in range(MAX_CHAIN_DEPTH):
        if current.issuer == root.subject:
            issuer = root
            _verify_certificate_signature(current, issuer.public_key())
            _valid_at(issuer, gen_time, "pinned TSA root")
            _require_ca(issuer, "pinned TSA root")
            _verify_certificate_signature(issuer, issuer.public_key())
            root_path_length = issuer.extensions.get_extension_for_class(
                x509.BasicConstraints
            ).value.path_length
            subordinate_ca_count = sum(
                1 for item in chain[1:] if item.extensions.get_extension_for_class(
                    x509.BasicConstraints
                ).value.ca
            )
            if root_path_length is not None and subordinate_ca_count > root_path_length:
                raise ValueError("pinned TSA root path-length constraint is exceeded")
            chain.append(issuer)
            if remaining:
                raise ValueError("timestamp token contains unrelated or unused certificates")
            return tuple(chain)
        matches = [candidate for candidate in remaining if candidate.subject == current.issuer]
        if len(matches) != 1:
            raise ValueError("TSA certificate chain has a missing or ambiguous issuer")
        issuer = matches[0]
        remaining.remove(issuer)
        _valid_at(issuer, gen_time, "TSA intermediate")
        _require_ca(issuer, "TSA intermediate")
        _verify_certificate_signature(current, issuer.public_key())
        subordinate_ca_count = sum(
            1 for item in chain[1:] if item.extensions.get_extension_for_class(
                x509.BasicConstraints
            ).value.ca
        )
        path_length = issuer.extensions.get_extension_for_class(
            x509.BasicConstraints
        ).value.path_length
        if path_length is not None and subordinate_ca_count > path_length:
            raise ValueError("TSA intermediate path-length constraint is exceeded")
        chain.append(issuer)
        current = issuer
    raise ValueError("TSA certificate chain exceeds maximum depth")


def _match_signer_certificate(signer_info, certificates):
    sid = signer_info["sid"]
    if sid.name != "issuer_and_serial_number":
        raise ValueError("RFC3161 CMS signer must use issuerAndSerialNumber SID")
    issuer_der = sid.chosen["issuer"].dump()
    serial = sid.chosen["serial_number"].native
    matches = [
        cert for cert in certificates
        if cert.issuer.public_bytes() == issuer_der and cert.serial_number == serial
    ]
    if len(matches) != 1:
        raise ValueError("RFC3161 signer certificate is missing or ambiguous")
    return matches[0]


def _verify_ess_issuer_serial(cert_id, signer_cert: x509.Certificate, label: str) -> None:
    """If ESS issuerSerial is present, bind it to the exact signer certificate."""
    issuer_serial = cert_id["issuer_serial"]
    if issuer_serial.native is None:
        return
    if issuer_serial["serial_number"].native != signer_cert.serial_number:
        raise ValueError(f"RFC3161 {label} issuerSerial serial number does not match signer certificate")
    signer_cert_asn1 = asn1_x509.Certificate.load(
        signer_cert.public_bytes(serialization.Encoding.DER),
        strict=True,
    )
    expected_issuer_name = signer_cert_asn1["tbs_certificate"]["issuer"].native
    issuer_names = issuer_serial["issuer"]
    if not any(
        name.name == "directory_name"
        and name.chosen.native == expected_issuer_name
        for name in issuer_names
    ):
        raise ValueError(f"RFC3161 {label} issuerSerial issuer does not match signer certificate")


def _verify_tstinfo_tsa_name(tst_info, signer_cert: x509.Certificate) -> None:
    """Bind a present TSTInfo tsa GeneralName to a signer-certificate name.

    Supported forms are directoryName (subject or SAN), rfc822Name, dNSName,
    uniformResourceIdentifier, iPAddress, and registeredID (SAN only). Text
    names are compared exactly and conservatively; no case folding or URI
    normalization is performed. Other GeneralName choices fail closed.
    """
    tsa_name = tst_info["tsa"]
    if tsa_name.native is None:
        return

    try:
        subject_alt_names = signer_cert.extensions.get_extension_for_class(
            x509.SubjectAlternativeName
        ).value
    except x509.ExtensionNotFound:
        subject_alt_names = ()

    if tsa_name.name == "directory_name":
        signer_cert_asn1 = asn1_x509.Certificate.load(
            signer_cert.public_bytes(serialization.Encoding.DER),
            strict=True,
        )
        accepted_names = [
            signer_cert_asn1["tbs_certificate"]["subject"].native
        ]
        for candidate in subject_alt_names:
            if isinstance(candidate, x509.DirectoryName):
                candidate_name = asn1_x509.Name.load(
                    candidate.value.public_bytes(),
                    strict=True,
                )
                accepted_names.append(candidate_name.native)
        if tsa_name.chosen.native in accepted_names:
            return
    else:
        san_types = {
            "rfc822_name": x509.RFC822Name,
            "dns_name": x509.DNSName,
            "uniform_resource_identifier": x509.UniformResourceIdentifier,
            "ip_address": x509.IPAddress,
            "registered_id": x509.RegisteredID,
        }
        candidate_type = san_types.get(tsa_name.name)
        if candidate_type is None:
            raise ValueError(
                "RFC3161 TSTInfo tsa GeneralName form is unsupported by this verifier"
            )

        expected = tsa_name.chosen.native
        if tsa_name.name == "ip_address":
            if type(expected) is not bytes:
                raise ValueError("RFC3161 TSTInfo tsa iPAddress has an invalid value")
            accepted_values = [
                candidate.value.packed
                for candidate in subject_alt_names
                if isinstance(candidate, candidate_type)
            ]
        elif tsa_name.name == "registered_id":
            if type(expected) is not str:
                raise ValueError("RFC3161 TSTInfo tsa registeredID has an invalid value")
            accepted_values = [
                candidate.value.dotted_string
                for candidate in subject_alt_names
                if isinstance(candidate, candidate_type)
            ]
        else:
            if type(expected) is not str:
                raise ValueError("RFC3161 TSTInfo tsa name has an invalid value")
            accepted_values = [
                candidate.value
                for candidate in subject_alt_names
                if isinstance(candidate, candidate_type)
            ]
        if expected in accepted_values:
            return

    raise ValueError(
        "RFC3161 TSTInfo tsa name does not match signer certificate subject names"
    )


def _verify_signing_certificate_binding(signed_attrs, signer_cert: x509.Certificate):
    """Require RFC 3161 ESS signer-certificate identification in signed attrs.

    RFC 3161 requires SigningCertificate (ESSCertID); RFC 5816 also permits
    SigningCertificateV2 (ESSCertIDv2). If both are present, both must bind
    the exact DER certificate selected by CMS issuerAndSerialNumber.
    """
    attr_types = [item["type"].native for item in signed_attrs]
    allowed = {
        "content_type",
        "message_digest",
        "signing_certificate",
        "signing_certificate_v2",
    }
    required = {"content_type", "message_digest"}
    if (
        len(attr_types) != len(set(attr_types))
        or not required.issubset(attr_types)
        or not set(attr_types).issubset(allowed)
        or not ({"signing_certificate", "signing_certificate_v2"} & set(attr_types))
    ):
        raise ValueError(
            "RFC3161 CMS signed attributes must contain unique contentType, "
            "messageDigest, and at least one ESS signing-certificate identifier only"
        )
    if any(len(item["values"]) != 1 for item in signed_attrs):
        raise ValueError("RFC3161 CMS signed attributes must contain exactly one value each")

    attrs = {item["type"].native: item["values"][0] for item in signed_attrs}
    signer_der = signer_cert.public_bytes(serialization.Encoding.DER)

    if "signing_certificate" in attrs:
        signing_certificate = attrs["signing_certificate"]
        cert_ids = signing_certificate["certs"]
        if len(cert_ids) < 1:
            raise ValueError("RFC3161 SigningCertificate ESSCertID list must not be empty")
        cert_id = cert_ids[0]
        expected = hashlib.sha1(signer_der).digest()
        if cert_id["cert_hash"].native != expected:
            raise ValueError(
                "RFC3161 SigningCertificate ESSCertID does not identify the exact signer certificate"
            )
        _verify_ess_issuer_serial(cert_id, signer_cert, "SigningCertificate")

    if "signing_certificate_v2" in attrs:
        signing_certificate_v2 = attrs["signing_certificate_v2"]
        cert_ids = signing_certificate_v2["certs"]
        if len(cert_ids) < 1:
            raise ValueError("RFC3161 SigningCertificateV2 ESSCertIDv2 list must not be empty")
        cert_id = cert_ids[0]
        algorithm_name = cert_id["hash_algorithm"]["algorithm"].native
        _hash_algorithm(algorithm_name)
        expected = hashlib.new(algorithm_name, signer_der).digest()
        if cert_id["cert_hash"].native != expected:
            raise ValueError(
                "RFC3161 SigningCertificateV2 ESSCertIDv2 does not identify the exact signer certificate"
            )
        _verify_ess_issuer_serial(cert_id, signer_cert, "SigningCertificateV2")

    return attrs


def verify_rfc3161_timestamp_token(
    token_der: bytes,
    data: bytes,
    *,
    pinned_tsa_root_certificate_der: bytes,
    expected_tsa_root_sha256: str,
    verification_time: datetime,
    expected_nonce: int | None = None,
) -> RFC3161Inspection:
    """Verify a DER RFC3161 token and TSA chain against a caller-pinned root.

    This checks CMS signed attributes, the TSTInfo imprint, TSA EKU/key usage,
    certificate signatures and validity at genTime, and optional nonce binding.
    The root fingerprint and verification clock remain caller-supplied.
    """
    if type(token_der) is not bytes or not 1 <= len(token_der) <= MAX_TOKEN_BYTES:
        raise ValueError("timestamp token must be exact DER bytes within size limit")
    if type(data) is not bytes or not data:
        raise ValueError("timestamp target data must be non-empty exact bytes")
    if type(pinned_tsa_root_certificate_der) is not bytes or not 1 <= len(pinned_tsa_root_certificate_der) <= MAX_CERTIFICATE_BYTES:
        raise ValueError("pinned TSA root certificate must be exact DER bytes within size limit")
    if type(expected_tsa_root_sha256) is not str or not _HEX256.fullmatch(expected_tsa_root_sha256):
        raise ValueError("expected TSA root fingerprint must be lowercase SHA-256 hex")
    if type(verification_time) is not datetime or verification_time.tzinfo is None:
        raise ValueError("verification_time must be a timezone-aware exact datetime")
    if expected_nonce is not None and (type(expected_nonce) is not int or expected_nonce < 1):
        raise ValueError("expected_nonce must be an exact positive integer")

    try:
        offset = verification_time.utcoffset()
    except Exception as exc:
        raise ValueError("verification_time timezone is invalid") from exc
    if type(offset) is not timedelta:
        raise ValueError("verification_time must have a valid timezone offset")
    now = (
        verification_time.replace(tzinfo=None) - offset
    ).replace(tzinfo=timezone.utc)
    root_digest = hashlib.sha256(pinned_tsa_root_certificate_der).hexdigest()
    if root_digest != expected_tsa_root_sha256:
        raise ValueError("pinned TSA root certificate fingerprint mismatch")
    try:
        root_asn1 = asn1_x509.Certificate.load(
            pinned_tsa_root_certificate_der, strict=True
        )
        if root_asn1.dump(force=True) != pinned_tsa_root_certificate_der:
            raise ValueError("pinned TSA root certificate must use canonical DER")
        root = x509.load_der_x509_certificate(pinned_tsa_root_certificate_der)
    except (ValueError, TypeError) as exc:
        raise ValueError("pinned TSA root certificate is not valid canonical DER X.509") from exc
    _require_ca(root, "pinned TSA root")

    try:
        content_info = cms.ContentInfo.load(token_der, strict=True)
        if content_info.dump(force=True) != token_der:
            raise ValueError("timestamp token must use canonical DER encoding")
        if content_info["content_type"].native != "signed_data":
            raise ValueError("timestamp token CMS content type must be signed_data")
        signed_data = content_info["content"]
        encap = signed_data["encap_content_info"]
        if encap["content_type"].native != "tst_info":
            raise ValueError("timestamp token encapsulated content must be TSTInfo")
        content = encap["content"]
        if content.native is None:
            raise ValueError("timestamp token must contain encapsulated TSTInfo bytes")
        tst_bytes = content.parsed.dump()
        tst_info = tsp.TSTInfo.load(tst_bytes, strict=True)
        if tst_info.dump(force=True) != tst_bytes:
            raise ValueError("TSTInfo must use canonical DER encoding")
        signer_infos = signed_data["signer_infos"]
        cert_choices = signed_data["certificates"]
    except (ValueError, TypeError, KeyError) as exc:
        if isinstance(exc, ValueError) and str(exc).startswith(("timestamp token", "TSTInfo")):
            raise
        raise ValueError("timestamp token has malformed CMS/TSTInfo structure") from exc

    tst_version = tst_info["version"].native
    if not (
        (type(tst_version) is int and tst_version == 1)
        or (type(tst_version) is str and tst_version == "v1")
    ):
        raise ValueError("RFC3161 TSTInfo version must be v1 (1)")

    if len(signer_infos) != 1:
        raise ValueError("timestamp token must contain exactly one CMS signer")
    if cert_choices is None or not 1 <= len(cert_choices) <= MAX_CERTIFICATES:
        raise ValueError("timestamp token must contain 1..8 X.509 certificates")
    cert_der_values = []
    for choice in cert_choices:
        if choice.name != "certificate":
            raise ValueError("timestamp token contains an unsupported certificate choice")
        der = choice.chosen.dump()
        if choice.chosen.dump(force=True) != der:
            raise ValueError("timestamp token certificate must use canonical DER")
        if len(der) > MAX_CERTIFICATE_BYTES:
            raise ValueError("timestamp token certificate exceeds size limit")
        cert_der_values.append(der)
    if len(set(cert_der_values)) != len(cert_der_values):
        raise ValueError("timestamp token contains duplicate certificates")
    try:
        certificates = tuple(x509.load_der_x509_certificate(value) for value in cert_der_values)
    except ValueError as exc:
        raise ValueError("timestamp token contains invalid DER X.509 certificate") from exc

    signer_info = signer_infos[0]
    signer_cert = _match_signer_certificate(signer_info, certificates)
    _require_tsa_leaf(signer_cert)
    _verify_tstinfo_tsa_name(tst_info, signer_cert)

    imprint = tst_info["message_imprint"]
    imprint_algorithm = imprint["hash_algorithm"]["algorithm"].native
    digest = _hash_algorithm(imprint_algorithm)
    imprint_bytes = imprint["hashed_message"].native
    expected_imprint = hashlib.new(imprint_algorithm, data).digest()
    if imprint_bytes != expected_imprint:
        raise ValueError("RFC3161 message imprint does not match exact target bytes")

    gen_time = tst_info["gen_time"].native
    if type(gen_time) is not datetime or gen_time.tzinfo is None:
        raise ValueError("RFC3161 genTime must be timezone-aware")
    gen_time = gen_time.astimezone(timezone.utc)
    if gen_time > now:
        raise ValueError("RFC3161 genTime is after caller-supplied verification time")
    serial = tst_info["serial_number"].native
    if type(serial) is not int or not 1 <= serial <= (1 << 63) - 1:
        raise ValueError("RFC3161 serial number must be a positive signed 64-bit integer")
    nonce = tst_info["nonce"].native if tst_info["nonce"].native is not None else None
    if nonce is not None and (
        type(nonce) is not int or not 1 <= nonce <= (1 << 63) - 1
    ):
        raise ValueError("RFC3161 nonce must be a positive signed 64-bit integer")
    if expected_nonce is not None and nonce is None:
        raise ValueError("RFC3161 timestamp token omits the required request nonce")
    if expected_nonce is not None and nonce != expected_nonce:
        raise ValueError("RFC3161 nonce does not match request nonce")

    root_fingerprint = root.fingerprint(hashes.SHA256())
    cert_intermediates = tuple(
        cert for cert in certificates
        if cert.fingerprint(hashes.SHA256()) not in {
            signer_cert.fingerprint(hashes.SHA256()), root_fingerprint
        }
    )
    _valid_at(signer_cert, gen_time, "TSA signer")
    chain = _build_chain(signer_cert, cert_intermediates, root, gen_time)

    signed_attrs = signer_info["signed_attrs"]
    if signed_attrs.native is None:
        raise ValueError("RFC3161 CMS signer must include signed attributes")
    attrs = _verify_signing_certificate_binding(signed_attrs, signer_cert)
    if attrs["content_type"].native != "tst_info":
        raise ValueError("RFC3161 CMS contentType signed attribute must be TSTInfo")
    cms_digest_name = signer_info["digest_algorithm"]["algorithm"].native
    cms_digest = _hash_algorithm(cms_digest_name)
    declared_digests = [
        item["algorithm"].native for item in signed_data["digest_algorithms"]
    ]
    if declared_digests != [cms_digest_name]:
        raise ValueError("CMS digestAlgorithms must contain exactly the signer's digest")
    if attrs["message_digest"].native != hashlib.new(cms_digest_name, tst_bytes).digest():
        raise ValueError("RFC3161 CMS messageDigest does not match encapsulated TSTInfo")
    signature_algorithm = signer_info["signature_algorithm"]["algorithm"].native
    signature = signer_info["signature"].native
    signed_payload = signed_attrs.untag().dump()
    _verify_signature(
        signer_cert.public_key(),
        signature,
        signed_payload,
        signature_algorithm,
        cms_digest,
    )

    accuracy = tst_info["accuracy"]
    accuracy_microseconds = None
    if accuracy.native is not None:
        seconds_value = accuracy["seconds"].native
        millis_value = accuracy["millis"].native
        micros_value = accuracy["micros"].native
        seconds = 0 if seconds_value is None else seconds_value
        if type(seconds) is not int or seconds < 0:
            raise ValueError("RFC3161 accuracy seconds must be a non-negative integer")
        if millis_value is not None and (
            type(millis_value) is not int or not 1 <= millis_value <= 999
        ):
            raise ValueError("RFC3161 accuracy millis must be 1..999 when present")
        if micros_value is not None and (
            type(micros_value) is not int or not 1 <= micros_value <= 999
        ):
            raise ValueError("RFC3161 accuracy micros must be 1..999 when present")
        millis = 0 if millis_value is None else millis_value
        micros = 0 if micros_value is None else micros_value
        accuracy_microseconds = seconds * 1_000_000 + millis * 1_000 + micros
    ordering = tst_info["ordering"].native
    if type(ordering) is not bool:
        raise ValueError("RFC3161 ordering must be an exact boolean")
    policy_oid = tst_info["policy"].dotted
    return RFC3161Inspection(
        token_sha256=hashlib.sha256(token_der).hexdigest(),
        message_imprint_algorithm=imprint_algorithm,
        message_imprint_hex=imprint_bytes.hex(),
        gen_time_utc=gen_time,
        serial_number=serial,
        policy_oid=policy_oid,
        accuracy_microseconds=accuracy_microseconds,
        ordering=ordering,
        tsa_certificate_sha256=signer_cert.fingerprint(hashes.SHA256()).hex(),
        tsa_root_certificate_sha256=root_digest,
        certificate_chain_length=len(chain),
        nonce_verified=expected_nonce is not None,
        trust_anchor_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        verification_clock_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        revocation_status="NOT_CHECKED",
        provenance_status="BLOCKED_PROVENANCE",
    )
