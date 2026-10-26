"""Vendor demo: generate a storyboard script for one product with the Claude API.

Standalone on purpose - the pipeline's generate_storyboard node is still a
placeholder. No popular-video analysis is fed in yet, so the storyboard is
built from the product details (and optional product images) only.

Usage:
    python storyboard_demo.py product_hoomic_cat_tree.json [--image path ...]
"""
import argparse
import base64
import json
import mimetypes
import os
import time
from datetime import datetime
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel

MODEL = "claude-opus-5-5"
# USD per million tokens (Anthropic pricing page, checked 2026-10-05)
PRICE_IN, PRICE_OUT = 4.00, 20.00

HERE = Path(__file__).parent
load_dotenv(HERE.parent / "backend" / ".env")


class Shot(BaseModel):
    shot_order: int
    duration_seconds: int
    visual_description: str
    selling_point: str
    on_screen_text: str
    prompt_text: str


class Storyboard(BaseModel):
    hook: str
    target_viewer: str
    selling_points: list[str]
    shots: list[Shot]


SYSTEM = """You write storyboard scripts for short vertical (9:16) TikTok product \
advertisements. Each shot will be generated separately by an image-to-video model \
from a real product photo, then joined by a human editor.

Use only facts given in the product details. Do not invent features, prices, \
discounts or claims that are not there.

Write 4 to 8 shots. Each shot's duration_seconds must be between 5 and 10. \
prompt_text is the English prompt sent to the video model: describe the scene, the \
action, the camera movement and the lighting in one paragraph, keep the product's \
colour and shape consistent with the reference photo, and do not ask the model to \
render text. Put any caption in on_screen_text instead; the editor adds it later."""


def image_block(path: Path) -> dict:
    media_type = mimetypes.guess_type(path.name)[0] or "image/webp"
    data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    return {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}}


def to_markdown(product: dict, board: Storyboard, run: dict) -> str:
    lines = [
        f"# Storyboard script: {product['title']}",
        "",
        f"- Product link: {product['product_url']}",
        f"- Generated: {run['generated_at']} with `{run['model']}`",
        f"- Generation time: {run['elapsed_seconds']} s",
        f"- Tokens: {run['input_tokens']} in / {run['output_tokens']} out "
        f"(about US${run['estimated_cost_usd']})",
        f"- Product images sent: {run['images_sent']}",
        "- Popular-video analysis input: none (analysis stage not built yet)",
        "",
        f"**Hook:** {board.hook}",
        "",
        f"**Target viewer:** {board.target_viewer}",
        "",
        "**Selling points:** " + "; ".join(board.selling_points),
        "",
    ]
    for s in board.shots:
        lines += [
            f"## Shot {s.shot_order} ({s.duration_seconds} s)",
            "",
            f"- Visual: {s.visual_description}",
            f"- Selling point: {s.selling_point}",
            f"- On-screen text: {s.on_screen_text}",
            f"- Video prompt: {s.prompt_text}",
            "",
        ]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("product_json", type=Path)
    ap.add_argument("--image", type=Path, action="append", default=[])
    args = ap.parse_args()

    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        raise SystemExit("No Anthropic credentials: set ANTHROPIC_API_KEY in code/backend/.env")

    product = json.loads(args.product_json.read_text())
    content = [image_block(p) for p in args.image]
    content.append({
        "type": "text",
        "text": "Product details:\n" + json.dumps(product, ensure_ascii=False, indent=2)
        + "\n\nWrite the storyboard script for this product.",
    })

    client = anthropic.Anthropic()
    started = time.monotonic()
    try:
        response = client.messages.parse(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM,
            messages=[{"role": "user", "content": content}],
            output_format=Storyboard,
        )
    except anthropic.AuthenticationError:
        raise SystemExit("No valid Anthropic credentials: set ANTHROPIC_API_KEY in code/backend/.env")
    except anthropic.RateLimitError as e:
        raise SystemExit(f"Rate limited, retry after {e.response.headers.get('retry-after', '60')} s")
    except anthropic.APIStatusError as e:
        raise SystemExit(f"API error {e.status_code}: {e.message}")
    except anthropic.APIConnectionError:
        raise SystemExit("Network error reaching the Anthropic API")
    elapsed = round(time.monotonic() - started, 1)

    if response.stop_reason != "end_turn" or response.parsed_output is None:
        raise SystemExit(f"No storyboard returned (stop_reason={response.stop_reason})")
    board = response.parsed_output

    bad = [s.shot_order for s in board.shots if not 5 <= s.duration_seconds <= 10]
    if not 4 <= len(board.shots) <= 8 or bad:
        print(f"WARNING: storyboard is outside the spec (shots={len(board.shots)}, bad durations={bad})")

    usage = response.usage
    run = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "model": response.model,
        "elapsed_seconds": elapsed,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "estimated_cost_usd": round(
            (usage.input_tokens * PRICE_IN + usage.output_tokens * PRICE_OUT) / 1_000_000, 4
        ),
        "images_sent": len(args.image),
    }

    out = HERE / "output"
    out.mkdir(exist_ok=True)
    stem = args.product_json.stem
    (out / f"{stem}_storyboard.json").write_text(
        json.dumps({"run": run, "storyboard": board.model_dump()}, ensure_ascii=False, indent=2)
    )
    (out / f"{stem}_storyboard.md").write_text(to_markdown(product, board, run))
    print(json.dumps(run, indent=2))
    print(f"Wrote {out / (stem + '_storyboard.md')}")


if __name__ == "__main__":
    main()
