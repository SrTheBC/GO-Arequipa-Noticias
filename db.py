import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = os.getenv("DATABASE_PATH", "data/noticias.db")


@contextmanager
def connect():
    path = Path(DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=20)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=15000")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init_db():
    with connect() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS news (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              unique_key TEXT NOT NULL UNIQUE,
              source TEXT NOT NULL,
              source_url TEXT NOT NULL,
              source_published TEXT NOT NULL,
              discovered_at TEXT NOT NULL,
              original_title TEXT NOT NULL,
              excerpt TEXT NOT NULL DEFAULT '',
              story_text TEXT NOT NULL DEFAULT '',
              region TEXT NOT NULL,
              priority INTEGER NOT NULL DEFAULT 0,
              photo_url TEXT NOT NULL DEFAULT '',
              photo_credit TEXT NOT NULL DEFAULT '',
              local_photo_path TEXT NOT NULL DEFAULT '',
              inset_photo_path TEXT NOT NULL DEFAULT '',
              photo_rights_confirmed INTEGER NOT NULL DEFAULT 0,
              model TEXT NOT NULL DEFAULT 'modelo_1',
              cintillo TEXT NOT NULL DEFAULT '',
              titulo TEXT NOT NULL DEFAULT '',
              bajada TEXT NOT NULL DEFAULT '',
              copy_text TEXT NOT NULL DEFAULT '',
              status TEXT NOT NULL DEFAULT 'pendiente',
              ai_status TEXT NOT NULL DEFAULT 'pendiente_verificacion',
              notes TEXT NOT NULL DEFAULT '',
              photo_main_x REAL NOT NULL DEFAULT 50,
              photo_main_y REAL NOT NULL DEFAULT 36,
              photo_main_zoom REAL NOT NULL DEFAULT 1,
              photo_inset_x REAL NOT NULL DEFAULT 50,
              photo_inset_y REAL NOT NULL DEFAULT 32,
              photo_inset_zoom REAL NOT NULL DEFAULT 1
            );
            CREATE INDEX IF NOT EXISTS news_date_idx ON news(source_published DESC);
            CREATE TABLE IF NOT EXISTS runs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              run_at TEXT NOT NULL,
              inserted INTEGER NOT NULL,
              scanned INTEGER NOT NULL,
              errors TEXT NOT NULL DEFAULT ''
            );
        """)
        # Compatibilidad con noticias.db de V5: nunca se descartan registros previos.
        existing = {row[1] for row in c.execute("PRAGMA table_info(news)")}
        for col, default in (("photo_main_x", 50), ("photo_main_y", 36),
                             ("photo_main_zoom", 1), ("photo_inset_x", 50),
                             ("photo_inset_y", 32), ("photo_inset_zoom", 1)):
            if col not in existing:
                c.execute(f"ALTER TABLE news ADD COLUMN {col} REAL NOT NULL DEFAULT {default}")


def list_news(status=None):
    with connect() as c:
        if status and status != "todas":
            return c.execute("SELECT * FROM news WHERE status=? ORDER BY priority DESC, source_published DESC LIMIT 250", (status,)).fetchall()
        return c.execute("SELECT * FROM news ORDER BY priority DESC, source_published DESC LIMIT 250").fetchall()


def news_by_id(news_id):
    with connect() as c:
        return c.execute("SELECT * FROM news WHERE id=?", (news_id,)).fetchone()


def insert_news(payload):
    cols = list(payload)
    params = [payload[k] for k in cols]
    with connect() as c:
        cur = c.execute(f"INSERT OR IGNORE INTO news ({','.join(cols)}) VALUES ({','.join(['?'] * len(cols))})", params)
        return cur.rowcount > 0


def record_run(inserted, scanned, errors):
    with connect() as c:
        c.execute("INSERT INTO runs (run_at,inserted,scanned,errors) VALUES (?,?,?,?)",
                  (datetime.now(timezone.utc).isoformat(), inserted, scanned, "\n".join(errors)[:4000]))


def last_run():
    with connect() as c:
        return c.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()


def edit_news(news_id, changes):
    ALLOWED = {"status", "cintillo", "titulo", "bajada", "copy_text", "model", "photo_credit", "local_photo_path", "photo_rights_confirmed", "notes", "ai_status", "inset_photo_path", "photo_main_x", "photo_main_y", "photo_main_zoom", "photo_inset_x", "photo_inset_y", "photo_inset_zoom"}
    changes = {k: v for k, v in changes.items() if k in ALLOWED}
    if not changes:
        return False
    cols = ", ".join(f"{k}=?" for k in changes)
    with connect() as c:
        result = c.execute(f"UPDATE news SET {cols} WHERE id=?", (*changes.values(), news_id))
        return result.rowcount == 1


def actualizar_borradores_antiguos():
    """Migra SOLO cintillos genéricos de registros no aprobados, sin tocar ediciones propias.

    Los textos que ya fueron redactados por una persona permanecen intactos.
    Esta operación es idempotente: iniciarla varias veces no altera borradores corregidos.
    """
    from editorial import is_legacy_placeholder, derive_editorial
    fixed = 0
    with connect() as c:
        rows = c.execute("""SELECT id, status, cintillo, titulo, bajada, copy_text,
                              original_title, excerpt, region, source, source_url, ai_status
                              FROM news WHERE status IN ('pendiente','revisada')""").fetchall()
        for r in rows:
            if not is_legacy_placeholder(r['cintillo']):
                continue
            d = derive_editorial(r['original_title'], r['excerpt'], r['region'],
                                 r['source'], r['source_url'])
            # No alterar titular ni bajada: el usuario puede haberlos corregido.
            update = {'cintillo': d['cintillo']}
            old = r['copy_text'] or ''
            # Reemplazar copy SOLO si conserva la plantilla genérica original.
            if ('Información pendiente de contraste editorial.' in old and
                    r['ai_status'] == 'borrador_basico_revisar'):
                update['copy_text'] = d['copy_text']
            columns = ', '.join(f"{key}=?" for key in update)
            c.execute(f"UPDATE news SET {columns} WHERE id=?", (*update.values(), r['id']))
            fixed += 1
    return fixed


def normalizar_copys_antiguos():
    """Limpia SOLO copys pendientes/revisados: mantiene relato editado, corrige etiquetas.

    En ningún caso altera noticias aprobadas/publicadas o descartadas.
    """
    from editorial import normalize_copy
    updated = 0
    with connect() as c:
        rows = c.execute("""SELECT id, region, original_title, excerpt, source, copy_text
            FROM news WHERE status IN ('pendiente','revisada')""").fetchall()
        for row in rows:
            old = row['copy_text'] or ''
            if not old.strip():
                continue
            new = normalize_copy(old, row['region'], row['original_title'], row['excerpt'], row['source'])
            if new != old:
                c.execute("UPDATE news SET copy_text=? WHERE id=?", (new, row['id']))
                updated += 1
    return updated
