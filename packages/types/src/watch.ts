export type SensorPreference = 'auto' | 'optical' | 'sar' | 'free';
export type WatchStatus = 'active' | 'paused' | 'error';
export type WatchFrequency = 'once' | 'daily' | 'weekly' | 'monthly';

export interface GeoJsonPolygon {
  type: 'Polygon';
  coordinates: number[][][];
}

export interface WatchCreate {
  name: string;
  question: string;
  aoi: GeoJsonPolygon;
  sensor_preference: SensorPreference;
  frequency: WatchFrequency;
  alert_threshold?: string;
}

export interface Watch extends WatchCreate {
  id: string;
  created_at: string;
  updated_at: string;
  status: WatchStatus;
  last_run_at?: string;
  next_run_at?: string;
}
