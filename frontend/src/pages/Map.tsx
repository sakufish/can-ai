import React, { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import Papa from 'papaparse';
import {Database, Image, Activity, Zap, Layers, Play, AlertCircle } from 'lucide-react';

const TABULAR_FEATURES = [
  "elevation",
  "land_cover_class",
  "mean_distance_to_water",
  "mean_ndvi",
  "nighttime_light",
  "slope"
];

interface TileData {
  id: string;
  polygon: number[][];
  score: number | null;
}

const Map = () => {
  const mapRef = useRef<HTMLDivElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const csvInputRef = useRef<HTMLInputElement>(null);
  
  const [tileData, setTileData] = useState<TileData[]>([]);
  const [csvRows, setCsvRows] = useState<any[]>([]);
  const [images, setImages] = useState<{ [tileId: string]: File }>({});
  const [progress, setProgress] = useState({ current: 0, total: 0, running: false });
  const [error, setError] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState({ csv: false, images: false });
  const [stats, setStats] = useState({ tiles: 0, avgScore: 0, predicted: 0, minScore: 0, maxScore: 0 });

  // dark ish color to match theme
  const scoreToColor = (score: number | null): string => {
    if (score == null) return "rgba(60, 60, 60, 0.4)";
    
    const { minScore, maxScore } = stats;
    
    // if we dont have any stats yet just use this range
    const actualMin = stats.predicted > 0 ? minScore : -0.1;
    const actualMax = stats.predicted > 0 ? maxScore : 2.130629447517176;
    
    // normalize score to 0-1 range based on actual data range
    const norm = Math.max(0, Math.min(1, (score - actualMin) / (actualMax - actualMin)));
    
    let red, green, blue;
    
    if (norm < 0.5) {
      const t = norm * 2; // 0 to 1
      red = Math.floor(120 + 60 * (1 - t)); // 180 to 120 (darker red)
      green = Math.floor(40 + 80 * t); // 40 to 120 (muted amber)
      blue = Math.floor(40 + 20 * t); // 40 to 60 (subtle blue)
    } else {
      const t = (norm - 0.5) * 2; // 0 to 1
      red = Math.floor(120 * (1 - t)); // 120 to 0
      green = Math.floor(120 + 60 * t); // 120 to 180 (muted green)
      blue = Math.floor(60 + 80 * t); // 60 to 140 (teal blue)
    }
    
    return `rgb(${red}, ${green}, ${blue})`;
  };

  useEffect(() => {
    if (imageInputRef.current) {
      imageInputRef.current.setAttribute('webkitdirectory', 'true');
      imageInputRef.current.setAttribute('directory', 'true');
    }
  }, []);

  useEffect(() => {
    const predictedTiles = tileData.filter(tile => tile.score !== null);
    
    if (predictedTiles.length > 0) {
      const scores = predictedTiles.map(tile => tile.score!);
      const minScore = Math.min(...scores);
      const maxScore = Math.max(...scores);
      const avgScore = scores.reduce((sum, score) => sum + score, 0) / scores.length;
      
      setStats({ 
        tiles: tileData.length, 
        avgScore, 
        predicted: predictedTiles.length,
        minScore,
        maxScore
      });
    } else {
      setStats({ 
        tiles: tileData.length, 
        avgScore: 0, 
        predicted: 0,
        minScore: 0,
        maxScore: 0
      });
    }
  }, [tileData]);

  const handleCSVUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setUploadProgress(prev => ({ ...prev, csv: true }));
    setError(null);
    
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: (results: Papa.ParseResult<any>) => {
        const rows = (results.data as any[]).filter(row => row.tile_id);
        setCsvRows(rows);
        
        // parse tile data with polygons
        const parsedTiles = rows.map((row) => {
          let polygon = [];
          try {
            const geo = JSON.parse(row[".geo"]);
            polygon = geo.coordinates[0];
          } catch {
            polygon = [];
          }
          return {
            id: row.tile_id,
            polygon,
            score: null // will be filled after prediction
          };
        });
        
        setTileData(parsedTiles);
        setTimeout(() => setUploadProgress(prev => ({ ...prev, csv: false })), 1000);
      },
      error: (error: any) => {
        setError("CSV parsing error: " + error.message);
        setUploadProgress(prev => ({ ...prev, csv: false }));
      },
    });
  };

  const handleImageFolderUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    
    setUploadProgress(prev => ({ ...prev, images: true }));
    
    const imgMap: { [tileId: string]: File } = {};
    for (let i = 0; i < files.length; ++i) {
      const file = files[i];
      // Use file name minus extension as tile_id
      const tileId = file.name.replace(/\.png$/i, "");
      imgMap[tileId] = file;
    }
    
    setImages(imgMap);
    console.log("Loaded image tile_ids:", Object.keys(imgMap));
    setTimeout(() => setUploadProgress(prev => ({ ...prev, images: false })), 1000);
  };

  // batch predict --> for each row, find image and send to backend
  const runBatchPrediction = async () => {
    setProgress({ current: 0, total: csvRows.length, running: true });
    setError(null);
    const newTileData = [...tileData];

    for (let i = 0; i < csvRows.length; ++i) {
      const row = csvRows[i];
      const tileId = row.tile_id;
      const imageFile = images[tileId];

      if (!imageFile) {
        newTileData[i].score = null;
        setError(`Image for tile_id ${tileId} not found`);
        continue;
      }

      // get tabular features in the expected order
      const features: Record<string, number> = {};
      for (const feat of TABULAR_FEATURES) {
        features[feat] = Number(row[feat]);
      }

      // build the FormData
      const formData = new FormData();
      formData.append("image", imageFile);
      formData.append("features", JSON.stringify(features));

      try {
        const response = await fetch("http://localhost:8000/predict/", {
          method: "POST",
          body: formData,
        });
        const data = await response.json();
        newTileData[i].score = data.predicted_score;
      } catch (err) {
        newTileData[i].score = null;
        setError(`Prediction failed for tile_id ${tileId}: ${err}`);
      }
      
      setProgress({ current: i + 1, total: csvRows.length, running: true });
      setTileData([...newTileData]);
    }
    setProgress(p => ({ ...p, running: false }));
  };

  useEffect(() => {
    if (!mapRef.current || tileData.length === 0) return;

    mapRef.current.innerHTML = "";
    
    // calculate bounds from tile data
    const validTiles = tileData.filter(tile => tile.polygon && tile.polygon.length > 0);
    if (validTiles.length === 0) return;
    
    let minLng = Infinity, maxLng = -Infinity;
    let minLat = Infinity, maxLat = -Infinity;
    
    validTiles.forEach(tile => {
      tile.polygon.forEach(([lng, lat]) => {
        minLng = Math.min(minLng, lng);
        maxLng = Math.max(maxLng, lng);
        minLat = Math.min(minLat, lat);
        maxLat = Math.max(maxLat, lat);
      });
    });
    
    const centerLng = (minLng + maxLng) / 2;
    const centerLat = (minLat + maxLat) / 2;
    
    const map = new maplibregl.Map({
      container: mapRef.current,
      style: 'https://tiles.stadiamaps.com/styles/alidade_smooth_dark.json',
      center: [centerLng, centerLat],
      zoom: 12,
      pitch: 45,
      bearing: -17.6,
    });

    map.on('load', () => {
      tileData.forEach((tile) => {
        if (!tile.polygon || tile.polygon.length === 0) return;
        
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
            'fill-opacity': tile.score !== null ? 0.85 : 0.3,
          },
        });
      });
      
      // fit map to show all tiles
      if (validTiles.length > 0) {
        const bounds = new maplibregl.LngLatBounds();
        validTiles.forEach(tile => {
          tile.polygon.forEach(([lng, lat]) => {
            bounds.extend([lng, lat]);
          });
        });
        
        map.fitBounds(bounds, {
          padding: 50,
          maxZoom: 15
        });
      }
    });

    return () => map.remove();
  }, [tileData, stats]);

  const triggerCSVUpload = () => csvInputRef.current?.click();
  const triggerImageUpload = () => imageInputRef.current?.click();

  const canRunPrediction = csvRows.length > 0 && Object.keys(images).length > 0 && !progress.running;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-slate-900 to-black text-white relative overflow-hidden">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl"></div>
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-purple-500/5 rounded-full blur-3xl"></div>
        <div className="absolute top-1/2 left-1/2 w-64 h-64 bg-cyan-500/5 rounded-full blur-3xl"></div>
      </div>

      <div className="relative z-10 border-b border-gray-800/50 backdrop-blur-xl bg-black/20">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-lg bg-gradient-to-r from-blue-500 to-purple-600">
                <Layers className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                  Water Access Mapper
                </h1>
                <p className="text-sm text-gray-400">a ML-powered tile analysis platform</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-gray-800/50 border border-gray-700/50">
                <Activity className="w-4 h-4 text-green-400" />
                <span className="text-sm text-green-400 font-medium">{stats.tiles} Total</span>
              </div>
              <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-gray-800/50 border border-gray-700/50">
                <Zap className="w-4 h-4 text-yellow-400" />
                <span className="text-sm text-yellow-400 font-medium">{stats.predicted} Predicted</span>
              </div>
              {stats.predicted > 0 && (
                <>
                  <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-gray-800/50 border border-gray-700/50">
                    <div className="w-4 h-4 rounded-full bg-gradient-to-r from-red-800 to-teal-700"></div>
                    <span className="text-sm text-gray-300 font-medium">Avg: {stats.avgScore.toFixed(2)}</span>
                  </div>
                  <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-gray-800/50 border border-gray-700/50">
                    <span className="text-xs text-gray-400">Range: {stats.minScore.toFixed(2)} to {stats.maxScore.toFixed(2)}</span>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="relative z-10 p-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
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
              <div className="text-xs text-blue-300/70">{csvRows.length > 0 ? `${csvRows.length} rows loaded` : 'Load geospatial tiles'}</div>
            </div>
          </button>

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
              <div className="text-xs text-purple-300/70">{Object.keys(images).length > 0 ? `${Object.keys(images).length} images loaded` : 'Select image folder'}</div>
            </div>
          </button>

          <button
            onClick={runBatchPrediction}
            disabled={!canRunPrediction}
            className="group flex items-center space-x-3 px-6 py-4 rounded-xl bg-gradient-to-r from-green-600/20 to-emerald-600/20 border border-green-500/30 hover:border-green-400/50 transition-all duration-300 hover:shadow-lg hover:shadow-green-500/20 disabled:opacity-50 disabled:cursor-not-allowed backdrop-blur-sm"
          >
            <div className="p-2 rounded-lg bg-green-500/20 group-hover:bg-green-500/30 transition-colors">
              {progress.running ? (
                <div className="w-5 h-5 border-2 border-green-400 border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <Play className="w-5 h-5 text-green-400" />
              )}
            </div>
            <div className="text-left">
              <div className="font-semibold text-green-100">
                {progress.running ? `Processing... (${progress.current}/${progress.total})` : 'Run Batch Prediction'}
              </div>
              <div className="text-xs text-green-300/70">
                {progress.running ? `${Math.round((progress.current / progress.total) * 100)}% complete` : 'AI model inference'}
              </div>
            </div>
          </button>
        </div>

        {progress.running && (
          <div className="mb-6 p-4 rounded-xl bg-gray-800/50 border border-gray-700/50 backdrop-blur-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-300">Processing tiles...</span>
              <span className="text-sm text-gray-400">{progress.current}/{progress.total}</span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-2">
              <div 
                className="bg-gradient-to-r from-blue-500 to-green-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${(progress.current / progress.total) * 100}%` }}
              ></div>
            </div>
          </div>
        )}

        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-900/20 border border-red-500/30 backdrop-blur-sm">
            <div className="flex items-center space-x-2">
              <AlertCircle className="w-5 h-5 text-red-400" />
              <span className="text-red-200">{error}</span>
            </div>
          </div>
        )}

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

      <div className="relative z-10 px-6 pb-6">
        <div className="relative rounded-2xl overflow-hidden border border-gray-700/50 shadow-2xl">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-500/5 to-purple-500/5 pointer-events-none z-10"></div>
          <div 
            ref={mapRef} 
            className="relative"
            style={{ 
              height: 'calc(100vh - 300px)', 
              width: '100%',
              minHeight: '400px',
              backgroundColor: '#181f2a'
            }} 
          />
          
          <div className="absolute top-4 right-4 z-20 flex flex-col space-y-2">
            <div className="px-3 py-2 rounded-lg bg-black/60 backdrop-blur-md border border-gray-600/30">
              <div className="text-xs text-gray-300 mb-1">Score Range</div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-red-900"></div>
                <span className="text-xs text-gray-400">Low</span>
                <div className="w-8 h-1 bg-gradient-to-r from-red-900 via-amber-800 to-teal-700 rounded"></div>
                <span className="text-xs text-gray-400">High</span>
                <div className="w-3 h-3 rounded-full bg-teal-700"></div>
              </div>
              {stats.predicted > 0 && (
                <div className="text-xs text-gray-400 mt-1">
                  {stats.minScore.toFixed(2)} - {stats.maxScore.toFixed(2)}
                </div>
              )}
            </div>
          </div>

          <div className="absolute bottom-4 left-4 z-20">
            <div className="px-4 py-2 rounded-lg bg-black/60 backdrop-blur-md border border-gray-600/30">
              <div className="text-xs text-gray-300">
                {progress.running ? 'Processing...' : stats.predicted > 0 ? 'Predictions Complete' : 'Ready for Analysis'}
              </div>
              <div className="flex items-center space-x-2 mt-1">
                <div className={`w-2 h-2 rounded-full ${progress.running ? 'bg-yellow-400 animate-pulse' : stats.predicted > 0 ? 'bg-green-400' : 'bg-gray-400'}`}></div>
                <span className={`text-sm font-medium ${progress.running ? 'text-yellow-400' : stats.predicted > 0 ? 'text-green-400' : 'text-gray-400'}`}>
                  {progress.running ? 'Live' : stats.predicted > 0 ? 'Complete' : 'Standby'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {tileData.length > 0 && (
        <div className="relative z-10 px-6 pb-6">
          <div className="rounded-2xl bg-gray-800/50 border border-gray-700/50 backdrop-blur-sm overflow-hidden">
            <div className="p-4 border-b border-gray-700/50">
              <h2 className="text-lg font-semibold text-white">Predictions Results</h2>
              <p className="text-sm text-gray-400">ML model predictions for water access analysis</p>
            </div>
            <div className="max-h-80 overflow-y-auto">
              <table className="w-full">
                <thead className="bg-gray-700/50 sticky top-0">
                  <tr>
                    <th className="p-3 text-left text-sm font-semibold text-gray-300">Tile ID</th>
                    <th className="p-3 text-left text-sm font-semibold text-gray-300">Predicted Score</th>
                    <th className="p-3 text-left text-sm font-semibold text-gray-300">Color Preview</th>
                    <th className="p-3 text-left text-sm font-semibold text-gray-300">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {tileData.map((tile, index) => (
                    <tr key={tile.id} className={`${index % 2 === 0 ? 'bg-gray-800/30' : 'bg-transparent'} hover:bg-gray-700/30 transition-colors`}>
                      <td className="p-3 text-sm text-gray-300 font-mono">{tile.id}</td>
                      <td className="p-3 text-sm text-gray-300">
                        {tile.score !== null ? (
                          <span className="font-medium">{tile.score.toFixed(3)}</span>
                        ) : (
                          <span className="text-gray-500">--</span>
                        )}
                      </td>
                      <td className="p-3">
                        <div 
                          className="w-6 h-6 rounded border border-gray-600"
                          style={{ backgroundColor: scoreToColor(tile.score) }}
                        ></div>
                      </td>
                      <td className="p-3">
                        {tile.score !== null ? (
                          <div className="flex items-center space-x-2">
                            <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                            <span className="text-xs text-green-400">Predicted</span>
                          </div>
                        ) : (
                          <div className="flex items-center space-x-2">
                            <div className="w-2 h-2 bg-gray-500 rounded-full"></div>
                            <span className="text-xs text-gray-500">Pending</span>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Map;