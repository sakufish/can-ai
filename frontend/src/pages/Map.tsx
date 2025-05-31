import { useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

const tileData = [
  {
    id: 'tile_1',
    polygon: [
      [34.1, 0.0],
      [34.11, 0.0],
      [34.11, 0.01],
      [34.1, 0.01],
      [34.1, 0.0],
    ],
    score: 0.9,
  },
  {
    id: 'tile_2',
    polygon: [
      [34.11, 0.0],
      [34.12, 0.0],
      [34.12, 0.01],
      [34.11, 0.01],
      [34.11, 0.0],
    ],
    score: 0.3,
  },
];

const scoreToColor = (score: number): string => {
  const norm = Math.max(0, Math.min(1, (score + 2) / 4));
  const red = Math.floor(40 + 80 * (1 - norm));
  const green = Math.floor(40 + 80 * norm);
  const blue = 60;
  return `rgb(${red}, ${green}, ${blue})`;
};

const Map = () => {
  const mapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!mapRef.current) return;

    const map = new maplibregl.Map({
      container: mapRef.current,
      style: 'https://tiles.stadiamaps.com/styles/alidade_smooth_dark.json',
      center: [34.11, 0.005],
      zoom: 12,
      pitch: 45,
      bearing: -17.6,
    });

    map.on('load', () => {
      tileData.forEach((tile) => {
        map.addSource(tile.id, {
          type: 'geojson',
          data: {
            type: 'Feature',
            geometry: {
              type: 'Polygon',
              coordinates: [tile.polygon],
            },
            properties: {
              score: tile.score,
            },
          },
        });

        map.addLayer({
          id: tile.id,
          type: 'fill',
          source: tile.id,
          paint: {
            'fill-color': scoreToColor(tile.score),
            'fill-opacity': 0.85,
          },
        });
      });
    });

    return () => map.remove();
  }, []);

  return <div ref={mapRef} style={{ height: '100vh', width: '100%', borderRadius: '0.5rem' }} />;
};

export default Map;
