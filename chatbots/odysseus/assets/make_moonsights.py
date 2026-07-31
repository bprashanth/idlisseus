"""Regenerate the moonsights brand assets from the source drawing.

    python3 assets/make_moonsights.py            # from chatbots/odysseus/

Inputs   assets/moonsights-src.png   the hand-drawn crescent (ink on paper)
Outputs  static/icons/moonsights.png          ink-as-alpha mark; the shell
         paints it with the theme ink via CSS mask (.eco-brand-ink), so the
         one asset works on light and dark
         static/icons/moonsights-favicon.png  the same ink on a rounded
         paper tile, so the tab icon reads on any browser chrome

The sketch's ink density becomes the alpha channel; the paper (and its
grain) goes fully transparent.
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
SRC = HERE / 'moonsights-src.png'
OUT_MARK = HERE.parent / 'static/icons/moonsights.png'
OUT_FAVICON = HERE.parent / 'static/icons/moonsights-favicon.png'

PAPER = (247, 245, 240)   # --paper
INK = (27, 26, 23)        # --ink (light theme)

im = Image.open(SRC).convert('L')
a = np.asarray(im, dtype=float) / 255.0

# Paper is near-white with texture; ink is dark. Alpha from darkness, with the
# paper floor cut off so texture noise stays fully transparent.
paper = np.percentile(a, 75)          # bulk of the image is paper
alpha = np.clip((paper - a) / (paper - 0.12), 0, 1) ** 1.35
alpha[alpha < 0.08] = 0               # kill paper-grain speckle

# Crop to the drawing, pad to a centred square with a small margin
ys, xs = np.where(alpha > 0.1)
top, bottom, left, right = ys.min(), ys.max(), xs.min(), xs.max()
cw, ch = right - left, bottom - top
side = int(max(cw, ch) * 1.08)
ccx, ccy = (left + right) // 2, (top + bottom) // 2
sq = np.zeros((side, side), dtype=float)
x0, y0 = ccx - side // 2, ccy - side // 2
sx0, sy0 = max(0, x0), max(0, y0)
sx1, sy1 = min(alpha.shape[1], x0 + side), min(alpha.shape[0], y0 + side)
sq[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = alpha[sy0:sy1, sx0:sx1]

# The mark: white RGB + the ink as alpha; 168px keeps the hatching legible
# at the 28px rail size
out = np.zeros((side, side, 4), dtype=np.uint8)
out[..., :3] = 255
out[..., 3] = (sq * 255).astype(np.uint8)
mark = Image.fromarray(out, 'RGBA')
mark.resize((168, 168), Image.LANCZOS).save(OUT_MARK, optimize=True)
print('wrote', OUT_MARK)

# The favicon: ink on a rounded paper tile (64px, radius matching the old
# rx=8-on-32 idli tile)
tile = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
draw = ImageDraw.Draw(tile)
draw.rounded_rectangle([0, 0, 63, 63], radius=16, fill=PAPER + (255,))
sketch = mark.resize((56, 56), Image.LANCZOS)
ink_layer = Image.new('RGBA', sketch.size, INK + (255,))
tile.paste(ink_layer, (4, 4), sketch)
tile.save(OUT_FAVICON, optimize=True)
print('wrote', OUT_FAVICON)
