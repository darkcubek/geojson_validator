from validator import check_feature_types, check_point_polygon_pairs


def point(name: str) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [69.0, 41.0]},
        "properties": {"iconCaption": name},
    }


def polygon(name: str) -> dict:
    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [68.0, 40.0],
                    [70.0, 40.0],
                    [70.0, 42.0],
                    [68.0, 42.0],
                    [68.0, 40.0],
                ]
            ],
        },
        "properties": {"description": name},
    }


def feature(geometry_type: str, properties: dict | None = None) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": geometry_type, "coordinates": []},
        "properties": properties or {},
    }


def test_check_feature_types_passes_for_valid_point_and_polygon():
    result = check_feature_types([point("V001"), polygon("31001")])

    assert result["passed"] is True
    assert result["errors"] == []


def test_check_feature_types_reports_invalid_point_name():
    result = check_feature_types([point("001")])

    assert result["passed"] is False
    assert result["errors"] == [
        "Feature[0]: Point с недопустимым именем '001' "
        "(ожидается V000–V999 в поле iconCaption)"
    ]


def test_check_feature_types_reports_invalid_polygon_name():
    result = check_feature_types([polygon("3101")])

    assert result["passed"] is False
    assert result["errors"] == [
        "Feature[0]: Polygon с недопустимым именем '3101' "
        "(ожидается 5-значный номер в поле description)"
    ]


def test_check_feature_types_reports_unsupported_geometry_type():
    result = check_feature_types([feature("LineString", {"name": "V001"})])

    assert result["passed"] is False
    assert result["errors"] == [
        "Feature[0]: недопустимый тип геометрии 'LineString' (имя: 'None')"
    ]


def test_check_point_polygon_pairs_passes_for_matching_pair():
    result = check_point_polygon_pairs([point("V001"), polygon("31001")])

    assert result["passed"] is True
    assert result["errors"] == []


def test_check_point_polygon_pairs_reports_missing_polygon():
    result = check_point_polygon_pairs([point("V001")])

    assert result["passed"] is False
    assert result["errors"] == [
        "Point 'V001' не имеет соответствующего Polygon '31001'"
    ]


def test_check_point_polygon_pairs_reports_missing_point():
    result = check_point_polygon_pairs([polygon("31001")])

    assert result["passed"] is False
    assert result["errors"] == [
        "Polygon '31001' не имеет соответствующего Point 'V001'"
    ]


def test_check_point_polygon_pairs_ignores_invalid_names():
    result = check_point_polygon_pairs([point("001"), polygon("abcde")])

    assert result["passed"] is True
    assert result["errors"] == []
