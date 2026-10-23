'use client';

import React, { useEffect, useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import styles from './StudyAreaResult.module.css';

export interface CandidateBlock {
  rank: number;
  block_id: string;
  uehi_score: number | null;
  risk_level: string;
  need_tier: string;
  ranking_explanation: string;
  indicators: {
    tree_density: number | null;
    ndvi: number | null;
    impervious_surfaces: number | null;
    temperature: number | null;
    population_exposure: number | null;
    aqi: number | null;
  };
  carbon: {
    standing_carbon_stock_tonnes_co2e: number | null;
    canopy_area_m2: number | null;
    estimated_tree_count: number | null;
    above_ground_biomass_kg: number | null;
  };
  centroid?: [number, number] | null;
  intersection_area_m2?: number | null;
  is_excluded?: boolean;
  feasibility: {
    ownership_status: string;
    utility_status: string;
    planting_permission_status: string;
    disclaimer: string;
  };
}

export interface StudyAreaUehi {
  score?: number | null;
  risk_level?: string | null;
  total_intersecting_blocks?: number;
  total_blocks?: number;
  eligible_intersection_area_m2?: number | null;
  risk_distribution?: {
    Critical?: number;
    High?: number;
    Moderate?: number;
    Low?: number;
  };
  distribution?: Record<string, number>;
}

export interface StudyAreaCarbon {
  total_carbon?: number;
  total_carbon_tonnes_co2e?: number;
  canopy_area_km2?: number;
  canopy_area_ha?: number;
  canopy_area_m2?: number;
  tree_stems_count?: number;
  canopy_density_t_co2e_per_ha?: number;
  gross_grid_density_t_co2e_per_ha?: number;
  total_blocks_analyzed?: number;
  nonzero_blocks?: number;
  error?: string | null;
}

export interface StudyAreaData {
  uehi?: StudyAreaUehi | null;
  carbon?: StudyAreaCarbon | null;
  candidate_blocks?: CandidateBlock[];
  total_blocks?: number;
  provenance?: Record<string, unknown>;
}

interface StudyAreaResultProps {
  loading: boolean;
  data: StudyAreaData | null;
  error: string | null;
  onClose: () => void;
  locationName: string;
  boundaryType: string;
  currentRadius?: number;
  onRadiusChange?: (radiusMeters: number) => void;
  onRetry?: () => void;
  onSelectBlock?: (blockId: string) => void;
}

const RADIUS_OPTIONS = [
  { label: '500m', areaKm2: '0.79 km²', value: 500 },
  { label: '1 km', areaKm2: '3.14 km²', value: 1000 },
  { label: '2 km', areaKm2: '12.57 km²', value: 2000 },
  { label: '5 km', areaKm2: '78.54 km²', value: 5000 },
];

export function StudyAreaResult({
  loading,
  data,
  error,
  onClose,
  locationName,
  boundaryType,
  currentRadius = 2000,
  onRadiusChange,
  onRetry,
  onSelectBlock,
}: StudyAreaResultProps) {
  const [isDesktop, setIsDesktop] = useState(false);
  const [activeTab, setActiveTab] = useState<'baseline' | 'planting'>('baseline');
  const [candidateSort, setCandidateSort] = useState<'need' | 'baseline' | 'canopy'>('need');
  const [comparedBlocks, setComparedBlocks] = useState<string[]>([]);

  useEffect(() => {
    const checkIsDesktop = () => setIsDesktop(window.innerWidth >= 1024);
    checkIsDesktop();
    window.addEventListener('resize', checkIsDesktop);
    return () => window.removeEventListener('resize', checkIsDesktop);
  }, []);

  const animationProps = isDesktop
    ? {
        initial: { x: 380, y: 0 },
        animate: { x: 0, y: 0 },
        exit: { x: 380, y: 0 },
        transition: { type: 'spring' as const, damping: 28, stiffness: 220 }
      }
    : {
        initial: { y: '70%' },
        animate: { y: 0 },
        exit: { y: '70%' },
        transition: { type: 'spring' as const, damping: 28, stiffness: 220 }
      };

  const score = data?.uehi?.score;
  const isOutsideCoverage = !loading && data && (score === null || score === undefined || data.uehi?.total_intersecting_blocks === 0);

  // Canonical UEHIS Risk Classification Thresholds (<25, 25-<50, 50-<75, >=75)
  const getRiskLabel = (s?: number | null) => {
    if (s === null || s === undefined) return 'Unscored / Excluded';
    if (s < 25.0) return 'CRITICAL RISK';
    if (s < 50.0) return 'HIGH VULNERABILITY';
    if (s < 75.0) return 'MODERATE STRESS';
    return 'LOW RISK / STABLE';
  };

  const getRiskColor = (s?: number | null) => {
    if (s === null || s === undefined) return 'var(--outline)';
    if (s < 25.0) return 'var(--risk-critical)';
    if (s < 50.0) return 'var(--risk-high)';
    if (s < 75.0) return 'var(--risk-moderate)';
    return 'var(--risk-low)';
  };

  const totalDist = data?.uehi?.risk_distribution ? (
    (data.uehi.risk_distribution.Critical || 0) +
    (data.uehi.risk_distribution.High || 0) +
    (data.uehi.risk_distribution.Moderate || 0) +
    (data.uehi.risk_distribution.Low || 0)
  ) : 0;

  const isPointRadius = boundaryType.toLowerCase().includes('point') || boundaryType.toLowerCase().includes('radius');

  // Candidate blocks processing
  const rawCandidates: CandidateBlock[] = useMemo(() => {
    return data?.candidate_blocks || [];
  }, [data?.candidate_blocks]);

  const sortedCandidates = useMemo(() => {
    const list = [...rawCandidates];
    if (candidateSort === 'need') {
      // Ecological need: lower UEHI score first (highest intervention urgency)
      list.sort((a, b) => {
        if (a.is_excluded && !b.is_excluded) return 1;
        if (!a.is_excluded && b.is_excluded) return -1;
        if (a.uehi_score === null) return 1;
        if (b.uehi_score === null) return -1;
        return (a.uehi_score || 0) - (b.uehi_score || 0);
      });
    } else if (candidateSort === 'baseline') {
      // High existing canopy baseline: highest UEHI score first
      list.sort((a, b) => {
        if (a.uehi_score === null) return 1;
        if (b.uehi_score === null) return -1;
        return (b.uehi_score || 0) - (a.uehi_score || 0);
      });
    } else if (candidateSort === 'canopy') {
      // Canopy deficit: lowest canopy area first
      list.sort((a, b) => {
        const cA = a.carbon?.canopy_area_m2 ?? 999999;
        const cB = b.carbon?.canopy_area_m2 ?? 999999;
        return cA - cB;
      });
    }
    return list;
  }, [rawCandidates, candidateSort]);

  const toggleCompare = (blockId: string) => {
    setComparedBlocks(prev => {
      if (prev.includes(blockId)) return prev.filter(id => id !== blockId);
      if (prev.length >= 3) return [...prev.slice(1), blockId];
      return [...prev, blockId];
    });
  };

  const comparedCandidateData = useMemo(() => {
    return rawCandidates.filter(c => comparedBlocks.includes(c.block_id));
  }, [rawCandidates, comparedBlocks]);

  return (
    <AnimatePresence>
      <motion.aside 
        className={styles.panel}
        {...animationProps}
        role="region"
        aria-label="Spatial Analysis Results"
      >
        {/* Mobile Drag Grasp Header Handle */}
        <div className={styles.mobileGripHandle} onClick={onClose} title="Tap to close sheet">
          <div className={styles.handleBar}></div>
        </div>

        {/* Masthead */}
        <div className={styles.panelHeader}>
          <div className={styles.panelHeaderTitle}>
            <span className="material-symbols-outlined" style={{ fontSize: '16px', color: 'var(--secondary-fixed, #8ff8b3)' }}>
              data_thresholding
            </span>
            <span>Spatial Analysis Report</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className={styles.panelHeaderTag}>EPSG:32643 · 250m</span>
            <button onClick={onClose} className={styles.closeBtn} aria-label="Close analysis panel">
              <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>close</span>
            </button>
          </div>
        </div>

        {/* View Mode Tabs */}
        <div className={styles.tabBar} role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'baseline'}
            className={`${styles.tabBtn} ${activeTab === 'baseline' ? styles.tabBtnActive : ''}`}
            onClick={() => setActiveTab('baseline')}
          >
            <span className="material-symbols-outlined" style={{ fontSize: '14px' }}>tune</span>
            <span>01 Baseline Intelligence</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'planting'}
            className={`${styles.tabBtn} ${activeTab === 'planting' ? styles.tabBtnActive : ''}`}
            onClick={() => setActiveTab('planting')}
          >
            <span className="material-symbols-outlined" style={{ fontSize: '14px' }}>park</span>
            <span>02 Planting Candidates ({rawCandidates.length})</span>
          </button>
        </div>

        {/* Radius Selector Controls (when analyzing point radius) */}
        {isPointRadius && onRadiusChange && (
          <div className={styles.radiusSelectorSection}>
            <div className={styles.radiusHeader}>
              <span className={styles.radiusHeaderTitle}>Calibration Radius</span>
              <span className={styles.radiusHeaderSub}>ORIGIN BUFFER</span>
            </div>
            <div className={styles.radiusGrid}>
              {RADIUS_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  className={`${styles.radiusTabBtn} ${currentRadius === opt.value ? styles.radiusTabActive : ''}`}
                  onClick={() => onRadiusChange(opt.value)}
                >
                  <span className={styles.radiusTabLabel}>{opt.label}</span>
                  <span className={styles.radiusTabArea}>{opt.areaKm2}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        <div className={styles.content}>
          {/* Title & Technical Extent Banner */}
          <div className={styles.areaMasthead}>
            <div className={styles.areaKicker}>ANALYTICAL BUFFER EXTENT</div>
            <h2 className={styles.areaTitle}>{locationName.toUpperCase()}</h2>
            <div className={styles.disclaimerBanner}>
              <div className={styles.disclaimerAlert}>
                <span className="material-symbols-outlined text-[14px]">warning</span>
                <span>POINT-RADIUS STUDY AREA — NOT AN ADMINISTRATIVE BOUNDARY</span>
              </div>
              <div className={styles.disclaimerSubtext}>
                Isotropic spatial evaluation across Pune 250m orthogonal cell mesh. Does not correspond to official PMC ward boundaries.
              </div>
            </div>
          </div>

          {loading && !data && (
            <div className={styles.loadingState}>
              <div className={styles.spinner}></div>
              <p style={{ fontFamily: 'var(--font-jetbrains-mono)', fontSize: '11px', textTransform: 'uppercase' }}>
                Intersecting 250m orthogonal blocks...
              </p>
            </div>
          )}

          {error && (
            <div className={styles.alertError}>
              <div className={styles.errorText}>
                <span className="material-symbols-outlined text-[16px]">error</span>
                <span>{error}</span>
              </div>
              {onRetry && (
                <button type="button" onClick={onRetry} className={styles.retryBtn}>
                  <span className="material-symbols-outlined text-[14px]">refresh</span>
                  <span>Retry Analysis</span>
                </button>
              )}
            </div>
          )}

          {isOutsideCoverage && (
            <div className={styles.alertWarning} style={{ borderLeft: '4px solid var(--risk-high)', padding: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 700, color: 'var(--risk-high)', textTransform: 'uppercase', marginBottom: '4px' }}>
                <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>explore_off</span>
                <span>Location Outside Evaluated Coverage Boundary</span>
              </div>
              <div style={{ fontSize: '12px', lineHeight: 1.45, color: 'var(--on-surface-variant)' }}>
                The selected location falls outside the 5,309 computational grid blocks evaluated under the Pune Municipal Corporation (PMC) and Pimpri Chinchwad (PCMC) study baseline.
              </div>
              <div style={{ fontSize: '11px', color: 'var(--outline)', marginTop: '6px', fontFamily: 'var(--font-jetbrains-mono)' }}>
                UEHIS model formulas and carbon density calculations are not extrapolated outside established study boundaries to prevent unverified scores.
              </div>
            </div>
          )}

          {data && !isOutsideCoverage && activeTab === 'baseline' && (
            <>
              {/* Composite Environmental Health Card */}
              <div className={styles.scoreCard}>
                <div className={styles.scoreCardTop}>
                  <div>
                    <span className={styles.scoreCardLabel}>Composite Environmental Health (UEHI)</span>
                    <div className={styles.scoreRow}>
                      <span className={styles.scoreValue} style={{ color: getRiskColor(score) }}>
                        {score !== null && score !== undefined ? score.toFixed(2) : 'N/A'}
                      </span>
                      <span className={styles.scoreDenominator}>/ 100</span>
                    </div>
                  </div>
                  <span className={styles.riskBadge} style={{ backgroundColor: getRiskColor(score) }}>
                    {getRiskLabel(score)}
                  </span>
                </div>

                {/* Multi-tier distribution bar with Canonical 25/50/75 Thresholds */}
                {totalDist > 0 && (
                  <div style={{ marginTop: '10px' }}>
                    <div className={styles.distribBar}>
                      <div
                        className={styles.distribSegment}
                        style={{
                          width: `${((data.uehi?.risk_distribution?.Critical || 0) / totalDist) * 100}%`,
                          backgroundColor: 'var(--risk-critical)'
                        }}
                        title={`Critical (<25): ${data.uehi?.risk_distribution?.Critical || 0}`}
                      />
                      <div
                        className={styles.distribSegment}
                        style={{
                          width: `${((data.uehi?.risk_distribution?.High || 0) / totalDist) * 100}%`,
                          backgroundColor: 'var(--risk-high)'
                        }}
                        title={`High (25-<50): ${data.uehi?.risk_distribution?.High || 0}`}
                      />
                      <div
                        className={styles.distribSegment}
                        style={{
                          width: `${((data.uehi?.risk_distribution?.Moderate || 0) / totalDist) * 100}%`,
                          backgroundColor: 'var(--risk-moderate)'
                        }}
                        title={`Moderate (50-<75): ${data.uehi?.risk_distribution?.Moderate || 0}`}
                      />
                      <div
                        className={styles.distribSegment}
                        style={{
                          width: `${((data.uehi?.risk_distribution?.Low || 0) / totalDist) * 100}%`,
                          backgroundColor: 'var(--risk-low)'
                        }}
                        title={`Low (>=75): ${data.uehi?.risk_distribution?.Low || 0}`}
                      />
                    </div>
                    <div className={styles.distribScale} style={{ marginTop: '4px' }}>
                      <span>Critical (&lt;25)</span>
                      <span>High (25–&lt;50)</span>
                      <span>Moderate (50–&lt;75)</span>
                      <span>Low (≥75)</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Spatial Statistics 4-Tile Grid */}
              <div className={styles.statsGrid}>
                <div className={styles.statTile}>
                  <span className={styles.statLabel}>Study Area Extent</span>
                  <span className={styles.statValue}>
                    {typeof data?.uehi?.eligible_intersection_area_m2 === 'number'
                      ? `${(data.uehi.eligible_intersection_area_m2 / 1000000).toFixed(2)} km²`
                      : `${(currentRadius === 500 ? 0.79 : currentRadius === 1000 ? 3.14 : currentRadius === 2000 ? 12.57 : 78.54)} km²`}
                  </span>
                  <span className={styles.statSub}>Eligible Intersection</span>
                </div>

                <div className={styles.statTile}>
                  <span className={styles.statLabel}>Intersecting Blocks</span>
                  <span className={styles.statValue}>
                    {data.uehi?.total_intersecting_blocks ?? data.uehi?.total_blocks ?? 0}
                  </span>
                  <span className={styles.statSub}>250m Orthogonal Cells</span>
                </div>

                <div className={styles.statTile}>
                  <span className={styles.statLabel}>Coordinate System</span>
                  <span className={styles.statValue}>EPSG:32643</span>
                  <span className={styles.statSub}>UTM Zone 43N</span>
                </div>

                <div className={styles.statTile}>
                  <span className={styles.statLabel}>Grid Standard</span>
                  <span className={styles.statValue}>250 m</span>
                  <span className={styles.statSub}>Orthogonal Regular Grid</span>
                </div>
              </div>

              {/* Carbon Assessment Section (Stock Semantics Disclosed) */}
              <div>
                <div className={styles.sectionHeading}>
                  <span>Carbon Assessment within Study Area</span>
                  <span className={styles.sectionHeadingBadge}>ALLOMETRIC</span>
                </div>
                <div style={{ marginTop: '6px' }}>
                  {loading && !data.carbon ? (
                    <div style={{ padding: '8px', fontSize: '11px', color: 'var(--outline)', fontFamily: 'var(--font-jetbrains-mono)' }}>
                      Recomputing canopy allometry...
                    </div>
                  ) : data.carbon?.error ? (
                    <div className={styles.alertWarning}>
                      {data.carbon.error}
                    </div>
                  ) : data.carbon ? (
                    <div className={styles.dataTable}>
                      <div className={styles.dataRow}>
                        <span>Estimated Standing Carbon Stock</span>
                        <strong>
                          {data.carbon?.total_carbon_tonnes_co2e != null
                            ? `${data.carbon.total_carbon_tonnes_co2e.toFixed(2)} t CO₂e`
                            : 'N/A'}
                        </strong>
                      </div>
                      <div className={styles.dataRow}>
                        <span>Estimated Tree Stems</span>
                        <strong>
                          {data.carbon?.tree_stems_count != null
                            ? Number(data.carbon.tree_stems_count).toLocaleString()
                            : 'N/A'}
                        </strong>
                      </div>
                      <div className={styles.dataRow}>
                        <span>Canopy Surface Area</span>
                        <strong>
                          {data.carbon?.canopy_area_m2 != null
                            ? `${(data.carbon.canopy_area_m2 / 10000).toFixed(2)} ha`
                            : 'N/A'}
                        </strong>
                      </div>
                      <div style={{ padding: '4px 6px', fontSize: '10px', color: 'var(--muted)', fontFamily: 'var(--font-jetbrains-mono)' }}>
                        Notice: Reflects static standing biomass, NOT certifiable annual sequestration flux.
                      </div>
                    </div>
                  ) : (
                    <div style={{ padding: '6px', fontSize: '11px', color: 'var(--outline)' }}>
                      Carbon calculations synchronized with spaceborne canopy height and ETH 2020 allometric baseline.
                    </div>
                  )}
                </div>
              </div>

              {/* Quick Jump to Candidate Blocks */}
              {rawCandidates.length > 0 && (
                <button
                  type="button"
                  className={styles.backToMapBtn}
                  style={{ backgroundColor: 'var(--primary)', color: 'var(--on-primary)', borderColor: 'var(--primary)' }}
                  onClick={() => setActiveTab('planting')}
                >
                  <span className="material-symbols-outlined text-[16px]">park</span>
                  <span>Analyze {rawCandidates.length} Candidate Planting Blocks</span>
                </button>
              )}
            </>
          )}

          {data && !isOutsideCoverage && activeTab === 'planting' && (
            <div className={styles.candidateList}>
              {/* Feasibility & Governance Disclosure Banner (Phase 3 Strict Requirement) */}
              <div className={styles.disclaimerBanner} style={{ borderLeft: '3px solid var(--seer-orange, #F36B24)' }}>
                <div style={{ fontWeight: 700, color: 'var(--seer-orange, #F36B24)', textTransform: 'uppercase', marginBottom: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span className="material-symbols-outlined" style={{ fontSize: '14px' }}>policy</span>
                  <span>Feasibility &amp; Governance Advisory</span>
                </div>
                <div>
                  Low UEHI score indicates severe vegetative/thermal need, NOT verified planting feasibility. Municipal ownership, underground utility clearances, land tenure, and physical plantability have NOT been established and require empirical on-site field surveys.
                </div>
              </div>

              {/* Sorting and Filter Controls */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '6px', backgroundColor: 'var(--surface-container-low)', padding: '6px 8px', border: '1px solid var(--outline-variant)' }}>
                <span style={{ fontSize: '10px', fontFamily: 'var(--font-ibm-plex-sans)', fontWeight: 600, textTransform: 'uppercase', color: 'var(--on-surface-variant)' }}>
                  Rank Candidate Blocks By:
                </span>
                <select
                  value={candidateSort}
                  onChange={(e) => setCandidateSort(e.target.value as 'need' | 'baseline' | 'canopy')}
                  style={{
                    padding: '3px 6px',
                    fontSize: '11px',
                    fontFamily: 'var(--font-jetbrains-mono)',
                    backgroundColor: 'var(--surface-container-lowest)',
                    border: '1px solid var(--outline-variant)',
                    color: 'var(--primary)',
                    outline: 'none'
                  }}
                >
                  <option value="need">Ecological Need (Lowest UEHI first)</option>
                  <option value="baseline">Preserved Canopy (Highest UEHI first)</option>
                  <option value="canopy">Canopy Deficit (Lowest canopy area)</option>
                </select>
              </div>

              {/* Side-by-side Candidate Comparison Drawer if items selected */}
              {comparedCandidateData.length > 0 && (
                <div className={styles.compareDrawer}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--primary)', textTransform: 'uppercase' }}>
                      Candidate Comparison ({comparedCandidateData.length}/3)
                    </span>
                    <button
                      type="button"
                      onClick={() => setComparedBlocks([])}
                      style={{ background: 'none', border: 'none', fontSize: '10px', color: 'var(--outline)', cursor: 'pointer', textDecoration: 'underline' }}
                    >
                      Clear Comparison
                    </button>
                  </div>
                  <table className={styles.compareTable}>
                    <thead>
                      <tr>
                        <th>Block ID</th>
                        <th>UEHI</th>
                        <th>Risk</th>
                        <th>Canopy Area</th>
                        <th>Surface Temp</th>
                        <th>Feasibility</th>
                      </tr>
                    </thead>
                    <tbody>
                      {comparedCandidateData.map(c => (
                        <tr key={c.block_id}>
                          <td><strong>{c.block_id}</strong></td>
                          <td style={{ color: getRiskColor(c.uehi_score) }}>{c.uehi_score !== null ? c.uehi_score.toFixed(1) : 'Unscored'}</td>
                          <td>{c.risk_level}</td>
                          <td>{c.carbon?.canopy_area_m2 ? `${c.carbon.canopy_area_m2.toFixed(0)} m²` : '0 m²'}</td>
                          <td>{c.indicators?.temperature ? `${c.indicators.temperature.toFixed(1)}°C` : 'N/A'}</td>
                          <td style={{ color: 'var(--risk-high)', fontSize: '9px' }}>Unverified</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Ranked Candidate List */}
              {sortedCandidates.length === 0 ? (
                <div className={styles.emptyState}>
                  No candidate blocks found within this spatial buffer extent.
                </div>
              ) : (
                sortedCandidates.map((candidate, idx) => {
                  const isChecked = comparedBlocks.includes(candidate.block_id);
                  const riskColor = getRiskColor(candidate.uehi_score);

                  return (
                    <div
                      key={candidate.block_id}
                      className={styles.candidateCard}
                      style={{ borderLeftColor: riskColor }}
                    >
                      <div className={styles.candidateHeader}>
                        <div className={styles.candidateHeaderLeft}>
                          <span className={styles.candidateRankBadge}>#{idx + 1}</span>
                          <span className={styles.candidateBlockId}>{candidate.block_id}</span>
                        </div>
                        <span
                          className={styles.candidateRiskBadge}
                          style={{ backgroundColor: riskColor }}
                        >
                          {candidate.risk_level}
                        </span>
                      </div>

                      {/* Indicator Data Grid */}
                      <div className={styles.candidateIndicators}>
                        <div className={styles.indicatorItem}>
                          <span className={styles.indicatorLabel}>UEHI Score</span>
                          <span className={styles.indicatorVal} style={{ color: riskColor }}>
                            {candidate.uehi_score !== null ? candidate.uehi_score.toFixed(1) : 'N/A'}
                          </span>
                        </div>
                        <div className={styles.indicatorItem}>
                          <span className={styles.indicatorLabel}>Tree Density</span>
                          <span className={styles.indicatorVal}>
                            {candidate.indicators?.tree_density !== null ? candidate.indicators.tree_density.toFixed(2) : 'N/A'}
                          </span>
                        </div>
                        <div className={styles.indicatorItem}>
                          <span className={styles.indicatorLabel}>Impervious</span>
                          <span className={styles.indicatorVal}>
                            {candidate.indicators?.impervious_surfaces !== null ? `${(candidate.indicators.impervious_surfaces * 100).toFixed(0)}%` : 'N/A'}
                          </span>
                        </div>
                        <div className={styles.indicatorItem}>
                          <span className={styles.indicatorLabel}>Surface Temp</span>
                          <span className={styles.indicatorVal}>
                            {candidate.indicators?.temperature !== null ? `${candidate.indicators.temperature.toFixed(1)}°C` : 'N/A'}
                          </span>
                        </div>
                        <div className={styles.indicatorItem}>
                          <span className={styles.indicatorLabel}>Canopy Area</span>
                          <span className={styles.indicatorVal}>
                            {candidate.carbon?.canopy_area_m2 !== null ? `${candidate.carbon.canopy_area_m2.toFixed(0)} m²` : '0 m²'}
                          </span>
                        </div>
                        <div className={styles.indicatorItem}>
                          <span className={styles.indicatorLabel}>Standing Stock</span>
                          <span className={styles.indicatorVal}>
                            {candidate.carbon?.standing_carbon_stock_tonnes_co2e !== null ? `${candidate.carbon.standing_carbon_stock_tonnes_co2e.toFixed(1)} t` : '0.0 t'}
                          </span>
                        </div>
                      </div>

                      {/* Data-Driven Ranking Explanation */}
                      <div className={styles.explanationBox}>
                        <strong>Ranking Rationale:</strong> {candidate.ranking_explanation}
                      </div>

                      {/* Feasibility Disclosures */}
                      <div className={styles.feasibilityTags}>
                        <span className={styles.feasibilityBadge} title="Municipal land cadastre records unverified">
                          OWNERSHIP: UNVERIFIED
                        </span>
                        <span className={styles.feasibilityBadge} title="Subterranean utility clearance required">
                          UTILITIES: UNVERIFIED
                        </span>
                        <span className={styles.feasibilityBadge} title="On-site arboricultural survey required">
                          SURVEY: REQUIRED
                        </span>
                      </div>

                      {/* Action buttons */}
                      <div className={styles.candidateActions}>
                        {onSelectBlock && (
                          <button
                            type="button"
                            className={styles.inspectBlockBtn}
                            onClick={() => onSelectBlock(candidate.block_id)}
                          >
                            <span className="material-symbols-outlined text-[13px]">zoom_in</span>
                            <span>Inspect on Map</span>
                          </button>
                        )}
                        <label className={styles.compareCheckLabel}>
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => toggleCompare(candidate.block_id)}
                          />
                          <span>Compare</span>
                        </label>
                      </div>
                    </div>
                  );
                })
              )}

              {/* Sandbox Scenario Navigation */}
              <div style={{ marginTop: '8px', padding: '10px', backgroundColor: 'var(--surface-container-low)', border: '1px solid var(--outline-variant)' }}>
                <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--primary)', marginBottom: '4px' }}>
                  Explore Intervention Modeling Sandbox
                </div>
                <div style={{ fontSize: '11px', color: 'var(--on-surface-variant)', lineHeight: 1.4, marginBottom: '8px' }}>
                  Simulate tree spacing constraints (≥10m) and model carbon outcomes across 100k, 250k, and 500k tracks. Detailed spatial units require institutional credentials.
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <Link
                    href={`/planting?name=${encodeURIComponent(locationName)}&radius=${currentRadius}`}
                    className={styles.inspectBlockBtn}
                    style={{ textAlign: 'center', textDecoration: 'none', backgroundColor: 'var(--primary)', color: 'var(--on-primary)' }}
                  >
                    Open in /planting
                  </Link>
                  <Link
                    href="/scenarios"
                    className={styles.inspectBlockBtn}
                    style={{ textAlign: 'center', textDecoration: 'none' }}
                  >
                    View Systemic Scenarios
                  </Link>
                </div>
              </div>
            </div>
          )}

          {/* Action buttons */}
          <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
            <button
              type="button"
              onClick={onClose}
              className={styles.backToMapBtn}
            >
              <span className="material-symbols-outlined text-[16px]">map</span>
              <span>Inspect Map Canvas</span>
            </button>
          </div>
        </div>
      </motion.aside>
    </AnimatePresence>
  );
}
