import numpy as np
import pytest
import joblib
from types import SimpleNamespace

import src.v264.CHISPAZO_V264_PARENT_REPAIR as v249_module

from src.v264.CHISPAZO_V264_PARENT_REPAIR import (
    _v249_numeric_payload_sha256,
    _v249_snapshot_manifest,
    _v249_snapshot_manifest_sha256,
    _v249_validate_snapshot_integrity,
    save_current_snapshot_v249,
    tie_safe_anti_saturation_score_v249,
)


def _payload():
    fused = np.array([0.11, 0.22, 0.33], dtype=np.float64)
    tie_signal = np.array([3.0, 2.0, 1.0], dtype=np.float64)
    anti_score, epsilon = tie_safe_anti_saturation_score_v249(fused, tie_signal)
    order = np.argsort(-anti_score, kind='stable').astype(np.int32)
    rank = np.empty(3, dtype=np.int32)
    rank[order] = np.arange(1, 4, dtype=np.int32)
    return {
        'anti_order': order,
        'anti_rank': rank,
        'anti_saturation_score': anti_score,
        'anti_saturation_epsilon': epsilon,
        'fused': fused,
        'portfolio_idx': np.array([2, 0], dtype=np.int32),
        'tie_signal': tie_signal,
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



def test_v249_snapshot_integrity_rejects_anti_score_not_derived_from_inputs():
    payload = _payload()
    payload['anti_saturation_score'][0] += 1e-6
    payload['score_payload_sha256'] = _v249_numeric_payload_sha256(payload)
    with pytest.raises(RuntimeError, match='anti_saturation_score inconsistent with fused/tie_signal'):
        _v249_validate_snapshot_integrity(payload)


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



def test_v249_snapshot_integrity_survives_joblib_roundtrip(tmp_path):
    payload = _payload()
    payload['score_payload_sha256'] = _v249_numeric_payload_sha256(payload)
    path = tmp_path / 'v249_snapshot.joblib'
    joblib.dump(payload, path, compress=3)
    restored = joblib.load(path)
    _v249_validate_snapshot_integrity(restored)
    assert restored['score_payload_sha256'] == payload['score_payload_sha256']
    assert np.array_equal(restored['anti_order'], payload['anti_order'])
    assert np.array_equal(restored['anti_rank'], payload['anti_rank'])





def test_v249_frozen_snapshot_reuse_revalidates_payload_and_refuses_corruption(tmp_path, monkeypatch):
    snapshot_path = tmp_path / 'snapshots' / 'target_12361.joblib'
    monkeypatch.setattr(v249_module, '_v249_snapshot_path', lambda _state_dir, _target: snapshot_path)
    audit = SimpleNamespace(max_concurso=12360, sha256='c' * 64)
    prod_gate = {'fusion_state': 'heuristic_only_after_holm', 'allocation_detail': {'state': 'validated'}}

    saved_path = save_current_snapshot_v249(tmp_path, 12361, audit, prod_gate, _payload())
    assert saved_path == snapshot_path
    original = joblib.load(saved_path)
    assert original['schema'] == 2
    assert original['manifest_sha256'] == _v249_snapshot_manifest_sha256(original)

    corrupted = dict(original)
    corrupted['anti_saturation_score'] = original['anti_saturation_score'].copy()
    corrupted['anti_saturation_score'][0] += 1e-5
    joblib.dump(corrupted, saved_path, compress=3)
    with pytest.raises(RuntimeError, match='numeric payload SHA256 mismatch'):
        save_current_snapshot_v249(tmp_path, 12361, audit, prod_gate, _payload())


def test_v249_frozen_snapshot_reuse_rejects_interpretation_metadata_tamper(tmp_path, monkeypatch):
    snapshot_path = tmp_path / 'snapshots' / 'target_12361.joblib'
    monkeypatch.setattr(v249_module, '_v249_snapshot_path', lambda _state_dir, _target: snapshot_path)
    audit = SimpleNamespace(max_concurso=12360, sha256='d' * 64)
    prod_gate = {'fusion_state': 'heuristic_only_after_holm', 'allocation_detail': {'state': 'validated'}}

    saved_path = save_current_snapshot_v249(tmp_path, 12361, audit, prod_gate, _payload())
    tampered = joblib.load(saved_path)
    tampered['tie_signal_name'] = 'different_signal_contract'
    joblib.dump(tampered, saved_path, compress=3)

    with pytest.raises(RuntimeError, match='existing manifest integrity failure'):
        save_current_snapshot_v249(tmp_path, 12361, audit, prod_gate, _payload())

def test_v249_oos_consume_rejects_snapshot_smaller_than_full_universe(tmp_path, monkeypatch):
    snapshot_path = tmp_path / 'snapshots' / 'target_12361.joblib'
    monkeypatch.setattr(v249_module, '_v249_snapshot_path', lambda _state_dir, _target: snapshot_path)
    save_audit = SimpleNamespace(max_concurso=12360, sha256='e' * 64)
    prod_gate = {'fusion_state': 'heuristic_only_after_holm', 'allocation_detail': {'state': 'validated'}}
    save_current_snapshot_v249(tmp_path, 12361, save_audit, prod_gate, _payload())

    import pandas as pd
    history = pd.DataFrame({'CONCURSO': [12361]})
    consume_audit = SimpleNamespace(max_concurso=12361)
    with pytest.raises(RuntimeError, match='universe size mismatch; expected 98280, got 3'):
        v249_module.consume_previous_snapshot_v249(
            history, consume_audit, tmp_path, {'v249_evaluated_targets': []}, lines=30
        )


def test_v249_snapshot_universe_guardrail_rejects_truncated_rank_vectors():
    payload = _payload()
    with pytest.raises(RuntimeError, match='universe size mismatch; expected 4, got 3'):
        v249_module._v249_validate_snapshot_universe(payload, expected_size=4)


def test_v249_snapshot_manifest_sha256_preserves_legacy_v1_contract():
    snapshot = {
        'schema': 1, 'target': 12361, 'history_last': 12360,
        'history_sha256': 'b' * 64, 'fusion_weights': {'heuristic': 1.0},
        'allocation': {'heuristic': 30}, 'portfolio_idx': np.array([1, 3], dtype=np.int32),
        'coverage_config': {'candidate_depth': 5000},
        'specialist_scores': {'heuristic': np.array([0.1, 0.2], dtype=np.float32)},
    }
    legacy_manifest = {
        'schema': 1, 'target': 12361, 'history_last': 12360,
        'history_sha256': 'b' * 64, 'fusion_weights': {'heuristic': 1.0},
        'allocation': {'heuristic': 30}, 'portfolio_idx': [1, 3],
        'coverage_config': {'candidate_depth': 5000}, 'strategies': ['heuristic'],
    }
    expected = __import__('hashlib').sha256(
        __import__('json').dumps(legacy_manifest, sort_keys=True, separators=(',', ':')).encode('utf-8')
    ).hexdigest()
    assert _v249_snapshot_manifest_sha256(snapshot) == expected


def test_v249_snapshot_manifest_sha256_rejects_unsupported_schema():
    with pytest.raises(RuntimeError, match='unsupported snapshot schema'):
        _v249_snapshot_manifest_sha256({'schema': 99})


def test_v249_v2_manifest_binds_interpretation_metadata():
    payload = _payload()
    payload.update({
        'schema': 2,
        'target': 12361,
        'history_last': 12360,
        'history_sha256': 'a' * 64,
        'tie_signal_name': 'heuristic_unclipped',
        'anti_saturation_epsilon': 1e-12,
        'fusion_state': 'heuristic_only_after_holm',
        'allocation_state': 'validated',
        'trained_at': 12360,
        'created_at': '2026-11-19 20:00:00',
    })
    payload['score_payload_sha256'] = _v249_numeric_payload_sha256(payload)
    manifest = _v249_snapshot_manifest(payload)
    baseline = __import__('hashlib').sha256(
        __import__('json').dumps(manifest, sort_keys=True, separators=(',', ':')).encode('utf-8')
    ).hexdigest()
    payload['tie_signal_name'] = 'tampered_interpretation'
    changed = _v249_snapshot_manifest(payload)
    changed_hash = __import__('hashlib').sha256(
        __import__('json').dumps(changed, sort_keys=True, separators=(',', ':')).encode('utf-8')
    ).hexdigest()
    assert baseline != changed_hash
