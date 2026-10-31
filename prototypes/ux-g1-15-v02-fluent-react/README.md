# VALORA — UX-G1.15 v02 (Microsoft Fluent UI React v9)

**Status:** Independent **interactive design prototype**, not production code and not a new domain/API approval. Uses real Microsoft `@fluentui/react-components` v9, `FluentProvider webLightTheme`, Fluent icons, and custom CSS only for VALORA-specific layout/table geometry. Built from the decisions documented in [Draft PR #223](https://github.com/Reguluspt/valora-engineering/pull/223).

## Quick start

Requires Node.js 20+ and network access to npm registry on the **developer's machine**.

```bash
npm install
npm run dev
```

Then open the local URL printed by Vite (normally `http://127.0.0.1:5173`). For production-style static bundle testing:

```bash
npm run build
npm run preview
```

Offline domain-independent tests:

```bash
npm run test:logic
```

**Build limitation in the authoring environment:** npm registry DNS is unavailable; source could be parsed/checked and deterministic logic tests executed, but **a full npm install / Vite build and actual browser-run Fluent rendering could not be verified here**. Do not report it as a tested live UI until someone runs those commands and records evidence. Dependency versions are aligned to VALORA frontend (`@fluentui/react-components@9.74.9`, React 19.2.8, Vite 6.4.5). Icon dependency is a separate real Fluent icons package.

## Visual review scenarios

Open the app and use the row table or the **prototype-only scenario toolbar** at the bottom.

1. **01 · Đã tự điền:** CNC model X100; two sourced price observations have an unusual difference. See actual Fluent MessageBar warning, source cards, customer price, surveyed price, editable human price and next/previous.
2. **02 · Thiếu nguồn:** Compressor with no confidently matched price; show similar Knowledge Base candidates and material differences; explicitly choose a reference or edit manually. Source link/evidence count on table updates.
3. **03 · Sửa đặc điểm:** Open generator, switch to **Đặc điểm & SL** tab, edit model/capacity, save; inline Fluent RadioGroup asks correction of shared knowledge / new variant / case-only. The shared KB is never activated by the prototype.
4. **Tổng kết & xuất:** View counts, warnings and total of known-value lines, navigate to an asset; confirm an **in-memory version only**. No real Excel is created or downloaded.

### Additional interaction coverage

- Sidebar collapse retains icons/tooltips; official Fluent `Breadcrumb` provides clickable ancestors.
- Real Fluent UI v9 `Table` primitives, `Button`, `Input`, `Field`, `Select`, `Badge`, `MessageBar`, `RadioGroup`, `TabList`, `InlineDrawer`, `DrawerHeader`/`Body`/`Footer` are used; **table column pinning and top/bottom horizontal scroll are custom VALORA layout CSS/behavior** rather than a claimed Microsoft DataGrid feature.
- Clipboard images in explanation input use browser `FileReader` (prototype-only, max 2 MB), link auto-detection, source attachment preview and evidence count.
- Separate statuses for auto-populated, missing-price, reviewed, needs-recheck and manually edited fields.
- No per-asset approval button. Mark viewed only after navigation away from asset.

## Boundaries / important caveats

- All assets, prices and source URLs are **fictional demonstration data** (`example.com`). There is no backend, authentication, online search, Knowledge Base, role permission, AI inference or persistence.
- The source ranking and confidence are **fixture labels**, not an implementation of real matching algorithms. No AI price calculation is certified. Suggested price uses surveyed price + percentage transport only when data is present; manually set proposed price is independent.
- History, saved state and exported versions are simulations in React memory; reload resets the prototype. Export button **does not generate XLSX**. Real XLSX output needs a separately approved domain/generator/security task.
- Avoid presenting fake source URL or image as real evidence. Initial source cards contain demonstrative links. New clipboard images are previewed only in memory.
- This package must not be merged into VALORA production routes, alter UAT #203 or trigger implementation without new explicit gate.

## Design + component evidence

- [OS-G1 vNext reading index](https://github.com/Reguluspt/valora-engineering/blob/docs/os-g1-vnext-fluent2-20261031/docs/design/os-g1-vnext/README.md).
- [Fluent 2 component mapping](https://github.com/Reguluspt/valora-engineering/blob/docs/os-g1-vnext-fluent2-20261031/docs/design/os-g1-vnext/FLUENT2_COMPONENT_MAPPING.md).
- [Fluent 2 breadcrumb guidance](https://fluent2.microsoft.design/components/web/react/core/breadcrumb/usage).
- [Fluent 2 drawer guidance](https://fluent2.microsoft.design/components/web/react/core/drawer/usage).
- [Microsoft Fluent React Table primitive guidance](https://react.fluentui.dev/).

## PO review conditions

Before labeling as a new approved baseline, demonstrate native Fluent rendering at 1440x900 and 1280x800, capture actual screenshots for the three core scenarios and summary, verify keyboard/zoom/focus, and sign off any deviation from archived 26-Oct mockup and v2.3 S12/S13 visual grammar. No such full runtime acceptance has been performed in this chat due dependency-install restrictions.
