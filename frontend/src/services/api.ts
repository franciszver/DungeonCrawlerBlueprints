import axios from 'axios';
import type { UploadResponse, DetectionResult } from '../types';

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

export const detectRooms = async (blueprintId: string, jobId?: string): Promise<DetectionResult> => {
  const response = await apiClient.post<DetectionResult>('/detect', {
    blueprint_id: blueprintId,
    job_id: jobId,
  });

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

