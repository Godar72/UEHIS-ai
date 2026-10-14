'use client';

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import styles from './rightpanel.module.css';

export interface BlockResponse {
  block_id: string;
  uehi_score: number;
  risk_level: string;
  factors: {
    ndvi: number;
    tree_density: number;
    impervious_surfaces: number;
    temperature: number;
    population_exposure: number;
    aqi: number;
  };
  co2_tonnes: number | null;
  carbon_details?: {
    canopy_area_m2: number | null;
    estimated_tree_count: number | null;
    above_ground_biomass_kg: number | null;
  } | null;
}

interface RightPanelProps {
  blockId: string | null;
  loading: boolean;
  data: BlockResponse | null;
  onClose: () => void;
  error?: string | null;
}

export function RightPanel({ blockId, loading, data, onClose, error }: RightPanelProps) {
  const [isDesktop, setIsDesktop] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const checkIsDesktop = () => setIsDesktop(window.innerWidth >= 1024);
    checkIsDesktop();
    window.addEventListener('resize', checkIsDesktop);
    return () => window.removeEventListener('resize', checkIsDesktop);
  }, []);

  const handleCopyId = () => {
    if (!blockId) return;
    navigator.clipboard.writeText(blockId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const animationProps = isDesktop
    ? {
        initial: { x: '100%' },
        animate: { x: 0 },
        exit: { x: '100%' },
        transition: { type: 'spring' as const, damping: 28, stiffness: 220 }
      }
    : {
        initial: { y: '100%' },
        animate: { y: 0 },
        exit: { y: '100%' },
        transition: { type: 'spring' as const, damping: 28, stiffness: 220 }
      };

  const getRiskColor = (level?: string) => {
    switch ((level || '').toLowerCase()) {
      case 'critical':
        return 'var(--risk-critical)';
      case 'high':
        return 'var(--risk-high)';
      case 'moderate':
        return 'var(--risk-moderate)';
      case 'low':
        return 'var(--risk-low)';
      default:
        return 'var(--primary)';
    }
  };

  return (
    <AnimatePresence>
      {blockId && (
        <motion.aside
          className={styles.panel}
          {...animationProps}
        >
          {/* Mobile Drag Grasp Header Handle */}
          <div className={styles.mobileGripHandle} onClick={onClose} title="Tap to close sheet">
            <div className={styles.handleBar}></div>
          </div>

          {/* Masthead */}
          <div className={styles.panelHeader}>
            <div className={styles.panelHeaderTitle}>
              <span className="material-symbols-outlined" style={{ fontSize: '16px', color: 'var(--secondary-fixed)' }}>
                analytics
              </span>
              <span>Block Attribution Inspector</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className={styles.panelHeaderTag}>250m × 250m</span>
              <button className={styles.closeBtn} onClick={onClose} aria-label="Close inspector">
                &times;
              </button>
            </div>
          </div>

          {loading ? (
            <div className={styles.stateMessage}>
              <span className="material-symbols-outlined" style={{ fontSize: '28px', color: 'var(--primary)', marginBottom: '8px', animation: 'spin 1.5s linear infinite' }}>
                sync
              </span>
              <span>Loading analytical block attribution...</span>
            </div>
          ) : error ? (
            <div className={styles.stateMessage}>
              <p className={styles.errorText}>{error}</p>
              <button className={styles.retryBtn} onClick={onClose}>Dismiss</button>
            </div>
          ) : data ? (
            <div className={styles.content}>
              {/* Spatial Block Reference Card */}
              <div className={styles.blockCard}>
                <div className={styles.blockCardHeader}>
                  <span className={styles.blockCardLabel}>Spatial Block Reference</span>
                  <button className={styles.copyBtn} onClick={handleCopyId} title="Copy block identifier">
                    <span className="material-symbols-outlined" style={{ fontSize: '12px' }}>content_copy</span>
                    {copied ? 'Copied' : 'Copy ID'}
                  </button>
                </div>
                <div className={styles.blockId}>{blockId}</div>
                <div className={styles.blockMetaGrid}>
                  <span>Grid Extent: 0.0625 km²</span>
                  <span>CRS: EPSG:32643</span>
                </div>
              </div>

              {/* Composite Score Card */}
              <div className={styles.scoreCard}>
                <div className={styles.scoreCardTop}>
                  <div>
                    <span className={styles.scoreCardLabel}>UEHI Composite Score</span>
                    <div className={styles.scoreRow}>
                      <span className={styles.scoreValue}>
                        {data.uehi_score !== null && data.uehi_score !== undefined
                          ? data.uehi_score.toFixed(2)
                          : 'N/A'}
                      </span>
                      <span className={styles.scoreDenominator}>/ 100</span>
                    </div>
                  </div>
                  <span
                    className={styles.riskBadge}
                    style={{ backgroundColor: getRiskColor(data.risk_level) }}
                  >
                    {data.risk_level || 'Unknown'} Risk
                  </span>
                </div>

                <div className={styles.progressBarTrack}>
                  <div
                    className={styles.progressBarFill}
                    style={{
                      width: `${Math.min(Math.max(data.uehi_score || 0, 0), 100)}%`,
                      backgroundColor: getRiskColor(data.risk_level)
                    }}
                  />
                </div>

                <div className={styles.scoreScale}>
                  <span>0.00 (Extreme Risk)</span>
                  <span>Regional Avg: 20.21</span>
                  <span>100.0</span>
                </div>
              </div>

              {/* 6 Core Factors Attribution */}
              <div>
                <div className={styles.sectionHeading}>
                  <span>Core Factor Attribution</span>
                  <span className={styles.sectionHeadingBadge}>DELTA VS BASELINE</span>
                </div>
                <div className={styles.dataTable} style={{ marginTop: '6px' }}>
                  {/* Tree Density */}
                  <div className={styles.dataRow}>
                    <div className={styles.dataRowLeft}>
                      <span className={styles.dataLabel}>Canopy Cover Fraction</span>
                      <span className={styles.dataSub} style={{ color: getRiskColor(data.risk_level) }}>
                        Deficit vs Urban Target (21.6%)
                      </span>
                    </div>
                    <div className={styles.dataRowRight}>
                      <span className={styles.dataValue}>
                        {data.factors?.tree_density !== undefined ? `${(data.factors.tree_density * 100).toFixed(1)}%` : 'N/A'}
                      </span>
                      <span className={styles.dataSource}>ETH 2020 10m</span>
                    </div>
                  </div>

                  {/* NDVI */}
                  <div className={styles.dataRow}>
                    <div className={styles.dataRowLeft}>
                      <span className={styles.dataLabel}>Normalized Veg. Index (NDVI)</span>
                      <span className={styles.dataSub} style={{ color: 'var(--on-surface-variant)' }}>
                        Sentinel-2 Surface Reflectance
                      </span>
                    </div>
                    <div className={styles.dataRowRight}>
                      <span className={styles.dataValue}>
                        {data.factors?.ndvi !== undefined ? data.factors.ndvi.toFixed(3) : 'N/A'}
                      </span>
                      <span className={styles.dataSource}>S2 MSI 10m</span>
                    </div>
                  </div>

                  {/* Impervious Surface */}
                  <div className={styles.dataRow}>
                    <div className={styles.dataRowLeft}>
                      <span className={styles.dataLabel}>Impervious Surface Fraction</span>
                      <span className={styles.dataSub} style={{ color: 'var(--risk-high)' }}>
                        Runoff &amp; Thermal Mass Risk
                      </span>
                    </div>
                    <div className={styles.dataRowRight}>
                      <span className={styles.dataValue}>
                        {data.factors?.impervious_surfaces !== undefined ? `${(data.factors.impervious_surfaces * 100).toFixed(1)}%` : 'N/A'}
                      </span>
                      <span className={styles.dataSource}>Built Pavement</span>
                    </div>
                  </div>

                  {/* Temperature */}
                  <div className={styles.dataRow}>
                    <div className={styles.dataRowLeft}>
                      <span className={styles.dataLabel}>Surface Temperature (LST)</span>
                      <span className={styles.dataSub} style={{ color: 'var(--risk-critical)' }}>
                        Thermal Stress Exposure
                      </span>
                    </div>
                    <div className={styles.dataRowRight}>
                      <span className={styles.dataValue}>
                        {data.factors?.temperature ? `${data.factors.temperature.toFixed(2)} °C` : 'N/A'}
                      </span>
                      <span className={styles.dataSource}>Landsat-9 TIRS</span>
                    </div>
                  </div>

                  {/* Population Exposure */}
                  <div className={styles.dataRow}>
                    <div className={styles.dataRowLeft}>
                      <span className={styles.dataLabel}>Population Exposure</span>
                      <span className={styles.dataSub} style={{ color: 'var(--on-surface-variant)' }}>
                        Residential &amp; Commercial Density
                      </span>
                    </div>
                    <div className={styles.dataRowRight}>
                      <span className={styles.dataValue}>
                        {data.factors?.population_exposure !== undefined ? data.factors.population_exposure.toFixed(2) : 'N/A'}
                      </span>
                      <span className={styles.dataSource}>WorldPop R2025A</span>
                    </div>
                  </div>

                  {/* AQI / PM2.5 */}
                  <div className={styles.dataRow}>
                    <div className={styles.dataRowLeft}>
                      <span className={styles.dataLabel}>PM2.5 Micro-exposure</span>
                      <span className={styles.dataSub} style={{ color: 'var(--risk-high)' }}>
                        Ground Calibrated Aerosol
                      </span>
                    </div>
                    <div className={styles.dataRowRight}>
                      <span className={styles.dataValue}>
                        {data.factors?.aqi ? `${data.factors.aqi.toFixed(2)} µg/m³` : 'N/A'}
                      </span>
                      <span className={styles.dataSource}>ACAG/WUSTL V6</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Carbon Sink Modeling */}
              <div>
                <div className={styles.sectionHeading}>
                  <span>Carbon Sink Modeling</span>
                  <span className={styles.sectionHeadingBadge}>ALLOMETRIC</span>
                </div>
                <div className={styles.dataTable} style={{ marginTop: '6px' }}>
                  {data.carbon_details && (
                    <>
                      <div className={styles.dataRow}>
                        <span className={styles.dataLabel}>Canopy area</span>
                        <span className={styles.dataValue}>
                          {data.carbon_details.canopy_area_m2 !== null 
                            ? `${(data.carbon_details.canopy_area_m2 / 1000000).toFixed(4)} km²` 
                            : 'Not available'}
                        </span>
                      </div>
                      <div className={styles.dataRow}>
                        <span className={styles.dataLabel}>Estimated stems</span>
                        <span className={styles.dataValue}>
                          {data.carbon_details.estimated_tree_count !== null 
                            ? Math.round(data.carbon_details.estimated_tree_count).toLocaleString() 
                            : 'Not available'}
                        </span>
                      </div>
                      <div className={styles.dataRow}>
                        <span className={styles.dataLabel}>Above-ground biomass</span>
                        <span className={styles.dataValue}>
                          {data.carbon_details.above_ground_biomass_kg !== null 
                            ? `${data.carbon_details.above_ground_biomass_kg.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})} kg` 
                            : 'Not available'}
                        </span>
                      </div>
                    </>
                  )}
                  <div className={styles.dataRow}>
                    <span className={styles.dataLabel}>Standing carbon stock</span>
                    <span className={styles.dataValue} style={{ color: 'var(--secondary)' }}>
                      {data.co2_tonnes !== null && data.co2_tonnes !== undefined
                        ? `${data.co2_tonnes.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})} t CO₂e`
                        : 'N/A'}
                    </span>
                  </div>
                </div>
                <p className={styles.carbonNote}>
                  Standing carbon stock represents current stored above-ground biomass, not annual future sequestration.
                </p>

                {/* Mobile Back to Map Action */}
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
          ) : (
            <div className={styles.stateMessage}>No data available for this block.</div>
          )}
        </motion.aside>
      )}
    </AnimatePresence>
  );
}

