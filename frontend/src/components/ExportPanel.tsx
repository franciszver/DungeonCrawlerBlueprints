import { useState } from 'react';
import { exportResults } from '../services/api';

interface ExportPanelProps {
  jobId: string;
}

export default function ExportPanel({ jobId }: ExportPanelProps) {
  const [exporting, setExporting] = useState(false);

  const handleExport = async (format: 'json' | 'svg') => {
    setExporting(true);
    try {
      const blob = await exportResults(jobId, format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `blueprint_${jobId}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error: any) {
      alert(`Export failed: ${error.message}`);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <h3 className="font-semibold mb-3">Export Results</h3>
      <div className="flex gap-2">
        <button
          onClick={() => handleExport('json')}
          disabled={exporting}
          className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors text-sm"
        >
          {exporting ? 'Exporting...' : 'Export JSON'}
        </button>
        <button
          onClick={() => handleExport('svg')}
          disabled={exporting}
          className="flex-1 bg-green-600 text-white py-2 px-4 rounded-lg hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors text-sm"
        >
          {exporting ? 'Exporting...' : 'Export SVG'}
        </button>
      </div>
    </div>
  );
}

