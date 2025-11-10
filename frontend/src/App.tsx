import { useState } from 'react';
import BlueprintUpload from './components/BlueprintUpload';
import ResultsViewer from './components/ResultsViewer';
import ExportPanel from './components/ExportPanel';
import LoadingSpinner from './components/LoadingSpinner';
import { detectRooms, getResults } from './services/api';
import type { UploadResponse, DetectionResult } from './types';

function App() {
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [detectionResult, setDetectionResult] = useState<DetectionResult | null>(null);
  const [blueprintImage, setBlueprintImage] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [isPolling, setIsPolling] = useState(false);
  const [, setPollingAttempt] = useState(0);

  const handleUploadComplete = async (result: UploadResponse) => {
    setUploadResult(result);
    setError('');
    setIsPolling(true);
    setPollingAttempt(0);

    // Start detection - api.ts handles all polling internally
    try {
      const detectResult = await detectRooms(
        result.blueprint_id, 
        result.job_id,
        (current, _total) => {
          setPollingAttempt(current);
        }
      );
      setDetectionResult(detectResult);
      setIsPolling(false);
      setPollingAttempt(0);
    } catch (err: any) {
      setIsPolling(false);
      setPollingAttempt(0);
      const errorMessage = err.response?.data?.error || err.message || 'Detection failed';
      setError(errorMessage);
      
      // If timeout error, show job_id for manual checking
      if (errorMessage.includes('longer than expected') && result.job_id) {
        setDetectionResult({
          job_id: result.job_id,
          blueprint_id: result.blueprint_id,
          status: 'processing',
        });
      }
    }
  };

  const handleCheckResults = async () => {
    if (!uploadResult?.job_id) return;
    
    setIsPolling(true);
    setError('');
    
    try {
      const result = await getResults(uploadResult.job_id);
      setDetectionResult(result);
      setIsPolling(false);
      
      if (result.status === 'completed') {
        setError('');
      } else if (result.status === 'failed') {
        setError(result.error || 'Detection failed');
      } else {
        setError('Detection is still processing. Please check again in a moment.');
      }
    } catch (err: any) {
      setIsPolling(false);
      setError(err.response?.data?.error || err.message || 'Failed to check results');
    }
  };


  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold text-gray-900">
            DungeonCrawlerBlueprints
          </h1>
          <p className="text-gray-600 mt-1">
            AI-Powered Room Detection from Architectural Blueprints
          </p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">{error}</p>
            <div className="mt-2 flex gap-2">
              {uploadResult?.job_id && (
                <button
                  onClick={handleCheckResults}
                  disabled={isPolling}
                  className="text-sm bg-red-600 text-white px-3 py-1 rounded hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
                >
                  {isPolling ? 'Checking...' : 'Check Results'}
                </button>
              )}
              <button
                onClick={() => setError('')}
                className="text-sm text-red-600 hover:text-red-800"
              >
                Dismiss
              </button>
            </div>
          </div>
        )}

        {!uploadResult ? (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
            <h2 className="text-2xl font-semibold mb-6 text-center">
              Upload Blueprint
            </h2>
            <BlueprintUpload
              onUploadComplete={handleUploadComplete}
              onError={setError}
              onFileSelect={(file) => {
                const reader = new FileReader();
                reader.onload = (e) => {
                  setBlueprintImage(e.target?.result as string);
                };
                reader.readAsDataURL(file);
              }}
            />
          </div>
        ) : isPolling ? (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12">
            <LoadingSpinner
              message="Processing Blueprint..."
            />
          </div>
        ) : (
          <div className="space-y-6">
            {detectionResult && (
              <>
                <ResultsViewer
                  result={detectionResult}
                  blueprintImage={blueprintImage}
                  jobId={detectionResult.job_id}
                />
                {detectionResult.status === 'completed' && (
                  <ExportPanel jobId={detectionResult.job_id} />
                )}
              </>
            )}

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 space-y-2">
              {detectionResult?.status === 'processing' && (
                <button
                  onClick={handleCheckResults}
                  disabled={isPolling}
                  className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                >
                  {isPolling ? 'Checking Results...' : 'Check Results Manually'}
                </button>
              )}
              <button
                onClick={() => {
                  setUploadResult(null);
                  setDetectionResult(null);
                  setBlueprintImage('');
                  setError('');
                  setIsPolling(false);
                }}
                className="w-full bg-gray-600 text-white py-2 px-4 rounded-lg hover:bg-gray-700 transition-colors"
              >
                Upload New Blueprint
              </button>
            </div>
          </div>
        )}
      </main>

      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 py-6 text-center text-sm text-gray-600">
          <p>Powered by Claude 3 Haiku & AWS Lambda</p>
        </div>
      </footer>
    </div>
  );
}

export default App;

