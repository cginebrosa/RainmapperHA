# Changelog

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

- Añade el modo configurable de log detallado de Wunderground.
- Muestra siempre un resumen de Wunderground con las estaciones fallidas.
- Muestra el progreso de Wunderground cada 10% de estaciones procesadas.

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
