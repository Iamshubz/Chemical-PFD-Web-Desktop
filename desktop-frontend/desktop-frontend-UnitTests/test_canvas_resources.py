import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

from src.canvas.resources import (
    clean_string,
    format_component_label,
    normalize_component_label,
    find_svg_path,
    find_svg_file,
    get_component_config_by_name,
)


class CanvasResourcesTests(unittest.TestCase):
    def test_clean_string_removes_separators_and_lowercases(self):
        self.assertEqual(clean_string("Pump / Valve_(A)"), "pumpvalvea")

    def test_format_component_label_success_with_suffix(self):
        self.assertEqual(format_component_label("PUMP", 3, "A"), "PUMP-03-A")

    def test_format_component_label_failure_when_legend_missing(self):
        self.assertEqual(format_component_label("", 3, "A"), "")

    def test_format_component_label_edge_when_count_is_non_numeric(self):
        self.assertEqual(format_component_label("PUMP", "x", ""), "PUMP-x")

    def test_normalize_component_label_preserves_already_formatted_label(self):
        self.assertEqual(normalize_component_label("PUMP-01-A", legend="PUMP", suffix="A"), "PUMP-01-A")

    def test_normalize_component_label_converts_compact_label(self):
        self.assertEqual(normalize_component_label("PUMP1", legend="PUMP"), "PUMP-01")

    def test_get_component_config_by_name_exact_and_clean_match(self):
        component_config = {
            "Centrifugal Pump": {"component": "Centrifugal Pump", "grips": [1, 2, 3]},
        }
        self.assertEqual(get_component_config_by_name("Centrifugal Pump", component_config)["grips"], [1, 2, 3])
        self.assertEqual(get_component_config_by_name("centrifugalpump", component_config)["grips"], [1, 2, 3])
        self.assertEqual(get_component_config_by_name("missing", component_config), {})

    def test_find_svg_path_returns_match_and_none_for_missing(self):
        with TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            svg_dir = base_dir / "ui" / "assets" / "svg" / "Pumps"
            svg_dir.mkdir(parents=True)
            svg_file = svg_dir / "Pump_A.svg"
            svg_file.write_text("<svg></svg>", encoding="utf-8")

            self.assertEqual(find_svg_path("Pump_A", str(base_dir)), str(svg_file))
            self.assertIsNone(find_svg_path("Missing", str(base_dir)))

    def test_find_svg_path_returns_none_when_directory_missing(self):
        with TemporaryDirectory() as tmpdir:
            self.assertIsNone(find_svg_path("Anything", tmpdir))

    def test_find_svg_file_prefers_exact_folder_match_and_falls_back(self):
        with TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            preferred_dir = base_dir / "ui" / "assets" / "svg" / "Pumps"
            preferred_dir.mkdir(parents=True)
            preferred_file = preferred_dir / "Pump_A.svg"
            preferred_file.write_text("<svg></svg>", encoding="utf-8")

            fallback_dir = base_dir / "ui" / "assets" / "svg" / "Other"
            fallback_dir.mkdir(parents=True)
            fallback_file = fallback_dir / "Fallback.svg"
            fallback_file.write_text("<svg></svg>", encoding="utf-8")

            self.assertEqual(find_svg_file("Pump_A.svg", "Pumps", str(base_dir)), str(preferred_file))
            self.assertEqual(find_svg_file("Fallback.svg", "Unknown", str(base_dir)), str(fallback_file))
            self.assertIsNone(find_svg_file("Missing.svg", "Pumps", str(base_dir)))


if __name__ == "__main__":
    unittest.main()
