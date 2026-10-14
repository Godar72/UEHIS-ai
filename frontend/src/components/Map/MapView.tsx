'use client';

import React, { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import Map, { Source, Layer, Popup, MapRef } from 'react-map-gl/maplibre';
import circle from '@turf/circle';
import area from '@turf/area';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import styles from './map.module.css';

if (typeof window !== 'undefined') {
  maplibregl.setWorkerUrl('/maplibre-gl-worker.mjs');
}

// Module-level stable constants to eliminate React re-render prop churn in react-map-gl
const UEHI_TILES = ['/tiles/uehi/{z}/{x}/{y}.pbf'];
const CARBON_TILES = ['/tiles/carbon/{z}/{x}/{y}.pbf'];
const PLANTING_AREAS_TILES = ['/tiles/planting-areas/{z}/{x}/{y}.pbf'];
const INTERACTIVE_LAYER_IDS = ['uehi-layer', 'carbon-layer', 'planting-units-layer', 'planting-areas-layer'];

const MODEL_COVERAGE_LINE_PAINT: any = {
  'line-color': '#FFFFFF',
  'line-width': 1.5,
  'line-dasharray': [3, 3],
  'line-opacity': 0.6
};

const MODEL_COVERAGE_LABEL_LAYOUT: any = {
  'symbol-placement': 'line',
  'text-field': 'Model Coverage',
  'text-size': 12,
  'text-letter-spacing': 0.1,
  'text-keep-upright': true,
  'text-offset': [0, -1],
  'text-max-angle': 30
};

const MODEL_COVERAGE_LABEL_PAINT: any = {
  'text-color': '#FFFFFF',
  'text-opacity': 0.8,
  'text-halo-color': 'rgba(0,0,0,0.6)',
  'text-halo-width': 1
};

const UEHI_FILL_PAINT: any = {
  'fill-color': [
    'match',
    ['get', 'risk_level'],
    'Critical', '#A83D32',
    'High', '#D5682D',
    'Moderate', '#B28A36',
    'Low', '#3D7650',
    '#cccccc'
  ],
  'fill-opacity': [
    'case',
    ['boolean', ['feature-state', 'selected'], false],
    0.5,
    0.15
  ]
};

const UEHI_SELECTED_LINE_PAINT: any = {
  'line-color': '#FFFFFF',
  'line-width': 2,
  'line-opacity': ['case', ['boolean', ['feature-state', 'selected'], false], 1, 0]
};

const CARBON_FILL_PAINT: any = {
  'fill-color': [
    'interpolate',
    ['linear'],
    ['get', 'standing_carbon_stock_tonnes_co2e'],
    0, '#e5e7eb',
    10, '#bbf7d0',
    100, '#4ade80',
    500, '#16a34a',
    1000, '#166534'
  ],
  'fill-opacity': [
    'case',
    ['boolean', ['feature-state', 'selected'], false],
    0.7,
    0.4
  ]
};

const CARBON_SELECTED_LINE_PAINT: any = {
  'line-color': '#FFFFFF',
  'line-width': 2,
  'line-opacity': ['case', ['boolean', ['feature-state', 'selected'], false], 1, 0]
};

const PLANTING_AREAS_FILL_PAINT: any = {
  'fill-color': '#FEF3C7',
  'fill-opacity': 0.6,
  'fill-outline-color': '#FDE68A'
};

const PLANTING_UNITS_CIRCLE_PAINT: any = {
  'circle-color': '#3D7650',
  'circle-radius': [
    'interpolate', ['linear'], ['zoom'],
    14, 2,
    16, 4
  ],
  'circle-stroke-width': 1,
  'circle-stroke-color': '#ffffff'
};

const FILTERED_PLANTING_UNITS_CIRCLE_PAINT: any = {
  'circle-color': '#3D7650',
  'circle-radius': [
    'interpolate', ['linear'], ['zoom'],
    10, 2,
    16, 4
  ],
  'circle-stroke-width': 1,
  'circle-stroke-color': '#ffffff'
};

const STUDY_AREA_FILL_PAINT: any = {
  'fill-color': '#F36B24',
  'fill-opacity': 0.1
};

const STUDY_AREA_OUTLINE_PAINT: any = {
  'line-color': '#F36B24',
  'line-width': 3
};

const PREVIEW_CIRCLE_FILL_PAINT: any = {
  'fill-color': '#F36B24',
  'fill-opacity': 0.2
};

const PREVIEW_CIRCLE_OUTLINE_PAINT: any = {
  'line-color': '#F36B24',
  'line-width': 2,
  'line-dasharray': [2, 2]
};

const DRAW_FILL_PAINT: any = {
  'fill-color': '#F36B24',
  'fill-opacity': 0.3
};

const DRAW_LINE_PAINT: any = {
  'line-color': '#F36B24',
  'line-width': 3,
  'line-dasharray': [2, 2]
};

const SELECTED_PLANTING_UNIT_PAINT: any = {
  'circle-color': '#3D7650',
  'circle-radius': 6,
  'circle-stroke-width': 3,
  'circle-stroke-color': '#FDE68A'
};

function latLonToUTM(lat: number, lon: number) {
  const a = 6378137;
  const eccSquared = 0.00669438;
  const k0 = 0.9996;
  const latRad = lat * Math.PI / 180;
  const lonRad = lon * Math.PI / 180;
  const zoneNumber = Math.floor((lon + 180) / 6) + 1;
  const centralMeridian = (zoneNumber - 1) * 6 - 180 + 3;
  const centralMeridianRad = centralMeridian * Math.PI / 180;
  const N = a / Math.sqrt(1 - eccSquared * Math.sin(latRad) * Math.sin(latRad));
  const T = Math.tan(latRad) * Math.tan(latRad);
  const C = eccSquared / (1 - eccSquared) * Math.cos(latRad) * Math.cos(latRad);
  const A = Math.cos(latRad) * (lonRad - centralMeridianRad);
  const M = a * ((1 - eccSquared / 4 - 3 * eccSquared * eccSquared / 64 - 5 * Math.pow(eccSquared, 3) / 256) * latRad 
                - (3 * eccSquared / 8 + 3 * eccSquared * eccSquared / 32 + 45 * Math.pow(eccSquared, 3) / 1024) * Math.sin(2 * latRad) 
                + (15 * eccSquared * eccSquared / 256 + 45 * Math.pow(eccSquared, 3) / 1024) * Math.sin(4 * latRad) 
                - (35 * Math.pow(eccSquared, 3) / 3072) * Math.sin(6 * latRad));
  const easting = k0 * N * (A + (1 - T + C) * A * A * A / 6 + (5 - 18 * T + T * T + 72 * C - 58 * eccSquared) * Math.pow(A, 5) / 120) + 500000;
  const northing = k0 * (M + N * Math.tan(latRad) * (A * A / 2 + (5 - T + 9 * C + 4 * C * C) * Math.pow(A, 4) / 24 + (61 - 58 * T + T * T + 600 * C - 330 * eccSquared) * Math.pow(A, 6) / 720));
  return { easting, northing, zoneNumber };
}



interface MapViewProps {
  onBlockClick: (blockId: string) => void;
  studyAreaGeometry?: any;
  onAnalyzeStudyArea?: (geometry: any, name: string, type: string) => void;
  searchResult?: { lat: number, lng: number, name: string, type: string } | null;
  plantingConfig?: {
    showAreas: boolean;
    showUnits: boolean;
    scenarioId: string | null;
    scenarioName?: string;
    filteredGeoJson?: any;
  };
  showUehi?: boolean;
  showCarbon?: boolean;
  selectedBlockId?: string | null;
  selectedUnitId?: string | null;
  onPlantingUnitClick?: (unit: any) => void;
  initialZoom?: number;
  initialCenter?: [number, number];
  cooperativeGestures?: boolean;
}

function MapViewComponent({ 
  onBlockClick, 
  studyAreaGeometry, 
  onAnalyzeStudyArea, 
  searchResult, 
  plantingConfig, 
  showUehi = true, 
  showCarbon = false, 
  selectedBlockId = null, 
  selectedUnitId = null,
  onPlantingUnitClick, 
  initialZoom = 12, 
  initialCenter = [73.8567, 18.5204],
  cooperativeGestures = false
}: MapViewProps) {
  const mapRef = useRef<MapRef>(null);

  // Uncontrolled camera state with discrete boolean triggers to eliminate 60Hz React re-rendering
  const [isZoomedOut, setIsZoomedOut] = useState(initialZoom < 14);
  const isZoomedOutRef = useRef(initialZoom < 14);
  const [isOutsideCoverage, setIsOutsideCoverage] = useState(
    initialCenter[0] < 73.749344 || initialCenter[0] > 74.021411 ||
    initialCenter[1] < 18.428852 || initialCenter[1] > 18.621015
  );
  const isOutsideCoverageRef = useRef(
    initialCenter[0] < 73.749344 || initialCenter[0] > 74.021411 ||
    initialCenter[1] < 18.428852 || initialCenter[1] > 18.621015
  );

  const initialViewState = useMemo(() => ({
    longitude: initialCenter[0],
    latitude: initialCenter[1],
    zoom: initialZoom
  }), [initialCenter, initialZoom]);

  const mapContainerStyle = useMemo(() => ({ width: '100%', height: '100%' }), []);

  const [selectedPoint, setSelectedPoint] = useState<{ lng: number; lat: number, name?: string, popupContent?: any, isPlantingUnit?: boolean } | null>(null);
  const [previewRadius, setPreviewRadius] = useState<number>(2000); // 2km default

  const [drawMode, setDrawMode] = useState(false);
  const drawModeRef = useRef(drawMode);
  drawModeRef.current = drawMode;
  const [drawVertices, setDrawVertices] = useState<[number, number][]>([]);
  const [pendingPolygon, setPendingPolygon] = useState<any>(null);

  const [cursor, setCursor] = useState<string>('auto');

  const [basemap, setBasemap] = useState<'satellite' | 'light'>('satellite');
  const [imageryError, setImageryError] = useState<string | null>(null);

  const mapTilerKey = process.env.NEXT_PUBLIC_MAPTILER_API_KEY;

  const hybridStyle = `https://api.maptiler.com/maps/hybrid/style.json?key=${mapTilerKey || ''}`;
  const lightStyle = mapTilerKey
    ? `https://api.maptiler.com/maps/dataviz-light/style.json?key=${mapTilerKey}`
    : 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json';
  
  const currentStyle = basemap === 'satellite' ? hybridStyle : lightStyle;

  // Memoized scenario vector tile array to avoid invalidating source on every render
  const plantingUnitsTiles = useMemo(() => {
    if (!plantingConfig?.scenarioId || plantingConfig.scenarioId === 'full') return null;
    return [`/tiles/planting-units/${plantingConfig.scenarioId}/{z}/{x}/{y}.pbf`];
  }, [plantingConfig?.scenarioId]);

  useEffect(() => {
    if (!selectedUnitId && selectedPoint?.isPlantingUnit) {
      setSelectedPoint(null);
    }
  }, [selectedUnitId]);

  useEffect(() => {
    setSelectedPoint(null);
  }, [plantingConfig?.scenarioId]);

  useEffect(() => {
    if (searchResult && mapRef.current) {
      mapRef.current.flyTo({
        center: [searchResult.lng, searchResult.lat],
        zoom: 13.5,
        duration: 1200
      });
    }
  }, [searchResult]);

  const handleMapError = useCallback((e: any) => {
    const errorUrl = e?.error?.url || '';
    const isMapTilerBasemapError = typeof errorUrl === 'string' && errorUrl.includes('api.maptiler.com/maps/');
    if (basemap === 'satellite' && isMapTilerBasemapError && (e?.error?.status === 401 || e?.error?.status === 403)) {
      console.warn('MapTiler imagery failed to load. Falling back to Light basemap.', e.error);
      setImageryError('Satellite imagery unavailable. Using Light basemap.');
      setBasemap('light');
    }
  }, [basemap]);

  // Sync testMap reference immediately on map load
  const handleMapLoad = useCallback((evt: any) => {
    if (typeof window !== 'undefined') {
      (window as any).testMap = evt.target;
    }
    if (searchResult && evt.target) {
      evt.target.flyTo({
        center: [searchResult.lng, searchResult.lat],
        zoom: 13.5,
        duration: 800
      });
    }
  }, [searchResult]);

  // Discrete threshold-based camera event handler: ONLY dispatches React state when crossing thresholds
  const handleMove = useCallback((evt: any) => {
    const { zoom, longitude, latitude } = evt.viewState;
    const zoomedOut = zoom < 14;
    const outside = longitude < 73.749344 || longitude > 74.021411 || latitude < 18.428852 || latitude > 18.621015;
    
    if (isZoomedOutRef.current !== zoomedOut) {
      isZoomedOutRef.current = zoomedOut;
      setIsZoomedOut(zoomedOut);
    }
    if (isOutsideCoverageRef.current !== outside) {
      isOutsideCoverageRef.current = outside;
      setIsOutsideCoverage(outside);
    }
  }, []);

  useEffect(() => {
    if (searchResult) {
      if (mapRef.current) {
        mapRef.current.flyTo({ center: [searchResult.lng, searchResult.lat], zoom: 14, duration: 1500 });
      }
      setSelectedPoint({ lng: searchResult.lng, lat: searchResult.lat, name: searchResult.name });
    }
  }, [searchResult]);

  useEffect(() => {
    const map = mapRef.current?.getMap();
    if (!map || !map.getSource('uehi')) return;
    
    try {
      map.removeFeatureState({ source: 'uehi', sourceLayer: 'uehi' });
      if (selectedBlockId) {
        map.setFeatureState(
          { source: 'uehi', sourceLayer: 'uehi', id: selectedBlockId },
          { selected: true }
        );
      }
    } catch (e) {
      console.warn("Could not set feature state", e);
    }
  }, [selectedBlockId]);

  // Fallback to guarantee window.testMap is populated if onLoad was missed
  useEffect(() => {
    const map = mapRef.current?.getMap();
    if (map && typeof window !== 'undefined') {
      (window as any).testMap = map;
    }
  }, []);

  // Native mouseenter/mouseleave on planting units to set cursor without React re-render churn
  useEffect(() => {
    const map = mapRef.current?.getMap();
    if (!map || !plantingConfig?.showUnits) return;

    const handleMouseEnter = () => { map.getCanvas().style.cursor = 'pointer'; };
    const handleMouseLeave = () => { map.getCanvas().style.cursor = ''; };

    map.on('mouseenter', 'planting-units-layer', handleMouseEnter);
    map.on('mouseleave', 'planting-units-layer', handleMouseLeave);

    return () => {
      map.off('mouseenter', 'planting-units-layer', handleMouseEnter);
      map.off('mouseleave', 'planting-units-layer', handleMouseLeave);
    };
  }, [plantingConfig?.showUnits]);

  // Single consolidated click handler for all interactive layers
  const onClick = useCallback((event: any) => {
    if (drawMode) {
      setDrawVertices(prev => [...prev, [event.lngLat.lng, event.lngLat.lat]]);
      return;
    }

    const map = event.target || mapRef.current?.getMap();
    // Prioritize planting units over underlying polygon areas
    let feature = event.features?.find((f: any) => f.layer.id === 'planting-units-layer');
    
    // Resilient fallback query with 6px tolerance for precise touch & click targeting on points
    if (!feature && map && event.point) {
      const bbox: any = [
        [event.point.x - 6, event.point.y - 6],
        [event.point.x + 6, event.point.y + 6]
      ];
      const directUnits = map.queryRenderedFeatures(bbox, { layers: ['planting-units-layer'] });
      if (directUnits && directUnits.length > 0) {
        feature = directUnits[0];
      }
    }

    if (!feature) {
      feature = event.features?.[0];
    }

    if (!feature && map && event.point) {
      const bbox: any = [
        [event.point.x - 6, event.point.y - 6],
        [event.point.x + 6, event.point.y + 6]
      ];
      const directOthers = map.queryRenderedFeatures(bbox, { layers: ['planting-areas-layer', 'uehi-layer', 'carbon-layer'] });
      if (directOthers && directOthers.length > 0) {
        feature = directOthers[0];
      }
    }

    if (feature) {
      if (feature.layer.id === 'planting-units-layer') {
        const unitFeature = feature;

        let exactLng = event.lngLat.lng;
        let exactLat = event.lngLat.lat;
        
        if (unitFeature.geometry && unitFeature.geometry.coordinates) {
          if (typeof unitFeature.geometry.coordinates[0] === 'number') {
            exactLng = unitFeature.geometry.coordinates[0];
            exactLat = unitFeature.geometry.coordinates[1];
          } else if (Array.isArray(unitFeature.geometry.coordinates[0]) && typeof unitFeature.geometry.coordinates[0][0] === 'number') {
            exactLng = unitFeature.geometry.coordinates[0][0];
            exactLat = unitFeature.geometry.coordinates[0][1];
          }
        } else if (unitFeature.properties && unitFeature.properties.lng) {
          exactLng = unitFeature.properties.lng;
          exactLat = unitFeature.properties.lat;
        }

        const utm = latLonToUTM(exactLat, exactLng);
        const bx = Math.floor(utm.easting / 250) * 250;
        const by = Math.floor(utm.northing / 250) * 250;
        const parentBlockId = `PN_${bx}_${by}`;
        const unitId = unitFeature.properties?.planting_unit_id || unitFeature.id || 'Unknown';

        if (onPlantingUnitClick) {
          onPlantingUnitClick({
            id: unitId,
            unitUuid: typeof unitId === 'string' && /^[0-9a-f-]{36}$/i.test(unitId) ? unitId : undefined,
            parentBlockId: parentBlockId,
            lat: exactLat,
            lng: exactLng,
            easting: utm.easting,
            northing: utm.northing,
            zone: utm.zoneNumber,
            scenario: plantingConfig?.scenarioName || 'Unknown',
            opportunityClass: null,
            uehi: null,
            riskLevel: null,
            waterDistance: null,
            ownershipStatus: 'Verification required',
            utilityStatus: 'Verification required',
            permissionStatus: 'Verification required',
            carbonAssumption: '0.5 t CO₂e/tree'
          });
        }

        setSelectedPoint({
          lng: exactLng,
          lat: exactLat,
          isPlantingUnit: true
        });
        return;
      }

      if (feature.layer.id === 'uehi-layer' && feature.properties.block_id) {
        onBlockClick(feature.properties.block_id);
        setSelectedPoint(null);
        return;
      }

      if (feature.layer.id === 'carbon-layer' && feature.properties.block_id) {
        onBlockClick(feature.properties.block_id);
        setSelectedPoint(null);
        return;
      }
      
      if (feature.layer.id === 'planting-areas-layer') {
        const props = feature.properties;
        const rawCategory = props.candidate_category || props.candidate_class || 'Unknown';
        let displayCategory = rawCategory;
        if (rawCategory.includes('public_like')) displayCategory = 'Public-like open space';
        else if (rawCategory.includes('context_dependent')) displayCategory = 'Context-dependent';
        else if (rawCategory.includes('other_open_space')) displayCategory = 'Other open space';

        const popupContent = (
          <div style={{ padding: '8px', color: '#111827', fontFamily: 'var(--font-family-sans)' }}>
            <h4 style={{ margin: '0 0 8px 0', fontSize: '14px' }}>Planting opportunity area — not a confirmed planting site</h4>
            <div style={{ fontSize: '12px' }}>
              <div style={{ marginBottom: '4px' }}>
                <span style={{ color: '#4B5563' }}>Category: </span>
                <span style={{ fontWeight: 600 }} title={rawCategory}>{displayCategory}</span>
              </div>
              <div style={{ marginBottom: '4px' }}>
                <span style={{ color: '#4B5563' }}>Ownership: </span>
                <span style={{ fontWeight: 600 }}>{props.ownership_status || 'Unknown'}</span>
              </div>
              <div style={{ marginBottom: '4px' }}>
                <span style={{ color: '#4B5563' }}>Utilities: </span>
                <span style={{ fontWeight: 600 }}>{props.utility_status || 'Unknown'}</span>
              </div>
              <div style={{ marginBottom: '4px' }}>
                <span style={{ color: '#4B5563' }}>Permission: </span>
                <span style={{ fontWeight: 600 }}>{props.permission_status || 'Unknown'}</span>
              </div>
            </div>
          </div>
        );
        setSelectedPoint({ lng: event.lngLat.lng, lat: event.lngLat.lat, popupContent });
        return;
      }
    }

    // Clicked on empty map
    if (plantingConfig) {
      setSelectedPoint(null);
      return;
    }

    setSelectedPoint({ lng: event.lngLat.lng, lat: event.lngLat.lat });
  }, [onBlockClick, drawMode, plantingConfig, onPlantingUnitClick]);

  // Memoize previewCircle geometry
  const previewCircle = useMemo(() => {
    if (!selectedPoint || drawMode || selectedPoint.isPlantingUnit) return null;
    return circle([selectedPoint.lng, selectedPoint.lat], previewRadius / 1000, { units: 'kilometers' }).geometry;
  }, [selectedPoint, drawMode, previewRadius]);

  const handleAnalyzePoint = useCallback(() => {
    if (selectedPoint && onAnalyzeStudyArea && previewCircle) {
      const radiusText = `${previewRadius >= 1000 ? previewRadius/1000 + ' km' : previewRadius + ' m'} radius`;
      const finalName = selectedPoint.name ? `${radiusText} around ${selectedPoint.name}` : radiusText;
      onAnalyzeStudyArea(
        { type: "Polygon", coordinates: previewCircle.coordinates },
        finalName,
        'Point radius'
      );
      setSelectedPoint(null);
    }
  }, [selectedPoint, onAnalyzeStudyArea, previewCircle, previewRadius]);

  const handleFinishDraw = useCallback(() => {
    if (drawVertices.length >= 3) {
      const coords = [...drawVertices, drawVertices[0]];
      setPendingPolygon({ type: "Polygon", coordinates: [coords] });
    }
    setDrawMode(false);
    setDrawVertices([]);
  }, [drawVertices]);

  const handleAnalyzePendingPolygon = useCallback(() => {
    if (pendingPolygon && onAnalyzeStudyArea) {
      onAnalyzeStudyArea(pendingPolygon, 'Custom Area', 'User polygon');
      setPendingPolygon(null);
    }
  }, [pendingPolygon, onAnalyzeStudyArea]);

  const handleClearPendingPolygon = useCallback(() => {
    setPendingPolygon(null);
  }, []);

  const drawGeoJson: any = useMemo(() => {
    if (drawVertices.length === 0) return null;
    if (drawVertices.length > 2) {
      return {
        type: "Feature",
        properties: {},
        geometry: {
          type: "Polygon",
          coordinates: [[...drawVertices, drawVertices[0]]]
        }
      };
    }
    return {
      type: "Feature",
      properties: {},
      geometry: {
        type: "LineString",
        coordinates: drawVertices
      }
    };
  }, [drawVertices]);

  return (
    <div className={styles.mapContainer}>
      
      {/* Basemap Selector */}
      <div className={styles.basemapControl}>
        <div className={styles.basemapCard}>
          <label className={styles.basemapLabel}>
            <input type="radio" name="basemap" checked={basemap === 'satellite'} onChange={() => setBasemap('satellite')} style={{ cursor: 'pointer' }} />
            <span>Satellite</span>
          </label>
          <label className={styles.basemapLabel}>
            <input type="radio" name="basemap" checked={basemap === 'light'} onChange={() => setBasemap('light')} style={{ cursor: 'pointer' }} />
            <span>Light</span>
          </label>
        </div>
        {imageryError && (
          <div style={{ backgroundColor: '#FEE2E2', color: '#991B1B', padding: '6px 10px', fontSize: '11px', fontWeight: 'bold', border: '1px solid #FCA5A5' }}>
            {imageryError}
          </div>
        )}
      </div>

      {/* Map UI Controls */}
      <div className={styles.drawControl}>
        {!pendingPolygon && (
          <button 
            type="button"
            onClick={() => { setDrawMode(!drawMode); setDrawVertices([]); setSelectedPoint(null); }}
            className={`${styles.drawBtn} ${drawMode ? styles.drawBtnActive : ''}`}
          >
            {drawMode ? 'Cancel Drawing' : 'Draw Polygon'}
          </button>
        )}
        {drawMode && drawVertices.length >= 3 && (
          <button 
            type="button"
            onClick={handleFinishDraw}
            className={styles.completeBtn}
          >
            Complete Polygon
          </button>
        )}
      </div>

      {pendingPolygon && (
        <div style={{ position: 'absolute', top: 60, left: '50%', transform: 'translateX(-50%)', zIndex: 10, backgroundColor: 'white', padding: '16px', borderRadius: '8px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)', border: '1px solid #D1D5DB', textAlign: 'center' }}>
          <div style={{ marginBottom: '12px', fontWeight: 'bold', fontSize: '14px', color: '#111827' }}>
            Selected area: {(area(pendingPolygon) / 1000000).toFixed(2)} km²
          </div>
          <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
            <button 
              onClick={handleAnalyzePendingPolygon}
              style={{ padding: '6px 12px', borderRadius: '4px', border: 'none', backgroundColor: '#F36B24', color: 'white', fontWeight: 'bold', cursor: 'pointer' }}
            >
              Analyze Area
            </button>
            <button 
              onClick={handleClearPendingPolygon}
              style={{ padding: '6px 12px', borderRadius: '4px', border: '1px solid #D1D5DB', backgroundColor: 'white', color: '#4B5563', fontWeight: 'bold', cursor: 'pointer' }}
            >
              Clear Area
            </button>
          </div>
        </div>
      )}

      {plantingConfig?.showUnits && isZoomedOut && (
        <div style={{ position: 'absolute', bottom: 30, left: '50%', transform: 'translateX(-50%)', zIndex: 10, backgroundColor: 'rgba(255, 255, 255, 0.9)', padding: '8px 16px', borderRadius: '20px', boxShadow: '0 2px 8px rgba(0,0,0,0.15)', fontSize: '13px', fontWeight: 'bold', color: '#333' }}>
          Zoom in to view planting opportunities.
        </div>
      )}

      {isOutsideCoverage && (
        <div style={{ position: 'absolute', top: 60, left: '50%', transform: 'translateX(-50%)', zIndex: 10, backgroundColor: 'rgba(255, 255, 255, 0.95)', padding: '8px 16px', borderRadius: '8px', border: '1px solid #D1D5DB', boxShadow: '0 4px 6px rgba(0,0,0,0.1)', fontSize: '13px', color: '#374151', textAlign: 'center', pointerEvents: 'none' }}>
          <strong>Outside model coverage.</strong> UEHIS analysis is currently unavailable for this area.
        </div>
      )}

      <Map
        ref={mapRef}
        initialViewState={initialViewState}
        onMove={handleMove}
        onLoad={handleMapLoad}
        cooperativeGestures={cooperativeGestures}
        maxTileCacheSize={250}
        maxTileCacheZoomLevels={10}
        renderWorldCopies={false}
        fadeDuration={0}
        mapStyle={currentStyle}
        style={mapContainerStyle}
        interactiveLayerIds={INTERACTIVE_LAYER_IDS}
        onClick={onClick}
        onError={handleMapError}
      >
        {/* Model Coverage Layer */}
        <Source id="model-coverage" type="geojson" data="/model_coverage.geojson">
          <Layer
            id="model-coverage-line"
            type="line"
            paint={MODEL_COVERAGE_LINE_PAINT}
          />
          <Layer
            id="model-coverage-label"
            type="symbol"
            layout={MODEL_COVERAGE_LABEL_LAYOUT}
            paint={MODEL_COVERAGE_LABEL_PAINT}
          />
        </Source>

        {/* UEHI Layer */}
        {showUehi && (
          <Source
            id="uehi"
            type="vector"
            tiles={UEHI_TILES}
            minzoom={10}
            maxzoom={16}
          >
            <Layer
              id="uehi-layer"
              type="fill"
              source="uehi"
              source-layer="uehi"
              paint={UEHI_FILL_PAINT}
            />
            <Layer
              id="uehi-selected-layer"
              type="line"
              source="uehi"
              source-layer="uehi"
              paint={UEHI_SELECTED_LINE_PAINT}
            />
          </Source>
        )}

        {/* Carbon Layer */}
        {showCarbon && (
          <Source
            id="carbon"
            type="vector"
            tiles={CARBON_TILES}
            minzoom={10}
            maxzoom={16}
          >
            <Layer
              id="carbon-layer"
              type="fill"
              source="carbon"
              source-layer="carbon"
              paint={CARBON_FILL_PAINT}
            />
            <Layer
              id="carbon-selected-layer"
              type="line"
              source="carbon"
              source-layer="carbon"
              paint={CARBON_SELECTED_LINE_PAINT}
            />
          </Source>
        )}

        {/* Planting Candidate Areas Layer */}
        {plantingConfig?.showAreas && (
          <Source
            id="planting-areas"
            type="vector"
            tiles={PLANTING_AREAS_TILES}
            minzoom={10}
            maxzoom={16}
          >
            <Layer
              id="planting-areas-layer"
              type="fill"
              source="planting-areas"
              source-layer="planting_candidate_areas"
              paint={PLANTING_AREAS_FILL_PAINT}
            />
          </Source>
        )}

        {/* Filtered Planting Units (GeoJSON) */}
        {plantingConfig?.showUnits && plantingConfig.filteredGeoJson && (
          <Source id="filtered-planting-units" type="geojson" data={plantingConfig.filteredGeoJson}>
            <Layer
              id="planting-units-layer"
              type="circle"
              paint={FILTERED_PLANTING_UNITS_CIRCLE_PAINT}
            />
          </Source>
        )}

        {/* Scenario Planting Units (Vector Tiles) */}
        {plantingConfig?.showUnits && plantingUnitsTiles && !plantingConfig.filteredGeoJson && (
          <Source
            id="planting-units"
            key="planting-units"
            type="vector"
            tiles={plantingUnitsTiles}
            minzoom={14}
            maxzoom={20}
          >
            <Layer
              id="planting-units-layer"
              type="circle"
              source="planting-units"
              source-layer="planting_units"
              paint={PLANTING_UNITS_CIRCLE_PAINT}
            />
          </Source>
        )}

        {/* Study Area Final Polygon */}
        {(studyAreaGeometry || pendingPolygon) && !drawMode && (
          <Source id="study-area" type="geojson" data={studyAreaGeometry || pendingPolygon}>
            <Layer
              id="study-area-fill"
              type="fill"
              paint={STUDY_AREA_FILL_PAINT}
            />
            <Layer
              id="study-area-outline"
              type="line"
              paint={STUDY_AREA_OUTLINE_PAINT}
            />
          </Source>
        )}

        {/* Preview Circle */}
        {previewCircle && !drawMode && (
          <Source id="preview-circle" type="geojson" data={previewCircle}>
            <Layer
              id="preview-circle-fill"
              type="fill"
              paint={PREVIEW_CIRCLE_FILL_PAINT}
            />
            <Layer
              id="preview-circle-outline"
              type="line"
              paint={PREVIEW_CIRCLE_OUTLINE_PAINT}
            />
          </Source>
        )}

        {/* Drawing Geometry */}
        {drawGeoJson && (
          <Source id="draw-geometry" type="geojson" data={drawGeoJson}>
            {drawVertices.length > 2 && (
              <Layer
                id="draw-fill"
                type="fill"
                paint={DRAW_FILL_PAINT}
              />
            )}
            <Layer
              id="draw-line"
              type="line"
              paint={DRAW_LINE_PAINT}
            />
          </Source>
        )}

        {/* Selected Point Highlight */}
        {selectedPoint && selectedPoint.isPlantingUnit && (
          <Source id="selected-planting-unit" type="geojson" data={{
            type: "Feature",
            geometry: { type: "Point", coordinates: [selectedPoint.lng, selectedPoint.lat] },
            properties: {}
          }}>
            <Layer
              id="selected-planting-unit-layer"
              type="circle"
              paint={SELECTED_PLANTING_UNIT_PAINT}
            />
          </Source>
        )}

        {/* Popup for Area Analysis (Floating planting unit detail popup removed in favor of inspection sidebar) */}
        {selectedPoint && !drawMode && !selectedPoint.isPlantingUnit && (
          <Popup
            longitude={selectedPoint.lng}
            latitude={selectedPoint.lat}
            anchor="bottom"
            onClose={() => setSelectedPoint(null)}
            closeOnClick={false}
          >
            {selectedPoint.popupContent ? (
              selectedPoint.popupContent
            ) : (
              <div style={{ padding: '8px', color: '#111827', fontFamily: 'var(--font-family-sans)' }}>
                <h4 style={{ margin: '0 0 8px 0', fontSize: '14px' }}>Analyze Area</h4>
                <select 
                  value={previewRadius} 
                  onChange={(e) => setPreviewRadius(Number(e.target.value))}
                  style={{ padding: '4px', width: '100%', marginBottom: '8px' }}
                >
                  <option value={500}>500 m</option>
                  <option value={1000}>1 km</option>
                  <option value={2000}>2 km</option>
                  <option value={5000}>5 km</option>
                </select>
                <button 
                  onClick={handleAnalyzePoint}
                  style={{
                    backgroundColor: '#F36B24',
                    color: 'white',
                    border: 'none',
                    padding: '6px 12px',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    width: '100%',
                    fontWeight: 'bold'
                  }}
                >
                  Analyze Area
                </button>
              </div>
            )}
          </Popup>
        )}
      </Map>
    </div>
  );
}

export const MapView = React.memo(MapViewComponent);
export default MapView;
