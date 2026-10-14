'use client';

import React from 'react';
import styles from './terms.module.css';

export default function TermsPage() {
  const clauses = [
    {
      id: 'sec-01',
      num: '01',
      title: 'Acceptance of Terms',
      content: (
        <p className={styles.clauseText}>
          By accessing or utilizing the Urban Ecosystem Health Intelligence System (UEHIS) web application, vector tile services, or associated geospatial APIs, you enter into a binding agreement to adhere to these Terms &amp; Conditions. If you do not accept these provisions, you must discontinue access to this platform.
        </p>
      )
    },
    {
      id: 'sec-02',
      num: '02',
      title: 'About UEHIS & Platform Scope',
      content: (
        <p className={styles.clauseText}>
          UEHIS is an academic and municipal environmental intelligence workstation engineered by the <strong>SEER Bharat Foundation</strong>. It computes biophysical and ecological indicators across Pune, India, projected in <strong>EPSG:32643 UTM Zone 43N</strong> on a strict 250m × 250m orthogonal grid.
        </p>
      )
    },
    {
      id: 'sec-03',
      num: '03',
      title: 'Nature of Analytical Information',
      content: (
        <>
          <p className={styles.clauseText}>
            All metrics, indices, and raster segmentations provided on this platform are computed model outputs and estimates derived from satellite remote sensing and demographic datasets. They represent high-level diagnostic analytics, <strong>not ground-truth cadastre engineering determinations</strong>.
          </p>
          <div className={styles.highlightBox}>
            <strong>Scientific Integrity Rule:</strong> Remote sensing estimations are subject to atmospheric distortions, monsoonal cloud masks, and sensor spatial resolutions. Independent physical ground truth remains the standard for engineering and legal works.
          </div>
        </>
      )
    },
    {
      id: 'sec-04',
      num: '04',
      title: 'UEHI Interpretation & Spatial Limitations',
      content: (
        <p className={styles.clauseText}>
          The Urban Ecosystem Health Index (UEHI) is a composite index calibrated from 0 to 100. It is designed to expose macro-scale relative ecological vulnerability across neighborhoods and blocks. It must not be interpreted as an exact parcel-level or property-boundary assessment.
        </p>
      )
    },
    {
      id: 'sec-05',
      num: '05',
      title: 'Study Areas & Polygon Computations',
      content: (
        <p className={styles.clauseText}>
          Study-area aggregations utilize planar topological intersection with area-weighted score redistribution. Cells with insufficient terrestrial land cover (&lt;10%) are omitted from the denominator and are never assigned false zero values.
        </p>
      )
    },
    {
      id: 'sec-06',
      num: '06',
      title: 'Carbon Stock Modeling & Non-Sequestration Rule',
      content: (
        <div className={styles.highlightBox}>
          <strong>Critical Accounting Notice:</strong> Carbon metrics reflect <em>standing carbon stock</em> (current stored above-ground and below-ground biomass), <strong>NOT annual future sequestration</strong>. They must not be cited as certified carbon offset credits without empirical field inventory validation.
        </div>
      )
    },
    {
      id: 'sec-07',
      num: '07',
      title: 'Planting Opportunities & Mandatory Site Verification',
      content: (
        <p className={styles.clauseText}>
          Points identified on the Planting Opportunities map represent <strong>potential theoretical planting opportunities</strong>. Site tenure, landowner permissions, underground utility clearances (water lines, electrical cables, gas conduits), and soil suitability are UNKNOWN. Mandatory physical surveys and municipal clearances are required prior to any tree planting.
        </p>
      )
    },
    {
      id: 'sec-08',
      num: '08',
      title: 'Analytical Scenarios & 10m Spacing Constraint',
      content: (
        <p className={styles.clauseText}>
          Intervention tracks (100K, 250K, 500K) are hypothetical modeling simulations constrained by a strict <strong>10-metre minimum iso-radial spacing rule</strong>. Carbon equivalents are evaluated using an illustrative planning proxy of 0.5 t CO₂e per mature tree.
        </p>
      )
    },
    {
      id: 'sec-09',
      num: '09',
      title: 'Data Sources & Cartographic Projections',
      content: (
        <p className={styles.clauseText}>
          Ingested satellite baselines include Copernicus Sentinel-2 MSI, Landsat 8 TIRS, WorldPop R2025A, ACAG/WUSTL PM2.5, and USGS SRTMGL1. All planar distances and areas are calculated in UTM Zone 43N to preserve true ground geometry.
        </p>
      )
    },
    {
      id: 'sec-10',
      num: '10',
      title: 'Accuracy, Availability & Non-Warranty',
      content: (
        <p className={styles.clauseText}>
          The platform is provided &quot;AS IS&quot; and &quot;AS AVAILABLE&quot; without warranties of any kind. SEER Bharat Foundation disclaims all warranties regarding continuous uninterrupted server availability or fitness for specific financial investments.
        </p>
      )
    },
    {
      id: 'sec-11',
      num: '11',
      title: 'Third-Party Geospatial Services',
      content: (
        <p className={styles.clauseText}>
          Basemap vector and satellite tiles are rendered via MapTiler, Carto, and OpenStreetMap. Use of those map stages is subject to their respective terms of service and attribution requirements.
        </p>
      )
    },
    {
      id: 'sec-12',
      num: '12',
      title: 'User Responsibilities & Acceptable Use',
      content: (
        <p className={styles.clauseText}>
          Users agree not to: (1) Circumvent API rate-limiting or security controls; (2) Scrape vector tiles using automated bulk harvesters; (3) Falsify scientific data provenance or misrepresent UEHIS outputs as statutory municipal legal orders.
        </p>
      )
    },
    {
      id: 'sec-13',
      num: '13',
      title: 'Intellectual Property & Academic Citations',
      content: (
        <p className={styles.clauseText}>
          The UEHIS computational models, neural network weights (<code>pune_unet_segmentation_FROZEN_2026</code>), and interface design are proprietary assets of SEER Bharat Foundation. Academic use and citations must include the official identifier: <em>&quot;UEHIS Platform, SEER Bharat Foundation, Pune (2024)&quot;</em>.
        </p>
      )
    },
    {
      id: 'sec-14',
      num: '14',
      title: 'Limitation of Liability & Indemnification',
      content: (
        <p className={styles.clauseText}>
          In no event shall SEER Bharat Foundation, its researchers, or technical contributors be liable for any direct, indirect, incidental, or consequential damages resulting from policy decisions, urban planning actions, or financial allocations based on platform outputs.
        </p>
      )
    },
    {
      id: 'sec-15',
      num: '15',
      title: 'Governing Law & Jurisdiction',
      content: (
        <p className={styles.clauseText}>
          These terms and all matters arising from access to UEHIS shall be governed by and construed in accordance with the laws of India, with exclusive jurisdiction resting in the courts of Pune, Maharashtra.
        </p>
      )
    },
    {
      id: 'sec-16',
      num: '16',
      title: 'Modifications to Terms & Institutional Inquiries',
      content: (
        <p className={styles.clauseText}>
          We reserve the right to amend these Terms as new versions of the computational models are published. Questions regarding licensing or municipal deployment should be directed to <code>legal@seer-bharat.org</code>.
        </p>
      )
    }
  ];

  return (
    <div className={styles.container}>
      {/* Breadcrumb Strip */}
      <section className={styles.breadcrumbStrip}>
        <div className={styles.breadcrumbInner}>
          <div>
            <span>GOVERNANCE</span>
            <span> / </span>
            <span>LEGAL SPECIFICATION</span>
            <span> / </span>
            <strong style={{ color: 'var(--primary)' }}>TERMS-2024-V2.4</strong>
          </div>
          <div>
            <span style={{ color: 'var(--on-surface-variant)' }}>STATUS: OFFICIAL OPERATIONAL SPEC</span>
          </div>
        </div>
      </section>

      {/* Hero */}
      <section className={styles.heroSection}>
        <div className={styles.heroInner}>
          <div className={styles.tagRow}>
            <span className={styles.tagPrimary}>LEGAL FRAMEWORK · TERMS OF USE</span>
            <span className={styles.tagMuted}>PUNE EXTENT · 5,309 CELLS</span>
            <span className={styles.tagMuted}>ORTHOGONAL 250M × 250M</span>
          </div>

          <h1 className={styles.heroTitle}>Terms &amp; Conditions</h1>
          <p className={styles.heroSubtitle}>
            Terms governing access to, operational manipulation of, and institutional citations derived from the Urban Ecosystem Health Intelligence System (UEHIS) platform and its analytical outputs across Pune.
          </p>

          <div className={styles.metaBar}>
            <div className={styles.metaItems}>
              <span><strong>EFFECTIVE:</strong> 2024 BASELINE</span>
              <span>·</span>
              <span><strong>VERSION:</strong> 2.4-STABLE</span>
              <span>·</span>
              <span><strong>REPOSITORY:</strong> SEER BHARAT FOUNDATION</span>
              <span>·</span>
              <span><strong>CRS:</strong> EPSG:32643 (UTM 43N)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span className="material-symbols-outlined" style={{ fontSize: '15px' }}>verified_user</span>
              <span>SYSTEMIC AUDIT LEVEL 3</span>
            </div>
          </div>

          <div className={styles.advisoryBanner}>
            <span className={`material-symbols-outlined ${styles.advisoryIcon}`}>warning</span>
            <div>
              <span className={styles.advisoryTitle}>Institutional Advisory &amp; Operational Status</span>
              <p className={styles.advisoryText}>
                This document serves as an operational specification and term sheet for research and planning use. All critical decisions involving capital deployment, municipal zoning, or infrastructure projects require independent on-site ground truth validation.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 2 Column Layout */}
      <div className={styles.contentArea}>
        <div className={styles.contentInner}>
          <aside className={styles.sidebar}>
            <div className={styles.indexCard}>
              <div className={styles.indexHeader}>
                <span className={styles.indexTitle}>Manifest Index</span>
                <span className={styles.indexCount}>16 CLAUSES</span>
              </div>

              <nav className={styles.indexList}>
                {clauses.map(c => (
                  <a key={c.id} href={`#${c.id}`} className={styles.indexItem}>
                    <span>{c.num} {c.title}</span>
                    <span style={{ fontSize: '10px', color: 'var(--outline)' }}>#{c.num}</span>
                  </a>
                ))}
              </nav>
            </div>
          </aside>

          <main className={styles.clausesContainer}>
            {clauses.map(c => (
              <section key={c.id} id={c.id} className={styles.clauseCard}>
                <div className={styles.clauseHeader}>
                  <span className={styles.clauseNum}>{c.num}</span>
                  <h2 className={styles.clauseTitle}>{c.title}</h2>
                </div>
                {c.content}
              </section>
            ))}
          </main>
        </div>
      </div>
    </div>
  );
}
