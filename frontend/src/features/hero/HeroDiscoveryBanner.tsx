import React, { useState } from 'react';
import {
  Shield,
  Bot,
  Database,
  CreditCard,
  Play,
  Mic,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { useAgentGuard } from '../../context/AgentGuardContext';

export const HeroDiscoveryBanner: React.FC = () => {
  const {
    triggerScenario,
    setActiveSurfaceTab,
    setIsConversationalOpen,
    loadingAction,
  } = useAgentGuard();

  const [expanded, setExpanded] = useState(true);

  const handleRunLiveDemo = async () => {
    setActiveSurfaceTab('DEFENSE');
    await triggerScenario(3); // Real price tampering verification flow
  };

  const handleTalkToAgent = () => {
    setIsConversationalOpen(true);
  };

  return (
    <section className="pt-6 pb-4 px-3 sm:px-6 max-w-7xl mx-auto w-full">
      <div className="bg-surface rounded-2xl sm:rounded-3xl p-6 sm:p-10 ambient-shadow-1 border border-surface-container relative overflow-hidden">
        {/* Ambient Glow */}
        <div className="absolute inset-0 bg-surface-glow pointer-events-none rounded-3xl" />

        {/* Hero Top Bar */}
        <div className="relative z-10 flex flex-col items-center text-center max-w-4xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-lavender-tint/80 border border-primary-fixed text-[#4C1D95] text-xs font-label-mono font-semibold mb-4">
            <span className="w-2 h-2 rounded-full bg-verified animate-pulse" />
            <span>AGENTIC COMMERCE FIREWALL & TRUST BOUNDARY</span>
          </div>

          <h1 className="font-outfit text-3xl sm:text-5xl font-extrabold text-primary tracking-tight leading-tight mb-4">
            Give AI agents a secure path to commerce.
          </h1>

          <p className="font-inter text-sm sm:text-lg text-on-surface-variant max-w-2xl mx-auto mb-6 leading-relaxed">
            Secure autonomous commerce, before money moves. AgentGuard acts as the definitive trust boundary between intelligent agents and your foundational ledgers.
          </p>

          {/* Action CTAs */}
          <div className="flex flex-wrap items-center justify-center gap-3 sm:gap-4 mb-8">
            <button
              onClick={handleRunLiveDemo}
              disabled={loadingAction}
              className="px-6 sm:px-8 py-3 bg-primary hover:bg-secondary text-white rounded-full font-inter font-semibold text-sm ambient-shadow-2 hover:shadow-xl hover:-translate-y-0.5 active:translate-y-0 transition-all flex items-center gap-2.5 disabled:opacity-50"
            >
              <Play className="w-4 h-4 fill-current text-white" />
              <span>Run Live Simulation</span>
            </button>

            <button
              onClick={handleTalkToAgent}
              className="px-6 sm:px-8 py-3 bg-white hover:bg-lavender-tint text-primary border border-primary/30 rounded-full font-inter font-semibold text-sm hover:-translate-y-0.5 active:translate-y-0 transition-all flex items-center gap-2.5"
            >
              <Mic className="w-4 h-4 text-primary" />
              <span>Talk to AgentGuard</span>
            </button>

            <button
              onClick={() => setExpanded(!expanded)}
              className="p-3 text-on-surface-variant hover:text-primary hover:bg-surface-container rounded-full transition-colors"
              title={expanded ? 'Collapse Trust Journey' : 'Expand Trust Journey'}
            >
              {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* The Secure Path to Execution (4-Step Trust Boundary Pipeline) */}
        {expanded && (
          <div className="relative z-10 pt-4 border-t border-surface-container-high transition-all">
            <div className="text-center mb-6">
              <span className="text-xs font-label-mono font-bold uppercase tracking-widest text-on-surface-variant/80">
                The Secure Path to Execution
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 relative">
              {/* Step 1: AI Agent */}
              <div className="bg-white rounded-2xl p-5 border border-surface-container ambient-shadow-1 flex flex-col items-center text-center relative group hover:border-primary-fixed transition-all">
                <div className="w-14 h-14 rounded-2xl bg-surface-container flex items-center justify-center mb-3 text-primary group-hover:scale-105 transition-transform">
                  <Bot className="w-7 h-7 text-error" />
                </div>
                <span className="font-outfit font-bold text-primary text-base mb-1">1. AI Agent Claim</span>
                <p className="font-inter text-xs text-on-surface-variant">Untrusted client proposes transaction intent</p>
                <span className="mt-3 text-[10px] font-label-mono font-semibold px-2 py-0.5 rounded-full bg-error-container/40 text-error">
                  Zero Trust
                </span>
              </div>

              {/* Step 2: AgentGuard */}
              <div className="bg-primary rounded-2xl p-5 text-white ambient-shadow-2 flex flex-col items-center text-center relative ring-4 ring-lavender-tint">
                <div className="w-14 h-14 rounded-2xl bg-white/10 flex items-center justify-center mb-3 text-white">
                  <Shield className="w-7 h-7 text-white" />
                </div>
                <span className="font-outfit font-bold text-white text-base mb-1">2. AgentGuard Core</span>
                <p className="font-inter text-xs text-white/80">Deterministic policy firewall & parameter gate</p>
                <span className="mt-3 text-[10px] font-label-mono font-semibold px-2 py-0.5 rounded-full bg-white/20 text-white">
                  Deterministic
                </span>
              </div>

              {/* Step 3: PostgreSQL */}
              <div className="bg-white rounded-2xl p-5 border border-surface-container ambient-shadow-1 flex flex-col items-center text-center relative group hover:border-secondary-fixed transition-all">
                <div className="w-14 h-14 rounded-2xl bg-surface-container flex items-center justify-center mb-3 text-secondary group-hover:scale-105 transition-transform">
                  <Database className="w-7 h-7 text-secondary" />
                </div>
                <span className="font-outfit font-bold text-primary text-base mb-1">3. PostgreSQL Truth</span>
                <p className="font-inter text-xs text-on-surface-variant">Authoritative pricing & atomic budget reservation</p>
                <span className="mt-3 text-[10px] font-label-mono font-semibold px-2 py-0.5 rounded-full bg-secondary-fixed text-[#00346e]">
                  Source of Truth
                </span>
              </div>

              {/* Step 4: Razorpay */}
              <div className="bg-white rounded-2xl p-5 border border-surface-container ambient-shadow-1 flex flex-col items-center text-center relative group hover:border-emerald-300 transition-all">
                <div className="w-14 h-14 rounded-2xl bg-surface-container flex items-center justify-center mb-3 text-verified group-hover:scale-105 transition-transform">
                  <CreditCard className="w-7 h-7 text-verified" />
                </div>
                <span className="font-outfit font-bold text-primary text-base mb-1">4. Razorpay Execution</span>
                <p className="font-inter text-xs text-on-surface-variant">Cryptographically signed, idempotent payment</p>
                <span className="mt-3 text-[10px] font-label-mono font-semibold px-2 py-0.5 rounded-full bg-[#F0FDF4] text-verified border border-[#BBF7D0]">
                  Verified Secure
                </span>
              </div>
            </div>

            {/* 3 Core Invariants Summary */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-6 pt-4 border-t border-surface-container text-xs font-inter text-on-surface-variant">
              <div className="flex items-center gap-2 justify-center">
                <CheckCircle2 className="w-4 h-4 text-verified flex-shrink-0" />
                <span><strong>Deterministic Policy:</strong> Zero LLM hallucination risk</span>
              </div>
              <div className="flex items-center gap-2 justify-center">
                <CheckCircle2 className="w-4 h-4 text-verified flex-shrink-0" />
                <span><strong>Catalog Pricing:</strong> Database is the sole financial authority</span>
              </div>
              <div className="flex items-center gap-2 justify-center">
                <CheckCircle2 className="w-4 h-4 text-verified flex-shrink-0" />
                <span><strong>SHA-256 Audit Trail:</strong> Immutable cryptographic chain</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
};
