"""Prueba de regresión: guarda desde el formulario web y relee desde SQLite."""
import os
import tempfile
import unittest
from pathlib import Path

import db


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_path = db.DB_PATH
        db.DB_PATH = str(Path(self.tmp.name) / 'base' / 'noticias.db')
        db.init_db()

    def tearDown(self):
        db.DB_PATH = self.old_path
        self.tmp.cleanup()

    def test_update_reopen_connection(self):
        news = dict(unique_key='uniq', source='Fuente', source_url='https://example.org/nota',
                    source_published='2026-11-03T16:00:00+00:00',
                    discovered_at='2026-11-03T16:00:00+00:00',
                    original_title='Noticia en Arequipa', region='arequipa')
        self.assertTrue(db.insert_news(news))
        ident = db.list_news()[0]['id']
        self.assertTrue(db.edit_news(ident, {
            'cintillo': 'CAMBIO GUARDADO', 'titulo': 'TÍTULO CORREGIDO',
            'bajada': 'Texto editado y almacenado',
            'copy_text': '#Arequipa | Texto que debe persistir.',
            'status': 'aprobada', 'notes': 'Confirmado por editor'
        }))
        self.assertEqual(db.news_by_id(ident)['titulo'], 'TÍTULO CORREGIDO')
        with db.connect() as c:
            self.assertEqual(c.execute('SELECT titulo FROM news WHERE id=?', (ident,)).fetchone()[0], 'TÍTULO CORREGIDO')
        self.assertTrue(Path(db.DB_PATH).is_file())

    def test_http_form_save_persists(self):
        os.environ.setdefault('SECRET_KEY', 'clave-prueba-secret-key-1234567890')
        os.environ.setdefault('ADMIN_PASSWORD', 'password-seguro-prueba')
        import app as editor
        news = dict(unique_key='uniq2', source='Fuente', source_url='https://example.org/nota2',
                    source_published='2026-11-03T16:00:00+00:00',
                    discovered_at='2026-11-03T16:00:00+00:00',
                    original_title='Noticia en Arequipa', region='arequipa')
        self.assertTrue(db.insert_news(news))
        ident = db.list_news()[0]['id']
        editor.app.config.update(TESTING=True)
        with editor.app.test_client() as client:
            with client.session_transaction() as sess:
                sess['auth'] = True
                sess['csrf'] = 'token-para-prueba'
            response = client.post(f'/noticia/{ident}/guardar', data={
                'csrf': 'token-para-prueba', 'cintillo': 'NOTICIA NUEVA',
                'titulo': 'NUEVO TITULAR PARA CANVA', 'bajada': 'Se ha cambiado la bajada',
                'copy_text': '#Arequipa | Copy editado sin emojis.',
                'model': 'modelo_2', 'status': 'aprobada',
                'notes': 'Mi nota editada', 'photo_credit': 'Autor original',
                'photo_rights_confirmed': '1'
            }, headers={'X-GO-Autosave': '1'})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json['ok'])
            page = client.get(f'/noticia/{ident}')
            self.assertIn(b'NUEVO TITULAR PARA CANVA', page.data)
        self.assertEqual(db.news_by_id(ident)['status'], 'aprobada')
        # El formulario conserva los párrafos del editor y normaliza el cierre
        # según la política vigente: exactamente cinco hashtags finales.
        saved_copy = db.news_by_id(ident)['copy_text']
        self.assertEqual(saved_copy, response.json['copy_text'])
        self.assertTrue(saved_copy.startswith('#Arequipa | Copy editado sin emojis.'))
        self.assertEqual(editor.news_engine.editorial.hashtag_count_final(saved_copy), 5)
        self.assertNotIn('Información pendiente de contraste editorial', saved_copy)


if __name__ == '__main__':
    unittest.main()
