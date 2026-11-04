"""Pruebas offline del generador local y migración sin pérdidas de cambios."""
import tempfile
import unittest
from pathlib import Path

import db
from editorial import derive_editorial, topic, is_legacy_placeholder


class DynamicEditorialTest(unittest.TestCase):
    def test_different_topics_have_distinct_cintillos(self):
        samples = [
            ('Capturan a dos sospechosos en Arequipa', 'La PNP realizó un operativo', 'OPERATIVO POLICIAL'),
            ('Contraloría detecta deficiencias en carretera de Caylloma', 'Informe de control', 'CONTRALORÍA ADVIERTE'),
            ('Advierten fuertes vientos en Caravelí', 'Senamhi prevé ráfagas de viento', 'ALERTA METEOROLÓGICA'),
            ('Crean feria de empleo en Arequipa', 'Ofrecerán puestos de trabajo', 'OPORTUNIDAD LABORAL'),
            ('Nacimientos en Arequipa disminuyeron', 'El reporte analiza estadísticas de salud', 'CAMBIO DEMOGRÁFICO'),
        ]
        got = [topic(t, e)[0] for t,e,_ in samples]
        self.assertEqual(got, [x[2] for x in samples])
        self.assertEqual(len(set(got)), len(samples))
        for cintillo in got:
            self.assertLessEqual(len(cintillo), 40)
            self.assertFalse(is_legacy_placeholder(cintillo))

    def test_copy_uses_source_and_no_filler(self):
        data=derive_editorial('Capturan a sospechoso en Arequipa',
            'La Policía Nacional informó sobre una intervención en el Cercado.',
            'arequipa', 'Radio Yaraví')
        self.assertEqual(data['cintillo'], 'OPERATIVO POLICIAL')
        self.assertTrue(data['copy_text'].startswith('#Arequipa |'))
        self.assertIn('Radio Yaraví', data['copy_text'])
        self.assertNotIn('Información pendiente de contraste editorial', data['copy_text'])
        self.assertIn('#GOArequipaNoticias', data['copy_text'])
        self.assertNotIn('🚨', data['copy_text'])

    def test_migration_only_placeholder_unapproved(self):
        with tempfile.TemporaryDirectory() as temp:
            old_path=db.DB_PATH
            db.DB_PATH=str(Path(temp) / 'noticias.db')
            try:
                db.init_db()
                for idx, status in enumerate(('pendiente','revisada','aprobada','publicada')):
                    db.insert_news(dict(unique_key=f'test{idx}', source='Fuente',
                        source_url=f'https://example.org/{idx}',
                        source_published='2026-11-03T16:00:00+00:00',
                        discovered_at='2026-11-03T16:00:00+00:00',
                        original_title='Obras en la carretera de Caylloma',
                        excerpt='Se realizan trabajos en la vía.', region='arequipa', status=status,
                        cintillo='INFORMACIÓN EN DESARROLLO', titulo='MI TÍTULO EDITADO',
                        bajada='Mi bajada editada',
                        copy_text='Mi copy revisado y diferente al mensaje por defecto',
                        ai_status='borrador_basico_revisar'))
                count=db.actualizar_borradores_antiguos()
                self.assertEqual(count, 2)
                rows=db.list_news()
                for r in rows:
                    self.assertEqual(r['titulo'], 'MI TÍTULO EDITADO')
                    self.assertEqual(r['bajada'], 'Mi bajada editada')
                    self.assertEqual(r['copy_text'], 'Mi copy revisado y diferente al mensaje por defecto')
                    if r['status'] in ('pendiente','revisada'):
                        self.assertEqual(r['cintillo'], 'OBRAS VIALES')
                    else:
                        self.assertEqual(r['cintillo'], 'INFORMACIÓN EN DESARROLLO')
                self.assertEqual(db.actualizar_borradores_antiguos(), 0)
            finally:
                db.DB_PATH=old_path

if __name__ == '__main__':
    unittest.main()
