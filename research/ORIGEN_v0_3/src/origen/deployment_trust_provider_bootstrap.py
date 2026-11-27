"""Deployment-owned ORIGEN trust-provider bootstrap.

The repository deliberately ships no authenticated provider. A reviewed deployment
image/package may replace this module through an administrative build process
that is independent of evidence submitters. Never load provider configuration
from request arguments, environment variables, repository data, CI variables,
receipt bytes, or a downloaded policy envelope.

The default loader returns None, so public provider-backed APIs fail closed.
A returned Python object is still not an unforgeable capability; the loader,
image provenance, service identity, administrative controls and external CAS
must be independently reviewed.
"""
from __future__ import annotations


def _load_deployment_trust_provider():
    """Return None until an independently provisioned provider is installed."""
    return None
