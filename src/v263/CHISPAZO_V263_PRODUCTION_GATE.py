#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""V263 production wrapper.

Healthy parent:
  parent health PASS -> build specialist islands -> monkey-patch V262 candidate
  eligibility -> run unchanged V262 probability/DRO objective.

Dead parent:
  abort with exit code 4, or emit an explicit structural null hedge only when
  --allow-degraded-hedge is supplied.
"""

import argparse
import importlib.util
import itertools
import json
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def parser():
    ap = argparse.ArgumentParser(description='Chispazo V263 production integrity gate + V262 island adapter')
    ap.add_argument('--ranking', required=True, help='Full V249 ranking, 98,280 rows')
    ap.add_argument('--target', required=True, type=int)
    ap.add_argument('--audit-out-dir', required=True)
    ap.add_argument('--v262-engine', default=str(HERE/'CHISPAZO_V262_EXACT_MASS_DRO.py'))
    ap.add_argument('--v262-config', default=None)
    ap.add_argument('--history', default=None)
    ap.add_argument('--expected-last', type=int, default=None)
    ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--allow-degraded-hedge', action='store_true')
    ap.add_argument('--max-island-extra', type=int, default=8000)
    ap.add_argument('--seed', type=int, default=777)
    ap.add_argument('--hedge-iterations', type=int, default=80000)
    ap.add_argument('--hedge-restarts', type=int, default=6)
    return ap


def combo_index_map():
    return {tuple(c): i for i, c in enumerate(itertools.combinations(range(1, 29), 5))}


def main() -> int:
    a = parser().parse_args()
    integrity = load_module(HERE/'CHISPAZO_V263_INTEGRITY_ISLAND_DRO.py', 'chispazo_v263_integrity')
    cfg = integrity.V263Config(seed=int(a.seed), hedge_iterations=int(a.hedge_iterations), hedge_restarts=int(a.hedge_restarts))
    ranking_path = Path(a.ranking)
    out = Path(a.audit_out_dir); out.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(ranking_path)
    health = integrity.parent_health_audit(df, cfg)
    health.update({'target': int(a.target), 'ranking_path': str(ranking_path), 'ranking_sha256': integrity.sha256_file(ranking_path)})
    (out/f'v263_parent_health_target_{a.target}.json').write_text(json.dumps(health, indent=2, ensure_ascii=False), encoding='utf-8')

    if health['state'] != 'PASS':
        if not a.allow_degraded_hedge:
            manifest = {'state':'ABORTED_PARENT_INTEGRITY','target':int(a.target),'health':health,
                        'statement':'V263 blocked V262 because the Exact5 parent failed integrity.'}
            (out/f'v263_production_manifest_target_{a.target}.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
            print(json.dumps({'state':manifest['state'],'health_state':health['state'],'live_exact5_count':health['live_exact5_count']},indent=2))
            return 4
        hedge, metrics, priority = integrity.null_hedge(df, health, int(a.target), cfg)
        hedge.to_csv(out/f'v263_DEGRADED_NULL_HEDGE_{cfg.lines}_target_{a.target}.csv',index=False)
        priority.to_csv(out/f'v263_number_priority_target_{a.target}.csv',index=False)
        manifest={'state':'DEGRADED_NULL_HEDGE','target':int(a.target),'health':health,'metrics':metrics,
                  'statement':'Research hedge only; V262 was not run because parent Exact5 failed integrity.'}
        (out/f'v263_production_manifest_target_{a.target}.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
        print(json.dumps({'state':manifest['state'],'health_state':health['state'],'metrics':metrics},indent=2,ensure_ascii=False))
        return 0

    islands, island_meta = integrity.candidate_islands(df, health, cfg)
    islands.to_csv(out/f'v263_candidate_islands_target_{a.target}.csv',index=False)
    c2i = combo_index_map()
    ranked_extra=[]
    for _,r in islands.iterrows():
        co=integrity.parse_combo(r['combo'])
        gi=c2i[co]
        ranked_extra.append((float(r['best_component_percentile']), int(r['parent_rank']), int(gi), str(r['combo'])))
    ranked_extra.sort()
    ranked_extra=ranked_extra[:max(0,int(a.max_island_extra))]
    extra_idx=np.asarray([x[2] for x in ranked_extra],dtype=np.int32)

    v262=load_module(Path(a.v262_engine), 'chispazo_v262_under_v263')
    original_candidate_pool=v262._candidate_pool
    merge_stats={'calls':0,'max_base':0,'max_merged':0,'extra_configured':int(len(extra_idx))}

    def v263_candidate_pool(parent_score, scenario_probs, pool_rank):
        base=np.asarray(original_candidate_pool(parent_score,scenario_probs,pool_rank),dtype=np.int32)
        merged=np.unique(np.concatenate([base,extra_idx])).astype(np.int32)
        meanp=np.mean(np.asarray(scenario_probs,float)[:,merged],axis=0)
        s=np.asarray(parent_score,float)
        merged=merged[np.lexsort((merged,-s[merged],-meanp))]
        merge_stats['calls']+=1; merge_stats['max_base']=max(merge_stats['max_base'],int(len(base))); merge_stats['max_merged']=max(merge_stats['max_merged'],int(len(merged)))
        return merged

    v262._candidate_pool=v263_candidate_pool

    old_argv=sys.argv[:]
    argv=[str(Path(a.v262_engine))]
    if a.v262_config: argv += ['--config',a.v262_config]
    if a.history: argv += ['--history',a.history]
    argv += ['--target',str(int(a.target))]
    if a.expected_last is not None: argv += ['--expected-last',str(int(a.expected_last))]
    if a.quiet: argv += ['--quiet']
    sys.argv=argv
    try:
        rc=int(v262.main())
    finally:
        sys.argv=old_argv
    manifest={'state':'V262_DRO_WITH_V263_ISLANDS' if rc==0 else 'V262_FAILED','target':int(a.target),'return_code':rc,
              'health':health,'island_meta':island_meta,'island_adapter':merge_stats,
              'statement':'V263 changed candidate eligibility only. V262 calibrated Exact5 probability/DRO remained the selection objective.'}
    (out/f'v263_production_manifest_target_{a.target}.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False,default=str),encoding='utf-8')
    print(json.dumps({'state':manifest['state'],'island_meta':island_meta,'adapter':merge_stats},indent=2,ensure_ascii=False))
    return rc


if __name__=='__main__':
    raise SystemExit(main())
