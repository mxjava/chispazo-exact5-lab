import pandas as pd
import pytest

from src.v265.CHISPAZO_V265_PHYSICAL_METADATA_EVALUATOR import (
    betting_gate_status,
    parse_local_timestamp,
    validate_postclose_final_metadata,
    validate_source_provenance,
)


def test_parse_local_timestamp_requires_explicit_timezone():
    with pytest.raises(ValueError, match="timezone offset is required"):
        parse_local_timestamp("2026-11-21T20:00:00", 12387, "close_time_local")


def test_parse_local_timestamp_normalizes_explicit_offset_to_mexico_city():
    value = parse_local_timestamp("2026-11-22T03:00:00Z", 12387, "close_time_local")
    assert str(value.tz) == "America/Mexico_City"
    assert value.hour == 21


def test_source_provenance_requires_document_url_and_sha256():
    good = pd.DataFrame([{
        "CONCURSO": 12387,
        "source_document": "official-acta.pdf",
        "source_url": "https://example.org/official-acta.pdf",
        "source_sha256": "a" * 64,
    }])
    assert validate_source_provenance(good) is True


@pytest.mark.parametrize("digest", ["", "xyz", "a" * 63, "g" * 64])
def test_source_provenance_rejects_invalid_sha256(digest):
    frame = pd.DataFrame([{
        "CONCURSO": 12387,
        "source_document": "official-acta.pdf",
        "source_url": "https://example.org/official-acta.pdf",
        "source_sha256": digest,
    }])
    with pytest.raises(ValueError, match="source_sha256"):
        validate_source_provenance(frame)


def test_final_sphere_set_must_be_timestamped_after_close():
    frame = pd.DataFrame([{
        "CONCURSO": 12387,
        "close_time_local": "2026-11-21T21:00:00-06:00",
        "final_sphere_set_known_time_utc": "2026-11-22T02:59:00Z",
    }])
    with pytest.raises(ValueError, match="at or after close"):
        validate_postclose_final_metadata(frame)


def test_final_sphere_set_timestamp_at_close_is_accepted():
    frame = pd.DataFrame([{
        "CONCURSO": 12387,
        "close_time_local": "2026-11-21T21:00:00-06:00",
        "final_sphere_set_known_time_utc": "2026-11-22T03:00:00Z",
    }])
    assert validate_postclose_final_metadata(frame) is True


def test_statistical_candidate_never_authorizes_betting_without_external_gates():
    gate = betting_gate_status(
        research_edge=True,
        n_oos=500,
        mean_log_lift=0.02,
        holm_adjusted_p=0.001,
    )
    assert gate["actionable_for_betting"] is False
    assert gate["status"] == "BLOCKED_EXTERNAL_EXACT5_AND_CUSTODY_GATES"
    assert "exact5_anytime_evalue_not_ingested_or_verified" in gate["blockers"]
    assert "independent_preclose_custody_not_ingested_or_verified" in gate["blockers"]
