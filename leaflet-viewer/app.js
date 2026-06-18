const defaultDataBase = (window.location.pathname.includes("/leaflet-viewer/") || window.location.pathname.includes("/mobile-viewer/"))
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

const DISPLAY_BOUNDS = L.latLngBounds(
  [39.0, -2.5],
  [43.7, 4.2],
);

const map = L.map("map", {
  preferCanvas: true,
  zoomControl: true,
  tap: true,
  maxBounds: DISPLAY_BOUNDS.pad(0.75),
  maxBoundsViscosity: 0.4,
}).setView([41.7, 2.1], 8);

const topographicLayer = L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", {
  maxZoom: 17,
  noWrap: true,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://opentopomap.org">OpenTopoMap</a>',
});

const hybridSatelliteLayer = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
  maxZoom: 19,
  noWrap: true,
  attribution: "Tiles &copy; Esri",
});

const hybridLabelsLayer = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}", {
  maxZoom: 19,
  noWrap: true,
  attribution: "Labels &copy; Esri",
});

const hybridRoadsLayer = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}", {
  maxZoom: 19,
  noWrap: true,
  attribution: "Roads &copy; Esri",
});

const hybridLayer = L.layerGroup([hybridSatelliteLayer, hybridRoadsLayer, hybridLabelsLayer]);

hybridLayer.addTo(map);

const baseLayers = {
  "Topographic": topographicLayer,
  "Hybrid": hybridLayer,
};

L.control.layers(
  baseLayers,
  {},
  { position: "topright" },
).addTo(map);

const RAIN_LEGEND_STEPS = [
  { label: "0-4.9", color: "#4ea5ff" },
  { label: "5-14.9", color: "#ffd166" },
  { label: "15-29.9", color: "#ff9f32" },
  { label: "30-59.9", color: "#ff4b2f" },
  { label: "60-99.9", color: "#c0002b" },
  { label: "100+", color: "#7a001f" },
];

function addRainLegend() {
  const legend = L.control({ position: "bottomleft" });
  legend.onAdd = () => {
    const container = L.DomUtil.create("div", "rain-legend");
    L.DomEvent.disableClickPropagation(container);
    container.innerHTML = `
      <div class="rain-legend-title">Rain</div>
      ${RAIN_LEGEND_STEPS.map((step) => `
        <div class="rain-legend-row">
          <span class="rain-legend-swatch" style="background:${step.color}"></span>
          <span>${step.label}</span>
        </div>
      `).join("")}
    `;
    return container;
  };
  legend.addTo(map);
}

addRainLegend();

let stationLayer = null;
let hasLoadedInitialMap = false;

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

function popupContent(properties) {
  const station = properties["Codi Estació"] || "";
  const name = properties["Estació"] || "Unknown station";
  const town = properties["Municipi"] || "Unknown town";
  const province = properties["Provincia"] || "";
  const altitude = properties["Altitud"] || "-";
  const total = Number(properties["Total"] || 0).toFixed(1);
  const lastReading = properties["Ultima Lectura"] || "-";
  const lastRain = lastRainRecord(properties);
  const rainHistory = recentRainHistory(properties);

  return `
    <div class="popup-title">${station} · ${name}</div>
    <div class="popup-row popup-metrics"><span><strong>Rain:</strong> ${total} mm</span><span><strong>Last:</strong> ${lastRain}</span></div>
    <div class="popup-row"><strong>Location:</strong> ${town}${province ? `, ${province}` : ""}</div>
    <div class="popup-row"><strong>Altitude:</strong> ${altitude} m</div>
    <div class="popup-row"><strong>Last reading:</strong> ${lastReading}</div>
    ${rainHistory}
  `;
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

function recentRainHistory(properties) {
  const rows = [];
  for (const record of rainHistoryRecords(properties)) {
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

function updateSummary(fileName, count) {
  const summary = document.getElementById("summary");
  summary.textContent = `${periods[fileName]} · ${count} station${count === 1 ? "" : "s"}`;
}

function updateGeneratedAt(generatedAt) {
  const generatedElement = document.getElementById("generated-at");
  if (!generatedElement) {
    return;
  }

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

async function loadMap(fileName) {
  const url = `${DATA_BASE}${fileName}`;
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Cannot load ${url}: ${response.status}`);
  }
  const data = await response.json();
  const features = data.features || [];
  const visibleFeatures = features.filter((feature) => {
    const coordinates = feature.geometry?.coordinates || [];
    const lon = Number(coordinates[0]);
    const lat = Number(coordinates[1]);
    return Number.isFinite(lat) && Number.isFinite(lon) && DISPLAY_BOUNDS.contains([lat, lon]);
  });
  const visibleData = {
    ...data,
    features: visibleFeatures,
  };
  const preserveView = hasLoadedInitialMap;

  map.closePopup();
  if (stationLayer) {
    stationLayer.remove();
  }

  stationLayer = L.geoJSON(visibleData, {
    pointToLayer: (feature, latlng) => {
      const total = Number(feature.properties?.Total || 0);
      return L.circleMarker(latlng, {
        radius: markerRadius(total),
        color: "#111923",
        weight: 1,
        fillColor: rainColor(total),
        fillOpacity: 0.72,
      });
    },
    onEachFeature: (feature, layer) => {
      layer.bindPopup(popupContent(feature.properties || {}), {
        autoPan: false,
        maxWidth: 320,
        minWidth: 250,
      });
    },
  }).addTo(map);

  const count = visibleFeatures.length;
  updateSummary(fileName, count);
  updateGeneratedAt(data.metadata?.generated_at);

  if (preserveView) {
    return;
  }

  hasLoadedInitialMap = true;
  if (count > 0) {
    map.fitBounds(stationLayer.getBounds(), { padding: [24, 24] });
  } else {
    map.fitBounds(DISPLAY_BOUNDS, { padding: [24, 24] });
  }
}

document.getElementById("map-selector").addEventListener("change", (event) => {
  loadMap(event.target.value).catch((error) => {
    document.getElementById("summary").textContent = error.message;
  });
});

loadMap(document.getElementById("map-selector").value).catch((error) => {
  document.getElementById("summary").textContent = error.message;
});
