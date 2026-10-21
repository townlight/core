<a id="civiccore-ui--the-civicsuite-design-system"></a>

# civiccore-ui — the Townlight design system

The shared, versioned UI layer every Townlight module builds on. Three layers,
each the single source of truth for its concern:

| Layer | File | Owns |
|---|---|---|
| **Tokens** | [`tokens/tokens.css`](tokens/tokens.css) | Values — color, ink ramp, status palette, type families, density, radii. WCAG-AA-validated ([`tokens/tokens-reference.html`](tokens/tokens-reference.html)). |
| **Components** | [`components/components.css`](components/components.css) | Structure — buttons, badges, status ribbon, tables, forms, alerts, first-run steps, empty states, audit drawer ([`components/components-reference.html`](components/components-reference.html)). |
| **Shell** | [`shell/shell.css`](shell/shell.css) | The app frame — brand block, topbar, surface switcher, nav, workspace, page header, letterhead, search overlay. |

## Dependency direction

```
tokens.css  ─┐
             ├─►  components.css  ─►  shell.css
             ┘
```

Components consume tokens; the shell consumes both. Load in that order. No layer
redefines a `:root` custom property that `tokens.css` already owns.

## Consumption (offline binaries cannot `@import` at runtime)

Consumers — the Tauri/WebView2 desktop app, the umbrella prototype — **vendor a
generated copy** of each file, pinned to a `civiccore` version, with a CI
`--check` drift gate that fails the build if a vendored copy drifts from the
source here. Any JS/JSON mirror is generated, never hand-maintained. This is the
same idiom as the `source_commit` pins and the generated topology block. See the
umbrella repo's `docs/design/windows-desktop-design-control.md` (Token Authority).

## Provenance

`components.css` and `shell.css` were extracted faithfully from the canonical
prototype (`docs/design/ui-ux-prototype/styles.css` in the umbrella repo) — same
class names, same behavior — with one accessibility correction: `.badge.gold`
uses `--gold-strong` (5.43:1 on `--gold-soft`) instead of `--gold-2` (4.31:1, an
AA fail). Migrating the prototype and desktop app to consume these files (rather
than their own copies) is the incremental follow-on, one surface at a time.
