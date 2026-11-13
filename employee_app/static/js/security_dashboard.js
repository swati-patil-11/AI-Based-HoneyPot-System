/**
 * Security & Honeypot Admin Dashboard (Phase 12).
 * Handles live telemetry, WebSocket feeds, Chart.js graphs, and admin controls.
 */

document.addEventListener("DOMContentLoaded", function () {
    const token = localStorage.getItem("access_token");
    const role = localStorage.getItem("role");

    // Enforce Admin Authentication
    if (!token) {
        window.location.href = "/";
        return;
    }
    if (role !== "admin") {
        window.location.href = "/dashboard";
        return;
    }

    // State
    let isStreamPaused = false;
    let websocket = null;
    let pingInterval = null;
    let blocksData = [];
    let sysChart = null;
    let rpsChart = null;

    // Elements
    const wsDot = document.getElementById("wsDot");
    const wsStatusText = document.getElementById("wsStatusText");
    const statActiveTraps = document.getElementById("statActiveTraps");
    const statTokensServed = document.getElementById("statTokensServed");
    const statActiveBlocks = document.getElementById("statActiveBlocks");
    const statCpuMem = document.getElementById("statCpuMem");
    const statRps = document.getElementById("statRps");

    const scoresTableBody = document.getElementById("scoresTableBody");
    const trapSessionsTableBody = document.getElementById("trapSessionsTableBody");
    const blocksTableBody = document.getElementById("blocksTableBody");
    const liveLogTableBody = document.getElementById("liveLogTableBody");

    const btnResetTrap = document.getElementById("btnResetTrap");
    const btnResetScores = document.getElementById("btnResetScores");
    const btnTogglePause = document.getElementById("btnTogglePause");
    const btnClearLogView = document.getElementById("btnClearLogView");
    const manualBlockForm = document.getElementById("manualBlockForm");

    // Initialize Chart.js graphs
    initCharts();

    // Load initial REST data
    loadInitialData();

    // Start WebSocket live connection
    connectWebSocket();

    // Start 1-second countdown interval for active blocks
    setInterval(updateBlockCountdowns, 1000);

    // -------------------------------------------------------------
    // Charts Setup
    // -------------------------------------------------------------
    function initCharts() {
        const sysCtx = document.getElementById("sysMetricsChart")?.getContext("2d");
        const rpsCtx = document.getElementById("rpsChart")?.getContext("2d");

        if (sysCtx) {
            sysChart = new Chart(sysCtx, {
                type: "line",
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: "CPU Usage (%)",
                            data: [],
                            borderColor: "#ef4444",
                            backgroundColor: "rgba(239, 68, 68, 0.1)",
                            tension: 0.3,
                            fill: true,
                        },
                        {
                            label: "Memory Usage (%)",
                            data: [],
                            borderColor: "#3b82f6",
                            backgroundColor: "rgba(59, 130, 246, 0.1)",
                            tension: 0.3,
                            fill: true,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { min: 0, max: 100 },
                    },
                    plugins: {
                        legend: { position: "top", labels: { boxWidth: 12 } },
                    },
                },
            });
        }

        if (rpsCtx) {
            rpsChart = new Chart(rpsCtx, {
                type: "line",
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: "Requests / Sec",
                            data: [],
                            borderColor: "#10b981",
                            backgroundColor: "rgba(16, 185, 129, 0.15)",
                            tension: 0.2,
                            fill: true,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { min: 0, suggestedMax: 10 },
                    },
                    plugins: {
                        legend: { position: "top", labels: { boxWidth: 12 } },
                    },
                },
            });
        }
    }

    function pushMetricsToCharts(timeLabel, cpu, mem, rps) {
        if (sysChart) {
            if (sysChart.data.labels.length > 20) {
                sysChart.data.labels.shift();
                sysChart.data.datasets[0].data.shift();
                sysChart.data.datasets[1].data.shift();
            }
            sysChart.data.labels.push(timeLabel);
            sysChart.data.datasets[0].data.push(cpu);
            sysChart.data.datasets[1].data.push(mem);
            sysChart.update("none");
        }

        if (rpsChart) {
            if (rpsChart.data.labels.length > 20) {
                rpsChart.data.labels.shift();
                rpsChart.data.datasets[0].data.shift();
            }
            rpsChart.data.labels.push(timeLabel);
            rpsChart.data.datasets[0].data.push(rps);
            rpsChart.update("none");
        }
    }

    // -------------------------------------------------------------
    // WebSocket Client
    // -------------------------------------------------------------
    function connectWebSocket() {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${protocol}//${window.location.host}/ws/admin?token=${encodeURIComponent(token)}`;

        wsStatusText.textContent = "Connecting...";
        wsDot.className = "ws-dot";

        try {
            websocket = new WebSocket(wsUrl);
        } catch (e) {
            wsStatusText.textContent = "Disconnected";
            wsDot.className = "ws-dot disconnected";
            setTimeout(connectWebSocket, 3000);
            return;
        }

        websocket.onopen = function () {
            wsStatusText.textContent = "Live Stream Active";
            wsDot.className = "ws-dot live";

            // Ping every 25 seconds to keepalive
            clearInterval(pingInterval);
            pingInterval = setInterval(() => {
                if (websocket && websocket.readyState === WebSocket.OPEN) {
                    websocket.send("ping");
                }
            }, 25000);
        };

        websocket.onclose = function () {
            wsStatusText.textContent = "Disconnected (Reconnecting...)";
            wsDot.className = "ws-dot disconnected";
            clearInterval(pingInterval);
            setTimeout(connectWebSocket, 3000);
        };

        websocket.onerror = function () {
            websocket.close();
        };

        websocket.onmessage = function (event) {
            try {
                const msg = JSON.parse(event.data);
                handleLiveEvent(msg);
            } catch (err) {
                console.error("Malformed WS event:", err);
            }
        };
    }

    function handleLiveEvent(msg) {
        const eventType = msg.event;
        const data = msg.data;

        if (eventType === "init") {
            if (data.scores) renderScores(data.scores);
            if (data.active_blocks) {
                blocksData = data.active_blocks;
                renderBlocks(blocksData);
            }
            if (data.recent_metrics && data.recent_metrics.length) {
                data.recent_metrics.forEach((m) => {
                    const timeLabel = new Date(m.timestamp).toLocaleTimeString();
                    pushMetricsToCharts(timeLabel, m.cpu_percent, m.memory_percent, m.requests_per_second);
                });
            }
        } else if (eventType === "request_log") {
            if (!isStreamPaused) {
                prependRequestLog(data);
            }
        } else if (eventType === "score_update") {
            upsertScoreRow(data);
        } else if (eventType === "trap_event") {
            loadTrapSessions();
        } else if (eventType === "block_event") {
            upsertBlockData(data);
        } else if (eventType === "system_metric") {
            updateSystemTelemetry(data);
        }
    }

    // -------------------------------------------------------------
    // REST API Loaders
    // -------------------------------------------------------------
    async function loadInitialData() {
        await Promise.all([
            loadScores(),
            loadTrapSessions(),
            loadBlocks(),
            loadRecentLogs(),
            loadHistoricalMetrics(),
            loadExperiments(),
        ]);
    }

    async function loadScores() {
        try {
            const resp = await apiFetch("/admin/security/scores");
            if (resp.ok) {
                const scores = await resp.json();
                renderScores(scores);
            }
        } catch (e) {
            console.error("Error loading scores:", e);
        }
    }

    async function loadTrapSessions() {
        try {
            const [sessResp, sumResp] = await Promise.all([
                apiFetch("/admin/security/trap-sessions?limit=15"),
                apiFetch("/admin/security/trap-summary"),
            ]);

            if (sessResp.ok) {
                const sessions = await sessResp.json();
                renderTrapSessions(sessions);
            }

            if (sumResp.ok) {
                const summary = await sumResp.json();
                statActiveTraps.textContent = summary.active_traps || 0;
                statTokensServed.textContent = (summary.total_tokens_served || 0).toLocaleString();
                const statTrapsSub = document.getElementById("statTrapsSub");
                if (statTrapsSub && summary.total_sessions !== undefined) {
                    statTrapsSub.textContent = `${summary.active_traps || 0} active / ${summary.total_sessions} total sessions`;
                }
            }
        } catch (e) {
            console.error("Error loading trap sessions:", e);
        }
    }

    async function loadBlocks() {
        try {
            const resp = await apiFetch("/admin/security/blocks");
            if (resp.ok) {
                blocksData = await resp.json();
                renderBlocks(blocksData);
            }
        } catch (e) {
            console.error("Error loading blocks:", e);
        }
    }

    async function loadRecentLogs() {
        try {
            const resp = await apiFetch("/admin/security/logs?limit=30");
            if (resp.ok) {
                const logs = await resp.json();
                renderLogs(logs);
            }
        } catch (e) {
            console.error("Error loading logs:", e);
        }
    }

    async function loadHistoricalMetrics() {
        try {
            const resp = await apiFetch("/admin/security/system-metrics?limit=15");
            if (resp.ok) {
                const metrics = await resp.json();
                metrics.forEach((m) => {
                    const timeLabel = new Date(m.timestamp).toLocaleTimeString();
                    pushMetricsToCharts(timeLabel, m.cpu_percent, m.memory_percent, m.requests_per_second);
                });
                if (metrics.length) {
                    updateSystemTelemetry(metrics[metrics.length - 1]);
                }
            }
        } catch (e) {
            console.error("Error loading system metrics:", e);
        }
    }

    async function loadExperiments() {
        try {
            const resp = await apiFetch("/admin/security/experiments?limit=10");
            if (resp.ok) {
                const runs = await resp.json();
                renderExperiments(runs);

                // Auto-compare newest baseline vs newest treatment if both exist
                const baseline = runs.find((r) => !r.trap_enabled && r.total_requests > 0);
                const treatment = runs.find((r) => r.trap_enabled && r.total_requests > 0);
                if (baseline && treatment) {
                    loadComparison(baseline.id, treatment.id);
                }
            }
        } catch (e) {
            console.error("Error loading experiments:", e);
        }
    }

    async function loadComparison(baselineId, treatmentId) {
        try {
            const resp = await apiFetch(
                `/admin/security/experiments/compare?baseline_id=${baselineId}&treatment_id=${treatmentId}`
            );
            if (resp.ok) {
                const comp = await resp.json();
                renderComparison(comp);
            }
        } catch (e) {
            console.error("Error loading comparison:", e);
        }
    }

    function renderExperiments(runs) {
        const tbody = document.getElementById("experimentsTableBody");
        if (!tbody) return;

        if (!runs || !runs.length) {
            tbody.innerHTML = `<tr><td colspan="9" class="empty-table">No experiment runs recorded yet</td></tr>`;
            return;
        }

        tbody.innerHTML = runs
            .map((r) => {
                const modeBadge = r.trap_enabled
                    ? `<span class="security-badge badge-trap">TRAP ON</span>`
                    : `<span class="security-badge badge-normal">BASELINE</span>`;

                const cpuMem = `${r.peak_cpu_percent || 0}% / ${r.peak_memory_percent || 0}%`;

                return `
                <tr>
                    <td><strong>#${r.id}</strong></td>
                    <td>${escapeHtml(r.name)}</td>
                    <td>${modeBadge}</td>
                    <td>${r.total_requests}</td>
                    <td style="color:#2563eb; font-weight:700;">${(r.total_tokens || 0).toLocaleString()}</td>
                    <td style="color:#dc2626; font-weight:700;">${r.real_records_served}</td>
                    <td style="color:#059669; font-weight:700;">${r.fake_records_served}</td>
                    <td><small>${cpuMem}</small></td>
                    <td><small>${escapeHtml(r.stop_reason || "--")}</small></td>
                </tr>
            `;
            })
            .join("");
    }

    function renderComparison(comp) {
        const box = document.getElementById("experimentComparisonBox");
        const tbody = document.getElementById("comparisonTableBody");
        if (!box || !tbody) return;

        box.style.display = "block";
        const b = comp.baseline;
        const t = comp.treatment;
        const a = comp.analysis;

        const rows = [
            ["Run Name & Mode", `${escapeHtml(b.name)} (Trap OFF)`, `${escapeHtml(t.name)} (Trap ON)`, "Controlled Comparison"],
            ["Stop Condition Triggered", escapeHtml(b.stop_reason || "--"), escapeHtml(t.stop_reason || "--"), "--"],
            ["Requests Until Stop", `${b.total_requests}`, `${t.total_requests}`, `${t.total_requests - b.total_requests >= 0 ? '+' : ''}${t.total_requests - b.total_requests} requests`],
            ["Tokens Consumed", `${(b.total_tokens || 0).toLocaleString()}`, `${(t.total_tokens || 0).toLocaleString()}`, `${a.tokens_wasted_on_deception.toLocaleString()} synthetic tokens`],
            ["Real Records Stolen", `<strong style="color:#dc2626;">${a.real_records_stolen_baseline}</strong>`, `<strong style="color:#059669;">${a.real_records_stolen_treatment}</strong>`, `<strong style="color:#059669;">${a.real_data_protected_percent.toFixed(1)}% DATA PROTECTED</strong>`],
            ["Synthetic Records Injected", `${b.fake_records_served}`, `<strong style="color:#059669;">${a.fake_records_injected}</strong>`, `+${a.fake_records_injected} fake employees`],
            ["Peak Server CPU / RAM", `${b.peak_cpu_percent || 0}% / ${b.peak_memory_percent || 0}%`, `${t.peak_cpu_percent || 0}% / ${t.peak_memory_percent || 0}%`, `CPU: ${a.peak_cpu_delta >= 0 ? '+' : ''}${a.peak_cpu_delta}%, RAM: ${a.peak_memory_delta >= 0 ? '+' : ''}${a.peak_memory_delta}%`],
        ];

        tbody.innerHTML = rows
            .map(
                ([metric, bVal, tVal, delta]) => `
            <tr>
                <td><strong>${metric}</strong></td>
                <td>${bVal}</td>
                <td>${tVal}</td>
                <td>${delta}</td>
            </tr>
        `
            )
            .join("");
    }


    // -------------------------------------------------------------
    // Telemetry & UI Renderers
    // -------------------------------------------------------------
    function updateSystemTelemetry(data) {
        statCpuMem.textContent = `${data.cpu_percent.toFixed(1)}% CPU / ${data.memory_percent.toFixed(1)}% RAM`;
        statRps.textContent = `${data.requests_per_second.toFixed(1)} req/sec`;
        statActiveTraps.textContent = data.active_traps || 0;

        const timeLabel = new Date(data.timestamp || Date.now()).toLocaleTimeString();
        pushMetricsToCharts(timeLabel, data.cpu_percent, data.memory_percent, data.requests_per_second);
    }

    function renderBreakdownHtml(s) {
        const b = s.breakdown || s.points_per_signal || {};
        const m = s.metrics || s.measured_values || {};

        const items = [
            { name: "🔢 Sequential IDs", pts: b.sequential_ids || 0, max: 20, desc: `${m.sequential_ids || 0} consecutive IDs (/employees/1..N)` },
            { name: "📄 Deep Pagination", pts: b.pagination_depth || 0, max: 15, desc: `Depth: page ${m.pagination_depth || 0}` },
            { name: "🔐 Failed Logins", pts: b.auth_failures || 0, max: 15, desc: `${m.auth_failures || 0} failed 401 attempts` },
            { name: "🌐 Sensitive Paths", pts: b.distinct_endpoints || 0, max: 10, desc: `${m.distinct_endpoints || 0} distinct endpoints touched` },
            { name: "🔍 Keyword Searches", pts: b.repeated_searches || 0, max: 10, desc: `${m.repeated_searches || 0} search queries executed` },
            { name: "🚀 Request Velocity", pts: b.request_rate || 0, max: 20, desc: `${m.request_rate || 0} requests per minute` },
            { name: "🤖 Automated User-Agent", pts: b.automated_user_agent || 0, max: 5, desc: m.automated_user_agent ? "Automated bot client detected" : "Browser User-Agent" },
            { name: "⚡ Fast Intervals", pts: b.short_intervals || 0, max: 5, desc: `${m.short_intervals || 0} request gaps < 0.3s` }
        ];

        return `
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px; margin: 4px 0;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 8px;">
                    <span style="font-size: 13px; font-weight: 700; color: #1e293b;">
                        🛡️ Heuristic Detection Report for ${escapeHtml(s.ip_address)}: Total ${s.score}/100 (${escapeHtml(s.level || "NORMAL")})
                    </span>
                    <small style="color: #64748b;">Activation Threshold: 75 Points</small>
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 8px;">
                    ${items.map(it => `
                        <div style="background: ${it.pts > 0 ? '#f0fdf4' : '#f8fafc'}; border: 1px solid ${it.pts > 0 ? '#bbf7d0' : '#e2e8f0'}; border-radius: 4px; padding: 6px 10px;">
                            <div style="display:flex; justify-content:space-between; font-weight:600; font-size: 11px;">
                                <span>${it.name}</span>
                                <span style="color: ${it.pts > 0 ? '#16a34a' : '#64748b'};">+${it.pts} / ${it.max}</span>
                            </div>
                            <div style="font-size: 10px; color: #64748b; margin-top: 2px;">${escapeHtml(it.desc)}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    window.toggleScoreBreakdown = function(ip) {
        const safeIp = ip.replace(/[\.\:]/g, '_');
        const breakdownRow = document.getElementById(`breakdown-${safeIp}`);
        if (breakdownRow) {
            breakdownRow.style.display = breakdownRow.style.display === "none" ? "table-row" : "none";
        }
    };

    function renderScores(scores) {
        if (!scores || !scores.length) {
            scoresTableBody.innerHTML = `<tr><td colspan="5" class="empty-table">No active IP scores in window</td></tr>`;
            return;
        }

        window._cachedScores = window._cachedScores || {};

        scoresTableBody.innerHTML = scores
            .map((s) => {
                window._cachedScores[s.ip_address] = s;
                const safeIp = s.ip_address.replace(/[\.\:]/g, '_');
                const badgeClass = getScoreBadgeClass(s.level, s.score);
                const maxSignal = getTopSignalName(s.points_per_signal || s.breakdown);

                return `
                <tr id="score-row-${safeIp}">
                    <td><strong>${escapeHtml(s.ip_address)}</strong></td>
                    <td style="min-width: 130px;">
                        <div style="display:flex; justify-content:space-between; font-weight:700;">
                            <span>${s.score}/100</span>
                        </div>
                        <div class="score-bar-bg">
                            <div class="score-bar-fill" style="width: ${s.score}%; background: ${getScoreColor(s.score)};"></div>
                        </div>
                    </td>
                    <td><span class="security-badge ${badgeClass}">${escapeHtml(s.level || "NORMAL")}</span></td>
                    <td><small style="color:#6b7280;">${escapeHtml(maxSignal)}</small></td>
                    <td>
                        <button class="action-button secondary-button" style="padding: 3px 8px; font-size: 11px;" onclick="toggleScoreBreakdown('${escapeHtml(s.ip_address)}')">
                            🔍 Signals
                        </button>
                    </td>
                </tr>
                <tr id="breakdown-${safeIp}" style="display: none; background: #f8fafc;">
                    <td colspan="5" style="padding: 6px 12px;">
                        ${renderBreakdownHtml(s)}
                    </td>
                </tr>
            `;
            })
            .join("");
    }

    function upsertScoreRow(scoreItem) {
        window._cachedScores = window._cachedScores || {};
        window._cachedScores[scoreItem.ip_address] = scoreItem;

        const safeIp = scoreItem.ip_address.replace(/[\.\:]/g, '_');
        const rowId = `score-row-${safeIp}`;
        const existingRow = document.getElementById(rowId);
        const badgeClass = getScoreBadgeClass(scoreItem.level, scoreItem.score);
        const maxSignal = getTopSignalName(scoreItem.breakdown || scoreItem.points_per_signal);

        const html = `
            <td><strong>${escapeHtml(scoreItem.ip_address)}</strong></td>
            <td style="min-width: 130px;">
                <div style="display:flex; justify-content:space-between; font-weight:700;">
                    <span>${scoreItem.score}/100</span>
                </div>
                <div class="score-bar-bg">
                    <div class="score-bar-fill" style="width: ${scoreItem.score}%; background: ${getScoreColor(scoreItem.score)};"></div>
                </div>
            </td>
            <td><span class="security-badge ${badgeClass}">${escapeHtml(scoreItem.level || "NORMAL")}</span></td>
            <td><small style="color:#6b7280;">${escapeHtml(maxSignal)}</small></td>
            <td>
                <button class="action-button secondary-button" style="padding: 3px 8px; font-size: 11px;" onclick="toggleScoreBreakdown('${escapeHtml(scoreItem.ip_address)}')">
                    🔍 Signals
                </button>
            </td>
        `;

        if (existingRow) {
            existingRow.innerHTML = html;
            existingRow.classList.add("row-new");
            setTimeout(() => existingRow.classList.remove("row-new"), 1500);

            // Update breakdown content if open
            const breakdownContent = document.getElementById(`breakdown-${safeIp}`);
            if (breakdownContent) {
                breakdownContent.querySelector("td").innerHTML = renderBreakdownHtml(scoreItem);
            }
        } else {
            const tr = document.createElement("tr");
            tr.id = rowId;
            tr.innerHTML = html;
            tr.classList.add("row-new");
            scoresTableBody.prepend(tr);

            const bTr = document.createElement("tr");
            bTr.id = `breakdown-${safeIp}`;
            bTr.style.display = "none";
            bTr.style.background = "#f8fafc";
            bTr.innerHTML = `<td colspan="5" style="padding: 6px 12px;">${renderBreakdownHtml(scoreItem)}</td>`;
            tr.after(bTr);
        }
    }

    function renderTrapSessions(sessions) {
        if (!sessions || !sessions.length) {
            trapSessionsTableBody.innerHTML = `<tr><td colspan="5" class="empty-table">No active trap sessions</td></tr>`;
            return;
        }

        trapSessionsTableBody.innerHTML = sessions
            .map((s) => {
                const statusBadge =
                    s.status === "TRAPPED"
                        ? "badge-trap"
                        : s.status === "COMPLETED"
                        ? "badge-unblocked"
                        : "badge-expired";

                return `
                <tr>
                    <td>#${s.id}</td>
                    <td><code>${escapeHtml(s.ip_address)}</code></td>
                    <td><span class="security-badge ${statusBadge}">${escapeHtml(s.status)}</span></td>
                    <td><strong>${s.records_served}</strong></td>
                    <td style="color:#2563eb; font-weight:700;">${(s.tokens_served || 0).toLocaleString()}</td>
                </tr>
            `;
            })
            .join("");
    }

    function renderBlocks(blocks) {
        const activeCount = blocks.filter((b) => b.status === "ACTIVE").length;
        statActiveBlocks.textContent = activeCount;

        if (!blocks || !blocks.length) {
            blocksTableBody.innerHTML = `<tr><td colspan="6" class="empty-table">No IP blocks recorded</td></tr>`;
            return;
        }

        blocksTableBody.innerHTML = blocks
            .map((b) => {
                const statusClass =
                    b.status === "ACTIVE"
                        ? "badge-active"
                        : b.status === "UNBLOCKED"
                        ? "badge-unblocked"
                        : "badge-expired";

                const isActionable = b.status === "ACTIVE";

                return `
                <tr id="block-row-${b.id}">
                    <td><strong><code>${escapeHtml(b.ip_address)}</code></strong></td>
                    <td><span class="security-badge ${statusClass}">${escapeHtml(b.status)}</span></td>
                    <td><small>${escapeHtml(b.reason || "Manual")} (${b.violation_count ? `Violation #${b.violation_count}` : ""})</small></td>
                    <td><small style="color:#6b7280;">${escapeHtml(b.created_by)}</small></td>
                    <td>${
                        isActionable
                            ? `<span class="countdown-live" data-expires="${b.expires_at}">${formatRemainingTime(b.seconds_remaining)}</span>`
                            : `<span style="color:#6b7280;">--</span>`
                    }</td>
                    <td>
                        ${
                            isActionable
                                ? `<button class="action-button danger-button btn-unblock" data-id="${b.id}" style="padding: 4px 8px; font-size: 11px;">Unblock</button>`
                                : `<span style="color:#9ca3af; font-size:12px;">--</span>`
                        }
                    </td>
                </tr>
            `;
            })
            .join("");

        // Attach unblock handlers
        document.querySelectorAll(".btn-unblock").forEach((btn) => {
            btn.addEventListener("click", function () {
                unblockIp(this.dataset.id);
            });
        });
    }

    function upsertBlockData(blockItem) {
        const idx = blocksData.findIndex((b) => b.id === blockItem.id);
        if (idx >= 0) {
            blocksData[idx] = blockItem;
        } else {
            blocksData.unshift(blockItem);
        }
        renderBlocks(blocksData);
    }

    function renderLogs(logs) {
        if (!logs || !logs.length) {
            liveLogTableBody.innerHTML = `<tr><td colspan="8" class="empty-table">No requests recorded</td></tr>`;
            return;
        }

        liveLogTableBody.innerHTML = logs.map((l) => formatLogRowHtml(l)).join("");
    }

    function prependRequestLog(log) {
        const tr = document.createElement("tr");
        tr.className = "row-new";
        tr.innerHTML = formatLogRowHtml(log, true);

        // Remove placeholder if present
        const emptyRow = liveLogTableBody.querySelector(".empty-table");
        if (emptyRow) emptyRow.closest("tr").remove();

        liveLogTableBody.prepend(tr);

        // Cap to 50 rows in DOM
        while (liveLogTableBody.children.length > 50) {
            liveLogTableBody.lastElementChild.remove();
        }
    }

    function formatLogRowHtml(l, isInnerHTML = false) {
        const timeStr = l.timestamp ? new Date(l.timestamp).toLocaleTimeString() : "--";
        const statusClass =
            l.status_code >= 200 && l.status_code < 300
                ? "color: #15803d; font-weight:700;"
                : l.status_code === 403
                ? "color: #ea580c; font-weight:700;"
                : l.status_code === 429
                ? "color: #b91c1c; font-weight:700;"
                : "color: #6b7280; font-weight:700;";

        const trapBadge = l.is_trap
            ? `<span class="security-badge badge-trap" style="font-size:10px;">TRAP</span>`
            : `<span style="color:#9ca3af; font-size:12px;">Real</span>`;

        const scoreText =
            l.suspicion_score !== null && l.suspicion_score !== undefined
                ? `<span style="font-weight:700; color:${getScoreColor(l.suspicion_score)}">${l.suspicion_score}</span>`
                : `<span style="color:#9ca3af;">--</span>`;

        const inner = `
            <td><small>${escapeHtml(timeStr)}</small></td>
            <td><code>${escapeHtml(l.ip_address)}</code></td>
            <td><strong style="font-size:11px;">${escapeHtml(l.method)}</strong></td>
            <td><code style="font-size:12px;">${escapeHtml(l.endpoint)}</code></td>
            <td><span style="${statusClass}">${l.status_code}</span></td>
            <td><small>${l.response_time_ms ? `${l.response_time_ms}ms` : "--"}</small></td>
            <td>${scoreText}</td>
            <td>${trapBadge}</td>
        `;

        return isInnerHTML ? inner : `<tr>${inner}</tr>`;
    }

    // -------------------------------------------------------------
    // Live Countdown
    // -------------------------------------------------------------
    function updateBlockCountdowns() {
        document.querySelectorAll(".countdown-live").forEach((span) => {
            let expiresIso = span.getAttribute("data-expires");
            if (!expiresIso) return;

            // Ensure trailing Z so browser parses as UTC and not local time
            if (!expiresIso.endsWith("Z") && !expiresIso.includes("+")) {
                expiresIso += "Z";
            }

            const diffSec = Math.floor((new Date(expiresIso).getTime() - Date.now()) / 1000);
            if (diffSec <= 0) {
                span.textContent = "Expired";
                span.style.color = "#6b7280";
                span.style.fontWeight = "normal";
            } else {
                span.textContent = formatRemainingTime(diffSec);
                span.style.color = "#ea580c";
                span.style.fontWeight = "bold";
            }
        });
    }

    function formatRemainingTime(sec) {
        if (!sec || sec <= 0) return "Expired";
        const m = Math.floor(sec / 60);
        const s = sec % 60;
        return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
    }

    // -------------------------------------------------------------
    // Admin Actions
    // -------------------------------------------------------------
    if (manualBlockForm) {
        manualBlockForm.addEventListener("submit", async function (e) {
            e.preventDefault();
            const ip = document.getElementById("blockIpInput").value.trim();
            const minutes = parseInt(document.getElementById("blockMinutesInput").value, 10);
            const reason = document.getElementById("blockReasonInput").value.trim();

            if (!ip) return;

            try {
                const resp = await apiFetch("/admin/security/blocks", {
                    method: "POST",
                    body: JSON.stringify({ ip_address: ip, minutes, reason }),
                });

                if (resp.ok) {
                    document.getElementById("blockIpInput").value = "";
                    loadBlocks();
                } else {
                    const err = await resp.json();
                    alert("Failed to create block: " + (err.detail || "Error"));
                }
            } catch (err) {
                alert("Error connecting to server.");
            }
        });
    }

    async function unblockIp(blockId) {
        if (!confirm("Are you sure you want to lift this block?")) return;
        try {
            const resp = await apiFetch(`/admin/security/blocks/${blockId}/unblock`, {
                method: "POST",
            });
            if (resp.ok) {
                loadBlocks();
            } else {
                const err = await resp.json();
                alert("Unblock failed: " + (err.detail || "Error"));
            }
        } catch (e) {
            alert("Error connecting to server.");
        }
    }

    if (btnResetTrap) {
        btnResetTrap.addEventListener("click", async function () {
            if (!confirm("Reset all active traps and clear cooldown periods?")) return;
            try {
                const resp = await apiFetch("/admin/security/trap/reset", { method: "POST" });
                if (resp.ok) {
                    loadTrapSessions();
                }
            } catch (e) {
                alert("Error resetting traps.");
            }
        });
    }

    if (btnResetScores) {
        btnResetScores.addEventListener("click", async function () {
            if (!confirm("Clear behavior scores for all IPs?")) return;
            try {
                const resp = await apiFetch("/admin/security/scores/reset", { method: "POST" });
                if (resp.ok) {
                    loadScores();
                }
            } catch (e) {
                alert("Error resetting scores.");
            }
        });
    }

    if (btnTogglePause) {
        btnTogglePause.addEventListener("click", function () {
            isStreamPaused = !isStreamPaused;
            btnTogglePause.textContent = isStreamPaused ? "▶️ Resume Feed" : "⏸️ Pause Feed";
            btnTogglePause.style.background = isStreamPaused ? "#fef3c7" : "";
        });
    }

    if (btnClearLogView) {
        btnClearLogView.addEventListener("click", function () {
            liveLogTableBody.innerHTML = `<tr><td colspan="8" class="empty-table">Cleared view. Live events will appear above...</td></tr>`;
        });
    }

    const btnRefreshExperiments = document.getElementById("btnRefreshExperiments");
    if (btnRefreshExperiments) {
        btnRefreshExperiments.addEventListener("click", function () {
            loadExperiments();
        });
    }

    // -------------------------------------------------------------
    // Utility Helpers
    // -------------------------------------------------------------
    function getScoreBadgeClass(level, score) {
        if (score >= 75 || level === "TRAP") return "badge-trap";
        if (score >= 61 || level === "SUSPICIOUS") return "badge-suspicious";
        if (score >= 31 || level === "MONITOR") return "badge-monitor";
        return "badge-normal";
    }

    function getScoreColor(score) {
        if (score >= 75) return "#ef4444";
        if (score >= 61) return "#f59e0b";
        if (score >= 31) return "#06b6d4";
        return "#10b981";
    }

    function getTopSignalName(breakdown) {
        if (!breakdown) return "None";
        let topSignal = "None";
        let maxPts = 0;
        for (const [sig, pts] of Object.entries(breakdown)) {
            if (pts > maxPts) {
                maxPts = pts;
                topSignal = `${sig} (+${pts})`;
            }
        }
        return topSignal;
    }

    function escapeHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }
});

