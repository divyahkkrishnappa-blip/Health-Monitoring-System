(() => {
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const api = async (url, options = {}) => {
    const response = await fetch(url, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || `Request failed (${response.status}).`);
    return payload;
  };
  const formatTime = (value) => {
    if (!value) return "—";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  };
  const metricNames = {
    heart_rate: "Heart rate",
    temperature: "Body temperature",
    systolic: "Systolic pressure",
    diastolic: "Diastolic pressure",
    oxygen: "Blood oxygen",
    sleep: "Sleep duration",
  };
  const setText = (selector, value) => {
    const element = $(selector);
    if (element) element.textContent = value == null ? "—" : value;
  };
  const showError = (element, message) => {
    if (!element) return;
    element.textContent = message;
    element.classList.add("error");
  };

  function startClock() {
    const clock = $("[data-clock]");
    if (!clock) return;
    const update = () => {
      clock.textContent = `${new Date().toISOString().slice(11, 19)} UTC`;
    };
    update();
    window.setInterval(update, 1000);
  }

  function setupNavigation() {
    const toggle = $("[data-menu-toggle]");
    const sidebar = $("#sidebar");
    if (toggle && sidebar) toggle.addEventListener("click", () => sidebar.classList.toggle("open"));
  }

  async function loadDashboard() {
    if (!$("#dashboard-chart")) return;
    try {
      const [data, history, alerts] = await Promise.all([
        api("/api/summary"),
        api("/api/measurements?metric=heart_rate&limit=16"),
        api("/api/alerts"),
      ]);
      const astronaut = data.astronaut || {};
      setText("[data-profile-first]", (astronaut.name || "Commander").split(" ").slice(-1)[0]);
      setText("[data-profile-name]", astronaut.name);
      setText("[data-profile-role]", astronaut.role);
      setText("[data-profile-callsign]", astronaut.call_sign);
      setText("[data-profile-mission]", astronaut.mission);
      setText("[data-profile-day]", astronaut.mission_day);
      const latest = data.measurements || {};
      ["heart_rate", "temperature", "oxygen", "sleep"].forEach((metric) => {
        const target = $(`[data-metric="${metric}"]`);
        if (target) target.textContent = latest[metric] ? latest[metric].value : "—";
        const status = $(`[data-metric-status="${metric}"]`);
        if (status && latest[metric]) status.textContent = latest[metric].source.toUpperCase();
      });
      setText("[data-pressure]", `${latest.systolic ? latest.systolic.value : "—"}/${latest.diastolic ? latest.diastolic.value : "—"}`);
      setText("[data-checkin-mood]", data.check_in ? data.check_in.mood : "—");
      setText("[data-checkin-stress]", data.check_in ? data.check_in.stress : "—");
      const latestTime = Object.values(latest).map((item) => item.recorded_at).sort().pop();
      setText("[data-last-updated]", latestTime ? formatTime(latestTime) : "No readings");
      if (window.AstroCharts) window.AstroCharts.dashboard(history.measurements);
      renderCompactAlerts(alerts.alerts.slice(0, 3));
    } catch (error) {
      const target = $("[data-recent-alerts]");
      if (target) showError(target, error.message);
    }
  }

  function renderCompactAlerts(alerts) {
    const target = $("[data-recent-alerts]");
    if (!target) return;
    target.replaceChildren();
    if (!alerts.length) {
      target.textContent = "No alerts recorded.";
      return;
    }
    alerts.forEach((alert) => {
      const item = document.createElement("article");
      item.className = "compact-alert";
      const icon = document.createElement("span");
      icon.className = "alert-symbol";
      const iconSvg = document.createElement("i");
      iconSvg.setAttribute("data-lucide", alert.severity === "Escalated" ? "triangle-alert" : "bell");
      icon.append(iconSvg);
      const body = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = alert.title;
      const message = document.createElement("p");
      message.textContent = alert.message;
      const time = document.createElement("time");
      time.textContent = formatTime(alert.created_at);
      body.append(title, message, time);
      item.append(icon, body);
      target.append(item);
    });
    if (window.lucide) window.lucide.createIcons();
  }

  async function loadMeasurements(metric) {
    const target = $("[data-measurement-rows]");
    try {
      const result = await api(`/api/measurements?metric=${encodeURIComponent(metric)}&limit=80`);
      if (window.AstroCharts) window.AstroCharts.monitoring(result.measurements, metric);
      if (!target) return;
      target.replaceChildren();
      if (!result.measurements.length) {
        const row = target.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 3;
        cell.textContent = "No readings recorded yet.";
      }
      result.measurements.slice().reverse().forEach((measurement) => {
        const row = target.insertRow();
        [formatTime(measurement.recorded_at), `${measurement.value} ${measurement.unit}`, measurement.source].forEach((text) => {
          const cell = row.insertCell();
          cell.textContent = text;
          if (text === measurement.source) cell.className = "source-label";
        });
      });
    } catch (error) {
      if (target) showError(target, error.message);
    }
  }

  function setupMonitoring() {
    const select = $("#metric-select");
    if (select) {
      loadMeasurements(select.value);
      select.addEventListener("change", () => loadMeasurements(select.value));
    }
    const measurementForm = $("[data-measurement-form]");
    if (measurementForm) measurementForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const message = $(".form-message", measurementForm);
      message.classList.remove("error");
      message.textContent = "Saving…";
      const form = new FormData(measurementForm);
      try {
        const result = await api("/api/measurements", {
          method: "POST",
          body: JSON.stringify({ metric: form.get("metric"), value: form.get("value"), notes: form.get("notes"), source: "User entered" }),
        });
        message.textContent = result.message;
        measurementForm.reset();
        loadMeasurements($("#metric-select").value);
      } catch (error) {
        showError(message, error.message);
      }
    });
    const checkinForm = $("[data-checkin-form]");
    if (checkinForm) checkinForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const message = $(".form-message", checkinForm);
      message.classList.remove("error");
      message.textContent = "Saving…";
      const form = new FormData(checkinForm);
      try {
        const result = await api("/api/check-ins", {
          method: "POST",
          body: JSON.stringify({
            mood: form.get("mood"),
            stress: form.get("stress"),
            sleep_hours: form.get("sleep_hours"),
          }),
        });
        message.textContent = result.message;
      } catch (error) {
        showError(message, error.message);
      }
    });
  }

  function setupSimulation() {
    const button = $("[data-simulate]");
    if (!button) return;
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        await api("/api/simulate", { method: "POST", body: "{}" });
        await loadDashboard();
      } catch (error) {
        window.alert(error.message);
      } finally {
        button.disabled = false;
      }
    });
  }

  function renderAlerts(alerts) {
    const target = $("[data-alert-list]");
    if (!target) return;
    target.replaceChildren();
    const open = alerts.filter((alert) => alert.status === "Open");
    setText("[data-open-alert-count]", `${open.length} OPEN`);
    if (!alerts.length) {
      target.textContent = "No alerts recorded.";
      return;
    }
    alerts.forEach((alert) => {
      const row = document.createElement("article");
      row.className = "alert-row";
      const head = document.createElement("div");
      head.className = "alert-row-head";
      const title = document.createElement("h3");
      title.textContent = alert.title;
      const severity = document.createElement("span");
      severity.className = `severity-tag${alert.severity === "Escalated" ? " escalated" : ""}`;
      severity.textContent = alert.severity.toUpperCase();
      head.append(title, severity);
      const message = document.createElement("p");
      message.textContent = alert.message;
      const foot = document.createElement("div");
      foot.className = "alert-row-foot";
      const time = document.createElement("time");
      time.textContent = `${formatTime(alert.created_at)} · ${alert.status}`;
      foot.append(time);
      if (alert.status === "Open") {
        const actions = document.createElement("span");
        const ack = document.createElement("button");
        ack.type = "button";
        ack.className = "alert-action";
        ack.textContent = "Acknowledge";
        ack.addEventListener("click", () => updateAlert(alert.id, "acknowledge"));
        actions.append(ack);
        if (alert.severity !== "Escalated") {
          const escalate = document.createElement("button");
          escalate.type = "button";
          escalate.className = "alert-action";
          escalate.textContent = "Simulate escalation";
          escalate.addEventListener("click", () => updateAlert(alert.id, "escalate"));
          actions.append(escalate);
        }
        foot.append(actions);
      }
      row.append(head, message, foot);
      target.append(row);
    });
  }

  async function updateAlert(id, action) {
    try {
      await api(`/api/alerts/${id}/${action}`, { method: "POST", body: "{}" });
      await loadAlerts();
    } catch (error) {
      window.alert(error.message);
    }
  }

  async function loadAlerts() {
    try {
      const result = await api("/api/alerts");
      renderAlerts(result.alerts);
    } catch (error) {
      const target = $("[data-alert-list]");
      if (target) showError(target, error.message);
    }
  }

  async function loadInsights() {
    const target = $("[data-insights]");
    if (!target) return;
    try {
      const result = await api("/api/insights");
      target.replaceChildren();
      result.insights.forEach((insight) => {
        const card = document.createElement("article");
        card.className = "glass-card insight-item";
        const icon = document.createElement("i");
        icon.setAttribute("data-lucide", insight.kind === "trend" ? "trending-up" : "circle-check");
        const body = document.createElement("div");
        const title = document.createElement("h3");
        title.textContent = insight.title;
        const detail = document.createElement("p");
        detail.textContent = insight.detail;
        body.append(title, detail);
        card.append(icon, body);
        target.append(card);
      });
      const notice = document.createElement("p");
      notice.className = "fine-print";
      notice.textContent = `${result.method} ${result.uncertainty}`;
      target.append(notice);
      if (window.lucide) window.lucide.createIcons();
    } catch (error) {
      showError(target, error.message);
    }
  }

  function setupInsights() {
    const button = $("[data-refresh-insights]");
    if (button) button.addEventListener("click", loadInsights);
    loadInsights();
  }

  const regionContent = {
    brain: ["Brain & balance", "Coordinates cognition, sensory processing, and balance.", "Spaceflight transitions and isolation can affect sleep, mood, and sensorimotor adaptation; effects vary.", "Self-reported sleep, mood, and stress check-ins can support personal reflection.", "Use mission-provided behavioral health and sleep resources; discuss concerns with the crew medical officer."],
    heart: ["Cardiovascular system", "Moves blood through the body to support tissues and organs.", "Fluid shifts and adaptation to altered gravity are among the areas studied in human spaceflight.", "Heart rate and appropriately measured blood pressure; these demo records do not assess cardiovascular health.", "Record readings using mission-approved equipment and follow the prescribed monitoring plan."],
    lungs: ["Lungs & respiration", "Exchange oxygen and carbon dioxide between air and blood.", "A closed habitat makes environmental control and air-quality monitoring important; this app has no habitat sensors.", "Only blood oxygen values from suitable validated equipment; webcam preview does not measure oxygen saturation.", "Follow mission environmental procedures and equipment guidance."],
    bones: ["Bones & skeleton", "Provide structure, protect organs, and support movement.", "Reduced mechanical loading in microgravity can affect bone adaptation; NASA researches countermeasures.", "No bone density measurement is collected by this prototype.", "Follow mission-planned exercise and clinical assessment schedules."],
    muscles: ["Muscles & movement", "Enable posture, movement, and force production.", "Altered gravity changes loading and can affect muscle conditioning during spaceflight.", "No muscle strength or composition sensor is connected in this demo.", "Follow mission exercise plans and report concerns through approved channels."],
  };

  function setupBodyExplorer() {
    const detail = $("[data-region-detail]");
    if (!detail) return;
    $$(".body-hotspot").forEach((button) => button.addEventListener("click", () => {
      const values = regionContent[button.dataset.region];
      if (!values) return;
      $$(".body-hotspot").forEach((item) => item.classList.toggle("selected", item === button));
      detail.replaceChildren();
      const label = document.createElement("div");
      label.className = "eyebrow";
      label.textContent = "SELECTED SYSTEM";
      const iconWrap = document.createElement("span");
      iconWrap.className = "region-icon";
      const icon = document.createElement("i");
      icon.setAttribute("data-lucide", button.dataset.region === "heart" ? "heart" : button.dataset.region === "brain" ? "brain" : button.dataset.region === "lungs" ? "wind" : button.dataset.region === "bones" ? "bone" : "dumbbell");
      iconWrap.append(icon);
      const heading = document.createElement("h2");
      heading.textContent = values[0];
      const intro = document.createElement("p");
      intro.textContent = values[1];
      const list = document.createElement("div");
      list.className = "detail-list";
      ["SPACEFLIGHT CONTEXT", "RELEVANT MEASUREMENTS", "MONITORING ACTIVITY"].forEach((title, index) => {
        const item = document.createElement("div");
        item.className = "detail-item";
        const strong = document.createElement("strong");
        strong.textContent = title;
        const text = document.createElement("p");
        text.textContent = values[index + 2];
        item.append(strong, text);
        list.append(item);
      });
      detail.append(label, iconWrap, heading, intro, list);
      if (window.lucide) window.lucide.createIcons();
    }));
  }

  function renderPeriodSummary(target, summary) {
    if (!target) return;
    target.replaceChildren();
    const metrics = Object.entries(summary.metrics || {});
    if (!metrics.length) {
      target.textContent = "No measurements in this period.";
      return;
    }
    metrics.forEach(([metric, stats]) => {
      const item = document.createElement("div");
      item.className = "period-metric";
      const label = document.createElement("strong");
      label.textContent = metricNames[metric] || metric;
      const value = document.createElement("span");
      value.textContent = `Avg ${stats.average} ${stats.unit} · min ${stats.minimum} · max ${stats.maximum} · n=${stats.count}`;
      item.append(label, value);
      target.append(item);
    });
  }

  async function loadReportChart(metric) {
    try {
      const result = await api(`/api/measurements?metric=${encodeURIComponent(metric)}&limit=500`);
      if (window.AstroCharts) window.AstroCharts.report(result.measurements, metric);
    } catch (error) {
      const canvas = $("#report-chart");
      if (canvas) showError(canvas.parentElement, error.message);
    }
  }

  async function loadReport() {
    const rows = $("[data-report-rows]");
    if (!rows) return;
    try {
      const [measurements, report] = await Promise.all([api("/api/measurements?limit=500"), api("/api/reports")]);
      setText("[data-report-daily-count]", report.summaries.daily.measurement_count);
      setText("[data-report-weekly-count]", report.summaries.weekly.measurement_count);
      setText("[data-report-alert-count]", report.alerts.length);
      renderPeriodSummary($("[data-daily-summary]"), report.summaries.daily);
      renderPeriodSummary($("[data-weekly-summary]"), report.summaries.weekly);
      rows.replaceChildren();
      measurements.measurements.slice().reverse().forEach((record) => {
        const row = rows.insertRow();
        [formatTime(record.recorded_at), metricNames[record.metric] || record.metric, `${record.value} ${record.unit}`, record.source].forEach((value) => {
          const cell = row.insertCell();
          cell.textContent = value;
        });
      });
      if (!measurements.measurements.length) {
        const row = rows.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 4;
        cell.textContent = "No measurements recorded.";
      }
      const alertRows = $("[data-report-alert-rows]");
      if (alertRows) {
        alertRows.replaceChildren();
        report.alerts.forEach((alert) => {
          const row = alertRows.insertRow();
          [formatTime(alert.created_at), alert.severity, alert.title, alert.status].forEach((value) => {
            const cell = row.insertCell();
            cell.textContent = value;
          });
        });
        if (!report.alerts.length) {
          const row = alertRows.insertRow();
          const cell = row.insertCell();
          cell.colSpan = 4;
          cell.textContent = "No alerts recorded.";
        }
      }
      loadReportChart($("#report-metric-select").value);
    } catch (error) {
      showError(rows, error.message);
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    startClock();
    setupNavigation();
    setupSimulation();
    setupMonitoring();
    setupInsights();
    setupBodyExplorer();
    const reportMetric = $("#report-metric-select");
    if (reportMetric) reportMetric.addEventListener("change", () => loadReportChart(reportMetric.value));
    loadDashboard();
    loadAlerts();
    loadReport();
    if (window.lucide) window.lucide.createIcons();
  });
})();
