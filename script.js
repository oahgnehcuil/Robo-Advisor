fetch("./data.json")
  .then(response => response.json())
  .then(data => {
    const labels = data.map(item => item.date);
    const mnavValues = data.map(item => item.mnav);

    new Chart(document.getElementById("mnavChart"), {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: "mNAV",
            data: mnavValues,
            borderWidth: 2,
            fill: false,
            tension: 0.2
          }
        ]
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            display: true
          }
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
  })
  .catch(error => {
    console.error("Error loading data:", error);
  });