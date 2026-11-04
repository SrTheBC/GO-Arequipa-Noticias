"""Aviso por Telegram, independiente de cuentas de ChatGPT. Optativo."""
import logging
import os
import requests


def send_telegram_alert(items):
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id or not items:
        return False
    titles = []
    for i, item in enumerate(items[:7], start=1):
        titles.append(f"{i}. [{item['ambito']}] {item['titulo'][:180]}\n{item['fuente']} · {item['url']}")
    content = (f"GO AREQUIPA NOTICIAS | {len(items)} NOTICIA(S) NUEVA(S)\n\n" +
               "\n\n".join(titles) +
               "\n\nRevisar la ficha editorial antes de publicar. Fotos y datos sin aprobación automática.")
    try:
        response = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", timeout=15,
                                 json={"chat_id": chat_id, "text": content[:3900], "disable_web_page_preview": True})
        response.raise_for_status()
        return response.json().get("ok") is True
    except Exception as exc:
        logging.warning("No se pudo enviar aviso por Telegram: %s", exc)
        return False
