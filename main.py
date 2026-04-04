from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import yfinance as yf

app = FastAPI()

# ---------------- MARKET API ----------------
@app.get("/market")
def market():
    ticker = yf.Ticker("HG=F")
    data = ticker.history(period="5d")

    prices = data["Close"].tolist()

    if len(prices) < 3:
        return {"error": "Not enough data"}

    current = round(prices[-1], 3)
    forecast = [round(p * 1.01, 4) for p in prices[-3:]]
    trend = round((prices[-1] - prices[0]) / prices[0], 3)

    return {
        "current": current,
        "forecast": forecast,
        "trend": trend
    }

# ---------------- DASHBOARD ----------------
@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!DOCTYPE html>
<html>

<head>
    <title>ScrapRadar Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />

    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>

<body style="font-family: Arial; padding: 20px; background:#111; color:#0f0;">

<h1>ScrapRadar Dashboard</h1>

<button onclick="loadData()" style="padding:10px; font-size:16px;">
    Load Market Data
</button>

<div style="margin-top:20px;">
    <input id="lbs" placeholder="Enter pounds"
        style="padding:8px; font-size:16px;" />

    <button onclick="calcValue()" style="padding:10px;">
        Calculate Value
    </button>

    <div id="value" style="margin-top:10px;"></div>
</div>

<pre <div id="stats" style="margin-top:20px; font-size:18px;"></div>
</pre>

<canvas id="chart" style="margin-top:20px; max-width:100%; background:#111;"></canvas>

<script>
let chart;

async function loadData() {
    try {
        const res = await fetch('/market?nocache=' + Date.now());
        const data = await res.json();

        // Show JSON document.getElementById('stats').innerHTML = `
    <div>📊 Current Price: <b>$${data.current}</b></div>
    <div>📈 Trend: <b>${(data.trend * 100).toFixed(2)}%</b></div>
    <div>🔮 Forecast: ${data.forecast.join(', ')}</div>
`;
        

        // Draw chart
        const ctx = document.getElementById('chart').getContext('2d');

        if (chart) {
            chart.destroy();
        }

        chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Now', 'Forecast 1', 'Forecast 2', 'Forecast 3'],
                datasets: [{
                    label: 'Copper Price Trend',
                    data: [data.current, ...data.forecast],
                    borderWidth: 2,
                    tension: 0.25
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        labels: {
                            color: '#0f0'
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: { color: '#0f0' },
                        grid: { color: '#333' }
                    },
                    y: {
                        ticks: { color: '#0f0' },
                        grid: { color: '#333' }
                    }
                }
            }
        });

    } catch (err) {
        document.getElementById('output').innerText = "Error loading data";
    }
}

function calcValue() {
    const lbs = parseFloat(document.getElementById('lbs').value);
    const output = document.getElementById('value');

    if (!lbs || lbs <= 0) {
        output.innerText = "Enter valid weight";
        return;
    }

    const current = chart.data.datasets[0].data[0];
    const total = (lbs * current).toFixed(2);

    output.innerText = `💰 Estimated Value: $${total}`;
} 

</script>

</body>
</html>
"""
