"""Pruebas offline: `python -m unittest discover -s tests` tras instalar requirements."""
import os
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import db
import graphics
from news_engine import classify, draft_fallback, canonical_url


class EditorialTests(unittest.TestCase):
    def test_arequipa_first(self):
        self.assertEqual(classify("Incendio en Cerro Colorado", "", []), "arequipa")
        self.assertIsNone(classify("Noticia de Lima sin relación regional", "", []))
        self.assertEqual(classify("Terremoto de magnitud 7 en Lima", "", ["terremoto de magnitud 7"]), "nacional_excepcional")

    def test_no_emojis_in_fallback(self):
        item = draft_fallback("Accidente en Arequipa", "Autoridades revisan el caso", "arequipa")
        self.assertTrue(item["copy_text"].startswith("#Arequipa |"))
        self.assertNotIn("información en desarrollo", item["cintillo"].lower())
        self.assertIn("#GOArequipaNoticias", item["copy_text"])

    def test_dedupe_url(self):
        self.assertEqual(canonical_url("https://example.com/noticia/?utm_source=x"), "https://example.com/noticia")

    def test_missing_photo_produces_readable_message(self):
        with tempfile.TemporaryDirectory() as folder:
            item = {"model": "modelo_1", "photo_rights_confirmed": 1,
                    "cintillo": "PRUEBA", "titulo": "TITULAR PRUEBA",
                    "bajada": "Texto de prueba"}
            dest = Path(folder) / "salida.jpg"
            for invalid in ("", None, "  "):
                with self.subTest(invalid=invalid):
                    with self.assertRaisesRegex(ValueError, "Primero sube una fotografía principal"):
                        graphics.render(item, invalid, dest)
            with self.assertRaisesRegex(ValueError, "No se encontró la fotografía principal"):
                graphics.render(item, Path(folder), dest)
            self.assertFalse(dest.exists())

    def test_graphic_two_models(self):
        with tempfile.TemporaryDirectory() as folder:
            pic = Path(folder) / "original.jpg"
            Image.new("RGB", (1300, 1600), "lightgray").save(pic)
            item = {"model": "modelo_1", "photo_rights_confirmed": 1,
                    "cintillo": "PRUEBA", "titulo": "ESTO ES UNA PRUEBA DEL SISTEMA",
                    "bajada": "Texto para verificar dimensiones de la composición."}
            for kind in ["modelo_1", "modelo_2"]:
                item["model"] = kind
                out = Path(folder) / f"{kind}.jpg"
                graphics.render(item, pic, out, pic)
                self.assertEqual(Image.open(out).size, (1080, 1350))


if __name__ == "__main__":
    unittest.main()
