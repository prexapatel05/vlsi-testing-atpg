from flask import Flask, render_template_string, jsonify, request
from pathlib import Path
import os
import sys
import tracemalloc
from time import perf_counter

# Import ATPG engines
sys.path.insert(0, os.path.dirname(__file__))
from d import DAlgorithmEngine
from podem import PODEMEngine
from netlist_graph import (
    assign_default_inputs,
    generate_faults,
    levelize,
    parse_netlist,
    simulate_event_driven,
)

app = Flask(__name__)
NETLISTS_FOLDER = Path(__file__).parent / 'netlists'

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ATPG Web Console</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --ink: #10243f;
            --ink-soft: #365274;
            --paper: #f8f6ef;
            --panel: #fffdf9;
            --line: #d7cfbf;
            --accent: #ff7a18;
            --accent-strong: #ea580c;
            --d-algo: #0f766e;
            --podem: #b91c1c;
            --glow: rgba(255, 122, 24, 0.2);
        }

        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            min-height: 100vh;
            font-family: 'Space Grotesk', sans-serif;
            color: var(--ink);
            background:
                radial-gradient(circle at 90% 0%, #ffdcb8 0%, transparent 40%),
                radial-gradient(circle at 0% 100%, #d7f0ff 0%, transparent 35%),
                var(--paper);
            padding: 24px;
        }

        .shell {
            max-width: 1240px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 360px 1fr;
            gap: 20px;
            animation: riseIn 500ms ease-out;
        }

        .panel {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 18px;
            box-shadow: 0 10px 35px rgba(16, 36, 63, 0.08);
            overflow: hidden;
        }

        .panel-head {
            padding: 16px 18px;
            border-bottom: 1px solid var(--line);
            background: linear-gradient(135deg, #fff4e8, #fffdf9);
        }

        .panel-head h2 {
            margin: 0;
            font-size: 18px;
        }

        .panel-head p {
            margin: 6px 0 0;
            font-size: 13px;
            color: var(--ink-soft);
        }

        .panel-body {
            padding: 16px 18px 18px;
            display: grid;
            gap: 12px;
        }

        label {
            display: grid;
            gap: 6px;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            color: var(--ink-soft);
        }

        select,
        input[type="text"],
        input[type="file"] {
            width: 100%;
            border: 1px solid var(--line);
            border-radius: 10px;
            background: #ffffff;
            padding: 10px 12px;
            color: var(--ink);
            font-size: 14px;
            font-family: 'Space Grotesk', sans-serif;
        }

        .btn-row {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }

        button {
            border: 0;
            border-radius: 10px;
            padding: 10px 14px;
            font-size: 13px;
            font-weight: 700;
            cursor: pointer;
            transition: transform 120ms ease, box-shadow 120ms ease;
            flex: 1;
            min-width: 100px;
        }

        .btn-primary {
            background: var(--accent);
            color: #fff;
            box-shadow: 0 8px 20px var(--glow);
        }

        .btn-primary:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .btn-soft {
            background: #ffe9d2;
            color: #7c2d12;
        }

        button:hover:not(:disabled) {
            transform: translateY(-1px);
        }

        .main {
            display: grid;
            gap: 20px;
            align-content: start;
        }

        .hero {
            padding: 24px;
            border-radius: 18px;
            background: linear-gradient(135deg, #112a46, #1e4d75);
            color: #ebf7ff;
            box-shadow: 0 16px 40px rgba(16, 36, 63, 0.25);
        }

        .hero h1 {
            margin: 0;
            font-size: clamp(22px, 3vw, 34px);
            line-height: 1.1;
        }

        .hero p {
            margin: 10px 0 0;
            max-width: 860px;
            font-size: 14px;
            color: #c9e8ff;
        }

        .results {
            display: grid;
            gap: 16px;
        }

        .result-card {
            border: 1px solid var(--line);
            border-radius: 14px;
            background: #ffffff;
            overflow: hidden;
            animation: cardIn 280ms ease-out;
        }

        .result-head {
            border-bottom: 1px solid var(--line);
            padding: 12px 14px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 8px;
            background: #fff8ef;
        }

        .result-head strong {
            font-size: 15px;
        }

        .badge {
            border-radius: 999px;
            padding: 4px 10px;
            color: #fff;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
        }

        .badge-d { background: var(--d-algo); }
        .badge-podem { background: var(--podem); }
        .badge-run { background: #4b5563; }

        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
            gap: 10px;
            padding: 14px;
        }

        .stat {
            border: 1px solid var(--line);
            border-radius: 10px;
            padding: 10px;
            background: #fffdf8;
        }

        .stat .k {
            font-size: 11px;
            color: var(--ink-soft);
            text-transform: uppercase;
            font-weight: 700;
            margin-bottom: 4px;
        }

        .stat .v {
            font-size: 16px;
            font-weight: 700;
        }

        details {
            padding: 0 14px 14px;
        }

        summary {
            border: 1px solid var(--line);
            border-radius: 10px;
            padding: 9px 10px;
            cursor: pointer;
            font-weight: 700;
            background: #f4f9ff;
        }

        .faults {
            margin-top: 8px;
            max-height: 280px;
            overflow: auto;
            border: 1px solid var(--line);
            border-radius: 10px;
            background: #fff;
        }

        .fault-item {
            padding: 8px 10px;
            border-bottom: 1px solid #ece8df;
            font-family: 'IBM Plex Mono', monospace;
            font-size: 12px;
            line-height: 1.4;
        }

        .fault-item:last-child {
            border-bottom: 0;
        }

        .status {
            min-height: 20px;
            font-size: 13px;
            color: #0f5132;
            padding: 6px;
            border-radius: 6px;
            background: #f1f5fe;
        }

        .status.running {
            color: #1e40af;
            animation: pulse 1.5s ease-in-out infinite;
        }

        .status.error {
            color: #7c2d12;
            background: #fed7aa;
        }

        .status.success {
            color: #0f5132;
            background: #dcfce7;
        }

        .empty {
            text-align: center;
            color: var(--ink-soft);
            border: 1px dashed var(--line);
            border-radius: 12px;
            padding: 20px;
            background: #fff;
        }

        .dse-panel {
            border: 1px solid var(--line);
            border-radius: 14px;
            background: #ffffff;
            padding: 14px;
        }

        .dse-controls {
            display: grid;
            gap: 8px;
            margin-bottom: 10px;
        }

        .dse-metrics {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            padding: 8px 0;
        }

        .dse-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            margin-top: 8px;
        }

        .dse-table th,
        .dse-table td {
            border: 1px solid var(--line);
            padding: 8px;
            text-align: left;
        }

        .dse-table th {
            background: #f4f9ff;
        }

        .dse-chart {
            margin-top: 10px;
            border: 1px solid var(--line);
            border-radius: 10px;
            padding: 10px;
            background: #fffdf8;
        }

        @keyframes riseIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes cardIn {
            from {
                opacity: 0;
                transform: translateY(6px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }

        @media (max-width: 980px) {
            .shell {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="shell">
        <aside class="panel">
            <div class="panel-head">
                <h2>Run Configuration</h2>
                <p>Select netlists & algorithms, then execute.</p>
            </div>
            <div class="panel-body">
                <label style="text-transform: uppercase; font-size: 12px; font-weight: 700; color: #365274; margin-bottom: 8px; display: block;">
                    Select Netlists
                </label>
                <div id="netlistsContainer" style="display: grid; gap: 6px; max-height: 160px; overflow-y: auto; border: 1px solid #d7cfbf; border-radius: 10px; padding: 10px; background: #fffdf9;">
                    <p style="margin: 0; color: #999; font-size: 13px;">Loading netlists...</p>
                </div>

                <label style="text-transform: uppercase; font-size: 12px; font-weight: 700; color: #365274; margin-top: 14px; margin-bottom: 8px; display: block;">
                    Select Algorithms
                </label>
                <div style="display: grid; gap: 6px;">
                    <label style="display: flex; align-items: center; gap: 8px; font-weight: 400; text-transform: none; margin: 0; color: #10243f; cursor: pointer;">
                        <input type="checkbox" id="algoBasic" value="BASIC" />
                        <span>Basic Flow</span>
                    </label>
                    <label style="display: flex; align-items: center; gap: 8px; font-weight: 400; text-transform: none; margin: 0; color: #10243f; cursor: pointer;">
                        <input type="checkbox" id="algoD" checked value="D" />
                        <span>D Algorithm</span>
                    </label>
                    <label style="display: flex; align-items: center; gap: 8px; font-weight: 400; text-transform: none; margin: 0; color: #10243f; cursor: pointer;">
                        <input type="checkbox" id="algoPODEM" checked value="PODEM" />
                        <span>PODEM</span>
                    </label>
                </div>

                <div class="btn-row" style="margin-top: 14px;">
                    <button class="btn-primary" id="runBtn" onclick="runATPC()">Run ATPG</button>
                </div>

                <div id="status" class="status"></div>
            </div>
        </aside>

        <main class="main">
            <section class="hero">
                <h1>ATPG Web Console</h1>
                <p>Full-stack web interface for automatic test pattern generation. Select a netlist, choose your algorithm and execute directly from the browser with real-time results.</p>
            </section>

            <section class="dse-panel">
                <h2 style="margin: 0 0 6px 0; font-size: 18px;">Design Space Exploration (DSE)</h2>
                <p style="margin: 0 0 10px 0; color: #365274; font-size: 13px;">Compare D, original PODEM (SCOAP-like), and PODEM no-heuristic baseline with table + bar charts.</p>
                <div class="dse-controls">
                    <label style="display:flex; align-items:center; gap:8px; text-transform:none; font-weight:500; color:#10243f;">
                        <input type="checkbox" id="dseCompareHeur" checked />
                        <span>Include PODEM no-heuristic baseline comparison</span>
                    </label>
                    <div class="dse-metrics">
                        <label style="display:flex; align-items:center; gap:6px; text-transform:none; font-weight:500; color:#10243f;"><input type="checkbox" id="metricCoverage" checked />Coverage</label>
                        <label style="display:flex; align-items:center; gap:6px; text-transform:none; font-weight:500; color:#10243f;"><input type="checkbox" id="metricTime" checked />Time</label>
                        <label style="display:flex; align-items:center; gap:6px; text-transform:none; font-weight:500; color:#10243f;"><input type="checkbox" id="metricBacktracks" checked />Backtracks</label>
                        <label style="display:flex; align-items:center; gap:6px; text-transform:none; font-weight:500; color:#10243f;"><input type="checkbox" id="metricMemory" checked />Memory</label>
                    </div>
                    <div class="btn-row" style="margin-top: 4px;">
                        <button class="btn-soft" id="runDseBtn" onclick="runDSE()">Run DSE</button>
                    </div>
                </div>
                <div id="dseResults" class="results">
                    <div class="empty">Run DSE to view comparisons and charts.</div>
                </div>
            </section>

            <section id="results" class="results">
                <div class="empty">Select a netlist and click Run ATPG.</div>
            </section>
        </main>
    </div>

    <script>
        const netlistsContainer = document.getElementById('netlistsContainer');
        const algoBasic = document.getElementById('algoBasic');
        const algoD = document.getElementById('algoD');
        const algoPODEM = document.getElementById('algoPODEM');
        const runBtn = document.getElementById('runBtn');
        const runDseBtn = document.getElementById('runDseBtn');
        const dseCompareHeur = document.getElementById('dseCompareHeur');
        const metricCoverage = document.getElementById('metricCoverage');
        const metricTime = document.getElementById('metricTime');
        const metricBacktracks = document.getElementById('metricBacktracks');
        const metricMemory = document.getElementById('metricMemory');
        const status = document.getElementById('status');
        const results = document.getElementById('results');
        const dseResults = document.getElementById('dseResults');

        function getSelectedNetlists() {
            return Array.from(document.querySelectorAll('.netlist-cb:checked')).map(cb => cb.value);
        }

        async function loadNetlists() {
            try {
                const resp = await fetch('/api/netlists');
                const data = await resp.json();
                const netlists = data.netlists || [];

                if (netlists.length === 0) {
                    netlistsContainer.innerHTML = '<p style="margin: 0; color: #999; font-size: 13px;">No netlists found.</p>';
                    return;
                }

                netlistsContainer.innerHTML = netlists.map(nl => `
                    <label style="display: flex; align-items: center; gap: 8px; font-weight: 400; text-transform: none; margin: 0; color: #10243f; cursor: pointer;">
                        <input type="checkbox" class="netlist-cb" value="${nl}" checked />
                        <span style="font-size: 13px;">${nl}</span>
                    </label>
                `).join('');

                status.textContent = `Loaded ${netlists.length} netlists.`;
                status.classList.remove('running', 'error');
            } catch (err) {
                status.textContent = 'Failed to load netlists: ' + err.message;
                status.classList.add('error');
            }
        }

        async function runATPC() {
            const selectedNetlists = getSelectedNetlists();
            const selectedAlgos = [];
            if (algoBasic.checked) selectedAlgos.push('BASIC');
            if (algoD.checked) selectedAlgos.push('D');
            if (algoPODEM.checked) selectedAlgos.push('PODEM');

            if (selectedNetlists.length === 0) {
                status.textContent = 'Please select at least one netlist.';
                status.classList.add('error');
                return;
            }

            if (selectedAlgos.length === 0) {
                status.textContent = 'Please select at least one algorithm.';
                status.classList.add('error');
                return;
            }

            runBtn.disabled = true;
            status.textContent = `Running ${selectedAlgos.join('+')} on ${selectedNetlists.length} netlist(s)...`;
            status.classList.add('running');
            status.classList.remove('error');
            results.innerHTML = '';

            try {
                const resp = await fetch('/api/run', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ netlists: selectedNetlists, algorithms: selectedAlgos })
                });

                if (!resp.ok) {
                    throw new Error('Server error: ' + resp.status);
                }

                const data = await resp.json();

                if (data.error) {
                    status.textContent = 'Error: ' + data.error;
                    status.classList.add('error');
                    results.innerHTML = '<div class="empty">' + data.error + '</div>';
                    return;
                }

                status.textContent = `Rendered ${(data.results || []).length} result block(s).`;
                status.classList.remove('running', 'error');
                status.classList.add('success');
                renderResults(data.results || []);
            } catch (err) {
                status.textContent = 'Run failed: ' + err.message;
                status.classList.add('error');
                results.innerHTML = '<div class="empty">' + err.message + '</div>';
            } finally {
                runBtn.disabled = false;
            }
        }

        async function runDSE() {
            const selectedNetlists = getSelectedNetlists();
            if (selectedNetlists.length === 0) {
                status.textContent = 'Please select at least one netlist for DSE.';
                status.classList.add('error');
                return;
            }

            const selectedMetrics = [];
            if (metricCoverage.checked) selectedMetrics.push('coverage');
            if (metricTime.checked) selectedMetrics.push('time');
            if (metricBacktracks.checked) selectedMetrics.push('backtracks');
            if (metricMemory.checked) selectedMetrics.push('memory');

            runDseBtn.disabled = true;
            status.textContent = `Running DSE on ${selectedNetlists.length} netlist(s)...`;
            status.classList.add('running');
            status.classList.remove('error');
            dseResults.innerHTML = '';

            try {
                const resp = await fetch('/api/dse', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        netlists: selectedNetlists,
                        compare_heuristics: dseCompareHeur.checked,
                        metrics: selectedMetrics,
                    })
                });

                if (!resp.ok) {
                    throw new Error('Server error: ' + resp.status);
                }

                const data = await resp.json();
                if (data.error) {
                    status.textContent = 'DSE error: ' + data.error;
                    status.classList.add('error');
                    dseResults.innerHTML = '<div class="empty">' + data.error + '</div>';
                    return;
                }

                status.textContent = `DSE complete: ${(data.comparisons || []).length} netlist comparison(s).`;
                status.classList.remove('running', 'error');
                status.classList.add('success');
                renderDseResults(data.comparisons || [], selectedMetrics);
            } catch (err) {
                status.textContent = 'DSE failed: ' + err.message;
                status.classList.add('error');
                dseResults.innerHTML = '<div class="empty">' + err.message + '</div>';
            } finally {
                runDseBtn.disabled = false;
            }
        }

        function renderResults(resultList) {
            if (!resultList || resultList.length === 0) {
                results.innerHTML = '<div class="empty">No results to display.</div>';
                return;
            }

            const chunks = resultList.map(res => {
                const badgeClass = res.algorithm === 'D' ? 'badge-d' : (res.algorithm === 'PODEM' ? 'badge-podem' : 'badge-run');
                const statHtml = Object.entries(res.stats || {})
                    .map(([k, v]) => `<div class="stat"><div class="k">${k}</div><div class="v">${v}</div></div>`)
                    .join('');
                const faults = res.faults || [];
                const faultsHtml = faults.length
                    ? faults.map(f => `<div class="fault-item">${f}</div>`).join('')
                    : '<div class="fault-item">No per-fault lines.</div>';

                return `
                    <article class="result-card">
                        <div class="result-head">
                            <strong>${res.filename}</strong>
                            <span class="badge ${badgeClass}">${res.algorithm}</span>
                        </div>
                        <div class="stats">${statHtml}</div>
                        <details>
                            <summary>Per-fault details (${faults.length})</summary>
                            <div class="faults">${faultsHtml}</div>
                        </details>
                    </article>
                `;
            });

            results.innerHTML = chunks.join('');
        }

        function renderDseResults(comparisons, selectedMetrics) {
            if (!comparisons || comparisons.length === 0) {
                dseResults.innerHTML = '<div class="empty">No DSE comparison data.</div>';
                return;
            }

            const metricLabels = {
                coverage: 'Coverage (%)',
                time: 'Time (ms)',
                backtracks: 'Total Backtracks',
                memory: 'Peak Memory (KB)',
            };

            const cards = comparisons.map((cmp, idx) => {
                const algos = cmp.algorithms || [];
                const headers = algos.map(a => `<th>${a.label}</th>`).join('');
                const rows = selectedMetrics.map(metric => {
                    const vals = algos.map(a => {
                        const v = a.metrics[metric];
                        if (v === null || v === undefined) return 'N/A';
                        if (typeof v === 'number') return v.toFixed(metric === 'coverage' ? 2 : 3);
                        return v;
                    }).map(v => `<td>${v}</td>`).join('');
                    return `<tr><td>${metricLabels[metric] || metric}</td>${vals}</tr>`;
                }).join('');

                const overlap = cmp.fault_overlap || {};
                const overlapText = `Both detected: ${overlap.both_detected || 0}, D-only: ${overlap.d_only || 0}, PODEM-only: ${overlap.podem_only || 0}`;

                return `
                    <article class="result-card">
                        <div class="result-head">
                            <strong>${cmp.netlist}</strong>
                            <span class="badge badge-run">DSE</span>
                        </div>
                        <div style="padding: 12px; color: #365274; font-size: 13px;">${overlapText}</div>
                        <div style="padding: 0 12px 12px 12px; overflow-x:auto;">
                            <table class="dse-table">
                                <thead><tr><th>Metric</th>${headers}</tr></thead>
                                <tbody>${rows}</tbody>
                            </table>
                        </div>
                        <div class="dse-chart">
                            <canvas id="dseChart_${idx}" height="160"></canvas>
                        </div>
                    </article>
                `;
            });

            dseResults.innerHTML = cards.join('');

            comparisons.forEach((cmp, idx) => drawDseChart(`dseChart_${idx}`, cmp, selectedMetrics));
        }

        function drawDseChart(canvasId, comparison, selectedMetrics) {
            const canvas = document.getElementById(canvasId);
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            const width = canvas.width = canvas.clientWidth;
            const height = canvas.height;
            ctx.clearRect(0, 0, width, height);

            const algos = comparison.algorithms || [];
            if (!algos.length || !selectedMetrics.length) return;

            const metric = selectedMetrics[0];
            const values = algos.map(a => Number(a.metrics[metric] || 0));
            const maxVal = Math.max(...values, 1);
            const barW = Math.max(24, Math.floor((width - 40) / Math.max(values.length, 1) - 10));
            const gap = 10;
            const colors = ['#0f766e', '#b91c1c', '#1d4ed8', '#7c3aed'];

            ctx.font = '12px Space Grotesk';
            ctx.fillStyle = '#365274';
            ctx.fillText(`Bar chart metric: ${metric}`, 10, 16);

            values.forEach((v, i) => {
                const h = Math.round((v / maxVal) * (height - 55));
                const x = 20 + i * (barW + gap);
                const y = height - 25 - h;
                ctx.fillStyle = colors[i % colors.length];
                ctx.fillRect(x, y, barW, h);
                ctx.fillStyle = '#10243f';
                ctx.fillText(String(v.toFixed(metric === 'coverage' ? 2 : 1)), x, y - 5);
                ctx.save();
                ctx.translate(x + 4, height - 6);
                ctx.rotate(-0.25);
                ctx.fillText(algos[i].label, 0, 0);
                ctx.restore();
            });
        }

        loadNetlists();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/netlists', methods=['GET'])
def list_netlists():
    """List available netlists."""
    try:
        if not NETLISTS_FOLDER.exists():
            return jsonify({'netlists': []})
        
        netlists = sorted([f.name for f in NETLISTS_FOLDER.glob('*.txt')])
        return jsonify({'netlists': netlists})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/run', methods=['POST'])
def run_atpg():
    """Run ATPG on selected netlists and algorithms."""
    try:
        payload = request.json or {}
        netlist_names = payload.get('netlists', [])
        algorithms = payload.get('algorithms', ['D'])

        if not netlist_names or not isinstance(netlist_names, list):
            return jsonify({'error': 'netlists array required'}), 400
        
        if not algorithms or not isinstance(algorithms, list):
            return jsonify({'error': 'algorithms array required'}), 400

        results = []

        for netlist_name in netlist_names:
            netlist_name = netlist_name.strip()
            netlist_path = NETLISTS_FOLDER / netlist_name

            if not netlist_path.exists():
                results.append({'error': f'Netlist not found: {netlist_name}'})
                continue

            for algo in algorithms:
                algo = algo.strip().upper()
                try:
                    circuit = parse_netlist(str(netlist_path))
                    levelize(circuit)

                    if algo == 'BASIC':
                        assign_default_inputs(circuit)
                        simulate_event_driven(circuit)
                        result_data = {
                            'status': 'ok',
                            'node_count': len(circuit.nodes),
                            'pi_count': len(circuit.PIs),
                            'po_count': len(circuit.POs),
                            'po_values': {po.name: po.value for po in circuit.POs},
                            'fault_count': len(generate_faults(circuit)),
                        }
                        results.append(format_basic_result(result_data, netlist_name))
                    elif algo == 'D':
                        engine = DAlgorithmEngine(circuit)
                        result_data = engine.run()
                        results.append(format_result(result_data, 'D', netlist_name))
                    elif algo == 'PODEM':
                        engine = PODEMEngine(circuit)
                        result_data = engine.run()
                        results.append(format_result(result_data, 'PODEM', netlist_name))
                except Exception as e:
                    results.append({'error': f'{algo} failed on {netlist_name}: {str(e)}'})

        return jsonify({'results': results})
    except Exception as e:
        return jsonify({'error': f'Internal error: {str(e)}'}), 500


def _run_engine_with_memory(engine):
    """Run an ATPG engine and capture wall time plus peak traced memory."""
    tracemalloc.start()
    t0 = perf_counter()
    result = engine.run()
    wall_ms = (perf_counter() - t0) * 1000.0
    _cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    result['_wall_time_ms'] = wall_ms
    result['_memory_peak_bytes'] = peak
    return result


def _dse_algo_metrics(label, result_data):
    return {
        'key': label,
        'label': label,
        'metrics': {
            'coverage': float(result_data.get('fault_coverage_pct', 0.0)),
            'time': float(result_data.get('total_time_ms', result_data.get('_wall_time_ms', 0.0))),
            'backtracks': float(result_data.get('total_backtracks', 0)),
            'memory': float(result_data.get('_memory_peak_bytes', 0)) / 1024.0,
        },
        'summary': {
            'status': result_data.get('status', 'ok'),
            'faults': result_data.get('fault_count', 0),
            'detected': result_data.get('detected_faults', 0),
            'undetected': result_data.get('undetected_faults', 0),
        },
    }


def _detected_fault_set(result_data):
    return {
        row.get('fault')
        for row in result_data.get('results', [])
        if row.get('detected', False)
    }


@app.route('/api/dse', methods=['POST'])
def run_dse():
    """Run Design Space Exploration comparing D and PODEM variants."""
    try:
        payload = request.json or {}
        netlist_names = payload.get('netlists', [])
        compare_heuristics = bool(payload.get('compare_heuristics', True))

        if not netlist_names or not isinstance(netlist_names, list):
            return jsonify({'error': 'netlists array required'}), 400

        comparisons = []

        for netlist_name in netlist_names:
            name = str(netlist_name).strip()
            netlist_path = NETLISTS_FOLDER / name
            if not netlist_path.exists():
                comparisons.append({
                    'netlist': name,
                    'error': f'Netlist not found: {name}',
                })
                continue

            d_result = None
            podem_result = None
            podem_no_heur_result = None

            circuit = parse_netlist(str(netlist_path))
            levelize(circuit)
            d_result = _run_engine_with_memory(DAlgorithmEngine(circuit))

            circuit = parse_netlist(str(netlist_path))
            levelize(circuit)
            podem_result = _run_engine_with_memory(PODEMEngine(circuit, use_heuristics=True))

            if compare_heuristics:
                circuit = parse_netlist(str(netlist_path))
                levelize(circuit)
                podem_no_heur_result = _run_engine_with_memory(PODEMEngine(circuit, use_heuristics=False))

            algo_rows = [
                _dse_algo_metrics('D', d_result),
                _dse_algo_metrics('PODEM', podem_result),
            ]
            if podem_no_heur_result is not None:
                algo_rows.append(_dse_algo_metrics('PODEM_NO_HEUR', podem_no_heur_result))

            # Compare D against original PODEM (heuristic-enabled).
            podem_ref = podem_result
            d_set = _detected_fault_set(d_result)
            p_set = _detected_fault_set(podem_ref)

            comparisons.append({
                'netlist': name,
                'algorithms': algo_rows,
                'fault_overlap': {
                    'both_detected': len(d_set & p_set),
                    'd_only': len(d_set - p_set),
                    'podem_only': len(p_set - d_set),
                },
            })

        return jsonify({
            'status': 'ok',
            'comparisons': comparisons,
        })
    except Exception as e:
        return jsonify({'error': f'Internal error: {str(e)}'}), 500

def format_result(result_data, algo, filename):
    """Format ATPG result data for frontend display."""
    # Mirror the CLI summary fields so web output matches terminal output.
    stats = {
        'Status': result_data.get('status', 'ok'),
        'Faults simulated': result_data.get('fault_count', 0),
        'Detected faults': result_data.get('detected_faults', 0),
        'Undetected faults': result_data.get('undetected_faults', 0),
        'Fault coverage (%)': f"{result_data.get('fault_coverage_pct', 0):.2f}",
        'Total backtracks': result_data.get('total_backtracks', 0),
        'Average backtracks per fault': f"{result_data.get('avg_backtracks_per_fault', 0):.2f}",
        'Total time (ms)': f"{result_data.get('total_time_ms', 0):.3f}",
        'Average per fault (us)': f"{result_data.get('avg_time_per_fault_us', 0):.3f}",
    }

    # Keep per-fault lines in the same style as CLI output.
    faults = []
    for entry in result_data.get('results', []):
        fault_str = (
            f"- Fault {entry['fault']} | vector={entry.get('test_vector', {})} "
            f"| detected={entry.get('detected', False)} "
            f"| po={entry.get('po_values', {})} "
            f"| backtracks={entry.get('backtracks', 0)} "
            f"| time_us={entry.get('elapsed_us', 0):.3f}"
        )
        faults.append(fault_str)

    return {
        'algorithm': algo,
        'filename': filename,
        'stats': stats,
        'faults': faults,
    }


def format_basic_result(result_data, filename):
    """Format old main.py option 1 (basic flow) data for frontend display."""
    stats = {
        'Status': result_data.get('status', 'ok'),
        'Nodes': result_data.get('node_count', 0),
        'PIs': result_data.get('pi_count', 0),
        'POs': result_data.get('po_count', 0),
        'Total faults generated': result_data.get('fault_count', 0),
    }

    faults = [
        f"{po_name} = {po_val}"
        for po_name, po_val in result_data.get('po_values', {}).items()
    ]

    return {
        'algorithm': 'BASIC',
        'filename': filename,
        'stats': stats,
        'faults': faults,
    }

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
