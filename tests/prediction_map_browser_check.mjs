// Real shared viewer + MapLibre, synthetic station/background/API, isolated Chrome.
// Usage: node tests/prediction_map_browser_check.mjs /path/maplibre.js /path/maplibre.css
// Add --preview to keep a loopback-only manual preview with local PublicData.
import assert from "node:assert/strict";
import { spawn, execFileSync } from "node:child_process";
import { createServer } from "node:http";
import { startPreviewReader } from "./prediction_map_preview_reader.mjs";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const chromePath = process.env.RAINMAPPER_TEST_CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const [library, libraryCSS] = process.argv.slice(2);
const preview = process.argv.includes("--preview");
const argument = (name) => { const i = process.argv.indexOf(name); return i < 0 ? undefined : process.argv[i + 1]; };
const municipalDataset = argument("--municipalities");
const terrainIndex = argument("--terrain-index");
const landCover = argument("--land-cover"), geology = argument("--geology");
const geographyUnavailable = { location: { status: "unavailable" }, terrain: { status: "unavailable" } };
if (argument("--profiles")) geographyUnavailable.ecology = {status:"unavailable", species:[]};
let geographyLookup = async () => ({ location: { status: "not_connected" }, terrain: { status: "not_connected" } });
if (preview && (municipalDataset || terrainIndex || landCover || geology || argument("--forest-index") || argument("--openlandmap-ph"))) {
  const python = argument("--geography-python") || argument("--municipalities-python");
  const edition = argument("--municipalities-edition");
  if (!python || (municipalDataset && !edition)) throw Error("Geography preview requires a GDAL Python interpreter and municipality edition when used.");
  const readerArgs = [path.join(root, "scripts/prediction-map-local-geography.py")];
  if (landCover) readerArgs.push("--land-cover", landCover);
  if (geology) readerArgs.push("--geology", geology);
  for (const flag of ["--land-cover-parts", "--geology-parts", "--forest-index", "--forest-catalogs",
                      "--profiles", "--ecology-catalogs", "--gis-mappings", "--openlandmap-ph", "--ecology-ph-source"]) {
    if (argument(flag)) readerArgs.push(flag, argument(flag));
  }
  if (municipalDataset) readerArgs.push("--municipalities", municipalDataset, "--municipalities-edition", edition);
  if (terrainIndex) {
    readerArgs.push("--terrain-index", terrainIndex);
    for (const key of ["--soil-root", "--dem-root", "--regional-root"]) {
      if (!argument(key)) throw Error(`Missing ${key}`);
      readerArgs.push(key, argument(key));
    }
  }
  geographyLookup = startPreviewReader(python, readerArgs, root, geographyUnavailable);
}
let modelLookup = null;
if (preview && argument("--models-root")) {
  const args=[path.join(root,"scripts/prediction-map-local-model.py")];
  for (const [flag,value] of [["--models-root",argument("--models-root")],
      ["--registry-path",argument("--model-registry")],["--profiles-path",argument("--profiles")],
      ["--data-root",argument("--weather-data")],["--stations-file",argument("--weather-stations")]]) {
    if (!value) throw Error(`Missing model input ${flag}`);
    args.push(flag,value);
  }
  modelLookup = startPreviewReader(argument("--model-python") || path.join(root,".venv/bin/python"),args,root,
    {data_mode:"prediction",species:[],model_status:"unavailable",provenance:{scientifically_validated:false}},90000);
}
const weatherData = argument("--weather-data");
let weatherLookup = async () => ({ weather: { status: "not_connected" } });
if (preview && weatherData) {
  if (!argument("--weather-stations")) throw Error("Missing --weather-stations");
  weatherLookup = startPreviewReader(argument("--weather-python") || path.join(root,".venv/bin/python"),
    [path.join(root,"scripts/prediction-map-local-weather.py"),"--data-root",weatherData,"--stations-file",argument("--weather-stations")],
    root, { weather: { status: "unavailable" } });
}
if (!library || !libraryCSS) throw Error("Provide the locally downloaded MapLibre 4.7.1 JS and CSS paths.");
await fs.access(chromePath);
const profile = await fs.mkdtemp(path.join(os.tmpdir(), "prediction-map-browser-"));
// Preview preferences are isolated from real HA users/devices and scientific data.
const previewSettingsPath = preview ? path.join(os.tmpdir(), "rainmapper-prediction-map-preview-settings.json") : null;
let deviceSettings = {};
if (previewSettingsPath) {
  try {
    if ((await fs.stat(previewSettingsPath)).size > 65536) throw Error("Preview settings too large");
    deviceSettings = JSON.parse(await fs.readFile(previewSettingsPath,"utf8"));
  } catch (error) { if (error.code !== "ENOENT") throw error; }
}
let settingsSaves = 0;
const labels = Object.fromEntries(Object.entries(JSON.parse(await fs.readFile(path.join(root, "mushroom-data/mushroom_labels.json"))))
  .filter(([k]) => k.startsWith("ui.prediction_map_")).map(([k, v]) => [k.replace("ui.prediction_map_", ""), v]));
const example = JSON.parse(execFileSync(path.join(root, ".venv/bin/python"), ["-c", `import json
from rainmapper_core.mushroom_prediction_map import demo_result
print(json.dumps(demo_result(dict(contract='prediction_map_point_v1',request_id='browser_test',point=dict(lat=42,lon=1.9),start_date='2026-09-12',horizon_days=7,history_days=30,species_ids=[]))))`], { cwd: root }));
const base = path.join(root, "rainmapper_core/viewers/maplibre-viewer");
const extension = path.join(root, "rainmapper_core/viewers/prediction-map");
let predictionAllowed = true;
let role = "admin", calls = 0, delay = 0, failure = false, richTerrain = true, lastExecution = null;
let compactMobileFixture = false;
let lastCalendar = null, lastStartDate = null;
let busyWorker = false;
let unavailableWorker = false, unavailableLocal = false;
const executionRequests = [];
let ecologyFixture = null;
let modelFixture = null;
const asyncQueries = new Map();
// Manual preview measures actual reader/transport time; no artificial delay.
const station = { type: "Feature", geometry: { type: "Point", coordinates: [1.9, 42] },
  properties: { Name: "TEST STATION", Station: "TEST STATION", Code: "TEST", Source: "Meteocat",
    rain_mm: 20, Total: 20, Rain: 20, Name_Original: "TEST STATION", temp_max_c: 20, temp_min_c: 10 } };
const server = createServer(async (req, res) => {
  try {
    if (preview && req.headers.host !== `127.0.0.1:${server.address().port}`) {
      res.writeHead(403); res.end(); return;
    }
    const url = new URL(req.url, "http://localhost");
    const name = url.pathname.split("/").at(-1);
    const send = (data, type = "application/json", status = 200) => { res.writeHead(status, { "Content-Type": type, "Cache-Control": "no-store" }); res.end(typeof data === "string" || Buffer.isBuffer(data) ? data : JSON.stringify(data)); };
    const queryPath = url.pathname.match(/\/queries\/(browser_async_\d+)(\/cancel)?$/);
    if (queryPath) {
      const job = asyncQueries.get(queryPath[1]);
      if (!job) return send({error:"not_found"},"application/json",404);
      if (queryPath[2]) { job.cancelled=true; return send({state:"cancelled"}); }
      if (job.cancelled) return send({error:"cancelled"},"application/json",409);
      if (performance.now() < job.ready) return send({state:"queued"},"application/json",202);
      return send(job.response);
    }
    if (name === "maplibre.js") return send(await fs.readFile(library), "application/javascript");
    if (name === "maplibre.css") return send(await fs.readFile(libraryCSS), "text/css");
    if (url.pathname.startsWith("/auth/")) {
      if (name === "device-settings") {
        if (req.method === "POST") {
          const chunks=[]; let size=0;
          for await (const chunk of req) { size+=chunk.length; if (size>32768) return send({},"application/json",413); chunks.push(chunk); }
          const values=JSON.parse(Buffer.concat(chunks)).settings;
          const previous=deviceSettings.prediction_execution;
          const previousCalendar=deviceSettings.prediction_timezone;
          deviceSettings={...values};
          if (!["local","worker"].includes(deviceSettings.prediction_execution)) {
            delete deviceSettings.prediction_execution;
            if (previous) deviceSettings.prediction_execution=previous;
          }
          if (!deviceSettings.prediction_timezone && previousCalendar) deviceSettings.prediction_timezone=previousCalendar;
          if (previewSettingsPath) await fs.writeFile(previewSettingsPath,JSON.stringify(deviceSettings),{mode:0o600});
          settingsSaves++;
        }
        return send({ ok: true, settings: deviceSettings });
      }
      return send({ ok: true, user: { username: preview ? "preview" : "test", role, can_use_heatmap: true, can_use_layer_metrics: true, can_use_estimated_field: true, can_use_prediction_map: predictionAllowed } });
    }
    if (name === "capabilities") return send({ can_use_prediction_map: predictionAllowed, admin_only: false, data_mode:preview ? "simulation" : "prediction", executors:{local:true,worker:!preview} }, "application/json", predictionAllowed ? 200 : 403);
    if (name === "demo" || name === "queries") {
      calls++;
      const chunks = []; let size = 0;
      for await (const chunk of req) {
        size += chunk.length;
        if (size > 32768) return send({ error: "request_too_large" }, "application/json", 413);
        chunks.push(chunk);
      }
      const query = JSON.parse(Buffer.concat(chunks));
      lastExecution = query.execution || "local";
      executionRequests.push(query);
      lastCalendar = query.calendar_timezone;
      lastStartDate = query.start_date;
      if (busyWorker && lastExecution === "worker") return send({error:"worker_busy"},"application/json",503);
      if ((unavailableWorker && lastExecution === "worker") || (unavailableLocal && lastExecution === "local")) return send({error:"executor_unavailable"},"application/json",503);
      if (!["local","worker"].includes(lastExecution)) return send({error:"invalid_execution"},"application/json",400);
      if (preview && lastExecution === "worker") return send({error:"executor_unavailable"},"application/json",503);
      const started = performance.now();
      const response = { ...example, request_id: query.request_id, point: query.point };
      if (preview) {
        const start = new Date(`${query.start_date}T00:00:00Z`);
        if (!Number.isFinite(start.getTime())) return send({ error: "invalid_date" }, "application/json", 400);
        response.dates = Array.from({ length: 7 }, (_, i) => new Date(start.getTime() + i * 86400000).toISOString().slice(0, 10));
        Object.assign(response, await geographyLookup({...query.point, start_date:query.start_date, horizon_days:query.horizon_days, species_ids:query.species_ids, model_inputs:!!modelLookup}));
        if (modelLookup) {
          Object.assign(response, {data_mode:'prediction', species:[], provenance:{engine:'existing_python_predictor',scientifically_validated:false}});
          if (response.ecology?.status === 'available' && !response.ecology.abstention_reason &&
              response.ecology.species.some(row => row.status === 'compatible' && row.daily_season_phases?.some(p => ['main','secondary'].includes(p)) && (!query.species_ids?.length || query.species_ids.includes(row.species_id)))) {
            Object.assign(response, await modelLookup({request:query,geography:response}));
          }
        }
        delete response.model_soil_water;
        const end = new Date(start.getTime()-86400000).toISOString().slice(0,10);
        Object.assign(response, await weatherLookup({ ...query.point, altitude_m: response.terrain?.elevation?.value_m,
          end_day: end, days: query.history_days, calendar_timezone: query.calendar_timezone }));
      } else {
        const weatherDates = Array.from({length:60},(_,i)=>new Date(Date.UTC(2026,6,14+i)).toISOString().slice(0,10));
        const values = value => weatherDates.map((_,i)=>i===57 ? null : value);
        response.weather = { status:"partial", data_mode:"observed_idw", dates:weatherDates,
          radius_km:15, sources:["meteocat"], nearby_stations:2,
          series:{rain_mm:values(2),temp_min_c:values(10),temp_max_c:values(20),humidity_min_pct:values(40),humidity_max_pct:values(80)},
          ...(richTerrain ? {wind:{station_name:"Viento <b>literal</b>",distance_km:2,avg_kmh:values(0),gust_kmh:values(12)}} : {}) };
        response.location = calls === 1 ? { status: "available", name: "Municipio de prueba <b>literal</b>" } : { status: "ambiguous" };
        if (compactMobileFixture) response.location = {status:"available",name:"La Quar"};
        response.land_context = {
          trees: richTerrain ? {status:"available",items:[
            {label:"Encinas <b>literal</b>",scientific_name:"Quercus ilex",labels:{es:"Encinas <b>literal</b>",en:"Holm oak",ca:"Alzina"}},
            {label:"Robles",scientific_name:"Quercus",labels:{es:"Robles",ca:"Roures"}},
            {label:"Pinos"}]} : {status:"not_connected"},
          vegetation: richTerrain ? {status:"available",code:"221",label:"Bosc <b>literal</b>",source_id:"icgc_cobertes_2024",edition:"2024"} : {status:"resource_limit"},
          geology: richTerrain ? {status:"available",code:"test",label:"Geologia de prueba",source_id:"geology_50000",edition:"2024-12"} : {status:"not_covered"}
        };
        response.terrain = richTerrain ? { status: "partial", data_mode: "geographic_sources",
          elevation: { status: "available", value_m: 765.3, resolution_m: 5, source_id: "dem_5m" },
          ph_openlandmap: {status:"available",source_id:"openlandmap_soildb_ph",estimate:6.7,lower:5.6,upper:7.9,
            depth_cm:[0,30],interval_probability:0.68,lookup:{method:"nearest",distance_m:84}},
          ph: { status: "partial", resolution_m: 250, source_id: "soilgrids_2_phh2o", depths: [
            { depth_cm: [0, 5], median: 6.3, lower: 4.3, upper: 8, status: "available" },
            { depth_cm: [5, 15], median: null, lower: null, upper: null, status: "no_data" },
            { depth_cm: [15, 30], median: 6.4, lower: null, upper: 8, status: "partial" }] } }
          : { status: "no_data", data_mode: "geographic_sources", elevation: { status: "not_covered" }, ph: { status: "no_data" } };
      }
      if (!preview && ecologyFixture) response.ecology = {...ecologyFixture, dates:response.dates};
      if (!preview && modelFixture) Object.assign(response,modelFixture);
      if (compactMobileFixture) {
        response.terrain.ph_openlandmap.lookup={method:'cell'};
        response.land_context.trees.items[0].labels={es:'Encina',ca:'Alzina',en:'Holm oak'};
        response.ecology.mapped_context={soil_tendencies:[
          {id:'calcareous',label:{es:'Calizo',ca:'Calcari',en:'Calcareous'}},
          {id:'sandy',label:{es:'Arenoso',ca:'Sorrenc',en:'Sandy'}}]};
      }
      response.execution = {mode:lastExecution,compute_ms:performance.now()-started};
      response.calendar_timezone = query.calendar_timezone;
      if (!preview && lastExecution === "worker" && !failure) {
        const id = `browser_async_${calls}`;
        asyncQueries.set(id,{response,ready:performance.now()+delay});
        return send({query_id:id,state:"queued"},"application/json",202);
      }
      return setTimeout(() => send(response, "application/json", failure ? 503 : 200), delay);
    }
    if (name === "config.js") return send(`window.RAINMAPPER_CONFIG=${JSON.stringify({ authRequired: true, authBase: "/auth", dataBase: "data/", predictionMap: { apiBase: "/api/mushrooms/prediction-map", contract: "prediction_map_point_v1", labels } })}`, "application/javascript");
    if (name === "index.html") {
      const page = (await fs.readFile(path.join(base, name), "utf8"))
        .replace("https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css", "/maplibre.css")
        .replace("https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js", "/maplibre.js");
      const setup = `<script>
        localStorage.setItem('rainmapperMaplibreAuth',JSON.stringify({username:'test',role:'${role}',sessionToken:'isolated-test-token',deviceId:'isolated-test-device'}));
        ${preview ? "" : `const NativeMap=maplibregl.Map;
        const blank={version:8,sources:{},layers:[{id:'blank',type:'background',paint:{'background-color':'#d9e6ec'}}]};
        maplibregl.Map=class extends NativeMap {constructor(options){super({...options,style:blank,center:[1.9,42],zoom:9});}setStyle(){return super.setStyle(blank);}};`}
      </script>`;
      let composed = page.replace('<script src="config.js', setup + '<script src="config.js');
      composed = composed.replace("</body>", '<script src="prediction-bootstrap.js"></script></body>');
      return send(composed, "text/html");
    }
    if (url.pathname.includes("/data/")) {
      if (preview && /^(01|07|14|21|30|60|90)d\.geojson$/.test(name)) {
        return send(await fs.readFile(path.join(root, "docker-data/PublicData", name)));
      }
      return send(name.endsWith(".geojson") ? { type: "FeatureCollection", features: [station] } : {});
    }
    if (["app.js", "style.css", "translations.json"].includes(name)) return send(await fs.readFile(path.join(base, name)), name.endsWith(".css") ? "text/css" : name.endsWith(".json") ? "application/json" : "application/javascript");
    if (["prediction-bootstrap.js", "prediction-mode.js", "prediction-mode.css", "prediction-weather.js"].includes(name)) return send(await fs.readFile(path.join(extension, name)), name.endsWith(".css") ? "text/css" : "application/javascript");
    return send({}, "application/json", 404);
  } catch (error) { res.writeHead(500); res.end(String(error)); }
});
await new Promise(resolve => server.listen(preview ? Number(argument("--port") || 0) : 0, "127.0.0.1", resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
if (preview) {
  console.log(JSON.stringify({ preview: origin + "/protected/prediction-map/index.html", weather: "docker-data/PublicData (read-only)", observed_weather: weatherData || "not_connected", prediction: modelLookup ? "existing_python_predictor" : "simulated", municipalities: municipalDataset || "not_connected", terrain: terrainIndex || "not_connected", demo_delay_ms: delay }));
  const stop = () => { server.closeAllConnections(); server.close(() => process.exit(0)); };
  process.on("SIGINT", stop); process.on("SIGTERM", stop);
  await new Promise(() => {});
}
const chrome = spawn(chromePath, ["--headless", "--no-first-run", "--disable-background-networking", "--disable-component-update",
  "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--remote-debugging-port=0", `--user-data-dir=${profile}`, "about:blank"], { stdio: "ignore" });
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
let ws, serial = 0; const waiting = new Map(); const errors = [];
const watchdog = setTimeout(() => { console.error("Browser timeout", errors); chrome.kill("SIGTERM"); server.close(); process.exit(2); }, 55000);
function send(method, params = {}) { const id = ++serial; return new Promise((resolve, reject) => { waiting.set(id, { resolve, reject }); ws.send(JSON.stringify({ id, method, params })); }); }
async function evaluate(expression) {
  const answer = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
  if (answer.exceptionDetails) throw Error(JSON.stringify(answer.exceptionDetails));
  return answer.result.value;
}
async function until(expression) {
  for (let i = 0; i < 80; i++) { if (await evaluate(expression)) return; await pause(75); }
  throw Error(`Condition failed: ${expression}; ${JSON.stringify(errors)}`);
}
async function clickAt(lon, lat) {
  const point = await evaluate(`(()=>{const p=map.project([${lon},${lat}]);const r=map.getCanvas().getBoundingClientRect();return {x:r.left+p.x,y:r.top+p.y}})()`);
  for (const type of ["mouseMoved", "mousePressed", "mouseReleased"]) await send("Input.dispatchMouseEvent", { type, ...point, button: type === "mouseMoved" ? "none" : "left", clickCount: type === "mouseMoved" ? 0 : 1 });
}
async function checkFixedHeader() {
  const state = await evaluate(`(()=>{
    const header=document.querySelector('.pm-result-header'), body=document.querySelector('.pm-result-body'),
      date=header.querySelector('select'), popup=document.querySelector('.pm-result');
    body.scrollTop=0;
    const before=header.getBoundingClientRect();
    body.scrollTop=body.scrollHeight;
    const after=header.getBoundingClientRect(), d=date.getBoundingClientRect(), r=popup.getBoundingClientRect();
    const result={fixed:before.top===after.top && before.bottom===after.bottom,
      dateVisible:d.top>=r.top && d.bottom<=r.bottom,
      scrolled:body.scrollTop>0, fits:body.scrollHeight<=body.clientHeight, bodyHeight:body.clientHeight, outerScroll:popup.scrollTop};
    body.scrollTop=0;
    return result;
  })()`);
  assert.ok(state.fixed && state.dateVisible && (state.scrolled || state.fits), JSON.stringify(state));
  assert.ok(state.bodyHeight >= 80, JSON.stringify(state));
  assert.equal(state.outerScroll, 0);
}
try {
  let port;
  for (let i = 0; i < 80; i++) { try { port = (await fs.readFile(path.join(profile, "DevToolsActivePort"), "utf8")).split("\n")[0]; break; } catch { await pause(75); } }
  if (!port) throw Error("Chrome did not start");
  const pages = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  ws = new WebSocket(pages.find(p => p.type === "page").webSocketDebuggerUrl);
  await new Promise(resolve => ws.addEventListener("open", resolve, { once: true }));
  ws.addEventListener("message", event => { const message = JSON.parse(event.data); if (message.id) { const task = waiting.get(message.id); waiting.delete(message.id); message.error ? task.reject(message.error) : task.resolve(message.result); } else if (message.method === "Runtime.exceptionThrown") errors.push(message.params.exceptionDetails); });
  await send("Page.enable"); await send("Runtime.enable"); await send("Network.enable");
  await send("Network.setBlockedURLs", { urls: ["https://*"] });
  await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
  await send("Page.navigate", { url: origin + "/protected/prediction-map/index.html" });
  await until("!!document.getElementById('prediction-mode-toggle') && !!map.getLayer('station-circles')");
  // Place navigation is independent from prediction and preserves station data.
  assert.equal(await evaluate("document.getElementById('settings-toggle').nextElementSibling.id"),'place-search-toggle');
  assert.equal(await evaluate("document.getElementById('place-search-toggle').nextElementSibling.id"),'terrain-mode-toggle');
  const beforePlaces=calls;
  await evaluate(`window.placeTestFetch=window.fetch;window.placeTestCalls=0;
    window.fetch=(url,options)=>String(url).startsWith('https://photon.komoot.io/api/')?
      (window.placeTestCalls++,Promise.resolve(new Response(JSON.stringify({features:[
        {geometry:{type:'Point',coordinates:[2.4,42.35]},properties:{name:'Molló <b>literal</b>',county:'Ripollès',country:'España',type:'city'}},
        {geometry:{type:'Point',coordinates:[null,42]},properties:{name:'invalid'}}]}),{status:200}))):window.placeTestFetch(url,options);
    applyLanguage('es');document.getElementById('place-search-toggle').click();
    document.getElementById('place-search-input').value='Molló';document.getElementById('place-search-form').requestSubmit()`);
  await until("document.querySelectorAll('#place-search-results button').length===1");
  assert.equal(await evaluate("document.querySelectorAll('#place-search-results b').length"),0);
  assert.equal(await evaluate("getComputedStyle(document.getElementById('place-search-panel')).backgroundColor"),'rgb(255, 255, 255)');
  await evaluate("document.querySelector('#place-search-results button').click()");
  await until('!map.isMoving()');
  assert.equal(await evaluate('Math.abs(map.getCenter().lat-42.35)<.0001'),true);
  assert.equal(await evaluate("document.querySelector('.map-place-marker').textContent"),'Molló <b>literal</b>');
  assert.equal(await evaluate("document.querySelectorAll('.map-place-marker b').length"),0);
  await evaluate("document.querySelector('.map-place-marker').click()");
  assert.equal(calls,beforePlaces);
  // Starting the next query immediately removes the previous POI, even with no result.
  await evaluate(`window.fetch=(url,options)=>String(url).startsWith('https://photon.komoot.io/api/')?
    new Promise(resolve=>{window.finishPlaceTest=()=>resolve(new Response('{"features":[]}',{status:200}))}):window.placeTestFetch(url,options);
    document.getElementById('place-search-toggle').click();document.getElementById('place-search-input').value='Unknown';document.getElementById('place-search-form').requestSubmit()`);
  assert.equal(await evaluate("document.querySelectorAll('.map-place-marker').length"),0);
  await until("typeof window.finishPlaceTest==='function'");
  await evaluate('window.finishPlaceTest();undefined');
  await until("!document.getElementById('place-search-submit').disabled");
  assert.ok(await evaluate("document.getElementById('place-search-status').textContent.includes('No se han encontrado')"));
  await send('Emulation.setDeviceMetricsOverride',{width:360,height:640,deviceScaleFactor:1,mobile:true});
  assert.equal(await evaluate(`(()=>{const r=document.getElementById('place-search-panel').getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.bottom<=innerHeight})()`),true);
  await evaluate("document.getElementById('place-search-input').dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))");
  assert.equal(await evaluate("document.getElementById('place-search-panel').hidden"),true);
  await evaluate("window.fetch=window.placeTestFetch; map.jumpTo({center:[1.9,42],zoom:9}); undefined");
  // iPhone login: guard the text size that triggers native focus zoom, and
  // ensure the keyboard's focused field is released before hiding the overlay.
  // Chrome emulation checks layout/focus; native iOS zoom still needs a device check.
  for (const height of [664, 844]) {
    await send("Emulation.setDeviceMetricsOverride", {width:390,height,deviceScaleFactor:1,mobile:true});
    await evaluate("showLogin()");
    await until("document.activeElement.id === 'login-username'");
    const inputSizes = await evaluate("Array.from(document.querySelectorAll('.login-card input'), e=>parseFloat(getComputedStyle(e).fontSize))");
    assert.ok(inputSizes.every(size=>size>=16), `Mobile login input sizes: ${inputSizes}`);
    await evaluate("hideLogin()");
    assert.equal(await evaluate("document.getElementById('login-overlay').contains(document.activeElement)"),false);
    await pause(100);
    const bounds=await evaluate(`['.topbar','.map-floating-controls','.maplibre-rain-legend','.period-timeline'].map(selector=>{
      const r=document.querySelector(selector).getBoundingClientRect();
      return {selector,left:r.left,top:r.top,right:r.right,bottom:r.bottom,width:innerWidth,height:innerHeight};
    })`);
    assert.ok(bounds.every(r=>r.left>=0 && r.top>=0 && r.right<=r.width+1 && r.bottom<=r.height+1),JSON.stringify(bounds));
  }
  const loginShot=await send('Page.captureScreenshot',{format:'png'});
  await fs.writeFile(path.join(profile,'mobile-after-login.png'),Buffer.from(loginShot.data,'base64'));
  // A reload with a saved session restores filters and a taller summary after
  // MapLibre has already measured its canvas. The map must fit the remainder.
  for (const [width,height] of [[360,640],[390,744]]) {
    await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:true});
    await send('Page.reload');
    await until("!!document.getElementById('prediction-mode-toggle') && !!map.getLayer('station-circles')");
    assert.equal(await evaluate("document.getElementById('login-overlay').hidden"),true);
    await evaluate("applyLanguage('ca'); minRainFilter=1; updateSummary('07d.geojson',1231,1995); document.getElementById('generated-at').textContent='15/09/26 - 23:56'");
    await pause(150);
    const layout=await evaluate(`(()=>{
      const header=document.querySelector('.topbar').getBoundingClientRect(), main=document.querySelector('main').getBoundingClientRect(), canvas=map.getCanvas().getBoundingClientRect();
      return {headerBottom:header.bottom,mainTop:main.top,mainBottom:main.bottom,canvasBottom:canvas.bottom,viewport:innerHeight,scrollWidth:document.documentElement.scrollWidth,width:innerWidth};
    })()`);
    assert.ok(layout.mainBottom<=layout.viewport+1 && Math.abs(layout.canvasBottom-layout.mainBottom)<=1 && layout.scrollWidth<=layout.width,JSON.stringify(layout));
  }
  const reloadShot=await send('Page.captureScreenshot',{format:'png'});
  await fs.writeFile(path.join(profile,'mobile-after-reload.png'),Buffer.from(reloadShot.data,'base64'));
  await evaluate("minRainFilter=0;updateSummary('21d.geojson',1)");
  await send("Emulation.setDeviceMetricsOverride", {width:1280,height:900,deviceScaleFactor:1,mobile:false});
  await evaluate("map.jumpTo({center:[1.9,42],zoom:9}); applyLanguage('es')");
  await evaluate("document.getElementById('settings-toggle').click();document.getElementById('settings-tab-prediction').click()");
  assert.equal(await evaluate("document.querySelectorAll('.map-settings-section.is-active').length"),1);
  assert.equal(await evaluate("document.querySelector('.map-settings-section.is-active').id"),"prediction-settings");
  assert.equal(await evaluate("document.getElementById('prediction-execution-selector').value"),"worker");
  assert.equal(await evaluate("document.getElementById('prediction-timezone-selector').value"),"Europe/Madrid");
  await send('Emulation.setTimezoneOverride',{timezoneId:'Pacific/Honolulu'});
  await evaluate("document.getElementById('prediction-timezone-selector').value='Pacific/Kiritimati';document.getElementById('prediction-timezone-selector').dispatchEvent(new Event('change'))");
  const settingsShot = await send("Page.captureScreenshot",{format:"png"});
  await fs.writeFile(path.join(profile,"prediction-settings.png"),Buffer.from(settingsShot.data,"base64"));
  await evaluate("document.getElementById('settings-tab-general').click()");
  assert.equal(await evaluate("document.querySelectorAll('.map-settings-section.is-active').length"),1);
  await evaluate("document.getElementById('settings-toggle').click()");
  assert.equal(await evaluate("document.getElementById('estimated-field-toggle').nextElementSibling.id"), "prediction-mode-toggle");
  assert.equal(await evaluate("performance.getEntriesByType('resource').some(r=>r.name.includes('prediction-mode.js'))"), false);
  await evaluate("document.getElementById('prediction-mode-toggle').click()");
  await until("document.getElementById('prediction-mode-toggle').getAttribute('aria-pressed')==='true'");
  assert.ok(await evaluate("document.querySelector('.pm-demo-banner').textContent.includes('Predicción experimental')"));
  const beforeStation = calls;
  const stationPoint = await evaluate("(()=>{const p=map.project([1.9,42]);const r=map.getCanvas().getBoundingClientRect();return {x:r.left+p.x,y:r.top+p.y}})()");
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", ...stationPoint });
  await until("!!hoverPopup && !currentPopup");
  assert.equal(calls, beforeStation);
  await clickAt(1.9, 42);
  await until("!!document.querySelector('.maplibregl-popup')");
  assert.equal(calls, beforeStation);
  assert.equal(await evaluate("!!document.querySelector('.pm-result')"), false);
  delay = 450;
  // The weather popup points right; click free map space on its left.
  await clickAt(1.78, 42.07);
  await until("!!document.querySelector('.pm-wait[open]')");
  await until("!!document.querySelector('.pm-result')");
  assert.equal(await evaluate("!!document.querySelector('.pm-wait[open]')"), false);
  assert.equal(await evaluate("document.querySelectorAll('.pm-species li').length"), 3);
  assert.equal(lastExecution,"worker");
  assert.equal(lastCalendar,'Pacific/Kiritimati');
  const expectedDay=await evaluate("(()=>{const p=new Intl.DateTimeFormat('en-CA',{timeZone:'Pacific/Kiritimati',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());return ['year','month','day'].map(k=>p.find(x=>x.type===k).value).join('-')})()");
  assert.equal(lastStartDate,expectedDay);
  assert.ok(await evaluate("document.querySelector('.pm-result').textContent.includes('Pacific/Kiritimati')"));
  assert.equal(deviceSettings.prediction_timezone,'Pacific/Kiritimati');
  assert.ok(await evaluate("document.querySelector('.pm-execution').textContent.startsWith('Worker ·')"));
  assert.ok(await evaluate("(()=>{const node=document.querySelector('.pm-result'), r=node.getBoundingClientRect();return node.scrollWidth<=node.clientWidth && r.left>=0 && r.right<=innerWidth && r.bottom<=innerHeight})()"));
  assert.ok(await evaluate("document.querySelector('.pm-result').textContent.includes('predicción simulada')"));
  assert.equal(await evaluate("document.querySelector('.pm-municipality').textContent"), "Municipio de prueba <b>literal</b>");
  assert.equal(await evaluate("document.querySelector('.pm-municipality b')"), null);
  assert.equal(await evaluate("document.querySelector('.pm-terrain').open"),false);
  assert.ok(await evaluate("document.querySelector('.pm-summary-altitude').textContent.includes('765.3 m')"));
  assert.ok(await evaluate("document.querySelector('.pm-summary-ph').textContent.includes('≈ 6.7')"));
  assert.ok(await evaluate("!document.querySelector('.pm-summary-ph').textContent.includes('cm')"));
  assert.ok(await evaluate("document.querySelector('.pm-summary-ph').textContent.includes('84 m')"));
  assert.equal(await evaluate("document.querySelectorAll('.pm-tree-chip').length"),4);
  assert.equal(await evaluate("document.querySelector('.pm-tree-chip b')"),null);
  const beforeHostLanguage = calls;
  for (const [language, expected] of [["en",["Soil undetermined","Holm oak","Quercus","Pinos"]],
                                    ["ca",["Sòl no determinat","Alzina","Roures","Pinos"]],
                                    ["es",["Suelo no determinado","Encinas <b>literal</b>","Robles","Pinos"]]]) {
    await evaluate(`applyLanguage('${language}')`);
    assert.deepEqual(await evaluate("Array.from(document.querySelectorAll('.pm-tree-chip'),n=>n.textContent)"),expected);
  }
  assert.equal(calls,beforeHostLanguage);
  assert.ok(await evaluate("document.querySelector('.pm-terrain-summary').getBoundingClientRect().left > document.querySelector('.pm-municipality').getBoundingClientRect().left"));
  await evaluate("document.querySelector('.pm-terrain').open=true");
  assert.ok(await evaluate("document.querySelector('.pm-altitude').textContent.includes('765.3 m')"));
  assert.equal(await evaluate("document.querySelectorAll('.pm-ph-table tbody tr').length"), 3);
  assert.equal(await evaluate("document.querySelectorAll('.pm-ph-table tbody tr')[1].children[1].textContent"), "—");
  assert.deepEqual(await evaluate("Array.from(document.querySelectorAll('.pm-ph-openlandmap tbody td'),n=>n.textContent)"),["6.7","5.6","7.9"]);
  assert.deepEqual(await evaluate("Array.from(document.querySelectorAll('.pm-ph-table tbody tr')[0].children,n=>n.textContent)"),["0–5 cm","6.3","4.3","8.0"]);
  assert.ok(await evaluate("document.querySelector('.pm-terrain').textContent.includes('0–30 cm')"));
  assert.ok(await evaluate("document.querySelector('.pm-terrain').textContent.includes('ISRIC')"));
  assert.ok(await evaluate("document.querySelector('.pm-land-vegetation').textContent.includes('Bosc <b>literal</b>')"));
  assert.equal(await evaluate("document.querySelector('.pm-land-vegetation b')"), null);
  assert.ok(await evaluate("document.querySelector('.pm-land-geology').textContent.includes('Geologia de prueba')"));
  const beforeDate = calls;
  await evaluate("document.querySelector('.pm-result select').value='2';document.querySelector('.pm-result select').dispatchEvent(new Event('change'))");
  assert.equal(calls, beforeDate);
  assert.ok(await evaluate("document.querySelector('.pm-result').textContent.includes('—')"));
  const screenshot = await send("Page.captureScreenshot", { format: "png" });
  await fs.writeFile(path.join(profile, "popup-desktop.png"), Buffer.from(screenshot.data, "base64"));
  await evaluate("document.querySelector('.pm-result-body').scrollTop=document.querySelector('.pm-result-body').scrollHeight");
  const terrainScreenshot = await send("Page.captureScreenshot", { format: "png" });
  await fs.writeFile(path.join(profile, "terrain-desktop.png"), Buffer.from(terrainScreenshot.data, "base64"));
  await checkFixedHeader();
  await evaluate("document.querySelector('.pm-terrain').open=false;document.querySelector('.pm-weather').open=true;document.querySelector('.pm-weather').scrollIntoView({block:'start'})");
  const beforeWeather = calls;
  await evaluate("document.querySelector('.pm-weather-range').value='7';document.querySelector('.pm-weather-range').dispatchEvent(new Event('change'))");
  assert.ok(await evaluate("document.querySelector('.pm-weather-total').textContent.includes('12.0')"));
  assert.equal(await evaluate("document.querySelectorAll('.pm-weather tbody tr').length"),7);
  assert.equal(await evaluate("document.querySelectorAll('.pm-weather tbody tr')[4].children[1].textContent"),"—");
  assert.equal(await evaluate("document.querySelector('.pm-weather-wind b')"),null);
  assert.equal(await evaluate("document.querySelectorAll('.pm-weather-figure')[1].querySelectorAll('polyline').length"),4);
  const weatherShot = await send("Page.captureScreenshot", {format:"png"});
  await fs.writeFile(path.join(profile,"weather-desktop.png"),Buffer.from(weatherShot.data,"base64"));
  await evaluate("document.querySelector('.pm-weather-range').value='60';document.querySelector('.pm-weather-range').dispatchEvent(new Event('change'))");
  assert.equal(await evaluate("document.querySelectorAll('.pm-weather tbody tr').length"),60);
  assert.equal(calls,beforeWeather);
  richTerrain = false;
  await evaluate("document.getElementById('settings-toggle').click();document.getElementById('settings-tab-prediction').click();document.getElementById('prediction-execution-selector').value='worker';document.getElementById('prediction-execution-selector').dispatchEvent(new Event('change'))");
  assert.equal(settingsSaves,1); // Calendar was saved on the first settings close.
  assert.equal(await evaluate("localStorage.getItem('rainmapperPredictionExecution:test')"),null);
  await evaluate("document.getElementById('settings-toggle').click()");
  await until("!document.body.classList.contains('settings-open')");
  await pause(100);
  assert.equal(settingsSaves,2);
  assert.equal(deviceSettings.prediction_execution,"worker");
  assert.ok(deviceSettings.period);
  await evaluate("document.querySelector('.pm-close').click()");
  delay = 700;
  await clickAt(2.04, 42.08);
  await until("!!document.querySelector('.pm-wait[open]')");
  await evaluate("document.querySelector('.pm-wait button').click()");
  await pause(800);
  assert.equal(await evaluate("!!document.querySelector('.pm-result') || !!document.querySelector('.pm-wait[open]')"), false);
  failure = true; delay = 0;
  await clickAt(2.04, 42.08);
  await until("document.querySelector('.pm-wait h2')?.textContent.includes('No se ha podido')");
  await evaluate("document.querySelector('.pm-wait button').click()");
  failure = false;
  const savesBeforeFallback=settingsSaves;
  for (const unavailable of ['busy','offline']) {
    busyWorker=unavailable==='busy'; unavailableWorker=unavailable==='offline';
    const beforeFallback=executionRequests.length;
    await clickAt(1.78,42.07);
    await until("!!document.querySelector('.pm-result')");
    const attempts=executionRequests.slice(beforeFallback);
    assert.deepEqual(attempts.map(r=>r.execution),['worker','local']);
    assert.notEqual(attempts[0].request_id,attempts[1].request_id);
    assert.deepEqual(attempts[0].point,attempts[1].point);
    assert.equal(attempts[0].start_date,attempts[1].start_date);
    assert.equal(attempts[0].calendar_timezone,attempts[1].calendar_timezone);
    assert.equal(await evaluate("document.getElementById('prediction-execution-selector').value"),'worker');
    assert.ok(await evaluate("document.querySelector('.pm-execution').textContent.startsWith('Local ·')"));
    assert.equal(deviceSettings.prediction_execution,'worker');
    assert.equal(settingsSaves,savesBeforeFallback);
    await evaluate("document.querySelector('.pm-close').click()");
  }
  unavailableLocal=true;
  const beforeBothUnavailable=executionRequests.length;
  await clickAt(1.78,42.07);
  await until("document.querySelector('.pm-wait h2')?.textContent.includes('No se ha podido')");
  assert.deepEqual(executionRequests.slice(beforeBothUnavailable).map(r=>r.execution),['worker','local']);
  await evaluate("document.querySelector('.pm-wait button').click()");
  unavailableLocal=false;
  // An explicit Local selection bypasses Worker even when it is unavailable.
  await evaluate("document.getElementById('prediction-execution-selector').value='local';document.getElementById('prediction-execution-selector').dispatchEvent(new Event('change'))");
  const beforeExplicitLocal=executionRequests.length;
  await clickAt(1.78,42.07); await until("!!document.querySelector('.pm-result')");
  assert.deepEqual(executionRequests.slice(beforeExplicitLocal).map(r=>r.execution),['local']);
  await evaluate("document.querySelector('.pm-close').click();document.getElementById('prediction-execution-selector').value='worker';document.getElementById('prediction-execution-selector').dispatchEvent(new Event('change'))");
  busyWorker=false; unavailableWorker=false;
  for (let i = 0; i < 4; i++) await evaluate("document.getElementById('prediction-mode-toggle').click()");
  const beforeOne = calls;
  await clickAt(2.04, 42.08);
  await until("!!document.querySelector('.pm-result')");
  assert.equal(calls, beforeOne + 1);
  assert.equal(lastExecution,"worker");
  assert.ok(await evaluate("document.querySelector('.pm-execution').textContent.includes('Worker')"));
  assert.equal(await evaluate("!!document.querySelector('.pm-municipality')"), false);
  assert.equal(await evaluate("!!document.querySelector('.pm-ph-table')"), false);
  assert.equal(await evaluate("document.querySelector('.pm-summary-altitude strong').textContent"),'—');
  assert.equal(await evaluate("document.querySelector('.pm-summary-ph strong').textContent"),'—');
  assert.ok(await evaluate("document.querySelector('.pm-summary-trees').textContent.includes('Pendiente')"));
  assert.ok(await evaluate("(() => { const t=document.querySelector('.pm-summary-trees').getBoundingClientRect();const h=document.querySelector('.pm-place-heading').getBoundingClientRect();return Math.abs(t.left-h.left)<1 && Math.abs(t.width-h.width)<1; })()"));
  assert.equal(await evaluate("!!document.querySelector('.pm-weather-wind')"), false);
  richTerrain = true;
  // Near either vertical edge, a lateral popup must retain useful height and
  // keep its pointer on the clicked coordinate. Desktop can exceed 650 px.
  for (const [x, y] of [[0.2, 0.05], [0.8, 0.05], [0.2, 0.85], [0.8, 0.85]]) {
    await evaluate("document.querySelector('.pm-close')?.click()");
    const location = await evaluate(`map.unproject([map.getCanvas().clientWidth*${x},map.getCanvas().clientHeight*${y}]).toArray()`);
    await clickAt(...location);
    await until("!!document.querySelector('.pm-result')");
    await evaluate("document.querySelector('.pm-terrain').open=true;document.querySelector('.pm-weather').open=true");
    await pause(80);
    const geometry = await evaluate(`(()=>{
      const p=document.querySelector('.pm-popup'), r=p.getBoundingClientRect(),
        c=map.getCanvas().getBoundingClientRect(), tip=p.querySelector('.maplibregl-popup-tip').getBoundingClientRect(),
        point=map.project(${JSON.stringify(location)}), body=document.querySelector('.pm-result');
      return {inside:r.top>=c.top && r.bottom<=c.bottom && r.left>=c.left && r.right<=c.right,
        height:body.clientHeight, tipError:Math.abs(tip.top+tip.height/2-c.top-point.y),scrollTop:body.scrollTop};
    })()`);
    assert.ok(geometry.inside, JSON.stringify(geometry));
    assert.ok(geometry.height > 650, JSON.stringify(geometry));
    assert.ok(geometry.tipError < 2, JSON.stringify(geometry));
    assert.equal(geometry.scrollTop, 0);
  }
  const edgeShot = await send("Page.captureScreenshot", {format:"png"});
  await fs.writeFile(path.join(profile,"popup-desktop-edge.png"),Buffer.from(edgeShot.data,"base64"));
  await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  await evaluate("map.resize();document.querySelector('.pm-close').click();map.jumpTo({center:[1.9,42],zoom:8});void 0");
  await clickAt(1.98, 42.01);
  await until("!!document.querySelector('.pm-result')");
  assert.ok(await evaluate("(()=>{const node=document.querySelector('.pm-result'), r=node.getBoundingClientRect();return node.scrollWidth<=node.clientWidth && r.width<=innerWidth && r.top>=0 && r.bottom<=innerHeight && r.left>=0 && r.right<=innerWidth})()"));
  assert.ok(await evaluate("(()=>{const r=document.querySelector('.pm-popup').getBoundingClientRect();return r.left>=0 && r.right<=innerWidth && r.bottom<=innerHeight})()"));
  const mobile = await send("Page.captureScreenshot", { format: "png" });
  await fs.writeFile(path.join(profile, "popup-mobile.png"), Buffer.from(mobile.data, "base64"));
  await evaluate("document.querySelector('.pm-terrain').open=true;document.querySelector('.pm-result-body').scrollTop=document.querySelector('.pm-result-body').scrollHeight");
  assert.ok(await evaluate("(()=>{const n=document.querySelector('.pm-result'), t=document.querySelector('.pm-ph-table').getBoundingClientRect(), r=n.getBoundingClientRect();return n.scrollWidth<=n.clientWidth && t.left>=r.left && t.right<=r.right && t.bottom<=r.bottom})()"));
  const mobileTerrain = await send("Page.captureScreenshot", { format: "png" });
  await fs.writeFile(path.join(profile, "terrain-mobile.png"), Buffer.from(mobileTerrain.data, "base64"));
  await evaluate("document.querySelector('.pm-terrain').open=false;document.querySelector('.pm-weather').open=true;document.querySelector('.pm-weather').scrollIntoView({block:'start'})");
  const weatherMobile = await send("Page.captureScreenshot", {format:"png"});
  await fs.writeFile(path.join(profile,"weather-mobile.png"),Buffer.from(weatherMobile.data,"base64"));
  await evaluate("document.querySelector('.pm-weather-records').open=true;document.querySelector('.pm-result-body').scrollTop=document.querySelector('.pm-result-body').scrollHeight");
  assert.ok(await evaluate("(()=>{const n=document.querySelector('.pm-result');return n.scrollWidth<=n.clientWidth && document.documentElement.scrollWidth<=innerWidth})()"));
  // Real ecological eligibility must suppress every simulated percentage.
  richTerrain = false;
  ecologyFixture = {status:"available", abstention_reason:null, mapped_context:{
    habitats:[{id:"meadow",label:{es:"Prado",ca:"Prat",en:"Meadow"}}],
    lithologies:[{id:"limestone",label:{es:"Caliza"}},{id:"sandstone",label:{es:"Arenisca"}}],
    soil_tendencies:[{id:"calcareous",label:{es:"Calizo"}},{id:"sandy",label:{es:"Arenoso"}}]
  }, species:[
    {name:"Compatible <b>literal</b>", scientific_name:"Species one", status:"compatible", daily_statuses:Array(7).fill("compatible"),daily_season_phases:Array(7).fill("main")},
    {name:"Sin hospedador compatible", scientific_name:"Species two", status:"unknown", reasons:["hosts_unknown","altitude_outside"], daily_statuses:Array(7).fill("unknown"),daily_season_phases:Array(7).fill("unknown")}
  ]};
  await evaluate("document.querySelector('.pm-close').click();map.jumpTo({center:[1.9,42],zoom:8});void 0");
  await clickAt(1.98,42.01); await until("!!document.querySelector('.pm-ecology')");
  assert.equal(await evaluate("document.querySelectorAll('.pm-species li').length"),1);
  assert.equal(await evaluate("document.querySelector('.pm-species strong').textContent"),"Compatible <b>literal</b>");
  assert.equal(await evaluate("document.querySelector('.pm-species b')"),null);
  assert.ok(await evaluate("document.querySelector('.pm-ecology-exclusions').textContent.includes('Falta un hospedador compatible identificado')"));
  assert.equal(await evaluate("!!document.querySelector('.pm-chart')"),false);
  assert.ok(await evaluate("!document.querySelector('.pm-result').textContent.includes('Especie de ejemplo')"));
  assert.equal(await evaluate("document.querySelector('.pm-summary-trees-label').textContent"),"Terreno");
  assert.deepEqual(await evaluate("Array.from(document.querySelectorAll('.pm-tree-chip'),n=>n.textContent)"),["Calizo","Arenoso","Prado"]);
  assert.deepEqual(await evaluate("Array.from(document.querySelectorAll('.pm-summary-trees .pm-soil-chip'),n=>n.textContent)"),["Calizo","Arenoso"]);
  assert.ok(await evaluate("document.querySelector('.pm-soil-tendencies').textContent.includes('Calizo, Arenoso')"));
  assert.ok(await evaluate("document.querySelector('.pm-materials').textContent.includes('Caliza, Arenisca')"));
  const unifiedTerrain = await send("Page.captureScreenshot", {format:"png"});
  await fs.writeFile(path.join(profile,"unified-terrain-mobile.png"),Buffer.from(unifiedTerrain.data,"base64"));
  await evaluate("document.querySelector('.pm-ecology-exclusions').open=true;document.querySelector('.pm-ecology-exclusions').scrollIntoView({block:'center'})");
  assert.ok(await evaluate("(()=>{const n=document.querySelector('.pm-ecology-exclusions li'), title=n.querySelector('strong').getBoundingClientRect(), reasons=Array.from(n.querySelectorAll('small'),x=>x.getBoundingClientRect());return reasons.length===3 && reasons[0].top>=title.bottom && reasons[1].top>=reasons[0].bottom && reasons[2].top>=reasons[1].bottom && document.querySelector('.pm-result').scrollWidth<=document.querySelector('.pm-result').clientWidth})()"));
  const exclusionsShot=await send("Page.captureScreenshot",{format:"png"});
  await fs.writeFile(path.join(profile,"exclusions-mobile.png"),Buffer.from(exclusionsShot.data,"base64"));
  await checkFixedHeader();
  await evaluate("document.querySelector('.pm-ecology-exclusions').open=false");
  await evaluate("document.querySelector('.pm-result-header select').value='1';document.querySelector('.pm-result-header select').dispatchEvent(new Event('change'))");
  assert.equal(await evaluate("document.querySelectorAll('.pm-species li').length"),1);
  assert.ok(await evaluate("document.querySelector('.pm-ecology-status').textContent.includes('temporada seleccionada')"));
  for (const fixture of [{status:"available",abstention_reason:"host_data_missing",species:ecologyFixture.species},
                         {status:"available",abstention_reason:"terrain_context_missing",species:ecologyFixture.species},
                         {status:"unavailable",species:[]}]) {
    ecologyFixture=fixture;
    await evaluate("document.querySelector('.pm-close').click()");
    await clickAt(1.98,42.01); await until("!!document.querySelector('.pm-ecology')");
    assert.equal(await evaluate("document.querySelectorAll('.pm-species li').length"),0);
    assert.equal(await evaluate("!!document.querySelector('.pm-chart')"),false);
    const expected = fixture.status!=="available" ? "No se puede evaluar" : fixture.abstention_reason==="terrain_context_missing" ? "falta información de terreno" : "falta información de hospedadores";
    assert.ok(await evaluate(`document.querySelector('.pm-ecology-status').textContent.includes('${expected}')`));
    assert.ok(await evaluate("document.querySelector('.pm-result').scrollWidth<=document.querySelector('.pm-result').clientWidth"));
  }
  ecologyFixture={status:"available",abstention_reason:null,species:
    ["lactarius_vinosus","lactarius_deliciosus","another","zero"].map((id,i)=>({species_id:id,
      name:["Rovelló · vinosus","Rovelló · deliciosus","Otra","Cero"][i],scientific_name:id,
      status:"compatible",reasons:i===1 ? ["ph_conflict_soil_supported"] : i===2 ? ["soil_ph_conditional"] : [],
      daily_statuses:Array(7).fill("compatible"),daily_season_phases:Array(7).fill("main")}))};
  modelFixture={data_mode:"prediction",species:[
    {species_id:"lactarius_deliciosus",label_key:"lactarius_deliciosus",status:"available",probabilities:[.2,.9,null,.3,.5,null,null]},
    {species_id:"another",label_key:"another",status:"available",probabilities:[.8,.1,...Array(5).fill(null)]},
    {species_id:"zero",label_key:"zero",status:"available",probabilities:Array(7).fill(0)}]};
  await evaluate("document.querySelector('.pm-close')?.click()");
  await clickAt(1.98,42.01); await until("!!document.querySelector('.pm-ecology')");
  assert.deepEqual(await evaluate("Array.from(document.querySelectorAll('.pm-species li'),n=>n.dataset.speciesId)"),
    ["another","lactarius_deliciosus","zero","lactarius_vinosus"]);
  assert.ok(await evaluate("document.querySelector('.pm-species li:last-child').textContent.includes('Sin IFF calculado')"));
  await evaluate("document.querySelector('.pm-species li:last-child .pm-iff-score').click()");
  assert.equal(await evaluate("getComputedStyle(document.querySelector('.pm-species li:last-child .pm-iff-help')).display"), 'block');
  assert.equal(await evaluate("document.querySelector('.pm-species li:last-child .pm-iff-band')"), null);
  await evaluate("document.querySelector('.pm-species li:last-child .pm-iff-score').blur()");
  assert.ok(await evaluate("document.querySelector('.pm-species').textContent.includes('No se ha confirmado descalcificación')"));
  assert.ok(await evaluate("document.querySelector('.pm-soil-ph-supported').textContent.includes('intervalo de pH solapado')"));
  assert.ok(await evaluate("document.querySelector('.pm-species [data-species-id=zero]').textContent.includes('0/100')"));
  assert.equal(await evaluate("document.querySelector('.pm-species [data-species-id=zero] .pm-iff-band').textContent"), 'Desfavorable');
  const bands = [[0,0,0],[.19,19,0],[.2,20,1],[.39,39,1],[.4,40,2],[.59,59,2],
    [.6,60,3],[.79,79,3],[.8,80,4],[.94,94,4],[.95,95,5],[1,100,5],[.596691,60,3],[.945,95,5]];
  assert.deepEqual(await evaluate(`import('./prediction-mode.js').then(m=>${JSON.stringify(bands)}.map(([v])=>[v,m.iffScore(v),m.iffBand(v)]))`),bands);
  assert.deepEqual(await evaluate("import('./prediction-mode.js').then(m=>[null,true,'0.65',NaN,Infinity,-1,1.1].map(v=>[m.iffScore(v),m.iffBand(v)]))"),Array(7).fill([null,null]));
  await evaluate("document.querySelector('.pm-iff-score').click()");
  assert.equal(await evaluate("getComputedStyle(document.querySelector('.pm-iff-help')).display"), 'block');
  assert.ok(await evaluate("document.querySelector('.pm-iff-help').textContent.includes('condiciones óptimas')"));
  await evaluate("document.querySelector('.pm-iff-score').blur()");
  assert.equal(await evaluate("document.querySelectorAll('.pm-weekly-chart g[data-species-id]').length"),3);
  assert.equal(await evaluate("document.querySelectorAll('.pm-weekly-chart [data-species-id=lactarius_deliciosus] polyline').length"),2);
  assert.equal(await evaluate("document.querySelectorAll('.pm-weekly-chart [data-species-id=lactarius_deliciosus] circle').length"),4);
  assert.equal(await evaluate("document.querySelectorAll('.pm-weekly-chart [data-species-id=zero] circle').length"),7);
  assert.equal(await evaluate("document.querySelector('.pm-species [data-species-id=lactarius_deliciosus] .pm-weekly-peak').textContent"),'Máx.: 90/100 · domingo 13/09/26');
  assert.equal(await evaluate("document.querySelector('.pm-species [data-species-id=zero] .pm-weekly-peak').textContent"),'Máx.: 0/100 · sábado 12/09/26');
  assert.equal(await evaluate("document.querySelector('.pm-species [data-species-id=lactarius_vinosus] .pm-weekly-peak')"),null);
  const iffColors=await evaluate(`(()=>{
    const row=document.querySelector('.pm-species [data-species-id=lactarius_deliciosus]');
    const wrap=row.querySelector('.pm-iff-value'),score=row.querySelector('.pm-iff-score'),band=row.querySelector('.pm-iff-band'),peak=row.querySelector('.pm-iff-peak-value');
    const original=wrap.dataset.iffBand;
    const colors=Array.from({length:6},(_,i)=>{wrap.dataset.iffBand=String(i);peak.dataset.iffBand=String(i);return [getComputedStyle(score).color,getComputedStyle(band).color,getComputedStyle(peak).color];});
    wrap.dataset.iffBand=original;peak.dataset.iffBand='4';
    return {colors,missing:document.querySelector('.pm-species [data-species-id=lactarius_vinosus] .pm-iff-value').dataset.iffBand??null};
  })()`);
  assert.equal(new Set(iffColors.colors.map(c=>c[0])).size,6);
  assert.ok(iffColors.colors.every(c=>c.every(v=>v===c[0])));
  assert.equal(iffColors.missing,null);
  const luminance=rgb=>rgb.map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
  const background=luminance([233,237,240]); // Translucent popup over a dark map.
  assert.ok(iffColors.colors.every(([rgb])=>(background+.05)/(luminance(rgb.match(/\d+/g).map(Number))+.05)>=4.5),JSON.stringify(iffColors));
  const seriesColors = await evaluate("Array.from(document.querySelectorAll('.pm-weekly-chart g[data-species-id]'),g=>[g.dataset.speciesId,g.getAttribute('stroke')]).sort()");
  assert.ok(await evaluate("Array.from(document.querySelectorAll('.pm-weekly-chart g[data-species-id]'),g=>getComputedStyle(g).stroke===getComputedStyle(document.querySelector('.pm-species [data-species-id='+g.dataset.speciesId+'] .pm-species-color')).backgroundColor).every(Boolean)"));
  await checkFixedHeader();
  const weeklyMobile=await send("Page.captureScreenshot",{format:"png"});
  await fs.writeFile(path.join(profile,"weekly-chart-mobile.png"),Buffer.from(weeklyMobile.data,"base64"));
  await evaluate("document.querySelector('.pm-close').click()");
  await send("Emulation.setDeviceMetricsOverride", {width:1280,height:1000,deviceScaleFactor:1,mobile:false});
  await evaluate("map.resize();map.jumpTo({center:[1.9,42],zoom:8});void 0");
  await clickAt(1.98,42.01); await until("!!document.querySelector('.pm-weekly-chart svg')");
  await evaluate("document.querySelector('.pm-terrain').open=true");
  await checkFixedHeader();
  const weeklyDesktop=await send("Page.captureScreenshot",{format:"png"});
  await fs.writeFile(path.join(profile,"weekly-chart-desktop.png"),Buffer.from(weeklyDesktop.data,"base64"));
  await evaluate("document.querySelector('.pm-close').click()");
  await send("Emulation.setDeviceMetricsOverride", {width:390,height:844,deviceScaleFactor:1,mobile:true});
  await evaluate("map.resize();map.jumpTo({center:[1.9,42],zoom:8});void 0");
  await clickAt(1.98,42.01); await until("!!document.querySelector('.pm-weekly-chart svg')");
  const predictionCalls=calls;
  await evaluate("document.querySelector('.pm-result-header select').value='1';document.querySelector('.pm-result-header select').dispatchEvent(new Event('change'))");
  assert.deepEqual(await evaluate("Array.from(document.querySelectorAll('.pm-species li'),n=>n.dataset.speciesId)"),
    ["lactarius_deliciosus","another","zero","lactarius_vinosus"]);
  assert.equal(calls,predictionCalls);
  assert.deepEqual(await evaluate("Array.from(document.querySelectorAll('.pm-weekly-chart g[data-species-id]'),g=>[g.dataset.speciesId,g.getAttribute('stroke')]).sort()"),seriesColors);
  await evaluate("applyLanguage('en')");
  await until("document.querySelector('.pm-result h2')?.textContent==='Prediction by species · 7 days'");
  assert.equal(await evaluate("document.querySelector('.pm-result-header select').value"),'1');
  assert.equal(await evaluate("document.querySelector('.pm-species [data-species-id=lactarius_deliciosus] .pm-weekly-peak').textContent"),'Max: 90/100 · Sunday 13/09/26');
  assert.equal(await evaluate("document.querySelector('.pm-species [data-species-id=lactarius_deliciosus] .pm-season-phase').textContent"),'Main season');
  assert.ok(await evaluate("document.querySelector('.pm-species [data-species-id=lactarius_vinosus]').textContent.includes('No IFF calculated')"));
  assert.ok(await evaluate("document.querySelector('.pm-weekly-chart svg').getAttribute('aria-label').includes('IFF by species')"));
  assert.equal(await evaluate("document.querySelector('.pm-species [data-species-id=lactarius_deliciosus] .pm-iff-band').textContent"), 'Very favorable');
  assert.ok(await evaluate("document.querySelector('.pm-iff-help').textContent.includes('Index of Fruiting Favorability')"));
  await evaluate("applyLanguage('ca')");
  assert.equal(await evaluate("document.querySelector('.pm-species [data-species-id=lactarius_deliciosus] .pm-iff-band').textContent"), 'Molt favorable');
  assert.ok(await evaluate("document.querySelector('.pm-iff-help').textContent.includes('condicions òptimes')"));
  assert.equal(calls,predictionCalls);
  await evaluate("applyLanguage('es')");
  await until("document.querySelector('.pm-result h2')?.textContent==='Predicción por especies · 7 días'");
  await evaluate("document.querySelector('.pm-weekly-chart circle').dispatchEvent(new MouseEvent('click',{bubbles:true,clientX:document.querySelector('.pm-weekly-chart svg').getBoundingClientRect().left+30}))");
  assert.equal(await evaluate("document.querySelector('.pm-result-header select').value"),'0');
  assert.equal(calls,predictionCalls);
  // Terrain stays compatible, but the visible list changes with seasonal phase.
  compactMobileFixture=true; richTerrain=true;
  const compactMeasurements=[];
  for (const [width,height,language] of [[360,640,'es'],[390,744,'ca'],[390,844,'en']]) {
    await evaluate("document.querySelector('.pm-close').click()");
    await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:true});
    await evaluate(`applyLanguage('${language}');map.jumpTo({center:[1.9,42],zoom:8});void 0`);
    await clickAt(1.98,42.01); await until("!!document.querySelector('.pm-weekly-chart svg')");
    const compact=await evaluate(`(()=>{
      const box=s=>document.querySelector(s).getBoundingClientRect();
      const coordinates=box('.pm-coordinates'),altitude=box('.pm-summary-altitude'),ph=box('.pm-summary-ph');
      const date=box('.pm-date-title'),timezone=box('.pm-calendar-timezone'),select=box('.pm-calendar select');
      const popup=box('.pm-result'),body=box('.pm-result-body');
      const baseline=s=>{const marker=document.createElement('span');marker.style.cssText='display:inline-block;width:0;height:0;vertical-align:baseline';document.querySelector(s).append(marker);const y=marker.getBoundingClientRect().top;marker.remove();return y;};
      return {width:innerWidth,height:innerHeight,bodyFraction:body.height/popup.height,
        coordinatesTop:coordinates.top,altitudeTop:altitude.top,phTop:ph.top,
        dateCenter:(date.top+date.bottom)/2,timezoneCenter:(timezone.top+timezone.bottom)/2,
        selectCenter:(select.top+select.bottom)/2,
        dateBaseline:baseline('.pm-date-title'),timezoneBaseline:baseline('.pm-calendar-timezone'),selectHeight:select.height,selectWidth:select.width,
        zoneFirst:timezone.right<=date.left && date.right<=select.left,
        zoneCaptionVisible:getComputedStyle(document.querySelector('.pm-zone-caption')).display!=='none',
        noticeHidden:!document.querySelector('.pm-simulation') || getComputedStyle(document.querySelector('.pm-simulation')).display==='none',
        timezoneCaptionHidden:getComputedStyle(document.querySelector('.pm-timezone-caption')).display==='none',
        noOverflow:document.querySelector('.pm-result').scrollWidth<=popup.width+1,
        selectFont:parseFloat(getComputedStyle(document.querySelector('.pm-calendar select')).fontSize)};
    })()`);
    assert.ok(await evaluate(`(()=>{
      const dates=[...document.querySelectorAll('.pm-chart-label tspan[dy]')].map(n=>n.getBoundingClientRect());
      return dates.every((r,i)=>!i || r.left>=dates[i-1].right);
    })()`),'Chart dates must not overlap on mobile');
    // Long band labels share the scientific-name row, below the IFF score.
    const bandLayout = await evaluate(`(()=>{
      const row=document.querySelector('.pm-species li'),band=row.querySelector('.pm-iff-band');
      band.textContent=({es:'Moderadamente favorable',ca:'Moderadament favorable',en:'Moderately favorable'})[document.documentElement.lang];
      const b=band.getBoundingClientRect(),s=row.querySelector('small').getBoundingClientRect(),score=row.querySelector('.pm-iff-score').getBoundingClientRect();
      const range=document.createRange();range.selectNodeContents(band);
      return {lines:range.getClientRects().length,top:b.top,scientificTop:s.top,left:b.left,scientificRight:s.right,right:b.right,scoreRight:score.right,overflow:row.scrollWidth>row.clientWidth};
    })()`);
    assert.ok(bandLayout.lines===1 && Math.abs(bandLayout.top-bandLayout.scientificTop)<2 && bandLayout.left>=bandLayout.scientificRight && Math.abs(bandLayout.right-bandLayout.scoreRight)<1 && !bandLayout.overflow,JSON.stringify(bandLayout));
    const seasonLayout=await evaluate(`(()=>{
      const row=document.querySelector('.pm-species li'),summary=row.querySelector('.pm-season-summary');
      const phase=summary.querySelector('.pm-season-phase'),peak=summary.querySelector('.pm-weekly-peak');
      const a=phase.getBoundingClientRect(),b=peak.getClientRects()[0];
      return {text:summary.textContent,phaseColor:getComputedStyle(phase).color,peakColor:getComputedStyle(peak).color,
        sameFirstLine:Math.abs(a.top-b.top)<2,overflow:row.scrollWidth>row.clientWidth,
        height:summary.getBoundingClientRect().height,lineHeight:parseFloat(getComputedStyle(summary).lineHeight)};
    })()`);
    assert.ok(seasonLayout.sameFirstLine && !seasonLayout.overflow && seasonLayout.phaseColor!==seasonLayout.peakColor && seasonLayout.text.includes(' — ') && seasonLayout.height<=seasonLayout.lineHeight*2+1,JSON.stringify(seasonLayout));
    compactMeasurements.push(compact);
    assert.ok(compact.noticeHidden && compact.timezoneCaptionHidden && compact.noOverflow,JSON.stringify(compact));
    assert.ok(Math.abs(compact.coordinatesTop-compact.altitudeTop)<3 && Math.abs(compact.coordinatesTop-compact.phTop)<3,JSON.stringify(compact));
    assert.ok(Math.abs(compact.dateBaseline-compact.timezoneBaseline)<1 && Math.abs(compact.dateCenter-compact.selectCenter)<4,JSON.stringify(compact));
    assert.ok(compact.bodyFraction>=.45 && compact.selectFont>=11 && compact.selectHeight<=24 && compact.selectWidth<=140,JSON.stringify(compact));
    assert.ok(compact.zoneFirst && compact.zoneCaptionVisible,JSON.stringify(compact));
    const shot=await send('Page.captureScreenshot',{format:'png'});
    await fs.writeFile(path.join(profile,`compact-header-${language}.png`),Buffer.from(shot.data,'base64'));
  }
  // Calendar presentation must not depend on the browser time zone.
  const calendarChecks = await evaluate(`(async()=>{
    const {formatCalendarDate}=await import(new URL('prediction-weather.js',document.querySelector('script[src*=prediction-bootstrap]').src));
    return ['es','ca','en'].map(lang=>[formatCalendarDate('2026-09-16',lang),formatCalendarDate('2028-02-29',lang)]);
  })()`);
  assert.deepEqual(calendarChecks,[['miércoles 16/09/26','martes 29/02/28'],['dimecres 16/09/26','dimarts 29/02/28'],['Wednesday 16/09/26','Tuesday 29/02/28']]);
  await evaluate("document.querySelector('.pm-close')?.click()");
  for (const [width,height] of [[1280,800],[375,667],[360,640]]) {
    await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width<500});
    for (const language of ['es','ca','en']) {
      await evaluate(`applyLanguage('${language}');document.getElementById('help-toggle').click()`);
      const help = await evaluate(`(()=>{
        const p=document.getElementById('map-help'),r=p.getBoundingClientRect();
        const titles=Array.from(p.querySelectorAll('[data-help-control]')).filter(n=>!n.hidden).map(n=>n.dataset.helpControl);
        return {top:r.top,bottom:r.bottom,left:r.left,right:r.right,height:innerHeight,width:innerWidth,
          scrollable:p.scrollHeight>p.clientHeight,titles,text:p.textContent};
      })()`);
      assert.ok(help.top>=0 && help.bottom<=height && help.left>=0 && help.right<=width && help.scrollable,JSON.stringify(help));
      assert.deepEqual(help.titles,['prediction-mode-toggle','quick-metric-toggle','heatmap-toggle','estimated-field-toggle']);
      const beforeZoom=await evaluate('map.getZoom()');
      await send('Input.dispatchMouseEvent',{type:'mouseWheel',x:(help.left+help.right)/2,y:(help.top+help.bottom)/2,deltaX:0,deltaY:10000});
      await pause(500);
      const scroll = await evaluate("(()=>{const p=document.getElementById('map-help'),r=p.getBoundingClientRect();return {top:p.scrollTop,height:p.clientHeight,total:p.scrollHeight,target:document.elementFromPoint((r.left+r.right)/2,(r.top+r.bottom)/2)?.outerHTML.slice(0,180)}})()");
      assert.ok(scroll.top>0 && scroll.top+scroll.height>=scroll.total-2,JSON.stringify({width,height,language,scroll}));
      assert.equal(await evaluate('map.getZoom()'),beforeZoom);
      if (language==='es') {
        const shot=await send('Page.captureScreenshot',{format:'png'});
        await fs.writeFile(path.join(profile,`help-bottom-${width}.png`),Buffer.from(shot.data,'base64'));
      }
      await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape'});
      await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Escape',code:'Escape'});
      assert.ok(await evaluate("document.getElementById('map-help').hidden && document.activeElement.id==='help-toggle'"),JSON.stringify(await evaluate("({hidden:document.getElementById('map-help').hidden,active:document.activeElement.outerHTML.slice(0,200)})")));
    }
  }
  console.log(JSON.stringify({compact_header:compactMeasurements}));
  compactMobileFixture=false; richTerrain=false;
  await evaluate("applyLanguage('es')");
  // Continue the season changes with the original fixture.
  ecologyFixture.species[0].daily_season_phases=Array(7).fill('out_of_season');
  ecologyFixture.species[0].status='incompatible';
  ecologyFixture.species[0].daily_statuses=Array(7).fill('incompatible');
  ecologyFixture.species[0].reasons=['ph_outside'];
  ecologyFixture.species[1].daily_season_phases=['out_of_season','secondary',...Array(5).fill('main')];
  ecologyFixture.species[2].daily_season_phases=Array(7).fill('unknown');
  await evaluate("document.querySelector('.pm-close')?.click()");
  await clickAt(1.98,42.01); await until("!!document.querySelector('.pm-ecology')");
  assert.deepEqual(await evaluate("Array.from(document.querySelectorAll('.pm-species li'),n=>n.dataset.speciesId)"),['zero']);
  assert.deepEqual(await evaluate("Array.from(document.querySelectorAll('.pm-ecology-exclusions li'),n=>n.dataset.speciesId)"),
    ['lactarius_vinosus','lactarius_deliciosus','another']);
  assert.equal(await evaluate("document.querySelectorAll('.pm-ecology-exclusions [data-species-id=lactarius_vinosus] small').length"),2);
  assert.ok(await evaluate("document.querySelector('.pm-ecology-exclusions [data-species-id=lactarius_deliciosus]').textContent.includes('Fuera de temporada')"));
  assert.ok(await evaluate("document.querySelector('.pm-ecology-exclusions [data-species-id=another]').textContent.includes('Temporada no determinada')"));
  assert.deepEqual(await evaluate("Array.from(document.querySelectorAll('.pm-weekly-chart g[data-species-id]'),g=>g.dataset.speciesId)"),['zero']);
  assert.equal(await evaluate("document.querySelector('.pm-species [data-species-id=zero] .pm-season-phase').textContent"),'Temporada principal');
  const seasonalCalls=calls;
  await evaluate("document.querySelector('.pm-result-header select').value='1';document.querySelector('.pm-result-header select').dispatchEvent(new Event('change'))");
  assert.deepEqual(await evaluate("Array.from(document.querySelectorAll('.pm-species li'),n=>n.dataset.speciesId)"),['lactarius_deliciosus','zero']);
  assert.equal(await evaluate("document.querySelector('.pm-ecology-exclusions [data-species-id=lactarius_deliciosus]')"),null);
  assert.equal(await evaluate("document.querySelector('.pm-species [data-species-id=lactarius_deliciosus] .pm-season-phase').textContent"),'Temporada secundaria');
  await evaluate("document.querySelector('.pm-result-header select').value='2';document.querySelector('.pm-result-header select').dispatchEvent(new Event('change'))");
  assert.equal(await evaluate("document.querySelector('.pm-species [data-species-id=lactarius_deliciosus] .pm-season-phase').textContent"),'Temporada principal');
  assert.equal(calls,seasonalCalls);
  // Regression: a large catalogue must not consume colors for absent curves.
  const plottedIds=['boletus_edulis','boletus_pinophilus','lactarius_deliciosus'];
  ecologyFixture={status:'available',abstention_reason:null,species:[
    ...plottedIds.map((id,i)=>({species_id:id,name:['Edulis','Pinícola','Rovelló · deliciosus'][i],
      scientific_name:id,status:'compatible',daily_statuses:Array(7).fill('compatible'),daily_season_phases:Array(7).fill('main')})),
    ...Array.from({length:18},(_,i)=>({species_id:`unplotted_${i}`,name:`Unplotted ${i}`,scientific_name:`Taxon ${i}`,
      status:'unknown',daily_statuses:Array(7).fill('unknown'),daily_season_phases:Array(7).fill('main')}))]};
  modelFixture={data_mode:'prediction',species:plottedIds.map((id,i)=>({species_id:id,label_key:id,status:'available',
    probabilities:Array.from({length:7},(_,day)=>[.54,.4,.6][i]+day*.006)}))};
  await evaluate("document.querySelector('.pm-close').click()");
  await send('Emulation.setDeviceMetricsOverride',{width:1280,height:1000,deviceScaleFactor:1,mobile:false});
  await evaluate("map.resize();map.jumpTo({center:[1.9,42],zoom:8});void 0");
  await clickAt(1.98,42.01); await until("!!document.querySelector('.pm-weekly-chart svg')");
  assert.deepEqual(await evaluate("Array.from(document.querySelectorAll('.pm-weekly-chart g[data-species-id]'),g=>[g.dataset.speciesId,g.getAttribute('stroke')]).sort()"),
    plottedIds.map((id,i)=>[id,['#0072b2','#d55e00','#7b3294'][i]]));
  assert.ok(await evaluate("Array.from(document.querySelectorAll('.pm-weekly-chart g[data-species-id]'),g=>getComputedStyle(g).stroke===getComputedStyle(document.querySelector('.pm-species [data-species-id='+g.dataset.speciesId+'] .pm-species-color')).backgroundColor).every(Boolean)"));
  const distinctColors=await send('Page.captureScreenshot',{format:'png'});
  await fs.writeFile(path.join(profile,'distinct-species-colors.png'),Buffer.from(distinctColors.data,'base64'));
  const beforeHoverCalls=calls;
  const immediateHover=await evaluate(`(()=>{
    const svg=document.querySelector('.pm-weekly-chart svg');
    const point=svg.querySelector('[data-species-id=lactarius_deliciosus] circle[data-day="6"]');
    const r=point.getBoundingClientRect();
    svg.dispatchEvent(new PointerEvent('pointermove',{clientX:r.x+r.width/2,clientY:svg.getBoundingClientRect().bottom-20}));
    const tip=document.querySelector('.pm-chart-tooltip'),b=tip.getBoundingClientRect(),s=svg.getBoundingClientRect();
    return {visible:!tip.hidden,text:tip.textContent,bounded:b.left>=s.left&&b.right<=s.right+1,
      nativeTitles:svg.querySelectorAll('circle title').length};
  })()`);
  assert.equal(immediateHover.visible,true);
  assert.ok(immediateHover.text.includes('Rovelló · deliciosus'));
  assert.ok(immediateHover.text.includes('IFF:64/100'));
  assert.ok(immediateHover.text.includes('Edulis'));
  assert.ok(immediateHover.text.includes('Pinícola'));
  assert.equal(await evaluate("document.querySelectorAll('.pm-chart-tooltip-row').length"),3);
  assert.equal(immediateHover.bounded,true);
  assert.equal(immediateHover.nativeTitles,0);
  const hoverShot=await send('Page.captureScreenshot',{format:'png'});
  await fs.writeFile(path.join(profile,'prediction-hover-immediate.png'),Buffer.from(hoverShot.data,'base64'));
  await evaluate("document.querySelector('.pm-weekly-chart svg').dispatchEvent(new PointerEvent('pointerleave'))");
  assert.equal(await evaluate("document.querySelector('.pm-chart-tooltip').hidden"),true);
  await evaluate("document.querySelector('.pm-weekly-chart [data-species-id=boletus_edulis] circle').focus()");
  assert.ok(await evaluate("!document.querySelector('.pm-chart-tooltip').hidden && document.querySelector('.pm-chart-tooltip').textContent.includes('Edulis')"));
  await evaluate("document.querySelector('.pm-weekly-chart svg').dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'}))");
  assert.equal(await evaluate("document.querySelector('.pm-chart-tooltip').hidden"),true);
  assert.equal(calls,beforeHoverCalls);
  for (const row of modelFixture.species) row.probabilities[3]=null;
  await evaluate("document.querySelector('.pm-close').click()");
  await clickAt(1.98,42.01); await until("!!document.querySelector('.pm-weekly-chart svg')");
  await evaluate("(()=>{const svg=document.querySelector('.pm-weekly-chart svg'),r=svg.getBoundingClientRect();svg.dispatchEvent(new PointerEvent('pointermove',{clientX:r.left+r.width*213/400,clientY:r.top+20}))})()");
  assert.ok(await evaluate("document.querySelector('.pm-chart-tooltip').textContent.includes('Sin IFF calculado')"));
  assert.equal(await evaluate("document.querySelectorAll('.pm-chart-tooltip-row').length"),0);
  // Applicability warnings use the selected day; absent models are distinct.
  modelFixture.species[0].applicability=[0,1,null,null,null,null,null];
  modelFixture.species[0].applicability_details=[
    {status:'caution',outside:8,total:160,examples:[{feature:'temp_min_c__lag_009',value:22.83,training_min:-7.63,training_max:22.73}]},
    {status:'outside_domain',outside:1,total:160,examples:[]}];
  modelFixture.species[0].probabilities[1]=null;
  modelFixture.species[0].reasons=['calculated','outside_domain',...Array(5).fill('calculated')];
  modelFixture.species[1].status='no_model';
  modelFixture.species[1].probabilities=Array(7).fill(null);
  modelFixture.species[1].reasons=Array(7).fill('model_unavailable');
  await evaluate("document.querySelector('.pm-close').click()");
  await clickAt(1.98,42.01); await until("!!document.querySelector('.pm-applicability')");
  assert.ok(await evaluate("document.querySelector('[data-species-id=boletus_edulis] .pm-applicability summary').textContent.includes('IFF con extrapolación')"));
  assert.equal(await evaluate("document.querySelector('[data-species-id=boletus_pinophilus] .pm-iff-score').textContent"),'Sin modelo disponible');
  await evaluate("document.querySelector('.pm-applicability summary').click()");
  assert.ok(await evaluate("document.querySelector('.pm-applicability').textContent.includes('8 de 160')"));
  assert.ok(await evaluate("document.querySelector('.pm-applicability').textContent.includes('Temperatura mínima')"));
  await evaluate("document.querySelector('.pm-weekly-chart [data-species-id=boletus_edulis] circle').focus()");
  assert.ok(await evaluate("document.querySelector('.pm-chart-tooltip').textContent.includes('IFF con extrapolación')"));
  await evaluate("(()=>{const s=document.querySelector('.pm-calendar select');s.value='1';s.dispatchEvent(new Event('change'))})()");
  assert.equal(await evaluate("document.querySelector('[data-species-id=boletus_edulis] .pm-iff-score').textContent"),'Fuera de rango');
  assert.ok(await evaluate("document.querySelector('[data-species-id=boletus_edulis] .pm-applicability').textContent.includes('IFF descartado')"));
  modelFixture=null;
  ecologyFixture=null;
  await evaluate("document.querySelector('.pm-close').click();map.jumpTo({center:[2.15,42.2],zoom:9});document.getElementById('settings-toggle').click();document.getElementById('settings-tab-general').click();document.getElementById('save-map-view-default').click();document.getElementById('settings-toggle').click()");
  await pause(100);
  assert.equal(deviceSettings.map_view.lng,2.15);
  assert.equal(deviceSettings.map_view.lat,42.2);
  predictionAllowed = false;
  role = "free";
  await send("Page.navigate", { url: origin + "/protected/prediction-map/index.html" });
  await until("typeof map?.getLayer === 'function' && !!map.getLayer('station-circles')"); await pause(150);
  assert.equal(await evaluate("!!document.getElementById('prediction-mode-toggle')"), false);
  assert.equal(await evaluate("!!document.getElementById('settings-tab-prediction')"), false);
  await evaluate("document.getElementById('settings-toggle').click();markDeviceSettingsChanged();document.getElementById('settings-toggle').click()");
  await pause(100);
  assert.equal(deviceSettings.prediction_execution,"worker");
  predictionAllowed = true;
  role = "basic";
  await send("Page.navigate", { url: origin + "/protected/prediction-map/index.html" });
  await until("!!document.getElementById('prediction-execution-selector')");
  assert.equal(await evaluate("document.getElementById('prediction-execution-selector').value"),"worker");
  assert.equal(await evaluate("document.getElementById('prediction-timezone-selector').value"),'Pacific/Kiritimati');
  await until("Math.abs(map.getCenter().lng-2.15)<0.0001 && Math.abs(map.getCenter().lat-42.2)<0.0001");
  await send("Page.navigate", { url: origin + "/protected/maplibre/index.html" });
  await until("typeof map?.getLayer === 'function' && !!map.getLayer('station-circles')");
  await until("!!document.getElementById('settings-tab-prediction')");
  assert.equal(await evaluate("!!document.getElementById('prediction-mode-toggle')"), true);
  predictionAllowed = false; role = "admin";
  await evaluate("validateStoredSession()");
  await until("!document.getElementById('prediction-mode-toggle')");
  await evaluate("document.getElementById('settings-toggle').click();markDeviceSettingsChanged();document.getElementById('settings-toggle').click()");
  await pause(100);
  assert.equal(deviceSettings.prediction_execution,"worker");
  assert.equal(errors.length, 0, JSON.stringify(errors));
  console.log(JSON.stringify({ ok: true, checks: "shared viewer, lazy module, station hover/click, modal, popup, dates, cancellation, errors, repeated toggles, mobile, non-admin, original route", screenshots: profile, demo_requests: calls }));
} finally {
  ws?.close(); chrome.kill("SIGTERM"); server.closeAllConnections(); server.close(); clearTimeout(watchdog);
}
