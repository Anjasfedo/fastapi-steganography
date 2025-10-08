// Task Result Types for All Experiment Methods
// Based on actual return values from tasks/experiments/*.py files

// Base task result structure
export interface BaseTaskResult<T> {
  task_id: string;
  status: "SUCCESS";
  result: T;
}

// LSB Task Results
export interface LsbEmbedTaskResult {
  stego_key: string;
  stego_url: string;
  k_val: number;
  job_id: string;
}

export interface LsbExtractTaskResult {
  record: string; // Extracted message
  metrics: {
    mse: number | "inf";
    psnr: number | "inf";
    ssim: number | "inf";
  };
}

// ECEG + LSB Task Results
export interface EcegLsbEmbedTaskResult {
  stego_key: string;
  stego_url: string;
  k_val: number;
  private_key: number;
  public_key: number;
}

export interface EcegLsbExtractTaskResult {
  record: string; // Decrypted message
  metrics: {
    mse: number | "inf";
    psnr: number | "inf";
    ssim: number | "inf";
    cr: number | "inf";
    ss: number | "inf";
  };
}

// ECEG + LZW + LSB Task Results
export interface EcegLzwLsbEmbedTaskResult {
  stego_key: string;
  stego_url: string;
  k_val: number;
  bit_width: number;
  private_key: number;
  public_key: number;
}

export interface EcegLzwLsbExtractTaskResult {
  record: string; // Decompressed decrypted message
  metrics: {
    mse: number | "inf";
    psnr: number | "inf";
    ssim: number | "inf";
    cr: number | "inf";
    ss: number | "inf";
  };
}

// ECEG + Huffman + LSB Task Results
export interface EcegHuffmanLsbEmbedTaskResult {
  stego_key: string;
  stego_url: string;
  k_val: number;
  codebook_key: string;
  codebook_url: string;
  private_key: number;
  public_key: number;
}

export interface EcegHuffmanLsbExtractTaskResult {
  record: string; // Decompressed decrypted message
  metrics: {
    mse: number | "inf";
    psnr: number | "inf";
    ssim: number | "inf";
    cr: number | "inf";
    ss: number | "inf";
  };
}

// LZW + ECEG + LSB Task Results
export interface LzwEcegLsbEmbedTaskResult {
  stego_key: string;
  stego_url: string;
  k_val: number;
  bit_width: number;
  private_key: number;
  public_key: number;
}

export interface LzwEcegLsbExtractTaskResult {
  record: string; // Decompressed decrypted message
  metrics: {
    mse: number | "inf";
    psnr: number | "inf";
    ssim: number | "inf";
    cr: number | "inf";
    ss: number | "inf";
  };
}

// Huffman + ECEG + LSB Task Results
export interface HuffmanEcegLsbEmbedTaskResult {
  stego_key: string;
  stego_url: string;
  k_val: number;
  codebook_key: string;
  codebook_url: string;
  private_key: number;
  public_key: number;
}

export interface HuffmanEcegLsbExtractTaskResult {
  record: string; // Decompressed decrypted message
  metrics: {
    mse: number | "inf";
    psnr: number | "inf";
    ssim: number | "inf";
    cr: number | "inf";
    ss: number | "inf";
  };
}

// LZW + LSB Task Results (from lzw_lsb.py)
export interface LzwLsbEmbedTaskResult {
  stego_key: string;
  stego_url: string;
  k_val: number;
  bit_width: number;
}

export interface LzwLsbExtractTaskResult {
  record: string; // Decompressed message
  metrics: {
    mse: number | "inf";
    psnr: number | "inf";
    ssim: number | "inf";
    cr: number | "inf";
    ss: number | "inf";
  };
}

// Huffman + LSB Task Results (from huffman_coding_lsb.py)
export interface HuffmanLsbEmbedTaskResult {
  stego_key: string;
  stego_url: string;
  k_val: number;
  codebook_key: string;
  codebook_url: string;
}

export interface HuffmanLsbExtractTaskResult {
  record: string; // Decompressed message
  metrics: {
    mse: number | "inf";
    psnr: number | "inf";
    ssim: number | "inf";
    cr: number | "inf";
    ss: number | "inf";
  };
}

// Task result union types
export type EmbedTaskResult =
  | LsbEmbedTaskResult
  | EcegLsbEmbedTaskResult
  | EcegLzwLsbEmbedTaskResult
  | EcegHuffmanLsbEmbedTaskResult
  | LzwEcegLsbEmbedTaskResult
  | HuffmanEcegLsbEmbedTaskResult
  | LzwLsbEmbedTaskResult
  | HuffmanLsbEmbedTaskResult;

export type ExtractTaskResult =
  | LsbExtractTaskResult
  | EcegLsbExtractTaskResult
  | EcegLzwLsbExtractTaskResult
  | EcegHuffmanLsbExtractTaskResult
  | LzwEcegLsbExtractTaskResult
  | HuffmanEcegLsbExtractTaskResult
  | LzwLsbExtractTaskResult
  | HuffmanLsbExtractTaskResult;

// Complete task response types
export type EmbedTaskResponse<T extends EmbedTaskResult = EmbedTaskResult> = BaseTaskResult<T>;

export type ExtractTaskResponse<T extends ExtractTaskResult = ExtractTaskResult> = BaseTaskResult<T>;

// Task metadata types (from update_state calls)
export interface TaskMetadata {
  stage: string;
  progress: number;
  [key: string]: string | number | boolean | undefined;
}

// ECEG task metadata stages
export interface EcegTaskStages {
  "Generating Keys": TaskMetadata;
  "Processing Plaintext": TaskMetadata;
  "Encrypted": TaskMetadata;
  "Embedded": TaskMetadata;
}

// Compression task metadata stages
export interface CompressionTaskStages {
  "Processing Plaintext": TaskMetadata;
  "Compressed": TaskMetadata;
  "Encrypted": TaskMetadata;
  "Embedded": TaskMetadata;
}

// Extraction task metadata stages
export interface ExtractionTaskStages {
  "Downloaded": TaskMetadata;
  "Extracted": TaskMetadata;
  "Decrypted": TaskMetadata;
  "Decompressed": TaskMetadata;
  "Processing plaintext": TaskMetadata;
  "Plaintext Ready": TaskMetadata;
}