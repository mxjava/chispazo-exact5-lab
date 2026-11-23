import io
import json
from pathlib import Path
import pandas as pd
from src.pipeline.freeze_prediction import normalize_lines, reject_non_predictive_portfolio
from src.pipeline.generate_uniform_portfolio import generate_uniform_portfolio, write_portfolio


def test_normalize_30_distinct():
    # 30 deterministic valid lines, not a prediction.
    lines=[]
    for i in range(30):
        a=1+(i%6)
        nums=sorted({a,7+(i%5),12+(i%5),18+(i%5),24+(i%5)})
        if len(nums)!=5:
            nums=[1,7,12,18,24+i%5]
        lines.append('-'.join(map(str,nums)))
    # ensure fixture itself is unique; normalize function is tested with generated combinations below
    combos=[]
    import itertools
    for c in itertools.islice(itertools.combinations(range(1,29),5),30):
        combos.append('-'.join(map(str,c)))
    out=normalize_lines(pd.DataFrame({'combo':combos}))
    assert len(out)==30 and len(set(out))==30


def test_uniform_coverage_portfolio_is_rejected_from_predictive_freeze():
    frame = pd.DataFrame({
        "combo": [f"{i:02d}-02-03-04-05" for i in range(1, 31)],
        "mode": ["UNIFORM_COVERAGE_NOT_PREDICTIVE"] * 30,
    })
    import pytest
    with pytest.raises(ValueError, match="explicitly non-predictive"):
        reject_non_predictive_portfolio(frame)


def test_predictive_candidate_mode_is_not_misclassified_as_uniform():
    frame = pd.DataFrame({
        "combo": [f"{i:02d}-02-03-04-05" for i in range(1, 31)],
        "mode": ["PREDICTIVE_CANDIDATE"] * 30,
    })
    reject_non_predictive_portfolio(frame)


def test_uniform_generator_output_cannot_enter_predictive_freeze():
    csv_buffer = io.StringIO()
    write_portfolio(generate_uniform_portfolio(seed=20261123, lines=30), 20261123, csv_buffer)
    csv_buffer.seek(0)
    frame = pd.read_csv(csv_buffer)
    import pytest
    with pytest.raises(ValueError, match="uniform coverage output"):
        reject_non_predictive_portfolio(frame)
