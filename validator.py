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

def _ok(description: str) -> dict:
    return {
        "passed": True,              # проверка пройдена
        "description": description,  # суть проверки
        "errors": [],                # список ошибок (пуст)
    }


def _fail(description: str, errors: list) -> dict:
    return {
        "passed": False,             # проверка не пройдена
        "description": description,  # суть проверки
        "errors": errors,            # список найденных ошибок
    }


def _result(description: str, errors: list) -> dict:
    return _ok(description) if not errors else _fail(description, errors)


def check_feature_types(features: list) -> dict:
    errors = []
    for i, f in enumerate(features):
        geom = f.get("geometry") or {}
        t = geom.get("type")
        if t == "Point":
            n = point_name(f)
            if not n or not POINT_NAME_RE.match(n):
                errors.append(
                    f"Feature[{i}]: Point с недопустимым именем '{n}' "
                    "(ожидается V000–V999 в поле iconCaption)"
                )
        elif t == "Polygon":
            n = polygon_name(f)
            if not n or not POLYGON_NAME_RE.match(n):
                errors.append(
                    f"Feature[{i}]: Polygon с недопустимым именем '{n}' "
                    "(ожидается 5-значный номер в поле description)"
                )
        else:
            n = feature_name(f)
            errors.append(
                f"Feature[{i}]: недопустимый тип геометрии '{t}' (имя: '{n}')"
            )
    return _result(
        "Только Point(V###) и Polygon(5 цифр) допустимы в файле",
        errors,
    )

def check_point_polygon_pairs(features: list) -> dict:
    """Each Point V### must have a corresponding Polygon 31###, and vice versa."""
    errors = []
    points = {
        point_name(f): f for f in features
        if (f.get("geometry") or {}).get("type") == "Point"
        and POINT_NAME_RE.match(point_name(f) or "")
    }
    polys = {
        polygon_name(f): f for f in features
        if (f.get("geometry") or {}).get("type") == "Polygon"
        and POLYGON_NAME_RE.match(polygon_name(f) or "")
    }

    for pn in points:
        exp = expected_polygon(pn)
        if exp not in polys:
            errors.append(f"Point '{pn}' не имеет соответствующего Polygon '{exp}'")

    for pln in polys:
        exp = expected_point(pln)
        if exp not in points:
            errors.append(f"Polygon '{pln}' не имеет соответствующего Point '{exp}'")

    return _result(
        "Каждый Point V### должен иметь Polygon 31### и наоборот",
        errors,
    )

def check_closed_polygons(features: list) -> dict:
    """First and last coordinate of every ring must be identical."""
    errors = []
    for f in features:
        if (f.get("geometry") or {}).get("type") != "Polygon":
            continue
        n = polygon_name(f)
        rings = f["geometry"].get("coordinates") or []
        for ri, ring in enumerate(rings):
            ring_label = f"Polygon '{n}' кольцо #{ri}"
            if len(ring) < 4:
                errors.append(f"{ring_label}: слишком мало точек ({len(ring)}, минимум 4)")
            elif ring[0] != ring[-1]:
                errors.append(
                    f"{ring_label}: не замкнуто — "
                    f"первая={ring[0]}, последняя={ring[-1]}"
                )
    return _result("Все полигоны должны быть замкнуты", errors)


def check_points_inside_polygons(features: list) -> dict:
    """Each Point V### must be spatially contained in Polygon 31###."""
    errors = []
    points = {
        point_name(f): f for f in features
        if (f.get("geometry") or {}).get("type") == "Point"
        and POINT_NAME_RE.match(point_name(f) or "")
    }
    polys = {
        polygon_name(f): f for f in features
        if (f.get("geometry") or {}).get("type") == "Polygon"
        and POLYGON_NAME_RE.match(polygon_name(f) or "")
    }

    for pn, pf in points.items():
        poly_name_str = expected_polygon(pn)
        if poly_name_str not in polys:
            continue

        try:
            pt_geom = shape(pf["geometry"])
            pg_geom = make_valid(shape(polys[poly_name_str]["geometry"]))
            if not pg_geom.contains(pt_geom):
                c = pf["geometry"]["coordinates"]
                errors.append(
                    f"Point '{pn}' ({c[0]:.6f}, {c[1]:.6f}) "
                    f"не находится внутри Polygon '{poly_name_str}'"
                )
        except Exception as exc:
            errors.append(
                f"Ошибка при проверке '{pn}' в '{poly_name_str}': {exc}"
            )

    return _result(
        "Каждый Point V### должен находиться внутри Polygon 31###",
        errors,
    )

if __name__ == "__main__":
    main()