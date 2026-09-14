import json
from pathlib import Path
import pandas as pd
from src.pipeline.freeze_prediction import normalize_lines


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
