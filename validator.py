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

if __name__ == "__main__":
    main()