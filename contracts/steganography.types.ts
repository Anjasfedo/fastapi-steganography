// Steganography LSB TypeScript Contracts
// API Endpoints: /api/v1/steganography/lsb/*

export interface LsbCalculateCapacityRequest {
  file: File; // PNG image
  k_val: number; // 1-8
}

export interface LsbCalculateCapacityResponse {
  status: boolean;
  message: string;
  data: {
    max_chars: number;
    max_bits: number;
    k_val: number;
    notes: string;
    dimensions: {
      width: number;
      height: number;
    };
  };
}

export interface LsbEmbedRequest {
  file: File; // PNG cover image
  message: string; // Secret message to hide
  k_val: number; // 1-8
}

export interface LsbEmbedResponse {
  status: boolean;
  message: string;
  data: {
    task_id: string;
    status: "PENDING";
    check: string; // `/tasks/${task_id}`
    job_id: string;
    cover_key: string;
    notes: string;
  };
}

export interface LsbExtractRequest {
  file: File; // PNG stego image
  original: File; // PNG original image
  k_val: number; // 1-8
}

export interface LsbExtractResponse {
  status: boolean;
  message: string;
  data: {
    task_id: string;
    status: "PENDING";
    check: string; // `/tasks/${task_id}`
    job_id: string;
    stego_key: string;
    original_key: string;
    notes: string;
  };
}

// Task success responses
export interface LsbEmbedTaskSuccessResponse {
  task_id: string;
  status: "SUCCESS";
  result: {
    stego_key: string;
    stego_url: string;
    k_val: number;
    job_id: string;
  };
}

export interface LsbExtractTaskSuccessResponse {
  task_id: string;
  status: "SUCCESS";
  result: {
    record: string; // Extracted message
    metrics: {
      mse: number | "inf";
      psnr: number | "inf";
      ssim: number | "inf";
    };
  };
}

// Error responses
export interface LsbCapacityErrorResponse {
  status: false;
  message: "Failed to calculate capacity";
  error: string;
}

export interface LsbEmbedErrorResponse {
  status: false;
  message: "Embedding failed";
  error: string;
}

export interface LsbPayloadTooLargeResponse {
  status: false;
  message: "Payload Too Large";
  error: string; // "Ukuran pesan (X karakter) melebihi kapasitas maksimum gambar (Y karakter)."
}