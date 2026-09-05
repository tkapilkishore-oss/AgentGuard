export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error: {
    code: string;
    message: string;
  } | null;
}

export interface Product {
  id: string;
  merchant_id: string;
  name: string;
  price: string;
  currency: string;
  stock: number;
}

export interface Mandate {
  id: string;
  user_id: string;
  budget_total: string;
  budget_remaining: string;
  merchant_scope: string | null;
  max_transaction_amount: string;
  status: string;
  expires_at: string | null;
}

export interface ProposeResponseData {
  transaction_id: string;
  decision: 'ALLOW' | 'ESCALATE' | 'DENY';
  reason_code: string;
  authoritative_total: number | string;
  expires_at: string;
}

export interface ExecuteResponseData {
  transaction_id: string;
  status: 'success' | 'failed' | 'escalation_required' | 'denied';
  reason_code: string;
  razorpay_payment_id: string | null;
}

export interface AgentChatResponseData {
  agent_thought: string;
  agent_claim: {
    product_id: string;
    claimed_price: string;
    quantity: number;
  };
  firewall_result: ProposeResponseData | null;
}

export interface AuditEventItem {
  seq_id: number;
  id: string;
  transaction_id: string | null;
  event_type: string;
  actor: string;
  payload_hash: string;
  prev_hash: string;
  created_at: string;
}

export interface TransactionSummary {
  id: string;
  product_id: string;
  product_name: string | null;
  claimed_price: string | number;
  authoritative_price: string | number;
  quantity: number;
  authoritative_total: string | number;
  status: string;
  reason_code: string;
  created_at: string;
  executed_at: string | null;
}

export interface TransactionAuditData {
  transaction: TransactionSummary;
  events: AuditEventItem[];
  chain_verified: boolean;
  chain_verification_error: string | null;
}

export interface ConversationAction {
  action_type: string;
  payload?: Record<string, any>;
  ui_tab_target?: string | null;
  scenario_id?: number | null;
}

export interface FollowUpSuggestion {
  label: string;
  query: string;
  intent_target: string;
  rationale: string;
}

export interface ProgressiveDisclosureOffer {
  offer_type: string;
  target_symbol?: string | null;
  target_file?: string | null;
  target_action?: ConversationAction | null;
  prompt_text: string;
}

export interface BrainTrace {
  session_id: string;
  turn_id: number;
  raw_query: string;
  resolved_query: string;
  intent: string;
  is_dynamic_live: boolean;
  live_tool_type?: string | null;
  retrieved_unit_ids: string[];
  top_authority?: string | null;
  safety_verdict: string;
  progressive_action?: string | null;
  llm_provider: string;
  latency_total_ms: number;
  latency_retrieval_ms: number;
  latency_live_ms: number;
  latency_llm_ms: number;
}

export interface AssistantResponse {
  session_id: string;
  turn_id: number;
  message: string;
  intent: string;
  dialogue_act: string;
  evidence_citations: Array<Record<string, any>>;
  live_data_used: boolean;
  live_readings: Record<string, any> | null;
  progressive_disclosure_offer: string | null;
  suggested_followups: Array<FollowUpSuggestion | string>;
  structured_followups?: FollowUpSuggestion[];
  action: ConversationAction | null;
  trace: BrainTrace | null;
}

export interface ConversationTurn {
  turn_id: number;
  timestamp: string;
  user_query: string;
  assistant_response: string;
  intent: string;
  dialogue_act: string;
  resolved_entities: Record<string, string>;
  retrieved_evidence_ids: string[];
  live_tool_called?: string | null;
  action_triggered?: ConversationAction | null;
  progressive_offer?: ProgressiveDisclosureOffer | null;
  latency_ms: number;
}

export interface TopicContext {
  topic_name: string;
  parent_topic?: string | null;
  depth: number;
  started_at: string;
  last_active_turn: number;
  key_symbols: string[];
  key_entities: Record<string, string>;
}

export interface ConversationSession {
  session_id: string;
  user_id: string;
  created_at: string;
  updated_at: string;
  history: ConversationTurn[];
  active_topic: TopicContext | null;
  topic_history: TopicContext[];
  active_entities: Record<string, string>;
  pending_progressive_offer: ProgressiveDisclosureOffer | null;
  metadata: Record<string, any>;
}

export interface ConversationalQueryRequest {
  query: string;
  session_id?: string | null;
  user_id?: string;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function fetchEnvelope<T>(
  url: string,
  options?: RequestInit
): Promise<{ status: number; envelope: ApiResponse<T> }> {
  try {
    const res = await fetch(`${API_BASE_URL}${url}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    const envelope: ApiResponse<T> = await res.json();
    return { status: res.status, envelope };
  } catch (err: any) {
    if (err?.name === 'AbortError') {
      return {
        status: 499,
        envelope: {
          success: false,
          data: null,
          error: {
            code: 'REQUEST_ABORTED',
            message: 'Request was cancelled by user action.',
          },
        },
      };
    }
    return {
      status: 500,
      envelope: {
        success: false,
        data: null,
        error: {
          code: 'NETWORK_ERROR',
          message: err instanceof Error ? err.message : 'Failed to connect to firewall backend',
        },
      },
    };
  }
}

export const api = {
  async getProducts(): Promise<ApiResponse<Product[]>> {
    const { envelope } = await fetchEnvelope<Product[]>('/products');
    return envelope;
  },

  async getMandate(mandateId = 'mandate-001'): Promise<ApiResponse<Mandate>> {
    const { envelope } = await fetchEnvelope<Mandate>(`/mandate/${mandateId}`);
    return envelope;
  },

  async revokeMandate(mandateId = 'mandate-001'): Promise<{ status: number; envelope: ApiResponse<any> }> {
    return fetchEnvelope<any>(`/mandate/${mandateId}/revoke`, {
      method: 'POST',
    });
  },

  async resetDemoMandate(): Promise<{ status: number; envelope: ApiResponse<any> }> {
    return fetchEnvelope<any>('/internal/demo/reset-mandate', {
      method: 'POST',
      headers: {
        'X-Demo-Control': 'agentguard-autonomous-demo',
      },
    });
  },

  async proposeTransaction(payload: {
    user_id?: string;
    mandate_id?: string;
    product_id: string;
    claimed_price: number;
    quantity?: number;
  }): Promise<{ status: number; envelope: ApiResponse<ProposeResponseData> }> {
    return fetchEnvelope<ProposeResponseData>('/transaction/propose', {
      method: 'POST',
      body: JSON.stringify({
        user_id: payload.user_id || 'user-001',
        mandate_id: payload.mandate_id || 'mandate-001',
        agent_claim: {
          product_id: payload.product_id,
          claimed_price: payload.claimed_price,
          quantity: payload.quantity || 1,
        },
      }),
    });
  },

  async executeTransaction(payload: {
    transaction_id: string;
    idempotency_key?: string;
  }): Promise<{ status: number; envelope: ApiResponse<ExecuteResponseData> }> {
    const key = payload.idempotency_key || `idemp-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
    return fetchEnvelope<ExecuteResponseData>('/transaction/execute', {
      method: 'POST',
      body: JSON.stringify({
        transaction_id: payload.transaction_id,
        idempotency_key: key,
      }),
    });
  },

  async approveTransaction(transactionId: string): Promise<{ status: number; envelope: ApiResponse<any> }> {
    return fetchEnvelope<any>(`/transaction/${transactionId}/approve`, {
      method: 'POST',
    });
  },

  async rejectTransaction(transactionId: string): Promise<{ status: number; envelope: ApiResponse<any> }> {
    return fetchEnvelope<any>(`/transaction/${transactionId}/reject`, {
      method: 'POST',
    });
  },

  async agentChat(prompt: string, user_id = 'user-001', mandate_id = 'mandate-001'): Promise<{ status: number; envelope: ApiResponse<AgentChatResponseData> }> {
    return fetchEnvelope<AgentChatResponseData>('/agent/chat', {
      method: 'POST',
      body: JSON.stringify({
        user_id,
        mandate_id,
        prompt,
      }),
    });
  },

  async getTransactions(): Promise<{ status: number; envelope: ApiResponse<TransactionSummary[]> }> {
    return fetchEnvelope<TransactionSummary[]>('/transactions');
  },

  async getTransactionAudit(transactionId: string): Promise<{ status: number; envelope: ApiResponse<TransactionAuditData> }> {
    return fetchEnvelope<TransactionAuditData>(`/transaction/${transactionId}/audit`);
  },

  // Phase 5.5B-3/B-4 Conversational Brain endpoints
  async conversationalQuery(
    payload: ConversationalQueryRequest,
    signal?: AbortSignal
  ): Promise<{ status: number; envelope: ApiResponse<AssistantResponse> }> {
    return fetchEnvelope<AssistantResponse>('/conversational/query', {
      method: 'POST',
      body: JSON.stringify({
        query: payload.query,
        session_id: payload.session_id || null,
        user_id: payload.user_id || 'user-001',
      }),
      signal,
    });
  },

  async getConversationalSession(
    sessionId: string,
    signal?: AbortSignal
  ): Promise<{ status: number; envelope: ApiResponse<ConversationSession> }> {
    return fetchEnvelope<ConversationSession>(`/conversational/session/${encodeURIComponent(sessionId)}`, {
      method: 'GET',
      signal,
    });
  },

  async resetConversationalSession(
    sessionId: string,
    signal?: AbortSignal
  ): Promise<{ status: number; envelope: ApiResponse<{ session_id: string; status: string }> }> {
    return fetchEnvelope<{ session_id: string; status: string }>(
      `/conversational/session/${encodeURIComponent(sessionId)}`,
      {
        method: 'DELETE',
        signal,
      }
    );
  },

  async synthesizeSpeech(
    text: string,
    signal?: AbortSignal
  ): Promise<{ status: number; blob: Blob | null; error?: string }> {
    try {
      const res = await fetch(`${API_BASE_URL}/tts/synthesize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text }),
        signal,
      });

      if (!res.ok) {
        let errMessage = 'Failed to synthesize speech';
        try {
          const errJson = await res.json();
          errMessage = errJson?.error?.message || errJson?.detail?.message || errMessage;
        } catch {
          // fallback
        }
        return { status: res.status, blob: null, error: errMessage };
      }

      const blob = await res.blob();
      return { status: res.status, blob };
    } catch (err: any) {
      if (err?.name === 'AbortError') {
        return { status: 499, blob: null, error: 'Request was cancelled' };
      }
      return {
        status: 500,
        blob: null,
        error: err instanceof Error ? err.message : 'Network error during speech synthesis',
      };
    }
  },
};
