from __future__ import annotations

import copy
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from rainmapper_core import mushroom_soilgrids as soilgrids


def create_raster(
    path: Path,
    *,
    value: int,
    bbox: tuple[int, int, int, int] = (
        soilgrids.GRID_MIN_X_M,
        soilgrids.GRID_MIN_Y_M,
        soilgrids.GRID_MIN_X_M + 128000,
        soilgrids.GRID_MIN_Y_M + 128000,
    ),
    size: tuple[int, int] = (512, 512),
    crs: bool,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    min_x, min_y, max_x, max_y = bbox
    command = [
        "gdal_create",
        "-q",
        "-of",
        "GTiff",
        "-ot",
        "Int16",
        "-outsize",
        str(size[0]),
        str(size[1]),
        "-burn",
        str(value),
        "-a_ullr",
        str(min_x),
        str(max_y),
        str(max_x),
        str(min_y),
        "-co",
        "TILED=YES",
        "-co",
        "COMPRESS=DEFLATE",
    ]
    if crs:
        command.extend(["-a_srs", soilgrids.NATIVE_CRS_PROJ4])
    command.append(str(path))
    subprocess.run(command, check=True, capture_output=True, text=True)


class MushroomSoilGridsTests(TestCase):
    def test_contract_declares_all_54_water_retention_coverages(self) -> None:
        coverages = soilgrids.required_coverage_ids()

        self.assertEqual(len(coverages), 54)
        self.assertEqual(len(set(coverages)), 54)
        self.assertIn("wv0010_0-5cm_Q0.05", coverages)
        self.assertIn("wv0033_30-60cm_Q0.5", coverages)
        self.assertIn("wv1500_100-200cm_Q0.95", coverages)

    def test_tile_contract_is_stable_and_wcs_url_uses_native_crs(self) -> None:
        self.assertEqual(
            soilgrids.tile_bbox("x5_y35"),
            (-19309750, -1667500, -19181750, -1539500),
        )
        url = soilgrids.wcs_get_coverage_url(
            "wv0033_0-5cm_Q0.5", "x5_y35"
        )
        self.assertIn("COVERAGEID=wv0033_0-5cm_Q0.5", url)
        self.assertIn("SUBSET=X%28-19309750%2C-19181750%29", url)
        self.assertIn("EPSG%2F0%2F152160", url)

    def test_manifest_round_trip_is_atomic_and_rejects_incomplete_contract(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = soilgrids.load_manifest(root, create=True)
            loaded = soilgrids.load_manifest(root)

            self.assertEqual(payload, loaded)
            self.assertEqual(len(loaded["coverages"]), 54)
            incomplete = copy.deepcopy(loaded)
            incomplete["coverages"].pop(next(iter(incomplete["coverages"])))
            with self.assertRaisesRegex(
                soilgrids.SoilGridsManifestError, "coverage set"
            ):
                soilgrids.save_manifest(root, incomplete)

    def test_capabilities_snapshot_requires_every_declared_coverage(self) -> None:
        def fetcher(url: str, _timeout: int) -> bytes:
            property_id = next(
                value for value in soilgrids.PROPERTIES if f"/{value}.map" in url
            )
            identifiers = "".join(
                f"<wcs:CoverageId>{coverage}</wcs:CoverageId>"
                for coverage in soilgrids.required_coverage_ids()
                if coverage.startswith(f"{property_id}_")
            )
            return (
                '<wcs:Capabilities xmlns:wcs="http://www.opengis.net/wcs/2.0">'
                f"<wcs:Contents>{identifiers}</wcs:Contents>"
                "</wcs:Capabilities>"
            ).encode()

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            hashes = soilgrids.record_capabilities(root, fetcher=fetcher)
            manifest = soilgrids.load_manifest(root)

            self.assertEqual(set(hashes), set(soilgrids.PROPERTIES))
            self.assertEqual(manifest["source"]["capabilities_sha256"], hashes)
            self.assertTrue(
                (
                    root
                    / "reports"
                    / soilgrids.SOURCE_VERSION
                    / "capabilities"
                    / "wv0033.xml"
                ).is_file()
            )

    def test_exact_polygon_rectangle_intersection_supports_holes(self) -> None:
        polygon = [
            [
                [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)],
                [(4, 4), (6, 4), (6, 6), (4, 6), (4, 4)],
            ]
        ]

        self.assertEqual(soilgrids.geometry_area(polygon), 96.0)
        self.assertEqual(
            soilgrids.geometry_intersection_area(polygon, (0, 0, 5, 10)),
            48.0,
        )

    def test_land_mask_excludes_only_valid_all_zero_tiles(self) -> None:
        manifest = soilgrids.empty_manifest()
        rows = manifest["coverages"][soilgrids.LAND_MASK_COVERAGE_ID]["tiles"]
        rows["x0_y0"] = {"status": "valid", "value_max": 0.0}
        rows["x1_y0"] = {"status": "valid", "value_max": 325.0}

        land, empty = soilgrids.land_tile_ids_from_manifest(
            manifest, ["x1_y0", "x0_y0"]
        )

        self.assertEqual(land, ["x1_y0"])
        self.assertEqual(empty, ["x0_y0"])

    def test_ensure_tile_validates_promotes_and_then_reuses(self) -> None:
        calls: list[str] = []

        def fetcher(url: str, destination: Path, _timeout: int) -> dict:
            calls.append(url)
            create_raster(destination, value=300, crs=False)
            return {
                "http_status": 200,
                "content_type": "image/tiff",
                "size_bytes": destination.stat().st_size,
            }

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            coverage = "wv0033_0-5cm_Q0.5"
            first = soilgrids.ensure_tile(
                root, coverage, "x0_y0", fetcher=fetcher
            )
            second = soilgrids.ensure_tile(
                root, coverage, "x0_y0", fetcher=fetcher
            )
            manifest = soilgrids.load_manifest(root)
            tile = manifest["coverages"][coverage]["tiles"]["x0_y0"]

            self.assertEqual(first["status"], "downloaded")
            self.assertEqual(second["status"], "reused")
            self.assertEqual(len(calls), 1)
            self.assertTrue((root / tile["raw_path"]).is_file())
            self.assertTrue((root / tile["normalized_path"]).is_file())
            soilgrids.validate_raster(
                root / tile["normalized_path"],
                soilgrids.tile_bbox("x0_y0"),
                require_crs=True,
            )

    def test_failed_download_does_not_register_a_partial_tile(self) -> None:
        def failing_fetcher(_url: str, destination: Path, _timeout: int) -> dict:
            destination.write_text("WCS XML error", encoding="utf-8")
            return {
                "http_status": 200,
                "content_type": "application/xml",
                "size_bytes": destination.stat().st_size,
            }

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(soilgrids.SoilGridsRasterError):
                soilgrids.ensure_tile(
                    root,
                    "wv0033_0-5cm_Q0.5",
                    "x0_y0",
                    fetcher=failing_fetcher,
                )

            manifest = soilgrids.load_manifest(root)
            self.assertEqual(
                manifest["coverages"]["wv0033_0-5cm_Q0.5"]["tiles"], {}
            )
            self.assertEqual(list((root / "staging").iterdir()), [])

    def test_bulk_download_fetches_once_splits_tiles_and_reuses_them(self) -> None:
        calls: list[str] = []
        first_bbox = soilgrids.tile_bbox("x0_y0")
        second_bbox = soilgrids.tile_bbox("x1_y0")
        bulk_bbox = (
            first_bbox[0],
            first_bbox[1],
            second_bbox[2],
            second_bbox[3],
        )

        def fetcher(url: str, destination: Path, _timeout: int) -> dict:
            calls.append(url)
            create_raster(
                destination,
                value=275,
                bbox=bulk_bbox,
                size=(1024, 512),
                crs=False,
            )
            return {"http_status": 200, "content_type": "image/tiff"}

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            coverage = "wv0033_0-5cm_Q0.5"
            first = soilgrids.ensure_tiles_bulk(
                root, coverage, ["x0_y0", "x1_y0"], fetcher=fetcher
            )
            second = soilgrids.ensure_tiles_bulk(
                root, coverage, ["x0_y0", "x1_y0"], fetcher=fetcher
            )
            tiles = soilgrids.load_manifest(root)["coverages"][coverage]["tiles"]

            self.assertEqual(first["downloaded"], 2)
            self.assertEqual(second["reused"], 2)
            self.assertEqual(len(calls), 1)
            self.assertEqual(tiles["x0_y0"]["raw_path"], tiles["x1_y0"]["raw_path"])
            self.assertNotEqual(
                tiles["x0_y0"]["normalized_path"],
                tiles["x1_y0"]["normalized_path"],
            )
            self.assertIn(tiles["x0_y0"]["raw_sha256"][:16], tiles["x0_y0"]["raw_path"])

    def test_aggregate_geometry_reads_all_depths_quantiles_and_properties(self) -> None:
        geometry = {
            "type": "Polygon",
            "coordinates": [
                [
                    [0.001, 0.001],
                    [0.003, 0.001],
                    [0.003, 0.003],
                    [0.001, 0.003],
                    [0.001, 0.001],
                ]
            ],
        }
        values = {"wv0010": 400, "wv0033": 300, "wv1500": 100}
        aggregate_tile = "x155_y48"
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = soilgrids.empty_manifest()
            property_paths: dict[str, Path] = {}
            for property_id, value in values.items():
                path = root / "fixtures" / f"{property_id}.tif"
                create_raster(
                    path,
                    value=value,
                    bbox=soilgrids.tile_bbox(aggregate_tile),
                    crs=True,
                )
                property_paths[property_id] = path
            for coverage in soilgrids.required_coverage_ids():
                property_id = coverage.split("_", 1)[0]
                path = property_paths[property_id]
                relative = path.relative_to(root).as_posix()
                sha256 = soilgrids.file_sha256(path)
                manifest["coverages"][coverage]["tiles"][aggregate_tile] = {
                    "bbox_native": list(soilgrids.tile_bbox(aggregate_tile)),
                    "raw_path": relative,
                    "normalized_path": relative,
                    "raw_sha256": sha256,
                    "normalized_sha256": sha256,
                    "width": 512,
                    "height": 512,
                    "status": "valid",
                }
            soilgrids.save_manifest(root, manifest)

            context = soilgrids.aggregate_geometry(root, geometry)

            self.assertEqual(context["status"], "complete")
            self.assertEqual(context["coverage_fraction"], 1.0)
            self.assertEqual(len(context["depths"]), 6)
            self.assertEqual(len(context["source"]["asset_hashes"]), 54)
            for depth in context["depths"]:
                self.assertGreater(depth["valid_pixel_count"], 0)
                self.assertEqual(
                    depth["area_weighted"]["Q0.50"],
                    {
                        "wv0010_mm_per_m": 400.0,
                        "wv0033_mm_per_m": 300.0,
                        "wv1500_mm_per_m": 100.0,
                    },
                )

    def test_apply_context_preserves_dem_context(self) -> None:
        micro_area = {"derived_context": {"gis_dem": {"altitude_mean_m": 700}}}
        context = soilgrids.pending_context(
            {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [0, 1], [0, 0]]]},
            tile_ids=["x0_y0"],
            reasons=["missing_cache_assets"],
        )

        soilgrids.apply_micro_area_context(micro_area, context)

        self.assertEqual(
            micro_area["derived_context"]["gis_dem"]["altitude_mean_m"], 700
        )
        self.assertEqual(
            micro_area["derived_context"]["soilgrids_water"]["status"],
            "pending",
        )

    def test_current_context_requires_matching_geometry_and_contracts(self) -> None:
        geometry = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [0, 1], [0, 0]]],
        }
        context = {
            "contract_id": soilgrids.CONTEXT_CONTRACT_ID,
            "geometry_hash": soilgrids.geometry_sha256(geometry),
            "status": "complete",
            "source": {
                "source_id": soilgrids.SOURCE_ID,
                "source_version": soilgrids.SOURCE_VERSION,
                "cache_contract_id": soilgrids.CACHE_CONTRACT_ID,
            },
        }

        self.assertTrue(soilgrids.context_is_current(context, geometry))
        stale = copy.deepcopy(context)
        stale["source"]["source_version"] = "old"
        self.assertFalse(soilgrids.context_is_current(stale, geometry))


if __name__ == "__main__":
    from unittest import main

    main()
