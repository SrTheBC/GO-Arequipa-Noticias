"""Pruebas del contrato: sin mensajes internos, cinco hashtags al cierre."""
import tempfile
import unittest
from pathlib import Path

import db
from editorial import derive_editorial, hashtag_count_final, normalize_copy


class CopyV41Tests(unittest.TestCase):
    def test_legacy_national_screenshot(self):
        previous = ("#Perú | Alerta de tsunami del Sismate sonó hoy en Perú: "
                    "¿por qué se activó y qué debes saber del simulacro de Indeci?.\n\n"
                    "El simulacro contempló un terremoto de magnitud 8.8 Mw, "
                    "con epicentro a 60 km del Callao.\n\n"
                    "Información pendiente de contraste editorial.\n\n"
                    "#NoticiasArequipa")
        updated = normalize_copy(previous, 'nacional_excepcional',
                                 'Alerta de tsunami en Perú durante simulacro de Indeci',
                                 'Sonó el Sismate durante un simulacro.')
        self.assertEqual(updated.splitlines()[0].split(' |')[0], '#Perú')
        self.assertIn('epicentro a 60 km del Callao', updated)
        self.assertNotIn('Información pendiente', updated)
        self.assertEqual(hashtag_count_final(updated), 5)
        self.assertNotIn('#NoticiasArequipa', updated)
        self.assertEqual(normalize_copy(updated, 'nacional_excepcional', 'Alerta de tsunami en Perú durante simulacro de Indeci', 'Sonó el Sismate durante un simulacro.'),updated)

    def test_fallback_local_five_relevant(self):
        d = derive_editorial('Capturan a sospechoso en Socabaya',
                             'La Policía informó sobre intervención en Socabaya.',
                             'arequipa', 'Radio Yaraví')
        self.assertTrue(d['copy_text'].startswith('#Arequipa |'))
        self.assertEqual(hashtag_count_final(d['copy_text']), 5)
        self.assertIn('#SeguridadCiudadana', d['copy_text'])
        self.assertNotIn('Información pendiente', d['copy_text'])

    def test_migration_preserves_approved_and_body_of_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = db.DB_PATH
            db.DB_PATH = str(Path(tmp)/'news.db')
            try:
                db.init_db()
                for idx,status in enumerate(('pendiente','revisada','aprobada','publicada')):
                    db.insert_news({
                        'unique_key': f'test-{idx}',
                        'source': 'Radio Yaraví',
                        'source_url': f'https://example.com/{idx}',
                        'source_published': '2026-11-04T13:00:00Z',
                        'discovered_at': '2026-11-04T13:00:00Z',
                        'original_title': 'Lluvias en Camaná',
                        'excerpt': 'Se prevén lluvias.',
                        'region': 'arequipa',
                        'status': status,
                        'cintillo': 'ALERTA METEOROLÓGICA',
                        'copy_text': '#Arequipa | Mi texto redactado por el editor.\n\nInformación pendiente de contraste editorial.\n\n#NoticiasArequipa',
                        'ai_status': 'borrador_basico_revisar'
                    })
                self.assertEqual(db.normalizar_copys_antiguos(),2)
                self.assertEqual(db.normalizar_copys_antiguos(),0)
                for row in db.list_news():
                    if row['status'] in ('pendiente','revisada'):
                        self.assertIn('Mi texto redactado por el editor.',row['copy_text'])
                        self.assertNotIn('pendiente de contraste',row['copy_text'])
                        self.assertEqual(hashtag_count_final(row['copy_text']),5)
                    else:
                        self.assertIn('Información pendiente',row['copy_text'])
            finally:
                db.DB_PATH = old


if __name__ == '__main__':
    unittest.main()
