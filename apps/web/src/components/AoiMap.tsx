'use client';
import { useCallback, useRef, useState } from 'react';
import Map, { type MapRef, Source, Layer } from 'react-map-gl/maplibre';
import type { GeoJsonPolygon } from '@sentinel/types';

interface Props {
  value: GeoJsonPolygon | null;
  onChange: (polygon: GeoJsonPolygon | null) => void;
  readOnly?: boolean;
}

export default function AoiMap({ value, onChange, readOnly = false }: Props) {
  const mapRef = useRef<MapRef>(null);
  const [drawing, setDrawing] = useState(false);
  const [points, setPoints] = useState<[number, number][]>([]);

  const handleMapClick = useCallback(
    (e: { lngLat: { lng: number; lat: number } }) => {
      if (readOnly) return;
      const pt: [number, number] = [e.lngLat.lng, e.lngLat.lat];
      setDrawing(true);
      setPoints((prev) => [...prev, pt]);
    },
    [readOnly],
  );

  const handleDblClick = useCallback(
    (e: { lngLat: { lng: number; lat: number }; preventDefault: () => void }) => {
      if (readOnly || points.length < 3) return;
      e.preventDefault(); // prevent map zoom
      const closed: [number, number][] = [...points, points[0]!];
      const polygon: GeoJsonPolygon = {
        type: 'Polygon',
        coordinates: [closed],
      };
      onChange(polygon);
      setDrawing(false);
      setPoints([]);
    },
    [readOnly, points, onChange],
  );

  const clear = useCallback(() => {
    onChange(null);
    setDrawing(false);
    setPoints([]);
  }, [onChange]);

  // Build preview GeoJSON while drawing
  const previewGeoJson = {
    type: 'geojson' as const,
    data: {
      type: 'FeatureCollection' as const,
      features:
        points.length >= 2
          ? [
              {
                type: 'Feature' as const,
                properties: {},
                geometry: {
                  type: 'LineString' as const,
                  coordinates: points,
                },
              },
            ]
          : [],
    },
  };

  const polygonGeoJson = {
    type: 'geojson' as const,
    data: value
      ? {
          type: 'Feature' as const,
          properties: {},
          geometry: value,
        }
      : { type: 'FeatureCollection' as const, features: [] as never[] },
  };

  return (
    <div className="relative w-full h-full rounded-lg overflow-hidden">
      <Map
        ref={mapRef}
        initialViewState={{ longitude: 0, latitude: 20, zoom: 1.5 }}
        style={{ width: '100%', height: '100%' }}
        mapStyle="https://demotiles.maplibre.org/style.json"
        onClick={handleMapClick}
        onDblClick={handleDblClick}
        cursor={readOnly ? 'default' : drawing ? 'crosshair' : 'pointer'}
        doubleClickZoom={false}
      >
        {/* Committed polygon */}
        <Source id="polygon" {...polygonGeoJson}>
          <Layer
            id="polygon-fill"
            type="fill"
            paint={{ 'fill-color': '#3b82f6', 'fill-opacity': 0.25 }}
          />
          <Layer
            id="polygon-outline"
            type="line"
            paint={{ 'line-color': '#3b82f6', 'line-width': 2 }}
          />
        </Source>

        {/* Drawing preview */}
        <Source id="preview" {...previewGeoJson}>
          <Layer
            id="preview-line"
            type="line"
            paint={{ 'line-color': '#f59e0b', 'line-width': 2, 'line-dasharray': [4, 2] }}
          />
        </Source>
      </Map>

      {/* Overlay instructions */}
      {!readOnly && (
        <div className="absolute top-3 left-3 right-3 flex items-center justify-between">
          <div className="bg-slate-900/90 text-slate-300 text-xs px-3 py-1.5 rounded-md">
            {value
              ? '✓ AOI selected'
              : drawing && points.length >= 3
              ? 'Double-click to close polygon'
              : drawing
              ? `${points.length} points — click to add more`
              : 'Click to start drawing your area of interest'}
          </div>
          {(value ?? points.length > 0) && (
            <button
              type="button"
              onClick={clear}
              className="bg-red-900/80 hover:bg-red-800 text-red-200 text-xs px-3 py-1.5 rounded-md transition-colors"
            >
              Clear
            </button>
          )}
        </div>
      )}
    </div>
  );
}
