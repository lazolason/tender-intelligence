# Tender Intelligence System — Complete Architecture & Codebase Guide

> **Version:** 2.1 | **Client:** Mexel Energy Sustain | **Stack:** Python + Static PWA + SQLite
> **Last Updated:** 2026-04-05

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Data Flow Pipeline](#data-flow-pipeline)
4. [Component Deep Dive](#component-deep-dive)
   - [Scraping Layer](#scraping-layer)
   - [Classification Engine](#classification-engine)
   - [Scoring Engine](#scoring-engine)
   - [Database Layer](#database-layer)
   - [Dashboard Frontend](#dashboard-frontend)
   - [Flask API](#flask-api)
   - [Automation & Scheduling](#automation--scheduling)
5. [Database Schema](#database-schema)
6. [Configuration & Environment](#configuration--environment)
7. [Security Model](#security-model)
8. [Testing & CI/CD](#testing--cicd)
9. [Deployment Architecture](#deployment-architecture)
10. [Developer Guide](#developer-guide)
11. [Glossary](#glossary)

---

## Executive Summary

The **Tender Intelligence System** is an automated tender discovery, classification, and scoring platform built for **Mexel Energy Sustain**, a South African thermal efficiency services company specializing in cooling water treatment, chemical dosing, and IoT-enabled monitoring for power generation, mining, and industrial clients.

### Business Purpose

The system solves three core problems:

1. **Discovery** — Automatically scrapes 11+ South African government, municipal, and state-owned enterprise (SOE) tender portals daily
2. **Filtering** — Classifies tenders using a three-profile keyword matching system to identify only those relevant to Mexel's core competencies
3. **Prioritization** — Scores qualified tenders using a composite algorithm (fit + industry value) to surface HIGH/MEDIUM/LOW priority opportunities

### Key Metrics

| Metric | Value |
|--------|-------|
| Data Sources | 11+ portals (municipalities, SOEs, National Treasury, water boards) |
| Scraping Methods | HTTP requests + BeautifulSoup, Selenium (headless Chrome), REST APIs |
| Classification Profiles | 3 (Profile A: Product, Profile B: System+Action, Exclusions) |
| Scoring Dimensions | 2 (Fit Score 60%, Industry Score 40%) |
| Priority Levels | 3 (HIGH ≥7.0, MEDIUM ≥4.5, LOW <4.5) |
| Dashboard | Static PWA with virtual scrolling, offline support, analytics |
| Storage | SQLite (primary), Excel (legacy compatibility) |
| Alerts | Email, Slack, SMS (Twilio) — all configurable |

---

## System Architecture

### High-Level Component Diagram

```mermaid
graph TB
    subgraph "Data Sources"
        A1[Municipalities<br/>Cape Town]
        A2[SOEs<br/>Eskom, Rand Water, Transnet, etc.]
        A3[National Treasury<br/>eTenders Portal]
        A4[Water Boards<br/>Umgeni, Magalies, Lepelle]
        A5[Joburg Water<br/>Selenium]
        A6[Eskom Bulletin<br/>API + Selenium]
    end

    subgraph "Scraping Layer (Python)"
        B1[tenderscan.py<br/>Main Orchestrator]
        B2[ThreadPoolExecutor<br/>Parallel Execution]
        B3[ScraperMonitor<br/>Circuit Breaker]
    end

    subgraph "Processing Pipeline"
        C1[TenderValidator<br/>Data Validation]
        C2[Semantic Dedup<br/>ML-based]
        C3[Classify Engine<br/>Keyword Rules]
        C4[Scoring Engine<br/>Composite Score]
    end

    subgraph "Storage Layer"
        D1[(SQLite Database<br/>tenders.db)]
        D2[PDF Analysis<br/>Table]
        D3[Bid Outcomes<br/>Table]
        D4[Excel Log<br/>Legacy]
    end

    subgraph "Output & Alerts"
        E1[output/new_tenders.json]
        E2[output/summary.txt]
        E3[output/scraper_health.json]
        E4[Email Alerts]
        E5[Slack/SMS Alerts]
    end

    subgraph "Dashboard"
        F1[sync_dashboard.py<br/>Data Sync]
        F2[dashboard/index.html<br/>Static PWA]
        F3[dashboard/tenders.json<br/>Client Data]
    end

    subgraph "API Layer"
        G1[app.py<br/>Flask API]
        G2[/api/run/daily]
        G3[/api/summarize]
        G4[/api/bids]
    end

    subgraph "Automation"
        H1[daily_runner.py<br/>Daily Workflow]
        H2[weekly_report.py<br/>Weekly Report]
        H3[launchd / cron<br/>Scheduling]
    end

    A1 --> B1
    A2 --> B1
    A3 --> B1
    A4 --> B1
    A5 --> B1
    A6 --> B1

    B1 --> B2
    B2 --> B3
    B3 --> C1
    C1 --> C2
    C2 --> C3
    C3 --> C4
    C4 --> D1
    D1 --> D2
    D1 --> D3
    D1 --> D4

    C4 --> E1
    C4 --> E2
    B3 --> E3
    C4 --> E4
    B3 --> E5

    D1 --> F1
    E1 --> F1
    F1 --> F3
    F3 --> F2

    G1 --> G2
    G1 --> G3
    G1 --> G4
    G2 --> H1
    D1 --> G1

    H3 --> H1
    H3 --> H2
    H1 --> B1
    H1 --> F1
```

### Module Dependency Graph

```mermaid
graph LR
    subgraph "Core Engines"
        CE[classify_engine.py]
        SE[scoring_engine.py]
        KR[keyword_rules.py]
    end

    subgraph "Main Pipeline"
        TS[tenderscan.py]
        DR[daily_runner.py]
        WR[weekly_report.py]
        SD[sync_dashboard.py]
    end

    subgraph "Scrapers"
        MUN[municipalities.py]
        SOE[soes.py]
        NTS[national_treasury_selenium.py]
        JWS[joburg_water_selenium.py]
        ESK[eskom_direct.py]
        WB[water_boards.py]
    end

    subgraph "Utils"
        DB[db_writer.py]
        DV[data_validator.py]
        SD2[semantic_duplicate_detector.py]
        DD[duplicate_detector.py]
        PA[pdf_analyzer.py]
        SM[scraper_monitor.py]
        RT[retry_tools.py]
        LT[logging_tools.py]
    end

    subgraph "Frontend"
        DH[dashboard/index.html]
        DJ[dashboard/js/modules/]
        DS[dashboard/service-worker.js]
    end

    subgraph "API"
        FL[app.py]
    end

    KR --> CE
    CE --> TS
    SE --> TS
    TS --> DB
    TS --> DV
    TS --> SD2
    TS --> SM
    TS --> LT
    TS --> PA

    MUN --> TS
    SOE --> TS
    NTS --> TS
    JWS --> TS
    ESK --> TS
    WB --> TS

    RT --> MUN
    RT --> SOE
    RT --> NTS
    RT --> ESK
    RT --> WB

    DD --> DB
    SD2 --> TS

    DB --> SD
    SD --> DH
    DH --> DJ
    DH --> DS

    FL --> DB
    DR --> TS
    DR --> SD
    WR --> FL
```

---

## Data Flow Pipeline

### End-to-End Pipeline

```mermaid
sequenceDiagram
    participant S as Scheduler
    participant DR as daily_runner.py
    participant TS as tenderscan.py
    participant SC as Scrapers (parallel)
    participant TV as TenderValidator
    participant SD as Semantic Dedup
    participant CE as Classify Engine
    participant SE as Scoring Engine
    participant DB as DatabaseWriter
    participant PA as PDF Analyzer
    participant OUT as Output Files
    participant AL as Alert System
    participant SYN as sync_dashboard.py
    participant DASH as Dashboard PWA

    S->>DR: Trigger daily run (08:00)
    DR->>TS: Import & execute
    TS->>SC: ThreadPoolExecutor (5 workers)

    par Parallel Scraping
        SC-->>TS: Municipalities tenders
        SC-->>TS: SOEs tenders
        SC-->>TS: Water Boards tenders
        SC-->>TS: National Treasury (Selenium)
        SC-->>TS: Joburg Water (Selenium)
        SC-->>TS: Eskom Bulletin (API)
    end

    TS->>SD: Cross-source semantic dedup
    SD-->>TS: Deduplicated tenders

    TS->>TV: Validate each tender
    TV-->>TS: Valid/Invalid results

    TS->>CE: Classify valid tenders
    CE-->>TS: MEXEL or EXCLUDED

    TS->>SE: Score MEXEL tenders
    SE-->>TS: Fit + Industry + Composite

    TS->>DB: Write to SQLite
    DB-->>TS: was_added confirmation

    alt URL ends with .pdf
        TS->>PA: Analyze PDF
        PA-->>TS: Requirements, deadlines, values
        TS->>DB: Save PDF analysis
    end

    TS->>OUT: new_tenders.json, summary.txt
    TS->>AL: Multi-channel alerts (if urgent)

    DR->>SYN: Sync dashboard
    SYN->>DB: Load tenders from SQLite
    DB-->>SYN: Tender records
    SYN->>DASH: Generate tenders.json
    SYN->>DASH: Update index.html

    DR-->>S: Complete with results
```

### Tender Lifecycle State Machine

```mermaid
stateDiagram-v2
    [*] --> Scraped: Scraper discovers tender
    Scraped --> Validated: TenderValidator passes
    Scraped --> Discarded: Validation fails

    Validated --> Classified: Classify Engine runs
    Validated --> Discarded: Duplicate detected

    Classified --> Excluded: NEGATIVE match or no signal
    Classified --> Mexel: Profile A or B match

    Mexel --> Scored: Scoring Engine runs
    Scored --> HighPriority: Composite ≥ 7.0
    Scored --> MediumPriority: Composite ≥ 4.5
    Scored --> LowPriority: Composite < 4.5

    HighPriority --> Database: Written to SQLite
    MediumPriority --> Database
    LowPriority --> Database

    Excluded --> Logged: Exclusion logged
    Excluded --> [*]

    Database --> Dashboard: sync_dashboard.py
    Database --> Alerts: If urgent & HIGH
    Database --> [*]
```

---

## Component Deep Dive

### Scraping Layer

The scraping layer consists of **6 active scraper modules** that extract tender data from South African government and SOE portals. Each scraper returns a standardized dictionary format.

#### Scraper Architecture

```mermaid
graph TB
    subgraph "Aggregator Functions"
        A1[scrape_all_municipalities]
        A2[scrape_all_soes]
        A3[scrape_all_water_boards]
    end

    subgraph "Individual Scrapers"
        B1[CapeTownScraper<br/>requests + BS4]
        B2[Rand Water<br/>requests + BS4]
        B3[Transnet<br/>requests + BS4]
        B4[Eskom Direct<br/>API + Selenium fallback]
        B5[Anglo American<br/>requests + BS4]
        B6[Harmony Gold<br/>requests + BS4]
        B7[Seriti<br/>requests + BS4]
        B8[Umgeni Water<br/>requests + BS4]
        B9[Magalies Water<br/>requests + BS4]
        B10[Lepelle Water<br/>requests + BS4]
        B11[National Treasury<br/>Selenium]
        B12[Joburg Water<br/>Selenium]
    end

    A1 --> B1
    A2 --> B2
    A2 --> B3
    A2 --> B4
    A2 --> B5
    A2 --> B6
    A2 --> B7
    A3 --> B8
    A3 --> B9
    A3 --> B10
```

#### Scraper Comparison Table

| Scraper | Source | Method | Pagination | Auth | Status |
|---------|--------|--------|------------|------|--------|
| `municipalities.py` | Cape Town | requests + BS4 | Single page | None | ✅ Active |
| `soes.py` (Rand Water) | randwater.co.za | requests + BS4 | 3 pages | None | ✅ Active |
| `soes.py` (Transnet) | etenders.gov.za | requests + BS4 | Single page | None | ✅ Active |
| `eskom_direct.py` | tenderbulletin.eskom.co.za | REST API → Selenium | 10 pages | None | ✅ Active |
| `soes.py` (Anglo) | angloamerican.com | requests + BS4 | Single page | None | ✅ Active |
| `soes.py` (Harmony) | harmony.co.za | requests + BS4 | Single page | None | ✅ Active |
| `soes.py` (Seriti) | seritiza.com | requests + BS4 | Single page | None | ✅ Active |
| `water_boards.py` (Umgeni) | umngeni-uthukela.co.za | requests + BS4 | Single page | None | ✅ Active |
| `water_boards.py` (Magalies) | magalieswater.co.za | requests + BS4 | Single page | None | ✅ Active |
| `water_boards.py` (Lepelle) | lepellewater.co.za | requests + BS4 | Single page | None | ✅ Active |
| `national_treasury_selenium.py` | etenders.gov.za | Selenium (Chrome) | Multi-page | None | ✅ Active |
| `joburg_water_selenium.py` | johannesburgwater.co.za | Selenium (DataTables) | Single page | None | ✅ Active |

#### Standardized Tender Schema

Every scraper returns dictionaries with these fields:

```python
{
    "ref": str,           # Unique reference number
    "title": str,         # Tender title
    "description": str,   # Tender description
    "client": str,        # Issuing organization
    "source": str,        # Scraper/source name
    "url": str,           # Link to tender page
    "closing_date": str,  # ISO format date
    "category": str,      # Pre-classification (set by classify_engine)
    "reason": str,        # Classification reason
    "short_title": str,   # Sanitized title for folders
}
```

#### Resilience Pattern

All scrapers use a layered resilience approach:

```mermaid
graph LR
    A[HTTP Request] --> B{safe_get / safe_driver_get}
    B -->|Success| C[Parse Response]
    B -->|Failure| D[Exponential Backoff]
    D --> E[Retry 1 — 2s delay]
    E --> B
    E -->|Fail| F[Retry 2 — 4s delay]
    F --> B
    F -->|Fail| G[Retry 3 — 8s delay]
    G --> B
    G -->|Fail| H[Log Error & Return Empty]

    C --> I{Parse Error?}
    I -->|Yes| J[Skip Item, Continue]
    I -->|No| K[Return Tender Dict]
```

#### Parallel Execution Model

```mermaid
graph TB
    subgraph "ThreadPoolExecutor (max_workers=5)"
        W1[Worker 1: Municipalities]
        W2[Worker 2: SOEs]
        W3[Worker 3: Water Boards]
        W4[Worker 4: National Treasury]
        W5[Worker 5: Joburg Water]
    end

    subgraph "ScraperMonitor"
        M1[Circuit Breaker<br/>per source]
        M2[Health Tracking<br/>success rate, avg time]
        M3[Failure Alerting<br/>3 consecutive failures]
    end

    W1 --> M1
    W2 --> M1
    W3 --> M1
    W4 --> M1
    W5 --> M1

    M1 --> M2
    M2 --> M3

    subgraph "Global Timeout"
        T[300 second timeout<br/>cancels remaining futures]
    end

    M3 --> T
```

---

### Classification Engine

The classification engine (`classify_engine.py`) implements a **three-profile matching system** that determines whether a tender is relevant to Mexel's business.

#### Classification Logic Flow

```mermaid
flowchart TD
    A[Raw Title + Description] --> B[clean: Normalize text]
    B --> C[Keyword Matching]

    C --> D{NEGATIVE_KEYWORDS match?}
    D -->|Yes| E{STRONG_MATCH_KEYWORDS present?}
    E -->|Yes| F[OVERRIDE: Include — Profile A signal]
    E -->|No| G[EXCLUDE: Out of scope]

    D -->|No| H{STRONG_MATCH_KEYWORDS match?}
    H -->|Yes| I[INCLUDE: Profile A — The Product]
    H -->|No| J{SYSTEM_KEYWORDS AND ACTION_KEYWORDS both match?}
    J -->|Yes| K[INCLUDE: Profile B — System + Action]
    J -->|No| G

    F --> L[Return: category=MEXEL]
    I --> L
    K --> L
    G --> M[Return: category=EXCLUDED]
```

#### Keyword Profile Details

**Profile A: The Product (Automatic Match)**
These keywords represent Mexel's core technologies and services. Any match triggers immediate inclusion.

| Category | Examples |
|----------|----------|
| Brand & Product | `mexel`, `mexel 432`, `mexsteam`, `film forming amine` |
| Core Technologies | `antiscalant`, `oxidizing biocide`, `surfactant`, `ffa` |
| Service Metrics | `condenser performance`, `thermal efficiency`, `heat rate`, `back pressure` |
| Service Delivery | `iot dosing`, `automated dosing`, `precision dosing` |
| Standards | `asme ptc 12.2`, `measurement and verification`, `m&v protocol` |
| Data Center | `pue`, `power usage effectiveness`, `legionella control` |

**Profile B: System + Action (Paired Match)**
Requires BOTH a system keyword AND an action keyword to match.

| Systems (B1) | Actions (B2) |
|--------------|--------------|
| `power plant`, `power station` | `efficiency`, `optimization`, `performance improvement` |
| `cooling tower`, `condenser` | `dosing`, `treatment`, `application` |
| `boiler`, `steam generator` | `monitoring`, `performance tracking` |
| `heat exchanger`, `chiller` | `fouling`, `scaling`, `corrosion prevention` |
| `data center`, `crac`, `crah` | `baseline`, `intervention`, `restoration` |
| `smelter`, `furnace cooling` | `supply`, `delivery`, `installation` |

**Exclusions (Negative Keywords)**
Any match triggers immediate exclusion unless overridden by Profile A.

| Category | Examples |
|----------|----------|
| Construction | `construction of`, `civil works`, `structural steel` |
| Building HVAC | `split unit`, `office air conditioning`, `building hvac` |
| Non-cooling Services | `security service`, `cleaning service`, `garden service` |
| Electrical | `switchgear`, `transformer`, `substation`, `transmission` |
| Water/Wastewater | `potable water`, `drinking water`, `sewage` |
| Staffing | `resourcing`, `personnel`, `appointment of` |
| Office | `office furniture`, `painting`, `plumbing` |

#### Matched Keywords Building

The engine builds a `matched_keywords` list that includes:
1. All matched keywords from the triggering profile
2. Composite aliases (e.g., `chemical` + `dosing` → `chemical dosing`)
3. Context tokens (`industrial`, `utility`, `plant`)

---

### Scoring Engine

The scoring engine (`scoring_engine.py`) evaluates qualified tenders on two dimensions and produces a composite priority score.

#### Scoring Architecture

```mermaid
graph TB
    subgraph "Input"
        T[Tender: title, description, client, category]
    end

    subgraph "Fit Score (60% weight)"
        F1[Base: 5/10]
        F2[Category boost: +2 if MEXEL]
        F3[Strong keywords: +1-2 based on count]
        F4[Cap: 1-10 range]
        F1 --> F2 --> F3 --> F4
    end

    subgraph "Industry Score (40% weight)"
        I1[Base: 5/10]
        I2[Match industry keywords in text]
        I3[Take highest matching score]
        I1 --> I2 --> I3
    end

    subgraph "Industry Value Scale"
        V1[Power/Eskom: 10]
        V2[Mining/Petrochemical: 9]
        V3[Water Utility: 8]
        V4[Municipal/Hospital: 7]
        V5[Manufacturing: 6]
        V6[Transport/Education: 4-5]
        V7[Retail/Office: 1-3]
    end

    subgraph "Mexel Suitability"
        S1[Strong keywords × 2 + Moderate keywords]
        S2[Cap at 10]
        S3[Strong ≥6, Moderate ≥3, Weak <3]
        S1 --> S2 --> S3
    end

    subgraph "Composite Score"
        C1[fit_score × 0.60 + industry_score × 0.40]
        C2{Priority Assignment}
        C3[HIGH ≥ 7.0]
        C4[MEDIUM ≥ 4.5]
        C5[LOW < 4.5]
        C1 --> C2 --> C3
        C2 --> C4
        C2 --> C5
    end

    T --> F1
    T --> I1
    T --> S1
    F4 --> C1
    I3 --> C1
    S3 --> C1
```

#### Composite Score Formula

```
composite = fit_score × 0.60 + industry_score × 0.40

Priority thresholds:
  HIGH   → composite ≥ 7.0
  MEDIUM → composite ≥ 4.5
  LOW    → composite < 4.5
```

#### Recommendation Engine

| Composite Score | Mexel Suitability | Recommendation |
|----------------|-------------------|----------------|
| ≥ 8.0 | Any | 🔥 PRIORITY BID — Strong fit, pursue immediately |
| 6.0–7.9 | Any | ✅ RECOMMENDED — Good opportunity, prepare bid |
| 4.0–5.9 | ≥ 6 | 📋 CONSIDER — Core capability match despite moderate score |
| 4.0–5.9 | < 6 | 📝 EVALUATE — May be worth pursuing if capacity allows |
| < 4.0 | Any | ⏭️ LOW PRIORITY — Does not align well with capabilities |

---

### Database Layer

The system uses **SQLite** as its primary storage backend, with a schema defined in `schema.sql`.

#### Entity Relationship Diagram

```mermaid
erDiagram
    TENDERS {
        INTEGER id PK
        TEXT ref UK
        TEXT title
        TEXT description
        TEXT client
        TEXT source
        TEXT url
        TEXT closing_date
        TEXT category
        TEXT classification_reason
        REAL fit_score
        REAL industry_score
        REAL mexel_suitability
        REAL composite_score
        TEXT priority
        TEXT recommendation
        TEXT stage
        TEXT status
        TEXT next_action
        TEXT notes
        TEXT matched_keywords
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }

    PDF_ANALYSIS {
        INTEGER id PK
        TEXT tender_ref FK
        INTEGER page_count
        INTEGER word_count
        TEXT requirements
        TEXT deadlines
        TEXT values_extracted
        TEXT contact_info
        TEXT full_text
        TIMESTAMP created_at
    }

    BID_OUTCOMES {
        INTEGER id PK
        TEXT tender_ref
        TEXT company
        BOOLEAN bid_submitted
        REAL bid_amount
        TEXT outcome
        TEXT winner_name
        REAL winning_amount
        TEXT bid_date
        TIMESTAMP created_at
    }

    BID_NOTES {
        INTEGER id PK
        TEXT tender_ref
        TEXT company
        TEXT note
        TIMESTAMP created_at
    }

    CLASSIFICATIONS {
        INTEGER id PK
        INTEGER tender_id FK
        TEXT matched_keywords
        TEXT classification_reason
        TIMESTAMP classified_at
    }

    SCRAPER_RUNS {
        INTEGER id PK
        TEXT source
        TIMESTAMP run_date
        INTEGER tenders_found
        INTEGER tenders_new
        TEXT status
        TEXT error_message
    }

    TENDERS ||--o| PDF_ANALYSIS : "has"
    TENDERS ||--o{ BID_OUTCOMES : "tracks"
    TENDERS ||--o{ BID_NOTES : "has"
    TENDERS ||--o{ CLASSIFICATIONS : "audited by"
```

#### DatabaseWriter Class

The `DatabaseWriter` class (`utils/db_writer.py`) provides the main interface:

| Method | Purpose |
|--------|---------|
| `add_tender_with_scoring()` | Full pipeline: classify → score → write → audit trail |
| `write_tender()` | Insert single tender with duplicate guard |
| `save_pdf_analysis()` | Store PDF extraction results (UPSERT) |
| `record_bid_outcome()` | Record bid won/lost/withdrawn (UPSERT) |
| `add_bid_note()` | Append note to bid history |
| `get_recent_tenders()` | Fetch N most recent for deduplication |
| `get_stats()` | Aggregate counts by type, priority, status |
| `get_active_mexel_tenders()` | Query MEXEL tenders for dashboard |

---

### Dashboard Frontend

The dashboard is a **zero-build static PWA** served as plain HTML/CSS/JS with modular ES module architecture.

#### Frontend Architecture

```mermaid
graph TB
    subgraph "Entry Point"
        IDX[index.html]
        IJS[js/index.js]
    end

    subgraph "Core Modules (js/modules/)"
        CFG[config.js — State & Config]
        DAT[data.js — Loading & Caching]
        UIJ[ui.js — Event Handling]
        REN[render.js — Virtual Scrolling]
        TND[tender.js — Classification Logic]
        STO[storage.js — localStorage CRUD]
        MOD[modal.js — Detail Modal]
        ANA[analytics.js — Charts]
        MET[metrics.js — Dashboard Metrics]
    end

    subgraph "Utilities"
        HLP[utils/helpers.js — debounce, escapeHtml, etc.]
    end

    subgraph "PWA"
        SW[service-worker.js]
        MF[manifest.json]
    end

    IDX --> IJS
    IJS --> CFG
    IJS --> DAT
    IJS --> UIJ
    IJS --> REN
    IJS --> TND
    IJS --> STO
    IJS --> MOD
    IJS --> ANA
    IJS --> MET
    IJS --> HLP

    IDX --> SW
    IDX --> MF

    DAT -.->|fetch| TJ[tenders.json]
    ANA -.->|renders| CH[Chart.js]
    UIJ -.->|gestures| HM[Hammer.js]
```

#### Key Frontend Features

| Feature | Implementation |
|---------|---------------|
| Virtual Scrolling | Renders only visible rows + 5 buffer (150px item height) |
| Smart Search | Natural language: "closes today", "next week", "urgent" |
| Three View Modes | Detailed table, Compact table, Card grid |
| Offline Support | Service worker with cache-first static, network-first data |
| Bid Calendar | Month grid with tender count indicators |
| Analytics Dashboard | Chart.js: trend line, source pie, priority bar, keyword cloud |
| Tender Detail Modal | 5 tabs: Overview, Details, Attachments, Similar, Discussion |
| Team Collaboration | Assignments, @mentions, comments, status lifecycle (8 states) |
| Export | CSV, Excel (SheetJS), PDF (jsPDF), Print |
| Persistence | localStorage for assignments, watchlists, comments, theme |

#### Data Flow in Frontend

```mermaid
flowchart LR
    A[tenders.json] -->|fetch| B[data.js]
    B -->|validate & normalize| C[state object]
    C -->|filter & sort| D[render.js]
    D -->|virtual scroll| E[DOM rows/cards]

    F[user interaction] -->|click, search, filter| G[ui.js]
    G -->|update state| C
    G -->|localStorage| H[storage.js]
    H -->|assignments, comments| C

    C -->|compute metrics| I[metrics.js]
    C -->|compute analytics| J[analytics.js]
    I --> K[stats cards]
    J --> L[Chart.js charts]

    M[click tender] -->|open modal| N[modal.js]
    N -->|5 tabs| O[detail view]
    N -->|save| H
```

---

### Flask API

The Flask API (`app.py`) provides programmatic access to the system.

#### API Architecture

```mermaid
graph TB
    subgraph "Flask App (app.py)"
        subgraph "Public Endpoints"
            H1[/health — Health check]
            T1[/api/tenders — List tenders]
            B1[/api/stats/bids — Bid statistics]
            A1[/api/tenders/:ref/analysis — PDF analysis]
        end

        subgraph "Protected Endpoints (require_api_key)"
            S1[/api/summarize — AI summarization]
            D1[/api/run/daily — Trigger scan]
            W1[/api/run/weekly — Generate report]
            C1[/cron/daily — Cron webhook]
            C2[/cron/weekly — Cron webhook]
            R1[/api/bids — Record bid outcome]
        end

        subgraph "Middleware"
            CORS[CORS enabled]
            AUTH[API Key decorator<br/>Bearer token or X-API-Key]
        end
    end

    CORS --> H1
    CORS --> T1
    CORS --> B1
    CORS --> A1

    AUTH --> S1
    AUTH --> D1
    AUTH --> W1
    AUTH --> C1
    AUTH --> C2
    AUTH --> R1
```

#### Authentication Flow

```mermaid
sequenceDiagram
    participant Client
    participant Flask
    participant Auth

    Client->>Flask: Request to protected endpoint
    Flask->>Auth: require_api_key decorator

    alt No API_KEY configured
        Auth-->>Flask: Pass through (open)
    else Bearer token
        Client->>Auth: Authorization: Bearer <key>
        Auth->>Auth: Compare with API_KEY
    else X-API-Key header
        Client->>Auth: X-API-Key: <key>
        Auth->>Auth: Compare with API_KEY
    end

    alt Valid key
        Auth-->>Flask: Proceed to handler
        Flask-->>Client: 200 OK + response
    else Invalid/missing key
        Auth-->>Client: 401 Unauthorized
    end
```

---

### Automation & Scheduling

#### Daily Workflow

```mermaid
flowchart TD
    A[Scheduler triggers daily_runner.py] --> B[Step 1: Run Tender Scan]
    B --> C[run_all_scrapers parallel execution]
    C --> D[Check scraper failures]
    D --> E{Critical failures ≥3?}
    E -->|Yes| F[Send health alerts]
    E -->|No| G[Continue]
    F --> G
    G --> H[process_tenders: classify + score]
    H --> I[save_outputs: JSON + summary]

    A --> J[Step 2: Sync Dashboard]
    I --> J
    J --> K[sync_dashboard.py: load from SQLite]
    K --> L[Generate tenders.json]

    A --> M[Step 3: Email Alerts]
    L --> M
    M --> N{HIGH priority tenders?}
    N -->|Yes| O[Send daily digest email]
    N -->|No| P[Skip]

    A --> Q[Step 4: Database Backup]
    O --> Q
    P --> Q
    Q --> R[backup_database: timestamped copy]
    R --> S[Cleanup: keep last 30 backups]
    S --> T[Complete]
```

#### Weekly Report

The `weekly_report.py` generates a comprehensive HTML report with:
- Total tenders and weekly additions
- Priority distribution (HIGH/MEDIUM/LOW)
- Category breakdown with bar charts
- Closing soon tenders (next 7 days)
- Top high-priority opportunities
- Scraper health status table
- Top industries

#### Scheduling Options

| Method | Platform | Configuration |
|--------|----------|---------------|
| launchd | macOS | `com.tenderscan.daily.plist`, `com.tenderscan.weekly.plist` |
| cron | Unix/Linux | `crontab -e` entries |
| GitHub Actions | Cloud | `.github/workflows/` |
| Flask API | Any | `/cron/daily`, `/cron/weekly` endpoints |
| Render | Cloud | `render.yaml` build/start commands |

---

## Database Schema

### Complete Schema Reference

```sql
-- Main tenders table
CREATE TABLE tenders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ref TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    client TEXT,
    source TEXT,
    url TEXT,
    closing_date TEXT,
    category TEXT,              -- MEXEL, EXCLUDED
    classification_reason TEXT,
    fit_score REAL,
    industry_score REAL,
    mexel_suitability REAL,
    composite_score REAL,
    priority TEXT,              -- HIGH, MEDIUM, LOW
    recommendation TEXT,
    stage TEXT DEFAULT 'New',
    status TEXT DEFAULT 'Open',
    next_action TEXT,
    notes TEXT,
    matched_keywords TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- PDF analysis (one-to-one with tenders)
CREATE TABLE pdf_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tender_ref TEXT UNIQUE NOT NULL,
    page_count INTEGER,
    word_count INTEGER,
    requirements TEXT,          -- JSON array
    deadlines TEXT,             -- JSON array
    values_extracted TEXT,      -- JSON array
    contact_info TEXT,          -- JSON object
    full_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bid outcomes (tracks submission results)
CREATE TABLE bid_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tender_ref TEXT NOT NULL,
    company TEXT NOT NULL,
    bid_submitted BOOLEAN DEFAULT 0,
    bid_amount REAL,
    outcome TEXT NOT NULL,      -- won, lost, withdrawn, no_bid
    winner_name TEXT,
    winning_amount REAL,
    bid_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tender_ref, company)
);

-- Bid notes (free-form annotations)
CREATE TABLE bid_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tender_ref TEXT NOT NULL,
    company TEXT NOT NULL,
    note TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Classification audit trail
CREATE TABLE classifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tender_id INTEGER,
    matched_keywords TEXT,
    classification_reason TEXT,
    classified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tender_id) REFERENCES tenders(id)
);

-- Scraper run monitoring
CREATE TABLE scraper_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT,
    run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tenders_found INTEGER,
    tenders_new INTEGER,
    status TEXT,
    error_message TEXT
);

-- Performance indexes
CREATE INDEX idx_tenders_ref ON tenders(ref);
CREATE INDEX idx_tenders_priority ON tenders(priority);
CREATE INDEX idx_tenders_category ON tenders(category);
CREATE INDEX idx_tenders_closing_date ON tenders(closing_date);
CREATE INDEX idx_tenders_created_at ON tenders(created_at);
```

---

## Configuration & Environment

### Configuration Hierarchy

```mermaid
graph TB
    subgraph "config.yaml"
        Y1[paths — file system paths]
        Y2[scrapers — Selenium toggle, timeouts, search terms]
        Y3[classification — mexel_only flag]
        Y4[scoring — weights, thresholds]
        Y5[email — SMTP settings]
        Y6[alerts — Slack, SMS, smart alerts]
        Y7[deduplication — semantic/fuzzy thresholds]
    end

    subgraph ".env (secrets)"
        E1[DB_PATH — SQLite path]
        E2[SMTP_USER — Gmail address]
        E3[SMTP_PASSWORD — App password]
        E4[API_KEY — Flask API auth]
        E5[OPENAI_API_KEY — Summarization]
        E6[SLACK_WEBHOOK_URL]
        E7[TWILIO_ACCOUNT_SID]
        E8[TWILIO_AUTH_TOKEN]
    end

    subgraph "Runtime Validation"
        V1[config_validator.py]
        V2[validate_config structure]
        V3[validate_env variables]
        V4[validate_env_on_startup]
    end

    Y1 --> V2
    Y2 --> V2
    Y3 --> V2
    Y4 --> V2
    Y5 --> V2
    Y6 --> V2
    Y7 --> V2

    E1 --> V3
    E2 --> V3
    E3 --> V3

    V2 --> V4
    V3 --> V4
    V4 -->|raises on failure| F[System Exit]
    V4 -->|passes| S[System Starts]
```

### Key Configuration Values

| Setting | Default | Description |
|---------|---------|-------------|
| `scoring.fit_weight` | 0.60 | Fit score weight in composite |
| `scoring.industry_weight` | 0.40 | Industry score weight in composite |
| `scoring.high_threshold` | 7.0 | Composite score for HIGH priority |
| `scoring.medium_threshold` | 4.5 | Composite score for MEDIUM priority |
| `scrapers.enable_selenium` | true | Toggle Selenium-based scrapers |
| `deduplication.semantic_threshold` | 0.75 | ML similarity threshold |
| `deduplication.fuzzy_threshold` | 85 | Fuzzy string match threshold |
| `deduplication.date_window_days` | 7 | Date proximity window for dedup |
| `alerts.urgent_threshold_days` | 3 | Days until closing for urgent alert |

---

## Security Model

```mermaid
graph TB
    subgraph "Secrets Management"
        S1[.env file — never committed]
        S2[.gitignore — excludes .env]
        S3[python-dotenv — loads at runtime]
    end

    subgraph "API Security"
        A1[require_api_key decorator]
        A2[Bearer token auth]
        A3[X-API-Key header auth]
        A4[Open if no API_KEY set]
    end

    subgraph "Data Protection"
        D1[SQLite file — local only]
        D2[No external DB connections]
        D3[Parameterized queries — SQL injection prevention]
    end

    subgraph "Frontend Security"
        F1[escapeHtml — XSS prevention]
        F2[No eval/innerHTML for user data]
        F3[Static PWA — no server-side rendering]
    end

    subgraph "Scraper Security"
        R1[retry_tools — exponential backoff]
        R2[Timeout protection — 300s global]
        R3[Circuit breaker — prevents hammering]
    end

    S1 --> S2
    S1 --> S3
    S3 --> A1
    A1 --> A2
    A1 --> A3
    A1 --> A4

    D1 --> D3
    F1 --> F2
    R1 --> R2
    R2 --> R3
```

### Security Checklist

| Area | Measure | Status |
|------|---------|--------|
| Secrets | `.env` in `.gitignore`, loaded via `python-dotenv` | ✅ |
| API Auth | Bearer token / X-API-Key decorator | ✅ |
| SQL Injection | Parameterized queries throughout | ✅ |
| XSS | `escapeHtml()` in frontend, no innerHTML for user data | ✅ |
| Scraper Resilience | Exponential backoff, circuit breaker, timeouts | ✅ |
| File Access | Local-only SQLite, no external connections | ✅ |
| CORS | Configured for Flask API endpoints | ✅ |

---

## Testing & CI/CD

### Test Infrastructure

```mermaid
graph TB
    subgraph "Backend Tests"
        B1[pytest — Python test runner]
        B2[pytest.ini — Configuration]
        B3[test_scoring_v2.py — Scoring tests]
        B4[test_exclusions.py — Classification tests]
        B5[test_hvac_keywords.py — HVAC keyword tests]
        B6[test_scrapers_direct.py — Scraper tests]
        B7[run_tests.py — Test runner]
    end

    subgraph "Frontend Tests"
        F1[Vitest — JS test runner]
        F2[vitest.config.js — Configuration]
        F3[tests/tender.test.js — Classification logic]
        F4[tests/helpers.test.js — Utility functions]
        F5[tests/setup.js — Mocks: localStorage, fetch, Chart]
    end

    subgraph "CI/CD Pipeline"
        C1[.github/workflows/test-and-lint.yml]
        C2[Ruff — Linter (120 char line limit)]
        C3[Pytest — Unit tests]
        C4[Codecov — Coverage reporting]
        C5[deploy-staging.yml — Staging deploy]
        C6[update-dashboard-tenders.yml — Dashboard sync]
    end

    B1 --> B2
    B3 --> B1
    B4 --> B1
    B5 --> B1
    B6 --> B1
    B7 --> B1

    F1 --> F2
    F3 --> F1
    F4 --> F1
    F5 --> F1

    C1 --> C2
    C1 --> C3
    C3 --> C4
    C1 --> C5
    C1 --> C6
```

### CI/CD Workflows

| Workflow | Trigger | Actions |
|----------|---------|---------|
| `test-and-lint.yml` | Push/PR to `main` | Ruff lint → Pytest → Codecov upload |
| `deploy-staging.yml` | Push to `main` | Deploy to staging environment |
| `update-dashboard-tenders.yml` | Schedule / Push | Sync dashboard data files |

### Test Commands

```bash
# Backend tests
python run_tests.py
python -m pytest tests/ -v

# Frontend tests
cd dashboard && npm test
cd dashboard && npm run test:coverage
cd dashboard && npm run test:ui

# Linting
ruff check .
cd dashboard && npm run lint
```

---

## Deployment Architecture

### Deployment Options

```mermaid
graph TB
    subgraph "Option 1: Local macOS (Primary)"
        L0[launchd app service: serve_app.sh]
        L1[launchd daily at 08:00]
        L2[launchd weekly Monday 09:00]
        L3[SQLite local file]
        L4[Gunicorn or Flask via serve_app.sh]
        L5[Dashboard + API: http://localhost:5001]
        L0 --> L4
        L1 --> L3
        L2 --> L3
        L3 --> L4
        L4 --> L5
    end

    subgraph "Option 2: Render Cloud"
        R1[GitHub repository]
        R2[Render Web Service]
        R3[Gunicorn + Flask]
        R4[SQLite on ephemeral storage]
        R5[Dashboard: Render URL]
        R1 --> R2
        R2 --> R3
        R3 --> R4
        R4 --> R5
    end

    subgraph "Option 3: Vercel (Frontend Only)"
        V1[GitHub repository]
        V2[Vercel Static Deploy]
        V3[dashboard/ directory]
        V4[vercel.json — SPA routing]
        V5[Dashboard: Vercel URL]
        V1 --> V2
        V2 --> V3
        V3 --> V4
        V4 --> V5
    end

    subgraph "Shared Components"
        S1[.env — Environment variables]
        S2[config.yaml — Configuration]
        S3[requirements.txt — Dependencies]
        S4[render.yaml — Render config]
    end

    S1 --> L1
    S1 --> R2
    S2 --> L1
    S2 --> R2
    S3 --> R2
    S4 --> R2
```

### Local macOS Automation

```mermaid
graph LR
    subgraph "launchd Agents"
        L1[com.tenderscan.daily.plist<br/>Daily 08:00]
        L2[com.tenderscan.weekly.plist<br/>Monday 09:00]
    end

    subgraph "Execution"
        E1[daily_runner.py]
        E2[weekly_report.py]
    end

    subgraph "Outputs"
        O1[SQLite Database]
        O2[Dashboard HTML]
        O3[Email Digest]
        O4[Weekly HTML Report]
        O5[Database Backup]
    end

    L1 --> E1
    L2 --> E2
    E1 --> O1
    E1 --> O2
    E1 --> O3
    E1 --> O5
    E2 --> O4
```

---

## Developer Guide

### Project Structure

```
tender-intelligence/
├── tenderscan.py              # Main orchestration engine
├── classify_engine.py         # Classification logic (Profile A/B)
├── scoring_engine.py          # Composite scoring algorithm
├── keyword_rules.py           # Keyword definitions (STRONG, SYSTEM, ACTION, NEGATIVE)
├── sync_dashboard.py          # Dashboard data sync (SQLite → JSON)
├── daily_runner.py            # Daily workflow orchestrator
├── weekly_report.py           # Weekly HTML report generator
├── app.py                     # Flask API server
│
├── scrapers/                  # Data source scrapers
│   ├── municipalities.py      # Cape Town municipality
│   ├── soes.py               # State-owned enterprises aggregator
│   ├── national_treasury_selenium.py  # eTenders (Selenium)
│   ├── joburg_water_selenium.py       # Johannesburg Water (Selenium)
│   ├── eskom_direct.py       # Eskom tender bulletin (API + Selenium)
│   ├── water_boards.py       # Water boards aggregator
│   ├── national_treasury.py  # eTenders API (unused)
│   ├── eskom.py              # Eskom via eTenders API (deprecated)
│   ├── transnet.py           # Transnet via eTenders API (disabled)
│   └── sadc.py               # SADC regional tenders
│
├── utils/                     # Shared utilities
│   ├── db_writer.py          # SQLite database operations
│   ├── excel_writer.py       # Excel operations (legacy)
│   ├── data_validator.py     # Tender data validation
│   ├── duplicate_detector.py # Fuzzy string deduplication
│   ├── semantic_duplicate_detector.py  # ML-based dedup
│   ├── pdf_analyzer.py       # PDF content extraction
│   ├── scraper_monitor.py    # Circuit breaker & health tracking
│   ├── retry_tools.py        # HTTP retry with backoff
│   ├── logging_tools.py      # Thread-safe logging
│   ├── folder_tools.py       # Tender folder creation
│   ├── bid_tracker.py        # Bid outcome tracking
│   ├── multi_channel_alerts.py  # Slack/SMS alerts
│   ├── email_alerts.py       # Email notifications
│   ├── config_validator.py   # Config & env validation
│   ├── backup_database.py    # SQLite backup with rotation
│   ├── text_cleaner.py       # Text normalization
│   ├── text_utils.py         # Date parsing, text utilities
│   └── pdf_tools.py          # PDF metadata detection
│
├── dashboard/                 # Static PWA frontend
│   ├── index.html            # Main dashboard page
│   ├── style.css             # Styles
│   ├── manifest.json         # PWA manifest
│   ├── service-worker.js     # Offline support
│   ├── tenders.json          # Client-side data (generated)
│   ├── js/                   # Modular JavaScript
│   │   ├── index.js          # Entry point
│   │   ├── modules/          # Core modules
│   │   │   ├── config.js     # State & configuration
│   │   │   ├── data.js       # Data loading & caching
│   │   │   ├── ui.js         # Event handling & theme
│   │   │   ├── render.js     # Virtual scrolling
│   │   │   ├── tender.js     # Classification logic
│   │   │   ├── storage.js    # localStorage CRUD
│   │   │   ├── modal.js      # Detail modal
│   │   │   ├── analytics.js  # Charts & analytics
│   │   │   └── metrics.js    # Dashboard metrics
│   │   └── utils/
│   │       └── helpers.js    # Utility functions
│   └── tests/                # Frontend tests
│
├── data/                      # SQLite database
│   └── tenders.db
│
├── output/                    # Generated outputs
│   ├── new_tenders.json      # Latest tenders
│   ├── summary.txt           # Scan summary
│   └── scraper_health.json   # Scraper health report
│
├── reports/                   # Weekly reports
├── backups/                   # Database backups
├── logs/                      # Scraper logs
│
├── config.yaml               # Main configuration
├── schema.sql                # Database schema
├── requirements.txt          # Python dependencies
├── .env.example              # Environment template
└── Launch Dashboard.command  # macOS launcher
```

### Adding a New Scraper

1. Create `scrapers/my_source.py`
2. Implement a function that returns `List[Dict]` with the standard schema
3. Use `utils.retry_tools.safe_get()` for HTTP requests
4. Call `classify_engine.classify_tender()` for classification
5. Add the scraper to `tenderscan.py:run_all_scrapers()`
6. Test with: `python -c "from scrapers.my_source import scrape_my_source; print(len(scrape_my_source()))"`

### Modifying Classification Rules

1. Edit `keyword_rules.py` — add/remove keywords from the appropriate list
2. Test with: `python -c "from classify_engine import classify_tender; print(classify_tender('Test Title', 'Test Description'))"`
3. Run `python tenderscan.py` to reclassify existing tenders

### Adjusting Scoring Weights

1. Edit `config.yaml` → `scoring:` section
2. Modify `scoring_engine.py` for algorithm changes
3. Test with: `python scoring_engine.py` (runs built-in tests)

---

## Glossary

| Term | Definition |
|------|------------|
| **Mexel Energy Sustain** | Client company — thermal efficiency services for power generation and industrial cooling |
| **Profile A** | Classification profile — direct product/technology match (automatic include) |
| **Profile B** | Classification profile — system + action keyword pair match (must both be present) |
| **Composite Score** | Weighted average of fit score (60%) and industry score (40%) |
| **Fit Score** | How well a tender matches Mexel's core capabilities (1-10) |
| **Industry Score** | Value of the client's industry to Mexel (1-10) |
| **Mexel Suitability** | Product-specific fit score based on keyword density (0-10) |
| **Semantic Deduplication** | ML-based duplicate detection using sentence embeddings |
| **Circuit Breaker** | Pattern that disables scrapers after consecutive failures |
| **PWA** | Progressive Web App — installable, offline-capable web application |
| **Virtual Scrolling** | Rendering only visible DOM elements for performance |
| **launchd** | macOS service manager for scheduled tasks |
| **SOE** | State-Owned Enterprise (Eskom, Transnet, Rand Water, etc.) |
| **TES** | Thermal Efficiency Services — Mexel's core business line |

---

## System Health Monitoring

```mermaid
graph TB
    subgraph "ScraperMonitor"
        M1[Per-source metrics]
        M2[Success rate tracking]
        M3[Consecutive failure count]
        M4[Average tenders per run]
        M5[Average duration]
    end

    subgraph "Circuit Breaker"
        C1[Threshold: 3 consecutive failures]
        C2[Cooldown: 3600 seconds]
        C3[CircuitOpenError — skip scraper]
    end

    subgraph "Alerting"
        A1[Should alert? — threshold check]
        A2[Mark alerted — prevent duplicates]
        A3[Slack webhook]
        A4[SMS via Twilio]
        A5[Email digest]
    end

    subgraph "Health Report"
        H1[output/scraper_health.json]
        H2[Weekly report scraper table]
        H3[Dashboard source health cards]
    end

    M1 --> C1
    M2 --> C1
    M3 --> C1
    C1 --> C3
    C1 --> C2
    C3 --> A1
    A1 --> A2
    A2 --> A3
    A2 --> A4
    A2 --> A5

    M1 --> H1
    M2 --> H2
    M4 --> H3
```

---

*This document was auto-generated by exploring the complete codebase. For implementation details, refer to the source files directly.*
