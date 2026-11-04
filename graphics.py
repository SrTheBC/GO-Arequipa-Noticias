"""Exportador editorial GO Arequipa: imágenes locales, logo real y recortes ajustables.
No edita automáticamente diseños alojados en Canva.
"""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SIZE = (1080, 1350)


def clamp_float(value, low, high, default):
    try:
        result = float(value)
        if not math.isfinite(result):
            return float(default)
        return max(float(low), min(float(high), result))
    except (TypeError, ValueError):
        return float(default)


def _get(row, key, default):
    try:
        value = row[key]
        return default if value is None else value
    except (KeyError, IndexError, TypeError):
        return default


def font(bold=False, size=42):
    paths = [
        'C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    ]
    for path in paths:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def textwidth(draw, text, ft):
    box = draw.textbbox((0, 0), text, font=ft)
    return box[2] - box[0]


def fit_lines(draw, text, max_width, max_height, start_size=60, min_size=28, bold=True):
    text = ' '.join(str(text or '').split())
    if not text:
        return [], font(bold, start_size), 0
    for size in range(start_size, min_size - 1, -1):
        ft = font(bold, size)
        lines, current = [], ''
        for word in text.split():
            new = (current + ' ' + word).strip()
            if textwidth(draw, new, ft) <= max_width:
                current = new
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        step = round(size * (1.19 if bold else 1.24))
        if lines and all(textwidth(draw, line, ft) <= max_width for line in lines) and len(lines)*step <= max_height:
            return lines, ft, step
    raise ValueError('El titular o texto pequeño es demasiado largo para la plantilla. Redúcelo y vuelve a generar la vista previa.')


def crop_focus(im, target_size, focus_x=50, focus_y=50, zoom=1):
    """Recorte en coordenadas normalizadas: X/Y=0 al inicio y 100 al final.
    El valor Y=32 favorece el tercio superior en retratos; no afirma detectar rostros.
    """
    im = im.convert('RGB')
    dest_w, dest_h = target_size
    zoom = clamp_float(zoom, 1, 3, 1)
    ratio = dest_w / dest_h
    w, h = im.size
    crop_w = min(float(w), float(h) * ratio) / zoom
    crop_h = crop_w / ratio
    crop_x = max(0, w - crop_w) * clamp_float(focus_x, 0, 100, 50) / 100
    crop_y = max(0, h - crop_h) * clamp_float(focus_y, 0, 100, 35) / 100
    return im.crop((round(crop_x), round(crop_y), round(crop_x+crop_w), round(crop_y+crop_h))).resize(target_size, Image.Resampling.LANCZOS)


def gradient(img):
    """Sombra naranja transparente, interpolada sin bucles por píxel de Python."""
    band = Image.new('RGBA', (1, SIZE[1]), (0, 0, 0, 0))
    points=[]
    for y in range(SIZE[1]):
        t = max(0.0, min(1.0, (y-610)/600))
        alpha = int(250 * (t**0.62)) if t else 0
        points.append((255, round(155-62*t), 0, alpha))
    band.putdata(points)
    return Image.alpha_composite(img, band.resize(SIZE, Image.Resampling.NEAREST))


def draw_logo(canvas, logo_path):
    path = Path(str(logo_path)) if logo_path else Path('assets/logo_go.png')
    if not path.is_file():
        raise ValueError('No se encontró el logotipo del medio. Ingresa a «Logo del medio» para subirlo.')
    with Image.open(path) as original:
        logo = original.convert('RGBA')
    logo.thumbnail((175, 175), Image.Resampling.LANCZOS)
    pos=(SIZE[0]-logo.width-36, 38)
    canvas.alpha_composite(logo, pos)


def inset_circle(canvas, inset_path, item):
    if not inset_path or not str(inset_path).strip() or not Path(str(inset_path)).is_file():
        return
    diameter = 315
    with Image.open(inset_path) as source:
        square = crop_focus(source, (diameter, diameter),
                            _get(item,'photo_inset_x',50),_get(item,'photo_inset_y',32),
                            _get(item,'photo_inset_zoom',1)).convert('RGBA')
    # Fondo oscuro para bordes de fotografías de tonos claros.
    draw=ImageDraw.Draw(canvas)
    x,y=37,30
    draw.ellipse((x-4,y-4,x+diameter+4,y+diameter+4),fill='#151515')
    mask=Image.new('L',(diameter,diameter),0)
    ImageDraw.Draw(mask).ellipse((0,0,diameter-1,diameter-1),fill=255)
    canvas.paste(square,(x,y),mask)
    draw=ImageDraw.Draw(canvas)
    draw.ellipse((x-4,y-4,x+diameter+4,y+diameter+4),outline='white',width=10)


def render(item, photo_file, destination, inset_file=None, logo_path=None, preview=False):
    if not photo_file or not str(photo_file).strip():
        raise ValueError('Primero sube una fotografía principal para crear el diseño.')
    path=Path(str(photo_file).strip())
    if not path.is_file():
        raise ValueError('No se encontró la fotografía principal. Vuelve a subirla desde la noticia.')
    if not preview and not _get(item,'photo_rights_confirmed',0):
        raise ValueError('Confirma el permiso de publicación de la imagen antes de exportar.')
    with Image.open(path) as source:
        img=crop_focus(source,SIZE,_get(item,'photo_main_x',50),_get(item,'photo_main_y',36),
                       _get(item,'photo_main_zoom',1)).convert('RGBA')
    img=gradient(img)
    model=_get(item,'model','modelo_1')
    if model=='modelo_2':
        inset_circle(img,inset_file,item)
    draw_logo(img,logo_path)
    dr=ImageDraw.Draw(img)

    cintillo=' '.join(str(_get(item,'cintillo','')).split()).upper()
    titulo=' '.join(str(_get(item,'titulo','')).split()).upper()
    bajada=' '.join(str(_get(item,'bajada','')).split())
    if not all((cintillo,titulo,bajada)):
        raise ValueError('Completa cintillo, título y texto pequeño para poder generar la imagen.')

    margin=80
    maxw=SIZE[0]-2*margin
    head, f_head, h_head=fit_lines(dr,titulo,maxw,360,63,31,True)
    sub, f_sub, h_sub=fit_lines(dr,bajada,maxw,135,29,22,False)
    tag, f_tag, h_tag=fit_lines(dr,cintillo,805,85,32,22,True)
    if len(tag)>2:
        raise ValueError('El cintillo es demasiado largo para su espacio. Acórtalo.')
    tagheight=len(tag)*h_tag+22
    headlineheight=len(head)*h_head
    subtitleheight=len(sub)*h_sub
    # Acomodar desde abajo con área de seguridad de 38 px.
    full=tagheight+23+headlineheight+16+11+25+subtitleheight
    y=max(755,SIZE[1]-42-full)
    if y+full>SIZE[1]-26:
        raise ValueError('Los textos no caben en el diseño. Acorta el titular o el texto pequeño.')
    tagwidth=max(textwidth(dr,t,f_tag) for t in tag)
    dr.rounded_rectangle((margin-10,y-5, min(1040,margin+tagwidth+22), y+tagheight+1),radius=9,fill='#0b0b0b')
    for line in tag:
        dr.text((margin,y+7),line,fill='#ffae21',font=f_tag)
        y+=h_tag
    y += 22+23
    for line in head:
        dr.text((margin,y),line,font=f_head,fill='#070707')
        y+=h_head
    y += 16
    dr.rounded_rectangle((margin,y,margin+120,y+10),radius=4,fill='#111111')
    y += 30
    for line in sub:
        dr.text((margin,y),line,font=f_sub,fill='#101010')
        y+=h_sub

    if preview:
        # Indicación solo de vista previa, nunca se añade al JPG publicado.
        dr.rounded_rectangle((16, SIZE[1]-35,370,SIZE[1]-7), radius=6, fill=(20,20,20,170))
        dr.text((28,SIZE[1]-32),'VISTA PREVIA · NO PUBLICAR',font=font(True,18),fill='white')

    img=img.convert('RGB')
    if hasattr(destination,'write'):
        img.save(destination,'JPEG',quality=90,optimize=True)
        return destination
    out=Path(destination)
    out.parent.mkdir(parents=True,exist_ok=True)
    img.save(out,'JPEG',quality=93,optimize=True)
    return str(out)
