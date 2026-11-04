import io
import sys
import os
import re
import secrets
import threading
import traceback
from functools import wraps
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv, set_key
load_dotenv()
from flask import Flask, abort, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.utils import secure_filename

import db
import news_engine
import graphics

VERSION = "6.0 - Editor visual + logo oficial"

# Localiza las plantillas tanto en el proyecto como dentro de PyInstaller.
BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
app = Flask(__name__, template_folder=str(BUNDLE_ROOT / "templates"),
            static_folder=str(BUNDLE_ROOT / "static"))
secret = os.getenv("SECRET_KEY", "")
password = os.getenv("ADMIN_PASSWORD", "")
if not secret or len(secret) < 24 or not password or password == "CAMBIAR_POR_CONTRASENA_LARGA":
    raise RuntimeError("Configura SECRET_KEY y ADMIN_PASSWORD seguros en .env antes de iniciar")
app.secret_key = secret
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "false").lower() == "true",
                  MAX_CONTENT_LENGTH=12 * 1024 * 1024)
db.init_db()
# Conservar toda edición manual: actualizar exclusivamente los antiguos cintillos
# genéricos todavía pendientes de aprobación, en la base de datos existente.
db.actualizar_borradores_antiguos()
# Normaliza copys pendientes sin alterar hechos ni noticias aprobadas/publicadas.
db.normalizar_copys_antiguos()
MEDIA = Path(os.getenv("MEDIA_PATH", "data/media"))
MEDIA.mkdir(parents=True, exist_ok=True)
def brand_logo_file():
    """Logo privado configurable; si aún no se copió, usa el incluido en V6."""
    selected = Path(os.getenv("GO_DATA_ROOT", "")) / "assets" / "logo_go.png" if os.getenv("GO_DATA_ROOT") else Path.cwd() / "assets" / "logo_go.png"
    if selected.is_file():
        return selected
    return BUNDLE_ROOT / "assets" / "logo_go.png"


scan_lock = threading.Lock()
scan_state = {"active": False, "result": ""}


def login_required(f):
    @wraps(f)
    def inner(*a, **kw):
        if not session.get("auth"):
            return redirect(url_for("login"))
        return f(*a, **kw)
    return inner


@app.before_request
def check_csrf():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(24)
    if request.method == "POST" and not secrets.compare_digest(request.form.get("csrf", ""), session["csrf"]):
        abort(403)


@app.context_processor
def tokens():
    return {"csrf_token": session.get("csrf", ""), "scan_state": scan_state, "canva_link": "https://canva.link/qb97kyldbrboag9", "storage_root": os.getenv("GO_DATA_ROOT", str(Path(db.DB_PATH).resolve().parent)), "app_version": VERSION}


@app.template_filter("lima")
def fmt_lima(value):
    try:
        return datetime.fromisoformat(value).astimezone(ZoneInfo("America/Lima")).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return value


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if secrets.compare_digest(request.form.get("password", ""), password):
            session.clear()
            session["auth"] = True
            session["csrf"] = secrets.token_hex(24)
            return redirect(url_for("index"))
        flash("Contraseña incorrecta", "error")
    return render_template("login.html")


@app.post("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/configuracion", methods=["GET", "POST"])
@login_required
def configuracion():
    """Clave de Gemini guardada SOLO en la PC, fuera del repositorio y del EXE."""
    settings_root = Path(os.getenv("GO_DATA_ROOT", Path.cwd()))
    env_file = settings_root / ".env"
    if request.method == "POST":
        action = request.form.get("action", "guardar")
        api_key = request.form.get("gemini_key", "").strip()
        model = request.form.get("gemini_model", "gemini-2.5-flash-lite").strip()
        if not re.fullmatch(r"gemini-[a-zA-Z0-9._-]{3,80}", model):
            flash("Nombre de modelo inválido; revisa la configuración", "error")
            return redirect(url_for("configuracion"))
        # Campo vacío = conservar la clave instalada; así no se exhibe en HTML.
        if api_key:
            if len(api_key) < 20 or len(api_key) > 500 or any(x.isspace() for x in api_key):
                flash("La clave API no parece válida. Vuelve a copiarla desde AI Studio.", "error")
                return redirect(url_for("configuracion"))
            set_key(str(env_file), "GEMINI_API_KEY", api_key, quote_mode="always")
            os.environ["GEMINI_API_KEY"] = api_key
        elif action == "borrar":
            set_key(str(env_file), "GEMINI_API_KEY", "", quote_mode="always")
            os.environ.pop("GEMINI_API_KEY", None)
            flash("Clave de Gemini retirada de este equipo", "success")
            return redirect(url_for("configuracion"))
        set_key(str(env_file), "GEMINI_MODEL", model, quote_mode="always")
        os.environ["GEMINI_MODEL"] = model
        if action == "probar":
            if not os.getenv("GEMINI_API_KEY"):
                flash("Introduce primero una clave de Gemini para probarla", "error")
            else:
                try:
                    text = news_engine.gemini_request(os.environ["GEMINI_API_KEY"], model,
                            'Responde con un JSON que contenga {"mensaje":"OK"}', timeout=20)
                    parsed = __import__("json").loads(text)
                    if isinstance(parsed, dict) and parsed.get("mensaje") == "OK":
                        flash("Conexión Gemini comprobada. Ya puedes redactar noticias con IA.", "success")
                    else:
                        flash("Gemini respondió, pero el formato no fue el esperado. Comprueba el modelo.", "info")
                except Exception as exc:
                    flash(f"No se pudo comprobar Gemini: {exc}", "error")
        else:
            flash("Configuración guardada en tu computadora. La clave no se subió a GitHub.", "success")
        return redirect(url_for("configuracion"))
    return render_template("configuracion.html",
        gemini_configured=bool(os.getenv("GEMINI_API_KEY", "").strip()),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"))


@app.get("/")
@login_required
def index():
    filter_status = request.args.get("estado", "todas")
    return render_template("index.html", items=db.list_news(filter_status), last=db.last_run(), status=filter_status)


def scan_background():
    try:
        scan_state["result"] = str(news_engine.ingest())
    except Exception as exc:
        scan_state["result"] = f"Error: {str(exc)[:300]}"
    finally:
        scan_state["active"] = False
        scan_lock.release()


@app.post("/buscar")
@login_required
def scan_now():
    if scan_lock.acquire(blocking=False):
        scan_state["active"] = True
        scan_state["result"] = ""
        threading.Thread(target=scan_background, daemon=True).start()
        flash("Búsqueda iniciada. Actualiza el panel para consultar los resultados.", "info")
    else:
        flash("Ya hay una búsqueda en curso", "info")
    return redirect(url_for("index"))


@app.get("/noticia/<int:news_id>")
@login_required
def detail(news_id):
    item = db.news_by_id(news_id)
    if item is None:
        abort(404)
    # Foto obtenida de una noticia (URL remota) NO equivale a un archivo local.
    local = str(item["local_photo_path"] or "").strip()
    photo_ready = bool(local) and Path(local).is_file()
    return render_template("detail.html", item=item, photo_ready=photo_ready)


@app.post("/noticia/<int:news_id>/guardar")
@login_required
def save(news_id):
    item = db.news_by_id(news_id)
    if item is None:
        abort(404)
    valid_statuses = {"pendiente", "revisada", "aprobada", "publicada", "descartada"}
    status = request.form.get("status", "pendiente")
    if status not in valid_statuses:
        abort(400)
    model = request.form.get("model", "modelo_1")
    if model not in ("modelo_1", "modelo_2"):
        abort(400)
    # No se aprueba automáticamente desde el motor; una persona lo hace desde este formulario.
    updated_copy = news_engine.editorial.normalize_copy(
        request.form.get("copy_text", "")[:12000], item["region"],
        item["original_title"], item["excerpt"], item["source"])
    updated = db.edit_news(news_id, {
        "photo_main_x": graphics.clamp_float(request.form.get("photo_main_x"), 0, 100, 50),
        "photo_main_y": graphics.clamp_float(request.form.get("photo_main_y"), 0, 100, 36),
        "photo_main_zoom": graphics.clamp_float(request.form.get("photo_main_zoom"), 1, 3, 1),
        "photo_inset_x": graphics.clamp_float(request.form.get("photo_inset_x"), 0, 100, 50),
        "photo_inset_y": graphics.clamp_float(request.form.get("photo_inset_y"), 0, 100, 32),
        "photo_inset_zoom": graphics.clamp_float(request.form.get("photo_inset_zoom"), 1, 3, 1),
        "cintillo": request.form.get("cintillo", "")[:100],
        "titulo": request.form.get("titulo", "")[:300],
        "bajada": request.form.get("bajada", "")[:700],
        "copy_text": updated_copy,
        "status": status, "model": model,
        "notes": request.form.get("notes", "")[:3000],
        "photo_credit": request.form.get("photo_credit", "")[:300],
        "photo_rights_confirmed": int(request.form.get("photo_rights_confirmed", "0") == "1"),
    })
    if not updated:
        abort(404)
    if request.headers.get("X-GO-Autosave") == "1":
        return jsonify({"ok": True, "guardado": True, "news_id": news_id,
                        "copy_text": updated_copy})
    flash("Cambios guardados en la base de datos", "success")
    return redirect(url_for("detail", news_id=news_id))


@app.post("/noticia/<int:news_id>/redactar")
@login_required
def redraft(news_id):
    """Regenera conscientemente textos a partir de la fuente; nunca los publica."""
    item = db.news_by_id(news_id)
    if item is None:
        abort(404)
    if item['status'] == 'publicada':
        flash('Esta noticia ya está marcada como publicada. Para evitar sobreescrituras, no se regenera.', 'error')
        return redirect(url_for('detail', news_id=news_id))
    redaction = news_engine.draft_ai(
        item['original_title'], item['excerpt'], item['story_text'],
        item['source_published'], item['region'], item['source'], item['source_url'])
    used_ai = redaction is not None
    if not redaction:
        redaction = news_engine.draft_fallback(
            item['original_title'], item['excerpt'], item['region'],
            item['source'], item['source_url'], item['story_text'])
    db.edit_news(news_id, {**redaction, 'status': 'pendiente'})
    if used_ai:
        flash('Redacción generada con IA. Comprueba fuente, hechos, fecha y acusaciones antes de aprobar.', 'success')
    elif os.getenv('GEMINI_API_KEY'):
        flash('Gemini no respondió correctamente; se usó un borrador local breve. Ve a Configuración para probar tu clave.', 'error')
    else:
        flash('Borrador local breve. Ve a Configuración y conecta tu clave de Gemini para generar copys completos.', 'info')
    return redirect(url_for('detail', news_id=news_id))


@app.post("/noticia/<int:news_id>/foto")
@login_required
def photo(news_id):
    item = db.news_by_id(news_id)
    if item is None:
        abort(404)
    upload = request.files.get("photo")
    if not upload or not upload.filename:
        abort(400)
    from PIL import Image, UnidentifiedImageError
    Image.MAX_IMAGE_PIXELS = 25000000
    try:
        im = Image.open(upload.stream)
        im.verify()
        upload.stream.seek(0)
        im = Image.open(upload.stream).convert("RGB")
        if im.width < 800 or im.height < 800:
            flash("Fotografía demasiado pequeña. Usa 800 × 800 px como mínimo; ideal 1080 px o más.", "error")
            return redirect(url_for("detail", news_id=news_id))
        im.thumbnail((4000, 4000))
        dest = MEDIA / f"noticia_{news_id}_autorizada.jpg"
        im.save(dest, "JPEG", quality=94)
        db.edit_news(news_id, {"local_photo_path": str(dest), "photo_rights_confirmed": 0})
    except (UnidentifiedImageError, OSError, ValueError):
        flash("Archivo de imagen inválido", "error")
        return redirect(url_for("detail", news_id=news_id))
    flash("Imagen subida; confirma los derechos y el crédito antes de generar la pieza.", "info")
    return redirect(url_for("detail", news_id=news_id))


@app.get("/noticia/<int:news_id>/foto")
@login_required
def view_photo(news_id):
    item = db.news_by_id(news_id)
    if not item or not item["local_photo_path"] or not Path(item["local_photo_path"]).is_file():
        abort(404)
    return send_file(item["local_photo_path"], mimetype="image/jpeg")


@app.post("/noticia/<int:news_id>/foto_secundaria")
@login_required
def inset_photo(news_id):
    item = db.news_by_id(news_id)
    if not item:
        abort(404)
    upload = request.files.get("photo")
    if not upload or not upload.filename:
        abort(400)
    from PIL import Image, UnidentifiedImageError
    Image.MAX_IMAGE_PIXELS = 25000000
    try:
        im = Image.open(upload.stream)
        im.verify()
        upload.stream.seek(0)
        im = Image.open(upload.stream).convert("RGB")
        if im.width < 400 or im.height < 400:
            flash("La imagen del círculo necesita 400 × 400 px como mínimo", "error")
            return redirect(url_for("detail", news_id=news_id))
        im.thumbnail((2500, 2500))
        dest = MEDIA / f"noticia_{news_id}_secundaria.jpg"
        im.save(dest, "JPEG", quality=93)
        db.edit_news(news_id, {"inset_photo_path": str(dest), "photo_rights_confirmed": 0})
    except (UnidentifiedImageError, OSError, ValueError):
        flash("Imagen secundaria inválida", "error")
        return redirect(url_for("detail", news_id=news_id))
    flash("Foto secundaria añadida; confirma derechos de ambas fotos", "info")
    return redirect(url_for("detail", news_id=news_id))


@app.get("/noticia/<int:news_id>/exportar")
@login_required
def download_copy(news_id):
    item = db.news_by_id(news_id)
    if not item:
        abort(404)
    text = (f"FUENTE: {item['source']}\nURL: {item['source_url']}\nFECHA PUBLICADA: {item['source_published']}\n"
            f"ÁMBITO: {item['region']}\nESTADO: {item['status']}\n\n"
            f"CINTILLO:\n{item['cintillo']}\n\nTÍTULO:\n{item['titulo']}\n\n"
            f"BAJADA:\n{item['bajada']}\n\nCOPY:\n{item['copy_text']}\n")
    return send_file(io.BytesIO(text.encode("utf-8-sig")), mimetype="text/plain; charset=utf-8",
                     as_attachment=True, download_name=f"GO_Arequipa_noticia_{news_id}.txt")


@app.get("/identidad/logo")
def view_brand_logo():
    path = brand_logo_file()
    if not path.is_file():
        abort(404)
    return send_file(path, mimetype="image/png", max_age=0)


@app.route("/identidad", methods=["GET", "POST"])
@login_required
def identidad():
    if request.method == "POST":
        upload = request.files.get("logo")
        if not upload or not upload.filename:
            flash("Selecciona primero un PNG o JPG de tu logotipo.", "error")
            return redirect(url_for("identidad"))
        try:
            from PIL import Image, UnidentifiedImageError
            with Image.open(upload.stream) as src:
                if src.width < 160 or src.height < 160:
                    raise ValueError("El logo necesita al menos 160 x 160 píxeles")
                if src.width * src.height > 24000000:
                    raise ValueError("El archivo de logo es demasiado grande")
                img = src.convert("RGBA")
                img.thumbnail((1600, 1600))
                target = Path(os.getenv("GO_DATA_ROOT", str(Path.cwd()))) / "assets" / "logo_go.png"
                target.parent.mkdir(parents=True, exist_ok=True)
                tmp = target.with_suffix(".tmp.png")
                img.save(tmp, "PNG")
                tmp.replace(target)
        except (ValueError, UnidentifiedImageError, OSError) as exc:
            flash(f"No se pudo guardar el logotipo: {exc}", "error")
            return redirect(url_for("identidad"))
        flash("Logotipo actualizado. Se aplicará a todos los diseños nuevos.", "success")
        return redirect(url_for("identidad"))
    return render_template("identidad.html")


@app.get("/noticia/<int:news_id>/foto_secundaria")
@login_required
def view_inset_photo(news_id):
    item = db.news_by_id(news_id)
    if not item or not item["inset_photo_path"] or not Path(item["inset_photo_path"]).is_file():
        abort(404)
    return send_file(item["inset_photo_path"], mimetype="image/jpeg", max_age=0)


@app.post("/noticia/<int:news_id>/vista_previa")
@login_required
def vista_previa(news_id):
    """Vista previa NO publicable, sin alterar SQLite y con encuadre aún sin guardar."""
    item = db.news_by_id(news_id)
    if not item:
        abort(404)
    photo_path = str(item["local_photo_path"] or "").strip()
    if not photo_path or not Path(photo_path).is_file():
        return jsonify({"error": "Primero sube una fotografía principal para ver el diseño."}), 400
    state = dict(item)
    state.update({
        "model": request.form.get("model", state["model"]),
        "cintillo": request.form.get("cintillo", state["cintillo"])[:100],
        "titulo": request.form.get("titulo", state["titulo"])[:300],
        "bajada": request.form.get("bajada", state["bajada"])[:700],
    })
    if state["model"] not in ("modelo_1", "modelo_2"):
        return jsonify({"error": "Modelo de diseño inválido."}), 400
    for key, minv, maxv, default in (("photo_main_x",0,100,50),("photo_main_y",0,100,36),
                                    ("photo_main_zoom",1,3,1),("photo_inset_x",0,100,50),
                                    ("photo_inset_y",0,100,32),("photo_inset_zoom",1,3,1)):
        state[key] = graphics.clamp_float(request.form.get(key), minv, maxv, default)
    try:
        output = io.BytesIO()
        graphics.render(state, photo_path, output, state["inset_photo_path"],
                        logo_path=brand_logo_file(), preview=True)
        output.seek(0)
        return send_file(output, mimetype="image/jpeg", max_age=0)
    except (ValueError, OSError) as exc:
        return jsonify({"error": str(exc)[:220]}), 400


@app.get("/noticia/<int:news_id>/diseño")
@login_required
def download_design(news_id):
    item = db.news_by_id(news_id)
    if not item:
        abort(404)
    if item["status"] not in ("aprobada", "publicada"):
        flash("Aprueba primero la noticia desde su ficha", "error")
        return redirect(url_for("detail", news_id=news_id))
    # Comprobación anticipada: una URL detectada en RSS no es una foto descargada.
    path_text = str(item["local_photo_path"] or "").strip()
    if not path_text or not Path(path_text).is_file():
        flash("Para generar el JPG: sube primero una fotografía principal en la ficha editorial. El enlace de foto sugerida no sirve como archivo local.", "error")
        return redirect(url_for("detail", news_id=news_id))
    if not bool(item["photo_rights_confirmed"]):
        flash("Confirma que tienes permiso para publicar la fotografía y guarda los cambios antes de generar el JPG.", "error")
        return redirect(url_for("detail", news_id=news_id))
    try:
        out = MEDIA / f"GO_Arequipa_{news_id}_{item['model']}.jpg"
        graphics.render(item, path_text, out, item["inset_photo_path"], logo_path=brand_logo_file())
        return send_file(out, mimetype="image/jpeg", as_attachment=True, download_name=out.name)
    except (ValueError, OSError) as exc:
        # Mensaje comprensible de validación. El error nunca debe revelar .env ni claves.
        flash(f"No se pudo generar el JPG: {exc}", "error")
        return redirect(url_for("detail", news_id=news_id))
    except Exception:
        # Registro local para diagnosticar errores futuros sin publicar trazas en la web.
        try:
            log = Path(os.getenv("GO_DATA_ROOT", str(MEDIA.parent))) / "diagnostico_jpg.log"
            with log.open("a", encoding="utf-8") as file:
                file.write(f"\n{datetime.now().isoformat()} | Noticia {news_id} | Versión {VERSION}\n")
                file.write(traceback.format_exc())
        except OSError:
            pass
        flash("Ocurrió un problema inesperado al generar el JPG. Abre el archivo diagnostico_jpg.log dentro de GO_Arequipa_Datos para identificarlo.", "error")
        return redirect(url_for("detail", news_id=news_id))


if __name__ == "__main__":
    app.run(host=os.getenv("HOST", "127.0.0.1"), port=5050, debug=False)
