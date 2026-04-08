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
    ticker = yf.Ticker("HG=F")
    data = ticker.history(period="5d")

    prices = data["Close"].dropna().tolist()

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
@app.get("/gold-spot")
def gold_spot():
    gold = yf.Ticker("GC=F")
    data = gold.history(period="1d")
    price = float(data["Close"].iloc[-1])
    return {"price": round(price, 2)}



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
            background: #111;
            color: #0f0;
            padding: 20px;
            margin: 0;
        }

        h1 {
            margin-bottom: 20px;
        }

        .row {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 15px;
        }

        input, select, button {
            padding: 10px;
            font-size: 16px;
            border-radius: 10px;
            border: none;
        }

        button {
            cursor: pointer;
        }

        .box {
            margin-top: 18px;
            padding: 12px;
            background: #000;
            border: 1px solid #222;
            border-radius: 10px;
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
        <div class="box">
    <h2>Gold Calculator</h2>

    <div class="row">
        <select id="karat">
            <option value="0.417">10k</option>
            <option value="0.585">14k</option>
            <option value="0.750">18k</option>
            <option value="0.916">22k</option>
            <option value="0.999">24k</option>
        </select>

        <input id="goldWeight" placeholder="Weight (grams)">
        <input id="spotPrice" placeholder="Spot ($/oz)">
        <input id="payout" placeholder="Payout % (e.g. 80)">
        
        <button onclick="calcGold()">Calculate Gold</button>
    </div>

    <div id="goldResult"></div>
</div>
    </style>

</head>
<body>
    <h1>ScrapRadar Dashboard</h1>

    <button onclick="loadData()">Load Market Data</button>

    <div class="row" style="margin-top:20px;">
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

    <div class="row" style="margin-top:20px;">
        <button onclick="saveCalc()">Save To History</button>
        <button onclick="loadHistory()">Load History</button>
    </div>

    <div id="historyBox" class="box">History will show here...</div>

   <div class="card">
  <div class="box">
  <h2>Gold Calculator</h2>

  <select id="karat">
    <option value="0.417">10k</option>
    <option value="0.585">14k</option>
    <option value="0.750">18k</option>
    <option value="0.916">22k</option>
    <option value="0.999">24k</option>
  </select>

  <input id="goldWeight" placeholder="Weight (grams)">
  <input id="spotPrice" placeholder="Spot ($/oz)">
  <input id="payout" placeholder="Payout %">

  <button onclick="calcGold()">Calculate Gold</button>


}

  <div id="goldResult"></div>
</div>

>
    
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
                document.getElementById('stats').innerText = 'Error loading market data';
            }
        }

        function calcValue() {
            const lbs = parseFloat(document.getElementById('lbs').value);
            const metal = document.getElementById('metalType').value;
            const customPrice = parseFloat(document.getElementById('customPrice').value);
            const cost = parseFloat(document.getElementById('cost').value);
            const output = document.getElementById('value');

            if (!lbs || lbs <= 0) {
                output.innerText = 'Enter valid weight';
                return;
            }

            if (!chart) {
                output.innerText = 'Load market data first';
                return;
            }

            let current = chart.data.datasets[0].data[0];

            if (customPrice && customPrice > 0) {
                current = customPrice;
            } else if (metal === 'brass') {
                current = current * 0.72;
            } else if (metal === 'aluminum') {
                current = current * 0.18;
            }

            const total = (lbs * current).toFixed(2);

            let html = `💰 Estimated ${metal} value: $${total} at $${current.toFixed(3)}/lb`;

            if (cost && cost > 0) {
                const rawProfit = (current - cost) * lbs;
                const percent = (((current - cost) / cost) * 100).toFixed(2);
                const label =
                    rawProfit < 0 ? '❌ PASS' :
                    percent >= 10 ? '✅ SELL NOW' :
                    percent >= 3 ? '👍 GOOD DEAL' :
                    '⚠️ HOLD';

                html += `<br>⚖️ Break-even: $${cost.toFixed(2)}`;
                html += `<br>📊 Margin: ${percent}%`;
                html += `<br>📈 Profit: $${rawProfit.toFixed(2)}`;
                html += `<br><b>${label}</b>`;

                if (rawProfit < 0) {
                    html += `<br>⚠️ Losing money`;
                }
            }

            output.innerHTML = html;
        }

        async function saveCalc() {
            const lbs = parseFloat(document.getElementById('lbs').value);
            const metal = document.getElementById('metalType').value;
            const output = document.getElementById('value');
            const customPrice = parseFloat(document.getElementById('customPrice').value);

            if (!lbs || lbs <= 0) {
                output.innerText = 'Enter valid weight first';
                return;
            }

            if (!chart) {
                output.innerText = 'Load market data first';
                return;
            }

            let current = chart.data.datasets[0].data[0];

            if (customPrice && customPrice > 0) {
                current = customPrice;
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
            loadHistory();
        }

        async function loadHistory() {
            try {
                const res = await fetch('/history?nocache=' + Date.now());
                const data = await res.json();

                let html = '';

                if (data.best_price !== null) {
                    html += `🏆 Best price/lb: $${Number(data.best_price).toFixed(2)}<br>`;
                }

                if (data.best_total !== null) {
                    html += `💰 Best total: $${Number(data.best_total).toFixed(2)}<br><br>`;
                }

                html += `<b>Recent Loads</b><br><br>`;

                if (!data.history.length) {
                    html += 'No history yet...';
                } else {
                    data.history.forEach(item => {
                        html += `
                            <div style="margin-bottom:12px; border-bottom:1px solid #333; padding-bottom:12px;">
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

        function calcGold() {
    const karat = parseFloat(document.getElementById('karat').value);
    const grams = parseFloat(document.getElementById('goldWeight').value);
    const spot = parseFloat(document.getElementById('spotPrice').value);
    const payout = parseFloat(document.getElementById('payout').value) / 100;

    const output = document.getElementById('goldResult');

    if (!grams || !spot || !payout) {
        output.innerText = "Enter all values";
        return;
    }

    const troyOunce = 31.1035;

    const pureGold = grams * karat;
    const meltValue = (pureGold / troyOunce) * spot;
    const offer = meltValue * payout;

    let rating =
        payout >= 0.9 ? "🔥 Excellent" :
        payout >= 0.8 ? "✅ Strong" :
        payout >= 0.7 ? "👍 Fair" :
        "⚠️ Low";

output.innerHTML = `
🔥 Pure Gold: ${pureGold.toFixed(2)}g<br>
💰 Melt Value: $${meltValue.toFixed(2)}<br>
🏦 Offer Value: $${offer.toFixed(2)}<br>
📊 Rating: <b>${rating}</b>
`;
    `;
function calcGold() {
  alert("clicked");
}

}

        loadData();
        loadHistory();
    </script>
</body>
</html>
"""
