// Experiments TypeScript Contracts
// API Endpoints: /api/v1/experiments/*

import { TaskSuccessResponse, EmbedTaskResult, ExtractTaskResult } from './tasks.types';

// Base experiment request types
export interface BaseExperimentEmbedRequest {
  file: File; // PNG cover image
  k_val: number; // 1-8
  plaintext: string; // Message to embed
}

export interface BaseExperimentExtractRequest {
  stego_image: File; // PNG stego image
  original_image?: File; // PNG original image - optional, required for steganography metrics
  k_val: number; // 1-8
  private_key?: number; // For ECEG decryption
}

// Base response types
export interface ExperimentEmbedResponse {
  status: boolean;
  message: string;
  data: {
    task_id: string;
    status: "PENDING";
  };
}

export interface ExperimentExtractResponse {
  status: boolean;
  message: string;
  data: {
    task_id: string;
    status: "PENDING";
  };
}

// Method-specific extract request types
export interface LzwExperimentExtractRequest extends BaseExperimentExtractRequest {
  bit_width: number; // For LZW decompression
}

export interface HuffmanExperimentExtractRequest extends BaseExperimentExtractRequest {
  codebook_key: string; // For Huffman decompression
}

// ECEG + LSB
export interface EcegLsbEmbedRequest extends BaseExperimentEmbedRequest {}
export interface EcegLsbExtractRequest extends BaseExperimentExtractRequest {}

export interface EcegLsbEmbedResult extends EmbedTaskResult {
  private_key: number;
  public_key: number;
}

// ECEG + LZW + LSB
export interface EcegLzwLsbEmbedRequest extends BaseExperimentEmbedRequest {}
export interface EcegLzwLsbExtractRequest extends LzwExperimentExtractRequest {}

export interface EcegLzwLsbEmbedResult extends EmbedTaskResult {
  private_key: number;
  public_key: number;
  bit_width: number;
}

// ECEG + Huffman + LSB
export interface EcegHuffmanLsbEmbedRequest extends BaseExperimentEmbedRequest {}
export interface EcegHuffmanLsbExtractRequest extends HuffmanExperimentExtractRequest {}

export interface EcegHuffmanLsbEmbedResult extends EmbedTaskResult {
  private_key: number;
  public_key: number;
  codebook_key: string;
  codebook_url: string;
}

// LZW + ECEG + LSB
export interface LzwEcegLsbEmbedRequest extends BaseExperimentEmbedRequest {}
export interface LzwEcegLsbExtractRequest extends LzwExperimentExtractRequest {}

export interface LzwEcegLsbEmbedResult extends EmbedTaskResult {
  private_key: number;
  public_key: number;
  bit_width: number;
}

// Huffman + ECEG + LSB
export interface HuffmanEcegLsbEmbedRequest extends BaseExperimentEmbedRequest {}
export interface HuffmanEcegLsbExtractRequest extends HuffmanExperimentExtractRequest {}

export interface HuffmanEcegLsbEmbedResult extends EmbedTaskResult {
  private_key: number;
  public_key: number;
  codebook_key: string;
  codebook_url: string;
}

// Task success responses with specific result types
export type EcegLsbTaskSuccessResponse = TaskSuccessResponse<EcegLsbEmbedResult>;
export type EcegLzwLsbTaskSuccessResponse = TaskSuccessResponse<EcegLzwLsbEmbedResult>;
export type EcegHuffmanLsbTaskSuccessResponse = TaskSuccessResponse<EcegHuffmanLsbEmbedResult>;
export type LzwEcegLsbTaskSuccessResponse = TaskSuccessResponse<LzwEcegLsbEmbedResult>;
export type HuffmanEcegLsbTaskSuccessResponse = TaskSuccessResponse<HuffmanEcegLsbEmbedResult>;

// All extract task responses have the same structure
export type ExperimentExtractTaskSuccessResponse = TaskSuccessResponse<ExtractTaskResult>;

// Error responses
export interface ExperimentErrorResponse {
  status: false;
  message: string;
  data: null;
  error: string;
}

// API endpoint mapping
export const EXPERIMENT_ENDPOINTS = {
  // ECEG + LSB
  EMBED_ECEG_LSB: '/experiments/eceg-lsb/embed',
  EXTRACT_ECEG_LSB: '/experiments/eceg-lsb/extract',

  // ECEG + LZW + LSB
  EMBED_ECEG_LZW_LSB: '/experiments/eceg-lzw-lsb/embed',
  EXTRACT_ECEG_LZW_LSB: '/experiments/eceg-lzw-lsb/extract',

  // ECEG + Huffman + LSB
  EMBED_ECEG_HUFFMAN_LSB: '/experiments/eceg-huffman-coding-lsb/embed',
  EXTRACT_ECEG_HUFFMAN_LSB: '/experiments/eceg-huffman-coding-lsb/extract',

  // LZW + ECEG + LSB
  EMBED_LZW_ECEG_LSB: '/experiments/lzw-eceg-lsb/embed',
  EXTRACT_LZW_ECEG_LSB: '/experiments/lzw-eceg-lsb/extract',

  // Huffman + ECEG + LSB
  EMBED_HUFFMAN_ECEG_LSB: '/experiments/huffman-coding-eceg-lsb/embed',
  EXTRACT_HUFFMAN_ECEG_LSB: '/experiments/huffman-coding-eceg-lsb/extract',
} as const;

// Method type union for easier type handling
export type ExperimentEmbedRequest =
  | EcegLsbEmbedRequest
  | EcegLzwLsbEmbedRequest
  | EcegHuffmanLsbEmbedRequest
  | LzwEcegLsbEmbedRequest
  | HuffmanEcegLsbEmbedRequest;

export type ExperimentExtractRequest =
  | EcegLsbExtractRequest
  | EcegLzwLsbExtractRequest
  | EcegHuffmanLsbExtractRequest
  | LzwEcegLsbExtractRequest
  | HuffmanEcegLsbExtractRequest;