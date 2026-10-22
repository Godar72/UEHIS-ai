'use client';

import React from 'react';
import styles from './sidebar.module.css';
import { Search } from './Search';

interface SidebarProps {
  onAnalyzeStudyArea?: (geometry: GeoJSON.Geometry | GeoJSON.Feature, name: string, type: string) => void;
  onLocationSelect?: (location: { lat: number; lng: number; name: string; type: string }) => void;
  layers?: {
    uehi: boolean;
  };
  onToggleLayer?: (layer: 'uehi') => void;
}

const QUICK_FOCUS_LOCALITIES = [
  { name: 'Baner', lat: 18.5588, lng: 73.7911, type: 'Locality' },
  { name: 'Kothrud', lat: 18.5074, lng: 73.8077, type: 'Locality' },
  { name: 'Hadapsar', lat: 18.5089, lng: 73.9259, type: 'Locality' },
  { name: 'Viman Nagar', lat: 18.5679, lng: 73.9143, type: 'Locality' },
  { name: 'Hinjawadi', lat: 18.5913, lng: 73.7389, type: 'Locality' },
];

export function Sidebar({ onLocationSelect, layers = { uehi: true }, onToggleLayer }: SidebarProps) {

  return (
    <aside className={styles.rail}>
      <div className={styles.railHeader}>
        <div className={styles.railTitle}>
          <span>Active Layers &amp; Tools</span>
          <span className={styles.railStatusBadge}>PROD::ONLINE</span>
        </div>
      </div>

      {/* 01: Geospatial Query & Quick Focus */}
      <div className={styles.railSection}>
        <div className={styles.sectionHeading}>
          <div className={styles.sectionHeadingLeft}>
            <span className={styles.sectionNumber}>01</span>
            <h3>Geospatial Query</h3>
          </div>
          <span className={styles.sectionTag}>SEARCH</span>
        </div>
        <p className={styles.instructions}>
          Locate a Pune ward, survey block, road, or landmark to center the geospatial extent.
        </p>
        <Search onLocationSelect={onLocationSelect || (() => {})} />
        
        <div className={styles.quickFocusContainer}>
          <div className={styles.quickFocusLabel}>Quick Focus Localities</div>
          <div className={styles.quickFocusChips}>
            {QUICK_FOCUS_LOCALITIES.map((loc) => (
              <button
                key={loc.name}
                type="button"
                className={styles.chipButton}
                onClick={() => onLocationSelect && onLocationSelect(loc)}
              >
                {loc.name}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 02: Ecological Layer Stack */}
      <div className={styles.railSection}>
        <div className={styles.sectionHeading}>
          <div className={styles.sectionHeadingLeft}>
            <span className={styles.sectionNumber}>02</span>
            <h3>Ecological Layer Stack</h3>
          </div>
          <span className={styles.sectionTag}>3 FEEDS</span>
        </div>
        <div className={styles.layerList}>
          {/* UEHI Composite */}
          <div className={styles.layerCard}>
            <label className={styles.layerToggle}>
              <div className={styles.layerLabelLeft}>
                <input
                  type="checkbox"
                  checked={layers.uehi}
                  onChange={() => onToggleLayer && onToggleLayer('uehi')}
                  className={styles.checkbox}
                />
                <span className={styles.layerName}>UEHI Composite Grids</span>
              </div>
              <span className={styles.layerBadgeCritical}>CRITICAL LAYER</span>
            </label>
            <div className={styles.layerMeta}>
              <span>Weight: 1.0 (Harmonized)</span>
              <span>250m Cell</span>
            </div>
          </div>

          {/* Reference feeds */}
          <div className={styles.layerCard}>
            <div className={styles.layerToggle}>
              <div className={styles.layerLabelLeft}>
                <span className="material-symbols-outlined" style={{ fontSize: '14px', color: 'var(--primary)' }}>nature</span>
                <span className={styles.layerName}>Canopy Height &amp; Strata</span>
              </div>
              <span className={styles.layerBadgeSource}>ETH 2020 10m</span>
            </div>
          </div>

          <div className={styles.layerCard}>
            <div className={styles.layerToggle}>
              <div className={styles.layerLabelLeft}>
                <span className="material-symbols-outlined" style={{ fontSize: '14px', color: 'var(--primary)' }}>thermostat</span>
                <span className={styles.layerName}>Surface Temp (LST)</span>
              </div>
              <span className={styles.layerBadgeSource}>Landsat-9 TIRS</span>
            </div>
          </div>
        </div>
      </div>

      {/* 03: Risk Classification Legend */}
      <div className={styles.railSection}>
        <div className={styles.sectionHeading}>
          <div className={styles.sectionHeadingLeft}>
            <span className={styles.sectionNumber}>03</span>
            <h3>Risk Classification</h3>
          </div>
          <span className={styles.sectionTag}>UEHI SCORE</span>
        </div>
        <div className={styles.legend}>
          <div className={styles.legendRow}>
            <div className={styles.legendLeft}>
              <div className={styles.legendSwatch} style={{ backgroundColor: 'var(--risk-critical)' }}></div>
              <span className={styles.legendLabel}>CRITICAL RISK</span>
            </div>
            <span className={styles.legendRange}>00.0 – 25.0</span>
          </div>
          <div className={styles.legendRow}>
            <div className={styles.legendLeft}>
              <div className={styles.legendSwatch} style={{ backgroundColor: 'var(--risk-high)' }}></div>
              <span className={styles.legendLabel}>HIGH VULNERABILITY</span>
            </div>
            <span className={styles.legendRange}>25.0 – 50.0</span>
          </div>
          <div className={styles.legendRow}>
            <div className={styles.legendLeft}>
              <div className={styles.legendSwatch} style={{ backgroundColor: 'var(--risk-moderate)' }}></div>
              <span className={styles.legendLabel}>MODERATE STRESS</span>
            </div>
            <span className={styles.legendRange}>50.0 – 75.0</span>
          </div>
          <div className={styles.legendRow}>
            <div className={styles.legendLeft}>
              <div className={styles.legendSwatch} style={{ backgroundColor: 'var(--risk-low)' }}></div>
              <span className={styles.legendLabel}>LOW RISK / STABLE</span>
            </div>
            <span className={styles.legendRange}>75.0 – 100.0</span>
          </div>
          <div className={styles.legendRow}>
            <div className={styles.legendLeft}>
              <div style={{ borderBottom: '2px dashed var(--outline)', width: '12px', height: '6px' }}></div>
              <span className={styles.legendLabel} style={{ color: 'var(--outline)' }}>Model Coverage Boundary</span>
            </div>
            <span className={styles.legendRange}>PMC + PCMC</span>
          </div>
        </div>
      </div>

      {/* 04: Projection Status */}
      <div className={styles.railSection}>
        <div className={styles.projectionBlock}>
          <div className={styles.projectionHeader}>Projection Datum</div>
          <div className={styles.projectionData}>UTM Zone 43N | GRS 1980</div>
          <div className={styles.projectionSub}>EPSG:32643 · 5,309 Analyzed Blocks</div>
        </div>
      </div>

      <div className={styles.railFooter}>
        <button className={styles.actionButton} onClick={() => window.print()}>
          <span className="material-symbols-outlined" style={{ fontSize: '15px' }}>print</span>
          Export Spatial Report
        </button>
      </div>
    </aside>
  );
}

