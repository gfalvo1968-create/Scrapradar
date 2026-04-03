from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from contextlib import closing
import sqlite3
import yfinance as yf
import numpy as np

app = FastAPI()

DB_NAME = "scrapradar_v2.db"


class PriceEntry(BaseModel):
    metal: str
    price: float
    yard: str
class PreciousEntry(BaseModel):
    metal: str
    price: float
    weight: float
    unit: str
    purity: float
    refinery: str

def init_db():
    with closing(sqlite3.connect(DB_NAME)) as conn:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metal TEXT NOT NULL,
                    price REAL NOT NULL,
                    yard TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS precious_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metal TEXT NOT NULL,
                    price REAL NOT NULL,
                    weight REAL NOT NULL,
                    unit TEXT NOT NULL,
                    purity REAL NOT NULL,
                    refinery TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
def init_db():
    with closing(sqlite3.connect(DB_NAME)) as conn:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metal TEXT NOT NULL,
                    price REAL NOT NULL,
                    yard TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS precious_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metal TEXT NOT NULL,
                    price REAL NOT NULL,
                    weight REAL NOT NULL,
                    refinery TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

init_db()


def get_copper_series():
    ticker = yf.Ticker("HG=F")
    hist = ticker.history(period="1mo")
    closes = hist["Close"].dropna().tolist()

    if not closes:
        return [4.25, 4.30, 4.20]

    return [float(x) for x in closes[-10:]]


def predict_prices(prices):
    if len(prices) < 2:
        return prices, 0

    x = np.arange(len(prices))
    y = np.array(prices)

    slope, intercept = np.polyfit(x, y, 1)
    trend = float(slope)

    future = []
    last_x = len(prices) - 1

    for i in range(1, 4):
        future_price = slope * (last_x + i) + intercept
        future.append(round(float(future_price), 4))

    return future, round(trend, 4)


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
            margin: 20px;
            background: #f4f6f8;
            color: #222;
        }

        h1 {
            margin-bottom: 10px;
        }

        .card {
            background: white;
            padding: 16px;
            margin-bottom: 16px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }

        input, button, select {
            padding: 10px;
            margin: 6px 0;
            width: 100%;
            max-width: 300px;
            display: block;
        }

        button {
            background: #1f6feb;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
        }

        button:hover {
            opacity: 0.92;
        }

        pre {
            background: #111;
            color: #0f0;
            padding: 12px;
            border-radius: 8px;
            overflow-x: auto;
        }

        canvas {
            margin-top: 12px;
            background: white;
            border-radius: 8px;
            max-width: 100%;
        }

        .navbar {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }

        .nav-btn {
            background: #222;
            color: white;
            border: none;
            border-radius: 10px;
            padding: 10px 16px;
            cursor: pointer;
        }

        .nav-btn.active {
            background: #1f6feb;
        }

        .section {
            display: none;
        }

        .section.active {
            display: block;
        }
    </style>
</head>
<body>
    <h1>ScrapRadar Dashboard</h1>

    <div class="card">
        <div class="navbar">
            <button class="nav-btn active" onclick="showSection('scrap', this)">Scrap Metals</button>
            <button class="nav-btn" onclick="showSection('precious', this)">Precious / Refinery</button>
            <button class="nav-btn" onclick="showSection('ewaste', this)">E-Waste / Recovery</button>
        </div>
    </div>

    <div id="scrap" class="section active">
        <div class="card">
            <h2>Current Market</h2>
            <button onclick="loadMarket()">Load Market</button>
            <pre id="marketBox">Press button to load market data...</pre>
        </div>

        <div class="card">
            <h2>Decision</h2>
            <button onclick="loadDecision()">Get Decision</button>
            <pre id="decisionBox">Press button to load decision...</pre>
        </div>

        <div class="card">
            <h2>Add Price</h2>
            <input id="metal" placeholder="Metal (example: copper)" />
            <input id="price" placeholder="Price (example: 4.25)" type="number" step="0.01" />
            <input id="yard" placeholder="Yard (example: Metro Scrap)" />
            <button onclick="addPrice()">Save Price</button>
            <pre id="addBox">Waiting for input...</pre>
        </div>

        <div class="card">
            <h2>History</h2>
            <button onclick="loadHistory()">Load History</button>
            <pre id="historyBox">Press button to load history...</pre>
        </div>

        <div class="card">
            <h2>Price Chart</h2>
            <button onclick="loadChart()">Load Chart</button>
            <canvas id="priceChart" height="120"></canvas>
        </div>
    </div>

    <div class="card">
    <h2>Add Precious Entry</h2>

    <input id="preciousMetal" placeholder="Metal (example: gold)" />
    <input id="preciousPrice" placeholder="Price per troy oz (example: 2350.50)" type="number" step="0.01" />
    <input id="preciousWeight" placeholder="Weight (example: 0.5 or 5)" type="number" step="0.01" />

    <select id="preciousUnit">
        <option value="oz">Troy Ounces (oz)</option>
        <option value="dwt">Pennyweights (dwt)</option>
    </select>

    <input id="preciousPurity" placeholder="Purity % (example: 41.7 for 10K)" type="number" step="0.1" />
    <input id="preciousRefinery" placeholder="Refinery name" />

    <button onclick="addPrecious()">Save Precious Entry</button>
    <pre id="preciousAddBox">Waiting for precious input...</pre>
</div>


    <div class="card">
        <h2>Precious History</h2>
        <button onclick="loadPreciousHistory()">Load Precious History</button>
        <pre id="preciousHistoryBox">Press button to load precious history...</pre>
    </div>

    <div class="card">
        <h2>Precious Payout Estimate</h2>
        <button onclick="calcPreciousPayout()">Calculate Payout</button>
        <pre id="preciousPayoutBox">Enter a precious entry, then calculate payout...</pre>
    </div>
</div>

    <div id="ewaste" class="section">
        <div class="card">
            <h2>E-Waste / Recovery</h2>
            <p>Chip boards, CPUs, RAM, hard drives</p>
            <pre>Recovery system coming next...</pre>
        </div>
    </div>

    <script>
        function showSection(sectionId, btn) {
            document.querySelectorAll('.section').forEach(sec => {
                sec.classList.remove('active');
            });

            document.querySelectorAll('.nav-btn').forEach(button => {
                button.classList.remove('active');
            });

            document.getElementById(sectionId).classList.add('active');
            btn.classList.add('active');
        }

        let priceChart = null;

        async function loadMarket() {
            const res = await fetch('/market');
            const data = await res.json();
            document.getElementById('marketBox').textContent = JSON.stringify(data, null, 2);
        }

        async function loadDecision() {
            const res = await fetch('/decision');
            const data = await res.json();
            document.getElementById('decisionBox').textContent = JSON.stringify(data, null, 2);
        }

        async function addPrice() {
            const metal = document.getElementById('metal').value;
            const price = parseFloat(document.getElementById('price').value);
            const yard = document.getElementById('yard').value;

            const res = await fetch('/add-price', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ metal, price, yard })
            });

            const data = await res.json();
            document.getElementById('addBox').textContent = JSON.stringify(data, null, 2);
        }

        async function loadHistory() {
            const res = await fetch('/history');
            const data = await res.json();
            document.getElementById('historyBox').textContent = JSON.stringify(data, null, 2);
        }

    async function addPrecious() {
    const metal = document.getElementById('preciousMetal').value;
    const price = parseFloat(document.getElementById('preciousPrice').value);
    const weight = parseFloat(document.getElementById('preciousWeight').value);
    const refinery = document.getElementById('preciousRefinery').value;

    async function addPrecious() {
    const metal = document.getElementById('preciousMetal').value;
    const price = parseFloat(document.getElementById('preciousPrice').value);
    const weight = parseFloat(document.getElementById('preciousWeight').value);
    const unit = document.getElementById('preciousUnit').value;
    const purity = parseFloat(document.getElementById('preciousPurity').value);
    const refinery = document.getElementById('preciousRefinery').value;

    const res = await fetch('/add-precious', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ metal, price, weight, unit, purity, refinery })
    });

    const data = await res.json();
    document.getElementById('preciousAddBox').textContent = JSON.stringify(data, null, 2);
}

async function addPrecious() {
    const metal = document.getElementById('preciousMetal').value;
    const price = parseFloat(document.getElementById('preciousPrice').value);
    const weight = parseFloat(document.getElementById('preciousWeight').value);
    const unit = document.getElementById('preciousUnit').value;
    const purity = parseFloat(document.getElementById('preciousPurity').value);
    const refinery = document.getElementById('preciousRefinery').value;

    const res = await fetch('/add-precious', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ metal, price, weight, unit, purity, refinery })
    });

    const data = await res.json();
    document.getElementById('preciousAddBox').textContent = JSON.stringify(data, null, 2);
}

function calcPreciousPayout() {
    const metal = document.getElementById('preciousMetal').value;
    const price = parseFloat(document.getElementById('preciousPrice').value);
    const weight = parseFloat(document.getElementById('preciousWeight').value);
    const refinery = document.getElementById('preciousRefinery').value;

    if (isNaN(price) || isNaN(weight)) {
        document.getElementById('preciousPayoutBox').textContent =
            JSON.stringify({ error: "Enter valid price and weight first." }, null, 2);
        return;
    }

    function calcPreciousPayout() {
    const metal = document.getElementById('preciousMetal').value;
    const price = parseFloat(document.getElementById('preciousPrice').value);
    const weight = parseFloat(document.getElementById('preciousWeight').value);
    const unit = document.getElementById('preciousUnit').value;
    const purity = parseFloat(document.getElementById('preciousPurity').value);
    const refinery = document.getElementById('preciousRefinery').value;

    if (isNaN(price) || isNaN(weight) || isNaN(purity)) {
        document.getElementById('preciousPayoutBox').textContent =
            JSON.stringify({ error: "Enter valid price, weight, and purity first." }, null, 2);
        return;
    }

    let weightOz = weight;
    if (unit === 'dwt') {
        weightOz = weight / 20;
    }

    const grossValue = price * weightOz;
    const pureValue = grossValue * (purity / 100);
    const estimatedPayout = pureValue * 0.98;

    const result = {
        metal: metal,
        refinery: refinery,
        unit: unit,
        entered_weight: weight,
        converted_weight_oz: Number(weightOz.toFixed(4)),
        purity_percent: purity,
        price_per_oz: price,
        gross_value: Number(grossValue.toFixed(2)),
        pure_value: Number(pureValue.toFixed(2)),
        estimated_payout: Number(estimatedPayout.toFixed(2))
    };

    document.getElementById('preciousPayoutBox').textContent = JSON.stringify(result, null, 2);
}

        async function loadChart() {
            const res = await fetch('/history');
            const data = await res.json();

            const labels = data.map(item => item.created_at).reverse();
            const prices = data.map(item => item.price).reverse();

            const canvas = document.getElementById('priceChart');
            const ctx = canvas.getContext('2d');

            if (priceChart) {
                priceChart.destroy();
            }

            priceChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Price History',
                        data: prices,
                        borderWidth: 2,
                        tension: 0.25
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: false
                        }
                    }
                }
            });
        }
    </script>
</body>
</html>
"""


@app.get("/market")
def market():
    copper_prices = get_copper_series()
    future, trend = predict_prices(copper_prices)

    with closing(sqlite3.connect(DB_NAME)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT metal, price, yard, created_at
            FROM prices
            ORDER BY created_at DESC
        """).fetchall()

    manual_entries = [dict(row) for row in rows]
    current_price = round(float(copper_prices[-1]), 4) if copper_prices else None

    return {
        "current": current_price,
        "forecast": future,
        "trend": trend,
        "manual_entries": manual_entries
    }


@app.get("/decision")
def decision():
    copper_prices = get_copper_series()
    _, trend = predict_prices(copper_prices)

    if trend > 0.01:
        result = "SELL NOW"
    elif trend < -0.01:
        result = "HOLD"
    else:
        result = "WAIT"

    return {"decision": result}


@app.post("/add-price")
def add_price(entry: PriceEntry):
    with closing(sqlite3.connect(DB_NAME)) as conn:
        with conn:
            conn.execute("""
                INSERT INTO prices (metal, price, yard)
                VALUES (?, ?, ?)
            """, (entry.metal, entry.price, entry.yard))

    return {"status": "saved"}


@app.get("/history")
def get_history():
    with closing(sqlite3.connect(DB_NAME)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT id, metal, price, yard, created_at
            FROM prices
            ORDER BY created_at DESC
        """).fetchall()

    return [dict(row) for row in rows]
    
@app.post("/add-precious")
def add_precious(entry: PreciousEntry):
    weight_oz = entry.weight / 20 if entry.unit == "dwt" else entry.weight

    with closing(sqlite3.connect(DB_NAME)) as conn:
        with conn:
            conn.execute("""
                INSERT INTO precious_prices (metal, price, weight, unit, purity, refinery)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                entry.metal,
                entry.price,
                entry.weight,
                entry.unit,
                entry.purity,
                entry.refinery
            ))

    gross_value = round(entry.price * weight_oz, 2)
    pure_value = round(gross_value * (entry.purity / 100), 2)
    estimated_payout = round(pure_value * 0.98, 2)

    return {
        "status": "saved",
        "metal": entry.metal,
        "unit": entry.unit,
        "entered_weight": entry.weight,
        "converted_weight_oz": round(weight_oz, 4),
        "purity_percent": entry.purity,
        "gross_value": gross_value,
        "pure_value": pure_value,
        "estimated_payout": estimated_payout
    }


@app.get("/history-precious")
def get_precious_history():
    with closing(sqlite3.connect(DB_NAME)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT id, metal, price, weight, refinery, created_at
            FROM precious_prices
            ORDER BY created_at DESC
        """).fetchall()

    return [dict(row) for row in rows]
