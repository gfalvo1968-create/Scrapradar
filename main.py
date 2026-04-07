from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
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
<body style="font-family:Arial; padding:20px; background:#111; color:#0f0;">

    <div id="startupOverlay" style="
        position:fixed;
        inset:0;
        background:#000;
        z-index:9999;
        display:flex;
        align-items:center;
        justify-content:center;
        flex-direction:column;
        color:#0f0;
    ">
        <div id="radarWrap" style="
            position:relative;
            width:260px;
            height:260px;
            border:3px solid #0f0;
            border-radius:50%;
            box-shadow:0 0 20px #0f0;
            overflow:hidden;
        ">
            <div style="
                position:absolute;
                inset:0;
                background:
                    radial-gradient(circle, rgba(0,255,0,0.08) 1px, transparent 2px),
                    repeating-radial-gradient(circle, transparent 0 38px, rgba(0,255,0,0.18) 40px 41px),
                    repeating-linear-gradient(0deg, transparent 0 49%, rgba(0,255,0,0.12) 50%, transparent 51%),
                    repeating-linear-gradient(90deg, transparent 0 49%, rgba(0,255,0,0.12) 50%, transparent 51%);
            "></div>

            <div id="radarSweep" style="
                position:absolute;
                left:50%;
                top:50%;
                width:50%;
                height:2px;
                background:#0f0;
                transform-origin:left center;
                transform:rotate(0deg);
                box-shadow:0 0 12px #0f0;
            "></div>

            <img src="/static/logo.png" id="radarLogo" style="
    position:absolute;
    left:50%;
    top:50%;
    width:80px;
    height:80px;
    object-fit:contain;
    transform:translate(-50%, -50%) scale(0.6);
    opacity:0;
    filter:drop-shadow(0 0 12px #0f0);
    transition:all 1.5s ease;
">
        </div>

        <div id="startupTitle" style="
            margin-top:28px;
            font-size:24px;
            font-weight:bold;
            letter-spacing:2px;
            color:#0f0;
            text-shadow:0 0 12px #0f0;
            transform:scale(0.7);
            transition:transform 0.25s ease;
        ">
            ScrapRadar
        </div>
    </div>

   </div> <!-- closes startupOverlay -->

<div id="mainApp" style="
    display:none;
    opacity:0;
    transition:opacity 0.8s ease;
    padding:20px;
"></div> <!-- closes startupOverlay -->
 
      <h1>ScrapRadar Dashboard</h1>

<button onclick="loadData()">Load Market Data</button>

<div style="margin-top:20px; display:flex; gap:10px;">
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

<div id="value"></div>

<div id="stats"></div>

<div>
    <button onclick="saveCalc()">Save</button>
    <button onclick="loadHistory()">Load History</button>
</div>

<div id="historyBox"></div>
        
        
        <h1>ScrapRadar Dashboard</h1>

        <button onclick="loadData()" style="padding:10px; font-size:16px; border-radius:20px;">
            Load Market Data
        </button>

        <div style="margin-top:20px; display:flex; flex-wrap:wrap; gap:8px; align-items:center;">
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

        <div id="value" style="margin-top:16px; font-size:18px; line-height:1.7;"></div>

        <div id="stats" style="margin-top:20px; font-size:18px;"></div>

        <div style="margin-top:20px;">
            <button onclick="saveCalc()" style="padding:10px; border-radius:20px;">Save To History</button>
            <button onclick="loadHistory()" style="padding:10px; margin-left:8px; border-radius:20px;">Load History</button>
        </div>

        <div id="historyBox" style="
            margin-top:20px;
            background:#000;
            padding:10px;
            color:#0f0;
            min-height:40px;
        ">History will show here...</div>

        <canvas id="chart" style="margin-top:20px; max-width:100%; background:#111;"></canvas>

    </div>

<script>
let chart;
const radarTargets = [
  { name: "Joe's Scrap Yard", type: "scrap", premium: true },
  { name: "Main St Jewelers", type: "gold", premium: false },
];

function playRadarBeep() {
    try {
        const logo = document.getElementById("radarLogo");

if (logo) {
    logo.style.opacity = Math.min(rotations * 0.3, 1);
    logo.style.transform = `translate(-50%, -50%) scale(${0.6 + rotations * 0.2})`;

if (rotations >= 3) {
    clearInterval(intro);
    overlay.style.display = "none";
    mainApp.style.display = "block";
}

}
        
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();

        osc.type = 'sine';
        osc.frequency.setValueAtTime(880, audioCtx.currentTime);

        gain.gain.setValueAtTime(0.001, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.12, audioCtx.currentTime + 0.01);
        gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.12);

        osc.connect(gain);
        gain.connect(audioCtx.destination);

        osc.start();
        osc.stop(audioCtx.currentTime + 0.13);
    } catch (e) {
        console.log("beep blocked");
    }
}

function runStartupIntro() {
    const overlay = document.getElementById('startupOverlay');
    const sweep = document.getElementById('radarSweep');
    const title = document.getElementById('startupTitle');
    const mainApp = document.getElementById('mainApp');

    let angle = 0;
    let rotations = 0;
    let scale = 0.7;

    const intro = setInterval(() => {
        angle += 4;
        sweep.style.transform = `rotate(${angle}deg)`;

       if (angle >= 360) {
    angle = 0;
    rotations += 1;

    playRadarBeep();

    if (angle >= 360) {
    angle = 0;
    rotations += 1;
    playRadarBeep();
}

    const target = radarTargets[Math.floor(Math.random() * radarTargets.length)];

    showRadarPing(target);

    if (target.premium) {
        playRadarBeep();
    }
}

            scale += 0.18;
            title.style.transform = `scale(${scale})`;

            if (rotations >= 4) {
                clearInterval(intro);
                overlay.style.transition = 'opacity 0.8s ease';
                overlay.style.opacity = '0';

                setTimeout(() => {
                    overlay.style.display = 'none';
                    mainApp.style.opacity = '1';
                }, 850);
            }
        }
    }, 20);
}

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
                    borderColor: '#3fa9f5',
                    backgroundColor: 'rgba(63,169,245,0.25)',
                    tension: 0.35
                }]
            },
            options: {
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
        document.getElementById('stats').innerText = "Error loading data";
    }
}

async function calcValue() {
    const lbs = parseFloat(document.getElementById('lbs').value);
    const metal = document.getElementById('metalType').value;
    const output = document.getElementById('value');

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
    const cost = parseFloat(document.getElementById('cost').value);

    let profitText = "";
    let extraText = "";

    if (cost && cost > 0) {
        const rawProfit = (current - cost) * lbs;
        const profit = rawProfit.toFixed(2);
        const percent = (((current - cost) / cost) * 100).toFixed(2);

        const profitColor = rawProfit >= 0 ? "#0f0" : "#f00";
        const marginColor =
            rawProfit < 0 ? "#f00" :
            percent > 10 ? "#0ff" :
            percent > 3 ? "#0f0" :
            percent > 0 ? "#ff0" :
            "#f00";

        let strength =
            rawProfit < 0 ? "❌ Loss" :
            percent > 10 ? "🔥 Strong" :
            percent > 3 ? "👍 Solid" :
            percent > 0 ? "⚠️ Thin" :
            "➖ Flat";

        let recommendation =
            rawProfit < 0 ? "🚫 Recommendation: PASS" :
            percent > 10 ? "✅ Recommendation: SELL NOW" :
            percent > 3 ? "👍 Recommendation: GOOD DEAL" :
            percent > 0 ? "⏳ Recommendation: HOLD / THIN MARGIN" :
            "➖ Recommendation: HOLD";

        profitText = ` | 📈 <span style="color:${profitColor}">Profit: $${profit}</span>`;
        extraText = `
            <div>⚖️ Break-even: <span style="color:#0ff">$${cost.toFixed(2)}</span></div>
            <div>📊 <span style="color:${marginColor}">Margin: ${percent}% ${strength}</span></div>
            <div style="font-weight:bold; text-shadow:0 0 10px ${profitColor};">${recommendation}</div>
        `;

        if (rawProfit < 0) {
            extraText += `<div>⚠️ Losing money</div>`;
        }
    }

    output.innerHTML = `
        <div>💰 Estimated ${metal} value: $${total} at $${current.toFixed(3)}/lb${profitText}</div>
        ${extraText}
    `;

    output.style.transition = "0.3s";
    output.style.boxShadow = cost && cost > 0
        ? (parseFloat((((current - cost) / cost) * 100).toFixed(2)) < 0
            ? "0 0 15px #f00"
            : "0 0 15px #0f0")
        : "none";
}

async function saveCalc() {
    const lbs = parseFloat(document.getElementById('lbs').value);
    const metal = document.getElementById('metalType').value;
    const output = document.getElementById('value');

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
    loadHistory();
}

async function loadHistory() {
    const res = await fetch('/history?nocache=' + Date.now());
    const data = await res.json();

    if (!data.history.length) {
        document.getElementById('historyBox').innerHTML = "No history yet...";
        return;
    }

    let html = `
        <div style="margin-bottom:16px;">
            <b>🏆 Best price/lb:</b> $${Number(data.best_price || 0).toFixed(2)}<br>
            <b>💰 Best total:</b> $${Number(data.best_total || 0).toFixed(2)}
        </div>
        <b>Recent Loads</b><br><br>
    `;

    data.history.forEach(item => {
        html += `
            <div style="margin-bottom:12px; border-bottom:1px solid #333; padding-bottom:8px;">
                🌕 <b>${item.metal}</b><br>
                ⚖️ Pounds: ${item.pounds}<br>
                💵 Price/lb: $${Number(item.price_per_lb).toFixed(2)}<br>
                💰 Total: $${Number(item.total).toFixed(2)}<br>
                🕒 ${item.created_at}
            </div>
        `;
    });

    document.getElementById('historyBox').innerHTML = html;
}

document.getElementById('startupOverlay').style.display = 'none';
document.getElementById('mainApp').style.opacity = '1';
loadData();
loadHistory();
</script>
</body>
</html>
"""


# Railway start target:
# uvicorn main:app --host 0.0.0.0 --port $PORT
