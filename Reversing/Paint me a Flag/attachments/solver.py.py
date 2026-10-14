#!/usr/bin/env python3
"""Decode every flag_part_XX with ./solve and build out/montage.png (needs: pip/apt 'pillow').
Run it in the folder that holds flag_part_*.png / flag_part_*.pmaf and the compiled ./solve"""
import glob, os, subprocess, sys
from PIL import Image, ImageChops, ImageDraw

os.makedirs("out", exist_ok=True)
tiles = []
for pmaf in sorted(glob.glob("flag_part_*.pmaf")):
    base = pmaf[:-5]                                   # e.g. flag_part_02
    num = base[-2:]
    im = Image.open(base + ".png").convert("RGB")      # the noisy START canvas
    w, h = im.size
    open("out/start.rgb", "wb").write(im.tobytes())
    print(f"[{base}] {w}x{h}", flush=True)
    if subprocess.run(["./solve", "out/start.rgb", pmaf, "out/final.rgb"]).returncode:
        sys.exit(f"solver failed on {pmaf}")
    res = Image.frombytes("RGB", (w, h), open("out/final.rgb", "rb").read())
    res.save(f"out/part_{num}.png")

    # crop horizontally to the ink, scale to a common height for the montage
    bg = res.getpixel((0, 0))
    x0, _, x1, _ = ImageChops.difference(res, Image.new("RGB", res.size, bg)).getbbox()
    pad = max(10, (x1 - x0) // 25)
    tile = res.crop((max(0, x0 - pad), 0, min(w, x1 + pad), h))
    tile = tile.resize((max(1, tile.width * 200 // h), 200), Image.LANCZOS)
    tiles.append((num, tile, bg))

COLS = 3
rows = [tiles[i:i + COLS] for i in range(0, len(tiles), COLS)]
rw = [sum(t.width + 20 for _, t, _ in r) + 20 for r in rows]
bgc = tiles[0][2]
sheet = Image.new("RGB", (max(rw), len(rows) * 230 + 20), bgc)
d = ImageDraw.Draw(sheet)
for ri, r in enumerate(rows):
    x = 20
    for num, tile, _ in r:
        sheet.paste(tile, (x, 20 + ri * 230))
        d.text((x, 6 + ri * 230), f"part {num}", fill=(150, 60, 60))
        x += tile.width + 20
sheet.save("out/montage.png")
print("\nDone. Open  out/montage.png  and read the parts in order (left->right, top->bottom).")
