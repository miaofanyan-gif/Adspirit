# TODO: for each video in state["videos"], pull metrics + transcript/visual
# content and produce an analysis_result (e.g. via Claude on extracted frames
# or captions). Currently just tags each video with a placeholder analysis.
def run(state: dict) -> dict:
    videos = state.get("videos", [])
    analyzed = [
        {**v, "metrics": {"views": None, "likes": None}, "analysis_result": {"mock": True}}
        for v in videos
    ]
    return {"videos": analyzed}
