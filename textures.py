"""Material textures for forge.py's home-made props -> art/tex/<name>.png
  python textures.py --placeholder   flat noisy colours (no ComfyUI needed, for geometry work)
  python textures.py                 paint them with FLUX through ComfyUI, made seamless for tiling
Tiled materials repeat every TILE world units (1 unit = 1 grid square); decals are stretched over one face."""
import random, sys
from pathlib import Path

OUT = Path(__file__).parent / "art" / "tex"
PAINT = "hand-painted stylized fantasy game texture, painterly, flat even lighting, top-down orthographic, no shadows"
# name: (tile size in squares or None for decal, placeholder colour, prompt)
TEXTURES = {
    "plaster": (1.2, (196, 182, 150), "seamless tileable texture of worn cream lime plaster wall with small cracks and dirt"),
    "timber": (0.6, (78, 52, 34), "seamless tileable texture of dark aged oak beam wood grain"),
    "stone": (1.0, (120, 116, 108), "seamless tileable texture of rough grey fieldstone masonry wall, irregular stones and mortar"),
    "roof": (0.8, (138, 62, 44), "seamless tileable texture of overlapping red-brown clay roof tiles in rows, weathered, moss"),
    "thatch": (0.8, (150, 120, 70), "seamless tileable texture of old straw thatch roof"),
    "planks": (0.7, (120, 84, 52), "seamless tileable texture of weathered wooden planks running vertically, nails"),
    "iron": (0.5, (64, 64, 70), "seamless tileable texture of dark hammered iron with rust spots"),
    "bricks": (1.2, (74, 78, 80), "seamless tileable texture of old dark dungeon stone blocks wall, damp, moss in the cracks"),
    "bark": (0.7, (82, 60, 42), "seamless tileable texture of rough pine tree bark running vertically"),
    "rock": (1.4, (96, 94, 92), "seamless tileable texture of dark grey cliff rock surface with cracks and lichen"),
    "pine": (0.6, (40, 70, 44), "seamless tileable texture of dense dark green pine needles foliage"),
    "leaves": (0.8, (58, 86, 46), "seamless tileable texture of dense dark green oak leaves canopy"),
    "canvas": (0.9, (160, 146, 112), "seamless tileable texture of dirty patched canvas cloth"),
    "cloth_red": (0.6, (130, 34, 34), "seamless tileable texture of rich deep red velvet cloth with gold trim pattern"),
    "gold": (0.4, (212, 170, 60), "seamless tileable texture of a heap of shiny gold coins"),
    "charcoal": (0.5, (34, 30, 28), "seamless tileable texture of black charred burnt wood and ash"),
    "flame": (1.0, (255, 150, 40), "seamless tileable texture of bright orange fire flames"),
    "woodend": (None, (150, 110, 70), "the cut end of a log seen straight on, tree rings, round, filling the image"),
    "window": (None, (60, 54, 48), "a single small medieval house window seen straight on, wooden frame, leaded glass panes, "
                                     "wooden shutters, filling the whole image"),
    "door": (None, (90, 60, 38), "a single medieval wooden plank door seen straight on, iron hinges and ring handle, "
                                 "filling the whole image"),
    "door_iron": (None, (60, 58, 56), "a single heavy dungeon door seen straight on, iron-banded dark wood, rivets, "
                                      "filling the whole image"),
    "banner": (None, (120, 30, 30), "a medieval heraldic banner seen straight on, deep red cloth, a black rat crest with a "
                                    "gold crown, filling the whole image"),
    "sign": (None, (110, 80, 50), "a wooden tavern sign seen straight on, painted tankard of ale, no text, filling the image"),
    # recoloured variants and floor colours used by forge.py (placeholder colours, no painted version yet)
    "plaster_white": (1.2, (190, 186, 176), None), "plaster_rose": (1.2, (176, 140, 128), None),
    "shingle": (0.8, (110, 70, 52), None), "wicker": (0.7, (140, 110, 60), None),
    "sewer_stone": (2.0, (70, 76, 72), None), "dirt_road": (2.5, (104, 86, 64), None),
    # painted pieces copied in by forge.py (art/raw/gm_top.png, build.py's art/out/screen_*): placeholders until then
    "gm_top": (None, (60, 30, 28), None),
    **{f"screen_{side}_{i}": (None, (200, 180, 150), None) for side in ("out", "in") for i in range(3)},
}


def placeholder(name, colour):
    from PIL import Image, ImageDraw, ImageFilter   # lazy: forge.py imports this table inside Blender, which has no Pillow
    rnd = random.Random(name)
    im = Image.new("RGB", (256, 256), colour)
    d = ImageDraw.Draw(im)
    for _ in range(260):   # soft mottling: fine speckle read as grain once tiled over walls and roofs
        x, y, r = rnd.randrange(256), rnd.randrange(256), rnd.randrange(4, 14)
        k = rnd.uniform(0.9, 1.08)
        d.ellipse((x - r, y - r, x + r, y + r), fill=tuple(min(255, int(c * k)) for c in colour))
    im = im.filter(ImageFilter.GaussianBlur(4))
    if name == "canvas":   # tents and bedrolls: faded striped ticking instead of a flat beige
        d = ImageDraw.Draw(im)
        for x in range(0, 256, 64):
            d.rectangle((x, 0, x + 22, 255), fill=(112, 58, 44))
            d.rectangle((x + 30, 0, x + 34, 255), fill=(150, 120, 80))
        im = im.filter(ImageFilter.GaussianBlur(1.5))
    return im


def seamless(im):
    """Cross-fade the image with a half-offset copy so its edges wrap."""
    from PIL import Image, ImageChops, ImageDraw, ImageFilter
    w, h = im.size
    shifted = ImageChops.offset(im, w // 2, h // 2)
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    for i in range(min(w, h) // 2):   # 0 at the centre (keep original), 255 near the edges (use shifted)
        d.rectangle((i, i, w - 1 - i, h - 1 - i), outline=int(255 * (1 - i / (min(w, h) / 2)) ** 1.5))
    return Image.composite(shifted, im, mask.filter(ImageFilter.GaussianBlur(8)))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    if "--placeholder" in sys.argv:
        for name, (_, colour, _) in TEXTURES.items():
            placeholder(name, colour).save(OUT / f"{name}.png")
        print(len(TEXTURES), "placeholder textures in", OUT)
    else:
        import gen_art
        from PIL import Image
        for i, (name, (tile, _, prompt)) in enumerate(TEXTURES.items()):
            raw = OUT / f"raw_{name}.png"
            if not raw.exists():
                raw.write_bytes(gen_art.render(f"{prompt}, {PAINT}", 1024, 1024, 4200 + i))
                print("painted", name)
            im = Image.open(raw).convert("RGB")
            (seamless(im) if tile else im).resize((512, 512), Image.LANCZOS).save(OUT / f"{name}.png")
