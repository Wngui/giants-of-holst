"""Render all raw art through a local ComfyUI (FLUX.1-schnell). Skips files that already exist,
so delete one to re-roll it. Usage: python gen_art.py  (ComfyUI must be on 127.0.0.1:8188)"""
import json, time, urllib.request, urllib.parse
from pathlib import Path
from content import HEROES, SCENES, STYLE, MAP_STYLE

COMFY = "http://127.0.0.1:8188"
RAW = Path(__file__).parent / "art" / "raw"


def jobs():
    for s in SCENES:
        yield f"map_{s['key']}", f"{MAP_STYLE}, {s['map_prompt']}", 1536, 1024
    for h in HEROES:
        yield f"portrait_{h['key']}", f"portrait of {h['portrait']}, {STYLE}", 768, 768
        for i, (_, _, prompt) in enumerate(h["cards"]):
            yield f"card_{h['key']}_{i}", f"{prompt}, {STYLE}", 768, 640
    yield "card_back", f"ornate symmetrical card back pattern, a giant's footprint inside a crown, gold on deep red, {STYLE}", 640, 896


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
            out.write_bytes(render(prompt, w, h, 1000 + seed))
            print("rendered", name)
