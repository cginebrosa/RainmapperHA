/* Point-query presentation. Scientific probabilities come from the executor. */
import { renderPointWeather } from "./prediction-weather.js";
export function createPredictionMode(bridge) {
  const { map, text, config } = bridge;
  let enabled = false;
  let revision = 0;
  let pending = null;
  let popup = null;
  let result = null;
  let dayIndex = 0;
  let remoteQuery = null;
  let elapsedMs = null;
  const colors = ["#087baa", "#993f76", "#6b7180"];
  const make = (tag, content, className) => {
    const node = document.createElement(tag);
    if (content !== undefined) node.textContent = content;
    if (className) node.className = className;
    return node;
  };
  const initialNotice = bridge.dataMode === "prediction" ? "prediction_experimental" : "simulation";
  const banner = make("div", text(initialNotice), "pm-demo-banner");
  banner.setAttribute("role", "status");
  const dialog = make("dialog", undefined, "pm-wait");
  const title = make("h2", text("calculating"));
  title.id = "pm-wait-title";
  dialog.setAttribute("aria-labelledby", title.id);
  const notice = make("p", text(initialNotice));
  const spinner = make("span", undefined, "pm-spinner");
  spinner.setAttribute("aria-hidden", "true");
  const status = make("p", "");
  status.setAttribute("role", "status");
  const cancel = make("button", text("cancel"));
  cancel.type = "button";
  dialog.append(spinner, title, notice, status, cancel);

  function closePopup() {
    const old = popup;
    popup = null;
    result = null;
    old?.remove();
  }
  function cancelQuery() {
    revision += 1;
    pending?.abort();
    pending = null;
    if (remoteQuery) {
      const id = remoteQuery; remoteQuery = null;
      bridge.fetch(`${config.apiBase}/queries/${encodeURIComponent(id)}/cancel`, { method: "POST" }).catch(() => {});
    }
    if (dialog.open) dialog.close();
  }
  cancel.addEventListener("click", cancelQuery);
  dialog.addEventListener("cancel", (event) => { event.preventDefault(); cancelQuery(); });

  function localDay() {
    const parts = new Intl.DateTimeFormat("en-CA", {
      timeZone: bridge.calendarTimezone(), year: "numeric", month: "2-digit", day: "2-digit"
    }).formatToParts(new Date());
    const value = name => parts.find(part => part.type === name).value;
    return `${value("year")}-${value("month")}-${value("day")}`;
  }
  function percent(value) {
    return value === null ? "—" : `${Math.round(value * 100)} %`;
  }
  function contextNames(kind) {
    const rows = result?.ecology?.status === "available" ? result.ecology.mapped_context?.[kind] : null;
    if (!Array.isArray(rows) || rows.length > 32) return [];
    const language = bridge.language?.() || "es";
    return rows.map(row => row.label?.[language] || row.label?.es || row.label?.en)
      .filter(label => typeof label === "string" && label.trim() && label.length <= 128);
  }
  function validEcology(ecology, dates) {
    if (ecology === undefined) return true; // Original isolated demo contract.
    if (!ecology || !["available", "unavailable"].includes(ecology.status)) return false;
    if (!Array.isArray(ecology.species) || ecology.species.length > 32) return false;
    if (ecology.status === "unavailable") return ecology.species.length === 0;
    const states = ["compatible", "incompatible", "unknown"];
    return Array.isArray(ecology.dates) && ecology.dates.length === dates.length &&
      ecology.dates.every((d, i) => d === dates[i]) &&
      [null, "host_data_missing", "terrain_context_missing"].includes(ecology.abstention_reason) &&
      ecology.species.every(row => typeof row.name === "string" && row.name.length <= 256 &&
        typeof row.scientific_name === "string" && row.scientific_name.length <= 256 &&
        states.includes(row.status) && Array.isArray(row.daily_statuses) &&
        row.daily_statuses.length === dates.length && row.daily_statuses.every(s => s === row.status) &&
        Array.isArray(row.daily_season_phases) && row.daily_season_phases.length === dates.length &&
        row.daily_season_phases.every(p => ["main","secondary","out_of_season","unknown"].includes(p)));
  }
  function validResponse(data, request) {
    return data?.contract === config.contract && data.request_id === request.request_id &&
      ["simulation","prediction"].includes(data.data_mode) && data.provenance?.scientifically_validated === false &&
      data.point?.lat === request.point.lat && data.point?.lon === request.point.lon &&
      Array.isArray(data.dates) && data.dates.length === 7 &&
      data.dates.every((day) => typeof day === "string" && /^\d{4}-\d{2}-\d{2}$/.test(day)) &&
      validEcology(data.ecology, data.dates) &&
      Array.isArray(data.species) && data.species.length <= 32 && data.species.every((row) =>
        typeof row.label_key === "string" && ["available", "no_model"].includes(row.status) &&
        Array.isArray(row.probabilities) && row.probabilities.length === data.dates.length &&
        row.probabilities.every((value) => value === null ||
          (typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 1)));
  }
  async function query(event) {
    if (!enabled || dialog.open || bridge.isStation(event.point) || bridge.wasLongPress()) return;
    cancelQuery();
    closePopup();
    const ownRevision = revision;
    const controller = new AbortController();
    pending = controller;
    title.textContent = text("calculating");
    cancel.textContent = text("cancel");
    status.textContent = "";
    spinner.hidden = false;
    dialog.showModal();
    cancel.focus();
    const request = {
      contract: config.contract,
      request_id: globalThis.crypto?.randomUUID?.() || `demo_${Date.now()}_${revision}`,
      point: { lat: event.lngLat.lat, lon: event.lngLat.lng }, start_date: localDay(),
      calendar_timezone: bridge.calendarTimezone(),
      horizon_days: 7, history_days: 60, species_ids: [],
      execution: bridge.execution(),
    };
    const started = performance.now();
    const timeout = setTimeout(() => controller.abort(), 60000);
    try {
      const submit = () => bridge.fetch(`${config.apiBase}/queries`, {
        method: "POST", cache: "no-store", signal: controller.signal,
        headers: { "Content-Type": "application/json" }, body: JSON.stringify(request),
      });
      let response = await submit();
      if (request.execution === "worker" && response.status === 503) {
        const failure = await response.clone().json().catch(() => null);
        if (["executor_unavailable", "worker_busy"].includes(failure?.error)) {
          if (!enabled || revision !== ownRevision || controller.signal.aborted) return;
          // A rejected submission has no queued query. Retry once locally;
          // the user's saved executor and the worker protocol stay unchanged.
          request.execution = "local";
          request.request_id = globalThis.crypto?.randomUUID?.() || `local_${Date.now()}_${revision}`;
          status.textContent = text("execution_fallback");
          response = await submit();
        }
      }
      if (!response.ok) {
        if (response.status === 503) {
          const failure = await response.json();
          throw new Error(failure.error === "worker_busy" ? "worker_busy" : "unavailable");
        }
        throw new Error("failed");
      }
      if (response.status === 202) {
        const accepted = await response.json();
        if (!/^[A-Za-z0-9_-]{8,80}$/.test(accepted.query_id || "")) throw new Error("invalid_query");
        remoteQuery = accepted.query_id;
        if (revision !== ownRevision || controller.signal.aborted) { cancelQuery(); return; }
        status.textContent = text(request.execution === "worker" ? "waiting_worker" : "calculating");
        while (true) {
          await new Promise(resolve => setTimeout(resolve, document.hidden ? 2000 : 400));
          if (controller.signal.aborted) throw new Error("cancelled");
          response = await bridge.fetch(`${config.apiBase}/queries/${encodeURIComponent(accepted.query_id)}`, {cache:"no-store", signal:controller.signal});
          if (!response.ok) throw new Error("failed");
          if (response.status !== 202) break;
        }
        remoteQuery = null;
      }
      const raw = await response.text();
      if (new TextEncoder().encode(raw).length > 256 * 1024) throw new Error("oversized");
      const data = JSON.parse(raw);
      if (!validResponse(data, request)) throw new Error("invalid_response");
      if (!enabled || revision !== ownRevision) return;
      pending = null;
      dialog.close();
      result = data;
      elapsedMs = performance.now() - started;
      dayIndex = 0;
      showResult(event.lngLat);
    } catch (error) {
      if (!enabled || revision !== ownRevision) return;
      pending = null;
      spinner.hidden = true;
      title.textContent = text("error");
      status.textContent = text(error.message === "worker_busy" ? "worker_busy" : error.message === "unavailable" ? "executor_unavailable" : "retry");
      cancel.textContent = text("close");
    } finally {
      clearTimeout(timeout);
    }
  }

  function calendarLabel() {
    const label = make("label", undefined, "pm-calendar");
    const timezone = make("span", undefined, "pm-calendar-timezone");
    timezone.append(make("span", `${text("calendar_timezone")}: `, "pm-timezone-caption"),
      make("span", `${text("calendar_zone")}: `, "pm-zone-caption"),
      make("span", result.calendar_timezone || bridge.calendarTimezone()));
    timezone.title = result.calendar_timezone || bridge.calendarTimezone();
    label.append(timezone, make("span", text("date"), "pm-date-title"));
    return label;
  }

  function renderEcology(container, header) {
    // Python supplies both levels; the visible list also requires an in-season day.
    const ecology = result.ecology;
    const section = make("section", undefined, "pm-ecology");
    const dateLabel = calendarLabel();
    const select = make("select");
    select.ariaLabel = text("date");
    result.dates.forEach((day, i) => {
      const option = make("option", day); option.value = String(i); select.append(option);
    });
    select.value = String(dayIndex); dateLabel.append(select);
    const predicted = new Map(result.data_mode === "prediction" ? result.species.map(row => [row.species_id,row]) : []);
    const weeklyValues = row => result.dates.map((_, day) =>
      row.status === "compatible" && ["main", "secondary"].includes(row.daily_season_phases[day]) &&
      Number.isFinite(predicted.get(row.species_id)?.probabilities?.[day])
        ? predicted.get(row.species_id).probabilities[day] : null);
    // Only plotted species consume colors. Keep the assignment for the whole
    // week, independent of daily ranking, absent models and discarded species.
    const ids = [...new Set(ecology.species.filter(row => weeklyValues(row).some(Number.isFinite))
      .map(row => row.species_id).filter(Boolean))].sort();
    const palette = ["#0072b2", "#d55e00", "#7b3294", "#00804a",
      "#cc338b", "#8c510a", "#008b9a", "#4d4d4d"];
    const speciesColors = new Map(ids.map((id, index) => [id, palette[index] ||
      `hsl(${((index - palette.length) * 137.508 + 35) % 360} 70% 30%)`]));
    const chart = make("div", undefined, "pm-weekly-chart");
    header.append(dateLabel, chart);
    const status = make("p", undefined, "pm-ecology-status");
    status.setAttribute("role", "status");
    const list = make("ul", undefined, "pm-species");
    const render = () => {
      list.replaceChildren();
      const probability = row => predicted.get(row.species_id)?.probabilities?.[dayIndex];
      const eligible = ecology.status === "available" && !ecology.abstention_reason
        ? ecology.species.filter(row => row.status === "compatible" &&
            ["main","secondary"].includes(row.daily_season_phases[dayIndex])) : [];
      status.textContent = text(ecology.status === "unavailable" ? "ecology_unavailable" :
        ecology.abstention_reason === "terrain_context_missing" ? "ecology_terrain_missing" :
        ecology.abstention_reason === "host_data_missing" ? "ecology_hosts_missing" :
        eligible.length ? (result.data_mode === "prediction" ? "ecology_calculated" : "ecology_candidates") : "ecology_none");
      eligible.sort((a,b) => (Number.isFinite(probability(b)) ? probability(b) : -1) -
        (Number.isFinite(probability(a)) ? probability(a) : -1));
      const series = eligible.map(row => ({id:row.species_id, name:row.name,
        color:speciesColors.get(row.species_id), values:weeklyValues(row)}));
      renderWeeklyChart(chart, series, select);
      for (const row of eligible) {
        const item = make("li");
        item.dataset.speciesId = row.species_id || "";
        const value = probability(row);
        const calculated = result.data_mode === "prediction";
        const name = make("strong", row.name, "pm-species-name");
        const values = weeklyValues(row);
        const valid = values.filter(Number.isFinite);
        if (valid.length) {
          const color = speciesColors.get(row.species_id);
          const dot = make("span", undefined, "pm-species-color");
          dot.style.backgroundColor = color;
          dot.setAttribute("aria-hidden", "true");
          name.prepend(dot);
        }
        item.append(name, make("span", calculated ?
          (Number.isFinite(value) ? percent(value) : text("prediction_uncalculated")) : text("prediction_pending")),
                    make("small", row.scientific_name));
        if (valid.length) {
          const peak = Math.max(...valid);
          item.append(make("small", `${text("weekly_peak")}: ${percent(peak)} · ${result.dates[values.indexOf(peak)]}`, "pm-weekly-peak"));
        }
        item.append(make("small", text(`season_${row.daily_season_phases[dayIndex]}`), "pm-season-phase"));
        if (row.reasons?.includes("ph_conflict_soil_supported")) {
          item.append(make("small", text("soil_ph_supported"), "pm-soil-ph-supported"));
        }
        for (const reason of ["soil_ph_conditional", "soil_not_listed"]) {
          if (row.reasons?.includes(reason)) item.append(make("small", text(reason)));
        }
        list.append(item);
      }
    };
    select.addEventListener("change", () => { dayIndex = Number(select.value); render(); });
    render(); section.append(status, list);
    const excluded = ecology.status === "available" ? ecology.species.filter(row => row.status !== "compatible") : [];
    if (excluded.length) {
      const details = make("details", undefined, "pm-ecology-exclusions");
      details.append(make("summary", text("ecology_exclusions")));
      const entries = make("ul");
      const reasonKeys = ["ph_outside", "ph_unknown", "ph_overlap", "soil_excluded", "soil_mixed_conflict",
        "soil_unresolved", "hosts_unknown", "habitat_unknown", "altitude_outside", "altitude_unknown", "terrain_context_missing"];
      for (const row of excluded) {
        const item = make("li");
        item.append(make("strong", row.name));
        for (const key of reasonKeys) {
          if (row.reasons?.includes(key)) item.append(make("small", text(`reason_${key}`)));
        }
        entries.append(item);
      }
      details.append(entries); section.append(details);
    }
    container.append(section);
  }

  function renderWeeklyChart(container, series, select) {
    container.replaceChildren();
    const calculated = series.filter(row => row.values.some(Number.isFinite));
    container.hidden = !calculated.length;
    if (!calculated.length) return;
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    // Reduce the plot area on phones, retaining the same label and marker sizes.
    const chartHeight = window.matchMedia("(max-width:480px)").matches ? 104 : 128;
    const plotBottom = chartHeight - 26;
    svg.setAttribute("viewBox", `0 0 400 ${chartHeight}`);
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", text("weekly_chart"));
    const node = (tag, attrs, label) => {
      const child = document.createElementNS(svg.namespaceURI, tag);
      Object.entries(attrs).forEach(([key,value]) => child.setAttribute(key, value));
      if (label !== undefined) child.textContent = label;
      return child;
    };
    const x = day => 34 + day * 358 / Math.max(1, result.dates.length - 1);
    const y = value => plotBottom - value * (plotBottom - 10);
    const descriptions = [];
    const tooltip = make("div", undefined, "pm-chart-tooltip");
    tooltip.setAttribute("role", "tooltip");
    tooltip.hidden = true;
    const hideTooltip = () => { tooltip.hidden = true; };
    let hoveredDay = null;
    const showTooltip = day => {
      if (!tooltip.hidden && hoveredDay === day) return;
      hoveredDay = day;
      tooltip.replaceChildren(make("strong", result.dates[day]));
      for (const row of calculated) {
        const value = row.values[day];
        if (!Number.isFinite(value)) continue;
        const entry = make("div", undefined, "pm-chart-tooltip-row");
        const dot = make("span", undefined, "pm-species-color");
        dot.style.backgroundColor = row.color;
        dot.setAttribute("aria-hidden", "true");
        entry.append(dot, make("span", row.name), make("strong", percent(value)));
        tooltip.append(entry);
      }
      if (tooltip.children.length === 1) tooltip.append(make("div", text("prediction_uncalculated")));
      tooltip.hidden = false;
      const bounds = svg.getBoundingClientRect();
      const width = tooltip.offsetWidth;
      const left = x(day) * bounds.width / 400 - width / 2;
      tooltip.style.left = `${Math.max(0, Math.min(bounds.width-width, left))}px`;
      tooltip.style.top = "0px";
    };
    for (const value of [0, .25, .5, .75, 1]) {
      svg.append(node("line", {x1:34,x2:392,y1:y(value),y2:y(value),stroke:"#cad6df"}),
        node("text", {x:29,y:y(value)+3,"text-anchor":"end",class:"pm-chart-label"}, `${value*100}%`));
    }
    svg.append(node("line", {x1:x(dayIndex),x2:x(dayIndex),y1:8,y2:plotBottom+2,
      stroke:"#526678","stroke-dasharray":"3 3",class:"pm-chart-selected-day"}));
    for (const row of calculated) {
      const group = node("g", {"data-species-id":row.id,stroke:row.color,fill:row.color});
      let segment = [];
      const flush = () => {
        if (segment.length > 1) group.append(node("polyline", {points:segment.join(" "),fill:"none","stroke-width":2}));
        segment = [];
      };
      row.values.forEach((value, day) => {
        if (!Number.isFinite(value)) { flush(); return; }
        segment.push(`${x(day)},${y(value)}`);
        const point = node("circle", {cx:x(day),cy:y(value),r:day===dayIndex?3.5:2.5,"data-day":day});
        const description = `${row.name} · ${result.dates[day]}: ${percent(value)}`;
        point.setAttribute("tabindex", "0");
        point.setAttribute("aria-label", description);
        point.addEventListener("focus", () => showTooltip(day));
        point.addEventListener("blur", hideTooltip);
        group.append(point); descriptions.push(description);
      });
      flush(); svg.append(group);
    }
    result.dates.forEach((date, day) => {
      svg.append(node("text", {x:x(day),y:chartHeight-6,"text-anchor":day===0?"start":day===result.dates.length-1?"end":"middle",
        class:"pm-chart-label"},date.slice(8,10)+"/"+date.slice(5,7)));
    });
    svg.append(node("desc", {}, descriptions.join("; ")));
    svg.addEventListener("pointermove", event => {
      const bounds = svg.getBoundingClientRect();
      const position = (event.clientX-bounds.left)*400/bounds.width;
      if (position < 34 || position > 398) { hideTooltip(); return; }
      showTooltip(Math.max(0, Math.min(result.dates.length-1,
        Math.round((position-34)/358*(result.dates.length-1)))));
    });
    svg.addEventListener("pointerleave", hideTooltip);
    svg.addEventListener("keydown", event => { if (event.key === "Escape") hideTooltip(); });
    // The existing select remains the keyboard-accessible date control.
    svg.addEventListener("click", event => {
      const bounds = svg.getBoundingClientRect();
      const day = Math.max(0, Math.min(result.dates.length-1,
        Math.round(((event.clientX-bounds.left)*400/bounds.width-34)/358*(result.dates.length-1))));
      select.value = String(day);
      select.dispatchEvent(new Event("change"));
    });
    container.append(svg, tooltip);
  }

  function showResult(lngLat) {
    const container = make("section", undefined, "pm-result");
    const header = make("header", undefined, "pm-result-header");
    const body = make("div", undefined, "pm-result-body");
    body.tabIndex = 0;
    body.setAttribute("role", "region");
    body.ariaLabel = text("result");
    container.append(header, body);
    const close = make("button", "×", "pm-close");
    close.type = "button";
    close.ariaLabel = text("close");
    close.addEventListener("click", closePopup);
    const modeNotice = text(result.data_mode === "prediction" ? "prediction_experimental" : result.ecology ? "ecology_prototype" : "simulation");
    banner.textContent = notice.textContent = modeNotice;
    header.append(close, make("strong", modeNotice, "pm-simulation"),
      make("h2", text("result")));
    const heading = make("div", undefined, "pm-place-heading");
    const place = make("div", undefined, "pm-place-name");
    const location = result.location;
    if (location?.status === "available" && typeof location.name === "string" &&
        location.name.length > 0 && location.name.length <= 256) {
      place.append(make("strong", location.name, "pm-municipality"));
    }
    place.append(make("p", `${result.point.lat.toFixed(5)}, ${result.point.lon.toFixed(5)}`, "pm-coordinates"));
    const summary = make("div", undefined, "pm-terrain-summary");
    const values = make("div", undefined, "pm-summary-values");
    const geographic = result.terrain?.data_mode === "geographic_sources";
    const elevation = geographic ? result.terrain.elevation : null;
    const altitudeValue = elevation?.status === "available" && Number.isFinite(elevation.value_m)
      ? `${elevation.value_m.toFixed(1)} m` : "—";
    const altitude = make("div", undefined, "pm-summary-altitude");
    altitude.append(make("span", text("altitude")), make("strong", altitudeValue));
    // Source/depth/uncertainty are detailed under Terrain, not in the heading.
    const surface = geographic && Array.isArray(result.terrain.ph?.depths)
      ? result.terrain.ph.depths.find(row => row.depth_cm?.[0] === 0 && row.depth_cm?.[1] === 5) : null;
    const openland = result.terrain?.ph_openlandmap;
    const useOpenland = result.ecology?.ph_selection?.source === "openlandmap" || openland !== undefined;
    const phContext = useOpenland ? openland : surface;
    const estimate = useOpenland ? openland?.estimate : surface?.median;
    const phValue = ["available", "partial"].includes(phContext?.status) &&
      Number.isFinite(estimate) && estimate > 0 && estimate <= 14 ? `≈ ${estimate.toFixed(1)}` : "—";
    const ph = make("div", undefined, "pm-summary-ph");
    ph.append(make("span", text("ph_estimated"), "pm-ph-full-label"),
      make("span", "pH", "pm-ph-short-label"), make("strong", phValue));
    ph.querySelector(".pm-ph-short-label").setAttribute("aria-hidden", "true");
    ph.title = text("ph_comparison_help");
    if (openland?.lookup?.method === "nearest" && Number.isFinite(openland.lookup.distance_m)) {
      ph.append(make("small", `${text("ph_nearby")}: ${Math.round(openland.lookup.distance_m)} m`, "pm-ph-nearby"));
    }
    values.append(altitude, ph);
    const trees = make("div", undefined, "pm-summary-trees");
    trees.append(make("span", text("terrain"), "pm-summary-trees-label"));
    for (const name of new Set(contextNames("soil_tendencies"))) {
      const chip = make("span", name, "pm-tree-chip pm-soil-chip");
      chip.title = text("soil_tendencies_help");
      trees.append(chip);
    }
    const treeData = result.land_context?.trees;
    const names = treeData?.status === "available" && Array.isArray(treeData.items) && treeData.items.length <= 8
      ? treeData.items.map(item => {
        const candidates = item?.labels ? [item.labels[bridge.language()], item.scientific_name] : [item?.label, item?.scientific_name];
        return candidates.find(name => typeof name === "string" && name.trim() && name.length <= 128);
      }).filter(Boolean) : [];
    const terrainNames = [...names, ...contextNames("habitats")];
    if (terrainNames.length) {
      for (const name of new Set(terrainNames)) trees.append(make("span", name, "pm-tree-chip"));
    } else {
      const pending = !treeData || treeData.status === "not_connected";
      trees.append(make("span", text(pending ? "trees_pending" : "terrain_context_no_data"), "pm-tree-chip pm-tree-chip-muted"));
    }
    summary.append(values);
    heading.append(place, summary, trees);
    header.append(heading);
    if (["local", "worker"].includes(result.execution?.mode)) {
      const timing = `${text(result.execution.mode === "local" ? "execution_local_short" : "execution_worker")} · ${text("query_time")}: ${(elapsedMs/1000).toFixed(2)} s`;
      header.append(make("p", timing + (Number.isFinite(result.execution.compute_ms) ? ` · ${text("compute_time")}: ${(result.execution.compute_ms/1000).toFixed(2)} s` : ""), "pm-execution"));
    }
    if (result.ecology) {
      renderEcology(body, header);
    } else {
      const chart = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      chart.setAttribute("viewBox", "0 0 400 150");
      chart.setAttribute("class", "pm-chart");
      chart.setAttribute("role", "img");
      chart.setAttribute("aria-label", text("chart"));
      const xAt = (day) => 36 + day * 58;
      const yAt = (value) => 118 - value * 100;
      const chartText = (content, x, y, anchor = "start") => {
        const label = document.createElementNS(chart.namespaceURI, "text");
        label.textContent = content;
        label.setAttribute("x", x); label.setAttribute("y", y);
        label.setAttribute("font-size", "10"); label.setAttribute("fill", "#344a5a");
        label.setAttribute("text-anchor", anchor);
        chart.append(label);
      };
      for (const level of [0, 0.5, 1]) {
        chartText(`${level * 100}%`, 0, yAt(level) + 3);
        const grid = document.createElementNS(chart.namespaceURI, "line");
        grid.setAttribute("x1", "34"); grid.setAttribute("x2", "390");
        grid.setAttribute("y1", yAt(level)); grid.setAttribute("y2", yAt(level));
        grid.setAttribute("stroke", "#cfdae1"); chart.append(grid);
      }
      chartText(result.dates[0], 0, 144);
      chartText(result.dates.at(-1), 400, 144, "end");
      const selectedDay = document.createElementNS(chart.namespaceURI, "line");
      selectedDay.setAttribute("y1", "12"); selectedDay.setAttribute("y2", "122");
      selectedDay.setAttribute("stroke", "#687d8a"); selectedDay.setAttribute("stroke-dasharray", "3 3");
      chart.append(selectedDay);
      result.species.forEach((row, index) => {
        let points = [];
        const flush = () => {
          if (!points.length) return;
          const path = document.createElementNS(chart.namespaceURI, "polyline");
          path.setAttribute("points", points.join(" "));
          path.setAttribute("stroke", colors[index % colors.length]);
          path.setAttribute("fill", "none");
          path.setAttribute("stroke-width", "2");
          chart.append(path);
          points = [];
        };
        row.probabilities.forEach((value, day) => {
          if (value === null) { flush(); return; }
          const x = xAt(day);
          const y = yAt(value);
          points.push(`${x},${y}`);
          const dot = document.createElementNS(chart.namespaceURI, "circle");
          dot.setAttribute("cx", x); dot.setAttribute("cy", y); dot.setAttribute("r", "3");
          dot.setAttribute("fill", colors[index % colors.length]);
          chart.append(dot);
        });
        flush();
      });
      const dateLabel = calendarLabel();
      const select = make("select");
      select.ariaLabel = text("date");
      result.dates.forEach((day, i) => {
        const option = make("option", day);
        option.value = String(i);
        select.append(option);
      });
      select.value = String(dayIndex);
      dateLabel.append(select);
      const list = make("ul", undefined, "pm-species");
      const renderRows = () => {
        selectedDay.setAttribute("x1", xAt(dayIndex)); selectedDay.setAttribute("x2", xAt(dayIndex));
        list.replaceChildren();
        result.species.forEach((row, index) => {
          const item = make("li");
          const name = make("strong", text(row.label_key));
          name.style.color = colors[index % colors.length];
          const value = row.status === "no_model" ? text("no_model") : percent(row.probabilities[dayIndex]);
          item.append(name, make("span", value));
          const valid = row.probabilities.filter((v) => v !== null);
          if (valid.length) {
            const peak = Math.max(...valid);
            item.append(make("small", `${text("peak")}: ${percent(peak)} · ${result.dates[row.probabilities.indexOf(peak)]}`));
          }
          list.append(item);
        });
      };
      select.addEventListener("change", () => { dayIndex = Number(select.value); renderRows(); });
      renderRows();
      header.append(dateLabel);
      body.append(chart, list);
    }
    const terrainDetail = make("details", undefined, "pm-terrain");
    terrainDetail.append(make("summary", text("terrain")));
    const terrain = result.terrain;
    const missing = (state) => text(state === "unavailable" ? "terrain_unavailable" : "terrain_no_data");
    if (terrain?.data_mode === "geographic_sources") {
      terrainDetail.append(make("p", text(result.ecology ? "ecology_terrain_real" : "terrain_real"), "pm-terrain-note"));
      const elevation = terrain.elevation;
      const knownDEM = { dem_5m: "source_dem_icgc", dem_andorra_5m: "source_dem_andorra",
        dem_france_rge_alti_5m: "source_dem_france", ign_mdt25: "source_dem_ign" };
      const altitude = elevation?.status === "available" && Number.isFinite(elevation.value_m)
        ? `${elevation.value_m.toFixed(1)} m` : missing(elevation?.status);
      terrainDetail.append(make("p", `${text("altitude")}: ${altitude}`, "pm-altitude"));
      if (knownDEM[elevation?.source_id]) {
        terrainDetail.append(make("small", `${text(knownDEM[elevation.source_id])} · ${text("resolution")}: ${elevation.resolution_m} m`));
      }
      const ph = terrain.ph;
      terrainDetail.append(make("h3", text("soil_ph")));
      const phValue = value => Number.isFinite(value) && value > 0 && value <= 14 ? value.toFixed(1) : "—";
      const olm = terrain.ph_openlandmap;
      if (olm !== undefined) {
        terrainDetail.append(make("h4", text("ph_openlandmap_source")));
        const table = make("table", undefined, "pm-ph-openlandmap");
        const header = make("tr");
        for (const key of ["ph_estimated", "ph_lower", "ph_upper"]) {
          const th = make("th", text(key)); th.scope="col"; header.append(th);
        }
        const head = make("thead"); head.append(header); table.append(head);
        const body = make("tbody"), row = make("tr");
        row.append(make("td", phValue(olm.estimate)),make("td", phValue(olm.lower)),make("td", phValue(olm.upper)));
        body.append(row); table.append(body); terrainDetail.append(table);
        terrainDetail.append(make("p", text("ph_openlandmap_details"), "pm-terrain-note"));
        if (olm.lookup?.method === "nearest" && Number.isFinite(olm.lookup.distance_m)) {
          terrainDetail.append(make("p", `${text("ph_nearby")}: ${Math.round(olm.lookup.distance_m)} m`, "pm-ph-nearby"));
        }
        if (!["available","partial"].includes(olm.status)) terrainDetail.append(make("p",missing(olm.status)));
        terrainDetail.append(make("p",text("ph_comparison_help"),"pm-terrain-note"));
      }
      terrainDetail.append(make("h4", text("ph_soilgrids_source")));
      if (Array.isArray(ph?.depths) && ph.depths.length === 3) {
        const table = make("table", undefined, "pm-ph-table");
        const header = make("tr");
        for (const key of ["depth", "median", "ph_lower", "ph_upper"]) {
          const th = make("th", text(key)); th.scope = "col"; header.append(th);
        }
        const head = make("thead"); head.append(header); table.append(head);
        const body = make("tbody");
        for (const [i, depth] of ph.depths.entries()) {
          const row = make("tr");
          row.append(make("td", ["0–5 cm", "5–15 cm", "15–30 cm"][i]),
            make("td", phValue(depth.median)), make("td", phValue(depth.lower)),make("td",phValue(depth.upper)));
          body.append(row);
        }
        table.append(body); terrainDetail.append(table);
        if (ph.status !== "available") terrainDetail.append(make("p", missing(ph.status)));
      } else {
        terrainDetail.append(make("p", missing(ph?.status)));
      }
      if (ph?.source_id === "soilgrids_2_phh2o") {
        terrainDetail.append(make("small", text("ph_source")), make("p", text("ph_estimate"), "pm-terrain-note"));
      }
    } else {
      terrainDetail.append(make("p", terrain?.status === "not_connected" ? text("not_connected") : missing(terrain?.status)));
    }
    const weatherDetail = renderPointWeather(result.weather, text);
    const lithologies = contextNames("lithologies");
    const soilTendencies = contextNames("soil_tendencies");
    if (lithologies.length) terrainDetail.append(make("p", `${text("terrain_materials")}: ${lithologies.join(", ")}`, "pm-materials"));
    if (soilTendencies.length) {
      terrainDetail.append(make("p", `${text("soil_tendencies")}: ${soilTendencies.join(", ")}`, "pm-soil-tendencies"),
        make("p", text("soil_tendencies_help"), "pm-terrain-note"));
    }
    if (result.land_context) {
      for (const key of ["vegetation", "geology"]) {
        const row = result.land_context[key];
        terrainDetail.append(make("h3", text(`land_${key}`)));
        if (row?.status === "available") {
          terrainDetail.append(make("p", `${row.label || row.code} · ${text("land_code")}: ${row.code}`, `pm-land-${key}`));
        } else {
          const state = ["ambiguous", "resource_limit", "not_connected", "unavailable"].includes(row?.status) ? row.status : "no_data";
          terrainDetail.append(make("p", text(`land_${state}`), `pm-land-${key}`));
        }
        if (row?.source_id) terrainDetail.append(make("small", `ICGC · ${row.edition}`));
      }
      terrainDetail.append(make("p", text(result.ecology ? "ecology_land_note" : "land_descriptive"), "pm-terrain-note"));
    }
    body.append(terrainDetail, weatherDetail);
    popup = bridge.openPopup(lngLat, container);
    const ownPopup = popup;
    ownPopup.on("close", () => { if (popup === ownPopup) { popup = null; result = null; } });
  }

  function refreshLanguage() {
    banner.textContent = notice.textContent = text(result?.data_mode === "prediction" ? "prediction_experimental" : result?.ecology ? "ecology_prototype" : result ? "simulation" : initialNotice);
    if (!dialog.open) title.textContent = text("calculating");
    // Preserve the queried coordinate and date; only rebuild the small UI.
    if (popup && result) {
      const location = popup.getLngLat();
      const saved = result;
      const old = popup; popup = null; old.remove(); result = saved;
      showResult(location);
    }
  }
  function setEnabled(value) {
    if (enabled === value) return;
    enabled = value;
    if (enabled) {
      document.body.append(banner, dialog);
      map.on("click", query);
    } else {
      map.off("click", query);
      cancelQuery(); closePopup(); banner.remove(); dialog.remove();
    }
  }
  return { get enabled() { return enabled; }, setEnabled, refreshLanguage, cancelQuery };
}
