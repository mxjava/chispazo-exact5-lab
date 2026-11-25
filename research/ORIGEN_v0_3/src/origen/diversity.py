"""Measure diversity of proposed research frames without claiming novelty."""
from __future__ import annotations
from itertools import combinations

def frame_diversity(frames: list[dict]) -> dict:
    if not frames: raise ValueError("empty_frame_set")
    lens_counts={}
    for frame in frames:
        lens=str(frame.get("lens","UNKNOWN")); lens_counts[lens]=lens_counts.get(lens,0)+1
    jaccards=[]
    for a,b in combinations(frames,2):
        sa,sb=set(a.get("observables",[])),set(b.get("observables",[])); union=sa|sb
        jaccards.append(len(sa&sb)/len(union) if union else 1.0)
    mean_overlap=sum(jaccards)/len(jaccards) if jaccards else 0.0
    return {"frames":len(frames),"distinct_lenses":len(lens_counts),"lens_counts":lens_counts,
            "distinct_representations":len({f.get("representation") for f in frames}),
            "mean_observable_jaccard":mean_overlap,
            "low_diversity_warning":len(lens_counts)<min(3,len(frames)) or mean_overlap>0.75,
            "interpretation":"Diversity is a diagnostic of search breadth, not evidence that a frame is correct or novel."}
