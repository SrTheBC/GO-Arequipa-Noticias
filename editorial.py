"""Redacción editorial local prudente: cintillos específicos y borradores sin inventar datos.

Sin API de redacción, el producto es un borrador breve basado en título/extracto.
No sustituye la verificación del editor ni simula corroboración de otras fuentes.
"""
from __future__ import annotations
import re
import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo


CINTILLOS_ANTIGUOS = {"INFORMACIÓN EN DESARROLLO", "INFORMACION EN DESARROLLO", "NOTICIA EN DESARROLLO"}


def normalize(s):
    value = unicodedata.normalize("NFKD", str(s or "").lower())
    return "".join(ch for ch in value if not unicodedata.combining(ch))


def plain(s):
    # Las entradas provienen de clean() en news_engine; protección adicional mínima.
    return " ".join(re.sub(r"<[^>]*>", "", str(s or "")).split())


# Primero se evalúan las especializaciones, después las categorías generales.
RULES = [
    (r"contraloria|situaciones adversas|informe de control|control concurrente", "CONTRALORÍA ADVIERTE", "#Contraloria"),
    (r"laboratorio de criminalistica", "SEGURIDAD CIUDADANA", "#SeguridadCiudadana"),
    (r"torrentera|defensa riberen|descolmatacion", "PREVENCIÓN ANTE LLUVIAS", "#Prevencion"),
    (r"paraliz|suspend|posterg|entramp|arbitraje", "OBRAS PARALIZADAS", "#ObrasPublicas"),
    (r"desabastec|falta de medicamentos|medicamentos onco", "ALERTA EN SALUD", "#Salud"),
    (r"nacimiento|demografic|poblacion disminuy", "CAMBIO DEMOGRÁFICO", "#Poblacion"),
    (r"feria labor|empleos|puestos de trabajo|ofertas de empleo", "OPORTUNIDAD LABORAL", "#Empleo"),
    (r"estado de emergencia|distritos en emergencia", "PREVENCIÓN Y EMERGENCIA", "#Emergencias"),
    (r"lluvia|vientos fuertes|senamhi|helada|granizo|meteorologic", "ALERTA METEOROLÓGICA", "#Senamhi"),
    (r"asesinat|homicid|feminicidio", "INVESTIGACIÓN POLICIAL", "#SeguridadCiudadana"),
    (r"condena|sentenci|poder judicial|fiscalia|juicio", "JUSTICIA EN AREQUIPA", "#Justicia"),
    (r"penal|inpe|requisa", "SEGURIDAD PENITENCIARIA", "#SeguridadCiudadana"),
    (r"captur|detuv|detenid|desarticul|allanamiento|operativo policial|presunta banda", "OPERATIVO POLICIAL", "#SeguridadCiudadana"),
    (r"atropell|choque|volcadura|accidente de transito", "ACCIDENTE DE TRÁNSITO", "#Transito"),
    (r"incendio|explosion|sismo|derrumbe|rescate", "EMERGENCIA EN AREQUIPA", "#Emergencias"),
    (r"hospital|iren|salud|anemia|vacun|medicinas", "SALUD PÚBLICA", "#Salud"),
    (r"colegio|universidad|estudiantes|educacion|escolar|docentes", "EDUCACIÓN EN AREQUIPA", "#Educacion"),
    (r"carretera|av(\.|enida)? |puente|adoquin|obra vial|infraestructura", "OBRAS VIALES", "#Infraestructura"),
    (r"agua potable|sedapar|corte de agua|represa|sequia", "SERVICIO DE AGUA", "#Agua"),
    (r"alcald|municipalidad|gerente municipal|regidores", "GESTIÓN MUNICIPAL", "#Municipalidad"),
    (r"gobierno regional|gore|consejero regional|gobernador", "GESTIÓN REGIONAL", "#GobiernoRegional"),
    (r"fiscaliz|congreso|diputad|comision multipartidaria", "FISCALIZACIÓN PÚBLICA", "#Fiscalizacion"),
    (r"contamina|basura|residuos|limpieza|rio chili|medio ambiente", "MEDIO AMBIENTE", "#MedioAmbiente"),
    (r"robo|asalto|estafa|delincuen|policia|pnp", "SEGURIDAD CIUDADANA", "#SeguridadCiudadana"),
    (r"festival|concierto|arte|literatura|hay festival|musica", "AGENDA CULTURAL", "#Cultura"),
    (r"futbol|liga 1|deporte|melgar|partido", "ACTUALIDAD DEPORTIVA", "#Deportes"),
    (r"economia|inversion|exportacion|produccion|empres", "ECONOMÍA REGIONAL", "#Economia"),
]

GEO = [
    ("socabaya", "SOCABAYA"), ("cerro colorado", "CERRO COLORADO"),
    ("paucarpata", "PAUCARPATA"), ("yanahuara", "YANAHUARA"),
    ("caylloma", "CAYLLOMA"), ("camana", "CAMANÁ"),
    ("caraveli", "CARAVELÍ"), ("islay", "ISLAY"),
    ("mollendo", "MOLLENDO"), ("majes", "MAJES"),
    ("cayma", "CAYMA"), ("la joya", "LA JOYA"),
    ("chivay", "CHIVAY"), ("sachaca", "SACHACA"),
]


def topic(title, excerpt="", region="arequipa"):
    key = normalize(f"{title} {excerpt}")
    for pattern, caption, hashtag in RULES:
        if re.search(pattern, key, flags=re.I):
            return caption, hashtag
    if region != "arequipa":
        return "ACTUALIDAD NACIONAL", "#Peru"
    for name, presentation in GEO:
        if name in key:
            return f"ACTUALIDAD EN {presentation}"[:40], "#Arequipa"
    return "ACTUALIDAD EN AREQUIPA", "#NoticiasArequipa"


def short_complete(text, max_chars):
    t = plain(text).strip(" .")
    if len(t) <= max_chars:
        return t
    # Jamás cortar una palabra a medias en la pieza gráfica.
    return t[:max_chars+1].rsplit(" ", 1)[0].rstrip(" ,.;:")


def normal_sentence(text):
    t = plain(text).strip().rstrip(".!? ")
    if not t:
        return ""
    return t[0].upper() + t[1:] + "."



# Política del medio: 5 hashtags AL FINAL de cada copy, adicionales a
# la etiqueta de apertura «#Arequipa |» o «#Perú |».
HASHTAG_RE = re.compile(r"(?<!\w)#[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9_]+")
AVISO_NO_PUBLICABLE_RE = re.compile(
    r"^\s*informaci[oó]n pendiente de contraste editorial\.?\s*$", re.I
)


def hashtag_count_final(copy):
    """Cuenta exclusivamente las etiquetas de la última línea."""
    lines = [x.strip() for x in (copy or "").strip().splitlines() if x.strip()]
    if not lines:
        return 0
    last = lines[-1]
    hashtags = HASHTAG_RE.findall(last)
    return len(hashtags) if last == " ".join(hashtags) else 0


def normalize_copy(copy, region, title="", excerpt="", source=""):
    """Quita aviso interno, da encabezado correcto y EXACTAMENTE cinco hashtags finales.

    El cuerpo informativo se conserva; no se añaden hechos ni afirmaciones de
    verificación. Esta función es idempotente y aplica a IA y redacción local.
    """
    text = str(copy or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    prefix = "#Arequipa" if region == "arequipa" else "#Perú"
    extracted_tags = HASHTAG_RE.findall(text)
    paragraphs = []
    for raw in text.split("\n"):
        line = raw.strip()
        if AVISO_NO_PUBLICABLE_RE.fullmatch(line):
            continue
        # Retirar el encabezado geográfico solo de la primera línea, y reconstruirlo.
        if not paragraphs and re.match(r"^#(?:Arequipa|Per[uú])\s*\|", line, re.I):
            line = line.split("|", 1)[1].strip()
        # En el cuerpo los hashtags solamente se utilizan al final.
        line = HASHTAG_RE.sub("", line)
        line = re.sub(r"[ \t]{2,}", " ", line).strip()
        if line:
            paragraphs.append(line)
        elif paragraphs and paragraphs[-1] != "":
            paragraphs.append("")
    while paragraphs and paragraphs[-1] == "":
        paragraphs.pop()
    body = "\n".join(paragraphs).strip()
    if not body:
        # Solo se utiliza un dato proporcionado; evita texto inventado.
        body = normal_sentence(title) if title else ""
    # El primer párrafo lleva obligatoriamente el rótulo geográfico.
    body = f"{prefix} | {body}" if body else f"{prefix} |"

    topic_tag = topic(title, excerpt, region)[1]
    context = normalize(" ".join((title, excerpt)))
    relevant = []
    for name, presentation in GEO:
        if name in context:
            relevant.append("#" + re.sub(r"[^A-Za-z0-9]", "", normalize(presentation)).title())
            break
    # Especializaciones sencillas basadas en términos presentes en la fuente.
    specific_tags = [
        (r"tsunami", "#Tsunami"), (r"simulacro|sismate", "#Simulacro"),
        (r"indeci", "#Indeci"), (r"rio chili", "#RioChili"),
        (r"reniec", "#Reniec"), (r"lluvias?", "#Lluvias"),
        (r"hospital", "#Hospitales"), (r"pn[p]|policia", "#PNP"),
    ]
    relevant += [tag for pattern, tag in specific_tags if re.search(pattern, context)]
    defaults = ["#GOArequipaNoticias", "#Arequipa" if region == "arequipa" else "#Peru", topic_tag]
    fallbacks = (["#NoticiasArequipa", "#ActualidadRegional", "#InformacionLocal"]
                 if region == "arequipa" else
                 ["#NoticiasPeru", "#ActualidadNacional", "#InformacionNacional"])
    final_tags = []
    # Se conservan hashtags que sugirió el editor, una vez asegurada la marca y geografía.
    for candidate in defaults + relevant + extracted_tags + fallbacks:
        candidate = candidate.strip()
        if not HASHTAG_RE.fullmatch(candidate):
            continue
        if candidate.casefold() not in {tag.casefold() for tag in final_tags}:
            final_tags.append(candidate)
        if len(final_tags) == 5:
            break
    return body.rstrip() + "\n\n" + " ".join(final_tags)


def derive_editorial(title, excerpt, region, source="", url="", published="", article=""):
    title = plain(title)
    excerpt = plain(excerpt)
    caption, topic_tag = topic(title, excerpt, region)
    headline = short_complete(title.upper(), 95)
    # Sólo datos que efectivamente vienen del resumen de origen. No inventa cifras ni nombres.
    summary = short_complete(excerpt, 156)
    if summary and len(summary) >= 22:
        bajada = normal_sentence(summary)
    elif title:
        bajada = normal_sentence(short_complete(f"{source or 'La fuente consultada'} informa sobre {title[0].lower() + title[1:]}", 157))
    else:
        bajada = "Consultar la fuente original antes de difundir."

    prefix = "#Arequipa" if region == "arequipa" else "#Perú"
    source_name = plain(source) or "un medio consultado"
    first = normal_sentence(title)
    second = normal_sentence(excerpt)
    lines = [f"{prefix} | {first}"]
    if second and normalize(second).strip(". ") != normalize(first).strip(". "):
        lines.append(second)
    # Un copy básico, breve y atribuido; no simula una cobertura propia ni añade hechos inexistentes.
    lines.append(f"Fuente informativa: {source_name}.")
    copy_text = normalize_copy("\n\n".join(lines), region, title, excerpt, source)
    return {"cintillo": caption, "titulo": headline, "bajada": bajada,
            "copy_text": copy_text, "ai_status": "borrador_basico_revisar"}


def is_legacy_placeholder(s):
    return plain(s).upper() in CINTILLOS_ANTIGUOS
