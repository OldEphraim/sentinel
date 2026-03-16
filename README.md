# Sentinel 🛰️

> *Ask any question about any place on Earth. Get an answer, not an image.*

---

## What is this?

Sentinel is an autonomous Earth intelligence monitoring agent built on top of [SkyFi](https://skyfi.com)'s geospatial intelligence platform. Instead of requiring users to understand satellite sensors, image resolutions, delivery pipelines, or GIS toolchains, Sentinel lets anyone describe what they want to *know* about a location in plain English — and handles everything else automatically.

You draw a polygon on a map. You type a question:

- *"Is construction still ongoing at this industrial site?"*
- *"How many vessels are anchored in this harbor right now?"*
- *"Has the water level in this reservoir changed since last month?"*
- *"Alert me when more than 100 cars appear in this parking lot."*

Sentinel's AI agent interprets the question, determines the right satellite data product (optical vs. SAR, archive vs. new tasking, which analytics to run), places the order via the SkyFi API, waits for delivery asynchronously, interprets the results, and writes you a plain-English answer — with supporting evidence from the imagery.

You can configure a watch to repeat on a schedule. You get alerts when thresholds are crossed. You get answers, not GeoTIFFs.

---

## Why I built this

I built this as an independent project during [Gauntlet AI](https://gauntletai.com)'s Gold Hiring Partner Week to demonstrate familiarity with SkyFi's platform, business model, and technical architecture.

The insight behind Sentinel is the same insight behind SkyFi's own Series A thesis: **imagery is a commodity. Answers are the product.** SkyFi CEO Luke Fischer has stated explicitly that the company's direction is toward "speed of delivery of answers" — not just faster image delivery but automated interpretation of what those images mean. Sentinel is a working demonstration of that future state, built on SkyFi's existing API and analytics products.

SkyFi's actual value proposition is: *you shouldn't need a contract, a GIS analyst, or a PhD to use satellite data.* Sentinel extends that to its logical conclusion: *you shouldn't need to know what type of satellite to order, either.*

---

## Architecture overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                              │
│  Next.js frontend: map, polygon draw, watch config, results │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST
┌──────────────────────────▼──────────────────────────────────┐
│                   FastAPI (Python)                           │
│  - Watch CRUD                                               │
│  - Agent orchestration (Claude tool-use loop)               │
│  - SkyFi REST API client                                    │
│  - Webhook receiver (SkyFi order callbacks)                 │
│  - SSE endpoint (real-time status to frontend)              │
└──────────┬──────────────────────────────────┬───────────────┘
           │ publishes                         │ reads/writes
┌──────────▼──────────┐           ┌───────────▼───────────────┐
│  RabbitMQ           │           │  PostgreSQL + PostGIS       │
│  order.placed       │           │  watches, orders, results  │
│  order.ready        │           │  alert history             │
└──────────┬──────────┘           └───────────────────────────┘
           │ consumes
┌──────────▼──────────────────────────────────────────────────┐
│               Python Worker Service                          │
│  - Polls SkyFi order status                                 │
│  - Downloads completed imagery/analytics                    │
│  - Runs agent interpretation step                           │
│  - Writes results to Postgres                               │
│  - Fires alert notifications                                │
└─────────────────────────────────────────────────────────────┘
```

---

## Tech stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | **Next.js + React + TypeScript** | SSR dashboard, map UI, real-time status |
| Backend | **FastAPI + Python** | Agent orchestration, SkyFi API client, webhooks |
| Database | **PostgreSQL + PostGIS** | Geospatial watch areas, order history, results |
| Messaging | **RabbitMQ** | Async order lifecycle events (satellite delivery is never instant) |
| AI | **Claude API (tool-use)** | Agent loop: question → sensor selection → order → interpretation |
| Infrastructure | **Docker + Kubernetes** | Local dev compose, production K8s manifests (GKE/EKS) |

This is SkyFi's own technical stack: TypeScript/JavaScript, Python, Postgres, REST APIs, RabbitMQ/Kafka, Kubernetes, GCP/AWS, Docker, and Agents.

---

## SkyFi API integration

Sentinel integrates with the following SkyFi platform capabilities:

- **Archive search** — search available imagery by AOI, date range, resolution, and sensor type
- **Satellite tasking** — request new captures with configurable parameters
- **Order placement** — transactional imagery purchasing
- **Analytics** — object detection (vehicles, vessels, aircraft), change detection, material classification
- **Satellite pass prediction** — estimate when the right asset will next overfly an AOI
- **Open data** — free Sentinel-2 10m imagery for low-resolution monitoring watches
- **Webhooks** — order completion callbacks driving the async worker pipeline

> **Note on API access**: This project is built against SkyFi's documented REST API (`app.skyfi.com/platform-api/docs`). A mock server is included for local development. To run against the real SkyFi platform, set `SKYFI_API_KEY` in your environment variables. SkyFi Pro accounts can obtain an API key from their platform settings.

---

## Local development

```bash
# Prerequisites: Docker Desktop, Node.js 20+, Python 3.11+

git clone https://github.com/<your-handle>/sentinel
cd sentinel

cp .env.example .env
# Set SKYFI_API_KEY, ANTHROPIC_API_KEY, etc.

docker compose up
```

Services will be available at:
- Frontend: http://localhost:3000
- API: http://localhost:8000 (docs at /docs)
- RabbitMQ management: http://localhost:15672
- Postgres: localhost:5432

---

## Demo watches (seed data)

The seed script populates three demonstration watches:

**1. Port of Rotterdam — vessel count**
> *"How many cargo vessels are currently anchored or docked in the Maasvlakte terminal?"*
Uses ICEYE US SAR data (works through North Sea cloud cover), vessel detection analytics.

**2. Permian Basin drilling activity — energy commodity intelligence**
> *"Are there active drilling rigs at this well pad? Has activity changed in the last 30 days?"*
Uses Planet SkySat optical, change detection analytics. This is the use case SkyFi was originally built for — Bill Perkins counting rigs for his energy hedge fund.

**3. Hoover Dam reservoir — water level monitoring**
> *"Has the water surface area of Lake Mead changed in the past 90 days?"*
Uses free Sentinel-2 open data (10m resolution sufficient for reservoir extent measurement), NDWI water index.

---

## Production deployment

Kubernetes manifests are in `k8s/`. A Helm chart is in `helm/sentinel/`. Documented for deployment to:
- **GKE** (Google Kubernetes Engine) with Cloud SQL Postgres and Cloud Pub/Sub
- **EKS** (Amazon Elastic Kubernetes Service) with RDS and Amazon MQ

---

## About the author

Built by Alan (OldEphraim on GitHub) during Gauntlet AI's Week 5 Hiring Partner Week.
Gauntlet AI is an elite AI engineering cohort run by Austen Allred in Austin, Texas.

---

*"There is no and will never be a 'contact sales' button on SkyFi." — Luke Fischer, CEO, SkyFi*

*Sentinel is not affiliated with or endorsed by SkyFi.*