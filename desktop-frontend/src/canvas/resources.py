import os
import json
import csv
import re

def clean_string(s):
    return s.lower().translate(str.maketrans("", "", " ,_/-()"))


def format_component_label(legend, count, suffix):
    legend = (legend or "").strip()
    suffix = (suffix or "").strip()

    if not legend:
        return ""

    try:
        number = int(count)
    except (TypeError, ValueError):
        return f"{legend}-{count}-{suffix}" if suffix else f"{legend}-{count}"

    return f"{legend}-{number:02d}-{suffix}" if suffix else f"{legend}-{number:02d}"


def normalize_component_label(label, legend="", suffix=""):
    label = (label or "").strip()
    legend = (legend or "").strip()
    suffix = (suffix or "").strip()

    if not label:
        return label

    if "-" in label:
        return label

    if legend and label.startswith(legend):
        tail = label[len(legend):]
        if suffix and tail.endswith(suffix):
            number_part = tail[:-len(suffix)]
            if number_part.isdigit():
                return format_component_label(legend, int(number_part), suffix)
        if tail.isdigit():
            return format_component_label(legend, int(tail), suffix)

    match = re.match(r"^([A-Za-z]+)(\d{1,3})([A-Za-z0-9/]+)?$", label)
    if match:
        return format_component_label(match.group(1), int(match.group(2)), match.group(3) or "")

    return label

def load_label_data(base_dir):
    label_data = {}
    
    # Try loading from JSON cache first (New Single Source of Truth)
    json_path = os.path.join(base_dir, "ui", "assets", "components_cache.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    key = item.get("object", "").strip() or item.get("name", "").strip()
                    if not key: continue
                    
                    label_data[clean_string(key)] = {
                        "legend": item.get("legend", "").strip(),
                        "suffix": item.get("suffix", "").strip(),
                        "count": 0
                    }
            return label_data
        except Exception as e:
            print("Failed to load components_cache.json:", e)

    # Fallback to legacy CSV
    try:
        csv_path = os.path.join(base_dir, "ui", "assets", "Component_Details.csv")
        if os.path.exists(csv_path):
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    key = row.get("object", "").strip() or row.get("name", "").strip()
                    if not key: continue

                    label_data[clean_string(key)] = {
                        "legend": row.get("legend", "").strip(),
                        "suffix": row.get("suffix", "").strip(),
                        "count": 0
                    }
    except Exception as e:
        print("Failed to load Component_Details.csv:", e)
    return label_data

def load_config(base_dir):
    component_config = {}
    try:
        path = os.path.join(base_dir, "ui", "assets", "grips.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                component_config[item["component"]] = item
    except Exception as e:
        print("Failed to load grips.json:", e)
    return component_config

def find_svg_path(name, base_dir):
    # ID_MAP removed (Legacy)
    # name = ID_MAP.get(name, name)
    
    svg_dir = os.path.join(base_dir, "ui", "assets", "svg")
    target = clean_string(name)

    if not os.path.exists(svg_dir):
        print(f"SVG directory missing: {svg_dir}")
        return None

    for root, _, files in os.walk(svg_dir):
        for f in files:
            if not f.lower().endswith(".svg"):
                continue

            fname = f[:-4]
            # Direct match
            if fname == name:
                return os.path.join(root, f)
            # Clean match
            if clean_string(fname) == target:
                return os.path.join(root, f)

    print(f"No SVG found for: {name}")
    return None

def get_component_config_by_name(name, component_config):
    # ID_MAP removed (Legacy)
    # name = ID_MAP.get(name, name)

    if name in component_config:
        return component_config[name]

    target = clean_string(name)
    for key, cfg in component_config.items():
        if clean_string(key) == target:
            return cfg

    return {}


FOLDER_MAP = {
    "Furnance and Boilers": "Furnaces and Boilers",
    "Storage Vessels/ Tanks": "Storage Vessels Tanks",
    "Size Reduction Equipments": "Size Reduction Equipements"
}

def find_svg_file(filename, parent, base_dir):
    """
    Find SVG file by exact filename and parent category.
    Preferred over find_svg_path (fuzzy match).
    """
    if not filename:
        return None
        
    folder = FOLDER_MAP.get(parent, parent)
    
    # Try specific path first
    path = os.path.join(base_dir, "ui", "assets", "svg", folder, filename)
    if os.path.exists(path):
        return path
        
    # Fallback: Search in all svg subdirectories
    svg_root = os.path.join(base_dir, "ui", "assets", "svg")
    for root, _, files in os.walk(svg_root):
        if filename in files:
            return os.path.join(root, filename)
            
    return None
