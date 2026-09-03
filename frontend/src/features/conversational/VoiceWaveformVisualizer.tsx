import React from 'react';
import { AgentVoiceState } from '../../context/AgentGuardContext';
import { Mic, Volume2, Cpu, CheckCircle2, ShieldAlert, AlertTriangle, AlertCircle, RefreshCw } from 'lucide-react';

interface VoiceWaveformVisualizerProps {
  state: AgentVoiceState;
}

export const VoiceWaveformVisualizer: React.FC<VoiceWaveformVisualizerProps> = ({
  state,
}) => {
  const getStatusBadge = () => {
    switch (state) {
      case 'LISTENING':
        return (
          <span className="px-3 py-1 rounded-full text-[10px] font-label-mono font-bold bg-[#FEF3C7] text-escalation border border-[#FDE68A] flex items-center gap-1.5 animate-pulse shadow-sm">
            <Mic className="w-3.5 h-3.5 text-escalation" />
            <span>LISTENING (SPEECH INPUT)</span>
          </span>
        );
      case 'THINKING':
        return (
          <span className="px-3 py-1 rounded-full text-[10px] font-label-mono font-bold bg-lavender-tint text-[#4C1D95] border border-primary-fixed flex items-center gap-1.5 shadow-sm">
            <Cpu className="w-3.5 h-3.5 text-primary-container animate-spin" />
            <span>THINKING (B-3 BRAIN)</span>
          </span>
        );
      case 'SPEAKING':
        return (
          <span className="px-3 py-1 rounded-full text-[10px] font-label-mono font-bold bg-secondary-fixed text-[#00346e] border border-secondary-container flex items-center gap-1.5 shadow-sm">
            <Volume2 className="w-3.5 h-3.5 text-secondary" />
            <span>GROUNDED RESPONSE</span>
          </span>
        );
      case 'EXECUTING':
        return (
          <span className="px-3 py-1 rounded-full text-[10px] font-label-mono font-bold bg-lavender-tint text-[#4C1D95] border border-primary-fixed flex items-center gap-1.5 shadow-sm">
            <RefreshCw className="w-3.5 h-3.5 text-primary animate-spin" />
            <span>EXECUTING UI ACTION</span>
          </span>
        );
      case 'WAITING_FOR_APPROVAL':
        return (
          <span className="px-3 py-1 rounded-full text-[10px] font-label-mono font-bold bg-[#FEF3C7] text-escalation border border-[#FDE68A] flex items-center gap-1.5 shadow-sm">
            <AlertTriangle className="w-3.5 h-3.5 text-escalation" />
            <span>WAITING FOR HUMAN APPROVAL</span>
          </span>
        );
      case 'SUCCESS':
        return (
          <span className="px-3 py-1 rounded-full text-[10px] font-label-mono font-bold bg-[#F0FDF4] text-verified border border-[#BBF7D0] flex items-center gap-1.5 shadow-sm">
            <CheckCircle2 className="w-3.5 h-3.5 text-verified" />
            <span>ACTION COMPLETED</span>
          </span>
        );
      case 'DENIED':
        return (
          <span className="px-3 py-1 rounded-full text-[10px] font-label-mono font-bold bg-error-container/50 text-error border border-error-container flex items-center gap-1.5 shadow-sm">
            <ShieldAlert className="w-3.5 h-3.5 text-error" />
            <span>GUARDRAIL REFUSAL</span>
          </span>
        );
      case 'ERROR':
        return (
          <span className="px-3 py-1 rounded-full text-[10px] font-label-mono font-bold bg-error-container/50 text-error border border-error-container flex items-center gap-1.5 shadow-sm">
            <AlertCircle className="w-3.5 h-3.5 text-error" />
            <span>SERVER ERROR</span>
          </span>
        );
      case 'IDLE':
      default:
        return (
          <span className="px-3 py-1 rounded-full text-[10px] font-label-mono font-bold bg-white text-on-surface-variant border border-surface-container flex items-center gap-1.5 shadow-sm">
            <Cpu className="w-3.5 h-3.5 text-outline" />
            <span>IDLE (B-3 READY)</span>
          </span>
        );
    }
  };

  return (
    <div className="bg-surface rounded-2xl p-4 border border-surface-container flex flex-col items-center justify-center space-y-3 shadow-sm">
      {/* Waveform Bars */}
      <div className="flex items-center space-x-1.5 h-8">
        {[0.4, 0.8, 1.2, 0.6, 1.0, 0.7, 1.3, 0.5, 0.9, 1.1, 0.6, 0.8].map((delay, idx) => (
          <div
            key={idx}
            className={`w-1 rounded-full transition-all duration-300 ${
              state === 'LISTENING'
                ? 'bg-escalation wave-bar'
                : state === 'SPEAKING'
                ? 'bg-secondary wave-bar'
                : state === 'THINKING' || state === 'EXECUTING'
                ? 'bg-primary-container wave-bar'
                : 'bg-surface-container-highest h-2'
            }`}
            style={{
              animationDelay: `${delay * 0.2}s`,
              height: state === 'IDLE' ? '6px' : undefined,
            }}
          />
        ))}
      </div>

      <div className="flex items-center space-x-2">{getStatusBadge()}</div>
    </div>
  );
};
