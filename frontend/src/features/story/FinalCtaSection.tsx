import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, Mic, Terminal, Shield, ArrowUp } from 'lucide-react';
import { useAgentGuard } from '../../context/AgentGuardContext';

export const FinalCtaSection: React.FC = () => {
  const navigate = useNavigate();
  const {
    triggerScenario,
    setIsConversationalOpen,
    setWireDrawerOpen,
    loadingAction,
  } = useAgentGuard();

  const handleRunSimulation = async () => {
    navigate('/live');
    await triggerScenario(3);
  };

  const handleScrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <section className="py-16 sm:py-20 px-4 sm:px-6 max-w-7xl mx-auto w-full">
      <div className="bg-primary text-white rounded-3xl p-8 sm:p-14 shadow-ambient-hero relative overflow-hidden text-center flex flex-col items-center justify-center space-y-6">
        {/* Subtle Ambient Rings */}
        <div className="absolute -top-24 -left-24 w-96 h-96 bg-secondary/30 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -right-24 w-96 h-96 bg-lavender-tint/20 rounded-full blur-3xl pointer-events-none" />

        <div className="w-16 h-16 rounded-full bg-white/10 flex items-center justify-center text-white ring-8 ring-white/10 shadow-lg mb-2 relative z-10">
          <Shield className="w-8 h-8 text-white" />
        </div>

        <h2 className="font-outfit text-3xl sm:text-5xl font-extrabold text-white tracking-tight max-w-3xl leading-tight relative z-10">
          Experience the Trust Layer in Action
        </h2>

        <p className="font-inter text-sm sm:text-lg text-white/80 max-w-2xl leading-relaxed relative z-10">
          Run real-time adversarial simulations against our deterministic policy engine, verify cryptographic evidence logs, or inspect raw wire telemetry.
        </p>

        {/* Action Triggers */}
        <div className="flex flex-wrap items-center justify-center gap-4 pt-2 relative z-10">
          <button
            onClick={handleRunSimulation}
            disabled={loadingAction}
            className="px-8 py-3.5 bg-white hover:bg-lavender-tint text-primary rounded-full font-inter font-bold text-sm sm:text-base shadow-lg hover:shadow-xl hover:-translate-y-0.5 active:translate-y-0 transition-all flex items-center gap-2.5 disabled:opacity-50"
          >
            <Play className="w-4 h-4 fill-current text-primary" />
            <span>Launch Live Protection</span>
          </button>

          <button
            onClick={() => setIsConversationalOpen(true)}
            className="px-8 py-3.5 bg-white/15 hover:bg-white/25 text-white border border-white/30 rounded-full font-inter font-semibold text-sm sm:text-base hover:-translate-y-0.5 active:translate-y-0 transition-all flex items-center gap-2.5"
          >
            <Mic className="w-4 h-4 text-white" />
            <span>Talk to AgentGuard</span>
          </button>

          <button
            onClick={() => setWireDrawerOpen(true)}
            className="px-6 py-3.5 bg-white/10 hover:bg-white/20 text-white/90 rounded-full font-inter font-medium text-sm flex items-center gap-2 transition-colors"
          >
            <Terminal className="w-4 h-4 text-white/80" />
            <span>Inspect Wire Protocol</span>
          </button>
        </div>

        <div className="pt-6 border-t border-white/15 w-full max-w-xl flex items-center justify-between text-xs text-white/70 font-inter relative z-10">
          <span>FastAPI + PostgreSQL + Razorpay</span>
          <button
            onClick={handleScrollToTop}
            className="hover:text-white transition-colors flex items-center gap-1 font-medium"
          >
            <span>Back to top</span>
            <ArrowUp className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </section>
  );
};
