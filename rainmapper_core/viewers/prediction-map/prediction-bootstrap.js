/* Optional adapter injected only into /protected/prediction-map/. The shared
 * viewer remains the owner of map, authentication, language and station popups. */
(() => {
  "use strict";
  const config = viewerConfig.predictionMap;
  if (!config) return;
  const assetBase = new URL(".", document.currentScript.src);
  const text = (key) => config.labels[key]?.[currentLanguage] || config.labels[key]?.en || key;
  let session = "";
  let button = null;
  let mode = null;
  let observations = null;
  let observationsRevision = 0;
  const mobileScreen = matchMedia('(max-width: 767px), (pointer: coarse) and (max-height: 600px)');
  let loading = false;
  let settings = null;
  let execution = "worker";
  let calendarTimezone = config.defaultCalendarTimezone || "Europe/Madrid";
  // Extend the existing save-on-panel-close payload only on the new route.
  const weatherDeviceSettings = currentDeviceSettings;
  currentDeviceSettings = function () {
    const values = weatherDeviceSettings();
    if (settings) {
      values.prediction_execution = execution;
      values.prediction_timezone = calendarTimezone;
    }
    return values;
  };
  const icon = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10" cy="14" r="8"/>' +
    '<circle cx="10" cy="14" r="4"/><path d="M10 14 21 3m-6 3 1 5 5 1M18 2l4 4"/></svg>';
  const bridge = {
    map, text, config, fetch: authFetch,
    language: () => currentLanguage,
    execution: () => execution,
    calendarTimezone: () => calendarTimezone,
    referenceDate: () => historicalMap?.date,
    historyBusy: () => historicalMap?.busy,
    isStation: (point) => map.getLayer(CIRCLE_LAYER_ID) &&
      map.queryRenderedFeatures(point, { layers: [CIRCLE_LAYER_ID] }).length > 0,
    wasLongPress: () => didTriggerLongPress,
    openPopup: (lngLat, element) => {
      closeHoverPopup();
      if (currentPopup) currentPopup.remove();
      const canvas = map.getCanvas();
      const heightLimit = () => canvas.clientWidth >= 900 ? canvas.clientHeight : 650;
      let point = map.project(lngLat);
      const width = Math.min(458, canvas.clientWidth - 32);
      let above = point.y - 16;
      let below = canvas.clientHeight - point.y - 16;
      let anchor;
      if (canvas.clientWidth - point.x >= width + 26) anchor = "left";
      else if (point.x >= width + 26) anchor = "right";
      else anchor = above >= below ? "bottom" : "top";
      // On narrow maps the fixed heading needs room for a useful scroll area.
      // Shift the map only when neither vertical side provides that space.
      if (anchor === "top" || anchor === "bottom") {
        const needed = Math.min(element.querySelector('.pm-weekly-chart:not([hidden])') ? 640 : 500, canvas.clientHeight - 32);
        const available = anchor === "bottom" ? above : below;
        if (available < needed) {
          const moveY = (needed - available) * (anchor === "bottom" ? 1 : -1);
          map.panBy([0, -moveY], { duration: 0 });
          point = map.project(lngLat);
          above = point.y - 16;
          below = canvas.clientHeight - point.y - 16;
        }
      }
      const verticalSpace = anchor === "left" || anchor === "right"
        ? canvas.clientHeight - 32 : Math.max(above, below);
      const centeredLeft = point.x - width / 2;
      const shiftX = anchor === "top" || anchor === "bottom"
        ? Math.max(16, Math.min(canvas.clientWidth - width - 16, centeredLeft)) - centeredLeft : 0;
      const offset = anchor === "left" ? [10, 0] : anchor === "right" ? [-10, 0]
        : [shiftX, anchor === "top" ? 10 : -10];
      element.style.width = `${width - 30}px`;
      element.style.maxHeight = `${Math.max(80, Math.min(heightLimit(), verticalSpace - 42))}px`;
      const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, focusAfterOpen: false,
        maxWidth: `${width}px`, offset, anchor,
        className: "pm-popup" }).setLngLat(lngLat).setDOMContent(element).addTo(map);
      // Keep the arrow on the coordinate when centering a wide mobile popup.
      popup.getElement().querySelector(".maplibregl-popup-tip").style.transform = `translateX(${-shiftX}px)`;
      // A lateral popup can use the full map height. Move its body inward near
      // an edge, and move the tip back so it still points at the coordinate.
      const fit = () => {
        const side = anchor === "left" || anchor === "right";
        if (!side) return;
        const projected = map.project(lngLat);
        element.style.maxHeight = `${Math.max(80, Math.min(heightLimit(), canvas.clientHeight - 74))}px`;
        const height = popup.getElement().offsetHeight;
        const centeredTop = projected.y - height / 2;
        const shiftY = Math.max(16, Math.min(canvas.clientHeight - height - 16, centeredTop)) - centeredTop;
        popup.setOffset([anchor === "left" ? 10 : -10, shiftY]);
        popup.getElement().querySelector(".maplibregl-popup-tip").style.transform = `translateY(${-shiftY}px)`;
      };
      const observer = new ResizeObserver(fit);
      observer.observe(element);
      map.on("move", fit);
      map.on("resize", fit);
      fit();
      element.querySelector(".pm-close")?.focus({ preventScroll: true });
      currentPopup = popup;
      activeStationPopupProperties = null;
      activeStationPopupId = null;
      popup.on("close", () => {
        observer.disconnect();
        map.off("move", fit);
        map.off("resize", fit);
        if (currentPopup === popup) currentPopup = null;
      });
      return popup;
    },
  };

  function reset() {
    observationsRevision++;
    observations?.destroy(); observations = null;
    historicalMap?.destroy(); historicalMap = null;
    mode?.setEnabled(false);
    button?.remove();
    button = null;
    settings?.remove();
    settings = null;
  }

  async function installObservations(next, allowed) {
    const own=++observationsRevision;
    if (!allowed || (mobileScreen.matches && config.observationsMobileEnabled !== true)) {
      observations?.destroy();observations=null;return;
    }
    if(observations)return;
    let style=document.getElementById('observations-mode-style');
    if(!style){style=document.createElement('link');style.id='observations-mode-style';style.rel='stylesheet';style.href=new URL('observations-mode.css',assetBase);document.head.append(style);}
    const module=await import(new URL('observations-mode.js',assetBase));
    if(session!==next || own!==observationsRevision)return;
    observations=module.createObservationsMode({...bridge,
      after:()=>document.getElementById('historical-mode-toggle') || button || document.getElementById('estimated-field-toggle'),
      closePopups:()=>{mode?.closePopup();closeHoverPopup();currentPopup?.remove();},
    });
  }

  function installSettings(capability, savedSettings) {
    const panel = document.getElementById("map-settings");
    const tabs = panel.querySelector(".map-settings-tabs");
    const tab = document.createElement("button");
    tab.id = "settings-tab-prediction";
    tab.className = "map-settings-tab";
    tab.type = "button";
    const section = document.createElement("section");
    section.className = "map-settings-section";
    section.dataset.settingsSection = "prediction";
    section.id = "prediction-settings";
    const row = document.createElement("label");
    row.className = "map-settings-row";
    const label = document.createElement("span");
    const select = document.createElement("select");
    select.id = "prediction-execution-selector";
    const options = ["worker", "local"].map(value => {
      const option = document.createElement("option"); option.value = value; select.append(option); return option;
    });
    const note = document.createElement("p");
    note.style.cssText = "font-size:13px;line-height:1.45;margin:12px 0 0";
    const key = `rainmapperPredictionExecution:${authState.username || "admin"}`;
    execution = savedSettings.prediction_execution;
    if (!["local", "worker"].includes(execution)) {
      // Read the old prototype preference once when the device has none yet.
      // New changes are saved by saveDeviceSettings(), never to localStorage.
      try { execution = localStorage.getItem(key) === "local" ? "local" : "worker"; } catch { execution = "worker"; }
    }
    select.value = execution;
    const calendarRow = document.createElement("label");
    calendarRow.className = "map-settings-row";
    const calendarLabel = document.createElement("span");
    const calendarSelect = document.createElement("select");
    calendarSelect.id = "prediction-timezone-selector";
    const zones = [...new Set(config.calendarTimezones || ["Europe/Madrid", "Atlantic/Canary", "UTC", ...Intl.supportedValuesOf("timeZone")])].sort();
    calendarTimezone = savedSettings.prediction_timezone || capability.calendar_timezone || config.defaultCalendarTimezone || "Europe/Madrid";
    if (!zones.includes(calendarTimezone)) calendarTimezone = "Europe/Madrid";
    zones.forEach(zone => { const option = document.createElement("option"); option.value = option.textContent = zone; calendarSelect.append(option); });
    calendarSelect.value = calendarTimezone;
    const calendarNote = document.createElement("p");
    calendarNote.style.cssText = note.style.cssText;
    const refreshText = () => {
      tab.textContent = text("settings"); label.textContent = select.ariaLabel = text("execution");
      options.forEach(option => { option.textContent = text(`execution_${option.value}`); });
      note.textContent = text("execution_help") + (execution === "local" && capability.executors?.local === false ? ` ${text("executor_unavailable")}` : "");
      calendarLabel.textContent = calendarSelect.ariaLabel = text("calendar_timezone");
      calendarNote.textContent = text("calendar_timezone_help");
    };
    select.addEventListener("change", () => {
      execution = select.value;
      markDeviceSettingsChanged();
      mode?.cancelQuery(); refreshText();
    });
    calendarSelect.addEventListener("change", () => {
      calendarTimezone = calendarSelect.value;
      markDeviceSettingsChanged();
      mode?.cancelQuery();
      historicalMap?.invalidate();
    });
    row.append(label, select); calendarRow.append(calendarLabel, calendarSelect);
    section.append(row, note, calendarRow, calendarNote); tabs.append(tab); panel.append(section);
    const click = event => {
      const target = event.target.closest("button");
      if (target === tab) {
        panel.querySelectorAll(".map-settings-tab").forEach(node => {
          node.classList.toggle("is-active", node === tab); node.setAttribute("aria-selected", String(node === tab));
        });
        panel.querySelectorAll("[data-settings-section]").forEach(node => node.classList.toggle("is-active", node === section));
      } else if (target?.hasAttribute("data-settings-tab")) {
        tab.classList.remove("is-active"); tab.setAttribute("aria-selected", "false"); section.classList.remove("is-active");
      }
    };
    tabs.addEventListener("click", click);
    refreshText();
    return { refreshText, remove() {
      if (tab.classList.contains("is-active")) document.getElementById("settings-tab-general").click();
      tabs.removeEventListener("click", click); tab.remove(); section.remove();
    } };
  }

  async function refresh() {
    const next = !document.body.classList.contains("auth-open") && authState?.sessionToken
      ? `${authState.sessionToken}:${authState.canUsePredictionMap === true}:${authState.canUseHistoricalMap === true}:${authState.canUseObservationsMap === true}` : "";
    if (next === session) {
      if (button) button.title = button.ariaLabel = text("mode");
      mode?.refreshLanguage();
      settings?.refreshText();
      historicalMap?.refreshLanguage();
      observations?.refreshLanguage();
      return;
    }
    session = next;
    reset();
    if (!next) return;
    try {
      const response = await authFetch(`${config.apiBase}/capabilities`, { cache: "no-store" });
      if (!response.ok || session !== next) return;
      const capability = await response.json();
      if (session !== next || (capability.can_use_prediction_map !== true && capability.can_use_historical_map !== true && capability.can_use_observations_map !== true)) return;
      const deviceResponse = await authFetch(`${AUTH_BASE}/device-settings`, { cache: "no-store" });
      if (!deviceResponse.ok || session !== next) return;
      const devicePayload = await deviceResponse.json();
      if (session !== next) return;
      if (capability.can_use_prediction_map === true || capability.can_use_historical_map === true) settings = installSettings(capability, devicePayload.settings || {});
      if (capability.can_use_prediction_map === true) {
      const control = document.createElement("button");
      control.type = "button";
      control.className = "map-control-button pm-mode-toggle";
      control.id = "prediction-mode-toggle";
      control.title = control.ariaLabel = text("mode");
      control.setAttribute("aria-pressed", "false");
      control.innerHTML = icon;
      // Button appearance is tiny; larger popup styles and code load on demand.
      control.querySelector("svg").setAttribute("style", "width:24px;height:24px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round");
      document.getElementById("estimated-field-toggle").after(control);
      button = control;
      control.addEventListener("click", async () => {
        if (loading || button !== control) return;
        loading = true;
        try {
          if (!mode) {
            const stylesheet = document.createElement("link");
            stylesheet.rel = "stylesheet";
            stylesheet.href = new URL("prediction-mode.css", assetBase);
            document.head.append(stylesheet);
            const module = await import(new URL("prediction-mode.js", assetBase));
            mode = module.createPredictionMode({...bridge, dataMode: capability.data_mode});
          }
          if (session !== next || button !== control) return;
          mode.setEnabled(!mode.enabled);
          control.setAttribute("aria-pressed", String(mode.enabled));
        } catch (_error) {
          control.title = control.ariaLabel = text("error");
        } finally {
          loading = false;
        }
      });
      }
      if (capability.can_use_historical_map === true) {
        let style = document.getElementById('historical-mode-style');
        if (!style) {
          style = document.createElement('link'); style.id='historical-mode-style';style.rel='stylesheet';
          style.href=new URL('historical-mode.css',assetBase);document.head.append(style);
        }
        const module = await import(new URL('historical-mode.js', assetBase));
        if (session !== next) return;
        historicalMap = module.createHistoricalMode({...bridge,
          after:()=>button || document.getElementById('estimated-field-toggle'),
          period:()=>currentPeriodFileName,
          apply:(period,data)=>loadMap(period,data), reload:()=>loadMap(currentPeriodFileName),
          cancelPrediction:()=>{mode?.cancelQuery();mode?.closePopup();closeHoverPopup();},
          bounds:(prefetch=false)=>{
            const canvas=map.getCanvas(), w=canvas.clientWidth, h=canvas.clientHeight;
            // Match the active interpolation support; pad pixels for heatmap edges.
            const pixels=heatmapEnabled ? 145*heatmapRadiusScale : 0;
            const padX=pixels+(prefetch?w*.2:0),padY=pixels+(prefetch?h*.2:0);
            const corners=[[-padX,-padY],[w+padX,-padY],[-padX,h+padY],[w+padX,h+padY]].map(p=>map.unproject(p));
            const radius=estimatedFieldEnabled ? Math.min(estimatedFieldRadiusKm(),estimatedFieldMaxRadiusKm()) : 0;
            const latMargin=radius/111.32;
            const extreme=Math.max(...corners.map(p=>Math.abs(p.lat)));
            const lonMargin=radius/Math.max(111.32*Math.cos(extreme*Math.PI/180),1);
            return [Math.max(-180,Math.min(...corners.map(p=>p.lng))-lonMargin),Math.max(-90,Math.min(...corners.map(p=>p.lat))-latMargin),
              Math.min(180,Math.max(...corners.map(p=>p.lng))+lonMargin),Math.min(90,Math.max(...corners.map(p=>p.lat))+latMargin)].map(v=>Math.round(v*1e6)/1e6);
          },
        });
      }
      await installObservations(next,capability.can_use_observations_map === true);
    } catch (_error) {
      // No authorization means no predictive controls; the weather UI owns login.
    }
  }

  const observer = new MutationObserver(refresh);
  observer.observe(document.getElementById("signed-in-user"), { attributes: true, childList: true, subtree: true });
  observer.observe(document.body, { attributes: true, attributeFilter: ["class"] });
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["lang"] });
  window.addEventListener("pagehide", () => { session = ""; reset(); });
  window.addEventListener("pageshow", refresh);
  mobileScreen.addEventListener('change',()=>{
    if(session)installObservations(session,authState.canUseObservationsMap === true).catch(()=>{});
  });
  refresh();
})();
