/* ============================================================
   variables.js — Variable browser page
   ============================================================ */

(function () {
    function render() {
        const esc = App.escapeHtml.bind(App);
        const escAttr = App.escapeAttr.bind(App);
        const ups = App.state.ups;
        const names = Object.keys(ups);

        if (names.length === 0) {
            return '<div class="page-header"><h1 class="page-title">Variables</h1></div>' +
                '<div class="empty-state">' +
                '<div class="spinner"></div>' +
                '<div class="empty-state-text">Waiting for UPS data...</div>' +
                '</div>';
        }

        let html = '<div class="page-header"><h1 class="page-title">Variables</h1>' +
            '<p class="page-subtitle">Raw NUT variable data for each UPS</p></div>';

        for (const name of names) {
            const u = ups[name];
            const vars = u.variables || {};
            const varNames = Object.keys(vars).sort();

            html += '<div class="card section">';
            html += '<div class="card-header">';
            html += '<div class="card-title">' + esc(name) + '</div>';
            html += '<button class="btn btn-ghost btn-sm" onclick="refreshVars(\'' + escAttr(name) + '\')">Refresh</button>';
            html += '</div>';

            if (varNames.length === 0) {
                html += '<div class="text-muted text-center" style="padding:20px">No variables available</div>';
            } else {
                // Group by prefix
                const groups = {};
                for (const vn of varNames) {
                    const prefix = vn.split('.').slice(0, -1).join('.') || 'other';
                    if (!groups[prefix]) groups[prefix] = [];
                    groups[prefix].push(vn);
                }

                html += '<div class="table-wrap"><table>';
                html += '<thead><tr><th>Variable</th><th>Value</th><th></th></tr></thead>';
                html += '<tbody>';

                const groupKeys = Object.keys(groups).sort();
                for (const gk of groupKeys) {
                    html += '<tr class="group-header"><td colspan="3">' + esc(gk) + '.*</td></tr>';
                    for (const vn of groups[gk]) {
                        const val = vars[vn];
                        html += '<tr>';
                        html += '<td class="mono">' + esc(vn) + '</td>';
                        html += '<td class="mono">' + esc(val) + '</td>';
                        html += '<td style="width:60px;text-align:right">' +
                            '<button class="btn btn-ghost btn-sm" onclick="App.copyToClipboard(\'' + escAttr(val) + '\')">Copy</button>' +
                            '</td>';
                        html += '</tr>';
                    }
                }

                html += '</tbody></table></div>';
            }

            html += '</div>'; // end card
        }

        return html;
    }

    App.registerPage('variables', render);
})();

// Global function for refresh button
function refreshVars(upsName) {
    App.api('/api/ups/' + encodeURIComponent(upsName) + '/variables')
        .then(function (vars) {
            if (App.state.ups[upsName]) {
                App.state.ups[upsName].variables = vars;
            }
            App.refresh();
            App.toast('Variables refreshed', 'success');
        })
        .catch(function (err) {
            App.toast('Failed to refresh: ' + err.message, 'error');
        });
}
