# TODO: video-gen API provider not chosen yet (Runway/Pika/Kling/Sora-style).
# Once picked, call it per shot in state["storyboard"]["shots"] and fill in
# clip_url + video_gen_response. Keep this function's signature stable so
# swapping providers only touches this file.
def run(state: dict) -> dict:
    shots = state.get("storyboard", {}).get("shots", [])
    clips = [
        {**shot, "video_gen_status": "pending", "clip_url": None, "video_gen_response": None}
        for shot in shots
    ]
    return {"clips": clips, "mock": True}
