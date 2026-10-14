'use client';

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import styles from './StudyAreaResult.module.css';

interface StudyAreaResultProps {
  loading: boolean;
  data: any;
  error: string | null;
  onClose: () => void;
  locationName: string;
  boundaryType: string;
  currentRadius?: number;
  onRadiusChange?: (radiusMeters: number) => void;
  onRetry?: () => void;
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
}: StudyAreaResultProps) {
  const [isDesktop, setIsDesktop] = useState(false);

  useEffect(() => {
    const checkIsDesktop = () => setIsDesktop(window.innerWidth >= 1024);
    checkIsDesktop();
    window.addEventListener('resize', checkIsDesktop);
    return () => window.removeEventListener('resize', checkIsDesktop);
  }, []);

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

  const score = data?.uehi?.score;
  const getRiskLabel = (s?: number | null) => {
    if (s === null || s === undefined) return 'Unknown';
    if (s <= 25) return 'CRITICAL RISK';
    if (s <= 45) return 'HIGH VULNERABILITY';
    if (s <= 65) return 'MODERATE STRESS';
    return 'LOW RISK / STABLE';
  };

  const getRiskColor = (s?: number | null) => {
    if (s === null || s === undefined) return 'var(--primary)';
    if (s <= 25) return 'var(--risk-critical)';
    if (s <= 45) return 'var(--risk-high)';
    if (s <= 65) return 'var(--risk-moderate)';
    return 'var(--risk-low)';
  };

  const totalDist = data?.uehi?.risk_distribution ? (
    (data.uehi.risk_distribution.Critical || 0) +
    (data.uehi.risk_distribution.High || 0) +
    (data.uehi.risk_distribution.Moderate || 0) +
    (data.uehi.risk_distribution.Low || 0)
  ) : 0;

  const isPointRadius = boundaryType.toLowerCase().includes('point') || boundaryType.toLowerCase().includes('radius');

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

        {/* Radius Selector Controls (Stitch Mobile Spec) */}
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
                <span>POINT-RADIUS STUDY AREA — NOT AN OFFICIAL ADMINISTRATIVE BOUNDARY</span>
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

          {data && (
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

                {/* Multi-tier distribution bar */}
                {totalDist > 0 && (
                  <div style={{ marginTop: '10px' }}>
                    <div className={styles.distribBar}>
                      <div
                        className={styles.distribSegment}
                        style={{
                          width: `${((data.uehi.risk_distribution.Critical || 0) / totalDist) * 100}%`,
                          backgroundColor: 'var(--risk-critical)'
                        }}
                        title={`Critical: ${data.uehi.risk_distribution.Critical || 0}`}
                      />
                      <div
                        className={styles.distribSegment}
                        style={{
                          width: `${((data.uehi.risk_distribution.High || 0) / totalDist) * 100}%`,
                          backgroundColor: 'var(--risk-high)'
                        }}
                        title={`High: ${data.uehi.risk_distribution.High || 0}`}
                      />
                      <div
                        className={styles.distribSegment}
                        style={{
                          width: `${((data.uehi.risk_distribution.Moderate || 0) / totalDist) * 100}%`,
                          backgroundColor: 'var(--risk-moderate)'
                        }}
                        title={`Moderate: ${data.uehi.risk_distribution.Moderate || 0}`}
                      />
                      <div
                        className={styles.distribSegment}
                        style={{
                          width: `${((data.uehi.risk_distribution.Low || 0) / totalDist) * 100}%`,
                          backgroundColor: 'var(--risk-low)'
                        }}
                        title={`Low: ${data.uehi.risk_distribution.Low || 0}`}
                      />
                    </div>
                    <div className={styles.distribScale} style={{ marginTop: '4px' }}>
                      <span>Critical (&lt;25)</span>
                      <span>High (25–45)</span>
                      <span>Moderate (45–65)</span>
                      <span>Low (&gt;65)</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Spatial Statistics 4-Tile Grid */}
              <div className={styles.statsGrid}>
                <div className={styles.statTile}>
                  <span className={styles.statLabel}>Study Area Extent</span>
                  <span className={styles.statValue}>
                    {data.uehi?.eligible_intersection_area_m2 != null
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

              {/* Carbon Assessment Section */}
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
                        <span>Estimated Standing Stock</span>
                        <strong>
                          {data.carbon?.total_carbon_tonnes_co2e != null
                            ? `${data.carbon.total_carbon_tonnes_co2e.toFixed(2)} t CO₂e`
                            : 'N/A'}
                        </strong>
                      </div>
                      <div className={styles.dataRow}>
                        <span>Tree Stems Estimated</span>
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
                    </div>
                  ) : (
                    <div style={{ padding: '6px', fontSize: '11px', color: 'var(--outline)' }}>
                      Carbon calculations synchronized with 2024 satellite canopy baseline.
                    </div>
                  )}
                </div>
              </div>

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
            </>
          )}
        </div>
      </motion.aside>
    </AnimatePresence>
  );
}
