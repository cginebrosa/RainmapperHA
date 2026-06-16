#!/usr/bin/env python

import argparse
import json
import math
from datetime import date, datetime
from pathlib import Path

import pandas as pd


TOMAP_FILES = {
    "01_Tomap_Last_day.csv": "01d.geojson",
    "02_Tomap_Last_week.csv": "07d.geojson",
    "03_Tomap_Last_two_weeks.csv": "14d.geojson",
    "04_Tomap_Last_three_weeks.csv": "21d.geojson",
    "05_Tomap_Last_month.csv": "30d.geojson",
    "06_Tomap_Last_two_months.csv": "60d.geojson",
    "07_Tomap_Last_three_months.csv": "90d.geojson",
}


def clean_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def dataframe_to_geojson(df, generated_at=None):
    features = []
    for record in df.to_dict(orient="records"):
        try:
            lat = float(record.get("Latitud"))
            lon = float(record.get("Longitud"))
        except (TypeError, ValueError):
            continue

        if math.isnan(lat) or math.isnan(lon):
            continue

        properties = {
            key: clean_value(value)
            for key, value in record.items()
            if key not in ("Latitud", "Longitud")
        }
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat],
                },
                "properties": properties,
            }
        )

    return {
        "type": "FeatureCollection",
        "metadata": {
            "generated_at": generated_at,
        },
        "features": features,
    }


def convert_file(input_file, output_file):
    df = pd.read_csv(input_file)
    missing_columns = {"Latitud", "Longitud"} - set(df.columns)
    if missing_columns:
        raise ValueError(f"{input_file} is missing columns: {', '.join(sorted(missing_columns))}")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    geojson = dataframe_to_geojson(df, generated_at=datetime.now().astimezone().isoformat(timespec="seconds"))
    output_file.write_text(
        json.dumps(geojson, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )
    return len(geojson["features"])


def convert_all(input_dir, output_dir):
    converted = []
    for csv_name, geojson_name in TOMAP_FILES.items():
        input_file = input_dir / csv_name
        output_file = output_dir / geojson_name
        if not input_file.exists():
            print(f"Skipping missing Tomap file: {input_file}")
            continue

        feature_count = convert_file(input_file, output_file)
        converted.append(output_file)
        print(f"Generated {output_file} with {feature_count} station(s)")

    return converted


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert Rainmapper Tomap CSV files to mobile-friendly GeoJSON files."
    )
    parser.add_argument(
        "--input-dir",
        default="Tomap",
        help="Directory containing Tomap CSV files. Default: Tomap",
    )
    parser.add_argument(
        "--output-dir",
        default="PublicData",
        help="Directory where GeoJSON files will be written. Default: PublicData",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    converted = convert_all(input_dir, output_dir)

    if not converted:
        raise SystemExit("No GeoJSON files were generated.")


if __name__ == "__main__":
    main()
