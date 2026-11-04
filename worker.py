"""Trabajador independiente del panel. Ejecución horaria al minuto 13 hora Lima."""
import logging
import os
from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv
load_dotenv()
import db
from news_engine import ingest
from notifications import send_telegram_alert

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def run():
    try:
        result = ingest()
        logging.info("Escaneo: %s noticias nuevas, %s entradas examinadas, %s errores", result["insertadas"], result["revisadas"], len(result["errores"]))
        if result["insertadas"]:
            send_telegram_alert(result["titulares"])
    except Exception:
        logging.exception("Fallo en escaneo; reintenta siguiente hora")


if __name__ == "__main__":
    db.init_db()
    scheduler = BlockingScheduler(timezone="America/Lima")
    scheduler.add_job(run, "cron", minute=13, id="noticias_por_hora", max_instances=1, coalesce=True, misfire_grace_time=1200)
    logging.info("Monitoreo independiente activado, cada hora al minuto 13 (Lima)")
    run()  # primer escaneo al iniciar; el siguiente en el minuto 13
    scheduler.start()
