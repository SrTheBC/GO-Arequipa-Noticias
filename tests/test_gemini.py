"""Pruebas de integración offline: ninguna clave real ni solicitud a Google."""
import json
import os
import unittest
from unittest.mock import patch

import news_engine
import editorial


class FakeResponse:
    def __init__(self, status, obj):
        self.status_code = status
        self.obj = obj
    def json(self):
        return self.obj


class GeminiTests(unittest.TestCase):
    def test_gemini_valid_json_and_five_hashtags(self):
        response = {
            "cintillo": "OPERATIVO POLICIAL",
            "titulo": "OPERATIVO DE SEGURIDAD EN AREQUIPA",
            "bajada": "La policía desarrolló un operativo en la ciudad.",
            "copy_text": "#Arequipa | Se informó sobre un operativo en Arequipa.\n\nLa fuente indicó que el caso continúa en investigación.\n\n#GOArequipaNoticias #Arequipa #PNP",
        }
        mock = FakeResponse(200, {"candidates": [{"content": {"parts": [{"text": json.dumps(response)}]}}]})
        with patch.dict(os.environ, {"GEMINI_API_KEY": "dummy-not-a-real-secret-value", "GEMINI_MODEL": "gemini-2.5-flash-lite"}), patch("news_engine.requests.post", return_value=mock) as post:
            result = news_engine.draft_ai("Operativo en Arequipa", "La Policía informó un operativo.", "", "2026-11-04T20:00:00Z", "arequipa", "Fuente oficial", "https://example.com")
        self.assertIsNotNone(result)
        self.assertEqual(result["cintillo"], "OPERATIVO POLICIAL")
        self.assertEqual(editorial.hashtag_count_final(result["copy_text"]), 5)
        self.assertEqual(result["ai_status"], "borrador_ia_revisar")
        self.assertTrue(result["copy_text"].startswith("#Arequipa |"))
        args, kwargs = post.call_args
        self.assertNotIn("dummy-not-a-real-secret-value", args[0])
        self.assertEqual(kwargs["headers"]["x-goog-api-key"], "dummy-not-a-real-secret-value")
        self.assertIn("responseMimeType", kwargs["json"]["generationConfig"])

    def test_invalid_model_not_sent(self):
        with patch("news_engine.requests.post") as post:
            with self.assertRaises(ValueError):
                news_engine.gemini_request("dummy", "../bad", "text")
            post.assert_not_called()

    def test_rate_limit_explicit_and_fallback(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-test-key", "GEMINI_MODEL": "gemini-2.5-flash-lite"}), patch("news_engine.requests.post", return_value=FakeResponse(429, {"error": {"message": "private-details-not-leaked"}})):
            with self.assertRaisesRegex(RuntimeError, "cuota gratuita") as err:
                news_engine.gemini_request("fake-test-key", "gemini-2.5-flash-lite", "hola")
            self.assertNotIn("private-details-not-leaked", str(err.exception))
            self.assertIsNone(news_engine.draft_ai("Incendio Arequipa", "Incidente reportado.", "", "2026-11-04", "arequipa", "Prensa", "https://example.com"))

    def test_prompt_contains_no_secret_and_no_fabrication(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "not-a-real-api-key", "GEMINI_MODEL": "gemini-2.5-flash-lite"}), patch("news_engine.gemini_request", return_value=json.dumps({"cintillo":"SALUD PÚBLICA","titulo":"NUEVO CENTRO DE SALUD","bajada":"Se informó de un centro de salud.","copy_text":"#Arequipa | Se informó de un centro de salud.\n\n#Arequipa #Salud"})) as func:
            result = news_engine.draft_gemini("Nuevo centro de salud", "Se informó un centro de salud", "", "2026-11-04", "arequipa", "Fuente", "https://example.com")
            prompt = func.call_args.args[2]
            self.assertIn("no inventes", prompt.lower())
            self.assertNotIn("not-a-real-api-key", prompt)
            self.assertEqual(editorial.hashtag_count_final(result["copy_text"]), 5)


if __name__ == "__main__":
    unittest.main()
