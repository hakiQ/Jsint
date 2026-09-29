# Jsint

**Self-hosted OSINT / recon graph platform — entity pivoting and link analysis in the spirit of Maltego, without the licence server or the cloud.**

Point it at a seed (a domain, an IP, an email, a username, a wallet, a person, a phone…), run enrichers to pivot, and watch the relationship graph grow. Everything — graph, keys, notes — stays on hardware you control.


---

## What is Jsint?

Jsint is a **graph-based investigation platform for OSINT / recon / threat-intel work**. Like Maltego, its core idea is simple:

> **Entities are graph nodes. Transforms are enrichers. Investigations are graphs you grow by pivoting.**

You start from what you already know and let the tool discover the next hop: a domain resolves to IPs, an IP belongs to an ASN, an ASN announces CIDRs, a WHOIS record exposes an organisation and an abuse mailbox, that mailbox reverse-searches to more domains, and so on. Every hop is a node plus an edge in a visual graph you can explore, filter, annotate and export.

What makes it different from most OSINT tools:

- **Local-first.** Postgres, Neo4j, Redis and the API all run in Docker on your machine. No telemetry, no licence server, no vendor account. Only port `5173` is even reachable.
- **Bring your own sources.** 49 built-in enrichers: **26 need no key at all**, 3 take an optional ProjectDiscovery key for extra reach, and 20 require a key for a paid source you opt into.
- **Extensible in Python.** An enricher is a class with an `InputType`, an `OutputType` and a `scan()` method — auto-discovered, no registry wiring.
- **Free and open source**, Apache-2.0 (see [LICENSE](./LICENSE)).

### How it relates to Maltego

Same mental model, different delivery model:

| | Maltego | Jsint |
|---|---|---|
| Core model | Entity graph + transforms | Entity graph + enrichers — same idea |
| Licensing | Commercial; paid tiers for many sources/features | Apache-2.0, free, self-hosted |
| Where data lives | Your machine (desktop) or Maltego server (enterprise) | Your machine, full stop (Postgres + Neo4j in Docker) |
| Sources | Large transform library + commercial data integrations | 49 built-in enrichers; you supply API keys for the paid ones |
| Extending it | Transform SDK (Python/TS) + iTDS server | Drop an `Enricher` subclass in `jsint-enrichers`; back it with an HTTP or Docker tool you also write |
| Automation | Machines, transforms, enterprise orchestration | Flows (chain enrichers), Celery workers, REST API, n8n connector |
| Collaboration | Maltego server / enterprise | Multi-user with per-investigation roles (owner / admin / editor / viewer) |
| AI | Commercial AI features | Built-in chat assistant |
| Maturity | 15+ years, large ecosystem, commercial support | **Early-stage open source** — fewer integrations, no vendor support |

**What it is not:** a drop-in Maltego replacement. There is no `.mtgx` / transform compatibility, no Maltego data marketplace, and the project is young. If you need a supported enterprise graph suite, buy one. If you want a hackable, self-hosted graph workbench you can extend in an afternoon, this is that.

---

## Feature tour

- **Graph workbench** — force-directed canvas (thousands of nodes), per-type colours/icons, selection tools, minimap, shortest-path finder, layout workers (force + dagre), PNG export, table view and a geo map view for located entities.
- **49 enrichers** across 12 categories — DNS, WHOIS (live + historic), subdomains, TLS, ports, ASN/CIDR expansion, geolocation, breach data, Gravatar, HudsonRock infostealer devices, SIRENE company registry, crypto wallet activity, social-username enumeration (Sherlock/Maigret), website crawling/trackers/links, Instagram profiles via Apify.
- **Investigations → sketches** — a case holds many sketches (graphs) plus analyses; collaborators get roles.
- **Import** — drop a `.txt` (one entity per line) or `.json` and Jsint auto-detects entity types (domain / IP / email / username / phone / ASN / CIDR …), previews the mapping and imports in bulk.
- **Analyses** — rich-text (TipTap) investigation reports attached to a case, with a report template.
- **Flows** — visually chain enrichers into repeatable pipelines and run them against a sketch.
- **Custom types** — define your own entity types (icon, colour, schema) and use them like built-ins.
- **Documentation browser** — the `docs/` book (getting started, sources, developer guides) is readable inside the app at `/dashboard/docs`, with chapter navigation and cross-links that stay in the reader.
- **Encrypted vault** — per-user API keys, AES-GCM at rest, key derived with HKDF from `MASTER_VAULT_KEY_V1`; enrichers resolve secrets at run time and never see them in logs.
- **Live logs & events** — enricher runs stream to the UI over SSE; a terminal panel shows the run log.
- **Accounts & sharing** — email + password auth (JWT), **admin-approved registrations**, a user-management dashboard (roles, approvals, suspensions, deletion), user search, and per-investigation collaborator management.
- **Dark & light themes**, command palette (`⌘/Ctrl + K`), keyboard-driven navigation.

---

## Quick start (Docker)

Requirements: **Docker** (Compose v2+). Nothing else — the images build from source.

```bash
git clone <your-repo-url> jsint
cd jsint
cp .env.example .env                     # sets local secrets
docker compose -f docker-compose.prod.yml up -d
```

> First run builds the Python environment and the SPA inside Docker — expect a few minutes.

Then open **http://localhost:5173/register** and create an account. There are no default credentials.

Edit `.env` first and replace the sample secrets:

- `AUTH_SECRET` — signs JWTs: `openssl rand -hex 32`
- `MASTER_VAULT_KEY_V1` — encrypts vault API keys: `python3 -c "import os, base64; print('base64:' + base64.b64encode(os.urandom(32)).decode())"`
- `NEO4J_PASSWORD` — Neo4j password

Everything else is optional. **No external API key is required to boot, register, build graphs, import, run flows or write analyses** — see the key table below for the sources you may want to unlock.

### Accounts, approval and administration

Jsint is multi-user, and account creation is **approval-based**:

1. Someone registers at `/register` → the account is created as **pending** and cannot sign in (the API answers `403 Account pending approval by an administrator`).
2. An administrator opens **`/dashboard/admin`** and approves it → the account becomes **active** and can sign in and use the UI.
3. Administrators can also **create accounts directly** (pre-approved), **suspend/reactivate**, **grant or remove administrator rights**, **reset passwords** and **delete accounts** — deleting a user removes their cases, sketches, analyses and Neo4j graph data.

**The admin dashboard** lists every account with its role, status, creation date and how many **cases (investigations/sketches/analyses)** it owns, plus counters for accounts awaiting approval.

Who becomes an administrator:

- **The first account ever registered** on a fresh install (so a deployment can never lock itself out), and
- every address listed in the **`ADMIN_EMAILS`** environment variable (comma-separated). A listed address is promoted to active administrator the next time it registers or signs in — handy to recover access on an existing install.

```bash
ADMIN_EMAILS=you@example.com,teammate@example.com
```

The account approval flow is separate from the **per-investigation collaborator roles** (`owner` / `admin` / `editor` / `viewer`) described in [Architecture](#architecture): one is who may use the instance at all, the other is who may see or edit one case.

### Development mode

```bash
make dev            # or: docker compose -f docker-compose.dev.yml up -d --build
```

Vite dev server with hot reload on `:5173`, API with autoreload on `:5001`. `make help` lists every target (`up-dev`, `logs-dev`, `migrate-dev`, `test`, `lint`, `typecheck`, `regenerate-router`, …).

---


**Before exposing it beyond localhost:**

1. **Rotate the three secrets** listed above — the `.env.example` values are samples.
2. **Add your hostname/IP to the Host-header allowlist** in `jsint-app/nginx.conf` (the `map $http_host $is_jsint_host` block). The default allowlist accepts only `localhost` / `127.0.0.1` / `[::1]`, which defends single-user installs against DNS rebinding; LAN and public deploys must opt in. Two commented-out template lines show the format.
3. **Put HTTPS in front** if it leaves a trusted LAN. Example with [Caddy](https://caddyserver.com/):

External APIs that need a key — exact vault names

Add keys in the UI at **Vault** (`/dashboard/vault`), or as environment variables with the same names. Secrets are encrypted per user; a key you add is available to every enricher run as that user.

| # | Vault key name (must match exactly) | Service | Get the key at | Enrichers that use it | Cost |
|---|---|---|---|---|---|
| 1 | `PDCP_API_KEY` | ProjectDiscovery Cloud | https://cloud.projectdiscovery.io → sign up → API key | `asn_to_cidrs`, `domain_to_asn`, `ip_to_asn`, `org_to_asn` (**required**); `domain_to_dns`, `cidr_to_ips`, `ip_to_ports` (passive mode) — optional | free tier available |
| 2 | `WHOXY_API_KEY` | Whoxy | https://www.whoxy.com/api/ (key appears in your account area once API credits are added) | `domain_to_history`, `email_to_domains`, `individual_to_domains`, `org_to_domains` | paid credits |
| 3 | `WHOISXML_API_KEY` | WhoisXML API | https://main.whoisxmlapi.com/login → account → API keys | `domain_to_whois_history` | trial credits, then paid |
| 4 | `HIBP_API_KEY` | Have I Been Pwned | https://haveibeenpwned.com/API/Key (sign in → dashboard → purchase key) | `email_to_breaches` | low monthly subscription |
| 5 | `DEHASHED_API_KEY` | DeHashed | https://www.dehashed.com/api (docs: https://www.dehashed.com/docs) | `domain_to_dehashed`, `email_to_intelligence`, `ip_to_intelligence`, `username_to_dehashed` | paid subscription |
| 6 | `SCAMLYTICS_USERNAME` | Scamalytics | https://scamalytics.com/ip/api/signup | `ip_to_fraudscore` | paid per lookup |
| 7 | `SCAMLYTICS_API_KEY` | Scamalytics | same page (emailed with your access details) | `ip_to_fraudscore` | — |
| 8 | `SCAMLYTICS_API_HOST` | Scamalytics | same email — your account's **API node** (`api11`, `api12`, …) | `ip_to_fraudscore` (defaults to `api12`; add it as a vault key, it is not exposed as a UI parameter) | — |
| 9 | `VERIPHONE_API_KEY` | Veriphone | https://veriphone.io/signup | `phone_to_carrier` | 1,000 free lookups/month, then paid |
| 10 | `C99_API_KEY` | c99.nl | https://api.c99.nl/ → *Purchase an API Key* → dashboard | `website_to_subdomains` | paid credits |
| 11 | `ETHERSCAN_API_KEY` | Etherscan | https://etherscan.io/myapikey | `cryptowallet_to_transactions`, `cryptowallet_to_nfts` | free tier |
| 12 | `APIFY_API_TOKEN` | Apify | https://console.apify.com/settings/integrations | `username_to_instagram_profile` | pay per result |
| 13 | `MISTRAL_API_KEY` / `OPENAI_API_KEY` / `DEEPSEEK_API_KEY` | LLM provider (pick one) | https://console.mistral.ai/api-keys · https://platform.openai.com/api-keys · https://platform.deepseek.com/api_keys | AI chat assistant | free credit / paid |

Notes:

- **12 vendor accounts, 13 vault entries.** Scamalytics needs three (username, key, API host); the rest need one.
- Coverage: **20 of the 49 enrichers require one of these keys**, 3 accept `PDCP_API_KEY` optionally, and **26 run with no key at all**.
- Provider selection for the AI features is the environment variable `LLM_PROVIDER` (`mistral` — the default, `openai`, or `deepseek`); the matching key goes in the vault as `<PROVIDER>_API_KEY` or in the environment.
- `ETHERSCAN_API_URL` and `HIBP_API_URL` are optional per-run parameters if you need to point at a mirror.
- The n8n connector takes your own webhook URL (and an optional token), not a vendor key.

### No key needed (internet access only)

crt.sh · ip-api.com · Gravatar · HudsonRock (`cavalier.hudsonrock.com`) · **SIRENE** (`recherche-entreprises.api.gouv.fr`, French company registry) · system DNS + `python-whois` · Sherlock · Maigret · ReconCrawl / ReconSpread / ReconTrack · plus the containerised CLIs (`subfinder`, `dnsx`, `httpx`, `naabu`, `mapcidr`, `asnmap`) that are pulled from Docker Hub on first use.

---

## Enricher catalog

49 enrichers are exposed in the UI (plus one internal n8n connector). Names are the exact enricher ids you will see in the launch dialog.

**Domain** — `domain_to_ip` (DNS) · `domain_to_dns` (dnsx A/AAAA) · `domain_to_subdomains` (subfinder + crt.sh) · `domain_to_whois` · `domain_to_whois_history` (WhoisXML) · `domain_to_history` (Whoxy) · `domain_to_root_domain` · `domain_to_website` · `domain_to_tls` (httpx) · `domain_to_asn` (asnmap) · `domain_to_dehashed`

**IP** — `ip_to_infos` (geolocation/ISP) · `ip_to_asn` · `ip_to_domain` (PTR + Certificate Transparency) · `ip_to_ports` (naabu) · `ip_to_fraudscore` (Scamalytics) · `ip_to_intelligence` (DeHashed)

**ASN / CIDR** — `asn_to_cidrs` (asnmap) · `cidr_to_ips` (mapcidr)

**Email** — `email_to_domain` · `email_to_username` · `email_to_domains` (reverse WHOIS) · `email_to_gravatar` · `email_to_breaches` (HIBP) · `email_to_intelligence` (DeHashed) · `email_to_device_hudsonrock`

**Phone** — `phone_to_carrier` (Veriphone) · `phone_to_device_hudsonrock`

**Username / social** — `username_to_socials_sherlock` · `username_to_socials_maigret` · `username_to_dehashed` · `username_to_device_hudsonrock` · `username_to_instagram_profile` (Apify)

**Website** — `website_to_crawler` (emails/phones) · `website_to_links` · `website_to_domain` · `website_to_text` · `website_to_webtrackers` · `website_to_subdomains` · `tech_detect`

**Organization** — `org_to_infos` (SIRENE) · `org_to_domains` (reverse WHOIS) · `org_to_asn`

**Individual** — `individual_to_organization` (SIRENE) · `individual_to_domains` (reverse WHOIS)

**Crypto** — `cryptowallet_to_transactions` (Etherscan) · `cryptowallet_to_nfts`

**Internal / test** — `domain_to_dummy`, `ip_to_dummy_domains` (kept for tests, not part of the public catalog), `n8n_connector`.

Full descriptions and data sources: [`docs/sources/available-enrichers.mdx`](./docs/sources/available-enrichers.mdx).

---

## Architecture

| Layer | Technology |
|---|---|
| **Frontend** (`jsint-app`) | React 19 + TypeScript, Vite, TanStack Router (file-based) + TanStack Query + TanStack Table, Zustand stores, Tailwind CSS v4 + Radix UI, Recharts, Framer Motion |
| **Graph rendering** | `react-force-graph-2d` for the canvas, `@xyflow/react` (React Flow) for the flow editor, `d3-force` + `@dagrejs/dagre` layouts in web workers, MapLibre GL for the geo map |
| **Editors & panels** | TipTap (analyses), xterm.js (live logs) |
| **API** (`jsint-api`) | FastAPI + Uvicorn, JWT (python-jose) + bcrypt, SSE (sse-starlette), Pydantic v2 schemas, Alembic migrations |
| **Core** (`jsint-core`) | Enricher base class + orchestrator, graph service/repository (Neo4j), SQLAlchemy models & repositories, encrypted vault, LLM providers (Mistral / OpenAI / DeepSeek), Celery app |
| **Enrichers** (`jsint-enrichers`) | 49 enrichers, 11 tools (asnmap, dnsx, httpx, mapcidr, naabu, subfinder, whoxy, whoisxml, reconcrawl, sirene, apify), auto-registered via `@jsint_enricher` |
| **Types** (`jsint-types`) | 40 Pydantic entity models (Domain, Ip, ASN, CIDR, Email, Username, SocialAccount, Phone, Individual, Organization, Website, CryptoWallet, Device, Breach, …) with a decorator registry |
| **Data** | PostgreSQL (metadata, users, vault, runs), Neo4j 5 + APOC (the graph), Redis (Celery broker + events) |
| **Runtime** | Docker Compose: `api`, `celery`, `app` (nginx), `postgres`, `neo4j`, `redis` |

### Project structure

```
jsint-app (frontend)
    ↓
jsint-api (FastAPI server)
    ↓
jsint-core (orchestrator, tasks, vault, graph services)
    ↓
jsint-enrichers (enrichers & tools)
    ↓
jsint-types (entity models)
```

| Module | Contents |
|---|---|
| **jsint-types** | Pydantic models for every entity, `@jsint_type` registry, type detection helpers |
| **jsint-enrichers** | Enricher modules by category, HTTP/Docker tools, enricher registry + auto-discovery |
| **jsint-core** | Enricher base class, flow orchestrator, graph repository/service/serializer, PostgreSQL models + repositories + services, vault, auth, logger, Celery tasks, LLM factory |
| **jsint-api** | Route modules (`auth`, `sketches`, `investigations`, `enrichers`, `flows`, `events`, `analyses`, `chats`, `scans`, `keys`, `types`, `custom-types`), schemas, Alembic migrations |
| **jsint-app** | Routes, components (graph, sketches, flows, tables, map, chat, terminal), API clients, Zustand stores, theme |

