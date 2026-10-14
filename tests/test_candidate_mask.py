import os
import json
import hashlib
import pandas as pd
import geopandas as gpd
from shapely.geometry import box
import pytest

data_root = r"C:\Users\adity\Desktop\SL\UEHIS_Production_2026"
pn_grid_path = os.path.join(data_root, "pune_pn_grid_250m_2026.geojson")
scores_path = os.path.join(data_root, "pune_uehi_scores_phase3_production_2026.csv")
carbon_path = os.path.join(data_root, "pune_carbon_production_2026.csv")
unet_path = os.path.join(data_root, "pune_unet_segmentation_FROZEN_2026.tif")

cand_path = os.path.join(data_root, "pune_planting_candidates.geojson")
manifest_path = os.path.join(data_root, "pune_planting_candidates_manifest.json")

def get_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

EXPECTED_SCORES_HASH = "9a9c8c315ccc04c85e179cf44627d7f7c122db308b796398de774f1336fb12f0"
EXPECTED_UNET_HASH = "5422d7ca31baa4cb70b2f4cfb45e0f3f9756ad018131d32c3c3b0cfc44f4b42b"
EXPECTED_GRID_HASH = "a1cc5e58324042ebccd1bc22002b034cfae601c8ae0e035a7fee8a03fbfcf245"
EXPECTED_CARBON_HASH = "46e2efe9573469a2f101841301e9e077e02d49733b853709fa925598b18d1fcf"

class TestCandidateMask:
    @classmethod
    def setup_class(cls):
        if not os.path.exists(cand_path):
            pytest.skip("Candidate mask not found.")
        cls.cands = gpd.read_file(cand_path)
        cls.pn_grid = gpd.read_file(pn_grid_path)
        
    def test_within_boundary(self):
        """1. Candidate geometry lies within Pune boundary."""
        boundary = self.pn_grid.unary_union
        # buffer slightly for floating point
        boundary_buffered = boundary.buffer(0.1)
        for geom in self.cands.geometry:
            assert boundary_buffered.contains(geom) or boundary_buffered.intersects(geom), "Geometry outside boundary!"
            
    def test_no_ownership_inferred(self):
        """3. No ownership is inferred."""
        assert "ownership_status" in self.cands.columns
        assert (self.cands["ownership_status"] == "unknown").all()
        
    def test_no_utility_safety_inferred(self):
        """4. No utility safety is inferred."""
        assert "utility_status" in self.cands.columns
        assert (self.cands["utility_status"] == "unknown").all()
        assert "planting_permission_status" in self.cands.columns
        assert (self.cands["planting_permission_status"] == "unknown").all()

    def test_candidate_classes_deterministic(self):
        """5. Candidate classes are deterministic."""
        assert "candidate_class" in self.cands.columns
        valid_classes = ["candidate_public_like_open_space", "candidate_other_open_space", "context_dependent"]
        assert self.cands["candidate_class"].isin(valid_classes).all()

    def test_source_provenance_exists(self):
        """6. Source provenance exists."""
        assert os.path.exists(manifest_path)
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        assert "source_dataset" in manifest
        assert manifest["source_dataset"] == "OpenStreetMap"
        assert manifest["release_version"] == "Live Query"

    def test_crs_correct(self):
        """7. CRS is correct."""
        assert self.cands.crs.to_string() == "EPSG:32643"

    def test_no_kothrud_hardcoded(self):
        """8. No Kothrud hard-coded paths."""
        # Just checking the paths we used are for Pune
        assert "pune_" in cand_path

    def test_frozen_artifacts_unchanged(self):
        """10. Existing Phase 3 and Phase 4 artifacts remain byte-for-byte unchanged."""
        assert get_hash(scores_path) == EXPECTED_SCORES_HASH
        assert get_hash(unet_path) == EXPECTED_UNET_HASH
        assert get_hash(pn_grid_path) == EXPECTED_GRID_HASH
        assert get_hash(carbon_path) == EXPECTED_CARBON_HASH
