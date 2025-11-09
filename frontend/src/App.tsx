import { useState } from 'react';
import BlueprintUpload from './components/BlueprintUpload';
import ResultsViewer from './components/ResultsViewer';
import ExportPanel from './components/ExportPanel';
import { detectRooms, getResults } from './services/api';
import type { UploadResponse, DetectionResult } from './types';

function App() {
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [detectionResult, setDetectionResult] = useState<DetectionResult | null>(null);
  const [blueprintImage, setBlueprintImage] = useState<string>('');
  const [error, setError] = useState<string>('');

  const handleUploadComplete = async (result: UploadResponse) => {
    setUploadResult(result);
    setError('');

    // Start detection
    try {
      const detectResult = await detectRooms(result.blueprint_id, result.job_id);
      setDetectionResult(detectResult);

      // If still processing, poll for results
      if (detectResult.status === 'processing') {
        pollForResults(result.job_id);
      }
    } catch (err: any) {
      setError(err.response?.data?.error || err.message || 'Detection failed');
    }
  };

  const pollForResults = async (jobId: string) => {
    const maxAttempts = 30; // 30 seconds max
    let attempts = 0;

    const poll = async () => {
      if (attempts >= maxAttempts) {
        setError('Detection timeout - please check results manually');
        return;
      }

      try {
        const result = await getResults(jobId);
        setDetectionResult(result);

        if (result.status !== 'completed' && result.status !== 'failed') {
          attempts++;
          setTimeout(poll, 1000); // Poll every second
        }
      } catch (err: any) {
        setError(err.response?.data?.error || err.message || 'Failed to get results');
      }
    };

    poll();
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
            <button
              onClick={() => setError('')}
              className="mt-2 text-sm text-red-600 hover:text-red-800"
            >
              Dismiss
            </button>
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

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <button
                onClick={() => {
                  setUploadResult(null);
                  setDetectionResult(null);
                  setBlueprintImage('');
                  setError('');
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
          <p>Powered by OpenRouter GPT-4 Vision & AWS Lambda</p>
        </div>
      </footer>
    </div>
  );
}

export default App;

