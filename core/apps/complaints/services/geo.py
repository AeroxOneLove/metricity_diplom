from __future__ import annotations

import math
from dataclasses import dataclass

CELL_PRECISION = 3
DUPLICATE_RADIUS_M = 50
EARTH_RADIUS_M = 6_371_000.0


@dataclass(frozen=True)
class Cell:
    lat: float
    lon: float


def _validate_precision(precision: int) -> None:
    if not isinstance(precision, int):
        raise TypeError("Точность должна быть целым числом.")
    if precision < 0 or precision > 7:
        raise ValueError("Точность должна быть в диапазоне от 0 до 7.")


def _to_float(value: float | int | str, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Поле '{field_name}' должно быть числом.") from exc


def _round_coordinate(value: float | int | str, precision: int, field_name: str) -> float:
    _validate_precision(precision)
    numeric_value = _to_float(value, field_name)
    return round(numeric_value, precision)


def make_cell_id(lat: float | int | str, lon: float | int | str, precision: int = CELL_PRECISION) -> str:
    rounded_lat = _round_coordinate(lat, precision, "lat")
    rounded_lon = _round_coordinate(lon, precision, "lon")
    return f"{rounded_lat:.{precision}f}:{rounded_lon:.{precision}f}"


def parse_cell_id(cell_id: str) -> Cell:
    if not isinstance(cell_id, str):
        raise TypeError("Идентификатор ячейки должен быть строкой.")
    parts = cell_id.split(":")
    if len(parts) != 2:
        raise ValueError(
            "Некорректный формат cell_id. Ожидается строка вида '56.949:24.105'."
        )

    lat_str, lon_str = parts
    lat = _to_float(lat_str, "lat")
    lon = _to_float(lon_str, "lon")

    return Cell(lat=lat, lon=lon)


def neighbor_cells(cell_id: str, precision: int = CELL_PRECISION) -> list[str]:
    _validate_precision(precision)
    center = parse_cell_id(cell_id)
    step = 10 ** (-precision)

    neighbors: list[str] = []

    for lat_offset in (-step, 0.0, step):
        for lon_offset in (-step, 0.0, step):
            neighbor_id = make_cell_id(
                lat=center.lat + lat_offset,
                lon=center.lon + lon_offset,
                precision=precision,
            )
            neighbors.append(neighbor_id)

    return neighbors


def haversine_m(
    lat1: float | int | str,
    lon1: float | int | str,
    lat2: float | int | str,
    lon2: float | int | str,
) -> float:

    lat1 = _to_float(lat1, "lat1")
    lon1 = _to_float(lon1, "lon1")
    lat2 = _to_float(lat2, "lat2")
    lon2 = _to_float(lon2, "lon2")

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_M * c