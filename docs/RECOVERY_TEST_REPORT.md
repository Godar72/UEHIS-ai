# UEHIS — Recovery Test & Verification Report

**Environment:** Windows, Python 3.12.10, Node.js v20+, TypeScript 5+, Next.js 16.3.6  
**Target Repository:** `C:\Users\adity\Desktop\UEHIS-AWS-Recovery`  
**Execution Timestamp:** `2026-10-23T23:28:00+05:30`  

---

## 1. Backend Automated Pytest Suite

Executed against the recovered test files in `C:\Users\adity\Desktop\UEHIS-AWS-Recovery\tests`:

```
Command: pytest tests/test_carbon_density_regression.py tests/test_location_search_and_planting.py -v
Platform: Windows, Python 3.12.10, pytest-9.1.1, pluggy-1.6.0

Collected 19 items:
tests/test_carbon_density_regression.py::TestCarbonDensityMathematics::test_canopy_area_normalized_density PASSED [  5%]
tests/test_carbon_density_regression.py::TestCarbonDensityMathematics::test_gross_grid_normalized_density PASSED [ 10%]
tests/test_carbon_density_regression.py::TestCarbonDensityMathematics::test_factor_of_ten_regression PASSED [ 15%]
tests/test_carbon_density_regression.py::TestCarbonDensityMathematics::test_km2_to_ha_conversion PASSED [ 21%]
tests/test_carbon_density_regression.py::TestProductionDatasetDensityIntegrity::test_production_csv_totals_and_density PASSED [ 26%]
tests/test_carbon_density_regression.py::TestStandingStockSemanticsCompatibility::test_standing_stock_column_names PASSED [ 31%]
tests/test_carbon_density_regression.py::TestApiSummaryCarbonDensity::test_api_summary_density_calculation PASSED [ 36%]
tests/test_location_search_and_planting.py::TestGeographicCoverageBounds::test_pune_core_localities_in_coverage PASSED [ 42%]
tests/test_location_search_and_planting.py::TestGeographicCoverageBounds::test_outside_locations_identified_as_uncovered PASSED [ 47%]
tests/test_location_search_and_planting.py::TestCandidateBlockRankingAndExplanations::test_ranking_explanation_critical_need PASSED [ 52%]
tests/test_location_search_and_planting.py::TestCandidateBlockRankingAndExplanations::test_ranking_explanation_high_need PASSED [ 57%]
tests/test_location_search_and_planting.py::TestCandidateBlockRankingAndExplanations::test_ranking_explanation_stable_baseline PASSED [ 63%]
tests/test_location_search_and_planting.py::TestCandidateBlockRankingAndExplanations::test_unscored_excluded_block_explanation PASSED [ 68%]
tests/test_location_search_and_planting.py::TestCanonicalRiskClassificationScale::test_threshold_boundaries PASSED [ 73%]
tests/test_location_search_and_planting.py::TestStandingStockSemanticsAndDensity::test_density_denominators PASSED [ 78%]
tests/test_location_search_and_planting.py::TestStandingStockSemanticsAndDensity::test_standing_stock_field_name_in_candidates PASSED [ 84%]
tests/test_location_search_and_planting.py::TestApiSecurityAndEndpointContracts::test_study_area_requires_auth_key PASSED [ 89%]
tests/test_location_search_and_planting.py::TestApiSecurityAndEndpointContracts::test_study_area_candidates_endpoint_structure PASSED [ 94%]
tests/test_location_search_and_planting.py::TestApiSecurityAndEndpointContracts::test_invalid_geometry_rejected PASSED [100%]

======================= 19 passed, 2 warnings in 65.97s =======================
```

---

## 2. Frontend TypeScript Compilation

```
Command: node frontend/node_modules/typescript/bin/tsc --noEmit --project frontend/tsconfig.json
Result: 0 errors (Passed cleanly in 4.1s)
Exit Code: 0
```

---

## 3. Next.js 16 Production Build Verification

```
Command: npm run build
Result:
▲ Next.js 16.3.6 (Turbopack)
✓ Compiled successfully in 6.9s
✓ Finished TypeScript in 4.1s
✓ Generating static pages using 21 workers (30/30) in 952ms
Route Status: 30/30 routes compiled cleanly (Static & Dynamic)
Exit Code: 0
```
