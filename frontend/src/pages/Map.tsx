import React, { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import Papa from 'papaparse';
import {Database, Image, Activity, Zap, Layers } from 'lucide-react';

interface TileData {
  id: string;
  polygon: number[][];
  score: number;
}

const scoreToColor = (score: number): string => {
  const norm = Math.max(0, Math.min(1, (score + 2) / 4));
  const red = Math.floor(40 + 80 * (1 - norm));
  const green = Math.floor(40 + 80 * norm);
  const blue = 60;
  return `rgb(${red}, ${green}, ${blue})`;
};

const Map = () => {
  const mapRef = useRef<HTMLDivElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const csvInputRef = useRef<HTMLInputElement>(null);
  const [tileData, setTileData] = useState<TileData[]>([
    {
      id: 'sample_1',
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
      id: 'sample_2',
      polygon: [
        [34.11, 0.0],
        [34.12, 0.0],
        [34.12, 0.01],
        [34.11, 0.01],
        [34.11, 0.0],
      ],
      score: 0.3,
    },
    {
      id: 'sample_3',
      polygon: [
        [34.12, 0.0],
        [34.13, 0.0],
        [34.13, 0.01],
        [34.12, 0.01],
        [34.12, 0.0],
      ],
      score: -0.6,
    },
  ]);

  const [uploadProgress, setUploadProgress] = useState({ csv: false, images: false });
  const [stats, setStats] = useState({ tiles: tileData.length, avgScore: 0.2 });

  useEffect(() => {
    if (imageInputRef.current) {
      imageInputRef.current.setAttribute('webkitdirectory', 'true');
    }
  }, []);

  useEffect(() => {
    const avgScore = tileData.reduce((sum, tile) => sum + tile.score, 0) / tileData.length;
    setStats({ tiles: tileData.length, avgScore });
  }, [tileData]);

  const handleCSVUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setUploadProgress(prev => ({ ...prev, csv: true }));
    
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: (results: Papa.ParseResult<any>) => {
        const parsed: TileData[] = (results.data as any[]).map((row) => {
          const geo = JSON.parse(row.geo);
          return {
            id: row.tile_id,
            polygon: geo.coordinates[0],
            score: parseFloat(row.score),
          };
        });
        setTileData(parsed);
        setTimeout(() => setUploadProgress(prev => ({ ...prev, csv: false })), 1000);
      },
      error: (error: any) => {
        console.error('CSV parsing error:', error);
        setUploadProgress(prev => ({ ...prev, csv: false }));
      },
    });
  };

  const handleImageFolderUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    
    setUploadProgress(prev => ({ ...prev, images: true }));
    console.log('Uploaded image files:', Array.from(files));
    setTimeout(() => setUploadProgress(prev => ({ ...prev, images: false })), 1000);
  };

  useEffect(() => {
    if (!mapRef.current || tileData.length === 0) return;

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
  }, [tileData]);

  const triggerCSVUpload = () => csvInputRef.current?.click();
  const triggerImageUpload = () => imageInputRef.current?.click();

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-slate-900 to-black text-white relative overflow-hidden">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-purple-500/5 rounded-full blur-3xl animate-pulse delay-1000"></div>
        <div className="absolute top-1/2 left-1/2 w-64 h-64 bg-cyan-500/5 rounded-full blur-3xl animate-pulse delay-2000"></div>
      </div>

      {/* Header */}
      <div className="relative z-10 border-b border-gray-800/50 backdrop-blur-xl bg-black/20">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-lg bg-gradient-to-r from-blue-500 to-purple-600">
                <Layers className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                  GeoSpatial Analytics
                </h1>
                <p className="text-sm text-gray-400">Advanced tile visualization platform</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-6">
              <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-gray-800/50 border border-gray-700/50">
                <Activity className="w-4 h-4 text-green-400" />
                <span className="text-sm text-green-400 font-medium">{stats.tiles} Tiles</span>
              </div>
              <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-gray-800/50 border border-gray-700/50">
                <Zap className="w-4 h-4 text-yellow-400" />
                <span className="text-sm text-yellow-400 font-medium">Avg: {stats.avgScore.toFixed(2)}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Control Panel */}
      <div className="relative z-10 p-6">
        <div className="flex space-x-4 mb-6">
          {/* CSV Upload Button */}
          <button
            onClick={triggerCSVUpload}
            disabled={uploadProgress.csv}
            className="group flex items-center space-x-3 px-6 py-4 rounded-xl bg-gradient-to-r from-blue-600/20 to-cyan-600/20 border border-blue-500/30 hover:border-blue-400/50 transition-all duration-300 hover:shadow-lg hover:shadow-blue-500/20 disabled:opacity-50 disabled:cursor-not-allowed backdrop-blur-sm"
          >
            <div className="p-2 rounded-lg bg-blue-500/20 group-hover:bg-blue-500/30 transition-colors">
              {uploadProgress.csv ? (
                <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <Database className="w-5 h-5 text-blue-400" />
              )}
            </div>
            <div className="text-left">
              <div className="font-semibold text-blue-100">Upload CSV Data</div>
              <div className="text-xs text-blue-300/70">Load geospatial tiles</div>
            </div>
          </button>

          {/* Image Upload Button */}
          <button
            onClick={triggerImageUpload}
            disabled={uploadProgress.images}
            className="group flex items-center space-x-3 px-6 py-4 rounded-xl bg-gradient-to-r from-purple-600/20 to-pink-600/20 border border-purple-500/30 hover:border-purple-400/50 transition-all duration-300 hover:shadow-lg hover:shadow-purple-500/20 disabled:opacity-50 disabled:cursor-not-allowed backdrop-blur-sm"
          >
            <div className="p-2 rounded-lg bg-purple-500/20 group-hover:bg-purple-500/30 transition-colors">
              {uploadProgress.images ? (
                <div className="w-5 h-5 border-2 border-purple-400 border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <Image className="w-5 h-5 text-purple-400" />
              )}
            </div>
            <div className="text-left">
              <div className="font-semibold text-purple-100">Upload PNG Tiles</div>
              <div className="text-xs text-purple-300/70">Select image folder</div>
            </div>
          </button>
        </div>

        {/* Hidden file inputs */}
        <input
          ref={csvInputRef}
          type="file"
          accept=".csv"
          onChange={handleCSVUpload}
          className="hidden"
        />
        <input
          ref={imageInputRef}
          type="file"
          accept="image/png"
          multiple
          onChange={handleImageFolderUpload}
          className="hidden"
        />
      </div>

      {/* Map Container */}
      <div className="relative z-10 px-6 pb-6">
        <div className="relative rounded-2xl overflow-hidden border border-gray-700/50 shadow-2xl">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-500/5 to-purple-500/5 pointer-events-none z-10"></div>
          <div 
            ref={mapRef} 
            className="relative"
            style={{ 
              height: 'calc(100vh - 200px)', 
              width: '100%',
              minHeight: '500px'
            }} 
          />
          
          {/* Map overlay controls */}
          <div className="absolute top-4 right-4 z-20 flex flex-col space-y-2">
            <div className="px-3 py-2 rounded-lg bg-black/60 backdrop-blur-md border border-gray-600/30">
              <div className="text-xs text-gray-300 mb-1">Score Range</div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full" style={{backgroundColor: scoreToColor(-2)}}></div>
                <span className="text-xs text-gray-400">Low</span>
                <div className="w-8 h-1 bg-gradient-to-r from-red-500 to-green-500 rounded"></div>
                <span className="text-xs text-gray-400">High</span>
                <div className="w-3 h-3 rounded-full" style={{backgroundColor: scoreToColor(2)}}></div>
              </div>
            </div>
          </div>

          <div className="absolute bottom-4 left-4 z-20">
            <div className="px-4 py-2 rounded-lg bg-black/60 backdrop-blur-md border border-gray-600/30">
              <div className="text-xs text-gray-300">Real-time Analytics</div>
              <div className="flex items-center space-x-2 mt-1">
                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                <span className="text-sm text-green-400 font-medium">Live</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Map;