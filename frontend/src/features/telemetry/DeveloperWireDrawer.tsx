import React, { useState } from 'react';
import { Terminal, Copy, Check, ChevronDown, ChevronUp } from 'lucide-react';
import { useAgentGuard } from '../../context/AgentGuardContext';

export const DeveloperWireDrawer: React.FC = () => {
  const { rawWireLog, wireDrawerOpen, setWireDrawerOpen } = useAgentGuard();
  const [copied, setCopied] = useState(false);

  if (!wireDrawerOpen) {
    return (
      <div className="fixed bottom-0 right-6 z-30">
        <button
          onClick={() => setWireDrawerOpen(true)}
          className="px-4 py-2 bg-primary hover:bg-secondary text-white rounded-t-2xl shadow-xl text-xs font-inter font-semibold flex items-center gap-2 transition-all"
          title="Open Developer Wire Telemetry Inspector"
        >
          <Terminal className="w-3.5 h-3.5 text-secondary-fixed" />
          <span>Wire Telemetry</span>
          <ChevronUp className="w-3.5 h-3.5 text-white/80" />
        </button>
      </div>
    );
  }

  const handleCopy = () => {
    if (rawWireLog) {
      navigator.clipboard.writeText(JSON.stringify(rawWireLog, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="fixed bottom-0 inset-x-0 z-40 bg-white/95 border-t border-surface-container-high shadow-2xl backdrop-blur-xl transition-all duration-300 max-h-[360px] flex flex-col text-xs">
      {/* Drawer Header */}
      <div className="px-6 py-3 bg-surface border-b border-surface-container flex items-center justify-between font-inter">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-primary font-bold font-outfit text-sm">
            <Terminal className="w-4 h-4 text-secondary" />
            <span>Developer Wire Telemetry & Raw Protocol</span>
          </div>

          {rawWireLog && (
            <span
              className={`px-2.5 py-0.5 rounded-full text-xs font-semibold font-inter ${
                rawWireLog.status >= 200 && rawWireLog.status < 300
                  ? 'bg-[#F0FDF4] text-verified border border-[#BBF7D0]'
                  : rawWireLog.status === 403 || rawWireLog.status === 409
                  ? 'bg-error-container text-error border border-error-container'
                  : 'bg-[#FEF3C7] text-escalation border border-[#FDE68A]'
              }`}
            >
              HTTP {rawWireLog.status} ({rawWireLog.method})
            </span>
          )}

          {rawWireLog?.durationMs && (
            <span className="text-xs text-on-surface-variant font-inter">
              Latency: <span className="text-secondary font-bold font-mono">{rawWireLog.durationMs}ms</span>
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 font-inter">
          {rawWireLog && (
            <button
              onClick={handleCopy}
              className="px-3 py-1 bg-surface-container hover:bg-surface-container-high text-primary rounded-full text-xs font-semibold transition-colors flex items-center gap-1"
              title="Copy JSON Payload"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-verified" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
          )}

          <button
            onClick={() => setWireDrawerOpen(false)}
            className="p-1.5 hover:bg-surface-container text-on-surface-variant hover:text-primary rounded-full transition-colors"
            title="Minimize Drawer"
          >
            <ChevronDown className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Payload Viewer */}
      <div className="flex-1 p-6 overflow-y-auto grid grid-cols-1 md:grid-cols-2 gap-6 bg-[#FAFBFD]">
        {rawWireLog ? (
          <>
            <div>
              <div className="text-xs text-outline uppercase mb-1 font-bold font-inter">
                Request Target & Payload:
              </div>
              <div className="text-on-surface-variant mb-1 text-xs font-inter">
                Endpoint: <span className="text-primary font-bold font-mono">{rawWireLog.endpoint}</span>
              </div>
              <pre className="bg-[#1e1e1e] text-[#d4d4d4] p-4 rounded-xl font-mono overflow-x-auto text-[11px] leading-relaxed max-h-[200px] shadow-inner">
                {JSON.stringify(rawWireLog.requestBody || { note: 'No request payload / GET' }, null, 2)}
              </pre>
            </div>

            <div>
              <div className="text-xs text-outline uppercase mb-1 font-bold font-inter">
                Authoritative Server Response:
              </div>
              <div className="text-on-surface-variant mb-1 text-xs font-inter">
                Timestamp: <span className="text-primary font-bold font-mono">{rawWireLog.timestamp}</span>
              </div>
              <pre className="bg-[#1e1e1e] text-[#d4d4d4] p-4 rounded-xl font-mono overflow-x-auto text-[11px] leading-relaxed max-h-[200px] shadow-inner">
                {JSON.stringify(rawWireLog.responseBody, null, 2)}
              </pre>
            </div>
          </>
        ) : (
          <div className="col-span-2 text-center py-10 text-on-surface-variant text-xs font-inter">
            No HTTP traffic captured yet. Perform any proposal, scenario trigger, or mandate operation to observe wire protocol telemetry.
          </div>
        )}
      </div>
    </div>
  );
};
