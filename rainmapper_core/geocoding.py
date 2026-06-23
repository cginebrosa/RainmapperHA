"""Shared Google Maps geocoding helpers for Rainmapper station metadata.

The existing data sources enrich station catalogs when a station is new or its
coordinates change. This module keeps that behavior in one place so new sources
do not grow subtly different reverse-geocoding rules.
"""


class GeocodingError(RuntimeError):
    """Raised when station geocoding cannot be completed."""


def google_component(address_components, component_type):
    """Extract a long_name value from Google reverse geocoding components."""
    for component in address_components:
        if component_type in component.get("types", []):
            return str(component.get("long_name") or "").strip()
    return ""


def result_has_type(result, result_type):
    """Return True when a Google reverse geocoding result has a given type."""
    return result_type in result.get("types", [])


def extract_google_metadata(reverse_geocode_result):
    """Extract municipality, province and comarca-like fields from Google results."""
    if not reverse_geocode_result:
        return {"municipality": "", "province": "", "comarca": ""}

    province = ""
    comarca = ""
    municipality = ""
    preferred_results = [
        result
        for result in reverse_geocode_result
        if not result_has_type(result, "plus_code")
    ] or reverse_geocode_result

    for result in preferred_results:
        components = result.get("address_components", [])
        province = province or google_component(components, "administrative_area_level_2")
        comarca = comarca or google_component(components, "administrative_area_level_3")
        municipality = municipality or google_component(components, "administrative_area_level_4")
        if municipality:
            break

    if not municipality:
        for result in preferred_results:
            components = result.get("address_components", [])
            municipality = municipality or google_component(components, "locality")
            municipality = municipality or google_component(components, "postal_town")
            if municipality:
                break

    if comarca and comarca == municipality:
        comarca = ""

    return {
        "municipality": municipality,
        "province": province,
        "comarca": comarca,
    }


def normalize_coordinates(lat, lon):
    """Return numeric latitude/longitude, fixing obviously flipped coordinates."""
    try:
        lat = float(lat)
        lon = float(lon)
        if lat < lon:
            lat, lon = lon, lat
        return lat, lon
    except (TypeError, ValueError) as exc:
        raise GeocodingError("Station latitude/longitude is not valid") from exc


def googlemaps_station_metadata(lat, lon, api_key, language="ES"):
    """Fetch altitude, municipality, province and comarca-like metadata."""
    try:
        import googlemaps
    except ImportError as exc:
        raise GeocodingError("googlemaps package is required for station geocoding") from exc

    if not api_key:
        raise GeocodingError("Google Maps API key is required for station geocoding")

    lat, lon = normalize_coordinates(lat, lon)
    client = googlemaps.Client(key=api_key)
    elevation_result = client.elevation((lat, lon))
    reverse_geocode_result = client.reverse_geocode((lat, lon), language=language)
    metadata = extract_google_metadata(reverse_geocode_result)
    altitude = 0
    if elevation_result:
        altitude = elevation_result[-1].get("elevation", 0)
    return {
        "altitude": altitude,
        "municipality": metadata["municipality"] or "Not found in googlemaps - Check lat/long",
        "province": metadata["province"] or "Not found - Check lat/long",
        "comarca": metadata["comarca"],
    }
