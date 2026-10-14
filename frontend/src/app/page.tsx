'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { uehisClient } from '@/lib/api/client';
import styles from './page.module.css';

interface ProductionSummary {
  uehi?: {
    mean_score?: number;
    total_blocks?: number;
    scored_blocks?: number;
  };
  carbon?: {
    total_carbon?: number;
  };
}

const SUPPORTED_RADII = [
  { label: '500m', value: 500 },
  { label: '1km', value: 1000 },
  { label: '2km', value: 2000 },
  { label: '5km', value: 5000 },
];

export default function Home() {
  const router = useRouter();
  const [summary, setSummary] = useState<ProductionSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('Baner, Pune');
  const [selectedRadius, setSelectedRadius] = useState<number>(2000); // 2km default
  const [isSearching, setIsSearching] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userRole, setUserRole] = useState<string | null>(null);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getSession().then(({ data: { session } }) => {
      setIsAuthenticated(!!session?.user);
      if (session?.user) {
        supabase.rpc('get_my_role').then(({ data }) => setUserRole(data || 'public'));
      }
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setIsAuthenticated(!!session?.user);
      if (session?.user) {
        supabase.rpc('get_my_role').then(({ data }) => setUserRole(data || 'public'));
      } else {
        setUserRole(null);
      }
    });

    uehisClient.system.getSummary()
      .then(data => {
        setSummary(data as ProductionSummary);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load summary', err);
        setLoading(false);
      });

    return () => subscription.unsubscribe();
  }, []);

  const handleAnalyzeLocation = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const query = searchQuery.trim();
    if (!query) {
      router.push(`/explore?action=study_area&radius=${selectedRadius}`);
      return;
    }

    setIsSearching(true);
    try {
      const res = await fetch(`/api/geocode?q=${encodeURIComponent(query)}`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          const loc = data[0];
          router.push(
            `/explore?lat=${loc.latitude}&lng=${loc.longitude}&radius=${selectedRadius}&name=${encodeURIComponent(loc.name || query)}`
          );
          return;
        }
      }
    } catch (err) {
      console.warn('Geocode lookup notice:', err);
    } finally {
      setIsSearching(false);
    }

    // Fallback if geocode is empty or network fails
    router.push(`/explore?name=${encodeURIComponent(query)}&radius=${selectedRadius}`);
  };

  const handleExploreGis = () => {
    router.push('/explore');
  };

  const isAuthorizedForPlanting = userRole === 'researcher' || userRole === 'admin';

  return (
    <div className={styles.container}>
      <main className={styles.main}>
        
        {/* SECTION 1: UEHIS IDENTITY & INTRO */}
        <section className={styles.heroSection}>
          <div className={styles.heroGrid}>
            <div className={styles.heroLeft}>
              <div className={styles.stamp}>
                <span className={styles.stampDot}></span>
                <span>SEER BHARAT FOUNDATION · PUNE ENVIRONMENTAL ATLAS</span>
              </div>

              <div className={styles.titleArea}>
                <h1 className={styles.heroTitle}>
                  Urban Ecosystem Health Intelligence System (UEHIS)
                </h1>
                <p className={styles.heroSubtitle}>
                  Spatial intelligence for understanding urban ecosystem health, canopy infrastructure, thermal exposure, and ecological vulnerability across Pune.
                </p>
              </div>

              {/* SECTION 2: PROMINENT LOCALITY SEARCH WIDGET */}
              <form className={styles.localityWidget} onSubmit={handleAnalyzeLocation}>
                <div className={styles.localityHeader}>
                  <label className={styles.localityLabel} htmlFor="locality-input">
                    <span className="material-symbols-outlined" style={{ fontSize: '15px', color: 'var(--primary)' }}>search</span>
                    <span>Search Locality or Landmark</span>
                  </label>
                  <span className={styles.localityTag}>GEOAPIFY ENGINE</span>
                </div>

                <div className={styles.searchBarWrapper}>
                  <span className={`material-symbols-outlined ${styles.searchIcon}`}>search</span>
                  <input
                    id="locality-input"
                    className={styles.localityInput}
                    placeholder="Search Pune locality, road or landmark... (e.g. Baner, Kothrud, FC Road, Aundh)"
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                  {searchQuery && (
                    <button
                      type="button"
                      className={styles.clearQueryBtn}
                      onClick={() => setSearchQuery('')}
                      aria-label="Clear query"
                    >
                      <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>close</span>
                    </button>
                  )}
                </div>

                {/* Radii Segmented Buttons (Stitch Spec) */}
                <div className={styles.radiiRow}>
                  <span className={styles.radiiLabel}>Radii:</span>
                  <div className={styles.radiiButtonGroup}>
                    {SUPPORTED_RADII.map((r) => (
                      <button
                        key={r.value}
                        type="button"
                        className={`${styles.radiusBtn} ${selectedRadius === r.value ? styles.radiusBtnActive : ''}`}
                        onClick={() => setSelectedRadius(r.value)}
                      >
                        {r.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div className={styles.localityNotice}>
                  <span className={`material-symbols-outlined ${styles.localityNoticeIcon}`}>info</span>
                  <span>
                    Powered by Geoapify. Point-radius study area (500m, 1km, 2km, 5km) — Not an official administrative boundary.
                  </span>
                </div>

                {/* Dual Action Grid (Stitch Spec) */}
                <div className={styles.actionsGrid}>
                  <button
                    type="button"
                    onClick={handleExploreGis}
                    className={styles.primaryExploreBtn}
                  >
                    <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>map</span>
                    <span>Explore Pune GIS</span>
                  </button>

                  <button
                    type="submit"
                    className={styles.secondaryAnalyzeBtn}
                    disabled={isSearching}
                  >
                    <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>location_searching</span>
                    <span>{isSearching ? 'Resolving...' : 'Analyze a Location'}</span>
                  </button>
                </div>
              </form>

              {/* Telemetry Summary Panel */}
              <div className={styles.telemetryPanel}>
                <div className={styles.telemetryGrid}>
                  <div className={styles.telemetryItem}>
                    <span className={styles.telemetryLabel}>Study Extent</span>
                    <span className={styles.telemetryValue}>331.81 km²</span>
                  </div>
                  <div className={styles.telemetryItem}>
                    <span className={styles.telemetryLabel}>Urban Canopy</span>
                    <span className={`${styles.telemetryValue} ${styles.telemetryValueGreen}`}>21.51 km² (6.48%)</span>
                  </div>
                  <div className={styles.telemetryItem}>
                    <span className={styles.telemetryLabel}>Mean UEHI</span>
                    <span className={`${styles.telemetryValue} ${styles.telemetryValueOrange}`}>
                      {loading ? '20.21' : summary?.uehi?.mean_score ? summary.uehi.mean_score.toFixed(2) : '20.21'} / 100
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* SECTION 3: PUNE CARTOGRAPHIC BASELINE MAP (Responsive) */}
            <div className={styles.cartoCanvas}>
              {/* Map Header HUD */}
              <div className={styles.cartoBar}>
                <div className={styles.cartoBarGroup}>
                  <span className="material-symbols-outlined" style={{ fontSize: '14px', color: 'var(--secondary)' }}>grid_4x4</span>
                  <span className={styles.cartoPillActive}>250m Orthogonal Cells · EPSG:32643</span>
                </div>
                <div className={styles.cartoBarGroup}>
                  <span className={styles.livePulse}></span>
                  <span className={styles.cartoPill}>SYNCHRONIZED</span>
                </div>
              </div>

              {/* Cartographic Visual Container */}
              <div className={styles.cartoImageWrapper}>
                <Image
                  src="/pune_study_area_map.png"
                  alt="Cartographic study area map of Pune showing 250m grid extent"
                  fill
                  className={styles.cartoImage}
                  priority
                  sizes="(max-width: 1024px) 100vw, 50vw"
                />
                <div className={styles.cartoOverlayBadge}>
                  AUTHORITATIVE BASELINE CARTOGRAPHY
                </div>
              </div>

              {/* Carto Bottom Bar with Legend */}
              <div className={styles.cartoFooter}>
                <div className={styles.legendGroup}>
                  <span className={styles.legendTitle}>Risk Category:</span>
                  <div className={styles.legendItems}>
                    <span className={styles.legendDot} style={{ backgroundColor: 'var(--risk-critical)' }}></span>
                    <span className={styles.legendText}>Critical</span>
                    <span className={styles.legendDot} style={{ backgroundColor: 'var(--risk-high)' }}></span>
                    <span className={styles.legendText}>High</span>
                    <span className={styles.legendDot} style={{ backgroundColor: 'var(--risk-moderate)' }}></span>
                    <span className={styles.legendText}>Moderate</span>
                    <span className={styles.legendDot} style={{ backgroundColor: 'var(--risk-low)' }}></span>
                    <span className={styles.legendText}>Low</span>
                  </div>
                </div>
                <div className={styles.cartoFooterNote}>
                  PUNE 250M GRID · EPSG:32643
                </div>
              </div>
            </div>

          </div>
        </section>

        {/* SECTION 4: PRODUCTION METRICS EVIDENCE BASE */}
        <section className={styles.metadataStrip}>
          <div className={styles.metadataGrid}>
            <div className={styles.metadataItem}>
              <span className={styles.metadataLabel}>Total Spatial Blocks</span>
              <span className={styles.metadataValue}>
                {loading ? '5,309' : summary?.uehi?.total_blocks?.toLocaleString() || '5,309'}
              </span>
            </div>
            <div className={styles.metadataItem}>
              <span className={styles.metadataLabel}>Scorable Blocks</span>
              <span className={`${styles.metadataValue} ${styles.metadataValueGreen}`}>
                {loading ? '5,298' : summary?.uehi?.scored_blocks?.toLocaleString() || '5,298'}
              </span>
            </div>
            <div className={styles.metadataItem}>
              <span className={styles.metadataLabel}>Excluded Perimeter</span>
              <span className={`${styles.metadataValue} ${styles.metadataValueOutline}`}>
                11 Blocks
              </span>
            </div>
            <div className={styles.metadataItem}>
              <span className={styles.metadataLabel}>Standing Carbon</span>
              <span className={`${styles.metadataValue} ${styles.metadataValueGreen}`}>
                {loading ? '493,093.69 t' : summary?.carbon?.total_carbon ? `${summary.carbon.total_carbon.toLocaleString(undefined, { maximumFractionDigits: 1 })} t` : '493,093.69 t'}
              </span>
            </div>
            <div className={styles.metadataItem}>
              <span className={styles.metadataLabel}>Cartographic CRS</span>
              <span className={styles.metadataValue}>EPSG:32643 UTM 43N</span>
            </div>
          </div>
        </section>

        {/* SECTION 5: ANALYTICAL WORKSTATION MODULES (Cards 01 to 04 from Stitch) */}
        <section className={styles.modulesSection}>
          <div className={styles.modulesHeader}>
            <span className={styles.sectionKicker}>ANALYTICAL WORKBENCH</span>
            <h2 className={styles.sectionTitle}>Modular Scientific Capabilities</h2>
          </div>

          <div className={styles.modulesGrid}>
            {/* 01: GIS Spatial Workspace */}
            <div className={styles.moduleCard}>
              <div className={styles.moduleCardTop}>
                <span className={styles.moduleNumber}>01</span>
                <span className={styles.moduleTag}>GEOSPATIAL</span>
              </div>
              <h3 className={styles.moduleTitle}>GIS Spatial Workspace</h3>
              <p className={styles.moduleDesc}>
                Interactive 250m orthogonal grid cartography. Inspect biophysical parameters, canopy masks, and thermal exposure across Pune.
              </p>
              <Link href="/explore" className={styles.moduleActionBtn}>
                <span>Launch GIS Workspace</span>
                <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>arrow_forward</span>
              </Link>
            </div>

            {/* 02: Terrestrial Carbon Stock */}
            <div className={styles.moduleCard}>
              <div className={styles.moduleCardTop}>
                <span className={styles.moduleNumber}>02</span>
                <span className={styles.moduleTag}>REGISTRY</span>
              </div>
              <h3 className={styles.moduleTitle}>Terrestrial Carbon Stock</h3>
              <p className={styles.moduleDesc}>
                Biomass allometry and standing terrestrial carbon registry across 5,309 blocks calibrated to 2024 satellite baselines.
              </p>
              <Link href="/carbon" className={styles.moduleActionBtn}>
                <span>View Carbon Stock Registry</span>
                <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>arrow_forward</span>
              </Link>
            </div>

            {/* 03: Planting Opportunities (Authorized researcher/admin) */}
            <div className={styles.moduleCard}>
              <div className={styles.moduleCardTop}>
                <span className={styles.moduleNumber}>03</span>
                <span className={styles.moduleTag}>REMEDIATION</span>
              </div>
              <h3 className={styles.moduleTitle}>Candidate Planting Opportunities</h3>
              <p className={styles.moduleDesc}>
                Candidate planting allocation algorithm strictly enforcing the 10-metre spacing constraint across eligible unpaved soils.
              </p>
              {isAuthorizedForPlanting ? (
                <Link href="/planting" className={styles.moduleActionBtn}>
                  <span>Access Planting Allocation</span>
                  <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>arrow_forward</span>
                </Link>
              ) : (
                <div className={styles.moduleRestrictedNote}>
                  <span className="material-symbols-outlined" style={{ fontSize: '14px', color: 'var(--outline)' }}>lock</span>
                  <span>Restricted to Authorized Researcher / Admin accounts</span>
                </div>
              )}
            </div>

            {/* 04: Systemic Analytical Scenarios */}
            <div className={styles.moduleCard}>
              <div className={styles.moduleCardTop}>
                <span className={styles.moduleNumber}>04</span>
                <span className={styles.moduleTag}>PROJECTIONS</span>
              </div>
              <h3 className={styles.moduleTitle}>Systemic Intervention Scenarios</h3>
              <p className={styles.moduleDesc}>
                Hypothetical scaling curves modeling incremental canopy and carbon yield under theoretical 100K, 250K, and 500K sapling volumes.
              </p>
              <Link href="/scenarios" className={styles.moduleActionBtn}>
                <span>Inspect Intervention Scenarios</span>
                <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>arrow_forward</span>
              </Link>
            </div>
          </div>
        </section>

        {/* SECTION 6: METHODOLOGICAL ARCHITECTURE */}
        <section className={styles.methodologySection}>
          <div className={styles.methodologyHeader}>
            <span className={styles.sectionKicker}>SCIENTIFIC RIGOUR &amp; PROVENANCE</span>
            <h2 className={styles.sectionTitle}>Methodological Architecture</h2>
          </div>

          <div className={styles.methodologyList}>
            <div className={styles.methodologyItem}>
              <span className={styles.methodologyLetter}>A</span>
              <div>
                <strong>Satellite Data Ingestion:</strong> High-resolution multispectral imagery pipeline calibrated for surface reflectance and thermal radiance.
              </div>
            </div>
            <div className={styles.methodologyItem}>
              <span className={styles.methodologyLetter}>B</span>
              <div>
                <strong>Semantic Segmentation:</strong> Deep architectural partition identifying impervious footprint, tree crown perimeter, and water conduits.
              </div>
            </div>
            <div className={styles.methodologyItem}>
              <span className={styles.methodologyLetter}>C</span>
              <div>
                <strong>Feature Engineering:</strong> Synthesizing biophysical signals across the Pune 250m orthogonal reference coordinate system (EPSG:32643).
              </div>
            </div>
            <div className={styles.methodologyItem}>
              <span className={styles.methodologyLetter}>D</span>
              <div>
                <strong>UEHI Scoring:</strong> Multi-criteria decision formulation weighting ecological deficit against ambient vulnerability.
              </div>
            </div>
            <div className={styles.methodologyItem}>
              <span className={styles.methodologyLetter}>E</span>
              <div>
                <strong>Carbon Estimation:</strong> Allometric biomass equations translated into verified baseline standing mass and simulated planting yields.
              </div>
            </div>
          </div>

          {/* Institutional Partnership Footer Box (Stitch Spec) */}
          <div className={styles.institutionBox}>
            <div className={styles.institutionHeader}>
              <div className={styles.institutionDot}></div>
              <span className={styles.institutionKicker}>INSTITUTIONAL COLLABORATION</span>
            </div>
            <h3 className={styles.institutionTitle}>SEER Bharat Foundation, Pune</h3>
            <p className={styles.institutionDesc}>
              Developed in active partnership with SEER Bharat Foundation to establish an open, authoritative spatial evidence base for ecological remediation, urban forestry planning, and heat vulnerability mitigation across the Pune metropolitan region.
            </p>
            <div className={styles.institutionMeta}>
              <span>PUNE ATLAS · PRODUCTION 2026</span>
              <span>EPSG:32643</span>
            </div>
          </div>
        </section>

      </main>
    </div>
  );
}
