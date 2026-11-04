"use strict";
/* VowSig member shell. No broker execution, notifications, payments, or hidden model data.
 * Do not construct markup with API strings: use textContent throughout.
 * Auth is server-cookie based; credentials/CSRF are never persisted in localStorage.
 */
(() => {
  const main = document.querySelector("#app-content");
  const error = document.querySelector("#app-error");
  const headings = {
    dashboard: "My research", signals: "Signal Center", history: "Recent history",
    markets: "All nine markets", watchlist: "My watchlist",
    learn: "Learn", settings: "Account & preferences", admin: "Owner research overview",
  };
  const route = location.pathname;
  const page = route.startsWith("/admin") ? "admin" :
    ({signals:"signals",history:"history",markets:"markets",watchlist:"watchlist",
      learn:"learn",settings:"settings"}[route.split("/").filter(Boolean)[1]] || "dashboard");
  document.title = "VowSig · " + headings[page];
  document.querySelector("#page-title").textContent = headings[page];
  document.querySelectorAll("[data-page]").forEach(a => {
    if (a.dataset.page === page) a.setAttribute("aria-current", "page");
  });
  const state = {me:null, catalog:[], watchlist:[], saved:[], feed:null, csrf:null};
  const E = (tag, attrs={}, ...children) => {
    const el = document.createElement(tag);
    for (const [k,v] of Object.entries(attrs)) {
      if (k === "class") el.className = v;
      else if (k === "text") el.textContent = String(v ?? "");
      else if (k === "value") el.value = v;
      else if (k === "disabled") el.disabled = Boolean(v);
      else if (k === "onClick") el.addEventListener("click", v);
      else if (v != null) el.setAttribute(k, String(v));
    }
    for (const child of children) {
      if (child == null) continue;
      el.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
    return el;
  };
  const clear = () => main.replaceChildren();
  const text = v => (v === null || v === undefined || v === "" ? "Not available" : String(v));
  const date = v => {
    if (!v) return "Not available";
    const d = new Date(v);
    return Number.isNaN(d.getTime()) ? "Not available" : d.toLocaleString(undefined, {year:"numeric",month:"short",day:"numeric",hour:"2-digit",minute:"2-digit",timeZoneName:"short"});
  };
  const panel = (title, ...kids) => E("section",{class:"panel"}, E("h2",{text:title}), ...kids);
  const msg = (title, body) => E("div",{class:"message"}, E("strong",{text:title}), E("p",{text:body}));
  const pill = (value,kind="") => E("span",{class:"pill "+kind,text:value});
  const compact = (pairs) => E("div",{class:"metrics"}, ...pairs.map(([k,v]) =>
    E("span",{},E("b",{text:k+": "}),text(v))));
  const btn = (label, fn, muted=false) => E("button",{type:"button",class:muted?"subtle":"button",onClick:fn,text:label});
  const link = (label, href) => E("a",{href,text:label});
  const fail = m => {
    error.hidden = false;
    error.className = "alert";
    error.textContent = m;
  };
  async function request(url, opts={}) {
    const cfg = {credentials:"same-origin",cache:"no-store",...opts,headers:{
      "Accept":"application/json", ...(opts.headers || {}),
    }};
    const response = await fetch(url,cfg);
    if (!response.ok) throw new Error(
      response.status === 401 ? "Your verified account session is unavailable. Sign in will be enabled at launch." :
      response.status === 403 ? "This action is not permitted for this account or research program." :
      response.status === 404 ? "The requested research record is no longer available." :
      "Research data is temporarily unavailable ("+response.status+")."
    );
    return await response.json();
  }
  function mutation(method,path,body) {
    return request(path,{method,headers:{
      "Origin":location.origin,"X-VowSig-CSRF":state.csrf,
      ...(body ? {"Content-Type":"application/json"} : {}),
    },...(body ? {body:JSON.stringify(body)} : {})});
  }
  const heading = s => E("h3",{text:s});
  function itemMarket(m) {
    const saved = state.watchlist.includes(m.symbol);
    const item = E("article",{class:"list-row"},
      E("div",{class:"row-head"},heading(m.name),pill(m.research_status.replaceAll("_"," "),
        m.research_signal_detail_available ? "closed":"restricted")),
      E("p",{class:"helper",text:m.research_signal_detail_available ?
        (m.current_signal_present ? "Current validated SHADOW_ONLY observation in source snapshot." :
          "Core research available; no verified current shadow signal.") :
        "Research validation / availability only. No detailed signal exposure."}),
      compact([["Symbol",m.symbol],["Source","Research only"],
        ["Snapshot",m.snapshot_fresh ? "Fresh" : "Unavailable / delayed"]]));
    const save = btn(saved?"Remove from watchlist":"Add to watchlist",async () => {
      save.disabled=true;
      try {
        const result = await mutation(saved?"DELETE":"PUT",
          "/api/v2/me/watchlist/"+encodeURIComponent(m.symbol));
        state.watchlist=result.markets;
        render();
      } catch(e) {fail(e.message);save.disabled=false;}
    },saved);
    item.append(save);
    return item;
  }
  function researchSignal(signal) {
    const symbol=signal.source_symbol;
    const el=E("article",{class:"list-row"},
      E("div",{class:"row-head"},heading(symbol+" · "+text(signal.direction)),
        pill(signal.status === "closed" ? "Closed research record" :
             signal.current_signal_eligible === true ? "Active SHADOW ONLY" :
             "Activity unverified · historical", signal.status==="closed"?"closed":"unavailable")),
      compact([["Issued",date(signal.issued_at_utc)],["Entry",signal.entry],
        ["Stop",signal.stop],["TP1",signal.tp1],["TP2",signal.tp2]]),
      E("p",{class:"reason",text:signal.rationale || "No published rationale."}),
      E("p",{class:"risk",text:(signal.risk_factors || []).join(" · ") || "Review stop, target and methodology before interpreting this research."}));
    if (signal.status==="closed")el.append(compact([
      ["Exit",date(signal.exit_at_utc)],["Combined net R",signal.net_r],
      ["Exit reason",signal.exit_reason],
    ]));
    const actions=E("div",{class:"inline-actions"});
    if (signal.entity_id) {
      actions.append(btn("Save research",async () => {
        try {await mutation("PUT","/api/v2/me/saved/"+encodeURIComponent(symbol)+"/"+encodeURIComponent(signal.entity_id));
          fail("Research item saved to your account.");}
        catch(e){fail(e.message);}
      },true));
    }
    actions.append(link("Understand signal lifecycle","/learn/signal-lifecycle/"));
    el.append(actions);
    return el;
  }
  function decisionCard(row) {
    return E("article",{class:"list-row"},
      E("div",{class:"row-head"},heading(row.source_symbol+" · "+text(row.decision)),
        pill(row.guard_publishable===true?"Research decision":"Not an eligible signal",
          row.decision==="NO_TRADE"?"no-trade":"restricted")),
      compact([["Observed",date(row.recorded_at_utc)],
        ["Status",row.status],["Confidence","Uncalibrated model score"]]),
      E("p",{class:"reason",text:row.rationale||"No published rationale."}),
      E("p",{class:"risk",text:(row.guard_reasons||[]).join(" · ") ||
        "A model decision is not automatically a published signal."}));
  }
  async function ensureFeed() {
    if (!state.feed) {
      const incoming = await request("/api/v2/me/history");
      const core = new Set(["XAUUSD", "USTEC", "US30"]);
      // Defense in depth only: the v2 server must also enforce this permission.
      state.feed = {
        ...incoming,
        signals: Array.isArray(incoming.signals) ?
          incoming.signals.filter(s => s && core.has(s.source_symbol)) : [],
        decisions: Array.isArray(incoming.decisions) ?
          incoming.decisions.filter(d => d && core.has(d.source_symbol)) : [],
      };
    }
    return state.feed;
  }
  function showDashboard() {
    const followed=state.catalog.filter(m=>state.watchlist.includes(m.symbol));
    main.append(panel("At a glance",
      E("div",{class:"tiles"},
        E("div",{class:"tile"},E("div",{class:"amount",text:state.catalog.length}),E("div",{class:"name",text:"Markets monitored"}),E("p",{text:"All nine research catalog symbols"})),
        E("div",{class:"tile"},E("div",{class:"amount",text:state.catalog.filter(x=>x.research_signal_detail_available).length}),E("div",{class:"name",text:"Core detail currently permitted"}),E("p",{text:"Research only, freshness gated"})),
        E("div",{class:"tile"},E("div",{class:"amount",text:state.watchlist.length}),E("div",{class:"name",text:"My watched markets"}),E("p",{text:"Not a trading portfolio"})))));
    main.append(panel("My watchlist",followed.length ?
      E("div",{class:"tiles"},...followed.map(x=>E("div",{class:"tile"},heading(x.name),
        E("p",{text:x.research_status.replaceAll("_"," ")})))) :
      msg("Start with a market","Open All Markets to follow any of the nine available research symbols."),
      link("Explore all markets","/app/markets/")));
    main.append(panel("Where to begin",
      E("div",{class:"learn-grid"},
        learnCard("Signal Center","Recent permitted core shadow setups and lifecycle.","/app/signals/"),
        learnCard("Understand outcomes","What after-cost R, stops and shadow mode mean.","/learn/shadow-validation/"))));
  }
  function learnCard(name,description,href) {
    return E("a",{class:"learn-card",href},E("b",{text:name}),E("span",{text:description}));
  }
  async function showSignals() {
    const feed=await ensureFeed();
    const core=state.catalog.filter(m=>m.research_signal_detail_available);
    main.append(panel("Permitted core research",
      E("p",{class:"helper",text:"These records come from the current bounded snapshot, not a complete track record. 'Active' means shadow research, never a customer trade alert."}),
      feed.status!=="shadow_only" ? msg("No fresh core research",
        "No eligible published core snapshot is currently available. Do not act on old entries.") :
      E("div",{class:"signals-list"},
        ...(feed.signals.length ? feed.signals.map(researchSignal) :
          [msg("No recent core signals","No eligible shadow signals in the bounded current snapshot.")]))));
    main.append(panel("Recent research decisions (including NO_TRADE)",
      E("div",{class:"signals-list"},
        ...(feed.decisions.length ? feed.decisions.slice(0,12).map(decisionCard) :
          [msg("No recent decisions","An unavailable inference is not a NO_TRADE.")]))));
    main.append(panel("Market scope",
      E("p",{class:"helper",text:"All nine markets can be followed; only currently permitted core research can show per-signal detail."}),
      compact([["Core markets",core.length],["Validation-only markets",state.catalog.length-core.length]])));
  }
  async function showHistory() {
    const feed=await ensureFeed();
    const select=E("select",{"aria-label":"Filter market"},E("option",{value:"ALL",text:"All permitted markets"}),
      ...["XAUUSD","USTEC","US30"].map(s=>E("option",{value:s,text:s})));
    const lifecycle=E("select",{"aria-label":"Filter lifecycle"},
      E("option",{value:"ALL",text:"All outcomes"}),E("option",{value:"active",text:"Open research"}),
      E("option",{value:"closed",text:"Closed research"}));
    const rows=E("div",{class:"signals-list"});
    const paint=()=>{
      const filtered=feed.signals.filter(s=>(select.value==="ALL"||s.source_symbol===select.value)
        &&(lifecycle.value==="ALL"||s.status===lifecycle.value));
      rows.replaceChildren(...(filtered.length?filtered.map(researchSignal):
        [msg("No records for these filters","This does not imply the market has no historical trades.")]));
    };
    select.addEventListener("change",paint);lifecycle.addEventListener("change",paint);
    main.append(panel("Recent eligible observations",
      msg("History is not yet complete",
      feed.record_window_notice||"Only the sanitized current snapshot is available. Losses and missing data are not hidden."),
      E("div",{class:"filters"},select,lifecycle),rows));
    paint();
    main.append(panel("NO_TRADE and guard decisions",
      E("div",{class:"stack"},...(feed.decisions.length ? feed.decisions.map(decisionCard):
        [msg("No decision records","No recent decisions in the bounded snapshot.")]))));
  }
  function showMarkets() {
    main.append(panel("All Markets · nine symbols",
      E("p",{class:"helper",text:"Saved markets do not grant a signal subscription. Validation-only symbols have no per-signal details."}),
      E("div",{class:"tiles"},...state.catalog.map(itemMarket))));
  }
  function showWatchlist() {
    const rows=state.catalog.filter(m=>state.watchlist.includes(m.symbol));
    main.append(panel("Saved markets",rows.length ?
      E("div",{class:"tiles"},...rows.map(itemMarket)) :
      msg("Your watchlist is empty","Add markets from All Markets; this is for research organization, not portfolio advice."),
      link("Browse markets","/app/markets/")));
    main.append(panel("Saved research records",
      E("p",{class:"helper",text:"A bookmark is a reference to an already-published core research record. It is not an active alert."}),
      ...(state.saved.length ? state.saved.map(s=>E("div",{class:"list-row"},
        compact([["Market",s.symbol],["Saved",date(s.saved_at_utc)]]),
        E("p",{class:"helper",text:s.signal_id}))) :
        [msg("No saved research","Open a permitted core signal and choose Save research.")])));
  }
  function showLearn() {
    main.append(panel("Learn how to read research, not just a trade direction",
      E("div",{class:"learn-grid"},
        learnCard("BUY, SELL or NO_TRADE","Abstention is a valid outcome, not an actionable market signal.","/learn/buy-sell-no-trade/"),
        learnCard("Signal lifecycle","Entry, stop, TP1, TP2, partial and closed status.","/learn/signal-lifecycle/"),
        learnCard("Shadow validation","Research observations vs real broker execution.","/learn/shadow-validation/"),
        learnCard("Forward vs backtest","Why historical results are not proof of future returns.","/learn/backtests-vs-forward-results/"),
        learnCard("Immutable history","Provenance, losses and transparent research evidence.","/learn/immutable-signal-history/"))));
  }
  async function showSettings() {
    const p=await request("/api/v2/me/preferences");
    const zone=E("input",{id:"tz",value:p.timezone,"aria-label":"IANA time zone",maxlength:"64"});
    const level=E("select",{id:"level","aria-label":"Education level"},
      ...["beginner","intermediate","advanced"].map(x=>E("option",{value:x,text:x})));
    level.value=p.educational_level;
    const consent=E("input",{type:"checkbox",id:"consent"});
    consent.checked=p.research_updates_opt_in===true;
    const save=btn("Save preferences",async()=>{
      try {
        save.disabled=true;
        await mutation("PATCH","/api/v2/me/preferences",{
          timezone:zone.value,educational_level:level.value,
          research_updates_opt_in:consent.checked,
        });
        fail("Preferences saved. This opt-in does NOT send signal alerts.");
      }catch(e){fail(e.message);}finally{save.disabled=false;}
    });
    const download=btn("Export my account data",async()=>{
      try {
        const data=await request("/api/v2/me/export");
        const blob=new Blob([JSON.stringify(data,null,2)],{type:"application/json"});
        const url=URL.createObjectURL(blob);
        const a=E("a",{href:url,download:"vowsig-account-export.json"});
        document.body.append(a);a.click();a.remove();URL.revokeObjectURL(url);
      }catch(e){fail(e.message);}
    },true);
    const deleteRequest=btn("Request account deletion (requires verification)",async()=>{
      if (!window.confirm("Record a request for identity-reverified account deletion? This does not erase data immediately.")) return;
      try {
        const outcome=await mutation("POST","/api/v2/me/deletion-request");
        fail("Deletion request status: "+outcome.status+". Data remains until verified processing.");
      }catch(e){fail(e.message);}
    },true);
    main.append(panel("Your account",
      compact([["Role",state.me.role],["Tier",state.me.access_tier],
        ["Verified email","Yes"],["Commercial trade execution","Disabled"]])));
    main.append(panel("Personal research preferences",
      E("form",{class:"preferences"},E("div",{class:"preference-grid"},
        E("label",{}, "Time zone (IANA format)",zone),
        E("label",{}, "Educational level",level),
        E("label",{class:"checkbox-label"},consent,"I consent to research product updates (no trading alerts)")),
      E("p",{class:"helper",text:"Notification delivery is not enabled in this release. Consent can be changed later."}),
      save,download,deleteRequest)));
    if(state.me.role==="owner"){
      const code=E("input",{type:"text",id:"owner-code","inputmode":"numeric",
        autocomplete:"one-time-code",maxlength:"6","aria-label":"Six-digit authenticator code",
        pattern:"[0-9]{6}"});
      const verify=btn("Verify owner authenticator code",async()=>{
        try{
          verify.disabled=true;
          const proof=await mutation("POST","/api/v2/me/owner-mfa/verify",{code:code.value});
          code.value="";
          if(proof.verified!==true)throw new Error("Owner verification was not confirmed.");
          fail("Owner verification completed. Admin access is time-limited.");
        }catch(e){
          code.value="";
          fail("Owner verification not confirmed. Check your code or request secure recovery.");
        }finally{verify.disabled=false;}
      });
      main.append(panel("Owner MFA · authenticator app",
        msg("Independent owner verification",
          "Enter the six-digit code from the pre-enrolled authenticator. Enrollment and recovery are handled offline; Auth0 premium MFA is not used."),
        E("label",{}, "Current one-time code",code),
        verify,
        E("a",{href:"/admin/"},"Open owner dashboard after verification")));
    }
  }
  async function showAdmin() {
    if (state.me.role!=="owner")throw new Error("Owner-only dashboard");
    const [ops,perf,growth,evidence]=await Promise.all([
      request("/api/v2/admin/operations"),
      request("/api/v2/admin/performance"),
      request("/api/v2/admin/growth"),
      request("/api/v2/admin/evidence"),
    ]);
    main.append(panel("Source-limited operational overview",
      compact([["Snapshot",date(ops.as_of_utc)],["Fresh",ops.snapshot_fresh?"Yes":"No"],
        ["VPS runtime independently verified","No"],["Backup restores proven here","No"]]),
      E("div",{class:"tiles"},...ops.programs.map(p=>E("article",{class:"tile"},
        heading(p.program_id),
        compact([["Reported healthy",text(p.reported_healthy)],
          ["Valid inferences",p.valid_inferences],["Errors",p.errors],
          ["Completed shadow",p.completed_shadow_trades]]))))));
    const cohort=perf&&perf.verified_full_cohort_history===true&&perf.performance;
    main.append(panel("Performance Lab",
      cohort ?
        E("div",{},
          msg("Independently attested cohort · research-only",
            "A signed, reviewer-approved original-ledger audit matched the entire named cohort. Other lineages are not certified by this result."),
          compact([["Program",perf.performance.source_program_id],
            ["Version",perf.performance.model_version],
            ["Cohort",perf.performance.cohort],
            ["Reviewed",date(perf.reviewed_at_utc)],
            ["Source outcomes",perf.performance.total_outcomes],
            ["Completed after-cost",perf.performance.completed_count],
            ["Wins / losses / flat",[perf.performance.win_count,
              perf.performance.loss_count,perf.performance.breakeven_count].join(" / ")],
            ["Win rate · completed only",
              perf.performance.win_rate==null?"N/A":(100*perf.performance.win_rate).toFixed(1)+"%"],
            ["Net normalized R",perf.performance.sum_completed_net_r==null?
              "N/A":perf.performance.sum_completed_net_r],
            ["Average net R",perf.performance.expectancy_net_r==null?
              "N/A":perf.performance.expectancy_net_r],
            ["Max closed-R drawdown",perf.performance.max_normalized_r_drawdown==null?
              "N/A":perf.performance.max_normalized_r_drawdown],
            ["Unresolved / abstain / rejected / errors",
              [perf.performance.open_count,perf.performance.no_trade_count,
               perf.performance.rejected_count,perf.performance.error_count].join(" / ")],
            ["Sample caveat",perf.performance.sample_warning||"None"],
            ["Real-money returns","Not available"]]))
        :
        msg("Source-reconciled performance unavailable",
          "A truncated public snapshot or a database verification flag alone cannot certify complete after-cost historical results."),
      E("p",{class:"helper",text:perf.notice})));
    const sourceRows=Array.isArray(evidence.snapshots)?evidence.snapshots:[];
    main.append(panel("Independent history evidence & reconciliation",
      msg("Original-ledger verification still required",
        evidence.next_evidence_required ||
        "Database projections are not proof that a historical cohort is complete."),
      compact([["Full history independently verified","No"],
        ["Source projections listed",sourceRows.length],
        ["Performance publishing permitted","No"],
        ["Inventory truncated",evidence.inventory_truncated?"Yes":"No"]]),
      sourceRows.length?
        E("div",{class:"tiles"},...sourceRows.slice(0,12).map(p=>E("article",{class:"tile"},
          heading(p.source_program_id+" · "+p.model_version),
          compact([["Stored projection status",p.ingest_status],
            ["Projected records",p.projected_records],
            ["Closed / open",String(p.projected_closed)+" / "+String(p.projected_open)],
            ["NO_TRADE / rejected / errors",
              [p.projected_no_trade,p.projected_rejected,p.projected_error].join(" / ")],
            ["Cost-attributed closed",p.projected_closed_after_costs],
            ["Independent source proof","Not provided"]])))):
        msg("No historical source projections",
          "The owner dashboard will populate only from reconciled evidence. No performance statistics are fabricated.")));
    main.append(panel("Growth, access security & recovery",
      msg("Database-observed counts · not invented retention",
        "Only privacy-safe verified-account, session and consent aggregates are reported. D7 retention and revenue remain unmeasured."),
      compact([["Registered accounts",growth.registered_accounts],
        ["Verified accounts",growth.verified_accounts],
        ["Unverified accounts",growth.unverified_accounts],
        ["New accounts · 24h",growth.new_accounts_24h],
        ["New accounts · 7d",growth.new_accounts_7d],
        ["New accounts · 30d",growth.new_accounts_30d],
        ["Verified percentage",growth.verified_rate==null?"N/A":(100*growth.verified_rate).toFixed(1)+"%"],
        ["Accounts with watchlists",growth.accounts_with_watchlist],
        ["Accounts with saved research",growth.accounts_with_saved_research],
        ["Research updates opt-in",growth.research_updates_opted_in_accounts],
        ["Deletion requests pending review",growth.pending_deletion_requests],
        ["Unrevoked unexpired sessions",growth.valid_account_sessions_now],
        ["Login sessions issued · 7d",growth.issued_sessions_last_7d],
        ["Owner authenticators enrolled",growth.owner_totp_enrolled_accounts],
        ["D7 retention","Not yet measured"],
        ["Revenue","Not enabled"],
        ["Independent Postgres restore",growth.backup_restore_proven?"Verified":"Not yet verified"]]),
      E("p",{class:"helper",text:growth.backup_notice||
        "PostgreSQL recovery integration is the first post-launch operational task."})));
  }
  async function render(){
    clear(); error.hidden=true;
    try{
      state.me=await request("/api/v2/me");state.csrf=state.me.csrf_token;
      document.querySelector("#tier-label").textContent=state.me.access_tier.replaceAll("_"," ");
      const [cat,watch]=await Promise.all([request("/api/v2/public/markets"),request("/api/v2/me/watchlist")]);
      state.catalog=cat.markets;state.watchlist=watch.markets;
      document.querySelector("#snapshot-status").textContent=cat.markets.every(m=>m.snapshot_fresh)?"Current snapshot":"Updates delayed / unavailable";
      if(page==="dashboard")showDashboard();
      else if(page==="markets")showMarkets();
      else if(page==="signals")await showSignals();
      else if(page==="history")await showHistory();
      else if(page==="watchlist"){
        state.saved=(await request("/api/v2/me/saved")).saved;showWatchlist();
      }
      else if(page==="learn")showLearn();
      else if(page==="settings")await showSettings();
      else if(page==="admin")await showAdmin();
    }catch(e){
      clear();fail(e.message);
      main.append(msg("Research workspace not ready",
        "Your existing public research site remains accessible. No signal is assumed active while this workspace is unavailable."),
        link("Back to public VowSig","/"));
    }
  }
  document.querySelector("#signout").addEventListener("click",async ()=>{
    try{await mutation("POST","/api/v2/me/logout");location.assign("/");}
    catch(e){fail(e.message);}
  });
  render();
})();
