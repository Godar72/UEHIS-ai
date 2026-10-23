# UEHIS — Authoritative AWS Recovery & Forensic Audit Report

**Audit Mode:** Strict Non-Destructive Read-Only Audit via Authenticated AWS Systems Manager (SSM)  
**Target Host:** AWS EC2 (`ip-172-31-4-14.ap-south-1.compute.internal` / `43.204.224.20`)  
**Project Directory on Host:** `/opt/uehis`  
**Execution Timestamp:** `2026-10-23T17:48:29Z` (UTC) / `2026-10-23T23:18:29+05:30` (IST)  
**Lead Auditor:** Senior DevOps Engineer, Geospatial Systems Architect, and Reliability Lead  

---

## 1. Access Method & Execution Topology

Direct external access to TCP port 22 on the EC2 host is firewalled by AWS Security Groups. All inspection operations were executed via an **authenticated, read-only AWS Systems Manager (SSM) session** (`ssm-user` with `sudo` for Docker inspection). Zero containers were restarted, rebuilt, or stopped; zero production databases were mutated; zero live environment variables or secrets were exposed.

---

## 2. Container Inventory & Running Image Identifiers

```
NAMES                           IMAGE                                      STATUS                  CREATED AT
uehis-frontend-carbon-test      uehis-frontend:carbon-fix-20261023         Up 4 hours (healthy)    2026-10-23 13:45:04 UTC
uehis-frontend-old-preview      uehis-frontend:rollback-20261019T163609Z   Up 7 hours (healthy)    2026-10-23 11:14:19 UTC
uehis-frontend-fixes-test2      uehis-frontend:fixes-20261023b             Up 7 hours (healthy)    2026-10-23 10:46:10 UTC
uehis-frontend-fixes-test       uehis-frontend:fixes-20261023              Up 8 hours (healthy)    2026-10-23 10:08:13 UTC
uehis-frontend-candidate-test   uehis-frontend:candidate-c0170c4           Up 20 hours (healthy)   2026-10-22 21:22:48 UTC
uehis-frontend-deployed         uehis-frontend:panel-fix-test              Up 22 hours (healthy)   2026-10-22 20:08:47 UTC
uehis-frontend-panel-test       uehis-frontend:panel-fix-test              Up 22 hours (healthy)   2026-10-22 19:59:36 UTC
uehis-api                       uehis-api:latest                           Up 23 hours (healthy)   2026-10-22 18:45:35 UTC
uehis-proxy                     nginx:alpine                               Up 8 days (healthy)     2026-10-15 05:03:21 UTC
```

### 2.1 The "Smoking Gun" Discovery: Nginx Proxy Routing
Inspection of Docker network aliases across the running containers revealed why the public website served stale text:
- **`uehis-proxy` Upstream Target:** Configured to proxy to `http://frontend_service;` resolving to `frontend:3000`.
- **Active Network Alias Assignment:**
  - `uehis-frontend-old-preview` -> Aliased to `frontend`!
  - `uehis-frontend-carbon-test` -> Aliased to `frontend-carbon-rollback`
  - `uehis-frontend-candidate-test` -> Aliased to `frontend-candidate-rollback`
- **Root Cause:** Public ingress traffic on `https://uehis.duckdns.org` was explicitly routed to `uehis-frontend-old-preview` (running rollback image `uehis-frontend:rollback-20261019T163609Z`, Next.js BUILD_ID `gW6JygSQz7sxG3jplaXr0`). The newer candidate builds remained dormant on the host.

---

## 3. Host Working-Tree Status in `/opt/uehis`

- **Git HEAD Commit:** `9355deff7015f3b64c4524214458371910093bc2` (`feat(deploy): finalize Docker Compose, Nginx ACME staging, and non-root API hardening`)
- **Working Tree State:** The host working tree was never fast-forwarded to commit `c0170c42`. Instead, local fixes were applied directly in `/opt/uehis`:
  1. `frontend/src/lib/planting-unit-utils.ts` (**Untracked module created directly on AWS**).
  2. `frontend/src/components/StudyAreaResult/StudyAreaResult.tsx` (Animation slide set to 380px).
  3. `frontend/src/components/StudyAreaResult/StudyAreaResult.module.css` (Panel resized from 440px to 380px).
  4. `frontend/src/components/Map/MapView.tsx` (Planting candidate areas styled with `#3D7650` fill and `#A7D7B5` outline).
  5. `docker-compose.yml` (Secret mounted from `/etc/uehis-secrets/api/gee-sa-key.json:ro`).

---

## 4. Container vs. Host Source Fingerprints

### 4.1 Backend API (`uehis-api:latest`)
- **Container `/app/api/main.py` SHA256:** `2952c9be119559c1d8ac674a524357decfaef3f94c22996a4866c8d84d984296`
- **Host `/opt/uehis/api/main.py` SHA256:** `d854e714f7436118b20dfcd23869846343ba907b099aa7290cd8545836d75ccb`
- **Diff Analysis:** The running container contains the verified carbon density metrics:
  - `canopy_density_t_co2e_per_ha: 229.22`
  - `gross_grid_density_t_co2e_per_ha: 14.86`
- **Container `/app/api/study_area.py`:** Contains `query_candidate_blocks_in_area`, `candidate_blocks` aggregation, and `POST /study-area/candidates`.

---

## 5. Authoritative Source Decisions by Component

| Component | Recovered Authoritative Source | Reason & Verification |
| :--- | :--- | :--- |
| **Backend API (`main.py`, `study_area.py`)** | AWS Container `uehis-api:latest` + commit `c0170c42` | Contains verified 229.22 t/ha canopy density, 14.86 t/ha gross grid density, and candidate block endpoints. |
| **Study Area Layout & CSS** | AWS Working Tree `/opt/uehis` | 380px panel width (`flex: 0 0 380px`) and matching animation props prevent map canvas crowding on laptop viewports. |
| **Planting Unit Utilities** | AWS Untracked `/opt/uehis` (`planting-unit-utils.ts`) | Extracted modular parsing for UUIDv5 and UTM 43N coordinates. |
| **Map Rendering (`MapView.tsx`)** | AWS Working Tree + Local Refinement | Incorporates `#3D7650` green planting fill, `styleDiffing={false}`, and microtask popup stability. |
| **Search Control (`Search.tsx`)** | Local Refinement (Verified) | Enter-key auto-selection of first geocoding result. |
| **Scoring Polarity & Risk Tiers** | Canonical Architecture (`scoring/uehi_config.json`) | **Higher = Healthier**; Critical (<25), High (25-<50), Mod (50-<75), Low (≥75). Stale rollback UI polarity was rejected. |
| **Regression Test Suites** | Local Workspace Tests | 19 tests validating carbon math and candidate block ranking contracts. |
