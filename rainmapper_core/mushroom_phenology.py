"""Lightweight season classification shared by territorial readers and Predictor."""
from datetime import date


def season_phase_for_months(target_date: date, main_months, secondary_months) -> str:
    """Classify a date using the editable profile's original seasonal windows."""
    if target_date.month in main_months:
        return "main"
    if target_date.month in secondary_months:
        return "secondary"
    return "out_of_season" if main_months or secondary_months else "unknown"
