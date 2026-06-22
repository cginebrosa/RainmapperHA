import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TRANSLATIONS_PATH = REPO_ROOT / "rainmapper_core" / "viewers" / "maplibre-viewer" / "translations.json"


class MapLibreTranslationsTests(unittest.TestCase):
    def test_translations_have_matching_language_keys(self) -> None:
        payload = json.loads(TRANSLATIONS_PATH.read_text(encoding="utf-8"))

        self.assertEqual(set(payload), {"en", "es", "ca"})
        english_keys = set(payload["en"])
        self.assertGreater(len(english_keys), 20)

        for language in ("es", "ca"):
            self.assertEqual(set(payload[language]), english_keys)

    def test_translation_values_are_strings(self) -> None:
        payload = json.loads(TRANSLATIONS_PATH.read_text(encoding="utf-8"))

        for language, translations in payload.items():
            with self.subTest(language=language):
                self.assertTrue(all(isinstance(value, str) for value in translations.values()))


if __name__ == "__main__":
    unittest.main()
