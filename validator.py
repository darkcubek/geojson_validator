import json
import re
import sys
import argparse
from typing import Optional
import requests
from shapely.geometry import shape
from shapely.validation import make_valid


STORES_API_URL = "https://fix-uzb.com/api/stores"

POINT_NAME_RE = re.compile(r"^V\d{3}$")
POLYGON_NAME_RE = re.compile(r"^\d{5}$")
COORD_TOLERANCE = 0.001 

parser = argparse.ArgumentParser(
    description="Валидатор GeoJSON для магазинов fix-uzb.com"
)
parser.add_argument(
    "input",
    nargs="?",
    help="Путь к GeoJSON файлу (если не указан — читается из stdin)",
)
parser.add_argument(
    "-o", "--output",
    help="Путь для записи результата JSON (если не указан — выводится в stdout)",
)
parser.add_argument("--indent", type=int, default=2, help="Отступ в JSON (по умолчанию 2)")
args = parser.parse_args()

try:
    if args.input:
        with open(args.input, encoding="utf-8") as fh:
            geojson = json.load(fh)
    else:
        geojson = json.load(sys.stdin)
except FileNotFoundError:
    sys.exit(f"Файл не найден: {args.input}")
except json.JSONDecodeError as exc:
    out = json.dumps(
        {"valid": False, "fatal": f"Некорректный JSON: {exc}"},
        ensure_ascii=False,
        indent=args.indent,
    )
    print(out)
    sys.exit(1)

try:
    if args.input:
        with open(args.input, encoding="utf-8") as fh:
            geojson = json.load(fh)
    else:
        geojson = json.load(sys.stdin)
except FileNotFoundError:
    sys.exit(f"Файл не найден: {args.input}")
except json.JSONDecodeError as exc:
    out = json.dumps(
        {"valid": False, "fatal": f"Некорректный JSON: {exc}"},
        ensure_ascii=False,
        indent=args.indent,
    )
    print(out)
    sys.exit(1)

if geojson.get("type") != "FeatureCollection":
    result = {
        "valid": False,
        "fatal": "Входной файл не является GeoJSON FeatureCollection",
        "summary": {},
        "checks": {},
    }
    print(json.dumps(result, ensure_ascii=False, indent=args.indent))
    sys.exit(1)

features = geojson.get("features") or []

def point_name(feature):
    props = feature.get("properties") or {}
    return props.get("iconCaption") or props.get("name") or props.get("Name")

def polygon_name(feature):
    props = feature.get("properties") or {}
    return props.get("description") or props.get("name") or props.get("Name")

def feature_name(feature):
    geom_type = (feature.get("geometry") or {}).get("type")
    if geom_type == "Point":
        return point_name(feature)
    if geom_type == "Polygon":
        return polygon_name(feature)
    return None

def expected_polygon(pt_name):
    return "31" + pt_name[1:]

def expected_point(poly_name):
    return "V" + poly_name[2:]

if __name__ == "__main__":
    main()