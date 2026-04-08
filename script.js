async function loadData() {
  const company = document.getElementById("companySelect").value;
  const companyData = data.companies[company];

  if (!companyData || companyData.error) {
    document.getElementById("summary").textContent =
      "資料載入失敗：" + (companyData ? companyData.error : "No company data");
    return;
  }

  const latest = companyData.latest;
  const series = companyData.series;

  try {
    const res = await fetch(`/api/mnav?period=7d&interval=1h`);
    const data = await res.json();

    console.log("API response:", data);

    if (data.error) {
      document.getElementById("latestMnav").textContent = "N/A";
      document.getElementById("latestMstr").textContent = "N/A";
      document.getElementById("latestBtc").textContent = "N/A";
      document.getElementById("summary").textContent = "資料載入失敗：" + data.error;
      return;
    }

    const companyData = data.companies[company];

    if (!companyData || companyData.error) {
      document.getElementById("latestMnav").textContent = "N/A";
      document.getElementById("latestMstr").textContent = "N/A";
      document.getElementById("latestBtc").textContent = "N/A";
      document.getElementById("summary").textContent =
        "公司資料載入失敗：" + (companyData ? companyData.error : "No company data");
      return;
    }

    const latest = companyData.latest;
    const series = companyData.series;

    document.getElementById("latestMnav").textContent = latest.mnav;
    document.getElementById("latestMstr").textContent = "$" + latest.stock_close.toLocaleString();
    document.getElementById("latestBtc").textContent = "$" + latest.btc_close.toLocaleString();

    const labels = series.map(x => x.date);
    const mnavValues = series.map(x => x.mnav);
    const stockValues = series.map(x => x.stock_close);

    if (chartInstance) {
      chartInstance.destroy();
    }

    chartInstance = new Chart(document.getElementById("mnavChart"), {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: `${companyData.company} mNAV`,
            data: mnavValues,
            yAxisID: "y1",
            borderWidth: 2,
            tension: 0.2,
            fill: false
          },
          {
            label: `${companyData.company} Stock Price`,
            data: stockValues,
            yAxisID: "y2",
            borderWidth: 2,
            tension: 0.2,
            fill: false
          }
        ]
      },
      options: {
        responsive: true,
        interaction: {
          mode: "index",
          intersect: false
        },
        scales: {
          y1: {
            type: "linear",
            position: "left",
            title: {
              display: true,
              text: "mNAV"
            }
          },
          y2: {
            type: "linear",
            position: "right",
            title: {
              display: true,
              text: "Stock Price"
            },
            grid: {
              drawOnChartArea: false
            }
          }
        }
      }
    });

    document.getElementById("summary").textContent =
      `${companyData.company_name} 最新股價為 ${latest.stock_close}，最新 mNAV 為 ${latest.mnav}。`;

  } catch (err) {
    document.getElementById("latestMnav").textContent = "N/A";
    document.getElementById("latestMstr").textContent = "N/A";
    document.getElementById("latestBtc").textContent = "N/A";
    document.getElementById("summary").textContent = "載入失敗：" + err.message;
  }
}

loadData();