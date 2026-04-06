from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import sqlite3
import yfinance as yf

app = FastAPI()

DB_NAME = "scrapradar_history.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metal TEXT,
            pounds REAL,
            price_per_lb REAL,
            total REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


init_db()


@app.get("/save-history")
def save_history(metal: str, pounds: float, price: float, total: float):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO history (metal, pounds, price_per_lb, total)
        VALUES (?, ?, ?, ?)
    """, (metal, pounds, price, total))
    conn.commit()
    conn.close()
    return {
    "history": [dict(row) for row in rows],
    "best_price": best_price,
    "best_total": best_total
}


@app.get("/history")
def get_history():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

rows = cur.execute("""
    SELECT id, metal, pounds, price_per_lb, total, created_at
    FROM history
    ORDER BY id DESC
    LIMIT 20
""").fetchall()
    SELECT id, metal, pounds, price_per_lb, total, created_at
    FROM history
    ORDER BY id DESC
    LIMIT 20
""").fetchall()

best_price = cur.execute("""
    SELECT MAX(price_per_lb) FROM history
""").fetchone()[0]

best_total = cur.execute("""
    SELECT MAX(total) FROM history
""").fetchone()[0]
     conn.close()
     return [dict(row) for row in rows]


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


@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>ScrapRadar Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body style="font-family: Arial; padding: 20px; background: #111; color: #0f0;">

    <h1>ScrapRadar Dashboard</h1>

    <button onclick="loadData()" style="padding:10px; font-size:16px; border-radius:20px;">
        Load Market Data
    </button>

    <div style="margin-top:20px; display:flex; flex-wrap:wrap; gap:8px;">
        <input id="lbs" placeholder="Enter pounds"
            style="padding:8px; font-size:16px; border-radius:10px;" />

        <select id="metalType"
            style="padding:8px; font-size:16px; border-radius:20px;">
            <option value="copper" selected>Copper</option>
            <option value="brass">Brass</option>
            <option value="aluminum">Aluminum</option>
        </select>

        <input id="customPrice" placeholder="Override price"
            style="padding:8px; font-size:16px; border-radius:10px;" />

        <input id="cost" placeholder="Your cost/lb"
            style="padding:8px; font-size:16px; border-radius:10px;" />

        <button onclick="calcValue()"
            style="padding:10px; border-radius:20px;">
            Calculate Value
        </button>
    </div>

    <div id="value" style="margin-top:16px; font-size:18px; line-height:1.6;"></div>

    <div id="stats" style="margin-top:20px; font-size:18px;"></div>

    <div style="margin-top:20px;">
        <button onclick="saveCalc()" style="padding:10px; border-radius:20px;">
            Save To History
        </button>

        <button onclick="loadHistory()" style="padding:10px; margin-left:8px; border-radius:20px;">
            Load History
        </button>
    </div>

    <div id="historyBox" style="
        margin-top:20px;
        background:#000;
        padding:10px;
        color:#0f0;
    ">History will show here...</div>

    <canvas id="chart" style="margin-top:20px; max-width:100%; background:#111;"></canvas>

    <script>
        let chart;

        async function loadData() {
            try {
                const res = await fetch('/market?nocache=' + Date.now());
                const data = await res.json();

                if (data.error) {
                    document.getElementById('stats').innerText = data.error;
                    return;
                }

                document.getElementById('stats').innerHTML = `
                    <div>📊 Current Price: <b>$${data.current}</b></div>
                    <div>📈 Trend: <b>${(data.trend * 100).toFixed(2)}%</b></div>
                    <div>🔮 Forecast: ${data.forecast.join(', ')}</div>
                `;

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
                document.getElementById('stats').innerText = "Error loading data";
            }
        }

        async function calcValue() {
            const lbs = parseFloat(document.getElementById('lbs').value);
            const metal = document.getElementById('metalType').value;
            const output = document.getElementById('value');

            if (!output) return;

            if (!lbs || lbs <= 0) {
                output.innerText = "Enter valid weight";
                return;
            }

            if (!chart) {
                output.innerText = "Load market data first";
                return;
            }

            let current = chart.data.datasets[0].data[0];
            const custom = parseFloat(document.getElementById('customPrice').value);

            if (custom && custom > 0) {
                current = custom;
            } else if (metal === 'brass') {
                current = current * 0.72;
            } else if (metal === 'aluminum') {
                current = current * 0.18;
            }

            const total = (lbs * current).toFixed(2);
            const cost = parseFloat(document.getElementById('cost')?.value);

            let profitText = "";

            if (cost && cost > 0) {
                const rawProfit = (current - cost) * lbs;
                const profit = rawProfit.toFixed(2);
                const percent = Number((((current - cost) / cost) * 100).toFixed(2));

                const color = rawProfit >= 0 ? "#0f0" : "#f00";

                let strength =
                    rawProfit < 0 ? "❌ Loss" :
                    percent > 10 ? "🔥 Strong" :
                    percent > 3 ? "👍 Solid" :
                    percent > 0 ? "⚠️ Thin" :
                    "➖ Flat";

                let percentColor =
                    rawProfit < 0 ? "#f00" :
                    percent > 5 ? "#0ff" :
                    percent > 2 ? "#0f0" :
                    percent > 0 ? "#ff0" :
                    "#f00";

                let recommendation = "";

                if (rawProfit < 0) {
                    recommendation = `<br>🚫 Recommendation: <span style="color:#f00; font-weight:bold;">PASS</span>`;
                } else if (percent >= 10) {
                    recommendation = `<br>✅ Recommendation: <span style="color:#0ff; font-weight:bold;">SELL NOW</span>`;
                } else if (percent >= 3) {
                    recommendation = `<br>👍 Recommendation: <span style="color:#0f0; font-weight:bold;">GOOD DEAL</span>`;
                } else if (percent > 0) {
                    recommendation = `<br>⏳ Recommendation: <span style="color:#ff0; font-weight:bold;">HOLD / THIN MARGIN</span>`;
                }

                profitText = ` | 📈 <span style="color:${color}">Profit: $${profit}</span>`;
                profitText += `<br>⚖️ Break-even: <span style="color:#0ff">$${cost.toFixed(2)}</span>`;
                profitText += `<br><span style="font-size:16px;">📊 <span style="color:${percentColor}; font-weight:bold;">Margin: ${percent}%</span> ${strength}</span>`;
                profitText += recommendation;

                if (rawProfit < 0) {
                    profitText += ` | ⚠️ Losing money`;
                }
            }

            output.innerHTML = `💰 Estimated ${metal} value: $${total} at $${current.toFixed(3)}/lb${profitText}`;

            output.style.transition = "0.3s";
            output.style.transform = "scale(1.02)";
            output.style.boxShadow = (cost && cost > 0)
                ? (((current - cost) * lbs) >= 0 ? "0 0 10px #0f0" : "0 0 10px #f00")
                : "none";

            setTimeout(() => {
                output.style.transform = "scale(1)";
            }, 200);
        }

        async function saveCalc() {
            const lbs = parseFloat(document.getElementById('lbs').value);
            const metal = document.getElementById('metalType').value;
            const output = document.getElementById('value');

            if (!output) return;

            if (!lbs || lbs <= 0) {
                output.innerText = "Enter valid weight first";
                return;
            }

            if (!chart) {
                output.innerText = "Load market data first";
                return;
            }

            let current = chart.data.datasets[0].data[0];
            const custom = parseFloat(document.getElementById('customPrice').value);

            if (custom && custom > 0) {
                current = custom;
            } else if (metal === 'brass') {
                current = current * 0.72;
            } else if (metal === 'aluminum') {
                current = current * 0.18;
            }

            const total = (lbs * current).toFixed(2);

            const res = await fetch(
                `/save-history?metal=${encodeURIComponent(metal)}&pounds=${lbs}&price=${current}&total=${total}`
            );
            await res.json();

            output.innerText = `Saved ${metal} load to history`;
        }

        async function loadHistory() {
             const res = await fetch('/history');
             const data = await res.json();

             let html = `
                  <div style="padding:10px; margin-bottom:10px; border:1px solid #0f0;">
                   🏆 Best Price Seen: $${data.best_price?.toFixed(2) || '0.00'}<br>
                   💰 Highest Load Value: $${data.best_total?.toFixed(2) || '0.00'}
                  </div>
    `;

             data.history.forEach(item => {
             html += `
            <div>
                🪙 ${item.metal}<br>
                ⚖️ Pounds: ${item.pounds}<br>
                💵 Price/lb: $${item.price_per_lb}<br>
                💰 Total: $${item.total}<br>
                🕒 ${item.created_at}
            </div>
            <hr>
        `;
    });

    document.getElementById('history').innerHTML = html;
}

            let html = "<b>Recent Loads</b><br><br>";

            data.forEach(item => {
                html += `
                    <div style="margin-bottom:12px; border-bottom:1px solid #333; padding-bottom:8px;">
                        🪙 <b>${item.metal}</b><br>
                        ⚖️ Pounds: ${item.pounds}<br>
                        💵 Price/lb: $${Number(item.price_per_lb).toFixed(2)}<br>
                        💰 Total: $${Number(item.total).toFixed(2)}<br>
                        🕒 ${item.created_at}
                    </div>
                `;
            });

            document.getElementById('historyBox').innerHTML = html;
        }

        loadData();
    </script>
</body>
</html>
"""
