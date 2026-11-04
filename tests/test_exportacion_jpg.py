"""Prueba real del botón que mostró Errno 2: sin foto, foto subida y JPG de salida."""
import io
import os
import tempfile
import unittest
from pathlib import Path

from PIL import Image

os.environ.setdefault('SECRET_KEY', 'clave-de-prueba-que-es-mayor-a-24-caracteres')
os.environ.setdefault('ADMIN_PASSWORD', 'solo-en-pruebas-no-real')

import db
import app as editor


class ExportacionJpgIntegracion(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db = db.DB_PATH
        self.old_media = editor.MEDIA
        db.DB_PATH = str(Path(self.tmp.name) / 'data' / 'noticias.db')
        editor.MEDIA = Path(self.tmp.name) / 'data' / 'media'
        editor.MEDIA.mkdir(parents=True, exist_ok=True)
        db.init_db()
        db.insert_news(dict(unique_key='imagen_prueba', source='Prueba',
            source_url='https://example.com/prueba', source_published='2026-11-04T16:00:00Z',
            discovered_at='2026-11-04T16:00:00Z', original_title='Noticia de prueba',
            region='arequipa', status='aprobada', photo_rights_confirmed=1,
            cintillo='AREQUIPA', titulo='TITULAR DE PRUEBA',
            bajada='La bajada sirve para comprobar la exportación del diseño.' ))
        self.id = db.list_news()[0]['id']
        editor.app.config.update(TESTING=True)
        self.client = editor.app.test_client()
        with self.client.session_transaction() as sess:
            sess['auth'] = True
            sess['csrf'] = 'token_de_prueba'

    def tearDown(self):
        db.DB_PATH = self.old_db
        editor.MEDIA = self.old_media
        self.tmp.cleanup()

    def test_no_foto_mensaje_legible(self):
        url = f'/noticia/{self.id}/diseño'
        resp = self.client.get(url, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('sube primero una fotografía principal'.encode(), resp.data)
        self.assertNotIn(b'[Errno 2]', resp.data)
        self.assertIn(b'5.0 - Gemini integrado', resp.data)

    def test_foto_subida_y_exportacion_completa(self):
        buf = io.BytesIO()
        Image.new('RGB', (1300, 1600), '#b0bccb').save(buf, 'JPEG')
        buf.seek(0)
        response = self.client.post(f'/noticia/{self.id}/foto', data={
            'csrf': 'token_de_prueba', 'photo': (buf, 'foto.jpg')},
            content_type='multipart/form-data', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue((editor.MEDIA / f'noticia_{self.id}_autorizada.jpg').exists())
        # La subida reinicia la confirmación de derechos: evita publicación accidental.
        self.assertEqual(db.news_by_id(self.id)['photo_rights_confirmed'], 0)
        db.edit_news(self.id, {'photo_rights_confirmed': 1})
        response = self.client.get(f'/noticia/{self.id}/diseño')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'image/jpeg')
        size = Image.open(io.BytesIO(response.data)).size
        self.assertEqual(size, (1080, 1350))

if __name__ == '__main__':
    unittest.main()
