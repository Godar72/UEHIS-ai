import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import styles from './PlantingDetail.module.css';

export interface PlantingUnitProps {
  id: string;
  unitUuid?: string;
  parentBlockId?: string;
  lat: number;
  lng: number;
  easting: number;
  northing: number;
  zone: number;
  scenario: string;
  opportunityClass: string;
  uehi?: number | null;
  riskLevel?: string | null;
  waterDistance?: number | string | null;
  ownershipStatus?: string;
  utilityStatus?: string;
  permissionStatus?: string;
  carbonAssumption?: string;
  loading?: boolean;
  error?: string | null;
}

interface PlantingDetailProps {
  unit: PlantingUnitProps | null;
  onClose: () => void;
}

function formatSafetyStatus(status?: string | null): string {
  if (!status || status.toLowerCase() === 'unknown' || status.toLowerCase() === 'not verified' || status.toLowerCase() === 'verification required') {
    return 'Verification required';
  }
  return status;
}

function getRiskColor(risk?: string | null): string {
  if (!risk) return 'var(--muted)';
  switch (risk.toLowerCase()) {
    case 'critical':
      return 'var(--risk-critical)';
    case 'high':
      return 'var(--risk-high, #D5682D)';
    case 'moderate':
      return 'var(--risk-moderate, #B28A36)';
    case 'low':
      return 'var(--risk-low, #3D7650)';
    default:
      return 'var(--primary)';
  }
}

function PlantingDetailComponent({ unit, onClose }: PlantingDetailProps) {
  const [isDesktop, setIsDesktop] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.matchMedia('(min-width: 1024px)').matches;
    }
    return true;
  });
  const [copiedMsg, setCopiedMsg] = useState<string | null>(null);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(min-width: 1024px)');
    const handleChange = (e: MediaQueryListEvent) => setIsDesktop(e.matches);
    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedMsg('Copied!');
    setTimeout(() => setCopiedMsg(null), 2000);
  };

  const animationProps = isDesktop
    ? {
        initial: { x: '100%' },
        animate: { x: 0 },
        exit: { x: '100%' },
        transition: { type: 'spring' as const, damping: 25, stiffness: 200 }
      }
    : {
        initial: { y: '100%' },
        animate: { y: 0 },
        exit: { y: '100%' },
        transition: { type: 'spring' as const, damping: 25, stiffness: 200 }
      };

  return (
    <AnimatePresence>
      {unit && (
        <motion.div className={styles.panel} data-testid="planting-detail-panel" {...animationProps}>
          {/* Mobile Drag Grasp Header Handle */}
          <div className={styles.mobileGripHandle} onClick={onClose} title="Tap to close sheet">
            <div className={styles.handleBar}></div>
          </div>

          {/* Masthead */}
          <div className={styles.panelHeader}>
            <div className={styles.panelHeaderTitle}>
              <span className="material-symbols-outlined" style={{ fontSize: '16px', color: 'var(--secondary-fixed)' }}>
                park
              </span>
              <span>Planting Unit Inspection</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className={styles.panelHeaderTag}>≥10m SPACING</span>
              <button className={styles.closeBtn} onClick={onClose} aria-label="Close panel">
                &times;
              </button>
            </div>
          </div>
          
          <div className={styles.content}>
            <div className={styles.header}>
              <div className={styles.kicker}>Spatial Unit Reference</div>
              <div className={styles.title}>{unit.id || 'Not available'}</div>
            </div>

            {unit.loading && (
              <div className={styles.loadingNotice}>
                <span className="material-symbols-outlined" style={{ fontSize: '14px' }}>sync</span>
                <span>Resolving authoritative block record...</span>
              </div>
            )}

            {unit.error ? (
              <div className={styles.dataSection} data-testid="unit-error-state">
                <div className={styles.sectionHeading}>Intervention Stratum</div>
                <div className={styles.errorNotice} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600 }}>
                    <span className="material-symbols-outlined" style={{ fontSize: '16px', color: 'var(--risk-critical)' }}>error</span>
                    <span>Inspection Data Retrieval Error</span>
                  </div>
                  <span style={{ fontSize: '11px', lineHeight: 1.4 }}>{unit.error}</span>
                </div>
                <div className={styles.dataRow} style={{ marginTop: '4px' }}>
                  <span className={styles.dataLabel}>Inspection Status</span>
                  <span className={styles.dataValue} style={{ color: 'var(--risk-critical)' }}>
                    Failed to resolve unit records
                  </span>
                </div>
                <div className={styles.dataRow}>
                  <span className={styles.dataLabel}>Scenario Scale</span>
                  <span className={styles.dataValue}>{unit.scenario}</span>
                </div>
              </div>
            ) : (
              <div className={styles.dataSection}>
                <div className={styles.sectionHeading}>Intervention Stratum</div>
                <div className={styles.dataRow}>
                  <span className={styles.dataLabel}>Scenario Scale</span>
                  <span className={styles.dataValue}>{unit.scenario}</span>
                </div>
                <div className={styles.dataRow}>
                  <span className={styles.dataLabel}>Opportunity Class</span>
                  <span className={styles.dataValue} style={{ color: 'var(--secondary)' }}>
                    {unit.loading ? 'Resolving...' : (unit.opportunityClass || 'Not available')}
                  </span>
                </div>
                <div className={styles.dataRow}>
                  <span className={styles.dataLabel}>Parent Block ID</span>
                  <span className={styles.dataValue} style={{ color: 'var(--primary)' }}>
                    {unit.parentBlockId ?? 'Not available'}
                  </span>
                </div>
                <div className={styles.dataRow}>
                  <span className={styles.dataLabel}>Block UEHI Score</span>
                  <span className={styles.dataValue}>
                    {unit.loading ? 'Resolving...' : (unit.uehi !== undefined && unit.uehi !== null ? Number(unit.uehi).toFixed(2) : 'Not available')}
                  </span>
                </div>
                <div className={styles.dataRow}>
                  <span className={styles.dataLabel}>Risk Classification</span>
                  <span className={styles.dataValue} style={{ color: getRiskColor(unit.riskLevel) }}>
                    {unit.loading ? 'Resolving...' : (unit.riskLevel ?? 'Not available')}
                  </span>
                </div>
                <div className={styles.dataRow}>
                  <span className={styles.dataLabel}>Distance to Water</span>
                  <span className={styles.dataValue}>
                    {unit.loading ? 'Resolving...' : (unit.waterDistance !== undefined && unit.waterDistance !== null && unit.waterDistance !== 'Unknown'
                      ? `${unit.waterDistance} m`
                      : 'Not available')}
                  </span>
                </div>
                <div className={styles.dataRow}>
                  <span className={styles.dataLabel}>Cadastre Ownership</span>
                  <span className={styles.dataValue} style={{ color: 'var(--risk-critical)' }}>
                    {formatSafetyStatus(unit.ownershipStatus)}
                  </span>
                </div>
                <div className={styles.dataRow}>
                  <span className={styles.dataLabel}>Utility Clearance</span>
                  <span className={styles.dataValue} style={{ color: 'var(--risk-critical)' }}>
                    {formatSafetyStatus(unit.utilityStatus)}
                  </span>
                </div>
                <div className={styles.dataRow}>
                  <span className={styles.dataLabel}>Planting Permission</span>
                  <span className={styles.dataValue} style={{ color: 'var(--risk-critical)' }}>
                    {formatSafetyStatus(unit.permissionStatus)}
                  </span>
                </div>
                <div className={styles.dataRow}>
                  <span className={styles.dataLabel}>Carbon Assumption</span>
                  <span className={styles.dataValue}>{unit.carbonAssumption ?? '0.5 t CO₂e/tree'}</span>
                </div>
              </div>
            )}

            <div className={styles.dataSection}>
              <div className={styles.sectionHeading}>Geodetic Location (WGS84)</div>
              <div className={styles.dataRow}>
                <span className={styles.dataLabel}>Latitude</span>
                <span className={styles.dataValue}>
                  {unit.lat.toFixed(6)}° N
                  <button className={styles.copyBtn} onClick={() => handleCopy(`${unit.lat.toFixed(6)}, ${unit.lng.toFixed(6)}`)}>
                    Copy
                  </button>
                </span>
              </div>
              <div className={styles.dataRow}>
                <span className={styles.dataLabel}>Longitude</span>
                <span className={styles.dataValue}>{unit.lng.toFixed(6)}° E</span>
              </div>
              <div className={styles.dataRow}>
                <span className={styles.dataLabel}>External Satellite</span>
                <span className={styles.dataValue}>
                  <a href={`https://www.google.com/maps/search/?api=1&query=${unit.lat},${unit.lng}`} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--primary)', textDecoration: 'underline', fontWeight: 600 }}>
                    Open in Maps
                  </a>
                </span>
              </div>
              
              <div className={styles.sectionHeading} style={{ marginTop: '12px' }}>Projected Grid (UTM Zone {unit.zone}N)</div>
              <div className={styles.dataRow}>
                <span className={styles.dataLabel}>Easting</span>
                <span className={styles.dataValue}>
                  {unit.easting.toFixed(1)} m
                  <button className={styles.copyBtn} onClick={() => handleCopy(`${unit.easting.toFixed(2)} E, ${unit.northing.toFixed(2)} N`)}>
                    Copy UTM
                  </button>
                </span>
              </div>
              <div className={styles.dataRow}>
                <span className={styles.dataLabel}>Northing</span>
                <span className={styles.dataValue}>{unit.northing.toFixed(1)} m</span>
              </div>
              
              {copiedMsg && <div style={{ color: 'var(--secondary)', fontSize: '11px', fontWeight: 'bold', marginTop: '4px', textAlign: 'right' }}>{copiedMsg}</div>}
            </div>

            <div className={styles.disclaimer}>
              <strong>Mandatory Protocol:</strong> Potential planting opportunity. Field verification, ownership title, subterranean utility clearance, and municipal planting permission are strictly required before physical implementation.
            </div>

            {/* Mobile Back to Map Action */}
            <button
              type="button"
              onClick={onClose}
              className={styles.backToMapBtn}
            >
              <span className="material-symbols-outlined text-[16px]">map</span>
              <span>Inspect Opportunity Map</span>
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export const PlantingDetail = React.memo(PlantingDetailComponent);

