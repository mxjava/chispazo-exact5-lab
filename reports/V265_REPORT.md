# V265 Physical-Regime Evidence Scanner

History: {'rows': 10887, 'min_concurso': 1363, 'max_concurso': 12249, 'dual_day_pairs': 3163}
Machine-era cutover: 2022-03-10 (3297 draws)

## Same-day Clásico conditioning
- slot_freq: mean exact-set log-lift -0.010254998
- global_repeat: mean exact-set log-lift -0.000662114
- num_repeat: mean exact-set log-lift -0.020579413
- weekday: mean exact-set log-lift -0.039205125
- blend: mean exact-set log-lift -0.023529084

Minimum Holm-adjusted carryover p-value: 0.132797

## Pair/triple persistence
All history: {'n': 10887, 'pairs_holm_sig': 0, 'triples_holm_sig': 0, 'pair_half_pearson': -0.06285995961446844, 'pair_half_spearman': -0.04559364047783834, 'triple_half_pearson': -0.002440132185770268, 'triple_half_spearman': 0.015097646769329348, 'most_extreme_pair': {'pair': '14-28', 'z': 2.8058531696324924, 'p_raw': 0.005018355395163178, 'p_holm': 1.0}, 'most_extreme_triple': {'triple': '13-14-28', 'z': 3.4342446138206424, 'p_raw': 0.0005942077066853707, 'p_holm': 1.0}}
Post-2022: {'n': 3297, 'pairs_holm_sig': 0, 'triples_holm_sig': 1, 'pair_half_pearson': 0.009049060464466888, 'pair_half_spearman': 0.02474325217905768, 'triple_half_pearson': 0.003062608937624912, 'triple_half_spearman': 0.0058365933202990765, 'most_extreme_pair': {'pair': '2-27', 'z': 3.1229546061651905, 'p_raw': 0.0017904536023659315, 'p_holm': 0.6767914616943221}, 'most_extreme_triple': {'triple': '4-11-15', 'z': 4.715281792849738, 'p_raw': 2.4137645238276755e-06, 'p_holm': 0.007907492580059464}}

Best periodic proxy: {'mod': 20.0, 'prior': 448.0, 'n': 3097.0, 'mean_loglift': -0.003625171558441954, 'last1000_mean_loglift': -0.0024632519945042793}
Best motif validation: {'motif': 'pair', 'prior': 3000, 'alpha': 0.1, 'n': 2997, 'discovery_mean_loglift': 0.00011540613100072161, 'validation_mean_loglift': -0.00012502153615399342, 'all_mean_loglift': -4.847813965884311e-06}

DECISION: RESEARCH_ONLY_METADATA_REQUIRED

Next required data: actual machine/ball-set identity, sphere weights/RFID verification and incidents per draw.