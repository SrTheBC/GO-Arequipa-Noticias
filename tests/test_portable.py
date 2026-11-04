"""Pruebas aisladas del primer inicio portable, sin red ni Flask."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import portable_launcher as pl


class PortableStartupTests(unittest.TestCase):
    def test_create_config_without_overwriting_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pl.ensure_configuration(root)
            self.assertTrue((root / 'config.json').exists())
            self.assertTrue((root / 'ACCESO_INICIAL.txt').exists())
            self.assertTrue((root / '.env').exists())
            first = (root / '.env').read_text()
            self.assertIn('ADMIN_PASSWORD=', first)
            self.assertIn('SECRET_KEY=', first)
            self.assertNotIn('CAMBIAR_POR_CONTRASENA_LARGA', first)
            (root / 'config.json').write_text('{"personalizado":true}', encoding='utf-8')
            pl.ensure_configuration(root)
            self.assertEqual((root / '.env').read_text(), first)
            self.assertEqual((root / 'config.json').read_text(), '{"personalizado":true}')


if __name__ == '__main__':
    unittest.main()
