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
    leaf_key_cert_sign=False,
    name_constraints_on=None,
    certificate_policies_on=None,
):
    root_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    root_name = _name("Synthetic TSA Root")
    root_builder = (
        x509.CertificateBuilder()
        .subject_name(root_name)
        .issuer_name(root_name)
        .public_key(root_key.public_key())
        .serial_number(100)
        .not_valid_before(GEN_TIME - timedelta(days=30))
        .not_valid_after(GEN_TIME + timedelta(days=365))
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
        .not_valid_before(GEN_TIME - timedelta(days=1))
        .not_valid_after(GEN_TIME + timedelta(days=30))
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
    tamper_signature=False,
    include_root=False,
    accuracy=None,
    critical_custom_extension_on=None,
    name_constraints_on=None,
    certificate_policies_on=None,
):
    root, tsa, tsa_key = _certs(
        critical_eku=critical_eku,
        critical_custom_extension_on=critical_custom_extension_on,
        leaf_key_cert_sign=leaf_key_cert_sign,
        name_constraints_on=name_constraints_on,
        certificate_policies_on=certificate_policies_on,
    )
    tst_info = tsp.TSTInfo({
        "version": "v1",
        "policy": "1.2.3.4.5",
        "message_imprint": {
            "hash_algorithm": {"algorithm": "sha256"},
            "hashed_message": hashlib.sha256(data).digest(),
        },
        "serial_number": 777,
        "gen_time": GEN_TIME,
        "nonce": nonce,
        "accuracy": accuracy,
    })
    tst_bytes = tst_info.dump()
    attrs = cms.CMSAttributes([
        cms.CMSAttribute({"type": "content_type", "values": ["tst_info"]}),
        cms.CMSAttribute({"type": "message_digest", "values": [hashlib.sha256(tst_bytes).digest()]}),
    ])
    signature = tsa_key.sign(attrs.untag().dump(), padding.PKCS1v15(), hashes.SHA256())
    if tamper_signature:
        signature = bytes([signature[0] ^ 1]) + signature[1:]
    cert_asn1 = asn1_x509.Certificate.load(tsa.public_bytes(serialization.Encoding.DER))
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

    def test_accuracy_is_preserved_for_downstream_preclose_bound(self):
        token, root_der = _token(accuracy={"seconds": 1, "millis": 250, "micros": 5})
        result = _verify(token, root_der)
        self.assertEqual(result.accuracy_microseconds, 1_250_005)
        self.assertFalse(result.ordering)


if __name__ == "__main__":
    unittest.main()
