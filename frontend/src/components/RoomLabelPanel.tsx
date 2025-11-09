import { useState, useEffect } from 'react';

interface TextLabel {
  text: string;
  bbox: [number, number, number, number];
  confidence: number;
  original_text?: string;
}

interface RoomLabelPanelProps {
  textLabels: TextLabel[];
  existingRooms: any[]; // Rooms that already have labels matched
  jobId: string;
  onGenerate: (selectedIndices: number[]) => void;
  onGenerateAll: () => void;
  onClose?: () => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
  warnings?: string[]; // Warnings from generation
}

export default function RoomLabelPanel({
  textLabels,
  existingRooms,
  jobId: _jobId, // Unused but kept for API compatibility
  onGenerate,
  onGenerateAll,
  onClose,
  isCollapsed = false,
  onToggleCollapse,
  warnings: externalWarnings = [],
}: RoomLabelPanelProps) {
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(new Set());
  const [isGenerating, setIsGenerating] = useState(false);
  const [warnings, setWarnings] = useState<string[]>(externalWarnings);
  
  // Update warnings when external warnings change
  useEffect(() => {
    setWarnings(externalWarnings);
  }, [externalWarnings]);

  // Filter out labels already matched to detected rooms
  const matchedLabelTexts = new Set<string>();
  existingRooms.forEach((room) => {
    if (room.name_source === 'blueprint_text') {
      matchedLabelTexts.add((room.name_hint || '').toLowerCase());
    }
  });

  const availableLabels = textLabels
    .map((label, idx) => ({ idx, label }))
    .filter(({ label }) => {
      const labelText = (label.text || '').toLowerCase();
      const originalText = (label.original_text || labelText).toLowerCase();
      return !matchedLabelTexts.has(originalText) && !matchedLabelTexts.has(labelText);
    });

  const handleToggleSelection = (idx: number) => {
    const newSelected = new Set(selectedIndices);
    if (newSelected.has(idx)) {
      newSelected.delete(idx);
    } else {
      newSelected.add(idx);
    }
    setSelectedIndices(newSelected);
  };

  const handleGenerateSelected = async () => {
    if (selectedIndices.size === 0) return;

    setIsGenerating(true);
    setWarnings([]);

    try {
      const indicesArray = Array.from(selectedIndices);
      await onGenerate(indicesArray);
      // Clear selection after successful generation
      setSelectedIndices(new Set());
    } catch (error) {
      console.error('Error generating rooms:', error);
      setWarnings([`Error: ${error instanceof Error ? error.message : 'Unknown error'}`]);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleGenerateAll = async () => {
    setIsGenerating(true);
    setWarnings([]);

    try {
      await onGenerateAll();
      // Clear selection after successful generation
      setSelectedIndices(new Set());
    } catch (error) {
      console.error('Error generating all rooms:', error);
      setWarnings([`Error: ${error instanceof Error ? error.message : 'Unknown error'}`]);
    } finally {
      setIsGenerating(false);
    }
  };

  // Show panel if there are any labels (available or matched)
  // This way users can see what labels were found even if all are matched
  if (textLabels.length === 0) {
    return null; // Don't show panel if no labels at all
  }

  // Get matched labels for display
  const matchedLabels = textLabels
    .map((label, idx) => ({ idx, label }))
    .filter(({ label }) => {
      const labelText = (label.text || '').toLowerCase();
      const originalText = (label.original_text || labelText).toLowerCase();
      return matchedLabelTexts.has(originalText) || matchedLabelTexts.has(labelText);
    });

  return (
    <div className="fixed left-4 top-20 w-80 bg-white rounded-lg shadow-2xl border border-gray-200 z-50">
      {/* Header with collapse button */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">Generate from Labels</h3>
        {onToggleCollapse && (
          <button
            onClick={onToggleCollapse}
            className="text-gray-500 hover:text-gray-700 transition-colors"
            aria-label={isCollapsed ? 'Expand' : 'Collapse'}
          >
            {isCollapsed ? (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
              </svg>
            )}
          </button>
        )}
      </div>

      {!isCollapsed && (
        <>
          {/* Info */}
          <div className="p-4 bg-blue-50 border-b border-gray-200">
            <p className="text-sm text-gray-700">
              {availableLabels.length > 0 ? (
                <>
                  {availableLabels.length} room label{availableLabels.length !== 1 ? 's' : ''} available for generation
                </>
              ) : (
                <>
                  All {textLabels.length} label{textLabels.length !== 1 ? 's' : ''} already matched to detected rooms
                </>
              )}
            </p>
            {matchedLabelTexts.size > 0 && (
              <p className="text-xs text-gray-600 mt-1">
                {matchedLabelTexts.size} label{matchedLabelTexts.size !== 1 ? 's' : ''} already matched to detected rooms
              </p>
            )}
          </div>

          {/* Warnings */}
          {warnings.length > 0 && (
            <div className="p-4 bg-yellow-50 border-b border-gray-200">
              {warnings.map((warning, idx) => (
                <p key={idx} className="text-sm text-yellow-800">{warning}</p>
              ))}
            </div>
          )}

          {/* Available Labels List */}
          {availableLabels.length > 0 && (
            <div className="max-h-96 overflow-y-auto p-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Available to Generate:</h4>
              {availableLabels.map(({ idx, label }) => {
                const isSelected = selectedIndices.has(idx);
                // Status could be 'ready' or 'warning' based on boundary validation in the future
                const hasWarning = warnings.some(w => w.toLowerCase().includes(label.text.toLowerCase()));

                return (
                  <div
                    key={idx}
                    className={`mb-2 p-3 rounded-md border cursor-pointer transition-colors ${
                      isSelected
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                    }`}
                    onClick={() => handleToggleSelection(idx)}
                  >
                    <div className="flex items-start gap-3">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => handleToggleSelection(idx)}
                        className="mt-1 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                        onClick={(e) => e.stopPropagation()}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-900">{label.text}</span>
                          {hasWarning && (
                            <span className="text-xs px-2 py-0.5 bg-yellow-100 text-yellow-800 rounded">
                              Warning
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-4 mt-1">
                          <span className="text-xs text-gray-500">
                            Confidence: {(label.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Matched Labels List (for reference) */}
          {matchedLabels.length > 0 && (
            <div className="p-4 border-t border-gray-200">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Already Matched:</h4>
              <div className="max-h-48 overflow-y-auto space-y-1">
                {matchedLabels.map(({ idx, label }) => (
                  <div
                    key={idx}
                    className="p-2 rounded-md bg-gray-50 border border-gray-200"
                  >
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span className="text-sm text-gray-700">{label.text}</span>
                      <span className="text-xs text-gray-500 ml-auto">
                        {(label.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          {availableLabels.length > 0 && (
            <div className="p-4 border-t border-gray-200 space-y-2">
              <button
                onClick={handleGenerateSelected}
                disabled={selectedIndices.size === 0 || isGenerating}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
              >
                {isGenerating ? (
                  <span className="flex items-center justify-center gap-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Generating...
                  </span>
                ) : (
                  `Generate Selected (${selectedIndices.size})`
                )}
              </button>
              <button
                onClick={handleGenerateAll}
                disabled={isGenerating}
                className="w-full px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
              >
                {isGenerating ? (
                  <span className="flex items-center justify-center gap-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Generating...
                  </span>
                ) : (
                  'Generate All Rooms'
                )}
              </button>
              {onClose && (
                <button
                  onClick={onClose}
                  className="w-full px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
                >
                  Close
                </button>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

