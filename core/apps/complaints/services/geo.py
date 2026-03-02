from __future__ import annotations

import math
from typing import List


CELL_PRECISION = 3
DUPLICATE_RADIUS_M = 50


def make_cell_id(lat: float, lon: float, precision: int = CELL_PRECISION) -> str:

    lat_r = round(float(lat), precision)
    lon_r = round(float(lon), precision)
    return f"{lat_r:.{precision}f}:{lon_r:.{precision}f}"


def neighbor_cells(cell_id: str, precision: int = CELL_PRECISION) -> List[str]:

    try:
        lat_str, lon_str = cell_id.split(":", maxsplit=1)
    except ValueError as exc:  
        raise ValueError("cell_id must be in 'lat:lon' format") from exc

    lat = float(lat_str)
    lon = float(lon_str)

    step = 10 ** (-precision)
    cells: List[str] = []
    for dlat in (-step, 0, step):
        for dlon in (-step, 0, step):
            cells.append(make_cell_id(lat + dlat, lon + dlon, precision))
    return cells


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:

    r_earth = 6_371_000 

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return r_earth * c


__all__ = [
    "CELL_PRECISION",
    "DUPLICATE_RADIUS_M",
    "make_cell_id",
    "neighbor_cells",
    "haversine_m",
]
