/* ============================================================
   manual.js — Manual setup page
   ============================================================ */

(function () {
    var _setupData = null;

    function render() {
        const esc = App.escapeHtml.bind(App);
        const escAttr = App.escapeAttr.bind(App);

        let html = '<div class="page-header"><h1 class="page-title">Manual Setup</h1>' +
            '<p class="page-subtitle">Connection details for manually configuring NUT clients</p></div>';

        html += '<div class="card section">';
        html += '<div class="card-header">';
        html += '<div class="card-title">Connection Details</div>';
        html += '<button class="btn btn-ghost btn-sm" onclick="loadManualSetup()">Refresh</button>';
        html += '</div>';

        if (!_setupData) {
            html += '<div class="empty-state" style="padding:40px"><div class="spinner"></div>' +
                '<div class="empty-state-text">Loading setup information...</div></div>';
        } else {
            // Connection detail fields (2-column grid)
            html += '<div class="grid-2">';

            html += renderField('UPS Name', _setupData.ups_name || '--');
            html += renderField('Server Address', _setupData.server_host || '--');
            html += renderField('Server Port', String(_setupData.server_port || 3493));
            html += renderField('Username', _setupData.monitor_user || '--');
            html += renderField('Password', _setupData.monitor_password || '--');
            html += renderField('Monitor Mode', 'secondary');

            html += '</div>'; // end grid-2

            // MONITOR line
            const monitorLine = 'MONITOR ' +
                (_setupData.ups_name || 'ups') + '@' +
                (_setupData.server_host || 'localhost') + ':' +
                (_setupData.server_port || 3493) + ' 1 ' +
                (_setupData.monitor_user || 'upsmon_secondary') + ' ' +
                (_setupData.monitor_password || '') + ' secondary';

            html += '<div class="mt-24">';
            html += '<div class="form-label" style="margin-bottom:8px">upsmon.conf MONITOR Line</div>';
            html += '<div class="code-block">' + esc(monitorLine);
            html += '<button class="copy-btn" onclick="App.copyToClipboard(\'' + escAttr(monitorLine) + '\')">Copy</button>';
            html += '</div>';
            html += '</div>';
        }

        html += '</div>'; // end connection card

        // Quick Reference card
        html += '<div class="card section">';
        html += '<div class="card-header"><div class="card-title">Quick Reference</div></div>';
        html += '<div class="table-wrap"><table>';
        html += '<thead><tr><th>Platform</th><th>Where to Configure</th></tr></thead>';
        html += '<tbody>';
        html += '<tr><td>OPNsense</td><td>Services &gt; NUT &gt; Client</td></tr>';
        html += '<tr><td>Synology</td><td>Control Panel &gt; Hardware &amp; Power &gt; UPS</td></tr>';
        html += '<tr><td>TrueNAS</td><td>Services &gt; UPS</td></tr>';
        html += '<tr><td>Proxmox</td><td>Use enrollment script (recommended) or manual <span class="mono">upsmon.conf</span></td></tr>';
        html += '</tbody></table></div>';
        html += '</div>'; // end quick reference card

        return html;
    }

    function renderField(label, value) {
        const esc = App.escapeHtml.bind(App);
        const escAttr = App.escapeAttr.bind(App);
        return '<div class="form-group">' +
            '<label class="form-label">' + esc(label) + '</label>' +
            '<div class="input-with-copy">' +
            '<input class="input readonly" type="text" value="' + escAttr(value) + '" readonly>' +
            '<button class="btn btn-ghost btn-sm" onclick="App.copyToClipboard(\'' + escAttr(value) + '\')">Copy</button>' +
            '</div></div>';
    }

    function init() {
        loadManualSetup();
    }

    App.registerPage('manual', render, init);

    window.loadManualSetup = function () {
        App.api('/api/manual-setup')
            .then(function (data) {
                _setupData = data;
                App.refresh();
            })
            .catch(function (err) {
                App.toast('Failed to load setup info: ' + err.message, 'error');
            });
    };
})();
