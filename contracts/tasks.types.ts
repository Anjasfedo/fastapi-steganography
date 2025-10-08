// Task Monitoring TypeScript Contracts
// API Endpoints: /api/v1/tasks/*

import {
  EmbedTaskResult,
  ExtractTaskResult,
  LsbEmbedTaskResult,
  LsbExtractTaskResult,
  EcegLsbEmbedTaskResult,
  EcegLsbExtractTaskResult,
  EcegLzwLsbEmbedTaskResult,
  EcegLzwLsbExtractTaskResult,
  EcegHuffmanLsbEmbedTaskResult,
  EcegHuffmanLsbExtractTaskResult,
  LzwEcegLsbEmbedTaskResult,
  LzwEcegLsbExtractTaskResult,
  HuffmanEcegLsbEmbedTaskResult,
  HuffmanEcegLsbExtractTaskResult,
  LzwLsbEmbedTaskResult,
  LzwLsbExtractTaskResult,
  HuffmanLsbEmbedTaskResult,
  HuffmanLsbExtractTaskResult
} from './task-results.types';

export interface TaskStatusResponse {
  status: boolean;
  message: string;
  data: TaskStatusData;
}

export interface TaskStatusData {
  task_id: string;
  status: TaskState;
  error?: TaskErrorInfo;
  result?:
    | LsbEmbedTaskResult
    | LsbExtractTaskResult
    | EcegLsbEmbedTaskResult
    | EcegLsbExtractTaskResult
    | EcegLzwLsbEmbedTaskResult
    | EcegLzwLsbExtractTaskResult
    | EcegHuffmanLsbEmbedTaskResult
    | EcegHuffmanLsbExtractTaskResult
    | LzwEcegLsbEmbedTaskResult
    | LzwEcegLsbExtractTaskResult
    | HuffmanEcegLsbEmbedTaskResult
    | HuffmanEcegLsbExtractTaskResult
    | LzwLsbEmbedTaskResult
    | LzwLsbExtractTaskResult
    | HuffmanLsbEmbedTaskResult
    | HuffmanLsbExtractTaskResult;
  info?: TaskInfo;
}

export type TaskState = "PENDING" | "STARTED" | "RETRY" | "FAILURE" | "SUCCESS";

export interface TaskErrorInfo {
  type: string;
  message: string;
  traceback: string;
}

export interface TaskInfo {
  [key: string]: string | number | boolean; // Custom metadata from update_state calls
}

// WebSocket responses
export interface TaskWebSocketResponse {
  task_id: string;
  status: TaskState;
  stage?: string;
  progress?: number;
  [key: string]: string | number | boolean | undefined; // Additional metadata from update_state
}

export interface TaskWebSocketErrorResponse {
  task_id: string;
  status: "ERROR";
  error: string;
}

// Generic task success response structure
export interface TaskSuccessResponse<
  T =
    | LsbEmbedTaskResult
    | LsbExtractTaskResult
    | EcegLsbEmbedTaskResult
    | EcegLsbExtractTaskResult
    | EcegLzwLsbEmbedTaskResult
    | EcegLzwLsbExtractTaskResult
    | EcegHuffmanLsbEmbedTaskResult
    | EcegHuffmanLsbExtractTaskResult
    | LzwEcegLsbEmbedTaskResult
    | LzwEcegLsbExtractTaskResult
    | HuffmanEcegLsbEmbedTaskResult
    | HuffmanEcegLsbExtractTaskResult
    | LzwLsbEmbedTaskResult
    | LzwLsbExtractTaskResult
    | HuffmanLsbEmbedTaskResult
    | HuffmanLsbExtractTaskResult
> {
  task_id: string;
  status: "SUCCESS";
  result: T;
}

// Embed task result types (deprecated - use specific types from task-results.types.ts)
export interface EmbedTaskResult {
  stego_key: string;
  stego_url: string;
  k_val: number;
  // Additional fields vary by method
  private_key?: number; // ECEG methods
  public_key?: number;  // ECEG methods
  codebook_key?: string; // Huffman methods
  codebook_url?: string; // Huffman methods
  bit_width?: number; // LZW methods
}

// Extract task result types (deprecated - use specific types from task-results.types.ts)
export interface ExtractTaskResult {
  record: string; // Extracted/decrypted message
  metrics: StegoMetrics;
}

export interface StegoMetrics {
  mse: number | "inf";
  psnr: number | "inf";
  ssim: number | "inf";
  cr?: number | "inf"; // Compression ratio - Compression methods only
  ss?: number | "inf"; // Space saving percentage - Compression methods only
}

// Progress tracking metadata
export interface TaskProgressMetadata {
  stage: string;
  progress: number; // 0-100
}

// Example metadata from different task types
export interface EcegTaskMetadata extends TaskProgressMetadata {
  stage: "Generating Keys" | "Processing Plaintext" | "Encrypted" | "Embedded";
}

export interface CompressionTaskMetadata extends TaskProgressMetadata {
  stage: "Processing Plaintext" | "Compressed" | "Encrypted" | "Embedded";
}

export interface ExtractionTaskMetadata extends TaskProgressMetadata {
  stage: "Downloaded" | "Extracted" | "Decrypted" | "Decompressed" | "Plaintext Ready";
}