export interface AgentThought {
  step: number;
  toolCalled?: string;
  toolInput?: Record<string, unknown>;
  toolOutput?: Record<string, unknown>;
}

export interface AgentRun {
  watchId: string;
  orderId: string;
  thoughts: AgentThought[];
  finalAnswer?: string;
  error?: string;
}
