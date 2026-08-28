import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import {
  api,
  Mandate,
  Product,
  ProposeResponseData,
  ExecuteResponseData,
  TransactionSummary,
  TransactionAuditData,
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
  executeActiveTransaction: (idempotencyKey?: string) => Promise<ExecuteResponseData | null>;
  approveActiveTransaction: () => Promise<boolean>;
  rejectActiveTransaction: () => Promise<boolean>;
  triggerScenario: (scenarioId: number) => Promise<void>;
  sendAgentChatMessage: (prompt: string) => Promise<{ thought: string; claim: any; result: any } | null>;
}

const AgentGuardContext = createContext<AgentGuardContextType | undefined>(undefined);

export const AgentGuardProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
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
      const res = await fetch('http://localhost:8000/health');
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

  const executeActiveTransaction = async (idempotencyKey?: string): Promise<ExecuteResponseData | null> => {
    if (!activeTransaction) return null;
    setLoadingAction(true);
    const start = performance.now();
    try {
      const { status, envelope } = await api.executeTransaction({
        transaction_id: activeTransaction.transaction_id,
        idempotency_key: idempotencyKey,
      });

      logWire(
        'POST /transaction/execute',
        'POST',
        status,
        envelope,
        { transaction_id: activeTransaction.transaction_id, idempotency_key: idempotencyKey },
        Math.round(performance.now() - start)
      );

      if (envelope.data) {
        setActiveExecutionResult(envelope.data);
      } else if (envelope.error) {
        setActiveExecutionResult({
          transaction_id: activeTransaction.transaction_id,
          status: 'denied',
          reason_code: envelope.error.code,
          razorpay_payment_id: null,
        });
      }

      await fetchMandate();
      await fetchTransactions();
      if (activeTransaction.transaction_id) {
        await fetchAuditData(activeTransaction.transaction_id);
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

  const triggerScenario = async (scenarioId: number): Promise<void> => {
    setLoadingAction(true);
    try {
      switch (scenarioId) {
        case 1: {
          // Scenario 1: Happy path within budget ₹2,799
          const result = await proposeClaim('prod-002', 2799.0, 1);
          if (result) {
            await executeActiveTransaction();
          }
          break;
        }
        case 2: {
          // Scenario 2: Over-budget ₹3,499 (exceeds ₹3,000 budget -> ESCALATE)
          await proposeClaim('prod-001', 3499.0, 1);
          break;
        }
        case 3: {
          // Scenario 3: Price tampering (claims ₹1,999 vs actual ₹3,499 -> DENY)
          await proposeClaim('prod-001', 1999.0, 1);
          break;
        }
        case 4: {
          // Scenario 4: Replay attack
          const propRes = await proposeClaim('prod-002', 2799.0, 1);
          if (propRes) {
            await executeActiveTransaction();
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
          break;
        }
        case 5: {
          // Scenario 5: Safe retry
          const propRes = await proposeClaim('prod-002', 2799.0, 1);
          if (propRes) {
            const retryKey = `retry-key-${Date.now()}`;
            await executeActiveTransaction(retryKey);
          }
          break;
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
          break;
        }
        default:
          break;
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
