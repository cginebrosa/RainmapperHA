const defaultDataBase = window.location.pathname.includes("/maplibre-viewer/")
  ? "../docker-data/PublicData/"
  : "data/";
const DATA_BASE = new URLSearchParams(window.location.search).get("data") || defaultDataBase;

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
const jawgAccessToken = window.RAINMAPPER_CONFIG?.jawgmapsAccessToken || "";

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

if (jawgAccessToken) {
  baseStyles.push(
    {
      id: "jawg-streets",
      label: "Street",
      url: `https://api.jawg.io/styles/jawg-streets.json?access-token=${encodeURIComponent(jawgAccessToken)}`,
    },
    {
      id: "jawg-terrain",
      label: "Terrain",
      url: `https://api.jawg.io/styles/jawg-terrain.json?access-token=${encodeURIComponent(jawgAccessToken)}`,
    },
  );
}

let currentStyle = baseStyles[0];
let currentData = null;
let currentPopup = null;
let hasLoadedInitialMap = false;

function styleDefinition(style) {
  return style.style || style.url;
}

const map = new maplibregl.Map({
  container: "map",
  style: styleDefinition(currentStyle),
  center: INITIAL_CENTER,
  zoom: INITIAL_ZOOM,
  attributionControl: true,
});

map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-left");

function rainColor(total) {
  if (total >= 100) return "#7a001f";
  if (total >= 60) return "#c0002b";
  if (total >= 30) return "#ff4b2f";
  if (total >= 15) return "#ff9f32";
  if (total >= 5) return "#ffd166";
  return "#4ea5ff";
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
  return {
    ...feature,
    properties: {
      ...(feature.properties || {}),
      rain_color: rainColor(total),
      marker_radius: markerRadius(total),
    },
  };
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
  return true;
}

function reloadCurrentPeriodAfterStyleChange(center, zoom, attempt = 0) {
  if (!map.isStyleLoaded()) {
    if (attempt < 40) {
      window.setTimeout(() => reloadCurrentPeriodAfterStyleChange(center, zoom, attempt + 1), 100);
    }
    return;
  }

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
  const town = properties["Municipi"] || "Unknown town";
  const province = properties["Provincia"] || "";
  const altitude = properties["Altitud"] || "-";
  const total = Number(properties["Total"] || 0).toFixed(1);
  const lastReading = properties["Ultima Lectura"] || "-";
  const rainHistory = recentRainHistory(properties);

  return `
    <div class="popup-title">${station} · ${name}</div>
    <div class="popup-row"><strong>Rain:</strong> ${total} mm</div>
    <div class="popup-row"><strong>Location:</strong> ${town}${province ? `, ${province}` : ""}</div>
    <div class="popup-row"><strong>Altitude:</strong> ${altitude} m</div>
    <div class="popup-row"><strong>Last reading:</strong> ${lastReading}</div>
    ${rainHistory}
  `;
}

function recentRainHistory(properties) {
  const rows = [];
  for (let index = 1; index <= 21; index += 1) {
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
    rows.push(`
      <tr>
        <td>${date}</td>
        <td>${Number.isFinite(rainValue) ? rainValue.toFixed(1) : rain}</td>
        <td>${Number.isFinite(tempMaxValue) ? tempMaxValue.toFixed(1) : "-"}</td>
        <td>${Number.isFinite(tempMinValue) ? tempMinValue.toFixed(1) : "-"}</td>
      </tr>
    `);
  }

  if (rows.length === 0) {
    return "";
  }

  return `
    <details class="history" open>
      <summary>Last 21 rain records</summary>
      <table class="history-table">
        <thead>
          <tr>
            <th>Date</th>
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

function updateSummary(fileName, count) {
  document.getElementById("summary").textContent = `${periods[fileName]} · ${count} station${count === 1 ? "" : "s"}`;
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
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Cannot load ${url}: ${response.status}`);
  }
  const data = await response.json();
  const features = visibleFeatures(data.features || []).map(prepareFeature);
  currentData = {
    ...data,
    features,
  };

  if (currentPopup) {
    currentPopup.remove();
    currentPopup = null;
  }

  addStationLayer();
  updateSummary(fileName, features.length);
  updateGeneratedAt(data.metadata?.generated_at);

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

map.on("load", () => {
  renderLayerSwitcher();
  loadMap(document.getElementById("map-selector").value).catch((error) => {
    document.getElementById("summary").textContent = error.message;
  });
});

map.on("click", CIRCLE_LAYER_ID, (event) => {
  const feature = event.features?.[0];
  if (!feature) {
    return;
  }
  const coordinates = feature.geometry.coordinates.slice();
  currentPopup = new maplibregl.Popup({
    closeButton: false,
    closeOnClick: true,
    maxWidth: "320px",
    anchor: "left",
    offset: 8,
  })
    .setLngLat(coordinates)
    .setHTML(popupContent(feature.properties || {}))
    .addTo(map);
});

map.on("mouseenter", CIRCLE_LAYER_ID, () => {
  map.getCanvas().style.cursor = "pointer";
});

map.on("mouseleave", CIRCLE_LAYER_ID, () => {
  map.getCanvas().style.cursor = "";
});

document.getElementById("map-selector").addEventListener("change", (event) => {
  loadMap(event.target.value).catch((error) => {
    document.getElementById("summary").textContent = error.message;
  });
});
