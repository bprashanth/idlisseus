"""Regenerate the drawn brand assets from the source sketches.

    python3 assets/make_moonsights.py            # from chatbots/odysseus/

Inputs   assets/moonsights-src.png    the hand-drawn crescent (ink on paper)
         assets/idliinsights-src.png  the hand-lettered "idli insights"
Outputs  static/icons/moonsights.png          ink-as-alpha mark; the shell
         paints it with the theme ink via CSS mask (.eco-brand-ink), so the
         one asset works on light and dark
         static/icons/moonsights-favicon.png  the same ink on a rounded
         paper tile, so the tab icon reads on any browser chrome
         static/icons/idli-wordmark.png       ink-as-alpha lettering for the
         landing hero (.eco-wordmark), same theme-ink mask trick

Each sketch's ink density becomes the alpha channel; the paper (and its
grain) goes fully transparent.
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
PAPER = (247, 245, 240)   # --paper
INK = (27, 26, 23)        # --ink (light theme)


def ink_alpha(src):
    """Ink density -> alpha, paper (with its grain) -> fully transparent."""
    im = Image.open(src).convert('L')
    a = np.asarray(im, dtype=float) / 255.0
    paper = np.percentile(a, 75)          # bulk of the image is paper
    alpha = np.clip((paper - a) / (paper - 0.12), 0, 1) ** 1.35
    alpha[alpha < 0.08] = 0               # kill paper-grain speckle
    return alpha


def crop_content(alpha, margin=1.08, square=True):
    ys, xs = np.where(alpha > 0.1)
    top, bottom, left, right = ys.min(), ys.max(), xs.min(), xs.max()
    cw, ch = right - left, bottom - top
    if square:
        side_w = side_h = int(max(cw, ch) * margin)
    else:
        side_w, side_h = int(cw * margin), int(ch * margin)
    ccx, ccy = (left + right) // 2, (top + bottom) // 2
    out = np.zeros((side_h, side_w), dtype=float)
    x0, y0 = ccx - side_w // 2, ccy - side_h // 2
    sx0, sy0 = max(0, x0), max(0, y0)
    sx1 = min(alpha.shape[1], x0 + side_w)
    sy1 = min(alpha.shape[0], y0 + side_h)
    out[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = alpha[sy0:sy1, sx0:sx1]
    return out


def save_alpha_png(alpha, path, width):
    h = int(round(alpha.shape[0] * width / alpha.shape[1]))
    rgba = np.zeros((*alpha.shape, 4), dtype=np.uint8)
    rgba[..., :3] = 255
    rgba[..., 3] = (alpha * 255).astype(np.uint8)
    img = Image.fromarray(rgba, 'RGBA').resize((width, h), Image.LANCZOS)
    img.save(path, optimize=True)
    print('wrote', path, f'{width}x{h}')
    return img


# ---- moonsights: the crescent mark + favicon --------------------------------
moon = crop_content(ink_alpha(HERE / 'moonsights-src.png'), square=True)
mark = save_alpha_png(moon, HERE.parent / 'static/icons/moonsights.png', 168)

# The favicon: ink on a rounded paper tile (64px, radius matching the old
# rx=8-on-32 idli tile)
tile = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
draw = ImageDraw.Draw(tile)
draw.rounded_rectangle([0, 0, 63, 63], radius=16, fill=PAPER + (255,))
sketch = mark.resize((56, 56), Image.LANCZOS)
ink_layer = Image.new('RGBA', sketch.size, INK + (255,))
tile.paste(ink_layer, (4, 4), sketch)
tile.save(HERE.parent / 'static/icons/moonsights-favicon.png', optimize=True)
print('wrote', HERE.parent / 'static/icons/moonsights-favicon.png')

# ---- idli insights: the hand-lettered wordmark ------------------------------
word = crop_content(ink_alpha(HERE / 'idliinsights-src.png'), margin=1.04, square=False)
save_alpha_png(word, HERE.parent / 'static/icons/idli-wordmark.png', 840)
