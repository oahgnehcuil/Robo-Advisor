let chartInstance = null;
const summaryCache = {};

async function loadSummary(companyData) {
  const summaryBox = document.getElementById("aiSummary");
  const cacheKey = `${companyData.company}-${companyData.latest.date}`;

  if (summaryCache[cacheKey]) {
    summaryBox.textContent = summaryCache[cacheKey];
    return;
  }

  summaryBox.textContent = "Generating AI summary...";

  try {
    const res = await fetch("/api/summary", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        company_name: companyData.company_name,
        ticker: companyData.ticker,
        latest: companyData.latest,
        series: companyData.series
      })
    });

    const data = await res.json();

    if (data.error) {
      summaryBox.textContent = "AI 摘要暫時無法取得：" + data.error;
      return;
    }

    const summary = data.summary || "No summary returned.";
    summaryCache[cacheKey] = summary;
    summaryBox.textContent = summary;
  } catch (err) {
    summaryBox.textContent = "AI 摘要暫時無法取得：" + err.message;
  }
}

async function loadData() {
  const company = document.getElementById("companySelect").value;

  try {
    const res = await fetch(`/api/mnav?period=1mo&interval=1d`);
    const data = await res.json();

    console.log("API response:", data);

    if (data.error) {
      document.getElementById("latestMnav").textContent = "N/A";
      document.getElementById("latestStock").textContent = "N/A";
      document.getElementById("latestBtc").textContent = "N/A";
      document.getElementById("aiSummary").textContent = "資料載入失敗：" + data.error;
      return;
    }

    const companyData = data.companies[company];

    if (!companyData || companyData.error) {
      document.getElementById("latestMnav").textContent = "N/A";
      document.getElementById("latestStock").textContent = "N/A";
      document.getElementById("latestBtc").textContent = "N/A";
      document.getElementById("aiSummary").textContent =
        "公司資料載入失敗：" + (companyData ? companyData.error : "No company data");
      return;
    }

    const latest = companyData.latest;
    const series = companyData.series;

    document.getElementById("latestMnav").textContent = latest.mnav;
    document.getElementById("latestStock").textContent = "$" + latest.stock_close.toLocaleString();
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
        plugins: {
          legend: {
            display: true
          }
        },
        scales: {
          x: {
            title: {
              display: true,
              text: "Time"
            }
          },
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

    loadSummary(companyData);
  } catch (err) {
    document.getElementById("latestMnav").textContent = "N/A";
    document.getElementById("latestStock").textContent = "N/A";
    document.getElementById("latestBtc").textContent = "N/A";
    document.getElementById("aiSummary").textContent = "載入失敗：" + err.message;
  }
}

document.getElementById("companySelect").addEventListener("change", loadData);

loadData();