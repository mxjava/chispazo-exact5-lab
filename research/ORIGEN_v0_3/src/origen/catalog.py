from .models import make_frame

LENSES = [
("temporal", "Represent observations as ordered transitions.", ["time_order", "lagged_observation"], "A frozen lagged statistic improves prospective log score.", "Temporal dependence is absent or sampling noise.", "Freeze lag and score on untouched future observations."),
("combinatorial", "Represent outcomes in the full valid combination space.", ["universe_size", "subset_frequency", "overlap"], "A predeclared invariant improves held-out score.", "Uniform sampling explains the apparent structure.", "Enumerate the full outcome space and test one frozen invariant."),
("information", "Represent the process through conditional information and code length.", ["conditional_log_score", "code_length"], "A frozen representation yields prospective information gain.", "Compression is due to model selection or leakage.", "Compare prequential code length with a fixed null."),
("symmetry", "Represent outcomes through invariances and transformations.", ["permutation_invariance", "orbit_size"], "A specified symmetry break replicates prospectively.", "The pattern is noise or coordinate artifact.", "Predeclare the group action and transformed controls."),
("compression", "Represent the process by minimum description length.", ["model_description_length", "residual_description_length"], "A compact model compresses untouched data better than null.", "Gain disappears after search complexity is charged.", "Freeze model class and compare total future description length."),
("adversarial", "Treat every pattern as a claim a rival generator must reproduce.", ["null_reproduction_rate", "search_budget"], "The effect survives nulls calibrated to the full search.", "A matched null reproduces the effect.", "Simulate the complete discovery pipeline under matched nulls."),
("observation_process", "Treat measurement, timing, publication and custody as part of the system.", ["timestamp", "source_lineage", "missingness"], "A pre-observation covariate has verified stable association.", "Selection or provenance defects create the association.", "Verify provenance and freeze covariates before outcome availability."),
("meta_scientific", "Represent researcher choices as an adaptive search process.", ["hypothesis_count", "metric_changes", "analysis_path"], "A discovery survives accounting for the full search path.", "Adaptive choices explain the result.", "Log all attempted frames and test on untouched data."),
("causal", "Represent mechanisms as interventions, not correlations.", ["intervention", "confounder_set", "causal_estimand"], "A feasible intervention changes outcomes as predicted.", "Association is confounded or non-causal.", "Specify an estimand and valid intervention or natural experiment."),
("geometric", "Represent observations in alternative metric spaces.", ["distance_definition", "embedding", "stability"], "A frozen geometry is stable and predictive out of sample.", "Geometry is induced by arbitrary scaling.", "Predeclare distance and scaling; validate on untouched data."),
]

def generate_frames(domain, count=10):
    if not 1 <= count <= 1000: raise ValueError("count must be between 1 and 1000")
    out=[]
    for i in range(count):
        lens, rep, obs, claim, rival, test = LENSES[i % len(LENSES)]
        if i >= len(LENSES): lens = f"{lens}_variant_{i // len(LENSES)+1}"
        out.append(make_frame(domain=domain, lens=lens, representation=rep,
            assumptions=["The observation process is documented enough to define the target.", "Test data are not used to invent or tune this frame."],
            observables=obs, falsifiable_claim=claim, null_or_rival=rival,
            prospective_test=test, failure_conditions=["Prospective score is non-positive.", "Multiplicity-adjusted test fails.", "Matched null or provenance audit explains the effect."]))
    return out
