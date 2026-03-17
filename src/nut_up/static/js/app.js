/* ============================================================
   app.js — SPA Core for nut-up
   ============================================================

   XSS Protection: All dynamic values rendered into HTML MUST
   pass through App.escapeHtml() before interpolation. This is
   the primary defense against injection in this SPA.
   ============================================================ */

const App = {
    state: {
        ups: {},
        connected: false,
    },

    _pages: {},
    _initFns: {},
    _currentPage: null,
    _ws: null,
    _wsReconnectTimer: null,

    // ----------------------------------------------------------
    // Security: HTML escaping — prevents XSS by encoding all
    // HTML-special characters in dynamic values.
    // ----------------------------------------------------------
    escapeHtml(str) {
        const el = document.createElement('div');
        el.textContent = String(str ?? '');
        return el.innerHTML;
    },

    /**
     * Escape a string for safe use inside a single-quoted HTML attribute.
     * escapeHtml does NOT encode single quotes, so this adds that.
     */
    escapeAttr(str) {
        return this.escapeHtml(str).replace(/'/g, '&#39;');
    },

    // ----------------------------------------------------------
    // Router
    // ----------------------------------------------------------
    registerPage(name, renderFn, initFn) {
        this._pages[name] = renderFn;
        if (initFn) {
            this._initFns[name] = initFn;
        }
    },

    setupRouter() {
        window.addEventListener('hashchange', () => this._onRouteChange());

        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                const href = link.getAttribute('href');
                if (href && href.startsWith('#')) {
                    // Let hashchange handle it
                }
            });
        });
    },

    navigate(hash) {
        window.location.hash = hash;
    },

    _onRouteChange() {
        const hash = window.location.hash || '#/';
        const path = hash.replace('#/', '').replace('#', '') || 'dashboard';

        // Map routes to page names
        const pageMap = {
            '': 'dashboard',
            'dashboard': 'dashboard',
            'variables': 'variables',
            'commands': 'commands',
            'enrollment': 'enrollment',
            'manual': 'manual',
        };

        const pageName = pageMap[path] || 'dashboard';
        this._renderPage(pageName);
    },

    _renderPage(pageName) {
        this._currentPage = pageName;

        // Update nav active state
        document.querySelectorAll('.nav-link').forEach(link => {
            const page = link.getAttribute('data-page');
            link.classList.toggle('active', page === pageName);
        });

        // Render page content — page renderers return pre-escaped
        // HTML strings where all dynamic values have been passed
        // through escapeHtml().
        const content = document.getElementById('content');
        const renderFn = this._pages[pageName];
        if (renderFn) {
            content.innerHTML = renderFn();
        } else {
            content.innerHTML = '<div class="empty-state"><div class="empty-state-text">Page not found</div></div>';
        }

        // Call init function if registered
        const initFn = this._initFns[pageName];
        if (initFn) {
            initFn();
        }
    },

    refresh() {
        if (this._currentPage && this._pages[this._currentPage]) {
            this._renderPage(this._currentPage);
        }
    },

    // ----------------------------------------------------------
    // WebSocket
    // ----------------------------------------------------------
    connectWebSocket() {
        if (this._ws) {
            try { this._ws.close(); } catch (e) { /* ignore */ }
        }

        this.setConnectionStatus('connecting');

        const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = proto + '//' + window.location.host + '/ws';

        try {
            this._ws = new WebSocket(url);
        } catch (e) {
            this.setConnectionStatus('disconnected');
            this._scheduleReconnect();
            return;
        }

        this._ws.onopen = () => {
            this.setConnectionStatus('connected');
            this.state.connected = true;
        };

        this._ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === 'ups_data') {
                    this.state.ups = msg.data || {};
                    this.refresh();
                } else if (msg.type === 'error') {
                    this.setConnectionStatus('disconnected');
                }
            } catch (e) {
                console.error('WebSocket message parse error:', e);
            }
        };

        this._ws.onclose = () => {
            this.state.connected = false;
            this.setConnectionStatus('disconnected');
            this._scheduleReconnect();
        };

        this._ws.onerror = () => {
            this.state.connected = false;
            this.setConnectionStatus('disconnected');
        };
    },

    _scheduleReconnect() {
        if (this._wsReconnectTimer) clearTimeout(this._wsReconnectTimer);
        this._wsReconnectTimer = setTimeout(() => this.connectWebSocket(), 3000);
    },

    setConnectionStatus(status) {
        const container = document.getElementById('connection-status');
        if (!container) return;

        const dot = container.querySelector('.status-dot');
        const text = container.querySelector('.status-text');

        dot.className = 'status-dot ' + status;

        const labels = {
            connected: 'Connected',
            disconnected: 'Disconnected',
            connecting: 'Connecting...',
        };
        text.textContent = labels[status] || status;
    },

    // ----------------------------------------------------------
    // API helper
    // ----------------------------------------------------------
    async api(path, options = {}) {
        const url = path.startsWith('/') ? path : '/' + path;
        const defaults = {
            headers: { 'Content-Type': 'application/json' },
        };
        const opts = { ...defaults, ...options };
        if (opts.body && typeof opts.body === 'object') {
            opts.body = JSON.stringify(opts.body);
        }

        const response = await fetch(url, opts);
        if (!response.ok) {
            let detail = 'HTTP ' + response.status;
            try {
                const err = await response.json();
                if (err.detail) detail = err.detail;
            } catch (e) { /* ignore */ }
            throw new Error(detail);
        }
        return response.json();
    },

    // ----------------------------------------------------------
    // Toast notifications
    // ----------------------------------------------------------
    toast(message, type) {
        type = type || 'info';
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = 'toast toast-' + type;
        toast.textContent = message;
        container.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('fade-out');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },

    // ----------------------------------------------------------
    // Formatting helpers
    // ----------------------------------------------------------
    formatRuntime(seconds) {
        const s = parseInt(seconds, 10);
        if (isNaN(s) || s < 0) return '--';
        const h = Math.floor(s / 3600);
        const m = Math.floor((s % 3600) / 60);
        if (h > 0) return h + 'h ' + m + 'm';
        return m + 'm';
    },

    /**
     * Renders a circular SVG gauge.
     * @param {*} value - Current value
     * @param {*} max - Maximum value
     * @param {string} label - Label below gauge
     * @param {string} unit - Unit text inside gauge
     * @param {string} mode - 'battery' or 'load' for color thresholds
     */
    gaugeHtml(value, max, label, unit, mode) {
        const esc = this.escapeHtml.bind(this);
        const numVal = parseFloat(value);
        const numMax = parseFloat(max);
        if (isNaN(numVal) || isNaN(numMax) || numMax === 0) {
            return '<div class="gauge-container">' +
                '<svg class="gauge-svg" width="120" height="120" viewBox="0 0 120 120">' +
                '<circle class="gauge-track" cx="60" cy="60" r="50"/>' +
                '<g class="gauge-text-group">' +
                '<text class="gauge-value-text" x="60" y="60">--</text>' +
                '</g>' +
                '</svg>' +
                '<div class="gauge-label">' + esc(label) + '</div>' +
                '</div>';
        }

        const pct = Math.min(Math.max(numVal / numMax, 0), 1);
        const circumference = 2 * Math.PI * 50;
        const offset = circumference * (1 - pct);

        // Determine color based on mode
        let color = 'var(--accent)';
        if (mode === 'battery') {
            if (pct < 0.3) color = 'var(--danger)';
            else if (pct < 0.6) color = 'var(--warning)';
        } else if (mode === 'load') {
            if (pct > 0.8) color = 'var(--danger)';
            else if (pct > 0.6) color = 'var(--warning)';
        }

        return '<div class="gauge-container">' +
            '<svg class="gauge-svg" width="120" height="120" viewBox="0 0 120 120">' +
            '<circle class="gauge-track" cx="60" cy="60" r="50"/>' +
            '<circle class="gauge-fill" cx="60" cy="60" r="50" ' +
            'stroke="' + color + '" ' +
            'stroke-dasharray="' + circumference.toFixed(2) + '" ' +
            'stroke-dashoffset="' + offset.toFixed(2) + '"/>' +
            '<g class="gauge-text-group">' +
            '<text class="gauge-value-text" x="60" y="56">' + esc(Math.round(numVal)) + '</text>' +
            '<text class="gauge-unit-text" x="60" y="72">' + esc(unit) + '</text>' +
            '</g>' +
            '</svg>' +
            '<div class="gauge-label">' + esc(label) + '</div>' +
            '</div>';
    },

    /**
     * Renders a CSS battery graphic.
     * @param {*} charge - Battery charge percentage
     */
    batteryHtml(charge) {
        const pct = parseFloat(charge);
        if (isNaN(pct)) {
            return '<div class="battery">' +
                '<div class="battery-body"><div class="battery-fill" style="width:0%"></div></div>' +
                '<div class="battery-tip"></div></div>';
        }
        let cls = 'high';
        if (pct < 30) cls = 'low';
        else if (pct < 60) cls = 'medium';

        const clampedPct = Math.min(Math.max(pct, 0), 100);

        return '<div class="battery ' + cls + '">' +
            '<div class="battery-body"><div class="battery-fill" style="width:' + clampedPct + '%"></div></div>' +
            '<div class="battery-tip"></div></div>';
    },

    /**
     * Renders a status badge based on UPS status tokens.
     * @param {string} status - UPS status string (e.g. "OL", "OB LB")
     */
    statusBadge(status) {
        const esc = this.escapeHtml.bind(this);
        if (!status || status === 'unknown') {
            return '<span class="badge badge-info">' + esc(status || 'Unknown') + '</span>';
        }

        const tokens = status.split(/\s+/);
        const hasOB = tokens.includes('OB');
        const hasLB = tokens.includes('LB');
        const hasOL = tokens.includes('OL');
        const hasOFF = tokens.includes('OFF');

        if (hasOB && hasLB) {
            return '<span class="badge badge-danger">LOW BATTERY</span>';
        }
        if (hasOB) {
            return '<span class="badge badge-warn">On Battery</span>';
        }
        if (hasOFF) {
            return '<span class="badge badge-danger">Offline</span>';
        }
        if (hasOL) {
            return '<span class="badge badge-ok">Online</span>';
        }
        return '<span class="badge badge-info">' + esc(status) + '</span>';
    },

    /**
     * Copies text to clipboard with toast feedback.
     * @param {string} text - Text to copy
     */
    copyToClipboard(text) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(() => {
                this.toast('Copied to clipboard', 'success');
            }).catch(() => {
                this.toast('Failed to copy', 'error');
            });
        } else {
            // Fallback for older browsers / non-HTTPS
            const ta = document.createElement('textarea');
            ta.value = text;
            ta.style.position = 'fixed';
            ta.style.left = '-9999px';
            document.body.appendChild(ta);
            ta.select();
            try {
                document.execCommand('copy');
                this.toast('Copied to clipboard', 'success');
            } catch (e) {
                this.toast('Failed to copy', 'error');
            }
            document.body.removeChild(ta);
        }
    },

    // ----------------------------------------------------------
    // Init
    // ----------------------------------------------------------
    init() {
        this.setupRouter();
        this.connectWebSocket();
        this._onRouteChange();
    },
};

document.addEventListener('DOMContentLoaded', () => App.init());
