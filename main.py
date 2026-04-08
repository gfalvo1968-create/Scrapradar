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
    return {"status": "saved"}


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

    best_price = cur.execute("""
        SELECT MAX(price_per_lb) FROM history
    """).fetchone()[0]

    best_total = cur.execute("""
        SELECT MAX(total) FROM history
    """).fetchone()[0]

    conn.close()

    return {
        "history": [dict(row) for row in rows],
        "best_price": best_price,
        "best_total": best_total
    }


@app.get("/market")
def market():
    try:
        ticker = yf.Ticker("HG=F")
        data = ticker.history(period="5d")

        prices = data["Close"].dropna().tolist()

        if len(prices) < 3:
            return {"error": "Not enough market data"}

        current = round(float(prices[-1]), 3)
        forecast = [round(float(p * 1.01), 4) for p in prices[-3:]]
        trend = round((float(prices[-1]) - float(prices[0])) / float(prices[0]), 4)

        return {
            "current": current,
            "forecast": forecast,
            "trend": trend
        }
    except Exception as e:
        return {"error": f"Market load failed: {str(e)}"}


@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>ScrapRadar Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            padding: 20px;
            background: #111;
            color: #0f0;
        }

        h1 {
            color: #0f0;
            margin-bottom: 18px;
        }

        input, select, button {
            padding: 10px;
            margin: 5px 5px 5px 0;
            border-radius: 10px;
            font-size: 16px;
        }

        .row {
            margin-top: 20px;
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }

        .box {
            margin-top: 18px;
            background: #000;
            border: 1px solid #222;
            border-radius: 10px;
            padding: 15px;
        }

        #value {
            font-size: 20px;
            line-height: 1.6;
        }

        #stats {
            font-size: 18px;
            line-height: 1.6;
        }

        #historyBox {
            line-height: 1.6;
        }

        canvas {
            margin-top: 20px;
            max-width: 100%;
            background: #111;
            border-radius: 10px;
        }
    </style>
</head>
<body>

<h1>ScrapRadar Dashboard</h1>

<button onclick="loadData()">Load Market Data</button>

<div class="row">
    <input id="lbs" placeholder="Enter pounds">
    <select id="metalType">
        <option value="copper">Copper</option>
        <option value="brass">Brass</option>
        <option value="aluminum">Aluminum</option>
    </select>
    <input id="customPrice" placeholder="Custom price">
    <input id="cost" placeholder="Your cost">
    <button onclick="calcValue()">Calculate Value</button>
</div>

<div id="value" class="box"></div>
<div id="stats" class="box"></div>

<div class="row">
    <button onclick="saveCalc()">Save To History</button>
    <button onclick="loadHistory()">Load History</button>
</div>

<div id="historyBox" class="box">History will show here...</div>

<canvas id="chart"></canvas>

<script>
let chart = null;

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
                    borderWidth: 3,
                    tension: 0.35
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        labels: { color: '#0f0' }
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
        document.getElementById('stats').innerText = 'Error loading market data';
    }
}

function calcValue() {
    const lbs = parseFloat(document.getElementById('lbs').value);
    const metal = document.getElementById('metalType').value;
    const customPrice = parseFloat(document.getElementById('customPrice').value);
    const cost = parseFloat(document.getElementById('cost').value);
    const output = document.getElementById('value');
    const statsText = document.getElementById('stats').innerText;

    const match = statsText.match(/\\$([0-9.]+)/);
    let current = match ? parseFloat(match[1]) : 0;

    if (customPrice) {
        current = customPrice;
    } else if (metal === 'brass') {
        current = current * 0.72;
    } else if (metal === 'aluminum') {
        current = current * 0.18;
    }

    if (!lbs || !current) {
        output.innerHTML = "<span style='color:red'>Enter pounds and load market data first</span>";
        return;
    }

    const total = lbs * current;
    let html = `💰 Estimated ${metal} value: <b>$${total.toFixed(2)}</b> at <b>$${current.toFixed(3)}/lb</b>`;

    if (cost && cost > 0) {
        const rawProfit = (current - cost) * lbs;
        const percent = ((current - cost) / cost) * 100;
        const color = rawProfit >= 0 ? '#0f0' : '#f00';

        html += ` | <span style="color:${color}">📈 Profit: $${rawProfit.toFixed(2)}</span>`;
        html += `<br>⚖️ Break-even: $${cost.toFixed(2)}`;
        html += `<br>📊 Margin: ${percent.toFixed(2)}%`;
    }

    output.innerHTML = html;
}

async function saveCalc() {
    const lbs = parseFloat(document.getElementById('lbs').value);
    const metal = document.getElementById('metalType').value;
    const customPrice = parseFloat(document.getElementById('customPrice').value);
    const statsText = document.getElementById('stats').innerText;
    const output = document.getElementById('value');

    const match = statsText.match(/\\$([0-9.]+)/);
    let current = match ? parseFloat(match[1]) : 0;

    if (customPrice) {
        current = customPrice;
    } else if (metal === 'brass') {
        current = current * 0.72;
    } else if (metal === 'aluminum') {
        current = current * 0.18;
    }

    if (!lbs || !current) {
        output.innerText = 'Nothing to save yet';
        return;
    }

    const total = lbs * current;

    try {
        const res = await fetch(
            `/save-history?metal=${encodeURIComponent(metal)}&pounds=${lbs}&price=${current}&total=${total}`
        );
        await res.json();
        output.innerText = `Saved ${metal} load to history`;
        loadHistory();
    } catch (err) {
        output.innerText = 'Error saving history';
    }
}

async function loadHistory() {
    try {
        const res = await fetch('/history?nocache=' + Date.now());
        const data = await res.json();

        let html = '';

        if (data.best_price != null) {
            html += `🏆 Best price/lb: $${Number(data.best_price).toFixed(2)}<br>`;
        }

        if (data.best_total != null) {
            html += `💰 Best total: $${Number(data.best_total).toFixed(2)}<br><br>`;
        }

        html += '<b>Recent Loads</b><br><br>';

        if (!data.history || !data.history.length) {
            html += 'No history yet...';
        } else {
            data.history.forEach(item => {
                html += `
                    <div style="margin-bottom:12px; border-bottom:1px solid #333; padding-bottom:10px;">
                        🪙 <b>${item.metal}</b><br>
                        ⚖️ Pounds: ${item.pounds}<br>
                        💵 Price/lb: $${Number(item.price_per_lb).toFixed(2)}<br>
                        💰 Total: $${Number(item.total).toFixed(2)}<br>
                        🕒 ${item.created_at}
                    </div>
                `;
            });
        }

        document.getElementById('historyBox').innerHTML = html;
    } catch (err) {
        document.getElementById('historyBox').innerText = 'Error loading history';
    }
}

loadData();
loadHistory();
</script>

</body>
</html>
"""
