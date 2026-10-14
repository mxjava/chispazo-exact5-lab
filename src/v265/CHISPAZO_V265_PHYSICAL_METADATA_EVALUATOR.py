from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
from collections import defaultdict

LOCAL_TZ = "America/Mexico_City"

N=28; K=5; BASE=K/N


def _ensure_data_deps():
    """Import heavy data dependencies only after cheap CLI validation."""
    global np, pd
    if "np" not in globals() or "pd" not in globals():
        import numpy as np_module
        import pandas as pd_module
        np = np_module
        pd = pd_module

def logprob_conditional5(p, chosen):
    _ensure_data_deps()
    p=np.clip(np.asarray(p,float),1e-9,1-1e-9)
    w=p/(1-p)
    e=np.zeros(K+1,float); e[0]=1.0
    for x in w:
        for j in range(K,0,-1): e[j]+=x*e[j-1]
    return sum(math.log(w[n-1]) for n in chosen)-math.log(e[K])

def shrunk_prob(counts, trials, prior):
    _ensure_data_deps()
    return (counts + prior*BASE)/(trials+prior)

def one_sided_ttest_greater(values):
    """Return (t, p) for H1: mean > 0 using the Student-t survival function."""
    _ensure_data_deps()
    arr = np.asarray(values, dtype=float)
    arr = arr[~np.isnan(arr)]  # match scipy.stats nan_policy="omit"
    if arr.size < 2 or not np.isfinite(arr).all():
        return float("nan"), float("nan")
    mean = float(np.mean(arr))
    sd = float(np.std(arr, ddof=1))
    if sd == 0.0:
        if mean > 0:
            return float("inf"), 0.0
        if mean < 0:
            return float("-inf"), 1.0
        return float("nan"), float("nan")
    t_stat = mean / (sd / math.sqrt(arr.size))
    # scipy.special is much lighter to import than scipy.stats, whose import
    # eagerly loads the broader optimization/statistics stack in CLI subprocesses.
    from scipy.special import stdtr
    return float(t_stat), float(stdtr(arr.size - 1, -t_stat))


def validate_draw_numbers(row, contest):
    """Reject malformed draws before likelihood or count updates."""
    vals = []
    for j in range(1, K + 1):
        raw = row[f"R{j}"]
        try:
            value = float(raw)
        except (TypeError, ValueError):
            raise ValueError(f"contest {contest}: R{j} is not numeric: {raw!r}")
        if not math.isfinite(value) or not value.is_integer():
            raise ValueError(f"contest {contest}: R{j} must be a finite integer, got {raw!r}")
        n = int(value)
        if not 1 <= n <= N:
            raise ValueError(f"contest {contest}: R{j} outside 1..{N}: {n}")
        vals.append(n)
    if len(set(vals)) != K:
        raise ValueError(f"contest {contest}: draw must contain {K} distinct numbers")
    return tuple(sorted(vals))


def validate_contest_keys(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    """Normalize and validate one row per integral contest ID before joining."""

    _ensure_data_deps()
    if 'CONCURSO' not in frame.columns:
        raise ValueError(f'{label} missing CONCURSO')
    key = pd.to_numeric(frame['CONCURSO'], errors='coerce')
    values = key.to_numpy(dtype=float)
    if key.isna().any() or not np.isfinite(values).all() or not np.equal(values, np.floor(values)).all():
        raise ValueError(f'{label} CONCURSO must contain finite integer IDs')
    duplicates = key.duplicated(keep=False)
    if (key <= 0).any():
        raise ValueError(f'{label} CONCURSO IDs must be positive integers')
    if duplicates.any():
        examples = sorted({int(v) for v in key[duplicates].tolist()})[:5]
        raise ValueError(f'{label} has duplicate CONCURSO IDs: {examples}')
    out = frame.copy()
    out['CONCURSO'] = key.astype('int64')
    return out


def holm_adjust(p_values):
    """Return Holm family-wise adjusted p-values in input order."""

    _ensure_data_deps()
    p = np.asarray(p_values, dtype=float)
    if p.ndim != 1 or len(p) == 0 or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("p-values must be a non-empty finite vector in [0, 1]")
    order = np.argsort(p)
    adjusted = np.empty(len(p), dtype=float)
    running = 0.0
    m = len(p)
    for rank, idx in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p[idx]))
        adjusted[idx] = running
    return adjusted


def read_p_family(path, candidate_id, observed_p):
    """Validate a predeclared family of all tested one-sided p-values."""

    _ensure_data_deps()
    family = pd.read_csv(path)
    required = {'candidate_id', 'p_one_sided'}
    if not required.issubset(family.columns):
        raise ValueError(f"p-family file must contain columns {sorted(required)}")
    ids_clean = family['candidate_id'].astype('string').str.strip()
    if ids_clean.isna().any() or ids_clean.eq('').any() or ids_clean.duplicated().any():
        raise ValueError("p-family candidate_id values must be non-empty and unique after trimming")
    values = pd.to_numeric(family['p_one_sided'], errors='coerce').to_numpy(dtype=float)
    adjusted = holm_adjust(values)
    ids = ids_clean.tolist()
    candidate_id = str(candidate_id).strip()
    if candidate_id not in ids:
        raise ValueError(f"candidate_id {candidate_id!r} missing from p-family")
    idx = ids.index(candidate_id)
    if abs(float(values[idx]) - float(observed_p)) > 1e-8:
        raise ValueError("candidate p-value in family does not match the observed p-value")
    return float(adjusted[idx]), len(ids)


def parse_availability(value, contest):
    text = str(value).strip().lower()
    if text in ('1', 'true', 'yes', 'si', 'sí'):
        return True
    if text in ('0', 'false', 'no'):
        return False
    raise ValueError(f"contest {contest}: invalid available_before_close value {value!r}")


def parse_local_timestamp(value, contest, field):
    """Parse a timestamp, interpreting naive values as Mexico City local time."""

    _ensure_data_deps()
    if pd.isna(value) or not str(value).strip():
        raise ValueError(f"contest {contest}: missing {field}")
    try:
        ts = pd.Timestamp(value)
        if pd.isna(ts):
            raise ValueError("NaT")
        if ts.tzinfo is None:
            ts = ts.tz_localize(LOCAL_TZ, ambiguous="raise", nonexistent="raise")
        else:
            ts = ts.tz_convert(LOCAL_TZ)
        return ts
    except Exception as exc:
        raise ValueError(f"contest {contest}: invalid {field} timestamp {value!r}") from exc


def validate_preclose_metadata(metadata):
    """Do not score any regime label unless its timestamp proves it predates close."""
    parsed = []
    unavailable = []
    for row in metadata.itertuples(index=False):
        contest = int(getattr(row, "CONCURSO"))
        available = bool(getattr(row, "available_before_close"))
        known = parse_local_timestamp(getattr(row, "metadata_known_time_local"), contest, "metadata_known_time_local")
        close = parse_local_timestamp(getattr(row, "close_time_local"), contest, "close_time_local")
        if not available:
            unavailable.append(contest)
        if known >= close:
            raise ValueError(
                f"contest {contest}: metadata_known_time_local must be strictly before close_time_local"
            )
        parsed.append((contest, known, close))
    if unavailable:
        raise ValueError(
            "physical metadata must be available before close for every history row; "
            f"unavailable_contests={unavailable[:5]}"
        )
    return parsed

def main():
    ap=argparse.ArgumentParser(description='V265 evaluator: physical metadata, chronological prequential only')
    ap.add_argument('--history',required=True)
    ap.add_argument('--metadata',required=True)
    ap.add_argument('--out-dir',default='v265_physical_eval')
    ap.add_argument('--burn',type=int,default=100)
    ap.add_argument('--prior-set',type=float,default=300.0)
    ap.add_argument('--prior-machine',type=float,default=600.0)
    ap.add_argument('--p-family', help='CSV of all predeclared candidate_id,p_one_sided tests')
    ap.add_argument('--candidate-id', default='physical_ensemble')
    args=ap.parse_args()
    if args.burn < 0:
        ap.error('--burn must be >= 0')
    if not math.isfinite(args.prior_set) or args.prior_set <= 0:
        ap.error('--prior-set must be finite and > 0')
    if not math.isfinite(args.prior_machine) or args.prior_machine <= 0:
        ap.error('--prior-machine must be finite and > 0')
    # Invalid CLI parameters fail before importing NumPy/Pandas/SciPy.
    _ensure_data_deps()
    out=Path(args.out_dir); out.mkdir(parents=True,exist_ok=True)
    # Remove prior outputs first: a failed rerun must never leave a stale report
    # that can be mistaken for evidence from the current inputs.
    csv_path = out / 'v265_physical_prequential.csv'
    report_path = out / 'v265_physical_eval_report.json'
    temp_csv = out / '.v265_physical_prequential.csv.tmp'
    temp_report = out / '.v265_physical_eval_report.json.tmp'
    for stale in (csv_path, report_path, temp_csv, temp_report):
        stale.unlink(missing_ok=True)
    h=pd.read_csv(args.history)
    m=pd.read_csv(args.metadata)
    req_h=['CONCURSO','R1','R2','R3','R4','R5']
    req_m=['CONCURSO','sphere_set_id','machine_id','available_before_close','close_time_local','metadata_known_time_local']
    for c in req_h:
        if c not in h: raise ValueError(f'history missing {c}')
    for c in req_m:
        if c not in m: raise ValueError(f'metadata missing {c}')
    h=validate_contest_keys(h,'history')
    m=validate_contest_keys(m,'metadata')
    # Physical regime labels must cover the exact chronological history used by
    # the online state. An inner join over partial metadata silently skips draws
    # from both scoring and state updates, which can make a partial sample look
    # like a complete prospective evaluation.
    history_ids = set(h['CONCURSO'].tolist())
    metadata_ids = set(m['CONCURSO'].tolist())
    missing_metadata = sorted(history_ids - metadata_ids)
    extra_metadata = sorted(metadata_ids - history_ids)
    if missing_metadata or extra_metadata:
        raise ValueError(
            'metadata CONCURSO coverage must exactly match history; '
            f'missing_metadata={missing_metadata[:5]} '
            f'extra_metadata={extra_metadata[:5]} '
            f'history_rows={len(h)} metadata_rows={len(m)}'
        )
    # Validate availability flags for all rows, including the burn-in period.
    m['available_before_close'] = [
        parse_availability(value, contest)
        for contest, value in zip(m['CONCURSO'], m['available_before_close'])
    ]
    # The boolean flag alone is not proof: require source-known time < close time
    # for every row, including burn-in, before any physical label enters the state.
    validate_preclose_metadata(m)
    for col in ('sphere_set_id', 'machine_id'):
        cleaned = m[col].astype('string').str.strip()
        if cleaned.isna().any() or cleaned.eq('').any():
            raise ValueError(f'metadata {col} must be present and non-empty for every row')
        m[col] = cleaned
    x=h.merge(m,on='CONCURSO',how='inner',validate='one_to_one').sort_values('CONCURSO').reset_index(drop=True)
    if len(x)<args.burn+30: raise ValueError('Insufficient joined metadata for prequential evaluation')
    global_c=np.zeros(N,int); global_t=0
    set_c=defaultdict(lambda:np.zeros(N,int)); set_t=defaultdict(int)
    mach_c=defaultdict(lambda:np.zeros(N,int)); mach_t=defaultdict(int)
    rows=[]
    for i,r in x.iterrows():
        y=validate_draw_numbers(r, r['CONCURSO'])
        sid=str(r['sphere_set_id']); mid=str(r['machine_id'])
        if i>=args.burn:
            pg=shrunk_prob(global_c,global_t,1000.0)
            ps=shrunk_prob(set_c[sid],set_t[sid],args.prior_set)
            pm=shrunk_prob(mach_c[mid],mach_t[mid],args.prior_machine)
            # Equal-weight log-odds ensemble; no target outcome enters these probabilities.
            def lg(p): return np.log(np.clip(p,1e-9,1-1e-9)/(1-np.clip(p,1e-9,1-1e-9)))
            z=(lg(pg)+lg(ps)+lg(pm))/3.0
            p=1/(1+np.exp(-z))
            lp=logprob_conditional5(p,y)
            logu=-math.log(math.comb(N,K))
            rows.append({'CONCURSO':int(r.CONCURSO),'log_lift':lp-logu,
                         'sphere_set_id':sid,'machine_id':mid,
                         'available_before_close':parse_availability(r['available_before_close'], r['CONCURSO'])})
        global_t+=1; set_t[sid]+=1; mach_t[mid]+=1
        for n in y:
            global_c[n-1]+=1; set_c[sid][n-1]+=1; mach_c[mid][n-1]+=1
    d=pd.DataFrame(rows)
    mean=float(d.log_lift.mean())
    t,p1=one_sided_ttest_greater(d.log_lift.to_numpy(dtype=float))
    all_preclose=bool(d.available_before_close.all())
    adjusted_p=None; family_size=0
    if args.p_family:
        adjusted_p, family_size = read_p_family(Path(args.p_family), args.candidate_id, p1)
    # A single unadjusted p-value is never enough to promote after model search.
    sample_ok = len(d) >= 100
    research_edge=bool(sample_ok and mean>0 and adjusted_p is not None and adjusted_p < 0.05)
    actionable=bool(research_edge and all_preclose and len(x) == len(h) and len(x) == len(m))
    if not sample_ok:
        decision='RESEARCH_ONLY_INSUFFICIENT_OOS_N'
    elif mean <= 0:
        decision='NO_PHYSICAL_EDGE'
    elif adjusted_p is None:
        decision='RESEARCH_ONLY_MULTIPLICITY_CONTROL_REQUIRED'
    elif adjusted_p >= 0.05:
        decision='NO_PHYSICAL_EDGE_AFTER_HOLM'
    elif not all_preclose:
        decision='RESEARCH_EDGE_NOT_ACTIONABLE_METADATA_NOT_PRE_CLOSE'
    else:
        decision='PROSPECTIVE_GATE_CANDIDATE_REVIEW_REQUIRED'
    def sha256_file(path):
        digest=hashlib.sha256()
        with open(path,'rb') as fh:
            for chunk in iter(lambda: fh.read(1024*1024), b''):
                digest.update(chunk)
        return digest.hexdigest()
    rep={'model_version':'V269.2-preclose-timestamp-integrity',
         'input_sha256':{'history':sha256_file(args.history),'metadata':sha256_file(args.metadata),
                         'p_family':sha256_file(args.p_family) if args.p_family else None},
         'parameters':{'burn':args.burn,'prior_set':args.prior_set,'prior_machine':args.prior_machine,
                       'candidate_id':args.candidate_id},
         'chronology':'ascending CONCURSO ID; score first, then update counts',
         'n':len(d),'mean_log_lift':mean,'one_sided_p':p1,
         'multiplicity_controlled': adjusted_p is not None,
         'holm_adjusted_p': adjusted_p, 'p_family_size': family_size,
         'minimum_oos_n':100, 'all_metadata_available_before_close':all_preclose,
         'research_edge':research_edge,'actionable_for_betting':actionable,
         'decision': decision,
         'history_rows':len(h),'metadata_rows':len(m),'joined_rows':len(x),
         'metadata_coverage_fraction_of_history':float(len(x)/len(h)) if len(h) else 0.0,
         'preclose_fraction_of_scored_rows':float(d.available_before_close.mean()),
         'production_rule':'Do not score or promote unless every physical metadata row is available before close by both flag and timestamp, with >=100 prequential OOS rows, positive mean log-lift, and Holm-adjusted p < 0.05 across the predeclared candidate family.'}
    # Stage both artifacts only after all input and multiplicity checks pass.
    # The report is published last and serves as the completion marker.
    try:
        d.to_csv(temp_csv, index=False)
        temp_report.write_text(json.dumps(rep, indent=2), encoding='utf-8')
        temp_csv.replace(csv_path)
        temp_report.replace(report_path)
    finally:
        temp_csv.unlink(missing_ok=True)
        temp_report.unlink(missing_ok=True)
    print(json.dumps(rep,indent=2))

if __name__=='__main__': main()
