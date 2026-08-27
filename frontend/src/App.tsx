import React, { useState, useEffect } from 'react';
import { ShieldCheck, RefreshCw, Server, CreditCard, Lock } from 'lucide-react';
import { ShoppingAgentChat } from './components/ShoppingAgentChat/ShoppingAgentChat';
import { DecisionTrace } from './components/DecisionTrace/DecisionTrace';
import { AttackConsole } from './components/AttackConsole/AttackConsole';
import { api, Mandate, ProposeResponseData } from './lib/api';

export const App: React.FC = () => {
  const [mandate, setMandate] = useState<Mandate | null>(null);
  const [currentTransaction, setCurrentTransaction] = useState<ProposeResponseData | null>(null);
  const [currentAgentClaim, setCurrentAgentClaim] = useState<any>(null);
  const [backendHealth, setBackendHealth] = useState<boolean | null>(null);

  const fetchMandate = async () => {
    try {
      const envelope = await api.getMandate('mandate-001');
      if (envelope.success && envelope.data) {
        setMandate(envelope.data);
      }
    } catch (err) {
      console.error('Failed to fetch mandate:', err);
    }
  };

  const checkHealth = async () => {
    try {
      const res = await fetch('http://localhost:8000/health');
      setBackendHealth(res.ok);
    } catch (err) {
      setBackendHealth(false);
    }
  };

  useEffect(() => {
    fetchMandate();
    checkHealth();
    const interval = setInterval(fetchMandate, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleTransactionResult = (result: ProposeResponseData, agentClaim?: any) => {
    setCurrentTransaction(result);
    if (agentClaim) {
      setCurrentAgentClaim(agentClaim);
    }
  };

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      {/* Top Navbar */}
      <header className="bg-slate-900/90 border-b border-slate-800 px-6 py-3 flex items-center justify-between sticky top-0 z-50 backdrop-blur-md">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-indigo-600 text-white rounded-xl shadow-lg shadow-indigo-600/30">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-base font-bold text-white tracking-tight">AgentGuard</h1>
              <span className="text-xs text-indigo-400 font-mono font-medium px-2 py-0.5 bg-indigo-500/10 rounded border border-indigo-500/20">
                COMMERCE FIREWALL v0.1.0
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Deterministic Authorization Boundary for Autonomous AI Agents (Razorpay Buildathon)
            </p>
          </div>
        </div>

        {/* System Status Indicators */}
        <div className="flex items-center space-x-3 text-xs font-mono">
          <div className="flex items-center space-x-1.5 px-3 py-1 bg-slate-950 rounded-lg border border-slate-800">
            <Server className="w-3.5 h-3.5 text-indigo-400" />
            <span className="text-slate-400">Backend:</span>
            <span className={backendHealth ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'}>
              {backendHealth ? 'ONLINE (200)' : 'OFFLINE'}
            </span>
          </div>

          <div className="flex items-center space-x-1.5 px-3 py-1 bg-slate-950 rounded-lg border border-slate-800">
            <CreditCard className="w-3.5 h-3.5 text-sky-400" />
            <span className="text-slate-400">Gateway:</span>
            <span className="text-sky-400 font-semibold">RAZORPAY TEST-MODE</span>
          </div>

          <div className="flex items-center space-x-1.5 px-3 py-1 bg-slate-950 rounded-lg border border-slate-800">
            <Lock className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-slate-400">Policy:</span>
            <span className="text-emerald-400 font-semibold">SERVER AUTHORITATIVE</span>
          </div>

          <button
            onClick={fetchMandate}
            className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition-colors"
            title="Refresh Mandate State"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </header>

      {/* Main Dashboard Workspace Layout */}
      <main className="flex-1 p-6 grid grid-cols-12 gap-6 h-[calc(100vh-65px)] max-w-[1800px] mx-auto w-full">
        {/* Left Column: Shopping Agent Chat (4 cols) */}
        <div className="col-span-4 h-full">
          <ShoppingAgentChat
            mandate={mandate}
            onNewTransaction={handleTransactionResult}
            onRefreshMandate={fetchMandate}
          />
        </div>

        {/* Center Column: Decision Trace Panel (4 cols) */}
        <div className="col-span-4 h-full">
          <DecisionTrace
            currentTransaction={currentTransaction}
            agentClaim={currentAgentClaim}
            onTransactionUpdated={(updated) => setCurrentTransaction(updated)}
            onRefreshMandate={fetchMandate}
          />
        </div>

        {/* Right Column: Attack Console (4 cols) */}
        <div className="col-span-4 h-full">
          <AttackConsole
            onTransactionResult={handleTransactionResult}
            onRefreshMandate={fetchMandate}
          />
        </div>
      </main>
    </div>
  );
};
