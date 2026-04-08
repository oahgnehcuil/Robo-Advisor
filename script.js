let chartInstance = null;

async function loadData() {
  const company = document.getElementById("companySelect").value;

  try {
    const res = await fetch(`/api/mnav?period=7d&interval=1h`);
    const data = await res.json();

    console.log("API response:", data);

    if (data.error) {
      document.getElementById("latestMnav").textContent = "N/A";
      document.getElementById("latestStock").textContent = "N/A";
      document.getElementById("latestBtc").textContent = "N/A";
      document.getElementById("summary").textContent = "資料載入失敗：" + data.error;
      return;
    }

    const companyData = data.companies[company];

    if (!companyData || companyData.error) {
      document.getElementById("latestMnav").textContent = "N/A";
      document.getElementById("latestStock").textContent = "N/A";
      document.getElementById("latestBtc").textContent = "N/A";
      document.getElementById("summary").textContent =
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

    const first = mnavValues[0];
    const last = mnavValues[mnavValues.length - 1];

    let trendText = "";
    if (last > first) {
      trendText = `${companyData.company_name} 的 mNAV 在這段期間整體上升，代表市場給予其相對於所持數位資產價值的溢價提高。`;
    } else if (last < first) {
      trendText = `${companyData.company_name} 的 mNAV 在這段期間整體下降，代表市場溢價收斂。`;
    } else {
      trendText = `${companyData.company_name} 的 mNAV 在這段期間大致持平。`;
    }

    document.getElementById("summary").textContent =
      `${trendText} 最新股價為 ${latest.stock_close}，最新 mNAV 為 ${latest.mnav}。`;

  } catch (err) {
    document.getElementById("latestMnav").textContent = "N/A";
    document.getElementById("latestStock").textContent = "N/A";
    document.getElementById("latestBtc").textContent = "N/A";
    document.getElementById("summary").textContent = "載入失敗：" + err.message;
  }
}

async function askGemini() {
  const question = document.getElementById("questionInput").value.trim();
  const answerBox = document.getElementById("aiAnswer");

  if (!question) {
    answerBox.textContent = "請先輸入問題";
    return;
  }

  answerBox.textContent = "Thinking...";

  try {
    const res = await fetch("/api/ask", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        question: question,
        period: "7d",
        interval: "1h"
      })
    });

    const data = await res.json();

    if (data.error) {
      answerBox.textContent = "AI 回答失敗：" + data.error;
      return;
    }

    answerBox.textContent = data.answer || "No answer returned.";

  } catch (err) {
    answerBox.textContent = "AI 回答失敗：" + err.message;
  }
}

document.getElementById("askButton").addEventListener("click", askGemini);
document.getElementById("companySelect").addEventListener("change", loadData);

loadData();