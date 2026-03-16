import type { AgentThought } from './agent';

export type OrderStatus =
  | 'pending'
  | 'processing'
  | 'complete'
  | 'failed'
  | 'interpreting'
  | 'answered';

export interface EvidenceItem {
  type: 'count' | 'comparison' | 'detection' | 'measurement';
  description: string;
  value?: number | string;
}

export interface OrderResult {
  answer: string;
  confidence: 'high' | 'medium' | 'low';
  evidence: EvidenceItem[];
  rawAnalytics?: Record<string, unknown>;
  imageryUrl?: string;
  capturedAt?: string;
}

export interface Order {
  id: string;
  watchId: string;
  skyfiOrderId?: string;
  skyfiArchiveId?: string;
  status: OrderStatus;
  sensorType: string;
  analyticsType?: string;
  costUsd?: number;
  createdAt: string;
  updatedAt: string;
  result?: OrderResult;
  agentThoughts?: AgentThought[];
}
