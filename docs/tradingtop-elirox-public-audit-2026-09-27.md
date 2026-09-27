# TradingTop / Elirox public product audit — 2026-09-27 UTC

## Scope and provenance

This note uses only this project's current chat, the `alisufyan-ai7/trading-signal-intelligence` repository, and fresh first-party TradingTop/Elirox pages. It records public product behavior, not an independent audit of either company's performance.

**Browser observation, 2026-09-27 UTC:** On `https://www.tradingtop.com/home.html`, the public navigation exposed AI Insights, AI Trading, Plans, Integrations, Partners and Track Record. The public `/tgai` page displayed asset categories, horizons, symbols including XAUUSD, a question box, Connect Account, AI Trading and View AI Logs. Selecting XAUUSD redirected to login. The `/price` page also redirected to login. Google sign-in was selected through the secure browser authentication flow, but Google's OAuth destination returned a 502 connection error. No authenticated TradingTop content, subscription prices or actual signal payloads were verified in this session.

### First-party references

- TradingTop home: https://www.tradingtop.com/home.html
- TradingTop AI public entry: https://www.tradingtop.com/tgai
- TradingTop Help Center: https://www.tradingtop.com/questions.html
- TradingTop AI description: https://www.tradingtop.com/ai.html
- Elirox product description: https://elirox.com/help-center/common-questions/what-is-elirox-and-how-does-it-work/
- Elirox TradingView automation: https://elirox.com/tradingview-alerts-automation/

## What the sources actually show

| Topic | TradingTop | Elirox | Implication for this project |
|---|---|---|---|
| Entry experience | Public AI page lists asset classes and symbols; choosing XAUUSD asks for login. | Published help describes download, broker connection, subscription and bot launch. | Let beta users understand a market's evidence and a sample signal lifecycle before asking them to sign up. |
| Core proposition | Public site positions AI reasoning, AI trading, logs, alerts and a track record. Its Help Center describes email subscriptions by instrument and says reasoning can occur every 6–8 hours. | Published help describes user-configured or AI Preset DCA/GRID bots. TradingView alerts can trigger broker orders. | Our research beta should lead with verified rule-based signals and their lifecycle, not claim parity with automated execution or discretionary AI reasoning. |
| Evidence | TradingTop Help Center claims 73.7% target-1 and 61.9% target-2 win rates; methodology and account-level evidence were not independently verified here. | Published product material explains bots and monitoring, not an independently verified comparison against our strategy. | Keep historical, forward, and operational evidence separate; show losses and sample sizes. Do not repeat competitor accuracy claims as established facts or infer our own accuracy. |
| User controls | Public AI page offers market categories/horizons and a question box; authenticated controls remain unverified. | Published help offers DCA/GRID settings and risk-level presets. | Start with market and alert preferences only after users can see signal validity, risk levels and evidence tier. |
| Pricing | Plans link exists; price page redirected to login in this browser. | Subscription is part of the published onboarding sequence; exact plan prices were not checked. | Ask users what they would pay and for which value; do not anchor price to an unverified competitor number. |

## Current repository product state

The repo's `web/index.html`, `web/app.js` and cloud API show three live-signal markets, separate evidence cards and immutable forward history. The next-actions document records a deployed research beta, two completed XAU forward trades, and no persistent Railway volume. It records feedback capture and first-user discovery as the next work. This note does **not** independently retest the hosted deployment.

The page and service currently use the name “TradingTop Early Access,” which is also the comparison site's public brand. Before inviting external users, choose an independently identifiable product name and review every visible title, service label and onboarding text. This is a brand-confusion risk observation, not a legal conclusion.

## Product decision proposal for the first-user milestone

1. **Keep the current evidence boundary.** S02 forward validation remains active and unchanged. The product describes XAU as the primary historical lead, USTEC/US30 as secondary transfer support, and the other six as research coverage. Do not present forward validation as complete.
2. **Design a feedback loop before inviting users.** Collect a small set of answers: which market they came for; whether they can distinguish a historical backtest from a forward result; which entry/stop/target/expiry detail is missing; whether they want alerts; and whether they would pay, including an optional price range and reason. Make free text optional. Never collect broker credentials or account balances.
3. **Choose durable storage before enabling a public feedback form.** The current cloud snapshot lives on an ephemeral Railway filesystem. A local JSON/SQLite feedback endpoint on that filesystem could acknowledge a submission and then lose it on redeploy. Use a configured durable database or a clearly identified external form provider, with access control, retention and privacy copy. Until then, show no misleading “feedback saved” confirmation.
4. **Measure activation with a narrow event set.** If analytics is added, count anonymous page load, live-market view, evidence view, signal-history view and feedback submit. Avoid raw market feed fields, user-level trade decisions and any claim that a view equals a successful trade.
5. **Prepare a small owner-selected cohort.** Invite only after brand, feedback destination and privacy text are settled. Ask each participant for one walkthrough of an actual signal record and one willingness-to-pay answer. Do not send invitations from this note.

## Checks before implementation

- Verify auth state and exact signal UX from a successfully signed-in TradingTop session; the current browser session could not reach Google OAuth.
- Select the durable feedback destination and retention policy, then implement the form, server validation, rate limiting, submission acknowledgment and a retrieval path for the owner.
- Test that a redeploy does not erase submitted feedback, and that failures show a clear retry message.
- Validate the public beta again after a product change; this audit only read the repository.

## Authenticated TradingTop follow-up — 2026-09-27 UTC

A later user-authorized email/password sign-in succeeded in the same Work browser session. The public-only limitations above describe the earlier Google OAuth failure and are now superseded for TradingTop pricing and the observed account views.

The complete screenshot index, hashes, observed plan tiers, XAU signal card, aggregate AI log and three separate model performance pages are in [the private research capture index](../research/competitors/tradingtop/2026-09-27/README.md). In particular, the displayed T2 gold model's last-three-month PnL was **-$441.30 over 53 trades**, while the aggregate AI log showed a separate 74.00% “Inference Accuracy” headline. These have different scopes and were not independently audited; they must not be combined into one performance claim. No broker connection, paid access or automated trading was activated.
