const viewerConfig = window.RAINMAPPER_CONFIG || {};
const defaultDataBase = viewerConfig.dataBase || (window.location.pathname.includes("/maplibre-viewer/")
  ? "../../../docker-data/PublicData/"
  : "data/");
const DATA_BASE = new URLSearchParams(window.location.search).get("data") || defaultDataBase;
const AUTH_REQUIRED = Boolean(viewerConfig.authRequired);
const AUTH_BASE = viewerConfig.authBase || "/auth";
const AUTH_STORAGE_KEY = "rainmapperMaplibreAuth";

const periods = {
  "01d.geojson": "1 day",
  "07d.geojson": "7 days",
  "14d.geojson": "14 days",
  "21d.geojson": "21 days",
  "30d.geojson": "30 days",
  "60d.geojson": "60 days",
  "90d.geojson": "90 days",
};

const DISPLAY_BOUNDS = [
  [-2.5, 39.0],
  [4.2, 43.7],
];
const INITIAL_CENTER = [2.1, 41.7];
const INITIAL_ZOOM = 7;
const SOURCE_ID = "stations";
const CIRCLE_LAYER_ID = "station-circles";
const TERRAIN_SOURCE_ID = "rainmapper-terrain-dem";
const TERRAIN_TILES = [
  "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png",
];
const TERRAIN_ELEVATION_ZOOM = 15;
const LONG_PRESS_MS = 650;
const LONG_PRESS_MOVE_TOLERANCE_PX = 12;
const HOVER_POPUP_MIN_ZOOM = 9;
const stationSources = [
  { id: "Meteocat", label: "Meteocat" },
  { id: "Meteoclimatic", label: "Meteoclimatic" },
  { id: "Wunderground", label: "Wunderground" },
  { id: "Unknown", label: "Unknown" },
];

const baseStyles = [
  {
    id: "esri-satellite-vector",
    label: "Satellite+",
    style: {
      version: 8,
      sources: {
        "esri-imagery": {
          type: "raster",
          tiles: [
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
          ],
          tileSize: 256,
          maxzoom: 19,
          attribution: "Tiles &copy; Esri",
        },
        "openmaptiles": {
          type: "vector",
          url: "https://tiles.openfreemap.org/planet",
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        },
      },
      glyphs: "https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf",
      layers: [
        { id: "esri-imagery", type: "raster", source: "esri-imagery" },
        {
          id: "satellite-boundary",
          type: "line",
          source: "openmaptiles",
          "source-layer": "boundary",
          filter: ["all", ["!=", ["get", "maritime"], 1], ["<=", ["get", "admin_level"], 6]],
          paint: {
            "line-color": "rgba(255,255,255,0.78)",
            "line-dasharray": [2, 2],
            "line-width": ["interpolate", ["linear"], ["zoom"], 5, 0.7, 10, 1.4, 14, 2.2],
          },
        },
        {
          id: "satellite-road-outline",
          type: "line",
          source: "openmaptiles",
          "source-layer": "transportation",
          filter: ["match", ["get", "class"], ["motorway", "trunk", "primary", "secondary", "tertiary"], true, false],
          layout: { "line-cap": "round", "line-join": "round" },
          paint: {
            "line-color": "rgba(0,0,0,0.75)",
            "line-width": ["interpolate", ["exponential", 1.2], ["zoom"], 6, 1.4, 10, 2.8, 15, 8],
          },
        },
        {
          id: "satellite-road",
          type: "line",
          source: "openmaptiles",
          "source-layer": "transportation",
          filter: ["match", ["get", "class"], ["motorway", "trunk", "primary", "secondary", "tertiary"], true, false],
          layout: { "line-cap": "round", "line-join": "round" },
          paint: {
            "line-color": ["match", ["get", "class"], ["motorway", "trunk"], "#f6c453", ["primary"], "#ffd37a", "#ffffff"],
            "line-width": ["interpolate", ["exponential", 1.2], ["zoom"], 6, 0.8, 10, 1.6, 15, 5],
          },
        },
        {
          id: "satellite-minor-road",
          type: "line",
          source: "openmaptiles",
          "source-layer": "transportation",
          minzoom: 12,
          filter: ["match", ["get", "class"], ["minor", "service", "track"], true, false],
          layout: { "line-cap": "round", "line-join": "round" },
          paint: {
            "line-color": "rgba(255,255,255,0.86)",
            "line-width": ["interpolate", ["exponential", 1.2], ["zoom"], 12, 0.6, 16, 3.2],
          },
        },
        {
          id: "satellite-road-label",
          type: "symbol",
          source: "openmaptiles",
          "source-layer": "transportation_name",
          minzoom: 12,
          filter: ["match", ["geometry-type"], ["LineString", "MultiLineString"], true, false],
          layout: {
            "symbol-placement": "line",
            "text-field": ["coalesce", ["get", "name_en"], ["get", "name"]],
            "text-font": ["Noto Sans Regular"],
            "text-size": ["interpolate", ["linear"], ["zoom"], 12, 11, 15, 13],
          },
          paint: {
            "text-color": "#ffffff",
            "text-halo-color": "rgba(0,0,0,0.8)",
            "text-halo-width": 1.4,
          },
        },
        {
          id: "satellite-place-label",
          type: "symbol",
          source: "openmaptiles",
          "source-layer": "place",
          filter: ["match", ["get", "class"], ["country", "state", "city", "town", "village"], true, false],
          layout: {
            "text-field": ["coalesce", ["get", "name_en"], ["get", "name"]],
            "text-font": ["Noto Sans Bold"],
            "text-size": ["interpolate", ["linear"], ["zoom"], 4, 11, 8, 14, 12, 18],
            "text-max-width": 9,
          },
          paint: {
            "text-color": "#ffffff",
            "text-halo-color": "rgba(0,0,0,0.9)",
            "text-halo-width": 1.8,
          },
        },
      ],
    },
  },
  {
    id: "esri-hybrid",
    label: "Hybrid",
    style: {
      version: 8,
      sources: {
        "esri-imagery": {
          type: "raster",
          tiles: [
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
          ],
          tileSize: 256,
          maxzoom: 19,
          attribution: "Tiles &copy; Esri",
        },
        "esri-roads": {
          type: "raster",
          tiles: [
            "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}",
          ],
          tileSize: 256,
          maxzoom: 19,
          attribution: "Roads &copy; Esri",
        },
        "esri-labels": {
          type: "raster",
          tiles: [
            "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
          ],
          tileSize: 256,
          maxzoom: 19,
          attribution: "Labels &copy; Esri",
        },
      },
      layers: [
        { id: "esri-imagery", type: "raster", source: "esri-imagery" },
        { id: "esri-roads", type: "raster", source: "esri-roads" },
        { id: "esri-labels", type: "raster", source: "esri-labels" },
      ],
    },
  },
  {
    id: "opentopomap",
    label: "Topographic",
    style: {
      version: 8,
      sources: {
        "opentopomap": {
          type: "raster",
          tiles: [
            "https://a.tile.opentopomap.org/{z}/{x}/{y}.png",
            "https://b.tile.opentopomap.org/{z}/{x}/{y}.png",
            "https://c.tile.opentopomap.org/{z}/{x}/{y}.png",
          ],
          tileSize: 256,
          maxzoom: 17,
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://opentopomap.org">OpenTopoMap</a>',
        },
      },
      layers: [
        { id: "opentopomap", type: "raster", source: "opentopomap" },
      ],
    },
  },
  {
    id: "openfreemap-liberty",
    label: "Liberty",
    url: "https://tiles.openfreemap.org/styles/liberty",
  },
];

let currentStyle = baseStyles[0];
let currentData = null;
let currentVisibleFeatures = [];
let currentPopup = null;
let hoverPopup = null;
let activeStationPopupProperties = null;
let activeStationPopupId = null;
let hasLoadedInitialMap = false;
let minRainFilter = 0;
let lastRainHistoryLimit = 0;
let enabledStationSources = new Set(stationSources.map((source) => source.id));
let sourceStatus = {};
let rainScaleMax = 200;
let terrainEnabled = false;
let terrainExaggeration = 1;
let authState = loadStoredAuthState();
let longPressTimer = null;
let longPressStartPoint = null;
let didTriggerLongPress = false;
const terrainTileCache = new Map();


function parseStoredAuthState(rawValue) {
  if (!rawValue) {
    return {};
  }
  try {
    const parsed = JSON.parse(rawValue);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch (_error) {
    return {};
  }
}

function loadStoredAuthState() {
  try {
    return parseStoredAuthState(window.localStorage.getItem(AUTH_STORAGE_KEY));
  } catch (_error) {
    return {};
  }
}

function saveStoredAuthState(nextState) {
  authState = nextState;
  try {
    window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(nextState));
  } catch (_error) {
    // Private browsing or strict storage settings can block localStorage.
    // The in-memory state still works until the tab is closed.
  }
}

function randomHex(byteLength) {
  const values = new Uint8Array(byteLength);
  if (window.crypto?.getRandomValues) {
    window.crypto.getRandomValues(values);
  } else {
    for (let index = 0; index < values.length; index += 1) {
      values[index] = Math.floor(Math.random() * 256);
    }
  }
  return Array.from(values, (value) => value.toString(16).padStart(2, "0")).join("");
}

function ensureDeviceId() {
  if (authState.deviceId) {
    return authState.deviceId;
  }
  const deviceId = window.crypto?.randomUUID ? window.crypto.randomUUID() : `rm-${randomHex(16)}`;
  saveStoredAuthState({ ...authState, deviceId });
  return deviceId;
}

function authHeaders() {
  if (!AUTH_REQUIRED) {
    return {};
  }
  const headers = { "X-Rainmapper-Device": ensureDeviceId() };
  if (authState.sessionToken) {
    headers.Authorization = `Bearer ${authState.sessionToken}`;
  }
  return headers;
}

async function authFetch(url, options = {}) {
  const headers = new Headers(options.headers || {});
  Object.entries(authHeaders()).forEach(([key, value]) => headers.set(key, value));
  const response = await fetch(url, { ...options, headers });
  if (AUTH_REQUIRED && response.status === 401) {
    showLogin("Sign in to continue.");
  }
  return response;
}

function showLogin(message = "") {
  const overlay = document.getElementById("login-overlay");
  const error = document.getElementById("login-error");
  if (!overlay) {
    return;
  }
  overlay.hidden = false;
  document.body.classList.add("auth-open");
  if (error) {
    error.textContent = message;
  }
  window.setTimeout(() => document.getElementById("login-username")?.focus(), 0);
}

function hideLogin() {
  const overlay = document.getElementById("login-overlay");
  if (!overlay) {
    return;
  }
  overlay.hidden = true;
  document.body.classList.remove("auth-open");
}

async function validateStoredSession() {
  if (!AUTH_REQUIRED) {
    return true;
  }
  ensureDeviceId();
  if (!authState.sessionToken) {
    return false;
  }
  const response = await authFetch(`${AUTH_BASE}/session`, { method: "POST", cache: "no-store" });
  return response.ok;
}

async function loginWithPassword(username, password) {
  const response = await fetch(`${AUTH_BASE}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, device_id: ensureDeviceId() }),
  });
  let payload = {};
  try {
    payload = await response.json();
  } catch (_error) {
    payload = {};
  }
  if (!response.ok || !payload.ok) {
    throw new Error(payload.error || "Cannot sign in.");
  }
  saveStoredAuthState({
    deviceId: payload.device_id || authState.deviceId,
    sessionToken: payload.session_token,
    username: payload.username,
    name: payload.name,
    email: payload.email,
    role: payload.role,
  });
}

function setupLoginForm(onAuthenticated) {
  const form = document.getElementById("login-form");
  if (!form) {
    return;
  }
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const error = document.getElementById("login-error");
    const submit = form.querySelector("button[type='submit']");
    if (error) {
      error.textContent = "";
    }
    if (submit) {
      submit.disabled = true;
      submit.textContent = "Signing in...";
    }
    try {
      await loginWithPassword(
        document.getElementById("login-username")?.value || "",
        document.getElementById("login-password")?.value || "",
      );
      hideLogin();
      await onAuthenticated();
    } catch (errorMessage) {
      if (error) {
        error.textContent = errorMessage.message || "Cannot sign in.";
      }
    } finally {
      if (submit) {
        submit.disabled = false;
        submit.textContent = "Sign in";
      }
    }
  });
}

async function requireAuthBeforeStart() {
  if (!AUTH_REQUIRED) {
    return true;
  }
  const isValid = await validateStoredSession();
  if (isValid) {
    hideLogin();
    return true;
  }
  showLogin("Sign in to view this map.");
  return false;
}

function styleDefinition(style) {
  if (!style.style) {
    return style.url;
  }
  return JSON.parse(JSON.stringify(style.style));
}

const map = new maplibregl.Map({
  container: "map",
  style: styleDefinition(currentStyle),
  center: INITIAL_CENTER,
  zoom: INITIAL_ZOOM,
  maxPitch: 85,
  attributionControl: false,
});

map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-left");

const rainColorStops = [
  { ratio: 0, color: "#4ea5ff" },
  { ratio: 0.08, color: "#78c679" },
  { ratio: 0.18, color: "#fecc5c" },
  { ratio: 0.32, color: "#fd8d3c" },
  { ratio: 0.52, color: "#f03b20" },
  { ratio: 0.72, color: "#bd0026" },
  { ratio: 0.88, color: "#7a0177" },
  { ratio: 1, color: "#4b0055" },
];

function hexToRgb(hexColor) {
  const value = hexColor.replace("#", "");
  return [
    Number.parseInt(value.slice(0, 2), 16),
    Number.parseInt(value.slice(2, 4), 16),
    Number.parseInt(value.slice(4, 6), 16),
  ];
}

function rgbToHex([red, green, blue]) {
  return `#${[red, green, blue].map((value) => Math.round(value).toString(16).padStart(2, "0")).join("")}`;
}

function interpolateColor(fromColor, toColor, amount) {
  const from = hexToRgb(fromColor);
  const to = hexToRgb(toColor);
  return rgbToHex(from.map((value, index) => value + (to[index] - value) * amount));
}

function rainColor(total) {
  const value = Math.max(0, Number(total) || 0);
  const ratio = Math.min(1, value / rainScaleMax);
  for (let index = 1; index < rainColorStops.length; index += 1) {
    const current = rainColorStops[index];
    const previous = rainColorStops[index - 1];
    if (ratio <= current.ratio) {
      const span = current.ratio - previous.ratio || 1;
      return interpolateColor(previous.color, current.color, (ratio - previous.ratio) / span);
    }
  }
  return rainColorStops[rainColorStops.length - 1].color;
}

function rainScaleCeiling(maxRain) {
  const maxValue = Math.ceil(maxRain || 0);
  const ceilings = [10, 25, 50, 100, 150, 200, 300, 500, 750, 1000];
  const ceiling = ceilings.find((value) => maxValue <= value);
  if (ceiling) return ceiling;
  return Math.ceil(maxValue / 500) * 500;
}

function percentile(sortedValues, ratio) {
  if (sortedValues.length === 0) {
    return 0;
  }
  const index = (sortedValues.length - 1) * ratio;
  const lowerIndex = Math.floor(index);
  const upperIndex = Math.ceil(index);
  if (lowerIndex === upperIndex) {
    return sortedValues[lowerIndex];
  }
  const weight = index - lowerIndex;
  return sortedValues[lowerIndex] * (1 - weight) + sortedValues[upperIndex] * weight;
}

function robustRainScaleMaximum(features) {
  const positiveTotals = features
    .map(featureRainTotal)
    .filter((value) => value > 0)
    .sort((left, right) => left - right);

  if (positiveTotals.length === 0) {
    return 10;
  }

  // Use a high percentile instead of the absolute maximum so one bad outlier
  // does not flatten the whole color scale for the current period.
  const reference = positiveTotals.length < 20
    ? positiveTotals[positiveTotals.length - 1]
    : percentile(positiveTotals, 0.95) * 1.25;
  return rainScaleCeiling(reference);
}

function updateRainScale(features) {
  rainScaleMax = robustRainScaleMaximum(features);
  const labels = document.getElementById("rain-legend-labels");
  if (!labels) {
    return;
  }
  const values = [rainScaleMax, rainScaleMax * 0.85, rainScaleMax * 0.7, rainScaleMax * 0.55, rainScaleMax * 0.4, rainScaleMax * 0.25, rainScaleMax * 0.12, 0];
  labels.innerHTML = values.map((value, index) => {
    const rounded = Math.round(value);
    return `<span>${index === 0 ? `${rounded}+` : rounded}</span>`;
  }).join("");
}

function markerRadius(total) {
  if (!Number.isFinite(total)) return 5;
  return Math.max(5, Math.min(24, 5 + Math.sqrt(Math.max(total, 0)) * 1.2));
}

function visibleFeatures(features) {
  return features.filter((feature) => {
    const coordinates = feature.geometry?.coordinates || [];
    const lon = Number(coordinates[0]);
    const lat = Number(coordinates[1]);
    return Number.isFinite(lat)
      && Number.isFinite(lon)
      && lon >= DISPLAY_BOUNDS[0][0]
      && lon <= DISPLAY_BOUNDS[1][0]
      && lat >= DISPLAY_BOUNDS[0][1]
      && lat <= DISPLAY_BOUNDS[1][1];
  });
}

function prepareFeature(feature) {
  const total = Number(feature.properties?.Total || 0);
  const source = feature.properties?.Source || inferStationSource(feature.properties?.["Codi Estació"]);
  return {
    ...feature,
    properties: {
      ...(feature.properties || {}),
      Source: source,
      rain_color: rainColor(total),
      marker_radius: markerRadius(total),
    },
  };
}

function featureRainTotal(feature) {
  const total = Number(feature.properties?.Total || 0);
  return Number.isFinite(total) ? total : 0;
}

function inferStationSource(stationCode) {
  const code = String(stationCode || "").trim().toUpperCase();
  if (code.startsWith("ES") && code.length >= 15) {
    return "Meteoclimatic";
  }
  if (code.startsWith("I")) {
    return "Wunderground";
  }
  if (code.length === 2) {
    return "Meteocat";
  }
  return "Unknown";
}

function featureStationSource(feature) {
  return feature.properties?.Source || inferStationSource(feature.properties?.["Codi Estació"]);
}

function filteredFeatures(features) {
  return features.filter((feature) => (
    featureRainTotal(feature) >= minRainFilter
    && enabledStationSources.has(featureStationSource(feature))
  ));
}

function sourceStatusClass(status) {
  const normalized = String(status || "").toUpperCase();
  if (normalized === "OK") return "source-status-ok";
  if (["STALE", "PENDING", "DISABLED"].includes(normalized)) return "source-status-warn";
  if (normalized === "NOK") return "source-status-danger";
  return "source-status-unknown";
}

function updateSourceStatusControls() {
  document.querySelectorAll("[data-source-status]").forEach((element) => {
    const sourceName = element.dataset.sourceStatus;
    const statusPayload = sourceStatus[sourceName] || {};
    const status = statusPayload.status || "Unknown";
    const rows = Number(statusPayload.rows);
    element.textContent = Number.isFinite(rows) && rows > 0 ? `${status} · ${rows}` : status;
    element.className = `source-status-pill ${sourceStatusClass(status)}`;
    element.title = statusPayload.message || "No source status available for the loaded data.";
  });
}

async function loadSourceStatus() {
  try {
    const response = await authFetch(`${DATA_BASE}source_status.json`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Cannot load source status: ${response.status}`);
    }
    const payload = await response.json();
    sourceStatus = payload.sources || {};
  } catch (_error) {
    sourceStatus = {};
  }
  updateSourceStatusControls();
}

function updateMinRainControl(features) {
  const maxRain = features.reduce((maxValue, feature) => Math.max(maxValue, featureRainTotal(feature)), 0);
  const sliderMax = Math.max(10, Math.ceil(maxRain / 10) * 10);
  const slider = document.getElementById("min-rain-filter");
  slider.max = String(sliderMax);
  if (minRainFilter > sliderMax) {
    minRainFilter = sliderMax;
    slider.value = String(minRainFilter);
  }
  updateMinRainValue();
}

function updateMinRainValue() {
  document.getElementById("min-rain-value").textContent = `${minRainFilter} mm`;
}

function rainHistoryIndexes(properties) {
  return Object.keys(properties || {})
    .map((key) => {
      const match = key.match(/^Data_Pluja_(\d+)$/);
      return match ? Number(match[1]) : null;
    })
    .filter((index) => Number.isInteger(index) && index > 0)
    .sort((a, b) => a - b);
}

function maxRainHistoryRecords(features) {
  return features.reduce((maxValue, feature) => (
    Math.max(maxValue, rainHistoryIndexes(feature.properties || {}).length)
  ), 0);
}

function updateLastRainHistoryValue() {
  const output = document.getElementById("last-rain-history-value");
  output.textContent = lastRainHistoryLimit > 0 ? `${lastRainHistoryLimit} records` : "-";
}

function updateLastRainHistoryControl(features) {
  const maxRecords = maxRainHistoryRecords(features);
  const slider = document.getElementById("last-rain-history-filter");
  if (maxRecords <= 0) {
    lastRainHistoryLimit = 0;
    slider.disabled = true;
    slider.max = "1";
    slider.value = "1";
    updateLastRainHistoryValue();
    return;
  }

  slider.disabled = false;
  slider.max = String(maxRecords);
  if (lastRainHistoryLimit <= 0 || lastRainHistoryLimit > maxRecords) {
    lastRainHistoryLimit = maxRecords;
  }
  slider.value = String(lastRainHistoryLimit);
  updateLastRainHistoryValue();
}

function refreshCurrentStationPopup() {
  if (!currentPopup || !activeStationPopupProperties) {
    return;
  }
  currentPopup.setHTML(popupContent(activeStationPopupProperties));
}

function stationIdFromProperties(properties) {
  return String(properties?.["Codi Estació"] || "").trim();
}

function findFeatureByStationId(features, stationId) {
  if (!stationId) {
    return null;
  }
  return features.find((feature) => stationIdFromProperties(feature.properties) === stationId) || null;
}

function openStationPopup(feature) {
  if (!feature) {
    return;
  }

  const coordinates = feature.geometry.coordinates.slice();
  const properties = feature.properties || {};
  activeStationPopupProperties = properties;
  activeStationPopupId = stationIdFromProperties(properties);
  closeHoverPopup();
  if (currentPopup) {
    currentPopup.remove();
  }
  const stationPopup = new maplibregl.Popup({
    closeButton: false,
    closeOnClick: true,
    maxWidth: "320px",
    anchor: "left",
    offset: 8,
  })
    .setLngLat(coordinates)
    .setHTML(popupContent(properties))
    .addTo(map);
  currentPopup = stationPopup;
  stationPopup.on("close", () => {
    if (currentPopup === stationPopup) {
      currentPopup = null;
      activeStationPopupProperties = null;
      activeStationPopupId = null;
    }
  });
}

function supportsHoverPopups() {
  return window.matchMedia("(hover: hover) and (pointer: fine)").matches;
}

function closeHoverPopup() {
  if (!hoverPopup) {
    return;
  }
  hoverPopup.remove();
  hoverPopup = null;
}

function showHoverPopup(feature) {
  if (!supportsHoverPopups() || map.getZoom() < HOVER_POPUP_MIN_ZOOM || currentPopup) {
    closeHoverPopup();
    return;
  }

  const coordinates = feature.geometry.coordinates.slice();
  const htmlContent = popupContent(feature.properties || {});
  if (!hoverPopup) {
    hoverPopup = new maplibregl.Popup({
      closeButton: false,
      closeOnClick: false,
      maxWidth: "320px",
      anchor: "left",
      offset: 8,
    });
  }
  hoverPopup
    .setLngLat(coordinates)
    .setHTML(htmlContent)
    .addTo(map);
}

function refreshFilteredData() {
  if (!currentVisibleFeatures.length) {
    return;
  }

  const selectedPeriod = document.getElementById("map-selector").value;
  const features = filteredFeatures(currentVisibleFeatures);
  const popupStationId = activeStationPopupId;
  currentData = {
    type: "FeatureCollection",
    metadata: currentData?.metadata || {},
    features,
  };

  if (currentPopup) {
    currentPopup.remove();
    currentPopup = null;
    activeStationPopupProperties = null;
    activeStationPopupId = null;
  }

  addStationLayer();
  updateSummary(selectedPeriod, features.length, currentVisibleFeatures.length);
  openStationPopup(findFeatureByStationId(features, popupStationId));
}

function ensureTerrainSource() {
  if (map.getSource(TERRAIN_SOURCE_ID)) {
    return;
  }

  map.addSource(TERRAIN_SOURCE_ID, {
    type: "raster-dem",
    tiles: TERRAIN_TILES,
    tileSize: 256,
    maxzoom: 15,
    encoding: "terrarium",
    attribution: "Elevation tiles &copy; Mapzen",
  });
}

function updateTerrainExaggerationValue() {
  document.getElementById("terrain-exaggeration-value").textContent = `${terrainExaggeration.toFixed(1)}x`;
}

function updateTerrainModeButton() {
  const terrainModeToggle = document.getElementById("terrain-mode-toggle");
  if (!terrainModeToggle) {
    return;
  }
  terrainModeToggle.textContent = terrainEnabled ? "3D" : "2D";
  terrainModeToggle.setAttribute("aria-pressed", String(terrainEnabled));
}

function applyTerrain() {
  if (!map.isStyleLoaded()) {
    return;
  }

  if (!terrainEnabled) {
    map.setTerrain(null);
    return;
  }

  try {
    ensureTerrainSource();
    map.setTerrain({
      source: TERRAIN_SOURCE_ID,
      exaggeration: terrainExaggeration,
    });
  } catch (error) {
    terrainEnabled = false;
    const terrainToggle = document.getElementById("terrain-toggle");
    const terrainSlider = document.getElementById("terrain-exaggeration");
    if (terrainToggle) {
      terrainToggle.checked = false;
    }
    if (terrainSlider) {
      terrainSlider.disabled = true;
    }
    updateTerrainModeButton();
    console.warn("Cannot enable terrain", error);
  }
}

function setTerrainEnabled(enabled) {
  const terrainToggle = document.getElementById("terrain-toggle");
  const terrainSlider = document.getElementById("terrain-exaggeration");
  terrainEnabled = enabled;
  if (terrainToggle) {
    terrainToggle.checked = terrainEnabled;
  }
  if (terrainSlider) {
    terrainSlider.disabled = !terrainEnabled;
  }
  updateTerrainModeButton();
  applyTerrain();
}

function isEditableKeyboardTarget(target) {
  if (!target) {
    return false;
  }

  const tagName = target.tagName?.toLowerCase();
  return target.isContentEditable || ["input", "select", "textarea"].includes(tagName);
}

function setupKeyboardShortcuts() {
  document.addEventListener("keydown", (event) => {
    if (event.defaultPrevented || event.repeat || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) {
      return;
    }
    if (isEditableKeyboardTarget(event.target)) {
      return;
    }
    if (event.key.toLowerCase() === "t") {
      event.preventDefault();
      setTerrainEnabled(!terrainEnabled);
    }
  });
}

function addStationLayer() {
  if (!currentData || !map.isStyleLoaded()) {
    return false;
  }

  if (map.getLayer(CIRCLE_LAYER_ID)) {
    map.removeLayer(CIRCLE_LAYER_ID);
  }
  if (map.getSource(SOURCE_ID)) {
    map.removeSource(SOURCE_ID);
  }

  map.addSource(SOURCE_ID, {
    type: "geojson",
    data: currentData,
  });
  map.addLayer({
    id: CIRCLE_LAYER_ID,
    type: "circle",
    source: SOURCE_ID,
    paint: {
      "circle-radius": ["get", "marker_radius"],
      "circle-color": ["get", "rain_color"],
      "circle-opacity": 0.72,
      "circle-stroke-color": "#111923",
      "circle-stroke-width": 1.2,
    },
  });
  applyTerrain();
  return true;
}

function reloadCurrentPeriodAfterStyleChange(center, zoom, attempt = 0) {
  if (!map.isStyleLoaded()) {
    if (attempt < 40) {
      window.setTimeout(() => reloadCurrentPeriodAfterStyleChange(center, zoom, attempt + 1), 100);
    }
    return;
  }

  applyTerrain();
  map.jumpTo({ center, zoom });
  const selectedPeriod = document.getElementById("map-selector").value;
  loadMap(selectedPeriod)
    .then(() => {
      map.jumpTo({ center, zoom });
    })
    .catch((error) => {
      document.getElementById("summary").textContent = error.message;
    });
}

function popupContent(properties) {
  const station = properties["Codi Estació"] || "";
  const name = properties["Estació"] || "Unknown station";
  const source = properties.Source || inferStationSource(station);
  const town = properties["Municipi"] || "Unknown town";
  const province = properties["Provincia"] || "";
  const altitude = properties["Altitud"] || "-";
  const total = Number(properties["Total"] || 0).toFixed(1);
  const lastReading = properties["Ultima Lectura"] || "-";
  const lastRain = lastRainRecord(properties);
  const rainHistory = recentRainHistory(properties);

  return `
    <div class="popup-title">${station} · ${name}</div>
    <div class="popup-row"><strong>Source:</strong> ${source}</div>
    <div class="popup-row popup-metrics"><span><strong>Rain:</strong> ${total} mm</span><span><strong>Last:</strong> ${lastRain}</span></div>
    <div class="popup-row"><strong>Location:</strong> ${town}${province ? `, ${province}` : ""}</div>
    <div class="popup-row"><strong>Altitude:</strong> ${altitude} m</div>
    <div class="popup-row"><strong>Last reading:</strong> ${lastReading}</div>
    ${rainHistory}
  `;
}

function terrainPopupContent(elevation, lngLat, status = "loading") {
  const latitude = lngLat.lat.toFixed(5);
  const longitude = lngLat.lng.toFixed(5);
  if (!Number.isFinite(elevation)) {
    const altitudeText = status === "error" ? "unavailable" : "loading";
    const noteText = status === "error"
      ? "External Terrarium DEM unavailable"
      : "Loading external Terrarium DEM";
    return `
      <div class="popup-title">Terrain</div>
      <div class="popup-row"><strong>Altitude:</strong> ${altitudeText}</div>
      <div class="popup-row terrain-note">${noteText}</div>
      <div class="popup-row terrain-coordinates">${latitude}, ${longitude}</div>
    `;
  }

  return `
    <div class="popup-title">Terrain</div>
    <div class="popup-row"><strong>Altitude:</strong> ${Math.round(elevation).toLocaleString("en-GB")} m</div>
    <div class="popup-row terrain-note">External Terrarium DEM</div>
    <div class="popup-row terrain-coordinates">${latitude}, ${longitude}</div>
  `;
}

function terrariumTileForLngLat(lngLat, zoom) {
  const latitude = Math.max(Math.min(lngLat.lat, 85.05112878), -85.05112878);
  const longitude = ((((lngLat.lng + 180) % 360) + 360) % 360) - 180;
  const latRad = latitude * Math.PI / 180;
  const scale = 2 ** zoom;
  const xFloat = (longitude + 180) / 360 * scale;
  const yFloat = (1 - Math.asinh(Math.tan(latRad)) / Math.PI) / 2 * scale;
  const x = Math.min(Math.max(Math.floor(xFloat), 0), scale - 1);
  const y = Math.min(Math.max(Math.floor(yFloat), 0), scale - 1);
  const pixelX = Math.min(Math.floor((xFloat - x) * 256), 255);
  const pixelY = Math.min(Math.floor((yFloat - y) * 256), 255);

  return { x, y, pixelX, pixelY, zoom };
}

function decodeTerrariumPixel(red, green, blue) {
  return (red * 256 + green + blue / 256) - 32768;
}

function loadTerrariumTile(tile) {
  const cacheKey = `${tile.zoom}/${tile.x}/${tile.y}`;
  if (terrainTileCache.has(cacheKey)) {
    return terrainTileCache.get(cacheKey);
  }

  const tileUrl = TERRAIN_TILES[0]
    .replace("{z}", tile.zoom)
    .replace("{x}", tile.x)
    .replace("{y}", tile.y);
  const imagePromise = new Promise((resolve, reject) => {
    const image = new Image();
    image.crossOrigin = "anonymous";
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error(`Cannot load terrain tile ${tileUrl}`));
    image.src = tileUrl;
  });

  terrainTileCache.set(cacheKey, imagePromise);
  return imagePromise;
}

async function queryTerrariumElevation(lngLat) {
  const tile = terrariumTileForLngLat(lngLat, TERRAIN_ELEVATION_ZOOM);
  const image = await loadTerrariumTile(tile);
  const canvas = document.createElement("canvas");
  canvas.width = 1;
  canvas.height = 1;
  const context = canvas.getContext("2d");
  context.drawImage(image, tile.pixelX, tile.pixelY, 1, 1, 0, 0, 1, 1);
  const [red, green, blue] = context.getImageData(0, 0, 1, 1).data;
  return decodeTerrariumPixel(red, green, blue);
}

function clearLongPressTimer() {
  if (longPressTimer) {
    window.clearTimeout(longPressTimer);
    longPressTimer = null;
  }
}

function showTerrainPopup(lngLat) {
  if (currentPopup) {
    currentPopup.remove();
  }
  activeStationPopupProperties = null;
  activeStationPopupId = null;

  const terrainPopup = new maplibregl.Popup({
    closeButton: false,
    closeOnClick: true,
    maxWidth: "260px",
    anchor: "left",
    offset: 8,
  })
    .setLngLat(lngLat)
    .setHTML(terrainPopupContent(null, lngLat))
    .addTo(map);
  currentPopup = terrainPopup;
  terrainPopup.on("close", () => {
    if (currentPopup === terrainPopup) {
      currentPopup = null;
      activeStationPopupProperties = null;
      activeStationPopupId = null;
    }
  });

  queryTerrariumElevation(lngLat)
    .then((elevation) => {
      if (currentPopup === terrainPopup && Number.isFinite(elevation)) {
        terrainPopup.setHTML(terrainPopupContent(elevation, lngLat));
      }
    })
    .catch((error) => {
      console.warn("Cannot query terrain elevation", error);
      if (currentPopup === terrainPopup) {
        terrainPopup.setHTML(terrainPopupContent(null, lngLat, "error"));
      }
    });
}

function setupLongPressElevation() {
  function startLongPress(event) {
    didTriggerLongPress = false;
    longPressStartPoint = event.point;
    clearLongPressTimer();
    longPressTimer = window.setTimeout(() => {
      didTriggerLongPress = true;
      showTerrainPopup(event.lngLat);
    }, LONG_PRESS_MS);
  }

  function cancelLongPress() {
    clearLongPressTimer();
    longPressStartPoint = null;
  }

  function cancelLongPressOnMove(event) {
    if (!longPressStartPoint) {
      return;
    }

    const deltaX = Math.abs(event.point.x - longPressStartPoint.x);
    const deltaY = Math.abs(event.point.y - longPressStartPoint.y);
    if (deltaX > LONG_PRESS_MOVE_TOLERANCE_PX || deltaY > LONG_PRESS_MOVE_TOLERANCE_PX) {
      cancelLongPress();
    }
  }

  map.on("mousedown", startLongPress);
  map.on("touchstart", startLongPress);
  map.on("mousemove", cancelLongPressOnMove);
  map.on("touchmove", cancelLongPressOnMove);
  map.on("mouseup", cancelLongPress);
  map.on("touchend", cancelLongPress);
  map.on("dragstart", cancelLongPress);

  map.on("contextmenu", (event) => {
    if (event.originalEvent?.preventDefault) {
      event.originalEvent.preventDefault();
    }
    didTriggerLongPress = true;
    cancelLongPress();
    showTerrainPopup(event.lngLat);
  });
}

function recentRainHistory(properties) {
  const rows = [];
  const records = rainHistoryRecords(properties).slice(0, lastRainHistoryLimit || undefined);
  for (const record of records) {
    const hasRain = Number.isFinite(record.rainValue) && record.rainValue > 0;
    rows.push(`
      <tr class="${hasRain ? "rainy-day" : ""}">
        <td>${record.date}</td>
        <td>${record.daysAgo}</td>
        <td>${Number.isFinite(record.rainValue) ? record.rainValue.toFixed(1) : record.rain}</td>
        <td>${Number.isFinite(record.tempMaxValue) ? record.tempMaxValue.toFixed(1) : "-"}</td>
        <td>${Number.isFinite(record.tempMinValue) ? record.tempMinValue.toFixed(1) : "-"}</td>
      </tr>
    `);
  }

  if (rows.length === 0) {
    return "";
  }

  return `
    <details class="history">
      <summary>Last ${rows.length} records</summary>
      <table class="history-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Days ago</th>
            <th>Rain</th>
            <th>Tmax</th>
            <th>Tmin</th>
          </tr>
        </thead>
        <tbody>${rows.join("")}</tbody>
      </table>
    </details>
  `;
}

function parseRainDate(dateText) {
  if (!dateText || dateText === "None" || dateText === "NaT" || dateText === "nan") {
    return null;
  }
  const parts = String(dateText).split(/[/-]/).map((part) => Number(part));
  if (parts.length !== 3 || parts.some((part) => !Number.isInteger(part))) {
    return null;
  }
  const [first, second, third] = parts;
  const year = first > 1900 ? first : third;
  const month = second;
  const day = first > 1900 ? third : first;
  const parsedDate = new Date(year, month - 1, day);
  if (parsedDate.getFullYear() !== year || parsedDate.getMonth() !== month - 1 || parsedDate.getDate() !== day) {
    return null;
  }
  return parsedDate;
}

function formatRainDateDisplay(dateText) {
  const parsedDate = parseRainDate(dateText);
  if (!parsedDate) {
    return "-";
  }
  const year = parsedDate.getFullYear();
  const month = String(parsedDate.getMonth() + 1).padStart(2, "0");
  const day = String(parsedDate.getDate()).padStart(2, "0");
  return `${day}/${month}/${year}`;
}

function daysAgo(dateText) {
  const parsedDate = parseRainDate(dateText);
  if (!parsedDate) {
    return "-";
  }
  const today = new Date();
  const todayMidnight = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const recordMidnight = new Date(parsedDate.getFullYear(), parsedDate.getMonth(), parsedDate.getDate());
  return Math.floor((todayMidnight - recordMidnight) / 86400000);
}

function rainHistoryRecords(properties) {
  const records = [];
  for (const index of rainHistoryIndexes(properties)) {
    const suffix = String(index).padStart(2, "0");
    const date = properties[`Data_Pluja_${suffix}`];
    const rain = properties[`Pluja_Diaria_${suffix}`];
    const tempMax = properties[`Temp_Max_${suffix}`];
    const tempMin = properties[`Temp_Min_${suffix}`];
    if (!date || date === "None" || date === "NaT" || date === "nan") {
      continue;
    }
    const rainValue = Number(rain);
    const tempMaxValue = Number(tempMax);
    const tempMinValue = Number(tempMin);
    records.push({
      date,
      daysAgo: daysAgo(date),
      rain,
      rainValue,
      tempMaxValue,
      tempMinValue,
    });
  }
  return records;
}

function lastRainRecord(properties) {
  const record = rainHistoryRecords(properties).find((item) => Number.isFinite(item.rainValue) && item.rainValue > 0);
  if (!record) {
    return "-";
  }
  return `${formatRainDateDisplay(record.date)} · ${record.rainValue.toFixed(1)} mm`;
}

function updateSummary(fileName, count, totalCount = count) {
  const summary = document.getElementById("summary");
  const stationText = `${count} station${count === 1 ? "" : "s"}`;
  const hasSourceFilter = enabledStationSources.size < stationSources.length;
  const hasAnyFilter = minRainFilter > 0 || hasSourceFilter;
  const mainParts = [periods[fileName], stationText];
  const detailParts = [];

  if (hasAnyFilter) {
    mainParts.push(`${totalCount} total`);
  }
  if (minRainFilter > 0) {
    detailParts.push(`Min: ${minRainFilter} mm`);
  }
  if (hasSourceFilter) {
    detailParts.push(`Sources: ${enabledStationSources.size}/${stationSources.length}`);
  }

  summary.replaceChildren();
  const mainLine = document.createElement("span");
  mainLine.className = "summary-main";
  mainLine.textContent = mainParts.join(" · ");
  summary.append(mainLine);
  if (detailParts.length > 0) {
    const filterLine = document.createElement("span");
    filterLine.className = "summary-filter";
    filterLine.textContent = detailParts.join(" · ");
    summary.append(filterLine);
  }
}

function updatePeriodTimeline(selectedFileName) {
  document.querySelectorAll(".period-timeline-button").forEach((button) => {
    const isSelected = button.dataset.period === selectedFileName;
    button.classList.toggle("is-active", isSelected);
    button.setAttribute("aria-current", isSelected ? "true" : "false");
  });
}

function renderPeriodTimeline() {
  const container = document.getElementById("period-timeline");
  const mapSelector = document.getElementById("map-selector");
  if (!container || !mapSelector) {
    return;
  }

  container.innerHTML = Object.entries(periods).map(([fileName, label]) => `
    <button class="period-timeline-button" type="button" data-period="${fileName}">
      <span>${label.replace(" days", "d").replace(" day", "d")}</span>
    </button>
  `).join("");

  container.addEventListener("click", (event) => {
    const button = event.target.closest(".period-timeline-button");
    if (!button) {
      return;
    }
    mapSelector.value = button.dataset.period;
    mapSelector.dispatchEvent(new Event("change"));
  });

  updatePeriodTimeline(mapSelector.value);
}

function updateGeneratedAt(generatedAt) {
  const generatedElement = document.getElementById("generated-at");
  if (!generatedAt) {
    generatedElement.textContent = "-";
    generatedElement.removeAttribute("datetime");
    return;
  }

  const generatedDate = new Date(generatedAt);
  if (Number.isNaN(generatedDate.getTime())) {
    generatedElement.textContent = generatedAt;
    generatedElement.setAttribute("datetime", generatedAt);
    return;
  }

  const datePart = new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "2-digit",
    year: "2-digit",
  }).format(generatedDate);
  const timePart = new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(generatedDate);
  generatedElement.textContent = `${datePart} - ${timePart}`;
  generatedElement.setAttribute("datetime", generatedAt);
}

function fitToData() {
  const features = currentData?.features || [];
  if (features.length === 0) {
    map.fitBounds(DISPLAY_BOUNDS, { padding: 24 });
    return;
  }

  const bounds = new maplibregl.LngLatBounds();
  features.forEach((feature) => bounds.extend(feature.geometry.coordinates));
  map.fitBounds(bounds, { padding: 24, duration: 0 });
}

async function loadMap(fileName) {
  const url = `${DATA_BASE}${fileName}`;
  const response = await authFetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Cannot load ${url}: ${response.status}`);
  }
  const data = await response.json();
  const popupStationId = activeStationPopupId;
  const visible = visibleFeatures(data.features || []);
  updateRainScale(visible);
  const features = visible.map(prepareFeature);
  currentVisibleFeatures = features;
  updateMinRainControl(features);
  updateLastRainHistoryControl(features);
  const filtered = filteredFeatures(features);
  currentData = {
    ...data,
    features: filtered,
  };

  if (currentPopup) {
    currentPopup.remove();
    currentPopup = null;
    activeStationPopupProperties = null;
    activeStationPopupId = null;
  }

  addStationLayer();
  updateSummary(fileName, filtered.length, features.length);
  updateGeneratedAt(data.metadata?.generated_at);
  updatePeriodTimeline(fileName);
  openStationPopup(findFeatureByStationId(filtered, popupStationId));

  if (!hasLoadedInitialMap) {
    hasLoadedInitialMap = true;
    fitToData();
  }
}

function renderLayerSwitcher() {
  const container = document.getElementById("layer-switcher");
  container.innerHTML = baseStyles.map((style) => `
    <label>
      <input type="radio" name="base-style" value="${style.id}" ${style.id === currentStyle.id ? "checked" : ""}>
      <span>${style.label}</span>
    </label>
  `).join("");

  container.addEventListener("change", (event) => {
    const nextStyle = baseStyles.find((style) => style.id === event.target.value);
    if (!nextStyle) {
      return;
    }

    currentStyle = nextStyle;
    const center = map.getCenter();
    const zoom = map.getZoom();
    let reloadedCurrentPeriod = false;
    const reloadOnce = () => {
      if (reloadedCurrentPeriod) {
        return;
      }
      reloadedCurrentPeriod = true;
      reloadCurrentPeriodAfterStyleChange(center, zoom);
    };

    map.once("idle", reloadOnce);
    map.setStyle(styleDefinition(currentStyle));
    window.setTimeout(reloadOnce, 600);
  });
}

function renderSettingsPanel() {
  const toggle = document.getElementById("settings-toggle");
  const northToggle = document.getElementById("north-toggle");
  const infoToggle = document.getElementById("info-toggle");
  const attributionPanel = document.getElementById("map-attribution");
  const panel = document.getElementById("map-settings");
  const slider = document.getElementById("min-rain-filter");
  const historySlider = document.getElementById("last-rain-history-filter");
  const terrainToggle = document.getElementById("terrain-toggle");
  const terrainSlider = document.getElementById("terrain-exaggeration");
  const terrainModeToggle = document.getElementById("terrain-mode-toggle");
  const sourceInputs = Array.from(panel.querySelectorAll("input[name='station-source']"));

  const setSettingsOpen = (isOpen) => {
    panel.toggleAttribute("hidden", !isOpen);
    toggle.setAttribute("aria-expanded", String(isOpen));
    document.body.classList.toggle("settings-open", isOpen);
  };

  toggle.addEventListener("click", () => {
    setSettingsOpen(panel.hasAttribute("hidden"));
  });

  map.on("click", () => {
    if (!panel.hasAttribute("hidden")) {
      setSettingsOpen(false);
    }
  });

  northToggle.addEventListener("click", () => {
    map.easeTo({ bearing: 0, duration: 350 });
  });

  infoToggle.addEventListener("click", () => {
    const isOpen = attributionPanel.hasAttribute("hidden");
    attributionPanel.toggleAttribute("hidden", !isOpen);
    infoToggle.setAttribute("aria-expanded", String(isOpen));
  });

  slider.addEventListener("input", (event) => {
    minRainFilter = Number(event.target.value);
    updateMinRainValue();
    refreshFilteredData();
  });

  historySlider.addEventListener("input", (event) => {
    lastRainHistoryLimit = Number(event.target.value);
    updateLastRainHistoryValue();
    refreshCurrentStationPopup();
  });

  sourceInputs.forEach((input) => {
    input.addEventListener("change", () => {
      const selectedSources = sourceInputs.filter((sourceInput) => sourceInput.checked);
      if (selectedSources.length === 0) {
        input.checked = true;
        return;
      }
      enabledStationSources = new Set(selectedSources.map((sourceInput) => sourceInput.value));
      refreshFilteredData();
    });
  });

  updateTerrainExaggerationValue();

  terrainToggle.addEventListener("change", (event) => {
    setTerrainEnabled(event.target.checked);
  });

  terrainModeToggle.addEventListener("click", () => {
    setTerrainEnabled(!terrainEnabled);
  });

  terrainSlider.addEventListener("input", (event) => {
    terrainExaggeration = Number(event.target.value);
    updateTerrainExaggerationValue();
    applyTerrain();
  });
}

async function startViewer() {
  await loadSourceStatus();
  await loadMap(document.getElementById("map-selector").value);
}

map.on("load", async () => {
  renderLayerSwitcher();
  renderPeriodTimeline();
  renderSettingsPanel();
  setupKeyboardShortcuts();
  setupLongPressElevation();
  updateTerrainModeButton();
  applyTerrain();
  setupLoginForm(startViewer);
  const authenticated = await requireAuthBeforeStart();
  if (!authenticated) {
    return;
  }
  startViewer().catch((error) => {
    document.getElementById("summary").textContent = error.message;
  });
});

map.on("click", CIRCLE_LAYER_ID, (event) => {
  if (didTriggerLongPress) {
    didTriggerLongPress = false;
    return;
  }

  const feature = event.features?.[0];
  if (!feature) {
    return;
  }
  openStationPopup(feature);
});

map.on("mouseenter", CIRCLE_LAYER_ID, () => {
  map.getCanvas().style.cursor = "pointer";
});

map.on("mousemove", CIRCLE_LAYER_ID, (event) => {
  const feature = event.features?.[0];
  if (feature) {
    showHoverPopup(feature);
  }
});

map.on("mouseleave", CIRCLE_LAYER_ID, () => {
  map.getCanvas().style.cursor = "";
  closeHoverPopup();
});

map.on("zoom", () => {
  if (map.getZoom() < HOVER_POPUP_MIN_ZOOM) {
    closeHoverPopup();
  }
});

document.getElementById("map-selector").addEventListener("change", (event) => {
  loadMap(event.target.value).catch((error) => {
    document.getElementById("summary").textContent = error.message;
  });
});
