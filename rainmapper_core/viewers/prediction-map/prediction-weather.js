/* Observed daily weather only. Local range selection never requests prediction. */
export function renderPointWeather(weather, text) {
  const make = (tag, content, cls) => {
    const node = document.createElement(tag);
    if (content !== undefined) node.textContent = content;
    if (cls) node.className = cls;
    return node;
  };
  const format = (key, values) => text(key).replace(/\{(\w+)\}/g, (_, key) => values[key] ?? "—");
  const detail = make("details", undefined, "pm-weather");
  detail.append(make("summary", text("weather")));
  const numeric = value => typeof value === "number" && Number.isFinite(value);
  const number = value => numeric(value) ? value.toFixed(1) : "—";
  const keys = ["rain_mm", "temp_min_c", "temp_max_c", "humidity_min_pct", "humidity_max_pct"];
  const dates = weather?.dates;
  const valid = weather?.data_mode === "observed_idw" && Array.isArray(dates) && dates.length >= 7 && dates.length <= 60 &&
    dates.every((day, i) => typeof day === "string" && /^\d{4}-\d{2}-\d{2}$/.test(day) &&
      Number.isFinite(Date.parse(day)) && (!i || Date.parse(day)-Date.parse(dates[i-1]) === 86400000)) &&
    keys.every(key => Array.isArray(weather.series?.[key]) && weather.series[key].length === dates.length &&
      weather.series[key].every(value => value === null || numeric(value)));
  if (!valid) {
    detail.append(make("p", text(weather?.status === "not_connected" ? "not_connected" : "weather_unavailable")));
    return detail;
  }
  detail.append(make("p", format("weather_method", { radius: weather.radius_km }), "pm-terrain-note"));
  const range = make("label", text("weather_period"));
  const select = make("select", undefined, "pm-weather-range");
  select.ariaLabel = text("weather_period");
  for (const days of [7, 15, 30, 60].filter(days => days <= dates.length)) {
    const option = make("option", format("weather_days", { days })); option.value = String(days); select.append(option);
  }
  select.value = String(Math.min(30, dates.length));
  range.append(select); detail.append(range);
  const body = make("div"); detail.append(body);
  const colors = ["#087baa", "#b74765"];
  function graph(title, unit, days, curves, bars = false) {
    const figure = make("figure", undefined, "pm-weather-figure");
    figure.append(make("figcaption", `${title} · ${unit}`));
    const values = curves.flatMap(curve => curve.values).filter(numeric);
    if (!values.length) { figure.append(make("p", text("weather_no_data"))); return figure; }
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 400 138"); svg.setAttribute("role", "img"); svg.setAttribute("aria-label", title);
    const el = (tag, attrs, content) => {
      const node = document.createElementNS(svg.namespaceURI, tag);
      for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
      if (content !== undefined) node.textContent = content;
      svg.append(node); return node;
    };
    let min = bars ? 0 : Math.min(...values), max = Math.max(...values);
    if (max <= min) { max = min + 1; if (!bars) min -= 1; }
    const xAt = i => 42 + i * 348 / Math.max(1, days.length - 1);
    const yAt = value => 110 - (value-min) / (max-min) * 94;
    for (const value of [min, (min+max)/2, max]) {
      el("line", { x1: 40, x2: 394, y1: yAt(value), y2: yAt(value), stroke: "#cbd7df" });
      el("text", { x: 0, y: yAt(value)+3, "font-size": 10, fill: "#344a5a" }, value.toFixed(1));
    }
    curves.forEach((curve, index) => {
      let points = [];
      const flush = () => {
        if (points.length) el("polyline", { points: points.join(" "), fill: "none", stroke: colors[index], "stroke-width": 2 });
        points = [];
      };
      curve.values.forEach((value, i) => {
        if (!numeric(value)) { flush(); return; }
        const x = xAt(i), y = yAt(value);
        if (bars) {
          const bar = el("rect", { x: x-2, y, width: Math.max(2,Math.min(8,300/days.length)), height: Math.max(1,110-y), fill: colors[index] });
          const label = document.createElementNS(svg.namespaceURI,"title"); label.textContent = `${days[i]}: ${number(value)} ${unit}`; bar.append(label);
        } else {
          points.push(`${x},${y}`); el("circle", { cx: x, cy: y, r: 1.7, fill: colors[index] });
        }
      });
      flush();
    });
    el("text", { x: 40, y: 132, "font-size": 10, fill: "#344a5a" }, days[0]);
    el("text", { x: 394, y: 132, "text-anchor": "end", "font-size": 10, fill: "#344a5a" }, days.at(-1));
    figure.append(svg);
    const legend = make("p", undefined, "pm-weather-legend");
    for (const [i, curve] of curves.entries()) {
      const item = make("span", curve.label); item.style.color = colors[i]; legend.append(item);
    }
    figure.append(legend);
    return figure;
  }
  function render() {
    const count = Number(select.value), days = dates.slice(-count);
    const series = Object.fromEntries(keys.map(key => [key, weather.series[key].slice(-count)]));
    body.replaceChildren(make("p", `${days[0]} — ${days.at(-1)}`, "pm-weather-dates"));
    const rain = series.rain_mm.filter(numeric);
    body.append(make("p", format("weather_rain_sum", { amount: rain.length ? number(rain.reduce((a,b) => a+b,0)) : "—", available: rain.length, days: count }), "pm-weather-total"));
    body.append(graph(text("rain"), "mm", days, [{ label: text("rain"), values: series.rain_mm }], true));
    body.append(graph(text("temperature"), "°C", days, [{ label: text("minimum"), values: series.temp_min_c }, { label: text("maximum"), values: series.temp_max_c }]));
    body.append(graph(text("humidity"), "%", days, [{ label: text("minimum"), values: series.humidity_min_pct }, { label: text("maximum"), values: series.humidity_max_pct }]));
    const wind = weather.wind;
    const validWind = wind && ["avg_kmh", "gust_kmh"].every(key => Array.isArray(wind[key]) && wind[key].length === dates.length &&
      wind[key].every(value => value === null || (numeric(value) && value >= 0)));
    const showWind = validWind && [...wind.avg_kmh.slice(-count), ...wind.gust_kmh.slice(-count)].some(numeric);
    if (showWind) {
      const figure = graph(text("wind"), "km/h", days, [{ label: text("wind_average"), values: wind.avg_kmh.slice(-count) }, { label: text("wind_gust"), values: wind.gust_kmh.slice(-count) }]);
      figure.classList.add("pm-weather-wind");
      figure.append(make("p", format("wind_station", { name: wind.station_name, distance: number(wind.distance_km) }), "pm-terrain-note"));
      body.append(figure);
    }
    const quality = make("p", format("weather_sources", { sources: (weather.sources || []).join(", ") || "—", count: weather.nearby_stations }), "pm-terrain-note");
    body.append(quality, make("p", text("weather_gaps"), "pm-terrain-note"));
    const imputed = (weather.rain_imputed_zero_counts || []).slice(-count).reduce((sum,value) => sum+(Number(value)||0),0);
    if (imputed) body.append(make("p", format("weather_imputed", { count: imputed }), "pm-terrain-note"));
    const records = make("details", undefined, "pm-weather-records");
    records.append(make("summary", text("weather_records")));
    const scroll = make("div", undefined, "pm-weather-table-scroll");
    const table = make("table");
    const header = make("tr");
    for (const title of [text("date"),`${text("rain")} mm`,`${text("minimum")} °C`,`${text("maximum")} °C`,`${text("minimum")} %`,`${text("maximum")} %`,
      ...(showWind ? [`${text("wind_average")} km/h`,`${text("wind_gust")} km/h`] : [])]) {
      const th = make("th",title); th.scope="col"; header.append(th);
    }
    const head = make("thead"); head.append(header); table.append(head);
    const tbody = make("tbody");
    days.forEach((day,i) => {
      const row = make("tr"); row.append(make("td",day));
      for (const key of keys) row.append(make("td",number(series[key][i])));
      if (showWind) for (const key of ["avg_kmh","gust_kmh"]) row.append(make("td",number(wind[key][dates.length-count+i])));
      tbody.append(row);
    });
    table.append(tbody); scroll.append(table); records.append(scroll); body.append(records);
  }
  select.addEventListener("change",render); render();
  return detail;
}
