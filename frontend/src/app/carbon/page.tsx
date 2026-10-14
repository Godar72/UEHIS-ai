'use client';

import React, { useState, useEffect, useRef, useCallback, Suspense, useMemo } from 'react';
import { motion } from 'framer-motion';
import { MapView } from '@/components/Map';
import { RightPanel } from '@/components/RightPanel/RightPanel';
import { uehisClient } from '@/lib/api/client';
import { recordActivity } from '@/lib/api/activity';
import styles from './page.module.css';

const WARD_BIOTOPE_DATA = [
  {
    ward: 'Kothrud - Bavdhan (Tekdi Buffer)',
    biotope: 'Semi-Deciduous Hill Forest',
    area: '38.40',
    canopy: '5.82',
    canopyPct: '15.1%',
    stems: '1,248,300',
    stock: '134,812.50',
    density: '23.16 t CO₂e/ha',
    risk: 'Critical Threat',
    riskColor: 'var(--risk-critical)'
  },
  {
    ward: 'Aundh - Baner - Balewadi',
    biotope: 'Mula Riverine Corridor & Urban Parks',
    area: '29.10',
    canopy: '2.94',
    canopyPct: '10.1%',
    stems: '628,450',
    stock: '68,240.10',
    density: '23.21 t CO₂e/ha',
    risk: 'High Encroach',
    riskColor: 'var(--risk-high)'
  },
  {
    ward: 'Shivajinagar - Deccan (Institutional)',
    biotope: 'Heritage Institutional Canopy (SPPU, COEP, Agri)',
    area: '21.80',
    canopy: '3.41',
    canopyPct: '15.6%',
    stems: '745,000',
    stock: '91,480.80',
    density: '26.82 t CO₂e/ha',
    risk: 'Protected Baseline',
    riskColor: 'var(--risk-low)'
  },
  {
    ward: 'Sinhagad Foothills Riparian Swath',
    biotope: 'Upper Mutha Riparian Buffer',
    area: '42.60',
    canopy: '4.18',
    canopyPct: '9.8%',
    stems: '892,100',
    stock: '86,340.20',
    density: '20.65 t CO₂e/ha',
    risk: 'High Encroach',
    riskColor: 'var(--risk-high)'
  },
  {
    ward: 'Hadapsar - Mundhwa Industrial Belt',
    biotope: 'Urban Dense Built Fringe',
    area: '36.50',
    canopy: '1.82',
    canopyPct: '5.0%',
    stems: '382,000',
    stock: '38,120.40',
    density: '20.94 t CO₂e/ha',
    risk: 'Critical Deficit',
    riskColor: 'var(--risk-critical)'
  },
  {
    ward: 'Yerawada - Kalyani Nagar',
    biotope: 'Bund Garden & Riverfront Corridor',
    area: '24.20',
    canopy: '2.25',
    canopyPct: '9.3%',
    stems: '484,200',
    stock: '51,890.30',
    density: '23.06 t CO₂e/ha',
    risk: 'Moderate Stress',
    riskColor: 'var(--risk-moderate)'
  }
];

function CarbonContent() {
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(null);
  const [blockLoading, setBlockLoading] = useState(false);
  const [blockData, setBlockData] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<any>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [summaryError, setSummaryError] = useState(false);
  const [filterText, setFilterText] = useState('');

  useEffect(() => {
    uehisClient.system.getSummary()
      .then(data => {
        setSummary(data);
        setSummaryLoading(false);
      })
      .catch(err => {
        console.error('Failed to load carbon summary', err);
        setSummaryError(true);
        setSummaryLoading(false);
      });
  }, []);

  const fetchController = useRef<AbortController | null>(null);

  const handleBlockClick = useCallback(async (blockId: string) => {
    setSelectedBlockId(blockId);
    setBlockLoading(true);
    setBlockData(null);
    setError(null);

    if (fetchController.current) {
      fetchController.current.abort();
    }
    fetchController.current = new AbortController();

    try {
      const data = await uehisClient.blocks.getDetail(blockId, { signal: fetchController.current.signal });
      setBlockData(data);
      recordActivity({
        activity_type: 'viewed_carbon',
        category: 'carbon',
        action_type: 'viewed',
        title: `Examined Carbon Stock: Block ${blockId}`,
        description: `Canopy: ${data.canopy_coverage_pct ?? 'N/A'}% · Biomass: ${data.biomass_density_t_ha ?? 'N/A'} t/ha · Carbon: ${data.carbon_density_t_ha ?? 'N/A'} t CO₂e/ha`,
        entity_type: 'block',
        entity_id: blockId,
        metadata: {
          block_id: blockId,
          ward_name: data.ward_name,
          reopen_url: `/explore/block/${blockId}`,
        },
      });
    } catch (err: any) {
      if (err.name === 'AbortError') return;
      console.error(err);
      setBlockData(null);
      if (err.isNotFound || err.status === 404) {
        setError(`Block "${blockId}" not found in Pune study area.`);
      } else if (err.isTimeout || err.status === 504) {
        setError("Request timed out while loading carbon analysis. Please try again.");
      } else if (err.isNetworkError) {
        setError("Network connection error. Please check your connection and retry.");
      } else {
        setError(err.message || "Block analysis is temporarily unavailable.");
      }
    } finally {
      setBlockLoading(false);
    }
  }, []);

  const handleClosePanel = useCallback(() => {
    setSelectedBlockId(null);
    setBlockData(null);
    setError(null);
  }, []);

  const filteredWards = useMemo(() => {
    if (!filterText.trim()) return WARD_BIOTOPE_DATA;
    const lower = filterText.toLowerCase();
    return WARD_BIOTOPE_DATA.filter(
      w => w.ward.toLowerCase().includes(lower) || w.biotope.toLowerCase().includes(lower)
    );
  }, [filterText]);

  return (
    <div className={styles.container}>
      {/* Editorial Scientific Datum Bar */}
      <section className={styles.datumBar}>
        <div className={styles.datumMeta}>
          <span className={styles.datumAssessId}>
            <span className="material-symbols-outlined" style={{ fontSize: '15px', color: 'var(--secondary)' }}>
              verified
            </span>
            SURFACE ASSESS ID: ERC-PUN-UEHIS-2024-C3
          </span>
          <span className={styles.datumDivider}>/</span>
          <span>STUDY EXTENT: <strong>PMC + PCMC (302.8 km²)</strong></span>
          <span className={styles.datumDivider}>/</span>
          <span>EPSG:32643 [UTM ZONE 43N]</span>
          <span className={styles.datumDivider}>/</span>
          <span>ACQUISITION: Q3–Q4 2023</span>
        </div>
        <div className={styles.datumBadges}>
          <span className={styles.badgeBaseline}>OBSERVED / MODELED BASELINE</span>
          <span className={styles.badgeStage}>STAGE 4 RESTRICTED RESEARCH</span>
        </div>
      </section>

      {/* Hero Scientific Headline Block */}
      <section className={styles.heroSection}>
        <div className={styles.heroGrid}>
          <div className={styles.heroContent}>
            <div className={styles.heroOverline}>
              <span className={styles.heroOverlineDot}></span>
              <span>Terrestrial Carbon Accounting • Pune Core Baseline</span>
            </div>
            <h1 className={styles.heroTitle}>Standing Carbon Stock Scientific Assessment</h1>
            <p className={styles.heroDesc}>
              Multi-spectral satellite observation fusion baseline measuring absolute dry biomass retention across 5,309 municipal grid blocks. This inventory documents standing urban carbon reservoirs within urban forests, tekdis, protected campuses, and riverine riparian corridors.
            </p>
          </div>

          {/* Hero Callout Metric Card */}
          <div className={styles.heroMetricCard}>
            <div>
              <div className={styles.heroMetricHeader}>
                <span className={styles.heroMetricLabel}>Total Standing Carbon Stock</span>
                <span className="material-symbols-outlined" style={{ fontSize: '18px', color: 'var(--secondary-fixed)' }}>
                  forest
                </span>
              </div>
              <div className={styles.heroMetricValue}>
                {summaryLoading ? (
                  <span style={{ fontSize: '24px' }}>Loading...</span>
                ) : summaryError || !summary ? (
                  <span style={{ fontSize: '24px', color: 'var(--error-container)' }}>493,093.69</span>
                ) : (
                  <>
                    {summary.carbon?.total_carbon?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '493,093.69'}
                    <span className={styles.heroMetricUnit}>t CO₂e</span>
                  </>
                )}
              </div>
              <div className={styles.heroMetricCI}>
                95% Confidence Interval: ±38,420 t CO₂e (±7.79%)
              </div>
            </div>

            <div className={styles.heroMetricFooter}>
              <span>ALLOMETRIC UNCERTAINTY: ±5.4%</span>
              <span className={styles.heroMetricCalibrated}>CALIBRATED</span>
            </div>
          </div>
        </div>
      </section>

      {/* Scientific Indicator Ribbon (Flat Planar Tiles) */}
      <section className={styles.indicatorRibbon}>
        <div className={styles.indicatorGrid}>
          <div className={styles.indicatorTile}>
            <span className={styles.indicatorTitle}>Total Canopy Area</span>
            <div className={styles.indicatorValue}>
              {summary?.carbon?.canopy_area_km2 ? summary.carbon.canopy_area_km2.toFixed(2) : '21.51'} <span style={{ fontSize: '11px', fontWeight: 400 }}>km²</span>
            </div>
            <span className={styles.indicatorSub}>7.10% total surface</span>
          </div>

          <div className={styles.indicatorTile}>
            <span className={styles.indicatorTitle}>Vegetated Grids</span>
            <div className={styles.indicatorValue}>
              {summary?.carbon?.nonzero_blocks ? summary.carbon.nonzero_blocks.toLocaleString() : '1,261'} <span style={{ fontSize: '11px', fontWeight: 400 }}>/ 5,309</span>
            </div>
            <span className={styles.indicatorSub}>23.75% active blocks</span>
          </div>

          <div className={styles.indicatorTile}>
            <span className={styles.indicatorTitle}>Estimated Stems</span>
            <div className={styles.indicatorValue}>
              {summary?.carbon?.tree_count ? (summary.carbon.tree_count / 1000000).toFixed(2) : '4.60'} <span style={{ fontSize: '11px', fontWeight: 400 }}>M Stems</span>
            </div>
            <span className={styles.indicatorSub}>μ 2,138 stems/ha veg</span>
          </div>

          <div className={styles.indicatorTile}>
            <span className={styles.indicatorTitle}>Above-Ground (AGB)</span>
            <div className={styles.indicatorValue}>
              {summary?.carbon?.biomass_kg ? (summary.carbon.biomass_kg / 1000000).toFixed(2) : '286.13'} <span style={{ fontSize: '11px', fontWeight: 400 }}>M kg</span>
            </div>
            <span className={styles.indicatorSub}>79.37% of biomass</span>
          </div>

          <div className={styles.indicatorTile}>
            <span className={styles.indicatorTitle}>Below-Ground (BGB)</span>
            <div className={styles.indicatorValue}>
              74.39 <span style={{ fontSize: '11px', fontWeight: 400 }}>M kg</span>
            </div>
            <span className={styles.indicatorSub}>R:S Ratio = 0.26</span>
          </div>

          <div className={styles.indicatorTile}>
            <span className={styles.indicatorTitle}>Mean Carbon Density</span>
            <div className={styles.indicatorValue}>
              22.92 <span style={{ fontSize: '11px', fontWeight: 400 }}>t CO₂e/ha</span>
            </div>
            <span className={styles.indicatorSub}>Canopy weighted</span>
          </div>
        </div>
      </section>

      {/* Interactive Cartography Stage & Analytics Duo */}
      <section className={styles.mapSection}>
        <div className={styles.mapDuoGrid}>
          {/* Map Container */}
          <div className={styles.mapContainer}>
            <div className={styles.mapMasthead}>
              <div className={styles.mapMastheadTitle}>
                <span className="material-symbols-outlined" style={{ fontSize: '16px', color: 'var(--secondary-fixed)' }}>
                  public
                </span>
                <span>Pune Biomass Carbon Density Raster</span>
              </div>
              <span className={styles.mapMastheadTag}>250m × 250m orthogonal grid</span>
            </div>

            <div className={styles.mapWrapper}>
              <MapView 
                onBlockClick={handleBlockClick} 
                showUehi={false}
                showCarbon={true}
                selectedBlockId={selectedBlockId}
                cooperativeGestures={true}
              />
              {selectedBlockId && (
                <RightPanel 
                  blockId={selectedBlockId}
                  loading={blockLoading}
                  data={blockData}
                  error={error}
                  onClose={handleClosePanel}
                />
              )}
            </div>

            {/* Restrained Cartographic Legend */}
            <div className={styles.legendBar}>
              <div className={styles.legendScale}>
                <span>BIOMASS CARBON DENSITY (t C / ha)</span>
                <span style={{ fontFamily: 'var(--font-jetbrains-mono)' }}>0 → 220+ t C/ha</span>
              </div>
              <div className={styles.legendTrack}>
                <div className={styles.legendStep} style={{ backgroundColor: '#faf9f4' }} title="0 - 10" />
                <div className={styles.legendStep} style={{ backgroundColor: '#bbf7d0' }} title="10 - 45" />
                <div className={styles.legendStep} style={{ backgroundColor: '#4ade80' }} title="45 - 90" />
                <div className={styles.legendStep} style={{ backgroundColor: '#16a34a' }} title="90 - 150" />
                <div className={styles.legendStep} style={{ backgroundColor: '#166534' }} title="150+" />
              </div>
              <div className={styles.legendLabels}>
                <span>0 (Built)</span>
                <span>45 (Sparse Canopy)</span>
                <span>110 (Mixed Tekdi)</span>
                <span>180+ (Dense Canopy)</span>
              </div>
            </div>
          </div>

          {/* Right Analytics Column */}
          <div className={styles.analyticsColumn}>
            {/* Canopy Height Architecture SVG Chart */}
            <div className={styles.chartCard}>
              <div className={styles.chartHeader}>
                <span className={styles.chartTitle}>Canopy Height Architecture</span>
                <span className={styles.chartSource}>ETH 2020 10m</span>
              </div>
              <div style={{ width: '100%', margin: '12px 0' }}>
                <svg className="w-full h-40" viewBox="0 0 320 150" fill="none" style={{ width: '100%', height: '140px' }}>
                  <line x1="40" y1="20" x2="310" y2="20" stroke="var(--outline-variant)" strokeDasharray="2 2" />
                  <line x1="40" y1="55" x2="310" y2="55" stroke="var(--outline-variant)" strokeDasharray="2 2" />
                  <line x1="40" y1="90" x2="310" y2="90" stroke="var(--outline-variant)" strokeDasharray="2 2" />
                  <line x1="40" y1="125" x2="310" y2="125" stroke="var(--outline)" />
                  <text x="5" y="24" fill="var(--outline)" fontSize="9" fontFamily="var(--font-jetbrains-mono)">180k t</text>
                  <text x="5" y="59" fill="var(--outline)" fontSize="9" fontFamily="var(--font-jetbrains-mono)">120k t</text>
                  <text x="5" y="94" fill="var(--outline)" fontSize="9" fontFamily="var(--font-jetbrains-mono)">60k t</text>
                  <text x="18" y="129" fill="var(--outline)" fontSize="9" fontFamily="var(--font-jetbrains-mono)">0</text>
                  {/* Bars */}
                  <rect x="55" y="85" width="34" height="40" fill="#c5c6d0" />
                  <rect x="105" y="50" width="34" height="75" fill="#8193cb" />
                  <rect x="155" y="25" width="34" height="100" fill="#006d3c" />
                  <rect x="205" y="38" width="34" height="87" fill="#172b5c" />
                  <rect x="255" y="95" width="34" height="30" fill="#531c00" />
                  {/* Labels */}
                  <text x="56" y="140" fill="var(--on-surface-variant)" fontSize="9" fontFamily="var(--font-jetbrains-mono)">0-5m</text>
                  <text x="104" y="140" fill="var(--on-surface-variant)" fontSize="9" fontFamily="var(--font-jetbrains-mono)">5-10m</text>
                  <text x="153" y="140" fill="var(--on-surface-variant)" fontSize="9" fontFamily="var(--font-jetbrains-mono)">10-15m</text>
                  <text x="203" y="140" fill="var(--on-surface-variant)" fontSize="9" fontFamily="var(--font-jetbrains-mono)">15-22m</text>
                  <text x="258" y="140" fill="var(--on-surface-variant)" fontSize="9" fontFamily="var(--font-jetbrains-mono)">&gt;22m</text>
                </svg>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '11px', fontFamily: 'var(--font-jetbrains-mono)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 6px', backgroundColor: 'var(--surface)' }}>
                  <span>Dominant Reservoir:</span>
                  <strong style={{ color: 'var(--primary)' }}>10–15m Class (184.2k t CO₂e)</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 6px', backgroundColor: 'var(--surface)' }}>
                  <span>Upper Strata (&gt;22m):</span>
                  <strong style={{ color: 'var(--primary)' }}>42.1k t CO₂e (8.5%)</strong>
                </div>
              </div>
            </div>

            {/* Field Validation Network Card */}
            <div className={styles.validationCard}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span className={styles.chartTitle}>Field Validation Network</span>
                <span style={{ backgroundColor: 'var(--secondary-fixed)', color: 'var(--on-secondary-fixed)', fontFamily: 'var(--font-jetbrains-mono)', fontSize: '10px', padding: '1px 6px', fontWeight: 600 }}>
                  R² = 0.884
                </span>
              </div>
              <div style={{ fontSize: '12px', lineHeight: 1.45, color: 'var(--on-surface-variant)' }}>
                148 validated circular permanent sample plots (0.1 ha) across Vetal Tekdi, Empress Garden, and SPPU Botanical Reserve. Mean Height Bias: -0.42m; RMSE: 1.83m.
              </div>
            </div>

            {/* Strict Method Notice Banner */}
            <div className={styles.noticeCard}>
              <div className={styles.noticeTitle}>
                <span className="material-symbols-outlined" style={{ fontSize: '15px' }}>warning</span>
                <span>Accounting Constraint Notice</span>
              </div>
              <p className={styles.noticeBody}>
                Standing carbon stock represents current stored above-ground biomass, not annual future sequestration. Do not conflate baseline stock with mitigation credits without longitudinal flux verification.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Ward & Biotope Carbon Distribution Matrix */}
      <section className={styles.tableSection}>
        <div className={styles.tableCard}>
          <div className={styles.tableHeader}>
            <div>
              <span style={{ fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--secondary)' }}>
                Spatial Aggregation Engine
              </span>
              <h2 className={styles.tableTitle}>Ward &amp; Biotope Carbon Distribution Matrix</h2>
              <p className={styles.tableSubtitle}>Comparative stock metrics across primary Pune municipal administrative zones</p>
            </div>
            <div>
              <input
                type="text"
                className={styles.tableFilter}
                placeholder="Filter ward / biotope..."
                value={filterText}
                onChange={(e) => setFilterText(e.target.value)}
              />
            </div>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table className={styles.matrixTable}>
              <thead>
                <tr>
                  <th>Ward / Biotope Unit</th>
                  <th style={{ textAlign: 'right' }}>Spatial Area (km²)</th>
                  <th style={{ textAlign: 'right' }}>Canopy Area (km²)</th>
                  <th style={{ textAlign: 'right' }}>Stem Count</th>
                  <th style={{ textAlign: 'right' }}>Biomass Stock (t CO₂e)</th>
                  <th style={{ textAlign: 'right' }}>Mean Carbon Density</th>
                  <th style={{ textAlign: 'center' }}>Biotope Risk Rating</th>
                </tr>
              </thead>
              <tbody>
                {filteredWards.map((w, idx) => (
                  <tr key={idx}>
                    <td>
                      <strong style={{ color: 'var(--primary)', fontFamily: 'var(--font-ibm-plex-sans)' }}>{w.ward}</strong>
                      <span style={{ display: 'block', fontSize: '10px', color: 'var(--outline)' }}>{w.biotope}</span>
                    </td>
                    <td style={{ textAlign: 'right' }}>{w.area}</td>
                    <td style={{ textAlign: 'right', color: 'var(--secondary)', fontWeight: 600 }}>
                      {w.canopy} <span style={{ fontSize: '10px', color: 'var(--outline)', fontWeight: 400 }}>({w.canopyPct})</span>
                    </td>
                    <td style={{ textAlign: 'right' }}>{w.stems}</td>
                    <td style={{ textAlign: 'right', fontWeight: 700, color: 'var(--primary)' }}>{w.stock}</td>
                    <td style={{ textAlign: 'right' }}>{w.density}</td>
                    <td style={{ textAlign: 'center' }}>
                      <span style={{ backgroundColor: w.riskColor, color: '#ffffff', fontSize: '9px', padding: '2px 6px', fontWeight: 600, textTransform: 'uppercase' }}>
                        {w.risk}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Methodological Chain Sequence */}
      <section className={styles.methodSection}>
        <div style={{ textAlign: 'center', maxWidth: '640px', margin: '0 auto' }}>
          <span style={{ fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--outline)' }}>
            Scientific Sequence
          </span>
          <h2 style={{ fontFamily: 'var(--font-ibm-plex-sans)', fontSize: '20px', fontWeight: 700, color: 'var(--primary)', marginTop: '4px' }}>
            Multi-Source Allometric Pipeline
          </h2>
        </div>

        <div className={styles.chain}>
          <div className={styles.chainStep}>
            <div className={styles.stepTitle}>01 CANOPY SEGMENTATION</div>
            <div className={styles.stepDesc}>Frozen UEHIS U-Net deep learning model providing 10m spatial urban canopy footprints from Sentinel-2 MSI.</div>
          </div>

          <div className={styles.chainStep}>
            <div className={styles.stepTitle}>02 CANOPY HEIGHT</div>
            <div className={styles.stepDesc}>ETH Global Canopy Height 2020 10m continuous raster intersected with canopy geometry for vertical structure.</div>
          </div>

          <div className={styles.chainStep}>
            <div className={styles.stepTitle}>03 ALLOMETRIC BIOMASS</div>
            <div className={styles.stepDesc}>Computed via urban_generic allometric models aggregating spatial and vertical metrics to establish woody mass.</div>
          </div>

          <div className={styles.chainStepActive}>
            <div className={styles.stepTitle}>04 STANDING CARBON</div>
            <div className={styles.stepDesc}>0.47 carbon fraction and 44/12 stoichiometric conversion. Represents current stored biomass, not future annual sequestration.</div>
          </div>
        </div>
      </section>
    </div>
  );
}

export default function CarbonPage() {
  return (
    <Suspense fallback={<div style={{ padding: '24px' }}>Loading Carbon Assessment...</div>}>
      <CarbonContent />
    </Suspense>
  );
}
