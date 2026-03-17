/* ============================================================
   dashboard.js — Dashboard page
   ============================================================ */

(function () {
    function render() {
        const esc = App.escapeHtml.bind(App);
        const ups = App.state.ups;
        const names = Object.keys(ups);

        if (names.length === 0) {
            return '<div class="page-header"><h1 class="page-title">Dashboard</h1></div>' +
                '<div class="empty-state">' +
                '<div class="spinner"></div>' +
                '<div class="empty-state-text">Waiting for data from upsd...</div>' +
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

            html += '<div class="card section">';
            html += '<div class="card-header">';
            html += '<div>';
            html += '<div class="card-title">' + esc(u.description || name) + '</div>';
            if (mfr || model) {
                html += '<div class="card-subtitle">' + esc(mfr) + (mfr && model ? ' ' : '') + esc(model) + '</div>';
            }
            html += '</div>';
            html += App.statusBadge(status);
            html += '</div>';

            // Primary gauges row
            html += '<div class="grid-4">';

            // Battery gauge + battery graphic
            html += '<div class="stat-card">';
            html += App.gaugeHtml(batteryCharge, 100, 'Battery', '%', 'battery');
            html += '<div style="margin-top:8px">' + App.batteryHtml(batteryCharge) + '</div>';
            html += '</div>';

            // Load gauge
            html += '<div class="stat-card">';
            html += App.gaugeHtml(load, 100, 'Load', '%', 'load');
            html += '</div>';

            // Runtime
            html += '<div class="stat-card">';
            html += '<div class="stat-value">' + esc(App.formatRuntime(batteryRuntime)) + '</div>';
            html += '<div class="stat-label">Runtime</div>';
            html += '</div>';

            // Temperature
            html += '<div class="stat-card">';
            if (temp != null) {
                html += '<div class="stat-value">' + esc(temp) + '<span style="font-size:0.6em;color:var(--text-secondary)">&deg;C</span></div>';
            } else {
                html += '<div class="stat-value" style="color:var(--text-muted)">--</div>';
            }
            html += '<div class="stat-label">Temperature</div>';
            html += '</div>';

            html += '</div>'; // end grid-4

            // Voltage row
            html += '<div class="grid-3 mt-16">';

            html += '<div class="stat-card">';
            html += '<div class="stat-value">' + esc(inputV != null ? inputV : '--') + '<span style="font-size:0.6em;color:var(--text-secondary)">V</span></div>';
            html += '<div class="stat-label">Input Voltage</div>';
            html += '</div>';

            html += '<div class="stat-card">';
            html += '<div class="stat-value">' + esc(outputV != null ? outputV : '--') + '<span style="font-size:0.6em;color:var(--text-secondary)">V</span></div>';
            html += '<div class="stat-label">Output Voltage</div>';
            html += '</div>';

            html += '<div class="stat-card">';
            html += '<div class="stat-value">' + esc(batteryV != null ? batteryV : '--') + '<span style="font-size:0.6em;color:var(--text-secondary)">V</span></div>';
            html += '<div class="stat-label">Battery Voltage</div>';
            html += '</div>';

            html += '</div>'; // end grid-3
            html += '</div>'; // end card
        }

        return html;
    }

    App.registerPage('dashboard', render);
})();
