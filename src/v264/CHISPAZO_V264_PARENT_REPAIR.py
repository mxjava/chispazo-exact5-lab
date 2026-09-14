"""
CHISPAZO HYPERLAB V249 — COVERAGE-CONSTRAINED ANTI-SATURATION EXACT5 + PROSPECTIVE EVIDENCE
=======================================================

V249 conserva el model-core V248 y agrega allocator de cobertura, score anti-saturación y auditoría de concentración:
- El ranker nuevo usa relevancia binaria: ganador exacto=1, cualquier no-ganador=0.
- Durante walk-forward, después de resolver cada target, mina falsos positivos Top-K
  de varios modelos que habían sido calculados ANTES de conocer ese resultado.
- Esos falsos positivos se agregan únicamente a re-entrenamientos FUTUROS del LTR,
  preservando causalidad y reduciendo el gap entrenamiento(~121 candidatos) -> inferencia(98,280).
- V244 (Holm/FDR, HAC, preregistro y evidencia prospectiva) se conserva como guardrail.
=======================================================

Objetivo:
- Rankear las 98,280 combinaciones posibles de Chispazo 5/28.
- Evitar fugas temporales.
- Usar señales causales / históricas únicamente.
- Combinar:
    * frecuencia multi-ventana
    * EWMA
    * gap / recencia
    * transición desde último sorteo
    * pares
    * carry / overlap
    * estructura geométrica
    * contexto temporal (si FECHA existe)
    * parent-4 fertility
    * dead->born swap tensor
    * exact-lag / recurrence
    * ensemble supervisado
- Validar:
    * frozen holdout
    * walk-forward
    * baseline uniforme
    * ranking del exacto
- Producir:
    * ranking completo
    * Top N líneas
    * reportes JSON / CSV / Markdown
    * decisión técnica de PLAY / NO_PLAY según evidencia

IMPORTANTE:
Este programa NO garantiza 5/5.
En un sorteo justo, la probabilidad uniforme de una línea exacta es 1 / C(28,5) = 1 / 98,280.
El objetivo del motor es verificar si alguna estructura histórica logra concentrar el resultado futuro
en posiciones superiores del ranking de forma estable y sin fuga.

Dependencias:
    pip install pandas numpy scikit-learn

Uso típico:
    python CHISPAZO_V249_COVERAGE_ANTISAT_EXACT5.py --history "Chispazo.csv" --lines 30 --backtest 120

Modo fuerte:
    python CHISPAZO_V249_COVERAGE_ANTISAT_EXACT5.py --history "Chispazo.csv" --lines 50 --backtest 250 --frozen 1000

Para concurso específico:
    python CHISPAZO_V249_COVERAGE_ANTISAT_EXACT5.py --history "Chispazo.csv" --target 12234 --expected-last 12233 --lines 30

Autoría:
    Consolidación técnica del linaje V176/V192/V203/V226/V227 + full-universe rank learning.
"""
from __future__ import annotations
import argparse
import hashlib
import itertools
import json
import math
import os
import random
import sys
import time
import tomllib
import warnings
from contextvars import ContextVar
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict, fields
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Mapping, Any
from types import MappingProxyType
import numpy as np
import pandas as pd

try:
    from scipy.stats import binomtest, beta as beta_dist, norm as norm_dist, binom as binom_dist, hypergeom as hypergeom_dist
    SCIPY_STATS_OK = True
except Exception as _e:
    binomtest = beta_dist = norm_dist = binom_dist = hypergeom_dist = None
    SCIPY_STATS_OK = False

try:
    from scipy.optimize import milp, LinearConstraint, Bounds
    from scipy.sparse import coo_matrix
    SCIPY_MILP_OK = True
except Exception as _e:
    milp = LinearConstraint = Bounds = coo_matrix = None
    SCIPY_MILP_OK = False

try:
    import optuna
    from sklearn.metrics import average_precision_score
    OPTUNA_OK = True
    optuna.logging.set_verbosity(optuna.logging.WARNING)
except Exception as _e:
    optuna = None
    average_precision_score = None
    OPTUNA_OK = False

try:
    import joblib
    JOBLIB_OK = True
except Exception as _e:
    joblib = None
    JOBLIB_OK = False

try:
    from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline
    from sklearn.metrics import roc_auc_score
    SKLEARN_OK = True
except Exception as _e:
    ExtraTreesClassifier = RandomForestClassifier = LogisticRegression = None
    StandardScaler = Pipeline = None
    roc_auc_score = None
    SKLEARN_OK = False

try:
    import xgboost as xgb
    from xgboost import XGBClassifier, XGBRanker
    XGBOOST_OK = True
except Exception as _e:
    xgb = XGBClassifier = XGBRanker = None
    XGBOOST_OK = False


@dataclass(frozen=True)
class ModelRuntime:
    gpu_enabled: bool
    gpu_required: bool
    gpu_device: str
    gpu_status: Dict[str, object]
    xgb_estimators: int

    @property
    def gpu_available(self) -> bool:
        return bool(self.gpu_enabled and self.gpu_status.get('available', False))

    @property
    def device(self) -> str:
        return self.gpu_device if self.gpu_available else 'cpu'

DEFAULT_XGB_ESTIMATORS = 700

def default_model_runtime() -> ModelRuntime:
    """Pure fallback runtime. Active V248 always injects a runtime explicitly."""
    return ModelRuntime(False, False, 'cpu', {'requested': False, 'available': False, 'device': 'cpu', 'reason': 'default CPU runtime'}, DEFAULT_XGB_ESTIMATORS)
_PROGRESS_ENABLED_CTX: ContextVar[bool] = ContextVar('v248_progress_enabled', default=True)
_PROGRESS_EVERY_CTX: ContextVar[int] = ContextVar('v248_progress_every', default=10)
_PROGRAM_T0_CTX: ContextVar[float] = ContextVar('v248_program_t0', default=time.time())

def configure_progress_v248(*, enabled: bool, every: int, t0: float) -> None:
    _PROGRESS_ENABLED_CTX.set(bool(enabled))
    _PROGRESS_EVERY_CTX.set(max(1, int(every)))
    _PROGRAM_T0_CTX.set(float(t0))

def _progress_enabled() -> bool:
    return bool(_PROGRESS_ENABLED_CTX.get())

def _progress_every() -> int:
    return max(1, int(_PROGRESS_EVERY_CTX.get()))

def progress(message: str, *, done: int | None=None, total: int | None=None) -> None:
    """Context-local progress reporting for parallel-safe independent runs."""
    if not _progress_enabled():
        return
    elapsed = time.time() - float(_PROGRAM_T0_CTX.get())
    prefix = time.strftime('%H:%M:%S')
    if done is not None and total:
        pct = 100.0 * done / max(1, total)
        print(f'[{prefix}] [{elapsed:8.1f}s] {message}  {done}/{total} ({pct:5.1f}%)', flush=True)
    else:
        print(f'[{prefix}] [{elapsed:8.1f}s] {message}', flush=True)
def log_exception(context: str, exc: BaseException) -> None:
    """Never degrade silently: report exception class and execution context."""
    print(f"WARNING [{context}] {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)

N_NUMBERS = 28
DRAW_SIZE = 5
NUMBERS = tuple(range(1, N_NUMBERS + 1))
REQ_COLS = ['CONCURSO', 'R1', 'R2', 'R3', 'R4', 'R5']
UNIVERSE_SIZE = math.comb(N_NUMBERS, DRAW_SIZE)
PRIMES = {2, 3, 5, 7, 11, 13, 17, 19, 23}
R_COLS = [f'R{i}' for i in range(1, 6)]
DEFAULT_SEED = 777
V248_SAMPLER_ARM_NAMES = ('balanced', 'hard', 'ultra')
ALL_COMBOS = np.array(list(itertools.combinations(NUMBERS, DRAW_SIZE)), dtype=np.int16)
COMBO_TO_INDEX = {tuple(map(int, c)): i for i, c in enumerate(ALL_COMBOS)}
COMBO_MASK = np.zeros((UNIVERSE_SIZE, N_NUMBERS), dtype=np.uint8)
COMBO_MASK[np.arange(UNIVERSE_SIZE)[:, None], ALL_COMBOS - 1] = 1
COMBO_SUM = ALL_COMBOS.sum(axis=1).astype(np.int16)
COMBO_ODD = np.sum(ALL_COMBOS % 2, axis=1).astype(np.int8)
COMBO_PRIME = np.isin(ALL_COMBOS, np.fromiter(PRIMES, dtype=np.int16)).sum(axis=1).astype(np.int8)
COMBO_SPAN = (ALL_COMBOS[:, -1] - ALL_COMBOS[:, 0]).astype(np.int8)

def _zone_counts_arr():
    low = np.sum(ALL_COMBOS <= 9, axis=1)
    mid = np.sum((ALL_COMBOS >= 10) & (ALL_COMBOS <= 19), axis=1)
    high = DRAW_SIZE - low - mid
    return np.column_stack([low, mid, high]).astype(np.int8)
COMBO_ZONES = _zone_counts_arr()

COMBO_CONSEC = np.sum(np.diff(ALL_COMBOS, axis=1) == 1, axis=1).astype(np.int8)
PARENT4_COMBOS = np.array(list(itertools.combinations(NUMBERS, DRAW_SIZE - 1)), dtype=np.int16)
PARENT4_TO_INDEX = {tuple(map(int, c)): i for i, c in enumerate(PARENT4_COMBOS)}
_PARENT4_BASE = np.array([29**3, 29**2, 29, 1], dtype=np.int64)
_PARENT4_KEYS = (PARENT4_COMBOS.astype(np.int64) * _PARENT4_BASE).sum(axis=1)
_PARENT4_SUBSETS = np.stack([np.delete(ALL_COMBOS, j, axis=1) for j in range(DRAW_SIZE)], axis=1)
_PARENT4_SUBSET_KEYS = (_PARENT4_SUBSETS.astype(np.int64) * _PARENT4_BASE[None, None, :]).sum(axis=2)
COMBO_PARENT4_INDEX = np.searchsorted(_PARENT4_KEYS, _PARENT4_SUBSET_KEYS).astype(np.int32)
del _PARENT4_SUBSETS, _PARENT4_SUBSET_KEYS
for _const_arr in (ALL_COMBOS, COMBO_MASK, COMBO_SUM, COMBO_ODD, COMBO_PRIME, COMBO_SPAN, COMBO_ZONES, COMBO_CONSEC, PARENT4_COMBOS, COMBO_PARENT4_INDEX):
    _const_arr.setflags(write=False)

@dataclass
class AuditResult:
    status: str
    rows: int
    min_concurso: int
    max_concurso: int
    target: int
    expected_last: int
    duplicates: int
    invalid_numbers: int
    repeated_inside_draw: int
    missing_count: int
    missing_sample: List[int]
    sha256: str
    messages: List[str]

@dataclass
class ValidationSummary:
    trials: int
    lines: int
    exact5: int
    ge4: int
    ge3: int
    avg_best: float
    avg_exact_rank: float
    median_exact_rank: float
    p_exact_in_topk: float
    expected_random_exact5: float
    exact5_lift: float
    rank_lift_vs_random_pct: float

@dataclass
class ModelContext:
    last_concurso: int
    last_combo: Tuple[int, ...]
    next_weekday: Optional[int]
    next_slot: Optional[str]
    history_rows: int

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

def combo_key(x: Sequence[int]) -> Tuple[int, ...]:
    return tuple(sorted((int(v) for v in x)))

def combo_str(x: Sequence[int]) -> str:
    return '-'.join((f'{int(v):02d}' for v in sorted(x)))

def safe_z(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=float)
    if v.size == 0:
        return v
    m = float(np.nanmean(v))
    s = float(np.nanstd(v))
    if not np.isfinite(s) or s < 1e-12:
        return np.zeros_like(v)
    z = np.nan_to_num((v - m) / s)
    return np.clip(z, -6.0, 6.0)

def expected_exact_random(trials: int, lines: int) -> float:
    return trials * lines / UNIVERSE_SIZE

def rank_lift(avg_rank: float) -> float:
    random_mean = (UNIVERSE_SIZE + 1) / 2.0
    return (random_mean - avg_rank) / random_mean * 100.0

def infer_slot(df: pd.DataFrame) -> pd.Series:
    if 'FECHA' not in df.columns:
        return pd.Series(['UNKNOWN'] * len(df), index=df.index)
    slots = pd.Series(index=df.index, dtype='object')
    for _, g in df.groupby(df['FECHA'].dt.date, sort=False):
        idxs = list(g.sort_values('CONCURSO').index)
        if len(idxs) == 1:
            slots.loc[idxs[0]] = 'SINGLE'
        else:
            for pos, idx in enumerate(idxs):
                if pos == 0:
                    slots.loc[idx] = '3PM'
                elif pos == len(idxs) - 1:
                    slots.loc[idx] = '9PM'
                else:
                    slots.loc[idx] = f'MID{pos}'
    return slots.fillna('UNKNOWN')

def read_history(path: Path) -> pd.DataFrame:
    encodings = ['utf-8-sig', 'utf-8', 'cp1252', 'latin-1']
    last_err = None
    for enc in encodings:
        try:
            df = pd.read_csv(path, encoding=enc)
            break
        except Exception as e:
            last_err = e
    else:
        raise RuntimeError(f'No pude leer CSV: {last_err}')
    df.columns = [str(c).strip().upper() for c in df.columns]
    for c in REQ_COLS:
        if c not in df.columns:
            raise ValueError(f'Falta columna obligatoria: {c}')
    x = df.copy()
    x['CONCURSO'] = pd.to_numeric(x['CONCURSO'], errors='coerce')
    for c in R_COLS:
        x[c] = pd.to_numeric(x[c], errors='coerce')
    x = x.dropna(subset=REQ_COLS).copy()
    x['CONCURSO'] = x['CONCURSO'].astype(int)
    for c in R_COLS:
        x[c] = x[c].astype(int)
    if 'FECHA' in x.columns:
        x['FECHA'] = pd.to_datetime(x['FECHA'], errors='coerce', dayfirst=True, format='mixed')
    x = x.sort_values('CONCURSO').reset_index(drop=True)
    x['COMBO'] = [combo_key(row) for row in x[R_COLS].to_numpy()]
    if 'FECHA' in x.columns:
        x['WEEKDAY'] = x['FECHA'].dt.weekday
        x['SLOT'] = infer_slot(x)
    else:
        x['WEEKDAY'] = -1
        x['SLOT'] = 'UNKNOWN'
    return x

def audit_history(path: Path, df: pd.DataFrame, target: Optional[int], expected_last: Optional[int]) -> AuditResult:
    messages = []
    duplicates = int(df['CONCURSO'].duplicated().sum())
    invalid = 0
    repeated = 0
    for row in df[R_COLS].to_numpy(dtype=int):
        if np.any((row < 1) | (row > 28)):
            invalid += 1
        if len(set(map(int, row))) != DRAW_SIZE:
            repeated += 1
    mn = int(df['CONCURSO'].min())
    mx = int(df['CONCURSO'].max())
    full = set(range(mn, mx + 1))
    missing = sorted(full.difference(set(df['CONCURSO'].astype(int).tolist())))
    if target is None:
        target = mx + 1
    if expected_last is None:
        expected_last = target - 1
    status = 'PASS'
    if duplicates:
        status = 'FAIL'
        messages.append(f'Hay {duplicates} concursos duplicados.')
    if invalid:
        status = 'FAIL'
        messages.append(f'Hay {invalid} filas con números fuera de 1..28.')
    if repeated:
        status = 'FAIL'
        messages.append(f'Hay {repeated} filas con números repetidos dentro del sorteo.')
    if missing:
        status = 'FAIL'
        messages.append(f'Hay {len(missing)} concursos faltantes dentro del rango; las transiciones quedarían desalineadas.')
    if mx != expected_last:
        status = 'FAIL'
        messages.append(f'Último concurso {mx}; se esperaba {expected_last}.')
    if target <= mx:
        status = 'FAIL'
        messages.append(f'Target {target} no es futuro respecto a último concurso {mx}.')
    return AuditResult(status=status, rows=len(df), min_concurso=mn, max_concurso=mx, target=int(target), expected_last=int(expected_last), duplicates=duplicates, invalid_numbers=invalid, repeated_inside_draw=repeated, missing_count=len(missing), missing_sample=missing[:20], sha256=sha256_file(path), messages=messages)

def history_incidence(draws: np.ndarray) -> np.ndarray:
    mat = np.zeros((len(draws), N_NUMBERS), dtype=np.uint8)
    for i, row in enumerate(draws):
        mat[i, row - 1] = 1
    return mat

def ewma_number_scores(mat: np.ndarray, half_life: float) -> np.ndarray:
    if len(mat) == 0:
        return np.zeros(N_NUMBERS)
    ages = np.arange(len(mat) - 1, -1, -1, dtype=float)
    w = np.power(0.5, ages / max(half_life, 1e-09))
    return (mat * w[:, None]).sum(axis=0) / max(w.sum(), 1e-12)

def gap_scores(mat: np.ndarray) -> np.ndarray:
    gaps = np.full(N_NUMBERS, len(mat) + 1, dtype=float)
    for j in range(N_NUMBERS):
        idx = np.where(mat[:, j] == 1)[0]
        if len(idx):
            gaps[j] = len(mat) - 1 - idx[-1]
    return gaps

def transition_number_score(draws: np.ndarray, window: int=1024, shrink: float=30.0) -> np.ndarray:
    if len(draws) < 3:
        return np.full(N_NUMBERS, DRAW_SIZE / N_NUMBERS, dtype=float)
    current = set(map(int, draws[-1]))
    start = max(0, len(draws) - 1 - window)
    den = np.zeros(N_NUMBERS, dtype=float)
    pair = np.zeros((N_NUMBERS, N_NUMBERS), dtype=float)
    for i in range(start, len(draws) - 1):
        prev = draws[i]
        nxt = draws[i + 1]
        for a in prev:
            den[a - 1] += 1
            for b in nxt:
                pair[a - 1, b - 1] += 1
    base = DRAW_SIZE / N_NUMBERS
    cond = (pair + shrink * base) / (den[:, None] + shrink)
    idx = np.array([n - 1 for n in current], dtype=int)
    return cond[idx].mean(axis=0)

def knn_transition_score(draws: np.ndarray, hist_w: int=2048, k: int=60, tau: float=3.0) -> np.ndarray:
    if len(draws) < 10:
        return np.full(N_NUMBERS, DRAW_SIZE / N_NUMBERS, dtype=float)
    cur = np.sort(draws[-1])
    cur_set = set(map(int, cur))
    start = max(0, len(draws) - 1 - hist_w)
    sims = []
    for i in range(start, len(draws) - 1):
        prev = np.sort(draws[i])
        overlap = len(set(map(int, prev)) & cur_set)
        shape = np.mean(np.abs(prev - cur))
        dist = shape - 1.5 * overlap
        sims.append((dist, i))
    sims.sort(key=lambda x: x[0])
    sims = sims[:min(k, len(sims))]
    if not sims:
        return np.full(N_NUMBERS, DRAW_SIZE / N_NUMBERS, dtype=float)
    d0 = sims[0][0]
    score = np.zeros(N_NUMBERS, dtype=float)
    denom = 0.0
    for d, i in sims:
        w = math.exp(-(d - d0) / tau)
        score[draws[i + 1] - 1] += w
        denom += w
    base = DRAW_SIZE / N_NUMBERS
    return (score + 30 * base) / (denom + 30)

def pair_matrix(draws: np.ndarray, window: int=500) -> np.ndarray:
    out = np.zeros((N_NUMBERS, N_NUMBERS), dtype=float)
    sub = draws[-min(window, len(draws)):]
    for d in sub:
        for a, b in itertools.combinations(map(int, d), 2):
            out[a - 1, b - 1] += 1
            out[b - 1, a - 1] += 1
    if len(sub):
        out /= len(sub)
    return out

def overlap_dist(draws: np.ndarray, window: int=500) -> np.ndarray:
    if len(draws) < 2:
        return np.ones(DRAW_SIZE + 1) / (DRAW_SIZE + 1)
    vals = []
    start = max(1, len(draws) - window)
    for i in range(start, len(draws)):
        vals.append(len(set(map(int, draws[i])) & set(map(int, draws[i - 1]))))
    cnt = np.bincount(vals, minlength=DRAW_SIZE + 1).astype(float) + 1.0
    return cnt / cnt.sum()

def exact_lag_score(draws: np.ndarray, max_lag: int=1024) -> Dict[Tuple[int, ...], float]:
    """
    Da más peso a combinaciones que aparecieron en lags históricamente fértiles.
    No se usa como señal fuerte; es una feature.
    """
    n = len(draws)
    cur = combo_key(draws[-1])
    out = defaultdict(float)
    start = max(0, n - max_lag)
    recent = [combo_key(x) for x in draws[start:]]
    positions = defaultdict(list)
    for i, c in enumerate(recent):
        positions[c].append(i)
    if cur in positions:
        for pos in positions[cur]:
            if pos + 1 < len(recent):
                out[recent[pos + 1]] += 1.0
    curset = set(cur)
    for i in range(len(recent) - 1):
        if len(curset & set(recent[i])) >= 4:
            out[recent[i + 1]] += 0.35
    return out

def parent4_fertility(draws: np.ndarray, window: int=3000, half_life: float=300.0) -> Tuple[np.ndarray, np.ndarray]:
    """Dense causal parent4/dead→born statistics.

    Returns a dense vector indexed by ``PARENT4_TO_INDEX`` plus the normalized
    dead→born swap matrix. The historical loop is at most ``window`` rows; the
    former 98,280×5 Python lookup loop is eliminated downstream.
    """
    start = max(1, len(draws) - window)
    parent_score = np.zeros(len(PARENT4_COMBOS), dtype=np.float64)
    swap = np.zeros((N_NUMBERS, N_NUMBERS), dtype=np.float64)
    decay_scale = max(10.0, float(half_life)) / math.log(2.0)
    for i in range(start, len(draws)):
        prev = set(map(int, draws[i - 1]))
        cur = set(map(int, draws[i]))
        common = prev & cur
        age = max(1, len(draws) - i)
        weight = math.exp(-float(age) / decay_scale)
        if len(common) == DRAW_SIZE - 1:
            parent = tuple(sorted(common))
            pi = PARENT4_TO_INDEX.get(parent)
            if pi is not None:
                parent_score[pi] += weight
            dead = list(prev - cur)
            born = list(cur - prev)
            if dead and born:
                swap[dead[0] - 1, born[0] - 1] += weight
    row_sum = swap.sum(axis=1, keepdims=True)
    np.divide(swap, np.maximum(row_sum, 1e-12), out=swap, where=row_sum > 0)
    return (parent_score, swap)
FEATURE_NAMES = ['num_freq10', 'num_freq50', 'num_freq200', 'num_ewma12', 'num_ewma40', 'num_gap_small', 'num_transition', 'num_knn_transition', 'pair_affinity', 'carry_prob', 'carry_count', 'sum_shape', 'parity_shape', 'zone_shape', 'span_shape', 'consec_shape', 'prime_shape', 'init_pair_prob', 'final_pair_prob', 'anchor_span_shape', 'parent4_score', 'swap_score', 'exact_lag_score', 'weekday_heat', 'slot_heat']
HEURISTIC_FEATURE_WEIGHTS = np.array([0.06, 0.06, 0.04, 0.06, 0.04, 0.03, 0.12, 0.05, 0.08, 0.02, 0.02, 0.03, 0.02, 0.02, 0.02, 0.02, 0.02, 0.025, 0.025, 0.02, 0.08, 0.07, 0.05, 0.03, 0.03], dtype=np.float32)
ENSEMBLE_FALLBACK_FEATURE_WEIGHTS = np.array([0.08, 0.08, 0.05, 0.08, 0.05, 0.04, 0.14, 0.06, 0.1, 0.03, 0.02, 0.03, 0.02, 0.02, 0.02, 0.02, 0.02, 0.025, 0.025, 0.02, 0.08, 0.07, 0.05, 0.03, 0.03], dtype=np.float32)
ENSEMBLE_MODEL_WEIGHTS = MappingProxyType({'xgb_gpu': 0.50, 'et': 0.24, 'rf': 0.16, 'lr': 0.10})
RESIDUAL_RANK_WEIGHTS = MappingProxyType({'number_markov': 0.52, 'ltr_adv_exact5': 0.16, 'ltr_exact5_hard': 0.11, 'ltr_exact5_ultra': 0.07, 'ltr_ndcg_exact5': 0.06, 'number_knn': 0.05, 'affinity': 0.03})
HEURISTIC_FEATURE_WEIGHTS.setflags(write=False)
ENSEMBLE_FALLBACK_FEATURE_WEIGHTS.setflags(write=False)

def pair_extremes_tensor(draws: np.ndarray, window: int=1500, alpha: float=0.75) -> Tuple[Dict[Tuple[int, int], float], Dict[Tuple[int, int], float]]:
    """
    Densidad causal suavizada de los dos números inferiores y dos superiores.
    Usa únicamente sorteos previos. alpha aplica Laplace smoothing para evitar
    ceros rígidos en pares nunca observados.
    """
    init_pairs = defaultdict(float)
    final_pairs = defaultdict(float)
    sub = np.asarray(draws[-min(window, len(draws)):], dtype=np.int16)
    for d in sub:
        sd = np.sort(d)
        init_pairs[int(sd[0]), int(sd[1])] += 1.0
        final_pairs[int(sd[3]), int(sd[4])] += 1.0
    pair_space = math.comb(N_NUMBERS, 2)
    den = max(1.0, float(len(sub)) + alpha * pair_space)
    for k in list(init_pairs):
        init_pairs[k] = (init_pairs[k] + alpha) / den
    for k in list(final_pairs):
        final_pairs[k] = (final_pairs[k] + alpha) / den
    unseen = alpha / den
    init_pairs['__UNSEEN__', '__UNSEEN__'] = unseen
    final_pairs['__UNSEEN__', '__UNSEEN__'] = unseen
    return (init_pairs, final_pairs)

def anchor_distance_score(draws: np.ndarray) -> np.ndarray:
    """
    Geometría de anclas internas: distancia entre el 2º menor y el 2º mayor.
    Para una combinación ordenada c equivale a c[3] - c[1].
    """
    if len(draws) == 0:
        return np.empty(0, dtype=float)
    sd = np.sort(np.asarray(draws, dtype=np.int16), axis=1)
    return (sd[:, 3] - sd[:, 1]).astype(float)

def structural_profile_score(values: np.ndarray, hist_values: np.ndarray) -> np.ndarray:
    if len(hist_values) < 10:
        return np.zeros_like(values, dtype=float)
    mu = float(np.mean(hist_values))
    sd = float(np.std(hist_values))
    if sd < 1e-09:
        return np.zeros_like(values, dtype=float)
    z = np.abs((values - mu) / sd)
    return np.exp(-0.5 * z * z)

def build_universe_features(hist_df: pd.DataFrame, candidate_mask: Optional[np.ndarray]=None) -> Tuple[np.ndarray, List[str], ModelContext]:
    draws = hist_df[R_COLS].to_numpy(dtype=np.int16)
    mat = history_incidence(draws)
    last = tuple(map(int, draws[-1]))
    last_set = set(last)
    f10 = mat[-min(10, len(mat)):].mean(axis=0)
    f50 = mat[-min(50, len(mat)):].mean(axis=0)
    f200 = mat[-min(200, len(mat)):].mean(axis=0)
    ew12 = ewma_number_scores(mat, 12)
    ew40 = ewma_number_scores(mat, 40)
    gap = gap_scores(mat)
    gap_small = np.exp(-gap / 10.0)
    trans = transition_number_score(draws, 1024)
    knn = knn_transition_score(draws, 2048, 60, 3.0)
    pm = pair_matrix(draws, 500)
    ovdist = overlap_dist(draws, 500)
    m = COMBO_MASK if candidate_mask is None else COMBO_MASK[candidate_mask]
    combos = ALL_COMBOS if candidate_mask is None else ALL_COMBOS[candidate_mask]
    csum = COMBO_SUM if candidate_mask is None else COMBO_SUM[candidate_mask]
    codd = COMBO_ODD if candidate_mask is None else COMBO_ODD[candidate_mask]
    cprime = COMBO_PRIME if candidate_mask is None else COMBO_PRIME[candidate_mask]
    cspan = COMBO_SPAN if candidate_mask is None else COMBO_SPAN[candidate_mask]
    czones = COMBO_ZONES if candidate_mask is None else COMBO_ZONES[candidate_mask]
    ccon = COMBO_CONSEC if candidate_mask is None else COMBO_CONSEC[candidate_mask]

    def agg_num(v):
        return m @ np.asarray(v, dtype=float) / DRAW_SIZE
    feat = []
    feat.append(agg_num(f10))
    feat.append(agg_num(f50))
    feat.append(agg_num(f200))
    feat.append(agg_num(ew12))
    feat.append(agg_num(ew40))
    feat.append(agg_num(gap_small))
    feat.append(agg_num(trans))
    feat.append(agg_num(knn))
    pa = np.zeros(len(combos), dtype=float)
    for pos in range(DRAW_SIZE):
        a = combos[:, pos] - 1
        for pos2 in range(pos + 1, DRAW_SIZE):
            b = combos[:, pos2] - 1
            pa += pm[a, b]
    pa /= math.comb(DRAW_SIZE, 2)
    feat.append(pa)
    carry_count = np.sum(np.isin(combos, np.array(last, dtype=int)), axis=1)
    carry_prob = np.array([ovdist[min(int(x), DRAW_SIZE)] for x in carry_count], dtype=float)
    feat.append(carry_prob)
    feat.append(carry_count.astype(float) / DRAW_SIZE)
    hist_sums = draws.sum(axis=1)
    hist_odds = np.sum(draws % 2, axis=1)
    hist_span = draws.max(axis=1) - draws.min(axis=1)
    hist_prime = np.array([sum((int(x) in PRIMES for x in d)) for d in draws])
    hist_zone = np.column_stack([np.sum(draws <= 9, axis=1), np.sum((draws >= 10) & (draws <= 19), axis=1), np.sum(draws >= 20, axis=1)])
    feat.append(structural_profile_score(csum, hist_sums))
    feat.append(structural_profile_score(codd, hist_odds))
    zone_mu = hist_zone.mean(axis=0)
    zone_sd = np.maximum(hist_zone.std(axis=0), 0.75)
    zone_z = np.sqrt(np.sum(((czones - zone_mu) / zone_sd) ** 2, axis=1))
    feat.append(np.exp(-0.5 * zone_z * zone_z))
    feat.append(structural_profile_score(cspan, hist_span))
    hist_con = np.array([sum((1 for a, b in zip(sorted(d)[:-1], sorted(d)[1:]) if b == a + 1)) for d in draws])
    feat.append(structural_profile_score(ccon, hist_con))
    feat.append(structural_profile_score(cprime, hist_prime))
    init_tensor, final_tensor = pair_extremes_tensor(draws)
    unseen_init = float(init_tensor.get(('__UNSEEN__', '__UNSEEN__'), 0.0))
    unseen_final = float(final_tensor.get(('__UNSEEN__', '__UNSEEN__'), 0.0))
    init_score = np.fromiter((init_tensor.get((int(co[0]), int(co[1])), unseen_init) for co in combos), dtype=float, count=len(combos))
    final_score = np.fromiter((final_tensor.get((int(co[3]), int(co[4])), unseen_final) for co in combos), dtype=float, count=len(combos))
    hist_anchor_span = anchor_distance_score(draws)
    anchor_span = (combos[:, 3] - combos[:, 1]).astype(float)
    feat.append(init_score)
    feat.append(final_score)
    feat.append(structural_profile_score(anchor_span, hist_anchor_span))
    p4_dense, swap = parent4_fertility(draws, 3000)
    pidx = COMBO_PARENT4_INDEX if candidate_mask is None else COMBO_PARENT4_INDEX[candidate_mask]
    parent_score = p4_dense[pidx].sum(axis=1)
    present = m.astype(bool, copy=False)
    last_mask = np.zeros(N_NUMBERS, dtype=bool)
    last_mask[np.asarray(last, dtype=int) - 1] = True
    dead_mask = ~present & last_mask[None, :]
    born_mask = present & ~last_mask[None, :]
    swap_sum = np.einsum('ni,ij,nj->n', dead_mask.astype(np.float64), swap, born_mask.astype(np.float64), optimize=True)
    swap_den = dead_mask.sum(axis=1).astype(np.float64) * born_mask.sum(axis=1).astype(np.float64)
    swap_score = np.divide(swap_sum, swap_den, out=np.zeros_like(swap_sum), where=swap_den > 0)
    feat.append(parent_score)
    feat.append(swap_score)
    lagmap = exact_lag_score(draws, 1024)
    lag_dense = np.zeros(UNIVERSE_SIZE, dtype=np.float64)
    for co, val in lagmap.items():
        ci = COMBO_TO_INDEX.get(tuple(map(int, co)))
        if ci is not None:
            lag_dense[ci] = float(val)
    elag = lag_dense if candidate_mask is None else lag_dense[np.asarray(candidate_mask, dtype=np.int64)]
    feat.append(elag)
    weekday_heat = np.zeros(N_NUMBERS, dtype=float)
    slot_heat = np.zeros(N_NUMBERS, dtype=float)
    next_weekday = None
    next_slot = None
    if 'FECHA' in hist_df.columns and hist_df['FECHA'].notna().any():
        last_row = hist_df.iloc[-1]
        if pd.isna(last_row.get('FECHA')):
            last_row = hist_df.loc[hist_df['FECHA'].notna()].iloc[-1]
        if str(last_row.get('SLOT', '')) == '3PM':
            next_weekday = int(last_row['WEEKDAY'])
            next_slot = '9PM'
        else:
            next_date = last_row['FECHA'] + pd.Timedelta(days=1)
            next_weekday = int(next_date.weekday())
            next_slot = '3PM'
        wd = hist_df[hist_df['WEEKDAY'] == next_weekday]
        if len(wd):
            wm = history_incidence(wd[R_COLS].to_numpy(dtype=np.int16))
            weekday_heat = wm.mean(axis=0)
        sl = hist_df[hist_df['SLOT'] == next_slot]
        if len(sl):
            sm = history_incidence(sl[R_COLS].to_numpy(dtype=np.int16))
            slot_heat = sm.mean(axis=0)
    feat.append(agg_num(weekday_heat))
    feat.append(agg_num(slot_heat))
    X = np.column_stack(feat).astype(np.float32)
    ctx = ModelContext(last_concurso=int(hist_df['CONCURSO'].iloc[-1]), last_combo=tuple(sorted(map(int, last))), next_weekday=next_weekday, next_slot=next_slot, history_rows=len(hist_df))
    return (X, FEATURE_NAMES[:], ctx)

def persistence_signature(audit, args, train_start: int, train_end: int) -> Dict[str, object]:
    """Firma estricta: sólo reutiliza entrenamiento si datos y parámetros son idénticos."""
    return {'engine': 'V235', 'history_sha256': str(audit.sha256), 'target': int(audit.target), 'history_last': int(audit.max_concurso), 'history_rows': int(audit.rows), 'train_start': int(train_start), 'train_end': int(train_end), 'train_examples': int(args.train_examples), 'negatives': int(args.negatives), 'hard_negative_ratio': float(args.hard_negative_ratio), 'seed': int(args.seed), 'xgb_estimators': int(args.xgb_estimators), 'gpu_device': str(args.gpu_device), 'feature_names': list(FEATURE_NAMES), 'xgboost_version': getattr(xgb, '__version__', None) if XGBOOST_OK else None}

def _atomic_joblib_dump(obj, path: Path, compress: int=3) -> None:
    if not JOBLIB_OK:
        raise RuntimeError('joblib no está disponible')
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    joblib.dump(obj, tmp, compress=compress)
    os.replace(tmp, path)

def probe_xgboost_gpu(seed: int=DEFAULT_SEED, *, enabled: bool=True, device: str='cuda') -> Dict[str, object]:
    """Prueba real de entrenamiento CUDA con configuración explícita."""
    status = {'requested': bool(enabled), 'xgboost_installed': bool(XGBOOST_OK), 'available': False, 'device': str(device), 'xgboost_version': getattr(xgb, '__version__', None) if XGBOOST_OK else None, 'reason': 'GPU disabled'}
    if not enabled:
        return status
    if not XGBOOST_OK:
        status['reason'] = 'xgboost is not installed'
        return status
    try:
        X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]] * 16, dtype=np.float32)
        y = np.array([0, 0, 0, 1] * 16, dtype=np.uint8)
        test = XGBClassifier(n_estimators=4, max_depth=2, learning_rate=0.2, tree_method='hist', device=str(device), objective='binary:logistic', eval_metric='logloss', random_state=seed, n_jobs=1, verbosity=0)
        test.fit(X, y)
        _ = test.predict_proba(X)
        status['available'] = True
        status['reason'] = 'CUDA training/prediction probe passed'
    except Exception as e:
        status['reason'] = f'CUDA probe failed: {type(e).__name__}: {e}'
    return status

def hard_negative_indices(true_combo: Tuple[int, ...], negatives_per_positive: int, rng: np.random.Generator, hard_ratio: float=0.8) -> np.ndarray:
    """
    Negativos difíciles para aprender EXACT-5, no sólo separar ganadora vs azar lejano.

    Mezcla por defecto:
      - ~45% comparten 4/5 con el positivo (máximo 115 combinaciones posibles)
      - ~35% comparten 3/5
      - resto aleatorio del universo

    Usar el resultado del target como etiqueta para construir negativos es aprendizaje
    supervisado estándar. Las FEATURES siguen calculándose únicamente con historia
    anterior al target, por lo que no introduce fuga hacia targets futuros.
    """
    n = max(1, int(negatives_per_positive))
    hard_ratio = float(np.clip(hard_ratio, 0.0, 1.0))
    true = tuple(sorted(map(int, true_combo)))
    tset = set(true)
    outside = [x for x in NUMBERS if x not in tset]
    n4 = min(115, int(round(n * hard_ratio * 0.56)))
    n3 = int(round(n * hard_ratio)) - n4
    nrand = n - n4 - n3
    pool4 = []
    for keep in itertools.combinations(true, 4):
        for x in outside:
            c = tuple(sorted((*keep, x)))
            pool4.append(COMBO_TO_INDEX[c])
    pool4 = np.array(sorted(set(pool4)), dtype=np.int32)
    pool3 = []
    for keep in itertools.combinations(true, 3):
        for add in itertools.combinations(outside, 2):
            c = tuple(sorted((*keep, *add)))
            pool3.append(COMBO_TO_INDEX[c])
    pool3 = np.array(sorted(set(pool3)), dtype=np.int32)
    chosen = []
    if n4 > 0 and len(pool4):
        chosen.extend(rng.choice(pool4, size=min(n4, len(pool4)), replace=False).tolist())
    if n3 > 0 and len(pool3):
        chosen.extend(rng.choice(pool3, size=min(n3, len(pool3)), replace=False).tolist())
    true_i = COMBO_TO_INDEX[true]
    used = set(chosen)
    used.add(true_i)
    need = n - len(chosen)
    while need > 0:
        batch = rng.integers(0, UNIVERSE_SIZE, size=max(need * 3, 32))
        for j in batch:
            j = int(j)
            if j not in used:
                chosen.append(j)
                used.add(j)
                need -= 1
                if need == 0:
                    break
    rng.shuffle(chosen)
    return np.asarray(chosen[:n], dtype=np.int32)

def _temporal_binary_splits_v240(n_rows: int, groupsize_hint: int=121, n_splits: int=3):
    """
    Cortes contiguos/temporales. Nunca mezcla filas futuras dentro del fold de entrenamiento.
    groupsize_hint aproxima 1 positivo + negativos por target.
    """
    if n_rows < max(600, groupsize_hint * 12):
        return []
    n_groups = max(6, n_rows // max(2, groupsize_hint))
    fold_groups = max(2, n_groups // (n_splits + 2))
    out = []
    for k in range(n_splits):
        train_groups = n_groups - (n_splits - k) * fold_groups
        val_start_g = max(2, train_groups)
        val_end_g = min(n_groups, val_start_g + fold_groups)
        tr_end = min(n_rows, val_start_g * groupsize_hint)
        va_end = min(n_rows, val_end_g * groupsize_hint)
        if tr_end >= groupsize_hint * 4 and va_end > tr_end:
            out.append((np.arange(0, tr_end), np.arange(tr_end, va_end)))
    return out

def optimize_xgb_gpu_temporal_v240(X_train: np.ndarray, y_train: np.ndarray, n_trials: int=0, seed: int=DEFAULT_SEED, negatives_per_positive: int=120, runtime: Optional[ModelRuntime]=None) -> Optional[Dict[str, object]]:
    """
    Optuna opcional con validación temporal contigua.
    No usa StratifiedKFold aleatorio porque rompería causalidad entre targets.
    Se ejecuta sólo cuando n_trials > 0 y Optuna está instalado.
    """
    runtime = runtime or default_model_runtime()
    if n_trials <= 0 or not OPTUNA_OK or (not XGBOOST_OK) or (len(X_train) < 1000):
        return None
    groupsize = max(2, int(negatives_per_positive) + 1)
    splits = _temporal_binary_splits_v240(len(X_train), groupsize, 3)
    if not splits:
        return None
    pos = max(1, int(np.sum(y_train == 1)))
    neg = max(1, int(np.sum(y_train == 0)))
    spw = float(neg / pos)

    def objective(trial):
        params = {'n_estimators': trial.suggest_int('n_estimators', 250, 800), 'max_depth': trial.suggest_int('max_depth', 4, 9), 'learning_rate': trial.suggest_float('learning_rate', 0.012, 0.12, log=True), 'subsample': trial.suggest_float('subsample', 0.65, 1.0), 'colsample_bytree': trial.suggest_float('colsample_bytree', 0.65, 1.0), 'gamma': trial.suggest_float('gamma', 0.0, 4.0), 'min_child_weight': trial.suggest_float('min_child_weight', 1.0, 10.0), 'reg_alpha': trial.suggest_float('reg_alpha', 0.0001, 0.5, log=True), 'reg_lambda': trial.suggest_float('reg_lambda', 0.5, 4.0, log=True), 'tree_method': 'hist', 'device': runtime.device, 'objective': 'binary:logistic', 'eval_metric': 'aucpr', 'scale_pos_weight': spw, 'random_state': seed, 'n_jobs': 1, 'verbosity': 0}
        vals = []
        for tr, va in splits:
            mdl = XGBClassifier(**params)
            mdl.fit(X_train[tr], y_train[tr], eval_set=[(X_train[va], y_train[va])], verbose=False)
            pred = mdl.predict_proba(X_train[va])[:, 1]
            vals.append(float(average_precision_score(y_train[va], pred)))
        return float(np.mean(vals))
    sampler = optuna.samplers.TPESampler(seed=seed)
    study = optuna.create_study(direction='maximize', sampler=sampler)
    progress(f'V240 Optuna temporal: {n_trials} trials | {len(splits)} folds causales')
    study.optimize(objective, n_trials=int(n_trials), show_progress_bar=False)
    best = dict(study.best_params)
    best.update({'tree_method': 'hist', 'device': runtime.device, 'objective': 'binary:logistic', 'eval_metric': 'aucpr', 'scale_pos_weight': spw, 'random_state': seed, 'n_jobs': 1, 'verbosity': 0})
    progress(f'V240 Optuna best AUC-PR temporal={study.best_value:.6f}')
    return best

def _append_mirage_rows_v240(X: np.ndarray, y: np.ndarray, mirage_bank: Optional[List[Dict[str, np.ndarray]]], max_rows: int=4000) -> Tuple[np.ndarray, np.ndarray]:
    """
    Añade falsos positivos históricos YA resueltos. Cada X fue calculado con el
    histórico disponible antes de su target, por lo que no existe fuga temporal.
    """
    if not mirage_bank:
        return (X, y)
    rows = []
    for rec in mirage_bank:
        xm = rec.get('X')
        if xm is not None and len(xm):
            rows.append(np.asarray(xm, dtype=np.float32))
    if not rows:
        return (X, y)
    M = np.vstack(rows)
    if len(M) > max_rows:
        M = M[-max_rows:]
    X2 = np.vstack([X, M])
    y2 = np.concatenate([y, np.zeros(len(M), dtype=np.uint8)])
    return (X2, y2)

def mine_mirages_v240(hist_df: pd.DataFrame, score: np.ndarray, realized_combo: Tuple[int, ...], top_k: int=100) -> Dict[str, np.ndarray]:
    """
    Después de resolver un target histórico, conserva sus Top-K falsos positivos
    y sus features pre-target para entrenamientos FUTUROS.
    """
    true_i = COMBO_TO_INDEX[tuple(sorted(map(int, realized_combo)))]
    k = min(max(1, int(top_k)), len(score) - 1)
    idx = np.argpartition(-score, k)[:k + 1]
    idx = idx[np.argsort(-score[idx])]
    idx = np.asarray([int(i) for i in idx if int(i) != true_i][:k], dtype=np.int32)
    X, _, _ = build_universe_features(hist_df, candidate_mask=idx)
    return {'indices': idx, 'X': X.astype(np.float32, copy=False)}

def train_ensemble(X: np.ndarray, y: np.ndarray, seed: int=DEFAULT_SEED, xgb_params: Optional[Dict[str, object]]=None, runtime: Optional[ModelRuntime]=None, estimators: Optional[int]=None):
    if not SKLEARN_OK or len(X) < 100 or len(np.unique(y)) < 2:
        return None
    runtime = runtime or default_model_runtime()
    n_estimators = max(50, int(estimators if estimators is not None else runtime.xgb_estimators))
    models = []
    if runtime.gpu_available and XGBOOST_OK:
        positives = max(1, int(np.sum(y == 1)))
        negatives = max(1, int(np.sum(y == 0)))
        scale_pos_weight = float(negatives / positives)
        base_xgb_params = dict(n_estimators=n_estimators, max_depth=8, learning_rate=0.035, min_child_weight=3.0, subsample=0.88, colsample_bytree=0.9, reg_alpha=0.05, reg_lambda=1.25, gamma=0.0, objective='binary:logistic', eval_metric='logloss', tree_method='hist', device=(runtime.gpu_device if runtime.gpu_available else 'cpu'), scale_pos_weight=scale_pos_weight, random_state=seed + 10, n_jobs=1, verbosity=0)
        if xgb_params:
            base_xgb_params.update(xgb_params)
        gpu_model = XGBClassifier(**base_xgb_params)
        try:
            progress(f'XGBoost GPU: entrenando {n_estimators} árboles en {runtime.gpu_device} con {len(X):,} filas')
            mt0 = time.time()
            gpu_model.fit(X, y)
            progress(f'XGBoost GPU: terminado en {time.time() - mt0:.1f}s')
            models.append(('xgb_gpu', gpu_model))
        except Exception as e:
            print(f'WARNING: XGBoost GPU training failed: {type(e).__name__}: {e}', file=sys.stderr)
            if runtime.gpu_required:
                raise RuntimeError('GPU was required but XGBoost CUDA training failed') from e
    et = ExtraTreesClassifier(n_estimators=220, max_depth=10, min_samples_leaf=3, class_weight='balanced', random_state=seed, n_jobs=-1)
    rf = RandomForestClassifier(n_estimators=180, max_depth=10, min_samples_leaf=3, class_weight='balanced_subsample', random_state=seed + 1, n_jobs=-1)
    lr = Pipeline([('scaler', StandardScaler()), ('lr', LogisticRegression(C=0.5, class_weight='balanced', max_iter=1000, random_state=seed + 3))])
    for name, mdl in [('et', et), ('rf', rf), ('lr', lr)]:
        try:
            progress(f'Modelo {name}: entrenando')
            mt0 = time.time()
            mdl.fit(X, y)
            progress(f'Modelo {name}: terminado en {time.time() - mt0:.1f}s')
            models.append((name, mdl))
        except Exception as e:
            print(f'WARNING: model {name} training failed: {type(e).__name__}: {e}', file=sys.stderr)
    return models if models else None

def ensemble_predict(models, X: np.ndarray) -> np.ndarray:
    if not models:
        weights = np.pad(ENSEMBLE_FALLBACK_FEATURE_WEIGHTS, (0, max(0, X.shape[1] - len(ENSEMBLE_FALLBACK_FEATURE_WEIGHTS))))[:X.shape[1]]
        return X @ weights
    preds = []
    w = []
    for name, mdl in models:
        try:
            p = mdl.predict_proba(X)[:, 1]
            preds.append(p)
            w.append(ENSEMBLE_MODEL_WEIGHTS.get(name, 0.20))
        except Exception as e:
            print(f'WARNING: model {name} prediction failed: {type(e).__name__}: {e}', file=sys.stderr)
    if not preds:
        return np.zeros(len(X))
    W = np.array(w, dtype=float)
    W /= W.sum()
    return np.column_stack(preds) @ W

def best_hit(portfolio: Sequence[Tuple[int, ...]], actual: Tuple[int, ...]) -> int:
    aset = set(actual)
    return max((len(aset & set(p)) for p in portfolio), default=0)

def exact_rank_from_scores(scores: np.ndarray, true_index: int) -> int:
    true_score = scores[true_index]
    return int(np.sum(scores >= true_score))
NUMBER_FEATURE_NAMES_V235 = ['freq10', 'freq50', 'freq200', 'ewma12', 'ewma40', 'gap_small', 'transition', 'knn_transition', 'pair_to_last']
V235_FUSION_WEIGHTS = {'binary': 0.3, 'pairwise_rank': 0.3, 'number': 0.18, 'affinity': 0.12, 'heuristic': 0.1}

def build_number_features_v235(hist_df: pd.DataFrame) -> np.ndarray:
    """Features causales por número (28 x 9), independientes del target futuro."""
    draws = hist_df[R_COLS].to_numpy(dtype=np.int16)
    mat = history_incidence(draws)
    f10 = mat[-min(10, len(mat)):].mean(axis=0)
    f50 = mat[-min(50, len(mat)):].mean(axis=0)
    f200 = mat[-min(200, len(mat)):].mean(axis=0)
    ew12 = ewma_number_scores(mat, 12)
    ew40 = ewma_number_scores(mat, 40)
    gap_small = np.exp(-gap_scores(mat) / 10.0)
    trans = transition_number_score(draws, 1024)
    knn = knn_transition_score(draws, 2048, 60, 3.0)
    pm = pair_matrix(draws, 500)
    last = draws[-1] - 1
    pair_to_last = pm[:, last].mean(axis=1) if len(last) else np.zeros(N_NUMBERS)
    return np.column_stack([f10, f50, f200, ew12, ew40, gap_small, trans, knn, pair_to_last]).astype(np.float32)

def combo_affinity_v235(hist_df: pd.DataFrame, candidate_mask: Optional[np.ndarray]=None) -> np.ndarray:
    """Afinidad causal explícita de pares + triples recientes para cada combinación."""
    draws = hist_df[R_COLS].to_numpy(dtype=np.int16)
    combos = ALL_COMBOS if candidate_mask is None else ALL_COMBOS[candidate_mask]
    pm = pair_matrix(draws, 1000)
    pair_sc = np.zeros(len(combos), dtype=np.float32)
    for a in range(DRAW_SIZE):
        ia = combos[:, a] - 1
        for b in range(a + 1, DRAW_SIZE):
            ib = combos[:, b] - 1
            pair_sc += pm[ia, ib].astype(np.float32)
    pair_sc /= float(math.comb(DRAW_SIZE, 2))
    tcount = Counter()
    sub = draws[-min(1500, len(draws)):]
    for d in sub:
        for tri in itertools.combinations(sorted(map(int, d)), 3):
            tcount[tri] += 1
    den = max(1.0, float(len(sub)))
    triple_sc = np.zeros(len(combos), dtype=np.float32)
    for i, co in enumerate(combos):
        triple_sc[i] = sum((tcount.get(tuple(map(int, tri)), 0) for tri in itertools.combinations(co, 3))) / (10.0 * den)
    return 0.58 * safe_z(pair_sc) + 0.42 * safe_z(triple_sc)

def build_master_cache_v235(df: pd.DataFrame, start_idx: int, end_idx: int, negatives_per_positive: int, seed: int, hard_ratio: float) -> Dict[int, Dict[str, np.ndarray]]:
    """
    Cache maestro causal por target.
    Cada entrada contiene combo-features, labels binarios, relevancia LTR,
    indices candidatos y dataset de 28 números. Una entrada nunca usa el target
    para calcular sus features: sólo df.iloc[:idx].
    """
    cache: Dict[int, Dict[str, np.ndarray]] = {}
    total = max(0, end_idx - start_idx)
    progress(f'V235 MASTER CACHE: {total} targets | negativos={negatives_per_positive} | hard={hard_ratio:.2f}')
    for pos, idx in enumerate(range(start_idx, end_idx), 1):
        if pos == 1 or pos == total or pos % max(1, _progress_every()) == 0:
            progress('Construyendo MASTER CACHE causal', done=pos, total=total)
        hist = df.iloc[:idx]
        true_combo = combo_key(df.iloc[idx][R_COLS].to_numpy(dtype=int))
        true_i = COMBO_TO_INDEX[true_combo]
        rng = np.random.default_rng(seed + idx * 1009)
        neg = hard_negative_indices(true_combo, negatives_per_positive, rng, hard_ratio)
        cand_idx = np.concatenate(([true_i], neg)).astype(np.int32)
        Xc, _, _ = build_universe_features(hist, candidate_mask=cand_idx)
        yb = np.zeros(len(cand_idx), dtype=np.uint8)
        yb[0] = 1
        true_set = set(true_combo)
        rel = np.array([len(true_set & set(map(int, ALL_COMBOS[j]))) for j in cand_idx], dtype=np.float32)
        Xn = build_number_features_v235(hist)
        yn = np.zeros(N_NUMBERS, dtype=np.uint8)
        yn[np.array(true_combo, dtype=int) - 1] = 1
        cache[idx] = {'Xc': Xc, 'yb': yb, 'rel': rel, 'cand_idx': cand_idx, 'Xn': Xn, 'yn': yn}
    return cache

def stack_master_combo_v235(cache, start_idx: int, end_idx: int):
    keys = [i for i in range(start_idx, end_idx) if i in cache]
    if not keys:
        return (np.empty((0, len(FEATURE_NAMES)), np.float32), np.empty(0, np.uint8), np.empty(0, np.float32), np.empty(0, np.int32), [])
    X = np.vstack([cache[i]['Xc'] for i in keys])
    y = np.concatenate([cache[i]['yb'] for i in keys])
    rel = np.concatenate([cache[i]['rel'] for i in keys])
    qid = np.concatenate([np.full(len(cache[i]['Xc']), k, dtype=np.int32) for k, i in enumerate(keys)])
    groups = [len(cache[i]['Xc']) for i in keys]
    return (X, y, rel, qid, groups)

def stack_master_number_v235(cache, start_idx: int, end_idx: int):
    keys = [i for i in range(start_idx, end_idx) if i in cache]
    if not keys:
        return (np.empty((0, len(NUMBER_FEATURE_NAMES_V235)), np.float32), np.empty(0, np.uint8))
    return (np.vstack([cache[i]['Xn'] for i in keys]), np.concatenate([cache[i]['yn'] for i in keys]))

def _exact5_relevance_v243(rel_overlap: np.ndarray) -> np.ndarray:
    """Relevancia NDCG graduada y muy orientada a exact-5."""
    r = np.asarray(rel_overlap, dtype=np.float32)
    out = np.zeros(len(r), dtype=np.float32)
    out[r >= 2] = 1.0
    out[r >= 3] = 2.0
    out[r >= 4] = 4.0
    out[r >= 5] = 7.0
    return out

def train_ndcg_exact5_ranker_v243(X, rel_overlap, qid, seed, estimators, topk=30, runtime: Optional[ModelRuntime]=None):
    runtime = runtime or default_model_runtime()
    if not XGBOOST_OK or len(X) < 100:
        return None
    qid = np.asarray(qid, dtype=np.int32)
    rel_overlap = np.asarray(rel_overlap, dtype=np.float32)
    if len(qid) != len(X):
        raise ValueError('V243 LTR: qid/X mismatch')
    if np.any(qid[1:] < qid[:-1]):
        order = np.argsort(qid, kind='stable')
        X = X[order]
        rel_overlap = rel_overlap[order]
        qid = qid[order]
    yrel = _exact5_relevance_v243(rel_overlap)
    mdl = XGBRanker(objective='rank:ndcg', eval_metric=f'ndcg@{max(10, int(topk))}', n_estimators=max(100, int(estimators)), max_depth=5, learning_rate=0.035, min_child_weight=3.0, subsample=0.86, colsample_bytree=0.88, reg_alpha=0.08, reg_lambda=1.5, gamma=0.0, tree_method='hist', device=(runtime.gpu_device if runtime.gpu_available else 'cpu'), lambdarank_pair_method='topk', lambdarank_num_pair_per_sample=max(16, int(topk)), random_state=int(seed), n_jobs=1, verbosity=0)
    progress(f"V264 NDCG seed={seed} | trees={mdl.get_params()['n_estimators']} | rows={len(X):,} | ndcg@{max(10, int(topk))}")
    t = time.time()
    mdl.fit(X, yrel, qid=qid)
    progress(f'V243 NDCG seed={seed} terminado en {time.time() - t:.1f}s')
    return mdl

def train_ndcg_ranker_ensemble_v243(X, rel_overlap, qid, seed, estimators, n_seeds=3, topk=30, runtime: Optional[ModelRuntime]=None):
    models = []
    for k in range(max(1, int(n_seeds))):
        m = train_ndcg_exact5_ranker_v243(X, rel_overlap, qid, seed + 243 + 1009 * k, estimators, topk, runtime=runtime)
        if m is not None:
            models.append(m)
    return models

def predict_ndcg_ranker_ensemble_v243(models, X):
    if not models:
        return np.zeros(len(X), dtype=float)
    acc = np.zeros(len(X), dtype=np.float64)
    used = 0
    den = math.log1p(max(2, len(X)))
    for m in models:
        try:
            raw = np.asarray(m.predict(X), dtype=float)
            order = np.argsort(-raw, kind='stable')
            ranks = np.empty(len(raw), dtype=np.int32)
            ranks[order] = np.arange(1, len(raw) + 1, dtype=np.int32)
            acc += 1.0 - np.log1p(ranks.astype(np.float64) - 1.0) / den
            used += 1
        except Exception as e:
            print(f'WARNING: V243 NDCG ensemble prediction failed: {type(e).__name__}: {e}', file=sys.stderr)
    return safe_z(acc / max(1, used))

def train_pairwise_ranker_v235(X: np.ndarray, rel: np.ndarray, qid: np.ndarray, seed: int, estimators: int, runtime: Optional[ModelRuntime]=None):
    runtime = runtime or default_model_runtime()
    if not XGBOOST_OK or len(X) < 100:
        return None
    mdl = XGBRanker(objective='rank:pairwise', n_estimators=max(80, int(estimators)), max_depth=7, learning_rate=0.035, min_child_weight=3.0, subsample=0.88, colsample_bytree=0.9, reg_alpha=0.05, reg_lambda=1.25, tree_method='hist', device=(runtime.gpu_device if runtime.gpu_available else 'cpu'), random_state=seed + 41, n_jobs=1, verbosity=0)
    progress(f"V264 XGBRanker: {mdl.get_params()['n_estimators']} árboles | {len(X):,} filas")
    t = time.time()
    mdl.fit(X, rel, qid=qid)
    progress(f'V264 XGBRanker terminado en {time.time() - t:.1f}s')
    return mdl

def train_number_model_v235(Xn: np.ndarray, yn: np.ndarray, seed: int, estimators: int, runtime: Optional[ModelRuntime]=None):
    runtime = runtime or default_model_runtime()
    if not (XGBOOST_OK and runtime.gpu_available) or len(Xn) < 200:
        return None
    pos = max(1, int((yn == 1).sum()))
    neg = max(1, int((yn == 0).sum()))
    mdl = XGBClassifier(n_estimators=max(80, min(int(estimators), 450)), max_depth=5, learning_rate=0.04, min_child_weight=3, subsample=0.9, colsample_bytree=0.95, reg_alpha=0.05, reg_lambda=1.2, objective='binary:logistic', eval_metric='logloss', tree_method='hist', device=(runtime.gpu_device if runtime.gpu_available else 'cpu'), scale_pos_weight=float(neg / pos), random_state=seed + 53, n_jobs=1, verbosity=0)
    progress(f"V235 number-model GPU: {mdl.get_params()['n_estimators']} árboles | {len(Xn):,} filas")
    mdl.fit(Xn, yn)
    return mdl

def score_full_universe_v235(hist_df: pd.DataFrame, bundle=None):
    X, _, ctx = build_universe_features(hist_df)
    Xh = np.column_stack([safe_z(X[:, i]) for i in range(X.shape[1])]).astype(np.float32)
    hw = HEURISTIC_FEATURE_WEIGHTS.copy()
    hw = np.pad(hw, (0, max(0, Xh.shape[1] - len(hw))))[:Xh.shape[1]]
    heur = safe_z(Xh @ hw)
    if not bundle:
        return (heur, ctx, {'heuristic': heur})
    binary = safe_z(ensemble_predict(bundle.get('binary_models'), X))
    ranker_m = bundle.get('pairwise_ranker')
    if ranker_m is not None:
        try:
            rank_sc = safe_z(np.asarray(ranker_m.predict(X), dtype=float))
        except Exception as e:
            log_exception('pairwise_ranker.predict', e)
            rank_sc = np.zeros(UNIVERSE_SIZE)
    else:
        rank_sc = np.zeros(UNIVERSE_SIZE)
    num_m = bundle.get('number_model')
    if num_m is not None:
        try:
            Xn = build_number_features_v235(hist_df)
            pn = np.asarray(num_m.predict_proba(Xn)[:, 1], dtype=float)
            num_sc = safe_z(np.mean(np.log(np.clip(pn[ALL_COMBOS - 1], 1e-06, 1.0)), axis=1))
        except Exception as e:
            log_exception('number_model.predict_proba', e)
            num_sc = np.zeros(UNIVERSE_SIZE)
    else:
        num_sc = np.zeros(UNIVERSE_SIZE)
    affinity = safe_z(combo_affinity_v235(hist_df))
    w = V235_FUSION_WEIGHTS
    score = w['binary'] * binary + w['pairwise_rank'] * rank_sc + w['number'] * num_sc + w['affinity'] * affinity + w['heuristic'] * heur
    parts = {'binary': binary, 'pairwise_rank': rank_sc, 'number': num_sc, 'affinity': affinity, 'heuristic': heur}
    return (score, ctx, parts)

def rank_full_universe_v235(hist_df: pd.DataFrame, bundle=None) -> pd.DataFrame:
    progress('V235 ranking: features + classifier + LTR + number-model + pair/triple affinity')
    scores, ctx, parts = score_full_universe_v235(hist_df, bundle)
    order = np.argsort(-scores)
    ranks = np.empty_like(order)
    ranks[order] = np.arange(1, UNIVERSE_SIZE + 1)
    df = pd.DataFrame({'rank': ranks, 'combo': [combo_str(c) for c in ALL_COMBOS], 'score': scores, 'score_binary': parts.get('binary'), 'score_pairwise': parts.get('pairwise_rank'), 'score_number': parts.get('number'), 'score_affinity': parts.get('affinity'), 'score_heuristic': parts.get('heuristic'), 'sum': COMBO_SUM, 'zone': [f'{a}-{b}-{c}' for a, b, c in COMBO_ZONES], 'overlap_last': np.sum(np.isin(ALL_COMBOS, np.array(ctx.last_combo)), axis=1)})
    return df.sort_values('rank').reset_index(drop=True)

def validation_summary_from_rows_v235(d: pd.DataFrame, lines: int) -> ValidationSummary:
    exact5 = int(d.exact5.sum())
    exp = expected_exact_random(len(d), lines)
    avg = float(d.exact_rank.mean())
    portfolio_exact_rate = float(d['exact5'].mean()) if 'exact5' in d.columns and len(d) else 0.0
    return ValidationSummary(trials=len(d), lines=lines, exact5=exact5, ge4=int(d.ge4.sum()), ge3=int(d.ge3.sum()), avg_best=float(d.best_hit.mean()), avg_exact_rank=avg, median_exact_rank=float(d.exact_rank.median()), p_exact_in_topk=portfolio_exact_rate, expected_random_exact5=exp, exact5_lift=float(exact5 / exp) if exp > 0 else 0.0, rank_lift_vs_random_pct=rank_lift(avg))
V236_STRATEGIES = {'binary': {'binary': 1.0}, 'pairwise': {'pairwise_rank': 1.0}, 'number': {'number': 1.0}, 'affinity': {'affinity': 1.0}, 'heuristic': {'heuristic': 1.0}, 'binary_heur': {'binary': 0.78, 'heuristic': 0.22}, 'binary_affinity': {'binary': 0.72, 'affinity': 0.18, 'heuristic': 0.1}, 'rank_binary': {'binary': 0.55, 'pairwise_rank': 0.35, 'heuristic': 0.1}, 'number_affinity': {'number': 0.58, 'affinity': 0.27, 'heuristic': 0.15}, 'v235_full': dict(V235_FUSION_WEIGHTS)}

def strategy_score_v236(parts: Dict[str, np.ndarray], strategy: str) -> np.ndarray:
    w = V236_STRATEGIES[strategy]
    out = np.zeros(UNIVERSE_SIZE, dtype=np.float64)
    for k, wt in w.items():
        arr = parts.get(k)
        if arr is not None:
            out += float(wt) * np.asarray(arr, dtype=float)
    return safe_z(out)

def train_bundle_v236(cache, start_idx: int, end_idx: int, seed: int, binary_estimators: int, ranker_estimators: int, runtime: Optional[ModelRuntime]=None):
    """Legacy specialist bundle with explicit runtime; no estimator globals are mutated."""
    runtime = runtime or default_model_runtime()
    X, y, rel, qid, _ = stack_master_combo_v235(cache, start_idx, end_idx)
    Xn, yn = stack_master_number_v235(cache, start_idx, end_idx)
    if len(X) == 0:
        return {'binary_models': None, 'pairwise_ranker': None, 'number_model': None}
    binary_runtime = ModelRuntime(runtime.gpu_enabled, runtime.gpu_required, runtime.gpu_device, dict(runtime.gpu_status), max(50, int(binary_estimators)))
    binary = train_ensemble(X, y, seed, runtime=binary_runtime, estimators=max(50, int(binary_estimators)))
    ranker = train_pairwise_ranker_v235(X, rel, qid, seed, ranker_estimators, runtime=runtime)
    number = train_number_model_v235(Xn, yn, seed, ranker_estimators, runtime=runtime)
    return {'binary_models': binary, 'pairwise_ranker': ranker, 'number_model': number}

def score_parts_v236(hist_df: pd.DataFrame, bundle=None):
    """Devuelve señales estandarizadas independientes para ablación."""
    _, ctx, parts = score_full_universe_v235(hist_df, bundle)
    for k in ['binary', 'pairwise_rank', 'number', 'affinity', 'heuristic']:
        if parts.get(k) is None:
            parts[k] = np.zeros(UNIVERSE_SIZE, dtype=float)
        else:
            parts[k] = safe_z(np.asarray(parts[k], dtype=float))
    return (ctx, parts)

def _strategy_metrics_v236(d: pd.DataFrame) -> Dict[str, float]:
    if d is None or len(d) == 0:
        return {'n': 0, 'avg_rank': float('nan'), 'median_rank': float('nan'), 'rank_lift': float('-inf'), 'top30': 0.0, 'top100': 0.0, 'top500': 0.0, 'top1000': 0.0, 'top5000': 0.0, 'ge4': 0.0, 'ge3': 0.0, 'avg_best': 0.0}
    avg = float(d.exact_rank.mean())
    return {'n': int(len(d)), 'avg_rank': avg, 'median_rank': float(d.exact_rank.median()), 'rank_lift': float(rank_lift(avg)), 'top30': float((d.exact_rank <= 30).mean()), 'top100': float((d.exact_rank <= 100).mean()), 'top500': float((d.exact_rank <= 500).mean()), 'top1000': float((d.exact_rank <= 1000).mean()), 'top5000': float((d.exact_rank <= 5000).mean()), 'ge4': float((d.best_hit >= 4).mean()), 'ge3': float((d.best_hit >= 3).mean()), 'avg_best': float(d.best_hit.mean())}

def weighted_cover_select_seeded_v236(ranked: pd.DataFrame, lines: int, candidate_pool: int=2500, lock_raw: int=10):
    lock = max(0, min(int(lock_raw), int(lines)))
    cand = ranked.head(min(candidate_pool, len(ranked))).copy()
    selected = []
    covered4 = set()
    covered3 = set()
    used = set()
    snapshots = []
    for _, row in ranked.head(lock).iterrows():
        co = tuple((int(x) for x in row.combo.split('-')))
        selected.append(co)
        used.add(row.combo)
        covered4.update(itertools.combinations(co, 4))
        covered3.update(itertools.combinations(co, 3))
        snapshots.append((len(covered4), len(covered3)))
    combo_cache = {row.combo: tuple((int(x) for x in row.combo.split('-'))) for _, row in cand.iterrows()}
    rank_score = 1.0 / np.sqrt(cand['rank'].to_numpy(dtype=float))
    while len(selected) < lines:
        select_no = len(selected) + 1
        progress('V236 cartera híbrida', done=select_no, total=lines)
        best_i = None
        best_sc = -1e+18
        for pos, (_, row) in enumerate(cand.iterrows()):
            if row.combo in used:
                continue
            co = combo_cache[row.combo]
            q4 = set(itertools.combinations(co, 4))
            q3 = set(itertools.combinations(co, 3))
            sc = 8.0 * rank_score[pos] + 0.7 * len(q4 - covered4) + 0.08 * len(q3 - covered3) + 0.12 * float(row.score)
            if selected:
                maxov = max((len(set(co) & set(x)) for x in selected))
                sc -= 0.55 * max(0, maxov - 2)
            if sc > best_sc:
                best_sc = sc
                best_i = pos
        if best_i is None:
            break
        row = cand.iloc[best_i]
        co = combo_cache[row.combo]
        selected.append(co)
        used.add(row.combo)
        covered4.update(itertools.combinations(co, 4))
        covered3.update(itertools.combinations(co, 3))
        snapshots.append((len(covered4), len(covered3)))
    rank_map = dict(zip(ranked.combo, ranked['rank']))
    score_map = dict(zip(ranked.combo, ranked.score))
    rows = []
    for i, co in enumerate(selected, 1):
        key = combo_str(co)
        c4, c3 = snapshots[i - 1]
        rows.append({'select_rank': i, 'combo': key, 'raw_rank': int(rank_map[key]), 'score': float(score_map[key]), 'sum': sum(co), 'locked_raw': bool(i <= lock), 'coverage4_unique': c4, 'coverage3_unique': c3})
    return pd.DataFrame(rows)

def technical_decision(wf: Optional[ValidationSummary], frozen: Optional[ValidationSummary]) -> Tuple[str, int, str]:
    if wf is None and frozen is None:
        return ('NO_DECISION', 5, 'No hubo validación.')
    signals = []
    rank_lifts = []
    exact_lifts = []
    for s in [wf, frozen]:
        if s is None:
            continue
        signals.append(s.p_exact_in_topk)
        rank_lifts.append(s.rank_lift_vs_random_pct)
        exact_lifts.append(s.exact5_lift)
    avg_rank_lift = float(np.mean(rank_lifts)) if rank_lifts else 0.0
    best_exact_lift = float(max(exact_lifts)) if exact_lifts else 0.0
    any_exact = any((s.exact5 > 0 for s in [wf, frozen] if s is not None))
    if any_exact and avg_rank_lift > 10 and (best_exact_lift > 1.25):
        conf = min(70, int(25 + avg_rank_lift + min(best_exact_lift, 5) * 5))
        return ('PLAY_EXPERIMENTAL_EDGE', conf, 'Hay señal histórica de concentración del exacto, pero no es garantía.')
    if avg_rank_lift > 5:
        conf = min(35, int(10 + avg_rank_lift))
        return ('WATCHLIST_WEAK_EDGE', conf, 'El ranking mejora frente al promedio aleatorio, pero la evidencia 5/5 es débil.')
    return ('NO_PLAY_5DE5_EDGE_NOT_PROVEN', 10, 'No se demostró ventaja estable para 5/5 frente al azar.')

def _prefix_hash_v238(df: pd.DataFrame, end_idx: int) -> str:
    end_idx = max(0, min(int(end_idx), len(df)))
    cols = ['CONCURSO'] + R_COLS
    raw = df.iloc[:end_idx][cols].to_csv(index=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()

def load_or_extend_shared_cache_v238(df, cache_dir: Path, start_idx: int, end_idx: int, negatives: int, seed: int, hard_ratio: float):
    """Reusable across V238 targets. Validates historical prefix, then builds only missing cache blocks."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    cp = cache_dir / 'master_cache_shared.joblib'
    mp = cache_dir / 'master_cache_shared.json'
    cache = {}
    status = 'MISS'
    if JOBLIB_OK and cp.exists() and mp.exists():
        try:
            meta = json.loads(mp.read_text(encoding='utf-8'))
            old_end = int(meta.get('end_idx', 0))
            params_ok = int(meta.get('negatives', -1)) == int(negatives) and int(meta.get('seed', -1)) == int(seed) and (abs(float(meta.get('hard_ratio', -1)) - float(hard_ratio)) < 1e-12)
            prefix_ok = old_end <= len(df) and meta.get('prefix_hash') == _prefix_hash_v238(df, old_end)
            if params_ok and prefix_ok:
                cache = joblib.load(cp)
                status = f'HIT prefix={old_end}'
        except Exception as e:
            status = f'MISS {type(e).__name__}'
    missing = [i for i in range(start_idx, end_idx) if i not in cache]
    if missing:
        progress(f'V238 shared cache: {status}; construyendo {len(missing)} bloques faltantes')
        runs = []
        a = prev = missing[0]
        for i in missing[1:]:
            if i == prev + 1:
                prev = i
            else:
                runs.append((a, prev + 1))
                a = prev = i
        runs.append((a, prev + 1))
        for a, b in runs:
            cache.update(build_master_cache_v235(df, a, b, negatives, seed, hard_ratio))
        if JOBLIB_OK:
            _atomic_joblib_dump(cache, cp, compress=3)
            meta = {'start_idx': min(cache) if cache else start_idx, 'end_idx': end_idx, 'negatives': int(negatives), 'seed': int(seed), 'hard_ratio': float(hard_ratio), 'prefix_hash': _prefix_hash_v238(df, end_idx), 'updated_at': time.strftime('%Y-%m-%d %H:%M:%S'), 'targets': len(cache)}
            tmp = cache_dir / 'master_cache_shared.json.tmp'
            tmp.write_text(json.dumps(meta, indent=2), encoding='utf-8')
            os.replace(tmp, mp)
        status = f'EXTENDED +{len(missing)}'
    else:
        status = f'{status} COMPLETE'
    return (cache, status)
V239_GATE_STRATEGIES = ['heuristic', 'number_transition', 'number_ml', 'number_transition_affinity', 'number_freq', 'number_markov', 'number_knn', 'v235_full', 'binary', 'pairwise']
V239_TRANSITION_COLS = [0, 1, 2, 3, 4, 6, 7, 8]

def train_transition_number_model_v239(Xn: np.ndarray, yn: np.ndarray, seed: int):
    """Calibrador causal de señales por número: frecuencia + EWMA + Markov + KNN + pair-to-last."""
    if not SKLEARN_OK or len(Xn) < 280:
        return None
    Xs = np.asarray(Xn[:, V239_TRANSITION_COLS], dtype=np.float32)
    mdl = Pipeline([('scaler', StandardScaler()), ('lr', LogisticRegression(C=0.35, solver='lbfgs', max_iter=1200, class_weight='balanced', random_state=seed + 239))])
    mdl.fit(Xs, np.asarray(yn, dtype=np.uint8))
    return mdl

def train_bundle_v239(cache, start_idx: int, end_idx: int, seed: int, binary_estimators: int, ranker_estimators: int, runtime: Optional[ModelRuntime]=None):
    bundle = train_bundle_v236(cache, start_idx, end_idx, seed, binary_estimators, ranker_estimators, runtime=runtime)
    Xn, yn = stack_master_number_v235(cache, start_idx, end_idx)
    bundle['transition_number_model'] = train_transition_number_model_v239(Xn, yn, seed)
    return bundle

def train_bundle_v243(cache, start_idx, end_idx, seed, binary_estimators, ranker_estimators, ltr_seeds=3, ltr_topk=30, mirage_bank=None, optuna_trials=0, negatives_per_positive=600, runtime: Optional[ModelRuntime]=None):
    runtime = runtime or default_model_runtime()
    X, y, rel, qid, _ = stack_master_combo_v235(cache, start_idx, end_idx)
    Xn, yn = stack_master_number_v235(cache, start_idx, end_idx)
    if len(X) == 0:
        return {'binary_models': None, 'pairwise_ranker': None, 'ndcg_rankers': [], 'number_model': None, 'transition_number_model': None}
    ndcg = train_ndcg_ranker_ensemble_v243(X, rel, qid, seed, ranker_estimators, ltr_seeds, ltr_topk, runtime=runtime)
    pairwise = train_pairwise_ranker_v235(X, rel, qid, seed, max(100, int(ranker_estimators * 0.75)), runtime=runtime)
    Xb, yb = _append_mirage_rows_v240(X, y, mirage_bank)
    tuned = optimize_xgb_gpu_temporal_v240(Xb, yb, n_trials=optuna_trials, seed=seed, negatives_per_positive=negatives_per_positive, runtime=runtime)
    binary = train_ensemble(Xb, yb, seed, xgb_params=tuned, runtime=runtime, estimators=binary_estimators)
    number = train_number_model_v235(Xn, yn, seed, ranker_estimators, runtime=runtime)
    transition = train_transition_number_model_v239(Xn, yn, seed)
    return {'binary_models': binary, 'pairwise_ranker': pairwise, 'ndcg_rankers': ndcg, 'number_model': number, 'transition_number_model': transition, 'v240_optuna_params': tuned, 'v243_ltr_seeds': len(ndcg), 'v243_ltr_topk': int(ltr_topk), 'v240_mirage_rows': int(sum((len(r.get('X', [])) for r in mirage_bank or [])))}
V245_ADV_SOURCES_DEFAULT = ('ltr_adv_exact5', 'ltr_ndcg_exact5', 'v241_fusion', 'binary', 'heuristic')

def stack_adversarial_queries_v245(cache, start_idx: int, end_idx: int, adversarial_bank: Optional[Dict[int, Dict[str, np.ndarray]]]=None, adv_memory: int=300):
    """
    Construye queries LTR con objetivo EXACT5 binario.

    Cada query conserva el positivo/negativos causales del MASTER CACHE. Para targets
    ya resueltos puede añadir falsos positivos que fueron minados por un modelo OOF
    antes de conocer ese target. El ganador exacto es la única relevancia 1.
    """
    keys = [i for i in range(start_idx, end_idx) if i in cache]
    if not keys:
        return (np.empty((0, len(FEATURE_NAMES)), np.float32), np.empty(0, np.float32), np.empty(0, np.int32), [], 0)
    adv_bank = adversarial_bank or {}
    eligible_adv = [k for k in sorted(adv_bank) if start_idx <= int(k) < end_idx]
    if adv_memory > 0:
        eligible_adv = eligible_adv[-int(adv_memory):]
    eligible_adv = set(map(int, eligible_adv))
    Xs, ys, qids, groups = ([], [], [], [])
    adv_rows = 0
    for q, idx in enumerate(keys):
        rec = cache[idx]
        X0 = np.asarray(rec['Xc'], dtype=np.float32)
        y0 = np.asarray(rec['yb'], dtype=np.float32)
        cand0 = np.asarray(rec.get('cand_idx', np.arange(len(X0))), dtype=np.int32)
        parts = [X0]
        labels = [y0]
        nrow = len(X0)
        if idx in eligible_adv:
            ar = adv_bank.get(idx) or {}
            Xa = ar.get('X')
            ia = ar.get('indices')
            if Xa is not None and ia is not None and (len(Xa) == len(ia)) and len(Xa):
                Xa = np.asarray(Xa, dtype=np.float32)
                ia = np.asarray(ia, dtype=np.int32)
                base_set = set(map(int, cand0.tolist()))
                keep = np.asarray([int(j) not in base_set for j in ia], dtype=bool)
                Xa = Xa[keep]
                if len(Xa):
                    parts.append(Xa)
                    labels.append(np.zeros(len(Xa), dtype=np.float32))
                    nrow += len(Xa)
                    adv_rows += len(Xa)
        Xq = np.vstack(parts) if len(parts) > 1 else parts[0]
        yq = np.concatenate(labels) if len(labels) > 1 else labels[0]
        if int(np.sum(yq > 0.5)) != 1:
            raise ValueError(f'V245 query {idx}: se esperaba exactamente un positivo, encontrados {int(np.sum(yq > 0.5))}')
        Xs.append(Xq)
        ys.append(yq)
        qids.append(np.full(nrow, q, dtype=np.int32))
        groups.append(int(nrow))
    return (np.vstack(Xs), np.concatenate(ys), np.concatenate(qids), groups, int(adv_rows))

def train_adversarial_exact5_ranker_v245(X, y_exact, qid, seed, estimators, topk=30, runtime: Optional[ModelRuntime]=None):
    """LambdaMART NDCG con relevancia binaria exacta: sólo la combinación ganadora vale 1."""
    runtime = runtime or default_model_runtime()
    if not XGBOOST_OK or len(X) < 100:
        return None
    X = np.asarray(X, dtype=np.float32)
    y = np.asarray(y_exact, dtype=np.float32)
    qid = np.asarray(qid, dtype=np.int32)
    if len(X) != len(y) or len(X) != len(qid):
        raise ValueError('V245 adversarial LTR: X/y/qid mismatch')
    if np.any(qid[1:] < qid[:-1]):
        order = np.argsort(qid, kind='stable')
        X, y, qid = (X[order], y[order], qid[order])
    mdl = XGBRanker(objective='rank:ndcg', eval_metric=f'ndcg@{max(10, int(topk))}', n_estimators=max(120, int(estimators)), max_depth=4, learning_rate=0.028, min_child_weight=4.0, subsample=0.88, colsample_bytree=0.9, reg_alpha=0.12, reg_lambda=2.2, gamma=0.02, tree_method='hist', device=(runtime.gpu_device if runtime.gpu_available else 'cpu'), lambdarank_pair_method='topk', lambdarank_num_pair_per_sample=max(32, int(topk) * 2), random_state=int(seed), n_jobs=1, verbosity=0)
    progress(f"V264 ADV-EXACT5 seed={seed} | trees={mdl.get_params()['n_estimators']} | rows={len(X):,} | ndcg@{max(10, int(topk))} | binary relevance")
    t = time.time()
    mdl.fit(X, y, qid=qid)
    progress(f'V245 ADV-EXACT5 seed={seed} terminado en {time.time() - t:.1f}s')
    return mdl

def train_adversarial_exact5_ensemble_v245(X, y, qid, seed, estimators, n_seeds=3, topk=30, runtime: Optional[ModelRuntime]=None):
    models = []
    for k in range(max(1, int(n_seeds))):
        m = train_adversarial_exact5_ranker_v245(X, y, qid, seed + 245 + 1301 * k, estimators, topk, runtime=runtime)
        if m is not None:
            models.append(m)
    return models

def predict_adversarial_exact5_ensemble_v245(models, X):
    """Rank-average logarítmico para neutralizar escala entre seeds."""
    if not models:
        return np.zeros(len(X), dtype=float)
    acc = np.zeros(len(X), dtype=np.float64)
    used = 0
    den = math.log1p(max(2, len(X)))
    for m in models:
        try:
            raw = np.asarray(m.predict(X), dtype=float)
            order = np.argsort(-raw, kind='stable')
            ranks = np.empty(len(raw), dtype=np.int32)
            ranks[order] = np.arange(1, len(raw) + 1, dtype=np.int32)
            acc += 1.0 - np.log1p(ranks.astype(np.float64) - 1.0) / den
            used += 1
        except Exception as e:
            print(f'WARNING: V245 adversarial ensemble prediction failed: {type(e).__name__}: {e}', file=sys.stderr)
    return safe_z(acc / max(1, used))

def mine_adversarial_query_v245(hist_df: pd.DataFrame, realized_combo: Tuple[int, ...], score_map: Dict[str, np.ndarray], sources: Sequence[str]=V245_ADV_SOURCES_DEFAULT, per_source: int=40, max_total: int=160) -> Dict[str, np.ndarray]:
    """
    Mina falsos positivos del universo completo DESPUÉS de resolver un target.
    Los scores y features fueron construidos con hist_df (pre-target). El resultado
    realizado sólo se usa para retirar el único positivo de la lista de negativos.
    """
    true_i = COMBO_TO_INDEX[tuple(sorted(map(int, realized_combo)))]
    chosen, seen = ([], {int(true_i)})
    source_id = []
    for sid, st in enumerate(sources):
        sc = score_map.get(st)
        if sc is None:
            continue
        sc = np.asarray(sc, dtype=float)
        if not np.all(np.isfinite(sc)) or float(np.std(sc)) < 1e-12:
            continue
        k = min(len(sc), max(2, int(per_source) + 1))
        if k <= 1:
            continue
        idx = np.argpartition(-sc, k - 1)[:k]
        idx = idx[np.argsort(-sc[idx], kind='stable')]
        added = 0
        for j in idx:
            jj = int(j)
            if jj in seen:
                continue
            seen.add(jj)
            chosen.append(jj)
            source_id.append(int(sid))
            added += 1
            if added >= int(per_source) or len(chosen) >= int(max_total):
                break
        if len(chosen) >= int(max_total):
            break
    if not chosen:
        return {'indices': np.empty(0, np.int32), 'X': np.empty((0, len(FEATURE_NAMES)), np.float32), 'source_id': np.empty(0, np.int16)}
    idx = np.asarray(chosen[:max_total], dtype=np.int32)
    X, _, _ = build_universe_features(hist_df, candidate_mask=idx)
    return {'indices': idx, 'X': X.astype(np.float32, copy=False), 'source_id': np.asarray(source_id[:len(idx)], dtype=np.int16)}

def train_bundle_v245(cache, start_idx: int, end_idx: int, seed: int, binary_estimators: int, ranker_estimators: int, ltr_seeds: int=3, ltr_topk: int=30, mirage_bank=None, adversarial_bank=None, adv_memory: int=300, optuna_trials: int=0, negatives_per_positive: int=120, runtime: Optional[ModelRuntime]=None):
    """V243 completo + especialista V245 exact-only con hard negatives OOF."""
    bundle = train_bundle_v243(cache, start_idx, end_idx, seed, binary_estimators, ranker_estimators, ltr_seeds=ltr_seeds, ltr_topk=ltr_topk, mirage_bank=mirage_bank, optuna_trials=optuna_trials, negatives_per_positive=negatives_per_positive, runtime=runtime)
    X, y, qid, groups, adv_rows = stack_adversarial_queries_v245(cache, start_idx, end_idx, adversarial_bank=adversarial_bank, adv_memory=adv_memory)
    adv_models = train_adversarial_exact5_ensemble_v245(X, y, qid, seed, ranker_estimators, n_seeds=ltr_seeds, topk=ltr_topk, runtime=runtime)
    bundle['v245_adv_exact_rankers'] = adv_models
    bundle['v245_adversarial_rows'] = int(adv_rows)
    bundle['v245_query_rows'] = int(len(X))
    bundle['v245_adv_memory'] = int(adv_memory)
    return bundle

def _combo_score_from_number_signal_v239(v: np.ndarray) -> np.ndarray:
    """Convierte una señal de 28 números en ranking de 98,280 combinaciones sin filtros geométricos."""
    z = safe_z(np.asarray(v, dtype=float))
    return safe_z(np.mean(z[ALL_COMBOS - 1], axis=1))

def number_specialist_parts_v239(hist_df: pd.DataFrame, bundle=None) -> Dict[str, np.ndarray]:
    Xn = build_number_features_v235(hist_df)
    freq_num = 0.22 * Xn[:, 0] + 0.22 * Xn[:, 1] + 0.12 * Xn[:, 2] + 0.24 * Xn[:, 3] + 0.2 * Xn[:, 4]
    markov_num = np.asarray(Xn[:, 6], dtype=float)
    knn_num = np.asarray(Xn[:, 7], dtype=float)
    ml_num = None
    if bundle and bundle.get('number_model') is not None:
        try:
            ml_num = np.asarray(bundle['number_model'].predict_proba(Xn)[:, 1], dtype=float)
        except Exception as e:
            log_exception('number_specialist.number_model', e)
            ml_num = None
    if ml_num is None:
        ml_num = np.asarray(freq_num, dtype=float)
    tr_num = None
    if bundle and bundle.get('transition_number_model') is not None:
        try:
            tr_num = np.asarray(bundle['transition_number_model'].predict_proba(Xn[:, V239_TRANSITION_COLS])[:, 1], dtype=float)
        except Exception as e:
            log_exception('number_specialist.transition_model', e)
            tr_num = None
    if tr_num is None:
        tr_num = 0.28 * safe_z(ml_num) + 0.24 * safe_z(freq_num) + 0.26 * safe_z(markov_num) + 0.22 * safe_z(knn_num)
    return {'number_ml': _combo_score_from_number_signal_v239(ml_num), 'number_freq': _combo_score_from_number_signal_v239(freq_num), 'number_markov': _combo_score_from_number_signal_v239(markov_num), 'number_knn': _combo_score_from_number_signal_v239(knn_num), 'number_transition': _combo_score_from_number_signal_v239(tr_num)}

def score_parts_v239(hist_df: pd.DataFrame, bundle=None):
    ctx, base = score_parts_v236(hist_df, bundle)
    ns = number_specialist_parts_v239(hist_df, bundle)
    parts = dict(base)
    parts.update(ns)
    need_combo_x = bool(bundle and (bundle.get('ndcg_rankers') or bundle.get('v245_adv_exact_rankers') or any((bundle.get(f'v246_{a}_rankers') for a in V248_SAMPLER_ARM_NAMES))))
    X_u = None
    if need_combo_x:
        try:
            X_u, _, _ = build_universe_features(hist_df)
        except Exception as e:
            print(f'WARNING: full-universe feature build failed: {type(e).__name__}: {e}', file=sys.stderr)
            X_u = None
    if bundle and bundle.get('ndcg_rankers') and (X_u is not None):
        try:
            parts['ltr_ndcg_exact5'] = predict_ndcg_ranker_ensemble_v243(bundle.get('ndcg_rankers'), X_u)
        except Exception as e:
            print(f'WARNING: ltr_ndcg_exact5 prediction failed: {type(e).__name__}: {e}', file=sys.stderr)
            parts['ltr_ndcg_exact5'] = np.zeros(UNIVERSE_SIZE, dtype=float)
    else:
        parts['ltr_ndcg_exact5'] = np.zeros(UNIVERSE_SIZE, dtype=float)
    if bundle and bundle.get('v245_adv_exact_rankers') and (X_u is not None):
        try:
            parts['ltr_adv_exact5'] = predict_adversarial_exact5_ensemble_v245(bundle.get('v245_adv_exact_rankers'), X_u)
        except Exception as e:
            print(f'WARNING: ltr_adv_exact5 prediction failed: {type(e).__name__}: {e}', file=sys.stderr)
            parts['ltr_adv_exact5'] = np.zeros(UNIVERSE_SIZE, dtype=float)
    else:
        parts['ltr_adv_exact5'] = np.zeros(UNIVERSE_SIZE, dtype=float)
    for _arm in V248_SAMPLER_ARM_NAMES:
        _name = f'ltr_exact5_{_arm}'
        _models = bundle.get(f'v246_{_arm}_rankers') if bundle else None
        if _models and X_u is not None:
            try:
                parts[_name] = predict_adversarial_exact5_ensemble_v245(_models, X_u)
            except Exception as e:
                print(f'WARNING: {_name} prediction failed: {type(e).__name__}: {e}', file=sys.stderr)
                parts[_name] = np.zeros(UNIVERSE_SIZE, dtype=float)
        else:
            parts[_name] = np.zeros(UNIVERSE_SIZE, dtype=float)
    parts['ltr_ndcg_number'] = safe_z(0.72 * parts['ltr_ndcg_exact5'] + 0.2 * parts['number_transition'] + 0.08 * parts['heuristic'])
    parts['number_transition_affinity'] = safe_z(0.78 * parts['number_transition'] + 0.14 * parts['affinity'] + 0.08 * parts['heuristic'])
    parts['v235_full'] = strategy_score_v236(base, 'v235_full')
    return (ctx, parts)

def strategy_score_v239(parts: Dict[str, np.ndarray], strategy: str) -> np.ndarray:
    if strategy in parts:
        return safe_z(np.asarray(parts[strategy], dtype=float))
    if strategy in V236_STRATEGIES:
        return strategy_score_v236(parts, strategy)
    raise KeyError(f'Estrategia V239 desconocida: {strategy}')
V243_LTR_SEEDS = 3
V244_ALPHA = 0.05
V244_CORRECTION = 'holm'
V244_SIGNIFICANCE_LOOKBACK = 300
V244_LINES = 30
V241_FUSION_STRATEGIES = ('heuristic', 'ltr_ndcg_exact5', 'ltr_adv_exact5', 'ltr_exact5_balanced', 'ltr_exact5_hard', 'ltr_exact5_ultra', 'ltr_ndcg_number', 'number_transition', 'number_ml', 'number_freq', 'number_markov', 'number_knn', 'number_transition_affinity', 'v235_full')

def adjust_pvalues_v244(pvals: Dict[str, float], method: str='holm') -> Dict[str, float]:
    """
    Corrección de comparaciones múltiples.
      holm: controla FWER (default, estricta).
      fdr_bh: Benjamini-Hochberg, controla FDR.
      none: sólo diagnóstico.
    """
    clean = {k: float(np.clip(v, 0.0, 1.0)) for k, v in pvals.items() if np.isfinite(v)}
    if not clean:
        return {}
    method = str(method).lower()
    names = list(clean)
    p = np.array([clean[k] for k in names], dtype=float)
    m = len(p)
    if method in {'none', 'raw'}:
        return dict(clean)
    order = np.argsort(p)
    adj = np.ones(m, dtype=float)
    if method in {'holm', 'holm-bonferroni', 'bonferroni-holm'}:
        running = 0.0
        for rank, j in enumerate(order):
            val = (m - rank) * p[j]
            running = max(running, val)
            adj[j] = min(1.0, running)
    elif method in {'fdr', 'fdr_bh', 'bh', 'benjamini-hochberg'}:
        running = 1.0
        for rev_rank in range(m - 1, -1, -1):
            j = order[rev_rank]
            rank1 = rev_rank + 1
            val = p[j] * m / rank1
            running = min(running, val)
            adj[j] = min(1.0, running)
    else:
        raise ValueError(f'Método de corrección no soportado: {method}')
    return {names[i]: float(adj[i]) for i in range(m)}

def hac_mean_test_v244(values: np.ndarray, max_lag: Optional[int]=None) -> Dict[str, float]:
    """
    Test unilateral H0: E[value] <= 0 vs H1: E[value] > 0
    con error estándar HAC/Newey-West para tolerar dependencia serial.
    """
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 12:
        return {'n': int(n), 'mean': float(np.mean(x)) if n else 0.0, 'se_hac': float('nan'), 'z': 0.0, 'p_one_sided': 1.0, 'ci95_low': float('nan'), 'ci95_high': float('nan'), 'max_lag': 0}
    mu = float(np.mean(x))
    u = x - mu
    if max_lag is None:
        max_lag = max(1, min(n // 4, int(round(4.0 * (n / 100.0) ** (2.0 / 9.0)))))
    gamma0 = float(np.dot(u, u) / n)
    lrv = gamma0
    for lag in range(1, max_lag + 1):
        gamma = float(np.dot(u[lag:], u[:-lag]) / n)
        weight = 1.0 - lag / (max_lag + 1.0)
        lrv += 2.0 * weight * gamma
    var_mean = max(1e-18, lrv / n)
    se = math.sqrt(var_mean)
    z = mu / se if se > 0 else 0.0
    if SCIPY_STATS_OK:
        p = float(norm_dist.sf(z))
        crit = float(norm_dist.ppf(0.975))
    else:
        p = 0.5 * math.erfc(z / math.sqrt(2.0))
        crit = 1.959963984540054
    return {'n': int(n), 'mean': mu, 'se_hac': float(se), 'z': float(z), 'p_one_sided': float(np.clip(p, 0.0, 1.0)), 'ci95_low': float(mu - crit * se), 'ci95_high': float(mu + crit * se), 'max_lag': int(max_lag)}

def paired_strategy_tests_v244(meta_rows: pd.DataFrame, baseline: str='heuristic', strategies: Optional[List[str]]=None, lookback: int=300, correction: str='holm', lines: Optional[int]=None) -> pd.DataFrame:
    """
    Compara rank OOS de cada challenger contra baseline.
    delta_pct > 0 => challenger mejora el rank del ganador.
    P-values corregidos en la misma familia de estrategias.
    """
    cols = ['strategy', 'n', 'mean_delta_pct', 'ci95_low', 'ci95_high', 'z_hac', 'p_raw', 'p_holm', 'p_fdr_bh', 'exact5_hits', 'exact5_p_raw', 'exact5_p_holm', 'exact5_p_fdr_bh']
    if meta_rows is None or meta_rows.empty:
        return pd.DataFrame(columns=cols)
    lines = int(V244_LINES if lines is None else lines)
    strategies = strategies or [s for s in V241_FUSION_STRATEGIES if s != baseline]
    d = meta_rows[meta_rows['strategy'].isin([baseline] + list(strategies))][['target', 'strategy', 'exact_rank']].copy()
    pvt = d.pivot_table(index='target', columns='strategy', values='exact_rank', aggfunc='last').sort_index()
    rows = []
    raw = {}
    for st in strategies:
        if baseline not in pvt.columns or st not in pvt.columns:
            continue
        q = pvt[[baseline, st]].dropna().tail(max(20, int(lookback)))
        if len(q) < 12:
            continue
        delta = 100.0 * (q[baseline].to_numpy(float) - q[st].to_numpy(float)) / float(UNIVERSE_SIZE)
        tst = hac_mean_test_v244(delta)
        raw[st] = tst['p_one_sided']
        ex_hits = int(np.sum(q[st].to_numpy(float) <= lines))
        ex_ev = exact5_binomial_evidence_v244(len(q), ex_hits, lines)
        rows.append({'strategy': st, 'n': int(tst['n']), 'mean_delta_pct': float(tst['mean']), 'ci95_low': float(tst['ci95_low']), 'ci95_high': float(tst['ci95_high']), 'z_hac': float(tst['z']), 'p_raw': float(tst['p_one_sided']), 'exact5_hits': ex_hits, 'exact5_p_raw': float(ex_ev['p_one_sided'])})
    holm = adjust_pvalues_v244(raw, 'holm')
    fdr = adjust_pvalues_v244(raw, 'fdr_bh')
    exact_raw = {r['strategy']: float(r['exact5_p_raw']) for r in rows}
    exact_holm = adjust_pvalues_v244(exact_raw, 'holm')
    exact_fdr = adjust_pvalues_v244(exact_raw, 'fdr_bh')
    for r in rows:
        r['p_holm'] = float(holm.get(r['strategy'], 1.0))
        r['p_fdr_bh'] = float(fdr.get(r['strategy'], 1.0))
        r['exact5_p_holm'] = float(exact_holm.get(r['strategy'], 1.0))
        r['exact5_p_fdr_bh'] = float(exact_fdr.get(r['strategy'], 1.0))
    return pd.DataFrame(rows, columns=cols).sort_values(['p_holm', 'mean_delta_pct'], ascending=[True, False]).reset_index(drop=True)

def exact5_binomial_evidence_v244(trials: int, hits: int, lines: int, confidence: float=0.95) -> Dict[str, float]:
    """
    Test exacto binomial unilateral contra H0 de ranking aleatorio.
    p0 = lines / C(28,5).
    IC Clopper-Pearson para la tasa observada y su lift.
    """
    n = int(max(0, trials))
    k = int(max(0, hits))
    p0 = float(lines / UNIVERSE_SIZE)
    alpha = 1.0 - float(confidence)
    if n <= 0:
        return {'trials': 0, 'hits': 0, 'p0_random': p0, 'observed_rate': 0.0, 'expected_hits': 0.0, 'lift': 0.0, 'p_one_sided': 1.0, 'rate_ci95_low': 0.0, 'rate_ci95_high': 1.0, 'lift_ci95_low': 0.0, 'lift_ci95_high': float('inf')}
    obs = k / n
    if SCIPY_STATS_OK:
        pval = float(binomtest(k, n=n, p=p0, alternative='greater').pvalue)
        lo = 0.0 if k == 0 else float(beta_dist.ppf(alpha / 2.0, k, n - k + 1))
        hi = 1.0 if k == n else float(beta_dist.ppf(1 - alpha / 2.0, k + 1, n - k))
    else:
        probs = []
        for j in range(k, n + 1):
            lp = math.lgamma(n + 1) - math.lgamma(j + 1) - math.lgamma(n - j + 1) + j * math.log(max(p0, 1e-300)) + (n - j) * math.log(max(1 - p0, 1e-300))
            probs.append(math.exp(lp))
        pval = min(1.0, float(sum(probs)))
        lo, hi = (0.0, 1.0)
    return {'trials': n, 'hits': k, 'p0_random': p0, 'observed_rate': float(obs), 'expected_hits': float(n * p0), 'lift': float(obs / p0) if p0 > 0 else float('inf'), 'p_one_sided': float(pval), 'rate_ci95_low': float(lo), 'rate_ci95_high': float(hi), 'lift_ci95_low': float(lo / p0) if p0 > 0 else 0.0, 'lift_ci95_high': float(hi / p0) if p0 > 0 else float('inf')}

def exact5_power_analysis_v244(lines: int, alpha: float=0.05, power_target: float=0.8, lifts: Sequence[float]=(2.0, 3.0, 5.0, 10.0), max_n: int=2000000) -> List[Dict[str, float]]:
    """
    Tamaño de muestra prospectiva aproximado/exacto-binomial para detectar
    una tasa de 5/5 = lift * p0 con test unilateral.
    """
    p0 = float(lines / UNIVERSE_SIZE)
    out = []
    if not SCIPY_STATS_OK:
        return out

    def power_at(n: int, p1: float):
        q = binom_dist.isf(alpha, n, p0)
        kcrit = int(q) + 1
        while kcrit > 0 and binom_dist.sf(kcrit - 2, n, p0) <= alpha:
            kcrit -= 1
        while binom_dist.sf(kcrit - 1, n, p0) > alpha:
            kcrit += 1
        pw = float(binom_dist.sf(kcrit - 1, n, p1))
        return (pw, kcrit)
    for lift in lifts:
        p1 = min(1.0, p0 * float(lift))
        lo, hi = (1, 128)
        pw, kc = power_at(hi, p1)
        while pw < power_target and hi < max_n:
            lo = hi + 1
            hi = min(max_n, hi * 2)
            pw, kc = power_at(hi, p1)
        if pw < power_target:
            out.append({'lift': float(lift), 'p0': p0, 'p1': p1, 'required_trials_80pct_power': None, 'critical_hits': None, 'achieved_power': float(pw)})
            continue
        left, right = (max(1, lo), hi)
        while left < right:
            mid = (left + right) // 2
            mpw, _ = power_at(mid, p1)
            if mpw >= power_target:
                right = mid
            else:
                left = mid + 1
        fpw, fkc = power_at(left, p1)
        out.append({'lift': float(lift), 'p0': p0, 'p1': p1, 'required_trials_80pct_power': int(left), 'critical_hits': int(fkc), 'achieved_power': float(fpw)})
    return out

def rank_uniform_evidence_v244(ranks: Sequence[float]) -> Dict[str, float]:
    """
    H0: el ganador es uniforme dentro del ranking 1..98,280.
    Test unilateral: rango medio menor que azar.
    """
    x = np.asarray(list(ranks), dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    mu0 = (UNIVERSE_SIZE + 1.0) / 2.0
    var0 = (UNIVERSE_SIZE ** 2 - 1.0) / 12.0
    if n <= 0:
        return {'n': 0, 'mean_rank': float('nan'), 'random_mean_rank': mu0, 'rank_lift_pct': 0.0, 'z': 0.0, 'p_one_sided': 1.0}
    mean = float(np.mean(x))
    se = math.sqrt(var0 / n)
    z = (mean - mu0) / se
    p = float(norm_dist.cdf(z)) if SCIPY_STATS_OK else 0.5 * (1 + math.erf(z / math.sqrt(2.0)))
    return {'n': int(n), 'mean_rank': mean, 'random_mean_rank': float(mu0), 'rank_lift_pct': float(100.0 * (1.0 - mean / mu0)), 'z': float(z), 'p_one_sided': float(np.clip(p, 0.0, 1.0))}

def statistical_report_v244(wf_detail: Optional[pd.DataFrame], meta_rows: Optional[pd.DataFrame], lines: int, lookback: int=300) -> Dict[str, object]:
    """
    HISTORICAL/EXPLORATORY evidence. No se etiqueta como confirmatoria,
    porque el motor fue desarrollado iterativamente sobre este mismo histórico.
    """
    report = {'evidence_class': 'historical_exploratory', 'warning': 'P-values históricos no son confirmatorios debido a iteración de modelos y researcher degrees of freedom. La confirmación requiere forward test pre-registrado.', 'prospective_power_exact5': exact5_power_analysis_v244(lines)}
    if wf_detail is not None and (not wf_detail.empty):
        n = len(wf_detail)
        hits = int(wf_detail['exact5'].sum()) if 'exact5' in wf_detail.columns else 0
        report['final_portfolio_exact5_binomial'] = exact5_binomial_evidence_v244(n, hits, lines)
        if 'exact_rank' in wf_detail.columns:
            report['final_portfolio_rank_vs_uniform'] = rank_uniform_evidence_v244(wf_detail['exact_rank'].to_numpy(float))
    tests = paired_strategy_tests_v244(meta_rows, baseline='heuristic', strategies=[x for x in V241_FUSION_STRATEGIES if x != 'heuristic'], lookback=lookback, lines=lines)
    report['multiple_strategy_tests'] = tests.to_dict(orient='records')
    return report

def select_rank_fusion_weights_v244(meta_rows: pd.DataFrame, min_history: int=80, bootstrap_samples: int=500, min_p_better: float=0.6, min_edge_pct: float=0.25, seed: int=DEFAULT_SEED, alpha: Optional[float]=None, correction: Optional[str]=None, significance_lookback: Optional[int]=None) -> Tuple[Dict[str, float], Dict[str, Dict[str, float]], str]:
    """
    V241 selector + guardrail V244.
    Un challenger recibe peso sólo si:
      a) pasa las reglas de efecto/estabilidad de V241;
      b) su mejora pareada de rank sobre heuristic sobrevive corrección múltiple.
    """
    alpha = float(V244_ALPHA if alpha is None else alpha)
    correction = str(V244_CORRECTION if correction is None else correction)
    significance_lookback = int(V244_SIGNIFICANCE_LOOKBACK if significance_lookback is None else significance_lookback)
    base_w, evidence, _ = select_rank_fusion_weights_v241(meta_rows, min_history=min_history, bootstrap_samples=bootstrap_samples, min_p_better=min_p_better, min_edge_pct=min_edge_pct, seed=seed)
    tests = paired_strategy_tests_v244(meta_rows, baseline='heuristic', strategies=[x for x in V241_FUSION_STRATEGIES if x != 'heuristic'], lookback=significance_lookback, correction=correction)
    pcol = 'p_holm' if str(correction).lower().startswith('holm') else 'p_fdr_bh' if str(correction).lower() in {'fdr', 'fdr_bh', 'bh', 'benjamini-hochberg'} else 'p_raw'
    sigmap = {}
    for _, r in tests.iterrows():
        sigmap[str(r['strategy'])] = {'p_raw': float(r['p_raw']), 'p_adjusted': float(r[pcol]), 'mean_delta_pct_hac': float(r['mean_delta_pct']), 'ci95_low': float(r['ci95_low']), 'ci95_high': float(r['ci95_high'])}
    kept = {'heuristic': float(base_w.get('heuristic', 1.0))}
    for st, w in base_w.items():
        if st == 'heuristic' or w <= 0:
            continue
        stsig = sigmap.get(st)
        if stsig and stsig['p_adjusted'] <= alpha and (stsig['ci95_low'] > 0.0):
            kept[st] = float(w)
    total = float(sum(kept.values()))
    kept = {k: float(v / total) for k, v in kept.items()}
    for st in V241_FUSION_STRATEGIES:
        if st == 'heuristic':
            continue
        evidence.setdefault(st, {})
        evidence[st]['v244_significance'] = sigmap.get(st, {'p_raw': 1.0, 'p_adjusted': 1.0, 'mean_delta_pct_hac': 0.0, 'ci95_low': float('nan'), 'ci95_high': float('nan')})
    if len(kept) == 1:
        state = f'heuristic_only_after_{correction}'
    elif len(kept) == 2:
        state = f'single_significant_challenger_{correction}'
    else:
        state = f'multi_significant_challengers_{correction}'
    return (kept, evidence, state)

def _sha256_file_v244(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def sha256_code_path_v248(path: Path) -> str:
    """Hash one standalone script or an entire modular package deterministically."""
    path = Path(path)
    if path.is_file():
        return _sha256_file_v244(path)
    if path.is_dir():
        h = hashlib.sha256()
        files = sorted(p for p in path.rglob('*.py') if '__pycache__' not in p.parts)
        for fp in files:
            rel = fp.relative_to(path).as_posix().encode('utf-8')
            h.update(len(rel).to_bytes(4, 'big')); h.update(rel)
            data = fp.read_bytes()
            h.update(len(data).to_bytes(8, 'big')); h.update(data)
        return h.hexdigest()
    raise FileNotFoundError(path)

def _canonical_sha_v244(obj: Dict[str, object]) -> str:
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()

def register_prospective_prediction_v244(registry_dir: Path, target: int, audit, portfolio: pd.DataFrame, ranking_path: Path, history_path: Path, script_path: Path, args, production_weights: Dict[str, float], production_allocation: Dict[str, int], statistical_report: Dict[str, object]) -> Path:
    """
    Pre-registro local con hash y cadena SHA256.
    Detecta modificaciones, pero NO sustituye un timestamp externo/notariado.
    """
    registry_dir.mkdir(parents=True, exist_ok=True)
    chain_path = registry_dir / 'v248_prospective_chain.jsonl'
    prev_hash = None
    if chain_path.exists():
        try:
            lines = [x for x in chain_path.read_text(encoding='utf-8').splitlines() if x.strip()]
            if lines:
                prev_hash = json.loads(lines[-1]).get('manifest_sha256')
        except Exception as e:
            log_exception('prospective_chain.read', e)
            prev_hash = None
    portfolio_records = portfolio.to_dict(orient='records')
    manifest = {'schema': 'chispazo-v248-prospective-v1', 'evidence_class': 'prospective_preregistered', 'registered_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'target': int(target), 'expected_last': int(audit.max_concurso), 'history_rows': int(audit.rows), 'history_sha256': _sha256_file_v244(history_path), 'script_sha256': sha256_code_path_v248(script_path), 'ranking_sha256': _sha256_file_v244(ranking_path), 'lines': int(args.lines), 'seed': int(args.seed), 'ltr_seeds': int(args.v243_ltr_seeds), 'ltr_topk': int(args.v243_ltr_topk), 'production_weights': production_weights, 'production_allocation': production_allocation, 'portfolio': portfolio_records, 'historical_statistical_report_sha256': _canonical_sha_v244(statistical_report), 'previous_manifest_sha256': prev_hash, 'note': 'Local cryptographic preregistration. Tampering is detectable if this hash is preserved externally; local files alone are not an independent timestamp.'}
    manifest['manifest_sha256'] = _canonical_sha_v244(manifest)
    out = registry_dir / f'target_{int(target)}_V248_preregister.json'
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    with chain_path.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps({'target': int(target), 'registered_utc': manifest['registered_utc'], 'manifest_sha256': manifest['manifest_sha256'], 'previous_manifest_sha256': prev_hash, 'file': out.name}, ensure_ascii=False) + '\n')
    return out

def evaluate_prospective_registration_v244(registration_path: Path, realized_result: str, record_result: bool=True) -> Dict[str, object]:
    """
    Evalúa sólo el portafolio que quedó registrado antes del sorteo.
    Si el hash es válido, actualiza un ledger prospectivo acumulativo.
    """
    reg = json.loads(registration_path.read_text(encoding='utf-8'))
    saved_hash = reg.get('manifest_sha256')
    check = dict(reg)
    check.pop('manifest_sha256', None)
    recomputed = _canonical_sha_v244(check)
    vals = tuple(sorted((int(x.strip()) for x in realized_result.replace('-', ',').split(',') if x.strip())))
    combo = '-'.join((f'{x:02d}' for x in vals))
    pcombos = [str(r.get('combo')) for r in reg.get('portfolio', [])]
    captured = combo in pcombos
    pos = pcombos.index(combo) + 1 if captured else None
    valid = bool(saved_hash == recomputed)
    result = {'registration': str(registration_path), 'target': reg.get('target'), 'manifest_hash_valid': valid, 'manifest_sha256': saved_hash, 'realized': combo, 'captured_5of5': bool(captured), 'portfolio_position': pos, 'lines': int(reg.get('lines', len(pcombos))), 'single_trial_random_probability': float(reg.get('lines', len(pcombos)) / UNIVERSE_SIZE), 'evaluated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    if record_result and valid:
        ledger_path = registration_path.parent / 'v248_prospective_results.jsonl'
        prior = []
        if ledger_path.exists():
            for line in ledger_path.read_text(encoding='utf-8').splitlines():
                if not line.strip():
                    continue
                try:
                    prior.append(json.loads(line))
                except Exception as e:
                    log_exception('suppressed operation', e)
        entry = {'target': int(reg.get('target')), 'manifest_sha256': saved_hash, 'lines': int(reg.get('lines', len(pcombos))), 'realized': combo, 'captured_5of5': bool(captured), 'portfolio_position': pos, 'evaluated_utc': result['evaluated_utc']}
        by_hash = {str(x.get('manifest_sha256')): x for x in prior if x.get('manifest_sha256')}
        by_hash[str(saved_hash)] = entry
        ordered = sorted(by_hash.values(), key=lambda x: int(x.get('target', 0)))
        ledger_path.write_text(''.join((json.dumps(x, ensure_ascii=False) + '\n' for x in ordered)), encoding='utf-8')
        same = [x for x in ordered if int(x.get('lines', 0)) == int(entry['lines'])]
        n = len(same)
        k = int(sum((bool(x.get('captured_5of5')) for x in same)))
        cumulative = exact5_binomial_evidence_v244(n, k, int(entry['lines']))
        cumulative.update({'evidence_class': 'prospective_preregistered_confirmatory', 'ledger': str(ledger_path), 'targets_first_last': [int(same[0]['target']) if same else None, int(same[-1]['target']) if same else None]})
        result['cumulative_prospective_evidence'] = cumulative
    return result

def _paired_rank_evidence_v241(meta_rows: pd.DataFrame, strategy: str, baseline: str='heuristic', min_history: int=60, bootstrap_samples: int=500, seed: int=DEFAULT_SEED) -> Dict[str, float]:
    """
    Evidencia causal OOS pareada:
      delta_pct > 0  => strategy colocó al ganador más arriba que baseline.
    Sólo usa targets ya resueltos contenidos en meta_rows.
    """
    empty = {'n': 0, 'mean_delta_pct': 0.0, 'median_delta_pct': 0.0, 'p_better': 0.5, 'positive_rate': 0.0, 'w50': 0.0, 'w100': 0.0, 'w200': 0.0, 'stability_penalty': 0.0, 'edge_score': 0.0}
    if meta_rows is None or meta_rows.empty:
        return empty
    d = meta_rows[meta_rows['strategy'].isin([baseline, strategy])][['target', 'strategy', 'exact_rank']].copy()
    if d.empty or strategy not in set(d['strategy'].astype(str)) or baseline not in set(d['strategy'].astype(str)):
        return empty
    p = d.pivot_table(index='target', columns='strategy', values='exact_rank', aggfunc='last').dropna()
    if baseline not in p.columns or strategy not in p.columns or len(p) < min_history:
        out = dict(empty)
        out['n'] = int(len(p))
        return out
    delta = 100.0 * (p[baseline].to_numpy(float) - p[strategy].to_numpy(float)) / float(UNIVERSE_SIZE)
    n = len(delta)

    def recent_mean(w):
        x = delta[-min(w, n):]
        return float(np.mean(x)) if len(x) else 0.0
    w50, w100, w200 = (recent_mean(50), recent_mean(100), recent_mean(200))
    weighted = 0.5 * w50 + 0.3 * w100 + 0.2 * w200
    stability = float(np.std([w50, w100, w200]))
    recent = delta[-min(300, n):]
    rng = np.random.default_rng(seed + sum(map(ord, strategy)))
    if len(recent) >= 2:
        idx = rng.integers(0, len(recent), size=(max(100, int(bootstrap_samples)), len(recent)))
        means = recent[idx].mean(axis=1)
        p_better = float(np.mean(means > 0.0))
    else:
        p_better = 0.5
    positive_rate = float(np.mean(recent > 0.0))
    edge_score = float(weighted - 0.6 * stability)
    return {'n': int(n), 'mean_delta_pct': float(np.mean(recent)), 'median_delta_pct': float(np.median(recent)), 'p_better': p_better, 'positive_rate': positive_rate, 'w50': w50, 'w100': w100, 'w200': w200, 'stability_penalty': stability, 'edge_score': edge_score}

def select_rank_fusion_weights_v241(meta_rows: pd.DataFrame, min_history: int=60, bootstrap_samples: int=500, min_p_better: float=0.6, min_edge_pct: float=0.25, seed: int=DEFAULT_SEED) -> Tuple[Dict[str, float], Dict[str, Dict[str, float]], str]:
    """
    Fusión conservadora:
      - heuristic siempre tiene soporte base.
      - cada challenger recibe peso sólo si mejora rank OOS pareado.
      - number_transition / number_ml tienen umbral normal.
      - señales individuales y v235_full exigen algo más de evidencia.
    """
    evidence = {}
    raw = {'heuristic': 1.0}
    for st in V241_FUSION_STRATEGIES:
        if st == 'heuristic':
            continue
        ev = _paired_rank_evidence_v241(meta_rows, st, 'heuristic', min_history=min_history, bootstrap_samples=bootstrap_samples, seed=seed)
        evidence[st] = ev
        p_floor = min_p_better
        edge_floor = min_edge_pct
        if st in {'number_freq', 'number_markov', 'number_knn', 'v235_full'}:
            p_floor += 0.05
            edge_floor += 0.1
        if st == 'number_transition_affinity':
            p_floor += 0.02
        stable_windows = sum((x > 0 for x in [ev['w50'], ev['w100'], ev['w200']]))
        eligible = ev['n'] >= min_history and ev['p_better'] >= p_floor and (ev['edge_score'] >= edge_floor) and (ev['positive_rate'] >= 0.48) and (stable_windows >= 2)
        if not eligible:
            continue
        certainty = max(0.0, min(1.0, (ev['p_better'] - 0.5) * 2.0))
        magnitude = max(0.0, min(3.0, ev['edge_score']))
        raw[st] = float(min(2.25, 0.35 + 0.65 * certainty + 0.35 * magnitude))
    total = float(sum(raw.values()))
    weights = {k: float(v / total) for k, v in raw.items()}
    if len(weights) == 1:
        state = 'heuristic_only'
    elif len(weights) == 2:
        state = 'single_challenger_fusion'
    else:
        state = 'multi_specialist_fusion'
    evidence['heuristic'] = {'n': int(meta_rows['target'].nunique()) if meta_rows is not None and (not meta_rows.empty) else 0, 'mean_delta_pct': 0.0, 'median_delta_pct': 0.0, 'p_better': 0.5, 'positive_rate': 0.5, 'w50': 0.0, 'w100': 0.0, 'w200': 0.0, 'stability_penalty': 0.0, 'edge_score': 0.0}
    return (weights, evidence, state)

def rank_fuse_scores_v241(strategy_scores: Dict[str, np.ndarray], weights: Dict[str, float]) -> np.ndarray:
    """
    Fusión por rangos, no por probabilidades internas.
    Evita que una estrategia domine por tener una escala de score más agresiva.
    La transformación log-rank enfatiza Top30/Top100 sin ignorar el resto.
    """
    fused = np.zeros(UNIVERSE_SIZE, dtype=np.float64)
    used = 0.0
    denom = math.log1p(UNIVERSE_SIZE)
    for st, w in weights.items():
        if w <= 0 or st not in strategy_scores:
            continue
        sc = np.asarray(strategy_scores[st], dtype=float)
        order = np.argsort(-sc, kind='stable')
        ranks = np.empty(UNIVERSE_SIZE, dtype=np.int32)
        ranks[order] = np.arange(1, UNIVERSE_SIZE + 1, dtype=np.int32)
        strength = 1.0 - np.log1p(ranks.astype(np.float64) - 1.0) / denom
        fused += float(w) * strength
        used += float(w)
    if used <= 0:
        return np.asarray(strategy_scores['heuristic'], dtype=float)
    return safe_z(fused / used)
V242_PORTFOLIO_STRATEGIES = V241_FUSION_STRATEGIES + ('v241_fusion',)

def _portfolio_rank_frame_v242(meta_rows: pd.DataFrame, fusion_decisions: pd.DataFrame) -> pd.DataFrame:
    """Targets x strategies con exact-rank OOS observado."""
    chunks = []
    if meta_rows is not None and (not meta_rows.empty):
        a = meta_rows[['target', 'strategy', 'exact_rank']].copy()
        a = a[a['strategy'].isin(V241_FUSION_STRATEGIES)]
        chunks.append(a)
    if fusion_decisions is not None and (not fusion_decisions.empty):
        b = fusion_decisions[['target', 'exact_rank']].copy()
        b['strategy'] = 'v241_fusion'
        chunks.append(b[['target', 'strategy', 'exact_rank']])
    if not chunks:
        return pd.DataFrame()
    d = pd.concat(chunks, ignore_index=True)
    return d.pivot_table(index='target', columns='strategy', values='exact_rank', aggfunc='last').sort_index()

def _allocation_row_utility_v242(R: np.ndarray, alloc: np.ndarray) -> np.ndarray:
    """
    Utilidad suave centrada en Top30.
    ratio=1 significa que el ganador cayó dentro de la profundidad asignada
    de al menos un especialista. Escalas 3x/10x/50x reducen sparsity sin
    convertir un rank lejano en un supuesto acierto.
    """
    active = alloc > 0
    if not np.any(active):
        return np.zeros(R.shape[0], dtype=float)
    denom = np.maximum(1.0, alloc[active].astype(float))
    ratio = np.min(R[:, active] / denom[None, :], axis=1)
    exact = (ratio <= 1.0).astype(float)
    near3 = (ratio <= 3.0).astype(float)
    near10 = (ratio <= 10.0).astype(float)
    near50 = (ratio <= 50.0).astype(float)
    smooth = 1.0 / (1.0 + np.log1p(np.maximum(0.0, ratio)))
    return 15.0 * exact + 6.0 * near3 + 2.0 * near10 + 0.6 * near50 + 0.4 * smooth

def _allocation_metrics_v242(R: np.ndarray, alloc: np.ndarray, recency_weights: Optional[np.ndarray]=None) -> Dict[str, float]:
    if len(R) == 0:
        return {'utility': -1000000000.0, 'exact_rate': 0.0, 'near3_rate': 0.0, 'near10_rate': 0.0, 'near50_rate': 0.0, 'mean_scaled_ratio': float('inf')}
    active = alloc > 0
    if not np.any(active):
        return {'utility': -1000000000.0, 'exact_rate': 0.0, 'near3_rate': 0.0, 'near10_rate': 0.0, 'near50_rate': 0.0, 'mean_scaled_ratio': float('inf')}
    denom = np.maximum(1.0, alloc[active].astype(float))
    ratio = np.min(R[:, active] / denom[None, :], axis=1)
    u = _allocation_row_utility_v242(R, alloc)
    if recency_weights is None:
        w = np.ones(len(R), dtype=float)
    else:
        w = np.asarray(recency_weights, dtype=float)
    w = w / max(1e-12, float(w.sum()))
    return {'utility': float(np.sum(w * u)), 'exact_rate': float(np.sum(w * (ratio <= 1.0))), 'near3_rate': float(np.sum(w * (ratio <= 3.0))), 'near10_rate': float(np.sum(w * (ratio <= 10.0))), 'near50_rate': float(np.sum(w * (ratio <= 50.0))), 'mean_scaled_ratio': float(np.sum(w * ratio))}

def _recency_weights_v242(n: int, half_life: float=90.0) -> np.ndarray:
    if n <= 0:
        return np.empty(0, dtype=float)
    age = np.arange(n - 1, -1, -1, dtype=float)
    return np.power(0.5, age / max(10.0, float(half_life)))

def optimize_top30_allocation_v242(rank_frame: pd.DataFrame, budget: int=30, min_history: int=80, lookback: int=300, beam_width: int=72, half_life: float=90.0, seed: int=DEFAULT_SEED) -> Tuple[Dict[str, int], Dict[str, object]]:
    """
    Optimiza directamente cómo repartir las 30 líneas entre especialistas.

    Anti-overfit:
      1) usa sólo outcomes OOS pasados;
      2) limita a lookback reciente;
      3) genera candidatos en tramo train antiguo;
      4) selecciona entre esos candidatos en tramo calibration más reciente.
    """
    baseline = {st: 0 for st in V242_PORTFOLIO_STRATEGIES}
    baseline['v241_fusion'] = int(budget)
    if rank_frame is None or rank_frame.empty:
        return (baseline, {'state': 'cold_start', 'n': 0})
    cols = [st for st in V242_PORTFOLIO_STRATEGIES if st in rank_frame.columns]
    d = rank_frame[cols].dropna().tail(max(min_history, int(lookback))).copy()
    if len(d) < min_history or 'v241_fusion' not in cols:
        return (baseline, {'state': 'cold_start', 'n': int(len(d))})
    R = d.to_numpy(dtype=float)
    n, m = R.shape
    split = max(min_history // 2, int(round(n * 0.65)))
    split = min(max(20, split), n - 15)
    if split <= 10 or n - split < 10:
        return (baseline, {'state': 'insufficient_calibration', 'n': int(n)})
    Rtr, Rva = (R[:split], R[split:])
    wtr = _recency_weights_v242(len(Rtr), half_life)
    wva = _recency_weights_v242(len(Rva), max(30.0, half_life * 0.65))

    def score_train(a):
        mt = _allocation_metrics_v242(Rtr, a, wtr)
        concentration = float(np.sum((a / max(1, budget)) ** 2))
        active = int(np.sum(a > 0))
        return mt['utility'] - 0.06 * concentration - 0.004 * max(0, active - 5)
    zero = tuple([0] * m)
    beam = {zero: 0.0}
    for _ in range(int(budget)):
        nxt = {}
        for alloc_t in beam:
            a0 = np.asarray(alloc_t, dtype=np.int16)
            for j in range(m):
                a = a0.copy()
                a[j] += 1
                cap = budget if cols[j] in {'v241_fusion', 'heuristic'} else min(20, budget)
                if a[j] > cap:
                    continue
                key = tuple(map(int, a))
                if key not in nxt:
                    nxt[key] = score_train(a)
        if not nxt:
            break
        best = sorted(nxt.items(), key=lambda kv: kv[1], reverse=True)[:max(12, int(beam_width))]
        beam = dict(best)
    anchors = []
    for st in ['v241_fusion', 'heuristic']:
        if st in cols:
            a = np.zeros(m, dtype=np.int16)
            a[cols.index(st)] = budget
            anchors.append(tuple(map(int, a)))
    candidates = list(beam.keys()) + anchors
    uniq = list(dict.fromkeys(candidates))
    rows = []
    for at in uniq:
        a = np.asarray(at, dtype=np.int16)
        mt = _allocation_metrics_v242(Rtr, a, wtr)
        mv = _allocation_metrics_v242(Rva, a, wva)
        gap = abs(mv['utility'] - mt['utility'])
        exact_bonus = 4.0 * mv['exact_rate']
        final = mv['utility'] + exact_bonus - 0.2 * gap
        rows.append((final, at, mt, mv))
    rows.sort(key=lambda x: x[0], reverse=True)
    best_score, best_t, mt, mv = rows[0]
    best_a = np.asarray(best_t, dtype=np.int16)
    allocation = {st: int(best_a[j]) for j, st in enumerate(cols) if best_a[j] > 0}
    b = np.zeros(m, dtype=np.int16)
    b[cols.index('v241_fusion')] = budget
    bmv = _allocation_metrics_v242(Rva, b, wva)
    detail = {'state': 'nested_causal_allocation', 'n': int(n), 'train_n': int(len(Rtr)), 'calibration_n': int(len(Rva)), 'strategies': cols, 'allocation': allocation, 'train_metrics': mt, 'calibration_metrics': mv, 'fusion30_calibration_metrics': bmv, 'calibration_utility_delta_vs_fusion30': float(mv['utility'] - bmv['utility']), 'beam_width': int(beam_width), 'lookback': int(lookback), 'half_life': float(half_life)}
    return (allocation, detail)

def build_causal_portfolio_v242(strategy_scores: Dict[str, np.ndarray], allocation: Dict[str, int], budget: int, fallback_score: np.ndarray) -> Tuple[pd.DataFrame, np.ndarray]:
    """
    Unión exacta de Top-K por especialista. Dedup no puede borrar una línea:
    si un ganador estaba en cualquier Top-K asignado, permanece en la unión.
    Las plazas liberadas por duplicados se rellenan con rank-fusion.
    """
    picked = {}
    for st, k in allocation.items():
        if k <= 0 or st not in strategy_scores:
            continue
        sc = np.asarray(strategy_scores[st], dtype=float)
        order = np.argsort(-sc, kind='stable')[:min(int(k), len(sc))]
        for pos, idx in enumerate(order, 1):
            norm_pos = pos / max(1, int(k))
            rec = picked.get(int(idx))
            if rec is None or norm_pos < rec['priority']:
                picked[int(idx)] = {'priority': float(norm_pos), 'source': st, 'source_rank': int(pos)}
    union = list(picked.keys())
    union.sort(key=lambda i: (picked[i]['priority'], -float(fallback_score[i])))
    if len(union) < budget:
        for idx in np.argsort(-fallback_score, kind='stable'):
            ii = int(idx)
            if ii not in picked:
                picked[ii] = {'priority': 9.0, 'source': 'v241_fusion_fill', 'source_rank': int(len(union) + 1)}
                union.append(ii)
                if len(union) >= budget:
                    break
    union = union[:budget]
    records = []
    for rank, idx in enumerate(union, 1):
        co = ALL_COMBOS[idx]
        rec = picked[idx]
        records.append({'portfolio_rank': rank, 'combo': combo_str(co), 'combo_index': idx, 'source': rec['source'], 'source_rank': rec['source_rank'], 'fusion_score': float(fallback_score[idx]), 'sum': int(COMBO_SUM[idx]), 'zone': f'{COMBO_ZONES[idx][0]}-{COMBO_ZONES[idx][1]}-{COMBO_ZONES[idx][2]}'})
    return (pd.DataFrame(records), np.asarray(union, dtype=np.int32))

def walkforward_validate_v248(df, master_cache, lines, backtest, train_examples, seed, retrain_every=10, validation_estimators=250, ranker_estimators=250, min_history=60, bootstrap_samples=500, min_p_better=0.6, min_edge_pct=0.25, optuna_trials=0, optuna_every=0, mirage_topk=100, mirage_memory=12, negatives_per_positive=120, allocation_lookback=300, allocation_beam=72, allocation_half_life=90.0, adv_per_source=32, adv_max_per_target=160, adv_memory=300, adv_sources=V245_ADV_SOURCES_DEFAULT, ltr_seeds=3, alpha=0.05, correction='holm', significance_lookback=300, ops=None, sampler_runtime: Optional[SamplerRuntime]=None, model_runtime: Optional[ModelRuntime]=None):
    """
    Dos niveles causales:
      A) V241 aprende pesos de rank-fusion sólo con outcomes anteriores.
      B) V242 aprende reparto de las 30 líneas sólo con ranks OOS anteriores.
    """
    if ops is None:
        ops = STRATEGY_REGISTRY['v248']
    start = max(250, len(df) - backtest)
    total = len(df) - start
    bundle = None
    trained_at = None
    meta_rows, fusion_decisions, portfolio_rows, ablation, mirage_bank = ([], [], [], [], [])
    adversarial_bank: Dict[int, Dict[str, np.ndarray]] = {}
    for pos, idx in enumerate(range(start, len(df)), 1):
        target_no = int(df.iloc[idx]['CONCURSO'])
        progress(f'V243 direct Top{lines} target {target_no}', done=pos, total=total)
        if bundle is None or (pos - 1) % max(1, retrain_every) == 0:
            ts = max(80, idx - train_examples)
            tune_now = int(optuna_trials) if int(optuna_trials) > 0 and (int(optuna_every) <= 1 or (pos - 1) // max(1, retrain_every) % max(1, int(optuna_every)) == 0) else 0
            bundle = train_bundle_v246(master_cache, ts, idx, seed + idx, validation_estimators, ranker_estimators, ltr_seeds=max(1, int(ltr_seeds)), ltr_topk=lines, mirage_bank=mirage_bank[-max(1, int(mirage_memory)):], adversarial_bank=adversarial_bank, adv_memory=adv_memory, optuna_trials=tune_now, negatives_per_positive=negatives_per_positive, sampler_runtime=sampler_runtime, model_runtime=model_runtime)
            trained_at = idx
        _, parts = ops.score_parts(df.iloc[:idx], bundle)
        specialist_scores = {st: strategy_score_v239(parts, st) for st in V241_FUSION_STRATEGIES}
        prior_meta = pd.DataFrame(meta_rows)
        prior_fdec = pd.DataFrame(fusion_decisions)
        fusion_weights, fusion_evidence, fusion_state = select_rank_fusion_weights_v244(prior_meta, min_history=min_history, bootstrap_samples=bootstrap_samples, min_p_better=min_p_better, min_edge_pct=min_edge_pct, seed=seed + idx, alpha=float(alpha), correction=str(correction), significance_lookback=int(significance_lookback))
        fused = ops.rank_fuse(specialist_scores, fusion_weights)
        all_scores = dict(specialist_scores)
        all_scores['v241_fusion'] = fused
        rank_frame = _portfolio_rank_frame_v242(prior_meta, prior_fdec)
        allocation, alloc_detail = optimize_top30_allocation_v242(rank_frame, budget=lines, min_history=max(min_history, 60), lookback=allocation_lookback, beam_width=allocation_beam, half_life=allocation_half_life, seed=seed + idx)
        portfolio_df, portfolio_idx = ops.build_portfolio(all_scores, allocation, lines, fused)
        actual = combo_key(df.iloc[idx][R_COLS].to_numpy(dtype=int))
        ti = COMBO_TO_INDEX[actual]
        exact5 = int(ti in set(map(int, portfolio_idx.tolist())))
        bh = best_hit([tuple(map(int, ALL_COMBOS[j])) for j in portfolio_idx], actual)
        fusion_rank = exact_rank_from_scores(fused, ti)
        portfolio_rows.append({'target': target_no, 'strategy': 'v248_clean_core_exact5_top30_portfolio', 'allocation_state': alloc_detail.get('state'), 'allocation_json': json.dumps(allocation, sort_keys=True), 'exact_rank': int(fusion_rank), 'best_hit': int(bh), 'exact5': exact5, 'ge4': int(bh >= 4), 'ge3': int(bh >= 3), 'trained_at': trained_at})
        fusion_decisions.append({'target': target_no, 'strategy': 'v241_fusion', 'fusion_state': fusion_state, 'weights_json': json.dumps(fusion_weights, sort_keys=True), 'exact_rank': int(fusion_rank), 'best_hit': int(best_hit([tuple(map(int, ALL_COMBOS[j])) for j in rank_order_v248(fused, specialist_scores.get(V248_RESIDUAL_STRATEGY, specialist_scores.get('number_markov', fused)))[:lines]], actual)), 'exact5': int(fusion_rank <= lines), 'trained_at': trained_at})
        for st in V241_FUSION_STRATEGIES:
            sc = specialist_scores[st]
            r = exact_rank_from_scores(sc, ti)
            top = rank_order_v248(sc, specialist_scores.get(V248_RESIDUAL_STRATEGY, specialist_scores.get('number_markov', fused)))[:lines]
            sbh = best_hit([tuple(map(int, ALL_COMBOS[j])) for j in top], actual)
            row = {'target': target_no, 'strategy': st, 'exact_rank': int(r), 'best_hit': int(sbh), 'trained_at': trained_at}
            meta_rows.append(row)
            ablation.append(dict(row))
        try:
            binary_sc = strategy_score_v239(parts, 'binary')
            mir = mine_mirages_v240(df.iloc[:idx], binary_sc, actual, top_k=mirage_topk)
            mirage_bank.append(mir)
            mirage_bank = mirage_bank[-max(2, int(mirage_memory)):]
        except Exception as e:
            print(f'WARNING V248 mirage mining target {target_no}: {type(e).__name__}: {e}', file=sys.stderr)
        try:
            mining_scores = dict(specialist_scores)
            mining_scores['v241_fusion'] = fused
            if 'binary' in parts:
                mining_scores['binary'] = strategy_score_v239(parts, 'binary')
            adv = mine_adversarial_query_v245(df.iloc[:idx], actual, mining_scores, sources=tuple(adv_sources), per_source=adv_per_source, max_total=adv_max_per_target)
            adversarial_bank[int(idx)] = adv
            if adv_memory > 0 and len(adversarial_bank) > int(adv_memory):
                for old_idx in sorted(adversarial_bank)[:-int(adv_memory)]:
                    adversarial_bank.pop(old_idx, None)
        except Exception as e:
            if _progress_enabled():
                print(f'WARNING V245 adversarial mining target {target_no}: {e}', file=sys.stderr, flush=True)
        if pos == 1 or pos == total or pos % max(1, _progress_every()) == 0 or exact5 or (bh >= 4):
            print(f"    V243 alloc={allocation} state={alloc_detail.get('state')} -> exact5={exact5} best={bh}/5 fusion_rank={fusion_rank:,}", flush=True)
    md = pd.DataFrame(meta_rows)
    fdec = pd.DataFrame(fusion_decisions)
    pdec = pd.DataFrame(portfolio_rows)
    abl = pd.DataFrame(ablation)
    summary = validation_summary_from_rows_v235(pdec, lines)
    prod_bundle = train_bundle_v246(master_cache, max(80, len(df) - train_examples), len(df), seed, validation_estimators, ranker_estimators, ltr_seeds=max(1, int(ltr_seeds)), ltr_topk=lines, mirage_bank=mirage_bank[-max(1, int(mirage_memory)):], adversarial_bank=adversarial_bank, adv_memory=adv_memory, optuna_trials=int(optuna_trials), negatives_per_positive=negatives_per_positive, sampler_runtime=sampler_runtime, model_runtime=model_runtime)
    _, pp = ops.score_parts(df, prod_bundle)
    prod_specialist = {st: strategy_score_v239(pp, st) for st in V241_FUSION_STRATEGIES}
    prod_weights, prod_ev, prod_fstate = select_rank_fusion_weights_v244(md, min_history=min_history, bootstrap_samples=bootstrap_samples, min_p_better=min_p_better, min_edge_pct=min_edge_pct, seed=seed, alpha=float(alpha), correction=str(correction), significance_lookback=int(significance_lookback))
    prod_fused = ops.rank_fuse(prod_specialist, prod_weights)
    prod_scores = dict(prod_specialist)
    prod_scores['v241_fusion'] = prod_fused
    prod_rf = _portfolio_rank_frame_v242(md, fdec)
    prod_alloc, prod_alloc_detail = optimize_top30_allocation_v242(prod_rf, budget=lines, min_history=max(min_history, 60), lookback=allocation_lookback, beam_width=allocation_beam, half_life=allocation_half_life, seed=seed)
    prod_info = {'strategy': 'v248_clean_core_exact5_top30_portfolio', 'fusion_state': prod_fstate, 'fusion_weights': prod_weights, 'allocation': prod_alloc, 'allocation_detail': prod_alloc_detail, 'objective': 'causal OOS capture of exact winning combination with adversarial full-universe false-positive mining', 'v245_adversarial_bank_targets': int(len(adversarial_bank)), 'v245_adversarial_rows_last_bundle': int(prod_bundle.get('v245_adversarial_rows', 0)) if prod_bundle else 0}
    return (summary, pdec, fdec, abl, md, prod_bundle, prod_weights, prod_alloc, prod_info)

def frozen_ablation_v239(df, master_cache, lines, holdout, train_examples, seed, binary_estimators=250, ranker_estimators=250):
    """Frozen real: entrena y congela señales/ranking en cutoff; el holdout no actualiza features ni modelos."""
    if holdout <= 0 or holdout >= len(df) - 250:
        raise ValueError('Holdout inválido')
    cutoff = len(df) - holdout
    ts = max(80, cutoff - train_examples)
    progress(f'V239 frozen: entrenamiento causal {ts}..{cutoff - 1}; ranking congelado en cutoff')
    bundle = train_bundle_v239(master_cache, ts, cutoff, seed, binary_estimators, ranker_estimators, runtime=runtime)
    _, parts = score_parts_v239(df.iloc[:cutoff], bundle)
    rank_maps = {}
    top_pkgs = {}
    for st in V239_GATE_STRATEGIES:
        sc = strategy_score_v239(parts, st)
        order = np.argsort(-sc)
        ranks = np.empty_like(order)
        ranks[order] = np.arange(1, UNIVERSE_SIZE + 1)
        rank_maps[st] = ranks
        top = order[:min(lines, len(order))]
        top_pkgs[st] = [tuple(map(int, ALL_COMBOS[j])) for j in top]
    rows = []
    for pos, idx in enumerate(range(cutoff, len(df)), 1):
        if pos == 1 or pos == holdout or pos % max(1, _progress_every()) == 0:
            progress('V239 frozen ablation', done=pos, total=holdout)
        actual = combo_key(df.iloc[idx][R_COLS].to_numpy(dtype=int))
        ti = COMBO_TO_INDEX[actual]
        for st in V239_GATE_STRATEGIES:
            rnk = int(rank_maps[st][ti])
            bh = best_hit(top_pkgs[st], actual)
            rows.append({'target': int(df.iloc[idx]['CONCURSO']), 'strategy': st, 'exact_rank': rnk, 'best_hit': bh, 'exact5': int(rnk <= lines), 'ge4': int(bh >= 4), 'ge3': int(bh >= 3)})
    d = pd.DataFrame(rows)
    table = []
    for st in V239_GATE_STRATEGIES:
        m = _strategy_metrics_v236(d[d.strategy == st])
        table.append({**m, 'strategy': st})
    t = pd.DataFrame(table).sort_values(['rank_lift', 'top5000', 'ge4'], ascending=[False, False, False]).reset_index(drop=True)
    return (d, t)
V246_SAMPLER_ARMS = MappingProxyType({'balanced': (0.45, 0.35, 0.2), 'hard': (0.65, 0.25, 0.1), 'ultra': (0.85, 0.15, 0.0)})
V246_ARM_SEEDS = 2
V246_SAMPLER_NEGATIVES = 135

@dataclass
class SamplerRuntime:
    df: pd.DataFrame
    arms: Dict[str, Tuple[float, float, float]]
    arm_seeds: int
    negatives: int
    seed: int
    cache_path: Optional[Path] = None
    meta_path: Optional[Path] = None
    bank: Dict[int, Dict[str, object]] = None
    loaded: bool = False

    def __post_init__(self):
        if self.bank is None:
            self.bank = {}

    @property
    def arm_names(self) -> Tuple[str, ...]:
        return tuple(self.arms)

def _v246_parse_arms(spec: str) -> Dict[str, Tuple[float, float, float]]:
    """Parse 'balanced:0.45,0.35,0.20;hard:...' and enforce sum=1."""
    if not spec:
        return dict(V246_SAMPLER_ARMS)
    out = {}
    for chunk in str(spec).split(';'):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ':' not in chunk:
            raise ValueError(f'Brazo V246 inválido: {chunk}')
        name, vals = chunk.split(':', 1)
        p = tuple((float(x.strip()) for x in vals.split(',')))
        if len(p) != 3 or any((x < 0 for x in p)) or sum(p) <= 0:
            raise ValueError(f'Proporciones V246 inválidas para {name}: {p}')
        z = sum(p)
        p = tuple((x / z for x in p))
        out[name.strip()] = p
    if not out:
        raise ValueError('No quedaron brazos V248 válidos')
    if tuple(out) != V248_SAMPLER_ARM_NAMES:
        raise ValueError(f'Los brazos V248 deben ser exactamente {V248_SAMPLER_ARM_NAMES}; recibido {tuple(out)}')
    return out

def negative_indices_by_mix_v246(true_combo: Tuple[int, ...], n: int, rng: np.random.Generator, p4: float, p3: float, pglobal: float) -> np.ndarray:
    """Sampler explícito 4/5, 3/5 y global. Siempre devuelve n negativos únicos."""
    n = max(1, int(n))
    true = tuple(sorted(map(int, true_combo)))
    tset = set(true)
    outside = [x for x in NUMBERS if x not in tset]
    p = np.asarray([p4, p3, pglobal], dtype=float)
    p = np.maximum(p, 0.0)
    p /= max(1e-12, p.sum())
    counts = np.floor(p * n).astype(int)
    rem = n - int(counts.sum())
    frac = p * n - counts
    for j in np.argsort(-frac)[:rem]:
        counts[j] += 1
    n4, n3, ng = map(int, counts)
    pool4 = []
    for keep in itertools.combinations(true, 4):
        for x in outside:
            pool4.append(COMBO_TO_INDEX[tuple(sorted((*keep, x)))])
    pool4 = np.asarray(sorted(set(pool4)), dtype=np.int32)
    pool3 = []
    for keep in itertools.combinations(true, 3):
        for add in itertools.combinations(outside, 2):
            pool3.append(COMBO_TO_INDEX[tuple(sorted((*keep, *add)))])
    pool3 = np.asarray(sorted(set(pool3)), dtype=np.int32)
    chosen = []
    true_i = COMBO_TO_INDEX[true]
    take4 = min(n4, len(pool4))
    short4 = max(0, n4 - take4)
    n3_eff = n3 + short4
    take3 = min(n3_eff, len(pool3))
    short3 = max(0, n3_eff - take3)
    if take4:
        chosen.extend(rng.choice(pool4, size=take4, replace=False).tolist())
    if take3:
        chosen.extend(rng.choice(pool3, size=take3, replace=False).tolist())
    used = set(map(int, chosen))
    used.add(int(true_i))
    need = n - len(chosen)
    while need > 0:
        batch = rng.integers(0, UNIVERSE_SIZE, size=max(128, need * 6))
        for j in batch:
            jj = int(j)
            if jj in used:
                continue
            if len(tset & set(map(int, ALL_COMBOS[jj]))) > 2:
                continue
            chosen.append(jj)
            used.add(jj)
            need -= 1
            if need <= 0:
                break
    rng.shuffle(chosen)
    return np.asarray(chosen[:n], dtype=np.int32)

def _build_sampler_record_v246(runtime: SamplerRuntime, idx: int) -> Dict[str, object]:
    df = runtime.df
    true_combo = combo_key(df.iloc[idx][R_COLS].to_numpy(dtype=int))
    true_i = COMBO_TO_INDEX[true_combo]
    arm_candidates = {}
    for ai, (arm, mix) in enumerate(runtime.arms.items()):
        rng = np.random.default_rng(int(runtime.seed) + idx * 1009 + ai * 104729)
        neg = negative_indices_by_mix_v246(true_combo, runtime.negatives, rng, *mix)
        arm_candidates[arm] = np.concatenate(([true_i], neg)).astype(np.int32)
    union = []
    seen = set()
    for arm in runtime.arm_names:
        for j in arm_candidates[arm]:
            jj = int(j)
            if jj not in seen:
                seen.add(jj)
                union.append(jj)
    union = np.asarray(union, dtype=np.int32)
    X, _, _ = build_universe_features(df.iloc[:idx], candidate_mask=union)
    pos = {int(j): k for k, j in enumerate(union)}
    rows = {arm: np.asarray([pos[int(j)] for j in arm_candidates[arm]], dtype=np.int32) for arm in runtime.arm_names}
    return {'X': X.astype(np.float32, copy=False), 'cand_idx': union, 'arm_rows': rows, 'true_i': int(true_i)}

def _v246_sampler_signature(end_idx: int, runtime: SamplerRuntime) -> Dict[str, object]:
    return {'engine': 'V248_sampler_bank_v1', 'end_idx': int(end_idx), 'prefix_hash': _prefix_hash_v238(runtime.df, end_idx), 'seed': int(runtime.seed), 'negatives': int(runtime.negatives), 'arms': {k: list(map(float, v)) for k, v in runtime.arms.items()}, 'feature_names': list(FEATURE_NAMES)}

def _ensure_sampler_bank_v246(start_idx: int, end_idx: int, runtime: SamplerRuntime) -> Dict[int, Dict[str, object]]:
    if not runtime.loaded:
        runtime.loaded = True
        if JOBLIB_OK and runtime.cache_path and runtime.meta_path and runtime.cache_path.exists() and runtime.meta_path.exists():
            try:
                meta = json.loads(runtime.meta_path.read_text(encoding='utf-8'))
                old_end = int(meta.get('end_idx', 0))
                params_ok = int(meta.get('seed', -1)) == int(runtime.seed) and int(meta.get('negatives', -1)) == int(runtime.negatives) and (meta.get('arms') == {k: list(map(float, v)) for k, v in runtime.arms.items()})
                prefix_ok = old_end <= len(runtime.df) and meta.get('prefix_hash') == _prefix_hash_v238(runtime.df, old_end)
                if params_ok and prefix_ok:
                    runtime.bank = joblib.load(runtime.cache_path)
                    progress(f'V248 sampler cache HIT: {len(runtime.bank):,} targets')
            except Exception as e:
                progress(f'V248 sampler cache MISS: {type(e).__name__}: {e}')
    missing = [i for i in range(start_idx, end_idx) if i not in runtime.bank]
    if missing:
        progress(f'V248 sampler bank: construyendo {len(missing):,} targets | arms={runtime.arms}')
        for pos, idx in enumerate(missing, 1):
            if pos == 1 or pos == len(missing) or pos % max(1, _progress_every()) == 0:
                progress('V248 sampler cache causal', done=pos, total=len(missing))
            runtime.bank[idx] = _build_sampler_record_v246(runtime, idx)
        if JOBLIB_OK and runtime.cache_path and runtime.meta_path:
            runtime.cache_path.parent.mkdir(parents=True, exist_ok=True)
            _atomic_joblib_dump(runtime.bank, runtime.cache_path, compress=3)
            sig = _v246_sampler_signature(end_idx, runtime)
            tmp = runtime.meta_path.with_suffix(runtime.meta_path.suffix + '.tmp')
            tmp.write_text(json.dumps(sig, indent=2, ensure_ascii=False), encoding='utf-8')
            os.replace(tmp, runtime.meta_path)
    return runtime.bank

def stack_sampler_arm_queries_v246(bank, start_idx, end_idx, arm, adversarial_bank=None, adv_memory=300):
    keys = [i for i in range(start_idx, end_idx) if i in bank]
    if not keys:
        return (np.empty((0, len(FEATURE_NAMES)), np.float32), np.empty(0, np.float32), np.empty(0, np.int32), 0)
    adv = adversarial_bank or {}
    eligible = [k for k in sorted(adv) if start_idx <= int(k) < end_idx]
    if adv_memory > 0:
        eligible = eligible[-int(adv_memory):]
    eligible = set(map(int, eligible))
    Xs = []
    ys = []
    qids = []
    adv_rows = 0
    for q, idx in enumerate(keys):
        rec = bank[idx]
        rows = np.asarray(rec['arm_rows'][arm], dtype=np.int32)
        Xq = np.asarray(rec['X'], dtype=np.float32)[rows]
        ci = np.asarray(rec['cand_idx'], dtype=np.int32)[rows]
        true_i = int(rec['true_i'])
        yq = (ci == true_i).astype(np.float32)
        parts = [Xq]
        labels = [yq]
        nrow = len(Xq)
        if idx in eligible:
            ar = adv.get(idx) or {}
            Xa = ar.get('X')
            ia = ar.get('indices')
            if Xa is not None and ia is not None and (len(Xa) == len(ia)) and len(Xa):
                ia = np.asarray(ia, dtype=np.int32)
                Xa = np.asarray(Xa, dtype=np.float32)
                base = set(map(int, ci.tolist()))
                keep = np.asarray([int(j) not in base and int(j) != true_i for j in ia], dtype=bool)
                Xa = Xa[keep]
                if len(Xa):
                    parts.append(Xa)
                    labels.append(np.zeros(len(Xa), np.float32))
                    nrow += len(Xa)
                    adv_rows += len(Xa)
        Xq = np.vstack(parts) if len(parts) > 1 else parts[0]
        yq = np.concatenate(labels) if len(labels) > 1 else labels[0]
        if int(np.sum(yq > 0.5)) != 1:
            raise ValueError(f'V246 {arm} query {idx}: positivos != 1')
        Xs.append(Xq)
        ys.append(yq)
        qids.append(np.full(nrow, q, dtype=np.int32))
    return (np.vstack(Xs), np.concatenate(ys), np.concatenate(qids), int(adv_rows))

def train_bundle_v246(cache, start_idx: int, end_idx: int, seed: int, binary_estimators: int, ranker_estimators: int, ltr_seeds: int=3, ltr_topk: int=30, mirage_bank=None, adversarial_bank=None, adv_memory: int=300, optuna_trials: int=0, negatives_per_positive: int=120, sampler_runtime: Optional[SamplerRuntime]=None, model_runtime: Optional[ModelRuntime]=None):
    """V246 wrapper: V245 completo + tres sampler-arm rankers EXACT5."""
    bundle = train_bundle_v245(cache, start_idx, end_idx, seed, binary_estimators, ranker_estimators, ltr_seeds=ltr_seeds, ltr_topk=ltr_topk, mirage_bank=mirage_bank, adversarial_bank=adversarial_bank, adv_memory=adv_memory, optuna_trials=optuna_trials, negatives_per_positive=negatives_per_positive, runtime=model_runtime)
    if sampler_runtime is None:
        raise ValueError('V248 requires explicit SamplerRuntime')
    bank = _ensure_sampler_bank_v246(start_idx, end_idx, sampler_runtime)
    arm_meta = {}
    for ai, arm in enumerate(sampler_runtime.arm_names):
        X, y, qid, adv_rows = stack_sampler_arm_queries_v246(bank, start_idx, end_idx, arm, adversarial_bank, adv_memory)
        models = train_adversarial_exact5_ensemble_v245(X, y, qid, seed + 24600 + ai * 1709, ranker_estimators, n_seeds=sampler_runtime.arm_seeds, topk=ltr_topk, runtime=model_runtime) if len(X) else []
        bundle[f'v246_{arm}_rankers'] = models
        arm_meta[arm] = {'rows': int(len(X)), 'adv_rows': int(adv_rows), 'models': int(len(models)), 'mix': list(sampler_runtime.arms[arm])}
    bundle['v246_sampler_meta'] = arm_meta
    return bundle

def sampler_funnel_table_v246(meta_rows: Optional[pd.DataFrame], lines: int=30) -> pd.DataFrame:
    """Top30-centric diagnostics for every strategy; no selection uses current/future outcome."""
    cols = ['strategy', 'n', 'top30', 'top100', 'top500', 'top1000', 'top5000', 'mrr', 'mean_log_rank', 'avg_rank', 'median_rank', 'rank_lift_pct', 'ge4', 'ge3']
    if meta_rows is None or meta_rows.empty:
        return pd.DataFrame(columns=cols)
    out = []
    for st, g in meta_rows.groupby('strategy'):
        r = g['exact_rank'].to_numpy(float)
        n = len(r)
        bh = g['best_hit'].to_numpy(float) if 'best_hit' in g else np.zeros(n)
        out.append({'strategy': st, 'n': n, 'top30': float(np.mean(r <= lines)), 'top100': float(np.mean(r <= 100)), 'top500': float(np.mean(r <= 500)), 'top1000': float(np.mean(r <= 1000)), 'top5000': float(np.mean(r <= 5000)), 'mrr': float(np.mean(1.0 / np.maximum(1.0, r))), 'mean_log_rank': float(np.mean(np.log1p(r))), 'avg_rank': float(np.mean(r)), 'median_rank': float(np.median(r)), 'rank_lift_pct': float(rank_lift(float(np.mean(r)))), 'ge4': float(np.mean(bh >= 4)), 'ge3': float(np.mean(bh >= 3))})
    return pd.DataFrame(out, columns=cols).sort_values(['top30', 'top100', 'top500', 'rank_lift_pct'], ascending=[False, False, False, False]).reset_index(drop=True)

def configure_v246_runtime(args, df: pd.DataFrame, model_dir: Path) -> SamplerRuntime:
    arms = _v246_parse_arms(args.v246_sampler_arms)
    required = {'balanced', 'hard', 'ultra'}
    if set(arms) != required:
        raise ValueError(f'V248 requiere exactamente brazos {sorted(required)}; recibidos {tuple(arms)}')
    runtime = SamplerRuntime(df=df, arms=arms, arm_seeds=max(1, int(args.v246_arm_seeds)), negatives=max(30, int(args.v246_sampler_negatives)), seed=int(args.seed), cache_path=model_dir / 'v246_sampler_bank.joblib', meta_path=model_dir / 'v246_sampler_bank.json')
    progress(f'V248 curricula: negatives={runtime.negatives} arm_seeds={runtime.arm_seeds} arms={runtime.arms}')
    return runtime
V248_RESIDUAL_STRATEGY = 'markov_exact5_residual'
V248_STATE_SCHEMA = 1

def tie_rank_stats_v248(scores: np.ndarray, true_index: int, topk: int=30) -> Dict[str, float]:
    """Rank interval for exact ties + probability of entering Top-K under neutral tie breaking."""
    sc = np.asarray(scores, dtype=np.float64)
    true_score = float(sc[int(true_index)])
    better = int(np.sum(sc > true_score))
    tied = int(np.sum(sc == true_score))
    tied = max(1, tied)
    best_rank = better + 1
    worst_rank = better + tied
    mid_rank = 0.5 * (best_rank + worst_rank)
    slots = max(0, int(topk) - better)
    topk_prob = float(min(1.0, max(0.0, slots / tied)))
    return {'rank_best': int(best_rank), 'rank_worst': int(worst_rank), 'rank_mid': float(mid_rank), 'tie_size': int(tied), 'topk_tie_prob': topk_prob}

def tie_midrank_vector_v248(scores: np.ndarray) -> np.ndarray:
    """Average rank for exact ties without arbitrary combination-index ordering."""
    sc = np.asarray(scores, dtype=np.float64)
    vals, inv, counts = np.unique(sc, return_inverse=True, return_counts=True)
    counts_desc = counts[::-1].astype(np.float64)
    before = np.cumsum(counts_desc) - counts_desc
    mid_desc = before + (counts_desc + 1.0) / 2.0
    mid_asc = mid_desc[::-1]
    return mid_asc[inv]

def rank_strength_v248(scores: np.ndarray) -> np.ndarray:
    ranks = tie_midrank_vector_v248(scores)
    return 1.0 - np.log1p(ranks - 1.0) / math.log1p(UNIVERSE_SIZE)

def rank_order_v248(scores: np.ndarray, secondary: Optional[np.ndarray]=None) -> np.ndarray:
    """Deterministic score order; exact ties use causal secondary evidence, never combo index alone."""
    sc = np.asarray(scores, dtype=np.float64)
    idx = np.arange(len(sc), dtype=np.int32)
    if secondary is None:
        secondary = np.zeros(len(sc), dtype=np.float64)
    sec = np.asarray(secondary, dtype=np.float64)
    if len(sec) != len(sc):
        sec = np.zeros(len(sc), dtype=np.float64)
    return np.lexsort((idx, -sec, -sc)).astype(np.int32)

def score_parts_v248(hist_df: pd.DataFrame, bundle=None):
    """V248 extends V246 with a causal Markov→Exact5 rank-consensus challenger."""
    ctx, parts = score_parts_v239(hist_df, bundle)
    zeros = np.zeros(UNIVERSE_SIZE, dtype=float)
    markov = np.asarray(parts.get('number_markov', zeros), dtype=float)
    knn = np.asarray(parts.get('number_knn', zeros), dtype=float)
    affinity = np.asarray(parts.get('affinity', zeros), dtype=float)
    adv = np.asarray(parts.get('ltr_adv_exact5', zeros), dtype=float)
    hard = np.asarray(parts.get('ltr_exact5_hard', zeros), dtype=float)
    ultra = np.asarray(parts.get('ltr_exact5_ultra', zeros), dtype=float)
    ndcg = np.asarray(parts.get('ltr_ndcg_exact5', zeros), dtype=float)
    residual_inputs = {'number_markov': markov, 'ltr_adv_exact5': adv, 'ltr_exact5_hard': hard, 'ltr_exact5_ultra': ultra, 'ltr_ndcg_exact5': ndcg, 'number_knn': knn, 'affinity': affinity}
    residual = np.zeros(UNIVERSE_SIZE, dtype=np.float64)
    for name, weight in RESIDUAL_RANK_WEIGHTS.items():
        residual += float(weight) * rank_strength_v248(residual_inputs[name])
    parts[V248_RESIDUAL_STRATEGY] = safe_z(residual)
    return (ctx, parts)

def rank_fuse_scores_v248(strategy_scores: Dict[str, np.ndarray], weights: Dict[str, float]) -> np.ndarray:
    """V248 rank fusion: average ranks for ties, eliminating index-order tie artifacts."""
    fused = np.zeros(UNIVERSE_SIZE, dtype=np.float64)
    used = 0.0
    denom = math.log1p(UNIVERSE_SIZE)
    for st, w in weights.items():
        if w <= 0 or st not in strategy_scores:
            continue
        ranks = tie_midrank_vector_v248(np.asarray(strategy_scores[st], dtype=float))
        strength = 1.0 - np.log1p(ranks - 1.0) / denom
        fused += float(w) * strength
        used += float(w)
    if used <= 0:
        return np.asarray(strategy_scores['heuristic'], dtype=float)
    return safe_z(fused / used)

def build_causal_portfolio_v248(strategy_scores: Dict[str, np.ndarray], allocation: Dict[str, int], budget: int, fallback_score: np.ndarray) -> Tuple[pd.DataFrame, np.ndarray]:
    """V248 Top-N union with causal tie breaking instead of array-index tie breaking."""
    secondary = np.asarray(strategy_scores.get(V248_RESIDUAL_STRATEGY, strategy_scores.get('number_markov', fallback_score)), dtype=float)
    picked: Dict[int, Dict[str, object]] = {}
    for st, k in allocation.items():
        if k <= 0 or st not in strategy_scores:
            continue
        sc = np.asarray(strategy_scores[st], dtype=float)
        sec = secondary if st != V248_RESIDUAL_STRATEGY else np.asarray(fallback_score, dtype=float)
        order = rank_order_v248(sc, sec)[:min(int(k), len(sc))]
        for pos, idx in enumerate(order, 1):
            norm_pos = pos / max(1, int(k))
            rec = picked.get(int(idx))
            if rec is None or norm_pos < float(rec['priority']):
                picked[int(idx)] = {'priority': float(norm_pos), 'source': st, 'source_rank': int(pos)}
    union = list(picked.keys())
    union.sort(key=lambda i: (float(picked[i]['priority']), -float(fallback_score[i]), -float(secondary[i])))
    if len(union) < int(budget):
        for idx in rank_order_v248(fallback_score, secondary):
            ii = int(idx)
            if ii not in picked:
                picked[ii] = {'priority': 9.0, 'source': 'v241_fusion_fill', 'source_rank': int(len(union) + 1)}
                union.append(ii)
                if len(union) >= int(budget):
                    break
    union = union[:int(budget)]
    records = []
    for rank, idx in enumerate(union, 1):
        co = ALL_COMBOS[idx]
        rec = picked[idx]
        records.append({'portfolio_rank': rank, 'combo': combo_str(co), 'combo_index': idx, 'source': rec['source'], 'source_rank': rec['source_rank'], 'fusion_score': float(fallback_score[idx]), 'tie_break_score': float(secondary[idx]), 'sum': int(COMBO_SUM[idx]), 'zone': f'{COMBO_ZONES[idx][0]}-{COMBO_ZONES[idx][1]}-{COMBO_ZONES[idx][2]}'})
    return (pd.DataFrame(records), np.asarray(union, dtype=np.int32))

@dataclass(frozen=True)
class StrategyOps:
    """Explicit versioned behavior. No global function reassignment is allowed."""
    score_parts: Callable
    rank_fuse: Callable
    build_portfolio: Callable
STRATEGY_REGISTRY: Dict[str, StrategyOps] = {'v246': StrategyOps(score_parts=score_parts_v239, rank_fuse=rank_fuse_scores_v241, build_portfolio=build_causal_portfolio_v242), 'v248': StrategyOps(score_parts=score_parts_v248, rank_fuse=rank_fuse_scores_v248, build_portfolio=build_causal_portfolio_v248)}

def production_portfolio_v248(hist_df: pd.DataFrame, bundle, fusion_weights: Dict[str, float], allocation: Dict[str, int], lines: int, ops=None) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, object]]:
    """V248 production with explicit strategy operations and immutable snapshot payload."""
    if ops is None:
        ops = STRATEGY_REGISTRY['v248']
    ctx, parts = ops.score_parts(hist_df, bundle)
    specialists = {st: strategy_score_v239(parts, st) for st in V241_FUSION_STRATEGIES}
    fused = ops.rank_fuse(specialists, fusion_weights)
    scores = dict(specialists)
    scores['v241_fusion'] = fused
    portfolio, portfolio_idx = ops.build_portfolio(scores, allocation, lines, fused)
    secondary = specialists.get(V248_RESIDUAL_STRATEGY, specialists.get('number_markov', fused))
    order = rank_order_v248(fused, secondary)
    ranks = np.empty(len(order), dtype=np.int32)
    ranks[order] = np.arange(1, len(order) + 1, dtype=np.int32)
    ranking = pd.DataFrame({'rank': ranks, 'combo': [combo_str(c) for c in ALL_COMBOS], 'score': fused, 'score_heuristic': specialists['heuristic'], 'score_markov_exact5_residual': specialists.get(V248_RESIDUAL_STRATEGY, np.zeros(UNIVERSE_SIZE)), 'score_ltr_ndcg_exact5': specialists['ltr_ndcg_exact5'], 'score_ltr_adv_exact5': specialists.get('ltr_adv_exact5', np.zeros(UNIVERSE_SIZE)), 'score_ltr_exact5_balanced': specialists.get('ltr_exact5_balanced', np.zeros(UNIVERSE_SIZE)), 'score_ltr_exact5_hard': specialists.get('ltr_exact5_hard', np.zeros(UNIVERSE_SIZE)), 'score_ltr_exact5_ultra': specialists.get('ltr_exact5_ultra', np.zeros(UNIVERSE_SIZE)), 'score_number_markov': specialists['number_markov'], 'score_number_knn': specialists['number_knn'], 'score_number_transition': specialists['number_transition'], 'sum': COMBO_SUM, 'zone': [f'{a}-{b}-{c}' for a, b, c in COMBO_ZONES], 'overlap_last': np.sum(np.isin(ALL_COMBOS, np.array(ctx.last_combo)), axis=1)}).sort_values('rank').reset_index(drop=True)
    snapshot_payload = {'specialist_scores': {k: np.asarray(v, dtype=np.float32) for k, v in specialists.items()}, 'fused': np.asarray(fused, dtype=np.float32), 'portfolio_idx': np.asarray(portfolio_idx, dtype=np.int32), 'portfolio': portfolio.copy(), 'fusion_weights': dict(fusion_weights), 'allocation': dict(allocation)}
    return (portfolio, ranking, snapshot_payload)

def realized_forensic_v248(df: pd.DataFrame, bundle, fusion_weights: Dict[str, float], allocation: Dict[str, int], realized, lines: int, ops=None) -> Dict[str, object]:
    ops = ops or STRATEGY_REGISTRY['v248']
    _, parts = ops.score_parts(df, bundle)
    specialists = {st: strategy_score_v239(parts, st) for st in V241_FUSION_STRATEGIES}
    fused = ops.rank_fuse(specialists, fusion_weights)
    scores = dict(specialists)
    scores['v241_fusion'] = fused
    portfolio, pidx = ops.build_portfolio(scores, allocation, lines, fused)
    ti = COMBO_TO_INDEX[realized]
    fstats = tie_rank_stats_v248(fused, ti, lines)
    return {'realized': combo_str(realized), 'captured_5of5_in_v248_portfolio': bool(ti in set(map(int, pidx.tolist()))), 'v248_fusion_tie_rank': fstats, 'best_hit_top_lines': int(best_hit([tuple(map(int, ALL_COMBOS[j])) for j in pidx], realized)), 'allocation': allocation, 'fusion_weights': fusion_weights, 'strategy_tie_ranks': {st: tie_rank_stats_v248(sc, ti, lines) for st, sc in scores.items()}}
_sampler_funnel_table_v246_base = sampler_funnel_table_v246

def sampler_funnel_table_v248(meta_rows: Optional[pd.DataFrame], lines: int=30) -> pd.DataFrame:
    base = _sampler_funnel_table_v246_base(meta_rows, lines)
    if meta_rows is None or meta_rows.empty or base.empty:
        return base
    extra = []
    for st, g in meta_rows.groupby('strategy'):
        rec = {'strategy': st}
        if 'tie_size' in g.columns:
            x = pd.to_numeric(g['tie_size'], errors='coerce').dropna()
            rec['avg_tie_size'] = float(x.mean()) if len(x) else float('nan')
            rec['tie_free_rate'] = float(np.mean(x <= 1.0)) if len(x) else float('nan')
        if 'top30_tie_prob' in g.columns:
            x = pd.to_numeric(g['top30_tie_prob'], errors='coerce').dropna()
            rec['mean_top30_tie_prob'] = float(x.mean()) if len(x) else float('nan')
        extra.append(rec)
    if extra:
        base = base.merge(pd.DataFrame(extra), on='strategy', how='left')
    return base

def _v248_state_path(state_dir: Path) -> Path:
    return state_dir / 'v248_oos_state.joblib'

def _v248_snapshot_path(state_dir: Path, target: int) -> Path:
    return state_dir / 'snapshots' / f'target_{int(target)}.joblib'

def load_v248_state(state_dir: Path) -> Optional[Dict[str, object]]:
    sp = _v248_state_path(state_dir)
    if not (JOBLIB_OK and sp.exists()):
        return None
    try:
        st = joblib.load(sp)
        if int(st.get('schema', -1)) != V248_STATE_SCHEMA:
            return None
        return st
    except Exception as e:
        progress(f'V248 state MISS: {type(e).__name__}: {e}')
        return None

def save_v248_state(state_dir: Path, state: Dict[str, object]) -> None:
    if not JOBLIB_OK:
        return
    state_dir.mkdir(parents=True, exist_ok=True)
    state['schema'] = V248_STATE_SCHEMA
    state['updated_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
    _atomic_joblib_dump(state, _v248_state_path(state_dir), compress=3)

def import_v246_state_v248(v246_dir: Path) -> Optional[Dict[str, object]]:
    """Seeds V248 with the already-paid V246 OOS evidence; no retrospective residual claims are invented."""
    if not v246_dir.exists():
        return None
    files = {'wf_detail': v246_dir / 'v246_walkforward_topn_portfolio.csv', 'fusion_detail': v246_dir / 'v246_walkforward_rank_fusion.csv', 'wf_ablation': v246_dir / 'v246_walkforward_ablation.csv', 'meta_rows': v246_dir / 'v246_meta_training_rows.csv'}
    if not all((x.exists() for x in files.values())):
        return None
    st = {'schema': V248_STATE_SCHEMA, 'origin': str(v246_dir), 'evaluated_targets': []}
    for k, fp in files.items():
        st[k] = pd.read_csv(fp)
    tg = st['wf_detail'].get('target') if isinstance(st['wf_detail'], pd.DataFrame) else None
    if tg is not None and len(tg):
        st['evaluated_targets'] = sorted(set(map(int, tg.dropna().astype(int).tolist())))
    progress(f"V248 imported V246 OOS state: {len(st['evaluated_targets'])} targets; residual challenger starts prospectively")
    return st

def seed_v248_shared_cache_from_v246(v246_model_dir: Optional[Path], shared_dir: Path, df: pd.DataFrame, negatives: int, seed: int, hard_ratio: float) -> None:
    if not JOBLIB_OK or v246_model_dir is None:
        return
    src = v246_model_dir / 'v246_master_causal_cache.joblib'
    dst = shared_dir / 'master_cache_shared.joblib'
    meta = shared_dir / 'master_cache_shared.json'
    if dst.exists() and meta.exists() or not src.exists():
        return
    try:
        cache = joblib.load(src)
        if not cache:
            return
        old_end = min(len(df), max(map(int, cache.keys())) + 1)
        shared_dir.mkdir(parents=True, exist_ok=True)
        _atomic_joblib_dump(cache, dst, compress=3)
        m = {'start_idx': min(map(int, cache.keys())), 'end_idx': old_end, 'negatives': int(negatives), 'seed': int(seed), 'hard_ratio': float(hard_ratio), 'prefix_hash': _prefix_hash_v238(df, old_end), 'updated_at': time.strftime('%Y-%m-%d %H:%M:%S'), 'targets': len(cache), 'imported_from': str(src)}
        meta.write_text(json.dumps(m, indent=2), encoding='utf-8')
        progress(f'V248 shared master cache seeded from V246: {len(cache):,} targets')
    except Exception as e:
        progress(f'V248 cache import skipped: {type(e).__name__}: {e}')

def seed_v248_sampler_cache_from_v246(v246_model_dir: Optional[Path], model_dir: Path) -> None:
    if not JOBLIB_OK or v246_model_dir is None:
        return
    for name in ('v246_sampler_bank.joblib', 'v246_sampler_bank.json'):
        src = v246_model_dir / name
        dst = model_dir / name
        if src.exists() and (not dst.exists()):
            try:
                model_dir.mkdir(parents=True, exist_ok=True)
                if src.suffix == '.joblib':
                    _atomic_joblib_dump(joblib.load(src), dst, compress=3)
                else:
                    dst.write_bytes(src.read_bytes())
                progress(f'V248 sampler cache imported: {name}')
            except Exception as e:
                progress(f'V248 sampler import skipped {name}: {type(e).__name__}: {e}')

def consume_previous_snapshot_v248(df: pd.DataFrame, audit: AuditResult, state_dir: Path, state: Dict[str, object], lines: int) -> bool:
    """Evaluate exactly one previously preregistered target after its result becomes known."""
    prev_target = int(audit.max_concurso)
    evaluated = set(map(int, state.get('evaluated_targets', [])))
    if prev_target in evaluated:
        return False
    sp = _v248_snapshot_path(state_dir, prev_target)
    if not (JOBLIB_OK and sp.exists()):
        progress(f'V248 incremental: no snapshot for resolved target {prev_target}; nothing to append')
        return False
    snap = joblib.load(sp)
    if int(snap.get('target', -1)) != prev_target or int(snap.get('history_last', -1)) != prev_target - 1:
        raise RuntimeError('V248 snapshot guardrail failed: target/history_last mismatch')
    manifest = {'schema': int(snap.get('schema', -1)), 'target': int(snap.get('target', -1)), 'history_last': int(snap.get('history_last', -1)), 'history_sha256': str(snap.get('history_sha256', '')), 'fusion_weights': snap.get('fusion_weights', {}), 'allocation': snap.get('allocation', {}), 'portfolio_idx': [int(x) for x in np.asarray(snap.get('portfolio_idx', []), dtype=int).tolist()], 'strategies': sorted(map(str, snap.get('specialist_scores', {}).keys()))}
    manifest_sha = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
    if str(snap.get('manifest_sha256', '')) != manifest_sha:
        raise RuntimeError('V248 snapshot guardrail failed: manifest SHA256 mismatch')
    rowdf = df[df['CONCURSO'] == prev_target]
    if len(rowdf) != 1:
        raise RuntimeError(f'V248 snapshot target {prev_target} not uniquely present in history')
    actual = combo_key(rowdf.iloc[0][R_COLS].to_numpy(dtype=int))
    ti = COMBO_TO_INDEX[actual]
    specialists = {k: np.asarray(v, dtype=float) for k, v in snap['specialist_scores'].items()}
    fused = np.asarray(snap['fused'], dtype=float)
    secondary = specialists.get(V248_RESIDUAL_STRATEGY, specialists.get('number_markov', fused))
    meta = state.get('meta_rows')
    meta = meta.copy() if isinstance(meta, pd.DataFrame) else pd.DataFrame()
    abl = state.get('wf_ablation')
    abl = abl.copy() if isinstance(abl, pd.DataFrame) else pd.DataFrame()
    new_meta = []
    for st, sc in specialists.items():
        ts = tie_rank_stats_v248(sc, ti, lines)
        top = rank_order_v248(sc, secondary)[:lines]
        bh = best_hit([tuple(map(int, ALL_COMBOS[j])) for j in top], actual)
        rec = {'target': prev_target, 'strategy': st, 'exact_rank': int(ts['rank_worst']), 'best_hit': int(bh), 'rank_best': int(ts['rank_best']), 'rank_mid': float(ts['rank_mid']), 'tie_size': int(ts['tie_size']), 'top30_tie_prob': float(ts['topk_tie_prob']), 'trained_at': int(snap.get('trained_at', -1))}
        new_meta.append(rec)
    if new_meta:
        meta = pd.concat([meta, pd.DataFrame(new_meta)], ignore_index=True)
        abl = pd.concat([abl, pd.DataFrame(new_meta)], ignore_index=True)
    fdec = state.get('fusion_detail')
    fdec = fdec.copy() if isinstance(fdec, pd.DataFrame) else pd.DataFrame()
    fts = tie_rank_stats_v248(fused, ti, lines)
    ftop = rank_order_v248(fused, secondary)[:lines]
    fbh = best_hit([tuple(map(int, ALL_COMBOS[j])) for j in ftop], actual)
    frow = {'target': prev_target, 'strategy': 'v241_fusion', 'fusion_state': snap.get('fusion_state', 'prospective'), 'weights_json': json.dumps(snap.get('fusion_weights', {}), sort_keys=True), 'exact_rank': int(fts['rank_worst']), 'best_hit': int(fbh), 'exact5': int(ti in set(map(int, ftop.tolist()))), 'rank_best': int(fts['rank_best']), 'rank_mid': float(fts['rank_mid']), 'tie_size': int(fts['tie_size']), 'top30_tie_prob': float(fts['topk_tie_prob']), 'trained_at': int(snap.get('trained_at', -1))}
    fdec = pd.concat([fdec, pd.DataFrame([frow])], ignore_index=True)
    pdec = state.get('wf_detail')
    pdec = pdec.copy() if isinstance(pdec, pd.DataFrame) else pd.DataFrame()
    portfolio_idx = np.asarray(snap['portfolio_idx'], dtype=np.int32)
    bh = best_hit([tuple(map(int, ALL_COMBOS[j])) for j in portfolio_idx], actual)
    prow = {'target': prev_target, 'strategy': 'v248_prospective_incremental_portfolio', 'allocation_state': snap.get('allocation_state', 'prospective'), 'allocation_json': json.dumps(snap.get('allocation', {}), sort_keys=True), 'exact_rank': int(fts['rank_worst']), 'best_hit': int(bh), 'exact5': int(ti in set(map(int, portfolio_idx.tolist()))), 'ge4': int(bh >= 4), 'ge3': int(bh >= 3), 'rank_best': int(fts['rank_best']), 'rank_mid': float(fts['rank_mid']), 'tie_size': int(fts['tie_size']), 'top30_tie_prob': float(fts['topk_tie_prob']), 'trained_at': int(snap.get('trained_at', -1))}
    pdec = pd.concat([pdec, pd.DataFrame([prow])], ignore_index=True)
    state.update({'meta_rows': meta, 'wf_ablation': abl, 'fusion_detail': fdec, 'wf_detail': pdec})
    evaluated.add(prev_target)
    state['evaluated_targets'] = sorted(evaluated)
    state['last_incremental_result'] = {'target': prev_target, 'actual': combo_str(actual), 'portfolio_exact5': int(prow['exact5']), 'best_hit': int(bh)}
    progress(f"V248 incremental consumed target {prev_target}: exact5={prow['exact5']} best={bh}/5")
    return True

def production_policy_from_state_v248(state: Dict[str, object], args) -> Tuple[ValidationSummary, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, float], Dict[str, int], Dict[str, object]]:
    pdec = state.get('wf_detail')
    pdec = pdec.copy() if isinstance(pdec, pd.DataFrame) else pd.DataFrame()
    fdec = state.get('fusion_detail')
    fdec = fdec.copy() if isinstance(fdec, pd.DataFrame) else pd.DataFrame()
    abl = state.get('wf_ablation')
    abl = abl.copy() if isinstance(abl, pd.DataFrame) else pd.DataFrame()
    md = state.get('meta_rows')
    md = md.copy() if isinstance(md, pd.DataFrame) else pd.DataFrame()
    if pdec.empty:
        raise RuntimeError('V248 state has no OOS portfolio rows')
    if args.backtest > 0:
        targets = sorted(set(map(int, pdec['target'].dropna().astype(int).tolist())))[-int(args.backtest):]
        keep = set(targets)
        ppol = pdec[pdec['target'].astype(int).isin(keep)].copy()
        fpol = fdec[fdec['target'].astype(int).isin(keep)].copy() if not fdec.empty else fdec
        mpol = md[md['target'].astype(int).isin(keep)].copy() if not md.empty else md
    else:
        ppol, fpol, mpol = (pdec, fdec, md)
    summary = validation_summary_from_rows_v235(ppol, int(args.lines))
    weights, evidence, fstate = select_rank_fusion_weights_v244(mpol, min_history=max(30, int(args.min_gate_history)), bootstrap_samples=int(args.v241_bootstrap_samples), min_p_better=float(args.v241_min_p_better), min_edge_pct=float(args.v241_min_edge_pct), seed=int(args.seed), alpha=float(args.v244_alpha), correction=str(args.v244_multiple_testing), significance_lookback=max(50, int(args.v244_significance_lookback)))
    rf = _portfolio_rank_frame_v242(mpol, fpol)
    allocation, adetail = optimize_top30_allocation_v242(rf, budget=int(args.lines), min_history=max(int(args.min_gate_history), 60), lookback=int(args.v242_allocation_lookback), beam_width=int(args.v242_allocation_beam), half_life=float(args.v242_allocation_half_life), seed=int(args.seed))
    info = {'strategy': 'v248_prospective_incremental_portfolio', 'fusion_state': fstate, 'fusion_weights': weights, 'allocation': allocation, 'allocation_detail': adetail, 'evidence': evidence, 'objective': 'prospective incremental tie-aware exact5 capture'}
    return (summary, pdec, fdec, abl, md, weights, allocation, info)

def save_current_snapshot_v248(state_dir: Path, target: int, audit: AuditResult, prod_gate: Dict[str, object], production_snapshot: Optional[Dict[str, object]]) -> Optional[Path]:
    if not JOBLIB_OK or not production_snapshot:
        return None
    sp = _v248_snapshot_path(state_dir, target)
    sp.parent.mkdir(parents=True, exist_ok=True)
    snap = dict(production_snapshot)
    snap.update({'schema': V248_STATE_SCHEMA, 'target': int(target), 'history_last': int(audit.max_concurso), 'history_sha256': str(audit.sha256), 'created_at': time.strftime('%Y-%m-%d %H:%M:%S'), 'fusion_state': prod_gate.get('fusion_state', 'unknown'), 'allocation_state': prod_gate.get('allocation_detail', {}).get('state', 'unknown'), 'trained_at': int(audit.max_concurso)})
    manifest = {'schema': V248_STATE_SCHEMA, 'target': int(target), 'history_last': int(audit.max_concurso), 'history_sha256': str(audit.sha256), 'fusion_weights': snap.get('fusion_weights', {}), 'allocation': snap.get('allocation', {}), 'portfolio_idx': [int(x) for x in np.asarray(snap.get('portfolio_idx', []), dtype=int).tolist()], 'strategies': sorted(map(str, snap.get('specialist_scores', {}).keys()))}
    snap['manifest_sha256'] = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
    _atomic_joblib_dump(snap, sp, compress=3)
    return sp


# ============================================================
# V249 — COVERAGE-CONSTRAINED / ANTI-SATURATION PORTFOLIO
# ============================================================
V249_STATE_SCHEMA = 1
V249_PORTFOLIO_STRATEGY = 'v249_coverage_constrained_portfolio'
V249_UNCLIPPED_HEURISTIC = '_heuristic_unclipped_v249'

@dataclass(frozen=True)
class CoverageConfigV249:
    candidate_depth: int = 5000
    max_candidate_depth: int = 40000
    lock_top: int = 3
    reference_quantile: float = 0.9995
    quality_weight: float = 0.78
    diversity_weight: float = 0.22
    redundancy_penalty: float = 0.10
    milp_time_limit: float = 15.0
    milp_rel_gap: float = 0.002


V249_PAIR_KEYS = tuple(itertools.combinations(tuple(map(int, NUMBERS)), 2))
V249_TRIPLE_KEYS = tuple(itertools.combinations(tuple(map(int, NUMBERS)), 3))
V249_PAIR_TO_ROW = {k: i for i, k in enumerate(V249_PAIR_KEYS)}
V249_TRIPLE_TO_ROW = {k: i for i, k in enumerate(V249_TRIPLE_KEYS)}


def zscore_unclipped_v249(v: np.ndarray) -> np.ndarray:
    """Standard z-score without tail clipping; used only to avoid artificial score plateaus."""
    x = np.asarray(v, dtype=np.float64)
    if x.size == 0:
        return x
    m = float(np.nanmean(x))
    sd = float(np.nanstd(x))
    if (not np.isfinite(sd)) or sd < 1e-12:
        return np.zeros_like(x)
    return np.nan_to_num((x - m) / sd)


def _heuristic_unclipped_v249(hist_df: pd.DataFrame) -> np.ndarray:
    """Rebuild the same heuristic feature contract but do not clip the final aggregate at ±6."""
    X, _, _ = build_universe_features(hist_df)
    Xh = np.column_stack([safe_z(X[:, i]) for i in range(X.shape[1])]).astype(np.float32)
    hw = HEURISTIC_FEATURE_WEIGHTS.copy()
    hw = np.pad(hw, (0, max(0, Xh.shape[1] - len(hw))))[:Xh.shape[1]]
    return zscore_unclipped_v249(Xh @ hw)


def score_parts_v249(hist_df: pd.DataFrame, bundle=None):
    """V249 model signals are V248-compatible; adds an unclipped heuristic only for tie resolution."""
    ctx, parts = score_parts_v248(hist_df, bundle)
    try:
        parts[V249_UNCLIPPED_HEURISTIC] = _heuristic_unclipped_v249(hist_df)
    except Exception as e:
        log_exception('v249.unclipped_heuristic', e)
        parts[V249_UNCLIPPED_HEURISTIC] = np.asarray(parts.get('heuristic', np.zeros(UNIVERSE_SIZE)), dtype=float)
    return ctx, parts


def rank_fuse_scores_v249(strategy_scores: Dict[str, np.ndarray], weights: Dict[str, float]) -> np.ndarray:
    """Tie-aware rank fusion without safe_z tail clipping, preventing artificial 6.0 plateaus."""
    fused = np.zeros(UNIVERSE_SIZE, dtype=np.float64)
    used = 0.0
    denom = math.log1p(UNIVERSE_SIZE)
    for st, w in weights.items():
        if w <= 0 or st not in strategy_scores:
            continue
        ranks = tie_midrank_vector_v248(np.asarray(strategy_scores[st], dtype=float))
        strength = 1.0 - np.log1p(ranks - 1.0) / denom
        fused += float(w) * strength
        used += float(w)
    if used <= 0:
        return zscore_unclipped_v249(np.asarray(strategy_scores['heuristic'], dtype=float))
    return zscore_unclipped_v249(fused / used)


def _minmax_v249(v: np.ndarray) -> np.ndarray:
    x = np.asarray(v, dtype=np.float64)
    if x.size == 0:
        return x
    lo = float(np.nanmin(x)); hi = float(np.nanmax(x))
    if (not np.isfinite(lo)) or (not np.isfinite(hi)) or hi - lo < 1e-15:
        return np.zeros_like(x)
    return np.nan_to_num((x - lo) / (hi - lo))


def tie_safe_anti_saturation_score_v249(primary: np.ndarray, tie_signal: np.ndarray) -> Tuple[np.ndarray, float]:
    """
    Convert lexicographic (primary, tie_signal) order to a scalar without allowing a tie-break
    to cross a genuinely different primary-score level.
    """
    p = np.asarray(primary, dtype=np.float64)
    t = rank_strength_v248(np.asarray(tie_signal, dtype=np.float64))
    unique = np.unique(p[np.isfinite(p)])
    if len(unique) > 1:
        gaps = np.diff(unique)
        gaps = gaps[gaps > 0]
        min_gap = float(gaps.min()) if len(gaps) else 1.0
        eps = max(np.finfo(np.float64).eps * 64.0, 0.25 * min_gap)
    else:
        eps = 1e-9
    anti = p + eps * _minmax_v249(t)
    return anti, float(eps)


def _hypergeom_ppf_v249(q: float, population: int, successes: int, draws: int) -> int:
    q = float(min(1.0 - 1e-12, max(1e-12, q)))
    if hypergeom_dist is not None:
        return int(hypergeom_dist.ppf(q, int(population), int(successes), int(draws)))
    p = float(successes) / float(population)
    if binom_dist is not None:
        return int(binom_dist.ppf(q, int(draws), p))
    # Conservative dependency-free fallback.
    mu = draws * p
    sd = math.sqrt(max(1e-12, draws * p * (1.0 - p)))
    return int(min(draws, math.ceil(mu + 4.0 * sd)))


def random_reference_limits_v249(lines: int, quantile: float=0.9995) -> Dict[str, object]:
    """
    Familywise concentration caps under a uniform 5/28 reference.

    These are portfolio-risk constraints, not a claim of predictive edge.  A fair draw
    still gives every distinct 30-line portfolio the same exact-hit probability.
    """
    L = max(1, int(lines))
    q = float(quantile)
    if not (0.90 < q < 1.0):
        raise ValueError('V249 reference_quantile debe estar entre 0.90 y 1.0')

    def family_cap(size: int) -> tuple[int, float, int]:
        successes = math.comb(N_NUMBERS - size, DRAW_SIZE - size)
        family = math.comb(N_NUMBERS, size)
        marginal_q = 1.0 - (1.0 - q) / float(family)
        cap = _hypergeom_ppf_v249(marginal_q, UNIVERSE_SIZE, successes, L)
        return max(1, int(cap)), float(L * successes / UNIVERSE_SIZE), int(family)

    max_number, exp_number, number_family = family_cap(1)
    max_pair, exp_pair, pair_family = family_cap(2)
    max_triple, exp_triple, triple_family = family_cap(3)

    k_overlap4 = math.comb(DRAW_SIZE, 4) * math.comb(N_NUMBERS - DRAW_SIZE, 1) + 1
    k_overlap3 = math.comb(DRAW_SIZE, 3) * math.comb(N_NUMBERS - DRAW_SIZE, 2) + k_overlap4
    max_overlap4 = _hypergeom_ppf_v249(q, UNIVERSE_SIZE, k_overlap4, L)
    max_overlap3 = _hypergeom_ppf_v249(q, UNIVERSE_SIZE, k_overlap3, L)
    return {
        'reference': 'uniform_without_replacement_hypergeometric_familywise',
        'quantile': q,
        'lines': L,
        'max_number_count': max_number,
        'max_pair_count': max_pair,
        'max_triple_count': max_triple,
        'max_overlap_ge4': max(0, int(max_overlap4)),
        'max_overlap_ge3': max(0, int(max_overlap3)),
        'expected_number_count': exp_number,
        'expected_pair_count': exp_pair,
        'expected_triple_count': exp_triple,
        'number_family_size': number_family,
        'pair_family_size': pair_family,
        'triple_family_size': triple_family,
        'expected_overlap_last_mean': float(DRAW_SIZE * DRAW_SIZE / N_NUMBERS),
        'p_overlap_ge4_single': float(k_overlap4 / UNIVERSE_SIZE),
        'p_overlap_ge3_single': float(k_overlap3 / UNIVERSE_SIZE),
    }


def portfolio_concentration_audit_v249(portfolio_idx: Sequence[int], last_combo: Sequence[int], limits: Optional[Dict[str, object]]=None) -> Dict[str, object]:
    idx = np.asarray(portfolio_idx, dtype=np.int32)
    combos = ALL_COMBOS[idx] if len(idx) else np.empty((0, DRAW_SIZE), dtype=np.int16)
    last = set(map(int, last_combo))
    number_counts = Counter(int(x) for x in combos.ravel())
    overlaps = np.asarray([len(last & set(map(int, c))) for c in combos], dtype=np.int16)
    pair_counts: Counter = Counter()
    triple_counts: Counter = Counter()
    quad_counts: Counter = Counter()
    for c in combos:
        co = tuple(map(int, c))
        pair_counts.update(itertools.combinations(co, 2))
        triple_counts.update(itertools.combinations(co, 3))
        quad_counts.update(itertools.combinations(co, 4))
    arr = np.asarray([number_counts.get(i, 0) for i in NUMBERS], dtype=float)
    p = arr / max(1.0, arr.sum())
    nz = p[p > 0]
    entropy = float(-np.sum(nz * np.log(nz)) / math.log(N_NUMBERS)) if len(nz) else 0.0
    dist = {str(k): int(np.sum(overlaps == k)) for k in range(DRAW_SIZE + 1)}
    audit = {
        'lines': int(len(idx)),
        'unique_lines': int(len(set(map(int, idx.tolist())))),
        'unique_numbers': int(sum(v > 0 for v in arr)),
        'number_counts': {str(i): int(number_counts.get(i, 0)) for i in NUMBERS},
        'max_number_count': int(arr.max()) if len(arr) else 0,
        'max_number_share': float(arr.max() / max(1, len(idx))) if len(arr) else 0.0,
        'number_entropy_normalized': entropy,
        'overlap_last_mean': float(overlaps.mean()) if len(overlaps) else 0.0,
        'overlap_last_distribution': dist,
        'overlap_ge3': int(np.sum(overlaps >= 3)),
        'overlap_ge4': int(np.sum(overlaps >= 4)),
        'exact_repeat_last': int(np.sum(overlaps >= 5)),
        'max_pair_count': int(max(pair_counts.values(), default=0)),
        'max_triple_count': int(max(triple_counts.values(), default=0)),
        'max_quad_count': int(max(quad_counts.values(), default=0)),
        'unique_pairs': int(len(pair_counts)),
        'unique_triples': int(len(triple_counts)),
        'unique_quads': int(len(quad_counts)),
    }
    if limits:
        audit['limits'] = dict(limits)
        audit['passes_number_limit'] = bool(audit['max_number_count'] <= int(limits['max_number_count']))
        audit['passes_pair_limit'] = bool(audit['max_pair_count'] <= int(limits['max_pair_count']))
        audit['passes_triple_limit'] = bool(audit['max_triple_count'] <= int(limits['max_triple_count']))
        audit['passes_overlap_ge3_limit'] = bool(audit['overlap_ge3'] <= int(limits['max_overlap_ge3']))
        audit['passes_overlap_ge4_limit'] = bool(audit['overlap_ge4'] <= int(limits['max_overlap_ge4']))
        audit['passes_all_hard_limits'] = bool(
            audit['passes_number_limit'] and audit['passes_pair_limit'] and audit['passes_triple_limit']
            and audit['passes_overlap_ge3_limit'] and audit['passes_overlap_ge4_limit']
        )
    return audit


def _normalize_source_caps_v249(strategy_scores: Dict[str, np.ndarray], allocation: Dict[str, int], budget: int) -> Dict[str, int]:
    caps = {str(st): int(k) for st, k in allocation.items() if int(k) > 0 and st in strategy_scores}
    if not caps:
        if 'v241_fusion' not in strategy_scores:
            raise ValueError('V249: no hay fuentes aprobadas para construir portafolio')
        caps = {'v241_fusion': int(budget)}
    total = sum(caps.values())
    if total < budget:
        fallback = 'v241_fusion' if 'v241_fusion' in caps else next(iter(caps))
        caps[fallback] += int(budget - total)
    elif total > budget:
        excess = int(total - budget)
        for st in reversed(list(caps)):
            take = min(excess, caps[st])
            caps[st] -= take
            excess -= take
            if caps[st] <= 0:
                caps.pop(st, None)
            if excess <= 0:
                break
    if sum(caps.values()) != int(budget):
        raise RuntimeError(f'V249 source quota invariant failed: {caps} budget={budget}')
    return caps


def _depth_schedule_v249(base: int, maximum: int) -> List[int]:
    base = max(1, int(base)); maximum = max(base, min(UNIVERSE_SIZE, int(maximum)))
    vals = [base]
    while vals[-1] < maximum:
        vals.append(min(maximum, vals[-1] * 2))
    return sorted(set(vals))


def _static_candidate_scores_v249(
    candidate_idx: np.ndarray,
    primary_ranks: np.ndarray,
    tie_ranks: np.ndarray,
    source_ranks: np.ndarray,
    last_combo: Sequence[int],
    cfg: CoverageConfigV249,
) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
    """Linear MILP objective: predictive quality + shelf rarity - last-draw concentration risk."""
    idx = np.asarray(candidate_idx, dtype=np.int32)
    combos = ALL_COMBOS[idx]
    n = len(idx)
    if n == 0:
        return np.empty(0, dtype=float), {}
    denom_u = math.log1p(UNIVERSE_SIZE)
    q_primary = 1.0 - np.log1p(np.maximum(0, primary_ranks[idx] - 1)) / denom_u
    q_tie = 1.0 - np.log1p(np.maximum(0, tie_ranks[idx] - 1)) / denom_u
    max_sr = max(2, int(np.max(source_ranks)))
    q_source = 1.0 - np.log1p(np.maximum(0, source_ranks - 1)) / math.log1p(max_sr)
    quality = 0.65 * q_primary + 0.25 * q_source + 0.10 * q_tie

    # Rarity is computed on unique candidate combinations, not source duplicates.
    uniq = np.unique(idx)
    uniq_combos = ALL_COMBOS[uniq]
    num_freq = np.bincount(uniq_combos.ravel(), minlength=N_NUMBERS + 1).astype(float)
    rarity_num = np.asarray([np.mean([1.0 / math.sqrt(max(1.0, num_freq[int(x)])) for x in c]) for c in combos])
    rarity_num = _minmax_v249(rarity_num)

    last = set(map(int, last_combo))
    overlap = np.asarray([len(last & set(map(int, c))) for c in combos], dtype=float)
    overlap_risk = (overlap / float(DRAW_SIZE)) ** 2
    diversity = 0.75 * rarity_num + 0.25 * (1.0 - overlap / float(DRAW_SIZE))
    objective = float(cfg.quality_weight) * quality + float(cfg.diversity_weight) * diversity - float(cfg.redundancy_penalty) * overlap_risk
    return objective.astype(np.float64), {
        'quality': quality.astype(np.float64),
        'diversity': diversity.astype(np.float64),
        'redundancy': overlap_risk.astype(np.float64),
        'overlap': overlap.astype(np.float64),
    }


def _solve_coverage_milp_v249(
    strategy_scores: Dict[str, np.ndarray],
    source_caps: Dict[str, int],
    budget: int,
    primary: np.ndarray,
    tie: np.ndarray,
    primary_ranks: np.ndarray,
    tie_ranks: np.ndarray,
    last_combo: Sequence[int],
    limits: Dict[str, object],
    depth: int,
    lock_top: int,
    cfg: CoverageConfigV249,
) -> Tuple[Optional[List[Tuple[int, str, int, int, Dict[str, float]]]], Dict[str, object]]:
    if not SCIPY_MILP_OK:
        return None, {'solver': 'unavailable', 'message': 'scipy.optimize.milp no disponible'}

    # Variable = (candidate combination, predictive source).  This preserves source quotas exactly.
    var_idx: List[int] = []
    var_source: List[str] = []
    var_source_rank: List[int] = []
    source_var_cols: Dict[str, List[int]] = {st: [] for st in source_caps}
    cand_var_cols: Dict[int, List[int]] = defaultdict(list)
    for st in source_caps:
        sc = np.asarray(strategy_scores[st], dtype=float)
        order = rank_order_v248(sc, tie)[:int(depth)]
        for pos, j in enumerate(order, 1):
            col = len(var_idx); jj = int(j)
            var_idx.append(jj); var_source.append(str(st)); var_source_rank.append(int(pos))
            source_var_cols[str(st)].append(col); cand_var_cols[jj].append(col)
    if not var_idx:
        return None, {'solver': 'milp', 'message': 'sin variables candidatas', 'depth': int(depth)}

    vi = np.asarray(var_idx, dtype=np.int32)
    vsr = np.asarray(var_source_rank, dtype=np.int32)
    objective, comp = _static_candidate_scores_v249(vi, primary_ranks, tie_ranks, vsr, last_combo, cfg)
    combos = ALL_COMBOS[vi]
    last = set(map(int, last_combo))
    overlaps = np.asarray([len(last & set(map(int, c))) for c in combos], dtype=np.int8)

    rows: List[int] = []; cols: List[int] = []; data: List[float] = []
    lb: List[float] = []; ub: List[float] = []
    rowno = 0
    def new_row(lower: float=-np.inf, upper: float=np.inf) -> int:
        nonlocal rowno
        r = rowno; rowno += 1; lb.append(float(lower)); ub.append(float(upper)); return r
    def add(r: int, c: int, value: float=1.0) -> None:
        rows.append(int(r)); cols.append(int(c)); data.append(float(value))

    # Exactly budget lines.
    r_total = new_row(budget, budget)
    for c in range(len(vi)): add(r_total, c)

    # Exact predictive-source quotas inherited from the Holm-gated allocator.
    for st, cap in source_caps.items():
        r = new_row(cap, cap)
        for c in source_var_cols.get(st, []): add(r, c)

    # A combination may be assigned to at most one source.
    for _, cc in cand_var_cols.items():
        if len(cc) > 1:
            r = new_row(0, 1)
            for c in cc: add(r, c)

    # Familywise caps for individual numbers.
    for nval in NUMBERS:
        r = new_row(0, int(limits['max_number_count']))
        for c in np.flatnonzero(np.any(combos == int(nval), axis=1)): add(r, int(c))

    # Pair reuse caps: directly prevents degenerate 03-05-type concentration.
    pair_rows = [new_row(0, int(limits['max_pair_count'])) for _ in V249_PAIR_KEYS]
    for c, combo in enumerate(combos):
        for pair in itertools.combinations(tuple(map(int, combo)), 2):
            add(pair_rows[V249_PAIR_TO_ROW[pair]], c)

    # Triple reuse caps: controls 3-number cores repeated across most tickets.
    triple_rows = [new_row(0, int(limits['max_triple_count'])) for _ in V249_TRIPLE_KEYS]
    for c, combo in enumerate(combos):
        for tri in itertools.combinations(tuple(map(int, combo)), 3):
            add(triple_rows[V249_TRIPLE_TO_ROW[tri]], c)

    r_ov3 = new_row(0, int(limits['max_overlap_ge3']))
    r_ov4 = new_row(0, int(limits['max_overlap_ge4']))
    for c, ov in enumerate(overlaps):
        if int(ov) >= 3: add(r_ov3, c)
        if int(ov) >= 4: add(r_ov4, c)

    # Preserve the strongest primary hypotheses only when compatible with hard risk limits.
    locked_candidates = []
    if int(lock_top) > 0:
        seen = set()
        for j in np.argsort(primary_ranks, kind='stable'):
            jj = int(j)
            if jj in cand_var_cols and jj not in seen:
                locked_candidates.append(jj); seen.add(jj)
                if len(locked_candidates) >= int(lock_top): break
        for jj in locked_candidates:
            r = new_row(1, 1)
            for c in cand_var_cols[jj]: add(r, c)

    A = coo_matrix((np.asarray(data, dtype=float), (np.asarray(rows, dtype=np.int32), np.asarray(cols, dtype=np.int32))), shape=(rowno, len(vi))).tocsr()
    constraints = LinearConstraint(A, np.asarray(lb, dtype=float), np.asarray(ub, dtype=float))
    options = {'presolve': True, 'time_limit': float(cfg.milp_time_limit), 'mip_rel_gap': float(cfg.milp_rel_gap)}
    t0 = time.time()
    res = milp(c=-objective, integrality=np.ones(len(vi), dtype=np.int8), bounds=Bounds(np.zeros(len(vi)), np.ones(len(vi))), constraints=constraints, options=options)
    elapsed = time.time() - t0
    detail = {
        'solver': 'scipy.optimize.milp/HiGHS', 'status': int(getattr(res, 'status', -1)),
        'message': str(getattr(res, 'message', '')), 'success': bool(getattr(res, 'success', False)),
        'depth': int(depth), 'variables': int(len(vi)), 'constraints': int(rowno),
        'lock_top_requested': int(lock_top), 'locked_candidates': [int(x) for x in locked_candidates],
        'elapsed_sec': float(elapsed), 'objective_value': float(-res.fun) if getattr(res, 'fun', None) is not None else None,
    }
    if getattr(res, 'x', None) is None:
        return None, detail
    selected_cols = np.flatnonzero(np.asarray(res.x) > 0.5)
    if len(selected_cols) != int(budget):
        detail['message'] += f' | selected={len(selected_cols)} != budget={budget}'
        return None, detail
    out: List[Tuple[int, str, int, int, Dict[str, float]]] = []
    for c in selected_cols:
        jj = int(vi[c])
        out.append((jj, str(var_source[c]), int(vsr[c]), int(c), {
            'selection_objective': float(objective[c]),
            'quality': float(comp['quality'][c]), 'diversity': float(comp['diversity'][c]),
            'redundancy': float(comp['redundancy'][c]), 'overlap_last': int(comp['overlap'][c]),
        }))
    return out, detail


def build_coverage_portfolio_v249(
    strategy_scores: Dict[str, np.ndarray],
    allocation: Dict[str, int],
    budget: int,
    primary_score: np.ndarray,
    tie_signal: np.ndarray,
    last_combo: Sequence[int],
    cfg: CoverageConfigV249,
) -> Tuple[pd.DataFrame, np.ndarray, Dict[str, object]]:
    """
    Exact Top-N portfolio optimization.

    Predictive credit remains entirely controlled by the inherited Holm gate.  MILP only
    allocates the already-approved source quotas while enforcing statistically calibrated
    concentration limits.  It expands candidate depth before ever dropping an elite lock;
    it never silently relaxes the hard limits.
    """
    budget = int(budget)
    primary = np.asarray(primary_score, dtype=float)
    tie = np.asarray(tie_signal, dtype=float)
    anti_score, eps = tie_safe_anti_saturation_score_v249(primary, tie)
    primary_order = np.argsort(-anti_score, kind='stable').astype(np.int32)
    primary_ranks = np.empty(UNIVERSE_SIZE, dtype=np.int32); primary_ranks[primary_order] = np.arange(1, UNIVERSE_SIZE + 1, dtype=np.int32)
    tie_order = rank_order_v248(tie)
    tie_ranks = np.empty(UNIVERSE_SIZE, dtype=np.int32); tie_ranks[tie_order] = np.arange(1, UNIVERSE_SIZE + 1, dtype=np.int32)

    scores = dict(strategy_scores)
    if 'v241_fusion' not in scores:
        scores['v241_fusion'] = primary
    source_caps = _normalize_source_caps_v249(scores, allocation, budget)
    base_limits = random_reference_limits_v249(budget, cfg.reference_quantile)
    attempts: List[Dict[str, object]] = []
    chosen = None
    solver_detail = None
    used_depth = None
    used_lock = None

    for depth in _depth_schedule_v249(cfg.candidate_depth, cfg.max_candidate_depth):
        # If an elite lock itself conflicts with concentration constraints, reduce only the lock;
        # predictive source quotas and statistical caps remain untouched.
        for lock in range(min(int(cfg.lock_top), budget), -1, -1):
            sel, det = _solve_coverage_milp_v249(scores, source_caps, budget, primary, tie, primary_ranks, tie_ranks, last_combo, base_limits, depth, lock, cfg)
            attempts.append(det)
            if sel is None:
                continue
            idx_test = [x[0] for x in sel]
            audit_test = portfolio_concentration_audit_v249(idx_test, last_combo, base_limits)
            src_test = Counter(x[1] for x in sel)
            quotas_ok = all(int(src_test.get(st, 0)) == int(cap) for st, cap in source_caps.items())
            if audit_test.get('passes_all_hard_limits', False) and quotas_ok and len(set(idx_test)) == budget:
                chosen, solver_detail, used_depth, used_lock = sel, det, int(depth), int(lock)
                break
        if chosen is not None:
            break

    if chosen is None:
        last_attempt = attempts[-1] if attempts else {}
        raise RuntimeError(
            'V249 COVERAGE INFEASIBLE: no se pudo construir el portafolio sin violar los límites '
            f'estadísticos hasta depth={cfg.max_candidate_depth}. Último solver={last_attempt}'
        )

    # Deterministic portfolio order by anti-saturated primary rank, not MILP column order.
    chosen = sorted(chosen, key=lambda x: (int(primary_ranks[x[0]]), int(tie_ranks[x[0]]), int(x[0]), x[1]))
    selected = [int(x[0]) for x in chosen]
    source_counts = Counter(x[1] for x in chosen)
    rows_meta = {int(j): {'source': st, 'source_rank': sr, **meta} for j, st, sr, _, meta in chosen}
    risk = portfolio_concentration_audit_v249(selected, last_combo, base_limits)
    raw_top = primary_order[:budget]
    raw_risk = portfolio_concentration_audit_v249(raw_top, last_combo, base_limits)
    saturation = {
        'primary_max_score': float(np.max(primary)) if len(primary) else 0.0,
        'primary_max_plateau_size': int(np.sum(np.isclose(primary, np.max(primary), rtol=0.0, atol=1e-12))) if len(primary) else 0,
        'unique_primary_scores_candidate_depth': int(len(np.unique(primary[primary_order[:used_depth]]))),
        'anti_saturation_epsilon': float(eps),
    }
    if not risk.get('passes_all_hard_limits', False):
        raise RuntimeError(f'V249 post-solve concentration invariant failed: {risk}')
    if any(int(source_counts.get(st, 0)) != int(cap) for st, cap in source_caps.items()):
        raise RuntimeError(f'V249 post-solve source quota invariant failed: counts={dict(source_counts)} caps={source_caps}')

    last = set(map(int, last_combo))
    records = []
    for rank, j in enumerate(selected, 1):
        co = ALL_COMBOS[j]; mm = rows_meta[j]
        records.append({
            'portfolio_rank': rank, 'combo': combo_str(co), 'combo_index': int(j),
            'source': str(mm['source']), 'source_rank': int(mm['source_rank']), 'primary_rank': int(primary_ranks[j]),
            'fusion_score': float(primary[j]), 'anti_saturation_score': float(anti_score[j]), 'tie_break_score': float(tie[j]),
            'selection_objective': float(mm.get('selection_objective', 0.0)), 'quality_component': float(mm.get('quality', 0.0)),
            'diversity_component': float(mm.get('diversity', 0.0)), 'redundancy_component': float(mm.get('redundancy', 0.0)),
            'overlap_last': int(mm.get('overlap_last', len(last & set(map(int, co))))),
            'locked_top': bool(int(j) in set(solver_detail.get('locked_candidates', []))),
            'sum': int(COMBO_SUM[j]), 'zone': f'{COMBO_ZONES[j][0]}-{COMBO_ZONES[j][1]}-{COMBO_ZONES[j][2]}',
        })
    detail = {
        'reference_limits': base_limits, 'effective_limits': dict(base_limits), 'source_caps': source_caps,
        'source_counts': {k: int(v) for k, v in source_counts.items()}, 'raw_top30_audit': raw_risk,
        'v249_portfolio_audit': risk, 'saturation_audit': saturation, 'candidate_depth_requested': int(cfg.candidate_depth),
        'candidate_depth_used': int(used_depth), 'max_candidate_depth': int(cfg.max_candidate_depth),
        'lock_top_requested': int(cfg.lock_top), 'lock_top_used': int(used_lock), 'hard_limits_relaxed': False,
        'solver': solver_detail, 'solver_attempts': attempts,
    }
    return pd.DataFrame(records), np.asarray(selected, dtype=np.int32), detail


def production_portfolio_v249(hist_df: pd.DataFrame, bundle, fusion_weights: Dict[str, float], allocation: Dict[str, int], lines: int, cfg: CoverageConfigV249) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, object]]:
    ctx, parts = score_parts_v249(hist_df, bundle)
    specialists = {st: strategy_score_v239(parts, st) for st in V241_FUSION_STRATEGIES}
    specialists[V248_RESIDUAL_STRATEGY] = strategy_score_v239(parts, V248_RESIDUAL_STRATEGY)
    fused = rank_fuse_scores_v249(specialists, fusion_weights)
    active = [st for st, w in fusion_weights.items() if float(w) > 0 and st in specialists]
    if len(active) == 1 and active[0] == 'heuristic':
        tie_signal = np.asarray(parts.get(V249_UNCLIPPED_HEURISTIC, specialists['heuristic']), dtype=float)
        tie_signal_name = 'heuristic_unclipped'
    else:
        tie_signal = np.asarray(specialists.get(V248_RESIDUAL_STRATEGY, specialists.get('number_markov', fused)), dtype=float)
        tie_signal_name = V248_RESIDUAL_STRATEGY
    anti_score, eps = tie_safe_anti_saturation_score_v249(fused, tie_signal)
    scores = dict(specialists)
    scores['v241_fusion'] = fused
    portfolio, portfolio_idx, coverage_detail = build_coverage_portfolio_v249(scores, allocation, lines, fused, tie_signal, ctx.last_combo, cfg)
    order = np.argsort(-anti_score, kind='stable').astype(np.int32)
    ranks = np.empty(len(order), dtype=np.int32)
    ranks[order] = np.arange(1, len(order) + 1, dtype=np.int32)
    ranking = pd.DataFrame({
        'rank': ranks,
        'combo': [combo_str(c) for c in ALL_COMBOS],
        'score': fused,
        'anti_saturation_score': anti_score,
        'score_heuristic': specialists['heuristic'],
        'score_heuristic_unclipped': np.asarray(parts.get(V249_UNCLIPPED_HEURISTIC, specialists['heuristic']), dtype=float),
        'score_markov_exact5_residual': specialists[V248_RESIDUAL_STRATEGY],
        'score_ltr_ndcg_exact5': specialists['ltr_ndcg_exact5'],
        'score_ltr_adv_exact5': specialists.get('ltr_adv_exact5', np.zeros(UNIVERSE_SIZE)),
        'score_ltr_exact5_balanced': specialists.get('ltr_exact5_balanced', np.zeros(UNIVERSE_SIZE)),
        'score_ltr_exact5_hard': specialists.get('ltr_exact5_hard', np.zeros(UNIVERSE_SIZE)),
        'score_ltr_exact5_ultra': specialists.get('ltr_exact5_ultra', np.zeros(UNIVERSE_SIZE)),
        'score_number_markov': specialists['number_markov'],
        'score_number_knn': specialists['number_knn'],
        'score_number_transition': specialists['number_transition'],
        'sum': COMBO_SUM,
        'zone': [f'{a}-{b}-{c}' for a, b, c in COMBO_ZONES],
        'overlap_last': np.sum(np.isin(ALL_COMBOS, np.array(ctx.last_combo)), axis=1),
    }).sort_values('rank').reset_index(drop=True)
    snapshot = {
        'specialist_scores': {k: np.asarray(v, dtype=np.float32) for k, v in specialists.items()},
        'fused': np.asarray(fused, dtype=np.float32),
        'anti_saturation_score': np.asarray(anti_score, dtype=np.float32),
        'tie_signal': np.asarray(tie_signal, dtype=np.float32),
        'tie_signal_name': tie_signal_name,
        'anti_saturation_epsilon': float(eps),
        'portfolio_idx': np.asarray(portfolio_idx, dtype=np.int32),
        'portfolio': portfolio.copy(),
        'fusion_weights': dict(fusion_weights),
        'allocation': dict(allocation),
        'coverage_detail': coverage_detail,
        'coverage_config': asdict(cfg),
    }
    return portfolio, ranking, snapshot


def realized_forensic_v249(hist_df: pd.DataFrame, bundle, fusion_weights: Dict[str, float], allocation: Dict[str, int], realized, lines: int, cfg: CoverageConfigV249) -> Dict[str, object]:
    portfolio, ranking, snap = production_portfolio_v249(hist_df, bundle, fusion_weights, allocation, lines, cfg)
    ti = COMBO_TO_INDEX[realized]
    fused = np.asarray(snap['fused'], dtype=float)
    fstats = tie_rank_stats_v248(fused, ti, lines)
    pidx = np.asarray(snap['portfolio_idx'], dtype=np.int32)
    return {
        'realized': combo_str(realized),
        'captured_5of5_in_v249_portfolio': bool(ti in set(map(int, pidx.tolist()))),
        'v249_fusion_tie_rank': fstats,
        'best_hit_top_lines': int(best_hit([tuple(map(int, ALL_COMBOS[j])) for j in pidx], realized)),
        'allocation': dict(allocation),
        'fusion_weights': dict(fusion_weights),
        'coverage_detail': snap.get('coverage_detail', {}),
    }


def _v249_state_path(state_dir: Path) -> Path:
    return state_dir / 'v249_oos_state.joblib'


def _v249_snapshot_path(state_dir: Path, target: int) -> Path:
    return state_dir / 'snapshots' / f'target_{int(target)}.joblib'


def load_v249_state(state_dir: Path) -> Optional[Dict[str, object]]:
    sp = _v249_state_path(state_dir)
    if not (JOBLIB_OK and sp.exists()):
        return None
    try:
        st = joblib.load(sp)
        return st if int(st.get('schema', -1)) == V249_STATE_SCHEMA else None
    except Exception as e:
        progress(f'V249 state MISS: {type(e).__name__}: {e}')
        return None


def save_v249_state(state_dir: Path, state: Dict[str, object]) -> None:
    if not JOBLIB_OK:
        return
    state_dir.mkdir(parents=True, exist_ok=True)
    state['schema'] = V249_STATE_SCHEMA
    state['updated_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
    _atomic_joblib_dump(state, _v249_state_path(state_dir), compress=3)


def import_v248_state_v249(v248_state_dir: Path) -> Optional[Dict[str, object]]:
    src = v248_state_dir / 'v248_oos_state.joblib'
    if not (JOBLIB_OK and src.exists()):
        return None
    try:
        old = joblib.load(src)
        st = {
            'schema': V249_STATE_SCHEMA,
            'origin': str(src),
            'wf_detail': old.get('wf_detail', pd.DataFrame()).copy(),
            'fusion_detail': old.get('fusion_detail', pd.DataFrame()).copy(),
            'wf_ablation': old.get('wf_ablation', pd.DataFrame()).copy(),
            'meta_rows': old.get('meta_rows', pd.DataFrame()).copy(),
            'gate_evaluated_targets': sorted(set(map(int, old.get('evaluated_targets', [])))),
            'v249_evaluated_targets': [],
            'v249_portfolio_oos': pd.DataFrame(),
        }
        progress(f"V249 imported V248 gate state: {len(st['gate_evaluated_targets'])} resolved strategy targets; V249 portfolio starts prospectively")
        return st
    except Exception as e:
        progress(f'V249 state import skipped: {type(e).__name__}: {e}')
        return None


def consume_previous_snapshot_v249(df: pd.DataFrame, audit: AuditResult, state_dir: Path, state: Dict[str, object], lines: int) -> bool:
    prev_target = int(audit.max_concurso)
    portfolio_done = set(map(int, state.get('v249_evaluated_targets', [])))
    if prev_target in portfolio_done:
        return False
    sp = _v249_snapshot_path(state_dir, prev_target)
    if not (JOBLIB_OK and sp.exists()):
        progress(f'V249 incremental: no V249 snapshot for resolved target {prev_target}; nothing to append')
        return False
    snap = joblib.load(sp)
    if int(snap.get('target', -1)) != prev_target or int(snap.get('history_last', -1)) != prev_target - 1:
        raise RuntimeError('V249 snapshot guardrail failed: target/history_last mismatch')
    manifest = {
        'schema': int(snap.get('schema', -1)), 'target': int(snap.get('target', -1)), 'history_last': int(snap.get('history_last', -1)),
        'history_sha256': str(snap.get('history_sha256', '')), 'fusion_weights': snap.get('fusion_weights', {}), 'allocation': snap.get('allocation', {}),
        'portfolio_idx': [int(x) for x in np.asarray(snap.get('portfolio_idx', []), dtype=int).tolist()],
        'coverage_config': snap.get('coverage_config', {}), 'strategies': sorted(map(str, snap.get('specialist_scores', {}).keys())),
    }
    manifest_sha = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
    if str(snap.get('manifest_sha256', '')) != manifest_sha:
        raise RuntimeError('V249 snapshot guardrail failed: manifest SHA256 mismatch')
    rowdf = df[df['CONCURSO'] == prev_target]
    if len(rowdf) != 1:
        raise RuntimeError(f'V249 snapshot target {prev_target} not uniquely present in history')
    actual = combo_key(rowdf.iloc[0][R_COLS].to_numpy(dtype=int))
    ti = COMBO_TO_INDEX[actual]
    specialists = {k: np.asarray(v, dtype=float) for k, v in snap['specialist_scores'].items()}
    fused = np.asarray(snap['fused'], dtype=float)
    tie_signal = np.asarray(snap.get('tie_signal', specialists.get(V248_RESIDUAL_STRATEGY, fused)), dtype=float)

    gate_done = set(map(int, state.get('gate_evaluated_targets', [])))
    if prev_target not in gate_done:
        meta = state.get('meta_rows'); meta = meta.copy() if isinstance(meta, pd.DataFrame) else pd.DataFrame()
        abl = state.get('wf_ablation'); abl = abl.copy() if isinstance(abl, pd.DataFrame) else pd.DataFrame()
        new_meta = []
        for st in V241_FUSION_STRATEGIES:
            if st not in specialists:
                continue
            sc = specialists[st]
            ts = tie_rank_stats_v248(sc, ti, lines)
            top = rank_order_v248(sc, tie_signal)[:lines]
            bh = best_hit([tuple(map(int, ALL_COMBOS[j])) for j in top], actual)
            new_meta.append({'target': prev_target, 'strategy': st, 'exact_rank': int(ts['rank_worst']), 'best_hit': int(bh), 'rank_best': int(ts['rank_best']), 'rank_mid': float(ts['rank_mid']), 'tie_size': int(ts['tie_size']), 'top30_tie_prob': float(ts['topk_tie_prob']), 'trained_at': int(snap.get('trained_at', -1))})
        if new_meta:
            meta = pd.concat([meta, pd.DataFrame(new_meta)], ignore_index=True)
            abl = pd.concat([abl, pd.DataFrame(new_meta)], ignore_index=True)
        fdec = state.get('fusion_detail'); fdec = fdec.copy() if isinstance(fdec, pd.DataFrame) else pd.DataFrame()
        fts = tie_rank_stats_v248(fused, ti, lines)
        ftop = np.argsort(-np.asarray(snap.get('anti_saturation_score', fused), dtype=float), kind='stable')[:lines]
        fbh = best_hit([tuple(map(int, ALL_COMBOS[j])) for j in ftop], actual)
        frow = {'target': prev_target, 'strategy': 'v241_fusion', 'fusion_state': snap.get('fusion_state', 'prospective'), 'weights_json': json.dumps(snap.get('fusion_weights', {}), sort_keys=True), 'exact_rank': int(fts['rank_worst']), 'best_hit': int(fbh), 'exact5': int(ti in set(map(int, ftop.tolist()))), 'rank_best': int(fts['rank_best']), 'rank_mid': float(fts['rank_mid']), 'tie_size': int(fts['tie_size']), 'top30_tie_prob': float(fts['topk_tie_prob']), 'trained_at': int(snap.get('trained_at', -1))}
        fdec = pd.concat([fdec, pd.DataFrame([frow])], ignore_index=True)
        state.update({'meta_rows': meta, 'wf_ablation': abl, 'fusion_detail': fdec})
        gate_done.add(prev_target)
        state['gate_evaluated_targets'] = sorted(gate_done)

    pidx = np.asarray(snap['portfolio_idx'], dtype=np.int32)
    bh = best_hit([tuple(map(int, ALL_COMBOS[j])) for j in pidx], actual)
    pobj = state.get('v249_portfolio_oos'); pobj = pobj.copy() if isinstance(pobj, pd.DataFrame) else pd.DataFrame()
    prow = {'target': prev_target, 'strategy': V249_PORTFOLIO_STRATEGY, 'best_hit': int(bh), 'exact5': int(ti in set(map(int, pidx.tolist()))), 'ge4': int(bh >= 4), 'ge3': int(bh >= 3), 'coverage_json': json.dumps(snap.get('coverage_detail', {}), sort_keys=True, default=str), 'manifest_sha256': str(snap.get('manifest_sha256', ''))}
    pobj = pd.concat([pobj, pd.DataFrame([prow])], ignore_index=True)
    portfolio_done.add(prev_target)
    state['v249_evaluated_targets'] = sorted(portfolio_done)
    state['v249_portfolio_oos'] = pobj
    state['last_v249_result'] = {'target': prev_target, 'actual': combo_str(actual), 'portfolio_exact5': int(prow['exact5']), 'best_hit': int(bh)}
    progress(f"V249 incremental consumed target {prev_target}: exact5={prow['exact5']} best={bh}/5")
    return True


def production_policy_from_state_v249(state: Dict[str, object], args):
    # Gate policy remains the statistically guarded V248/V244 policy; only portfolio construction changes.
    shadow = {
        'wf_detail': state.get('wf_detail', pd.DataFrame()), 'fusion_detail': state.get('fusion_detail', pd.DataFrame()),
        'wf_ablation': state.get('wf_ablation', pd.DataFrame()), 'meta_rows': state.get('meta_rows', pd.DataFrame())
    }
    summary, pdec, fdec, abl, md, weights, allocation, info = production_policy_from_state_v248(shadow, args)
    info = dict(info)
    info.update({'strategy': V249_PORTFOLIO_STRATEGY, 'objective': 'Holm-gated prediction + coverage-constrained prospective Top-N'})
    return summary, pdec, fdec, abl, md, weights, allocation, info


def save_current_snapshot_v249(state_dir: Path, target: int, audit: AuditResult, prod_gate: Dict[str, object], production_snapshot: Optional[Dict[str, object]]) -> Optional[Path]:
    if not JOBLIB_OK or not production_snapshot:
        return None
    sp = _v249_snapshot_path(state_dir, target)
    sp.parent.mkdir(parents=True, exist_ok=True)
    # Prospective immutability: once a target snapshot exists, never rewrite it.
    if sp.exists():
        existing = joblib.load(sp)
        if int(existing.get('target', -1)) != int(target):
            raise RuntimeError('V249 frozen snapshot has unexpected target')
        if str(existing.get('history_sha256', '')) != str(audit.sha256):
            raise RuntimeError('V249 FROZEN SNAPSHOT CONFLICT: same target with different history hash')
        progress(f'V249 snapshot FROZEN HIT: target {target}; existing manifest preserved')
        return sp
    snap = dict(production_snapshot)
    snap.update({'schema': V249_STATE_SCHEMA, 'target': int(target), 'history_last': int(audit.max_concurso), 'history_sha256': str(audit.sha256), 'created_at': time.strftime('%Y-%m-%d %H:%M:%S'), 'fusion_state': prod_gate.get('fusion_state', 'unknown'), 'allocation_state': prod_gate.get('allocation_detail', {}).get('state', 'unknown'), 'trained_at': int(audit.max_concurso)})
    manifest = {'schema': V249_STATE_SCHEMA, 'target': int(target), 'history_last': int(audit.max_concurso), 'history_sha256': str(audit.sha256), 'fusion_weights': snap.get('fusion_weights', {}), 'allocation': snap.get('allocation', {}), 'portfolio_idx': [int(x) for x in np.asarray(snap.get('portfolio_idx', []), dtype=int).tolist()], 'coverage_config': snap.get('coverage_config', {}), 'strategies': sorted(map(str, snap.get('specialist_scores', {}).keys()))}
    snap['manifest_sha256'] = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
    _atomic_joblib_dump(snap, sp, compress=3)
    return sp


def seed_v249_model_core_from_v248(v248_model_dir: Optional[Path], v249_model_dir: Path, expected_signature: Dict[str, object]) -> bool:
    """Import a compatible V248 model-core once, while keeping V249 persistence files separate."""
    if not JOBLIB_OK or v248_model_dir is None:
        return False
    sm = v248_model_dir / 'v248_metadata.json'
    sb = v248_model_dir / 'v248_model_bundle.joblib'
    sc = v248_model_dir / 'v248_master_causal_cache.joblib'
    if not (sm.exists() and sb.exists() and sc.exists()):
        return False
    dm = v249_model_dir / 'v249_metadata.json'
    db = v249_model_dir / 'v249_model_bundle.joblib'
    dc = v249_model_dir / 'v249_master_causal_cache.joblib'
    if dm.exists() and db.exists() and dc.exists():
        return False
    try:
        old = json.loads(sm.read_text(encoding='utf-8')).get('signature', {})
        def norm(x):
            y = dict(x or {}); y.pop('engine', None); return y
        if norm(old) != norm(expected_signature):
            progress('V249 V248 model-core import skipped: signature mismatch')
            return False
        v249_model_dir.mkdir(parents=True, exist_ok=True)
        _atomic_joblib_dump(joblib.load(sb), db, compress=3)
        _atomic_joblib_dump(joblib.load(sc), dc, compress=3)
        dm.write_text(json.dumps({'signature': expected_signature, 'created_at': time.strftime('%Y-%m-%d %H:%M:%S'), 'imported_from': str(v248_model_dir)}, indent=2), encoding='utf-8')
        for name in ('v246_sampler_bank.joblib', 'v246_sampler_bank.json'):
            src = v248_model_dir / name; dst = v249_model_dir / name
            if src.exists() and not dst.exists():
                if src.suffix == '.joblib': _atomic_joblib_dump(joblib.load(src), dst, compress=3)
                else: dst.write_bytes(src.read_bytes())
        progress('V249 model-core seeded from compatible V248 persistence')
        return True
    except Exception as e:
        progress(f'V249 V248 model-core import failed: {type(e).__name__}: {e}')
        return False


def register_prospective_prediction_v249(registry_dir: Path, target: int, audit, portfolio: pd.DataFrame, ranking_path: Path, history_path: Path, script_path: Path, args, production_weights: Dict[str, float], production_allocation: Dict[str, int], statistical_report: Dict[str, object], coverage_detail: Dict[str, object]) -> Path:
    registry_dir.mkdir(parents=True, exist_ok=True)
    chain_path = registry_dir / 'v249_prospective_chain.jsonl'
    prev_hash = None
    if chain_path.exists():
        try:
            lines = [x for x in chain_path.read_text(encoding='utf-8').splitlines() if x.strip()]
            if lines: prev_hash = json.loads(lines[-1]).get('manifest_sha256')
        except Exception as e:
            log_exception('v249.prospective_chain.read', e)
    manifest = {
        'schema': 'chispazo-v249-prospective-v1', 'evidence_class': 'prospective_preregistered_experimental',
        'registered_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'target': int(target), 'expected_last': int(audit.max_concurso),
        'history_rows': int(audit.rows), 'history_sha256': _sha256_file_v244(history_path), 'script_sha256': sha256_code_path_v248(script_path),
        'ranking_sha256': _sha256_file_v244(ranking_path), 'lines': int(args.lines), 'seed': int(args.seed), 'ltr_seeds': int(args.v243_ltr_seeds),
        'ltr_topk': int(args.v243_ltr_topk), 'production_weights': production_weights, 'production_allocation': production_allocation,
        'coverage_config': coverage_detail.get('coverage_config', {}), 'coverage_detail': coverage_detail, 'portfolio': portfolio.to_dict(orient='records'),
        'historical_statistical_report_sha256': _canonical_sha_v244(statistical_report), 'previous_manifest_sha256': prev_hash,
        'note': 'V249 is a new experimental portfolio policy. It must be evaluated separately from the already-frozen V248 chain.'
    }
    manifest['manifest_sha256'] = _canonical_sha_v244(manifest)
    out = registry_dir / f'target_{int(target)}_V249_preregister.json'
    # Confirmatory chain is append-once per target. Re-running the same future target
    # cannot rewrite the frozen prediction, even if code/models/config changed later.
    if out.exists():
        existing = json.loads(out.read_text(encoding='utf-8'))
        saved = existing.get('manifest_sha256')
        chk = dict(existing); chk.pop('manifest_sha256', None)
        if saved != _canonical_sha_v244(chk):
            raise RuntimeError('V249 existing preregistration hash is invalid; refusing overwrite')
        if int(existing.get('target', -1)) != int(target):
            raise RuntimeError('V249 preregistration target conflict')
        if str(existing.get('history_sha256', '')) != str(manifest.get('history_sha256', '')):
            raise RuntimeError('V249 FROZEN PREREGISTRATION CONFLICT: same target with different history hash')
        progress(f'V249 preregistration FROZEN HIT: target {target}; SHA {saved} preserved')
        return out
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    with chain_path.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps({'target': int(target), 'registered_utc': manifest['registered_utc'], 'manifest_sha256': manifest['manifest_sha256'], 'previous_manifest_sha256': prev_hash, 'file': out.name}, ensure_ascii=False) + '\n')
    return out


def evaluate_prospective_registration_v249(registration_path: Path, realized_result: str, record_result: bool=True) -> Dict[str, object]:
    reg = json.loads(registration_path.read_text(encoding='utf-8'))
    saved_hash = reg.get('manifest_sha256')
    check = dict(reg); check.pop('manifest_sha256', None)
    recomputed = _canonical_sha_v244(check)
    vals = tuple(sorted(int(x.strip()) for x in realized_result.replace('-', ',').split(',') if x.strip()))
    combo = '-'.join(f'{x:02d}' for x in vals)
    pcombos = [str(r.get('combo')) for r in reg.get('portfolio', [])]
    captured = combo in pcombos
    pos = pcombos.index(combo) + 1 if captured else None
    valid = bool(saved_hash == recomputed)
    result = {'registration': str(registration_path), 'target': reg.get('target'), 'manifest_hash_valid': valid, 'manifest_sha256': saved_hash, 'realized': combo, 'captured_5of5': bool(captured), 'portfolio_position': pos, 'lines': int(reg.get('lines', len(pcombos))), 'single_trial_random_probability': float(reg.get('lines', len(pcombos)) / UNIVERSE_SIZE), 'evaluated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    if record_result and valid:
        ledger = registration_path.parent / 'v249_prospective_results.jsonl'
        prior=[]
        if ledger.exists():
            for line in ledger.read_text(encoding='utf-8').splitlines():
                if not line.strip(): continue
                try: prior.append(json.loads(line))
                except Exception as e: log_exception('v249.ledger.read', e)
        entry={'target':int(reg.get('target')),'manifest_sha256':saved_hash,'lines':int(reg.get('lines',len(pcombos))),'realized':combo,'captured_5of5':bool(captured),'portfolio_position':pos,'evaluated_utc':result['evaluated_utc']}
        by={str(x.get('manifest_sha256')):x for x in prior if x.get('manifest_sha256')}; by[str(saved_hash)]=entry
        ordered=sorted(by.values(), key=lambda x:int(x.get('target',0)))
        ledger.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in ordered),encoding='utf-8')
        same=[x for x in ordered if int(x.get('lines',0))==int(entry['lines'])]
        cumulative=exact5_binomial_evidence_v244(len(same), int(sum(bool(x.get('captured_5of5')) for x in same)), int(entry['lines']))
        cumulative.update({'evidence_class':'prospective_preregistered_v249','ledger':str(ledger)})
        result['cumulative_prospective_evidence']=cumulative
    return result

@dataclass(frozen=True)
class RunConfig:
    config: Optional[str] = None
    history: Optional[str] = None
    target: Optional[int] = None
    expected_last: Optional[int] = None
    lines: int = 30
    candidate_pool: int = 5000
    backtest: int = 300
    frozen: int = 500
    train_examples: int = 1200
    negatives: int = 120
    validation_negatives: int = 120
    hard_negative_ratio: float = 0.80
    realized_result: Optional[str] = None
    seed: int = 777
    out_dir: Optional[str] = None
    model_dir: Optional[str] = None
    force_retrain: bool = False
    no_save_training: bool = False
    no_ml: bool = False
    no_gpu: bool = False
    gpu_required: bool = False
    gpu_device: str = 'cuda'
    xgb_estimators: int = 1000
    validation_xgb_estimators: int = 250
    v239_ranker_estimators: int = 350
    wf_retrain_every: int = 10
    min_gate_history: int = 60
    gate_prob_floor: float = 0.64
    gate_delta_floor: float = 1.0
    secondary_prob_floor: float = 0.70
    restricted_prob_floor: float = 0.84
    shared_cache_dir: Optional[str] = None
    lock_raw: int = 10
    master_cache_start: int = 0
    optuna_trials: int = 0
    optuna_every: int = 3
    mirage_topk: int = 100
    mirage_memory: int = 12
    v241_bootstrap_samples: int = 500
    v241_min_p_better: float = 0.60
    v241_min_edge_pct: float = 0.25
    v242_allocation_lookback: int = 300
    v242_allocation_beam: int = 72
    v242_allocation_half_life: float = 90.0
    v243_ltr_seeds: int = 3
    v243_ltr_topk: int = 30
    v245_adv_per_source: int = 32
    v245_adv_max_per_target: int = 160
    v245_adv_memory: int = 300
    v245_adv_sources: str = 'ltr_adv_exact5,ltr_ndcg_exact5,v241_fusion,binary,heuristic'
    v246_sampler_negatives: int = 135
    v246_arm_seeds: int = 2
    v246_sampler_arms: str = 'balanced:0.45,0.35,0.20;hard:0.65,0.25,0.10;ultra:0.85,0.15,0.00'
    v248_state_dir: Optional[str] = None
    v248_import_v246_dir: Optional[str] = None
    v248_import_v246_model_dir: Optional[str] = None
    v248_full_refresh: bool = False
    v249_state_dir: Optional[str] = None
    v249_import_v248_state_dir: Optional[str] = None
    v249_import_v248_model_dir: Optional[str] = None
    v249_full_refresh: bool = False
    v249_candidate_depth: int = 5000
    v249_max_candidate_depth: int = 40000
    v249_lock_top: int = 3
    v249_reference_quantile: float = 0.9995
    v249_quality_weight: float = 0.78
    v249_diversity_weight: float = 0.22
    v249_redundancy_penalty: float = 0.10
    v249_milp_time_limit: float = 15.0
    v249_milp_rel_gap: float = 0.002
    v244_alpha: float = 0.05
    v244_multiple_testing: str = 'holm'
    v244_significance_lookback: int = 300
    prospective_register: bool = False
    prospective_registry_dir: Optional[str] = None
    evaluate_registration: Optional[str] = None
    progress_every: int = 10
    quiet: bool = False
    force: bool = False

    @classmethod
    def from_namespace(cls, ns: argparse.Namespace) -> 'RunConfig':
        valid = {f.name for f in fields(cls)}
        values = {k: v for k, v in vars(ns).items() if k in valid}
        return cls(**values)

def load_toml_config_v248(path: Path) -> Dict[str, object]:
    """Load TOML into argparse-compatible defaults without external dependencies."""
    with path.open('rb') as fh:
        data = tomllib.load(fh)
    out: Dict[str, object] = {}

    def walk(obj):
        for k, v in obj.items():
            key = str(k).replace('-', '_')
            if isinstance(v, dict):
                walk(v)
            else:
                out[key] = v
    walk(data)
    return out

def validate_config_v248(args) -> None:
    checks = [
        (1 <= int(args.lines) <= UNIVERSE_SIZE, 'lines fuera de rango'),
        (int(args.candidate_pool) >= int(args.lines), 'candidate_pool debe ser >= lines'),
        (int(args.backtest) >= 0, 'backtest debe ser >= 0'),
        (int(args.frozen) >= 0, 'frozen debe ser >= 0'),
        (int(args.train_examples) >= 80, 'train_examples debe ser >= 80'),
        (int(args.negatives) >= 1, 'negatives debe ser >= 1'),
        (int(args.validation_negatives) >= 1, 'validation_negatives debe ser >= 1'),
        (0.0 <= float(args.hard_negative_ratio) <= 1.0, 'hard_negative_ratio debe estar en [0,1]'),
        (int(args.xgb_estimators) >= 10, 'xgb_estimators debe ser >= 10'),
        (int(args.validation_xgb_estimators) >= 10, 'validation_xgb_estimators debe ser >= 10'),
        (int(args.v239_ranker_estimators) >= 10, 'ranker_estimators debe ser >= 10'),
        (int(args.wf_retrain_every) >= 1, 'wf_retrain_every debe ser >= 1'),
        (int(args.min_gate_history) >= 1, 'min_gate_history debe ser >= 1'),
        (int(args.v241_bootstrap_samples) >= 20, 'bootstrap_samples debe ser >= 20'),
        (0.0 <= float(args.v241_min_p_better) <= 1.0, 'min_p_better debe estar en [0,1]'),
        (float(args.v241_min_edge_pct) >= 0.0, 'min_edge_pct debe ser >= 0'),
        (int(args.v242_allocation_lookback) >= 20, 'allocation_lookback debe ser >= 20'),
        (int(args.v242_allocation_beam) >= 1, 'allocation_beam debe ser >= 1'),
        (float(args.v242_allocation_half_life) > 0.0, 'allocation_half_life debe ser > 0'),
        (int(args.v243_ltr_seeds) >= 1, 'v243_ltr_seeds debe ser >= 1'),
        (int(args.v243_ltr_topk) == int(args.lines), 'v243_ltr_topk debe ser igual a lines'),
        (int(args.v245_adv_per_source) >= 0, 'adv_per_source debe ser >= 0'),
        (int(args.v245_adv_max_per_target) >= int(args.v245_adv_per_source), 'adv_max_per_target debe ser >= adv_per_source'),
        (int(args.v245_adv_memory) >= 1, 'adv_memory debe ser >= 1'),
        (int(args.v246_sampler_negatives) >= 30, 'v246_sampler_negatives debe ser >= 30'),
        (int(args.v246_arm_seeds) >= 1, 'v246_arm_seeds debe ser >= 1'),
        (0.0 < float(args.v244_alpha) < 1.0, 'v244_alpha debe estar en (0,1)'),
        (int(args.v244_significance_lookback) >= 20, 'significance_lookback debe ser >= 20'),
        (int(args.progress_every) >= 1, 'progress_every debe ser >= 1'),
        (not (bool(args.gpu_required) and bool(args.no_gpu)), 'gpu_required y no_gpu son incompatibles'),
        (not (bool(args.gpu_required) and bool(args.no_ml)), 'gpu_required y no_ml son incompatibles'),
        (int(args.v249_candidate_depth) >= int(args.lines), 'v249_candidate_depth debe ser >= lines'),
        (int(args.v249_max_candidate_depth) >= int(args.v249_candidate_depth), 'v249_max_candidate_depth debe ser >= candidate_depth'),
        (int(args.v249_max_candidate_depth) <= UNIVERSE_SIZE, 'v249_max_candidate_depth no puede exceder universo'),
        (0 <= int(args.v249_lock_top) <= int(args.lines), 'v249_lock_top fuera de rango'),
        (0.90 < float(args.v249_reference_quantile) < 1.0, 'v249_reference_quantile debe estar entre 0.90 y 1.0'),
        (float(args.v249_quality_weight) >= 0.0, 'v249_quality_weight debe ser >= 0'),
        (float(args.v249_diversity_weight) >= 0.0, 'v249_diversity_weight debe ser >= 0'),
        (float(args.v249_quality_weight) + float(args.v249_diversity_weight) > 0.0, 'V249 quality+diversity debe ser > 0'),
        (float(args.v249_redundancy_penalty) >= 0.0, 'v249_redundancy_penalty debe ser >= 0'),
        (float(args.v249_milp_time_limit) > 0.0, 'v249_milp_time_limit debe ser > 0'),
        (0.0 <= float(args.v249_milp_rel_gap) <= 0.25, 'v249_milp_rel_gap debe estar en [0,0.25]'),
    ]
    errors = [msg for ok, msg in checks if not ok]
    try:
        _v246_parse_arms(str(args.v246_sampler_arms))
    except Exception as e:
        errors.append(f'v246_sampler_arms inválido: {e}')
    if errors:
        raise ValueError('Configuración V249 inválida: ' + '; '.join(errors))

def format_target_path_v248(value: Optional[str], target: int) -> Optional[str]:
    if value is None:
        return None
    return str(value).replace('{target}', str(int(target)))

def main() -> int:
    ap = argparse.ArgumentParser(description='Chispazo HyperLab V249 Coverage-Constrained Anti-Saturation Exact5 + Prospective Evidence')
    ap.add_argument('--config', default=None, help='Archivo TOML V249; los flags CLI sólo actúan como overrides')
    ap.add_argument('--history', default=None)
    ap.add_argument('--target', type=int, default=None)
    ap.add_argument('--expected-last', type=int, default=None)
    ap.add_argument('--lines', type=int, default=30)
    ap.add_argument('--candidate-pool', type=int, default=5000)
    ap.add_argument('--backtest', type=int, default=300)
    ap.add_argument('--frozen', type=int, default=500)
    ap.add_argument('--train-examples', type=int, default=1200)
    ap.add_argument('--negatives', type=int, default=120)
    ap.add_argument('--validation-negatives', type=int, default=120)
    ap.add_argument('--hard-negative-ratio', type=float, default=0.8)
    ap.add_argument('--realized-result', default=None)
    ap.add_argument('--seed', type=int, default=DEFAULT_SEED)
    ap.add_argument('--out-dir', default=None)
    ap.add_argument('--model-dir', default=None)
    ap.add_argument('--force-retrain', action='store_true')
    ap.add_argument('--reuse-training', dest='force_retrain', action='store_false')
    ap.add_argument('--no-save-training', action='store_true')
    ap.add_argument('--save-training', dest='no_save_training', action='store_false')
    ap.add_argument('--no-ml', action='store_true')
    ap.add_argument('--ml', dest='no_ml', action='store_false')
    ap.add_argument('--no-gpu', action='store_true')
    ap.add_argument('--gpu', dest='no_gpu', action='store_false')
    ap.add_argument('--gpu-required', action='store_true')
    ap.add_argument('--gpu-optional', dest='gpu_required', action='store_false')
    ap.add_argument('--gpu-device', default='cuda')
    ap.add_argument('--xgb-estimators', type=int, default=1000)
    ap.add_argument('--validation-xgb-estimators', type=int, default=250)
    ap.add_argument('--v243-ranker-estimators', '--v242-ranker-estimators', '--v241-ranker-estimators', '--v239-ranker-estimators', dest='v239_ranker_estimators', type=int, default=350)
    ap.add_argument('--wf-retrain-every', type=int, default=10)
    ap.add_argument('--min-gate-history', type=int, default=60)
    ap.add_argument('--gate-prob-floor', type=float, default=0.64)
    ap.add_argument('--gate-delta-floor', type=float, default=1.0)
    ap.add_argument('--secondary-prob-floor', type=float, default=0.7)
    ap.add_argument('--restricted-prob-floor', type=float, default=0.84)
    ap.add_argument('--shared-cache-dir', default=None)
    ap.add_argument('--lock-raw', type=int, default=10)
    ap.add_argument('--master-cache-start', type=int, default=0)
    ap.add_argument('--optuna-trials', type=int, default=0, help='Trials Optuna temporales para XGB binario; 0 desactiva')
    ap.add_argument('--optuna-every', type=int, default=3, help='Ejecutar Optuna cada N retrains WF')
    ap.add_argument('--mirage-topk', type=int, default=100, help='Top falsos positivos causales a recordar por target')
    ap.add_argument('--mirage-memory', type=int, default=12, help='Número de targets previos de espejismos retenidos')
    ap.add_argument('--v242-bootstrap-samples', '--v241-bootstrap-samples', dest='v241_bootstrap_samples', type=int, default=500, help='Bootstrap pareado para P(challenger mejora rank)')
    ap.add_argument('--v242-min-p-better', '--v241-min-p-better', dest='v241_min_p_better', type=float, default=0.6, help='Probabilidad mínima OOS para dar peso a challenger')
    ap.add_argument('--v242-min-edge-pct', '--v241-min-edge-pct', dest='v241_min_edge_pct', type=float, default=0.25, help='Mejora mínima de rank porcentual penalizada')
    ap.add_argument('--v242-allocation-lookback', type=int, default=300, help='Targets OOS usados para repartir las líneas')
    ap.add_argument('--v242-allocation-beam', type=int, default=72, help='Ancho del beam para optimizar las 30 plazas')
    ap.add_argument('--v242-allocation-half-life', type=float, default=90.0, help='Semivida de ponderación reciente del optimizador Top-N')
    ap.add_argument('--v243-ltr-seeds', type=int, default=3, help='Semillas XGBRanker NDCG del ensemble')
    ap.add_argument('--v243-ltr-topk', type=int, default=30, help='Top-K de NDCG; use el mismo valor de --lines')
    ap.add_argument('--v245-adv-per-source', type=int, default=32, help='Falsos positivos OOF por fuente y target')
    ap.add_argument('--v245-adv-max-per-target', type=int, default=160, help='Máximo de negativos adversariales únicos por target')
    ap.add_argument('--v245-adv-memory', type=int, default=300, help='Targets OOF recientes con adversariales retenidos para LTR')
    ap.add_argument('--v245-adv-sources', default=','.join(V245_ADV_SOURCES_DEFAULT), help='Fuentes separadas por coma para hard-negative mining')
    ap.add_argument('--v246-sampler-negatives', type=int, default=135, help='Negativos por query para cada currículo V246; 135 hace exhaustivo el anillo 4/5 del brazo ultra')
    ap.add_argument('--v246-arm-seeds', type=int, default=2, help='Semillas XGBRanker por brazo V246')
    ap.add_argument('--v246-sampler-arms', default='balanced:0.45,0.35,0.20;hard:0.65,0.25,0.10;ultra:0.85,0.15,0.00', help='Currículos 4/5,3/5,global pre-registrados')
    ap.add_argument('--v248-state-dir', '--v247-state-dir', dest='v248_state_dir', default=None, help='Estado persistente OOS/prospectivo entre concursos')
    ap.add_argument('--v248-import-v246-dir', '--v247-import-v246-dir', dest='v248_import_v246_dir', default=None, help='Importa CSV OOS ya calculados por V246 para evitar repetir 300 targets')
    ap.add_argument('--v248-import-v246-model-dir', '--v247-import-v246-model-dir', dest='v248_import_v246_model_dir', default=None, help='Importa master/sampler cache de la corrida V246 existente')
    ap.add_argument('--v248-full-refresh', '--v247-full-refresh', dest='v248_full_refresh', action='store_true', help='Ignora estado incremental y recalcula walk-forward completo')
    ap.add_argument('--v248-incremental', dest='v248_full_refresh', action='store_false', help='Usa estado OOS incremental si existe')
    ap.add_argument('--v249-state-dir', default=None, help='Estado prospectivo separado de V248')
    ap.add_argument('--v249-import-v248-state-dir', default=None, help='Importa sólo evidencia/gate V248; el portafolio V249 empieza prospectivamente')
    ap.add_argument('--v249-import-v248-model-dir', default=None, help='Reutiliza una vez el model-core V248 compatible, sin compartir archivos mutables')
    ap.add_argument('--v249-full-refresh', action='store_true', help='Recalcula gate walk-forward; normalmente no es necesario')
    ap.add_argument('--v249-incremental', dest='v249_full_refresh', action='store_false')
    ap.add_argument('--v249-candidate-depth', type=int, default=5000, help='Profundidad inicial de candidatos gate-approved para MILP')
    ap.add_argument('--v249-max-candidate-depth', type=int, default=40000, help='Profundidad máxima antes de declarar cobertura inviable; nunca relaja límites silenciosamente')
    ap.add_argument('--v249-lock-top', type=int, default=3, help='Líneas elite que MILP intenta preservar si son compatibles con guardrails')
    ap.add_argument('--v249-reference-quantile', type=float, default=0.9995, help='Cuantil de referencia uniforme para límites de concentración')
    ap.add_argument('--v249-quality-weight', type=float, default=0.78)
    ap.add_argument('--v249-diversity-weight', type=float, default=0.22)
    ap.add_argument('--v249-redundancy-penalty', type=float, default=0.10)
    ap.add_argument('--v249-milp-time-limit', type=float, default=15.0, help='Límite de segundos por intento MILP/HiGHS')
    ap.add_argument('--v249-milp-rel-gap', type=float, default=0.002, help='Gap relativo máximo del MILP')
    ap.add_argument('--v244-alpha', type=float, default=0.05, help='Alpha para pruebas de significancia')
    ap.add_argument('--v244-multiple-testing', choices=['holm', 'fdr_bh', 'none'], default='holm', help='Corrección entre estrategias')
    ap.add_argument('--v244-significance-lookback', type=int, default=300, help='Ventana OOS para tests pareados')
    ap.add_argument('--prospective-register', action='store_true', help='Pre-registrar criptográficamente la predicción antes del sorteo')
    ap.add_argument('--no-prospective-register', dest='prospective_register', action='store_false')
    ap.add_argument('--prospective-registry-dir', default=None, help='Directorio de registros prospectivos')
    ap.add_argument('--evaluate-registration', default=None, help='Evaluar un preregistro V249 existente')
    ap.add_argument('--progress-every', type=int, default=10)
    ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--force', action='store_true')
    cfg_path = None
    if '--config' in sys.argv:
        try:
            cfg_path = Path(sys.argv[sys.argv.index('--config') + 1])
        except Exception as e:
            raise SystemExit(f'--config inválido: {e}')
    else:
        for tok in sys.argv[1:]:
            if tok.startswith('--config='):
                cfg_path = Path(tok.split('=', 1)[1])
                break
    if cfg_path is not None:
        defaults = load_toml_config_v248(cfg_path)
        valid_dests = {a.dest for a in ap._actions}
        unknown = sorted((k for k in defaults if k not in valid_dests))
        if unknown:
            raise SystemExit(f'Config V249 contiene claves desconocidas: {unknown}')
        ap.set_defaults(**defaults)
    args = RunConfig.from_namespace(ap.parse_args())
    t0 = time.time()
    validate_config_v248(args)
    adv_sources = tuple((x.strip() for x in str(args.v245_adv_sources).split(',') if x.strip()))
    if not adv_sources:
        adv_sources = V245_ADV_SOURCES_DEFAULT
    if args.evaluate_registration:
        if not args.realized_result:
            print('ERROR: --evaluate-registration requiere --realized-result', file=sys.stderr)
            return 2
        ev = evaluate_prospective_registration_v249(Path(args.evaluate_registration), args.realized_result)
        print(json.dumps(ev, indent=2, ensure_ascii=False))
        return 0
    if not args.history:
        print('ERROR: --history es requerido salvo cuando se usa --evaluate-registration', file=sys.stderr)
        return 2
    configure_progress_v248(enabled=not args.quiet, every=args.progress_every, t0=t0)
    gpu_enabled = not args.no_gpu and (not args.no_ml)
    gpu_status = probe_xgboost_gpu(args.seed, enabled=gpu_enabled, device=str(args.gpu_device))
    model_runtime = ModelRuntime(gpu_enabled=gpu_enabled, gpu_required=bool(args.gpu_required), gpu_device=str(args.gpu_device), gpu_status=gpu_status, xgb_estimators=max(50, int(args.xgb_estimators)))
    progress('Iniciando Chispazo HyperLab V249 Coverage-Constrained Anti-Saturation Exact5 + Prospective Evidence')
    print('\n=== GPU STATUS ===')
    print(json.dumps(gpu_status, indent=2, ensure_ascii=False))
    if model_runtime.gpu_required and (not model_runtime.gpu_available):
        print('ABORTADO: GPU requerida no disponible', file=sys.stderr)
        return 4
    path = Path(args.history)
    if not path.exists():
        print(f'ERROR: no existe {path}', file=sys.stderr)
        return 2
    df = read_history(path)
    audit = audit_history(path, df, args.target, args.expected_last)
    print('\n=== AUDIT ===')
    print(json.dumps(asdict(audit), indent=2, ensure_ascii=False))
    if audit.status != 'PASS' and (not args.force):
        print('ABORTADO por guardrail', file=sys.stderr)
        return 3
    target = audit.target
    out = Path(format_target_path_v248(args.out_dir, target) or f'chispazo_v249_target_{target}')
    out.mkdir(parents=True, exist_ok=True)
    model_dir = Path(format_target_path_v248(args.model_dir, target)) if args.model_dir else out / 'models_v249'
    bundle = None
    master_cache = None
    reused = False
    reason = 'ML desactivado' if args.no_ml else 'pendiente'
    state_dir = Path(format_target_path_v248(args.v249_state_dir, target)) if args.v249_state_dir else model_dir / 'state_v249'
    state_dir.mkdir(parents=True, exist_ok=True)
    v246_model_import = Path(args.v248_import_v246_model_dir) if args.v248_import_v246_model_dir else None
    sampler_runtime = configure_v246_runtime(args, df, model_dir)
    seed_v248_sampler_cache_from_v246(v246_model_import, model_dir)
    if not args.no_ml:
        prod_start = max(80, len(df) - args.train_examples)
        wf_start = max(250, len(df) - max(0, args.backtest)) if args.backtest > 0 else len(df)
        wf_train = min(args.train_examples, max(180, args.backtest * 2))
        wf_cache_start = max(80, wf_start - wf_train) if args.backtest > 0 else prod_start
        frozen_cutoff = len(df) - args.frozen if args.frozen > 0 else len(df)
        frozen_cache_start = max(80, frozen_cutoff - args.train_examples) if args.frozen > 0 else prod_start
        auto_master_start = min(prod_start, wf_cache_start, frozen_cache_start)
        master_start = max(80, args.master_cache_start) if args.master_cache_start > 0 else auto_master_start
        master_start = min(master_start, auto_master_start)
        sig = persistence_signature(audit, args, master_start, len(df))
        sig.update({'engine': 'V249_MODEL_CORE', 'master_start': master_start, 'validation_negatives': int(args.validation_negatives), 'v239_ranker_estimators': int(args.v239_ranker_estimators), 'v246_adv_per_source': int(args.v245_adv_per_source), 'v246_adv_max_per_target': int(args.v245_adv_max_per_target), 'v246_adv_memory': int(args.v245_adv_memory), 'v246_adv_sources': list(adv_sources), 'v246_sampler_negatives': int(args.v246_sampler_negatives), 'v246_arm_seeds': int(args.v246_arm_seeds), 'v246_sampler_arms': str(args.v246_sampler_arms)})
        print('\n=== V249 MODEL-CORE / PERSISTENCIA ===')
        mp = model_dir / 'v249_metadata.json'
        bp = model_dir / 'v249_model_bundle.joblib'
        cp = model_dir / 'v249_master_causal_cache.joblib'
        v248_model_core = Path(args.v249_import_v248_model_dir) if args.v249_import_v248_model_dir else None
        if not args.force_retrain:
            seed_v249_model_core_from_v248(v248_model_core, model_dir, sig)
        if not args.force_retrain and JOBLIB_OK and mp.exists() and bp.exists() and cp.exists():
            try:
                meta = json.loads(mp.read_text(encoding='utf-8'))
                if meta.get('signature') == sig:
                    bundle = joblib.load(bp)
                    master_cache = joblib.load(cp)
                    reused = True
                    reason = 'OK'
                    progress(f'V249 Persistencia HIT: bundle + master cache ({len(master_cache):,} targets)')
            except Exception as e:
                reason = f'carga falló: {e}'
        if not reused:
            cache_neg = max(args.negatives, args.validation_negatives)
            shared_dir = Path(args.shared_cache_dir) if args.shared_cache_dir else state_dir / 'shared_master_cache'
            seed_v248_shared_cache_from_v246(v246_model_import, shared_dir, df, cache_neg, args.seed, args.hard_negative_ratio)
            master_cache, cache_status = load_or_extend_shared_cache_v238(df, shared_dir, master_start, len(df), cache_neg, args.seed, args.hard_negative_ratio)
            progress(f'V248 shared cache status: {cache_status}')
            bundle = train_bundle_v246(master_cache, prod_start, len(df), args.seed, args.xgb_estimators, args.v239_ranker_estimators, ltr_seeds=args.v243_ltr_seeds, ltr_topk=args.v243_ltr_topk, mirage_bank=None, adversarial_bank=None, adv_memory=args.v245_adv_memory, optuna_trials=args.optuna_trials, negatives_per_positive=args.negatives, sampler_runtime=sampler_runtime, model_runtime=model_runtime)
            reason = 'V249 model-core entrenado'
            if not args.no_save_training and JOBLIB_OK:
                model_dir.mkdir(parents=True, exist_ok=True)
                _atomic_joblib_dump(bundle, bp, compress=3)
                _atomic_joblib_dump(master_cache, cp, compress=3)
                tmp = model_dir / 'v249_metadata.json.tmp'
                tmp.write_text(json.dumps({'signature': sig, 'created_at': time.strftime('%Y-%m-%d %H:%M:%S'), 'cache_targets': len(master_cache)}, indent=2), encoding='utf-8')
                os.replace(tmp, mp)
                reason = 'V249 model-core entrenado y guardado'
    v249_state = None
    if not args.v249_full_refresh:
        v249_state = load_v249_state(state_dir)
        if v249_state is None and args.v249_import_v248_state_dir:
            v249_state = import_v248_state_v249(Path(args.v249_import_v248_state_dir))
            if v249_state is not None:
                save_v249_state(state_dir, v249_state)
        if v249_state is not None:
            consume_previous_snapshot_v249(df, audit, state_dir, v249_state, args.lines)
            save_v249_state(state_dir, v249_state)
    wf_summary = wf_detail = wf_ablation = meta_rows = None
    fusion_detail = None
    production_strategy = V249_PORTFOLIO_STRATEGY
    prod_gate = {}
    production_weights = {'heuristic': 1.0}
    production_allocation = {'v241_fusion': args.lines}
    production_bundle = bundle
    if v249_state is not None:
        print('\n=== V249 GATE STATE + PROSPECTIVE PORTFOLIO STATE ===')
        wf_summary, wf_detail, fusion_detail, wf_ablation, meta_rows, production_weights, production_allocation, prod_gate = production_policy_from_state_v249(v249_state, args)
        production_bundle = bundle
        print(json.dumps(asdict(wf_summary), indent=2))
        print('\nPRODUCTION V249 — HOLM GATE (predictive source allocation):')
        print(json.dumps(prod_gate, indent=2, ensure_ascii=False))
        wf_detail.to_csv(out / 'v249_gate_legacy_portfolio_rows.csv', index=False)
        fusion_detail.to_csv(out / 'v249_gate_rank_fusion.csv', index=False)
        wf_ablation.to_csv(out / 'v249_gate_ablation.csv', index=False)
        meta_rows.to_csv(out / 'v249_gate_meta_rows.csv', index=False)
        v249_funnel = sampler_funnel_table_v248(meta_rows, args.lines)
        v249_funnel.to_csv(out / 'v249_sampler_funnel.csv', index=False)
        print('\n=== V249 INHERITED STRATEGY CAPTURE FUNNEL ===')
        print(v249_funnel.to_string(index=False))
    elif args.backtest > 0 and master_cache is not None:
        print('\n=== V249 FULL GATE WALK-FORWARD (ONE-TIME REFRESH) ===')
        wf_train = min(args.train_examples, max(180, args.backtest * 2))
        wf_summary, wf_detail, fusion_detail, wf_ablation, meta_rows, production_bundle, production_weights, production_allocation, prod_gate = walkforward_validate_v248(df, master_cache, args.lines, args.backtest, wf_train, args.seed, max(1, args.wf_retrain_every), max(50, args.validation_xgb_estimators), max(80, min(args.v239_ranker_estimators, args.validation_xgb_estimators)), max(30, args.min_gate_history), bootstrap_samples=args.v241_bootstrap_samples, min_p_better=args.v241_min_p_better, min_edge_pct=args.v241_min_edge_pct, optuna_trials=args.optuna_trials, optuna_every=args.optuna_every, mirage_topk=args.mirage_topk, mirage_memory=args.mirage_memory, negatives_per_positive=args.validation_negatives, allocation_lookback=args.v242_allocation_lookback, allocation_beam=args.v242_allocation_beam, allocation_half_life=args.v242_allocation_half_life, adv_per_source=args.v245_adv_per_source, adv_max_per_target=args.v245_adv_max_per_target, adv_memory=args.v245_adv_memory, adv_sources=adv_sources, ltr_seeds=args.v243_ltr_seeds, alpha=args.v244_alpha, correction=args.v244_multiple_testing, significance_lookback=args.v244_significance_lookback, ops=STRATEGY_REGISTRY['v248'], sampler_runtime=sampler_runtime, model_runtime=model_runtime)
        print(json.dumps(asdict(wf_summary), indent=2))
        print('\nPRODUCTION V249 — HOLM GATE (predictive source allocation):')
        print(json.dumps(prod_gate, indent=2, ensure_ascii=False))
        wf_detail.to_csv(out / 'v249_gate_legacy_portfolio_rows.csv', index=False)
        fusion_detail.to_csv(out / 'v249_gate_rank_fusion.csv', index=False)
        wf_ablation.to_csv(out / 'v249_gate_ablation.csv', index=False)
        meta_rows.to_csv(out / 'v249_gate_meta_rows.csv', index=False)
        v246_funnel = sampler_funnel_table_v248(meta_rows, args.lines)
        v246_funnel.to_csv(out / 'v249_sampler_funnel.csv', index=False)
        print('\n=== V249 INHERITED STRATEGY CAPTURE FUNNEL ===')
        print(v246_funnel.to_string(index=False))
        gate_targets = sorted(set(map(int, meta_rows['target'].dropna().astype(int).tolist()))) if meta_rows is not None and (not meta_rows.empty) else []
        v249_state = {'schema': V249_STATE_SCHEMA, 'origin': 'v249_full_refresh', 'gate_evaluated_targets': gate_targets, 'v249_evaluated_targets': [], 'v249_portfolio_oos': pd.DataFrame(), 'wf_detail': wf_detail, 'fusion_detail': fusion_detail, 'wf_ablation': wf_ablation, 'meta_rows': meta_rows}
        save_v249_state(state_dir, v249_state)
    print('\n=== V249 COVERAGE-CONSTRAINED + ANTI-SATURATION PORTFOLIO 98,280 ===')
    if production_bundle is None:
        production_bundle = bundle
    coverage_cfg = CoverageConfigV249(candidate_depth=int(args.v249_candidate_depth), max_candidate_depth=int(args.v249_max_candidate_depth), lock_top=int(args.v249_lock_top), reference_quantile=float(args.v249_reference_quantile), quality_weight=float(args.v249_quality_weight), diversity_weight=float(args.v249_diversity_weight), redundancy_penalty=float(args.v249_redundancy_penalty), milp_time_limit=float(args.v249_milp_time_limit), milp_rel_gap=float(args.v249_milp_rel_gap))
    if production_bundle:
        coverage_cfg = CoverageConfigV249(candidate_depth=int(args.v249_candidate_depth), max_candidate_depth=int(args.v249_max_candidate_depth), lock_top=int(args.v249_lock_top), reference_quantile=float(args.v249_reference_quantile), quality_weight=float(args.v249_quality_weight), diversity_weight=float(args.v249_diversity_weight), redundancy_penalty=float(args.v249_redundancy_penalty), milp_time_limit=float(args.v249_milp_time_limit), milp_rel_gap=float(args.v249_milp_rel_gap))
        portfolio, ranked, production_snapshot = production_portfolio_v249(df, production_bundle, production_weights, production_allocation, args.lines, coverage_cfg)
    else:
        # No-ML mode still exercises the complete V249 portfolio policy using the heuristic gate only.
        production_weights = {'heuristic': 1.0}
        production_allocation = {'heuristic': int(args.lines)}
        portfolio, ranked, production_snapshot = production_portfolio_v249(df, None, production_weights, production_allocation, args.lines, coverage_cfg)
    ranked.to_csv(out / 'v249_full_ranking_98280.csv', index=False)
    portfolio.to_csv(out / f'v249_selected_{args.lines}_target_{target}.csv', index=False)
    snapshot_path = save_current_snapshot_v249(state_dir, target, audit, prod_gate, production_snapshot)
    if v249_state is None:
        gate_targets = sorted(set(map(int, meta_rows['target'].dropna().astype(int).tolist()))) if meta_rows is not None and (not meta_rows.empty) else []
        v249_state = {'schema': V249_STATE_SCHEMA, 'origin': 'v249', 'wf_detail': wf_detail if wf_detail is not None else pd.DataFrame(), 'fusion_detail': fusion_detail if fusion_detail is not None else pd.DataFrame(), 'wf_ablation': wf_ablation if wf_ablation is not None else pd.DataFrame(), 'meta_rows': meta_rows if meta_rows is not None else pd.DataFrame(), 'gate_evaluated_targets': gate_targets, 'v249_evaluated_targets': [], 'v249_portfolio_oos': pd.DataFrame()}
    v249_state['latest_snapshot_target'] = int(target)
    v249_state['latest_snapshot_path'] = str(snapshot_path) if snapshot_path else None
    save_v249_state(state_dir, v249_state)
    stat_report = statistical_report_v244(wf_detail, meta_rows, args.lines, lookback=args.v244_significance_lookback)
    (out / 'v249_statistical_evidence.json').write_text(json.dumps(stat_report, indent=2, ensure_ascii=False), encoding='utf-8')
    pd.DataFrame(stat_report.get('multiple_strategy_tests', [])).to_csv(out / 'v249_multiple_testing_strategy_tests.csv', index=False)
    coverage_detail = dict(production_snapshot.get('coverage_detail', {})) if production_snapshot else {}
    coverage_detail['coverage_config'] = asdict(coverage_cfg)
    (out / 'v249_concentration_audit.json').write_text(json.dumps(coverage_detail, indent=2, ensure_ascii=False), encoding='utf-8')
    if coverage_detail:
        print('\n=== V249 CONCENTRATION AUDIT ===')
        print(json.dumps(coverage_detail, indent=2, ensure_ascii=False))
    prereg_path = None
    if args.prospective_register:
        reg_dir = Path(format_target_path_v248(args.prospective_registry_dir, target)) if args.prospective_registry_dir else out / 'prospective_registry'
        prereg_path = register_prospective_prediction_v249(reg_dir, target, audit, portfolio, out / 'v249_full_ranking_98280.csv', path, Path(__file__), args, production_weights, production_allocation, stat_report, coverage_detail)
        print('\n=== V249 PROSPECTIVE PREREGISTRATION ===')
        print('Registry:', prereg_path)
        preg = json.loads(prereg_path.read_text(encoding='utf-8'))
        print('Manifest SHA256:', preg['manifest_sha256'])
    print(ranked.head(10)[['rank', 'combo', 'score', 'sum', 'zone', 'overlap_last']].to_string(index=False))
    print(f'\n=== V249 FINAL EXACT5 PORTFOLIO {args.lines} ===')
    print(portfolio.to_string(index=False))
    realized_diag = None
    if args.realized_result:
        try:
            vals = [int(x) for x in args.realized_result.replace('-', ',').split(',') if x.strip()]
            realized = combo_key(vals)
            realized_diag = realized_forensic_v249(df, production_bundle, production_weights, production_allocation, realized, args.lines, coverage_cfg)
            realized_diag.update({'target': int(target), 'allocation_state': prod_gate.get('allocation_detail', {}).get('state')})
            print('\n=== DIAGNOSTICO REAL V249 (EX-POST, NO TRAINING LEAK) ===')
            print(json.dumps(realized_diag, indent=2, ensure_ascii=False))
        except Exception as e:
            print('WARNING realized-result:', e, file=sys.stderr)
    frozen_ablation = frozen_table = None
    frozen_summary = None
    if args.frozen > 0 and master_cache is not None:
        print('\n=== V249 FROZEN LEGACY-SPECIALIST CORROBORATION ===')
        frozen_ablation, frozen_table = frozen_ablation_v239(df, master_cache, args.lines, args.frozen, args.train_examples, args.seed + 100, max(50, args.validation_xgb_estimators), max(80, min(args.v239_ranker_estimators, args.validation_xgb_estimators)), runtime=model_runtime)
        frozen_ablation.to_csv(out / 'v249_frozen_ablation.csv', index=False)
        frozen_table.to_csv(out / 'v249_frozen_strategy_table.csv', index=False)
        print(frozen_table.to_string(index=False))
        frozen_summary = None
    decision, confidence, dec_reason = technical_decision(wf_summary, frozen_summary)
    meta = {'engine': 'V249 Coverage-Constrained Anti-Saturation Exact5 + Statistical/Prospective Evidence', 'target': target, 'history_last': audit.max_concurso, 'production_strategy': V249_PORTFOLIO_STRATEGY, 'production_weights': production_weights, 'production_allocation': production_allocation, 'production_gate': prod_gate, 'gate_config': {'min_history': args.min_gate_history, 'prob_floor': args.gate_prob_floor, 'delta_floor': args.gate_delta_floor, 'secondary_prob_floor': args.secondary_prob_floor, 'restricted_prob_floor': args.restricted_prob_floor}, 'walkforward': asdict(wf_summary) if wf_summary else None, 'frozen_selected_strategy': asdict(frozen_summary) if frozen_summary else None, 'realized_diagnostic': realized_diag, 'decision': decision, 'confidence': confidence, 'reason': dec_reason, 'statistical_evidence': stat_report, 'prospective_registration': str(prereg_path) if prereg_path else None, 'multiple_testing': {'method': args.v244_multiple_testing, 'alpha': args.v244_alpha, 'lookback': args.v244_significance_lookback}, 'v248_adversarial': {'sources': list(adv_sources), 'per_source': args.v245_adv_per_source, 'max_per_target': args.v245_adv_max_per_target, 'memory': args.v245_adv_memory, 'production_adv_rows': int(production_bundle.get('v246_adversarial_rows', 0)) if production_bundle else 0, 'production_query_rows': int(production_bundle.get('v246_query_rows', 0)) if production_bundle else 0}, 'v248_sampler': {'arms': {k: list(v) for k, v in V246_SAMPLER_ARMS.items()}, 'negatives': V246_SAMPLER_NEGATIVES, 'arm_seeds': V246_ARM_SEEDS, 'sampler_bank_targets': int(len(sampler_runtime.bank)), 'production_meta': production_bundle.get('v246_sampler_meta', {}) if production_bundle else {}}, 'v249': {'state_dir': str(state_dir), 'snapshot': str(snapshot_path) if snapshot_path else None, 'residual_strategy': V248_RESIDUAL_STRATEGY, 'coverage_config': asdict(coverage_cfg), 'coverage_detail': coverage_detail, 'incremental': bool(v249_state is not None)}, 'persistence': {'model_dir': str(model_dir), 'reused': reused, 'status': reason}, 'audit': asdict(audit), 'elapsed_sec': round(time.time() - t0, 2)}
    (out / 'v249_certificate.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
    rep = [f'# Chispazo HyperLab V249 — Target {target}\n\n', f'- Production strategy: **v249_coverage_constrained_portfolio**\n', f"- Allocation state: **{prod_gate.get('allocation_detail', {}).get('state', 'n/a')}**\n", f'- Decision: **{decision}** ({confidence}/100)\n', f'- Persistence reused: {reused}\n\n']
    if wf_summary:
        rep += ['## Causal walk-forward\n', pd.DataFrame([asdict(wf_summary)]).to_markdown(index=False), '\n\n']
    rep += ['## Statistical evidence (historical / exploratory)\n', '```json\n' + json.dumps(stat_report, indent=2, ensure_ascii=False) + '\n```\n\n']
    if prereg_path:
        rep += ['## Prospective preregistration\n', f'- File: `{prereg_path}`\n', f'- This is the confirmatory path for future draws.\n\n']
    if wf_detail is not None:
        rep += ['## Gate decisions (last 30)\n', wf_detail.tail(30).to_markdown(index=False), '\n\n']
    if frozen_table is not None:
        rep += ['## Frozen specialist corroboration\n', frozen_table.to_markdown(index=False), '\n\n']
    if realized_diag is not None:
        rep += ['## Realized forensic (ex-post only)\n', '```json\n' + json.dumps(realized_diag, indent=2, ensure_ascii=False) + '\n```\n\n']
    rep += ['## Concentration audit\n', '```json\n' + json.dumps(coverage_detail, indent=2, ensure_ascii=False) + '\n```\n\n']
    rep += ['## Top 20\n', ranked.head(20)[['rank', 'combo', 'score', 'anti_saturation_score', 'sum', 'zone']].to_markdown(index=False), '\n\n', '## Portfolio\n', portfolio.to_markdown(index=False), '\n']
    (out / 'v249_report.md').write_text(''.join(rep), encoding='utf-8')
    print('\n=== V249 TRAINING PERSISTENCE ===')
    print('Model dir:', model_dir)
    print('Reused:', reused)
    print('Status:', reason)
    print('\n=== DECISION ===')
    print(decision)
    print(f'Confidence: {confidence}/100')
    print(dec_reason)
    print('V249 strategy: Holm-gated rank fusion + anti-saturation tie resolution + coverage-constrained Top30')
    print('Allocation:', production_allocation)
    print('Fusion weights:', production_weights)
    print('Multiple testing:', args.v244_multiple_testing, 'alpha=', args.v244_alpha)
    if prereg_path:
        print('Prospective preregister:', prereg_path)
    print('V249 state:', state_dir)
    print('V249 snapshot:', snapshot_path)
    print(f'\nOutputs: {out.resolve()}')
    print(f'Elapsed: {time.time() - t0:.2f}s')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
