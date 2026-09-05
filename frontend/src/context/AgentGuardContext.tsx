import React, { createContext, useContext, useState, useEffect, useCallback, useRef, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  api,
  Mandate,
  Product,
  ProposeResponseData,
  ExecuteResponseData,
  TransactionSummary,
  TransactionAuditData,
  AssistantResponse,
  ConversationAction,
  FollowUpSuggestion,
  BrainTrace,
} from '../lib/api';

export interface WireLogEntry {
  endpoint: string;
  method: string;
  status: number;
  requestBody?: any;
  responseBody: any;
  timestamp: string;
  durationMs?: number;
}

export type SurfaceTab = 'DEFENSE' | 'THREAT_LAB' | 'FORENSICS';

export type AgentVoiceState =
  | 'IDLE'
  | 'LISTENING'
  | 'THINKING'
  | 'SPEAKING'
  | 'EXECUTING'
  | 'WAITING_FOR_APPROVAL'
  | 'SUCCESS'
  | 'DENIED'
  | 'ERROR'
  | 'INTERRUPTED';

export interface ChatMessageItem {
  id: string;
  sender: 'user' | 'agent';
  text: string;
  timestamp: string;
  intent?: string;
  dialogueAct?: string;
  liveDataUsed?: boolean;
  liveReadings?: Record<string, any> | null;
  evidenceCitations?: Array<Record<string, any>>;
  suggestedFollowups?: Array<FollowUpSuggestion | string>;
  progressiveOffer?: string | null;
  action?: ConversationAction | null;
  actionStatus?: 'PENDING' | 'EXECUTED' | 'BLOCKED' | 'FAILED';
  actionDescription?: string;
  latencyMs?: number;
  isError?: boolean;
  isAdversarialRefusal?: boolean;
  trace?: BrainTrace | null;
}

const INITIAL_CONVERSATIONAL_MESSAGES: ChatMessageItem[] = [
  {
    id: 'msg-welcome-001',
    sender: 'agent',
    text: "Hello! I am the AgentGuard Conversational Assistant. Grounded directly in the authoritative B-3 security brain, cryptographic audit ledger, and live database state. How can I assist your security review today?",
    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    intent: 'GREETING_OR_META',
    dialogueAct: 'INFORM',
    suggestedFollowups: [
      {
        label: 'What is AgentGuard?',
        query: 'What is AgentGuard?',
        intent_target: 'CONCEPT_EXPLANATION',
        rationale: 'Learn core architecture and trust boundary.',
      },
      {
        label: 'Check Mandate Budget',
        query: 'How much budget is left right now?',
        intent_target: 'LIVE_DATA_QUERY',
        rationale: 'Inspect live authoritative mandate balance in PostgreSQL.',
      },
      {
        label: 'Price Tampering Attack',
        query: 'How does AgentGuard prevent price tampering?',
        intent_target: 'SECURITY_SCENARIO',
        rationale: 'Understand AST policy checks vs untrusted agent claims.',
      },
      {
        label: 'Cryptographic Audit Ledger',
        query: 'Show me the cryptographic audit ledger',
        intent_target: 'FRONTEND_NAVIGATION',
        rationale: 'Review SHA-256 forward-chained integrity verification.',
      },
    ],
  },
];

export interface ConversationalInterceptor {
  onQuery?: (query: string) => Promise<boolean>;
  onResponse?: (response: AssistantResponse) => AssistantResponse;
}

interface AgentGuardContextType {
  // Authoritative server state
  mandate: Mandate | null;
  products: Product[];
  transactions: TransactionSummary[];
  selectedTxnId: string | null;
  auditData: TransactionAuditData | null;
  backendHealth: boolean | null;

  // Active Transaction focus
  activeTransaction: ProposeResponseData | null;
  activeAgentClaim: {
    product_id: string;
    claimed_price: string;
    quantity: number;
  } | null;
  activeExecutionResult: ExecuteResponseData | null;

  // Telemetry & Interaction
  rawWireLog: WireLogEntry | null;
  activeSurfaceTab: SurfaceTab;
  isConversationalOpen: boolean;
  agentVoiceState: AgentVoiceState;
  wireDrawerOpen: boolean;
  loadingAction: boolean;

  // Conversational Assistant State (Phase 5.5B-4)
  conversationalSessionId: string | null;
  conversationalMessages: ChatMessageItem[];
  isConversationalQuerying: boolean;
  conversationalError: string | null;

  // Action Dispatchers
  setActiveSurfaceTab: (tab: SurfaceTab) => void;
  setIsConversationalOpen: (open: boolean) => void;
  setAgentVoiceState: (state: AgentVoiceState) => void;
  setWireDrawerOpen: (open: boolean) => void;
  setSelectedTxnId: (id: string | null) => void;

  fetchMandate: () => Promise<void>;
  fetchProducts: () => Promise<void>;
  fetchTransactions: () => Promise<void>;
  fetchAuditData: (txnId: string) => Promise<void>;
  revokeMandate: () => Promise<void>;

  proposeClaim: (productId: string, claimedPrice: number, quantity?: number) => Promise<ProposeResponseData | null>;
  executeActiveTransaction: (idempotencyKey?: string, explicitTxnId?: string) => Promise<ExecuteResponseData | null>;
  approveActiveTransaction: () => Promise<boolean>;
  rejectActiveTransaction: () => Promise<boolean>;
  triggerScenario: (scenarioId: number) => Promise<ProposeResponseData | null>;
  sendAgentChatMessage: (prompt: string) => Promise<{ thought: string; claim: any; result: any } | null>;
  // Real B-3 Conversational Operations
  sendConversationalQuery: (query: string) => Promise<AssistantResponse | null>;
  resetConversationalSession: () => Promise<void>;
  registerConversationalInterceptor?: (interceptor: ConversationalInterceptor) => () => void;
  appendAgentMessage?: (text: string) => void;
}

const AgentGuardContext = createContext<AgentGuardContextType | undefined>(undefined);

export const AgentGuardProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const navigate = useNavigate();

  const [mandate, setMandate] = useState<Mandate | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [transactions, setTransactions] = useState<TransactionSummary[]>([]);
  const [selectedTxnId, setSelectedTxnId] = useState<string | null>(null);
  const [auditData, setAuditData] = useState<TransactionAuditData | null>(null);
  const [backendHealth, setBackendHealth] = useState<boolean | null>(null);

  const [activeTransaction, setActiveTransaction] = useState<ProposeResponseData | null>(null);
  const [activeAgentClaim, setActiveAgentClaim] = useState<{
    product_id: string;
    claimed_price: string;
    quantity: number;
  } | null>(null);
  const [activeExecutionResult, setActiveExecutionResult] = useState<ExecuteResponseData | null>(null);

  const [rawWireLog, setRawWireLog] = useState<WireLogEntry | null>(null);
  const [activeSurfaceTab, setActiveSurfaceTab] = useState<SurfaceTab>('DEFENSE');
  const [isConversationalOpen, setIsConversationalOpen] = useState<boolean>(false);
  const [agentVoiceState, setAgentVoiceState] = useState<AgentVoiceState>('IDLE');
  const [wireDrawerOpen, setWireDrawerOpen] = useState<boolean>(false);
  const [loadingAction, setLoadingAction] = useState<boolean>(false);

  // Conversational State & Race Safety
  const [conversationalSessionId, setConversationalSessionId] = useState<string | null>(null);
  const [conversationalMessages, setConversationalMessages] = useState<ChatMessageItem[]>(INITIAL_CONVERSATIONAL_MESSAGES);
  const [isConversationalQuerying, setIsConversationalQuerying] = useState<boolean>(false);
  const [conversationalError, setConversationalError] = useState<string | null>(null);

  const inFlightAbortControllerRef = useRef<AbortController | null>(null);
  const latestRequestIdRef = useRef<number>(0);
  const interceptorRef = useRef<ConversationalInterceptor | null>(null);

  const registerConversationalInterceptor = useCallback((interceptor: ConversationalInterceptor) => {
    interceptorRef.current = interceptor;
    return () => {
      if (interceptorRef.current === interceptor) {
        interceptorRef.current = null;
      }
    };
  }, []);

  const appendAgentMessage = useCallback((text: string) => {
    const msgId = `agt-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`;
    const agentMsg: ChatMessageItem = {
      id: msgId,
      sender: 'agent',
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setConversationalMessages((prev) => [...prev, agentMsg]);
  }, []);

  const logWire = (
    endpoint: string,
    method: string,
    status: number,
    responseBody: any,
    requestBody?: any,
    durationMs?: number
  ) => {
    setRawWireLog({
      endpoint,
      method,
      status,
      requestBody,
      responseBody,
      timestamp: new Date().toLocaleTimeString(),
      durationMs,
    });
  };

  const fetchMandate = useCallback(async () => {
    try {
      const envelope = await api.getMandate('mandate-001');
      if (envelope.success && envelope.data) {
        setMandate(envelope.data);
      }
    } catch (err) {
      console.error('Failed to fetch mandate:', err);
    }
  }, []);

  const fetchProducts = useCallback(async () => {
    try {
      const envelope = await api.getProducts();
      if (envelope.success && envelope.data) {
        setProducts(envelope.data);
      }
    } catch (err) {
      console.error('Failed to fetch products:', err);
    }
  }, []);

  const fetchTransactions = useCallback(async () => {
    try {
      const { envelope } = await api.getTransactions();
      if (envelope.success && envelope.data) {
        setTransactions(envelope.data);
        if (!selectedTxnId && envelope.data.length > 0) {
          setSelectedTxnId(envelope.data[0].id);
        }
      }
    } catch (err) {
      console.error('Failed to fetch transactions:', err);
    }
  }, [selectedTxnId]);

  const fetchAuditData = useCallback(async (txnId: string) => {
    try {
      const { envelope } = await api.getTransactionAudit(txnId);
      if (envelope.success && envelope.data) {
        setAuditData(envelope.data);
      }
    } catch (err) {
      console.error('Failed to fetch audit data:', err);
    }
  }, []);

  const checkHealth = useCallback(async () => {
    try {
      const apiBase =
        import.meta.env.VITE_API_URL ??
        (import.meta.env.DEV ? 'http://localhost:8000' : '');
      const res = await fetch(`${apiBase}/health`);
      setBackendHealth(res.ok);
    } catch {
      setBackendHealth(false);
    }
  }, []);

  useEffect(() => {
    fetchMandate();
    fetchProducts();
    fetchTransactions();
    checkHealth();

    const interval = setInterval(() => {
      if (!document.hidden) {
        fetchMandate();
        checkHealth();
      }
    }, 4000);

    return () => clearInterval(interval);
  }, [fetchMandate, fetchProducts, fetchTransactions, checkHealth]);

  useEffect(() => {
    if (selectedTxnId) {
      fetchAuditData(selectedTxnId);
    }
  }, [selectedTxnId, fetchAuditData]);

  const revokeMandate = async () => {
    setLoadingAction(true);
    const start = performance.now();
    try {
      const { status, envelope } = await api.revokeMandate('mandate-001');
      logWire('POST /mandate/mandate-001/revoke', 'POST', status, envelope, null, Math.round(performance.now() - start));
      await fetchMandate();
      await fetchTransactions();
    } finally {
      setLoadingAction(false);
    }
  };

  const proposeClaim = async (
    productId: string,
    claimedPrice: number,
    quantity: number = 1
  ): Promise<ProposeResponseData | null> => {
    setLoadingAction(true);
    const start = performance.now();
    const claimObj = {
      product_id: productId,
      claimed_price: claimedPrice.toFixed(2),
      quantity,
    };
    setActiveAgentClaim(claimObj);
    setActiveExecutionResult(null);

    try {
      const { status, envelope } = await api.proposeTransaction({
        product_id: productId,
        claimed_price: claimedPrice,
        quantity,
      });

      logWire(
        'POST /transaction/propose',
        'POST',
        status,
        envelope,
        { product_id: productId, claimed_price: claimedPrice, quantity },
        Math.round(performance.now() - start)
      );

      if (envelope.data) {
        setActiveTransaction(envelope.data);
        setSelectedTxnId(envelope.data.transaction_id);
        await fetchMandate();
        await fetchTransactions();
        return envelope.data;
      }
      return null;
    } finally {
      setLoadingAction(false);
    }
  };

  const executeActiveTransaction = async (
    idempotencyKey?: string,
    explicitTxnId?: string
  ): Promise<ExecuteResponseData | null> => {
    const targetTxnId = explicitTxnId || activeTransaction?.transaction_id;
    if (!targetTxnId) return null;
    setLoadingAction(true);
    const start = performance.now();
    try {
      const { status, envelope } = await api.executeTransaction({
        transaction_id: targetTxnId,
        idempotency_key: idempotencyKey,
      });

      logWire(
        'POST /transaction/execute',
        'POST',
        status,
        envelope,
        { transaction_id: targetTxnId, idempotency_key: idempotencyKey },
        Math.round(performance.now() - start)
      );

      if (envelope.data) {
        setActiveExecutionResult(envelope.data);
      } else if (envelope.error) {
        setActiveExecutionResult({
          transaction_id: targetTxnId,
          status: 'denied',
          reason_code: envelope.error.code,
          razorpay_payment_id: null,
        });
      }

      await fetchMandate();
      await fetchTransactions();
      if (targetTxnId) {
        await fetchAuditData(targetTxnId);
      }
      return envelope.data;
    } finally {
      setLoadingAction(false);
    }
  };

  const approveActiveTransaction = async (): Promise<boolean> => {
    if (!activeTransaction) return false;
    setLoadingAction(true);
    const start = performance.now();
    try {
      const { status, envelope } = await api.approveTransaction(activeTransaction.transaction_id);
      logWire(
        `POST /transaction/${activeTransaction.transaction_id}/approve`,
        'POST',
        status,
        envelope,
        null,
        Math.round(performance.now() - start)
      );

      if (envelope.success) {
        setActiveTransaction({
          ...activeTransaction,
          decision: 'ALLOW',
          reason_code: 'APPROVED_BY_HUMAN',
        });
        await fetchMandate();
        await fetchTransactions();
        return true;
      }
      return false;
    } finally {
      setLoadingAction(false);
    }
  };

  const rejectActiveTransaction = async (): Promise<boolean> => {
    if (!activeTransaction) return false;
    setLoadingAction(true);
    const start = performance.now();
    try {
      const { status, envelope } = await api.rejectTransaction(activeTransaction.transaction_id);
      logWire(
        `POST /transaction/${activeTransaction.transaction_id}/reject`,
        'POST',
        status,
        envelope,
        null,
        Math.round(performance.now() - start)
      );

      if (envelope.success) {
        setActiveTransaction({
          ...activeTransaction,
          decision: 'DENY',
          reason_code: 'REJECTED_BY_HUMAN',
        });
        await fetchMandate();
        await fetchTransactions();
        return true;
      }
      return false;
    } finally {
      setLoadingAction(false);
    }
  };

  const triggerScenario = async (scenarioId: number): Promise<ProposeResponseData | null> => {
    setLoadingAction(true);
    try {
      switch (scenarioId) {
        case 1: {
          // Scenario 1: Happy path within budget ₹2,799
          const result = await proposeClaim('prod-002', 2799.0, 1);
          if (result) {
            await executeActiveTransaction(undefined, result.transaction_id);
          }
          return result;
        }
        case 2: {
          // Scenario 2: Over-budget ₹3,499 (exceeds ₹3,000 budget -> ESCALATE)
          return await proposeClaim('prod-001', 3499.0, 1);
        }
        case 3: {
          // Scenario 3: Price tampering (claims ₹1,999 vs actual ₹3,499 -> DENY)
          return await proposeClaim('prod-001', 1999.0, 1);
        }
        case 4: {
          // Scenario 4: Replay attack
          const propRes = await proposeClaim('prod-002', 2799.0, 1);
          if (propRes) {
            await executeActiveTransaction(undefined, propRes.transaction_id);
            // Fire replay with new idempotency key on same successful transaction
            const start = performance.now();
            const { status, envelope } = await api.executeTransaction({
              transaction_id: propRes.transaction_id,
              idempotency_key: `replay-attempt-${Date.now()}`,
            });
            logWire(
              `POST /transaction/execute (Replay Attack on ${propRes.transaction_id.substring(0, 8)})`,
              'POST',
              status,
              envelope,
              { transaction_id: propRes.transaction_id },
              Math.round(performance.now() - start)
            );
            setActiveTransaction({
              ...propRes,
              decision: 'DENY',
              reason_code: envelope.error?.code || 'REPLAY_DETECTED',
            });
            setActiveExecutionResult({
              transaction_id: propRes.transaction_id,
              status: 'denied',
              reason_code: envelope.error?.code || 'REPLAY_DETECTED',
              razorpay_payment_id: null,
            });
          }
          return propRes;
        }
        case 5: {
          // Scenario 5: Safe retry
          const propRes = await proposeClaim('prod-002', 2799.0, 1);
          if (propRes) {
            const retryKey = `retry-key-${Date.now()}`;
            await executeActiveTransaction(retryKey, propRes.transaction_id);
          }
          return propRes;
        }
        case 6: {
          // Scenario 6: Mandate Revocation mid-session
          const propRes = await proposeClaim('prod-002', 2799.0, 1);
          if (propRes) {
            await revokeMandate();
            const start = performance.now();
            const { status, envelope } = await api.executeTransaction({
              transaction_id: propRes.transaction_id,
            });
            logWire(
              'POST /transaction/execute (Post-Revocation Attempt)',
              'POST',
              status,
              envelope,
              { transaction_id: propRes.transaction_id },
              Math.round(performance.now() - start)
            );
            setActiveTransaction({
              ...propRes,
              decision: 'DENY',
              reason_code: envelope.error?.code || 'MANDATE_REVOKED',
            });
          }
          return propRes;
        }
        default:
          return null;
      }
    } finally {
      setLoadingAction(false);
      await fetchMandate();
      await fetchTransactions();
    }
  };

  const sendAgentChatMessage = async (prompt: string) => {
    setLoadingAction(true);
    const start = performance.now();
    try {
      const { status, envelope } = await api.agentChat(prompt);
      logWire('POST /agent/chat', 'POST', status, envelope, { prompt }, Math.round(performance.now() - start));

      if (envelope.success && envelope.data) {
        const data = envelope.data;
        setActiveAgentClaim(data.agent_claim);
        if (data.firewall_result) {
          setActiveTransaction(data.firewall_result);
          setSelectedTxnId(data.firewall_result.transaction_id);
        }
        await fetchMandate();
        await fetchTransactions();
        return {
          thought: data.agent_thought,
          claim: data.agent_claim,
          result: data.firewall_result,
        };
      }
      return null;
    } finally {
      setLoadingAction(false);
    }
  };

  const sendConversationalQuery = async (queryText: string): Promise<AssistantResponse | null> => {
    const trimmed = queryText.trim();
    if (!trimmed || isConversationalQuerying) return null;

    // Interceptor check (e.g. stopped Q&A continuation flow)
    if (interceptorRef.current?.onQuery) {
      const handled = await interceptorRef.current.onQuery(trimmed);
      if (handled) {
        const userMsgId = `usr-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`;
        const userMsg: ChatMessageItem = {
          id: userMsgId,
          sender: 'user',
          text: trimmed,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
        setConversationalMessages((prev) => [...prev, userMsg]);
        return null;
      }
    }

    // 1. Race Safety: Invalidate any existing in-flight request
    if (inFlightAbortControllerRef.current) {
      inFlightAbortControllerRef.current.abort();
    }
    const abortController = new AbortController();
    inFlightAbortControllerRef.current = abortController;

    const currentRequestId = ++latestRequestIdRef.current;
    setIsConversationalQuerying(true);
    setConversationalError(null);
    setAgentVoiceState('THINKING');

    const userMsgId = `usr-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`;
    const userMsg: ChatMessageItem = {
      id: userMsgId,
      sender: 'user',
      text: trimmed,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setConversationalMessages((prev) => [...prev, userMsg]);
    const startTime = performance.now();

    try {
      const { status, envelope } = await api.conversationalQuery(
        {
          query: trimmed,
          session_id: conversationalSessionId || undefined,
          user_id: 'user-001',
        },
        abortController.signal
      );

      // Invalidate if superseded by a newer request
      if (latestRequestIdRef.current !== currentRequestId) {
        return null;
      }

      const durationMs = Math.round(performance.now() - startTime);

      logWire(
        'POST /conversational/query',
        'POST',
        status,
        envelope,
        { query: trimmed, session_id: conversationalSessionId },
        durationMs
      );

      if (envelope.success && envelope.data) {
        let resp = envelope.data;
        if (interceptorRef.current?.onResponse) {
          resp = interceptorRef.current.onResponse(resp);
        }
        setConversationalSessionId(resp.session_id);

        const isRefusal =
          resp.intent === 'ADVERSARIAL_INJECTION' || resp.dialogue_act === 'REFUSE_ADVERSARIAL';

        let actionStatus: 'PENDING' | 'EXECUTED' | 'BLOCKED' | 'FAILED' | undefined = undefined;
        let actionDescription: string | undefined = undefined;

        // 2. Action Safety Classification & Preparation
        if (resp.action) {
          const act = resp.action;
          if (act.action_type === 'NAVIGATE_TAB') {
            const target = (act.ui_tab_target || '').toUpperCase();
            if (target === 'DEFENSE' || target === 'LIVE') {
              actionStatus = 'EXECUTED';
              actionDescription = 'Navigating to Live Protection';
            } else if (target === 'THREAT' || target === 'THREAT_LAB') {
              actionStatus = 'EXECUTED';
              actionDescription = 'Navigating to Threat Lab';
            } else if (target === 'FORENSICS' || target === 'AUDIT') {
              actionStatus = 'EXECUTED';
              actionDescription = 'Navigating to Forensic Ledger';
            } else if (target === 'COCKPIT' || target === 'HOME') {
              actionStatus = 'EXECUTED';
              actionDescription = 'Navigating to Home Cockpit';
            } else if (target === 'TELEMETRY') {
              actionStatus = 'EXECUTED';
              actionDescription = 'Opening Wire Telemetry';
            } else {
              actionStatus = 'BLOCKED';
              actionDescription = 'Unknown navigation target safely blocked';
            }
          } else if (act.action_type === 'TRIGGER_SCENARIO') {
            actionStatus = 'EXECUTED';
            actionDescription = `Navigating to Threat Lab for ${act.payload?.scenario_name || 'Scenario'}`;
          } else if (act.action_type === 'INSPECT_TRANSACTION') {
            actionStatus = 'EXECUTED';
            actionDescription = `Inspecting Transaction ${act.payload?.transaction_id || ''}`;
          } else if (act.action_type === 'HIGHLIGHT_CODE') {
            actionStatus = 'EXECUTED';
            actionDescription = `Referenced ${act.payload?.file || 'source code'}`;
          } else {
            actionStatus = 'BLOCKED';
            actionDescription = 'Action blocked by safety policy';
          }
        }

        const agentMsgId = `agt-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`;
        const agentMsg: ChatMessageItem = {
          id: agentMsgId,
          sender: 'agent',
          text: resp.message,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          intent: resp.intent,
          dialogueAct: resp.dialogue_act,
          liveDataUsed: resp.live_data_used,
          liveReadings: resp.live_readings,
          evidenceCitations: resp.evidence_citations,
          suggestedFollowups: resp.suggested_followups,
          progressiveOffer: resp.progressive_disclosure_offer,
          action: resp.action,
          actionStatus,
          actionDescription,
          latencyMs: durationMs,
          isAdversarialRefusal: isRefusal,
          trace: resp.trace,
        };

        // 3. Render Assistant Response first (No UI jumping)
        setConversationalMessages((prev) => [...prev, agentMsg]);

        // 4. State Machine Transition
        if (isRefusal) {
          setAgentVoiceState('DENIED');
        } else if (actionStatus === 'EXECUTED') {
          setAgentVoiceState('SUCCESS');
        } else {
          setAgentVoiceState('SPEAKING');
        }

        setTimeout(() => {
          setAgentVoiceState('IDLE');
        }, 1500);

        // 5. Intentional Visual Breathing Pause before UI Navigation (~700ms)
        // Skip for PROJECT_WALKTHROUGH as AutonomousDemoContext coordinates navigation and demo steps
        if (resp.action && actionStatus === 'EXECUTED' && resp.intent !== 'PROJECT_WALKTHROUGH') {
          const act = resp.action;
          setTimeout(() => {
            // Ensure request has not been superseded by a newer query
            if (latestRequestIdRef.current !== currentRequestId) return;

            if (act.action_type === 'NAVIGATE_TAB') {
              const target = (act.ui_tab_target || '').toUpperCase();
              if (target === 'DEFENSE' || target === 'LIVE') {
                navigate('/live');
              } else if (target === 'THREAT' || target === 'THREAT_LAB') {
                navigate('/threats');
              } else if (target === 'FORENSICS' || target === 'AUDIT') {
                navigate('/forensics');
              } else if (target === 'COCKPIT' || target === 'HOME') {
                navigate('/');
              } else if (target === 'TELEMETRY') {
                setWireDrawerOpen(true);
              }
            } else if (act.action_type === 'TRIGGER_SCENARIO') {
              navigate('/threats');
            } else if (act.action_type === 'INSPECT_TRANSACTION') {
              const txnId = act.payload?.transaction_id;
              if (txnId) {
                setSelectedTxnId(txnId);
                fetchAuditData(txnId);
                navigate('/forensics');
              }
            }
          }, 700);
        }

        if (resp.intent === 'PROJECT_WALKTHROUGH') {
          return {
            ...resp,
            message: '', // Autonomous demo orchestrator coordinates spoken narration
          };
        }

        return resp;
      } else {
        const errMsg = envelope.error?.message || 'Failed to process conversational query.';
        setConversationalError(errMsg);
        setAgentVoiceState('ERROR');

        const errorMsg: ChatMessageItem = {
          id: `err-${Date.now()}`,
          sender: 'agent',
          text: `Error: ${errMsg}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          isError: true,
        };
        setConversationalMessages((prev) => [...prev, errorMsg]);

        setTimeout(() => {
          setAgentVoiceState('IDLE');
        }, 2000);

        return null;
      }
    } catch (err: any) {
      if (err?.name === 'AbortError' || abortController.signal.aborted) {
        return null;
      }
      const errText = err instanceof Error ? err.message : 'Network error communicating with backend';
      setConversationalError(errText);
      setAgentVoiceState('ERROR');

      const errorMsg: ChatMessageItem = {
        id: `err-${Date.now()}`,
        sender: 'agent',
        text: `Connection Error: ${errText}. Please ensure the AgentGuard backend server is running.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isError: true,
      };
      setConversationalMessages((prev) => [...prev, errorMsg]);

      setTimeout(() => {
        setAgentVoiceState('IDLE');
      }, 2000);

      return null;
    } finally {
      if (latestRequestIdRef.current === currentRequestId) {
        setIsConversationalQuerying(false);
        inFlightAbortControllerRef.current = null;
      }
    }
  };

  const resetConversationalSession = async () => {
    // Abort in-flight request
    if (inFlightAbortControllerRef.current) {
      inFlightAbortControllerRef.current.abort();
      inFlightAbortControllerRef.current = null;
    }
    setIsConversationalQuerying(false);
    setConversationalError(null);

    const sessionIdToReset = conversationalSessionId;
    setConversationalSessionId(null);
    setConversationalMessages(INITIAL_CONVERSATIONAL_MESSAGES);
    setAgentVoiceState('IDLE');

    // Only send DELETE if an active backend session actually exists
    if (sessionIdToReset) {
      try {
        await api.resetConversationalSession(sessionIdToReset);
      } catch (err) {
        console.warn('Session reset error on backend (silently recovered):', err);
      }
    }
  };

  return (
    <AgentGuardContext.Provider
      value={{
        mandate,
        products,
        transactions,
        selectedTxnId,
        auditData,
        backendHealth,
        activeTransaction,
        activeAgentClaim,
        activeExecutionResult,
        rawWireLog,
        activeSurfaceTab,
        isConversationalOpen,
        agentVoiceState,
        wireDrawerOpen,
        loadingAction,
        conversationalSessionId,
        conversationalMessages,
        isConversationalQuerying,
        conversationalError,
        setActiveSurfaceTab,
        setIsConversationalOpen,
        setAgentVoiceState,
        setWireDrawerOpen,
        setSelectedTxnId,
        fetchMandate,
        fetchProducts,
        fetchTransactions,
        fetchAuditData,
        revokeMandate,
        proposeClaim,
        executeActiveTransaction,
        approveActiveTransaction,
        rejectActiveTransaction,
        triggerScenario,
        sendAgentChatMessage,
        sendConversationalQuery,
        resetConversationalSession,
        registerConversationalInterceptor,
        appendAgentMessage,
      }}
    >
      {children}
    </AgentGuardContext.Provider>
  );
};

export const useAgentGuard = (): AgentGuardContextType => {
  const context = useContext(AgentGuardContext);
  if (!context) {
    throw new Error('useAgentGuard must be used within an AgentGuardProvider');
  }
  return context;
};
