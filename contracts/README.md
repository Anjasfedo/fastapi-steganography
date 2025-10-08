# TypeScript Contracts

This directory contains TypeScript type definitions for the Steganography API, providing type safety and autocompletion for frontend applications that consume the API.

## 📁 File Structure

```
contracts/
├── README.md                    # This file
├── index.ts                     # Main export file with common types
├── ktp-generator.types.ts       # KTP generator API types
├── steganography.types.ts       # LSB steganography API types
├── experiments.types.ts         # Experiment endpoints API types
├── tasks.types.ts               # Task monitoring and WebSocket types
└── task-results.types.ts        # Task result types for all methods
```

## 🔧 Usage

### Installation

```typescript
// Import specific types
import { KtpGeneratorRequest, LsbEmbedRequest } from './contracts/ktp-generator.types';
import { TaskStatusResponse, TaskWebSocketResponse } from './contracts/tasks.types';

// Or import all types
import * as API from './contracts';
```

### Example: Type-Safe API Calls

```typescript
import {
  KtpGeneratorQueryParams,
  LsbCalculateCapacityRequest,
  TaskStatusResponse,
  ExperimentEmbedRequest
} from './contracts';

// KTP Generator
const ktpParams: KtpGeneratorQueryParams = {
  generation_type: 'unique',
  max_bits: 3145696,
  additional_length: 0
};

// LSB Capacity Calculation
const capacityData: LsbCalculateCapacityRequest = {
  file: imageFile,
  k_val: 4
};

// Task Status Check
const handleTaskResponse = (response: TaskStatusResponse) => {
  if (response.data.status === 'SUCCESS') {
    console.log('Task completed:', response.data.result);
  }
};

// Experiment Embed Request
const embedData: ExperimentEmbedRequest = {
  file: coverImage,
  k_val: 4,
  plaintext: "Secret message"
};
```

### Example: WebSocket Integration

```typescript
import { TaskWebSocketResponse, TaskState } from './contracts';

const connectToTask = (taskId: string) => {
  const ws = new WebSocket(`ws://localhost:5000/api/v1/tasks/${taskId}/ws`);

  ws.onmessage = (event) => {
    const data: TaskWebSocketResponse = JSON.parse(event.data);

    console.log(`Task ${data.task_id}: ${data.stage} - ${data.progress}%`);

    if (data.status === 'SUCCESS') {
      console.log('Task completed successfully!');
      ws.close();
    } else if (data.status === 'FAILURE') {
      console.error('Task failed:', data.error);
      ws.close();
    }
  };
};
```

## 📋 Type Categories

### 1. KTP Generator Types (`ktp-generator.types.ts`)

- `KtpGeneratorRequest` - Request parameters for KTP generation
- `KtpGeneratorResponse` - Response types for different generation modes
- `KtpGeneratorQueryParams` - Query parameter interface

### 2. Steganography Types (`steganography.types.ts`)

- `LsbCalculateCapacityRequest/Response` - LSB capacity calculation
- `LsbEmbedRequest/Response` - LSB embedding operations
- `LsbExtractRequest/Response` - LSB extraction operations
- Task result types for LSB operations

### 3. Experiments Types (`experiments.types.ts`)

- Request/response types for all 5 experiment methods:
  - ECEG + LSB
  - ECEG + LZW + LSB
  - ECEG + Huffman + LSB
  - LZW + ECEG + LSB
  - Huffman + ECEG + LSB
- Method-specific parameter types
- Endpoint constants

### 4. Tasks Types (`tasks.types.ts`)

- `TaskStatusResponse` - Task status checking
- `TaskWebSocketResponse` - Real-time task updates
- `TaskProgressMetadata` - Progress tracking
- Generic task result structures

### 5. Task Results Types (`task-results.types.ts`)

- Specific result types for each experiment method
- Embed task result types with method-specific fields
- Extract task result types with metrics
- Task metadata and stage definitions

### 6. Common Types (`index.ts`)

- `ApiResponse<T>` - Generic API response wrapper
- `TaskStatus` - Task status union type
- `GenerationType` - KTP generation types
- `SteganographyMethod` - Available steganography methods
- Endpoint and URL constants
- Utility types

## 🎯 Type Safety Benefits

1. **Compile-time checking** - Catch type errors before runtime
2. **Autocompletion** - IDE support for API parameters and responses
3. **Documentation** - Types serve as inline documentation
4. **Refactoring safety** - Easy to update types across the application
5. **Consistency** - Ensures consistent API usage across the frontend

## 🔄 API Method Reference

### Available Experiment Methods

| Method | Embed Result Fields | Extract Parameters |
|--------|-------------------|-------------------|
| ECEG + LSB | `stego_key, stego_url, k_val, private_key, public_key` | `private_key` |
| ECEG + LZW + LSB | `+ bit_width` | `private_key, bit_width` |
| ECEG + Huffman + LSB | `+ codebook_key, codebook_url` | `private_key, codebook_key` |
| LZW + ECEG + LSB | `+ bit_width` | `private_key, bit_width` |
| Huffman + ECEG + LSB | `+ codebook_key, codebook_url` | `private_key, codebook_key` |

### Response Metrics

All extract operations return the following metrics:
- `mse` - Mean Squared Error
- `psnr` - Peak Signal-to-Noise Ratio
- `ssim` - Structural Similarity Index
- `cr` - Compression Ratio - For compression methods only
- `ss` - Space Saving Percentage - For compression methods only

## 🚀 Integration Examples

### React Component Example

```typescript
import React, { useState, useEffect } from 'react';
import { LsbEmbedRequest, TaskWebSocketResponse } from '../contracts';

const LsbEmbedComponent: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState('');
  const [taskId, setTaskId] = useState<string>('');
  const [progress, setProgress] = useState(0);

  const handleEmbed = async () => {
    if (!file) return;

    const data: LsbEmbedRequest = {
      file,
      message,
      k_val: 4
    };

    const response = await fetch('/api/v1/steganography/lsb/embed', {
      method: 'POST',
      body: formData
    });

    const result = await response.json();
    setTaskId(result.data.task_id);
  };

  useEffect(() => {
    if (!taskId) return;

    const ws = new WebSocket(`ws://localhost:5000/api/v1/tasks/${taskId}/ws`);

    ws.onmessage = (event) => {
      const data: TaskWebSocketResponse = JSON.parse(event.data);
      setProgress(data.progress || 0);
    };

    return () => ws.close();
  }, [taskId]);

  return (
    <div>
      <input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} />
      <input value={message} onChange={(e) => setMessage(e.target.value)} />
      <button onClick={handleEmbed}>Embed Message</button>
      <div>Progress: {progress}%</div>
    </div>
  );
};
```

## 📝 Updating Types

When the API changes, update the corresponding type files:

1. **Add new endpoints** - Update the appropriate file or create new types
2. **Modify existing endpoints** - Update request/response interfaces
3. **Add new fields** - Extend existing interfaces
4. **Remove deprecated fields** - Update or mark as optional

All types are designed to be extensible and backward-compatible where possible.