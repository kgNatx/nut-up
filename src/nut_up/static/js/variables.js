/* ============================================================
   variables.js — Variable browser page
   ============================================================ */

(function () {
    // Cache of writable variable names per UPS (loaded once)
    var _rwVars = {};

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
            '<p class="page-subtitle">NUT variable data — writable variables can be edited inline</p></div>';

        for (const name of names) {
            const u = ups[name];
            const vars = u.variables || {};
            const rw = _rwVars[name] || {};
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
                html += '<thead><tr><th>Variable</th><th>Value</th><th>Description</th><th></th></tr></thead>';
                html += '<tbody>';

                const groupKeys = Object.keys(groups).sort();
                for (const gk of groupKeys) {
                    html += '<tr class="group-header"><td colspan="4">' + esc(gk) + '.*</td></tr>';
                    for (const vn of groups[gk]) {
                        const val = vars[vn];
                        const desc = App.getDescription('variables', vn);
                        const isWritable = vn in rw;

                        html += '<tr>';
                        html += '<td class="mono">' + esc(vn);
                        if (isWritable) html += ' <span class="badge badge-info" style="font-size:9px;padding:1px 5px">RW</span>';
                        html += '</td>';

                        if (isWritable) {
                            // Editable field
                            html += '<td><input class="input" type="text" id="var-' + escAttr(name) + '-' + escAttr(vn) + '" value="' + escAttr(val) + '" style="max-width:160px;font-family:var(--font-mono);font-size:13px"></td>';
                        } else {
                            html += '<td class="mono">' + esc(val) + '</td>';
                        }

                        html += '<td class="text-muted" style="font-size:12px">' + esc(desc) + '</td>';

                        html += '<td style="width:80px;text-align:right">';
                        if (isWritable) {
                            html += '<button class="btn btn-primary btn-sm" onclick="saveVar(\'' + escAttr(name) + '\', \'' + escAttr(vn) + '\')">Set</button>';
                        } else {
                            html += '<button class="btn btn-ghost btn-sm" onclick="App.copyToClipboard(\'' + escAttr(val) + '\')">Copy</button>';
                        }
                        html += '</td>';
                        html += '</tr>';
                    }
                }

                html += '</tbody></table></div>';
            }

            html += '</div>'; // end card
        }

        return html;
    }

    function init() {
        // Load writable variable names for each UPS (once)
        const names = Object.keys(App.state.ups);
        for (const name of names) {
            if (_rwVars[name]) continue; // already loaded
            App.api('/api/ups/' + encodeURIComponent(name) + '/rw')
                .then(function (vars) {
                    _rwVars[name] = vars;
                    App.refresh();
                })
                .catch(function () {
                    _rwVars[name] = {}; // mark as loaded (empty)
                });
        }
    }

    App.registerPage('variables', render, init);

    window.refreshVars = function (upsName) {
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
    };

    window.saveVar = function (upsName, varName) {
        var inputEl = document.getElementById('var-' + upsName + '-' + varName);
        if (!inputEl) return;
        var newValue = inputEl.value;

        App.api('/api/ups/' + encodeURIComponent(upsName) + '/variable', {
            method: 'POST',
            body: { variable: varName, value: newValue },
        })
            .then(function () {
                App.toast(varName + ' updated', 'success');
                // Update local state
                if (App.state.ups[upsName] && App.state.ups[upsName].variables) {
                    App.state.ups[upsName].variables[varName] = newValue;
                }
                if (_rwVars[upsName]) {
                    _rwVars[upsName][varName] = newValue;
                }
            })
            .catch(function (err) {
                App.toast('Failed to set ' + varName + ': ' + err.message, 'error');
            });
    };
})();
