// Main TypeScript Contracts Export
// Steganography API Type Definitions

// Export all types from individual contract files
export * from './ktp-generator.types';
export * from './steganography.types';
export * from './experiments.types';
export * from './tasks.types';
export * from './task-results.types';

// Common utility types
export interface ApiResponse<T = any> {
  status: boolean;
  message: string;
  data: T;
}

export interface ApiErrorResponse {
  status: false;
  message: string;
  data: null;
  error: string;
}

export interface PaginatedResponse<T = any> {
  status: boolean;
  message: string;
  data: {
    items: T[];
    total: number;
    page: number;
    limit: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

// HTTP method types
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';

// Common content types
export type ContentType = 'application/json' | 'multipart/form-data' | 'application/x-www-form-urlencoded';

// File upload types
export interface FileUpload {
  file: File;
  filename?: string;
  contentType?: string;
}

// Task status union type
export type TaskStatus = 'PENDING' | 'STARTED' | 'RETRY' | 'FAILURE' | 'SUCCESS';

// Generation types
export type GenerationType = 'unique' | 'repeat';

// K-value range for LSB
export type KValueRange = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;

// Steganography methods
export type SteganographyMethod =
  | 'lsb'
  | 'eceg-lsb'
  | 'eceg-lzw-lsb'
  | 'eceg-huffman-lsb'
  | 'lzw-eceg-lsb'
  | 'huffman-eceg-lsb';

// Compression types
export type CompressionMethod = 'lzw' | 'huffman';

// Cryptography types
export type CryptographyMethod = 'eceg';

// API base URL
export const API_BASE_URL = 'http://localhost:5000/api/v1';

// WebSocket URL
export const WS_BASE_URL = 'ws://localhost:5000/api/v1';

// Endpoint paths
export const ENDPOINTS = {
  // KTP Generator
  KTP_GENERATOR: '/ktp/generator',

  // Steganography LSB
  LSB_CALCULATE_CAPACITY: '/steganography/lsb/calculate-capacity',
  LSB_EMBED: '/steganography/lsb/embed',
  LSB_EXTRACT: '/steganography/lsb/extract',

  // Task monitoring
  TASK_STATUS: '/tasks/:taskId',
  TASK_WEBSOCKET: '/tasks/:taskId/ws',
} as const;

// Helper type for extracting task ID from URL
export type TaskIdFromUrl<T extends string> = T extends `/tasks/${infer U}/ws`
  ? U
  : T extends `/tasks/${infer U}`
  ? U
  : never;

// Generic error types
export interface ValidationError {
  field: string;
  message: string;
  value?: any;
}

export interface FormValidationError {
  detail: string;
  errors?: ValidationError[];
}

// Progress tracking types
export interface ProgressUpdate {
  task_id: string;
  stage: string;
  progress: number; // 0-100
  timestamp?: string;
}

// Metrics types
export interface ImageMetrics {
  mse: number | 'inf';
  psnr: number | 'inf';
  ssim: number | 'inf';
}

export interface CompressionMetrics {
  cr: number | 'inf'; // Compression ratio
  ss: number | 'inf'; // Space saving percentage
}

export interface FullMetrics extends ImageMetrics, CompressionMetrics {}

// Utility type for optional parameters
export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;

// Utility type for required parameters
export type Required<T, K extends keyof T> = T & Required<Pick<T, K>>;