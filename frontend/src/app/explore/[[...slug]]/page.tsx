'use client';

import React, { useState, useEffect, useRef, useCallback, Suspense } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import circle from '@turf/circle';
import { Sidebar } from '@/components/Sidebar/Sidebar';
import { MapView } from '@/components/Map';
import { RightPanel, BlockResponse } from '@/components/RightPanel/RightPanel';

interface ExploreBlockResponse extends BlockResponse {
  ward_name?: string;
}
import { StudyAreaResult, CandidateBlock, StudyAreaData } from '@/components/StudyAreaResult/StudyAreaResult';
import { uehisClient, APIError } from '@/lib/api/client';
import { recordActivity } from '@/lib/api/activity';
import styles from '../page.module.css';

export interface StudyAreaAnalysisResult {
  uehi?: {
    score?: number;
    risk_level?: string;
    total_blocks?: number;
    distribution?: Record<string, number>;
  } | null;
  provenance?: Record<string, unknown>;
  carbon?: {
    total_carbon?: number;
    canopy_density?: number;
    gross_grid_density?: number;
    error?: string;
  } | null;
  candidate_blocks?: CandidateBlock[];
  total_blocks?: number;
}

function ExploreContent() {
  const params = useParams();
  const searchParams = useSearchParams();
  const slug = params.slug as string[] | undefined;
  
  // Block state
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(null);
  const [blockLoading, setBlockLoading] = useState(false);
  const [blockData, setBlockData] = useState<ExploreBlockResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Study Area state
  const [studyAreaActive, setStudyAreaActive] = useState(false);
  const [studyAreaLoading, setStudyAreaLoading] = useState(false);
  const [studyAreaData, setStudyAreaData] = useState<StudyAreaData | null>(null);
  const [studyAreaError, setStudyAreaError] = useState<string | null>(null);
  const [studyAreaGeometry, setStudyAreaGeometry] = useState<GeoJSON.Geometry | GeoJSON.Feature | null>(null);
  const [studyAreaLocationName, setStudyAreaLocationName] = useState('Custom Area');
  const [studyAreaBoundaryType, setStudyAreaBoundaryType] = useState('User polygon');
  const [currentRadius, setCurrentRadius] = useState<number>(2000);

  // Search and mobile interaction state
  const [searchResult, setSearchResult] = useState<{ lat: number; lng: number; name: string; type: string } | null>(null);
  const [isMobileToolsOpen, setIsMobileToolsOpen] = useState(false);
  const [layers, setLayers] = useState({ uehi: false });

  const fetchController = useRef<AbortController | null>(null);
  const activeBlockRef = useRef<string | null>(null);
  const analyzedUrlRef = useRef<string | null>(null);

  // Listen to mobile bottom nav "Study Area" tab action
  useEffect(() => {
    const handleOpenStudyAreaEvent = () => {
      setIsMobileToolsOpen(true);
    };
    window.addEventListener('uehis:open-study-area', handleOpenStudyAreaEvent);
    return () => window.removeEventListener('uehis:open-study-area', handleOpenStudyAreaEvent);
  }, []);

  // Primary Spatial Analysis Execution
  // Primary Block Inspection Execution (hoisted before slug effect)
  const handleBlockClick = useCallback(async (blockId: string) => {
    activeBlockRef.current = blockId;
    setSelectedBlockId(blockId);
    setBlockLoading(true);
    setBlockData(null);
    setError(null);
    setStudyAreaActive(false);
    setIsMobileToolsOpen(false);

    if (typeof window !== 'undefined' && window.location.pathname !== `/explore/block/${blockId}`) {
      window.history.pushState(null, '', `/explore/block/${blockId}`);
    }

    if (fetchController.current) {
      fetchController.current.abort();
    }
    fetchController.current = new AbortController();

    try {
      const data = await uehisClient.blocks.getDetail(blockId, { signal: fetchController.current.signal }) as ExploreBlockResponse;
      // Stale request guard: if another block was clicked while this request was in flight, do not overwrite!
      if (activeBlockRef.current !== blockId) return;

      setBlockData(data);
      recordActivity({
        activity_type: 'viewed_block',
        category: 'explore',
        action_type: 'viewed',
        title: `Examined Ecological Block ${blockId}`,
        description: `UEHI Score: ${data.uehi_score !== null && data.uehi_score !== undefined ? data.uehi_score : 'N/A'} · Risk: ${data.risk_level || 'N/A'}${data.ward_name ? ` · Ward: ${data.ward_name}` : ''}`,
        entity_type: 'block',
        entity_id: blockId,
        metadata: {
          block_id: blockId,
          uehi_score: data.uehi_score,
          risk_level: data.risk_level,
          ward_name: data.ward_name,
          reopen_url: `/explore/block/${blockId}`,
        },
      });
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') return;
      if (activeBlockRef.current !== blockId) return; // Stale error guard

      console.error('Block load error:', err);
      setBlockData(null);
      const apiErr = err as Partial<APIError>;
      if (apiErr?.isNotFound || apiErr?.status === 404) {
        setError(`Block "${blockId}" not found in Pune study area.`);
      } else if (apiErr?.isTimeout || apiErr?.status === 504) {
        setError('Request timed out while loading block analysis.');
      } else if (apiErr?.isNetworkError) {
        setError('Network error. Check connection and retry.');
      } else {
        setError(err instanceof Error ? err.message : 'Block analysis is temporarily unavailable.');
      }
    } finally {
      if (activeBlockRef.current === blockId) {
        setBlockLoading(false);
      }
    }
  }, []);

  // Primary Spatial Analysis Execution
  const handleAnalyzeStudyArea = useCallback(async (
    geometry: GeoJSON.Geometry | GeoJSON.Feature,
    locationName: string,
    boundaryType: string,
    radiusMeters: number = 2000
  ) => {
    setSelectedBlockId(null);
    setStudyAreaActive(true);
    setStudyAreaGeometry(geometry);
    setStudyAreaLocationName(locationName);
    setStudyAreaBoundaryType(boundaryType);
    setCurrentRadius(radiusMeters);
    setStudyAreaLoading(true);
    setStudyAreaError(null);
    setStudyAreaData(null);

    try {
      // Step 1: Calculate UEHI Composite
      const uehiResponse = await uehisClient.studyArea.analyzeUehi(geometry) as StudyAreaAnalysisResult;
      setStudyAreaData({ uehi: uehiResponse.uehi, provenance: uehiResponse.provenance, carbon: null });

      // Record verified research operation
      recordActivity({
        activity_type: 'analyzed_study_area',
        category: 'analysis',
        action_type: 'analyzed',
        title: `Analyzed Study Area: ${locationName || 'Custom Boundary'}`,
        description: `Study area evaluated across ${uehiResponse?.total_blocks || 0} blocks. Mean UEHI: ${uehiResponse?.uehi?.score ?? 'N/A'}`,
        entity_type: 'study_area',
        entity_id: locationName || 'custom_area',
        metadata: {
          location_name: locationName,
          boundary_type: boundaryType,
          total_blocks: uehiResponse?.total_blocks,
          mean_uehi: uehiResponse?.uehi?.score,
          radius: radiusMeters,
        },
      });

      // Step 2: Background Carbon Estimation
      uehisClient.studyArea.analyzeCarbon(geometry).then((carbonResponse: unknown) => {
        const cResp = carbonResponse as { carbon?: StudyAreaAnalysisResult['carbon']; provenance?: Record<string, unknown> };
        setStudyAreaData((prev) => ({
          ...(prev || {}),
          carbon: cResp?.carbon || null,
          provenance: { ...(prev?.provenance || {}), ...(cResp?.provenance || {}) }
        }));
      }).catch(() => {
        setStudyAreaData((prev) => ({
          ...(prev || {}),
          carbon: { error: 'Failed to estimate carbon.' }
        }));
      }).finally(() => {
        setStudyAreaLoading(false);
      });

    } catch (err: unknown) {
      console.error('Study area analysis error:', err);
      const msg = err instanceof Error ? err.message : 'Analysis failed. Please try again.';
      setStudyAreaError(msg);
      setStudyAreaLoading(false);
    }
  }, []);

  // Initialize and synchronize from URL search parameters
  useEffect(() => {
    const latParam = searchParams.get('lat');
    const lngParam = searchParams.get('lng');
    const radiusParam = searchParams.get('radius');
    const nameParam = searchParams.get('name');

    const cacheKey = `${latParam}_${lngParam}_${radiusParam}_${nameParam}`;
    if (!latParam && !lngParam && !nameParam) return;
    if (analyzedUrlRef.current === cacheKey) return;

    const radius = radiusParam ? parseInt(radiusParam, 10) : 2000;

    if (latParam && lngParam) {
      const lat = parseFloat(latParam);
      const lng = parseFloat(lngParam);
      const name = nameParam || 'Custom Study Area';
      analyzedUrlRef.current = cacheKey;

      queueMicrotask(() => {
        setCurrentRadius(radius);
        setSearchResult({ lat, lng, name, type: 'point_radius' });
        const circleGeom = circle([lng, lat], radius / 1000, { units: 'kilometers' }).geometry;
        handleAnalyzeStudyArea(circleGeom, name, 'point_radius', radius);
      });
    } else if (nameParam) {
      // Name provided without coordinates (e.g. from homepage search redirect)
      analyzedUrlRef.current = cacheKey;
      queueMicrotask(() => {
        setCurrentRadius(radius);
        setStudyAreaLoading(true);
        setStudyAreaActive(true);
        setStudyAreaLocationName(nameParam);
      });

      fetch(`/api/geocode?q=${encodeURIComponent(nameParam)}`)
        .then((res) => res.json())
        .then((data: unknown) => {
          if (Array.isArray(data) && data.length > 0) {
            const first = data[0] as { lat: string; lon?: string; lng?: string; display_name?: string };
            const lat = parseFloat(first.lat);
            const lng = parseFloat(first.lon || first.lng || '0');
            const locName = first.display_name?.split(',')[0] || nameParam;
            
            setSearchResult({ lat, lng, name: locName, type: 'point_radius' });
            
            const circleGeom = circle([lng, lat], radius / 1000, { units: 'kilometers' }).geometry;
            handleAnalyzeStudyArea(circleGeom, locName, 'point_radius', radius);

            // Update URL cleanly with geocoded coordinates
            const currentUrl = new URL(window.location.href);
            currentUrl.searchParams.set('lat', lat.toString());
            currentUrl.searchParams.set('lng', lng.toString());
            currentUrl.searchParams.set('radius', radius.toString());
            currentUrl.searchParams.set('name', locName);
            window.history.replaceState(null, '', currentUrl.pathname + currentUrl.search);
          } else {
            setStudyAreaError(`Location "${nameParam}" could not be geocoded within Pune.`);
            setStudyAreaLoading(false);
          }
        })
        .catch((err: unknown) => {
          console.error('Geocoding error:', err);
          setStudyAreaError('Geocoding service unavailable.');
          setStudyAreaLoading(false);
        });
    }
  }, [searchParams, handleAnalyzeStudyArea]);

  // Sync Block Selection from route slug
  useEffect(() => {
    if (slug && slug.length >= 2 && slug[0] === 'block') {
      const urlBlockId = slug[1];
      if (urlBlockId !== selectedBlockId) {
        queueMicrotask(() => {
          handleBlockClick(urlBlockId);
        });
      }
    } else if (!slug || slug[0] !== 'block') {
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/explore/block')) {
        if (selectedBlockId !== null) {
          queueMicrotask(() => {
            activeBlockRef.current = null;
            setSelectedBlockId(null);
            setBlockData(null);
            setError(null);
          });
        }
      }
    }
  }, [slug, selectedBlockId, handleBlockClick]);

  // Synchronize browser history popstate (Back/Forward navigation)
  useEffect(() => {
    const handlePopState = () => {
      const path = window.location.pathname;
      const match = path.match(/\/explore\/block\/([A-Za-z0-9_-]+)/);
      if (match && match[1]) {
        handleBlockClick(match[1]);
      } else if (path === '/explore' || path === '/explore/') {
        activeBlockRef.current = null;
        setSelectedBlockId(null);
        setBlockData(null);
        setError(null);
      }
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [handleBlockClick]);

  const handleClosePanel = useCallback(() => {
    activeBlockRef.current = null;
    setSelectedBlockId(null);
    setBlockData(null);
    setError(null);
    setStudyAreaActive(false);
    if (typeof window !== 'undefined' && window.location.pathname !== '/explore') {
      window.history.pushState(null, '', '/explore');
    }
  }, []);

  const handleLocationSelect = useCallback((location: { lat: number; lng: number; name: string; type: string }) => {
    setSelectedBlockId(null);
    setBlockData(null);
    setError(null);
    setIsMobileToolsOpen(false); // Close mobile drawer so map and results are visible

    setSearchResult(location);
    const radius = currentRadius || 2000;
    const circleGeom = circle([location.lng, location.lat], radius / 1000, { units: 'kilometers' }).geometry;

    handleAnalyzeStudyArea(circleGeom, location.name, 'point_radius', radius);

    // Update URL query parameters
    const currentUrl = new URL(window.location.href);
    currentUrl.searchParams.set('lat', location.lat.toString());
    currentUrl.searchParams.set('lng', location.lng.toString());
    currentUrl.searchParams.set('radius', radius.toString());
    currentUrl.searchParams.set('name', location.name);
    window.history.pushState(null, '', currentUrl.pathname + currentUrl.search);
  }, [currentRadius, handleAnalyzeStudyArea]);

  const handleRadiusChange = useCallback((newRadius: number) => {
    setCurrentRadius(newRadius);
    if (searchResult) {
      const circleGeom = circle([searchResult.lng, searchResult.lat], newRadius / 1000, { units: 'kilometers' }).geometry;
      const currentUrl = new URL(window.location.href);
      currentUrl.searchParams.set('radius', newRadius.toString());
      window.history.replaceState(null, '', currentUrl.pathname + currentUrl.search);
      handleAnalyzeStudyArea(circleGeom, studyAreaLocationName, 'point_radius', newRadius);
    }
  }, [searchResult, studyAreaLocationName, handleAnalyzeStudyArea]);

  const handleRetryAnalysis = useCallback(() => {
    if (studyAreaGeometry) {
      handleAnalyzeStudyArea(studyAreaGeometry, studyAreaLocationName, studyAreaBoundaryType, currentRadius);
    }
  }, [studyAreaGeometry, studyAreaLocationName, studyAreaBoundaryType, currentRadius, handleAnalyzeStudyArea]);

  const handleToggleLayer = useCallback((layer: 'uehi') => {
    setLayers((prev) => ({ ...prev, [layer]: !prev[layer] }));
  }, []);

  return (
    <div className={styles.container}>
      {/* Desktop Sidebar (Left Rail) */}
      <div className={styles.desktopSidebar}>
        <Sidebar
          onAnalyzeStudyArea={handleAnalyzeStudyArea}
          onLocationSelect={handleLocationSelect}
          layers={layers}
          onToggleLayer={handleToggleLayer}
        />
      </div>

      {/* Interactive Map Canvas */}
      <div className={styles.mapWrapper}>
        <MapView
          onBlockClick={handleBlockClick}
          studyAreaGeometry={studyAreaGeometry}
          onAnalyzeStudyArea={handleAnalyzeStudyArea}
          searchResult={searchResult}
          showUehi={layers.uehi}
          selectedBlockId={selectedBlockId}
        />

        {/* Mobile Floating Action Controls */}
        <div className={styles.mobileFloatingBar}>
          <button
            type="button"
            className={styles.mobileToolsBtn}
            onClick={() => setIsMobileToolsOpen(true)}
            aria-label="Open layers and geospatial search tools"
          >
            <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>layers</span>
            <span>Layers &amp; Search</span>
          </button>

          {!studyAreaActive && studyAreaData && (
            <button
              type="button"
              className={styles.reopenResultsBtn}
              onClick={() => {
                setSelectedBlockId(null);
                setStudyAreaActive(true);
              }}
              aria-label="Reopen study area analysis report"
            >
              <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>assessment</span>
              <span>{studyAreaLocationName}</span>
            </button>
          )}
        </div>
      </div>

      {/* Mobile Tools Drawer (Slide-up Sheet) */}
      {isMobileToolsOpen && (
        <>
          <div
            className={styles.mobileDrawerBackdrop}
            onClick={() => setIsMobileToolsOpen(false)}
            aria-hidden="true"
          />
          <aside className={styles.mobileDrawer} role="dialog" aria-label="Geospatial tools and layer stack">
            <div className={styles.drawerHeader}>
              <div className={styles.drawerTitle}>
                <span className="material-symbols-outlined" style={{ fontSize: '16px', color: 'var(--secondary-fixed, #8ff8b3)' }}>
                  tune
                </span>
                <span>Active Layers &amp; Query Tools</span>
              </div>
              <button
                type="button"
                className={styles.drawerCloseBtn}
                onClick={() => setIsMobileToolsOpen(false)}
                aria-label="Close tools panel"
              >
                <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>close</span>
              </button>
            </div>
            <div className={styles.drawerBody}>
              <Sidebar
                onAnalyzeStudyArea={(geom, name, type) => {
                  setIsMobileToolsOpen(false);
                  handleAnalyzeStudyArea(geom, name, type, currentRadius);
                }}
                onLocationSelect={handleLocationSelect}
                layers={layers}
                onToggleLayer={handleToggleLayer}
              />
            </div>
          </aside>
        </>
      )}

      {/* Block Attribution Inspector Sheet */}
      {!studyAreaActive && (
        <RightPanel
          blockId={selectedBlockId}
          loading={blockLoading}
          data={blockData}
          error={error}
          onClose={handleClosePanel}
        />
      )}

      {/* Study Area Results Sheet */}
      {studyAreaActive && (
        <StudyAreaResult
          loading={studyAreaLoading}
          data={studyAreaData}
          error={studyAreaError}
          onClose={handleClosePanel}
          locationName={studyAreaLocationName}
          boundaryType={studyAreaBoundaryType}
          currentRadius={currentRadius}
          onRadiusChange={handleRadiusChange}
          onRetry={handleRetryAnalysis}
          onSelectBlock={handleBlockClick}
        />
      )}
    </div>
  );
}

export default function ExplorePage() {
  return (
    <Suspense fallback={<div style={{ padding: '24px', fontFamily: 'var(--font-jetbrains-mono)' }}>Loading Pune Geospatial Workspace...</div>}>
      <ExploreContent />
    </Suspense>
  );
}
