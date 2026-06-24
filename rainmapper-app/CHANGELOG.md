# Changelog

## 0.2.120

- Add a separate experimental MapLibre heatmap viewer route for validating metric overlays without changing the protected viewer.
- Add MapLibre layer metric controls for rain, temperature, humidity and wind, including a quick metric panel and metric legend.
- Add an experimental heatmap toggle and opacity slider using all valid stations for the selected period.

## 0.2.119

- Align MapLibre station history temperature, humidity and wind values with fixed internal subcolumns.
- Add AEMET OpenData request diagnostics, including timestamps and index/data URL context for 429 errors.
- Track AEMET 429 counts for the last 24 hours and consecutive runs, showing non-zero counters in the WebUI.
- Add WebUI `Update only` actions for each source without changing persistent Home Assistant options.

## 0.2.118

- Restore the daily age column in MapLibre station history rows.
- Keep the station history table header visible while scrolling popup history.

## 0.2.117

- Keep one compact row per day in the MapLibre station history table.
- Use short column labels for daily rain, temperature, humidity and wind.
- Show wind direction as cardinal labels instead of degrees in MapLibre popups.

## 0.2.116

- Restore fast Tomap period aggregation while keeping wind and humidity fields in GeoJSON.
- Replace the MapLibre daily weather table with a compact wrapping history list for desktop and mobile popups.
- Hide empty wind lines in station popups.

## 0.2.115

- Show period temperature, humidity, wind speed, wind direction and gusts in MapLibre station popups when available.
- Include humidity and wind fields in the recent daily history shown in MapLibre station popups.
- Propagate optional wind and humidity fields through Tomap and GeoJSON without breaking older incremental CSVs.

## 0.2.114

- Add normalized daily wind fields for Meteocat/XEMA, Meteoclimatic, Weather Underground and AEMET where each source provides them.
- Preserve manual AEMET daily backfills when runtime hourly updates rebuild `Aemet_incremental.csv`.
- Store Meteoclimatic raw observations in `Meteoclimatic_observations_incremental.csv` and derive daily wind aggregates from them.

## 0.2.113

- Show MapLibre source status badges on two lines so long states such as `DISABLED` keep the station count visible.
- Adjust the mobile MapLibre help panel to avoid overlapping the rain legend and period selector.

## 0.2.112

- Add a final `?` help button to the protected MapLibre toolbar with ES/EN/CA help text for map usage, filters, controls, terrain and data notes.
- Document current Home Assistant data sources, configuration options and the standard MapLibre help update procedure.

## 0.2.111

- Align Meteoclimatic and Weather Underground MapLibre attribution wording with Rainmapper-elaborated data.

## 0.2.110

- Clarify MapLibre source attribution wording for AEMET and Meteocat as Rainmapper-elaborated data.

## 0.2.109

- Include AEMET in the standard Home Assistant Tomap/GeoJSON generation used by the protected MapLibre viewer.
- Disable the separate experimental AEMET MapLibre route while keeping the publisher code as a temporary rollback hook.

## 0.2.108

- Add an explicit MapLibre Settings action to save the current map view as the device default without autosaving map movement.
- Fix AEMET daily incremental aggregation when persisted hourly history and new hourly rows use different `local_date` types.
- Add per-source station counts to `source_status.json`, show them in MapLibre Settings, and keep both row and station counts in the Home Assistant WebUI.

## 0.2.107

- Hide the internal `AEMET:` station-code prefix in MapLibre station popups.
- Polish MapLibre source attribution wording for AEMET and Meteoclimatic.

## 0.2.106

- Add visible MapLibre station attributions for Meteocat, Meteoclimatic and Wunderground.
- Replace the generic station `Source` popup row with source-specific legal attribution text.

## 0.2.105

- Show all valid MapLibre stations regardless of the previous regional bounds, and report invalid-coordinate features in the header.
- Add AEMET hourly temperature and humidity capture, with daily max/min aggregation for Tomap and GeoJSON.

## 0.2.104

- Fix experimental AEMET MapLibre publishing when Tomap merges AEMET with existing sources that have different optional weather column types.

## 0.2.103

- Pass the `create_aemet` Home Assistant option through WebUI-triggered `update` and `all` jobs.

## 0.2.102

- Add AEMET OpenData as an optional data source, disabled by default, with hourly history and daily incremental CSV generation.
- Add an experimental MapLibre AEMET viewer route while keeping the protected standard viewer on existing sources.
- Share Google Maps station reverse geocoding across sources and AEMET station catalog enrichment.
- Show AEMET attribution in MapLibre station popups and credits.

## 0.2.101

- Improve the Home Assistant `Users` page with a sticky toolbar, manual refresh and free-text filtering across users and registered devices.
- Keep scroll position and the current search while refreshing user/device data.

## 0.2.100

- Compact the MapLibre mobile floating controls to reduce screen height usage.
- Move the mobile controls closer to the right edge and the rain legend closer to the left edge.

## 0.2.99

- Add ES/EN/CA language selection to the protected MapLibre viewer Settings panel.
- Store the selected MapLibre language per device in `devices.json`.
- Move MapLibre UI translations to `translations.json` and publish it with the viewer assets.

## 0.2.98

- Add a quick MapLibre layer button between the `2D`/`3D` control and north compass.
- Keep quick map and bottom-period changes non-persistent while Settings controls continue to update device preferences.

## 0.2.97

- Store protected MapLibre settings per registered device in `devices.json`.
- Add a Settings period selector and persist device preferences only when closing Settings after a panel change.
- Keep bottom period navigation and the quick `2D`/`3D` button as non-persistent map actions.

## 0.2.96

- Show the nearest rainy station in the MapLibre terrain long-press popup.
- Include the selected-period rain total for that station and a clear no-rain fallback.

## 0.2.95

- Lower the MapLibre station hover popup threshold to zoom 7.
- Add nearest-station context to the MapLibre terrain long-press popup.
- Keep the temporary header zoom indicator as an operational aid while validating the hover threshold.

## 0.2.94

- Re-add the temporary MapLibre header zoom indicator for the live demo.

## 0.2.93

- Remove the temporary MapLibre header zoom indicator after demo preparation.

## 0.2.92

- Add a temporary MapLibre header zoom indicator to tune the station hover zoom threshold during the live demo.

## 0.2.91

- Compact the MapLibre header on mobile by removing visible `Generated`/`User` labels and showing `username (role)`.

## 0.2.90

- Show the authenticated MapLibre user and role in the viewer header under the generated timestamp.

## 0.2.89

- Add a Home Assistant `Users` action to delete a user and all registered devices associated with that user.

## 0.2.88

- Remove the temporary MapLibre header zoom indicator after demo validation.

## 0.2.87

- Add a temporary MapLibre header zoom indicator below the generated timestamp to help tune the station hover zoom threshold during demos.

## 0.2.86

- Clarify password management in the Home Assistant `Users` page: stored passwords cannot be viewed, but newly typed passwords can be shown while editing.
- Split password admin actions: `Set password` stores an administrator-defined password and clears the user's devices, while `Reset password` forces the user to choose a different password on next sign-in.
- Add the protected MapLibre password-change flow for users marked with `must_change_password`.

## 0.2.85

- Stop auto-refreshing the Home Assistant `Users` and `App settings` pages so forms can be edited safely.

## 0.2.84

- Remove the old authentication format; `users.json` is now the only supported MapLibre user store.
- Add the Home Assistant WebUI `Users` page to create users, edit role/status/device limits, reset passwords, and delete registered devices.

## 0.2.83

- Use `users.json` as the primary MapLibre auth user store with `username`, `name`, `email`, `password`, `role`, `enabled`, and `max_devices`.
- Add role defaults for `free`, `basic`, `pro`, and unlimited `admin` users, with per-user `max_devices` overrides.
- Seed `/share/rainmapper/users.json` from `users.example.json` when no user file exists.

## 0.2.82

- Add lightweight login protection for the MapLibre viewer and GeoJSON data.
- Create the initial user and device files in `/share/rainmapper` when missing.
- Publish port `8099/tcp` so Cloudflared can reach the protected Rainmapper web server directly.
- Keep `/local/rainmapper-maplibre/index.html` as a temporary public fallback while validating the protected Cloudflared route.

## 0.2.81

- Modernize the MapLibre viewer UI with a light header, floating map controls, a compact period selector, and a dynamic vertical rain legend.
- Move MapLibre credits behind an info control while preserving attribution links.
- Improve MapLibre settings, popups, rain-history highlighting, and summary text layout on mobile.
- Keep an open station popup refreshed when changing the rain period if the station remains visible after filters.

## 0.2.80

- Remove root Python compatibility wrappers `Rainmapper.py` and `Rainmapper_Client.py`; Docker local, Home Assistant, and the webUI now execute `rainmapper_core` modules directly.
- Keep shell wrappers as the supported user-facing local commands.

## 0.2.79

- Move classic Bokeh map generation into `rainmapper_core/bokeh_maps.py`.
- Move Leaflet and MapLibre viewer sources into `rainmapper_core/viewers`.
- Publish Home Assistant viewer assets directly from the shared core viewer paths, removing separate viewer copies from `rainmapper-app/app`.
- Keep root-level viewer paths as local compatibility links for existing local test URLs.

## 0.2.78

- Move source-specific helper libraries into `rainmapper_core/sources`.
- Keep Home Assistant packaged copies aligned with the shared core source layout.
- Document the next core/app/local repository structure phase before starting it.

## 0.2.77

- Add a compact MapLibre `2D`/`3D` terrain toggle below the generated timestamp.
- Keep the MapLibre terrain toggle, Settings checkbox, and `t` keyboard shortcut synchronized.
- Add a pointer tail to long-press terrain elevation popups.
- Restore desktop station hover popups after closing a terrain elevation popup.

## 0.2.76

- Add real per-source duration metrics to `source_status.json`.
- Show source durations in the Home Assistant webUI.
- Add Meteocat step timings for metadata, conditions, rain, merge, and save phases.
- Keep process timing metrics out of MapLibre; the map viewer continues to show only source status badges.

## 0.2.75

- Stop running inline Tomap generation inside `Rainmapper.py`; `tomap_builder.py` is now the active Tomap rebuild path for `MODE=maps` and `MODE=all`.
- Keep legacy Tomap helper functions marked for review before final cleanup.
- Validate the new local `MODE=all` flow after the inline Tomap removal.
- Add internal documentation to maintenance scripts.

## 0.2.74

- Add `tomap_builder.py` to rebuild Tomap CSV files from existing incremental history without downloading new weather data.
- Make `Generate maps` / `MODE=maps` rebuild Tomap before generating Bokeh and GeoJSON outputs.
- Add local validation helpers: `local_update.sh` and `scripts/compare-tomap-builder.sh`.
- Add unit coverage for Tomap rebuild output.

## 0.2.73

- Add global update exit-code semantics: `0` complete success, `2` degraded success, and `1` total/non-recoverable failure.
- Continue `Run all` through map generation when the update step finishes degraded.
- Keep source status writes from aborting local Docker runs if the filesystem temporarily refuses `source_status.json`.
- Upgrade `pip` during Docker builds before installing Python dependencies to reduce transient package download/hash failures.
- Mark MapLibre 3D terrain as a stable feature after local, Home Assistant, and iPhone validation.

## 0.2.72

- Keep MapLibre desktop hover popups working after opening and closing a station popup by click.

## 0.2.71

- Add per-source update status for Meteoclimatic, Meteocat, and Wunderground in the Home Assistant webUI.
- Show per-source status badges in the MapLibre Settings source filter when `source_status.json` is available.
- Show MapLibre station popups on desktop hover from zoom level 9 without changing mobile tap behavior.
- Continue an update with previous incremental data when a source fails completely and mark that source as `STALE`.
- Publish `source_status.json` with Leaflet and MapLibre data for future viewer-side source status.

## 0.2.70

- Add `Days ago` to station popup rain history in Leaflet and MapLibre.
- Highlight rainy history rows and show the latest rain date/amount in the station popup summary.

## 0.2.69

- Remove optional Jawg Maps layers and `jawgmaps_api_key` configuration from Leaflet, MapLibre, Docker local, and the Home Assistant app.
- Keep MapLibre base maps focused on Satellite+, Hybrid, Topographic, and Liberty to avoid API-key/licensing complexity.

## 0.2.68

- Add configurable Meteocat/Socrata request timeout and retry attempts to avoid failing a full run on transient read timeouts.

## 0.2.67

- Add `last_rains_history` to Home Assistant options to configure how many recent rain records Rainmapper generates for station popups.
- Make Leaflet and MapLibre station popups detect available recent-rain columns dynamically; MapLibre can limit displayed rows from Settings.

## 0.2.66

- Add a MapLibre station popup pointer while keeping the existing square popup styling.

## 0.2.65

- Refresh Leaflet and MapLibre viewer asset cache busters to match the Home Assistant app version.
- Add a smoke-test check to catch stale viewer asset version query strings before publishing.
- Use MapLibre map events and `contextmenu` as a more robust trigger for long-press terrain elevation popups.

## 0.2.63

- Add MapLibre long-press terrain elevation popups using direct Terrarium DEM tile decoding.
- Avoid `queryTerrainElevation` for displayed altitude after it returned incorrect negative values in terrain tests.

## 0.2.62

- Add an experimental MapLibre 3D terrain option using external Terrarium DEM tiles.
- Move the MapLibre base map selector into Settings to reduce map overlay clutter.
- Add a MapLibre north-orientation button that resets bearing without changing zoom, pitch, filters, or selected map data.
- Add `local_maps.sh` to regenerate maps/GeoJSON locally without downloading fresh weather data.
- Clarify Spanish app documentation for `gmap_api_key`, including station metadata enrichment during updates.

## 0.2.61

- Improve Spanish Home Assistant app documentation for multiple Meteoclimatic patterns and option coverage.
- Document optional Jawg layers, Wunderground diagnostic logging, source toggles, and day range options.

## 0.2.60

- Rename the MapLibre source filter group title from `Stations` to `Source`.
- Make GitHub Actions image publishing manual-only; normal HA image publishing now uses local Buildx before the version commit is pushed.

## 0.2.59

- Classify Meteocat stations only when station codes have two characters.
- Keep unclassified station codes as `Source=Unknown` in GeoJSON and warn during conversion.
- Show `Unknown` as a selectable MapLibre station-source filter.

## 0.2.58

- Add a MapLibre settings filter to show/hide Meteocat, Meteoclimatic, and Wunderground stations.
- Add station source metadata to generated GeoJSON files using the current station-code patterns.
- Enable GitHub Actions Buildx cache for faster pre-built image publishing.

## 0.2.57

- Configure Home Assistant to use a pre-built multi-arch GHCR image instead of building the app locally.
- Add a GitHub Actions workflow to publish `amd64` and `arm64` images for the app version.

## 0.2.56

- Fix returning to the MapLibre Satellite+ base layer after switching to another layer.
- Refresh MapLibre viewer asset cache busters.

## 0.2.55

- Handle SIGTERM/SIGINT in the Home Assistant web server so app updates can stop Rainmapper cleanly, waiting for active jobs before shutdown when possible.

## 0.2.54

- Add a MapLibre viewer settings panel with a minimum rain filter slider for validating app-style filtering in the current web viewer.

## 0.2.53

- Refresh Leaflet viewer asset cache busters and ignore whitespace-only Jawg tokens so optional Jawg layers disappear when the API key is empty.

## 0.2.52

- Fix the Home Assistant WebUI status panel layout so status cards stay grouped in three explicit rows.

## 0.2.51

- Show the running app version in the Home Assistant WebUI status panel.

## 0.2.50

- Add app-version cache busters to the Home Assistant WebUI viewer links to avoid stale viewer/config loads.
- Make Satellite+ the default MapLibre base style.

## 0.2.49

- Remove the OpenFreeMap Bright style from the MapLibre layer selector.
- Keep Hybrid, Satellite+, Topographic, Liberty, and optional Jawg styles available.

## 0.2.48

- Add a MapLibre Satellite+ style with Esri World Imagery and OpenFreeMap vector orientation labels/roads.
- Keep Tracestrack out of runtime configuration because its vector maps require a paid app key.

## 0.2.47

- Add MapLibre raster base maps for Hybrid imagery and Topographic tiles.
- Keep existing MapLibre vector styles available and make the Hybrid raster map the default base layer.

## 0.2.46

- Translate visible core runtime logs to English, including Wunderground progress and summary output.
- Keep the Home Assistant WebUI progress parser compatible with the previous Spanish Wunderground progress format.

## 0.2.45

- Keep Home Assistant visible UI and metadata text in English.
- Translate older Spanish changelog entries to English.

## 0.2.44

- Show only the recommended App settings link by default and move alternate settings routes into an advanced fallback section.

## 0.2.43

- Make the App settings page more portable by showing the recommended Home Assistant settings route plus fallback routes instead of immediately redirecting to a single URL.

## 0.2.42

- Remove the legacy `/local/rainmapper-mobile` publication path.
- Keep publishing Leaflet at `/local/rainmapper-leaflet` and MapLibre at `/local/rainmapper-maplibre`.

## 0.2.41

- Document the Bokeh, Leaflet, and MapLibre map viewers and their public URLs.
- Align Docker image labels and runtime version banner with the Home Assistant app version.

## 0.2.40

- Add `ignore_stations_tomap.txt` to exclude selected stations from generated GeoJSON maps without deleting historical data.
- Make the MapLibre station popup match the Leaflet popup behavior more closely on mobile.

## 0.2.39

- Remove the MapLibre navigation bounds so edge stations can be inspected more comfortably.

## 0.2.38

- Reload the current MapLibre period data after base style changes so station markers remain visible.

## 0.2.37

- Restore MapLibre station markers after switching base map styles.

## 0.2.36

- Add a separate experimental MapLibre viewer with OpenFreeMap Liberty and Bright styles.
- Add optional Jawg Streets and Terrain vector styles to the MapLibre viewer when a Jawg access token is configured.
- Rename Leaflet viewer source folders while keeping the legacy rainmapper-mobile URL temporarily available.

## 0.2.35

- Restore Leaflet raster tile settings after retina tiles made labels too small.

## 0.2.34

- Improve raster tile sharpness in the Leaflet viewer on high-density screens.
- Increase Jawg layer zoom support for Street and Terrain maps.

## 0.2.33

- Add optional Jawg Maps Street and Terrain layers to the Leaflet viewer when a Jawg access token is configured.

## 0.2.32

- Preserve the Leaflet map center and zoom when switching rain periods after the initial load.

## 0.2.31

- Align the Leaflet viewer header as three columns: title, generation time, and period selector.

## 0.2.30

- Save Wunderground station timing metrics to `Data/metricas_wunderground.csv`.
- Show the selected map generation time in the Leaflet viewer header.

## 0.2.29

- Add Wunderground station timing metrics: average, median, fastest, slowest, and top slow stations.

## 0.2.28

- Disable Leaflet popup auto-panning so station popups do not move the map.

## 0.2.27

- Move the rain period selector into the header row and compact the map layer selector.

## 0.2.26

- Move the rainfall legend to the lower left and make the layer selector more compact.

## 0.2.25

- Keep rainfall legend compact while restoring range labels and right alignment.

## 0.2.24

- Make the Leaflet rainfall legend more compact on mobile screens.

## 0.2.23

- Add a rainfall color legend to the Leaflet mobile viewer.

## 0.2.22

- Allow multiple Meteoclimatic RSS patterns in `meteoclimatic_pattern`.
- Accept comma, semicolon, or ` - ` separated patterns, with a short delay between feed requests.

## 0.2.21

- Keep only Topographic and Hybrid map layers in the Leaflet viewer.
- Use Hybrid as the default Leaflet base map.

## 0.2.20

- Add cache-busting query strings to Leaflet viewer assets so browsers load updated map layers.

## 0.2.19

- Add Leaflet base maps without API keys: Street, Minimal, Topographic, Satellite, and Hybrid.

## 0.2.18

- Point the Leaflet viewer button to `/local/rainmapper-mobile/index.html` for reliable Home Assistant static serving.

## 0.2.17

- Add GeoJSON export for the seven generated Tomap periods: 1, 7, 14, 21, 30, 60, and 90 days.
- Publish a Leaflet mobile viewer to `/local/rainmapper-mobile` after map generation.
- Add WebUI viewer buttons for the Leaflet viewer and existing Bokeh maps.

## 0.2.16

- Speed up map filtering by using vectorized pandas date masks.
- Allow map generation with short rebuilt histories by filling missing last-rain columns.

## 0.2.15

- Build the WebUI app settings link from the Home Assistant Supervisor self-info API when available.

## 0.2.14

- Point the WebUI app settings link to the Home Assistant app configuration page.

## 0.2.13

- Do not show disabled Wunderground error stations as current in the WebUI cards.

## 0.2.12

- Make WebUI action buttons work reliably behind Home Assistant ingress.
- Add an intermediate settings page for opening Home Assistant app settings.
- Use the Home Assistant Configuration tab route for the app settings link.

## 0.2.11

- Add a WebUI link to the Home Assistant app settings page.
- Return to the WebUI after enabling or disabling Wunderground station groups.

## 0.2.10

- Move Wunderground error cards to a separate two-column row in the WebUI.

## 0.2.9

- Show municipality, province, and altitude for Wunderground error stations.
- Refresh the WebUI every 5 seconds while monitoring runs.

## 0.2.8

- Keep disabled Wunderground station groups tagged in stations.txt so they can be re-enabled later.

## 0.2.7

- Add WebUI controls to disable or enable Wunderground stations by error group.

## 0.2.6

- Add WebUI current step and Wunderground progress cards.

## 0.2.5

- Add configurable detailed Wunderground logging.
- Always show a Wunderground summary with failed stations.
- Show Wunderground progress every 10% of processed stations.

## 0.2.4

- Allow multiple daily schedule times in `schedule_time`.
- Add optional `schedule_days` filtering for scheduled runs.

## 0.2.3

- Publish generated maps automatically to Home Assistant `/local/Plots`.
- Publish public map filenames as `rain_01d.html`, `rain_07d.html`, `rain_14d.html`, `rain_21d.html`, `rain_30d.html`, `rain_60d.html`, and `rain_90d.html`.

## 0.2.2

- Improve startup banner coloring in the Home Assistant log viewer.
- Keep verbose Rainmapper output in the webUI `last_run.log` without flooding the Home Assistant system log.
- Stop logging every webUI auto-refresh request to the Home Assistant system log.
- Keep the webUI log panel scrollable instead of making the whole page grow indefinitely.

## 0.2.1

- Keep `last_run.log` limited to the latest run instead of appending forever.
- Show the full latest log in the webUI.
- Add run duration in `HH:MM:SS`.
- Auto-refresh the webUI every 15 seconds.
- Show generation date/time for each generated map.
- Add a startup banner with app, runtime, schedule, and data path information.

## 0.2.0

- Make the Home Assistant app work as a long-running sidebar service.
- Add a Rainmapper landing page with run buttons, map links, status, and recent logs.
- Add internal scheduling options for `update`, `maps`, or `all`.

## 0.1.5

- Enable map wheel/pinch zoom by default in generated Bokeh maps.
- Enable map pan by default so mobile users can interact without the toolbar.

## 0.1.4

- Add Home Assistant ingress support for the sidebar.
- Add `serve` mode to browse generated HTML maps from `/share/rainmapper/Plots`.

## 0.1.3

- Align Docker image labels with the Home Assistant app version.
- Avoid stale `0.1.0` version labels during local Home Assistant builds.

## 0.1.2

- Add changelog for Home Assistant update dialog.
- Keep app metadata aligned with Home Assistant app updates.

## 0.1.1

- Improve Home Assistant app documentation.
- Add repository URL to app metadata.

## 0.1.0

- Initial Home Assistant app package.
- Add Docker-based Rainmapper runner.
- Persist data under `/share/rainmapper`.
- Support `help`, `update`, `maps`, and `all` modes.
