-- Migration: 20261003101747_add_carbon_details_to_blocks.sql
-- Adds detailed carbon stock metrics to carbon_blocks table for block inspection API.
-- Uses IF NOT EXISTS to guarantee idempotent and clean-project execution.

ALTER TABLE public.carbon_blocks
    ADD COLUMN IF NOT EXISTS canopy_area_m2 NUMERIC,
    ADD COLUMN IF NOT EXISTS estimated_tree_count NUMERIC,
    ADD COLUMN IF NOT EXISTS above_ground_biomass_kg NUMERIC;
