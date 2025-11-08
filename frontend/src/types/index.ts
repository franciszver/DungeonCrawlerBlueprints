export interface Room {
  id: string;
  bounding_box: [number, number, number, number]; // [x_min, y_min, x_max, y_max]
  confidence: number;
  name_hint?: string;
  adjacent_to?: string[];
}

export interface DetectionMetadata {
  model_used: string;
  processing_time_ms: number;
  timestamp: string;
}

export interface DetectionResult {
  job_id: string;
  blueprint_id: string;
  status: 'uploaded' | 'processing' | 'completed' | 'failed';
  rooms?: Room[];
  metadata?: DetectionMetadata;
  error?: string;
  error_code?: string;
  partial_results?: Room[];
}

export interface UploadResponse {
  job_id: string;
  blueprint_id: string;
  status: string;
  s3_key: string;
  message: string;
}

