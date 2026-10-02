"""Render all raw art through a local ComfyUI (FLUX.1-schnell). Skips files that already exist,
so delete one to re-roll it. Usage: python gen_art.py  (ComfyUI must be on 127.0.0.1:8188)"""
import json, time, urllib.request, urllib.parse
from pathlib import Path
from content import HEROES, SCENES, STYLE, MAP_STYLE, ITEMS, SKIES, SKY_STYLE, SCREEN_ART, GROUNDS, GROUND_STYLE

COMFY = "http://127.0.0.1:8188"
RAW = Path(__file__).parent / "art" / "raw"
REROLL = {"card_back": 1, "card_thief_4": 1, "card_wizard_1": 1, "card_wizard_2": 1, "portrait_healer": 1, "map_passage": 1, "ground_outskirts": 1, "ground_den": 2, "ground_cart": 1, "item_6": 1, "screen_art": 1}  # bump to get a new seed


def jobs():
    for s in SCENES:
        yield f"map_{s['key']}", f"{MAP_STYLE}, {s['map_prompt']}", 1536, 1024
    for key, prompt in GROUNDS.items():
        yield f"ground_{key}", f"{prompt}, {GROUND_STYLE}", 1536, 1024
    for h in HEROES:
        yield f"portrait_{h['key']}", f"portrait of {h['portrait']}, {STYLE}", 768, 768
        for i, (_, _, prompt) in enumerate(h["cards"]):
            yield f"card_{h['key']}_{i}", f"{prompt}, {STYLE}", 768, 640
    # bare planks: "candle wax" + "no objects" painted candles and emblems onto the border
    yield "table_wood", ("a bare dark old oak tabletop of long worn wooden planks seen from directly above, scratched and "
                         f"weathered, filling the whole frame, {STYLE}"), 1536, 1024
    yield "card_back", f"ornate symmetrical celtic knotwork pattern, gold filigree on deep crimson leather, no symbols, {STYLE}", 640, 896
    # GM desk art, appended so earlier jobs keep their seeds
    for i, (_, _, prompt, _) in enumerate(ITEMS):
        yield f"item_{i}", f"{prompt}, {STYLE}", 768, 640
    for key, (prompt, _, _) in SKIES.items():
        yield f"sky_{key}", f"{prompt} {SKY_STYLE}", 1536, 768
    yield "screen_art", f"{SCREEN_ART}, {STYLE}", 1536, 768
    yield "gm_top", ("A top-down view of an old dark oak tabletop with a large worn crimson leather desk mat in the middle, "
                     f"its edges tooled with a thin gold border pattern, seen from directly above, filling the frame, {STYLE}"), 768, 1536


def workflow(prompt, w, h, seed):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "flux1-schnell-fp8.safetensors"}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["1", 1]}},
        "4": {"class_type": "EmptySD3LatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0],
              "latent_image": ["4", 0], "seed": seed, "steps": 4, "cfg": 1.0, "sampler_name": "euler",
              "scheduler": "simple", "denoise": 1.0}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": "tabletop"}},
    }


def call(path, data=None):
    req = urllib.request.Request(COMFY + path, data=json.dumps(data).encode() if data else None,
                                 headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req).read()


def render(prompt, w, h, seed):
    pid = json.loads(call("/prompt", {"prompt": workflow(prompt, w, h, seed)}))["prompt_id"]
    while True:
        hist = json.loads(call(f"/history/{pid}"))
        if pid in hist:
            img = hist[pid]["outputs"]["7"]["images"][0]
            return call("/view?" + urllib.parse.urlencode(img))
        time.sleep(1)


if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    for seed, (name, prompt, w, h) in enumerate(jobs()):
        out = RAW / f"{name}.png"
        if not out.exists():
            out.write_bytes(render(prompt, w, h, 1000 + seed + 100 * REROLL.get(name, 0)))
            print("rendered", name)
