import numpy as np
import pytest

from src.v264.CHISPAZO_V264_PARENT_REPAIR import (
    _v249_numeric_payload_sha256,
    _v249_validate_snapshot_integrity,
)


def _payload():
    order = np.array([2, 1, 0], dtype=np.int32)
    rank = np.empty(3, dtype=np.int32)
    rank[order] = np.arange(1, 4, dtype=np.int32)
    return {
        'anti_order': order,
        'anti_rank': rank,
        'anti_saturation_score': np.array([0.1, 0.2, 0.3], dtype=np.float64),
        'fused': np.array([0.11, 0.22, 0.33], dtype=np.float64),
        'portfolio_idx': np.array([2, 0], dtype=np.int32),
        'tie_signal': np.array([3.0, 2.0, 1.0], dtype=np.float64),
        'specialist_scores': {'heuristic': np.array([1.0, 2.0, 3.0], dtype=np.float64)},
    }


def test_v249_payload_digest_is_stable_and_binds_dtype_and_shape():
    payload = _payload()
    digest = _v249_numeric_payload_sha256(payload)
    assert digest == _v249_numeric_payload_sha256(payload)
    changed_dtype = dict(payload, fused=payload['fused'].astype(np.float32))
    assert digest != _v249_numeric_payload_sha256(changed_dtype)
    changed_shape = dict(payload, fused=payload['fused'].reshape(3, 1))
    assert digest != _v249_numeric_payload_sha256(changed_shape)


def test_v249_snapshot_integrity_accepts_inverse_rank_vectors():
    payload = _payload()
    payload['score_payload_sha256'] = _v249_numeric_payload_sha256(payload)
    _v249_validate_snapshot_integrity(payload)


def test_v249_snapshot_integrity_rejects_payload_mutation():
    payload = _payload()
    payload['score_payload_sha256'] = _v249_numeric_payload_sha256(payload)
    payload['fused'][0] += 1e-12
    with pytest.raises(RuntimeError, match='numeric payload SHA256 mismatch'):
        _v249_validate_snapshot_integrity(payload)


def test_v249_snapshot_integrity_rejects_non_inverse_rank_vectors():
    payload = _payload()
    payload['anti_rank'] = np.array([1, 2, 3], dtype=np.int32)
    payload['score_payload_sha256'] = _v249_numeric_payload_sha256(payload)
    with pytest.raises(RuntimeError, match='anti_order/anti_rank mismatch'):
        _v249_validate_snapshot_integrity(payload)


def test_v249_snapshot_integrity_rejects_non_permutation_order():
    payload = _payload()
    payload['anti_order'] = np.array([0, 0, 2], dtype=np.int32)
    payload['score_payload_sha256'] = _v249_numeric_payload_sha256(payload)
    with pytest.raises(RuntimeError, match='anti_order is not an integer permutation'):
        _v249_validate_snapshot_integrity(payload)


def test_v249_snapshot_integrity_rejects_object_arrays():
    payload = _payload()
    payload['specialist_scores'] = {'bad': np.array([object()], dtype=object)}
    with pytest.raises(TypeError, match='unsupported dtype'):
        _v249_numeric_payload_sha256(payload)



def test_v249_snapshot_integrity_rejects_order_not_matching_saved_scores():
    payload = _payload()
    payload['anti_order'] = np.array([0, 1, 2], dtype=np.int32)
    payload['anti_rank'] = np.array([1, 2, 3], dtype=np.int32)
    payload['score_payload_sha256'] = _v249_numeric_payload_sha256(payload)
    with pytest.raises(RuntimeError, match='anti_order does not match anti_saturation_score'):
        _v249_validate_snapshot_integrity(payload)


def test_v249_snapshot_integrity_rejects_duplicate_portfolio_indices():
    payload = _payload()
    payload['portfolio_idx'] = np.array([2, 2], dtype=np.int32)
    payload['score_payload_sha256'] = _v249_numeric_payload_sha256(payload)
    with pytest.raises(RuntimeError, match='portfolio_idx out of range or duplicated'):
        _v249_validate_snapshot_integrity(payload)



def test_v249_snapshot_integrity_rejects_float32_v2_scores():
    payload = _payload()
    payload['anti_saturation_score'] = payload['anti_saturation_score'].astype(np.float32)
    payload['score_payload_sha256'] = _v249_numeric_payload_sha256(payload)
    with pytest.raises(RuntimeError, match='v2 score arrays must be float64'):
        _v249_validate_snapshot_integrity(payload)


def test_v249_snapshot_integrity_rejects_non_finite_scores():
    payload = _payload()
    payload['fused'][1] = np.nan
    payload['score_payload_sha256'] = _v249_numeric_payload_sha256(payload)
    with pytest.raises(RuntimeError, match='non-finite score payload'):
        _v249_validate_snapshot_integrity(payload)



def test_v249_snapshot_integrity_rejects_misaligned_specialist_vector():
    payload = _payload()
    payload['specialist_scores'] = {'heuristic': np.array([1.0, 2.0], dtype=np.float64)}
    payload['score_payload_sha256'] = _v249_numeric_payload_sha256(payload)
    with pytest.raises(RuntimeError, match='score vector shapes do not match universe'):
        _v249_validate_snapshot_integrity(payload)
