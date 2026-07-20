# Changelog

## 0.2.211

- Refresh worker activity notices together with live job state so preparation,
  queue and conflict messages disappear when the associated work finishes.
- Keep real preparation, connectivity and configuration errors visible after
  the worker queue becomes idle.

## 0.2.210

- Keep the `Workers and jobs` interface responsive by preserving interactive
  DOM nodes across heartbeat refreshes and aborting polling during navigation.
- Prepare immutable worker inputs in the background, reject concurrent bundle
  preparations and disable submitted controls immediately.
- Cache GIS/DEM hashes using private filesystem identities so unchanged
  semi-static datasets are not rehashed for every external worker job.

## 0.2.209

- Fix the `Workers and jobs` manual and automatic refresh paths under Home
  Assistant Ingress.
- Keep the Control Panel publication summary limited to the latest run instead
  of accumulating protected MapLibre publication messages across schedules.

## 0.2.208

- Add the private external-worker coordinator, pairing, multi-worker registry,
  persistent job control and the `Workers and jobs` Home Assistant interface.
- Support full, pending-only and single-species candidate rebuilds on an
  external worker while preserving the existing Home Assistant rebuild as the
  default fallback.
- Transfer immutable snapshots and versioned GIS/DEM datasets through bounded,
  authenticated routes; validate returned manifests and artifacts before any
  explicit atomic promotion.
- Separate the protected web/Ingress listener on port 8099 from the worker
  protocol on port 8100, which remains unpublished and disabled by default.
- Add independent `Enable external worker connections` and
  `Allow external rebuilds and promotion` Home Assistant options, both disabled
  by default.

## 0.2.207

- Refine and compact the observations, species, evidence, parameters and calibration workspaces, keeping their controls visible and replacing technical identifiers with localized names where appropriate.
- Use the reference catalog to classify every flush abundance as favorable or unfavorable for prediction without changing stored observations.
- Rebuild one species or the complete learned V0 model in the background from the existing interface, with cancellable progress feedback.
- Report incremental progress across GIS enrichment, weather joins, feature generation and learned-model reconstruction instead of leaving an indeterminate progress bar during the later phases.
- Improve observation browsing with clearer localized outcomes, streamlined details and stable partial updates across maintenance screens.

## 0.2.206

- Add a calendar-based observation date filter with direct month and year navigation.
- Refine the observation workspace with a larger media preview, clearer detail labels, denser rows and actions, and more usable horizontal space.
- Polish the species workspace with balanced health indicators, a two-row status grid, wider scientific/common names and a vertically compact editor that keeps bottom actions visible.
- Standardize maintenance toolbars and keep observation media confirmation dialogs open while lightweight detail navigation is active.

## 0.2.205

- Paginate observations on the server, show Area and Micro-area by name and update only the detail panel when selecting a row.
- Keep the species list loaded and replace only the selected editor, showing all common names without repeating the technical ID.
- Avoid reloading the known-sites screen when changing area or micro-area and open the map directly on the selected geometry, without the previous visual map jump.
- Keep the Control Panel five-second refresh without reloading the document or modifying the DOM when the state has not changed.

## 0.2.204

- Allow images and videos larger than 16 MB to be uploaded through Home Assistant ingress using streaming and chunked HTTP body support.
- Show real upload progress and a visible status while reading EXIF data, generating previews and converting video.
- Allow an active preview or upload to be cancelled without leaving duplicate requests in Safari.
- Fix the MapLibre quick viewer link to use `rainmap.nomentero.com`.

## 0.2.203

- Add true fullscreen mode to the observation image viewer, returning to the same modal with `Esc`.
- Add a large viewer in a separate tab with zoom, actual-size and fit-to-window controls.
- Replace the new text actions in the header with compact controls overlaid on the image.

## 0.2.202

- Allow observation MP4 videos to play in Safari through Home Assistant ingress using partial HTTP requests and `HEAD`.
- Explicitly declare the MP4 source and video thumbnail in the observation media viewer.

## 0.2.201

- Accept observation images and videos through the same single and batch import workflows.
- Normalize uploaded videos to compact MP4/H.264 at up to 480p and 30 seconds, with 100 MB per-file and 500 MB batch limits.
- Generate video thumbnails and preserve useful capture date and GPS metadata.
- Propose DEM altitude when imported media provides coordinates but no usable altitude, preserving its DEM provenance.
- Refine observation list sizing, scroll stability, editor density and multi-file EXIF import layout.

## 0.2.200

- Add persistent mushroom areas and micro-areas with polygon editing, GIS/DEM review and observation assignment workflows.
- Expand observation image management with separate image-only, EXIF-only and combined imports, plus a consistent multi-image EXIF creation form.
- Refine observation editing, detail alignment, backup retention and shared maintenance action styles across species, observations, parameters, GIS mappings, known sites and reference catalogs.

## 0.2.199

- Fix MapLibre viewer asset cache busting so Home Assistant loads the current `app.js` after add-on upgrades.
- Serve the protected MapLibre `index.html` without browser caching and inject the running app version into viewer asset URLs.

## 0.2.198

- Keep Wunderground monthly backfill windows on exact local calendar dates to avoid duplicate previous-month API calls caused by UTC conversion.
- Document the intentional difference between normal Wunderground early-month rereads and administrative monthly backfills.
- Allow local HA UI runs to inherit Google Maps and AEMET API keys from environment variables when add-on options are empty.
- Show point-specific IDW rain before temperature, humidity and wind in the MapLibre long-press popup.

## 0.2.197

- Add administrative monthly backfill windows with incremental CSV backup and visible pause status in the Home Assistant summary.
- Add a source/station backfill filter, currently applied to Wunderground, using `source::station1,station2` syntax for targeted station rebuilds.
- Force totals output off during monthly backfill windows to avoid legacy totals failures when only one source is enabled.

## 0.2.196

- Use Terrarium/Mapzen DEM per cell for MapLibre IDW altitude correction on temperature layers, with visible `IDW DEM` / `IDW sin DEM` status badges.
- Add `Zoom DEM` to IDW settings and save it per device.
- Add localized help bubbles for IDW settings.
- Show point-specific IDW values in the long-press map popup, including normal temperature, DEM-corrected temperature, humidity and wind.
- Align packaged MapLibre heatmap and IDW defaults with the validated Home Assistant configuration.

## 0.2.195

- Show AEMET as the active current step while a full run is processing AEMET data.
- Align GIS mappings and reference catalog maintenance pages with the species maintenance header layout by showing the action bar before the title.

## 0.2.194

- Use Wunderground daily JSON data as the primary source for monthly station weather, falling back to the existing HTML scraper only when the API has no data.
- Reuse cached Wunderground station metadata to avoid unnecessary HTML fetches for known stations, reducing Wunderground scrape time while preserving incremental updates.
- Show Wunderground API fallback errors in the source summary.

## 0.2.193

- Read raw Meteoclimatic observation history with explicit text dtypes to avoid pandas mixed-type warnings on altitude/location metadata.

## 0.2.192

- Refine mushroom Species and Observations layouts, including compact observation rows and a better General metadata card.
- Separate observation source type from location and altitude sources, and preserve explicit EXIF/manual origins.
- Rebuild local observation origin metadata from stored photos when EXIF matches the observation.
- Preserve the internal Observations list scroll position across row selection and observation modals.

## 0.2.191

- Add mushroom observation photo storage and EXIF preview/apply flow for observation create, edit and duplicate screens.
- Improve mushroom observation photo, map and evidence modals with scroll restoration and compact detail layouts.

## 0.2.190

- Use `publish_to_www` as the single switch for legacy public Bokeh/Google Maps and Leaflet publishing, disabled by default.

## 0.2.189

- Fix partial saves from mushroom Parameters v0 so hidden/unrendered fields are preserved instead of being overwritten with null values.

## 0.2.188

- Disable legacy Bokeh/Google Maps generation by default during `maps` and `all`, while keeping it available through `generate_bokeh_maps`.
- Hide the Bokeh quick viewer link when legacy Bokeh map generation is disabled.

## 0.2.187

- Vectorize Meteoclimatic daily history rebuild to remove the per-station/day Python loop from source updates.
- Vectorize Tomap last-rains rainfall aggregation to reduce map rebuild time on Raspberry Pi.

## 0.2.186

- Add detailed phase timing breakdowns for Meteocat, Meteoclimatic and Wunderground source updates in the Home Assistant control panel.

## 0.2.185

- Vectorize AEMET hourly-to-daily aggregation to remove the Python per-station/day loop that dominated runtime on Raspberry Pi.

## 0.2.184

- Fix threaded elapsed-time logs so parallel source workers no longer share one timer.
- Add AEMET phase timings for fetch, CSV reads, hourly merge, station catalog, daily rebuild, daily merge and writes.
- Show the AEMET timing breakdown in the Home Assistant control panel.
- Read AEMET CSV text key columns with explicit dtypes to avoid mixed-type warnings.

## 0.2.183

- Fix mushroom v0 rebuild progress polling under Home Assistant ingress.
- Filter stale pending model species against current eligible observations before showing or running the pending rebuild.

## 0.2.182

- Move Home Assistant mushroom GIS layer access to `/media/rainmapper/mushroom-GIS` so full `/share` backups do not include the 5-6 GB GIS/DEM layer bundle.
- Keep `RAINMAPPER_MUSHROOM_GIS_ROOT` as an explicit override and retain `/share/rainmapper/mushroom-GIS` as a controlled fallback if it still exists.

## 0.2.181

- Fix mushroom evidence counts so field observations are matched against profile items consistently across hosts, forests, soils, habitat and orientations.
- Rename evidence tabs away from GIS-only wording and improve selected-observation contrast and modal navigation history in mushroom maintenance.
- Refresh packaged mushroom defaults from the curated local data and support Home Assistant GIS layers under `/share/rainmapper/mushroom-GIS`.
- Add more detailed `run_all` timing instrumentation for source updates, map generation and publishing phases.

## 0.2.180

- Keep mushroom species saves on the current internal tab after saving or validation errors.
- Improve mushroom observation filters with editable date fields and automatic date-picker submission.
- Move scoring weights into their own Parameters section and rebalance the Parameters layout.
- Replace phenology season-pattern and topography aspect textareas with localized selectable catalog chips.
- Add localized tooltips and aligned headers for the species-list confidence, calibration-priority and review-status chips, with internal scrolling for long species lists.

## 0.2.179

- Refine the mushroom Species editor `Fenología y Topografía` tab with separate phenology/topography sections and denser desktop-first layouts.
- Replace editable month textareas with toggleable month chips while preserving list-based saves.
- Align primary and secondary month chip styling in the editor and General summary.
- Add the missing `snowmelt_bonus` label as `Snowmelt bonus` / `Bonus deshielo` / `Bonus desglaç`.

## 0.2.178

- Translate the Species tab weather-model and scoring field labels from `mushroom_labels.json` instead of showing raw JSON keys.
- Translate controlled species values such as confidence, calibration status, review status and source quality through `mushroom_labels.json`.
- Render General tab season patterns, trophic mode, aspects and confidence summaries with localized catalog/value labels.
- Keep month chips at a stable width so secondary-month labels do not resize the phenology layout.

## 0.2.177

- Expand `mushroom-data/mushroom_labels.json` so the mushroom maintenance domain uses centralized English, Spanish and Catalan UI labels across profiles, parameters, calibration, observations and reference catalogs.
- Wire the Home Assistant `ui_language` option to the mushroom maintenance screens through `RAINMAPPER_MUSHROOM_UI_LANGUAGE`, with `en`, `es` and `ca` supported after add-on restart.
- Count observation references in the reference catalog hub so observation-backed catalog entries are not reported as unused.

## 0.2.176

- Move reference catalog group names to `mushroom-data/mushroom_labels.json` with `catalog_group.*` keys for English, Spanish and Catalan.
- Use those labels in the `/mushrooms/catalogs` group cards and new-entry group selector so observation catalog groups no longer show long raw IDs as their visible title.
- Show an explicit `missing label: catalog_group.<group>` marker when a group label is absent instead of silently falling back to raw IDs.

## 0.2.175

- Rename the mushroom field label dictionary to `mushroom-data/mushroom_labels.json` for use beyond `Parameters`.
- Add English and Spanish observation schema documentation under `docs/mushrooms/`.
- Add observation reference catalog groups for abundance, validation, calibration use, sources and exclusion reasons.
- Add the first editable `mushroom_observations.json` store with validator coverage and Home Assistant seeding.
- Replace the observations placeholder with a real maintenance screen: metrics, filter bar, table, detail panel and new-observation form.
- Add `ui_language` to Home Assistant add-on options for future EN/ES/CA maintenance rendering.

## 0.2.174

- Compact the mushroom species `Parameters` screen toward the visual reference layout.
- Add human parameter labels with English, Spanish and Catalan entries.
- Separate host affinities into primary, secondary and other groups in the `Parameters` habitat summary.
- Add icons and denser controls for climate, habitat, topography, phenology and scoring blocks.

## 0.2.173

- Add top-level mushroom species `Parameters`, `Calibration` and `Observations` sections.
- Let `Parameters` save climate, phenology, topography and scoring fields with a partial update that preserves identity and catalog-backed affinities.
- Let `Calibration` save confidence/review fields while keeping observation coverage as a future dataset.
- Add an `Observations` workspace placeholder that does not store observations inside `mushroom_profiles.json`.

## 0.2.172

- Fix the species Summary weather card so it reads the documented `weather_model` keys used by the JSON data and Weather tab.

## 0.2.171

- Make `Archive species` show the selected species ID as read-only, without requiring manual retyping, and return to the species list after archiving.
- Sort the species maintenance sidebar alphabetically by scientific name for display without rewriting the JSON data order.

## 0.2.170

- Fix mushroom species lifecycle modals so `New species`, `Duplicate species` and `Restore species` forms receive clicks and keyboard focus in Home Assistant.

## 0.2.169

- Move the species maintenance toolbar above the page title and align the title with the mushroom section tabs to recover vertical space.
- Keep `Trophic mode` on the Ecology section header line so affinity subtabs and rows start higher on the screen.
- Replace anchor-jump controls with server-rendered modals for `New species`, `Duplicate species`, `Archive species` and `Restore species`.
- Implement defensive species lifecycle actions: duplicate creates a reviewed draft copy, archive moves an active profile to an archive file, restore brings it back when the ID is free, and permanent delete is only available from the archive with two browser warnings.

## 0.2.168

- Move the guided `New species` panel near the top of the species maintenance page so it is easier to test from Home Assistant.
- Mark `Duplicate species`, `Validate profile` and `Archive species` as planned disabled actions instead of leaving them looking like broken maintenance buttons.
- Document that create/duplicate/archive species flows need explicit functional review before closing the species maintenance workflow.

## 0.2.167

- Continue the mushroom species maintenance visual pass toward the documented mockup without changing the JSON model or POST contract.
- Make the `General` tab a read-only dashboard and move identity/taxonomy editing into the `Metadata` tab.
- Add semantic status-chip classes for confidence, calibration, taxonomy, edibility and review states.
- Add icon-bearing dashboard card titles and stronger card/list styling for the species maintenance page.
- Keep scoring decimal inputs at `0.01`, existing validation, import/export, raw JSON and `New species` behavior unchanged.

## 0.2.166

- Continue the mushroom species maintenance redesign toward the documented mockup.
- Compact the species metric strip so the validation card fits on wide Home Assistant screens.
- Replace outlined species tabs with underline-style tabs and add lightweight inline SVG icons.
- Add Ecology subtabs for host, forest, soil, lithology and habitat-feature affinities while preserving the existing POST fields and validation flow.
- Reduce profile detail value typography to match field labels more closely for a denser maintenance layout.

## 0.2.165

- Refine the mushroom species maintenance redesign with top section tabs, a wider species navigator and collapsed cross-validation warnings.
- Increase the Home Assistant WebUI maximum content width so Control Panel, Users and mushroom maintenance pages waste less lateral space on wide screens.
- Make scoring weight inputs use decimal steps of `0.01` with `0..1` bounds and a visible current-total indicator.
- Accept comma decimal values in profile/catalog numeric form submissions for Home Assistant browsers using Spanish/Catalan locale formatting.
- Move reference catalog rendering helpers into `mushroom_catalogs_ui.py` and remove stale mushroom profile rendering copies from `web_server.py`, keeping the HA server focused on routing, POST handling and persistence.

## 0.2.164

- Redesign the mushroom species detail view toward the documented species maintenance mockup.
- Move mushroom species UI rendering helpers out of `web_server.py` into a HA-specific presentation module.
- Add compact species status chips, left-side species navigation, overview cards, month chips, scoring bars and an action bar while preserving existing save/import/export behavior.

## 0.2.163

- Add guided mushroom species creation from the species maintenance page.
- Create new species as validated draft starter profiles with human-validation and calibration flags set conservatively.
- Block duplicate or malformed species IDs before persisting new profiles.

## 0.2.162

- Make mushroom species validation failures visible as validation-error alerts instead of generic status messages.
- Redirect failed species saves to the validation alert so blocked saves are easier to notice in Home Assistant.

## 0.2.161

- Add shared semantic validation for mushroom species profiles.
- Block duplicated simple profile values, duplicated affinity IDs and overlapping main/secondary fruiting months before saving.
- Keep the same semantic checks in the standalone mushroom JSON validator and HA-backed persistence flow.

## 0.2.160

- Compact the mushroom species summary metrics into a single-line dashboard band on wide screens.
- Hide already-used affinity IDs from new affinity dropdown rows while keeping backend duplicate protection.
- Document the pending redesign of the long Ecology tab.

## 0.2.159

- Split the mushroom species editor into tabs and expose calibration as its own maintenance area.
- Block duplicate IDs inside species affinity groups before saving profile changes.
- Add navigation from reference catalogs back to mushroom species.

## 0.2.158

- Add the first mushroom species maintenance WebUI with a species list, guided profile editor, catalog-backed ecology selectors, validation-backed saves and raw JSON advanced editing.
- Add full profiles JSON import/export and empty-template access from the species maintenance page.

## 0.2.157

- Add visible mushroom catalog cross-reference checks for host parent IDs and internal forest/lithology catalog references.
- Render host and forest parent IDs as selectors backed by the reference catalog.

## 0.2.156

- Replace mushroom catalog group chips with domain summary cards and add a domain-impact panel for the active catalog scope.

## 0.2.155

- Compact the mushroom catalog detail editor by removing duplicated usage metrics and widening the field-based form.

## 0.2.154

- Add field-based mushroom reference catalog editing while keeping raw JSON entry editing as an advanced panel.
- Add a first use-and-impact panel for selected catalog entries.

## 0.2.153

- Fix the mushroom catalog `All` filter so it keeps the full table visible instead of forcing the first catalog group.

## 0.2.152

- Fix mushroom catalog group filters so selecting a group without an entry ID selects the first row in that group instead of resetting to the first catalog.

## 0.2.151

- Fix mushroom catalog maintenance under Home Assistant ingress by using relative links/forms, seeding mushroom JSON defaults at server startup, and deriving reference-error counts from validator errors.

## 0.2.150

- Add the first mushroom reference catalog maintenance WebUI with validation-backed persistence, catalog entry creation, JSON import/export and empty template export.

## 0.2.149

- Fix the Users accordion so expanded panels honor the hidden state, all users start collapsed, and opening one user closes the others.

## 0.2.148

- Compact the expanded Users panel by keeping user details, permissions and audit in the save form while moving permissions to a scalable card grid and security actions to a separate compact row.

## 0.2.147

- Redesign the Home Assistant Control Panel as a compact tabbed dashboard while preserving all existing run, source, viewer, map, log and station enable/disable actions.

## 0.2.146

- Redesign the Home Assistant Users page as a compact accordion with a create-user modal, confirmation prompts for user/device/password actions and user audit timestamps.
- Replace deprecated UTC timestamp generation with timezone-aware UTC output while keeping the existing `Z` timestamp format.

## 0.2.145

- Optimize the MapLibre IDW layer refresh by reusing unchanged calculated data and avoiding duplicated recalculations during style and toggle events.

## 0.2.144

- Show the effective MapLibre IDW radius, grid cell size and smoothing power next to the device settings selectors.

## 0.2.143

- Render the MapLibre IDW layer above station circles so full opacity can cover station markers.

## 0.2.142

- Ensure the MapLibre IDW source and visual layer are both present on every refresh and force a repaint after data changes.

## 0.2.141

- Fix MapLibre IDW refresh so quick toggles, period changes and metric changes update the layer immediately without waiting for map movement.
- Avoid redundant IDW recalculation during base map style changes.

## 0.2.140

- Fix MapLibre IDW/Heatmap interaction state so quick buttons are session-only and Settings checkboxes persist mutually exclusive modes.
- Change MapLibre IDW radius and grid quality tuning to fixed kilometer-based values.
- Prevent zero-rain stations from painting an IDW rain field by themselves.

## 0.2.139

- Limit MapLibre IDW rain painting so zero-rain stations do not create a full blue overlay.

## 0.2.138

- Add an experimental MapLibre IDW layer with per-user access and per-device settings.
- Add Home Assistant defaults and technical tuning options for IDW radius, quality, smoothing, opacity and temperature altitude correction.

## 0.2.137

- Prevent protected MapLibre `config.js` from being cached so changed Home Assistant defaults take effect after restart.

## 0.2.136

- Fix MapLibre heatmap defaults for new devices and reset action by preserving absent device settings.
- Allow decimal Home Assistant values for the MapLibre station hover zoom threshold.
- Document validation of the nearest rainy station terrain popup.

## 0.2.135

- Add Home Assistant options for MapLibre hover zoom and default heatmap tuning.
- Add a MapLibre heatmap reset action to restore configured defaults per device.

## 0.2.134

- Adjust the MapLibre popup history sticky header spacing so it no longer covers the expanded history title while scrolling.

## 0.2.133

- Add per-user MapLibre permissions for heatmap access and metric selector access.
- Replace protected viewer admin-role gating for heatmap/metric controls with explicit user permissions.
- Enable both MapLibre heatmap permissions by default when creating admin users.
- Document the future permission-profile architecture for growing feature permissions.

## 0.2.132

- Fix MapLibre popup history column headers being partially covered by neighboring sticky header backgrounds.

## 0.2.131

- Fix the MapLibre station history sticky header spacing so column titles remain fully visible while the header stays flush with the popup top edge.

## 0.2.130

- Move the MapLibre station history sticky column header flush with the popup top edge to hide scrolled rows behind it.
- Prioritize data source startup so AEMET, Meteoclimatic and Meteocat start before Wunderground when three source worker threads are configured.

## 0.2.129

- Restore full-popup scrolling for MapLibre station history while keeping only the history column header sticky.

## 0.2.128

- Keep the MapLibre station history table header pinned to the top of the history list while scrolling long popup histories.

## 0.2.127

- Persist MapLibre admin heatmap settings in per-device settings.
- Keep Heatmap settings saving aligned with the rest of Settings: changes are saved when Settings is closed.

## 0.2.126

- Treat missing metric values as no data instead of zero in MapLibre scales, station points, popups and heatmaps.
- Preserve missing rain totals through Tomap aggregation instead of fabricating zero when all source values are missing.
- Keep real numeric zero values distinct from missing data for rain, humidity, temperature and wind.

## 0.2.125

- Hide MapLibre heatmap and metric buttons correctly for non-admin protected users.
- Use dynamic min/max metric scales for selected non-rain stations, including negative temperatures.
- Add a non-refreshing WebUI log page opened from the main log panel.
- Improve the sticky MapLibre popup history header so rows do not show through while scrolling.

## 0.2.124

- Promote MapLibre heatmap controls to the protected viewer for admin users only.
- Hide heatmap and metric controls completely for non-admin protected users while keeping the public experimental viewer available.
- Persist heatmap metric, enabled state, opacity, radius, intensity and weight curve per admin device.

## 0.2.123

- Add a Heatmap tab to the experimental MapLibre settings with metric, opacity, radius, intensity and weight curve controls.

## 0.2.122

- Read large incremental CSV files with full-file dtype inference to avoid pandas mixed-type warnings during update and map generation.

## 0.2.121

- Broaden the experimental MapLibre heatmap radius and make it adjustable from Settings.
- Draw the experimental heatmap above station points so the density layer is easier to inspect.
- Keep the heatmap independent from the minimum rain filter while respecting active source filters.

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
