"""Deployment-owned trust bootstrap boundary for ORIGEN.

No authenticated institutional root, monotonic anti-rollback store, or trusted
clock is provisioned in this repository. The default loader therefore returns
None. A deployment must replace this provider through an independently reviewed
package/image configuration path protected from the submitting user.

Do not populate this module from environment variables, request arguments,
repository files, CI variables, receipt contents, or the signed envelope itself.
Synthetic fixtures belong only in tests.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class _ProvisionedTrustBootstrap:
    """One immutable snapshot from a deployment-controlled bootstrap provider.

    This is an internal data carrier, not an unforgeable Python capability.
    Its provenance depends on the loader and process/deployment boundary.
    """
    policy_envelope_bytes: bytes
    pinned_root_public_key_bytes: bytes
    expected_root_key_id: str
    minimum_policy_sequence: int
    verification_time: datetime


def _load_provisioned_trust_bootstrap() -> _ProvisionedTrustBootstrap | None:
    """Return None until genuine out-of-band deployment provisioning exists."""
    return None
