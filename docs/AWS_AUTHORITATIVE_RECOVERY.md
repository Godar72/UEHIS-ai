# UEHIS — Authoritative AWS Recovery & Forensic Audit Report

**Audit Mode:** Strict Non-Destructive Read-Only Audit via Authenticated AWS Systems Manager (SSM)
**Target Environment:** AWS EC2 Production Environment
**Project Directory on Host:** `/opt/uehis`
**Audit Scope:** Production Host & Container Forensic Inspection
**Lead Auditor:** Senior DevOps Engineer, Geospatial Systems Architect, and Reliability Lead

---

## 1. Access Method & Execution Topology

Direct external access to TCP port 22 on the EC2 host is firewalled by AWS Security Groups. All inspection operations were executed via an **authenticated, read-only AWS Systems Manager (SSM) session** (`ssm-user` with `sudo` for container inspection). No containers were restarted, rebuilt, or stopped during the audit; no production databases were mutated; and no secret values were retrieved or recorded.

---

## 2. Ingress Routing & Frontend Deployment Discrepancy

Forensic inspection of the reverse proxy configuration and container networking resolved why the deployed website served legacy copy (including inverted scoring statements):

- **Reverse Proxy Routing:** The Nginx proxy configuration routed incoming traffic from the `frontend_service` upstream to the `frontend:3000` network alias.
- **Root Cause of Public Discrepancy:** On the production host, the `frontend` network alias was routed to an older rollback frontend container rather than the updated candidate container build.
- **Architectural Conclusion:** The deployed frontend was running an obsolete rollback build and did not match the intended recovered codebase. Consequently, the live frontend code was rejected as an authoritative source and replaced with the verified implementation reconciling GitHub base commit `c0170c42` with tested host working-tree fixes.

---

## 3. Host Working-Tree Status in `/opt/uehis`

- **Git HEAD Commit:** `9355deff7015f3b64c4524214458371910093bc2` (`feat(deploy): finalize Docker Compose, Nginx ACME staging, and non-root API hardening`)
- **Working Tree State:** The host working tree was on an earlier commit and had not been fast-forwarded to commit `c0170c42`. However, essential bug fixes and module extractions were applied directly in the `/opt/uehis` working tree:
  1. `frontend/src/lib/planting-unit-utils.ts` (**Untracked module created directly on AWS**).
  2. `frontend/src/components/StudyAreaResult/StudyAreaResult.tsx` (Slide animation reconciled to 380px).
  3. `frontend/src/components/StudyAreaResult/StudyAreaResult.module.css` (Panel width adjusted from 440px to 380px).
  4. `frontend/src/components/Map/MapView.tsx` (Planting candidate areas styled with `#3D7650` fill and outline).
  5. `docker-compose.yml` (Secret mounted from external path `/etc/uehis-secrets/api/gee-sa-key.json:ro`).

---

## 4. Container vs. Host Source Fingerprints

### 4.1 Backend API
- **Running API Container `/app/api/main.py` SHA256:** `2952c9be119559c1d8ac674a524357decfaef3f94c22996a4866c8d84d984296`
- **Host `/opt/uehis/api/main.py` SHA256:** `d854e714f7436118b20dfcd23869846343ba907b099aa7290cd8545836d75ccb`
- **Hash Divergence Analysis:** The recorded source hashes differ between the running container and the host file system. The container was observed to contain the specified API behavior, including the verified carbon density metrics:
  - `canopy_density_t_co2e_per_ha: 229.22`
  - `gross_grid_density_t_co2e_per_ha: 14.86`
- **Container `/app/api/study_area.py`:** Contains observed `query_candidate_blocks_in_area`, candidate blocks aggregation, and `/study-area/candidates` contracts.

---

## 5. Authoritative Source Decisions by Component

| Component | Recovered Authoritative Source | Reason & Verification |
| :--- | :--- | :--- |
| **Backend API (`main.py`, `study_area.py`)** | Observed API Container Behavior | Contains verified 229.22 t/ha canopy density, 14.86 t/ha gross grid density, and candidate block endpoints. Recorded container source hash differs from host file hash. |
| **Study Area Layout & CSS** | AWS Working Tree `/opt/uehis` | 380px panel width (`flex: 0 0 380px`) and matching animation props prevent map canvas crowding on laptop viewports. |
| **Planting Unit Utilities** | AWS Untracked `/opt/uehis` (`planting-unit-utils.ts`) | Extracted modular parsing for UUIDv5 and UTM 43N coordinates. |
| **Map Rendering (`MapView.tsx`)** | AWS Working Tree + Local Refinement | Incorporates `#3D7650` green planting palette, `styleDiffing={false}`, and microtask popup stability. |
| **Search Control (`Search.tsx`)** | Local Refinement (Verified) | Enter-key auto-selection of first geocoding result. |
| **Scoring Polarity & Risk Tiers** | Canonical Architecture (`scoring/uehi_config.json`) | **Higher = Healthier**; Critical (<25), High (25-<50), Mod (50-<75), Low (≥75). Stale rollback UI polarity was rejected. |
| **Regression Test Suites** | Local Workspace Tests | Validates carbon math and candidate block ranking contracts. |
