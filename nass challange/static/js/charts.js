(() => {
  const chartInstances = new WeakMap();
  const palette = { cyan: "#69e0e9", blue: "#6c8cff", grid: "rgba(155,183,232,.10)", text: "#91a0ba" };
  const labels = (rows) => rows.map((row) => {
    const date = new Date(row.recorded_at);
    return Number.isNaN(date.getTime()) ? row.recorded_at : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  });
  const values = (rows) => rows.map((row) => Number(row.value));
  function createChart(canvas, rows, label, compact = false) {
    if (!canvas || !window.Chart) return;
    const existing = chartInstances.get(canvas);
    if (existing) existing.destroy();
    const chart = new Chart(canvas, {
      type: "line",
      data: {
        labels: labels(rows),
        datasets: [{
          label,
          data: values(rows),
          borderColor: compact ? palette.blue : palette.cyan,
          backgroundColor: compact ? "rgba(108,140,255,.12)" : "rgba(105,224,233,.10)",
          borderWidth: compact ? 1.7 : 2,
          pointRadius: compact ? 0 : 3,
          pointHoverRadius: 5,
          pointBackgroundColor: palette.cyan,
          fill: true,
          tension: .38,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 350 },
        plugins: {
          legend: { display: false },
          tooltip: { backgroundColor: "#111b31", borderColor: "rgba(155,183,232,.2)", borderWidth: 1, titleColor: "#dce7f8", bodyColor: "#c5d2e6" },
        },
        scales: {
          x: { display: !compact, grid: { display: false }, ticks: { color: palette.text, maxTicksLimit: 7, font: { size: 9 } } },
          y: { display: !compact, grid: { color: palette.grid }, ticks: { color: palette.text, maxTicksLimit: 5, font: { size: 9 } } },
        },
      },
    });
    chartInstances.set(canvas, chart);
  }
  window.AstroCharts = {
    dashboard(rows) {
      createChart(document.getElementById("dashboard-chart"), rows, "Heart rate");
      document.querySelectorAll("[data-mini-chart]").forEach((canvas) => {
        const metric = canvas.dataset.miniChart;
        if (metric === "heart_rate") createChart(canvas, rows.slice(-8), "Heart rate", true);
      });
    },
    monitoring(rows, metric) {
      const names = { heart_rate: "Heart rate (bpm)", temperature: "Temperature (°C)", systolic: "Systolic pressure (mmHg)", diastolic: "Diastolic pressure (mmHg)", sleep: "Sleep duration (h)", oxygen: "Blood oxygen (%)" };
      createChart(document.getElementById("monitoring-chart"), rows, names[metric] || metric);
    },
    report(rows, metric) {
      const names = { heart_rate: "Heart rate (bpm)", temperature: "Temperature (°C)", systolic: "Systolic pressure (mmHg)", diastolic: "Diastolic pressure (mmHg)", sleep: "Sleep duration (h)", oxygen: "Blood oxygen (%)" };
      createChart(document.getElementById("report-chart"), rows, names[metric] || metric);
    },
  };
})();
