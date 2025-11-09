interface LoadingSpinnerProps {
  message?: string;
  progress?: {
    current: number;
    total: number;
  };
  estimatedTime?: string;
}

export default function LoadingSpinner({ message, progress, estimatedTime }: LoadingSpinnerProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-4">
      {/* Spinner */}
      <div className="relative w-16 h-16">
        <div className="absolute inset-0 border-4 border-gray-200 rounded-full"></div>
        <div className="absolute inset-0 border-4 border-blue-500 rounded-full border-t-transparent animate-spin"></div>
      </div>

      {/* Message */}
      {message && (
        <p className="text-gray-700 font-medium text-center">{message}</p>
      )}

      {/* Progress */}
      {progress && (
        <div className="flex flex-col items-center gap-2">
          <p className="text-sm text-gray-600">
            Attempt {progress.current} of {progress.total}
          </p>
          <div className="w-64 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 transition-all duration-300"
              style={{ width: `${(progress.current / progress.total) * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* Estimated Time */}
      {estimatedTime && (
        <p className="text-sm text-gray-500">{estimatedTime}</p>
      )}
    </div>
  );
}

