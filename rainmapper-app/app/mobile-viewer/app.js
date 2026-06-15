const defaultDataBase = window.location.pathname.includes("/mobile-viewer/")
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

L.control.layers(
  {
    "Topographic": topographicLayer,
    "Hybrid": hybridLayer,
  },
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
  const legend = L.control({ position: "bottomright" });
  legend.onAdd = () => {
    const container = L.DomUtil.create("div", "rain-legend");
    L.DomEvent.disableClickPropagation(container);
    container.innerHTML = `
      <div class="rain-legend-title">Rain (mm)</div>
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
  const summary = document.getElementById("summary");
  summary.textContent = `${periods[fileName]} · ${count} station${count === 1 ? "" : "s"}`;
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
        maxWidth: 320,
        minWidth: 250,
        autoPanPadding: [18, 92],
      });
    },
  }).addTo(map);

  const count = visibleFeatures.length;
  updateSummary(fileName, count);

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
