---
name: Meeting Reality Engine
description: Evidence-grounded meeting intelligence — what was decided, not what was said
colors:
  bg: "#0A0A0C"
  surface: "#131316"
  surface-raised: "#1C1C21"
  border: "#232326"
  border-subtle: "#1A1A1D"
  text-primary: "#F2F2F3"
  text-secondary: "#8B8B90"
  text-disabled: "#7C7C82"
  status-decided: "#34D399"
  status-committed: "#60A5FA"
  status-discussed: "#FBBF24"
  status-conflict: "#F87171"
  status-unknown: "#9CA3AF"
typography:
  display:
    fontFamily: "Space Grotesk Variable, Space Grotesk, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(2.75rem, 5vw, 3.75rem)"
    fontWeight: 500
    lineHeight: 1.08
    letterSpacing: "-0.03em"
  body:
    fontFamily: "Inter Variable, Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "normal"
  mono:
    fontFamily: "JetBrains Mono Variable, JetBrains Mono, ui-monospace, monospace"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "normal"
rounded:
  sm: "0.25rem"
  md: "0.375rem"
  lg: "0.5rem"
  xl: "0.75rem"
  2xl: "1rem"
  pill: "9999px"
spacing:
  sm: "0.5rem"
  md: "1rem"
  lg: "1.5rem"
  xl: "2rem"
  2xl: "3rem"
components:
  button-primary:
    backgroundColor: "{colors.text-primary}"
    textColor: "{colors.bg}"
    rounded: "{rounded.lg}"
    padding: "12px 20px"
  status-badge:
    backgroundColor: "transparent"
    rounded: "{rounded.pill}"
    padding: "2px 8px"
---

# Design System: Meeting Reality Engine

## Overview

**Creative North Star: "The Reconstruction Room"**

The product doesn't summarize a meeting — it reconstructs what became true after one. The surface plays that role back visually: a near-black room where a raw, unstructured transcript line resolves, in front of you, into a clean structured claim with a status and an owner. Noise on the left, order on the right; nothing is claimed that isn't shown happening.

This is not a generic "AI-powered" gradient-hero template. There is no gradient text, no kicker label, no stock hero illustration. Color shows up as soft ambient light — status-red and status-green pooling behind proof cards — never as a fill inside a headline. Depth comes from layered shadow and glow, not flat colored halos. Every mono-styled string on the page is either real transcript text, a real terminal command, or a real status word — mono is evidence, not a "technical" costume.

**Key Characteristics:**
- Near-black ground with soft, status-colored radial glow doing the accent work
- A geometric display face (Space Grotesk) with real point of view, reserved for headlines
- Every claim demonstrated live (streaming transcript → resolved status card), never just asserted
- The five-state taxonomy (Decided / Committed / Discussed / Conflict / Unknown) is load-bearing brand vocabulary, not decoration

## Colors

Near-black neutral ground; color is spent entirely on the five-state status system, never on decoration.

### Primary
- **Signal Blue** (`#60A5FA`, `--status-committed`): the "someone owns this" color — commitment pills, the primary demo card's resolved state, focus rings.

### Secondary
- **Verified Green** (`#34D399`, `--status-decided`): resolution and proof — "reconstructed" badges, the after-side of any before/after comparison, positive empty states.
- **Conflict Red** (`#F87171`, `--status-conflict`): disagreement and noise — conflict pills, the before-side ambient glow, unresolved-tension accents.

### Tertiary
- **Caution Amber** (`#FBBF24`, `--status-discussed`): talked-about-not-landed, and "tentative" qualifiers riding beside a committed claim.
- **Neutral Gray** (`#9CA3AF`, `--status-unknown`): implied-but-never-resolved — the quietest status, deliberately desaturated.

### Neutral
- **Void** (`#0A0A0C`, `--bg`): page ground.
- **Card Surface** (`#131316`, `--surface`): card and panel fill.
- **Raised Surface** (`#1C1C21`, `--surface-raised`): nested/hover surface.
- **Hairline** (`#232326`, `--border`): default 1px borders.
- **Subtle Hairline** (`#1A1A1D`, `--border-subtle`): quieter dividers (legend rule, footer rule).
- **Primary Text** (`#F2F2F3`, `--text-primary`): headlines, resolved claim titles.
- **Secondary Text** (`#8B8B90`, `--text-secondary`): body copy, supporting sentences.
- **Tertiary Text** (`#7C7C82`, `--text-disabled`): captions, mono hints, timestamps — tuned to stay ≥4.5:1 against the void ground; it is dim, never illegible.

### Named Rules
**The Glow, Not Fill Rule.** Status color pools as ambient radial light behind a card (`.glow-spot`, blurred 80px) or lives in a small saturated badge/dot. It never fills text, never becomes a gradient headline, never becomes a colored left-border accent.

## Typography

**Display Font:** Space Grotesk Variable (self-hosted via `@fontsource-variable/space-grotesk`), with system-ui fallback
**Body Font:** Inter Variable, with system-ui fallback
**Label/Mono Font:** JetBrains Mono Variable, with ui-monospace fallback

**Character:** Space Grotesk's geometric, slightly technical letterforms carry the headlines with confidence without tipping into whimsy; Inter stays purely functional for body copy; JetBrains Mono is reserved for anything that is literally data — transcript text, terminal commands, status qualifiers.

### Hierarchy
- **Display** (500, `clamp(2.75rem, 5vw, 3.75rem)`, 1.08 line-height, -0.03em tracking): page and section headlines, `font-display` class.
- **Body** (400, 1.125rem, 1.6 line-height): hero subhead and lead paragraphs, max ~46ch measure.
- **Body small** (400, 0.875–1rem): supporting sentences inside cards.
- **Label** (500, 0.75rem, uppercase optional): status badge text, section labels — never used as a kicker above a heading.
- **Mono** (400, 0.6875–0.8125rem): transcript lines, evidence quotes, terminal commands, timestamps.

### Named Rules
**The Mono-Is-Evidence Rule.** Monospace only renders real transcript text, real commands, or real data — never a "this looks technical" costume on ordinary UI copy.

## Layout

Single-column content stack, `max-w-5xl`–`max-w-6xl` centered containers, generous `py-20`–`py-32` section rhythm with a 1px hairline dividing each section. The hero is the one asymmetric composition: a `1.1fr / 1fr` two-column grid above the `lg` (1024px) breakpoint (headline + CTA left, live demo card right), collapsing to a single stacked column below it — content order becomes headline → CTA → demo card. Comparison cards run `grid-cols-2` from `sm` (640px) up, stacking to one column below it, with the status badge relocating above the headline on mobile (`flex-col-reverse` → `sm:flex-row`) rather than forcing two-line headline wraps.

## Elevation & Depth

Hybrid: flat surfaces by default, lifted only where a card needs to separate from ambient glow behind it. Depth reads through layered shadow (`offset + blur`, never a flat colored halo) plus, on the signature demo card, `backdrop-blur-sm` at 80% surface opacity so the glow behind it visibly diffuses through the glass rather than being blocked by it.

### Shadow Vocabulary
- **`surface-sm`** (`0 1px 2px 0 rgba(0,0,0,0.5)`): default resting card edge.
- **`surface`** (`0 2px 8px 0 rgba(0,0,0,0.6)`): raised interactive surfaces.
- **`surface-lg`** (`0 8px 32px 0 rgba(0,0,0,0.7)`): the hero demo card — the page's single most elevated element.
- **`glow-*`** (`0 0 12px 0 rgba(<status>,0.25)`): status-colored ambient glow, used sparingly and only tied to a real status meaning.

### Named Rules
**The Earned Glass Rule.** `backdrop-blur` only appears where it is doing a specific job — separating the signature demo card from the glow behind it — never as generic card decoration.

## Shapes

Rounded-2xl (`1rem`) for primary cards, rounded-lg (`0.5rem`) for buttons and small controls, full pill radius for status badges. 1px hairline borders throughout; no colored border-left/right accents — status meaning is carried by badges, dots, and glow, never by a stripe on the card edge.

## Components

### Buttons
- **Shape:** `rounded-lg` (0.5rem).
- **Primary:** solid `text-primary` fill on `bg` text (inverted), 12px/20px padding, `hover:brightness-110`, `active:scale-[0.98]`.
- **Ghost/utility (Replay):** 1px border, transparent fill, border/text brighten on hover.

### Status Badge
- **Style:** pill radius, transparent-tinted background at 8% opacity of the status hue, solid-color text and a small `currentColor` dot — never a solid fill badge.
- **States:** one badge per state (Decided / Committed / Discussed / Conflict / Unknown); an optional adjacent mono qualifier (e.g. "tentative") in `--status-discussed`.

### Cards / Containers
- **Corner Style:** `rounded-2xl` (1rem).
- **Background:** `--surface`, occasionally `/80` with `backdrop-blur-sm` for the signature demo card.
- **Shadow Strategy:** see Elevation & Depth; comparison cards stay flat (`overflow-hidden` + internal glow only), the demo card carries `shadow-surface-lg`.
- **Border:** 1px `--border`.
- **Internal Padding:** `1.25rem`–`1.5rem` (`p-5`/`p-6`).

### Live Demo Card (signature component)
The `HeroDemo` component: a transcript line streams in character-by-character (`AiStreamingText`, ~16ms/char), then a resolved status-pill claim card fades and slides in beneath a hairline divider. A small "Replay" control (RotateCw icon + label) remounts the stream via a `key` bump. This is the page's one authored motion moment — no other scroll-triggered or hover-scattered animation competes with it.

## Do's and Don'ts

### Do:
- **Do** keep the five-state vocabulary (Decided / Committed / Discussed / Conflict / Unknown) exact and consistent everywhere it appears — it is product semantics, not a color choice.
- **Do** ground every marketing claim in something the working tool (`static/index.html` / `main.py`) actually produces — the before/after numbers on the landing page come from a real synthesis run against a representative transcript, not invented figures.
- **Do** reserve JetBrains Mono for literal data/commands/transcript text.
- **Do** use `--text-disabled` for tertiary captions — it is tuned to ≥4.5:1 contrast against `--bg`; don't reintroduce the old `#4a4a50` value.

### Don't:
- **Don't** use gradient-filled text for emphasis — use weight, size, or a status-colored badge/glow instead.
- **Don't** add a kicker/eyebrow label above a heading.
- **Don't** add a colored left-border accent to a card — status meaning lives in badges, dots, and glow only.
- **Don't** invent product claims, customer logos, testimonials, or metrics that the working tool doesn't actually produce.
