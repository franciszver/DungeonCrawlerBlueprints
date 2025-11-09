import axios from 'axios';
import type { 
  UploadResponse, 
  DetectionResult, 
  RoomExtensionRequest, 
  RoomExtensionResponse,
  GenerationMode,
  Polygon 
} from '../types';

const API_URL = import.meta.env.VITE_API_URL || '';
const API_KEY = import.meta.env.VITE_API_KEY || '';

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
    'x-api-key': API_KEY,
  },
});

export const uploadBlueprint = async (file: File): Promise<UploadResponse> => {
  // Convert file to base64
  const base64 = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      // Remove data URL prefix
      const base64 = result.split(',')[1];
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });

  const response = await apiClient.post<UploadResponse>('/upload', {
    file: base64,
    source_type: 'image',
  });

  return response.data;
};

export const detectRooms = async (
  blueprintId: string, 
  jobId?: string,
  onProgress?: (current: number, total: number) => void
): Promise<DetectionResult> => {
  const response = await apiClient.post<DetectionResult>('/detect', {
    blueprint_id: blueprintId,
    job_id: jobId,
  });

  // If async processing (202), poll for results
  if (response.status === 202) {
    const asyncJobId = response.data.job_id;
    
    // Poll every 2 seconds for up to 6 minutes (to allow for complex blueprints + validation retry)
    // Increased from 3 minutes to handle longer processing times
    const maxAttempts = 180; // 180 attempts * 2 seconds = 6 minutes
    let attempts = 0;
    
    while (attempts < maxAttempts) {
      await new Promise(resolve => setTimeout(resolve, 2000));
      attempts++;
      
      // Report progress
      if (onProgress) {
        onProgress(attempts, maxAttempts);
      }
      
      try {
        const result = await getResults(asyncJobId);
        console.log(`Polling attempt ${attempts}/${maxAttempts}: status=${result.status}`);
        
        if (result.status === 'completed') {
          console.log('Detection completed successfully!');
          return result;
        } else if (result.status === 'failed') {
          throw new Error(result.error || 'Detection failed');
        }
        // Continue polling if status is 'processing'
      } catch (error: any) {
        // Only log errors that aren't "not found" (job might not be ready yet)
        if (error.response?.status !== 404) {
          console.log(`Polling attempt ${attempts} error:`, error);
        }
        // Continue polling on errors (job might not be ready yet)
        if (attempts >= maxAttempts) {
          // Return a processing result so user can manually check later
          throw new Error(`Detection is taking longer than expected (${Math.floor(maxAttempts * 2 / 60)} minutes). Your job ID is ${asyncJobId} - you can check results manually using the "Check Results" button.`);
        }
      }
    }
    
    throw new Error(`Detection timeout after ${Math.floor(maxAttempts * 2 / 60)} minutes. Your job ID is ${asyncJobId} - please use the "Check Results" button to check if processing completed.`);
  }

  return response.data;
};

export const getResults = async (jobId: string): Promise<DetectionResult> => {
  const response = await apiClient.get<DetectionResult>(`/results/${jobId}`);
  return response.data;
};

export const exportResults = async (jobId: string, format: 'json' | 'svg' = 'json'): Promise<Blob> => {
  const response = await apiClient.get(`/export/${jobId}`, {
    params: { format },
    responseType: 'blob',
  });

  return response.data;
};

// Room Extension API Functions

export const getRoomSuggestions = async (
  jobId: string,
  doorDirection: 'N' | 'S' | 'E' | 'W',
  currentRoomType: string,
  mode: GenerationMode = 'realistic'
): Promise<RoomExtensionResponse> => {
  const request: RoomExtensionRequest = {
    action: 'suggest',
    door_direction: doorDirection,
    current_room_type: currentRoomType,
    mode,
  };

  const response = await apiClient.post<RoomExtensionResponse>(`/extend/${jobId}`, request);
  return response.data;
};

export const generateRoom = async (
  jobId: string,
  doorLocation: [number, number],
  doorDirection: 'N' | 'S' | 'E' | 'W',
  currentRoomType: string,
  roomType?: string,
  mode: GenerationMode = 'realistic'
): Promise<RoomExtensionResponse> => {
  const request: RoomExtensionRequest = {
    action: 'generate',
    door_location: doorLocation,
    door_direction: doorDirection,
    current_room_type: currentRoomType,
    room_type: roomType,
    mode,
  };

  const response = await apiClient.post<RoomExtensionResponse>(`/extend/${jobId}`, request);
  return response.data;
};

export const validateRoomPlacement = async (
  jobId: string,
  roomPolygon: Polygon
): Promise<RoomExtensionResponse> => {
  const request: RoomExtensionRequest = {
    action: 'validate',
    room_polygon: roomPolygon,
  };

  const response = await apiClient.post<RoomExtensionResponse>(`/extend/${jobId}`, request);
  return response.data;
};

export const updatePlan = async (
  jobId: string,
  modifiedRooms?: any[],
  extendedRooms?: any[],
  doors?: any[]
): Promise<{ job_id: string; message: string }> => {
  const request: any = {
    action: 'update_plan',
  };
  
  if (modifiedRooms !== undefined) {
    request.modified_rooms = modifiedRooms;
  }
  if (extendedRooms !== undefined) {
    request.extended_rooms = extendedRooms;
  }
  if (doors !== undefined) {
    request.doors = doors;
  }

  const response = await apiClient.post<{ job_id: string; message: string }>(`/extend/${jobId}`, request);
  return response.data;
};

export interface RefineRoomBoundariesResponse {
  success: boolean;
  rooms: any[];
  extended_rooms: any[];
  modified_rooms: any[];
  stats: {
    total_rooms: number;
    refined_rooms: number;
    vertices_snapped: number;
    average_snap_distance: number;
  };
}

export const refineRoomBoundaries = async (
  jobId: string,
  threshold: number = 50
): Promise<RefineRoomBoundariesResponse> => {
  const response = await apiClient.post<RefineRoomBoundariesResponse>(
    `/refine/${jobId}`,
    { threshold }
  );
  return response.data;
};

