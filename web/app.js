const niceEvidence = {
  historical_robustness_passed_forward_active: "Primary historical lead • forward active",
  historical_transfer_support_secondary: "Secondary historical transfer support",
  mixed_historical_not_live_launch_signal: "Mixed historical evidence",
  unstable_historical_not_live_launch_signal: "Historically unstable",
  regime_unstable_not_live_launch_signal: "Regime unstable",
  transfer_test_failed_full_oos: "Transfer evidence insufficient",
  transfer_test_failed_final: "Final-test evidence insufficient",
  transfer_test_failed_oos: "OOS evidence insufficient",
};

const esc = (value) => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

function fmtR(value) {
  if (value === null || value === undefined) return "—";
  const n = Number(value);
  return `${n >= 0 ? "+" : ""}${n.toFixed(3)}R`;
}

function card(market, live) {
  const forward = market.forward;
  const state = live
    ? (forward?.state === "active_signal"
      ? "Active setup in forward ledger"
      : forward?.state === "scanning"
      ? "Scanning • no active setup"
      : "Forward collector not activated yet")
    : "Research monitoring";

  const badgeClass = live ? "badge" : "badge warn";
  return `
    <article class="card">
      <div class="meta">${esc(market.asset_class.toUpperCase())} • ${esc(market.source_symbol)}</div>
      <h3>${esc(market.canonical_symbol)}</h3>
      <div class="${badgeClass}">${esc(niceEvidence[market.evidence_status] || market.evidence_status)}</div>
      <div class="state">${esc(state)}</div>
    </article>
  `;
}

function evidenceCard(market) {
  const e = market.evidence;
  if (!e) return "";
  const h = e.historical || {};
  return `
    <article class="card evidence-card">
      <div class="meta">${esc(market.source_symbol)} • ${esc(e.evidence_tier.replaceAll("_", " "))}</div>
      <h3>${esc(market.canonical_symbol)}</h3>
      <div class="metric-row">
        <div><span>Validation</span><strong>${fmtR(h.validation_net_expectancy_r)}</strong></div>
        <div><span>Final test</span><strong>${fmtR(h.final_test_net_expectancy_r)}</strong></div>
      </div>
      <p>${esc(e.summary)}</p>
      <small>${esc(e.caveat)}</small>
    </article>
  `;
}

function signalRows(marketsPayload) {
  const rows = [];
  for (const market of marketsPayload.markets || []) {
    for (const signal of market.signals || []) {
      rows.push(signal);
    }
  }
  rows.sort((a, b) => String(b.issued_at_utc).localeCompare(String(a.issued_at_utc)));
  return rows;
}

function renderSignals(payload) {
  const host = document.querySelector("#signal-history");
  const rows = signalRows(payload);
  if (!rows.length) {
    host.innerHTML = `
      <div class="empty">
        <strong>No forward signals issued yet.</strong>
        <span>The collectors are live. The first qualifying setup will appear here automatically.</span>
      </div>
    `;
    return;
  }

  host.innerHTML = rows.map(signal => `
    <article class="signal-row">
      <div>
        <span class="meta">${esc(signal.canonical_symbol)} • ${esc(signal.direction?.toUpperCase())}</span>
        <strong>${esc(signal.status === "active" ? "ACTIVE" : "CLOSED")}</strong>
      </div>
      <div><span>Issued</span><strong>${esc(signal.issued_at_utc)}</strong></div>
      <div><span>Entry</span><strong>${esc(signal.entry)}</strong></div>
      <div><span>Stop</span><strong>${esc(signal.stop)}</strong></div>
      <div><span>Target</span><strong>${esc(signal.target)}</strong></div>
      <div><span>Result</span><strong>${signal.net_r == null ? "Open" : fmtR(signal.net_r)}</strong></div>
      <div class="hash"><span>Record</span><code>${esc(signal.record_hash)}</code></div>
    </article>
  `).join("");
}

async function boot() {
  const [healthRes, marketsRes, signalsRes] = await Promise.all([
    fetch("/api/health"),
    fetch("/api/markets"),
    fetch("/api/signals"),
  ]);
  const health = await healthRes.json();
  const markets = await marketsRes.json();
  const signals = await signalsRes.json();

  const label = document.querySelector("#health-label");
  const detail = document.querySelector("#health-detail");
  const dot = document.querySelector(".dot");

  if (!health.ok) {
    label.textContent = "Attention required";
    detail.textContent = `Ledger error: ${health.ledger_errors.join(", ") || "unknown"}`;
    dot.classList.add("warn");
  } else if (!health.launch_ready) {
    label.textContent = "Launch setup incomplete";
    detail.textContent =
      `${health.ready_collector_count}/${health.live_signal_markets} live collectors active`;
    dot.classList.add("warn");
  } else {
    label.textContent = "Systems operational";
    detail.textContent =
      `${health.ready_collector_count}/${health.live_signal_markets} live collectors active`;
    dot.classList.remove("warn");
  }

  const live = markets.filter(m => m.product_status === "live_signal_market");
  const research = markets.filter(m => m.product_status === "research_monitoring");

  document.querySelector("#live-grid").innerHTML = live.map(m => card(m, true)).join("");
  document.querySelector("#evidence-grid").innerHTML = live.map(evidenceCard).join("");
  document.querySelector("#research-grid").innerHTML = research.map(m => card(m, false)).join("");
  renderSignals(signals);
}

boot().catch(err => {
  document.querySelector("#health-label").textContent = "Unable to load status";
  document.querySelector("#health-detail").textContent = String(err);
});
