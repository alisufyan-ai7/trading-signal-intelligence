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
      <div class="meta">${market.asset_class.toUpperCase()} • ${market.source_symbol}</div>
      <h3>${market.canonical_symbol}</h3>
      <div class="${badgeClass}">${niceEvidence[market.evidence_status] || market.evidence_status}</div>
      <div class="state">${state}</div>
    </article>
  `;
}

async function boot() {
  const [healthRes, marketsRes] = await Promise.all([
    fetch("/api/health"),
    fetch("/api/markets"),
  ]);
  const health = await healthRes.json();
  const markets = await marketsRes.json();

  document.querySelector("#health-label").textContent = health.ok ? "Systems operational" : "Attention required";
  document.querySelector("#health-detail").textContent =
    `${health.live_signal_markets} live-signal markets configured`;

  const live = markets.filter(m => m.product_status === "live_signal_market");
  const research = markets.filter(m => m.product_status === "research_monitoring");

  document.querySelector("#live-grid").innerHTML = live.map(m => card(m, true)).join("");
  document.querySelector("#research-grid").innerHTML = research.map(m => card(m, false)).join("");
}

boot().catch(err => {
  document.querySelector("#health-label").textContent = "Unable to load status";
  document.querySelector("#health-detail").textContent = String(err);
});
