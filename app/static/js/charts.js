/*
 * Trekk Management App — Reusable Chart.js Components
 *
 * One shared dark theme + three chart factories (doughnut / bar / line), so a
 * dashboard never configures Chart.js directly — it declares what it wants.
 *
 * Data efficiency: TrekkCharts.mount() fetches its dashboard's analytics
 * endpoint EXACTLY ONCE and hands the payload to every chart on the page.
 * Individual charts never make their own requests.
 *
 * Usage:
 *     TrekkCharts.mount('/admin/api/analytics', function (data) {
 *         TrekkCharts.doughnut('bookingStatusChart', data.booking_status);
 *         TrekkCharts.line('revenueChart', data.monthly_revenue, { prefix: '₹' });
 *     });
 */
window.TrekkCharts = (function () {
    'use strict';

    // Palette drawn from the app's own design tokens.
    var PALETTE = ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#14b8a6', '#6366f1'];
    var GRID = 'rgba(255, 255, 255, 0.08)';
    var TICK = '#9ca3af';

    function applyTheme() {
        if (typeof Chart === 'undefined') return false;
        Chart.defaults.color = TICK;
        Chart.defaults.font.family = "'Inter', -apple-system, 'Segoe UI', sans-serif";
        Chart.defaults.font.size = 12;
        Chart.defaults.plugins.legend.labels.usePointStyle = true;
        Chart.defaults.plugins.legend.labels.boxWidth = 8;
        Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(17, 24, 39, 0.95)';
        Chart.defaults.plugins.tooltip.borderColor = GRID;
        Chart.defaults.plugins.tooltip.borderWidth = 1;
        Chart.defaults.plugins.tooltip.padding = 10;
        Chart.defaults.maintainAspectRatio = false;   // fill the card, stay responsive
        Chart.defaults.responsive = true;
        return true;
    }

    /* A series with no data at all should say so, not render an empty axis. */
    function isEmpty(series) {
        if (!series || !series.data || !series.data.length) return true;
        return series.data.every(function (v) { return !v; });
    }

    function showEmpty(canvas, message) {
        var note = document.createElement('p');
        note.className = 'chart-empty';
        note.textContent = message || 'No data yet.';
        canvas.replaceWith(note);
    }

    function prepare(canvasId, series) {
        var canvas = document.getElementById(canvasId);
        if (!canvas) return null;                       // chart not on this page
        if (isEmpty(series)) {
            showEmpty(canvas, canvas.dataset.empty);
            return null;
        }
        return canvas;
    }

    function formatNumber(prefix) {
        return function (value) {
            return (prefix || '') + Number(value).toLocaleString('en-IN');
        };
    }

    function axes(prefix) {
        return {
            x: { grid: { display: false }, ticks: { color: TICK } },
            y: {
                beginAtZero: true,
                grid: { color: GRID },
                ticks: { color: TICK, precision: 0, callback: formatNumber(prefix) }
            }
        };
    }

    function tooltip(prefix) {
        return {
            callbacks: {
                label: function (ctx) {
                    var v = ctx.parsed.y !== undefined ? ctx.parsed.y : ctx.parsed;
                    return ' ' + (prefix || '') + Number(v).toLocaleString('en-IN');
                }
            }
        };
    }

    // ── Factories ──────────────────────────────────────────────────────
    function doughnut(canvasId, series, opts) {
        opts = opts || {};
        var canvas = prepare(canvasId, series);
        if (!canvas) return null;

        return new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: series.labels,
                datasets: [{
                    data: series.data,
                    backgroundColor: PALETTE,
                    borderColor: 'rgba(10, 14, 23, 0.9)',
                    borderWidth: 2,
                    hoverOffset: 6
                }]
            },
            options: {
                cutout: '62%',
                plugins: {
                    legend: { position: opts.legend || 'bottom' },
                    tooltip: tooltip(opts.prefix)
                }
            }
        });
    }

    function bar(canvasId, series, opts) {
        opts = opts || {};
        var canvas = prepare(canvasId, series);
        if (!canvas) return null;

        return new Chart(canvas, {
            type: 'bar',
            data: {
                labels: series.labels,
                datasets: [{
                    label: opts.label || 'Count',
                    data: series.data,
                    backgroundColor: opts.color || PALETTE[0],
                    borderRadius: 6,
                    maxBarThickness: 48
                }]
            },
            options: {
                indexAxis: opts.horizontal ? 'y' : 'x',
                plugins: {
                    legend: { display: false },
                    tooltip: tooltip(opts.prefix)
                },
                scales: opts.horizontal ? {
                    x: { beginAtZero: true, grid: { color: GRID },
                         ticks: { color: TICK, precision: 0 } },
                    y: { grid: { display: false }, ticks: { color: TICK } }
                } : axes(opts.prefix)
            }
        });
    }

    function line(canvasId, series, opts) {
        opts = opts || {};
        var canvas = prepare(canvasId, series);
        if (!canvas) return null;

        return new Chart(canvas, {
            type: 'line',
            data: {
                labels: series.labels,
                datasets: [{
                    label: opts.label || 'Value',
                    data: series.data,
                    borderColor: opts.color || PALETTE[0],
                    backgroundColor: 'rgba(16, 185, 129, 0.12)',
                    fill: true,
                    tension: 0.35,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: opts.color || PALETTE[0]
                }]
            },
            options: {
                plugins: {
                    legend: { display: false },
                    tooltip: tooltip(opts.prefix)
                },
                scales: axes(opts.prefix)
            }
        });
    }

    // ── Mount: one fetch per dashboard, shared by every chart ───────────
    function mount(url, build) {
        document.addEventListener('DOMContentLoaded', function () {
            if (!applyTheme()) {
                console.warn('TrekkCharts: Chart.js failed to load; skipping charts.');
                return;
            }

            fetch(url, { headers: { 'Accept': 'application/json' }, credentials: 'same-origin' })
                .then(function (res) {
                    if (!res.ok) throw new Error('Analytics request failed: ' + res.status);
                    return res.json();
                })
                .then(build)
                .catch(function (err) {
                    console.error(err);
                    document.querySelectorAll('.chart-canvas').forEach(function (c) {
                        showEmpty(c, 'Could not load chart data.');
                    });
                });
        });
    }

    return {
        mount: mount,
        doughnut: doughnut,
        bar: bar,
        line: line,
        palette: PALETTE
    };
})();
