"""Vendor demo: generate shot clips with the Kling 3.0 image-to-video API.

Standalone on purpose - the pipeline's generate_clips node is still a
placeholder. Request and response shapes follow the Kling 3.0 "Image to Video"
API page (create task, then query task by ID).

Usage:
    python kling_demo.py --image first_frame.png --prompt "..." --duration 5 --name test
    python kling_demo.py --image first_frame.png --storyboard output/x_storyboard.json --shots 1,3
"""
import argparse
import base64
import json
import os
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_URL = "https://api-singapore.klingai.com"
POLL_SECONDS = 10
TIMEOUT_SECONDS = 20 * 60

HERE = Path(__file__).parent
load_dotenv(HERE.parent / "backend" / ".env")


def call(method: str, path: str, **kwargs) -> dict:
    headers = {
        "Authorization": f"Bearer {os.environ['VIDEO_GEN_API_KEY']}",
        "Content-Type": "application/json",
    }
    resp = requests.request(method, BASE_URL + path, headers=headers, timeout=60, **kwargs)
    body = resp.json()
    if resp.status_code != 200 or body.get("code") != 0:
        raise SystemExit(f"Kling API error (HTTP {resp.status_code}): {body}")
    return body["data"]


def generate(image: Path, prompt: str, duration: int, resolution: str, name: str) -> dict:
    payload = {
        "contents": [
            {"type": "prompt", "text": prompt},
            {"type": "first_frame", "url": base64.b64encode(image.read_bytes()).decode("utf-8")},
        ],
        "settings": {"resolution": resolution, "duration": duration, "audio": "off", "multi_shot": False},
    }
    started = time.monotonic()
    task_id = call("POST", "/image-to-video/kling-3.0", json=payload)["id"]
    print(f"[{name}] task {task_id} submitted")

    while True:
        task = call("GET", "/tasks", params={"task_ids": task_id})[0]
        if task["status"] in ("succeeded", "failed"):
            break
        if time.monotonic() - started > TIMEOUT_SECONDS:
            raise SystemExit(f"[{name}] task {task_id} still {task['status']} after {TIMEOUT_SECONDS} s")
        time.sleep(POLL_SECONDS)
    elapsed = round(time.monotonic() - started, 1)

    run = {
        "name": name,
        "task_id": task_id,
        "status": task["status"],
        "message": task.get("message"),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "elapsed_seconds": elapsed,
        "first_frame": str(image),
        "prompt": prompt,
        "duration_requested": duration,
        "resolution": resolution,
        "billing": task.get("billing"),
        "clip_file": None,
    }
    if task["status"] == "succeeded":
        video = next(o for o in task["outputs"] if o["type"] == "video")
        clips = HERE / "output" / "clips"
        clips.mkdir(parents=True, exist_ok=True)
        clip = clips / f"{name}.mp4"
        clip.write_bytes(requests.get(video["url"], timeout=300).content)
        run["duration_returned"] = video.get("duration")
        run["clip_file"] = str(clip.relative_to(HERE))
    print(f"[{name}] {task['status']} in {elapsed} s -> {run['clip_file']}")
    return run


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", type=Path, required=True)
    ap.add_argument("--prompt")
    ap.add_argument("--duration", type=int, default=5)
    ap.add_argument("--name", default="clip")
    ap.add_argument("--storyboard", type=Path)
    ap.add_argument("--shots", help="comma-separated shot_order values, e.g. 1,3")
    ap.add_argument("--resolution", default="1080p", choices=["720p", "1080p", "4k"])
    args = ap.parse_args()

    if not os.environ.get("VIDEO_GEN_API_KEY"):
        raise SystemExit("No Kling key: set VIDEO_GEN_API_KEY in code/backend/.env")

    if args.storyboard:
        shots = json.loads(args.storyboard.read_text())["storyboard"]["shots"]
        wanted = {int(n) for n in args.shots.split(",")} if args.shots else None
        jobs = [
            (s["prompt_text"], s["duration_seconds"], f"{args.name}_shot{s['shot_order']}")
            for s in shots if wanted is None or s["shot_order"] in wanted
        ]
    elif args.prompt:
        jobs = [(args.prompt, args.duration, args.name)]
    else:
        ap.error("give --prompt or --storyboard")

    log = HERE / "output" / "kling_runs.json"
    runs = json.loads(log.read_text()) if log.exists() else []
    for prompt, duration, name in jobs:
        runs.append(generate(args.image, prompt, duration, args.resolution, name))
        log.parent.mkdir(exist_ok=True)
        log.write_text(json.dumps(runs, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
