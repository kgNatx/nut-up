/* ============================================================
   dashboard.js — Dashboard page (redesigned)
   ============================================================

   XSS: All dynamic values pass through App.escapeHtml() /
   App.escapeAttr() before interpolation into HTML strings.
   ============================================================ */

(function () {

    // ==========================================================
    // Canvas chart utility
    // ==========================================================

    /**
     * Draw a line chart on a <canvas> element.
     *
     * @param {HTMLCanvasElement} canvas
     * @param {Array<{data: number[], color: string, fill?: boolean}>} datasets
     * @param {object} [options]
     * @param {number}  [options.yMin]     - Force Y minimum
     * @param {number}  [options.yMax]     - Force Y maximum
     * @param {boolean} [options.grid]     - Show grid lines (default true)
     * @param {string[]} [options.xLabels] - Labels for the X axis
     * @param {string}  [options.emptyText] - Text when no data
     */
    function drawLineChart(canvas, datasets, options) {
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const dpr = window.devicePixelRatio || 1;
        const rect = canvas.getBoundingClientRect();

        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        ctx.scale(dpr, dpr);

        const W = rect.width;
        const H = rect.height;
        const pad = { top: 8, right: 12, bottom: 22, left: 36 };
        const plotW = W - pad.left - pad.right;
        const plotH = H - pad.top - pad.bottom;

        ctx.clearRect(0, 0, W, H);

        // Check if we have any data
        const hasData = datasets.some(ds => ds.data && ds.data.length > 1);
        if (!hasData) {
            ctx.fillStyle = '#64748b';
            ctx.font = '12px -apple-system, BlinkMacSystemFont, sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(options && options.emptyText || 'Collecting data\u2026', W / 2, H / 2);
            return;
        }

        const opts = options || {};
        const showGrid = opts.grid !== false;

        // Compute Y range
        let yMin = opts.yMin != null ? opts.yMin : Infinity;
        let yMax = opts.yMax != null ? opts.yMax : -Infinity;
        if (yMin === Infinity || yMax === -Infinity) {
            for (const ds of datasets) {
                for (const v of ds.data) {
                    if (v < yMin) yMin = v;
                    if (v > yMax) yMax = v;
                }
            }
            // Add 5 % padding
            const range = yMax - yMin || 1;
            if (opts.yMin == null) yMin = Math.max(0, yMin - range * 0.05);
            if (opts.yMax == null) yMax = yMax + range * 0.05;
        }

        const yRange = yMax - yMin || 1;

        // Grid
        if (showGrid) {
            ctx.strokeStyle = 'rgba(255,255,255,0.05)';
            ctx.lineWidth = 1;
            const gridLines = 4;
            for (let i = 0; i <= gridLines; i++) {
                const y = pad.top + (plotH / gridLines) * i;
                ctx.beginPath();
                ctx.moveTo(pad.left, y);
                ctx.lineTo(pad.left + plotW, y);
                ctx.stroke();

                // Y labels
                const val = yMax - (yRange / gridLines) * i;
                ctx.fillStyle = '#64748b';
                ctx.font = '9px -apple-system, BlinkMacSystemFont, sans-serif';
                ctx.textAlign = 'right';
                ctx.textBaseline = 'middle';
                ctx.fillText(Math.round(val).toString(), pad.left - 6, y);
            }
        }

        // X labels
        if (opts.xLabels && opts.xLabels.length) {
            ctx.fillStyle = '#64748b';
            ctx.font = '9px -apple-system, BlinkMacSystemFont, sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'top';
            const labels = opts.xLabels;
            for (let i = 0; i < labels.length; i++) {
                const x = pad.left + (plotW / (labels.length - 1)) * i;
                ctx.fillText(labels[i], x, pad.top + plotH + 6);
            }
        }

        // Draw datasets
        for (const ds of datasets) {
            if (!ds.data || ds.data.length < 2) continue;
            const len = ds.data.length;
            const stepX = plotW / (len - 1);

            const points = [];
            for (let i = 0; i < len; i++) {
                const x = pad.left + stepX * i;
                const y = pad.top + plotH - ((ds.data[i] - yMin) / yRange) * plotH;
                points.push({ x, y });
            }

            // Fill
            if (ds.fill) {
                ctx.beginPath();
                ctx.moveTo(points[0].x, pad.top + plotH);
                for (const p of points) ctx.lineTo(p.x, p.y);
                ctx.lineTo(points[points.length - 1].x, pad.top + plotH);
                ctx.closePath();

                const grad = ctx.createLinearGradient(0, pad.top, 0, pad.top + plotH);
                grad.addColorStop(0, ds.color.replace(')', ', 0.35)').replace('rgb', 'rgba'));
                grad.addColorStop(1, ds.color.replace(')', ', 0)').replace('rgb', 'rgba'));
                ctx.fillStyle = grad;
                ctx.fill();
            }

            // Line
            ctx.beginPath();
            ctx.moveTo(points[0].x, points[0].y);
            for (let i = 1; i < points.length; i++) {
                ctx.lineTo(points[i].x, points[i].y);
            }
            ctx.strokeStyle = ds.color;
            ctx.lineWidth = 1.5;
            ctx.lineJoin = 'round';
            ctx.stroke();
        }
    }

    /**
     * Draw a mini sparkline on a <canvas> element.
     * Simpler than drawLineChart — no axes, no grid, just a line.
     */
    function drawSparkline(canvas, data, color) {
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const dpr = window.devicePixelRatio || 1;
        const rect = canvas.getBoundingClientRect();

        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        ctx.scale(dpr, dpr);

        const W = rect.width;
        const H = rect.height;
        const pad = 4;

        ctx.clearRect(0, 0, W, H);

        if (!data || data.length < 2) {
            ctx.fillStyle = '#64748b';
            ctx.font = '10px -apple-system, BlinkMacSystemFont, sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText('Collecting\u2026', W / 2, H / 2);
            return;
        }

        let min = Infinity, max = -Infinity;
        for (const v of data) {
            if (v < min) min = v;
            if (v > max) max = v;
        }
        // Provide at least a small range to avoid flat-line at edge
        const range = max - min || 1;
        min = min - range * 0.1;
        max = max + range * 0.1;
        const yRange = max - min;

        const plotW = W - pad * 2;
        const plotH = H - pad * 2;
        const stepX = plotW / (data.length - 1);

        // Subtle grid
        ctx.strokeStyle = 'rgba(255,255,255,0.04)';
        ctx.lineWidth = 1;
        for (let i = 0; i <= 2; i++) {
            const y = pad + (plotH / 2) * i;
            ctx.beginPath();
            ctx.moveTo(pad, y);
            ctx.lineTo(pad + plotW, y);
            ctx.stroke();
        }

        // Fill
        ctx.beginPath();
        ctx.moveTo(pad, pad + plotH);
        for (let i = 0; i < data.length; i++) {
            const x = pad + stepX * i;
            const y = pad + plotH - ((data[i] - min) / yRange) * plotH;
            ctx.lineTo(x, y);
        }
        ctx.lineTo(pad + plotW, pad + plotH);
        ctx.closePath();
        const grad = ctx.createLinearGradient(0, pad, 0, pad + plotH);
        grad.addColorStop(0, color.replace(')', ', 0.2)').replace('rgb', 'rgba'));
        grad.addColorStop(1, 'rgba(0,0,0,0)');
        ctx.fillStyle = grad;
        ctx.fill();

        // Line
        ctx.beginPath();
        for (let i = 0; i < data.length; i++) {
            const x = pad + stepX * i;
            const y = pad + plotH - ((data[i] - min) / yRange) * plotH;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.lineJoin = 'round';
        ctx.stroke();
    }

    // ==========================================================
    // Health determination
    // ==========================================================

    function getHealth(vars, status) {
        const charge = parseFloat(vars['battery.charge']);
        const load = parseFloat(vars['ups.load']);
        const runtime = parseFloat(vars['battery.runtime']);
        const tokens = (status || '').split(/\s+/);
        const hasOB = tokens.includes('OB');
        const hasLB = tokens.includes('LB');

        // Critical
        if (hasOB && hasLB) return 'critical';
        if (!isNaN(charge) && charge < 20) return 'critical';
        if (!isNaN(load) && load > 90) return 'critical';
        if (!isNaN(runtime) && runtime < 300) return 'critical'; // 5 min

        // Warning
        if (hasOB) return 'warning';
        if (!isNaN(charge) && charge < 50) return 'warning';
        if (!isNaN(load) && load > 70) return 'warning';
        if (!isNaN(runtime) && runtime < 900) return 'warning'; // 15 min

        return 'good';
    }

    // ==========================================================
    // Gauge builder (larger 140 px SVG gauge)
    // ==========================================================

    /**
     * Render a ring gauge SVG with a primary value centered and optional unit text.
     * @param {number|string} value - Current value
     * @param {number} max - Maximum value for fill calculation
     * @param {string} mode - 'battery'|'load'|'runtime' for color logic
     * @param {string} centerText - Text shown large in center of ring
     * @param {string} [unitText] - Small text shown below center value
     */
    function ringGauge(value, max, mode, centerText, unitText) {
        const esc = App.escapeHtml.bind(App);
        const numVal = parseFloat(value);
        const numMax = parseFloat(max);
        const size = 150;
        const r = 62;
        const cx = size / 2;
        const cy = size / 2;
        const circumference = 2 * Math.PI * r;

        if (isNaN(numVal) || isNaN(numMax) || numMax === 0) {
            return '<svg class="dash-ring-svg" width="' + size + '" height="' + size + '" viewBox="0 0 ' + size + ' ' + size + '">' +
                '<circle class="ring-track" cx="' + cx + '" cy="' + cy + '" r="' + r + '"/>' +
                '<g class="ring-text-group">' +
                '<text class="ring-center" x="' + cx + '" y="' + cy + '">--</text>' +
                '</g></svg>';
        }

        const pct = Math.min(Math.max(numVal / numMax, 0), 1);
        const offset = circumference * (1 - pct);

        let color = 'var(--accent)';
        if (mode === 'battery') {
            if (pct < 0.3) color = 'var(--danger)';
            else if (pct < 0.6) color = 'var(--warning)';
        } else if (mode === 'load') {
            if (pct > 0.9) color = 'var(--danger)';
            else if (pct > 0.7) color = 'var(--warning)';
        } else if (mode === 'runtime') {
            const secs = parseFloat(value);
            if (secs < 600) color = 'var(--danger)';
            else if (secs < 1800) color = 'var(--warning)';
        }

        let textY = unitText ? cy - 6 : cy;
        let svg = '<svg class="dash-ring-svg" width="' + size + '" height="' + size + '" viewBox="0 0 ' + size + ' ' + size + '">' +
            '<circle class="ring-track" cx="' + cx + '" cy="' + cy + '" r="' + r + '"/>' +
            '<circle class="ring-fill" cx="' + cx + '" cy="' + cy + '" r="' + r + '" ' +
            'stroke="' + color + '" ' +
            'stroke-dasharray="' + circumference.toFixed(2) + '" ' +
            'stroke-dashoffset="' + offset.toFixed(2) + '"/>' +
            '<g class="ring-text-group">' +
            '<text class="ring-center" x="' + cx + '" y="' + textY + '">' + esc(centerText) + '</text>';
        if (unitText) {
            svg += '<text class="ring-unit" x="' + cx + '" y="' + (cy + 18) + '">' + esc(unitText) + '</text>';
        }
        svg += '</g></svg>';
        return svg;
    }

    // ==========================================================
    // Runtime hero formatting
    // ==========================================================

    function formatRuntimeHero(seconds) {
        const s = parseInt(seconds, 10);
        if (isNaN(s) || s < 0) return { text: '--', sub: '' };
        const h = Math.floor(s / 3600);
        const m = Math.floor((s % 3600) / 60);
        if (h > 0) return { text: h + 'h ' + m + 'm', sub: '' };
        return { text: m + 'm', sub: '' };
    }

    function runtimeColor(seconds) {
        const s = parseInt(seconds, 10);
        if (isNaN(s) || s < 0) return 'var(--text-muted)';
        if (s < 600) return 'var(--danger)';      // <10 min
        if (s < 1800) return 'var(--warning)';     // <30 min
        return 'var(--accent)';
    }

    function runtimePct(seconds) {
        const s = parseInt(seconds, 10);
        if (isNaN(s) || s < 0) return 0;
        // Max 2 hours = 7200s
        return Math.min(s / 7200, 1) * 100;
    }

    // ==========================================================
    // Load wattage helper
    // ==========================================================

    function loadWattageLabel(vars) {
        const esc = App.escapeHtml.bind(App);
        const load = parseFloat(vars['ups.load']);
        const nominal = parseFloat(vars['ups.realpower.nominal']) || parseFloat(vars['ups.power.nominal']);

        if (isNaN(load)) return '<span class="dash-load-watts">--%</span>';

        if (!isNaN(nominal) && nominal > 0) {
            const watts = Math.round((load / 100) * nominal);
            return '<span class="dash-load-watts">' + esc(watts) + 'W of ' + esc(Math.round(nominal)) + 'W</span>';
        }
        return '<span class="dash-load-watts">' + esc(Math.round(load)) + '%</span>';
    }

    // ==========================================================
    // Build X labels for chart (time axis)
    // ==========================================================

    function timeXLabels() {
        return ['5m ago', '4m', '3m', '2m', '1m', 'now'];
    }

    // ==========================================================
    // Render
    // ==========================================================

    function render() {
        const esc = App.escapeHtml.bind(App);
        const escAttr = App.escapeAttr.bind(App);
        const ups = App.state.ups;
        const names = Object.keys(ups);

        if (names.length === 0) {
            return '<div class="page-header"><h1 class="page-title">Dashboard</h1></div>' +
                '<div class="empty-state">' +
                '<div class="spinner"></div>' +
                '<div class="empty-state-text">Waiting for data from upsd\u2026</div>' +
                '</div>';
        }

        let html = '<div class="page-header"><h1 class="page-title">Dashboard</h1></div>';

        for (const name of names) {
            const u = ups[name];
            const vars = u.variables || {};

            const model = vars['device.model'] || vars['ups.model'] || '';
            const mfr = vars['device.mfr'] || vars['ups.mfr'] || '';
            const status = u.status || vars['ups.status'] || 'unknown';
            const batteryCharge = vars['battery.charge'];
            const batteryRuntime = vars['battery.runtime'];
            const load = vars['ups.load'];
            const temp = vars['ups.temperature'] || vars['battery.temperature'];
            const inputV = vars['input.voltage'];
            const outputV = vars['output.voltage'];
            const batteryV = vars['battery.voltage'];
            const serial = vars['ups.serial'] || vars['device.serial'];

            const health = getHealth(vars, status);
            const healthClass = 'dash-card-' + health;

            // --- Card wrapper ---
            html += '<div class="dash-card ' + healthClass + ' section">';

            // --- Header bar ---
            html += '<div class="dash-header">';
            html += '<div class="dash-header-info">';
            html += '<span class="dash-ups-name">' + esc(u.description || name) + '</span>';
            if (mfr || model) {
                html += '<span class="dash-ups-model">' + esc(mfr) + (mfr && model ? ' ' : '') + esc(model) + '</span>';
            }
            html += '</div>';
            html += App.statusBadge(status);
            html += '</div>';

            // --- Top metrics row (3 cols) ---
            html += '<div class="dash-metrics-row">';

            // Compute load wattage
            var loadPct = parseFloat(load);
            var nominalW = parseFloat(vars['ups.realpower.nominal']) || parseFloat(vars['ups.power.nominal']);
            var loadWatts = (!isNaN(loadPct) && !isNaN(nominalW) && nominalW > 0) ? Math.round((loadPct / 100) * nominalW) : null;

            // Compute runtime
            var rt = formatRuntimeHero(batteryRuntime);
            var rtSecs = parseInt(batteryRuntime, 10);
            var rtMax = parseFloat(vars['battery.runtime.nominal']) || 7200;
            var rtMaxFormatted = formatRuntimeHero(rtMax).text;

            // 1. Battery
            html += '<div class="dash-metric">';
            html += '<div class="dash-metric-title">BATTERY</div>';
            html += '<div class="dash-ring-wrap">';
            html += ringGauge(batteryCharge, 100, 'battery', (isNaN(parseFloat(batteryCharge)) ? '--' : Math.round(parseFloat(batteryCharge)) + '%'));
            html += '</div>';
            html += '<div class="dash-metric-sub">' + App.batteryHtml(batteryCharge) + '</div>';
            html += '</div>';

            // 2. Load
            html += '<div class="dash-metric">';
            html += '<div class="dash-metric-title">LOAD</div>';
            html += '<div class="dash-ring-wrap">';
            if (loadWatts !== null) {
                html += ringGauge(load, 100, 'load', loadWatts + 'W', Math.round(loadPct) + '%');
            } else {
                html += ringGauge(load, 100, 'load', (isNaN(loadPct) ? '--' : Math.round(loadPct) + '%'));
            }
            html += '</div>';
            html += '<div class="dash-metric-sub">';
            if (loadWatts !== null) {
                html += '<span class="dash-sub-text">of ' + esc(Math.round(nominalW)) + 'W</span>';
            }
            // Power plug icon for visual weight
            html += '<svg class="dash-metric-icon" viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">';
            html += '<path d="M12 2v6M8 2v6M16 2v6"/>';
            html += '<rect x="6" y="8" width="12" height="6" rx="1"/>';
            html += '<path d="M10 14v3a2 2 0 0 0 4 0v-3"/>';
            html += '<line x1="12" y1="19" x2="12" y2="22"/>';
            html += '</svg>';
            html += '</div>';
            html += '</div>';

            // 3. Runtime (ring gauge)
            html += '<div class="dash-metric">';
            html += '<div class="dash-metric-title">RUNTIME</div>';
            html += '<div class="dash-ring-wrap">';
            html += ringGauge(batteryRuntime, rtMax, 'runtime', rt.text);
            html += '</div>';
            html += '<div class="dash-metric-sub"><span class="dash-sub-text">of ' + esc(rtMaxFormatted) + '</span>';
            // Clock icon for visual weight
            html += '<svg class="dash-metric-icon" viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">';
            html += '<circle cx="12" cy="12" r="10"/>';
            html += '<polyline points="12 6 12 12 16 14"/>';
            html += '</svg>';
            html += '</div>';
            html += '</div>';

            html += '</div>'; // end dash-metrics-row

            // --- Voltage row (2 cols) ---
            html += '<div class="dash-voltage-row">';

            html += '<div class="dash-voltage-card">';
            html += '<div class="dash-voltage-header">';
            html += '<span class="dash-voltage-label">Input Voltage</span>';
            html += '<span class="dash-voltage-value">' + esc(inputV != null ? inputV : '--') + '<small>V</small></span>';
            html += '</div>';
            html += '<canvas class="dash-sparkline" data-ups="' + escAttr(name) + '" data-metric="input_voltage"></canvas>';
            html += '</div>';

            html += '<div class="dash-voltage-card">';
            html += '<div class="dash-voltage-header">';
            html += '<span class="dash-voltage-label">Output Voltage</span>';
            html += '<span class="dash-voltage-value">' + esc(outputV != null ? outputV : '--') + '<small>V</small></span>';
            html += '</div>';
            html += '<canvas class="dash-sparkline" data-ups="' + escAttr(name) + '" data-metric="output_voltage"></canvas>';
            html += '</div>';

            html += '</div>'; // end dash-voltage-row

            // --- Load history chart (full width) ---
            html += '<div class="dash-chart-section">';
            html += '<div class="dash-chart-label">Load History</div>';
            html += '<canvas class="dash-load-chart" data-ups="' + escAttr(name) + '"></canvas>';
            html += '</div>';

            // --- Bottom info bar ---
            html += '<div class="dash-info-bar">';
            html += '<div class="dash-info-item"><span class="dash-info-label">Battery</span><span class="dash-info-value">' + esc(batteryV != null ? batteryV + 'V' : '--') + '</span></div>';
            html += '<div class="dash-info-item"><span class="dash-info-label">Temp</span><span class="dash-info-value">' + esc(temp != null ? temp + '\u00b0C' : '--') + '</span></div>';
            html += '<div class="dash-info-item"><span class="dash-info-label">Serial</span><span class="dash-info-value">' + esc(serial || '--') + '</span></div>';
            html += '</div>';

            html += '</div>'; // end dash-card
        }

        return html;
    }

    // ==========================================================
    // Init — called once after render; draws canvases
    // ==========================================================

    function init() {
        drawAllCanvases();
    }

    function drawAllCanvases() {
        // Sparklines
        document.querySelectorAll('.dash-sparkline').forEach(function (canvas) {
            var upsName = canvas.getAttribute('data-ups');
            var metric = canvas.getAttribute('data-metric');
            if (!upsName || !metric) return;
            var hist = App.getHistory(upsName);
            var data = hist[metric] || [];
            drawSparkline(canvas, data, 'rgb(34, 211, 167)');
        });

        // Load history charts
        document.querySelectorAll('.dash-load-chart').forEach(function (canvas) {
            var upsName = canvas.getAttribute('data-ups');
            if (!upsName) return;
            var hist = App.getHistory(upsName);
            drawLineChart(canvas, [
                { data: hist.load, color: 'rgb(34, 211, 167)', fill: true }
            ], {
                yMin: 0,
                yMax: 100,
                grid: true,
                xLabels: timeXLabels(),
                emptyText: 'Collecting load data\u2026'
            });
        });
    }

    // ==========================================================
    // Register — use init to draw canvases after each render.
    // Because refresh() doesn't call init, we hook into refresh
    // to redraw canvases via a MutationObserver fallback: we use
    // requestAnimationFrame after render.
    // ==========================================================

    // Patch: we need canvases redrawn on every refresh.  The page
    // system calls init only on first navigation, and refresh()
    // only calls render().  So we override refresh to also draw.
    var _origRefresh = null;

    function patchRefresh() {
        if (_origRefresh) return; // already patched
        _origRefresh = App.refresh.bind(App);
        App.refresh = function () {
            _origRefresh();
            // Only draw canvases if dashboard is current page
            if (App._currentPage === 'dashboard') {
                // Use rAF to let the DOM settle after innerHTML
                requestAnimationFrame(drawAllCanvases);
            }
        };
    }

    App.registerPage('dashboard', render, function () {
        patchRefresh();
        init();
    });
})();
