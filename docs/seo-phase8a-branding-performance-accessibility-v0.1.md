# VowSig SEO Phase 8A — Branding, Performance, Mobile & Accessibility v0.1

_Status: ISOLATED IMPLEMENTATION / PRE-PRODUCTION_  
_Date: 2026-10-02_  
_Parent: GitHub Issue #8_  
_Branch: `product/vowsig-phase8a-polish-v0.1`_

## Scope

This follow-up closes the remaining practical Phase 8A polish without changing
AI-v1.1 decision behavior, the AI-v1.0 decision protocol, S02, ledgers,
scheduler semantics, broker execution, or public performance claims.

## Search-result / browser branding

Adds a deterministic VowSig icon built only from existing public brand colors:

- navy background: `#09111f`;
- mint V mark: `#78e0b1`;
- gold signal dot: `#ffd479`.

Assets:

- `web/vowsig-favicon.svg`;
- `web/vowsig-favicon-96.png`;
- `web/vowsig-apple-touch-icon.png`.

All 12 canonical HTML pages reference the SVG favicon, 96x96 PNG fallback and
180x180 Apple touch icon. They also set the existing dark background as
`theme-color`.

## Performance changes

The public surface is already lightweight: no remote font, image, analytics or
third-party script dependency is introduced.

This follow-up:

- defers the root dashboard JavaScript so HTML parsing is not blocked;
- keeps favicon assets very small;
- retains local-only CSS/JS/assets;
- keeps static payload budgets enforced by tests;
- bumps the stylesheet cache key only because CSS changes.

This is a practical code-level performance pass. It is not a claim that field
Core Web Vitals have passed; real-user CWV data remains an observation item
when enough data exists.

## Mobile changes

- existing 820px/520px responsive grid behavior is preserved;
- narrow-screen shell/nav width is tightened to avoid edge crowding;
- mobile navigation links become clear touch targets;
- feedback controls use a 16px mobile font size to reduce unwanted mobile zoom;
- interactive controls enforce practical 44px minimum target height.

## Accessibility changes

All 12 canonical HTML pages now have:

- a keyboard-visible “Skip to main content” link;
- `main#main-content`;
- primary navigation with its existing accessible label;
- current-section navigation state;
- exactly one H1;
- viewport metadata;
- no image missing an alt attribute.

Content pages use semantic breadcrumb navigation.

CSS adds:

- high-visibility `:focus-visible` outlines;
- keyboard-accessible skip-link behavior;
- reduced-motion handling;
- long-code wrapping;
- minimum touch-target sizing.

The current core text/accent/warning/error palette is regression-tested against
all three dark surface colors at WCAG AA normal-text contrast (>= 4.5:1).

## Governance

Every file under `web/` is covered by the public-surface exact tracked-tree
manifest.

Therefore this branch must receive a new sequence-3 governed
`AI-v1.1-public-surface-v0.2` correction successor after the exact final
implementation is tested.

The existing correction builder already supports successor sequencing and
must be used; no correction anchor is created before the implementation/test
checkpoint passes.

## Production boundary

Do not merge or deploy this branch yet.

Required before production:

1. isolated compile/tests;
2. static branding/mobile/accessibility audit PASS;
3. generate exactly one sequence-3 correction anchor;
4. commit/push the exact reviewed anchor;
5. verify full correction chain upstream;
6. explicit owner production-cutover approval;
7. controlled production sync and hosted verification;
8. natural AI-v1.1/publisher continuity proof.
