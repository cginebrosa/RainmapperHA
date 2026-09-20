/* Observed daily weather only. Local range selection never requests prediction. */
// Calendar days are formatted in UTC to avoid shifting them in browser time zones.
export function formatCalendarDate(day, language = "en", weekday = "long") {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day || "")) return "—";
  const date = new Date(`${day}T12:00:00Z`);
  if (!Number.isFinite(date.getTime())) return "—";
  const name = new Intl.DateTimeFormat(language, { weekday, timeZone: "UTC" }).format(date);
  return `${name} ${day.slice(8,10)}/${day.slice(5,7)}/${day.slice(2,4)}`;
}
function historyGraph(text, language) {
  const dateText = day => formatCalendarDate(day, language);
  const numeric = value => typeof value === "number" && Number.isFinite(value);
  const number = value => numeric(value) ? value.toFixed(1) : "—";
  const make = (tag, content, cls) => {
    const node = document.createElement(tag);
    if (content !== undefined) node.textContent = content;
    if (cls) node.className = cls;
    return node;
  };
  const colors = ["#087baa", "#b74765"];
  function graph(title, unit, days, curves, bars = false, domain = null, showLegend = true) {
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
    let min = domain ? domain[0] : bars ? Math.min(0, ...values) : Math.min(...values);
    let max = domain ? domain[1] : bars ? Math.max(0, ...values) : Math.max(...values);
    if (max <= min) { max = min + 1; if (!bars) min -= 1; }
    const xAt = i => 42 + i * 348 / Math.max(1, days.length - 1);
    const yAt = value => 110 - (value-min) / (max-min) * 94;
    for (const value of [min, (min+max)/2, max]) {
      el("line", { x1: 40, x2: 394, y1: yAt(value), y2: yAt(value), stroke: "#cbd7df" });
      el("text", { x: 0, y: yAt(value)+3, "font-size": 10, fill: "#344a5a" }, value.toFixed(1));
    }
    if (bars) el("line", {x1:40,x2:394,y1:yAt(0),y2:yAt(0),stroke:"#526678","stroke-width":1.5});
    curves.forEach((curve, index) => {
      if (Array.isArray(curve.lower) && Array.isArray(curve.upper)) {
        let band = [];
        const flushBand = () => {
          if (band.length) el("polygon", { points: [...band.map(([i,lo])=>`${xAt(i)},${yAt(lo)}`),
            ...band.slice().reverse().map(([i,,hi])=>`${xAt(i)},${yAt(hi)}`)].join(" "), fill:"#087baa", "fill-opacity":.14 });
          band=[];
        };
        curve.values.forEach((value,i)=>{
          if (numeric(value) && numeric(curve.lower[i]) && numeric(curve.upper[i])) band.push([i,curve.lower[i],curve.upper[i]]);
          else flushBand();
        });
        flushBand();
      }
      let points = [];
      const flush = () => {
        if (points.length) el("polyline", { points: points.join(" "), fill: "none", stroke: colors[index], "stroke-width": 2 });
        points = [];
      };
      curve.values.forEach((value, i) => {
        if (!numeric(value)) { flush(); return; }
        const x = xAt(i), y = yAt(value);
        if (bars) {
          const bar = el("rect", { x: x-2, y: Math.min(y,yAt(0)), width: Math.max(2,Math.min(8,300/days.length)), height: Math.abs(yAt(0)-y), fill: value < 0 ? "#b74765" : colors[index] });
          const label = document.createElementNS(svg.namespaceURI,"title"); label.textContent = `${dateText(days[i])}: ${number(value)} ${unit}`; bar.append(label);
        } else {
          points.push(`${x},${y}`); el("circle", { cx: x, cy: y, r: 1.7, fill: colors[index] });
        }
      });
      flush();
    });
    el("text", { x: 40, y: 132, "font-size": 10, fill: "#344a5a" }, dateText(days[0]));
    el("text", { x: 394, y: 132, "text-anchor": "end", "font-size": 10, fill: "#344a5a" }, dateText(days.at(-1)));
    figure.append(svg);
    const tooltip = make("div", undefined, "pm-chart-tooltip pm-history-tooltip");
    tooltip.hidden = true; tooltip.setAttribute("role", "status"); figure.append(tooltip);
    svg.tabIndex = 0;
    let selected = days.length - 1;
    function show(i) {
      selected = Math.max(0, Math.min(days.length-1, i));
      tooltip.replaceChildren(make("strong",dateText(days[selected])));
      for (const curve of curves) {
        const value = curve.values[selected];
        tooltip.append(make("div",`${curve.label}: ${curve.formatValue ? curve.formatValue(value,selected) : `${number(value)} ${unit}`}`));
      }
      tooltip.hidden = false;
    }
    const point = event => {
      const rect = svg.getBoundingClientRect();
      show(Math.round(((event.clientX-rect.left)/rect.width*400-42)/348*(days.length-1)));
    };
    svg.addEventListener("pointermove",point);
    svg.addEventListener("click",point);
    svg.addEventListener("pointerleave",()=>{tooltip.hidden=true;});
    svg.addEventListener("blur",()=>{tooltip.hidden=true;});
    svg.addEventListener("keydown",event=>{
      if (event.key === "Escape") tooltip.hidden=true;
      if (["ArrowLeft","ArrowRight","Home","End"].includes(event.key)) {
        event.preventDefault();
        show(event.key === "Home" ? 0 : event.key === "End" ? days.length-1 : selected+(event.key === "ArrowLeft" ? -1 : 1));
      }
    });
    if (showLegend) {
      const legend = make("p", undefined, "pm-weather-legend");
      const help = make("span", undefined, "pm-chart-tooltip pm-legend-tooltip");
      help.hidden = true; help.setAttribute("role", "tooltip");
      for (const [i, curve] of curves.entries()) {
        const item = make(curve.description ? "button" : "span", curve.label);
        item.style.color = colors[i]; legend.append(item);
        if (curve.description) {
          item.type = "button"; item.className = "pm-legend-help";
          item.setAttribute("aria-label", `${curve.label}: ${curve.description}`);
          const show = () => { help.textContent=curve.description; help.hidden=false; };
          item.addEventListener("pointerenter",show);
          item.addEventListener("pointerleave",()=>{help.hidden=true;});
          item.addEventListener("focus",show);
          item.addEventListener("click",show);
          item.addEventListener("blur",()=>{help.hidden=true;});
          item.addEventListener("keydown",e=>{if(e.key==="Escape") help.hidden=true;});
        }
      }
      if (curves.some(c=>c.description)) legend.append(help);
      figure.append(legend);
    }
    return figure;
  }
  return graph;
}

export function renderPointWeather(weather, text, language = "en") {
  const dateText = day => formatCalendarDate(day, language);
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
  const graph = historyGraph(text, language);
  function render() {
    const count = Number(select.value), days = dates.slice(-count);
    const series = Object.fromEntries(keys.map(key => [key, weather.series[key].slice(-count)]));
    body.replaceChildren(make("p", `${dateText(days[0])} — ${dateText(days.at(-1))}`, "pm-weather-dates"));
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
      const row = make("tr"); row.append(make("td",dateText(day)));
      for (const key of keys) row.append(make("td",number(series[key][i])));
      if (showWind) for (const key of ["avg_kmh","gust_kmh"]) row.append(make("td",number(wind[key][dates.length-count+i])));
      tbody.append(row);
    });
    table.append(tbody); scroll.append(table); records.append(scroll); body.append(records);
  }
  select.addEventListener("change",render); render();
  return detail;
}

// Separate from future IFF: the same completed historical dates as weather.
export function renderPointHydrology(weather, text, language = "en") {
  const make = (tag, content, cls) => {
    const node = document.createElement(tag);
    if (content !== undefined) node.textContent = content;
    if (cls) node.className = cls;
    return node;
  };
  const detail = make("details",undefined,"pm-hydrology");
  detail.append(make("summary",text("hydrology")));
  const water = weather?.water_balance, dates = weather?.dates;
  const valid = water?.data_mode === "estimated_water_balance" && Array.isArray(dates) && dates.length >= 7 && dates.length <= 60 &&
    dates.every((day,i)=>/^\d{4}-\d{2}-\d{2}$/.test(day) && Number.isFinite(Date.parse(day)) && (!i || Date.parse(day)-Date.parse(dates[i-1])===86400000)) &&
    ["balance_mm","smi_pct","smi_reasons"].every(key=>Array.isArray(water[key]) && water[key].length===dates.length) &&
    ["balance_mm","smi_pct"].every(key=>water[key].every(v=>v===null || (typeof v==="number" && Number.isFinite(v) && (key!=="smi_pct" || (v>=0 && v<=100)))));
  if (!valid) { detail.append(make("p",text("hydrology_unavailable"))); return detail; }
  detail.append(make("p",text("hydrology_method"),"pm-terrain-note"));
  if (water.history_start) detail.append(make("p",text("hydrology_history_start")
    .replace("{date}",formatCalendarDate(water.history_start,language)),"pm-terrain-note pm-hydrology-history-start"));
  if (["map_reference_water_v2", "regulated_pm_single_layer_v1"].includes(water.method_id)) {
    const methods = make("details",undefined,"pm-hydrology-assumptions");
    methods.append(make("summary",text("hydrology_assumptions")),make("p",text("hydrology_reference_model"),"pm-terrain-note"));
    const counts = key => water.et0_method_counts?.[key] ?? (water.et0_methods || []).filter(v=>v===key).length;
    methods.append(make("p",text("hydrology_et0_methods")
      .replace("{station}",counts("pm_station_wind")).replace("{estimated}",counts("pm_estimated_wind"))
      .replace("{fallback}",counts("hargreaves")),"pm-terrain-note"));
    for (const station of Object.values(water.wind_stations || {})) {
      if (typeof station.name === "string" && Number.isFinite(station.distance_km))
        methods.append(make("p",`${station.name} · ${station.distance_km.toFixed(1)} km${Number.isFinite(station.altitude_m) ? ` · ${Math.round(station.altitude_m)} m` : ""}`,"pm-terrain-note"));
    }
    detail.append(methods);
  }
  const hasCapacity = typeof water.capacity_mm === "number" && Number.isFinite(water.capacity_mm) && water.capacity_mm > 0;
  // One mm of water over one square metre is one litre. Missing SMI stays missing.
  const reserve = value => typeof value === "number" && hasCapacity ? (value * water.capacity_mm / 100).toFixed(1) : "—";
  const percent = value => typeof value === "number" ? value.toFixed(1) : "—";
  if (hasCapacity) {
    detail.append(make("p",text("hydrology_capacity").replace("{amount}",water.capacity_mm.toFixed(1)),"pm-terrain-note"));
  }
  const range = make("label",text("weather_period"));
  const select = make("select",undefined,"pm-hydrology-range"); select.ariaLabel=text("weather_period");
  for (const days of [7,15,30,60].filter(d=>d<=dates.length)) {
    const option=make("option",text("weather_days").replace("{days}",days));option.value=String(days);select.append(option);
  }
  select.value=String(Math.min(30,dates.length));range.append(select);detail.append(range);
  const body=make("div");detail.append(body);
  const graph=historyGraph(text,language);
  function render() {
    const count=Number(select.value), days=dates.slice(-count);
    const bounds = ["smi_low_pct","smi_high_pct"].map(key => Array.isArray(water[key]) && water[key].length===dates.length
      ? water[key].slice(-count).map(v=>typeof v==="number" && Number.isFinite(v) && v>=0 && v<=100 ? v : null) : []);
    body.replaceChildren(make("p",`${formatCalendarDate(days[0],language)} — ${formatCalendarDate(days.at(-1),language)}`,"pm-weather-dates"));
    const balance=graph(text("hydrology_balance"),"mm",days,[{label:text("hydrology_balance"),values:water.balance_mm.slice(-count)}],true,null,false);
    balance.classList.add("pm-hydrology-balance");
    const etMethods = water.et0_method_counts ? Object.keys(water.et0_method_counts).filter(k=>water.et0_method_counts[k]>0) : water.et0_methods || [];
    const hasPM = etMethods.some(m=>m.startsWith("pm_")), hasHS = etMethods.includes("hargreaves");
    const curves=[{label:text("hydrology_smi_regulated"),description:text("hydrology_regulated_help") + " " + text(hasPM ? (hasHS ? "hydrology_smi_mixed" : "hydrology_smi_pm") : "hydrology_smi_hs"),values:water.smi_pct.slice(-count),lower:bounds[0],upper:bounds[1],
      formatValue: (value,i) => `${percent(value)} %${hasCapacity ? ` · ${reserve(value)} L/m²` : ""}${
        typeof bounds[0][i]==="number" && typeof bounds[1][i]==="number" ? ` · ${text("hydrology_sensitivity_short")}: ${percent(bounds[0][i])}–${percent(bounds[1][i])} %` : ""}`}];
    if (Array.isArray(water.smi_legacy_pct) && water.smi_legacy_pct.length===dates.length) curves.push({
      label:text("hydrology_smi_simple"),description:text("hydrology_simple_help"),
      values:water.smi_legacy_pct.slice(-count).map(v=>typeof v==="number" && Number.isFinite(v) && v>=0 && v<=100 ? v : null),
      formatValue:value=>`${percent(value)} %${hasCapacity ? ` · ${reserve(value)} L/m²` : ""}`
    });
    const smi=graph(text("hydrology_smi"),"%",days,curves,false,[0,100],true);
    smi.classList.add("pm-hydrology-smi");
    if (hasCapacity) smi.append(make("p",text("hydrology_reserve")
      .replace("{date}",formatCalendarDate(days.at(-1),language))
      .replace("{percent}",percent(water.smi_pct.at(-1)))
      .replace("{amount}",reserve(water.smi_pct.at(-1))),"pm-terrain-note pm-hydrology-reserve"));
    body.append(smi,balance);
    if (curves.length===2) smi.append(make("p",text("hydrology_comparison"),"pm-terrain-note"));
    if (["map_reference_water_v2", "regulated_pm_single_layer_v1"].includes(water.method_id)) body.append(make("p",text("hydrology_sensitivity"),"pm-terrain-note"));
    const known = new Set(["soil_unavailable","inputs_incomplete","spinup_incomplete","not_converged"]);
    for (const reason of new Set(water.smi_reasons.slice(-count))) {
      if (known.has(reason)) body.append(make("p",text(`hydrology_${reason}`),"pm-terrain-note"));
    }
    body.append(make("p",text("hydrology_limits"),"pm-terrain-note"));
  }
  select.addEventListener("change",render);render();
  return detail;
}
