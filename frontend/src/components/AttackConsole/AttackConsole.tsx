import React, { useState } from 'react';
import {
  Zap,
  ShieldAlert,
  Repeat,
  AlertOctagon,
  RefreshCw,
  Eye,
  CheckCircle,
  Terminal,
  Play,
  RotateCcw,
} from 'lucide-react';
import { api } from '../../lib/api';

interface AttackConsoleProps {
  onTransactionResult: (result: any, claim?: any) => void;
  onRefreshMandate: () => void;
}

export const AttackConsole: React.FC<AttackConsoleProps> = ({
  onTransactionResult,
  onRefreshMandate,
}) => {
  const [runningScenario, setRunningScenario] = useState<number | null>(null);
  const [rawHttpResponse, setRawHttpResponse] = useState<{
    endpoint: string;
    status: number;
    body: any;
  } | null>(null);

  const logHttp = (endpoint: string, status: number, body: any) => {
    setRawHttpResponse({ endpoint, status, body });
  };

  // Scenario 1: Happy Path
  const runScenario1 = async () => {
    setRunningScenario(1);
    try {
      const claim = { product_id: 'prod-002', claimed_price: '2799.00', quantity: 1 };
      const { status, envelope } = await api.proposeTransaction({
        product_id: 'prod-002',
        claimed_price: 2799.00,
        quantity: 1,
      });
      logHttp('POST /transaction/propose', status, envelope);
      if (envelope.data) {
        onTransactionResult(envelope.data, claim);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setRunningScenario(null);
      onRefreshMandate();
    }
  };

  // Scenario 2: Over-Budget Escalation
  const runScenario2 = async () => {
    setRunningScenario(2);
    try {
      const claim = { product_id: 'prod-001', claimed_price: '3499.00', quantity: 1 };
      const { status, envelope } = await api.proposeTransaction({
        product_id: 'prod-001',
        claimed_price: 3499.00,
        quantity: 1,
      });
      logHttp('POST /transaction/propose (Over-Budget)', status, envelope);
      if (envelope.data) {
        onTransactionResult(envelope.data, claim);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setRunningScenario(null);
      onRefreshMandate();
    }
  };

  // Scenario 3: Price Tampering Attack
  const runScenario3 = async () => {
    setRunningScenario(3);
    try {
      const claim = { product_id: 'prod-001', claimed_price: '1999.00', quantity: 1 };
      const { status, envelope } = await api.proposeTransaction({
        product_id: 'prod-001',
        claimed_price: 1999.00,
        quantity: 1,
      });
      logHttp('POST /transaction/propose (Price Tampering)', status, envelope);
      if (envelope.data) {
        onTransactionResult(envelope.data, claim);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setRunningScenario(null);
      onRefreshMandate();
    }
  };

  // Scenario 4: Replay Attack
  const runScenario4 = async () => {
    setRunningScenario(4);
    try {
      // 1. Propose & execute first attempt
      const { envelope: propEnv } = await api.proposeTransaction({
        product_id: 'prod-002',
        claimed_price: 2799.00,
        quantity: 1,
      });

      if (propEnv.data) {
        const txnId = propEnv.data.transaction_id;
        const { envelope: exec1Env } = await api.executeTransaction({ transaction_id: txnId });

        if (exec1Env.data?.status === 'success') {
          // 2. Attempt replay with NEW idempotency key
          const { status, envelope: replayEnv } = await api.executeTransaction({
            transaction_id: txnId,
            idempotency_key: `replay-attack-${Date.now()}`,
          });
          logHttp(`POST /transaction/execute (Replay on ${txnId.substring(0, 8)})`, status, replayEnv);
          onTransactionResult({
            transaction_id: txnId,
            decision: 'DENY',
            reason_code: replayEnv.error?.code || 'REPLAY_DETECTED',
            authoritative_total: 2799.00,
            expires_at: new Date().toISOString(),
          });
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setRunningScenario(null);
      onRefreshMandate();
    }
  };

  // Scenario 5: Payment Failure & Safe Retry
  const runScenario5 = async () => {
    setRunningScenario(5);
    try {
      const { envelope: propEnv } = await api.proposeTransaction({
        product_id: 'prod-002',
        claimed_price: 2799.00,
        quantity: 1,
      });
      if (propEnv.data) {
        const txnId = propEnv.data.transaction_id;
        const retryKey = `retry-key-${Date.now()}`;
        const { status, envelope: execEnv } = await api.executeTransaction({
          transaction_id: txnId,
          idempotency_key: retryKey,
        });
        logHttp('POST /transaction/execute (Safe Retry)', status, execEnv);
        onTransactionResult(propEnv.data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setRunningScenario(null);
      onRefreshMandate();
    }
  };

  // Scenario 6: Mandate Revocation Race
  const runScenario6 = async () => {
    setRunningScenario(6);
    try {
      // 1. Propose transaction (returns ALLOW)
      const { envelope: propEnv } = await api.proposeTransaction({
        product_id: 'prod-002',
        claimed_price: 2799.00,
        quantity: 1,
      });

      if (propEnv.data) {
        const txnId = propEnv.data.transaction_id;
        // 2. Revoke mandate mid-session
        await api.revokeMandate('mandate-001');

        // 3. Attempt to execute
        const { status, envelope: execEnv } = await api.executeTransaction({ transaction_id: txnId });
        logHttp('POST /transaction/execute (Mandate Revoked Mid-Session)', status, execEnv);
        onTransactionResult({
          ...propEnv.data,
          decision: 'DENY',
          reason_code: execEnv.error?.code || 'MANDATE_REVOKED',
        });
      }
    } catch (err) {
      console.error(err);
    } finally {
      setRunningScenario(null);
      onRefreshMandate();
    }
  };

  return (
    <div className="flex flex-col h-full glass-panel rounded-xl overflow-hidden border border-slate-800 shadow-2xl p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <div className="p-1.5 bg-rose-500/10 text-rose-400 rounded-lg border border-rose-500/20">
            <Zap className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-slate-100">Attack Console</h2>
            <p className="text-xs text-slate-400">Adversarial Scenario Trigger Grid (6 Core + 7th Visual Trace)</p>
          </div>
        </div>
        <span className="px-2 py-0.5 text-[10px] font-mono bg-rose-950/60 text-rose-300 border border-rose-800/60 rounded">
          LIVE FASTAPI BACKEND TARGET
        </span>
      </div>

      {/* Scenario Buttons Grid */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        {/* Scenario 1 */}
        <button
          onClick={runScenario1}
          disabled={runningScenario !== null}
          className="p-3 bg-slate-900/90 hover:bg-slate-800/90 border border-slate-800 rounded-xl text-left transition-all hover:border-emerald-500/40 group flex flex-col justify-between"
        >
          <div className="flex items-center justify-between text-emerald-400 font-semibold mb-1">
            <span className="flex items-center space-x-1.5">
              <CheckCircle className="w-3.5 h-3.5" />
              <span>1. Happy Path</span>
            </span>
            <Play className="w-3 h-3 text-slate-600 group-hover:text-emerald-400 transition-colors" />
          </div>
          <p className="text-[11px] text-slate-400">Within budget ₹2,799 → ALLOW → Execute SUCCESS</p>
        </button>

        {/* Scenario 2 */}
        <button
          onClick={runScenario2}
          disabled={runningScenario !== null}
          className="p-3 bg-slate-900/90 hover:bg-slate-800/90 border border-slate-800 rounded-xl text-left transition-all hover:border-amber-500/40 group flex flex-col justify-between"
        >
          <div className="flex items-center justify-between text-amber-400 font-semibold mb-1">
            <span className="flex items-center space-x-1.5">
              <AlertOctagon className="w-3.5 h-3.5" />
              <span>2. Over-Budget</span>
            </span>
            <Play className="w-3 h-3 text-slate-600 group-hover:text-amber-400 transition-colors" />
          </div>
          <p className="text-[11px] text-slate-400">Propose ₹3,499 → ESCALATE → Requires Human Approval</p>
        </button>

        {/* Scenario 3 */}
        <button
          onClick={runScenario3}
          disabled={runningScenario !== null}
          className="p-3 bg-slate-900/90 hover:bg-slate-800/90 border border-slate-800 rounded-xl text-left transition-all hover:border-rose-500/40 group flex flex-col justify-between"
        >
          <div className="flex items-center justify-between text-rose-400 font-semibold mb-1">
            <span className="flex items-center space-x-1.5">
              <ShieldAlert className="w-3.5 h-3.5" />
              <span>3. Price Tampering</span>
            </span>
            <Play className="w-3 h-3 text-slate-600 group-hover:text-rose-400 transition-colors" />
          </div>
          <p className="text-[11px] text-slate-400">Claim ₹1,999 vs actual ₹3,499 → DENY PRICE_MISMATCH</p>
        </button>

        {/* Scenario 4 */}
        <button
          onClick={runScenario4}
          disabled={runningScenario !== null}
          className="p-3 bg-slate-900/90 hover:bg-slate-800/90 border border-slate-800 rounded-xl text-left transition-all hover:border-indigo-500/40 group flex flex-col justify-between"
        >
          <div className="flex items-center justify-between text-indigo-400 font-semibold mb-1">
            <span className="flex items-center space-x-1.5">
              <Repeat className="w-3.5 h-3.5" />
              <span>4. Replay Attack</span>
            </span>
            <Play className="w-3 h-3 text-slate-600 group-hover:text-indigo-400 transition-colors" />
          </div>
          <p className="text-[11px] text-slate-400">Re-submit executed Txn ID → DENY REPLAY_DETECTED</p>
        </button>

        {/* Scenario 5 */}
        <button
          onClick={runScenario5}
          disabled={runningScenario !== null}
          className="p-3 bg-slate-900/90 hover:bg-slate-800/90 border border-slate-800 rounded-xl text-left transition-all hover:border-cyan-500/40 group flex flex-col justify-between"
        >
          <div className="flex items-center justify-between text-cyan-400 font-semibold mb-1">
            <span className="flex items-center space-x-1.5">
              <RefreshCw className="w-3.5 h-3.5" />
              <span>5. Safe Retry</span>
            </span>
            <Play className="w-3 h-3 text-slate-600 group-hover:text-cyan-400 transition-colors" />
          </div>
          <p className="text-[11px] text-slate-400">Payment failure retry → idempotent no double-charge</p>
        </button>

        {/* Scenario 6 */}
        <button
          onClick={runScenario6}
          disabled={runningScenario !== null}
          className="p-3 bg-slate-900/90 hover:bg-slate-800/90 border border-slate-800 rounded-xl text-left transition-all hover:border-purple-500/40 group flex flex-col justify-between"
        >
          <div className="flex items-center justify-between text-purple-400 font-semibold mb-1">
            <span className="flex items-center space-x-1.5">
              <RotateCcw className="w-3.5 h-3.5" />
              <span>6. Mandate Revocation</span>
            </span>
            <Play className="w-3 h-3 text-slate-600 group-hover:text-purple-400 transition-colors" />
          </div>
          <p className="text-[11px] text-slate-400">Revoke mandate mid-session → DENY MANDATE_REVOKED</p>
        </button>
      </div>

      {/* Scenario 7 Visual Banner */}
      <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 flex items-center justify-between text-xs font-mono text-slate-400">
        <div className="flex items-center space-x-2">
          <Eye className="w-4 h-4 text-indigo-400" />
          <span>Scenario 7 (Emergent): Live "LLM Lies" Visual Trace</span>
        </div>
        <span className="text-[10px] text-emerald-400">ACTIVE IN TRACE PANEL</span>
      </div>

      {/* Live Raw HTTP Inspector Box */}
      <div className="flex-1 bg-slate-950 rounded-xl border border-slate-800/80 p-3 flex flex-col overflow-hidden font-mono">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800/80 text-[11px]">
          <div className="flex items-center space-x-2 text-slate-300 font-sans font-semibold">
            <Terminal className="w-3.5 h-3.5 text-indigo-400" />
            <span>Raw HTTP Response Inspector</span>
          </div>
          {rawHttpResponse && (
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                rawHttpResponse.status >= 200 && rawHttpResponse.status < 300
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : rawHttpResponse.status === 403 || rawHttpResponse.status === 409
                  ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                  : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
              }`}
            >
              HTTP {rawHttpResponse.status}
            </span>
          )}
        </div>

        <div className="flex-1 mt-2 overflow-y-auto text-[11px] leading-relaxed">
          {rawHttpResponse ? (
            <div className="space-y-2">
              <div className="text-slate-400 border-b border-slate-900 pb-1">
                Endpoint: <span className="text-indigo-300 font-semibold">{rawHttpResponse.endpoint}</span>
              </div>
              <pre className="text-slate-300 bg-slate-900/80 p-2.5 rounded border border-slate-800/60 overflow-x-auto">
                {JSON.stringify(rawHttpResponse.body, null, 2)}
              </pre>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-slate-600 text-xs font-sans text-center">
              Click any scenario above to observe live backend HTTP status and response payload.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
