// KTP Generator TypeScript Contracts
// API Endpoints: /api/v1/ktp/*

export interface KtpGeneratorRequest {
  generation_type?: 'unique' | 'repeat';
  max_bits?: number;
  additional_length?: number;
}

export interface KtpGeneratorResponse {
  status: boolean;
  message: string;
  data: string | string[];
}

export interface KtpGeneratorQueryParams {
  generation_type?: 'unique' | 'repeat';
  max_bits?: number;
  additional_length?: number;
}

// Response examples
export interface KtpGeneratorSingleResponse {
  status: true;
  message: "Successfully generated 1 KTP records";
  data: string; // Merged KTP string format
}

export interface KtpGeneratorMultipleResponse {
  status: true;
  message: "Successfully generated 5 KTP records";
  data: string[]; // Array of merged KTP strings
}

export interface KtpGeneratorTargetedResponse {
  status: true;
  message: "Successfully generated KTP data with target bit size 3145696";
  data: string; // Long repeated KTP string for target length
}

export interface KtpGeneratorErrorResponse {
  status: false;
  message: "An unexpected server error occurred";
  data: null;
  error: string;
}