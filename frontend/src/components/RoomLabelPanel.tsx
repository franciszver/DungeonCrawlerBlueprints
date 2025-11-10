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
  onAddManualLabel?: () => void;
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
  onAddManualLabel,
}: RoomLabelPanelProps) {
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(new Set());
  const [isGenerating, setIsGenerating] = useState(false);
  const [warnings, setWarnings] = useState<string[]>(externalWarnings);
  
  // Update warnings when external warnings change
  useEffect(() => {
    setWarnings(externalWarnings);
  }, [externalWarnings]);

  // Track which labels have generated rooms (by label_index)
  const generatedLabelIndices = new Set<number>();
  existingRooms.forEach((room) => {
    if (room.is_extended && (room as any).label_index !== undefined) {
      generatedLabelIndices.add((room as any).label_index);
    }
  });

  // Show ALL labels, but mark which ones are generated
  const allLabels = textLabels.map((label, idx) => ({ 
    idx, 
    label, 
    isGenerated: generatedLabelIndices.has(idx)
  }));

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

  // Always show panel so user can add manual labels
  return (
    <div className="fixed right-4 top-4 w-80 bg-white rounded-lg shadow-2xl border border-gray-200 z-50">
      {/* Header with collapse button */}
      <div className="flex items-center justify-between p-3 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-blue-100">
        <h3 className="text-sm font-semibold text-gray-900">📝 Room Labels</h3>
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
          {textLabels.length > 0 && (
            <div className="p-3 bg-blue-50 border-b border-gray-200">
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-700">
                  <span className="font-semibold">{allLabels.length}</span> label{allLabels.length !== 1 ? 's' : ''}
                </span>
                {generatedLabelIndices.size > 0 && (
                  <span className="text-green-700">
                    <span className="font-semibold">{generatedLabelIndices.size}</span> generated
                  </span>
                )}
              </div>
            </div>
          )}
          
          {/* Empty state message */}
          {textLabels.length === 0 && (
            <div className="p-4 text-center text-gray-500 text-sm">
              <p className="mb-2">No labels detected</p>
              <p className="text-xs">Click "Add Manual Label" below to create one</p>
            </div>
          )}

          {/* Warnings */}
          {warnings.length > 0 && (
            <div className="p-4 bg-yellow-50 border-b border-gray-200">
              {warnings.map((warning, idx) => (
                <p key={idx} className="text-sm text-yellow-800">{warning}</p>
              ))}
            </div>
          )}

          {/* All Labels List */}
          {allLabels.length > 0 && (
            <div className="max-h-96 overflow-y-auto p-3">
              {allLabels.map(({ idx, label, isGenerated }) => {
                const isSelected = selectedIndices.has(idx);
                const hasWarning = warnings.some(w => w.toLowerCase().includes(label.text.toLowerCase()));

                return (
                  <div
                    key={idx}
                    className={`mb-2 p-2 rounded border transition-colors ${
                      isGenerated
                        ? 'border-green-300 bg-green-50'
                        : isSelected
                        ? 'border-blue-500 bg-blue-50 cursor-pointer'
                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50 cursor-pointer'
                    }`}
                    onClick={() => !isGenerated && handleToggleSelection(idx)}
                  >
                    <div className="flex items-center gap-2">
                      {!isGenerated && (
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => handleToggleSelection(idx)}
                          className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 flex-shrink-0"
                          onClick={(e) => e.stopPropagation()}
                        />
                      )}
                      {isGenerated && (
                        <svg className="w-4 h-4 text-green-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                      <div className="flex-1 min-w-0">
                        <span className={`text-sm font-medium ${isGenerated ? 'text-green-800' : 'text-gray-900'}`}>
                          {label.text}
                        </span>
                        {hasWarning && !isGenerated && (
                          <span className="ml-2 text-xs text-yellow-600">⚠️</span>
                        )}
                      </div>
                      {!isGenerated && (
                        <button
                          onClick={async (e) => {
                            e.stopPropagation();
                            setIsGenerating(true);
                            setWarnings([]);
                            try {
                              await onGenerate([idx]);
                              setSelectedIndices(prev => {
                                const newSet = new Set(prev);
                                newSet.delete(idx);
                                return newSet;
                              });
                            } catch (error) {
                              console.error('Error generating room:', error);
                              setWarnings([`Error: ${error instanceof Error ? error.message : 'Unknown error'}`]);
                            } finally {
                              setIsGenerating(false);
                            }
                          }}
                          disabled={isGenerating}
                          className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex-shrink-0"
                          title="Generate this room"
                        >
                          {isGenerating ? '⏳' : '✨'}
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Add Manual Label Button */}
          {onAddManualLabel && (
            <div className="p-3 border-t border-gray-200">
              <button
                onClick={onAddManualLabel}
                className="w-full px-3 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors text-sm font-medium"
              >
                ➕ Add Manual Label
              </button>
            </div>
          )}

          {/* Actions */}
          {allLabels.filter(l => !l.isGenerated).length > 0 && (
            <div className="p-3 border-t border-gray-200 space-y-2">
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
                disabled={isGenerating || allLabels.filter(l => !l.isGenerated).length === 0}
                className="w-full px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
              >
                {isGenerating ? (
                  <span className="flex items-center justify-center gap-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Generating...
                  </span>
                ) : (
                  `Generate All Remaining (${allLabels.filter(l => !l.isGenerated).length})`
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

