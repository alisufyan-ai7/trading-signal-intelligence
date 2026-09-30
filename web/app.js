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

const marketNames = {
  XAUUSD: "XAU/USD",
  USTEC: "NASDAQ 100",
  US30: "DOW 30",
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

function fmtPct(value) {
  if (value === null || value === undefined) return "—";
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function fmtTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString();
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
    for (const signal of market.signals || []) rows.push(signal);
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
      <div><span>Issued</span><strong>${esc(fmtTime(signal.issued_at_utc))}</strong></div>
      <div><span>Entry</span><strong>${esc(signal.entry)}</strong></div>
      <div><span>Stop</span><strong>${esc(signal.stop)}</strong></div>
      <div><span>Target</span><strong>${esc(signal.target)}</strong></div>
      <div><span>Result</span><strong>${signal.net_r == null ? "Open" : fmtR(signal.net_r)}</strong></div>
      <div class="hash"><span>Record</span><code>${esc(signal.record_hash)}</code></div>
    </article>
  `).join("");
}

function aiUnavailable(ai) {
  return !ai || ["snapshot_pending", "temporarily_unavailable"].includes(ai.status);
}

function renderAi(ai) {
  const statusHost = document.querySelector("#ai-status");
  const overviewHost = document.querySelector("#ai-overview");
  const gatesHost = document.querySelector("#ai-gates");
  const marketHost = document.querySelector("#ai-market-grid");
  const decisionsHost = document.querySelector("#ai-decisions");
  const signalsHost = document.querySelector("#ai-shadow-signals");

  if (aiUnavailable(ai)) {
    statusHost.innerHTML = `
      <div class="empty">
        <strong>AI-v1 shadow insights are not available in the current cloud snapshot.</strong>
        <span>${esc(ai?.customer_notice || "Waiting for the next VPS-derived snapshot.")}</span>
      </div>
    `;
    overviewHost.innerHTML = "";
    gatesHost.innerHTML = "";
    marketHost.innerHTML = "";
    decisionsHost.innerHTML = '<div class="empty">No AI decision snapshot available yet.</div>';
    signalsHost.innerHTML = '<div class="empty">No AI shadow-signal snapshot available yet.</div>';
    return;
  }

  const h = ai.health || {};
  statusHost.innerHTML = `
    <div class="ai-health ${h.healthy ? "" : "warn"}">
      <div>
        <span class="eyebrow">${h.healthy ? "SHADOW RUNTIME HEALTHY" : "ATTENTION REQUIRED"}</span>
        <strong>${esc(ai.runtime_version || ai.protocol_version)} • ${esc(ai.mode)}</strong>
        <span class="meta">Decision protocol ${esc(ai.decision_protocol_version || ai.protocol_version)}</span>
      </div>
      <div class="ai-health-flags">
        <span>${h.ledgers_valid ? "Ledger chains verified" : "Ledger verification failed"}</span>
        <span>${h.scheduler_healthy ? "Scheduler healthy" : "Scheduler issue"}</span>
        <span>${h.broker_execution_disabled ? "Broker execution disabled" : "Broker execution boundary issue"}</span>
      </div>
    </div>
    <p class="ai-notice">${esc(ai.customer_notice)}</p>
    ${ai.lineage_notice ? `<p class="ai-notice">${esc(ai.lineage_notice)}</p>` : ""}
  `;

  const t = ai.totals || {};
  overviewHost.innerHTML = [
    ["Valid inferences", t.valid_inferences ?? 0],
    ["Shadow signals", t.signals ?? 0],
    ["Open signals", t.open_shadow_signals ?? 0],
    ["Completed trades", t.completed_shadow_trades ?? 0],
    ["NO_TRADE", t.no_trade ?? 0],
    ["Missed opportunities", `${t.missed_inferences ?? 0} • ${fmtPct(t.missed_rate)}`],
    ["Errors", t.errors ?? 0],
    ["Net R", fmtR(t.performance_observational_only?.cumulative_net_r)],
  ].map(([label, value]) => `
    <div class="mini-metric">
      <span>${esc(label)}</span>
      <strong>${esc(value)}</strong>
    </div>
  `).join("");

  gatesHost.innerHTML = ["A1", "A2", "A3"].map(name => {
    const gate = ai.gates?.[name];
    if (!gate) return "";
    const inf = gate.valid_inferences;
    const trades = gate.completed_shadow_trades;
    const infPct = Math.min(100, 100 * Number(inf.current || 0) / Number(inf.required || 1));
    const tradePct = Math.min(100, 100 * Number(trades.current || 0) / Number(trades.required || 1));
    return `
      <article class="card gate-card">
        <div class="gate-title">
          <span class="meta">${esc(name)}</span>
          <span class="badge ${gate.eligible ? "" : "warn"}">${gate.eligible ? "ELIGIBLE" : "COLLECTING"}</span>
        </div>
        <div class="gate-line"><span>Valid inferences</span><strong>${esc(inf.current)}/${esc(inf.required)}</strong></div>
        <div class="progress"><i style="width:${infPct}%"></i></div>
        <div class="gate-line"><span>Completed trades</span><strong>${esc(trades.current)}/${esc(trades.required)}</strong></div>
        <div class="progress"><i style="width:${tradePct}%"></i></div>
        <small>${gate.minimum_calendar_days
          ? `Minimum ${esc(gate.minimum_calendar_days)} days • ${esc(gate.calendar_days_remaining)} days remaining`
          : "Operational-audit threshold only"}</small>
      </article>
    `;
  }).join("");

  marketHost.innerHTML = (ai.markets || []).map(m => `
    <article class="card ai-market-card">
      <div class="meta">${esc(m.source_symbol)} • ${m.ledger_valid ? "LEDGER PASS" : "LEDGER FAIL"}</div>
      <h3>${esc(marketNames[m.source_symbol] || m.source_symbol)}</h3>
      <div class="metric-row">
        <div><span>Inferences</span><strong>${esc(m.valid_inferences)}</strong></div>
        <div><span>Signals</span><strong>${esc(m.signals)}</strong></div>
        <div><span>Missed</span><strong>${esc(m.missed_inferences)}</strong></div>
        <div><span>Errors</span><strong>${esc(m.errors)}</strong></div>
      </div>
      <div class="state">Missed-rate: ${fmtPct(m.missed_rate)} • latest evidence: ${esc(fmtTime(m.latest_recorded_at_utc))}</div>
    </article>
  `).join("");

  const decisions = ai.recent_decisions || [];
  if (!decisions.length) {
    decisionsHost.innerHTML = '<div class="empty">No valid AI inferences have been recorded yet.</div>';
  } else {
    decisionsHost.innerHTML = decisions.map(d => {
      const decisionClass = String(d.decision || "").toLowerCase().replace("_", "-");
      const factors = (d.supporting_factors || []).map(x => `<span class="factor good">${esc(x)}</span>`).join("");
      const risks = (d.risk_factors || []).map(x => `<span class="factor risk">${esc(x)}</span>`).join("");
      return `
        <article class="ai-decision-row">
          <div class="decision-top">
            <div>
              <span class="meta">${esc(marketNames[d.source_symbol] || d.source_symbol)} • ${esc(fmtTime(d.source_bar_close_utc))}</span>
              <div class="decision-title">
                <strong class="decision-pill ${esc(decisionClass)}">${esc(d.decision)}</strong>
                <span>${esc(d.raw_confidence)} / 100 raw confidence</span>
                <span>${esc(d.regime)}</span>
              </div>
            </div>
            <span class="badge ${d.guard_publishable ? "" : "warn"}">${d.guard_publishable ? "GUARD PASS" : "GUARD BLOCK"}</span>
          </div>
          <p>${esc(d.rationale || "No rationale summary available.")}</p>
          <div class="factor-list">${factors}${risks}</div>
          <div class="decision-foot">
            <span>Status: ${esc(d.status)}</span>
            <span>Estimated cost: ${d.estimated_cost_r == null ? "—" : fmtR(d.estimated_cost_r)}</span>
            <code>${esc(d.record_hash)}</code>
          </div>
        </article>
      `;
    }).join("");
  }

  const shadowSignals = ai.shadow_signals || [];
  if (!shadowSignals.length) {
    signalsHost.innerHTML = `
      <div class="empty">
        <strong>No AI-v1 shadow signal has been issued yet.</strong>
        <span>Valid NO_TRADE decisions still count toward inference evidence.</span>
      </div>
    `;
  } else {
    signalsHost.innerHTML = shadowSignals.map(s => `
      <article class="signal-row ai-signal-row">
        <div>
          <span class="meta">${esc(marketNames[s.source_symbol] || s.source_symbol)} • ${esc(s.direction)}</span>
          <strong>${esc(s.status.toUpperCase())}</strong>
        </div>
        <div><span>Entry</span><strong>${esc(s.entry)}</strong></div>
        <div><span>Stop</span><strong>${esc(s.stop)}</strong></div>
        <div><span>TP1</span><strong>${esc(s.tp1)}</strong></div>
        <div><span>TP2</span><strong>${esc(s.tp2)}</strong></div>
        <div><span>Confidence</span><strong>${esc(s.raw_confidence)} / 100</strong></div>
        <div><span>Result</span><strong>${s.net_r == null ? "Open" : fmtR(s.net_r)}</strong></div>
        <div class="hash"><span>Record</span><code>${esc(s.record_hash)}</code></div>
      </article>
    `).join("");
  }
}


function setupFeedbackForm() {
  const form = document.querySelector("#feedback-form");
  if (!form) return;

  const submit = document.querySelector("#feedback-submit");
  const status = document.querySelector("#feedback-status");

  form.addEventListener("submit", async event => {
    event.preventDefault();
    status.textContent = "";
    status.classList.remove("success", "error");

    const data = new FormData(form);
    const marketInterests = data.getAll("market_interests");
    if (!marketInterests.length) {
      status.textContent = "Select at least one market.";
      status.classList.add("error");
      return;
    }

    const payload = {
      comprehension_rating: Number(data.get("comprehension_rating")),
      lifecycle_clarity_rating: Number(data.get("lifecycle_clarity_rating")),
      ai_reasoning_clarity_rating: Number(data.get("ai_reasoning_clarity_rating")),
      immutable_record_trust: data.get("immutable_record_trust"),
      missing_details: data.getAll("missing_details"),
      alert_preference: data.get("alert_preference"),
      willingness_to_pay: data.get("willingness_to_pay"),
      price_range: data.get("price_range"),
      market_interests: marketInterests,
      feedback_text: data.get("feedback_text") || "",
    };

    submit.disabled = true;
    submit.textContent = "Submitting…";
    status.textContent = "Saving feedback…";

    try {
      const response = await fetch("/api/feedback", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(result.detail || `Feedback request failed (HTTP ${response.status})`);
      }

      form.reset();
      status.textContent = "Thanks — feedback recorded. No trading action was taken.";
      status.classList.add("success");
    } catch (error) {
      status.textContent = String(error.message || error);
      status.classList.add("error");
    } finally {
      submit.disabled = false;
      submit.textContent = "Submit feedback";
    }
  });
}

async function boot() {
  const aiRequest = fetch("/api/ai/insights")
    .then(res => res.ok ? res.json() : Promise.reject(new Error(`AI endpoint HTTP ${res.status}`)))
    .catch(err => ({
      status: "temporarily_unavailable",
      customer_notice: String(err),
      health: { healthy: false },
    }));

  const [healthRes, marketsRes, signalsRes, ai] = await Promise.all([
    fetch("/api/health"),
    fetch("/api/markets"),
    fetch("/api/signals"),
    aiRequest,
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

  renderAi(ai);
  document.querySelector("#live-grid").innerHTML = live.map(m => card(m, true)).join("");
  document.querySelector("#evidence-grid").innerHTML = live.map(evidenceCard).join("");
  document.querySelector("#research-grid").innerHTML = research.map(m => card(m, false)).join("");
  renderSignals(signals);
}

setupFeedbackForm();

boot().catch(err => {
  document.querySelector("#health-label").textContent = "Unable to load status";
  document.querySelector("#health-detail").textContent = String(err);
  renderAi({
    status: "temporarily_unavailable",
    customer_notice: "The AI Insights section could not be loaded.",
  });
});
