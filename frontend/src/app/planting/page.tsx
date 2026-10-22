'use client';

import React, { useState, useEffect, useCallback, useMemo, Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { motion } from 'framer-motion';
import circle from '@turf/circle';
import { MapView } from '@/components/Map';
import { PlantingDetail, PlantingUnitProps } from '@/components/PlantingDetail/PlantingDetail';
import { Search } from '@/components/Sidebar/Search';
import styles from './planting.module.css';
import { uehisClient } from '@/lib/api/client';
import { recordActivity } from '@/lib/api/activity';
import { createClient } from '@/lib/supabase/client';

interface ScenarioItem {
  id: string;
  scenario_id: string;
  name: string;
  total_selected?: number;
}

interface FilteredSummary {
  total_units: number;
  mean_uehi: number | null;
}

interface FilteredData {
  geojson: GeoJSON.FeatureCollection | null;
  summary: FilteredSummary;
}

const INITIAL_CENTER: [number, number] = [73.8586, 18.5500];

function PlantingPageContent() {
  const [authStatus, setAuthStatus] = useState<'loading' | 'authorized' | 'denied'>('loading');
  const router = useRouter();
  const searchParams = useSearchParams();

  const [scenarios, setScenarios] = useState<ScenarioItem[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string | null>(null);
  
  const [selectedUnit, setSelectedUnit] = useState<PlantingUnitProps | null>(null);

  const [studyAreaGeometry, setStudyAreaGeometry] = useState<GeoJSON.Geometry | GeoJSON.Feature | GeoJSON.FeatureCollection | null>(null);
  const [filteredData, setFilteredData] = useState<FilteredData | null>(null);
  const [isFiltering, setIsFiltering] = useState(false);
  const [searchResult, setSearchResult] = useState<{ lat: number; lng: number; name: string; type: string; inCoverage?: boolean } | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function checkAuthAndLoad() {
      try {
        const supabase = createClient();
        const { data: { user } } = await supabase.auth.getUser();

        if (!user) {
          if (isMounted) {
            setAuthStatus('denied');
            router.replace('/login?next=/planting');
          }
          return;
        }

        const { data: role, error: roleError } = await supabase.rpc('get_my_role');
        if (roleError || !['admin', 'researcher'].includes(role)) {
          if (isMounted) {
            setAuthStatus('denied');
          }
          return;
        }

        if (!isMounted) return;
        setAuthStatus('authorized');

        // Only after authorization is confirmed, load scenarios
        const data = await uehisClient.planting.getScenarios();
        const resp = data as { scenarios?: ScenarioItem[] };
        const filtered = resp?.scenarios ? resp.scenarios.filter((s: ScenarioItem) => 
          ['100k', '250k', '500k'].includes(s.id)
        ) : [];
        if (isMounted) {
          setScenarios(filtered);
          if (filtered.length > 0) {
            const s100k = filtered.find((s: ScenarioItem) => s.id === '100k');
            setSelectedScenarioId(s100k ? s100k.scenario_id : filtered[0].scenario_id);
          }
        }
      } catch (err) {
        console.error('Failed to verify planting authorization:', err);
        if (isMounted) {
          setAuthStatus('denied');
        }
      }
    }

    checkAuthAndLoad();

    return () => {
      isMounted = false;
    };
  }, [router]);

  const selectedScenarioData = useMemo(() => {
    if (!selectedScenarioId || scenarios.length === 0) return null;
    return scenarios.find(s => s.scenario_id === selectedScenarioId) || null;
  }, [scenarios, selectedScenarioId]);

  // Synchronize from URL search parameters (e.g. redirected from /explore candidate block click)
  useEffect(() => {
    const latParam = searchParams.get('lat');
    const lngParam = searchParams.get('lng');
    const nameParam = searchParams.get('name');
    const radiusParam = searchParams.get('radius');

    if (latParam && lngParam && authStatus === 'authorized') {
      const lat = parseFloat(latParam);
      const lng = parseFloat(lngParam);
      const name = nameParam || 'Searched Extent';
      const radius = radiusParam ? parseInt(radiusParam, 10) : 2000;

      const loc = { lat, lng, name, type: 'Locality', inCoverage: true };
      const circleGeom = circle([lng, lat], radius / 1000, { units: 'kilometers' }).geometry;

      queueMicrotask(() => {
        setSearchResult(loc);
        setStudyAreaGeometry(circleGeom);
        if (selectedScenarioId) {
          setIsFiltering(true);
          uehisClient.planting.filterUnits(selectedScenarioId, circleGeom)
            .then(data => setFilteredData(data as FilteredData))
            .catch(err => {
              console.error('Failed to filter units from URL params:', err);
              setFilteredData(null);
            })
            .finally(() => setIsFiltering(false));
        }
      });
    }
  }, [searchParams, selectedScenarioId, authStatus]);

  const handlePlantingUnitClick = useCallback(async (unit: PlantingUnitProps) => {
    setSelectedUnit({
      ...unit,
      loading: true,
      error: null
    });

    const lookupId = unit.unitUuid || unit.id;
    if (lookupId && lookupId !== 'Unknown') {
      try {
        const detail = await uehisClient.planting.getUnitDetail(lookupId);
        if (detail && detail.properties) {
          const p = detail.properties;
          let oppClass = p.opportunity_class || p.candidate_class || null;
          if (oppClass && typeof oppClass === 'string') {
            if (oppClass.includes('public_like')) oppClass = 'Public-like open space';
            else if (oppClass.includes('context_dependent')) oppClass = 'Context-dependent';
            else if (oppClass.includes('other_open_space')) oppClass = 'Other open space';
          }

          recordActivity({
            activity_type: 'viewed_planting_opportunity',
            category: 'planting',
            action_type: 'viewed',
            title: `Inspected Planting Unit ${lookupId}`,
            description: `Opportunity Class: ${oppClass ?? 'Open space'} · Parent Block: ${p.parent_block_id ?? 'N/A'}`,
            entity_type: 'planting_unit',
            entity_id: lookupId,
            metadata: {
              unit_id: lookupId,
              opportunity_class: oppClass ?? undefined,
              parent_block_id: p.parent_block_id,
              reopen_url: '/planting',
            },
          });

          setSelectedUnit(prev => {
            if (!prev) return null;
            const currentId = prev.unitUuid || prev.id;
            const resId = detail.unit_id || p.planting_unit_id;
            if (currentId && resId && currentId !== resId && currentId !== p.planting_unit_id) {
              return prev;
            }

            return {
              ...prev,
              id: p.planting_unit_id || detail.unit_id || prev.id,
              unitUuid: detail.unit_id,
              parentBlockId: p.parent_block_id ?? prev.parentBlockId,
              opportunityClass: oppClass ?? 'Not available',
              uehi: p.uehi_score !== undefined && p.uehi_score !== null ? Number(p.uehi_score) : null,
              riskLevel: p.risk_level ?? null,
              waterDistance: p.distance_to_water_m !== undefined && p.distance_to_water_m !== null
                ? Math.round(Number(p.distance_to_water_m) * 10) / 10 
                : null,
              ownershipStatus: p.ownership_status ?? 'Verification required',
              utilityStatus: p.utility_status ?? 'Verification required',
              permissionStatus: p.planting_permission_status ?? 'Verification required',
              carbonAssumption: p.scenario_carbon_per_mature_tree ? `${p.scenario_carbon_per_mature_tree} t CO₂e/tree` : (prev.carbonAssumption || '0.5 t CO₂e/tree'),
              loading: false,
              error: null
            };
          });
        }
      } catch (err: unknown) {
        console.error('Failed to fetch planting unit detail:', err);
        const errMessage = err instanceof Error ? err.message : 'Authentication required to inspect unit records';
        setSelectedUnit(prev => {
          if (!prev) return null;
          return {
            ...prev,
            loading: false,
            error: errMessage
          };
        });
      }
    } else {
      setSelectedUnit(prev => prev ? { ...prev, loading: false } : null);
    }
  }, []);

  const handleCloseDetail = useCallback(() => {
    setSelectedUnit(null);
  }, []);

  const handleAnalyzeStudyArea = useCallback(async (geometry: GeoJSON.Geometry | GeoJSON.Feature) => {
    if (!selectedScenarioId) return;
    setStudyAreaGeometry(geometry);
    setIsFiltering(true);
    try {
      const data = await uehisClient.planting.filterUnits(selectedScenarioId, geometry);
      setFilteredData(data as FilteredData);
    } catch (err) {
      console.error(err);
      setFilteredData(null);
    } finally {
      setIsFiltering(false);
    }
  }, [selectedScenarioId]);

  const handleLocationSelect = useCallback(async (location: { lat: number; lng: number; name: string; type: string; inCoverage?: boolean }) => {
    setSelectedUnit(null);
    setSearchResult(location);

    if (selectedScenarioId) {
      const radiusMeters = 2000;
      const circleGeom = circle([location.lng, location.lat], radiusMeters / 1000, { units: 'kilometers' }).geometry;
      setStudyAreaGeometry(circleGeom);
      setIsFiltering(true);
      try {
        const data = await uehisClient.planting.filterUnits(selectedScenarioId, circleGeom);
        setFilteredData(data as FilteredData);
        recordActivity({
          activity_type: 'analyzed_study_area',
          category: 'planting',
          action_type: 'analyzed',
          title: `Filtered Planting Units at ${location.name}`,
          description: `Identified candidate units within ${radiusMeters}m radius for scenario ${selectedScenarioId}.`,
          entity_type: 'study_area',
          entity_id: location.name,
          metadata: {
            scenario_id: selectedScenarioId,
            lat: location.lat,
            lng: location.lng,
            radius: radiusMeters,
          },
        });
      } catch (err) {
        console.error('Failed to filter planting units for selected location:', err);
        setFilteredData(null);
      } finally {
        setIsFiltering(false);
      }
    }
  }, [selectedScenarioId]);

  const handleClearArea = useCallback(() => {
    setStudyAreaGeometry(null);
    setFilteredData(null);
    setSearchResult(null);
  }, []);

  const handleBlockClick = useCallback(() => {}, []);

  const plantingConfig = useMemo(() => ({
    showAreas: true,
    showUnits: true,
    scenarioId: selectedScenarioId,
    scenarioName: selectedScenarioData ? selectedScenarioData.name : 'Unknown',
    filteredGeoJson: filteredData ? filteredData.geojson : null
  }), [selectedScenarioId, selectedScenarioData, filteredData]);

  if (authStatus === 'loading') {
    return (
      <div className={styles.authContainer}>
        <div className={styles.authCard}>
          <div className={styles.authKicker}>CREDENTIAL VERIFICATION // PROTOCOL EPSG:32643</div>
          <h2 className={styles.authTitle}>Authenticating Access...</h2>
          <p className={styles.authSubtitle}>
            Verifying institutional researcher or administrator clearance for candidate planting units.
          </p>
        </div>
      </div>
    );
  }

  if (authStatus === 'denied') {
    return (
      <div className={styles.authContainer}>
        <div className={styles.authCard}>
          <div className={styles.authKicker} style={{ color: 'var(--risk-critical)' }}>
            RESTRICTED ACCESS // 403 FORBIDDEN
          </div>
          <h2 className={styles.authTitle}>Institutional Authorization Required</h2>
          <p className={styles.authSubtitle}>
            Detailed candidate planting opportunities and precise spatial coordinates are restricted to authenticated personnel with researcher or administrator privileges.
          </p>
          <div className={styles.authActions}>
            <Link href="/explore" className={styles.authPrimaryBtn}>
              Return to GIS Workspace
            </Link>
            <Link href="/login?next=/planting" className={styles.authSecondaryBtn}>
              Sign In with Authorized Credentials
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* Telemetry Bar */}
      <div className={styles.telemetryBar}>
        <div className={styles.telemetryLeft}>
          <span className={styles.telemetryPulse}></span>
          <span>LAYER: PUNE EPSG:32643 · 250m RESOLUTION</span>
        </div>
        <div className={styles.telemetryRight}>
          <span>MIN SPACING: ≥10m</span>
          <span>|</span>
          <span style={{ color: 'var(--primary)', fontWeight: 600 }}>100K / 250K / 500K SCENARIO MODEL</span>
        </div>
      </div>

      <header className={styles.header} data-testid="planting-header">
        <div className={styles.titleArea}>
          <div className={styles.kicker}>Phase 5 Intervention Modeling</div>
          <h1 className={styles.title}>Candidate Planting Opportunities</h1>
        </div>

        <div className={styles.controlsArea}>
          {/* Location Search Bar in Planting Header */}
          <div style={{ minWidth: '240px', maxWidth: '320px', flex: '1 1 240px' }}>
            <Search
              placeholder="Search locality in Pune to filter units..."
              onLocationSelect={handleLocationSelect}
            />
          </div>

          <div className={styles.scenarioSelector}>
            <label className={styles.selectLabel}>Scenario Scale</label>
            <select 
              className={styles.select}
              value={selectedScenarioId || ''} 
              onChange={e => {
                setSelectedScenarioId(e.target.value);
                setSelectedUnit(null);
                setFilteredData(null);
              }}
            >
              {scenarios.map(s => {
                const label = s.total_selected 
                  ? `${s.name} (${s.total_selected.toLocaleString()} units)`
                  : s.name;
                return (
                  <option key={s.id} value={s.scenario_id}>{label}</option>
                );
              })}
            </select>
          </div>

          {selectedScenarioData && !filteredData && (
            <motion.div 
              className={styles.metrics}
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              key={selectedScenarioId}
            >
              <div className={styles.metric}>
                <span className={styles.metricLabel}>Total Target Units</span>
                <span className={styles.metricVal}>{(selectedScenarioData.total_selected ?? 0).toLocaleString()}</span>
              </div>
              <div className={styles.metric}>
                <span className={styles.metricLabel}>Mature Carbon Potential</span>
                <span className={styles.metricVal}>{((selectedScenarioData.total_selected ?? 0) * 0.5).toLocaleString()} t CO₂e</span>
              </div>
              <div className={styles.spacingBadge}>
                <span className="material-symbols-outlined" style={{ fontSize: '14px', color: 'var(--secondary)' }}>straighten</span>
                <span>Spacing Constraint: ≥10m Unit Center</span>
              </div>
            </motion.div>
          )}

          {filteredData && (
            <motion.div 
              className={styles.metrics}
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              key="filtered"
            >
              <div className={styles.metric}>
                <span className={styles.metricLabel}>Units in Envelope</span>
                <span className={styles.metricVal}>
                  {isFiltering ? '...' : filteredData.summary.total_units.toLocaleString()}
                </span>
              </div>
              <div className={styles.metric}>
                <span className={styles.metricLabel}>Mean UEHI</span>
                <span className={styles.metricVal}>
                  {isFiltering ? '...' : (filteredData.summary.mean_uehi !== null ? filteredData.summary.mean_uehi.toFixed(2) : 'N/A')}
                </span>
              </div>
              <div className={styles.metric}>
                <span className={styles.metricLabel}>Est. Carbon</span>
                <span className={styles.metricVal}>
                  {isFiltering ? '...' : (filteredData.summary.total_units * 0.5).toLocaleString()} t CO₂e</span>
              </div>
              <button 
                onClick={handleClearArea}
                className={styles.clearAreaBtn}
              >
                Clear Selection
              </button>
            </motion.div>
          )}
        </div>
      </header>

      <div className={styles.mapLayout}>
        <div className={styles.mapWrapper}>
          <MapView 
            onBlockClick={handleBlockClick}
            onPlantingUnitClick={handlePlantingUnitClick}
            studyAreaGeometry={studyAreaGeometry}
            onAnalyzeStudyArea={handleAnalyzeStudyArea}
            searchResult={searchResult}
            plantingConfig={plantingConfig}
            selectedUnitId={selectedUnit?.id || null}
            showUehi={false}
            initialZoom={searchResult ? 14 : 15}
            initialCenter={searchResult ? [searchResult.lng, searchResult.lat] : INITIAL_CENTER}
          />
        </div>
        
        <PlantingDetail 
          unit={selectedUnit}
          onClose={handleCloseDetail}
        />
      </div>
    </div>
  );
}

export default function PlantingPage() {
  return (
    <Suspense fallback={
      <div style={{ padding: '32px', fontFamily: 'var(--font-jetbrains-mono)', color: 'var(--primary)' }}>
        Authenticating and loading planting intervention model...
      </div>
    }>
      <PlantingPageContent />
    </Suspense>
  );
}
