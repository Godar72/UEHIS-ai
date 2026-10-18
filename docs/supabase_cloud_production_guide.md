# UEHIS — Supabase Cloud Production Guide & Architecture Blueprint

**System**: Urban Ecosystem Health Intelligence System (UEHIS)  
**Target Infrastructure**: AWS EC2 (`ap-south-1`) + Supabase Cloud Managed PostgreSQL Tier  
**Database Engine**: PostgreSQL 17 + PostGIS (Hosted by Supabase Cloud)  
**Status**: Pre-Cloud Provisioning Audit (Read-Only; Verified Against Commit `7985db69`)  

---

## 1. Production Environment-Variable Inventory

The following table specifies every production variable consumed across the Nginx reverse proxy, Next.js web application, and FastAPI geospatial microservice.  
*All values shown are safe placeholders — NEVER commit actual secrets.*

| Variable Name | Secret / Public | Consumer Layer | Purpose & Validation Rules | Configuration Location |
| :--- | :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | Server-Only | FastAPI, Next.js | Enforces fail-closed security and remote TLS requirements. Must be set to `production`. | EC2 `.env`, Docker Compose |
| `DATABASE_URL` | Server-Only | FastAPI (`api/database.py`) | Remote PostgreSQL connection string. Must point to a remote host and include `?sslmode=require`. | EC2 `.env` |
| `DOCKER_DATABASE_URL` | Server-Only | FastAPI container | Dedicated container network connection string. Falls back to `DATABASE_URL`. | EC2 `.env` |
| `NEXT_PUBLIC_SUPABASE_URL` | **Public** | Browser JS, Next.js SSR | Canonical HTTPS URL for Supabase Cloud (`https://[project-ref].supabase.co`). | Docker Build ARG & Runtime ENV |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | **Public** | Browser JS, Next.js SSR | Anonymous client API key. Governed by database Row-Level Security (RLS). | Docker Build ARG & Runtime ENV |
| `SUPABASE_INTERNAL_URL` | Server-Only | Next.js Server | Internal base URL for container-to-Supabase REST/Auth calls. Set to same as `NEXT_PUBLIC_SUPABASE_URL`. | EC2 `.env`, Runtime ENV |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-Only | Next.js Server (`admin.ts`) | Elevated service-role key for administrative tasks (account deletion, rate-limit resets). **Never leak to client.** | EC2 `.env`, Runtime ENV |
| `NEXT_PUBLIC_SITE_URL` | **Public** | Next.js Browser/SSR | Canonical public domain URL (e.g. `https://uehis.duckdns.org`). | Docker Build ARG & Runtime ENV |
| `UEHIS_API_KEY` | Server-Only | Next.js Server, FastAPI | Shared internal secret token passed via `X-API-Key` header. FastAPI fails closed without it. | EC2 `.env`, Runtime ENV |
| `PYTHON_SERVICE_URL` | Server-Only | Next.js Server | Internal Docker network URL to reach FastAPI microservice (`http://api:8000`). | Docker Compose Runtime ENV |
| `NEXT_PUBLIC_MAPTILER_API_KEY` | **Public** | Browser JS | MapTiler client key for client-side raster satellite and vector basemaps. | Docker Build ARG & Runtime ENV |
| `MAPTILER_API_KEY` | Server-Only | Next.js Server | Server-side MapTiler API key for proxying tile requests if needed. | EC2 `.env`, Runtime ENV |
| `GEOAPIFY_API_KEY` | Server-Only | Next.js Server | Server-side location autocomplete and forward geocoding token (`/api/geocode`). | EC2 `.env`, Runtime ENV |
| `OPENWEATHER_API_KEY` | Server-Only | FastAPI | Weather API key for dynamic temperature, humidity, and atmospheric factor ingestion. | EC2 `.env`, Runtime ENV |
| `GEE_PROJECT_ID` | Server-Only | FastAPI | Google Cloud / Earth Engine project ID for satellite canopy height queries. | EC2 `.env`, Runtime ENV |
| `GEE_SERVICE_ACCOUNT_JSON` | Server-Only | FastAPI | Optional raw JSON credential string for Google Earth Engine service account. | EC2 `.env` / Secrets Manager |
| `GEE_SERVICE_ACCOUNT_FILE` | Server-Only | FastAPI | Optional path to mounted service account JSON key file (`/etc/secrets/gee.json`). | EC2 volume mount |
| `AUTH_IP_FLOOD_LIMIT` | Server-Only | Next.js Server | Rate limit window threshold for network-level IP flooding (default: `30`). | EC2 `.env` |
| `AUTH_LOGIN_MAX_FAILED_ATTEMPTS` | Server-Only | Next.js Server | Maximum consecutive failed logins per account/IP before temporary lockout (default: `5`). | EC2 `.env` |

---

## 2. Migration-by-Migration Technical Review

All 12 active migrations in `supabase/migrations/` apply sequentially and idempotently:

| Migration File | Timestamp | Objects Created / Modified | Search Path & PostGIS Placement | Cloud Compatibility & Idempotency Notes |
| :--- | :--- | :--- | :--- | :--- |
| `20260927000000_init_uehis.sql` | 27 Sep 2026 | `postgis` ext, types (`risk_level`, `pipeline_type`, `location_type`), tables (`data_sources`, `methodology_versions`, `production_runs`, `uehi_blocks`, `carbon_blocks`, `planting_candidates`, `planting_scenarios`, `study_areas`), indexes, initial RLS | `public` default | Clean project compatible. Foreign keys to `auth.users` bind to Supabase pre-existing schema. |
| `20260927171433_planting_geometry_correction.sql` | 27 Sep 2026 | Drops naive `planting_candidates`; creates `planting_candidate_areas` (MultiPolygon), `planting_units` (Point), `planting_scenario_units` (mapping) | Default | Replaces legacy centroid table cleanly. Enables RLS on all three tables. |
| `20260927173000_api_functions.sql` | 27 Sep 2026 | `get_blocks_in_viewport`, `get_block_detail`, `generate_point_radius_study_area`, `aggregate_study_area`, `get_provenance_info` | `public, postgis` (overridden later) | Function signatures established. Granted to `anon` and `authenticated`. |
| `20260927230000_mvt_functions.sql` | 27 Sep 2026 | Vector tile RPCs: `mvt_uehi_blocks`, `mvt_carbon_blocks`, `mvt_planting_candidate_areas`, `mvt_planting_units` | `public, postgis` (overridden later) | Computes binary protobuf tiles via `ST_AsMVT`. |
| `20260928000000_study_area_risk_distribution.sql` | 28 Sep 2026 | Enhances `aggregate_study_area` to return categorical risk breakdown (`Critical`, `High`, `Moderate`, `Low`) | `public, postgis` (overridden later) | Backward-compatible JSON schema extension. |
| `20261003101747_add_carbon_details_to_blocks.sql` | 03 Oct 2026 | `canopy_area_m2`, `estimated_tree_count`, `above_ground_biomass_kg` added to `carbon_blocks` | N/A | **Idempotent**: Uses `ADD COLUMN IF NOT EXISTS`. Safe on both fresh and existing databases. |
| `20261009000000_auth_rbac_api_keys.sql` | 09 Oct 2026 | `pgcrypto` ext, `user_roles` table, `api_keys` table, `get_user_role()`, `verify_api_key()`, restricted table policies | `public` | Establishes role-based access control (`public`, `researcher`, `admin`) and API key hashing. |
| `20261009100000_security_hardening.sql` | 09 Oct 2026 | Upgrades all RPCs and MVTs; adds `get_my_role()`, `get_block_detail_public()`; enforces privilege boundaries | `public, extensions` | **Major Hardening**: Explicitly sets `search_path = public, extensions` across all functions, matching Supabase Cloud extension layout. |
| `20261015000000_fix_mvt_planting_candidate_areas.sql` | 15 Oct 2026 | Drops reference to dropped `candidate_category` column in `mvt_planting_candidate_areas` | `public, postgis` (temporary regression) | Repaired column query, but temporarily regressed search path. |
| `20261017000000_user_profiles_and_activity.sql` | 17 Oct 2026 | `user_profiles`, `user_activity`, `update_my_profile()`, `record_user_activity()` | `search_path = ''` (fully qualified) | Security-definer self-isolated user tier. Immutable audit logs. |
| `20261018000000_auth_rate_limiting.sql` | 18 Oct 2026 | `auth_rate_limits` table, atomic rate limiting functions (`check_rate_limit_atomic`, `get_rate_limit_status`, `reset_rate_limit_atomic`) | `public, extensions` | Distributed multi-instance protection. Granted strictly to `service_role`. |
| `20261019000000_fix_mvt_planting_candidate_areas_search_path.sql` | 19 Oct 2026 | Re-defines `mvt_planting_candidate_areas` with `search_path = public, extensions` | `public, extensions` | **Final Hardening**: Permanently fixes PostGIS search path for Supabase Cloud. Grants execute strictly to `authenticated`. |

---

## 3. PostGIS Extension & Schema Resolution Guarantee

* **Supabase Cloud Behavior**: In Supabase Cloud, extensions are provisioned in the `extensions` schema, whereas `public` is reserved for application domain tables.
* **Resolution Guarantee**: Every PostGIS function callable in the final application schema:
  - `mvt_uehi_blocks` -> `SET search_path = public, extensions`
  - `mvt_carbon_blocks` -> `SET search_path = public, extensions`
  - `mvt_planting_candidate_areas` -> `SET search_path = public, extensions`
  - `mvt_planting_units` -> `SET search_path = public, extensions`
  - `get_blocks_in_viewport` -> `SET search_path = public, extensions`
  - `get_block_detail` -> `SET search_path = public, extensions`
  - `get_block_detail_public` -> `SET search_path = public, extensions`
  - `generate_point_radius_study_area` -> `SET search_path = public, extensions`
  - `aggregate_study_area` -> `SET search_path = public, extensions`
  - `verify_api_key` -> calls `extensions.digest()` with `search_path = public, extensions`
* **Result**: Zero `function st_transform(...) does not exist` or `function digest(...) does not exist` runtime errors on Supabase Cloud.

---

## 4. Supabase Connection Strategy (AWS EC2 to Cloud)

### Direct Connection vs. Connection Pooler
1. **Direct Connection (`db.[project-ref].supabase.co:5432`)**:
   - In several AWS regions, Supabase Cloud direct endpoints resolve exclusively to IPv6 addresses. If the host AWS EC2 instance does not have an IPv6 egress route configured, direct TCP connections will fail with `ConnectionRefused` or `Network is unreachable`.
2. **Supabase Connection Pooler (`aws-0-[region].pooler.supabase.com:5432`)**:
   - The Supabase pooler resolves to dual-stack IPv4 and IPv6 addresses.
   - **Recommendation for FastAPI**: Use the **Session Mode Pooler (Port 5432)** with `?sslmode=require`:
     ```
     postgresql://postgres.[project-ref]:[DB_PASSWORD]@aws-0-[region].pooler.supabase.com:5432/postgres?sslmode=require
     ```
   - Session mode supports standard PostgreSQL prepared statements, transactional DDL, and full GeoAlchemy2 spatial queries.

---

## 5. Data-Loading Dependencies (Scientific Baseline Data)

> [!IMPORTANT]
> Running `supabase db push` creates the **database structure only** (tables, functions, types, and policies). It **DOES NOT** populate the 5,309 Pune blocks or planting optimization scenarios.

To transition a clean Supabase Cloud database into a functioning UEHIS environment, the scientific baseline data in `UEHIS_Production_2026/` must be loaded into the cloud instance following migration:

1. **Provenance Records**:
   - `data_sources` (Sentinel-2, Landsat-8, Pune PMC administrative boundaries)
   - `methodology_versions` (`v4.0.0-frozen-carbon`, `uehi_scoring`, etc.)
   - `production_runs` (Pipeline execution hashes)
2. **UEHI Blocks (5,309 records)**:
   - Source: `UEHIS_Production_2026/pune_uehi_scores_phase3_production_2026.csv` + `pune_pn_grid_250m_2026.geojson`
   - Target Table: `public.uehi_blocks` (EPSG:32643)
3. **Carbon Blocks (5,309 records)**:
   - Source: `UEHIS_Production_2026/pune_carbon_production_2026.csv`
   - Target Table: `public.carbon_blocks`
4. **Planting Optimization Scenarios**:
   - `100k Scenario`: `UEHIS_Production_2026/pune_planting_optimization_scenario_100k_2026.geojson`
   - `250k Scenario`: `UEHIS_Production_2026/pune_planting_optimization_scenario_250k_2026.geojson`
   - `500k Scenario`: `UEHIS_Production_2026/pune_planting_optimization_scenario_500k_2026.geojson`
   - Target Tables: `planting_scenarios`, `planting_units` (500,000 points), `planting_scenario_units` (850,000 relationships)
   - Opportunity Masks: `UEHIS_Production_2026/pune_planting_candidates.geojson` -> `planting_candidate_areas`

---

## 6. Supabase Dashboard Configuration Checklist

Execute the following one-time administrative steps in the Supabase Cloud Dashboard:

- [ ] **1. Enable SSL Enforcement**: Under *Settings -> Database -> SSL Enforcement*, verify SSL is enforced.
- [ ] **2. Auth URL Configuration**:
  - **Site URL**: `https://<domain>` (e.g. `https://uehis.duckdns.org`)
  - **Redirect URLs**:
    - `https://<domain>/**`
    - `https://<domain>/auth/callback`
    - `https://<domain>/reset-password`
- [ ] **3. Google OAuth Provider**:
  - Enter Client ID: `636877906096-...apps.googleusercontent.com`
  - Enter Google Client Secret.
  - In Google Cloud Console, set Authorized Redirect URI to:
    `https://[project-ref].supabase.co/auth/v1/callback`
- [ ] **4. Initial Administrator Role Assignment**:
  - Sign up the initial primary account via the web application or Supabase Auth.
  - In the Supabase SQL Editor, grant the admin role:
    ```sql
    INSERT INTO public.user_roles (user_id, role)
    VALUES ('<USER_UUID>', 'admin')
    ON CONFLICT (user_id) DO UPDATE SET role = 'admin';
    ```

---

## 7. Pre- and Post-Migration Test Suite

### Pre-Migration Verification (Local Repository)
1. Python unit and integration suite: `pytest tests/` (**209 passed, 1 skipped**).
2. Frontend Next.js build: `npm run build` (**clean success, exit code 0**).
3. ESLint: `npx eslint ...` (**0 errors, 0 warnings**).
4. Git state: clean working tree, 0 unreviewed changes staged.

### Post-Migration Verification (Supabase Cloud Database)
1. **Verify MVT Function Security & Grants**:
   ```sql
   SELECT proname, prosecdef, proacl FROM pg_proc WHERE proname LIKE 'mvt_%';
   ```
   *Expectation*: All 4 functions have `prosecdef = true` and appropriate execution grants.
2. **Verify Carbon Block Columns**:
   ```sql
   SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'carbon_blocks';
   ```
   *Expectation*: 8 columns present including `canopy_area_m2`, `estimated_tree_count`, and `above_ground_biomass_kg`.
3. **Verify Table Count & RLS Status**:
   ```sql
   SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';
   ```
   *Expectation*: 15 public tables, all with `rowsecurity = true` (or revoked client permissions).
4. **Verify Data Loading**:
   ```sql
   SELECT count(*) FROM public.uehi_blocks;      -- Expect 5309
   SELECT count(*) FROM public.carbon_blocks;    -- Expect 5309
   SELECT count(*) FROM public.planting_units;   -- Expect 500000
   ```

---

## 8. Go / No-Go Recommendation

### **Recommendation: GO FOR SUPABASE CLOUD LINKING & MIGRATION**

* **Blocker Evaluation**: **Zero blockers**.
* **Integrity**: Idempotent DDL, verified extension search paths, hardened security-definer execution, and strict service-role isolation.
* **Safety**: All remote actions are paused. Awaiting explicit user approval before running `supabase link` or `supabase db push`.
