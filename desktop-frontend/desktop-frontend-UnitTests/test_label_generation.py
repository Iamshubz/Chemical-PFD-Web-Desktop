import csv
import importlib.util
import json
import os


PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

RESOURCES_MODULE_PATH = os.path.join(PROJECT_ROOT, "src", "canvas", "resources.py")
_spec = importlib.util.spec_from_file_location("desktop_resources", RESOURCES_MODULE_PATH)
_module = importlib.util.module_from_spec(_spec)
assert _spec is not None and _spec.loader is not None
_spec.loader.exec_module(_module)

clean_string = _module.clean_string
format_component_label = _module.format_component_label
normalize_component_label = _module.normalize_component_label
load_label_data = _module.load_label_data


def test_format_component_label_with_suffix_and_zero_padding():
    assert format_component_label("P", 1, "A") == "P-01-A"


def test_format_component_label_without_suffix():
    assert format_component_label("HEX", 12, "") == "HEX-12"


def test_format_component_label_returns_empty_when_legend_missing():
    assert format_component_label("", 1, "A") == ""


def test_normalize_component_label_preserves_hyphenated_labels():
    assert normalize_component_label("P-01-A", "P", "A") == "P-01-A"


def test_normalize_component_label_from_legend_number_suffix_pattern():
    assert normalize_component_label("P1A", "P", "A") == "P-01-A"


def test_normalize_component_label_from_compact_pattern_without_args():
    assert normalize_component_label("HEX12B") == "HEX-12-B"


def test_normalize_component_label_returns_original_when_no_known_pattern():
    assert normalize_component_label("UNKNOWN_LABEL") == "UNKNOWN_LABEL"


def test_clean_string_normalizes_symbols_and_spacing():
    assert clean_string("In-flow Line (A)") == "inflowlinea"


def test_load_label_data_prefers_json_cache_over_csv(tmp_path):
    base_dir = tmp_path
    assets_dir = base_dir / "ui" / "assets"
    assets_dir.mkdir(parents=True)

    json_payload = [
        {"object": "PumpUnit", "legend": "P", "suffix": "A"},
        {"name": "Heat Exchanger", "legend": "HEX", "suffix": ""},
    ]

    with open(assets_dir / "components_cache.json", "w", encoding="utf-8") as f:
        json.dump(json_payload, f)

    with open(assets_dir / "Component_Details.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["object", "name", "legend", "suffix"])
        writer.writeheader()
        writer.writerow({"object": "ShouldNotBeUsed", "name": "", "legend": "X", "suffix": "Z"})

    result = load_label_data(str(base_dir))

    assert result["pumpunit"] == {"legend": "P", "suffix": "A", "count": 0}
    assert result["heatexchanger"] == {"legend": "HEX", "suffix": "", "count": 0}
    assert "shouldnotbeused" not in result


def test_load_label_data_falls_back_to_csv_when_json_missing(tmp_path):
    base_dir = tmp_path
    assets_dir = base_dir / "ui" / "assets"
    assets_dir.mkdir(parents=True)

    with open(assets_dir / "Component_Details.csv", "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["object", "name", "legend", "suffix"])
        writer.writeheader()
        writer.writerow({"object": "inflowline", "name": "", "legend": "IN", "suffix": ""})
        writer.writerow({"object": "", "name": "Heat Exchanger", "legend": "HEX", "suffix": "B"})

    result = load_label_data(str(base_dir))

    assert result["inflowline"] == {"legend": "IN", "suffix": "", "count": 0}
    assert result["heatexchanger"] == {"legend": "HEX", "suffix": "B", "count": 0}
