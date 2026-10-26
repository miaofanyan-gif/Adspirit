# TODO: call the Claude API with state["content_factors"] to produce a
# storyboard: a list of shot beats, each with a prompt_text and
# duration_seconds, ready to hand to the video-generation API node.
def run(state: dict) -> dict:
    storyboard = {
        "shots": [
            {"shot_order": i, "prompt_text": f"TODO: storyboard beat {i}", "duration_seconds": 8}
            for i in range(1, 4)
        ],
        "mock": True,
    }
    return {"storyboard": storyboard}
