# Changelog

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
