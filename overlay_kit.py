"""
overlay_kit.py
Libreria per creare gli overlay dei video di Abcia2 (card, frecce, chip, griglie, transizioni).
Tutto esce su sfondo trasparente (PNG RGBA).

Uso tipico in una chat:
    from overlay_kit import *
    setup()                                   # scarica font e asset (una volta per chat)
    c = comment_card(icon('chat_blue'), ['Tell me', 'in the comments!'], BLUE)
    save(c, 'tell_me')                        # salva in /mnt/user-data/outputs e crea preview
"""
import os, math, random, urllib.request, zipfile, io
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageEnhance

# ------------------------------------------------------------------ configurazione
REPO = "https://raw.githubusercontent.com/Abcia2/overlay-assets/main/"   # cambia se il repo ha un altro nome
WORK = "/home/claude/overlay"
OUT = "/mnt/user-data/outputs"
FONT_URLS = {
    "fredoka":   "https://raw.githubusercontent.com/google/fonts/main/ofl/fredoka/Fredoka%5Bwdth,wght%5D.ttf",
    "baloo":     "https://raw.githubusercontent.com/google/fonts/main/ofl/baloo2/Baloo2%5Bwght%5D.ttf",
    "comfortaa": "https://raw.githubusercontent.com/google/fonts/main/ofl/comfortaa/Comfortaa%5Bwght%5D.ttf",
    "mono":      "https://raw.githubusercontent.com/JetBrains/JetBrainsMono/master/fonts/ttf/JetBrainsMono-Bold.ttf",
}
S = 3  # supersampling: si disegna a 3x e si riduce alla fine

# ------------------------------------------------------------------ palette (accent, scuro)
WHITE = (255, 255, 255, 255)
CARD_BG = (34, 27, 44, 235)          # fondo scuro delle card
PURPLE = (74, 52, 140, 255)          # frecce e pill delle annotazioni
BLUE = (95, 125, 215, 255)
GREEN = (120, 185, 70, 255)
GOLD = (205, 150, 70, 255)
ORANGE = (230, 140, 50, 255)
PINK = (200, 90, 165, 255)
RED = (190, 60, 60, 255)
GREY = (175, 172, 190, 255)
# colori dei bottoni del sito Gacha Story: (chiaro, scuro)
SITE_GREEN = ((174, 238, 118, 255), (95, 150, 45, 255))
SITE_PINK = ((238, 149, 167, 255), (182, 58, 84, 255))
SITE_LAVENDER = ((200, 185, 240, 255), (74, 47, 126, 255))


# ------------------------------------------------------------------ setup e asset
def _get(url, path):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        urllib.request.urlretrieve(url, path)
    return path


REPO_ZIP = "https://codeload.github.com/Abcia2/overlay-assets/zip/refs/heads/main"  # tutto il repo in un colpo


def setup(assets=True):
    """Scarica i font e (se assets=True) tutto il repo GitHub con gli asset. Non serve nessun assets.zip."""
    os.makedirs(OUT, exist_ok=True)
    for name, url in FONT_URLS.items():
        _get(url, f"{WORK}/fonts/{name}.ttf")
    if assets and not os.path.exists(f"{WORK}/assets"):
        try:
            z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(REPO_ZIP).read()))
            for m in z.infolist():
                parts = m.filename.split("/", 1)          # toglie la cartella "overlay-assets-main/"
                if len(parts) < 2 or not parts[1] or m.is_dir():
                    continue
                dest = os.path.join(WORK, "assets", parts[1])
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "wb") as f:
                    f.write(z.read(m))
            print("asset scaricati in", f"{WORK}/assets")
        except Exception as e:
            print("Asset dal repo non disponibili:", e, "(usa i file caricati in chat)")
    print("overlay_kit pronto")


def asset_path(rel):
    """Cerca un asset: prima negli upload della chat, poi nel pacchetto scaricato."""
    for base in ("/mnt/user-data/uploads", f"{WORK}/assets"):
        p = os.path.join(base, rel)
        if os.path.exists(p):
            return p
    raise FileNotFoundError(rel)


def icon(name):
    """icon('chat_blue') -> Image dell'icona in assets/icons/chat_blue.png (oppure un path completo)."""
    if os.path.exists(name):
        return trim(Image.open(name).convert("RGBA"))
    folders = ("icons", "icons_drawn", "logos", "emoticons", "bracelets", "characters", "beads", "")
    for folder in folders:
        try:
            return trim(Image.open(asset_path(os.path.join(folder, name + ".png"))).convert("RGBA"))
        except FileNotFoundError:
            pass
    for folder in folders:  # ultimo tentativo: scarica il singolo file dal repo
        try:
            p = _get(REPO + f"{folder}/{name}.png".lstrip("/"), f"{WORK}/assets/{folder}/{name}.png")
            return trim(Image.open(p).convert("RGBA"))
        except Exception:
            if os.path.exists(f"{WORK}/assets/{folder}/{name}.png"):
                os.remove(f"{WORK}/assets/{folder}/{name}.png")
    raise FileNotFoundError(name)


def font(size, name="fredoka", weight=650):
    f = ImageFont.truetype(f"{WORK}/fonts/{name}.ttf", int(size * S))
    try:
        axes = f.get_variation_axes()
        f.set_variation_by_axes([weight if b"eight" in a["name"] else a["default"] for a in axes])
    except Exception:
        pass
    return f


# ------------------------------------------------------------------ utilita immagini
def trim(im, thr=8):
    a = im.getchannel("A").point(lambda v: 255 if v > thr else 0)
    bb = a.getbbox()
    return im.crop(bb) if bb else im


def fit(im, w, h):
    """Ridimensiona mantenendo le proporzioni per stare in w x h (in pixel finali * S)."""
    k = min(w / im.width, h / im.height)
    return im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)


def finish(big, w, h):
    return big.resize((w, h), Image.LANCZOS)


def shade(c, f=0.75):
    return tuple(int(v * f) for v in c[:3]) + (255,)


def gray(im):
    g = ImageEnhance.Brightness(ImageEnhance.Contrast(ImageOps.grayscale(im.convert("RGB"))).enhance(0.8)).enhance(1.15)
    return Image.merge("RGBA", (g, g, g, im.getchannel("A")))


def recolor(im, dark, light):
    """Ricolora un'icona a due toni (es. il globo blu in viola)."""
    import numpy as np
    a = np.asarray(im.convert("RGBA")).astype(float)
    lum = a[..., 0] * .3 + a[..., 1] * .59 + a[..., 2] * .11
    m = a[..., 3] > 0
    t = np.clip((lum - lum[m].min()) / (lum[m].ptp() + 1e-6), 0, 1)[..., None]
    rgb = np.array(dark[:3]) * (1 - t) + np.array(light[:3]) * t
    return Image.fromarray(np.dstack([rgb, a[..., 3:]]).astype("uint8"), "RGBA")


def round_corners(im, r):
    im = im.convert("RGBA")
    m = Image.new("L", (im.width * 2, im.height * 2), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, m.width - 1, m.height - 1), radius=r * 2, fill=255)
    im.putalpha(Image.composite(im.getchannel("A"), Image.new("L", im.size, 0), m.resize(im.size, Image.LANCZOS)))
    return im


def crop_black_bars(im, thr=30):
    import numpy as np
    a = np.asarray(im.convert("RGB")).astype(int)
    rows = np.where(a.max(axis=(1, 2)) > thr)[0]
    cols = np.where(a.max(axis=(0, 2)) > thr)[0]
    return im.crop((cols[0], rows[0], cols[-1] + 1, rows[-1] + 1))


def save(im, name, preview_bg=(40, 40, 50)):
    """Salva il PNG finale in outputs e una preview su sfondo pieno in /home/claude/preview_<name>.png."""
    path = f"{OUT}/{name}.png"
    im.save(path, optimize=True)
    bg = Image.new("RGBA", (im.width + 40, im.height + 40), preview_bg + (255,))
    bg.alpha_composite(im, (20, 20))
    pv = f"/home/claude/preview_{name}.png"
    k = min(1, 1600 / bg.width)
    bg.convert("RGB").resize((int(bg.width * k), int(bg.height * k))).save(pv)
    print("salvato", path, im.size, "| preview:", pv)
    return path


# ------------------------------------------------------------------ primitive di disegno
def _bez(p0, p1, p2, p3, n=120):
    return [tuple((1 - t) ** 3 * p0[j] + 3 * (1 - t) ** 2 * t * p1[j] + 3 * (1 - t) * t * t * p2[j] + t ** 3 * p3[j]
                  for j in (0, 1)) for t in [i / n for i in range(n + 1)]]


def _stroke(d, pts, w, c):
    pts = [(x * S, y * S) for x, y in pts]
    r = w * S / 2
    d.line(pts, fill=c, width=int(w * S), joint="curve")
    for x, y in (pts[0], pts[-1]):
        d.ellipse((x - r, y - r, x + r, y + r), fill=c)


def draw_arrow(d, p0, p1, p2, p3, color=PURPLE, k=1.0, outline=WHITE):
    """Freccia curva (bezier) con punta a V e bordo bianco: lo stile approvato."""
    pts = _bez(p0, p1, p2, p3)
    layers = ((14 * k, outline), (7 * k, color)) if outline else ((7 * k, color),)
    for w, c in layers:
        _stroke(d, pts, w, c)
        (xa, ya), (xb, yb) = pts[-6], pts[-1]
        an = math.atan2(yb - ya, xb - xa)
        for s in (0.6, -0.6):
            _stroke(d, [(xb, yb), (xb - 18 * k * math.cos(an + s), yb - 18 * k * math.sin(an + s))], w, c)


def draw_label(d, text, cx, cy, color=PURPLE, k=1.0, fnt="fredoka"):
    """Pill etichetta (es. 'Name', 'Table') con bordo bianco."""
    f = font(44 * k, fnt)
    tw = d.textlength(text, font=f) / S
    h = 66 * k
    d.rounded_rectangle(((cx - tw / 2 - 28 * k) * S, (cy - h / 2) * S, (cx + tw / 2 + 28 * k) * S, (cy + h / 2) * S),
                        radius=h / 2 * S, fill=color, outline=WHITE, width=int(5 * k * S))
    d.text((cx * S, cy * S), text, font=f, fill=WHITE, anchor="mm")


def draw_block_arrow_down(d, cx, top, color, h=170, outline=CARD_BG):
    sw, hw, shaft = 90, 210, 80
    poly = [(cx - sw / 2, top), (cx + sw / 2, top), (cx + sw / 2, top + shaft), (cx + hw / 2, top + shaft),
            (cx, top + h), (cx - hw / 2, top + shaft), (cx - sw / 2, top + shaft)]
    P = [(x * S, y * S) for x, y in poly]
    d.polygon(P, fill=color)
    d.line(P + [P[0]], fill=outline, width=12 * S, joint="curve")
    for x, y in P:
        r = 6 * S
        d.ellipse((x - r, y - r, x + r, y + r), fill=outline)


# ------------------------------------------------------------------ componenti
def card(icon_img, title, subtitle=None, pills=(), accent=BLUE, pill_color=None, top_line=None,
         width=None, height=300, icon_box=(180, 170), title_size=72):
    """
    Card scura con bordo colorato e icona a sinistra.
      - title + subtitle (sottotitolo nel colore accent)          es. card SVG / PSD
      - title + pills (pill colorate con testo bianco)            es. 'PC' + 'Mod available'
      - top_line (piccolo, accent) + title (grande)               es. 'Heads up' / 'Be careful on mobile!'
    """
    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    ft, fs, fp = font(title_size), font(44, weight=500), font(44)
    tw = tmp.textlength(title, font=ft) / S
    for t in (subtitle, top_line):
        if t:
            tw = max(tw, tmp.textlength(t, font=fs) / S)
    pw = sum(tmp.textlength(p, font=fp) / S + 70 for p in pills)
    x0 = 50 + icon_box[0] + 50
    W = width or int(x0 + max(tw, pw) + 60)
    H = height
    out = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    d.rounded_rectangle((0, 0, W * S - 1, H * S - 1), radius=50 * S, fill=CARD_BG, outline=accent, width=10 * S)
    if icon_img is not None:
        ic = fit(icon_img, icon_box[0] * S, icon_box[1] * S)
        out.alpha_composite(ic, (int(50 * S + (icon_box[0] * S - ic.width) / 2), int((H * S - ic.height) / 2)))
    x, cy = x0, H / 2
    if top_line:
        d.text((x * S, (cy - 40) * S), top_line, font=fs, fill=accent, anchor="lm")
        d.text((x * S, (cy + 30) * S), title, font=ft, fill=WHITE, anchor="lm")
    elif subtitle:
        d.text((x * S, (cy - 32) * S), title, font=ft, fill=WHITE, anchor="lm")
        d.text((x * S, (cy + 50) * S), subtitle, font=fs, fill=accent, anchor="lm")
    elif pills:
        d.text((x * S, (cy - 45) * S), title, font=ft, fill=WHITE, anchor="lm")
        px, py, ph = x, cy + 50, 72
        for p in pills:
            ptw = d.textlength(p, font=fp) / S
            d.rounded_rectangle((px * S, (py - ph / 2) * S, (px + ptw + 52) * S, (py + ph / 2) * S),
                                radius=ph / 2 * S, fill=pill_color or accent)
            d.text(((px + 26) * S, py * S), p, font=fp, fill=WHITE, anchor="lm")
            px += ptw + 70
    else:
        d.text((x * S, cy * S), title, font=ft, fill=WHITE, anchor="lm")
    return finish(out, W, H)


def comment_card(icon_img, lines, accent=BLUE, arrow=True, size=66):
    """Card 'commenta' (Tell me in the comments, Who's your favorite...) con freccia grossa verso il basso."""
    lines = [l.replace("'", "\u2019") for l in lines]
    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    f = font(size)
    tw = max(tmp.textlength(l, font=f) for l in lines) / S
    ic = fit(icon_img, 999 * S, 170 * S)
    iw = ic.width / S
    pad, gap, cardH, ah, m = 50, 40, 260, 170, 10
    cardW = int(pad + iw + gap + tw + pad)
    W, H = cardW + 2 * m, cardH + 2 * m + (30 + ah if arrow else 0)
    out = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    d.rounded_rectangle((m * S, m * S, (m + cardW) * S, (m + cardH) * S), radius=50 * S, fill=CARD_BG, outline=accent, width=10 * S)
    out.alpha_composite(ic, (int((m + pad) * S), int((m + (cardH - 170) / 2) * S)))
    tx, lh = m + pad + iw + gap, size * 1.27
    y0 = m + cardH / 2 - (len(lines) - 1) * lh / 2
    for i, l in enumerate(lines):
        d.text((tx * S, (y0 + i * lh) * S), l, font=f, fill=WHITE, anchor="lm")
    if arrow:
        draw_block_arrow_down(d, m + cardW / 2, m + cardH + 30, accent, ah)
    return finish(out, W, H)


def chip(text, color, size=52, fnt="fredoka", text_color=WHITE):
    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    f = font(size, fnt)
    tw = tmp.textlength(text, font=f) / S
    W, H = int(tw + 80), int(size * 1.6)
    out = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    d.rounded_rectangle((0, 0, W * S - 1, H * S - 1), radius=H / 2 * S, fill=color)
    d.text((W * S / 2, H * S / 2), text, font=f, fill=text_color, anchor="mm")
    return finish(out, W, H)


def icon_with_chip(icon_img, text, color, icon_size=230, width=None):
    c = chip(text, color)
    W = width or max(c.width, icon_size) + 20
    H = icon_size + 24 + c.height
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ic = fit(icon_img, icon_size, icon_size)
    out.alpha_composite(ic, ((W - ic.width) // 2, (icon_size - ic.height) // 2))
    out.alpha_composite(c, ((W - c.width) // 2, icon_size + 24))
    return out


def annotation_layer(size, arrows=(), labels=(), ghost=None, k=None, color=PURPLE):
    """
    Livello trasparente grande quanto lo screenshot, da sovrapporre a tutto schermo.
      size   = (W, H) dello screenshot
      arrows = [((x0,y0),(c1x,c1y),(c2x,c2y),(x1,y1)), ...]  punti di controllo in pixel dello screenshot
      labels = [('Name', cx, cy), ...]
      ghost  = (x0,y0,x1,y1) contorno tratteggiato a pillola (es. tasto mancante)
      k      = scala (default: larghezza/1066, cioe 1.8 a 1920 e 2.4 a 2560)
    Regola: una freccia (con la sua etichetta) per file, salvo richiesta diversa.
    """
    W, H = size
    k = k or W / 1066
    SS = 2
    global S
    old, S = S, SS
    try:
        out = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
        d = ImageDraw.Draw(out)
        if ghost:
            x0, y0, x1, y1 = ghost
            r = (y1 - y0) / 2
            L = x1 - x0 - 2 * r
            P = 2 * L + 2 * math.pi * r

            def pt(s):
                s %= P
                if s < L: return (x0 + r + s, y0)
                s -= L
                if s < math.pi * r: a = -math.pi / 2 + s / r; return (x1 - r + r * math.cos(a), y0 + r + r * math.sin(a))
                s -= math.pi * r
                if s < L: return (x1 - r - s, y1)
                s -= L; a = math.pi / 2 + s / r; return (x0 + r + r * math.cos(a), y0 + r + r * math.sin(a))
            n = int(P / 70)
            for w, c in ((14 * k * .9, WHITE), (7 * k * .9, color)):
                for i in range(n):
                    _stroke(d, [pt((i + t / 20 * .55) * P / n) for t in range(21)], w, c)
        for a in arrows:
            draw_arrow(d, *a, color=color, k=k)
        for t, cx, cy in labels:
            draw_label(d, t, cx, cy, color=color, k=k)
        return finish(out, W, H)
    finally:
        S = old


def row(images, gap=8, align="bottom", margin=4):
    H = max(i.height for i in images)
    W = sum(i.width for i in images) + gap * (len(images) - 1) + 2 * margin
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x = margin
    for im in images:
        y = {"bottom": H - im.height, "top": 0, "center": (H - im.height) // 2}[align]
        out.alpha_composite(im, (x, y))
        x += im.width + gap
    return out


def grid(images, cols, gap=0, cell=None, rounded=0):
    """Griglia: cols = numero di colonne (6x7 = 6 colonne, 7 righe). cell=(w,h) per celle uguali."""
    cw, ch = cell or (max(i.width for i in images), max(i.height for i in images))
    rows_n = math.ceil(len(images) / cols)
    out = Image.new("RGBA", (cols * cw + (cols - 1) * gap, rows_n * ch + (rows_n - 1) * gap), (0, 0, 0, 0))
    for i, im in enumerate(images):
        if rounded:
            im = round_corners(im, rounded)
        x = (i % cols) * (cw + gap) + (cw - im.width) // 2
        y = (i // cols) * (ch + gap) + (ch - im.height) // 2
        out.alpha_composite(im.convert("RGBA"), (x, y))
    return out


def common_crop(images, pad=5, thr=8):
    """Ritaglia tutte le immagini sullo stesso rettangolo (utile per pose/frame da tenere allineati)."""
    bbs = [i.getchannel("A").point(lambda v: 255 if v > thr else 0).getbbox() for i in images]
    L = max(0, min(b[0] for b in bbs) - pad); T = max(0, min(b[1] for b in bbs) - pad)
    R = max(b[2] for b in bbs) + pad; B = max(b[3] for b in bbs) + pad
    return [i.crop((L, T, R, B)) for i in images]


def text_logo(text, outer=(245, 175, 95), inner=(150, 80, 30), top=(255, 244, 220), bottom=(255, 212, 150)):
    """Scritta 'a bottone' con doppio contorno e sfumatura (stile icona PNG/SVG)."""
    f = font(300 / S, weight=700)
    W, H = 1000, 460
    def mask(sw=0):
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).text((W / 2, H / 2), text, font=f, fill=255, anchor="mm", stroke_width=sw, stroke_fill=255)
        return m
    o = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    o.paste(Image.new("RGBA", (W, H), shade(outer + (255,), .7)), (0, 10), mask(46))
    o.paste(Image.new("RGBA", (W, H), outer + (255,)), (0, 0), mask(46))
    o.paste(Image.new("RGBA", (W, H), inner + (255,)), (0, 0), mask(22))
    g = Image.new("RGBA", (W, H))
    gd = ImageDraw.Draw(g)
    for y in range(H):
        t = y / H
        gd.line([(0, y), (W, y)], fill=tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3)) + (255,))
    o.paste(g, (0, 0), mask())
    return trim(o)


# ------------------------------------------------------------------ icone disegnate (stile: contorno spesso, interno chiaro, ombra)
def _ic():
    Z = 4
    im = Image.new("RGBA", (200 * Z, 200 * Z), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im), (lambda *v: tuple(x * Z for x in v)), Z


def draw_phone(oc, fc):
    im, d, P, Z = _ic()
    d.rounded_rectangle(P(55, 20, 145, 196), radius=22 * Z, fill=shade(oc)); d.rounded_rectangle(P(55, 12, 145, 188), radius=22 * Z, fill=oc)
    d.rounded_rectangle(P(67, 34, 133, 160), radius=8 * Z, fill=fc); d.rounded_rectangle(P(88, 20, 112, 26), radius=3 * Z, fill=fc)
    d.ellipse(P(92, 166, 108, 182), fill=fc)
    return trim(im)


def draw_monitor(oc, fc):
    im, d, P, Z = _ic()
    d.rounded_rectangle(P(60, 166, 140, 186), radius=10 * Z, fill=shade(oc)); d.rounded_rectangle(P(60, 160, 140, 180), radius=10 * Z, fill=oc)
    d.rectangle(P(88, 138, 112, 165), fill=oc)
    d.rounded_rectangle(P(12, 38, 188, 154), radius=18 * Z, fill=shade(oc)); d.rounded_rectangle(P(12, 30, 188, 146), radius=18 * Z, fill=oc)
    d.rounded_rectangle(P(26, 44, 174, 132), radius=8 * Z, fill=fc)
    return trim(im)


def draw_pin(oc, fc):
    im, d, P, Z = _ic()
    d.line([P(100, 120), P(100, 192)], fill=(120, 120, 135, 255), width=10 * Z)
    d.rounded_rectangle(P(48, 104, 152, 128), radius=12 * Z, fill=shade(oc)); d.rounded_rectangle(P(48, 98, 152, 122), radius=12 * Z, fill=oc)
    d.polygon([P(72, 40), P(128, 40), P(138, 104), P(62, 104)], fill=oc); d.polygon([P(82, 50), P(118, 50), P(124, 96), P(76, 96)], fill=fc)
    d.rounded_rectangle(P(58, 10, 142, 48), radius=16 * Z, fill=shade(oc)); d.rounded_rectangle(P(58, 4, 142, 42), radius=16 * Z, fill=oc)
    d.rounded_rectangle(P(70, 14, 130, 32), radius=8 * Z, fill=fc)
    return trim(im.rotate(-30, resample=Image.BICUBIC, expand=True))


def draw_folder(oc, fc):
    im, d, P, Z = _ic()
    d.rounded_rectangle(P(15, 48, 185, 172), radius=16 * Z, fill=shade(oc)); d.rounded_rectangle(P(15, 30, 90, 65), radius=14 * Z, fill=oc)
    d.rounded_rectangle(P(15, 42, 185, 165), radius=16 * Z, fill=oc); d.rounded_rectangle(P(26, 62, 174, 155), radius=10 * Z, fill=fc)
    cx, cy = 100, 107
    d.rounded_rectangle(P(cx - 9, cy - 35, cx + 9, cy + 10), radius=5 * Z, fill=oc)
    d.polygon([P(cx - 29, cy + 2), P(cx + 29, cy + 2), P(cx, cy + 34)], fill=oc)
    return trim(im)


def draw_check(oc, fc):
    im, d, P, Z = _ic()
    d.ellipse(P(20, 28, 180, 188), fill=shade(oc)); d.ellipse(P(20, 20, 180, 180), fill=oc); d.ellipse(P(33, 33, 167, 167), fill=fc)
    d.line([P(65, 102), P(92, 130), P(138, 80)], fill=oc, width=17 * Z, joint="curve")
    for x, y in ((65, 102), (138, 80)):
        r = 8.5 * Z; d.ellipse((x * Z - r, y * Z - r, x * Z + r, y * Z + r), fill=oc)
    return trim(im)


# ------------------------------------------------------------------ transizione a perline
def scatter_transition(pieces, W=2560, H=4200, core=(1350, 2850), decay=380, weights=None, scale=(0.9, 1.35), seed=5):
    """
    Striscia verticale per transizione: piena nella fascia core (nessun pixel trasparente),
    sempre piu rada verso i bordi, nessun pezzo tagliato in alto o in basso.
    weights: lista di pesi per pieces (es. 0.25 per i colori da usare meno).
    """
    import numpy as np
    random.seed(seed); np.random.seed(seed)
    weights = weights or [1] * len(pieces)
    M = 150
    canvas = Image.new("RGBA", (W + 2 * M, H + 2 * M), (0, 0, 0, 0))

    def place(cx, cy):
        b = random.choices(pieces, weights=weights)[0]
        s = random.uniform(*scale)
        b = b.resize((round(b.width * s), round(b.height * s)), Image.LANCZOS)
        y = max(4, min(H - b.height - 4, int(cy - b.height / 2)))
        canvas.alpha_composite(b, (int(cx - b.width / 2 + M), y + M))

    def dens(y):
        if core[0] <= y <= core[1]: return 1
        return math.exp(-((core[0] - y) if y < core[0] else (y - core[1])) / decay)
    avg = sum(p.width * p.height for p in pieces) / len(pieces)
    pts = []
    for _ in range(int(W * H / avg * 4.8)):
        y = random.uniform(0, H)
        if random.random() < dens(y):
            pts.append((random.uniform(-40, W + 40), y))
    random.shuffle(pts)
    for p in pts:
        place(*p)
    for _ in range(40):
        a = np.asarray(canvas)[M + core[0]:M + core[1], M:M + W, 3]
        ys, xs = np.where(a < 250)
        if not len(ys): break
        for i in np.random.permutation(len(ys))[:400]:
            place(xs[i], ys[i] + core[0])
    return canvas.crop((M, M, M + W, M + H))


def draw_tablet(oc, fc):
    im, d, P, Z = _ic()
    d.rounded_rectangle(P(28, 20, 172, 196), radius=20 * Z, fill=shade(oc)); d.rounded_rectangle(P(28, 12, 172, 188), radius=20 * Z, fill=oc)
    d.rounded_rectangle(P(40, 30, 160, 170), radius=8 * Z, fill=fc); d.ellipse(P(96, 18, 104, 26), fill=fc)
    d.rounded_rectangle(P(85, 177, 115, 182), radius=3 * Z, fill=fc)
    return trim(im)


def draw_file(oc, fc):
    """File con angolo piegato e simbolo immagine."""
    Z = 4; N = 200
    def P(*v): return tuple(x * Z for x in v)
    def shape(box, r, cut):
        m = Image.new("L", (N * Z, N * Z), 0); dd = ImageDraw.Draw(m); dd.rounded_rectangle(P(*box), radius=r * Z, fill=255)
        x1, y0 = box[2], box[1]; dd.polygon([P(x1 - cut, y0 - 3), P(x1 + 3, y0 - 3), P(x1 + 3, y0 + cut)], fill=0); return m
    outer = shape((45, 10, 160, 190), 15, 40); inner = shape((56, 21, 149, 179), 8, 34)
    im = Image.new("RGBA", (N * Z, N * Z), (0, 0, 0, 0))
    sm = Image.new("L", im.size, 0); sm.paste(outer, (0, 7 * Z))
    im.paste(Image.new("RGBA", im.size, shade(oc)), (0, 0), sm)
    im.paste(Image.new("RGBA", im.size, oc), (0, 0), outer); im.paste(Image.new("RGBA", im.size, fc), (0, 0), inner)
    d = ImageDraw.Draw(im)
    d.polygon([P(120, 10), P(120, 50), P(160, 50)], fill=oc); d.rounded_rectangle(P(120, 10, 125, 50), radius=2 * Z, fill=oc)
    d.polygon([P(126, 23), P(126, 44), P(147, 44)], fill=shade(fc, .85))
    d.ellipse(P(70, 75, 95, 100), fill=oc)
    d.polygon([P(65, 160), P(100, 110), P(120, 135), P(130, 122), P(145, 160)], fill=oc)
    return trim(im)


# schemi colore (contorno, interno) per le icone disegnate
ICON_COLORS = {
    "green": ((105, 165, 55, 255), (178, 236, 122, 255)),
    "blue": ((74, 104, 190, 255), (205, 215, 250, 255)),
    "pink": ((182, 58, 84, 255), (238, 149, 167, 255)),
    "purple": ((74, 47, 126, 255), (200, 185, 240, 255)),
    "gold": ((170, 135, 55, 255), (240, 208, 125, 255)),
    "orange": ((190, 110, 35, 255), (255, 200, 130, 255)),
}
