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

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function fetchEnvelope<T>(url: string, options?: RequestInit): Promise<{ status: number; envelope: ApiResponse<T> }> {
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
  } catch (err) {
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
};
