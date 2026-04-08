async function loadData() {
  try {
    const res = await fetch("/api/mnav");
    const data = await res.json();

    if (data.error) {
      document.getElementById("summary").textContent = "資料載入失敗：" + data.error;
      return;
    }

    const latest = data.latest;
    const series = data.series;

    document.getElementById("latestMnav").textContent = latest.mnav;
    document.getElementById("latestMstr").textContent = "$" + latest.mstr_close;
    document.getElementById("latestBtc").textContent = "$" + latest.btc_close.toLocaleString();

    const labels = series.map(x => x.date);
    const mnavValues = series.map(x => x.mnav);

    new Chart(document.getElementById("mnavChart"), {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: "MSTR mNAV",
            data: mnavValues,
            borderWidth: 2,
            tension: 0.2,
            fill: false
          }
        ]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: true }
        },
        scales: {
          x: {
            title: {
              display: true,
              text: "Date"
            }
          },
          y: {
            title: {
              display: true,
              text: "mNAV"
            }
          }
        }
      }
    });

    let trendText = "";
    const first = mnavValues[0];
    const last = mnavValues[mnavValues.length - 1];

    if (last > first) {
      trendText = "近六個月 mNAV 整體上升，代表市場給 MSTR 的估值溢價相對變高。";
    } else if (last < first) {
      trendText = "近六個月 mNAV 整體下降，代表市場給 MSTR 的估值溢價相對收斂。";
    } else {
      trendText = "近六個月 mNAV 變化不大，代表市場對 MSTR 相對 BTC 資產價值的估值大致穩定。";
    }

    document.getElementById("summary").textContent =
      `${trendText} 最新 mNAV 為 ${latest.mnav}，這裡的 BTC holdings 採用固定假設值 ${data.btc_holdings_assumption} BTC。`;
  } catch (err) {
    document.getElementById("summary").textContent = "載入失敗：" + err.message;
  }
}

loadData();