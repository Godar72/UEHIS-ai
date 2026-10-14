'use client';

import React from 'react';
import styles from './privacy.module.css';

export default function PrivacyPage() {
  const sections = [
    {
      id: 'sec-01',
      num: '01',
      title: 'Scope of Governance',
      content: (
        <>
          <p className={styles.clauseBody}>
            This Privacy Policy defines the statutory and technical data governance protocols governing the <strong>Urban Ecosystem Health Intelligence System (UEHIS)</strong> web platform, analytical spatial workspace, and geocoding interfaces. These systems are jointly engineered and maintained in institutional research partnership with the <strong>SEER Bharat Foundation</strong>.
          </p>
          <p className={styles.clauseBody}>
            The platform serves municipal planners, ecological researchers, institutional analysts, and the public within the municipal and peri-urban extent of Pune (UTM Zone 43N / EPSG:32643).
          </p>
        </>
      )
    },
    {
      id: 'sec-02',
      num: '02',
      title: 'Information We May Process',
      content: (
        <>
          <p className={styles.clauseBody}>
            In conformity with computational data minimization principles, UEHIS captures only data essential for geospatial calculations, spatial raster/vector rendering, and system uptime diagnostics.
          </p>
          <div className={styles.subSection}>
            <div className={styles.subHeader}>
              <span className={styles.subBadge}>SUBSECTION A</span>
              <h3 className={styles.subTitle}>Account Information (Authentication)</h3>
            </div>
            <p className={styles.clauseBody}>
              Account creation is required solely for persistent workspace preferences, policy export configurations, and institutional administrative capabilities. If an account is provisioned:
            </p>
            <ul className={styles.bulletList}>
              <li><strong>Email Address:</strong> Used strictly as the primary login identifier and for platform security notices.</li>
              <li><strong>Authentication Credentials:</strong> Passwords are cryptographically salted and hashed using bcrypt before storage.</li>
              <li><strong>Role-Based Access:</strong> Institutional role attributes (e.g., researcher, municipal analyst, admin) to govern tier authorization.</li>
            </ul>
          </div>
          <div className={styles.subSection}>
            <div className={styles.subHeader}>
              <span className={styles.subBadge}>SUBSECTION B</span>
              <h3 className={styles.subTitle}>Analytical Workspace &amp; Spatial Queries</h3>
            </div>
            <p className={styles.clauseBody}>
              Ephemeral spatial queries submitted via the Study Area or Coordinate Inspector are processed in-memory. Saved polygons or custom scenario configurations are stored only when explicitly committed by authenticated users.
            </p>
          </div>
        </>
      )
    },
    {
      id: 'sec-03',
      num: '03',
      title: 'Purpose of Processing',
      content: (
        <p className={styles.clauseBody}>
          Data is processed strictly to: (1) Deliver real-time environmental index calculations across Pune&apos;s 5,309 grid blocks; (2) Safeguard API endpoints via IP rate-limiting against denial-of-service disruptions; (3) Facilitate authorized spatial data exports for municipal audits.
        </p>
      )
    },
    {
      id: 'sec-04',
      num: '04',
      title: 'Location Information & Non-Boundary Spatial Scopes',
      content: (
        <p className={styles.clauseBody}>
          UEHIS does <strong>not</strong> track user GPS locations. Geospatial queries involve user-specified study areas or map panning events within the predetermined Pune computational boundary (331.81 km²).
        </p>
      )
    },
    {
      id: 'sec-05',
      num: '05',
      title: 'Third-Party Geospatial & Cloud Services',
      content: (
        <p className={styles.clauseBody}>
          The platform integrates with verified spatial data infrastructure providers including MapTiler/Carto (basemap raster tiles), Supabase (PostGIS database storage), and Earth Observation repositories (Copernicus Sentinel-2, Landsat 8). No personal identifiable information is shared with third-party advertising networks.
        </p>
      )
    },
    {
      id: 'sec-06',
      num: '06',
      title: 'Cookies & Local Browser Storage',
      content: (
        <p className={styles.clauseBody}>
          We utilize essential session cookies strictly to preserve authentication state and local storage keys to cache active basemap preferences and UI layer visibility toggles.
        </p>
      )
    },
    {
      id: 'sec-07',
      num: '07',
      title: 'Data Retention Protocol',
      content: (
        <p className={styles.clauseBody}>
          Diagnostic API access logs and rate-limiting counters are retained on an automated rolling 30-day purge schedule. Authenticated user profile data is retained until account deactivation is requested.
        </p>
      )
    },
    {
      id: 'sec-08',
      num: '08',
      title: 'Data Security Protocol',
      content: (
        <p className={styles.clauseBody}>
          All communications are encrypted in transit via TLS 1.3. Database access relies on strict Row Level Security (RLS) policies preventing cross-tenant data leaks. Server-side credentials and service role keys are strictly segregated from client code.
        </p>
      )
    },
    {
      id: 'sec-09',
      num: '09',
      title: 'User Rights & Data Corrections',
      content: (
        <p className={styles.clauseBody}>
          Users have the right to inspect, export, or request deletion of their authenticated profile information at any time via the Account control portal.
        </p>
      )
    },
    {
      id: 'sec-10',
      num: '10',
      title: "Children's Privacy Protection",
      content: (
        <p className={styles.clauseBody}>
          UEHIS is an academic and municipal environmental intelligence tool and does not knowingly collect personal information from individuals under 18 years of age.
        </p>
      )
    },
    {
      id: 'sec-11',
      num: '11',
      title: 'Policy Amendments',
      content: (
        <p className={styles.clauseBody}>
          Amendments reflecting municipal regulatory updates or scientific pipeline upgrades will be posted with updated revision numbers and timestamp headers.
        </p>
      )
    },
    {
      id: 'sec-12',
      num: '12',
      title: 'Contact Authority',
      content: (
        <p className={styles.clauseBody}>
          For governance inquiries or data protection notices, contact the SEER Bharat Foundation Data Governance Office at <code>governance@seer-bharat.org</code>.
        </p>
      )
    }
  ];

  return (
    <div className={styles.container}>
      {/* Hero */}
      <section className={styles.heroSection}>
        <div className={styles.heroInner}>
          <div className={styles.badgeRow}>
            <span className={styles.badgePrimary}>DATA GOVERNANCE · PRIVACY FRAMEWORK</span>
            <span className={styles.badgeMuted}>REF: UEHIS-POL-SEC-2024-V2.4</span>
            <span className={styles.badgeGreen}>STRICT COMPUTATIONAL SCOPE</span>
          </div>

          <h1 className={styles.heroTitle}>Privacy Policy</h1>
          <p className={styles.heroSubtitle}>
            How the Urban Ecosystem Health Intelligence System (UEHIS) handles information associated with platform metrics, spatial queries, and environmental cartographic exploration across Pune.
          </p>

          <div className={styles.telemetryBar}>
            <div className={styles.telemetryItems}>
              <span>STATUS: <strong style={{ color: 'var(--primary)' }}>OPERATIONAL BASELINE</strong></span>
              <span>·</span>
              <span>DATA CONTROLLER: <strong style={{ color: 'var(--primary)' }}>SEER Bharat Foundation</strong></span>
              <span>·</span>
              <span>EXTENT: PUNE (EPSG:32643)</span>
            </div>
            <span>PROTOCOL: SEC-EO-SYS-43N</span>
          </div>

          <div className={styles.advisoryBox}>
            <span className="material-symbols-outlined" style={{ color: 'var(--tertiary-container)', fontSize: '20px' }}>
              policy
            </span>
            <div>
              <span className={styles.advisoryTitle}>Institutional Governance Notice</span>
              <p className={styles.advisoryText}>
                This policy reflects the operational data pipeline of the UEHIS platform. All spatial metrics adhere to verified institutional and statutory municipal environmental standards.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Two Column Layout */}
      <div className={styles.layout}>
        <aside className={styles.sidebar}>
          <div className={styles.navCard}>
            <div className={styles.navHeader}>
              <span className={styles.navTitle}>Table of Contents</span>
              <span style={{ fontSize: '0.625rem', fontFamily: 'var(--font-ibm-plex-mono)', color: 'var(--on-surface-variant)' }}>
                12 SECTIONS
              </span>
            </div>

            <nav className={styles.navList}>
              {sections.map(s => (
                <a key={s.id} href={`#${s.id}`} className={styles.navItem}>
                  <span>{s.num} {s.title}</span>
                  <span style={{ opacity: 0.4 }}>›</span>
                </a>
              ))}
            </nav>
          </div>

          <div className={styles.ruleBox}>
            <span className={styles.ruleTitle}>GIS Integrity Rule</span>
            <p className={styles.ruleText}>
              Intersections query static 250m vector envelopes. No persistent GPS track points are registered or stored.
            </p>
          </div>
        </aside>

        <main className={styles.clausesList}>
          {sections.map(s => (
            <section key={s.id} id={s.id} className={styles.clauseCard}>
              <div className={styles.clauseHeader}>
                <span className={styles.clauseNum}>{s.num}</span>
                <h2 className={styles.clauseTitle}>{s.title}</h2>
              </div>
              {s.content}
            </section>
          ))}
        </main>
      </div>
    </div>
  );
}
