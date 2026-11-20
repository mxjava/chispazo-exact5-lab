from v265.CHISPAZO_V265_PHYSICAL_METADATA_EVALUATOR import (
    V265_PROMOTION_BLOCKERS,
    v265_evidence_guardrail,
)


def test_v265_regime_proxy_can_never_be_physical_bias_evidence():
    result = v265_evidence_guardrail(proxy_association=True)
    assert result["proxy_association"] is True
    assert result["research_edge"] is False
    assert result["physical_bias_evidence"] is False
    assert result["physical_measurements_consumed"] is False
    assert result["physical_identity_mapping_verified"] is False
    assert result["rfid_event_log_consumed"] is False
    assert result["extraction_order_consumed"] is False
    assert result["classification"] == "RESEARCH_ONLY_REGIME_PROXY_NOT_PHYSICAL_EVIDENCE"


def test_v265_proxy_can_never_be_actionable_or_promoted():
    for proxy in (False, True):
        result = v265_evidence_guardrail(proxy_association=proxy)
        assert result["actionable_for_betting"] is False
        assert result["promotion_eligible"] is False


def test_v265_promotion_blockers_cover_missing_physical_traceability_and_exact5_gates():
    required = {
        "NO_28_PER_SPHERE_MASSES",
        "NO_STABLE_PHYSICAL_SPHERE_IDS",
        "NO_VERIFIED_SPHERE_ID_TO_PRINTED_NUMBER_MAPPING",
        "NO_RAW_RFID_TAG_READER_EVENT_LOG",
        "NO_FEEDER_LOAD_OR_EXTRACTION_ORDER",
        "NO_PRIMARY_DOCUMENT_AUTHENTICATION_AND_INDEPENDENT_CUSTODY",
        "NO_TRUSTED_TIMESTAMP_CHAIN_FOR_EACH_PHYSICAL_EVENT",
        "NO_EXACT5_ANYTIME_E_VALUE_GATE",
        "NO_TWO_INDEPENDENTLY_SEALED_PRE_CLOSE_OUTPUTS",
    }
    assert set(V265_PROMOTION_BLOCKERS) == required
