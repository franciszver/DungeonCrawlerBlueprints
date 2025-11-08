import { useEffect, useRef } from 'react';
import type { Room, DetectionResult } from '../types';

interface ResultsViewerProps {
  result: DetectionResult;
  blueprintImage?: string;
}

export default function ResultsViewer({ result, blueprintImage }: ResultsViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current || !blueprintImage || !result.rooms) return;

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

      // Draw bounding boxes
      result.rooms?.forEach((room: Room) => {
        const [x_min, y_min, x_max, y_max] = room.bounding_box;
        const width = x_max - x_min;
        const height = y_max - y_min;

        // Draw rectangle
        ctx.strokeStyle = '#3b82f6';
        ctx.lineWidth = 2;
        ctx.strokeRect(x_min, y_min, width, height);

        // Draw label
        if (room.name_hint) {
          ctx.fillStyle = '#1e40af';
          ctx.font = '12px Arial';
          ctx.fillText(room.name_hint, x_min + 5, y_min + 15);
        }

        // Draw confidence
        ctx.fillStyle = '#059669';
        ctx.font = '10px Arial';
        ctx.fillText(`${(room.confidence * 100).toFixed(0)}%`, x_min + 5, y_min + 30);
      });
    };
    img.src = blueprintImage;
  }, [result.rooms, blueprintImage]);

  if (result.status === 'processing') {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
        <p className="mt-4 text-blue-700">Processing blueprint...</p>
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

  if (result.status === 'completed' && result.rooms) {
    return (
      <div className="space-y-4">
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h3 className="text-lg font-semibold mb-4">Detection Results</h3>
          
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
            <p className="text-sm text-gray-600">
              <span className="font-medium">Rooms detected:</span> {result.rooms.length}
            </p>
            {result.metadata && (
              <p className="text-sm text-gray-600">
                <span className="font-medium">Processing time:</span>{' '}
                {result.metadata.processing_time_ms}ms
              </p>
            )}
            {result.metadata && (
              <p className="text-sm text-gray-600">
                <span className="font-medium">Model:</span> {result.metadata.model_used}
              </p>
            )}
          </div>

          <div className="mt-4 space-y-2 max-h-64 overflow-y-auto">
            {result.rooms.map((room: Room) => (
              <div
                key={room.id}
                className="bg-gray-50 border border-gray-200 rounded p-3 text-sm"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-medium text-gray-800">
                      {room.name_hint || room.id}
                    </p>
                    <p className="text-gray-600 text-xs mt-1">
                      BBox: [{room.bounding_box.join(', ')}]
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-green-600 font-medium">
                      {(room.confidence * 100).toFixed(0)}%
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <h4 className="font-semibold mb-2">JSON Output</h4>
          <pre className="text-xs bg-white p-3 rounded border border-gray-200 overflow-auto max-h-64">
            {JSON.stringify(result.rooms, null, 2)}
          </pre>
        </div>
      </div>
    );
  }

  return null;
}

