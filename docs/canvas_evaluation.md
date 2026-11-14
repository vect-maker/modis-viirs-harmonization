# Business Model Canvas Evaluation: FIRMS Wildfire Harmonizer

> **Scope:** Evaluation of the `MODELO CANVAS` against the [NASA Space Apps Challenge 2026](hackathon_challenge.md) requirements, the [video transcript](video_transcript.md), and the current codebase in `apps/`. Evaluated for both **short-term hackathon viability** and **long-term NGO/open-source operation**.

---

## Executive Summary

| Dimension | Verdict | Score | Key Takeaway |
| :--- | :--- | :---: | :--- |
| **Challenge Alignment** | Strong on core problem, partial on delivery | **7.5 / 10** | Directly targets the MODIS→VIIRS continuity gap, but key UI/API features (live harmonized calendar, historical median comparison) are not yet wired end-to-end. |
| **Canvas Completeness** | 8 of 9 blocks populated; 1 critical gap | **6.5 / 10** | *Fuente de Ingresos* has only a non-profit note with zero funding mechanisms; *Relación con Clientes* and *Canales* overpromise relative to team capacity. |
| **Internal Coherence** | Moderate friction | **5.5 / 10** | Cost structure (servers, storage, security, support) is unfunded; consumer social channels (Instagram/Facebook) mismatch institutional B2G users. |
| **Hackathon Viability** | Viable with targeted edits | **8.0 / 10** | Honest about harmonization being in development; fixing the funding & channel blocks will make the pitch much stronger for judges. |
| **Post-Hackathon Viability** | **High Risk** as currently written | **4.5 / 10** | Operating a 20+ year spatial PostGIS DB + offering institutional support with zero revenue/grant model is unsustainable. |

---

## 1. Challenge & Codebase Reality Check

Before evaluating the Canvas claims, here is how the **actual repository** compares against the **NASA Space Apps Challenge 2026** requirements and the **Canvas claims**:

| Requirement / Canvas Claim | Source | Current Repo Status | Evidence in Codebase |
| :--- | :--- | :--- | :--- |
| **NASA FIRMS MODIS + VIIRS ingestion** | Challenge & Canvas | **Implemented** | `apps/pipeline/pipeline/fetcher.py` fetches `modis`, `viirs-snpp`, `viirs-jpss1` into Parquet. |
| **Sensor fusion (Silver & Star Schema Gold)** | Canvas (*Recursos Clave*) | **Implemented** | `sql/fuse_datasets.sql` & `sql/normalize_star_schema.sql` unify columns, confidence, and UUIDv5 keys. |
| **MODIS–VIIRS Harmonization** | Challenge Part 1 & Canvas | **Prototype / In Progress** | `sql/test_spatial_harmonization.sql` implements a 5-class spatio-temporal prototype (`~2 km` / `1 hr` bins + weight $w_i$), documented in `apps/report/sections/02-methods.typ`. **Not yet applied to frontend calendar.** |
| **Interactive Map & ROI Drawing** | Challenge Part 2 & Canvas | **Implemented** | `FireMap.vue` + `@mapbox/mapbox-gl-draw` + `@turf/turf` compute ROI area ($\text{km}^2$) and filter sample hotspots (`sample_hotspots.json`, Nicaragua 2024, 5,000 pts). |
| **Burning Activity Calendar** | Challenge Part 2 & Canvas | **Partial** | `HistoricalCalendar.vue` renders Nicaragua `2000–2025` (`historical_monthly.json`), **but** explicitly notes: *"Map area and date filters do not apply here. Counts are not harmonized; observation coverage is unverified."* |
| **Historical Median / Anomaly Comparison** | Challenge Part 2 | **Missing in UI** | `apps/backend/analytics/AnomalyDetector.py` exists, but the frontend calendar only shows raw monthly log-scale counts without historical median baselines. |
| **Live Backend API Integration** | Canvas (*Actividades Clave*) | **Partial / Disconnected** | `apps/backend/main.py` exposes `/` and `/hotspots`, plus `WeatherDataClient`, but `apps/frontend` currently loads static JSON (`sample_hotspots.json`, `historical_monthly.json`) rather than live API queries. |
| **CSV & Analytics Export** | Challenge Part 2 & Canvas | **Partial** | `HotspotCsvExport.vue` exports filtered map hotspots as RFC-4180 CSV; downloadable calendar/analytics charts are not yet implemented. |

> [!WARNING]
> **Pitch Accuracy Check:** Your Canvas wisely says *"Armonización en desarrollo"*, which is honest and accurate. However, *"Consultas por ubicación y periodo"* and *"Mapas y calendarios interactivos"* currently operate on a **static Nicaragua sample** rather than a live global/regional API—be transparent about this scope during hackathon judging.

---

## 2. 9-Block Completeness & Coherence Audit

### 1. Segmento de Clientes — *Score: 7 / 10*
- **What's on the Canvas:** Early-warning teams, firefighters & civil protection; environmental authorities & protected area managers; institutions needing territorial analysis & specialized support.
- **Strengths:** Directly matches `docs/hackathon_challenge.md` target audience.
- **Gaps:**
  - Missing **scientific/academic researchers** (explicitly mentioned in your *Propuesta de Valor* and in the challenge brief, yet omitted from *Segmento de Clientes*!).
  - No **geographic or tier prioritization** (e.g., starting with Latin America / Nicaragua / Argentina like CONAE's Chilecito case study vs. global).
  - *B2G/Institutional buyers* have very different procurement and trust needs than *NGOs/researchers*.

### 2. Propuesta de Valor — *Score: 7.5 / 10*
- **What's on the Canvas:** Free centralized MODIS+VIIRS access; friendly UI without advanced GIS skills; interactive maps & calendars; location/period queries; easy data download; harmonization in development.
- **Strengths:** Clear, user-centered, and avoids overclaiming on harmonization.
- **Gaps:**
  - **Buries the lead:** The unique value from the challenge is **solving the MODIS retirement discontinuity** and **comparing current fire activity against historical baselines/medians**—this should be headline-level, not a final bullet.
  - **Missing "why not just use NASA FIRMS Web?"**: NASA FIRMS already offers free maps and CSV downloads. Your differentiator is **cross-sensor historical harmonization + burning activity calendar**.

### 3. Canales — *Score: 4.5 / 10 (Major Gap)*
- **What's on the Canvas:** Instagram, Facebook, LinkedIn; web app; NASA Space Apps; email for institutions/allies.
- **Strengths:** NASA Space Apps and direct institutional email are realistic for early discovery.
- **Gaps:**
  - **Channel–Audience Mismatch:** Firefighters, civil protection agencies, and environmental ministries do not adopt operational monitoring tools via Instagram or Facebook.
  - Missing **domain-native channels**: OSGeo / GIS communities, NASA FIRMS user forums, CONAE / regional disaster-risk networks (e.g., CEPREDENAC, CIIFEN), GitHub/open-source communities, and academic/preprint distribution (e.g., your Typst technical report in `apps/report/`).

### 4. Relación con Clientes — *Score: 5.5 / 10*
- **What's on the Canvas:** Self-service platform; guides & training; technical support & institutional accompaniment; user feedback.
- **Strengths:** Self-service + user feedback fits an open web platform.
- **Gaps:**
  - **Resource Trap:** *"Soporte técnico y acompañamiento institucional"* + *"Guías y capacitación"* are high-touch B2G services that conflict with a zero-revenue NGO model. Without dedicated funding or partner-led training, this will bottleneck a small dev team.

### 5. Fuente de Ingresos — *Score: 2 / 10 (Critical Gap)*
- **What's on the Canvas:** *"Nota: Funcionamos similar a una ONG. No lucrativo."*
- **Gaps:**
  - **Non-profit ≠ No funding model.** Even an NGO needs inflows to pay for servers, PostGIS storage, backups, and developer time.
  - Missing concrete sustainability streams:
    - Public/international grants (climate, disaster risk reduction, Earth observation).
    - Cloud infrastructure credits (AWS Open Data / Azure AI for Earth / Google Cloud credits).
    - Institutional co-funding or B2G customization/integration contracts (while keeping the core web tool free).
    - Open-source sponsorships / academic consortium backing.

### 6. Recursos Clave — *Score: 8 / 10*
- **What's on the Canvas:** Historical MODIS/VIIRS data from NASA FIRMS; dev & geospatial team; web app, pipeline & spatial DB; servers & storage; validated harmonization methodology.
- **Strengths:** Very well aligned with the actual stack (DuckDB, PostGIS, FastAPI, Vue 3/MapLibre).
- **Gaps:**
  - Minor: *"Metodología de armonización validada"* is still a **prototype** (`sql/test_spatial_harmonization.sql`), so it's a *developing* resource rather than an already-validated one.
  - Missing **NASA FIRMS API key / rate-limit quota** and **open-source codebase/IP**.

### 7. Actividades Clave — *Score: 8 / 10*
- **What's on the Canvas:** Download/clean/update satellite data; develop & validate MODIS–VIIRS harmonization; integrate map, API & historical calendar; user testing & platform maintenance.
- **Strengths:** Accurately reflects the engineering roadmap (`fetcher.py` → `fuse_datasets.sql` → harmonization → FastAPI + Vue integration).
- **Gaps:**
  - Missing **automated/scheduled ETL & data quality monitoring** (essential for early-warning credibility) and **scientific/peer validation** of the harmonization weights.

### 8. Socios Clave — *Score: 7.5 / 10*
- **What's on the Canvas:** NASA FIRMS/Earthdata (open data provider); firefighters, civil protection & environmental authorities (allies); conservation orgs & tech infrastructure providers.
- **Strengths:** Good separation of data provider, domain allies, and infra partners.
- **Gaps:**
  - **Overlapping roles:** Firefighters and environmental authorities appear in both *Socios Clave* and *Segmento de Clientes*. Clarify *who* is a **validation/co-design partner** (e.g., CONAE, national forestry/fire agencies, universities) vs. an **end user**.
  - Explicitly name **cloud/infra grant partners** (AWS/Azure/GCP) and **academic/scientific validators** for the harmonization method.

### 9. Estructura de Costos — *Score: 6.5 / 10*
- **What's on the Canvas:** Software dev & maintenance; processing, hosting & storage; backups & security; training & technical support.
- **Strengths:** Captures the real cost drivers of a PostGIS + FastAPI + ETL platform.
- **Gaps:**
  - **No cost-tiering or mitigation strategy:** Storing 20+ years of global MODIS+VIIRS hotspots in PostGIS is expensive if unbounded. Scoping to **regional archives (e.g., Central/South America)** or **pre-aggregated Parquet/DuckDB tiles** dramatically lowers hosting costs and makes the NGO model viable.

---

## 3. Marketing Council Review (Simulated)

> *Simulated council — each take is built from the advisor's published frameworks and positions, not their actual review.*

### The Question Before the Council
How should **FIRMS Wildfire Harmonizer** sharpen its positioning, target audience, and channels so it is credible to both NASA Space Apps judges and real fire-management institutions?

### Seated: April Dunford, Seth Godin, Byron Sharp (Dissenter), Rory Sutherland

#### **April Dunford** — *Positioning against real alternatives*
Your biggest competitor isn't another startup—it's **NASA FIRMS Web + manual Excel/QGIS workflows**. Every fire analyst and researcher already has free access to FIRMS maps and CSVs. If your *Propuesta de Valor* leads with "free access to MODIS and VIIRS," you sound like a redundant wrapper. Flip the causal chain:
1. **Competitive Alternative:** Using raw FIRMS exports where MODIS and VIIRS counts can't be compared across 2012–present.
2. **Unique Attribute:** Point-level spatio-temporal harmonization + a 25-year burning activity calendar.
3. **Value:** Fire managers can tell whether *this* fire season is genuinely anomalous vs. a sensor-resolution artifact.
**Bottom line:** Position as a **historical fire-regime & anomaly calendar**, not a generic "satellite fire map."

#### **Seth Godin** — *Smallest viable audience*
Trying to serve firefighters, civil protection, environmental ministries, territorial analysts, *and* Instagram followers at the same time will dilute your product until nobody relies on it. Who is the **smallest viable audience** that would miss you if you disappeared tomorrow? Pick **one** concrete beachhead—for example, **regional environmental analysts / forestry researchers in Nicaragua (or CONAE-style early-warning scientists)** who already have your 2000–2025 calendar data. Delight them first; let them carry you into civil protection.
**Bottom line:** Drop consumer social media and pick one beachhead user group to overwhelm with usefulness.

#### **Byron Sharp** *(Designated Dissenter)* — *Availability beats narrow targeting*
Godin's "smallest viable audience" is fine for a weekend hackathon, but in the real world, **niche products die from low mental and physical availability**. Fire managers don't wake up looking for a "harmonized MODIS–VIIRS tool"—they reach for whatever tool is already bookmarked in their emergency-response workflow when a fire season starts. Don't hide in a tiny academic corner; make the tool **immediately usable without login, embeddable, and linked from existing GIS/disaster portals** so it's physically available at the moment of need.
**Bottom line:** Maximize frictionless physical availability (zero-login web access + open API/embed) rather than over-segmenting your audience.

#### **Rory Sutherland** — *Psycho-logic & costly signaling*
Writing *"Nota: Funcionamos similar a una ONG. No lucrativo"* in the revenue box accidentally signals **"hobby project that might go offline next month."** In institutional B2G and emergency response, **free without visible institutional backing feels risky, not generous**. Paradoxically, showing *how* the platform is funded (e.g., cloud credits, university/agency partnership, or open-source governance) increases trust far more than promising "free." Also, showing **confidence intervals / unverified-coverage badges** (which your `HistoricalCalendar.vue` already does!) is a brilliant trust signal—it proves scientific honesty.
**Bottom line:** Reframe "free NGO" into **"open-source public infrastructure backed by institutional/grant partners"** so authorities trust it.

### Where the Council Disagrees
1. **Beachhead Focus vs. Broad Availability** — *Godin* says narrow to one specific analyst group (e.g., Central/South American forestry researchers); *Sharp* warns that over-targeting caps adoption and says focus on frictionless physical availability across all category users. **What settles it:** For the hackathon, pick **one** clear primary persona + region (e.g., Nicaragua/LatAm fire analysts) for the demo, while keeping the web app zero-login and open-URL for everyone.

---

## 4. Prioritized Action Plan (To Fix Your Canvas)

| Priority | Block | Action to Take |
| :---: | :--- | :--- |
| **1. Critical** | **Fuente de Ingresos** | Replace the blank NGO note with 3 concrete sustainability pillars: **(a)** Cloud/infra credits (AWS/Azure/GCP for Earth Observation), **(b)** Climate/EO grants & academic partnerships, **(c)** Optional paid institutional customization/hosting while keeping the public platform free. |
| **2. Critical** | **Canales** | Replace Instagram/Facebook with institutional & technical channels: **GIS/OSGeo communities, NASA FIRMS/Earthdata networks, regional disaster-risk agencies, academic publications/preprints, and GitHub**. Keep LinkedIn + direct institutional email. |
| **3. High** | **Propuesta de Valor** | Lead with the **core differentiator**: *"Continuidad histórica MODIS–VIIRS y calendario de anomalías de fuego"*—explicitly contrasting against raw, non-comparable FIRMS data. |
| **4. High** | **Relación con Clientes** | Scope support realistically: **self-service + open documentation/tutorials** for general users, and **co-design/technical accompaniment only with formal partner institutions** (to avoid unfunded support burn). |
| **5. Medium** | **Segmento de Clientes** | Explicitly add **researchers & environmental scientists** (matching your Value Prop), and define a **beachhead region** (e.g., Latin America / Nicaragua–Argentina case studies) before global expansion. |
| **6. Medium** | **Estructura de Costos** | Add a **cost-control note**: regional/country-scoped Parquet + DuckDB/PostGIS architecture to keep hosting lean. |

---

## 5. Ready-to-Use Revised Canvas Text (Spanish)

You can copy-paste these refined bullets directly into your `MODELO CANVAS` slide:

- **Socios Clave:**
  - NASA FIRMS / Earthdata (datos abiertos satelitales).
  - Universidades y agencias espaciales/ambientales (validación científica de la armonización).
  - Organizaciones de conservación y programas de créditos cloud / infraestructura abierta.
- **Actividades Clave:**
  - Ingesta, depuración y actualización automatizada de datos MODIS y VIIRS.
  - Desarrollo y validación científica de la armonización MODIS–VIIRS.
  - Integración de mapa interactivo, API espacial y calendario histórico de anomalías.
  - Pruebas de usabilidad con gestores de fuego y mantenimiento de la plataforma.
- **Recursos Clave:**
  - Archivo histórico MODIS y VIIRS (2000–presente) de NASA FIRMS.
  - Equipo de desarrollo web e ingeniería de datos geoespaciales.
  - Pipeline ETL (DuckDB/Parquet), base espacial (PostGIS), API y aplicación web.
  - Metodología de armonización espacio-temporal en validación.
- **Propuesta de Valor:**
  - Resolver la discontinuidad histórica entre MODIS y VIIRS mediante un calendario interactivo de actividad y anomalías de fuego, permitiendo comparar temporadas actuales con líneas base históricas sin requerir conocimientos GIS avanzados:
    - Armonización MODIS–VIIRS (en desarrollo) para comparaciones históricas consistentes.
    - Calendario interactivo y mapa por área de interés (AOI) y periodo.
    - Acceso abierto, sin registro y con descarga directa en CSV.
- **Relación con Clientes:**
  - Autoservicio abierto con documentación y guías prácticas.
  - Canal de retroalimentación y reportes de comunidad (GitHub / formulario).
  - Acompañamiento técnico y co-diseño focalizado únicamente en instituciones aliadas.
- **Canales:**
  - Aplicación web abierta (acceso directo sin fricción) y repositorio GitHub.
  - NASA Space Apps, redes Earth Observation / OSGeo y comunidad NASA FIRMS.
  - LinkedIn, publicaciones técnicas y contacto institucional directo por correo.
- **Segmento de Clientes:**
  - **Primario (Beachhead):** Analistas ambientales, investigadores y gestores de áreas protegidas (enfoque inicial regional: Latinoamérica).
  - **Secundario:** Equipos de alerta temprana, bomberos y protección civil para planificación preventiva.
- **Estructura de Costos:**
  - Desarrollo y mantenimiento del software open-source.
  - Alojamiento, cómputo y almacenamiento espacial optimizado (Parquet/PostGIS).
  - Seguridad, respaldos y automatización del pipeline.
  - Documentación y soporte acotado a aliados.
- **Fuente de Ingresos / Sostenibilidad (Modelo Abierto / ONG):**
  - **Acceso público gratuito** a la plataforma base.
  - **Créditos de infraestructura cloud** para datos abiertos y observación de la Tierra.
  - **Fondos concursables y grants** de clima, biodiversidad y gestión de riesgo.
  - **Convenios institucionales** para despliegues regionales a medida, APIs dedicadas o capacitación.
