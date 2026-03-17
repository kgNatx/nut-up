/* ============================================================
   enrollment.js — Enrollment management page
   ============================================================ */

(function () {
    var _keys = [];
    var _clients = [];
    var _createdKey = null;
    var _curlCmd = null;

    function render() {
        const esc = App.escapeHtml.bind(App);
        const escAttr = App.escapeAttr.bind(App);

        let html = '<div class="page-header"><h1 class="page-title">Enrollment</h1>' +
            '<p class="page-subtitle">Generate enrollment keys for one-command client setup</p></div>';

        // Create Key form
        html += '<div class="card section">';
        html += '<div class="card-header"><div class="card-title">Create Enrollment Key</div></div>';
        html += '<div class="grid-3" style="align-items:end">';
        html += '<div class="form-group">';
        html += '<label class="form-label" for="key-label">Label</label>';
        html += '<input class="input" type="text" id="key-label" placeholder="e.g. Proxmox node 1">';
        html += '</div>';
        html += '<div class="form-group">';
        html += '<label class="form-label" for="key-expiry">Expiry</label>';
        html += '<select class="input" id="key-expiry">';
        html += '<option value="0.1667">10 minutes</option>';
        html += '<option value="1">1 hour</option>';
        html += '<option value="24" selected>24 hours</option>';
        html += '<option value="168">7 days</option>';
        html += '</select>';
        html += '</div>';
        html += '<div class="form-group">';
        html += '<button class="btn btn-primary" onclick="createEnrollmentKey()">Create Key</button>';
        html += '</div>';
        html += '</div>';

        // Show created key banner
        if (_createdKey) {
            const setupUrl = window.location.origin + '/setup?key=' + encodeURIComponent(_createdKey);
            _curlCmd = 'curl -sL "' + setupUrl + '" | sudo bash';
            html += '<div class="banner mt-16">';
            html += '<div class="banner-title">Enrollment Key Created</div>';
            html += '<p style="margin-bottom:8px;color:var(--text-secondary)">Run this on the client machine:</p>';
            html += '<div class="code-block">' + esc(_curlCmd);
            html += '<button class="copy-btn" onclick="copyCurlCmd()">Copy</button>';
            html += '</div>';
            html += '</div>';
        }

        html += '</div>'; // end create key card

        // Active Keys table
        html += '<div class="card section">';
        html += '<div class="card-header"><div class="card-title">Active Keys</div></div>';

        if (_keys.length === 0) {
            html += '<div class="text-muted text-center" style="padding:20px">No enrollment keys</div>';
        } else {
            html += '<div class="table-wrap"><table>';
            html += '<thead><tr><th>Key</th><th>Label</th><th>Created</th><th>Expires</th><th>Status</th><th></th></tr></thead>';
            html += '<tbody>';
            for (const k of _keys) {
                const keyTrunc = k.key ? k.key.substring(0, 12) + '...' : '--';
                const isExpired = k.expires_at && new Date(k.expires_at) < new Date();
                const isRevoked = k.revoked;
                let statusHtml;
                if (isRevoked) {
                    statusHtml = '<span class="badge badge-danger">Revoked</span>';
                } else if (isExpired) {
                    statusHtml = '<span class="badge badge-warn">Expired</span>';
                } else {
                    statusHtml = '<span class="badge badge-ok">Active</span>';
                }

                html += '<tr>';
                html += '<td class="mono">' + esc(keyTrunc) + '</td>';
                html += '<td>' + esc(k.label || '') + '</td>';
                html += '<td>' + esc(k.created_at ? new Date(k.created_at).toLocaleString() : '--') + '</td>';
                html += '<td>' + esc(k.expires_at ? new Date(k.expires_at).toLocaleString() : '--') + '</td>';
                html += '<td>' + statusHtml + '</td>';
                html += '<td style="width:80px;text-align:right">';
                if (!isRevoked) {
                    html += '<button class="btn btn-danger btn-sm" onclick="revokeKey(\'' + escAttr(k.key) + '\')">Revoke</button>';
                }
                html += '</td>';
                html += '</tr>';
            }
            html += '</tbody></table></div>';
        }

        html += '</div>'; // end keys card

        // Enrolled Clients table
        html += '<div class="card section">';
        html += '<div class="card-header"><div class="card-title">Enrolled Clients</div></div>';

        if (_clients.length === 0) {
            html += '<div class="text-muted text-center" style="padding:20px">No enrolled clients</div>';
        } else {
            html += '<div class="table-wrap"><table>';
            html += '<thead><tr><th>Hostname</th><th>IP Address</th><th>Enrolled</th></tr></thead>';
            html += '<tbody>';
            for (const c of _clients) {
                html += '<tr>';
                html += '<td class="mono">' + esc(c.hostname || '') + '</td>';
                html += '<td class="mono">' + esc(c.ip || '') + '</td>';
                html += '<td>' + esc(c.enrolled_at ? new Date(c.enrolled_at).toLocaleString() : '--') + '</td>';
                html += '</tr>';
            }
            html += '</tbody></table></div>';
        }

        html += '</div>'; // end clients card

        return html;
    }

    function init() {
        // Auto-load keys and clients
        App.api('/api/keys')
            .then(function (keys) {
                _keys = keys;
                App.refresh();
            })
            .catch(function (err) {
                App.toast('Failed to load keys: ' + err.message, 'error');
            });

        App.api('/api/clients')
            .then(function (clients) {
                _clients = clients;
                App.refresh();
            })
            .catch(function (err) {
                App.toast('Failed to load clients: ' + err.message, 'error');
            });
    }

    App.registerPage('enrollment', render, init);

    // Global functions for onclick handlers
    window.copyCurlCmd = function () {
        if (_curlCmd) App.copyToClipboard(_curlCmd);
    };

    window.createEnrollmentKey = function () {
        const labelEl = document.getElementById('key-label');
        const expiryEl = document.getElementById('key-expiry');
        if (!labelEl || !expiryEl) return;

        const label = labelEl.value.trim();
        if (!label) {
            App.toast('Please enter a label', 'warning');
            return;
        }

        const hours = parseFloat(expiryEl.value);

        App.api('/api/keys', {
            method: 'POST',
            body: { label: label, hours: hours },
        })
            .then(function (result) {
                _createdKey = result.key;
                App.toast('Enrollment key created', 'success');
                // Reload keys list
                return App.api('/api/keys');
            })
            .then(function (keys) {
                _keys = keys;
                App.refresh();
            })
            .catch(function (err) {
                App.toast('Failed to create key: ' + err.message, 'error');
            });
    };

    window.revokeKey = function (key) {
        if (!confirm('Revoke this enrollment key?')) return;
        App.api('/api/keys/' + encodeURIComponent(key), { method: 'DELETE' })
            .then(function () {
                App.toast('Key revoked', 'success');
                return App.api('/api/keys');
            })
            .then(function (keys) {
                _keys = keys;
                App.refresh();
            })
            .catch(function (err) {
                App.toast('Failed to revoke key: ' + err.message, 'error');
            });
    };
})();
