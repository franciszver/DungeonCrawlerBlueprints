import { useEffect, useRef, useState } from 'react';
import InteractiveEditor from './InteractiveEditor';
import type { Room, DetectionResult } from '../types';

interface ResultsViewerProps {
  result: DetectionResult;
  blueprintImage?: string;
  jobId?: string;
}

export default function ResultsViewer({ result, blueprintImage, jobId }: ResultsViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [viewMode, setViewMode] = useState<'static' | 'interactive'>('static');
  const [extendedRooms, setExtendedRooms] = useState<Room[]>([]);
  const [showInteractiveModeWarning, setShowInteractiveModeWarning] = useState(false);

  useEffect(() => {
    if (!canvasRef.current || !blueprintImage || !result.rooms || viewMode === 'interactive') return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    canvas.width = 1000;
    canvas.height = 1000;

    // Load and draw blueprint image
    const img = new Image();
    img.onload = () => {
      // Draw image scaled to 1000x1000
      ctx.drawImage(img, 0, 0, 1000, 1000);

      // Draw polygons or bounding boxes
      result.rooms?.forEach((room: Room) => {
        if (room.polygon && room.polygon.length > 0) {
          // Draw polygon
          ctx.beginPath();
          ctx.moveTo(room.polygon[0][0], room.polygon[0][1]);
          room.polygon.slice(1).forEach(([x, y]) => {
            ctx.lineTo(x, y);
          });
          ctx.closePath();
          ctx.strokeStyle = room.is_extended ? '#16a34a' : '#3b82f6';
          ctx.lineWidth = 2;
          ctx.stroke();
          ctx.fillStyle = room.is_extended ? 'rgba(34, 197, 94, 0.1)' : 'rgba(59, 130, 246, 0.1)';
          ctx.fill();
        } else {
          // Fallback to bounding box
          const [x_min, y_min, x_max, y_max] = room.bounding_box;
          const width = x_max - x_min;
          const height = y_max - y_min;

          ctx.strokeStyle = room.is_extended ? '#16a34a' : '#3b82f6';
          ctx.lineWidth = 2;
          ctx.strokeRect(x_min, y_min, width, height);
        }

        // Draw label
        if (room.name_hint) {
          const [x_min, y_min] = room.bounding_box;
          ctx.fillStyle = '#1e40af';
          ctx.font = '12px Arial';
          ctx.fillText(room.name_hint, x_min + 5, y_min + 15);
        }

        // Draw confidence
        if (room.confidence !== undefined) {
          const [x_min, y_min] = room.bounding_box;
          ctx.fillStyle = '#059669';
          ctx.font = '10px Arial';
          ctx.fillText(`${(room.confidence * 100).toFixed(0)}%`, x_min + 5, y_min + 30);
        }
      });

      // Draw doors
      if (result.doors && result.doors.length > 0) {
        result.doors.forEach((door) => {
          const [x, y] = door.location;
          ctx.beginPath();
          ctx.arc(x, y, 5, 0, 2 * Math.PI);
          ctx.fillStyle = '#ef4444';
          ctx.fill();
          ctx.strokeStyle = '#991b1b';
          ctx.lineWidth = 1;
          ctx.stroke();
        });
      }
    };
    img.src = blueprintImage;
  }, [result.rooms, result.doors, blueprintImage, viewMode]);

  if (result.status === 'processing') {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
        <p className="mt-4 text-blue-700 font-semibold">Processing blueprint...</p>
        <p className="mt-2 text-sm text-blue-600">Detecting rooms with AI vision models</p>
        <p className="mt-1 text-xs text-blue-500">Using 5 training examples + validation for maximum accuracy</p>
        <p className="mt-2 text-xs text-blue-400">Complex blueprints may take 2-6 minutes. Please wait...</p>
      </div>
    );
  }

  if (result.status === 'failed') {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <h3 className="text-red-800 font-semibold mb-2">Detection Failed</h3>
        <p className="text-red-600">{result.error || 'Unknown error'}</p>
        {result.error_code && (
          <p className="text-sm text-red-500 mt-2">Error Code: {result.error_code}</p>
        )}
        {result.partial_results && result.partial_results.length > 0 && (
          <div className="mt-4">
            <p className="text-sm text-red-700">Partial results available:</p>
            <pre className="mt-2 text-xs bg-red-100 p-2 rounded overflow-auto">
              {JSON.stringify(result.partial_results, null, 2)}
            </pre>
          </div>
        )}
      </div>
    );
  }

  if (result.status === 'completed') {
    // Combine all rooms: original detected + extended from backend + modified from backend + extended from interactive mode
    const allRooms = [
      ...(result.rooms || []),
      ...(result.extended_rooms || []),
      ...(result.modified_rooms || []),
      ...extendedRooms
    ];
    // Show interactive mode if there are doors, text labels, or any rooms detected
    const hasTextLabels = result.metadata?.text_labels && result.metadata.text_labels.length > 0;
    const hasDoors = result.doors && result.doors.length > 0;
    const hasRooms = allRooms.length > 0;
    const hasDoorsAndInteractive = (hasDoors || hasTextLabels || hasRooms) && jobId;

    return (
      <div className="space-y-4">
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold">Detection Results</h3>
            
            {hasDoorsAndInteractive && (
              <div className="flex gap-2">
                <button
                  onClick={() => setViewMode('static')}
                  className={`px-4 py-2 rounded transition-colors ${
                    viewMode === 'static'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  📊 View Results
                </button>
                <button
                  onClick={() => {
                    // Show warning if there are detected rooms
                    if (viewMode === 'static' && (result.rooms?.length || 0) > 0) {
                      setShowInteractiveModeWarning(true);
                    } else {
                      setViewMode('interactive');
                    }
                  }}
                  className={`px-4 py-2 rounded transition-colors ${
                    viewMode === 'interactive'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  🎮 Interactive Mode
                </button>
              </div>
            )}
          </div>

          {viewMode === 'interactive' && hasDoorsAndInteractive ? (
            <div className="h-[600px] border border-gray-300 rounded-lg overflow-hidden">
              <InteractiveEditor
                jobId={jobId}
                rooms={[]}
                doors={result.doors || []}
                blueprintImage={blueprintImage || ''}
                initialExtendedRooms={[]}
                initialModifiedRooms={[]}
                initialTextLabels={(() => {
                  const labels = result.metadata?.text_labels || [];
                  console.log('🏷️ Passing labels to InteractiveEditor:', labels);
                  console.log('🏷️ Number of labels:', labels.length);
                  return labels;
                })()}
                onExtendedRoomsChange={setExtendedRooms}
              />
            </div>
          ) : (
            <>
              {blueprintImage && (
                <div className="mb-4 border border-gray-300 rounded-lg overflow-hidden">
                  <canvas
                    ref={canvasRef}
                    className="w-full h-auto max-h-96 object-contain"
                    style={{ imageRendering: 'auto' }}
                  />
                </div>
              )}

              <div className="space-y-2">
                <p className="text-sm text-gray-900 font-semibold">
                  <span className="font-bold">Total rooms:</span> {allRooms.length}
                </p>
                <div className="pl-4 space-y-1">
                  <p className="text-sm text-gray-600">
                    <span className="font-medium">Detected:</span> {result.rooms?.length || 0}
                  </p>
                  {(result.extended_rooms?.length || 0) > 0 && (
                    <p className="text-sm text-green-600">
                      <span className="font-medium">Extended (from backend):</span> {result.extended_rooms?.length || 0}
                    </p>
                  )}
                  {(result.modified_rooms?.length || 0) > 0 && (
                    <p className="text-sm text-blue-600">
                      <span className="font-medium">Modified:</span> {result.modified_rooms?.length || 0}
                    </p>
                  )}
                  {extendedRooms.length > 0 && (
                    <p className="text-sm text-green-600">
                      <span className="font-medium">Extended (interactive):</span> {extendedRooms.length}
                    </p>
                  )}
                </div>
                {result.doors && result.doors.length > 0 && (
                  <p className="text-sm text-gray-600">
                    <span className="font-medium">Doors detected:</span> {result.doors.length}
                  </p>
                )}
                {result.confidence !== undefined && (
                  <p className="text-sm text-gray-600">
                    <span className="font-medium">Overall confidence:</span>{' '}
                    {(result.confidence * 100).toFixed(0)}%
                  </p>
                )}
                {result.metadata && result.metadata.processing_time_ms && (
                  <p className="text-sm text-gray-600">
                    <span className="font-medium">Processing time:</span>{' '}
                    {result.metadata.processing_time_ms}ms
                  </p>
                )}
                {result.metadata && result.metadata.primary_model && (
                  <p className="text-sm text-gray-600">
                    <span className="font-medium">Primary model:</span> {result.metadata.primary_model}
                  </p>
                )}
                {result.metadata && result.metadata.models_used && result.metadata.models_used.length > 1 && (
                  <p className="text-sm text-gray-600">
                    <span className="font-medium">Validation models:</span>{' '}
                    {result.metadata.models_used.join(', ')}
                  </p>
                )}
              </div>

              {/* Master Room List */}
              <div className="mt-6">
                <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                  <span>📋</span>
                  <span>Room List</span>
                  <span className="text-sm font-normal text-gray-500">
                    ({allRooms.length} {allRooms.length === 1 ? 'room' : 'rooms'})
                  </span>
                </h4>
                <div className="space-y-2 max-h-96 overflow-y-auto border border-gray-200 rounded-lg p-3 bg-gray-50">
                  {allRooms.map((room: Room, index: number) => (
                    <div
                      key={room.id}
                      className={`border rounded-lg p-3 text-sm transition-colors ${
                        room.is_extended
                          ? 'bg-green-50 border-green-300 hover:bg-green-100'
                          : 'bg-white border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-gray-500 font-mono text-xs">#{index + 1}</span>
                            <p className="font-semibold text-gray-900">
                              {room.name_hint || room.id}
                            </p>
                            {room.is_extended && (
                              <span className="px-2 py-0.5 text-xs text-green-700 bg-green-200 rounded-full font-medium">
                                Extended
                              </span>
                            )}
                            {room.is_modified && (
                              <span className="px-2 py-0.5 text-xs text-blue-700 bg-blue-200 rounded-full font-medium">
                                Modified
                              </span>
                            )}
                          </div>
                          <p className="text-gray-600 text-xs mt-1.5">
                            {room.polygon
                              ? `Polygon: ${room.polygon.length} vertices`
                              : `Bounding Box: [${room.bounding_box.map(n => Math.round(n)).join(', ')}]`}
                          </p>
                        </div>
                        <div className="text-right ml-3">
                          {room.confidence !== undefined && (
                            <div className="flex flex-col items-end">
                              <p className="text-green-600 font-semibold text-base">
                                {(room.confidence * 100).toFixed(0)}%
                              </p>
                              <p className="text-xs text-gray-500">confidence</p>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>

        {viewMode === 'static' && (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold mb-2">JSON Output</h4>
            <pre className="text-xs bg-white p-3 rounded border border-gray-200 overflow-auto max-h-64">
              {JSON.stringify(
                {
                  rooms: allRooms,
                  doors: result.doors,
                  metadata: result.metadata,
                },
                null,
                2
              )}
            </pre>
          </div>
        )}

        {/* Warning Modal for Interactive Mode */}
        {showInteractiveModeWarning && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-2xl p-6 max-w-md w-full mx-4">
              <div className="flex items-start gap-3 mb-4">
                <span className="text-3xl">⚠️</span>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    Switch to Interactive Mode?
                  </h3>
                  <p className="text-sm text-gray-700 mb-3">
                    Entering Interactive Mode will <strong>reset and delete all automatically detected rooms</strong>.
                  </p>
                  <p className="text-sm text-gray-700 mb-3">
                    You will need to generate rooms manually using the text labels on the blueprint.
                  </p>
                  <div className="bg-blue-50 border border-blue-200 rounded p-3 text-sm text-blue-800">
                    <strong>What you'll keep:</strong>
                    <ul className="list-disc ml-4 mt-1">
                      <li>Text labels from the blueprint</li>
                      <li>Doors (if detected)</li>
                      <li>Ability to add manual labels</li>
                    </ul>
                  </div>
                </div>
              </div>
              <div className="flex gap-2 justify-end">
                <button
                  onClick={() => setShowInteractiveModeWarning(false)}
                  className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    setShowInteractiveModeWarning(false);
                    setViewMode('interactive');
                  }}
                  className="px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 transition-colors font-medium"
                >
                  Continue to Interactive Mode
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  return null;
}

