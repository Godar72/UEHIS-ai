'use client';

import React, { useState, useMemo } from 'react';
import styles from './methodology.module.css';

interface SectionDef {
  id: string;
  num: string;
  title: string;
  sub: string;
  keywords: string;
  render: () => React.ReactNode;
}

export default function MethodologyPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    'sec-01': true,
    'sec-04': true
  });
  const [allExpanded, setAllExpanded] = useState(false);

  const sections: SectionDef[] = useMemo(() => [
    {
      id: 'sec-01',
      num: '01',
      title: 'System Overview & Spatial Foundation',
      sub: 'Partitioning logic, CRS, and cell eligibility',
      keywords: 'spatial foundation orthogonal grid 5309 5298 250m epsg 32643 scorable excluded coordinate reference utm 43n',
      render: () => (
        <>
          <div className={styles.statsQuad}>
            <div className={styles.statQuadBox}>
              <span className={styles.statQuadLabel}>Total Grid Cells</span>
              <span className={styles.statQuadValue}>5,309 Blocks</span>
            </div>
            <div className={styles.statQuadBox}>
              <span className={styles.statQuadLabel}>Cell Dimensions</span>
              <span className={styles.statQuadValue}>250m × 250m</span>
            </div>
            <div className={styles.statQuadBox}>
              <span className={styles.statQuadLabel}>Scorable Partition</span>
              <span className={styles.statQuadValueGreen}>5,298 Active</span>
            </div>
            <div className={styles.statQuadBox}>
              <span className={styles.statQuadLabel}>Excluded Boundary</span>
              <span className={styles.statQuadValueRed}>11 Excluded</span>
            </div>
          </div>
          <p className={styles.textParagraph}>
            The municipal computational fabric relies on an orthogonal regular grid projected in <strong>EPSG:32643 (UTM Zone 43N)</strong>. This projection minimizes planar area and distance distortion across Pune's heterogeneous terrain and ridgelines.
          </p>
          <div className={styles.calloutNotice}>
            <strong>Exclusion Criteria:</strong> 11 perimeter cells lack sufficient terrestrial surface area (&lt;10% land surface) along jurisdictional water reservoirs and river margins; these cells are excluded from index calculations and are strictly not treated as zero values.
          </div>
        </>
      )
    },
    {
      id: 'sec-02',
      num: '02',
      title: 'Satellite Data & Earth Observation Sensors',
      sub: '5 remote sensing instruments & ingested baselines',
      keywords: 'sentinel landsat worldpop satpm acag wustl srtm sensors optical thermal srtmgl1 multispectral ndvi lst pm25',
      render: () => (
        <div className={styles.itemsGrid}>
          <div className={styles.itemCard}>
            <div className={styles.itemHeader}>
              <span className={styles.itemName}>Sentinel-2 L2A MSI</span>
              <span className={styles.itemBadgeGreen}>10m / 20m</span>
            </div>
            <p className={styles.itemDesc}>
              Multispectral surface reflectance. Utilized for continuous Normalized Difference Vegetation Index (NDVI), canopy cover ratios, and impervious fraction masking.
            </p>
          </div>
          <div className={styles.itemCard}>
            <div className={styles.itemHeader}>
              <span className={styles.itemName}>Landsat 8 LST Thermal Infrared</span>
              <span className={styles.itemBadge}>30m (Resampled)</span>
            </div>
            <p className={styles.itemDesc}>
              Split-window thermal radiometry producing calibrated Land Surface Temperature (°C) baseline layers across peak diurnal solar cycles.
            </p>
          </div>
          <div className={styles.itemCard}>
            <div className={styles.itemHeader}>
              <span className={styles.itemName}>WorldPop R2025A 2024</span>
              <span className={styles.itemBadge}>100m Constrained</span>
            </div>
            <p className={styles.itemDesc}>
              High-resolution demographic dasymetric mapping for computing human population density and environmental exposure multipliers.
            </p>
          </div>
          <div className={styles.itemCard}>
            <div className={styles.itemHeader}>
              <span className={styles.itemName}>ACAG/WUSTL SatPM V6.GL.03</span>
              <span className={styles.itemBadge}>0.01° Grid</span>
            </div>
            <p className={styles.itemDesc}>
              2024 seasonal ground-level fine particulate matter (PM2.5) derived via aerosol optical depth combined with GEOS-Chem chemical transport models.
            </p>
          </div>
          <div className={styles.itemCard}>
            <div className={styles.itemHeader}>
              <span className={styles.itemName}>USGS SRTMGL1_003</span>
              <span className={styles.itemBadge}>1 Arc-Second</span>
            </div>
            <p className={styles.itemDesc}>
              Digital elevation model baseline for continuous terrain slope analysis, ridgeline masking, and hydrologic drainage conditioning.
            </p>
          </div>
        </div>
      )
    },
    {
      id: 'sec-03',
      num: '03',
      title: 'Semantic Segmentation Engine',
      sub: 'Neural architecture & weight freeze protocol',
      keywords: 'semantic segmentation unet model pune frozen 2026 inference deep learning tta augmentation',
      render: () => (
        <>
          <div className={styles.calloutNotice}>
            <strong>Model Identification:</strong> <code>pune_unet_segmentation_FROZEN_2026</code>
          </div>
          <p className={styles.textParagraph}>
            A modified encoder-decoder U-Net backbone trained over high-resolution aerial and satellite imagery specifically tuned for the Deccan plateau peri-urban morphology. The model generates class masks across tree canopies, built structures, bare soil, and riparian water courses.
          </p>
          <p className={styles.textParagraph}>
            Inference robustness is achieved via an <strong>8-way Test-Time Augmentation (TTA)</strong> production pipeline. Weights are cryptographically locked under the 2026 frozen tag to prevent model drift between seasonal temporal runs and ensure comparability across legislative reviews.
          </p>
        </>
      )
    },
    {
      id: 'sec-04',
      num: '04',
      title: 'UEHI Index Formulation & Weighting',
      sub: 'Area-weighted block intersection aggregation & 6-factor model',
      keywords: 'uehi index formulation formula area-weighted intersection math aggregation normalization entropy variance floor population multiplier beta 0.3',
      render: () => (
        <>
          <span className={styles.statQuadLabel}>Study-Area Aggregation Formula</span>
          <div className={styles.equationBlock}>
            <div className={styles.equationText}>
              UEHI_area = ∑(UEHI_i × intersection_area_i) / ∑(intersection_area_i)
            </div>
          </div>
          <p className={styles.textParagraph}>
            When assessing custom study areas, wards, or environmental impact polygons, the composite score is resolved through exact planar topological clipping. The 6 core factors include:
          </p>
          <div className={styles.itemsGrid}>
            <div className={styles.itemCard}>
              <div className={styles.itemHeader}>
                <span className={styles.itemName}>tree_density (Positive)</span>
                <span className={styles.itemBadgeGreen}>Weight: Dynamic Entropy</span>
              </div>
              <p className={styles.itemDesc}>Derived from Sentinel-2 canopy segmentations.</p>
            </div>
            <div className={styles.itemCard}>
              <div className={styles.itemHeader}>
                <span className={styles.itemName}>ndvi (Positive)</span>
                <span className={styles.itemBadgeGreen}>Weight: Dynamic Entropy</span>
              </div>
              <p className={styles.itemDesc}>Multispectral vegetation vigour index.</p>
            </div>
            <div className={styles.itemCard}>
              <div className={styles.itemHeader}>
                <span className={styles.itemName}>impervious_surfaces (Negative)</span>
                <span className={styles.itemBadge}>Penalty</span>
              </div>
              <p className={styles.itemDesc}>Built-up fraction reducing natural hydrologic infiltration.</p>
            </div>
            <div className={styles.itemCard}>
              <div className={styles.itemHeader}>
                <span className={styles.itemName}>temperature (Negative)</span>
                <span className={styles.itemBadge}>Penalty</span>
              </div>
              <p className={styles.itemDesc}>Land Surface Temperature thermal heat island impact.</p>
            </div>
            <div className={styles.itemCard}>
              <div className={styles.itemHeader}>
                <span className={styles.itemName}>pm25 (Negative)</span>
                <span className={styles.itemBadge}>Penalty</span>
              </div>
              <p className={styles.itemDesc}>Ambient fine particulate matter concentration baseline.</p>
            </div>
            <div className={styles.itemCard}>
              <div className={styles.itemHeader}>
                <span className={styles.itemName}>population_exposure (Negative Penalty Multiplier)</span>
                <span className={styles.itemBadge}>m(i) = 1 - β · N(Pop_i)</span>
              </div>
              <p className={styles.itemDesc}>
                Demographic density from WorldPop. With β = 0.3, higher population exposure acts as a strict penalty reducing the final health score.
              </p>
            </div>
          </div>
          <p className={styles.textParagraph}>
            To prevent dimensional collapse in low-variance variables, a <strong>coefficient-of-variation variance floor</strong> is strictly enforced prior to Shannon entropy weighting.
          </p>
        </>
      )
    },
    {
      id: 'sec-05',
      num: '05',
      title: 'Carbon Stock Estimation',
      sub: 'Allometric scaling & stoichiometric conversions',
      keywords: 'carbon stock estimation eth canopy height 2020 allometric stoichiometric 0.47 biomass 44/12 standing carbon',
      render: () => (
        <>
          <div className={styles.statsQuad}>
            <div className={styles.statQuadBox}>
              <span className={styles.statQuadLabel}>Carbon Fraction</span>
              <span className={styles.statQuadValue}>0.47 Dry Mass</span>
            </div>
            <div className={styles.statQuadBox}>
              <span className={styles.statQuadLabel}>Stoichiometric Ratio</span>
              <span className={styles.statQuadValue}>44 / 12 CO₂e</span>
            </div>
          </div>
          <p className={styles.textParagraph}>
            Carbon estimations synthesize <strong>frozen U-Net canopy</strong> masks with <strong>ETH Global Canopy Height 2020</strong> (10m continuous raster) and the standard <strong>urban_generic</strong> allometric equation.
          </p>
          <div className={styles.calloutNotice}>
            <strong>Critical Accounting Notice:</strong> Standing carbon stock represents current stored above-ground and below-ground biomass, NOT annual future sequestration. Estimates quantify structural storage present at the baseline timestamp.
          </div>
        </>
      )
    },
    {
      id: 'sec-06',
      num: '06',
      title: 'Planting Opportunities & Land Suitability',
      sub: 'Eligible opportunity classes & tenure boundaries',
      keywords: 'planting opportunities candidate classes open space ownership utilities permission unknown cadastre',
      render: () => (
        <>
          <p className={styles.textParagraph}>
            Potential planting opportunities are identified across non-built, non-water, and non-road land surfaces classified into three empirical opportunity classes:
          </p>
          <div className={styles.itemsGrid}>
            <div className={styles.itemCard}>
              <div className={styles.itemHeader}>
                <span className={styles.itemName}>Public-like open space</span>
                <span className={styles.itemBadgeGreen}>High Viability</span>
              </div>
              <p className={styles.itemDesc}>Public gardens, institution campuses, and designated green zones.</p>
            </div>
            <div className={styles.itemCard}>
              <div className={styles.itemHeader}>
                <span className={styles.itemName}>Context-dependent space</span>
                <span className={styles.itemBadge}>Conditional Viability</span>
              </div>
              <p className={styles.itemDesc}>Road easements, perimeter buffers, and institutional setbacks requiring clearance.</p>
            </div>
            <div className={styles.itemCard}>
              <div className={styles.itemHeader}>
                <span className={styles.itemName}>Other open space</span>
                <span className={styles.itemBadge}>Secondary Viability</span>
              </div>
              <p className={styles.itemDesc}>Vacant open plots and low-density undeveloped perimeters.</p>
            </div>
          </div>
          <div className={styles.calloutNotice}>
            <strong>Tenure Disclaimers:</strong> Site ownership, subterranean utility corridors, and municipal permissions are UNKNOWN. Field verification and ground surveys are required before any planting activity.
          </div>
        </>
      )
    },
    {
      id: 'sec-07',
      num: '07',
      title: 'Analytical Scenarios & Spacing Constraint',
      sub: '100K, 250K, 500K units with 10m minimum spacing rule',
      keywords: 'analytical scenarios 100k 250k 500k units 10m spacing standing carbon co2e iso-radial buffer',
      render: () => (
        <>
          <p className={styles.textParagraph}>
            Intervention modeling tests hypothetical deployment tracks subject to a strict <strong>10-metre minimum iso-radial spacing constraint</strong> between candidate planting points to prevent unrealistic density clustering.
          </p>
          <div className={styles.statsQuad}>
            <div className={styles.statQuadBox}>
              <span className={styles.statQuadLabel}>Track 01</span>
              <span className={styles.statQuadValue}>100K Units</span>
              <span className={styles.itemDesc}>~50k t CO₂e yield</span>
            </div>
            <div className={styles.statQuadBox}>
              <span className={styles.statQuadLabel}>Track 02</span>
              <span className={styles.statQuadValue}>250K Units</span>
              <span className={styles.itemDesc}>~125k t CO₂e yield</span>
            </div>
            <div className={styles.statQuadBox}>
              <span className={styles.statQuadLabel}>Track 03</span>
              <span className={styles.statQuadValue}>500K Units</span>
              <span className={styles.itemDesc}>~250k t CO₂e yield</span>
            </div>
          </div>
          <div className={styles.calloutNotice}>
            <strong>Conversion Assumption:</strong> Modeled using an illustrative proxy factor of 0.5 t CO₂e per tree once full structural canopy maturity is achieved.
          </div>
        </>
      )
    },
    {
      id: 'sec-08',
      num: '08',
      title: 'Limitations & Uncertainty Boundaries',
      sub: 'Sensor temporal revisit, cloud masks, and utility constraints',
      keywords: 'limitations satellite revisit cloud cover masks subsurface utility constraints uncertainty',
      render: () => (
        <div className={styles.itemsGrid}>
          <div className={styles.itemCard}>
            <span className={styles.itemName}>1. Satellite Revisit Cycles</span>
            <p className={styles.itemDesc}>
              Constellation orbital cycles range from 5 to 16 days. Rapid surface alterations or tree felling events may experience latency before detection.
            </p>
          </div>
          <div className={styles.itemCard}>
            <span className={styles.itemName}>2. Cloud Cover Masks</span>
            <p className={styles.itemDesc}>
              Monsoonal cloud opacity during peak vegetative growth (June–September) requires composite synthesis, leading to potential dry-season biases in optical indexes.
            </p>
          </div>
          <div className={styles.itemCard}>
            <span className={styles.itemName}>3. Subsurface Utility Constraints</span>
            <p className={styles.itemDesc}>
              Underground storm water mains, electrical cabling, and metro infrastructure cannot be detected via satellite and require physical ground radar verification.
            </p>
          </div>
        </div>
      )
    }
  ], []);

  const toggleSection = (id: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  const handleToggleAll = () => {
    const nextState = !allExpanded;
    setAllExpanded(nextState);
    const updated: Record<string, boolean> = {};
    sections.forEach(s => {
      updated[s.id] = nextState;
    });
    setExpandedSections(updated);
  };

  const filteredSections = useMemo(() => {
    if (!searchTerm.trim()) return sections;
    const term = searchTerm.toLowerCase();
    return sections.filter(s => 
      s.title.toLowerCase().includes(term) ||
      s.sub.toLowerCase().includes(term) ||
      s.keywords.toLowerCase().includes(term)
    );
  }, [sections, searchTerm]);

  return (
    <div className={styles.container}>
      <div className={styles.inner}>
        {/* Document Official Header */}
        <section className={styles.docHeader}>
          <div className={styles.headerTop}>
            <div className={styles.docRefBadge}>
              DOC-REF // 2024-ETH-UEHI
            </div>
            <span className={styles.revBadge}>REV 4.2 · OFFICIAL SPEC</span>
          </div>

          <h1 className={styles.docTitle}>UEHIS Technical Methodology &amp; Provenance</h1>
          <p className={styles.docSubtitle}>
            Urban Ecosystem Health Intelligence System · Pune Baseline 2024
          </p>

          <div className={styles.metaInfoCard}>
            <div className={styles.metaCol}>
              <span className={styles.metaLabel}>Institutional Affiliation</span>
              <span className={styles.metaValue}>SEER Bharat Foundation, Pune</span>
            </div>
            <div className={styles.metaColRight}>
              <span className={styles.metaLabel}>Spatial Datum</span>
              <span className={styles.metaValueDatum}>EPSG:32643 · UTM 43N</span>
            </div>
          </div>
        </section>

        {/* Search & Collapse Toolbar */}
        <div className={styles.toolbar}>
          <div className={styles.searchBox}>
            <span className="material-symbols-outlined" style={{ fontSize: '16px', color: 'var(--on-surface-variant)' }}>
              search
            </span>
            <input 
              type="text"
              placeholder="Filter parameters, models, equations..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <button className={styles.expandBtn} onClick={handleToggleAll}>
            <span className="material-symbols-outlined" style={{ fontSize: '15px' }}>
              {allExpanded ? 'unfold_less' : 'unfold_more'}
            </span>
            <span>{allExpanded ? 'Collapse All' : 'Expand All'}</span>
          </button>
        </div>

        {/* Accordions */}
        <div className={styles.accordionList}>
          {filteredSections.map(sec => {
            const isOpen = searchTerm.trim().length > 0 || !!expandedSections[sec.id];

            return (
              <div key={sec.id} className={styles.sectionCard}>
                <button 
                  className={styles.sectionHeader}
                  onClick={() => toggleSection(sec.id)}
                  aria-expanded={isOpen}
                >
                  <div className={styles.headerLeft}>
                    <span className={styles.sectionIndex}>{sec.num}</span>
                    <div>
                      <span className={styles.sectionHeaderTitle}>{sec.title}</span>
                      <span className={styles.sectionHeaderSub}>{sec.sub}</span>
                    </div>
                  </div>
                  <span className={`material-symbols-outlined ${styles.arrowIcon} ${isOpen ? styles.arrowOpen : ''}`}>
                    expand_more
                  </span>
                </button>

                {isOpen && (
                  <div className={styles.sectionContent}>
                    {sec.render()}
                  </div>
                )}
              </div>
            );
          })}

          {filteredSections.length === 0 && (
            <div style={{ padding: '32px', textAlign: 'center', color: 'var(--on-surface-variant)' }}>
              No methodology sections match &quot;{searchTerm}&quot;
            </div>
          )}
        </div>

        {/* Document Provenance Certification Footer */}
        <section className={styles.certificationCard}>
          <div className={styles.certHeader}>
            <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>verified_user</span>
            <span className={styles.certTitle}>Methodology Integrity Certification</span>
          </div>
          <p className={styles.certText}>
            This computational reference establishes the standard environmental auditing framework for Pune Municipal Corporation ward demarcations. Published by SEER Bharat Foundation under spatial research protocol v2024.3.
          </p>
          <div className={styles.certFooter}>
            <span>HASH: 9a9c8c315ccc04c85e179cf44627d7f7...</span>
            <span>MARCH 2025 · PROD_NODE_04</span>
          </div>
        </section>
      </div>
    </div>
  );
}
