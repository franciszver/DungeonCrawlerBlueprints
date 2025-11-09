export type Polygon = [number, number][]; // Array of [x, y] coordinates

export interface Door {
  id: string;
  location: [number, number]; // [x, y]
  direction: 'N' | 'S' | 'E' | 'W';
  connects?: string[]; // IDs of connected rooms
}

export interface Room {
  id: string;
  bounding_box: [number, number, number, number]; // [x_min, y_min, x_max, y_max]
  polygon?: Polygon; // Optional polygon vertices
  confidence: number;
  name_hint?: string;
  adjacent_to?: string[];
  doors?: Door[];
  is_extended?: boolean; // True if user-generated
  connected_door?: {
    location: [number, number];
    direction: string;
  };
}

export interface DetectionMetadata {
  models_used?: string[]; // Models attempted
  retry_count?: number;
  primary_confidence?: number;
  final_confidence?: number;
  detection_type?: 'polygon' | 'bounding_box';
  primary_model?: string;
  processing_time_ms: number;
  timestamp: string;
  few_shot_examples_used?: number;
}

export interface DetectionResult {
  job_id: string;
  blueprint_id: string;
  status: 'uploaded' | 'processing' | 'completed' | 'failed';
  rooms?: Room[];
  doors?: Door[];
  extended_rooms?: Room[];
  confidence?: number;
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

export interface RoomSuggestion {
  room_type: string;
  probability: number;
  typical_dimensions: {
    width: number;
    height: number;
  };
}

export type GenerationMode = 'realistic' | 'fantasy';

export interface ExtendedRoom extends Room {
  is_extended: true;
  connected_door: {
    location: [number, number];
    direction: string;
  };
}

export interface HistoryAction {
  type: 'add' | 'modify' | 'delete';
  room?: Room;
  previousState?: Room;
  timestamp: number;
}

export interface RoomExtensionRequest {
  action: 'generate' | 'suggest' | 'validate';
  door_location?: [number, number];
  door_direction?: 'N' | 'S' | 'E' | 'W';
  current_room_type?: string;
  room_type?: string;
  mode?: GenerationMode;
  room_polygon?: Polygon;
}

export interface RoomExtensionResponse {
  job_id: string;
  room?: Room;
  suggestions?: RoomSuggestion[];
  valid?: boolean;
  error?: string;
  overlapping_room_id?: string;
  message?: string;
}
