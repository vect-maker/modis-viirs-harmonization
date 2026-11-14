# FIRMS Wildfire Harmonizer — Frontend

Interactive web application for the **NASA Space Apps Challenge 2026: Harmonization of MODIS and VIIRS Hot Spots**. Built with Vue 3, MapLibre GL, and Tailwind CSS.

---

## 🛠️ Stack Quick Reference

* **Framework:** [Vue 3](https://vuejs.org/) (Composition API with `<script setup lang="ts">`)
* **State Management:** [Pinia](https://pinia.vuejs.org/)
* **Styling:** [Tailwind CSS v4](https://tailwindcss.com/)
* **UI Primitives:** [Reka UI](https://reka-ui.com/) (accessible headless components)
* **Composables:** [VueUse](https://vueuse.org/) (`@vueuse/core`)
* **Map & Spatial:** [MapLibre GL JS](https://maplibre.org/) + `@mapbox/mapbox-gl-draw` + `@turf/turf`
* **Satellite Imagery:** Esri World Imagery (high-resolution optical basemap)
* **Build Tool:** [Vite](https://vite.dev/)

> [!IMPORTANT]
> **Architecture & Design Guide:** Before creating new components or utilities, read [docs/frontend_desing.md](../../docs/frontend_desing.md) for the mandatory implementation hierarchy (Check VueUse first ➔ Check Reka UI second ➔ Custom component only as last resort) and dumb vs. logic component separation rules.
>
> **Spatial Queries Note:** In the future, spatial filtering will run on a backend API powered by PostgreSQL + PostGIS. Currently, spatial queries are mocked client-side using Turf.js over a local DuckDB sample dataset.

---

## 🚀 Getting Started

From the monorepo root:

```bash
# 1. Export sample dataset from DuckDB pipeline
just sample-data

# 2. Install dependencies
just frontend install

# 3. Start development server
just frontend dev

# 4. Run typecheck & build
just frontend build
```

Or directly inside `apps/frontend`:

```bash
npm install
npm run dev
```

---

## 📜 Available Scripts

| Command | Description |
| :--- | :--- |
| `npm run dev` | Starts the Vite dev server with HMR at `http://localhost:5173` |
| `npm run build` | Full production build with `vue-tsc` type-checking |
| `npm run type-check` | Runs `vue-tsc --build` |
| `npm run lint` | Runs `oxlint` (Rust-speed linter) and `eslint` |
| `npm run format` | Auto-formats code with Prettier |

---

## 🧩 Component Standards

* **Dumb Components (`src/components/common/`, `src/components/ui/`):** Purely presentational, accepts props, emits events, zero direct store/API imports.
* **Logic Components (`src/components/features/`, `src/views/`):** Connects to Pinia stores, coordinates state, handles map/query events.
* **Reka UI Wrappers (`src/components/ui/`):** Never scatter unstyled Reka UI primitives across features; wrap them in dedicated UI components styled with Tailwind CSS v4.
