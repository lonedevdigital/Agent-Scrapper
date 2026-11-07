---
name: Precision Editorial Workstation
colors:
  surface: '#0b1326'
  surface-dim: '#0b1326'
  surface-bright: '#31394d'
  surface-container-lowest: '#060e20'
  surface-container-low: '#131b2e'
  surface-container: '#171f33'
  surface-container-high: '#222a3d'
  surface-container-highest: '#2d3449'
  on-surface: '#dae2fd'
  on-surface-variant: '#bfc7d2'
  inverse-surface: '#dae2fd'
  inverse-on-surface: '#283044'
  outline: '#89929b'
  outline-variant: '#3f4850'
  surface-tint: '#93ccff'
  primary: '#93ccff'
  on-primary: '#003351'
  primary-container: '#3198dc'
  on-primary-container: '#002c47'
  inverse-primary: '#006398'
  secondary: '#4edea3'
  on-secondary: '#003824'
  secondary-container: '#00a572'
  on-secondary-container: '#00311f'
  tertiary: '#d0bcff'
  on-tertiary: '#3c0091'
  tertiary-container: '#a078ff'
  on-tertiary-container: '#340080'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#cce5ff'
  primary-fixed-dim: '#93ccff'
  on-primary-fixed: '#001d31'
  on-primary-fixed-variant: '#004b73'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#e9ddff'
  tertiary-fixed-dim: '#d0bcff'
  on-tertiary-fixed: '#23005c'
  on-tertiary-fixed-variant: '#5516be'
  background: '#0b1326'
  on-background: '#dae2fd'
  surface-variant: '#2d3449'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-xl-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.015em
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 26px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 28px
    letterSpacing: -0.005em
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
    letterSpacing: 0em
  code-body:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: -0.01em
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 18px
    letterSpacing: 0em
  kbd-badge:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.04em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-desktop: 1.5rem
  margin: 1rem
  margin-desktop: 1.5rem
  space-2xs: 0.125rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
  space-2xl: 2rem
---

## Brand & Style

This design system targets machine learning engineers, computational linguists, and data labeling specialists who spend 6–10 hours per session scanning, segmenting, and categorizing text. The emotional mandate is focused clarity, low visual fatigue, and uncompromised operator efficiency. 

The aesthetic is Modern Technical Minimalist: crisp structural boundaries, subdued slate surfaces that recede behind the document text, and high-visibility classification badges that pop instantly without cluttering visual parsing. Text legibility is treated as a core operational feature rather than a decorative choice. The system pairs dense, precise data presentation with immediate tactile and visual feedback for keyboard shortcuts, batch actions, and token-level highlight spans.

## Colors

The system uses a calibrated Dark Slate base (`#0f172a`) as its primary working environment to minimize eye fatigue during extended annotation sessions, while mapping 1:1 onto a high-contrast Light Slate mode for bright environments. 

### Semantic Role Palette
- **Primary Canvas / Workbench (`#0284c7` Sky Blue)**: Controls primary system actions, text token selection handles, active navigation tabs, and intent/informational classifications.
- **Positive / Approve (`#10b981` Emerald)**: Verification marks, accepted spans, high-confidence model inferences, and positive classification categories.
- **Negative / Reject (`#f43f5e` Rose)**: Rejected labels, flagged hallucinations, syntax errors, and toxic text spans.
- **Neutral / Ambiguous (`#f59e0b` Amber)**: Uncertain spans, unassigned tokens, pending review warnings, and edge-case highlights.
- **Entity / Custom Extraction (`#8b5cf6` Violet)**: Custom taxonomy classes, named entities (NER), and multi-class token annotations.

### Functional Tinting
Backgrounds in dark mode progress from `#090d16` (deep canvas base) to `#0f172a` (card workbench) and `#1e293b` (elevated control bars and toolbars). In light mode, backgrounds sit on `#f8fafc` canvas, `#ffffff` panels, and `#f1f5f9` structural dividers. All badge fills must utilize low-opacity tinted grounds (12–16% fill) paired with solid 100% border strokes and saturated text to maintain WCAG AAA compliance against dense body copy.

## Typography

Typography prioritizes continuous micro-legibility and tabular alignment. 

- **Primary Reading Surface**: **Inter** is set with open line heights (`lineHeight: 28px` on `16px` base body) within the main text corpus. This prevents adjacent line collisions when overlapping multi-colored entity underline brackets or background highlights are present.
- **Accents & Telemetry**: **JetBrains Mono** is reserved for raw corpus tokens, regex query bars, confidence score readouts, JSON schema attributes, and hotkey indicators.
- **Tabular Numerals**: All numeric indicators (confidence metrics, dataset row index, token start/end offset coordinates) must enable tabular figures (`font-variant-numeric: tabular-nums`) to avoid layout jitter during rapid paging.

## Layout & Spacing

The workspace uses a dense, tool-oriented 3-pane layout designed for high data throughput:
1. **Left Rail (Navigation & Queue)**: 280px fixed width, collapsible to 64px icon bar. Shows dataset split filters, progress gauges, and record queues.
2. **Center Stage (The Annotation Canvas)**: Fluid workbench optimized with a maximum line width constraint of 72ch for textual corpus reading.
3. **Right Rail (Entity Palette & Telemetry)**: 340px fixed width displaying hierarchical class tags, model predictions, metadata attributes, and hotkey bindings.

### Breakpoints & Reflow
- **Desktop (>= 1280px)**: Persistent 3-panel architecture. Multi-record text view mode available.
- **Tablet (768px – 1279px)**: Left rail collapses to a sliding drawer. Annotation canvas and taxonomy palette remain side-by-side.
- **Mobile (< 768px)**: Single-column stack. The taxonomy palette converts into a thumb-zone bottom navigation sheet. Selected text spans trigger a thumb-friendly radial or bottom action strip with 44px minimum tap targets.

## Elevation & Depth

Visual hierarchy uses tonal surface layering combined with low-contrast structural borders (`#334155` in dark mode, `#cbd5e1` in light mode) rather than heavy drop shadows, maintaining crisp contrast for rapid spatial orientation.

- **Level 0 (Base Canvas)**: `#090d16` (Dark) / `#f8fafc` (Light). Global backdrop for non-interactive gutter zones.
- **Level 1 (Card & Workspace Panels)**: `#0f172a` (Dark) / `#ffffff` (Light). Crisp 1px outline with low-contrast borders. No shadow.
- **Level 2 (Active Document / Selection Card)**: `#1e293b` (Dark) / `#ffffff` (Light). Uses an ambient shadow: `0 4px 16px -2px rgba(0, 0, 0, 0.4)` with a 1px border highlighted in primary slate.
- **Level 3 (Floating Menus, Annotation Popovers, Modals)**: Elevated surface with `0 10px 30px -4px rgba(0, 0, 0, 0.6)` and a dual border system (1px structural border plus 1px semi-transparent inner glow).

## Shapes

The design system maintains a geometric, precise visual identity with a compact border radius level (`roundedness: 1`). 

- Standard inputs, buttons, panels, and dataset table rows utilize a disciplined 4px (`0.25rem`) corner radius.
- Cards, modal overlays, and code blocks use 8px (`0.5rem`).
- Keyboard shortcut indicators and tag chips leverage 4px (`0.25rem`) to maintain structural alignment with monospaced characters.
- Fully rounded pills (`9999px`) are strictly forbidden, as they reduce usable surface area in dense token annotation ribbons and clash with the technical editorial visual structure.

## Components

### Buttons
- **Primary**: Solid blue (`#0284c7`), dark text/white text with 4px radius, 36px desktop height (44px on mobile). Pairs inline keyboard indicators where applicable.
- **Ghost/Tertiary**: Borderless, elevated only on hover (`#1e293b` fill), used for quick pagination (`Next [E]`, `Previous [Q]`).
- **Mobile Action Buttons**: Full-width bottom sticky buttons with integrated thumb zone clearance and haptic feedback triggers.

### Chips & Entity Badges
- **Annotation Tag Badge**: Tinted background (12% alpha) matching taxonomy group (Emerald, Rose, Amber, Sky Blue, Violet), 1px solid border matching 80% category color, text rendered at 100% saturation. Left side displays the class hotkey badge; right side shows token count or confidence score.
- **Inline Text Highlight Spans**: 2px bottom border line with a subtle 20% alpha background tint over selected corpus characters. Never obscure text readability.

### Keyboard Shortcut Badges (`<kbd>`)
- Formatted in `JetBrains Mono` at 11px. Rendered with an extruded technical feel: dark neutral surface, 1px top/lateral border, and a pronounced 2px bottom border (`#475569`) to mimic physical tactile keycaps.

### Checkboxes & Radios
- Sharp 4px rounded rectangles for multi-label selection; circles for single-class intent. 
- High-contrast states: inactive borders sit at `#475569`; checked state features solid primary or category color with high-contrast glyph.

### Input Fields & Search Bars
- Fixed height of 36px for dense tabular filtering. Background in `#090d16` with 1px border. Transitions to solid Sky Blue (`#0284c7`) with a 1px halo ring upon focus. Includes monospaced syntax indicators (`/regex/` or `key:value`).

### Annotation Cards
- Contain the sample ID, status indicator, character counter, text display body, and tag ribbon. Padding is strictly constrained to `16px`. Active card marked by a 2px left border accent in primary Sky Blue.

### Token Selection Toolbar (Popover)
- Appears immediately above highlighted character spans on pointer release or shortcut trigger. Contains horizontal quick-tag numbers `1` through `9`, rendered with high-contrast category colors for rapid single-stroke annotation.