#!/usr/bin/env python3
"""Resident geography adapter for the isolated preview, not a worker job."""
import argparse
import json
import logging
from pathlib import Path
import sqlite3
import sys
from contextlib import ExitStack

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rainmapper_core.mushroom_map_municipalities import MunicipalityReader
from rainmapper_core.mushroom_map_terrain import TerrainReader
from rainmapper_core.mushroom_map_land import LandReader
from rainmapper_core.mushroom_map_forest import ForestReader
from rainmapper_core.mushroom_map_ecology import EcologyReader, POLICY, prediction_candidates
from rainmapper_core.mushroom_map_ph import OpenLandMapPHReader
from rainmapper_core.mushroom_geography_store import SourceIdentities
from rainmapper_core.mushroom_soil_water_state import available_water_capacity_mm


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--municipalities")
    parser.add_argument("--municipalities-edition", default="unspecified")
    parser.add_argument("--terrain-index")
    parser.add_argument("--soil-root")
    parser.add_argument("--dem-root")
    parser.add_argument("--regional-root")
    parser.add_argument("--land-cover")
    parser.add_argument("--geology")
    parser.add_argument("--land-cover-parts")
    parser.add_argument("--geology-parts")
    parser.add_argument("--forest-index")
    parser.add_argument("--forest-catalogs")
    parser.add_argument("--profiles")
    parser.add_argument("--ecology-catalogs")
    parser.add_argument("--gis-mappings")
    parser.add_argument("--openlandmap-ph")
    parser.add_argument("--geography-sources")
    parser.add_argument("--ecology-ph-source", choices=('soilgrids','openlandmap'), default='soilgrids')
    args = parser.parse_args()
    sources = SourceIdentities(args.geography_sources)
    ecology_paths = (args.profiles, args.ecology_catalogs, args.gis_mappings)
    if any(ecology_paths) and not all(ecology_paths):
        parser.error("Ecology requires profiles, catalogs and GIS mappings")
    with ExitStack() as cleanup:
        municipality = terrain = forest = openlandmap = None
        ecology = None
        if args.profiles:
            try:
                ecology = EcologyReader(*ecology_paths, ph_source=args.ecology_ph_source)
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
                logging.getLogger(__name__).exception("Prediction map geography: ecology reader initialization failed")
        if args.openlandmap_ph:
            try:
                openlandmap = OpenLandMapPHReader(args.openlandmap_ph, sources=sources)
                cleanup.callback(openlandmap.close)
            except (ImportError,OSError,ValueError,KeyError,TypeError,RuntimeError) as error:
                logging.getLogger(__name__).exception("Prediction map geography: OpenLandMap reader initialization failed")
        if args.forest_index:
            try:
                forest = ForestReader(args.forest_index, catalogs=args.forest_catalogs, sources=sources)
                cleanup.callback(forest.close)
            except (ImportError, OSError, ValueError, RuntimeError, sqlite3.Error) as error:
                logging.getLogger(__name__).exception("Prediction map geography: forest reader initialization failed")
        land_readers = {}
        for kind, path in (("vegetation", args.land_cover), ("geology", args.geology)):
            if path:
                try:
                    parts = args.land_cover_parts if kind == 'vegetation' else args.geology_parts
                    land_readers[kind] = LandReader(path, kind, parts=parts, sources=sources)
                    cleanup.callback(land_readers[kind].close)
                except (ImportError, OSError, ValueError, RuntimeError, sqlite3.Error) as error:
                    logging.getLogger(__name__).exception("Prediction map geography: %s reader initialization failed", kind)
        if args.municipalities:
            try:
                municipality = MunicipalityReader(args.municipalities, edition=args.municipalities_edition)
                cleanup.callback(municipality.close)
            except (ImportError, OSError, ValueError, RuntimeError, sqlite3.Error) as error:
                logging.getLogger(__name__).exception("Prediction map geography: municipality reader initialization failed")
        if args.terrain_index:
            if not all((args.soil_root, args.dem_root, args.regional_root)):
                parser.error("Terrain index requires all three data roots")
            try:
                terrain = TerrainReader(args.terrain_index, {"soil": args.soil_root, "dem": args.dem_root, "regional": args.regional_root}, sources=sources)
                cleanup.callback(terrain.close)
            except (ImportError, OSError, ValueError, RuntimeError, sqlite3.Error) as error:
                logging.getLogger(__name__).exception("Prediction map geography: terrain reader initialization failed")
        while True:
            line = sys.stdin.readline(4097)
            if not line:
                break
            if len(line.encode('utf-8')) > 4096:
                raise ValueError("geography_request_too_large")
            request = json.loads(line)
            if request.get("op") == "capabilities":
                required = [terrain is not None]
                for configured, reader in ((args.municipalities,municipality),
                        (args.forest_index,forest),(args.profiles,ecology),
                        (args.openlandmap_ph,openlandmap)):
                    if configured:
                        required.append(reader is not None)
                required.extend(kind in land_readers for kind,path in
                                (("vegetation",args.land_cover),("geology",args.geology)) if path)
                print(json.dumps({"id":request["id"],"terrain_ready":terrain is not None,
                                  "geography_ready":all(required)}),flush=True)
                continue
            result = {"id": request["id"]}
            result["land_context"] = {}
            try:
                result["land_context"]["trees"] = forest.lookup(request["lat"], request["lon"]) if forest else {"status": "unavailable" if args.forest_index else "not_connected"}
            except (ValueError, RuntimeError, OSError, sqlite3.Error):
                logging.getLogger(__name__).exception("Prediction map geography: forest query failed")
                result["land_context"]["trees"] = {"status": "unavailable"}
            for kind, path in (("vegetation", args.land_cover), ("geology", args.geology)):
                try:
                    reader = land_readers.get(kind)
                    result["land_context"][kind] = reader.lookup(request["lat"], request["lon"]) if reader else {"status": "unavailable" if path else "not_connected"}
                except (ValueError, RuntimeError, OSError, sqlite3.Error):
                    logging.getLogger(__name__).exception("Prediction map geography: %s query failed", kind)
                    result["land_context"][kind] = {"status": "unavailable"}
            for key, reader in (("location", municipality), ("terrain", terrain)):
                try:
                    configured = args.municipalities if key == "location" else args.terrain_index
                    result[key] = reader.lookup(request["lat"], request["lon"]) if reader else {"status": "unavailable" if configured else "not_connected"}
                except (ValueError, RuntimeError, OSError, sqlite3.Error):
                    logging.getLogger(__name__).exception("Prediction map geography: %s query failed", key)
                    result[key] = {"status": "unavailable"}
            if args.openlandmap_ph:
                try:
                    result['terrain']['ph_openlandmap'] = openlandmap.lookup(request['lat'],request['lon']) if openlandmap else {'status':'unavailable'}
                except (ValueError,RuntimeError,OSError):
                    logging.getLogger(__name__).exception("Prediction map geography: OpenLandMap query failed")
                    result['terrain']['ph_openlandmap'] = {'status':'unavailable'}
            if args.profiles:
                result["ecology"] = {"status":"unavailable", "policy":POLICY, "species":[]}
                if ecology:
                    try:
                        result["ecology"] = ecology.evaluate(result, request["start_date"], request.get("horizon_days",7))
                    except (ValueError, KeyError, TypeError):
                        logging.getLogger(__name__).exception("Prediction map geography: ecology evaluation failed")
            model_inputs = (request.get('model_inputs') is True
                            and prediction_candidates(result.get('ecology', {}), request.get('species_ids')))
            if terrain and (model_inputs or request.get('water_history') is True):
                try:
                    soil = terrain.soil_water_context(request['lat'],request['lon'])
                    if model_inputs:
                        result['model_soil_water'] = soil
                    if request.get('water_history') is True:
                        try:
                            result['water_capacity_mm'] = available_water_capacity_mm(soil, profile_depth_cm=30)['capacity_mm']
                        except (TypeError, ValueError, KeyError):
                            result['water_capacity_mm'] = None
                except (ValueError,RuntimeError,OSError,sqlite3.Error):
                    logging.getLogger(__name__).exception("Prediction map geography: soil water query failed")
                    result['model_soil_water'] = None
            print(json.dumps(result, ensure_ascii=False, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
