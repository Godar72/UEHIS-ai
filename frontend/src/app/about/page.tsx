'use client';

import React from 'react';
import styles from './about.module.css';
import Link from 'next/link';

export default function AboutPage() {
  const chapters = [
    {
      id: 'ch-01',
      num: '01',
      title: 'Getting Started with UEHIS',
      category: 'SYSTEM FOUNDATION',
      content: (
        <>
          <p className={styles.chapterText}>
            The <strong>Urban Ecosystem Health Intelligence System (UEHIS)</strong> is an authoritative scientific cartographic workstation and spatial computing platform designed for Pune, India. Developed in partnership with the <em>SEER Bharat Foundation</em>, UEHIS shifts environmental discourse into verifiable, sub-kilometer biophysical accounting.
          </p>
          <div className={styles.dataCallout}>
            <span className={styles.dataCalloutTitle}>Spatial Orthogonal Matrix Specification</span>
            <div className={styles.dataStatsGrid}>
              <div className={styles.dataStatBox}>
                <span className={styles.dataStatLabel}>Total Study Grid</span>
                <span className={styles.dataStatValue}>5,309 Blocks</span>
              </div>
              <div className={styles.dataStatBox}>
                <span className={styles.dataStatLabel}>Evaluated Scorable</span>
                <span className={styles.dataStatValueGreen}>5,298 Active</span>
              </div>
              <div className={styles.dataStatBox}>
                <span className={styles.dataStatLabel}>Resolution</span>
                <span className={styles.dataStatValue}>250m × 250m</span>
              </div>
            </div>
          </div>
          <p className={styles.chapterText}>
            The central operational index is the <strong>Urban Ecosystem Health Index (UEHI)</strong>—a normalized composite index scored on a scale from <code>0 to 100</code> (where lower indicates healthier conditions), projected in <strong>EPSG:32643 UTM Zone 43N</strong>.
          </p>
        </>
      )
    },
    {
      id: 'ch-02',
      num: '02',
      title: 'Understanding the Homepage',
      category: 'ATLAS OVERVIEW',
      content: (
        <>
          <p className={styles.chapterText}>
            The homepage serves as the institutional gateway to Pune&apos;s biophysical baseline. It features an interactive hero map stage, live municipal summary metrics (total blocks, mean UEHI, carbon stock, canopy coverage), and a 6-factor methodology breakdown.
          </p>
          <div className={styles.stepsList}>
            <div className={styles.stepItem}>
              <span className={styles.stepNum}>01</span>
              <div className={styles.stepContent}>
                <span className={styles.stepHeader}>Live Telemetry</span>
                <p className={styles.stepDesc}>Review citywide totals: 5,309 grid blocks, 493.1k t CO₂e carbon stock, and 21.51 km² tree canopy area.</p>
              </div>
            </div>
            <div className={styles.stepItem}>
              <span className={styles.stepNum}>02</span>
              <div className={styles.stepContent}>
                <span className={styles.stepHeader}>Locality Jump</span>
                <p className={styles.stepDesc}>Use quick locality chips (Baner, Kothrud, Hadapsar, Viman Nagar, Hinjawadi) to instantly navigate to focal zones.</p>
              </div>
            </div>
          </div>
        </>
      )
    },
    {
      id: 'ch-03',
      num: '03',
      title: 'Using the Explore Map',
      category: 'GIS WORKSPACE',
      content: (
        <>
          <p className={styles.chapterText}>
            The <code>/explore</code> workspace is the primary geospatial interface. Built on MapLibre GL with GPU-accelerated vector tiles (<code>/tiles/uehi/...</code>), it renders Pune&apos;s 5,309 blocks with smooth pan, zoom, and continuous data querying.
          </p>
          <div className={styles.dataCallout}>
            <span className={styles.dataCalloutTitle}>Map Control Capabilities</span>
            <p className={styles.chapterText}>
              • <strong>Basemap Switcher:</strong> Toggle between high-contrast Carto Light vector basemap and true-color Sentinel-2 satellite imagery.<br />
              • <strong>Layer Stack:</strong> Enable or disable UEHI score choropleths, carbon density overlays, and candidate planting units.<br />
              • <strong>Four-Tier Risk Legend:</strong> Low (&lt;45), Moderate (45-60), High (60-75), Severe (&gt;75).
            </p>
          </div>
        </>
      )
    },
    {
      id: 'ch-04',
      num: '04',
      title: 'Understanding a Block (250m × 250m)',
      category: 'DATA INSPECTOR',
      content: (
        <>
          <p className={styles.chapterText}>
            Clicking any grid cell activates the <strong>Block Attribution Inspector</strong> dock. Every 250m × 250m cell provides:
          </p>
          <div className={styles.stepsList}>
            <div className={styles.stepItem}>
              <span className={styles.stepNum}>A</span>
              <div className={styles.stepContent}>
                <span className={styles.stepHeader}>Composite Index &amp; Risk Classification</span>
                <p className={styles.stepDesc}>Calibrated score (0-100) and risk tier badge.</p>
              </div>
            </div>
            <div className={styles.stepItem}>
              <span className={styles.stepNum}>B</span>
              <div className={styles.stepContent}>
                <span className={styles.stepHeader}>Six Core Environmental Indicators</span>
                <p className={styles.stepDesc}>Tree density, NDVI, impervious surface fraction, land surface temperature (°C), PM2.5, and population exposure.</p>
              </div>
            </div>
            <div className={styles.stepItem}>
              <span className={styles.stepNum}>C</span>
              <div className={styles.stepContent}>
                <span className={styles.stepHeader}>Carbon Sink &amp; Biomass Metrics</span>
                <p className={styles.stepDesc}>Calculated carbon stock (t CO₂e), mean canopy height (m), and estimated tree count.</p>
              </div>
            </div>
            <div className={styles.stepItem}>
              <span className={styles.stepNum}>D</span>
              <div className={styles.stepContent}>
                <span className={styles.stepHeader}>Coordinate Precision &amp; Copy Action</span>
                <p className={styles.stepDesc}>Centroid geodetic coordinates (WGS84 lat/lng and UTM Zone 43N northing/easting) with one-click clipboard copying.</p>
              </div>
            </div>
          </div>
        </>
      )
    },
    {
      id: 'ch-05',
      num: '05',
      title: 'Searching for a Location',
      category: 'GEOCODING & NAVIGATION',
      content: (
        <>
          <p className={styles.chapterText}>
            The search bar in the GIS sidebar provides autocomplete geocoding. Enter ward names, neighborhood landmarks, or coordinates to fly the camera directly to that location with optimal zoom and highlight bounds.
          </p>
        </>
      )
    },
    {
      id: 'ch-06',
      num: '06',
      title: 'Study-Area Spatial Analysis',
      category: 'POLYGON ANALYTICS',
      content: (
        <>
          <p className={styles.chapterText}>
            When selecting custom study areas, wards, or bounding polygons, the system executes real-time planar topological clipping and re-aggregates the composite index using exact area weighting:
          </p>
          <div className={styles.dataCallout}>
            <span className={styles.dataCalloutTitle}>Area-Weighted Formulation</span>
            <code style={{ fontFamily: 'var(--font-jetbrains-mono)', fontSize: '0.8125rem', color: 'var(--primary)' }}>
              UEHI_area = ∑(UEHI_i × intersection_area_i) / ∑(intersection_area_i)
            </code>
            <p className={styles.chapterText} style={{ marginTop: '8px' }}>
              The report details the scorable surface fraction, 4-tier risk distribution, recomputed carbon stock, and candidate planting opportunities.
            </p>
          </div>
        </>
      )
    },
    {
      id: 'ch-07',
      num: '07',
      title: 'Carbon Stock Scientific Assessment',
      category: 'CARBON MODELING',
      content: (
        <>
          <p className={styles.chapterText}>
            The <code>/carbon</code> page provides a dedicated biophysical assessment of Pune&apos;s vegetative carbon reservoir. Grounded in ETH Global Canopy Height 2020 and Sentinel-2 segmentation, it quantifies total standing carbon at <strong>493.1k t CO₂e (±7.79% CI)</strong>.
          </p>
          <div className={styles.dataCallout}>
            <span className={styles.dataCalloutTitle}>Crucial Scientific Accounting Rule</span>
            <p className={styles.chapterText}>
              Standing carbon stock represents currently stored above-ground and below-ground biomass, <strong>NOT annual future sequestration</strong>.
            </p>
          </div>
        </>
      )
    },
    {
      id: 'ch-08',
      num: '08',
      title: 'Planting Opportunities & Field Protocol',
      category: 'VEGETATION PLANNING',
      content: (
        <>
          <p className={styles.chapterText}>
            The <code>/planting</code> workspace visualizes candidate planting units derived from unbuilt, non-road, non-water surfaces. Every candidate unit enforces a strict <strong>10-metre iso-radial spacing constraint</strong>.
          </p>
          <p className={styles.chapterText}>
            <strong>Municipal Cadastre Notice:</strong> All points represent potential theoretical opportunities. Site tenure, utility easements, and permissions are unknown and require site-level engineering surveys.
          </p>
        </>
      )
    },
    {
      id: 'ch-09',
      num: '09',
      title: 'Systemic Intervention Scenarios',
      category: 'SCENARIO MODELING',
      content: (
        <>
          <p className={styles.chapterText}>
            The <code>/scenarios</code> sandbox models three strategic tracks: <strong>100K Units</strong> (corridor infill), <strong>250K Units</strong> (public easement expansion), and <strong>500K Units</strong> (saturated intervention). Each track projects mean UEHI improvements and standing carbon gains using an illustrative 0.5 t CO₂e/unit assumption.
          </p>
        </>
      )
    },
    {
      id: 'ch-10',
      num: '10',
      title: 'Methodology & Data Provenance',
      category: 'SCIENTIFIC INTEGRITY',
      content: (
        <>
          <p className={styles.chapterText}>
            Access the full peer-reviewed methodology at <code>/methodology</code>. Model weights are frozen under <code>pune_unet_segmentation_FROZEN_2026</code> with verified cryptographic hashing to ensure multi-year audit reproducibility.
          </p>
        </>
      )
    },
    {
      id: 'ch-11',
      num: '11',
      title: 'Limitations & Uncertainty Boundaries',
      category: 'RISK & COMPLIANCE',
      content: (
        <>
          <p className={styles.chapterText}>
            Users must account for remote sensing revisit cycles (5-16 days), monsoonal cloud masking, and subterranean infrastructure limitations when using UEHIS data for municipal policymaking.
          </p>
        </>
      )
    },
    {
      id: 'ch-12',
      num: '12',
      title: 'Scientific Glossary & Standards',
      category: 'REFERENCE',
      content: (
        <>
          <p className={styles.chapterText}>
            • <strong>AGB / BGB:</strong> Above-Ground and Below-Ground Biomass.<br />
            • <strong>EPSG:32643:</strong> UTM Zone 43N projected coordinate reference system.<br />
            • <strong>LST:</strong> Land Surface Temperature (°C) derived from Landsat 8 TIRS.<br />
            • <strong>NDVI:</strong> Normalized Difference Vegetation Index (Band 8 - Band 4)/(Band 8 + Band 4).<br />
            • <strong>PM2.5:</strong> Atmospheric particulate matter &le; 2.5 microns (μg/m³).
          </p>
        </>
      )
    }
  ];

  return (
    <div className={styles.container}>
      {/* Top ID Strip */}
      <section className={styles.idStrip}>
        <div className={styles.idStripInner}>
          <div className={styles.idBadges}>
            <span className={styles.idBadgePrimary}>DOC: REF-2024-UEHIS-MANUAL</span>
            <span className={styles.idBadgeMuted}>STANDARD MANUAL V2.4-STABLE</span>
            <span className={styles.idBadgeMuted}>SCIENTIFIC BASELINE 2024</span>
          </div>

          <div className={styles.idActions}>
            <button className={styles.printBtn} onClick={() => window.print()}>
              <span className="material-symbols-outlined" style={{ fontSize: '15px' }}>print</span>
              <span>Export Citation Sheet</span>
            </button>
          </div>
        </div>
      </section>

      {/* Hero Header */}
      <header className={styles.heroSection}>
        <div className={styles.heroInner}>
          <div className={styles.tagPills}>
            <span className={styles.tagPillOrange}>TECHNICAL DOCUMENTATION · USER GUIDE</span>
            <span className={styles.tagPillMuted}>GIS OPERATIONAL SPECIFICATION</span>
            <span className={styles.tagPillGreen}>VERIFIED GEO-COORDINATION</span>
          </div>

          <div className={styles.heroTitleRow}>
            <div className={styles.heroTitles}>
              <h1 className={styles.heroTitle}>UEHIS User Manual &amp; Platform Guide</h1>
              <p className={styles.heroSubtitle}>
                A practical, scientific guide to exploring Pune’s urban ecosystem intelligence, spatial datasets, and analytical modeling.
              </p>
            </div>

            <div className={styles.heroMetaCard}>
              <span className={styles.heroMetaLabel}>Spatial Metadata Target</span>
              <span className={styles.heroMetaValue}>5,309 BLOCKS · EPSG:32643</span>
              <span className={styles.heroMetaSub}>
                <span style={{ width: '6px', height: '6px', backgroundColor: 'var(--secondary)', display: 'inline-block' }} />
                SEER Bharat Verified Ground Truth
              </span>
            </div>
          </div>

          <div className={styles.telemetryStrip}>
            <div className={styles.telemetryItems}>
              <span>GUIDE VERSION: 2.4-STABLE</span>
              <span style={{ opacity: 0.5 }}>/</span>
              <span>COVERAGE: 5,309 BLOCKS (331.81 KM²)</span>
              <span style={{ opacity: 0.5 }}>/</span>
              <span>CARTOGRAPHIC: EPSG:32643 UTM ZONE 43N</span>
            </div>
            <span className={styles.telemetryBadge}>RESEARCH-GRADE CARTOGRAPHY</span>
          </div>
        </div>
      </header>

      {/* Main 2-column documentation layout */}
      <div className={styles.contentArea}>
        {/* Sticky Table of Contents */}
        <aside className={styles.sidebarNav}>
          <div className={styles.tocCard}>
            <div className={styles.tocHeader}>
              <span className={styles.tocTitle}>Index Directory</span>
              <span className={styles.tocCount}>12 Chapters</span>
            </div>

            <nav className={styles.tocList}>
              {chapters.map(ch => (
                <a key={ch.id} href={`#${ch.id}`} className={styles.tocItem}>
                  <span className={styles.tocNum}>{ch.num}</span>
                  <span>{ch.title}</span>
                </a>
              ))}
            </nav>
          </div>

          <div className={styles.specWidget}>
            <span className={styles.specWidgetTitle}>Production Specs</span>
            <div className={styles.specGrid}>
              <div className={styles.specRow}>
                <span style={{ color: 'var(--outline-variant)' }}>Grid Unit:</span>
                <span>250m × 250m</span>
              </div>
              <div className={styles.specRow}>
                <span style={{ color: 'var(--outline-variant)' }}>Total Extent:</span>
                <span>331.81 km²</span>
              </div>
              <div className={styles.specRow}>
                <span style={{ color: 'var(--outline-variant)' }}>Canopy Extent:</span>
                <span>21.51 km² (6.48%)</span>
              </div>
              <div className={styles.specRow}>
                <span style={{ color: 'var(--outline-variant)' }}>Carbon Stock:</span>
                <span>493.1k t CO₂e</span>
              </div>
            </div>
          </div>
        </aside>

        {/* Chapters Flow */}
        <main className={styles.articleList}>
          {chapters.map(ch => (
            <section key={ch.id} id={ch.id} className={styles.chapterCard}>
              <div className={styles.chapterHeader}>
                <div className={styles.chapterTitleGroup}>
                  <span className={styles.chapterBadge}>{ch.num}</span>
                  <h2 className={styles.chapterTitle}>{ch.title}</h2>
                </div>
                <span className={styles.chapterSub}>{ch.category}</span>
              </div>

              {ch.content}
            </section>
          ))}
        </main>
      </div>
    </div>
  );
}
