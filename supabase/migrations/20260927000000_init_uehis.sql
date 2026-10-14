-- ==============================================================================
-- UEHIS PRODUCTION DATABASE MIGRATION - PHASE 1
-- Based on FROZEN UEHIS Data & API Architecture v2
-- ==============================================================================

-- 1. Enable Required Extensions
CREATE EXTENSION IF NOT EXISTS postgis;

-- 2. Create Enums and Types
CREATE TYPE risk_level AS ENUM ('Critical', 'High', 'Moderate', 'Low');
CREATE TYPE pipeline_type AS ENUM ('uehi_scoring', 'carbon_estimation', 'planting_candidate_generation', 'planting_scenario_generation');
CREATE TYPE location_type AS ENUM ('authoritative_boundary', 'point_radius', 'user_polygon');

-- 3. Create Tables

-- Provenance: Data Sources
CREATE TABLE data_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_name TEXT NOT NULL,
    dataset_name TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    data_year INT NOT NULL,
    spatial_resolution TEXT NOT NULL,
    source_url TEXT,
    processing_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Provenance: Methodology Versions
CREATE TABLE methodology_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_type pipeline_type NOT NULL,
    version_hash TEXT UNIQUE NOT NULL,
    description TEXT NOT NULL,
    valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Provenance: Production Runs
CREATE TABLE production_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_name TEXT NOT NULL,
    pipeline_version TEXT NOT NULL,
    run_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    input_manifest_hash TEXT NOT NULL,
    output_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    notes TEXT
);

-- Analytical Outputs: UEHI Blocks
CREATE TABLE uehi_blocks (
    block_id TEXT PRIMARY KEY,
    geom geometry(Polygon, 32643) NOT NULL,
    
    -- Scientific factors
    tree_density NUMERIC,
    ndvi NUMERIC,
    impervious_surfaces NUMERIC,
    temperature NUMERIC,
    population_exposure NUMERIC,
    pm25 NUMERIC,
    
    -- Scoring
    uehi_score NUMERIC CHECK (uehi_score >= 0 AND uehi_score <= 100),
    risk_level risk_level,
    is_excluded BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Provenance Links
    methodology_id UUID NOT NULL REFERENCES methodology_versions(id),
    production_run_id UUID NOT NULL REFERENCES production_runs(id)
);

-- Analytical Outputs: Carbon Blocks
CREATE TABLE carbon_blocks (
    block_id TEXT PRIMARY KEY REFERENCES uehi_blocks(block_id),
    geom geometry(Polygon, 32643) NOT NULL,
    standing_carbon_stock NUMERIC NOT NULL,
    
    -- Provenance Links
    methodology_id UUID NOT NULL REFERENCES methodology_versions(id),
    production_run_id UUID NOT NULL REFERENCES production_runs(id)
);

-- Analytical Outputs: Planting Candidates
CREATE TABLE planting_candidates (
    candidate_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    geom geometry(Point, 32643) NOT NULL,
    status TEXT NOT NULL DEFAULT 'verification required',
    
    -- Explicitly communicating uncertainty
    ownership_unknown BOOLEAN NOT NULL DEFAULT TRUE,
    permission_unknown BOOLEAN NOT NULL DEFAULT TRUE,
    utility_clearance_unknown BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Provenance Links
    methodology_id UUID NOT NULL REFERENCES methodology_versions(id),
    production_run_id UUID NOT NULL REFERENCES production_runs(id)
);

-- Analytical Outputs: Planting Scenarios
CREATE TABLE planting_scenarios (
    scenario_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_name TEXT NOT NULL,
    selected_unit_count INT NOT NULL,
    spacing_m NUMERIC NOT NULL,
    scenario_carbon_assumption NUMERIC NOT NULL DEFAULT 0.5,
    assumption_type TEXT NOT NULL,
    priority_method TEXT NOT NULL,
    
    -- Provenance Link
    methodology_id UUID NOT NULL REFERENCES methodology_versions(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- User Entities: Study Areas
CREATE TABLE study_areas (
    area_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID, -- Nullable for anonymous sessions. In a real environment, FK to auth.users(id)
    name TEXT NOT NULL,
    location_type location_type NOT NULL,
    radius_m NUMERIC,
    geom geometry(MultiPolygon, 32643) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. Create Indexes

-- GiST spatial indexes (Justification: required for map viewport intersection queries and rendering)
CREATE INDEX idx_uehi_blocks_geom ON uehi_blocks USING GIST (geom);
CREATE INDEX idx_carbon_blocks_geom ON carbon_blocks USING GIST (geom);
CREATE INDEX idx_planting_candidates_geom ON planting_candidates USING GIST (geom);
CREATE INDEX idx_study_areas_geom ON study_areas USING GIST (geom);

-- B-tree indexes (Justification: required for fast filtering and provenance joins)
CREATE INDEX idx_uehi_blocks_risk_level ON uehi_blocks (risk_level);
CREATE INDEX idx_uehi_blocks_prod_run ON uehi_blocks (production_run_id);
CREATE INDEX idx_uehi_blocks_methodology ON uehi_blocks (methodology_id);

CREATE INDEX idx_carbon_blocks_prod_run ON carbon_blocks (production_run_id);
CREATE INDEX idx_carbon_blocks_methodology ON carbon_blocks (methodology_id);

CREATE INDEX idx_planting_candidates_prod_run ON planting_candidates (production_run_id);
CREATE INDEX idx_planting_candidates_methodology ON planting_candidates (methodology_id);

CREATE INDEX idx_study_areas_location_type ON study_areas (location_type);

-- 5. Row Level Security (RLS)

ALTER TABLE data_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE methodology_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE production_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE uehi_blocks ENABLE ROW LEVEL SECURITY;
ALTER TABLE carbon_blocks ENABLE ROW LEVEL SECURITY;
ALTER TABLE planting_candidates ENABLE ROW LEVEL SECURITY;
ALTER TABLE planting_scenarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE study_areas ENABLE ROW LEVEL SECURITY;

-- Public read access for safe analytical and provenance tables
CREATE POLICY "Public select on data_sources" ON data_sources FOR SELECT TO public USING (true);
CREATE POLICY "Public select on methodology_versions" ON methodology_versions FOR SELECT TO public USING (true);
CREATE POLICY "Public select on production_runs" ON production_runs FOR SELECT TO public USING (true);
CREATE POLICY "Public select on uehi_blocks" ON uehi_blocks FOR SELECT TO public USING (true);
CREATE POLICY "Public select on carbon_blocks" ON carbon_blocks FOR SELECT TO public USING (true);
CREATE POLICY "Public select on planting_scenarios" ON planting_scenarios FOR SELECT TO public USING (true);

-- planting_candidates deliberately lacks a public SELECT policy.
-- Unrestricted table access is prohibited. It will be served exclusively through controlled RPCs/APIs bypassing RLS safely via SECURITY DEFINER.

-- Study areas policies
CREATE POLICY "Users can manage their own study areas" ON study_areas FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Anon can view unowned study areas" ON study_areas FOR SELECT TO anon USING (user_id IS NULL);
CREATE POLICY "Anon can create unowned study areas" ON study_areas FOR INSERT TO anon WITH CHECK (user_id IS NULL);
