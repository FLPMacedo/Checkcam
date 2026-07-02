// Trend histórico do drill-down: busca /api/historico/<id> e desenha um
// line chart da evolução das câmeras (OK, alerta, sem conexão) ao longo do tempo.
(function () {
  "use strict";

  const canvas = document.getElementById("trend-chart");
  if (!canvas || typeof Chart === "undefined") return;

  const id = canvas.dataset.instalacao;
  if (!id) return;

  const CORES = {
    ok: "#2ecc71",
    alerta: "#f39c12",
    sem_conexao: "#e74c3c",
  };

  fetch(`/api/historico/${id}`)
    .then((r) => r.json())
    .then((dados) => {
      if (!Array.isArray(dados) || dados.length === 0) return;

      const rotulos = dados.map((d) => formatarData(d.executado_em));

      new Chart(canvas, {
        type: "line",
        data: {
          labels: rotulos,
          datasets: [
            serie("Câmeras OK", dados.map((d) => d.cameras_ok), CORES.ok),
            serie("Alerta", dados.map((d) => d.cameras_alerta), CORES.alerta),
            serie("Sem conexão", dados.map((d) => d.cameras_sem_conexao), CORES.sem_conexao),
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: "index", intersect: false },
          scales: {
            x: { ticks: { color: "#9aa4b2" }, grid: { color: "#2a2f3a" } },
            y: {
              beginAtZero: true,
              ticks: { color: "#9aa4b2", precision: 0 },
              grid: { color: "#2a2f3a" },
            },
          },
          plugins: {
            legend: { labels: { color: "#d7dbe0" } },
          },
        },
      });
    })
    .catch(() => {
      /* silencioso: se o histórico falhar, a página segue sem o gráfico */
    });

  function serie(label, valores, cor) {
    return {
      label: label,
      data: valores,
      borderColor: cor,
      backgroundColor: cor + "33",
      tension: 0.25,
      fill: false,
      pointRadius: 3,
    };
  }

  // "2026-07-02T14:30:00" → "02/07 14:30"
  function formatarData(iso) {
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    const p = (n) => String(n).padStart(2, "0");
    return `${p(d.getDate())}/${p(d.getMonth() + 1)} ${p(d.getHours())}:${p(d.getMinutes())}`;
  }
})();
