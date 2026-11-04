"""Punto de entrada para el ejecutable de Windows de GO Arequipa Noticias.

No requiere instalar Python en la PC del usuario. El ejecutable empaqueta los módulos
con PyInstaller. Toda la información del medio se guarda FUERA del .exe.
"""
from __future__ import annotations

import os
import secrets
import sqlite3
from datetime import datetime
import shutil
import sys
import threading
import time
import traceback
import webbrowser
from pathlib import Path
from urllib.request import urlopen


def bundled(path: str) -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / path


def data_root() -> Path:
    """Portable si puede escribir junto al EXE; si no, usa AppData local."""
    root = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    candidate = root / "GO_Arequipa_Datos"
    try:
        candidate.mkdir(parents=True, exist_ok=True)
        probe = candidate / ".escribible"
        probe.write_text("ok", encoding="ascii")
        probe.unlink()
        return candidate
    except (OSError, PermissionError):
        alternative = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "GO_Arequipa_Noticias"
        alternative.mkdir(parents=True, exist_ok=True)
        return alternative


def ensure_configuration(root: Path) -> None:
    """Primer arranque: claves aleatorias en el equipo, nunca en el repositorio."""
    cfg = root / "config.json"
    if not cfg.exists():
        shutil.copyfile(bundled("config.json"), cfg)
    (root / "assets").mkdir(exist_ok=True)
    # Incorporar logo original del medio solo en el primer arranque V6;
    # jamás reemplazar uno que el editor haya personalizado.
    bundled_logo = bundled("assets/logo_go.png")
    selected_logo = root / "assets" / "logo_go.png"
    if bundled_logo.is_file() and not selected_logo.exists():
        shutil.copyfile(bundled_logo, selected_logo)
    (root / "data" / "media").mkdir(parents=True, exist_ok=True)

    env_file = root / ".env"
    if not env_file.exists():
        password = secrets.token_urlsafe(18)
        key = secrets.token_urlsafe(48)
        content = (f"ADMIN_PASSWORD={password}\nSECRET_KEY={key}\n"
                   "OPENAI_API_KEY=\nOPENAI_MODEL=gpt-4.1-mini\nGEMINI_API_KEY=\nGEMINI_MODEL=gemini-2.5-flash-lite\n"
                   "DATABASE_PATH=data/noticias.db\nMEDIA_PATH=data/media\n"
                   "COOKIE_SECURE=false\nTELEGRAM_BOT_TOKEN=\nTELEGRAM_CHAT_ID=\n")
        # exclusive creation: no sobreescribe secretos de un inicio anterior
        with env_file.open("x", encoding="utf-8") as f:
            f.write(content)
        os.chmod(env_file, 0o600)
        access_file = root / "ACCESO_INICIAL.txt"
        with access_file.open("x", encoding="utf-8") as f:
            f.write("GO AREQUIPA NOTICIAS - ACCESO LOCAL\n"
                    f"Contraseña generada: {password}\n"
                    "Panel: se abre automáticamente al iniciar el ejecutable.\n\n"
                    "Guarda este archivo en privado, no lo compartas por chat.\n"
                    "Puedes cambiar ADMIN_PASSWORD en el archivo .env con la aplicación cerrada.\n")
        os.chmod(access_file, 0o600)
        print("\nPRIMER INICIO: abre GO_Arequipa_Datos\\ACCESO_INICIAL.txt para ver tu contraseña.\n", flush=True)
    else:
        print("Configuración anterior conservada; no se han modificado tus claves.", flush=True)


def browser_when_ready(url: str) -> None:
    for _ in range(35):
        try:
            with urlopen(url + "/login", timeout=1) as res:
                if res.status == 200:
                    webbrowser.open(url + "/login", new=1)
                    return
        except Exception:
            time.sleep(0.25)
    print(f"Si no se abrió el navegador, entra manualmente en {url}", flush=True)


def run_periodic_scan(app_module) -> None:
    """Primer escaneo al abrir, siguientes cada 60 min mientras el EXE siga abierto."""
    from notifications import send_telegram_alert
    import news_engine

    next_scan = time.monotonic()
    while True:
        wait = max(0, next_scan - time.monotonic())
        if wait:
            time.sleep(wait)
        next_scan = max(next_scan + 3600, time.monotonic() + 1)
        if not app_module.scan_lock.acquire(blocking=False):
            print("Escaneo omitido: ya hay otra búsqueda en curso", flush=True)
            continue
        app_module.scan_state["active"] = True
        try:
            result = news_engine.ingest()
            app_module.scan_state["result"] = (f"{result['insertadas']} nuevas, "
                                                 f"{result['revisadas']} revisadas, "
                                                 f"{len(result['errores'])} errores")
            print(f"Búsqueda horaria: {app_module.scan_state['result']}", flush=True)
            if result["insertadas"]:
                send_telegram_alert(result["titulares"])
        except Exception as exc:
            app_module.scan_state["result"] = f"Error: {exc}"
            print(f"Error de búsqueda: {exc}", flush=True)
        finally:
            app_module.scan_state["active"] = False
            app_module.scan_lock.release()



def backup_database(root: Path) -> None:
    """Conserva hasta 5 copias coherentes de SQLite antes de que el usuario edite."""
    original = Path(os.environ["DATABASE_PATH"])
    if not original.is_file():
        return
    folder = root / "copias_de_seguridad"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / ("noticias_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".db")
    source = sqlite3.connect(str(original), timeout=20)
    try:
        snapshot = sqlite3.connect(str(target))
        try:
            source.backup(snapshot)
        finally:
            snapshot.close()
    finally:
        source.close()
    for previous in sorted(folder.glob("noticias_*.db"))[:-5]:
        previous.unlink(missing_ok=True)


def main() -> int:
    root = data_root()
    ensure_configuration(root)
    os.chdir(root)  # config.json, data, .env y assets apuntan a la carpeta portable

    from dotenv import load_dotenv
    load_dotenv(dotenv_path=root / ".env", override=False)
    # Conviértelas en rutas absolutas: evita guardar/leer bases diferentes según
    # desde qué acceso directo o carpeta se abra el ejecutable.
    for name, fallback in (("DATABASE_PATH", "data/noticias.db"),
                           ("MEDIA_PATH", "data/media")):
        location = Path(os.environ.get(name, fallback))
        if not location.is_absolute():
            location = root / location
        os.environ[name] = str(location.resolve())
    os.environ["GO_DATA_ROOT"] = str(root)
    import app as app_module
    # No modificamos la base anterior al actualizar; creamos copia en arranque.
    try:
        backup_database(root)
        print("Copia de seguridad guardada en:", root / "copias_de_seguridad", flush=True)
    except Exception as exc:
        print("AVISO: no se pudo crear respaldo de SQLite:", exc, flush=True)

    from werkzeug.serving import make_server
    try:
        server = make_server("127.0.0.1", 5050, app_module.app, threaded=True)
    except OSError:
        server = make_server("127.0.0.1", 0, app_module.app, threaded=True)
    port = server.server_port
    url = f"http://127.0.0.1:{port}"

    print("=" * 58, flush=True)
    print("GO AREQUIPA NOTICIAS · PANEL LOCAL", flush=True)
    print("Panel:", url, flush=True)
    print("Datos y configuración:", root, flush=True)
    print("Noticias: se revisarán al iniciar y cada 60 minutos.", flush=True)
    print("Para detener: cierra esta ventana. Guarda respaldo de GO_Arequipa_Datos.", flush=True)
    print("=" * 58, flush=True)
    threading.Thread(target=browser_when_ready, args=(url,), daemon=True).start()
    threading.Thread(target=run_periodic_scan, args=(app_module,), daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Cerrando panel.")
        server.shutdown()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        print("Se produjo un error al iniciar el programa:", file=sys.stderr)
        traceback.print_exc()
        input("Pulsa Enter para cerrar y conservar el mensaje de error...")
        raise
