/* ============================================================
   commands.js — Commands page
   ============================================================ */

(function () {
    // Local state for loaded commands/rw vars per UPS
    var _commands = {};
    var _rwVars = {};

    function render() {
        const esc = App.escapeHtml.bind(App);
        const escAttr = App.escapeAttr.bind(App);
        const ups = App.state.ups;
        const names = Object.keys(ups);

        if (names.length === 0) {
            return '<div class="page-header"><h1 class="page-title">Commands</h1></div>' +
                '<div class="empty-state">' +
                '<div class="spinner"></div>' +
                '<div class="empty-state-text">Waiting for UPS data...</div>' +
                '</div>';
        }

        let html = '<div class="page-header"><h1 class="page-title">Commands</h1>' +
            '<p class="page-subtitle">Execute instant commands and set writable variables</p></div>';

        for (const name of names) {
            // Instant Commands card
            html += '<div class="card section">';
            html += '<div class="card-header">';
            html += '<div class="card-title">Instant Commands - ' + esc(name) + '</div>';
            html += '<button class="btn btn-ghost btn-sm" onclick="loadCommands(\'' + escAttr(name) + '\')">Load Commands</button>';
            html += '</div>';

            if (_commands[name] && _commands[name].length > 0) {
                html += '<div class="table-wrap"><table>';
                html += '<thead><tr><th>Command</th><th>Description</th><th></th></tr></thead>';
                html += '<tbody>';
                for (const cmd of _commands[name]) {
                    const desc = App.getDescription('commands', cmd);
                    html += '<tr>';
                    html += '<td class="mono">' + esc(cmd) + '</td>';
                    html += '<td class="text-muted" style="font-size:12px">' + esc(desc) + '</td>';
                    html += '<td style="width:60px;text-align:right"><button class="btn btn-ghost btn-sm" onclick="runCommand(\'' + escAttr(name) + '\', \'' + escAttr(cmd) + '\')">Run</button></td>';
                    html += '</tr>';
                }
                html += '</tbody></table></div>';
            } else if (_commands[name]) {
                html += '<div class="text-muted" style="padding:8px 0">No instant commands available</div>';
            } else {
                html += '<div class="text-muted" style="padding:8px 0">Click "Load Commands" to fetch available commands</div>';
            }

            html += '</div>'; // end commands card

            // Writable Variables card
            html += '<div class="card section">';
            html += '<div class="card-header">';
            html += '<div class="card-title">Writable Variables - ' + esc(name) + '</div>';
            html += '<button class="btn btn-ghost btn-sm" onclick="loadRwVars(\'' + escAttr(name) + '\')">Load Writable Vars</button>';
            html += '</div>';

            if (_rwVars[name] && Object.keys(_rwVars[name]).length > 0) {
                html += '<div class="table-wrap"><table>';
                html += '<thead><tr><th>Variable</th><th>Description</th><th>Current</th><th>New Value</th><th></th></tr></thead>';
                html += '<tbody>';
                const rwKeys = Object.keys(_rwVars[name]).sort();
                for (const vn of rwKeys) {
                    const currentVal = _rwVars[name][vn];
                    const desc = App.getDescription('variables', vn);
                    html += '<tr>';
                    html += '<td class="mono">' + esc(vn) + '</td>';
                    html += '<td class="text-muted" style="font-size:12px">' + esc(desc) + '</td>';
                    html += '<td class="mono">' + esc(currentVal) + '</td>';
                    html += '<td><input class="input" type="text" id="rw-' + esc(name) + '-' + esc(vn) + '" value="' + esc(currentVal) + '" style="max-width:160px"></td>';
                    html += '<td style="width:60px"><button class="btn btn-primary btn-sm" onclick="setVariable(\'' + escAttr(name) + '\', \'' + escAttr(vn) + '\')">Set</button></td>';
                    html += '</tr>';
                }
                html += '</tbody></table></div>';
            } else if (_rwVars[name]) {
                html += '<div class="text-muted" style="padding:8px 0">No writable variables available</div>';
            } else {
                html += '<div class="text-muted" style="padding:8px 0">Click "Load Writable Vars" to fetch writable variables</div>';
            }

            html += '</div>'; // end rw card
        }

        return html;
    }

    App.registerPage('commands', render);

    // Expose functions globally for onclick handlers
    window.loadCommands = function (upsName) {
        App.api('/api/ups/' + encodeURIComponent(upsName) + '/commands')
            .then(function (cmds) {
                _commands[upsName] = cmds;
                App.refresh();
                App.toast('Commands loaded', 'success');
            })
            .catch(function (err) {
                App.toast('Failed to load commands: ' + err.message, 'error');
            });
    };

    window.runCommand = function (upsName, cmd) {
        if (!confirm('Run command "' + cmd + '" on ' + upsName + '?')) return;
        App.api('/api/ups/' + encodeURIComponent(upsName) + '/command', {
            method: 'POST',
            body: { command: cmd },
        })
            .then(function () {
                App.toast('Command "' + cmd + '" executed', 'success');
            })
            .catch(function (err) {
                App.toast('Command failed: ' + err.message, 'error');
            });
    };

    window.loadRwVars = function (upsName) {
        App.api('/api/ups/' + encodeURIComponent(upsName) + '/rw')
            .then(function (vars) {
                _rwVars[upsName] = vars;
                App.refresh();
                App.toast('Writable variables loaded', 'success');
            })
            .catch(function (err) {
                App.toast('Failed to load writable variables: ' + err.message, 'error');
            });
    };

    window.setVariable = function (upsName, varName) {
        const inputId = 'rw-' + upsName + '-' + varName;
        const inputEl = document.getElementById(inputId);
        if (!inputEl) return;
        const newValue = inputEl.value;

        App.api('/api/ups/' + encodeURIComponent(upsName) + '/variable', {
            method: 'POST',
            body: { variable: varName, value: newValue },
        })
            .then(function () {
                App.toast('Variable "' + varName + '" updated', 'success');
                // Update local state
                if (_rwVars[upsName]) {
                    _rwVars[upsName][varName] = newValue;
                }
            })
            .catch(function (err) {
                App.toast('Failed to set variable: ' + err.message, 'error');
            });
    };
})();
