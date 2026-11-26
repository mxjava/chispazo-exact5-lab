from __future__ import annotations

import hashlib
import unittest
from datetime import datetime, timedelta, timezone

from asn1crypto import cms, tsp, x509 as asn1_x509
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID, ObjectIdentifier

from origen.rfc3161_tsa_verifier_v1 import verify_rfc3161_timestamp_token

NOW = datetime(2026, 11, 25, 6, 0, tzinfo=timezone.utc)
GEN_TIME = datetime(2026, 11, 25, 5, 55, tzinfo=timezone.utc)
DATA = b"synthetic physical evidence artifact"


def _name(common_name):
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])


def _certs(
    *,
    critical_eku=True,
    leaf_key_cert_sign=False,
    critical_custom_extension_on=None,
    name_constraints_on=None,
    certificate_policies_on=None,
    gen_time=GEN_TIME,
    tsa_san_names=(),
    root_subject_name=None,
):
    root_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    root_name = root_subject_name or _name("Synthetic TSA Root")
    root_builder = (
        x509.CertificateBuilder()
        .subject_name(root_name)
        .issuer_name(root_name)
        .public_key(root_key.public_key())
        .serial_number(100)
        .not_valid_before(gen_time - timedelta(days=30))
        .not_valid_after(gen_time + timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=1), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=False, content_commitment=False, key_encipherment=False,
                data_encipherment=False, key_agreement=False, key_cert_sign=True,
                crl_sign=True, encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
    )
    if critical_custom_extension_on == "root":
        root_builder = root_builder.add_extension(
            x509.UnrecognizedExtension(ObjectIdentifier("1.3.6.1.4.1.55555.1"), b"\\x05\\x00"),
            critical=True,
        )
    if name_constraints_on == "root":
        root_builder = root_builder.add_extension(
            x509.NameConstraints(
                permitted_subtrees=[x509.DirectoryName(_name("Synthetic TSA"))],
                excluded_subtrees=None,
            ),
            critical=True,
        )
    if certificate_policies_on == "root":
        root_builder = root_builder.add_extension(
            x509.CertificatePolicies([
                x509.PolicyInformation(ObjectIdentifier("1.2.3.4.5.6"), None)
            ]),
            critical=False,
        )
    root = root_builder.sign(root_key, hashes.SHA256())

    tsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    tsa_builder = (
        x509.CertificateBuilder()
        .subject_name(_name("Synthetic TSA"))
        .issuer_name(root.subject)
        .public_key(tsa_key.public_key())
        .serial_number(200)
        .not_valid_before(gen_time - timedelta(days=1))
        .not_valid_after(gen_time + timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, content_commitment=False, key_encipherment=False,
                data_encipherment=False, key_agreement=False, key_cert_sign=leaf_key_cert_sign,
                crl_sign=False, encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.TIME_STAMPING]),
            critical=critical_eku,
        )
    )
    if tsa_san_names:
        tsa_builder = tsa_builder.add_extension(
            x509.SubjectAlternativeName(list(tsa_san_names)),
            critical=False,
        )
    if critical_custom_extension_on == "leaf":
        tsa_builder = tsa_builder.add_extension(
            x509.UnrecognizedExtension(ObjectIdentifier("1.3.6.1.4.1.55555.1"), b"\\x05\\x00"),
            critical=True,
        )
    tsa = tsa_builder.sign(root_key, hashes.SHA256())
    return root, tsa, tsa_key


def _token(
    data=DATA,
    *,
    nonce=12345,
    critical_eku=True,
    leaf_key_cert_sign=False,
    tamper_signature=False,
    include_root=False,
    accuracy=None,
    critical_custom_extension_on=None,
    name_constraints_on=None,
    certificate_policies_on=None,
    gen_time=GEN_TIME,
    include_signing_certificate=True,
    signing_certificate_version="v2",
    signing_certificate_hash=None,
    include_legacy_signing_certificate=False,
    include_issuer_serial=False,
    wrong_issuer_serial=False,
    wrong_issuer_name=False,
    tst_version="v1",
    tsa_common_name=None,
    tsa_general_name_type="directory_name",
    tsa_general_name_value=None,
    tsa_san_names=(),
    root_subject_name=None,
    issuer_serial_name_override=None,
):
    root, tsa, tsa_key = _certs(
        critical_eku=critical_eku,
        critical_custom_extension_on=critical_custom_extension_on,
        leaf_key_cert_sign=leaf_key_cert_sign,
        name_constraints_on=name_constraints_on,
        certificate_policies_on=certificate_policies_on,
        gen_time=gen_time,
        tsa_san_names=tsa_san_names,
        root_subject_name=root_subject_name,
    )
    tst_info_fields = {
        "version": tst_version,
        "policy": "1.2.3.4.5",
        "message_imprint": {
            "hash_algorithm": {"algorithm": "sha256"},
            "hashed_message": hashlib.sha256(data).digest(),
        },
        "serial_number": 777,
        "gen_time": gen_time,
        "nonce": nonce,
        "accuracy": accuracy,
    }
    if tsa_general_name_value is None:
        tsa_general_name_value = tsa_common_name
    if tsa_general_name_value is not None:
        if tsa_general_name_type == "directory_name":
            if isinstance(tsa_general_name_value, x509.Name):
                tsa_value = asn1_x509.Name.load(
                    tsa_general_name_value.public_bytes(),
                    strict=True,
                )
            else:
                subject_common_names = tsa.subject.get_attributes_for_oid(
                    NameOID.COMMON_NAME
                )
                if (
                    len(subject_common_names) == 1
                    and tsa_general_name_value == subject_common_names[0].value
                ):
                    tsa_value = asn1_x509.Name.load(
                        tsa.subject.public_bytes(),
                        strict=True,
                    )
                else:
                    tsa_value = asn1_x509.Name.build(
                        {"common_name": tsa_general_name_value}
                    )
        else:
            tsa_value = tsa_general_name_value
        tst_info_fields["tsa"] = asn1_x509.GeneralName(
            name=tsa_general_name_type,
            value=tsa_value,
        )
    tst_info = tsp.TSTInfo(tst_info_fields)
    tst_bytes = tst_info.dump()
    cert_der = tsa.public_bytes(serialization.Encoding.DER)
    cert_asn1 = asn1_x509.Certificate.load(cert_der)
    attrs_list = [
        cms.CMSAttribute({"type": "content_type", "values": ["tst_info"]}),
        cms.CMSAttribute({"type": "message_digest", "values": [hashlib.sha256(tst_bytes).digest()]}),
    ]

    def _ess_cert_id(cert_hash):
        value = {"cert_hash": cert_hash}
        if include_issuer_serial:
            issuer_names = asn1_x509.GeneralNames()
            if issuer_serial_name_override is not None:
                issuer_name = (
                    asn1_x509.Name.load(
                        issuer_serial_name_override.public_bytes(),
                        strict=True,
                    )
                    if isinstance(issuer_serial_name_override, x509.Name)
                    else issuer_serial_name_override
                )
            elif wrong_issuer_name:
                issuer_name = asn1_x509.Name.build(
                    {"common_name": "Wrong Synthetic Issuer"}
                )
            else:
                issuer_name = cert_asn1.issuer
            issuer_names.append(
                asn1_x509.GeneralName(
                    name="directory_name",
                    value=issuer_name,
                )
            )
            value["issuer_serial"] = {
                "issuer": issuer_names,
                "serial_number": cert_asn1.serial_number + (1 if wrong_issuer_serial else 0),
            }
        return value

    if include_signing_certificate:
        if signing_certificate_version == "v1":
            cert_hash = (
                hashlib.sha1(cert_der).digest()
                if signing_certificate_hash is None
                else signing_certificate_hash
            )
            signing_certificate = tsp.SigningCertificate({
                "certs": [_ess_cert_id(cert_hash)],
            })
            attrs_list.append(cms.CMSAttribute({
                "type": "signing_certificate",
                "values": [signing_certificate],
            }))
        elif signing_certificate_version == "v2":
            cert_hash = (
                hashlib.sha256(cert_der).digest()
                if signing_certificate_hash is None
                else signing_certificate_hash
            )
            signing_certificate = tsp.SigningCertificateV2({
                "certs": [_ess_cert_id(cert_hash)],
            })
            attrs_list.append(cms.CMSAttribute({
                "type": "signing_certificate_v2",
                "values": [signing_certificate],
            }))
        else:
            raise ValueError("unsupported synthetic ESS signing-certificate version")

    if include_legacy_signing_certificate and signing_certificate_version != "v1":
        legacy_certificate = tsp.SigningCertificate({
            "certs": [_ess_cert_id(hashlib.sha1(cert_der).digest())],
        })
        attrs_list.append(cms.CMSAttribute({
            "type": "signing_certificate",
            "values": [legacy_certificate],
        }))

    attrs = cms.CMSAttributes(attrs_list)
    signature = tsa_key.sign(attrs.untag().dump(), padding.PKCS1v15(), hashes.SHA256())
    if tamper_signature:
        signature = bytes([signature[0] ^ 1]) + signature[1:]
    signer = cms.SignerInfo({
        "version": "v1",
        "sid": {
            "issuer_and_serial_number": {
                "issuer": cert_asn1.issuer,
                "serial_number": cert_asn1.serial_number,
            }
        },
        "digest_algorithm": {"algorithm": "sha256"},
        "signed_attrs": attrs,
        "signature_algorithm": {"algorithm": "rsassa_pkcs1v15"},
        "signature": signature,
    })
    encap = cms.EncapsulatedContentInfo({
        "content_type": "tst_info",
        "content": tst_info,
    })
    root_asn1 = asn1_x509.Certificate.load(
        root.public_bytes(serialization.Encoding.DER)
    )
    certs = [cert_asn1] + ([root_asn1] if include_root else [])
    signed_data = cms.SignedData({
        "version": "v3",
        "digest_algorithms": [{"algorithm": "sha256"}],
        "encap_content_info": encap,
        "certificates": certs,
        "signer_infos": [signer],
    })
    token = cms.ContentInfo({
        "content_type": "signed_data",
        "content": signed_data,
    }).dump()
    root_der = root.public_bytes(serialization.Encoding.DER)
    return token, root_der


def _verify(token, root_der, data=DATA, **kwargs):
    values = {
        "pinned_tsa_root_certificate_der": root_der,
        "expected_tsa_root_sha256": hashlib.sha256(root_der).hexdigest(),
        "verification_time": NOW,
        "expected_nonce": 12345,
    }
    values.update(kwargs)
    return verify_rfc3161_timestamp_token(token, data, **values)


class RFC3161TimestampVerifierTests(unittest.TestCase):
    def test_valid_synthetic_rfc3161_token_verifies_but_remains_blocked(self):
        token, root_der = _token()
        result = _verify(token, root_der)
        self.assertEqual(result.message_imprint_algorithm, "sha256")
        self.assertEqual(result.serial_number, 777)
        self.assertTrue(result.nonce_verified)
        self.assertEqual(result.trust_anchor_source, "CALLER_SUPPLIED_UNAUTHENTICATED")
        self.assertEqual(result.verification_clock_source, "CALLER_SUPPLIED_UNAUTHENTICATED")
        self.assertEqual(result.revocation_status, "NOT_CHECKED")
        self.assertEqual(result.provenance_status, "BLOCKED_PROVENANCE")

    def test_non_v1_tstinfo_version_is_rejected(self):
        token, root_der = _token(tst_version=2)
        with self.assertRaisesRegex(ValueError, "TSTInfo version must be v1"):
            _verify(token, root_der)

    def test_tstinfo_tsa_directory_name_must_match_signer_certificate(self):
        token, root_der = _token(tsa_common_name="Synthetic TSA")
        _verify(token, root_der)

        token, root_der = _token(tsa_common_name="Wrong Synthetic TSA")
        with self.assertRaisesRegex(ValueError, "does not match signer certificate subject names"):
            _verify(token, root_der)

    def test_tstinfo_tsa_directory_name_may_match_subject_alt_name(self):
        alternate_name = _name("Alternate Synthetic TSA")
        token, root_der = _token(
            tsa_general_name_value=alternate_name,
            tsa_general_name_type="directory_name",
            tsa_san_names=(x509.DirectoryName(alternate_name),),
        )
        _verify(token, root_der)

    def test_tstinfo_tsa_directory_name_preserves_rdn_boundaries(self):
        attributes = (
            x509.NameAttribute(NameOID.COMMON_NAME, "Alternate Synthetic TSA"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Evidence"),
        )
        tsa_name = x509.Name([
            x509.RelativeDistinguishedName(list(attributes)),
        ])
        certificate_name = x509.Name([
            x509.RelativeDistinguishedName([attributes[1]]),
            x509.RelativeDistinguishedName([attributes[0]]),
        ])
        tsa_asn1 = asn1_x509.Name.load(tsa_name.public_bytes(), strict=True)
        certificate_asn1 = asn1_x509.Name.load(
            certificate_name.public_bytes(),
            strict=True,
        )
        self.assertEqual(tsa_asn1.native, certificate_asn1.native)
        self.assertNotEqual(tsa_name.public_bytes(), certificate_name.public_bytes())

        token, root_der = _token(
            tsa_general_name_value=tsa_name,
            tsa_general_name_type="directory_name",
            tsa_san_names=(x509.DirectoryName(certificate_name),),
        )
        with self.assertRaisesRegex(ValueError, "does not match signer certificate"):
            _verify(token, root_der)

    def test_tstinfo_tsa_supported_general_names_must_match_subject_alt_name(self):
        import ipaddress

        cases = (
            (
                "dns_name",
                "tsa.example.test",
                x509.DNSName("tsa.example.test"),
                "other.example.test",
            ),
            (
                "rfc822_name",
                "tsa@example.test",
                x509.RFC822Name("tsa@example.test"),
                "other@example.test",
            ),
            (
                "uniform_resource_identifier",
                "https://tsa.example.test/timestamp",
                x509.UniformResourceIdentifier(
                    "https://tsa.example.test/timestamp"
                ),
                "https://other.example.test/timestamp",
            ),
            (
                "ip_address",
                "192.0.2.10",
                x509.IPAddress(ipaddress.ip_address("192.0.2.10")),
                "192.0.2.11",
            ),
            (
                "ip_address",
                "2001:db8::10",
                x509.IPAddress(ipaddress.ip_address("2001:db8::10")),
                "2001:db8::11",
            ),
            (
                "registered_id",
                "1.3.6.1.4.1.55555.1",
                x509.RegisteredID(ObjectIdentifier("1.3.6.1.4.1.55555.1")),
                "1.3.6.1.4.1.55555.2",
            ),
        )
        for name_type, matching_value, san_name, mismatching_value in cases:
            with self.subTest(name_type=name_type, outcome="match"):
                token, root_der = _token(
                    tsa_general_name_type=name_type,
                    tsa_general_name_value=matching_value,
                    tsa_san_names=(san_name,),
                )
                _verify(token, root_der)
            with self.subTest(name_type=name_type, outcome="mismatch"):
                token, root_der = _token(
                    tsa_general_name_type=name_type,
                    tsa_general_name_value=mismatching_value,
                    tsa_san_names=(san_name,),
                )
                with self.assertRaisesRegex(ValueError, "does not match signer certificate"):
                    _verify(token, root_der)

    def test_tstinfo_tsa_dns_name_without_matching_san_is_rejected(self):
        token, root_der = _token(
            tsa_general_name_type="dns_name",
            tsa_general_name_value="tsa.example.test",
        )
        with self.assertRaisesRegex(ValueError, "does not match signer certificate"):
            _verify(token, root_der)

    def test_tstinfo_tsa_ip_address_does_not_accept_network_san(self):
        import ipaddress

        network = ipaddress.ip_network("192.0.2.0/24")
        token, root_der = _token(
            tsa_general_name_type="ip_address",
            tsa_general_name_value="192.0.2.0/24",
            tsa_san_names=(x509.IPAddress(network),),
        )
        with self.assertRaisesRegex(ValueError, "does not match signer certificate"):
            _verify(token, root_der)


    def test_wrong_artifact_bytes_fail_imprint_binding(self):
        token, root_der = _token()
        with self.assertRaisesRegex(ValueError, "message imprint"):
            _verify(token, root_der, b"different artifact")

    def test_wrong_expected_nonce_fails(self):
        token, root_der = _token()
        with self.assertRaisesRegex(ValueError, "nonce"):
            _verify(token, root_der, expected_nonce=12346)

    def test_wrong_pinned_root_fingerprint_fails(self):
        token, root_der = _token()
        with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
            verify_rfc3161_timestamp_token(
                token, DATA,
                pinned_tsa_root_certificate_der=root_der,
                expected_tsa_root_sha256="0" * 64,
                verification_time=NOW,
                expected_nonce=12345,
            )

    def test_tampered_cms_signature_fails(self):
        token, root_der = _token(tamper_signature=True)
        with self.assertRaisesRegex(ValueError, "CMS signature verification failed"):
            _verify(token, root_der)

    def test_tsa_leaf_must_not_assert_key_cert_sign_when_ca_is_false(self):
        token, root_der = _token(leaf_key_cert_sign=True)
        with self.assertRaisesRegex(ValueError, "must not assert keyCertSign"):
            _verify(token, root_der)

    def test_tsa_eku_must_be_critical(self):
        token, root_der = _token(critical_eku=False)
        with self.assertRaisesRegex(ValueError, "critical timeStamping-only EKU"):
            _verify(token, root_der)

    def test_token_requires_expected_nonce_when_requested(self):
        token, root_der = _token(nonce=None)
        with self.assertRaisesRegex(ValueError, "omits the required request nonce"):
            _verify(token, root_der)

    def test_unhandled_critical_tsa_leaf_extension_fails_closed(self):
        token, root_der = _token(critical_custom_extension_on="leaf")
        with self.assertRaisesRegex(ValueError, "unhandled critical extension"):
            _verify(token, root_der)

    def test_unhandled_critical_pinned_root_extension_fails_closed(self):
        token, root_der = _token(critical_custom_extension_on="root")
        with self.assertRaisesRegex(ValueError, "unhandled critical extension"):
            _verify(token, root_der)

    def test_unsupported_name_constraints_fail_closed(self):
        token, root_der = _token(name_constraints_on="root")
        with self.assertRaisesRegex(ValueError, "unsupported RFC 5280 path extension"):
            _verify(token, root_der)

    def test_unsupported_certificate_policies_fail_closed_even_when_noncritical(self):
        token, root_der = _token(certificate_policies_on="root")
        with self.assertRaisesRegex(ValueError, "unsupported RFC 5280 path extension"):
            _verify(token, root_der)

    def test_non_der_trailing_bytes_are_rejected(self):
        token, root_der = _token()
        with self.assertRaises(ValueError):
            _verify(token + b"\x00", root_der)

    def test_verification_time_must_not_precede_gen_time(self):
        token, root_der = _token()
        with self.assertRaisesRegex(ValueError, "after caller-supplied verification time"):
            verify_rfc3161_timestamp_token(
                token,
                DATA,
                pinned_tsa_root_certificate_der=root_der,
                expected_tsa_root_sha256=hashlib.sha256(root_der).hexdigest(),
                verification_time=GEN_TIME - timedelta(seconds=1),
                expected_nonce=12345,
            )

    def test_root_certificate_may_be_included_in_cms_certificate_set(self):
        token, root_der = _token(include_root=True)
        result = _verify(token, root_der)
        self.assertEqual(result.certificate_chain_length, 2)


    def test_signing_certificate_v2_must_bind_exact_tsa_signer_certificate(self):
        token, root_der = _token(signing_certificate_hash=bytes(32))
        with self.assertRaisesRegex(ValueError, "SigningCertificateV2 ESSCertIDv2"):
            _verify(token, root_der)

    def test_missing_ess_signing_certificate_attribute_is_rejected(self):
        token, root_der = _token(include_signing_certificate=False)
        with self.assertRaisesRegex(ValueError, "at least one ESS signing-certificate identifier"):
            _verify(token, root_der)

    def test_legacy_signing_certificate_v1_sha1_binding_is_verified(self):
        token, root_der = _token(signing_certificate_version="v1")
        result = _verify(token, root_der)
        self.assertEqual(result.provenance_status, "BLOCKED_PROVENANCE")

        token, root_der = _token(
            signing_certificate_version="v1",
            signing_certificate_hash=bytes(20),
        )
        with self.assertRaisesRegex(ValueError, "SigningCertificate ESSCertID"):
            _verify(token, root_der)

    def test_both_ess_signing_certificate_versions_must_bind_signer(self):
        token, root_der = _token(include_legacy_signing_certificate=True)
        result = _verify(token, root_der)
        self.assertEqual(result.provenance_status, "BLOCKED_PROVENANCE")

    def test_optional_ess_issuer_serial_must_match_signer_certificate(self):
        token, root_der = _token(include_issuer_serial=True)
        _verify(token, root_der)

        token, root_der = _token(
            include_issuer_serial=True,
            wrong_issuer_serial=True,
        )
        with self.assertRaisesRegex(ValueError, "issuerSerial serial number"):
            _verify(token, root_der)

        token, root_der = _token(
            include_issuer_serial=True,
            wrong_issuer_name=True,
        )
        with self.assertRaisesRegex(ValueError, "issuerSerial issuer"):
            _verify(token, root_der)

    def test_ess_issuer_serial_directory_name_preserves_rdn_boundaries(self):
        attributes = (
            x509.NameAttribute(NameOID.COMMON_NAME, "Synthetic TSA Root"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Timestamping"),
        )
        root_name = x509.Name([
            x509.RelativeDistinguishedName(list(attributes)),
        ])
        different_rdn_layout = x509.Name([
            x509.RelativeDistinguishedName([attributes[1]]),
            x509.RelativeDistinguishedName([attributes[0]]),
        ])
        root_asn1 = asn1_x509.Name.load(root_name.public_bytes(), strict=True)
        mismatched_asn1 = asn1_x509.Name.load(
            different_rdn_layout.public_bytes(),
            strict=True,
        )
        self.assertEqual(root_asn1.native, mismatched_asn1.native)
        self.assertNotEqual(root_name.public_bytes(), different_rdn_layout.public_bytes())

        token, root_der = _token(
            include_issuer_serial=True,
            root_subject_name=root_name,
            issuer_serial_name_override=different_rdn_layout,
        )
        with self.assertRaisesRegex(ValueError, "issuerSerial issuer"):
            _verify(token, root_der)

    def test_accuracy_millis_explicit_zero_is_rejected(self):
        token, root_der = _token(accuracy={"millis": 0})
        with self.assertRaisesRegex(ValueError, "accuracy millis must be 1..999 when present"):
            _verify(token, root_der)

    def test_accuracy_micros_explicit_zero_is_rejected(self):
        token, root_der = _token(accuracy={"micros": 0})
        with self.assertRaisesRegex(ValueError, "accuracy micros must be 1..999 when present"):
            _verify(token, root_der)

    def test_accuracy_fractional_boundaries_one_and_999_are_accepted(self):
        token, root_der = _token(accuracy={"millis": 1, "micros": 999})
        result = _verify(token, root_der)
        self.assertEqual(result.accuracy_microseconds, 1_999)

        token, root_der = _token(accuracy={"millis": 999, "micros": 1})
        result = _verify(token, root_der)
        self.assertEqual(result.accuracy_microseconds, 999_001)

    def test_accuracy_is_preserved_for_downstream_preclose_bound(self):
        token, root_der = _token(accuracy={"seconds": 1, "millis": 250, "micros": 5})
        result = _verify(token, root_der)
        self.assertEqual(result.accuracy_microseconds, 1_250_005)
        self.assertFalse(result.ordering)


if __name__ == "__main__":
    unittest.main()
