const viewerConfig = window.RAINMAPPER_CONFIG || {};
const defaultDataBase = viewerConfig.dataBase || (window.location.pathname.includes("/maplibre-viewer/")
  ? "../../../docker-data/PublicData/"
  : "data/");
const DATA_BASE = new URLSearchParams(window.location.search).get("data") || defaultDataBase;
const AUTH_REQUIRED = Boolean(viewerConfig.authRequired);
const AUTH_BASE = viewerConfig.authBase || "/auth";
const AUTH_STORAGE_KEY = "rainmapperMaplibreAuth";
const EXPERIMENTAL_HEATMAP = Boolean(viewerConfig.experimentalHeatmap);

const periods = {
  "01d.geojson": "1 day",
  "07d.geojson": "7 days",
  "14d.geojson": "14 days",
  "21d.geojson": "21 days",
  "30d.geojson": "30 days",
  "60d.geojson": "60 days",
  "90d.geojson": "90 days",
};

const supportedLanguages = ["en", "es", "ca"];
let translations = {
  en: {
    loadingMapData: "Loading map data...",
    selectedPeriod: "selected period"
  }
};

const FALLBACK_BOUNDS = [
  [-2.5, 39.0],
  [4.2, 43.7],
];
const INITIAL_CENTER = [2.1, 41.7];
const INITIAL_ZOOM = 7;
const SOURCE_ID = "stations";
const HEATMAP_SOURCE_ID = "stations-heatmap";
const HEATMAP_LAYER_ID = "station-rain-heatmap";
const ESTIMATED_FIELD_SOURCE_ID = "estimated-field";
const ESTIMATED_FIELD_LAYER_ID = "station-estimated-field";
const CIRCLE_LAYER_ID = "station-circles";
const TERRAIN_SOURCE_ID = "rainmapper-terrain-dem";
const TERRAIN_TILES = [
  "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png",
];
const TERRAIN_ELEVATION_ZOOM = 15;
const LONG_PRESS_MS = 650;
const LONG_PRESS_MOVE_TOLERANCE_PX = 12;
const configuredHoverPopupMinZoom = Number(viewerConfig.hoverPopupMinZoom);
const HOVER_POPUP_MIN_ZOOM = Number.isFinite(configuredHoverPopupMinZoom)
  ? Math.max(0, Math.min(22, configuredHoverPopupMinZoom))
  : 6;
const configuredHeatmapDefaults = viewerConfig.heatmapDefaults || {};
const DEFAULT_HEATMAP_OPACITY = clampNumber(Number(configuredHeatmapDefaults.opacity), 0, 1, 0.65);
const DEFAULT_HEATMAP_RADIUS_SCALE = clampNumber(Number(configuredHeatmapDefaults.radiusScale), 0.5, 3, 0.9);
const DEFAULT_HEATMAP_INTENSITY_SCALE = clampNumber(Number(configuredHeatmapDefaults.intensityScale), 0.2, 2, 0.7);
const DEFAULT_HEATMAP_WEIGHT_CURVE = ["linear", "soft", "strong"].includes(configuredHeatmapDefaults.weightCurve)
  ? configuredHeatmapDefaults.weightCurve
  : "soft";
const configuredEstimatedField = viewerConfig.estimatedField || {};
const configuredEstimatedFieldDefaults = configuredEstimatedField.defaults || {};
const ESTIMATED_FIELD_RADIUS_OPTIONS = ["small", "medium", "large"];
const ESTIMATED_FIELD_QUALITY_OPTIONS = ["low", "medium", "high"];
const ESTIMATED_FIELD_SMOOTHING_OPTIONS = ["smooth", "balanced", "local"];
const DEFAULT_ESTIMATED_FIELD_ENABLED = Boolean(configuredEstimatedFieldDefaults.enabled);
const DEFAULT_ESTIMATED_FIELD_OPACITY = clampNumber(Number(configuredEstimatedFieldDefaults.opacity), 0, 1, 0.65);
const DEFAULT_ESTIMATED_FIELD_RADIUS = ESTIMATED_FIELD_RADIUS_OPTIONS.includes(configuredEstimatedFieldDefaults.radius)
  ? configuredEstimatedFieldDefaults.radius
  : "medium";
const DEFAULT_ESTIMATED_FIELD_QUALITY = ESTIMATED_FIELD_QUALITY_OPTIONS.includes(configuredEstimatedFieldDefaults.quality)
  ? configuredEstimatedFieldDefaults.quality
  : "medium";
const DEFAULT_ESTIMATED_FIELD_SMOOTHING = ESTIMATED_FIELD_SMOOTHING_OPTIONS.includes(configuredEstimatedFieldDefaults.smoothing)
  ? configuredEstimatedFieldDefaults.smoothing
  : "balanced";
const DEFAULT_ESTIMATED_FIELD_ALTITUDE_CORRECTION = Boolean(configuredEstimatedFieldDefaults.altitudeCorrection);
const estimatedFieldGridConfig = configuredEstimatedField.grid || {};
const estimatedFieldSmoothingPowerConfig = configuredEstimatedField.smoothingPower || {};
const stationSources = [
  { id: "Meteocat", label: "Meteocat" },
  { id: "Meteoclimatic", label: "Meteoclimatic" },
  { id: "Wunderground", label: "Wunderground" },
  { id: "AEMET", label: "AEMET" },
  { id: "Unknown", label: "Unknown" },
];

const baseStyles = [
  {
    id: "esri-satellite-vector",
    label: "Satellite+",
    labelKey: "styleEsriSatelliteVector",
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
    labelKey: "styleEsriHybrid",
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
    labelKey: "styleOpenTopoMap",
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
    labelKey: "styleOpenFreeMapLiberty",
    url: "https://tiles.openfreemap.org/styles/liberty",
  },
];

let currentStyle = baseStyles[0];
let preferredMapStyleId = currentStyle.id;
let currentPeriodFileName = "21d.geojson";
let preferredPeriodFileName = currentPeriodFileName;
let currentLanguage = browserLanguage();
let currentData = null;
let currentHeatmapData = null;
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
let metricScaleMin = 0;
let metricScaleMax = 200;
let currentLayerMetric = "rain";
let heatmapEnabled = EXPERIMENTAL_HEATMAP;
let savedHeatmapEnabled = heatmapEnabled;
let heatmapOpacity = DEFAULT_HEATMAP_OPACITY;
let heatmapRadiusScale = DEFAULT_HEATMAP_RADIUS_SCALE;
let heatmapIntensityScale = DEFAULT_HEATMAP_INTENSITY_SCALE;
let heatmapWeightCurve = DEFAULT_HEATMAP_WEIGHT_CURVE;
let estimatedFieldEnabled = DEFAULT_ESTIMATED_FIELD_ENABLED;
let savedEstimatedFieldEnabled = estimatedFieldEnabled;
let estimatedFieldOpacity = DEFAULT_ESTIMATED_FIELD_OPACITY;
let estimatedFieldRadius = DEFAULT_ESTIMATED_FIELD_RADIUS;
let estimatedFieldQuality = DEFAULT_ESTIMATED_FIELD_QUALITY;
let estimatedFieldSmoothing = DEFAULT_ESTIMATED_FIELD_SMOOTHING;
let estimatedFieldAltitudeCorrection = DEFAULT_ESTIMATED_FIELD_ALTITUDE_CORRECTION;
let estimatedFieldUpdateTimer = null;
let baseStyleReloadPending = false;
let terrainEnabled = false;
let terrainExaggeration = 1;
let authState = loadStoredAuthState();
let pendingPasswordChange = null;
let isApplyingDeviceSettings = false;
let hasLoadedDeviceSettings = false;
let hasPendingDeviceSettingsChanges = false;
let savedMapView = null;
let lastSavedMapView = null;
let longPressTimer = null;
let longPressStartPoint = null;
let didTriggerLongPress = false;
let invalidFeatureCount = 0;
const terrainTileCache = new Map();


function authPermissionEnabled(fieldName) {
  if (authState && Object.prototype.hasOwnProperty.call(authState, fieldName)) {
    return authState[fieldName] === true;
  }
  return String(authState?.role || "").trim().toLowerCase() === "admin";
}

function canUseHeatmap() {
  return EXPERIMENTAL_HEATMAP || (AUTH_REQUIRED && authPermissionEnabled("canUseHeatmap"));
}

function canUseLayerMetrics() {
  return EXPERIMENTAL_HEATMAP || (AUTH_REQUIRED && authPermissionEnabled("canUseLayerMetrics"));
}

function canUseEstimatedField() {
  return AUTH_REQUIRED && authPermissionEnabled("canUseEstimatedField");
}

function browserLanguage() {
  const language = String(navigator.language || "en").slice(0, 2).toLowerCase();
  return supportedLanguages.includes(language) ? language : "en";
}

function normalizeTranslations(payload) {
  if (!payload || typeof payload !== "object") {
    return translations;
  }
  const normalized = { ...translations };
  supportedLanguages.forEach((language) => {
    if (payload[language] && typeof payload[language] === "object") {
      normalized[language] = {
        ...normalized.en,
        ...payload[language],
      };
    }
  });
  return normalized;
}

async function loadTranslations() {
  try {
    const response = await fetch("translations.json", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Cannot load translations: ${response.status}`);
    }
    translations = normalizeTranslations(await response.json());
  } catch (error) {
    console.warn("Cannot load translations, using built-in fallback", error);
  }
}

function t(key, params = {}) {
  const template = translations[currentLanguage]?.[key] || translations.en[key] || key;
  return Object.entries(params).reduce(
    (text, [name, value]) => text.replaceAll(`{${name}}`, String(value)),
    template,
  );
}

function periodKey(fileName) {
  return `period${String(fileName).slice(0, 3)}`;
}

function periodLabel(fileName) {
  return t(periodKey(fileName)) || periods[fileName] || t("selectedPeriod");
}

function periodShortLabel(fileName) {
  return periodLabel(fileName)
    .replace(" days", "d")
    .replace(" day", "d")
    .replace(" días", "d")
    .replace(" día", "d")
    .replace(" dies", "d")
    .replace(" dia", "d");
}

function styleLabel(style) {
  return t(style.labelKey) || style.label;
}

function sourceLabel(source) {
  return source === "Unknown" ? t("unknown") : source;
}

function setText(selector, text) {
  const element = document.querySelector(selector);
  if (element) {
    element.textContent = text;
  }
}

function setLabelText(controlId, text) {
  setText(`label[for="${controlId}"]`, text);
}

function clampNumber(value, minimum, maximum, fallback) {
  return Number.isFinite(value) ? Math.max(minimum, Math.min(maximum, value)) : fallback;
}

function updateHelpPanelText() {
  [
    ["#help-title", "mapHelp"],
    ["#help-rain-title", "helpRainTitle"],
    ["#help-rain-copy", "helpRainCopy"],
    ["#help-stations-title", "helpStationsTitle"],
    ["#help-stations-click", "helpStationsClick"],
    ["#help-stations-hover", "helpStationsHover"],
    ["#help-stations-history", "helpStationsHistory"],
    ["#help-controls-title", "helpControlsTitle"],
    ["#help-controls-settings", "helpControlsSettings"],
    ["#help-controls-terrain", "helpControlsTerrain"],
    ["#help-controls-layers", "helpControlsLayers"],
    ["#help-controls-north", "helpControlsNorth"],
    ["#help-controls-credits", "helpControlsCredits"],
    ["#help-filters-title", "helpFiltersTitle"],
    ["#help-filters-rain", "helpFiltersRain"],
    ["#help-filters-source", "helpFiltersSource"],
    ["#help-filters-history", "helpFiltersHistory"],
    ["#help-filters-save", "helpFiltersSave"],
    ["#help-filters-view", "helpFiltersView"],
    ["#help-terrain-title", "helpTerrainTitle"],
    ["#help-terrain-longpress", "helpTerrainLongPress"],
    ["#help-terrain-dem", "helpTerrainDem"],
    ["#help-data-title", "helpDataTitle"],
    ["#help-data-status", "helpDataStatus"],
    ["#help-data-invalid", "helpDataInvalid"],
    ["#help-data-auth", "helpDataAuth"],
  ].forEach(([selector, key]) => setText(selector, t(key)));
  setText("#help-stations-hover", t("helpStationsHover").replace("{zoom}", HOVER_POPUP_MIN_ZOOM));
}

function updatePeriodSelectLabels() {
  document.querySelectorAll("#map-selector option, #settings-period-selector option").forEach((option) => {
    option.textContent = periodLabel(option.value);
  });
}

function applyLanguage(language = currentLanguage) {
  currentLanguage = supportedLanguages.includes(language) ? language : "en";
  document.documentElement.lang = currentLanguage;

  const languageSelector = document.getElementById("language-selector");
  if (languageSelector) {
    languageSelector.value = currentLanguage;
  }

  setText("#summary", t("loadingMapData"));
  setText("#demo-zoom-level", `${t("zoom")} ${map ? map.getZoom().toFixed(2) : "-"}`);
  document.getElementById("demo-zoom-level")?.setAttribute("title", t("temporaryZoomIndicator"));

  setLabelText("language-selector", t("language"));
  setLabelText("settings-period-selector", t("period"));
  setLabelText("min-rain-filter", t("minRain"));
  setLabelText("last-rain-history-filter", t("lastRainsHistory"));
  setLabelText("layer-metric-selector", t("layerMetric"));
  setText("#heatmap-enabled-toggle + span", t("heatmap"));
  setLabelText("heatmap-weight-curve-selector", t("heatmapWeightCurve"));
  setLabelText("heatmap-opacity-filter", t("heatmapOpacity"));
  setLabelText("heatmap-radius-filter", t("heatmapRadius"));
  setLabelText("heatmap-intensity-filter", t("heatmapIntensity"));
  setText("#estimated-field-enabled-toggle + span", t("estimatedField"));
  setLabelText("estimated-field-opacity-filter", t("estimatedFieldOpacity"));
  setLabelText("estimated-field-radius-selector", t("estimatedFieldRadius"));
  setLabelText("estimated-field-quality-selector", t("estimatedFieldQuality"));
  setLabelText("estimated-field-smoothing-selector", t("estimatedFieldSmoothing"));
  setText("#estimated-field-altitude-correction-toggle + span", t("estimatedFieldAltitudeCorrection"));
  setLabelText("terrain-exaggeration", t("exaggeration"));
  setText("#layer-switcher legend", t("map"));
  setText(".source-settings-group legend", t("source"));
  setText("#settings-section-terrain legend", t("terrain"));
  setText("#save-map-view-default", t("setCurrentViewDefault"));
  setText("#settings-tab-general", t("settingsGeneral"));
  setText("#settings-tab-heatmap", t("heatmap"));
  setText("#reset-heatmap-defaults", t("resetHeatmapDefaults"));
  setText("#settings-tab-estimated-field", t("estimatedField"));
  setText("#reset-estimated-field-defaults", t("resetEstimatedFieldDefaults"));
  setText("#settings-tab-sources", t("sources"));
  setText("#settings-tab-terrain", t("terrain"));
  setText("#terrain-toggle + span", t("terrain3d"));
  setText("#login-fields label:nth-child(1) span", t("username"));
  setText("#login-fields label:nth-child(2) span", t("password"));
  setText("#password-change-fields label:nth-child(1) span", t("newPassword"));
  setText("#password-change-fields label:nth-child(2) span", t("repeatNewPassword"));
  setText("#map-attribution strong", t("credits"));
  document.querySelectorAll("input[name='station-source']").forEach((input) => {
    const label = input.closest("label")?.querySelector("span");
    if (label) {
      label.textContent = sourceLabel(input.value);
    }
  });

  const labelledElements = [
    ["#login-overlay", "Rainmapper login"],
    ["#settings-toggle", "mapSettings"],
    ["#terrain-mode-toggle", "toggle3dTerrain"],
    ["#quick-map-toggle", "mapLayer"],
    ["#quick-metric-toggle", "layerMetric"],
    ["#heatmap-toggle", "heatmap"],
    ["#estimated-field-toggle", "estimatedField"],
    ["#north-toggle", "faceNorth"],
    ["#info-toggle", "mapCredits"],
    ["#help-toggle", "mapHelp"],
    ["#map-attribution", "mapCredits"],
    ["#map-help", "mapHelp"],
    ["#quick-map-panel", "mapLayer"],
    ["#quick-metric-panel", "layerMetric"],
    ["#map-settings", "mapSettings"],
    ["#map-selector", "rainPeriod"],
    ["#period-timeline", "rainPeriod"],
    [".rain-legend", "rainLegend"],
  ];
  labelledElements.forEach(([selector, key]) => {
    const element = document.querySelector(selector);
    if (!element) {
      return;
    }
    const label = key === "Rainmapper login" ? key : t(key);
    element.setAttribute("aria-label", label);
    if (element.matches("button")) {
      element.setAttribute("title", label);
    }
  });

  updatePeriodSelectLabels();
  updateHelpPanelText();
  updateMinRainValue();
  updateLastRainHistoryValue();
  updateTerrainExaggerationValue();
  renderLayerMetricSelector();
  updateHeatmapOpacityValue();
  updateHeatmapRadiusValue();
  updateHeatmapIntensityValue();
  renderHeatmapWeightCurveSelector();
  updateMetricLegend();
  updateHeatmapToggle();
  renderLayerSwitcher();
  renderQuickMapPanelOptions();
  renderQuickMetricPanelOptions();
  renderPeriodTimeline();
  updateSourceStatusControls();
  updateTerrainModeButton();
  if (hasLoadedInitialMap) {
    updateSummary(
      currentPeriodFileName,
      currentData?.features?.length || 0,
      currentVisibleFeatures.length,
      invalidFeatureCount,
    );
  }
}


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
  updateSignedInUser();
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
    showLogin(t("signInContinue"));
  }
  return response;
}

function showLogin(message = "") {
  const overlay = document.getElementById("login-overlay");
  const error = document.getElementById("login-error");
  if (!overlay) {
    return;
  }
  setSignInMode();
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

function setSignInMode() {
  pendingPasswordChange = null;
  const title = document.getElementById("login-title");
  const copy = document.getElementById("login-copy");
  const loginFields = document.getElementById("login-fields");
  const changeFields = document.getElementById("password-change-fields");
  const submit = document.querySelector("#login-form button[type='submit']");
  if (title) {
    title.textContent = "Rainmapper";
  }
  if (copy) {
    copy.textContent = t("signInProtected");
  }
  if (loginFields) {
    loginFields.hidden = false;
  }
  if (changeFields) {
    changeFields.hidden = true;
  }
  const newPassword = document.getElementById("new-password");
  const repeatedPassword = document.getElementById("new-password-repeat");
  if (newPassword) {
    newPassword.value = "";
  }
  if (repeatedPassword) {
    repeatedPassword.value = "";
  }
  if (submit) {
    submit.textContent = t("signIn");
  }
}

function setPasswordChangeMode(username, currentPassword) {
  pendingPasswordChange = { username, currentPassword };
  const title = document.getElementById("login-title");
  const copy = document.getElementById("login-copy");
  const loginFields = document.getElementById("login-fields");
  const changeFields = document.getElementById("password-change-fields");
  const submit = document.querySelector("#login-form button[type='submit']");
  if (title) {
    title.textContent = t("changePassword");
  }
  if (copy) {
    copy.textContent = t("passwordReset");
  }
  if (loginFields) {
    loginFields.hidden = true;
  }
  if (changeFields) {
    changeFields.hidden = false;
  }
  if (submit) {
    submit.textContent = t("changePassword");
  }
  window.setTimeout(() => document.getElementById("new-password")?.focus(), 0);
}

async function validateStoredSession() {
  if (!AUTH_REQUIRED) {
    updateSignedInUser();
    return true;
  }
  ensureDeviceId();
  if (!authState.sessionToken) {
    updateSignedInUser();
    return false;
  }
  const response = await authFetch(`${AUTH_BASE}/session`, { method: "POST", cache: "no-store" });
  if (response.ok) {
    let payload = {};
    try {
      payload = await response.json();
    } catch (_error) {
      payload = {};
    }
    if (payload.user) {
      saveStoredAuthState({
        ...authState,
        username: payload.user.username,
        name: payload.user.name,
        email: payload.user.email,
        role: payload.user.role,
        canUseHeatmap: payload.user.can_use_heatmap === true,
        canUseLayerMetrics: payload.user.can_use_layer_metrics === true,
        canUseEstimatedField: payload.user.can_use_estimated_field === true,
      });
    }
  } else {
    saveStoredAuthState({ deviceId: authState.deviceId });
  }
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
  if (payload.code === "password_change_required") {
    const error = new Error(payload.error || t("passwordChangeRequired"));
    error.code = payload.code;
    error.username = payload.username || username;
    throw error;
  }
  if (!response.ok || !payload.ok) {
    throw new Error(payload.error || t("cannotSignIn"));
  }
  saveAuthenticatedPayload(payload);
}

async function changeRequiredPassword(username, currentPassword, newPassword) {
  const response = await fetch(`${AUTH_BASE}/change-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username,
      current_password: currentPassword,
      new_password: newPassword,
      device_id: ensureDeviceId(),
    }),
  });
  let payload = {};
  try {
    payload = await response.json();
  } catch (_error) {
    payload = {};
  }
  if (!response.ok || !payload.ok) {
    throw new Error(payload.error || t("cannotChangePassword"));
  }
  saveAuthenticatedPayload(payload);
}

function saveAuthenticatedPayload(payload) {
  saveStoredAuthState({
    deviceId: payload.device_id || authState.deviceId,
    sessionToken: payload.session_token,
    username: payload.username,
    name: payload.name,
    email: payload.email,
    role: payload.role,
    canUseHeatmap: payload.can_use_heatmap === true,
    canUseLayerMetrics: payload.can_use_layer_metrics === true,
    canUseEstimatedField: payload.can_use_estimated_field === true,
  });
}

function updateSignedInUser() {
  const container = document.getElementById("signed-in-user");
  const value = document.getElementById("signed-in-user-value");
  if (!container || !value) {
    syncHeatmapAccessUi();
    syncEstimatedFieldAccessUi();
    return;
  }
  const username = String(authState.username || "").trim();
  const name = String(authState.name || "").trim();
  const email = String(authState.email || "").trim();
  const role = String(authState.role || "").trim().toLowerCase();
  const displayName = username || name || email;
  if (!AUTH_REQUIRED || !authState.sessionToken || !displayName) {
    container.hidden = true;
    value.textContent = "-";
    syncHeatmapAccessUi();
    syncEstimatedFieldAccessUi();
    return;
  }
  value.textContent = role ? `${displayName} (${role})` : displayName;
  container.hidden = false;
  syncHeatmapAccessUi();
  syncEstimatedFieldAccessUi();
}

function selectedPeriodFileName() {
  return currentPeriodFileName;
}

function syncVisiblePeriodSelector(fileName = currentPeriodFileName) {
  const mapSelector = document.getElementById("map-selector");
  if (mapSelector && periods[fileName]) {
    mapSelector.value = fileName;
  }
}

function syncSettingsPeriodSelector(fileName = preferredPeriodFileName) {
  const settingsSelector = document.getElementById("settings-period-selector");
  if (settingsSelector && periods[fileName]) {
    settingsSelector.value = fileName;
  }
}

function selectedStationSources() {
  return Array.from(enabledStationSources).filter((source) => stationSources.some((known) => known.id === source));
}

function normalizedMapViewFromMap() {
  const center = map.getCenter();
  return {
    lng: Number(center.lng.toFixed(6)),
    lat: Number(center.lat.toFixed(6)),
    zoom: Number(map.getZoom().toFixed(3)),
    bearing: Number(map.getBearing().toFixed(2)),
    pitch: Number(map.getPitch().toFixed(2)),
  };
}

function isUsableMapView(view) {
  return Boolean(
    view
    && Number.isFinite(Number(view.lng))
    && Number.isFinite(Number(view.lat))
    && Number.isFinite(Number(view.zoom))
    && Math.abs(Number(view.lng)) <= 180
    && Math.abs(Number(view.lat)) <= 90
    && Number(view.zoom) >= 0
    && Number(view.zoom) <= 22
  );
}

function sanitizeClientMapView(view) {
  if (!isUsableMapView(view)) {
    return null;
  }
  return {
    lng: Number(Number(view.lng).toFixed(6)),
    lat: Number(Number(view.lat).toFixed(6)),
    zoom: Math.max(0, Math.min(22, Number(Number(view.zoom).toFixed(3)))),
    bearing: Number(Number(view.bearing || 0).toFixed(2)),
    pitch: Math.max(0, Math.min(85, Number(Number(view.pitch || 0).toFixed(2)))),
  };
}

function mapViewsAreClose(left, right) {
  if (!left || !right) {
    return false;
  }
  return (
    Math.abs(left.lng - right.lng) < 0.0005
    && Math.abs(left.lat - right.lat) < 0.0005
    && Math.abs(left.zoom - right.zoom) < 0.02
    && Math.abs(left.bearing - right.bearing) < 0.5
    && Math.abs(left.pitch - right.pitch) < 0.5
  );
}

function captureCurrentMapViewAsDefault() {
  const nextView = normalizedMapViewFromMap();
  savedMapView = nextView;
  if (!mapViewsAreClose(nextView, lastSavedMapView)) {
    markDeviceSettingsChanged();
  }
}

function currentDeviceSettings() {
  const settings = {
    period: preferredPeriodFileName,
    min_rain_mm: minRainFilter,
    map_style: preferredMapStyleId,
    language: currentLanguage,
    last_rains_history: lastRainHistoryLimit,
    station_sources: selectedStationSources(),
    terrain_enabled: terrainEnabled,
    terrain_exaggeration: terrainExaggeration,
  };
  if (canUseLayerMetrics()) {
    settings.layer_metric = currentLayerMetric;
  }
  if (canUseHeatmap()) {
    settings.heatmap_enabled = savedHeatmapEnabled;
    settings.heatmap_opacity = heatmapOpacity;
    settings.heatmap_radius_scale = heatmapRadiusScale;
    settings.heatmap_intensity_scale = heatmapIntensityScale;
    settings.heatmap_weight_curve = heatmapWeightCurve;
  }
  if (canUseEstimatedField()) {
    settings.estimated_field_enabled = savedEstimatedFieldEnabled;
    settings.estimated_field_opacity = estimatedFieldOpacity;
    settings.estimated_field_radius = estimatedFieldRadius;
    settings.estimated_field_quality = estimatedFieldQuality;
    settings.estimated_field_smoothing = estimatedFieldSmoothing;
    settings.estimated_field_altitude_correction = estimatedFieldAltitudeCorrection;
  }
  if (savedMapView) {
    settings.map_view = savedMapView;
  }
  return settings;
}

function markDeviceSettingsChanged() {
  if (!isApplyingDeviceSettings) {
    hasPendingDeviceSettingsChanges = true;
  }
}

async function saveDeviceSettings() {
  if (!AUTH_REQUIRED || !authState.sessionToken || isApplyingDeviceSettings) {
    return;
  }
  try {
    await authFetch(`${AUTH_BASE}/device-settings`, {
      method: "POST",
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ settings: currentDeviceSettings() }),
    });
    if (savedMapView) {
      lastSavedMapView = savedMapView;
    }
  } catch (error) {
    console.warn("Cannot save device settings", error);
  }
}

function setSourceControlsFromSettings(sourceIds) {
  if (!Array.isArray(sourceIds)) {
    return;
  }
  const allowedSources = sourceIds.filter((source) => stationSources.some((known) => known.id === source));
  if (allowedSources.length === 0) {
    return;
  }
  enabledStationSources = new Set(allowedSources);
  document.querySelectorAll("input[name='station-source']").forEach((input) => {
    input.checked = enabledStationSources.has(input.value);
  });
}

function setLayerControlsFromStyle(styleId) {
  document.querySelectorAll("input[name='base-style']").forEach((input) => {
    input.checked = input.value === styleId;
  });
}

function setQuickMapControlsFromStyle(styleId) {
  document.querySelectorAll(".quick-map-option").forEach((button) => {
    const isActive = button.dataset.styleId === styleId;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-current", isActive ? "true" : "false");
  });
}

function setQuickMetricControlsFromMetric(metricId = currentLayerMetric) {
  document.querySelectorAll(".quick-metric-option").forEach((button) => {
    const isActive = button.dataset.metricId === metricId;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-current", isActive ? "true" : "false");
  });
}

function waitForMapIdle() {
  return new Promise((resolve) => {
    let resolved = false;
    const done = () => {
      if (resolved) {
        return;
      }
      resolved = true;
      resolve();
    };
    map.once("idle", done);
    window.setTimeout(done, 800);
  });
}

async function applyDeviceSettings(settings) {
  if (!settings || typeof settings !== "object") {
    return;
  }

  isApplyingDeviceSettings = true;
  try {
    if (supportedLanguages.includes(settings.language)) {
      applyLanguage(settings.language);
    }

    const requestedStyle = baseStyles.find((style) => style.id === settings.map_style);
    if (requestedStyle) {
      currentStyle = requestedStyle;
      preferredMapStyleId = requestedStyle.id;
      setLayerControlsFromStyle(preferredMapStyleId);
      setQuickMapControlsFromStyle(currentStyle.id);
      map.setStyle(styleDefinition(currentStyle));
      await waitForMapIdle();
    }

    if (periods[settings.period]) {
      currentPeriodFileName = settings.period;
      preferredPeriodFileName = settings.period;
      syncVisiblePeriodSelector(currentPeriodFileName);
      syncSettingsPeriodSelector(preferredPeriodFileName);
      updatePeriodTimeline(currentPeriodFileName);
    }

    const savedMinRain = Number(settings.min_rain_mm);
    if (Number.isFinite(savedMinRain) && savedMinRain >= 0) {
      minRainFilter = savedMinRain;
      const slider = document.getElementById("min-rain-filter");
      if (slider) {
        slider.value = String(minRainFilter);
      }
      updateMinRainValue();
    }

    const savedHistoryLimit = Number(settings.last_rains_history);
    if (Number.isInteger(savedHistoryLimit) && savedHistoryLimit > 0) {
      lastRainHistoryLimit = savedHistoryLimit;
    }

    setSourceControlsFromSettings(settings.station_sources);

    const savedExaggeration = Number(settings.terrain_exaggeration);
    if (Number.isFinite(savedExaggeration)) {
      terrainExaggeration = Math.max(0.5, Math.min(3, savedExaggeration));
      const terrainSlider = document.getElementById("terrain-exaggeration");
      if (terrainSlider) {
        terrainSlider.value = String(terrainExaggeration);
      }
      updateTerrainExaggerationValue();
    }

    if (typeof settings.terrain_enabled === "boolean") {
      setTerrainEnabled(settings.terrain_enabled);
    }

    if (canUseLayerMetrics()) {
      if (layerMetrics.some((metric) => metric.id === settings.layer_metric)) {
        currentLayerMetric = settings.layer_metric;
        const layerMetricSelector = document.getElementById("layer-metric-selector");
        if (layerMetricSelector) {
          layerMetricSelector.value = currentLayerMetric;
        }
        setQuickMetricControlsFromMetric();
      }
    } else {
      currentLayerMetric = "rain";
    }

    if (canUseHeatmap()) {
      if (typeof settings.heatmap_enabled === "boolean") {
        savedHeatmapEnabled = settings.heatmap_enabled;
        heatmapEnabled = savedHeatmapEnabled;
      }

      const savedHeatmapOpacity = Number(settings.heatmap_opacity);
      if (Number.isFinite(savedHeatmapOpacity)) {
        heatmapOpacity = Math.max(0, Math.min(1, savedHeatmapOpacity));
        const heatmapOpacitySlider = document.getElementById("heatmap-opacity-filter");
        if (heatmapOpacitySlider) {
          heatmapOpacitySlider.value = String(Math.round(heatmapOpacity * 100));
        }
        updateHeatmapOpacityValue();
      }

      const savedHeatmapRadiusScale = Number(settings.heatmap_radius_scale);
      if (Number.isFinite(savedHeatmapRadiusScale)) {
        heatmapRadiusScale = Math.max(0.5, Math.min(3, savedHeatmapRadiusScale));
        const heatmapRadiusSlider = document.getElementById("heatmap-radius-filter");
        if (heatmapRadiusSlider) {
          heatmapRadiusSlider.value = String(Math.round(heatmapRadiusScale * 100));
        }
        updateHeatmapRadiusValue();
      }

      const savedHeatmapIntensityScale = Number(settings.heatmap_intensity_scale);
      if (Number.isFinite(savedHeatmapIntensityScale)) {
        heatmapIntensityScale = Math.max(0.2, Math.min(2, savedHeatmapIntensityScale));
        const heatmapIntensitySlider = document.getElementById("heatmap-intensity-filter");
        if (heatmapIntensitySlider) {
          heatmapIntensitySlider.value = String(Math.round(heatmapIntensityScale * 100));
        }
        updateHeatmapIntensityValue();
      }

      if (["linear", "soft", "strong"].includes(settings.heatmap_weight_curve)) {
        heatmapWeightCurve = settings.heatmap_weight_curve;
        renderHeatmapWeightCurveSelector();
      }
    } else {
      heatmapEnabled = false;
    }

    if (canUseEstimatedField()) {
      if (typeof settings.estimated_field_enabled === "boolean") {
        savedEstimatedFieldEnabled = settings.estimated_field_enabled;
        estimatedFieldEnabled = savedEstimatedFieldEnabled;
      }

      const savedEstimatedFieldOpacity = Number(settings.estimated_field_opacity);
      if (Number.isFinite(savedEstimatedFieldOpacity)) {
        estimatedFieldOpacity = Math.max(0, Math.min(1, savedEstimatedFieldOpacity));
      }

      if (ESTIMATED_FIELD_RADIUS_OPTIONS.includes(settings.estimated_field_radius)) {
        estimatedFieldRadius = settings.estimated_field_radius;
      }
      if (ESTIMATED_FIELD_QUALITY_OPTIONS.includes(settings.estimated_field_quality)) {
        estimatedFieldQuality = settings.estimated_field_quality;
      }
      if (ESTIMATED_FIELD_SMOOTHING_OPTIONS.includes(settings.estimated_field_smoothing)) {
        estimatedFieldSmoothing = settings.estimated_field_smoothing;
      }
      if (typeof settings.estimated_field_altitude_correction === "boolean") {
        estimatedFieldAltitudeCorrection = settings.estimated_field_altitude_correction;
      }
      const opacitySlider = document.getElementById("estimated-field-opacity-filter");
      const altitudeToggle = document.getElementById("estimated-field-altitude-correction-toggle");
      if (opacitySlider) opacitySlider.value = String(Math.round(estimatedFieldOpacity * 100));
      if (altitudeToggle) altitudeToggle.checked = estimatedFieldAltitudeCorrection;
      renderEstimatedFieldSelectors();
      updateEstimatedFieldOpacityValue();
    } else {
      estimatedFieldEnabled = false;
    }

    if (heatmapEnabled && estimatedFieldEnabled) {
      heatmapEnabled = false;
      savedHeatmapEnabled = false;
    }
    syncHeatmapEnabledControl();
    syncEstimatedFieldEnabledControl();
    updateHeatmapToggle();
    updateEstimatedFieldToggle();

    const loadedMapView = sanitizeClientMapView(settings.map_view);
    if (loadedMapView) {
      savedMapView = loadedMapView;
      lastSavedMapView = loadedMapView;
    }
  } finally {
    isApplyingDeviceSettings = false;
  }
}

async function loadDeviceSettings() {
  if (!AUTH_REQUIRED || !authState.sessionToken || hasLoadedDeviceSettings) {
    return;
  }
  hasLoadedDeviceSettings = true;
  try {
    const response = await authFetch(`${AUTH_BASE}/device-settings`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Cannot load device settings: ${response.status}`);
    }
    const payload = await response.json();
    await applyDeviceSettings(payload.settings || {});
  } catch (error) {
    console.warn("Cannot load device settings", error);
  }
}

function updateDemoZoomLevel() {
  const element = document.getElementById("demo-zoom-level");
  if (!element) {
    return;
  }
  element.textContent = `${t("zoom")} ${map.getZoom().toFixed(2)}`;
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
      submit.textContent = pendingPasswordChange ? t("changingPassword") : t("signingIn");
    }
    try {
      if (pendingPasswordChange) {
        const newPassword = document.getElementById("new-password")?.value || "";
        const repeatedPassword = document.getElementById("new-password-repeat")?.value || "";
        if (newPassword !== repeatedPassword) {
          throw new Error(t("passwordMismatch"));
        }
        await changeRequiredPassword(
          pendingPasswordChange.username,
          pendingPasswordChange.currentPassword,
          newPassword,
        );
      } else {
        await loginWithPassword(
          document.getElementById("login-username")?.value || "",
          document.getElementById("login-password")?.value || "",
        );
      }
      hideLogin();
      await onAuthenticated();
    } catch (errorMessage) {
      if (errorMessage.code === "password_change_required") {
        setPasswordChangeMode(
          errorMessage.username || document.getElementById("login-username")?.value || "",
          document.getElementById("login-password")?.value || "",
        );
        errorMessage.message = t("enterNewPassword");
      }
      if (error) {
        error.textContent = errorMessage.message || t("cannotSignIn");
      }
    } finally {
      if (submit) {
        submit.disabled = false;
        submit.textContent = pendingPasswordChange ? t("changePassword") : t("signIn");
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
  showLogin(t("signInViewMap"));
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

const layerMetrics = [
  { id: "rain", labelKey: "metricRain", property: "Total", unit: "mm", decimals: 0, floor: 0 },
  { id: "max_temp", labelKey: "metricMaxTemp", property: "max_temp_celsius", unit: "°C", decimals: 0 },
  { id: "min_temp", labelKey: "metricMinTemp", property: "min_temp_celsius", unit: "°C", decimals: 0 },
  { id: "max_humidity", labelKey: "metricMaxHumidity", property: "max_humidity_percent", unit: "%", decimals: 0, floor: 0, ceiling: 100 },
  { id: "min_humidity", labelKey: "metricMinHumidity", property: "min_humidity_percent", unit: "%", decimals: 0, floor: 0, ceiling: 100 },
  { id: "wind", labelKey: "metricWind", property: "wind_avg_kmh", unit: "km/h", decimals: 0, floor: 0 },
];
const noDataMetricColor = "#8a95a3";

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
  return colorForRatio(ratio);
}

function colorForRatio(ratioValue) {
  const ratio = Math.max(0, Math.min(1, Number(ratioValue) || 0));
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

function selectedLayerMetric() {
  if (!canUseLayerMetrics()) {
    return layerMetrics[0];
  }
  return layerMetrics.find((metric) => metric.id === currentLayerMetric) || layerMetrics[0];
}

function layerMetricLabel(metric = selectedLayerMetric()) {
  return t(metric.labelKey);
}

function parseOptionalNumber(value) {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === "string") {
    const normalized = value.trim();
    if (!normalized || ["-", "none", "nan", "nat", "null"].includes(normalized.toLowerCase())) {
      return null;
    }
    const parsedString = Number(normalized);
    return Number.isFinite(parsedString) ? parsedString : null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function featureMetricValue(feature, metric = selectedLayerMetric()) {
  return parseOptionalNumber(feature.properties?.[metric.property]);
}

function metricScaleCeiling(maxValue) {
  const maximum = Math.ceil(maxValue || 0);
  const ceilings = [10, 25, 50, 100, 150, 200, 300, 500, 750, 1000];
  const ceiling = ceilings.find((value) => maximum <= value);
  if (ceiling) return ceiling;
  return Math.ceil(maximum / 500) * 500;
}

function metricScaleFloor(minValue) {
  const minimum = Math.floor(minValue || 0);
  if (minimum >= 0) {
    return 0;
  }
  return Math.floor(minimum / 5) * 5;
}

function robustMetricScale(features) {
  const metric = selectedLayerMetric();
  if (metric.id === "rain") {
    return [0, rainScaleMax];
  }
  const values = features
    .map((feature) => featureMetricValue(feature, metric))
    .filter((value) => Number.isFinite(value))
    .sort((left, right) => left - right);
  if (values.length === 0) {
    const floor = Number.isFinite(metric.floor) ? metric.floor : -10;
    const ceiling = Number.isFinite(metric.ceiling) ? metric.ceiling : 10;
    return [floor, ceiling];
  }
  const floor = Math.floor(values[0]);
  const ceiling = Math.ceil(values[values.length - 1]);
  return floor === ceiling ? [floor - 1, ceiling + 1] : [floor, ceiling];
}

function updateMetricScale(features) {
  [metricScaleMin, metricScaleMax] = robustMetricScale(features);
  updateMetricLegend();
}

function metricScaleFeatures(features) {
  return selectedLayerMetric().id === "rain" ? features : filteredFeatures(features);
}

function metricRatio(value) {
  if (!Number.isFinite(value)) {
    return 0;
  }
  const span = metricScaleMax - metricScaleMin || 1;
  return Math.max(0, Math.min(1, (value - metricScaleMin) / span));
}

function metricColor(value) {
  return colorForRatio(metricRatio(value));
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
    .filter((value) => Number.isFinite(value) && value > 0)
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
}

function formatLegendValue(value, metric = selectedLayerMetric()) {
  if (!Number.isFinite(value)) {
    return "-";
  }
  return String(Math.round(value));
}

function updateMetricLegend() {
  const metric = selectedLayerMetric();
  const title = document.getElementById("rain-legend-title");
  const labels = document.getElementById("rain-legend-labels");
  if (title) {
    title.textContent = metric.unit;
    title.title = layerMetricLabel(metric);
  }
  if (!labels) {
    return;
  }
  const span = metricScaleMax - metricScaleMin;
  const values = [1, 0.85, 0.7, 0.55, 0.4, 0.25, 0.12, 0].map((ratio) => metricScaleMin + span * ratio);
  labels.innerHTML = values.map((value, index) => {
    const formatted = formatLegendValue(value, metric);
    return `<span>${index === 0 ? `${formatted}+` : formatted}</span>`;
  }).join("");
}

function renderLayerMetricSelector() {
  const selector = document.getElementById("layer-metric-selector");
  if (!selector) {
    return;
  }
  selector.innerHTML = layerMetrics.map((metric) => `
    <option value="${metric.id}">${layerMetricLabel(metric)}</option>
  `).join("");
  selector.value = currentLayerMetric;
}

function renderHeatmapWeightCurveSelector() {
  const selector = document.getElementById("heatmap-weight-curve-selector");
  if (selector) {
    selector.querySelector('option[value="linear"]').textContent = t("heatmapWeightLinear");
    selector.querySelector('option[value="soft"]').textContent = t("heatmapWeightSoft");
    selector.querySelector('option[value="strong"]').textContent = t("heatmapWeightStrong");
    selector.value = heatmapWeightCurve;
  }
}

function updateHeatmapOpacityValue() {
  const output = document.getElementById("heatmap-opacity-value");
  if (output) {
    output.textContent = `${Math.round(heatmapOpacity * 100)}%`;
  }
}

function updateHeatmapRadiusValue() {
  const output = document.getElementById("heatmap-radius-value");
  if (output) {
    output.textContent = `${Math.round(heatmapRadiusScale * 100)}%`;
  }
}

function updateHeatmapIntensityValue() {
  const output = document.getElementById("heatmap-intensity-value");
  if (output) {
    output.textContent = `${Math.round(heatmapIntensityScale * 100)}%`;
  }
}

function updateHeatmapToggle() {
  const toggle = document.getElementById("heatmap-toggle");
  if (!toggle) {
    return;
  }
  toggle.hidden = !canUseHeatmap();
  toggle.setAttribute("aria-pressed", String(heatmapEnabled));
}

function syncHeatmapEnabledControl() {
  const enabledToggle = document.getElementById("heatmap-enabled-toggle");
  if (enabledToggle) {
    enabledToggle.checked = savedHeatmapEnabled;
  }
}

function syncEstimatedFieldEnabledControl() {
  const enabledToggle = document.getElementById("estimated-field-enabled-toggle");
  if (enabledToggle) {
    enabledToggle.checked = savedEstimatedFieldEnabled;
  }
}

function setHeatmapEnabled(enabled) {
  heatmapEnabled = canUseHeatmap() && enabled;
  if (heatmapEnabled && estimatedFieldEnabled) {
    estimatedFieldEnabled = false;
    updateEstimatedFieldToggle();
    removeEstimatedFieldLayer();
  }
  updateHeatmapToggle();
}

function setEstimatedFieldEnabled(enabled) {
  estimatedFieldEnabled = canUseEstimatedField() && enabled;
  if (estimatedFieldEnabled && heatmapEnabled) {
    heatmapEnabled = false;
    updateHeatmapToggle();
  }
  updateEstimatedFieldToggle();
}

function applyHeatmapDefaults() {
  heatmapOpacity = DEFAULT_HEATMAP_OPACITY;
  heatmapRadiusScale = DEFAULT_HEATMAP_RADIUS_SCALE;
  heatmapIntensityScale = DEFAULT_HEATMAP_INTENSITY_SCALE;
  heatmapWeightCurve = DEFAULT_HEATMAP_WEIGHT_CURVE;
  renderHeatmapWeightCurveSelector();
  const heatmapOpacitySlider = document.getElementById("heatmap-opacity-filter");
  if (heatmapOpacitySlider) {
    heatmapOpacitySlider.value = String(Math.round(heatmapOpacity * 100));
  }
  const heatmapRadiusSlider = document.getElementById("heatmap-radius-filter");
  if (heatmapRadiusSlider) {
    heatmapRadiusSlider.value = String(Math.round(heatmapRadiusScale * 100));
  }
  const heatmapIntensitySlider = document.getElementById("heatmap-intensity-filter");
  if (heatmapIntensitySlider) {
    heatmapIntensitySlider.value = String(Math.round(heatmapIntensityScale * 100));
  }
  updateHeatmapOpacityValue();
  updateHeatmapRadiusValue();
  updateHeatmapIntensityValue();
  syncHeatmapEnabledControl();
}

function syncHeatmapAccessUi() {
  const heatmapAllowed = canUseHeatmap();
  const metricsAllowed = canUseLayerMetrics();
  const quickMetricToggle = document.getElementById("quick-metric-toggle");
  const quickMetricPanel = document.getElementById("quick-metric-panel");
  const layerMetricSelector = document.getElementById("layer-metric-selector");
  const layerMetricRow = layerMetricSelector?.closest(".map-settings-row");
  const heatmapExperimentSettings = document.getElementById("heatmap-experiment-settings");
  const heatmapSettingsTab = document.getElementById("settings-tab-heatmap");
  const generalSettingsTab = document.getElementById("settings-tab-general");
  const activeHeatmapTab = heatmapSettingsTab?.classList.contains("is-active");

  if (!metricsAllowed) {
    currentLayerMetric = "rain";
    if (quickMetricPanel) {
      quickMetricPanel.hidden = true;
    }
  }
  if (!heatmapAllowed) {
    heatmapEnabled = false;
    savedHeatmapEnabled = false;
  }
  if (quickMetricToggle) {
    quickMetricToggle.hidden = !metricsAllowed;
    quickMetricToggle.setAttribute("aria-expanded", "false");
  }
  if (layerMetricRow) {
    layerMetricRow.hidden = !metricsAllowed;
  }
  if (heatmapExperimentSettings) {
    heatmapExperimentSettings.hidden = !heatmapAllowed;
  }
  if (heatmapSettingsTab) {
    heatmapSettingsTab.hidden = !heatmapAllowed;
  }
  if (!heatmapAllowed && activeHeatmapTab && generalSettingsTab) {
    generalSettingsTab.click();
  }
  updateHeatmapToggle();
  syncHeatmapEnabledControl();
  renderLayerMetricSelector();
  setQuickMetricControlsFromMetric();
}

function estimatedFieldCellKm() {
  const fallback = { low: 10, medium: 5, high: 2.5 };
  const configured = estimatedFieldGridConfig[estimatedFieldQuality];
  return clampNumber(
    Number(configured),
    0.1,
    100,
    fallback[estimatedFieldQuality] || fallback.medium,
  );
}

function estimatedFieldGridSize(width, height) {
  const cellKm = estimatedFieldCellKm();
  const horizontalCenter = height / 2;
  const verticalCenter = width / 2;
  const west = map.unproject([0, horizontalCenter]);
  const east = map.unproject([width, horizontalCenter]);
  const north = map.unproject([verticalCenter, 0]);
  const south = map.unproject([verticalCenter, height]);
  const widthKm = Math.max(haversineKm(west, east), cellKm);
  const heightKm = Math.max(haversineKm(north, south), cellKm);
  return {
    cols: Math.max(1, Math.min(700, Math.ceil(widthKm / cellKm))),
    rows: Math.max(1, Math.min(500, Math.ceil(heightKm / cellKm))),
  };
}

function estimatedFieldRadiusKm() {
  const fallback = { small: 10, medium: 25, large: 50 };
  const configuredRadiusKm = configuredEstimatedField.radiusKm || {};
  return clampNumber(
    Number(configuredRadiusKm[estimatedFieldRadius]),
    1,
    1000,
    fallback[estimatedFieldRadius] || fallback.medium,
  );
}

function estimatedFieldSmoothingPower() {
  const fallback = { smooth: 1, balanced: 2, local: 3 };
  return clampNumber(
    Number(estimatedFieldSmoothingPowerConfig[estimatedFieldSmoothing]),
    0.1,
    8,
    fallback[estimatedFieldSmoothing] || fallback.balanced,
  );
}

function estimatedFieldMaxRadiusKm() {
  return clampNumber(Number(configuredEstimatedField.maxRadiusKm), 1, 1000, 100);
}

function estimatedFieldTemperatureLapseRate() {
  return clampNumber(Number(configuredEstimatedField.temperatureLapseRateCPer100m), 0, 2, 0.65);
}

function isTemperatureMetric(metric) {
  return metric.id === "max_temp" || metric.id === "min_temp";
}

function featureAltitude(feature) {
  return parseOptionalNumber(feature.properties?.["Altitud"] ?? feature.properties?.Altitude ?? feature.properties?.altitude);
}

function haversineKm(leftLngLat, rightLngLat) {
  const earthRadiusKm = 6371;
  const toRadians = (degrees) => degrees * Math.PI / 180;
  const leftLat = toRadians(leftLngLat.lat);
  const rightLat = toRadians(rightLngLat.lat);
  const deltaLat = toRadians(rightLngLat.lat - leftLngLat.lat);
  const deltaLng = toRadians(rightLngLat.lng - leftLngLat.lng);
  const halfChord = Math.sin(deltaLat / 2) ** 2
    + Math.cos(leftLat) * Math.cos(rightLat) * Math.sin(deltaLng / 2) ** 2;
  return earthRadiusKm * 2 * Math.atan2(Math.sqrt(halfChord), Math.sqrt(1 - halfChord));
}

function removeEstimatedFieldLayer() {
  if (map.getLayer(ESTIMATED_FIELD_LAYER_ID)) {
    map.removeLayer(ESTIMATED_FIELD_LAYER_ID);
  }
  if (map.getSource(ESTIMATED_FIELD_SOURCE_ID)) {
    map.removeSource(ESTIMATED_FIELD_SOURCE_ID);
  }
}

function estimatedFieldUsableFeatures(features, metric = selectedLayerMetric()) {
  return features
    .filter((feature) => {
      return enabledStationSources.has(featureStationSource(feature));
    })
    .map((feature) => ({
      feature,
      value: featureMetricValue(feature, metric),
      coordinates: feature.geometry?.coordinates,
      altitude: featureAltitude(feature),
    }))
    .filter((item) => (
      Number.isFinite(item.value)
      && Array.isArray(item.coordinates)
      && Number.isFinite(Number(item.coordinates[0]))
      && Number.isFinite(Number(item.coordinates[1]))
    ));
}

function estimatedFieldPaintSupport(value, metric) {
  if (!Number.isFinite(value)) {
    return 0;
  }
  if (metric.id === "rain") {
    return metricRatio(value);
  }
  return 1;
}

function estimateFieldCellValue(cellLngLat, stations, radiusKm, power, metric) {
  let weightedValue = 0;
  let totalWeight = 0;
  let weightedAltitude = 0;
  let totalAltitudeWeight = 0;
  let supportWeight = 0;
  let nearestDistanceKm = Infinity;
  const nearby = [];
  const cellLat = Number(cellLngLat.lat);
  const cellLng = Number(cellLngLat.lng);
  const latRadius = radiusKm / 111.32;
  const lngRadius = radiusKm / Math.max(111.32 * Math.cos(cellLat * Math.PI / 180), 1);

  stations.forEach((station) => {
    if (Math.abs(station.lat - cellLat) > latRadius || Math.abs(station.lng - cellLng) > lngRadius) {
      return;
    }
    const distanceKm = haversineKm(cellLngLat, station);
    if (distanceKm > radiusKm) {
      return;
    }
    nearestDistanceKm = Math.min(nearestDistanceKm, distanceKm);
    const weight = 1 / (Math.max(distanceKm, 0.1) ** power);
    supportWeight += weight * estimatedFieldPaintSupport(station.value, metric);
    nearby.push({ ...station, weight });
    if (Number.isFinite(station.altitude)) {
      weightedAltitude += station.altitude * weight;
      totalAltitudeWeight += weight;
    }
  });

  if (nearby.length === 0) {
    return null;
  }
  const coreRadiusKm = Math.max(radiusKm * 0.55, 0.1);
  const minimumSupportWeight = 1 / (coreRadiusKm ** power);
  if (metric.id === "rain" && supportWeight < minimumSupportWeight) {
    return null;
  }
  if (metric.id !== "rain" && supportWeight < minimumSupportWeight && nearestDistanceKm > coreRadiusKm) {
    return null;
  }

  const targetAltitude = totalAltitudeWeight > 0 ? weightedAltitude / totalAltitudeWeight : null;
  const applyAltitudeCorrection = estimatedFieldAltitudeCorrection
    && isTemperatureMetric(metric)
    && Number.isFinite(targetAltitude);
  const lapseRate = estimatedFieldTemperatureLapseRate();

  nearby.forEach((station) => {
    let value = station.value;
    if (applyAltitudeCorrection && Number.isFinite(station.altitude)) {
      value += ((station.altitude - targetAltitude) / 100) * lapseRate;
    }
    weightedValue += value * station.weight;
    totalWeight += station.weight;
  });

  return totalWeight > 0 ? weightedValue / totalWeight : null;
}

function buildEstimatedFieldData(features) {
  if (!canUseEstimatedField() || !estimatedFieldEnabled || !map?.isStyleLoaded()) {
    return { type: "FeatureCollection", features: [] };
  }
  const metric = selectedLayerMetric();
  const stations = estimatedFieldUsableFeatures(features, metric)
    .map((station) => ({
      ...station,
      lng: Number(station.coordinates[0]),
      lat: Number(station.coordinates[1]),
    }));
  if (stations.length === 0) {
    return { type: "FeatureCollection", features: [] };
  }

  const canvas = map.getCanvas();
  const width = canvas.clientWidth || canvas.width || 0;
  const height = canvas.clientHeight || canvas.height || 0;
  if (width <= 0 || height <= 0) {
    return { type: "FeatureCollection", features: [] };
  }

  const { cols, rows } = estimatedFieldGridSize(width, height);
  const cellWidth = width / cols;
  const cellHeight = height / rows;
  const radiusKm = Math.min(estimatedFieldRadiusKm(), estimatedFieldMaxRadiusKm());
  const power = estimatedFieldSmoothingPower();
  const estimatedFeatures = [];

  for (let row = 0; row < rows; row += 1) {
    const top = row * cellHeight;
    const bottom = (row + 1) * cellHeight;
    for (let col = 0; col < cols; col += 1) {
      const left = col * cellWidth;
      const right = (col + 1) * cellWidth;
      const centerPoint = { x: left + cellWidth / 2, y: top + cellHeight / 2 };
      const centerLngLat = map.unproject([centerPoint.x, centerPoint.y]);
      const value = estimateFieldCellValue(centerLngLat, stations, radiusKm, power, metric);
      if (!Number.isFinite(value)) {
        continue;
      }
      const topLeft = map.unproject([left, top]);
      const topRight = map.unproject([right, top]);
      const bottomRight = map.unproject([right, bottom]);
      const bottomLeft = map.unproject([left, bottom]);
      estimatedFeatures.push({
        type: "Feature",
        properties: {
          value,
          color: metricColor(value),
        },
        geometry: {
          type: "Polygon",
          coordinates: [[
            [topLeft.lng, topLeft.lat],
            [topRight.lng, topRight.lat],
            [bottomRight.lng, bottomRight.lat],
            [bottomLeft.lng, bottomLeft.lat],
            [topLeft.lng, topLeft.lat],
          ]],
        },
      });
    }
  }

  return { type: "FeatureCollection", features: estimatedFeatures };
}

function updateEstimatedFieldLayer({ immediate = false } = {}) {
  if (estimatedFieldUpdateTimer) {
    window.clearTimeout(estimatedFieldUpdateTimer);
    estimatedFieldUpdateTimer = null;
  }
  const run = () => {
    if (!map?.isStyleLoaded()) {
      map?.once?.("idle", () => updateEstimatedFieldLayer({ immediate: true }));
      return;
    }
    if (!canUseEstimatedField() || !estimatedFieldEnabled) {
      removeEstimatedFieldLayer();
      return;
    }
    const data = buildEstimatedFieldData(currentVisibleFeatures);
    if (!map.getSource(ESTIMATED_FIELD_SOURCE_ID)) {
      map.addSource(ESTIMATED_FIELD_SOURCE_ID, {
        type: "geojson",
        data,
      });
    } else {
      map.getSource(ESTIMATED_FIELD_SOURCE_ID).setData(data);
    }

    if (!map.getLayer(ESTIMATED_FIELD_LAYER_ID)) {
      map.addLayer({
        id: ESTIMATED_FIELD_LAYER_ID,
        type: "fill",
        source: ESTIMATED_FIELD_SOURCE_ID,
        paint: {
          "fill-color": ["get", "color"],
          "fill-opacity": estimatedFieldOpacity,
          "fill-outline-color": "rgba(255,255,255,0)",
        },
      });
    }
    map.setPaintProperty(ESTIMATED_FIELD_LAYER_ID, "fill-opacity", estimatedFieldOpacity);
    map.triggerRepaint?.();
  };

  if (immediate) {
    run();
  } else {
    estimatedFieldUpdateTimer = window.setTimeout(run, 180);
  }
}

function updateEstimatedFieldToggle() {
  const toggle = document.getElementById("estimated-field-toggle");
  if (!toggle) {
    return;
  }
  toggle.hidden = !canUseEstimatedField();
  toggle.setAttribute("aria-pressed", String(estimatedFieldEnabled));
}

function updateEstimatedFieldOpacityValue() {
  const output = document.getElementById("estimated-field-opacity-value");
  if (output) {
    output.textContent = `${Math.round(estimatedFieldOpacity * 100)}%`;
  }
}

function renderEstimatedFieldSelectors() {
  const radiusSelector = document.getElementById("estimated-field-radius-selector");
  const qualitySelector = document.getElementById("estimated-field-quality-selector");
  const smoothingSelector = document.getElementById("estimated-field-smoothing-selector");
  if (radiusSelector) {
    radiusSelector.querySelector('option[value="small"]').textContent = t("estimatedFieldRadiusSmall");
    radiusSelector.querySelector('option[value="medium"]').textContent = t("estimatedFieldRadiusMedium");
    radiusSelector.querySelector('option[value="large"]').textContent = t("estimatedFieldRadiusLarge");
    radiusSelector.value = estimatedFieldRadius;
  }
  if (qualitySelector) {
    qualitySelector.querySelector('option[value="low"]').textContent = t("estimatedFieldQualityLow");
    qualitySelector.querySelector('option[value="medium"]').textContent = t("estimatedFieldQualityMedium");
    qualitySelector.querySelector('option[value="high"]').textContent = t("estimatedFieldQualityHigh");
    qualitySelector.value = estimatedFieldQuality;
  }
  if (smoothingSelector) {
    smoothingSelector.querySelector('option[value="smooth"]').textContent = t("estimatedFieldSmoothingSmooth");
    smoothingSelector.querySelector('option[value="balanced"]').textContent = t("estimatedFieldSmoothingBalanced");
    smoothingSelector.querySelector('option[value="local"]').textContent = t("estimatedFieldSmoothingLocal");
    smoothingSelector.value = estimatedFieldSmoothing;
  }
}

function applyEstimatedFieldDefaults() {
  savedEstimatedFieldEnabled = canUseEstimatedField() && DEFAULT_ESTIMATED_FIELD_ENABLED;
  setEstimatedFieldEnabled(DEFAULT_ESTIMATED_FIELD_ENABLED);
  if (savedEstimatedFieldEnabled) {
    savedHeatmapEnabled = false;
    heatmapEnabled = false;
    syncHeatmapEnabledControl();
    updateHeatmapToggle();
  }
  estimatedFieldOpacity = DEFAULT_ESTIMATED_FIELD_OPACITY;
  estimatedFieldRadius = DEFAULT_ESTIMATED_FIELD_RADIUS;
  estimatedFieldQuality = DEFAULT_ESTIMATED_FIELD_QUALITY;
  estimatedFieldSmoothing = DEFAULT_ESTIMATED_FIELD_SMOOTHING;
  estimatedFieldAltitudeCorrection = DEFAULT_ESTIMATED_FIELD_ALTITUDE_CORRECTION;
  const opacitySlider = document.getElementById("estimated-field-opacity-filter");
  const altitudeToggle = document.getElementById("estimated-field-altitude-correction-toggle");
  syncEstimatedFieldEnabledControl();
  if (opacitySlider) opacitySlider.value = String(Math.round(estimatedFieldOpacity * 100));
  if (altitudeToggle) altitudeToggle.checked = estimatedFieldAltitudeCorrection;
  renderEstimatedFieldSelectors();
  updateEstimatedFieldOpacityValue();
}

function syncEstimatedFieldAccessUi() {
  const estimatedAllowed = canUseEstimatedField();
  const settingsTab = document.getElementById("settings-tab-estimated-field");
  const settingsSection = document.getElementById("estimated-field-settings");
  const generalSettingsTab = document.getElementById("settings-tab-general");
  const activeTab = settingsTab?.classList.contains("is-active");
  if (!estimatedAllowed) {
    estimatedFieldEnabled = false;
    savedEstimatedFieldEnabled = false;
    removeEstimatedFieldLayer();
  }
  if (settingsTab) {
    settingsTab.hidden = !estimatedAllowed;
  }
  if (settingsSection) {
    settingsSection.hidden = !estimatedAllowed;
  }
  if (!estimatedAllowed && activeTab && generalSettingsTab) {
    generalSettingsTab.click();
  }
  updateEstimatedFieldToggle();
  syncEstimatedFieldEnabledControl();
  renderEstimatedFieldSelectors();
}

function refreshMetricStyling() {
  if (!currentVisibleFeatures.length) {
    updateMetricLegend();
    updateEstimatedFieldLayer();
    return;
  }
  setQuickMetricControlsFromMetric();
  refreshFilteredData();
}

function markerRadius(value) {
  if (!Number.isFinite(value)) return 5;
  return Math.max(5, Math.min(24, 5 + Math.sqrt(Math.max(value - metricScaleMin, 0)) * 1.2));
}

function validCoordinateFeatures(features) {
  return features.filter((feature) => {
    const coordinates = feature.geometry?.coordinates || [];
    const lon = Number(coordinates[0]);
    const lat = Number(coordinates[1]);
    return Number.isFinite(lat)
      && Number.isFinite(lon)
      && lon >= -180
      && lon <= 180
      && lat >= -85.05112878
      && lat <= 85.05112878;
  });
}

function prepareFeature(feature) {
  const total = featureRainTotal(feature);
  const metric = selectedLayerMetric();
  const metricValue = featureMetricValue(feature, metric);
  const hasMetricValue = Number.isFinite(metricValue);
  const useMetricStyle = canUseLayerMetrics();
  const source = feature.properties?.Source || inferStationSource(feature.properties?.["Codi Estació"]);
  return {
    ...feature,
    properties: {
      ...(feature.properties || {}),
      Source: source,
      rain_color: useMetricStyle
        ? (hasMetricValue ? metricColor(metricValue) : noDataMetricColor)
        : (Number.isFinite(total) ? rainColor(total) : noDataMetricColor),
      marker_radius: useMetricStyle && !hasMetricValue
        ? 5
        : (useMetricStyle
          ? markerRadius(metricValue)
          : (Number.isFinite(total) ? markerRadius(total) : 5)),
      layer_metric_value: metricValue,
    },
  };
}

function featureRainTotal(feature) {
  return parseOptionalNumber(feature.properties?.Total);
}

function inferStationSource(stationCode) {
  const code = String(stationCode || "").trim().toUpperCase();
  if (code.startsWith("AEMET:")) {
    return "AEMET";
  }
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

const stationSourceAttributions = {
  AEMET: "Fuente: AEMET · Información elaborada por Rainmapper a partir de datos de la Agencia Estatal de Meteorología",
  Meteocat: "Font: Generalitat de Catalunya. Departament de Territori, Habitatge i Transició Ecològica. METEOCAT. Dades meteorològiques de la XEMA. Dades elaborades per Rainmapper.",
  Meteoclimatic: "Fuente: Información elaborada por Rainmapper a partir de datos de Meteoclimatic (www.meteoclimatic.net)",
  Wunderground: "Source: Information elaborated by Rainmapper from Weather Underground data",
};

function displayStationCode(stationCode) {
  const code = String(stationCode || "").trim();
  return code.startsWith("AEMET:") ? code.slice("AEMET:".length) : code;
}

function sourceAttribution(properties) {
  const source = properties.Source || inferStationSource(properties["Codi Estació"]);
  const attribution = stationSourceAttributions[source];
  if (!attribution) {
    return "";
  }
  return `
    <div class="popup-row popup-source-credit">${attribution}</div>
  `;
}

function featureStationSource(feature) {
  return feature.properties?.Source || inferStationSource(feature.properties?.["Codi Estació"]);
}

function filteredFeatures(features) {
  return features.filter((feature) => {
    const rainTotal = featureRainTotal(feature);
    const passesRainFilter = Number.isFinite(rainTotal)
      ? rainTotal >= minRainFilter
      : minRainFilter <= 0;
    return passesRainFilter && enabledStationSources.has(featureStationSource(feature));
  });
}

function heatmapFeatures(features) {
  const metric = selectedLayerMetric();
  return features.filter((feature) => (
    enabledStationSources.has(featureStationSource(feature))
    && Number.isFinite(featureMetricValue(feature, metric))
  ));
}

function heatmapWeightExpression() {
  const metricValue = ["coalesce", ["to-number", ["get", "layer_metric_value"]], metricScaleMin];
  if (heatmapWeightCurve === "soft") {
    return [
      "interpolate",
      ["linear"],
      metricValue,
      metricScaleMin,
      0,
      metricScaleMin + (metricScaleMax - metricScaleMin) * 0.25,
      0.1,
      metricScaleMin + (metricScaleMax - metricScaleMin) * 0.5,
      0.3,
      metricScaleMin + (metricScaleMax - metricScaleMin) * 0.75,
      0.65,
      metricScaleMax,
      1,
    ];
  }
  if (heatmapWeightCurve === "strong") {
    return [
      "interpolate",
      ["linear"],
      metricValue,
      metricScaleMin,
      0,
      metricScaleMin + (metricScaleMax - metricScaleMin) * 0.25,
      0.35,
      metricScaleMin + (metricScaleMax - metricScaleMin) * 0.5,
      0.7,
      metricScaleMin + (metricScaleMax - metricScaleMin) * 0.75,
      0.9,
      metricScaleMax,
      1,
    ];
  }
  return [
    "interpolate",
    ["linear"],
    metricValue,
    metricScaleMin,
    0,
    metricScaleMax,
    1,
  ];
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
    const status = statusPayload.status || t("unknown");
    const stations = Number(statusPayload.stations);
    const hasStationCount = Number.isFinite(stations) && stations >= 0;
    element.replaceChildren();
    const statusLine = document.createElement("span");
    statusLine.className = "source-status-state";
    statusLine.textContent = status;
    element.appendChild(statusLine);
    if (hasStationCount) {
      const stationsLine = document.createElement("span");
      stationsLine.className = "source-status-count";
      stationsLine.textContent = String(stations);
      element.appendChild(stationsLine);
    }
    element.className = `source-status-pill ${sourceStatusClass(status)}`;
    const statusLabel = hasStationCount ? `${status} · ${stations}` : status;
    element.title = statusPayload.message || statusLabel || t("sourceStatusUnavailable");
  });
  document.querySelectorAll(".source-status-unknown").forEach((element) => {
    if (!element.dataset.sourceStatus) {
      element.textContent = t("noStatus");
      element.title = t("sourceStatusUnavailable");
    }
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
  const maxRain = features.reduce((maxValue, feature) => {
    const rainTotal = featureRainTotal(feature);
    return Number.isFinite(rainTotal) ? Math.max(maxValue, rainTotal) : maxValue;
  }, 0);
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
  output.textContent = lastRainHistoryLimit > 0 ? `${lastRainHistoryLimit} ${t("records")}` : "-";
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

function distanceKmBetweenLngLat(leftLngLat, rightLngLat) {
  const earthRadiusKm = 6371;
  const leftLatRad = leftLngLat.lat * Math.PI / 180;
  const rightLatRad = rightLngLat.lat * Math.PI / 180;
  const deltaLatRad = (rightLngLat.lat - leftLngLat.lat) * Math.PI / 180;
  const deltaLngRad = (rightLngLat.lng - leftLngLat.lng) * Math.PI / 180;
  const haversine = Math.sin(deltaLatRad / 2) ** 2
    + Math.cos(leftLatRad) * Math.cos(rightLatRad) * Math.sin(deltaLngRad / 2) ** 2;
  return earthRadiusKm * 2 * Math.atan2(Math.sqrt(haversine), Math.sqrt(1 - haversine));
}

function nearestRainyStationForLngLat(lngLat) {
  let nearestStation = null;
  const mapFeatures = currentData?.features || [];
  mapFeatures.forEach((feature) => {
    const rainTotal = featureRainTotal(feature);
    if (!Number.isFinite(rainTotal) || rainTotal <= 0) {
      return;
    }
    const coordinates = feature.geometry?.coordinates || [];
    const longitude = Number(coordinates[0]);
    const latitude = Number(coordinates[1]);
    if (!Number.isFinite(longitude) || !Number.isFinite(latitude)) {
      return;
    }
    const distanceKm = distanceKmBetweenLngLat(
      { lng: lngLat.lng, lat: lngLat.lat },
      { lng: longitude, lat: latitude },
    );
    if (!nearestStation || distanceKm < nearestStation.distanceKm) {
      nearestStation = { feature, distanceKm, rainTotal };
    }
  });
  return nearestStation;
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

  const selectedPeriod = currentPeriodFileName;
  const popupStationId = activeStationPopupId;
  updateMetricScale(metricScaleFeatures(currentVisibleFeatures));
  currentVisibleFeatures = currentVisibleFeatures.map(prepareFeature);
  const features = filteredFeatures(currentVisibleFeatures);
  currentHeatmapData = {
    type: "FeatureCollection",
    metadata: currentHeatmapData?.metadata || currentData?.metadata || {},
    features: heatmapFeatures(currentVisibleFeatures),
  };
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
  updateSummary(selectedPeriod, features.length, currentVisibleFeatures.length, invalidFeatureCount);
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

function addStationLayer({ resetEstimatedField = false } = {}) {
  if (!currentData || !map.isStyleLoaded()) {
    return false;
  }

  if (map.getLayer(CIRCLE_LAYER_ID)) {
    map.removeLayer(CIRCLE_LAYER_ID);
  }
  if (map.getLayer(HEATMAP_LAYER_ID)) {
    map.removeLayer(HEATMAP_LAYER_ID);
  }
  if (resetEstimatedField) {
    removeEstimatedFieldLayer();
  }
  if (map.getSource(SOURCE_ID)) {
    map.removeSource(SOURCE_ID);
  }
  if (map.getSource(HEATMAP_SOURCE_ID)) {
    map.removeSource(HEATMAP_SOURCE_ID);
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

  if (canUseHeatmap() && heatmapEnabled) {
    map.addSource(HEATMAP_SOURCE_ID, {
      type: "geojson",
      data: currentHeatmapData || { type: "FeatureCollection", features: [] },
    });
    map.addLayer({
      id: HEATMAP_LAYER_ID,
      type: "heatmap",
      source: HEATMAP_SOURCE_ID,
      maxzoom: 12,
      paint: {
        "heatmap-weight": heatmapWeightExpression(),
        "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 5, 0.7 * heatmapIntensityScale, 9, 1.35 * heatmapIntensityScale, 12, 1.75 * heatmapIntensityScale],
        "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 5, 34 * heatmapRadiusScale, 9, 82 * heatmapRadiusScale, 12, 145 * heatmapRadiusScale],
        "heatmap-opacity": ["interpolate", ["linear"], ["zoom"], 5, heatmapOpacity, 11, heatmapOpacity * 0.82, 12, heatmapOpacity * 0.35],
        "heatmap-color": [
          "interpolate",
          ["linear"],
          ["heatmap-density"],
          0,
          "rgba(78, 165, 255, 0)",
          0.12,
          "#4ea5ff",
          0.28,
          "#78c679",
          0.45,
          "#fecc5c",
          0.62,
          "#fd8d3c",
          0.78,
          "#f03b20",
          0.9,
          "#bd0026",
          1,
          "#7a0177",
        ],
      },
    });
  }
  updateEstimatedFieldLayer({ immediate: true });
  applyTerrain();
  return true;
}

function reloadCurrentPeriodAfterStyleChange(center, zoom, attempt = 0) {
  if (!map.isStyleLoaded()) {
    if (attempt < 40) {
      window.setTimeout(() => reloadCurrentPeriodAfterStyleChange(center, zoom, attempt + 1), 100);
    } else {
      baseStyleReloadPending = false;
    }
    return;
  }

  applyTerrain();
  map.jumpTo({ center, zoom });
  const selectedPeriod = currentPeriodFileName;
  loadMap(selectedPeriod)
    .then(() => {
      map.jumpTo({ center, zoom });
      window.setTimeout(() => {
        baseStyleReloadPending = false;
      }, 0);
    })
    .catch((error) => {
      baseStyleReloadPending = false;
      document.getElementById("summary").textContent = error.message;
    });
}

function popupContent(properties) {
  const station = properties["Codi Estació"] || "";
  const visibleStation = displayStationCode(station);
  const name = properties["Estació"] || t("unknownStation");
  const town = properties["Municipi"] || t("unknownTown");
  const province = properties["Provincia"] || "";
  const altitude = properties["Altitud"] || "-";
  const totalValue = parseOptionalNumber(properties["Total"]);
  const total = Number.isFinite(totalValue) ? totalValue.toFixed(1) : "-";
  const lastReading = properties["Ultima Lectura"] || "-";
  const lastRain = lastRainRecord(properties);
  const periodWeather = periodWeatherSummary(properties);
  const rainHistory = recentRainHistory(properties);

  return `
    <div class="popup-title">${visibleStation} · ${name}</div>
    <div class="popup-row popup-metrics"><span><strong>${t("rain")}:</strong> ${total} mm</span><span><strong>${t("last")}:</strong> ${lastRain}</span></div>
    ${periodWeather}
    <div class="popup-row"><strong>${t("location")}:</strong> ${town}${province ? `, ${province}` : ""}</div>
    <div class="popup-row"><strong>${t("altitude")}:</strong> ${altitude} m</div>
    <div class="popup-row"><strong>${t("lastReading")}:</strong> ${lastReading}</div>
    ${sourceAttribution(properties)}
    ${rainHistory}
  `;
}

function numericProperty(properties, key) {
  return parseOptionalNumber(properties?.[key]);
}

function formatNumber(value, decimals = 1) {
  return Number.isFinite(value) ? value.toFixed(decimals) : "-";
}

function formatRange(maxValue, minValue, unit, decimals = 1) {
  if (!Number.isFinite(maxValue) && !Number.isFinite(minValue)) {
    return "-";
  }
  if (Number.isFinite(maxValue) && Number.isFinite(minValue)) {
    return `${formatNumber(maxValue, decimals)}/${formatNumber(minValue, decimals)} ${unit}`;
  }
  const value = Number.isFinite(maxValue) ? maxValue : minValue;
  return `${formatNumber(value, decimals)} ${unit}`;
}

function formatDirection(value) {
  if (!Number.isFinite(value)) {
    return "-";
  }
  const directions = currentLanguage === "en"
    ? ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    : ["N", "NE", "E", "SE", "S", "SO", "O", "NO"];
  const normalized = ((value % 360) + 360) % 360;
  return directions[Math.round(normalized / 45) % directions.length];
}

function formatWind(speed, direction) {
  if (!Number.isFinite(speed) && !Number.isFinite(direction)) {
    return "-";
  }
  if (Number.isFinite(speed) && Number.isFinite(direction)) {
    return `${formatNumber(speed)} km/h · ${formatDirection(direction)}`;
  }
  if (Number.isFinite(speed)) {
    return `${formatNumber(speed)} km/h`;
  }
  return formatDirection(direction);
}

function periodWeatherSummary(properties) {
  const tempMax = numericProperty(properties, "max_temp_celsius");
  const tempMin = numericProperty(properties, "min_temp_celsius");
  const humidityMax = numericProperty(properties, "max_humidity_percent");
  const humidityMin = numericProperty(properties, "min_humidity_percent");
  const windAvg = numericProperty(properties, "wind_avg_kmh");
  const windDirection = numericProperty(properties, "wind_direction_deg");
  const windGust = numericProperty(properties, "wind_gust_kmh");

  const hasWeather = [
    tempMax,
    tempMin,
    humidityMax,
    humidityMin,
    windAvg,
    windDirection,
    windGust,
  ].some((value) => Number.isFinite(value));
  if (!hasWeather) {
    return "";
  }

  const temperatureText = formatRange(tempMax, tempMin, "°C");
  const humidityText = formatRange(humidityMax, humidityMin, "%", 0);
  const windText = formatWind(windAvg, windDirection);
  const gustText = Number.isFinite(windGust) ? ` · ${t("gust")} ${formatNumber(windGust)} km/h` : "";
  const windLine = windText === "-" && !gustText ? "" : `<span><strong>${t("wind")}:</strong> ${windText}${gustText}</span>`;
  return `
    <div class="popup-row popup-weather">
      <span><strong>${t("temperature")}:</strong> ${temperatureText}</span>
      <span><strong>${t("humidity")}:</strong> ${humidityText}</span>
      ${windLine}
    </div>
  `;
}

function formatDistanceKm(distanceKm) {
  if (!Number.isFinite(distanceKm)) {
    return "-";
  }
  if (distanceKm < 1) {
    return `${Math.round(distanceKm * 1000)} m`;
  }
  return `${distanceKm.toFixed(distanceKm < 10 ? 1 : 0)} km`;
}

function currentPeriodLabel() {
  const selectedFile = currentPeriodFileName;
  return periodLabel(selectedFile) || t("selectedPeriod");
}

function nearestRainyStationContent(nearestStation) {
  const periodLabel = currentPeriodLabel();
  if (!nearestStation?.feature) {
    return `
      <div class="popup-row terrain-nearest-title"><strong>${t("nearestRainyStation")}:</strong></div>
      <div class="popup-row">${t("noRainyStation", { period: periodLabel })}</div>
    `;
  }

  const properties = nearestStation.feature.properties || {};
  const station = properties["Codi Estació"] || "";
  const name = properties["Estació"] || t("unknownStation");
  const town = properties["Municipi"] || t("unknownTown");
  const province = properties["Provincia"] || "";
  const altitude = properties["Altitud"] || "-";
  const location = `${town}${province ? `, ${province}` : ""}`;
  const rainTotal = nearestStation.rainTotal.toFixed(1);
  return `
    <div class="popup-row terrain-nearest-title"><strong>${t("nearestRainyStation")}:</strong></div>
    <div class="popup-row">${station ? `${station} · ` : ""}${name}</div>
    <div class="popup-row"><strong>${t("rain")}:</strong> ${rainTotal} mm (${periodLabel})</div>
    <div class="popup-row"><strong>${t("distance")}:</strong> ${formatDistanceKm(nearestStation.distanceKm)}</div>
    <div class="popup-row"><strong>${t("location")}:</strong> ${location}</div>
    <div class="popup-row"><strong>${t("stationAltitude")}:</strong> ${altitude} m</div>
  `;
}

function terrainPopupContent(elevation, lngLat, status = "loading", nearestStation = null) {
  const latitude = lngLat.lat.toFixed(5);
  const longitude = lngLat.lng.toFixed(5);
  const nearestStationHtml = nearestRainyStationContent(nearestStation);
  if (!Number.isFinite(elevation)) {
    const altitudeText = status === "error" ? t("unavailable") : t("loading");
    const noteText = status === "error"
      ? t("externalDemUnavailable")
      : t("loadingExternalDem");
    return `
      <div class="popup-title">${latitude}, ${longitude}</div>
      <div class="popup-row"><strong>${t("altitude")}:</strong> ${altitudeText}</div>
      <div class="popup-row terrain-note">${noteText}</div>
      ${nearestStationHtml}
    `;
  }

  return `
    <div class="popup-title">${latitude}, ${longitude}</div>
    <div class="popup-row"><strong>${t("altitude")}:</strong> ${Math.round(elevation).toLocaleString(currentLanguage)} m</div>
    <div class="popup-row terrain-note">${t("externalDem")}</div>
    ${nearestStationHtml}
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
  const nearestStation = nearestRainyStationForLngLat(lngLat);

  const terrainPopup = new maplibregl.Popup({
    closeButton: false,
    closeOnClick: true,
    maxWidth: "320px",
    anchor: "left",
    offset: 8,
  })
    .setLngLat(lngLat)
    .setHTML(terrainPopupContent(null, lngLat, "loading", nearestStation))
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
        terrainPopup.setHTML(terrainPopupContent(elevation, lngLat, "loaded", nearestStation));
      }
    })
    .catch((error) => {
      console.warn("Cannot query terrain elevation", error);
      if (currentPopup === terrainPopup) {
        terrainPopup.setHTML(terrainPopupContent(null, lngLat, "error", nearestStation));
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
    const temperatureText = compactRangeHtml(record.tempMaxValue, record.tempMinValue, 0);
    const humidityText = compactRangeHtml(record.humidityMaxValue, record.humidityMinValue, 0);
    const windText = compactWindHtml(record.windAvgValue, record.windDirectionValue);
    rows.push(`
      <tr class="${hasRain ? "rainy-day" : ""}">
        <td>${record.date}</td>
        <td>${record.daysAgo}</td>
        <td>${Number.isFinite(record.rainValue) ? record.rainValue.toFixed(1) : record.rain}</td>
        <td>${temperatureText}</td>
        <td>${humidityText}</td>
        <td>${windText}</td>
      </tr>
    `);
  }

  if (rows.length === 0) {
    return "";
  }

  return `
    <details class="history">
      <summary>${t("lastRecords", { count: rows.length })}</summary>
      <table class="history-table">
        <thead>
          <tr>
            <th>${t("date")}</th>
            <th>${t("daysShort")}</th>
            <th>mm</th>
            <th>°C</th>
            <th>%</th>
            <th>km/h</th>
          </tr>
        </thead>
        <tbody>${rows.join("")}</tbody>
      </table>
    </details>
  `;
}

function compactRangeHtml(maxValue, minValue, decimals = 0) {
  if (!Number.isFinite(maxValue) && !Number.isFinite(minValue)) {
    return "-";
  }
  if (Number.isFinite(maxValue) && Number.isFinite(minValue)) {
    return `
      <span class="history-range">
        <span class="history-range-value">${formatNumber(maxValue, decimals)}</span>
        <span class="history-range-separator">/</span>
        <span class="history-range-value">${formatNumber(minValue, decimals)}</span>
      </span>
    `;
  }
  const value = Number.isFinite(maxValue) ? maxValue : minValue;
  return `<span class="history-range history-range-single">${formatNumber(value, decimals)}</span>`;
}

function compactWindHtml(speed, direction) {
  if (!Number.isFinite(speed) && !Number.isFinite(direction)) {
    return "-";
  }
  const speedText = Number.isFinite(speed) ? formatNumber(speed, 0) : "";
  const directionText = Number.isFinite(direction) ? formatDirection(direction) : "";
  if (Number.isFinite(speed) && Number.isFinite(direction)) {
    return `
      <span class="history-wind">
        <span class="history-wind-speed">${speedText}</span>
        <span class="history-wind-direction">${directionText}</span>
      </span>
    `;
  }
  if (Number.isFinite(speed)) {
    return `<span class="history-wind history-wind-speed-only"><span class="history-wind-speed">${speedText}</span></span>`;
  }
  return `<span class="history-wind history-wind-direction-only"><span class="history-wind-direction">${directionText}</span></span>`;
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
    const humidityMax = properties[`Hum_Max_${suffix}`];
    const humidityMin = properties[`Hum_Min_${suffix}`];
    const windAvg = properties[`Wind_Avg_${suffix}`];
    const windDirection = properties[`Wind_Dir_${suffix}`];
    if (!date || date === "None" || date === "NaT" || date === "nan") {
      continue;
    }
    const rainValue = parseOptionalNumber(rain);
    const tempMaxValue = parseOptionalNumber(tempMax);
    const tempMinValue = parseOptionalNumber(tempMin);
    const humidityMaxValue = parseOptionalNumber(humidityMax);
    const humidityMinValue = parseOptionalNumber(humidityMin);
    const windAvgValue = parseOptionalNumber(windAvg);
    const windDirectionValue = parseOptionalNumber(windDirection);
    records.push({
      date,
      daysAgo: daysAgo(date),
      rain,
      rainValue,
      tempMaxValue,
      tempMinValue,
      humidityMaxValue,
      humidityMinValue,
      windAvgValue,
      windDirectionValue,
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

function updateSummary(fileName, count, totalCount = count, invalidCount = 0) {
  const summary = document.getElementById("summary");
  const stationText = `${count} ${count === 1 ? t("station") : t("stations")}`;
  const hasSourceFilter = enabledStationSources.size < stationSources.length;
  const hasInvalidFeatures = invalidCount > 0;
  const hasAnyFilter = minRainFilter > 0 || hasSourceFilter || hasInvalidFeatures;
  const mainParts = [periodLabel(fileName), stationText];
  const detailParts = [];

  if (hasAnyFilter) {
    mainParts.push(`${totalCount} ${t("total")}`);
  }
  if (minRainFilter > 0) {
    detailParts.push(`${t("min")}: ${minRainFilter} mm`);
  }
  if (hasSourceFilter) {
    detailParts.push(`${t("sources")}: ${enabledStationSources.size}/${stationSources.length}`);
  }
  if (hasInvalidFeatures) {
    detailParts.push(`${t("invalid")}: ${invalidCount}`);
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
  if (!container) {
    return;
  }

  container.innerHTML = Object.keys(periods).map((fileName) => `
    <button class="period-timeline-button" type="button" data-period="${fileName}">
      <span>${periodShortLabel(fileName)}</span>
    </button>
  `).join("");

  if (!container.dataset.bound) {
    container.dataset.bound = "true";
    container.addEventListener("click", (event) => {
      const button = event.target.closest(".period-timeline-button");
      if (!button) {
        return;
      }
      const selectedPeriod = button.dataset.period;
      currentPeriodFileName = selectedPeriod;
      syncVisiblePeriodSelector(currentPeriodFileName);
      updatePeriodTimeline(currentPeriodFileName);
      loadMap(currentPeriodFileName).catch((error) => {
        document.getElementById("summary").textContent = error.message;
      });
    });
  }

  updatePeriodTimeline(currentPeriodFileName);
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
  if (savedMapView) {
    map.jumpTo({
      center: [savedMapView.lng, savedMapView.lat],
      zoom: savedMapView.zoom,
      bearing: savedMapView.bearing || 0,
      pitch: savedMapView.pitch || 0,
    });
    return;
  }

  const features = currentData?.features || [];
  if (features.length === 0) {
    map.fitBounds(FALLBACK_BOUNDS, { padding: 24 });
    return;
  }

  const bounds = new maplibregl.LngLatBounds();
  features.forEach((feature) => bounds.extend(feature.geometry.coordinates));
  map.fitBounds(bounds, { padding: 24, duration: 0 });
}

async function loadMap(fileName) {
  currentPeriodFileName = fileName;
  syncVisiblePeriodSelector(currentPeriodFileName);
  const url = `${DATA_BASE}${fileName}`;
  const response = await authFetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Cannot load ${url}: ${response.status}`);
  }
  const data = await response.json();
  const popupStationId = activeStationPopupId;
  const rawFeatures = data.features || [];
  const visible = validCoordinateFeatures(rawFeatures);
  invalidFeatureCount = Math.max(0, rawFeatures.length - visible.length);
  updateRainScale(visible);
  updateMinRainControl(visible);
  updateLastRainHistoryControl(visible);
  updateMetricScale(metricScaleFeatures(visible));
  const features = visible.map(prepareFeature);
  currentVisibleFeatures = features;
  currentHeatmapData = {
    ...data,
    features: heatmapFeatures(features),
  };
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
  updateSummary(fileName, filtered.length, features.length, invalidFeatureCount);
  updateGeneratedAt(data.metadata?.generated_at);
  updatePeriodTimeline(fileName);
  syncSettingsPeriodSelector(preferredPeriodFileName);
  openStationPopup(findFeatureByStationId(filtered, popupStationId));

  if (!hasLoadedInitialMap) {
    hasLoadedInitialMap = true;
    fitToData();
  }
}

function selectBaseStyle(styleId, { persistPreference = false } = {}) {
  const nextStyle = baseStyles.find((style) => style.id === styleId);
  if (!nextStyle || nextStyle.id === currentStyle.id) {
    if (nextStyle && persistPreference && preferredMapStyleId !== nextStyle.id) {
      preferredMapStyleId = nextStyle.id;
      markDeviceSettingsChanged();
      setLayerControlsFromStyle(preferredMapStyleId);
    }
    return;
  }

  if (persistPreference) {
    preferredMapStyleId = nextStyle.id;
    markDeviceSettingsChanged();
  }

  currentStyle = nextStyle;
  if (persistPreference) {
    setLayerControlsFromStyle(preferredMapStyleId);
  }
  setQuickMapControlsFromStyle(currentStyle.id);
  const center = map.getCenter();
  const zoom = map.getZoom();
  let reloadedCurrentPeriod = false;
  baseStyleReloadPending = true;
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
}

function renderLayerSwitcher() {
  const container = document.getElementById("layer-switcher");
  container.innerHTML = baseStyles.map((style) => `
    <label>
      <input type="radio" name="base-style" value="${style.id}" ${style.id === preferredMapStyleId ? "checked" : ""}>
      <span>${styleLabel(style)}</span>
    </label>
  `).join("");

  if (!container.dataset.bound) {
    container.dataset.bound = "true";
    container.addEventListener("change", (event) => {
      if (!event.target.matches("input[name='base-style']")) {
        return;
      }
      selectBaseStyle(event.target.value, { persistPreference: true });
    });
  }
}

function renderQuickMapPanelOptions() {
  const panel = document.getElementById("quick-map-panel");
  if (!panel) {
    return;
  }
  panel.innerHTML = baseStyles.map((style) => `
    <button class="quick-map-option" type="button" data-style-id="${style.id}">
      <span>${styleLabel(style)}</span>
    </button>
  `).join("");
  setQuickMapControlsFromStyle(currentStyle.id);
}

function renderQuickMapPanel() {
  const toggle = document.getElementById("quick-map-toggle");
  const panel = document.getElementById("quick-map-panel");
  if (!toggle || !panel) {
    return;
  }

  renderQuickMapPanelOptions();

  const setQuickMapOpen = (isOpen) => {
    if (isOpen) {
      closeSecondaryPanels({ except: "quick-map" });
    }
    panel.toggleAttribute("hidden", !isOpen);
    toggle.setAttribute("aria-expanded", String(isOpen));
  };

  toggle.addEventListener("click", (event) => {
    event.stopPropagation();
    setQuickMapOpen(panel.hasAttribute("hidden"));
  });

  panel.addEventListener("click", (event) => {
    event.stopPropagation();
    const button = event.target.closest(".quick-map-option");
    if (!button) {
      return;
    }
    selectBaseStyle(button.dataset.styleId, { persistPreference: false });
    setQuickMapOpen(false);
  });

  map.on("click", () => {
    if (!panel.hasAttribute("hidden")) {
      setQuickMapOpen(false);
    }
  });

  setLayerControlsFromStyle(preferredMapStyleId);
  setQuickMapControlsFromStyle(currentStyle.id);
}

function renderQuickMetricPanelOptions() {
  const panel = document.getElementById("quick-metric-panel");
  const toggle = document.getElementById("quick-metric-toggle");
  if (!panel || !toggle) {
    return;
  }
  toggle.hidden = !canUseLayerMetrics();
  if (!canUseLayerMetrics()) {
    panel.hidden = true;
    return;
  }
  panel.innerHTML = layerMetrics.map((metric) => `
    <button class="quick-metric-option" type="button" data-metric-id="${metric.id}">
      <span>${layerMetricLabel(metric)}</span>
    </button>
  `).join("");
  setQuickMetricControlsFromMetric();
}

function renderQuickMetricPanel() {
  const toggle = document.getElementById("quick-metric-toggle");
  const panel = document.getElementById("quick-metric-panel");
  if (!toggle || !panel) {
    return;
  }

  renderQuickMetricPanelOptions();

  const setQuickMetricOpen = (isOpen) => {
    if (!canUseLayerMetrics()) {
      return;
    }
    if (isOpen) {
      closeSecondaryPanels({ except: "quick-metric" });
    }
    panel.toggleAttribute("hidden", !isOpen);
    toggle.setAttribute("aria-expanded", String(isOpen));
  };

  toggle.addEventListener("click", (event) => {
    event.stopPropagation();
    setQuickMetricOpen(panel.hasAttribute("hidden"));
  });

  panel.addEventListener("click", (event) => {
    event.stopPropagation();
    const button = event.target.closest(".quick-metric-option");
    if (!button) {
      return;
    }
    currentLayerMetric = button.dataset.metricId;
    markDeviceSettingsChanged();
    const metricSelector = document.getElementById("layer-metric-selector");
    if (metricSelector) {
      metricSelector.value = currentLayerMetric;
    }
    setQuickMetricControlsFromMetric();
    refreshMetricStyling();
    setQuickMetricOpen(false);
  });

  map.on("click", () => {
    if (!panel.hasAttribute("hidden")) {
      setQuickMetricOpen(false);
    }
  });
}

function closeSecondaryPanels({ except = "" } = {}) {
  const quickMapPanel = document.getElementById("quick-map-panel");
  const quickMapToggle = document.getElementById("quick-map-toggle");
  const quickMetricPanel = document.getElementById("quick-metric-panel");
  const quickMetricToggle = document.getElementById("quick-metric-toggle");
  const attributionPanel = document.getElementById("map-attribution");
  const infoToggle = document.getElementById("info-toggle");
  const helpPanel = document.getElementById("map-help");
  const helpToggle = document.getElementById("help-toggle");

  if (except !== "quick-map" && quickMapPanel && quickMapToggle) {
    quickMapPanel.hidden = true;
    quickMapToggle.setAttribute("aria-expanded", "false");
  }
  if (except !== "quick-metric" && quickMetricPanel && quickMetricToggle) {
    quickMetricPanel.hidden = true;
    quickMetricToggle.setAttribute("aria-expanded", "false");
  }
  if (except !== "credits" && attributionPanel && infoToggle) {
    attributionPanel.hidden = true;
    infoToggle.setAttribute("aria-expanded", "false");
  }
  if (except !== "help" && helpPanel && helpToggle) {
    helpPanel.hidden = true;
    helpToggle.setAttribute("aria-expanded", "false");
  }
}

function renderSettingsPanel() {
  const toggle = document.getElementById("settings-toggle");
  const northToggle = document.getElementById("north-toggle");
  const infoToggle = document.getElementById("info-toggle");
  const heatmapToggle = document.getElementById("heatmap-toggle");
  const estimatedFieldToggle = document.getElementById("estimated-field-toggle");
  const attributionPanel = document.getElementById("map-attribution");
  const helpToggle = document.getElementById("help-toggle");
  const helpPanel = document.getElementById("map-help");
  const panel = document.getElementById("map-settings");
  const settingsTabs = Array.from(panel.querySelectorAll("[data-settings-tab]"));
  const settingsSections = Array.from(panel.querySelectorAll("[data-settings-section]"));
  const languageSelector = document.getElementById("language-selector");
  const settingsPeriodSelector = document.getElementById("settings-period-selector");
  const slider = document.getElementById("min-rain-filter");
  const historySlider = document.getElementById("last-rain-history-filter");
  const heatmapExperimentSettings = document.getElementById("heatmap-experiment-settings");
  const heatmapSettingsTab = document.getElementById("settings-tab-heatmap");
  const layerMetricSelector = document.getElementById("layer-metric-selector");
  const heatmapEnabledToggle = document.getElementById("heatmap-enabled-toggle");
  const heatmapWeightCurveSelector = document.getElementById("heatmap-weight-curve-selector");
  const heatmapOpacitySlider = document.getElementById("heatmap-opacity-filter");
  const heatmapRadiusSlider = document.getElementById("heatmap-radius-filter");
  const heatmapIntensitySlider = document.getElementById("heatmap-intensity-filter");
  const resetHeatmapDefaultsButton = document.getElementById("reset-heatmap-defaults");
  const estimatedFieldSettings = document.getElementById("estimated-field-settings");
  const estimatedFieldSettingsTab = document.getElementById("settings-tab-estimated-field");
  const estimatedFieldEnabledToggle = document.getElementById("estimated-field-enabled-toggle");
  const estimatedFieldOpacitySlider = document.getElementById("estimated-field-opacity-filter");
  const estimatedFieldRadiusSelector = document.getElementById("estimated-field-radius-selector");
  const estimatedFieldQualitySelector = document.getElementById("estimated-field-quality-selector");
  const estimatedFieldSmoothingSelector = document.getElementById("estimated-field-smoothing-selector");
  const estimatedFieldAltitudeCorrectionToggle = document.getElementById("estimated-field-altitude-correction-toggle");
  const resetEstimatedFieldDefaultsButton = document.getElementById("reset-estimated-field-defaults");
  const terrainToggle = document.getElementById("terrain-toggle");
  const terrainSlider = document.getElementById("terrain-exaggeration");
  const terrainModeToggle = document.getElementById("terrain-mode-toggle");
  const saveMapViewButton = document.getElementById("save-map-view-default");
  const sourceInputs = Array.from(panel.querySelectorAll("input[name='station-source']"));
  if (heatmapExperimentSettings) {
    heatmapExperimentSettings.hidden = !canUseHeatmap();
  }
  if (heatmapSettingsTab) {
    heatmapSettingsTab.hidden = !canUseHeatmap();
  }
  if (estimatedFieldSettings) {
    estimatedFieldSettings.hidden = !canUseEstimatedField();
  }
  if (estimatedFieldSettingsTab) {
    estimatedFieldSettingsTab.hidden = !canUseEstimatedField();
  }
  const layerMetricRow = layerMetricSelector?.closest(".map-settings-row");
  if (layerMetricRow) {
    layerMetricRow.hidden = !canUseLayerMetrics();
  }
  updateHeatmapToggle();
  syncHeatmapEnabledControl();
  renderLayerMetricSelector();
  renderHeatmapWeightCurveSelector();
  if (heatmapOpacitySlider) {
    heatmapOpacitySlider.value = String(Math.round(heatmapOpacity * 100));
  }
  if (heatmapRadiusSlider) {
    heatmapRadiusSlider.value = String(Math.round(heatmapRadiusScale * 100));
  }
  if (heatmapIntensitySlider) {
    heatmapIntensitySlider.value = String(Math.round(heatmapIntensityScale * 100));
  }
  updateHeatmapOpacityValue();
  updateHeatmapRadiusValue();
  updateHeatmapIntensityValue();
  syncEstimatedFieldEnabledControl();
  if (estimatedFieldOpacitySlider) {
    estimatedFieldOpacitySlider.value = String(Math.round(estimatedFieldOpacity * 100));
  }
  if (estimatedFieldAltitudeCorrectionToggle) {
    estimatedFieldAltitudeCorrectionToggle.checked = estimatedFieldAltitudeCorrection;
  }
  renderEstimatedFieldSelectors();
  updateEstimatedFieldOpacityValue();
  updateEstimatedFieldToggle();

  const showSettingsTab = (tabName) => {
    settingsTabs.forEach((tab) => {
      const isActive = tab.dataset.settingsTab === tabName;
      tab.classList.toggle("is-active", isActive);
      tab.setAttribute("aria-selected", String(isActive));
    });
    settingsSections.forEach((section) => {
      section.classList.toggle("is-active", section.dataset.settingsSection === tabName);
    });
  };

  settingsTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      if (!tab.hidden) {
        showSettingsTab(tab.dataset.settingsTab);
      }
    });
  });

  const setSettingsOpen = (isOpen) => {
    const wasOpen = !panel.hasAttribute("hidden");
    if (!wasOpen && isOpen) {
      hasPendingDeviceSettingsChanges = false;
      if (saveMapViewButton) {
        saveMapViewButton.textContent = t("setCurrentViewDefault");
      }
    }
    if (isOpen) {
      closeSecondaryPanels();
    }
    panel.toggleAttribute("hidden", !isOpen);
    toggle.setAttribute("aria-expanded", String(isOpen));
    document.body.classList.toggle("settings-open", isOpen);
    if (wasOpen && !isOpen && hasPendingDeviceSettingsChanges) {
      saveDeviceSettings();
      hasPendingDeviceSettingsChanges = false;
    }
  };

  toggle.addEventListener("click", () => {
    setSettingsOpen(panel.hasAttribute("hidden"));
  });

  map.on("click", () => {
    if (!panel.hasAttribute("hidden")) {
      setSettingsOpen(false);
    }
    closeSecondaryPanels();
  });

  northToggle.addEventListener("click", () => {
    map.easeTo({ bearing: 0, duration: 350 });
  });

  heatmapToggle?.addEventListener("click", () => {
    if (!canUseHeatmap()) {
      return;
    }
    setHeatmapEnabled(!heatmapEnabled);
    addStationLayer();
  });

  estimatedFieldToggle?.addEventListener("click", () => {
    if (!canUseEstimatedField()) {
      return;
    }
    setEstimatedFieldEnabled(!estimatedFieldEnabled);
    if (estimatedFieldEnabled) {
      addStationLayer();
    } else {
      removeEstimatedFieldLayer();
    }
  });

  infoToggle.addEventListener("click", () => {
    const isOpen = attributionPanel.hasAttribute("hidden");
    if (isOpen) {
      closeSecondaryPanels({ except: "credits" });
      setSettingsOpen(false);
    }
    attributionPanel.toggleAttribute("hidden", !isOpen);
    infoToggle.setAttribute("aria-expanded", String(isOpen));
  });

  helpToggle.addEventListener("click", () => {
    const isOpen = helpPanel.hasAttribute("hidden");
    if (isOpen) {
      closeSecondaryPanels({ except: "help" });
      setSettingsOpen(false);
    }
    helpPanel.toggleAttribute("hidden", !isOpen);
    helpToggle.setAttribute("aria-expanded", String(isOpen));
  });

  languageSelector.addEventListener("change", (event) => {
    markDeviceSettingsChanged();
    applyLanguage(event.target.value);
  });

  settingsPeriodSelector.addEventListener("change", (event) => {
    markDeviceSettingsChanged();
    const selectedPeriod = event.target.value;
    preferredPeriodFileName = selectedPeriod;
    currentPeriodFileName = selectedPeriod;
    syncVisiblePeriodSelector(currentPeriodFileName);
    loadMap(currentPeriodFileName).catch((error) => {
      document.getElementById("summary").textContent = error.message;
    });
  });

  slider.addEventListener("input", (event) => {
    markDeviceSettingsChanged();
    minRainFilter = Number(event.target.value);
    updateMinRainValue();
    refreshFilteredData();
  });

  historySlider.addEventListener("input", (event) => {
    markDeviceSettingsChanged();
    lastRainHistoryLimit = Number(event.target.value);
    updateLastRainHistoryValue();
    refreshCurrentStationPopup();
  });

  layerMetricSelector?.addEventListener("change", (event) => {
    currentLayerMetric = event.target.value;
    markDeviceSettingsChanged();
    refreshMetricStyling();
  });

  heatmapEnabledToggle?.addEventListener("change", (event) => {
    savedHeatmapEnabled = canUseHeatmap() && event.target.checked;
    heatmapEnabled = savedHeatmapEnabled;
    if (savedHeatmapEnabled) {
      savedEstimatedFieldEnabled = false;
      estimatedFieldEnabled = false;
      syncEstimatedFieldEnabledControl();
      updateEstimatedFieldToggle();
      removeEstimatedFieldLayer();
    }
    syncHeatmapEnabledControl();
    updateHeatmapToggle();
    markDeviceSettingsChanged();
    addStationLayer();
  });

  heatmapWeightCurveSelector?.addEventListener("change", (event) => {
    heatmapWeightCurve = event.target.value;
    markDeviceSettingsChanged();
    addStationLayer();
  });

  heatmapOpacitySlider?.addEventListener("input", (event) => {
    heatmapOpacity = Math.max(0, Math.min(1, Number(event.target.value) / 100));
    markDeviceSettingsChanged();
    updateHeatmapOpacityValue();
    addStationLayer();
  });

  heatmapRadiusSlider?.addEventListener("input", (event) => {
    heatmapRadiusScale = Math.max(0.5, Math.min(3, Number(event.target.value) / 100));
    markDeviceSettingsChanged();
    updateHeatmapRadiusValue();
    addStationLayer();
  });

  heatmapIntensitySlider?.addEventListener("input", (event) => {
    heatmapIntensityScale = Math.max(0.2, Math.min(2, Number(event.target.value) / 100));
    markDeviceSettingsChanged();
    updateHeatmapIntensityValue();
    addStationLayer();
  });

  resetHeatmapDefaultsButton?.addEventListener("click", () => {
    applyHeatmapDefaults();
    markDeviceSettingsChanged();
    addStationLayer();
  });

  estimatedFieldEnabledToggle?.addEventListener("change", (event) => {
    savedEstimatedFieldEnabled = canUseEstimatedField() && event.target.checked;
    estimatedFieldEnabled = savedEstimatedFieldEnabled;
    if (savedEstimatedFieldEnabled) {
      savedHeatmapEnabled = false;
      heatmapEnabled = false;
      syncHeatmapEnabledControl();
      updateHeatmapToggle();
    }
    syncEstimatedFieldEnabledControl();
    updateEstimatedFieldToggle();
    markDeviceSettingsChanged();
    if (estimatedFieldEnabled) {
      addStationLayer();
    } else {
      removeEstimatedFieldLayer();
    }
  });

  estimatedFieldOpacitySlider?.addEventListener("input", (event) => {
    estimatedFieldOpacity = Math.max(0, Math.min(1, Number(event.target.value) / 100));
    markDeviceSettingsChanged();
    updateEstimatedFieldOpacityValue();
    updateEstimatedFieldLayer();
  });

  estimatedFieldRadiusSelector?.addEventListener("change", (event) => {
    if (!ESTIMATED_FIELD_RADIUS_OPTIONS.includes(event.target.value)) {
      return;
    }
    estimatedFieldRadius = event.target.value;
    markDeviceSettingsChanged();
    updateEstimatedFieldLayer();
  });

  estimatedFieldQualitySelector?.addEventListener("change", (event) => {
    if (!ESTIMATED_FIELD_QUALITY_OPTIONS.includes(event.target.value)) {
      return;
    }
    estimatedFieldQuality = event.target.value;
    markDeviceSettingsChanged();
    updateEstimatedFieldLayer();
  });

  estimatedFieldSmoothingSelector?.addEventListener("change", (event) => {
    if (!ESTIMATED_FIELD_SMOOTHING_OPTIONS.includes(event.target.value)) {
      return;
    }
    estimatedFieldSmoothing = event.target.value;
    markDeviceSettingsChanged();
    updateEstimatedFieldLayer();
  });

  estimatedFieldAltitudeCorrectionToggle?.addEventListener("change", (event) => {
    estimatedFieldAltitudeCorrection = event.target.checked;
    markDeviceSettingsChanged();
    updateEstimatedFieldLayer();
  });

  resetEstimatedFieldDefaultsButton?.addEventListener("click", () => {
    applyEstimatedFieldDefaults();
    markDeviceSettingsChanged();
    if (estimatedFieldEnabled) {
      addStationLayer();
    } else {
      removeEstimatedFieldLayer();
    }
  });

  sourceInputs.forEach((input) => {
    input.addEventListener("change", () => {
      const selectedSources = sourceInputs.filter((sourceInput) => sourceInput.checked);
      if (selectedSources.length === 0) {
        input.checked = true;
        return;
      }
      markDeviceSettingsChanged();
      enabledStationSources = new Set(selectedSources.map((sourceInput) => sourceInput.value));
      refreshFilteredData();
    });
  });

  saveMapViewButton?.addEventListener("click", () => {
    captureCurrentMapViewAsDefault();
    saveMapViewButton.textContent = t("currentViewDefaultSaved");
  });

  updateTerrainExaggerationValue();

  terrainToggle.addEventListener("change", (event) => {
    markDeviceSettingsChanged();
    setTerrainEnabled(event.target.checked);
  });

  terrainModeToggle.addEventListener("click", () => {
    setTerrainEnabled(!terrainEnabled);
  });

  terrainSlider.addEventListener("input", (event) => {
    markDeviceSettingsChanged();
    terrainExaggeration = Number(event.target.value);
    updateTerrainExaggerationValue();
    applyTerrain();
  });
}

async function startViewer() {
  syncHeatmapAccessUi();
  syncEstimatedFieldAccessUi();
  await loadDeviceSettings();
  syncHeatmapAccessUi();
  syncEstimatedFieldAccessUi();
  await loadSourceStatus();
  await loadMap(selectedPeriodFileName());
}

map.on("load", async () => {
  await loadTranslations();
  renderLayerSwitcher();
  renderQuickMapPanel();
  renderQuickMetricPanel();
  renderPeriodTimeline();
  renderSettingsPanel();
  applyLanguage(currentLanguage);
  setupKeyboardShortcuts();
  setupLongPressElevation();
  updateTerrainModeButton();
  updateDemoZoomLevel();
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
  updateDemoZoomLevel();
  if (map.getZoom() < HOVER_POPUP_MIN_ZOOM) {
    closeHoverPopup();
  }
});

map.on("moveend", () => {
  if (baseStyleReloadPending) {
    return;
  }
  updateEstimatedFieldLayer();
});

map.on("zoomend", () => {
  if (baseStyleReloadPending) {
    return;
  }
  updateEstimatedFieldLayer();
});

document.getElementById("map-selector").addEventListener("change", (event) => {
  currentPeriodFileName = event.target.value;
  loadMap(currentPeriodFileName)
    .catch((error) => {
      document.getElementById("summary").textContent = error.message;
    });
});
