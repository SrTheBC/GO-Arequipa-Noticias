"""Comprobación local del formulario. La clave utilizada es ficticia."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class ConfiguracionGeminiTests(unittest.TestCase):
    def test_config_store_secret_only_in_local_env(self):
        import app
        fake_key = "test-solo-para-pruebas-sin-validez-1234567"
        with tempfile.TemporaryDirectory() as tmp:
            local_env = Path(tmp) / ".env"
            local_env.write_text('ADMIN_PASSWORD=test\nSECRET_KEY=123456789012345678901234\n', encoding='utf-8')
            with patch.dict(os.environ, {"GO_DATA_ROOT": tmp}, clear=False):
                app.app.config["TESTING"] = True
                with app.app.test_client() as c:
                    with c.session_transaction() as sess:
                        sess['auth'] = True
                        sess['csrf'] = 'token-de-prueba'
                    response = c.post('/configuracion', data={
                        'csrf': 'token-de-prueba', 'action': 'guardar',
                        'gemini_key': fake_key, 'gemini_model': 'gemini-2.5-flash-lite'
                    }, follow_redirects=True)
                    self.assertEqual(response.status_code, 200)
                    self.assertIn('Clave configurada en esta PC', response.get_data(as_text=True))
                    self.assertNotIn(fake_key, response.get_data(as_text=True))
                    self.assertIn(fake_key, local_env.read_text(encoding='utf-8'))
                    with patch('news_engine.gemini_request', return_value='{"mensaje":"OK"}'):
                        result = c.post('/configuracion', data={
                            'csrf': 'token-de-prueba', 'action': 'probar',
                            'gemini_key': '', 'gemini_model': 'gemini-2.5-flash-lite'
                        }, follow_redirects=True)
                        self.assertIn('Conexión Gemini comprobada', result.get_data(as_text=True))
        os.environ.pop('GEMINI_API_KEY', None)
        os.environ.pop('GEMINI_MODEL', None)


if __name__ == '__main__':
    unittest.main()
