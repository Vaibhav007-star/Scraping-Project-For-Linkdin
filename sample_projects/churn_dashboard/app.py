"""
Sample Interactive Customer Churn Prediction Dashboard
Self-contained Python HTTP server with rich visual analytics, metrics,
and interactive prediction buttons for Playwright automated demo recording.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import sys

HTML_DASHBOARD = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Customer Churn Intelligence Engine</title>
    <style>
        :root {
            --bg: #0f172a;
            --surface: #1e293b;
            --primary: #3b82f6;
            --accent: #10b981;
            --danger: #ef4444;
            --text: #f8fafc;
            --muted: #94a3b8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        body { background: var(--bg); color: var(--text); padding: 24px; }
        header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 16px; margin-bottom: 24px; }
        h1 { font-size: 24px; font-weight: 700; color: #60a5fa; }
        .badge { background: rgba(59, 130, 246, 0.2); color: #93c5fd; padding: 6px 12px; border-radius: 9999px; font-size: 13px; font-weight: 600; border: 1px solid #3b82f6; }
        .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
        .card { background: var(--surface); border-radius: 12px; padding: 20px; border: 1px solid #334155; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
        .card-title { font-size: 13px; text-transform: uppercase; color: var(--muted); margin-bottom: 8px; letter-spacing: 0.05em; }
        .card-value { font-size: 28px; font-weight: 700; }
        .val-good { color: var(--accent); }
        .val-bad { color: var(--danger); }
        .val-blue { color: #60a5fa; }
        .main-layout { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }
        .chart-panel { background: var(--surface); border-radius: 12px; padding: 20px; border: 1px solid #334155; min-height: 280px; }
        .chart-bars { display: flex; align-items: flex-end; height: 160px; gap: 14px; margin-top: 24px; border-bottom: 2px solid #475569; padding-bottom: 8px; }
        .bar { flex: 1; background: linear-gradient(180deg, #3b82f6 0%, #1d4ed8 100%); border-radius: 6px 6px 0 0; position: relative; transition: height 0.6s ease; }
        .bar:nth-child(4) { background: linear-gradient(180deg, #ef4444 0%, #b91c1c 100%); }
        .bar-label { position: absolute; bottom: -24px; left: 0; right: 0; text-align: center; font-size: 11px; color: var(--muted); }
        .control-panel { background: var(--surface); border-radius: 12px; padding: 20px; border: 1px solid #334155; }
        .form-group { margin-bottom: 16px; }
        label { display: block; font-size: 13px; color: var(--muted); margin-bottom: 6px; }
        input, select { width: 100%; background: #0f172a; border: 1px solid #475569; color: #fff; padding: 10px; border-radius: 8px; font-size: 14px; }
        button.btn-primary { width: 100%; background: #2563eb; color: #fff; border: none; padding: 12px; border-radius: 8px; font-size: 15px; font-weight: 600; cursor: pointer; transition: background 0.2s; margin-top: 10px; }
        button.btn-primary:hover { background: #1d4ed8; }
        .prediction-result { margin-top: 18px; padding: 14px; background: rgba(16, 185, 129, 0.1); border: 1px solid #10b981; border-radius: 8px; display: none; }
        .tabs { display: flex; gap: 10px; margin-bottom: 16px; }
        .tab-btn { background: #334155; border: none; color: #fff; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 500; }
        .tab-btn.active { background: #2563eb; }
    </style>
</head>
<body>
    <header>
        <div>
            <h1>Customer Churn Intelligence Engine</h1>
            <p style="color: var(--muted); font-size: 14px; margin-top: 4px;">Real-Time Gradient Boosted Survival & Retention Forecaster</p>
        </div>
        <div class="badge">Model: XGBoost v2.4 (F1: 0.89)</div>
    </header>

    <div class="tabs">
        <button class="tab-btn active" onclick="switchTab('overview')">Overview Dashboard</button>
        <button class="tab-btn" onclick="switchTab('inference')">Live Inference Model</button>
        <button class="tab-btn" onclick="switchTab('features')">SHAP Feature Importances</button>
    </div>

    <div class="grid">
        <div class="card">
            <div class="card-title">Monthly Churn Rate</div>
            <div class="card-value val-bad">2.14% <span style="font-size: 14px; color: var(--accent);">(-0.48%)</span></div>
        </div>
        <div class="card">
            <div class="card-title">High Risk Accounts</div>
            <div class="card-value val-bad">142 <span style="font-size: 14px; color: var(--muted);">/ 6,850</span></div>
        </div>
        <div class="card">
            <div class="card-title">Retained ARR Protected</div>
            <div class="card-value val-good">$1.42M</div>
        </div>
        <div class="card">
            <div class="card-title">Inference Latency</div>
            <div class="card-value val-blue">14 ms</div>
        </div>
    </div>

    <div class="main-layout">
        <div class="chart-panel">
            <h3 style="font-size: 16px; margin-bottom: 4px;">Cohort Risk Distribution & Model Forecast</h3>
            <p style="font-size: 12px; color: var(--muted);">Probability buckets across active customer accounts</p>
            <div class="chart-bars">
                <div class="bar" style="height: 35%;"><div class="bar-label">0-15%</div></div>
                <div class="bar" style="height: 65%;"><div class="bar-label">15-35%</div></div>
                <div class="bar" style="height: 85%;"><div class="bar-label">35-65%</div></div>
                <div class="bar" style="height: 45%;"><div class="bar-label">>65% Risk</div></div>
            </div>
        </div>

        <div class="control-panel">
            <h3 style="font-size: 16px; margin-bottom: 12px;">Instant Account Predictor</h3>
            <div class="form-group">
                <label>Contract Tenure (Months)</label>
                <input type="number" id="tenure" value="14" min="1" max="72">
            </div>
            <div class="form-group">
                <label>Support Tickets (Last 30 Days)</label>
                <input type="number" id="tickets" value="5" min="0" max="20">
            </div>
            <div class="form-group">
                <label>Monthly Spend Tier</label>
                <select id="spend">
                    <option value="enterprise">Enterprise ($2,400/mo)</option>
                    <option value="growth" selected>Growth Tier ($650/mo)</option>
                    <option value="starter">Starter Tier ($99/mo)</option>
                </select>
            </div>
            <button class="btn-primary" id="predictBtn" onclick="runPrediction()">Run Churn Prediction</button>
            <div class="prediction-result" id="predictionResult">
                <div style="font-weight: 700; color: #34d399; font-size: 14px;">PREDICTION: LOW CHURN RISK</div>
                <div style="font-size: 12px; color: var(--text); margin-top: 4px;">Estimated Churn Probability: <strong>11.4%</strong></div>
                <div style="font-size: 12px; color: var(--muted); margin-top: 2px;">Recommended: Schedule QBR engagement.</div>
            </div>
        </div>
    </div>

    <script>
        function runPrediction() {
            const res = document.getElementById('predictionResult');
            res.style.display = 'block';
            res.style.animation = 'fadeIn 0.5s';
        }
        function switchTab(name) {
            const tabs = document.querySelectorAll('.tab-btn');
            tabs.forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
        }
    </script>
</body>
</html>
"""


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_DASHBOARD.encode("utf-8"))

    def log_message(self, format, *args):
        # Suppress noisy HTTP request terminal output
        return


def run(port=8501):
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, DashboardHandler)
    print(f"Sample Churn Dashboard Server running at http://127.0.0.1:{port}")
    sys.stdout.flush()
    httpd.serve_forever()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8501
    run(port)
