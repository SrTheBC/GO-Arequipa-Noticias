"""Piezas originales de estilo GO Arequipa en JPG; no modifica diseños alojados en Canva."""
import os
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

SIZE = (1080, 1350)


def font(bold=False, size=42):
    files = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for p in files:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def fit_lines(d, txt, max_width, max_height, start_size=58, min_size=29, bold=True):
    txt = " ".join(txt.split())
    if not txt:
        return [], font(bold, start_size), 0
    for size in range(start_size, min_size - 1, -1):
        ft = font(bold, size)
        lines = []
        current = ""
        for word in txt.split():
            prospective = (current + " " + word).strip()
            if d.textbbox((0, 0), prospective, font=ft)[2] <= max_width:
                current = prospective
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        line_height = round(size * 1.14)
        if lines and len(lines) * line_height <= max_height and all(d.textbbox((0,0),line,font=ft)[2] <= max_width for line in lines):
            return lines, ft, line_height
    raise ValueError("Texto demasiado largo para la plantilla: acorta el titular o la bajada")


def write_lines(d, lines, ft, x, y, step, fill="#090909", spacing=0):
    for s in lines:
        d.text((x, y), s, font=ft, fill=fill, stroke_width=0)
        y += step + spacing
    return y


def logo(draw, canvas):
    logo_path = Path("assets/logo_go.png")
    if logo_path.exists():
        im = Image.open(logo_path).convert("RGBA")
        im.thumbnail((166, 166))
        canvas.paste(im, (880, 40), im)
    else:
        draw.ellipse((891, 47, 1042, 198), fill="#f7ae00", outline="#101010", width=5)
        draw.text((917, 71), "GO", font=font(True, 49), fill="black")
        draw.text((905, 136), "AREQUIPA", font=font(True, 18), fill="black")
        draw.text((925, 159), "NOTICIAS", font=font(True, 13), fill="black")


def fade(canvas):
    # Degradado naranja editorial inspirado en capturas del usuario.
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    px = layer.load()
    for y in range(650, SIZE[1]):
        amount = min(1.0, max(0, (y - 650) / 500))
        a = int(245 * (amount ** 0.60))
        for x in range(SIZE[0]):
            px[x, y] = (255, int(150 - 70 * amount), 0, a)
    return Image.alpha_composite(canvas, layer)


def inset_circle(canvas, inset_file):
    if not inset_file or not str(inset_file).strip() or not Path(inset_file).is_file():
        return canvas
    diameter = 290
    sample = ImageOps.fit(Image.open(inset_file).convert("RGB"), (diameter, diameter), method=Image.Resampling.LANCZOS)
    mask = Image.new("L", (diameter, diameter), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse((0, 0, diameter-1, diameter-1), fill=255)
    canvas.paste(sample.convert("RGBA"), (40, 35), mask)
    d = ImageDraw.Draw(canvas)
    d.ellipse((38, 33, 332, 327), outline="white", width=10)
    return canvas


def render(item, photo_file, destination, inset_file=None):
    # Una ruta vacía se convierte en Path("."), que existe pero es una carpeta.
    # En ese caso Image.open("") lanzaba [Errno 2] No such file or directory: ''.
    # Requerimos explícitamente una ruta no vacía a un archivo real.
    if photo_file is None or not str(photo_file).strip():
        raise ValueError("Primero sube una fotografía principal para generar el diseño JPG")
    photo_path = Path(str(photo_file).strip()).expanduser()
    if not photo_path.is_file():
        raise ValueError("No se encontró la fotografía principal. Vuelve a subirla desde la ficha editorial")
    if not item["photo_rights_confirmed"]:
        raise ValueError("Confirma los derechos de uso de la imagen")
    try:
        with Image.open(photo_path) as photograph:
            picture = photograph.convert("RGB")
    except (OSError, ValueError) as exc:
        raise ValueError("No se pudo leer la fotografía principal. Vuelve a subirla como JPG, PNG o WebP") from exc
    img = ImageOps.fit(picture, SIZE, method=Image.Resampling.LANCZOS, centering=(0.5, 0.37)).convert("RGBA")
    img = fade(img)
    if item["model"] == "modelo_2":
        img = inset_circle(img, inset_file)
    dr = ImageDraw.Draw(img)
    logo(dr, img)

    x, width = 80, 925
    head_text = item["titulo"].strip().upper()
    sub_text = item["bajada"].strip()
    if not head_text or not sub_text:
        raise ValueError("Completa titular y bajada primero")
    title_lines, title_ft, title_step = fit_lines(dr, head_text, width, 330, 61, 34)
    sub_lines, sub_ft, sub_step = fit_lines(dr, sub_text, width, 126, 29, 22, False)
    head_height = len(title_lines) * title_step
    sub_height = len(sub_lines) * sub_step
    total = 62 + head_height + 32 + sub_height + 28
    y_top = max(790, 1320 - total)
    tag = " ".join(item["cintillo"].split()).upper()
    tag_lines, tag_font, _ = fit_lines(dr, tag, 820, 40, 30, 23)
    tag_text = tag_lines[0] if tag_lines else "GO AREQUIPA NOTICIAS"
    tw = dr.textbbox((0, 0), tag_text, font=tag_font)[2]
    dr.rounded_rectangle((x - 8, y_top-12, min(1040, x + tw+25), y_top+47), fill="#090909", radius=10)
    dr.text((x + 5, y_top-3), tag_text, font=tag_font, fill="#ffb028")
    pos = write_lines(dr, title_lines, title_ft, x, y_top+70, title_step)
    rule_y = pos + 8
    dr.rounded_rectangle((x, rule_y, x+120, rule_y+10), fill="#080808", radius=4)
    write_lines(dr, sub_lines, sub_ft, x, rule_y+25, sub_step)
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output, "JPEG", quality=92, optimize=True)
    return str(output)
