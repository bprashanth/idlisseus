"""Regenerate the brand assets from the source drawings.

    python3 assets/make_brand.py            # from chatbots/odysseus/

Inputs
  assets/raven-src.png         the raven silhouette (ink on paper)

Outputs
  static/icons/raven.png           ink-as-alpha mark. The shell paints it with
                                   the theme ink via CSS mask (.eco-brand-ink),
                                   so one asset serves light and dark.
  static/icons/raven-favicon.png   the same ink on a rounded paper tile, so the
                                   tab icon reads on any browser chrome.
  static/icons/raven-cloud.png     the same bird resolved out of data points —
                                   density, not outline, carries the form. Used
                                   large (the landing hero), where the dots are
                                   legible as marks rather than noise.

The ink density of the source becomes the alpha channel; the paper (and its
grain) goes fully transparent. The point cloud samples that same alpha.
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / 'static/icons'
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
    print('wrote', path.name, f'{width}x{h}')
    return img


def point_cloud(alpha, width, dots=1150, seed=7):
    """Resolve the silhouette out of scattered points.

    Rejection sampling against the alpha field: a point survives where the ink
    is. Dot radius grows slightly toward the interior, so the form reads as
    density rather than as an edge — you have to look to see the bird.
    """
    rng = np.random.default_rng(seed)
    h = int(round(alpha.shape[0] * width / alpha.shape[1]))
    scale = 4  # supersample, then downscale — dots stay crisp at any size
    W, H = width * scale, h * scale
    img = Image.new('RGBA', (W, H), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    ah, aw = alpha.shape
    placed = 0
    guard = 0
    while placed < dots and guard < dots * 60:
        guard += 1
        x = rng.random()
        y = rng.random()
        av = alpha[min(ah - 1, int(y * ah)), min(aw - 1, int(x * aw))]
        if av <= 0.06 or rng.random() > av:
            continue
        # Interior dots are a touch larger; edge dots stay fine, so the
        # boundary dissolves instead of drawing itself. Dots stay well apart —
        # the form has to be inferred from where they cluster.
        r = (0.7 + 1.5 * av ** 2) * scale * (width / 420)
        cx, cy = x * W, y * H
        a8 = int(255 * min(1.0, 0.35 + 0.6 * av))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, a8))
        placed += 1

    img = img.resize((width, h), Image.LANCZOS)
    return img


raven = crop_content(ink_alpha(HERE / 'raven-src.png'), margin=1.06, square=True)
mark = save_alpha_png(raven, OUT / 'raven.png', 192)

# Favicon: ink on a rounded paper tile (64px, radius matching the app's tiles).
tile = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
ImageDraw.Draw(tile).rounded_rectangle([0, 0, 63, 63], radius=16, fill=PAPER + (255,))
sketch = mark.resize((54, 54), Image.LANCZOS)
tile.paste(Image.new('RGBA', sketch.size, INK + (255,)), (5, 5), sketch)
tile.save(OUT / 'raven-favicon.png', optimize=True)
print('wrote raven-favicon.png')

# The cryptic hero: the same bird, made of data.
cloud = point_cloud(raven, 420)
cloud.save(OUT / 'raven-cloud.png', optimize=True)
print('wrote raven-cloud.png', cloud.size)
