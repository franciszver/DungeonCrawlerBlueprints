import { useState } from 'react';
import type { RoomSuggestion, Door, GenerationMode } from '../types';

interface RoomSuggestionPanelProps {
  door: Door;
  currentRoomType: string;
  suggestions: RoomSuggestion[];
  mode: GenerationMode;
  isLoading: boolean;
  error: string | null;
  onGenerate: (roomType: string) => void;
  onCancel: () => void;
  onToggleMode: () => void;
}

export default function RoomSuggestionPanel({
  door,
  currentRoomType,
  suggestions,
  mode,
  isLoading,
  error,
  onGenerate,
  onCancel,
  onToggleMode,
}: RoomSuggestionPanelProps) {
  const [selectedSuggestion, setSelectedSuggestion] = useState<string | null>(null);
  const [customRoomType, setCustomRoomType] = useState('');

  const handleGenerate = () => {
    const roomType = customRoomType || selectedSuggestion;
    if (roomType) {
      onGenerate(roomType);
    }
  };

  const directionLabel = {
    N: 'North',
    S: 'South',
    E: 'East',
    W: 'West',
  }[door.direction];

  return (
    <div className="fixed right-4 top-1/2 -translate-y-1/2 w-80 bg-white rounded-lg shadow-2xl border border-gray-200 p-6 z-50">
      {/* Header */}
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Add Room</h3>
        <p className="text-sm text-gray-600 mt-1">
          Current: <span className="font-medium">{currentRoomType}</span>
        </p>
        <p className="text-sm text-gray-600">
          Door facing: <span className="font-medium">{directionLabel}</span>
        </p>
      </div>

      {/* Mode Toggle */}
      <div className="mb-4">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600">Mode:</span>
          <button
            onClick={onToggleMode}
            className="flex items-center gap-2 px-3 py-1 rounded-md border border-gray-300 hover:bg-gray-50 transition-colors"
          >
            <span className={`text-sm font-medium ${mode === 'realistic' ? 'text-blue-600' : 'text-gray-600'}`}>
              Realistic
            </span>
            <div className="w-10 h-5 bg-gray-200 rounded-full relative">
              <div
                className={`absolute top-0.5 w-4 h-4 bg-blue-600 rounded-full transition-all ${
                  mode === 'fantasy' ? 'left-5' : 'left-0.5'
                }`}
              />
            </div>
            <span className={`text-sm font-medium ${mode === 'fantasy' ? 'text-purple-600' : 'text-gray-600'}`}>
              Fantasy
            </span>
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="mb-4 p-4 text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="text-sm text-gray-600 mt-2">Loading suggestions...</p>
        </div>
      )}

      {/* Suggestions */}
      {!isLoading && suggestions.length > 0 && (
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Suggested Rooms:
          </label>
          <div className="space-y-2">
            {suggestions.map((suggestion, index) => (
              <label
                key={index}
                className="flex items-center gap-3 p-3 border border-gray-200 rounded-md hover:bg-gray-50 cursor-pointer transition-colors"
              >
                <input
                  type="radio"
                  name="room-suggestion"
                  value={suggestion.room_type}
                  checked={selectedSuggestion === suggestion.room_type}
                  onChange={() => {
                    setSelectedSuggestion(suggestion.room_type);
                    setCustomRoomType('');
                  }}
                  className="text-blue-600 focus:ring-blue-500"
                />
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-900">
                    {suggestion.room_type}
                  </div>
                  <div className="text-xs text-gray-500">
                    {Math.round(suggestion.probability * 100)}% probability
                  </div>
                </div>
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Custom Room Type */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Or enter custom:
        </label>
        <input
          type="text"
          value={customRoomType}
          onChange={(e) => {
            setCustomRoomType(e.target.value);
            setSelectedSuggestion(null);
          }}
          placeholder="e.g., Storage Room"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={onCancel}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={handleGenerate}
          disabled={!selectedSuggestion && !customRoomType}
          className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
        >
          Generate Room
        </button>
      </div>
    </div>
  );
}

