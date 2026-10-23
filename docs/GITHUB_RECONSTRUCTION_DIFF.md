# UEHIS — GitHub Reconstruction Diff & Component Justification

**Repository Target:** `recovery/aws-authoritative-reconstruction`
**Base Commit:** `c0170c42241aa118378eddc3727c25eeebb9b7f5` (`origin/main`)
**Reconstruction Workspace:** `C:\Users\adity\Desktop\UEHIS-AWS-Recovery`

---

## 1. Summary of Changes

This reconstruction incorporates the verified changes recovered from the AWS host (`/opt/uehis`), running API container inspection, and local stability test suites.

```
 .gitignore                                                         |   4 +
 docs/AWS_AUTHORITATIVE_RECOVERY.md                                 |  77 +++++++
 docs/GITHUB_RECONSTRUCTION_DIFF.md                                 |  68 ++++++
 docs/RECOVERY_AND_ROLLBACK_PLAN.md                                 |  65 ++++++
 docs/RECOVERY_TEST_REPORT.md                                       |  64 ++++++
 docs/SECURITY_AUDIT.md                                             |  47 ++++
 frontend/src/app/api/planting/units/[id]/route.ts                  | 123 +---------
 frontend/src/app/explore/[[...slug]]/page.tsx                      |  74 +++---
 frontend/src/components/Map/MapView.tsx                            |  24 +-
 frontend/src/components/Sidebar/Search.tsx                         |   2 +
 frontend/src/components/StudyAreaResult/StudyAreaResult.module.css  |  21 +-
 frontend/src/components/StudyAreaResult/StudyAreaResult.tsx         |  10 +-
 frontend/src/lib/planting-unit-utils.ts                            | 105 +++++++++
 tests/test_carbon_density_regression.py                            | 182 +++++++++++++++
 tests/test_location_search_and_planting.py                         | 251 +++++++++++++++++++++
 15 files changed, 957 insertions(+), 160 deletions(-)
```

---

## 2. File-by-File Technical Justification

### 2.1 `frontend/src/lib/planting-unit-utils.ts`
- **Origin:** Recovered from untracked files on AWS EC2 host `/opt/uehis`.
- **Justification:** Modularizes UUIDv5 generation and UTM Zone 43N projected coordinate parsing (`parseCoordinates`, `isUtm43n`) out of Next.js route handlers into a testable standalone module.

### 2.2 `frontend/src/app/api/planting/units/[id]/route.ts`
- **Origin:** Recovered from AWS `/opt/uehis` working tree.
- **Justification:** Replaces 110 lines of inlined crypto and byte parsing with imports from `planting-unit-utils.ts`, maintaining full backward compatibility by re-exporting all interfaces.

### 2.3 `frontend/src/components/StudyAreaResult/StudyAreaResult.tsx` & `.module.css`
- **Origin:** Recovered from AWS `/opt/uehis` working tree diff.
- **Justification:** Desktop panel width resized from `440px` to `380px` (`flex: 0 0 380px`, `box-sizing: border-box`, `box-shadow: -4px 0 16px rgba(0, 21, 68, 0.08)`); animation slide parameters updated to `initial: { x: 380, y: 0 }`, `exit: { x: 380, y: 0 }`. Prevents study area inspection panels from occluding the map canvas on laptop screens.

### 2.4 `frontend/src/components/Map/MapView.tsx`
- **Origin:** Reconciled from AWS `/opt/uehis` working tree and local UX refinements.
- **Justification:**
  - Sets planting candidate area fill to `#3D7650` (opacity 0.16) with line outline `#3D7650` (width 1.5, opacity 0.85).
  - Sets `styleDiffing={false}` on the `<Map>` element to eliminate MapLibre GL layer detachment and WebGL style flickering.
  - Eliminates microtask queue glitches when displaying the search origin marker popup.

### 2.5 `frontend/src/app/explore/[[...slug]]/page.tsx`
- **Origin:** Local stability refinement.
- **Justification:** Hardens geocoded coordinate parsing using `Number()` and `isNaN()` guards, preventing frontend runtime crashes if an address returns malformed coordinates; adds fallback for `total_blocks` to inspect `total_intersecting_blocks`.

### 2.6 `frontend/src/components/Sidebar/Search.tsx`
- **Origin:** Local UX refinement.
- **Justification:** Adds Enter-key auto-selection fallback to select `results[0]` when a user types a locality and presses Enter without navigating the dropdown.

### 2.7 `tests/test_carbon_density_regression.py` & `test_location_search_and_planting.py`
- **Origin:** Authoritative test suites.
- **Justification:** Permanently safeguards the repository against the factor-of-ten carbon density regression (22.92 vs 229.22 t/ha) and verifies candidate block ranking contracts.

### 2.8 `.gitignore`
- **Origin:** Security hardening.
- **Justification:** Excludes `*-project-*.json`, `*service-account*.json`, and `*credentials*.json` so service account keys can never be committed.
