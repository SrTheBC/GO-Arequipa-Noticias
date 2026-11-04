"""V6: logo auténtico, migración no destructiva y encuadre persistente."""
import io
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from PIL import Image

os.environ.setdefault('SECRET_KEY', 'clave-v6-ficticia-superior-a-24-caracteres')
os.environ.setdefault('ADMIN_PASSWORD', 'solo-pruebas-no-publicar')

import db
import graphics
import app as editor


class VisualV6(unittest.TestCase):
    def test_logo_bundled_and_render_two_models(self):
        logo = Path(__file__).resolve().parents[1] / 'assets/logo_go.png'
        self.assertTrue(logo.is_file())
        self.assertEqual(Image.open(logo).mode, 'RGBA')
        with tempfile.TemporaryDirectory() as folder:
            photo = Path(folder) / 'foto.jpg'
            Image.new('RGB', (1300,1700), '#5d94bd').save(photo)
            for modelo in ('modelo_1','modelo_2'):
                state = dict(model=modelo, cintillo='NOTICIAS AREQUIPA',
                             titulo='TITULAR PARA LA PRUEBA DEL EDITOR VISUAL',
                             bajada='Texto pequeño completo para verificar que el diseño no lo recorta.',
                             photo_rights_confirmed=1,
                             photo_inset_x=50, photo_inset_y=20, photo_inset_zoom=1.4,
                             photo_main_x=50,photo_main_y=35,photo_main_zoom=1.1)
                data=io.BytesIO()
                graphics.render(state, photo, data, photo if modelo == 'modelo_2' else None,
                                logo_path=logo)
                data.seek(0)
                self.assertEqual(Image.open(data).size,(1080,1350))

    def test_crop_focus_moves_without_cropping_title(self):
        im = Image.new('RGB',(600,1200),'#0044ff')
        out=graphics.crop_focus(im,(300,300),focus_x=50,focus_y=0,zoom=1)
        self.assertEqual(out.size,(300,300))
        self.assertEqual(graphics.clamp_float('',1,3,1),1)
        self.assertEqual(graphics.clamp_float('100000',1,3,1),3)

    def test_old_sqlite_table_gets_new_columns_and_preserves_old_news(self):
        with tempfile.TemporaryDirectory() as temp:
            dbpath=Path(temp)/'antigua.db'
            con=sqlite3.connect(dbpath)
            con.execute('CREATE TABLE news (id INTEGER PRIMARY KEY, unique_key TEXT UNIQUE, titulo TEXT, status TEXT, source_published TEXT)')
            con.execute("INSERT INTO news (id,unique_key,titulo,status) VALUES (1,'antigua','Titular guardado','pendiente')")
            con.commit();con.close()
            old=db.DB_PATH
            db.DB_PATH=str(dbpath)
            try:
                db.init_db()
                with db.connect() as conn:
                    cols={r[1] for r in conn.execute('PRAGMA table_info(news)')}
                    record=conn.execute('SELECT * FROM news WHERE id=1').fetchone()
                self.assertTrue({'photo_main_x','photo_inset_y','photo_inset_zoom'}.issubset(cols))
                self.assertEqual(record['titulo'],'Titular guardado')
            finally:
                db.DB_PATH=old

    def test_preview_endpoint_and_save_framing(self):
        with tempfile.TemporaryDirectory() as temp:
            old_db, old_media = db.DB_PATH, editor.MEDIA
            db.DB_PATH = str(Path(temp)/'data/noticias.db')
            editor.MEDIA=Path(temp)/'data/media';editor.MEDIA.mkdir(parents=True,exist_ok=True)
            try:
                db.init_db()
                db.insert_news(dict(unique_key='v6news',source='Prueba',source_url='https://example.org',
                    source_published='2026-11-04T10:00:00Z',discovered_at='2026-11-04T10:00:00Z',
                    original_title='Nota de pruebas',region='arequipa',cintillo='NOTICIA DE PRUEBA',
                    titulo='TÍTULO DE EJEMPLO PARA LA VISTA PREVIA',
                    bajada='Texto de prueba sin inventar hechos.',status='pendiente'))
                ident=db.list_news()[0]['id']
                editor.app.config['TESTING']=True
                with editor.app.test_client() as client:
                    with client.session_transaction() as sess:
                        sess['auth']=True;sess['csrf']='token-v6'
                    res=client.post(f'/noticia/{ident}/vista_previa',data={'csrf':'token-v6'})
                    self.assertEqual(res.status_code,400)
                    main=editor.MEDIA/'foto_verdadera.jpg'
                    Image.new('RGB',(1500,1600),'#839fbf').save(main)
                    db.edit_news(ident,{'local_photo_path':str(main)})
                    res=client.post(f'/noticia/{ident}/vista_previa',data={
                        'csrf':'token-v6','model':'modelo_2','cintillo':'ALERTA REGIONAL',
                        'titulo':'TITULAR NUEVO EN VISTA PREVIA',
                        'bajada':'Texto corto de vista previa',
                        'photo_inset_x':'65','photo_inset_zoom':'1.85',
                        'photo_main_y':'5'})
                    self.assertEqual(res.status_code,200)
                    self.assertEqual(res.mimetype,'image/jpeg')
                    self.assertEqual(Image.open(io.BytesIO(res.data)).size,(1080,1350))
                    self.assertEqual(db.news_by_id(ident)['titulo'],'TÍTULO DE EJEMPLO PARA LA VISTA PREVIA')
                    saved=client.post(f'/noticia/{ident}/guardar',data={
                        'csrf':'token-v6','status':'pendiente','model':'modelo_2',
                        'cintillo':'CINTILLO','titulo':'TITULO','bajada':'Bajada',
                        'copy_text':'#Arequipa | Copy de prueba.',
                        'photo_main_y':'5', 'photo_inset_zoom':'1.85', 'photo_inset_x':'65'},
                        headers={'X-GO-Autosave':'1'})
                    self.assertEqual(saved.status_code,200)
                    record=db.news_by_id(ident)
                    self.assertAlmostEqual(record['photo_main_y'],5.0)
                    self.assertAlmostEqual(record['photo_inset_zoom'],1.85)
            finally:
                db.DB_PATH, editor.MEDIA = old_db, old_media


if __name__ == '__main__':
    unittest.main()
