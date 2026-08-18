# Changelog

## 0.2.260

- Reuse models produced by the same worker through a transient SHA-256 object
  cache, avoiding a redundant round trip through Home Assistant.
- Transfer a cold Predictor runtime as one verified archive while retaining
  hash-level delta synchronization whenever reusable local objects exist.
- Make Predictor freshness checks both accurate for rebased derived features
  and fast for immutable partitioned weather generations.

## 0.2.259

- Automatically promote a complete external reconstruction, ML v0, and V2--V6
  generation as soon as its linked comparison job finishes successfully.
- Preserve freshness validation, atomic installation, rollback, and predictor
  cache invalidation while keeping failed and unlinked jobs outside automation.

## 0.2.258

- Chain V2--V6 training from the exact species set verified as trained by ML v0,
  instead of recalculating a broader eligibility list from observations.

## 0.2.257

- Build V2--V6 training inputs from each fresh immutable rebuild snapshot and
  validate complete runtime benchmark coverage before fitting any member.
- Promote reconstruction, ML v0, and V2--V6 as one verified generation while
  retaining failed staging data for diagnosis and preserving the prior batch.
- Use enabled multi-source IDW weather consistently across V2--V6; count finite
  zero rainfall as valid support and exclude missing values without coercion.
- Derive V5/V6 ET0, climatic balance, and soil-moisture state from micro-area
  IDW weather with matching training and inference contracts.
- Resolve the historical V2 card exclusively from installed common-IDW batch
  artifacts instead of the legacy single-station comparator.
- Report granular preparation and fitting progress for complete local updates,
  including version, species, completed fits, successes, and failures.
- Cache validated manifests and immutable model bundles per Predictor request,
  and limit weather preparation to the exact lookback and physical state used
  by each installed profile.
- Reuse one extended IDW series per area in the species-week grid, fixing its
  unbound area error and reducing repeated overlapping weather calculations.
- Warn when trained inputs differ from current observations or weather while
  keeping every V2--V6 member explicitly experimental.
- Coordinate private worker `1.0.11` with fresh multiversion snapshots,
  physical-state inference parity, and safe terminal-result cleanup.

## 0.2.256

- Compare Biology V3 and altitude V2 on identical observation/horizon rows and
  whole 7/14-day fruiting groups, including per-horizon metrics and coverage.
- Keep month and direct altitude registered but inactive after matched tests;
  altitude remains applied through the physical temperature correction.
- Expose the V2--V6 mushroom model catalog through one generic registry while
  keeping unavailable exact generations visible but not selectable.
- Compare installed contract, temporal and estimator members independently in
  Predictor, preserving the existing explanations and never averaging member
  probabilities into an implicit ensemble.
- Give V2--V6 the same experimental status and show each version by profile,
  temporal contract, horizon and estimator with hold-out and domain cautions.
- Reset incompatible areas when the selected species changes so cached or
  handcrafted requests cannot render an unobserved species-area pair.
- Package hash-verified immutable runtime batches for local or external-worker
  inference, with strict generation resolution and no fallback to V2.
- Add an isolated worker `1.0.10` multiversion training command that writes no
  operational model and keeps one fitted lag-event artifact for horizons
  1/2/3/7.

## 0.2.255

- Cache DEM altitude when a micro-area is created or its geometry changes, and
  preserve the cached value when geometry is unchanged.
- Resolve elevation through the Catalunya, Andorra, and IGN MTN50 592 DEM
  chain while keeping missing coverage explicit.
- Keep Biology V3 benchmark inputs separated into predictive, quality, and
  metadata fields, with readable eligibility gates for fixed-gap and lag-event
  contracts.
- Preserve area-IDW rainfall and observation-level 7/14-day fruiting groups in
  the local Biology V3 benchmark contracts.
- Add a non-operational Biology V3 evaluator with chronological whole-flush
  splits and explicit feature-family comparisons; it never writes a reusable
  model artifact.

## 0.2.254

- Require training results to declare exactly the
  `fixed_gap_7d_altitude_v2` and `lag_event_altitude_v2` contracts; reject
  incompatible V1 generations before promotion.
- Coordinate worker `1.0.8`, which materializes station altitude in rebuilt
  features and trains the altitude-corrected temperature models.

## 0.2.253

- Train chained shadow models against the exact live metadata identity that is
  published by coordinated full-generation promotion.
- Wrap long Predictor worker errors inside the executor modal so internal paths
  and hashes remain readable without overflowing the dialog.

## 0.2.252

- Replace partial artifact rebuild and separate training controls with one
  explicit full rebuild-and-retrain workflow executed by the external worker.
- Automatically chain verified reconstructed artifacts into full model
  training, keeping both jobs independently diagnosable.
- Activate reconstructed artifacts and trained models as one coordinated
  generation, with rollback on promotion failure and pending observations
  cleared only after the complete update succeeds.

## 0.2.251

- Reset current-week Predictor views when leaving historical queries so their
  headings, day cards and remote calculations always use the same effective
  date, rendered without container-locale month names.

## 0.2.250

- Require `partitioned_weather_history_v1` before creating external-worker
  snapshots from the active partitioned weather archive.
- Transfer immutable weather generations as bounded, hash-verified snapshots
  and let worker `1.0.7` reuse unchanged objects from its persistent cache.
- Make weather feature windows deterministic across hosts and architectures.
- Cache the complete immutable partitioned weather generation in Predictor
  workers so historical queries read bounded station/date windows locally.
- Retain only the current and immediately previous Predictor runtime versions,
  reusing unchanged historical partitions by hash.
- Retain only 30 days of Wunderground diagnostic metrics using atomic writes.

## 0.2.248

- Prune immutable weather generations after every archive while retaining
  `CURRENT`, its immediate predecessor and every generation with an active
  reader lease.
- Delete only manifests and Parquet/catalog objects that are unreferenced by
  the complete retained set, under the exclusive weather writer lock.
- Run generation cleanup before downloads even when no pending batch exists,
  preventing scheduled runs from accumulating obsolete data in `/share`.

## 0.2.247

- Store canonical daily weather history in bounded source/year Parquet
  partitions and update only the partitions touched by each scheduled run.
- Keep the four live incremental CSV files to a 180-day operational window and
  retain complete recent intraday days for AEMET and Meteoclimatic rebuilding.
- Capture source updates in replay-safe pending batches and publish generations,
  live CSV files and catalogs atomically under a single run lock.
- Build Tomap from a bounded Parquet window, preserve missing-rain semantics and
  stop map publication when weather archiving cannot close successfully.
- Reduce Tomap memory pressure by avoiding full-frame metadata copies and keep
  Predictor reads bounded to the requested stations and dates.

## 0.2.246

- Clarify that the experimental Predictor signal selects the shadow estimator
  with the lowest valid Brier score independently for each weather contract.
- Explain that the displayed estimator names and probability range combine
  those per-contract winners rather than ranking all shadows by raw percentage.
- Clarify in the statistical-reliability help that `limited` can describe one
  validated estimator family or a disagreement of at least 20 points; it does
  not mean that the selected estimator failed validation.

## 0.2.245

- Populate remote recommender areas explicitly and derive them defensively from
  rankings so the initial weekly Predictor summary cannot render empty.
- Add cooperative cancellation to the remote Predictor modal and preserve
  terminal cancellation before the worker publishes a completed response.
- Raise the interactive Predictor response guardrail to 8 MiB and retain the
  exact Home Assistant rejection detail for worker-side diagnostics.
- Externalize completed Predictor responses from the hot job queue into
  size- and SHA-256-verified sidecars, preventing polling from repeatedly
  parsing tens of megabytes of retained responses.

## 0.2.244

- Rename the Predictor's ecological and operational reliability indicators so
  their scope is explicit instead of relying on internal model terminology.
- Add localized, keyboard-focusable help to verdict fields, weather contracts,
  estimators and technical diagnostics including Brier, ROC-AUC, score origin,
  coverage, horizon and out-of-domain variables.
- Increase the Predictor's desktop width while retaining responsive wrapping
  and horizontally scrollable technical tables on narrow screens.

## 0.2.243

- Replace the future-blind Predictor recommendation with the operational
  `fixed_gap_7d_v1` and `lag_event_v1` contracts, sharing the same feature
  construction between training, Home Assistant and external workers.
- Preserve weather-window coverage, tolerate isolated missing rain days, search
  significant events for 90 days and select the nearest sufficiently complete
  station within 15 km.
- Separate ecological compatibility, validated statistical support and the
  practical verdict, retaining rich deterministic explanations and complete
  technical audit data without presenting raw scores as calibrated probabilities.
- Compare Extra Trees, Histogram Gradient Boosting, KNN and calibrated SVM as
  shadow estimators, exposing their best validated experimental signal without
  allowing it to change recommendations or rankings.
- Improve Predictor typography and reference-range presentation, and show model
  comparison details by default on the date view.

## 0.2.242

- Gate Predictor results with each species' configured main and secondary
  phenology, excluding out-of-season species before loading models or weather.
- Keep temporal holdout as an optional diagnostic, use stratified cross-validation
  over all eligible episodes, and refit production models with the complete dataset.
- Define the operational training target as a worthwhile outing: treat `scarce`
  as favorable while retaining `very_scarce` and `absent` as unfavorable.

## 0.2.241

- Coalesce external rebuild and ML-training progress and cancellation polling
  to one update every two seconds while preserving the latest and terminal state.
- Reuse filesystem-identity-bound GIS hashes when validating candidate promotion,
  rehashing only files whose identity changed instead of rereading the full dataset.

## 0.2.240

- Rank Predictor Auto choices by median cold opening wall time instead of mixed
  backend-only samples, while keeping the selected executor for the session.
- Show separate first-opening and warm-navigation timings and use the matching
  estimate for initial entry and subsequent Predictor navigation.
- Record completed Home Assistant and worker Predictor wall times once per
  operation alongside their backend duration.
- Increase Predictor typography and usable width while preserving horizontally
  scrollable tables on narrow screens.

## 0.2.239

- Stop relaying fine-grained Predictor progress synchronously through the worker
  coordinator, avoiding HTTP round trips that dominated fast predictions.
- Show a client-side estimated waiting indicator from comparable executor
  timings while preserving real completion metrics in runtime diagnostics.
- Keep interactive worker job state limited to durable launch and completion
  transitions, with the full diagnostic response retained by Home Assistant.

## 0.2.238

- Keep Predictor executor selection and progress as mutually exclusive modal
  states, avoiding a stale Home Assistant recommendation during worker jobs.
- Batch model inference for rankings, weekly matrices and history while retaining
  the same features, probabilities and transport contract.
- Reuse bounded per-runtime prediction and response caches across interactive
  navigation, and expose response-cache hits in Home Assistant diagnostics.
- Describe worker Predictor claims as interactive predictions instead of generic
  non-destructive tests.

## 0.2.237

- Preserve the selected Predictor executor across week, species, date and
  history views, reselecting only when it becomes unavailable.
- Show executor selection and worker progress in modals for every interactive
  Predictor navigation instead of replacing the current page.
- Label `worker_predictor_v1` jobs as interactive predictions in worker history.
- Centralize manual executor selection and Home Assistant execution as two
  independent code-level capabilities, both enabled for the current private
  Home Assistant panel and ready for future authenticated policy resolution.

## 0.2.236

- Preserve the worker's authoritative cold/warm state in remote Predictor
  diagnostics instead of defaulting completed worker requests to warm.
- Retain remote runtime cache status, transferred bytes, backend duration, job
  identity and worker version in the Home Assistant diagnostic summary.

## 0.2.235

- Distinguish operational duration from the longer diagnostic observation
  window that may include the 60- and 600-second recovery snapshots.
- Format diagnostic durations of at least one minute as `m:ss`, while retaining
  numeric seconds in the persistent diagnostic records.
- Keep twenty recent executions in a ten-row scrollable table with a sticky
  header, and group version averages by operation and comparable workload.

## 0.2.234

- Run the Fruiting Predictor on Home Assistant or an idle compatible worker,
  with capability-based compatibility, immutable runtime synchronization and
  coordinator-owned results and diagnostics.
- Recommend the fastest comparable executor from retained cold/warm timings,
  while preserving explicit manual selection and Home Assistant fallback.
- Open executor selection and live job progress in a localized Control Panel
  modal, retaining the direct full-page flow as a no-JavaScript fallback.
- Reuse verified worker runtime files by SHA-256, retain predictor instances for
  warm requests and avoid retransmitting unchanged models and weather data.

## 0.2.233

- Move runtime observability into a dedicated Diagnostics tab with retained
  history, comparable A/B executions, regional timestamps, temporal and
  per-version evolution, explicit metric outcomes and shared-scale Gantt views.
- Record real download, parse, incremental and write intervals for AEMET,
  Meteoclimatic, Meteocat and Wunderground in diagnostic schema `2.2`, while
  preserving older `2.1` executions as limited-detail history.
- Prefer the compact daily weather Parquet for capable external workers and
  retain automatic CSV fallback for legacy workers; reject incompatible job
  reassignment through explicit heartbeat capabilities.
- Reconcile worker storage before every external launch with a visible notice,
  retain 50 scrollable job tombstones, remove terminal/promoted private bundles
  safely and acknowledge worker-side cleanup without touching GIS/DEM caches.

## 0.2.232

- Persist runner and Predictor resource heartbeats every ten seconds with host
  boot identity, uptime, cumulative memory peaks, temperature and OOM counters.
- Bound the complete indexed AEMET observations download to 90 seconds and
  record download, decode, parse and normalization phases for crash diagnosis.
- Archive the partial runner log automatically when startup reconciles an
  interrupted action, preserving it before the next run overwrites `last_run.log`.

## 0.2.231

- Preserve the Home Assistant Ingress token when reporting Predictor browser
  Navigation Timing, and verify URL resolution under both Ingress and direct
  paths.
- Include the rollback-safe observation lifecycle and persistent media cleanup
  introduced in `0.2.230` without overwriting that published image tag.

## 0.2.230

- Make observation archive and restore mutations serialized and rollback-safe,
  avoiding partial moves and duplicate active/archive records after failures.
- Persist media cleanup intents before removing the last observation reference,
  recheck active and archived references before unlinking, and retry interrupted
  cleanup safely during startup and profile maintenance.
- Protect media shared by multiple observations and cover delete, archive,
  restore, unlink-failure and rollback paths with regression tests.

## 0.2.229

- Evolve runtime diagnostics into a persistent black box with boot IDs,
  interruption recovery, bounded long-term summaries and anomalies, retained
  failed-run logs, an expanded ZIP and live Control Panel status.
- Correlate full Predictor server requests, cold model loads, weather loads and
  browser Navigation Timing without storing species, areas or predictions.
- Bound normal Predictor weather materialisation to one replaceable 96-day
  window (90-day coverage lookback plus the seven-day UI horizon). Historical
  date queries load their window on demand; History loads its required episode
  span once and the next current view releases it.

## 0.2.228

- Include `ml_train_report.json` in external `ml_train_v0` results and validate
  its schema, size, hash and trained-species set before accepting the candidate.
- Promote model files first and their verified report last with atomic writes,
  then release the Predictor cache so the newly trained models become visible.
- Hide stale `.joblib` files from the Predictor unless the live training report
  confirms that their species completed successfully.

## 0.2.227

- Make the Predictor's filtered parquet read effective on RPi4: the runner now
  writes station-sorted row groups of 512 rows atomically, while the interactive
  path rejects an old monolithic parquet before it can materialise the full
  dataset. A missing or stale station catalog is rebuilt safely from parquet.
- Keep training and prediction feature construction aligned, including duplicate
  consecutive-rain filtering and best-coverage station selection among the five
  nearest candidates. Cache identity now includes the station filter and cache
  loads are single-flight.
- Add automatic bounded runtime diagnostics for runner and Predictor memory,
  cgroup usage, CPU, temperature, duration and OOM events. Diagnostics can be
  downloaded as a redacted ZIP from the Control Panel.
- Prevent runner and Predictor from overlapping. Predictor caches are released
  before a runner starts, and Predictor displays a translated notice while an
  update or map generation is active.
- Populate `PredictionResult.features_used` with the 39 real model inputs and
  correct the translated weather-factor bars to use 14-day rain and 7-day
  temperature feature names.

## 0.2.226

- Fix P0 memory issue: the Predictor no longer materialises all 1,932 weather
  stations (~358 MiB) on startup. It now loads a lightweight station coordinate
  catalog (~100 KB) and filters the daily parquet to the top-5 nearest stations
  within 15 km of each model micro-area (~100 stations, ~40 MiB, 89% reduction).
  The runner generates `weather_stations_catalog.parquet` alongside the existing
  `weather_daily.parquet`.
- Fix rain values showing "undefined" or "null" in the MapLibre popup for days
  where the quality filter nullified consecutive duplicate readings (Wunderground
  sensor carry-forward artefact): these now display as "N/A".

## 0.2.225

- Show model reliability statistics in the Predictor: species-level holdout
  accuracy and per-area episode count with colour badges (🟩 ≥10 / 🟨 4–9 /
  🟥 1–3) on both the "Por especie" and "Consultar fecha" tabs.
- Compute backtest statistics during ML training (stored in
  `mushroom_ml_v0_report.json`): holdout test accuracy (honest 30% newest
  episodes the model never saw), per-area episode count, false-negative and
  false-positive counts. These are read by the Predictor UI without any live
  computation.
- Fix Predictor showing stale weather data after the runner regenerates
  `weather_daily.parquet` without an add-on restart: the shared parquet cache
  now checks `st_mtime` on every Predictor request and reloads automatically
  when the file has changed.

## 0.2.224

- Fix "← Control panel" back link on the Predictor page returning 404: the
  link used `../../` but under HA Ingress one level up (`../`) is correct,
  consistent with all other mushroom screens.

## 0.2.223

- Add "← Control panel" back link on the Predictor page so it is possible to
  return to the main panel without navigating away in HA.

## 0.2.222

- Speed up Predictor initial load (first cold start after add-on restart):
  `load_daily_weather_parquet` now uses vectorised pandas operations instead of
  a row-by-row Python loop over 620k records. Date parsing, string filtering and
  float conversion are applied to whole columns before grouping by station,
  reducing load time from ~30 s to ~3–6 s on the RPi.
- Add timing and file size to the `weather_daily.parquet generated` log line.

## 0.2.221

- Fix Predictor page timing out (blank page) after promoting trained models: all
  `MushroomMLPredictor` instances now share a single module-level weather stations
  cache instead of each loading the full incremental CSV files (~110 MB) independently.
  With 7+ trained species the previous behaviour caused the RPi to read 770+ MB of CSV
  data synchronously on every first Predictor page load, triggering OOM and an HA
  ingress timeout.

## 0.2.220

- Fix Predictor showing no back button when there are no trained models yet.

## 0.2.219

- Fix ML training result manifest using wrong filename (`{species_id}.joblib`
  instead of `mushroom_ml_v0_{species_id}.joblib`), causing promoted models to
  be empty and the Predictor to show no trained species.

## 0.2.218

- Fix stuck jobs blocking new ml_train_v0 enqueuing: `cancel_requested` jobs
  no longer count as active for work-key deduplication.
- Add "Abandon job" button for force-cancelled jobs whose worker is unreachable,
  allowing the operator to permanently mark them as cancelled.
- Fix ml_train worker selector not pre-selecting the default worker, which could
  cause jobs to be routed to a non-default (potentially disconnected) worker.

## 0.2.217

- Fix `ml_train_v0` jobs not showing the Promote action in Workers and jobs:
  the job-type set controlling the actions column excluded `worker_ml_train_v0`.
- Fix completed `ml_train_v0` jobs showing "Assignment test completed" as the
  phase instead of "ML training completed".

## 0.2.216

- Fix HTTP 409 error when the external worker downloads `ml_train_v0` input
  files: `authorize_input_download` was missing `JOB_TYPE_ML_TRAIN` in its
  allowed job-type set, causing the worker to fail immediately after claiming
  the job.

## 0.2.215

- Add ML model training job type `ml_train_v0` for the external worker: the
  worker trains scikit-learn models from the current features artifact, uploads
  a manifest and `.joblib` files, and the operator promotes them manually from
  `Workers and jobs`.
- Add `Predictor` screen with four views: this week's ranking by area, per-species
  week detail, single-date query, and history with clickable correct/FN/FP filter
  cards.
- Add evidence clipboard to observations: copy and paste the five evidence groups
  and two notes across observations from the same field trip via `localStorage`.
- Add date filter with auto-slash insertion and submit-on-blur in observations.
- Replace native `confirm()` for permanent observation deletion with a centred
  CSS modal.
- Fix observation archiving to not expand the archived list and to auto-select
  the next observation.
- Fix observation duplication to inherit media references from the original.
- Fix predictor history view to use the correct `observed_at` key and `actual`
  key for FN/FP counts, and show a binary favorable/unfavorable label in the
  Real column.

## 0.2.214

- Restore immediate observation searches when pressing Enter and submit them
  automatically after a short typing delay.
- Search every persisted observation field and resolved display values such as
  species, area, micro-area and catalog labels across the complete active
  dataset before pagination.
- Reset observation searches to the first result page so matches cannot remain
  hidden by a stale page selection.

## 0.2.213

- Allow operators to discard terminal, unpromoted worker candidates through a
  confirmation dialog while preserving the live model, rollback copies and
  shared GIS/DEM cache.
- Coordinate authenticated, idempotent cleanup of private candidate inputs,
  results and worker job files without permitting active or uncertain
  promotions to be deleted.
- Compact `Workers and jobs` for Home Assistant plus two external workers,
  collapse technical controls and remove redundant header content.
- Make every recent-job column sortable, order mixed HA/worker timestamps by
  their actual instant and label local rebuilds without exposing random IDs.
- Remove the legacy GIS review panel from Observations because it was not tied
  to an identifiable recent job and could present an empty or stale result.

## 0.2.212

- Run verified worker-candidate promotion in the background so Home Assistant
  Ingress remains responsive during freshness and GIS/DEM hash validation.
- Persist promotion phases and percentage and show a live progress bar in
  `Workers and jobs` while preventing duplicate promotion submissions.
- Preserve fail-closed freshness checks, atomic installation, rollback copies
  and the Home Assistant reconstruction fallback.

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
