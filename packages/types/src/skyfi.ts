export interface SkyFiArchiveResult {
  id: string;
  provider: string;
  satellite: string;
  sensorType: 'optical' | 'sar' | 'multispectral' | 'hyperspectral';
  resolution: number;
  cloudCover?: number;
  capturedAt: string;
  thumbnailUrl?: string;
  price: number;
  openData: boolean;
  bbox: [number, number, number, number];
}

export interface SkyFiOrderResponse {
  orderId: string;
  status: string;
  estimatedDelivery?: string;
}

export interface SkyFiAnalyticsProduct {
  id: string;
  name: string;
  description: string;
  pricePerSqKm: number;
  supportedSensors: string[];
  category: 'object_detection' | 'change_detection' | 'material_detection' | 'topographic';
}

export interface SkyFiPassPrediction {
  satellite: string;
  provider: string;
  predictedAt: string;
  resolution: number;
  sensorType: string;
}
