import React, { useState, useRef, useEffect } from 'react';
import {
  Mic,
  MicOff,
  StopCircle,
  X,
  Bot,
  User,
  Zap,
  Send,
  RotateCcw,
  ShieldAlert,
  Database,
  FileCode2,
  ChevronDown,
  ChevronUp,
  Sparkles,
  CheckCircle2,
  Terminal,
  Activity,
  AlertCircle,
} from 'lucide-react';
import { useVoiceIO } from './useVoiceIO';
import { useAgentGuard, ChatMessageItem } from '../../context/AgentGuardContext';
import { VoiceWaveformVisualizer } from './VoiceWaveformVisualizer';
import { FollowUpSuggestion } from '../../lib/api';
import { useAutonomousDemo } from '../demo/AutonomousDemoContext';

/**
 * Safe Markdown text formatter that parses paragraphs, bold text, inline code,
 * bullet lists, and code blocks into native React elements without dangerous HTML injection.
 */
const SafeFormattedText: React.FC<{ text: string }> = ({ text }) => {
  if (!text) return null;

  // Split text by lines
  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];
  let currentList: React.ReactNode[] = [];
  let inCodeBlock = false;
  let codeBlockLines: string[] = [];

  const flushList = () => {
    if (currentList.length > 0) {
      elements.push(
        <ul key={`list-${elements.length}`} className="list-disc pl-4 my-1.5 space-y-1 text-on-surface">
          {currentList}
        </ul>
      );
      currentList = [];
    }
  };

  const formatInline = (str: string): React.ReactNode[] => {
    // Parse inline code `code` and bold **bold**
    const tokens: React.ReactNode[] = [];
    let remaining = str;
    let keyIdx = 0;

    while (remaining.length > 0) {
      // Check for inline code
      const codeMatch = remaining.match(/^(.*?)`([^`]+)`(.*)$/);
      // Check for bold
      const boldMatch = remaining.match(/^(.*?)\*\*([^*]+)\*\*(.*)$/);

      if (codeMatch && (!boldMatch || (codeMatch.index ?? 0) <= (boldMatch.index ?? 0))) {
        if (codeMatch[1]) tokens.push(codeMatch[1]);
        tokens.push(
          <code
            key={`code-${keyIdx++}`}
            className="px-1.5 py-0.5 bg-lavender-tint text-primary font-mono text-[11px] rounded border border-primary-fixed font-semibold"
          >
            {codeMatch[2]}
          </code>
        );
        remaining = codeMatch[3];
      } else if (boldMatch) {
        if (boldMatch[1]) tokens.push(boldMatch[1]);
        tokens.push(
          <strong key={`bold-${keyIdx++}`} className="font-semibold text-primary">
            {boldMatch[2]}
          </strong>
        );
        remaining = boldMatch[3];
      } else {
        tokens.push(remaining);
        break;
      }
    }
    return tokens;
  };

  lines.forEach((line, idx) => {
    const trimmed = line.trim();

    if (trimmed.startsWith('```')) {
      if (inCodeBlock) {
        // End of code block
        elements.push(
          <pre
            key={`codeblock-${idx}`}
            className="bg-[#1e1e1e] text-[#d4d4d4] p-3 rounded-lg font-mono text-[11px] overflow-x-auto my-2 shadow-inner"
          >
            <code>{codeBlockLines.join('\n')}</code>
          </pre>
        );
        codeBlockLines = [];
        inCodeBlock = false;
      } else {
        flushList();
        inCodeBlock = true;
      }
      return;
    }

    if (inCodeBlock) {
      codeBlockLines.push(line);
      return;
    }

    if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || /^\d+\.\s/.test(trimmed)) {
      const content = trimmed.replace(/^[-*]\s+|\d+\.\s+/, '');
      currentList.push(
        <li key={`li-${idx}`} className="text-xs leading-relaxed text-on-surface">
          {formatInline(content)}
        </li>
      );
      return;
    }

    flushList();

    if (trimmed.length > 0) {
      elements.push(
        <p key={`p-${idx}`} className="text-xs leading-relaxed text-on-surface my-1">
          {formatInline(trimmed)}
        </p>
      );
    }
  });

  flushList();

  if (inCodeBlock && codeBlockLines.length > 0) {
    elements.push(
      <pre
        key={`codeblock-end`}
        className="bg-[#1e1e1e] text-[#d4d4d4] p-3 rounded-lg font-mono text-[11px] overflow-x-auto my-2"
      >
        <code>{codeBlockLines.join('\n')}</code>
      </pre>
    );
  }

  return <div className="space-y-1">{elements}</div>;
};

export const ConversationalVoiceDrawer: React.FC = () => {
  const {
    isConversationalOpen,
    setIsConversationalOpen,
    agentVoiceState,
    setAgentVoiceState,
    conversationalSessionId,
    conversationalMessages,
    isConversationalQuerying,
    sendConversationalQuery,
    resetConversationalSession,
    setWireDrawerOpen,
  } = useAgentGuard();

  const [inputQuery, setInputQuery] = useState('');
  const [expandedCitationMsgId, setExpandedCitationMsgId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // ── Voice I/O — Phase 5.5C ────────────────────────────────────────────────
  // Routes all transcripts through the EXISTING sendConversationalQuery pipeline.
  // Never calls financial or mutation APIs directly.
  const {
    voiceState,
    voiceError,
    isSTTSupported,
    startListening,
    stopListening,
    stopSpeaking,
    dismissError,
  } = useVoiceIO({ sendConversationalQuery, setAgentVoiceState });

  // Auto-scroll on new messages
  useEffect(() => {
    if (isConversationalOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [conversationalMessages, isConversationalOpen, isConversationalQuerying]);

  // Focus input on drawer open
  useEffect(() => {
    if (isConversationalOpen) {
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [isConversationalOpen]);

  const { demoState } = useAutonomousDemo();

  // Drawer is mounted if opened or during any active demo state
  const isDemoActive = demoState !== 'IDLE';
  if (!isConversationalOpen && !isDemoActive) return null;

  // Drawer slides completely offscreen when demo is RUNNING, and returns on PAUSE / STOP / COMPLETED
  const isDrawerHidden = !isConversationalOpen || demoState === 'RUNNING';

  const handleSubmit = async (queryText: string) => {
    const trimmed = queryText.trim();
    if (!trimmed || isConversationalQuerying) return;
    setInputQuery('');
    await sendConversationalQuery(trimmed);
  };

  const handleSuggestionClick = async (suggestion: FollowUpSuggestion | string) => {
    if (isConversationalQuerying) return;
    const query = typeof suggestion === 'string' ? suggestion : (suggestion.query || suggestion.label);
    await sendConversationalQuery(query);
  };

  const latestAgentMessage = [...conversationalMessages]
    .reverse()
    .find((m) => m.sender === 'agent');

  return (
    <div
      className={`fixed inset-y-0 right-0 z-50 w-full sm:w-[500px] max-w-full bg-white border-l border-surface-container shadow-2xl backdrop-blur-2xl flex flex-col transition-transform duration-500 ease-in-out font-inter ${
        isDrawerHidden ? 'translate-x-full pointer-events-none' : 'translate-x-0'
      }`}
    >
      {/* Drawer Header */}
      <div className="p-4 sm:p-5 bg-surface border-b border-surface-container flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center text-white ring-4 ring-lavender-tint shadow-sm flex-shrink-0">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-primary font-outfit">The Voice of Trust</h3>
              <span className="text-[10px] font-inter font-semibold px-2 py-0.5 bg-lavender-tint text-[#4C1D95] rounded-full border border-primary-fixed flex items-center gap-1">
                <Sparkles className="w-2.5 h-2.5 text-primary" />
                <span>B-3 Brain Active</span>
              </span>
            </div>
            <p className="text-xs text-on-surface-variant font-inter">
              Grounded Conversational Intelligence & Diagnostics
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          {/* Reset / New Chat Button */}
          <button
            onClick={() => resetConversationalSession()}
            disabled={isConversationalQuerying}
            className="p-2 text-on-surface-variant hover:text-primary hover:bg-surface-container rounded-full transition-colors disabled:opacity-40"
            title="Start New Conversation Session"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          {/* Close Drawer Button */}
          <button
            onClick={() => setIsConversationalOpen(false)}
            className="p-2 text-on-surface-variant hover:text-primary hover:bg-surface-container rounded-full transition-colors"
            title="Close Assistant"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Voice Waveform Visualizer & Presence Section */}
      <div className="p-3.5 bg-gradient-to-b from-surface to-white border-b border-surface-container flex-shrink-0">
        <VoiceWaveformVisualizer state={agentVoiceState} />
      </div>

      {/* Messages Stream */}
      <div className="flex-1 p-4 overflow-y-auto space-y-4 text-xs bg-[#FAFBFD]">
        {conversationalMessages.map((m: ChatMessageItem) => {
          const isUser = m.sender === 'user';
          const isLatestAgent = !isUser && m.id === latestAgentMessage?.id;

          return (
            <div key={m.id} className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} space-y-1.5`}>
              {/* Message Bubble Container */}
              <div className={`flex items-start gap-2.5 max-w-[92%] ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
                {/* Avatar */}
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 shadow-sm mt-0.5 text-white ${
                    isUser ? 'bg-secondary' : m.isError ? 'bg-error' : 'bg-primary ring-2 ring-lavender-tint'
                  }`}
                >
                  {isUser ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
                </div>

                {/* Bubble Body */}
                <div
                  className={`rounded-2xl p-3.5 text-xs leading-relaxed shadow-sm font-inter ${
                    isUser
                      ? 'bg-primary text-white rounded-tr-none'
                      : m.isError
                      ? 'bg-error-container/30 border border-error-container text-on-surface rounded-tl-none space-y-2'
                      : 'bg-white border border-surface-container text-on-surface rounded-tl-none space-y-2'
                  }`}
                >
                  {/* Message Formatted Content */}
                  {isUser ? (
                    <div className="whitespace-pre-wrap">{m.text}</div>
                  ) : (
                    <SafeFormattedText text={m.text} />
                  )}

                  {/* Guardrail Refusal Banner (Zero Financial Authority) */}
                  {m.isAdversarialRefusal && (
                    <div className="mt-2 p-2.5 bg-[#FEF2F2] border border-[#FCA5A5] rounded-xl text-error flex items-start gap-2 text-[11px] font-inter">
                      <ShieldAlert className="w-4 h-4 text-error flex-shrink-0 mt-0.5" />
                      <div>
                        <div className="font-bold">Firewall Invariant Enforced</div>
                        <div className="text-on-surface-variant text-[10px]">
                          Conversational layer has zero financial authorization authority. Mutations must be executed via authenticated client flows.
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Live System Data Card */}
                  {m.liveDataUsed && (
                    <div className="mt-2 p-2.5 bg-[#F0FDF4] border border-[#BBF7D0] rounded-xl text-[11px] space-y-1.5 font-inter">
                      <div className="flex items-center gap-1.5 text-verified font-bold">
                        <Database className="w-3.5 h-3.5 text-verified" />
                        <span>Authoritative Live System Data</span>
                      </div>
                      {m.liveReadings && (
                        <div className="grid grid-cols-2 gap-1.5 text-[10px] bg-white/80 p-2 rounded-lg border border-[#DCFCE7]">
                          {Object.entries(m.liveReadings).map(([k, v]) => (
                            <div key={k} className="flex justify-between items-center pr-1">
                              <span className="text-on-surface-variant font-mono">{k}:</span>
                              <span className="font-bold text-primary font-mono">{String(v)}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Action Executed Badge */}
                  {m.actionStatus === 'EXECUTED' && m.actionDescription && (
                    <div className="mt-2 px-2.5 py-1.5 bg-lavender-tint text-primary border border-primary-fixed rounded-lg text-[11px] flex items-center justify-between font-semibold">
                      <div className="flex items-center gap-1.5">
                        <Zap className="w-3.5 h-3.5 text-primary" />
                        <span>{m.actionDescription}</span>
                      </div>
                      <CheckCircle2 className="w-3.5 h-3.5 text-verified" />
                    </div>
                  )}

                  {/* Progressive Disclosure Offer Prompt */}
                  {m.progressiveOffer && (
                    <div className="mt-2 p-2 bg-surface-container-low border border-surface-container rounded-lg text-[11px] text-primary italic flex items-center gap-2">
                      <Sparkles className="w-3.5 h-3.5 text-secondary flex-shrink-0" />
                      <span>{m.progressiveOffer}</span>
                    </div>
                  )}

                  {/* Citations & Evidence Provenance Accordion */}
                  {m.evidenceCitations && m.evidenceCitations.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-surface-container">
                      <button
                        onClick={() =>
                          setExpandedCitationMsgId(expandedCitationMsgId === m.id ? null : m.id)
                        }
                        className="text-[11px] font-semibold text-secondary hover:text-primary transition-colors flex items-center gap-1"
                      >
                        <FileCode2 className="w-3.5 h-3.5 text-secondary" />
                        <span>Authoritative Sources & Citations ({m.evidenceCitations.length})</span>
                        {expandedCitationMsgId === m.id ? (
                          <ChevronUp className="w-3 h-3 ml-0.5" />
                        ) : (
                          <ChevronDown className="w-3 h-3 ml-0.5" />
                        )}
                      </button>

                      {expandedCitationMsgId === m.id && (
                        <div className="mt-2 space-y-1.5">
                          {m.evidenceCitations.map((c, cIdx) => (
                            <div
                              key={cIdx}
                              className="p-2 bg-surface rounded-lg border border-surface-container text-[10px] space-y-1 font-mono"
                            >
                              <div className="flex justify-between items-center">
                                <span className="font-bold text-primary truncate max-w-[240px]">
                                  {c.unit_id || c.title || 'Evidence Unit'}
                                </span>
                                {c.authority && (
                                  <span className="px-1.5 py-0.5 bg-lavender-tint text-primary rounded text-[9px] font-bold">
                                    {c.authority}
                                  </span>
                                )}
                              </div>
                              {c.source_path && (
                                <div className="text-on-surface-variant truncate">
                                  File: <span className="text-secondary font-semibold">{c.source_path}</span>
                                </div>
                              )}
                              {c.snippet && (
                                <div className="text-on-surface-variant font-inter italic text-[10px] bg-white p-1 rounded border border-surface-container-high line-clamp-2">
                                  "{c.snippet}"
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Message Meta & Latency Badge */}
                  <div className="flex items-center justify-between text-[10px] text-on-surface-variant pt-1">
                    <span>{m.timestamp}</span>
                    {m.latencyMs !== undefined && (
                      <span className="font-mono text-secondary font-semibold">
                        Response: {m.latencyMs} ms
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Follow-up Suggestion Chips (Rendered on Latest Agent Message) */}
              {isLatestAgent && m.suggestedFollowups && m.suggestedFollowups.length > 0 && (
                <div className="pl-9 pr-2 pt-1.5 space-y-1.5 w-full">
                  <div className="flex items-center gap-1.5 text-[10px] text-outline font-bold uppercase tracking-wider">
                    <Sparkles className="w-3 h-3 text-secondary" />
                    <span>Suggested Next Questions</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {m.suggestedFollowups.map((s, sIdx) => {
                      const label = typeof s === 'string' ? s : (s.label || s.query);
                      return (
                        <button
                          key={sIdx}
                          onClick={() => handleSuggestionClick(s)}
                          disabled={isConversationalQuerying}
                          className="px-3 py-1.5 bg-white hover:bg-lavender-tint text-primary hover:text-primary rounded-full border border-surface-container hover:border-primary-fixed text-[11px] font-medium transition-all shadow-sm flex items-center gap-1.5 active:scale-95 disabled:opacity-50 text-left"
                        >
                          <span>{label}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {/* Loading Indicator while in-flight */}
        {isConversationalQuerying && (
          <div className="flex items-start gap-2.5 max-w-[85%]">
            <div className="w-7 h-7 rounded-full bg-primary text-white flex items-center justify-center flex-shrink-0 shadow-sm mt-0.5 ring-2 ring-lavender-tint">
              <Bot className="w-3.5 h-3.5" />
            </div>
            <div className="bg-white border border-surface-container rounded-2xl rounded-tl-none p-3.5 shadow-sm space-y-1">
              <div className="flex items-center gap-2 text-primary font-semibold text-xs">
                <Activity className="w-3.5 h-3.5 animate-spin text-secondary" />
                <span>B-3 Conversational Brain is evaluating query...</span>
              </div>
              <p className="text-[11px] text-on-surface-variant font-inter">
                Resolving context, AST evidence retrieval, and safety invariants.
              </p>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* System State & Telemetry Feedback Bar */}
      <div className="p-2.5 px-4 bg-surface border-t border-surface-container text-xs font-inter flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-2 truncate">
          <span className="w-2 h-2 rounded-full bg-verified animate-pulse flex-shrink-0"></span>
          <span className="text-[11px] text-on-surface-variant truncate">
            {conversationalSessionId
              ? `Session: ${conversationalSessionId.substring(0, 18)}...`
              : 'New Dialogue Session Ready'}
          </span>
        </div>

        <button
          onClick={() => setWireDrawerOpen(true)}
          className="text-[11px] text-secondary hover:text-primary font-semibold flex items-center gap-1 flex-shrink-0 transition-colors"
          title="Inspect Wire Telemetry"
        >
          <Terminal className="w-3 h-3 text-secondary" />
          <span>Wire Telemetry</span>
        </button>
      </div>

      {/* Voice Error Banner */}
      {voiceError && (
        <div className="px-4 py-2.5 bg-[#FEF2F2] border-t border-[#FCA5A5] flex items-start gap-2 flex-shrink-0">
          <AlertCircle className="w-3.5 h-3.5 text-error flex-shrink-0 mt-0.5" />
          <span className="text-[11px] text-error font-inter flex-1 leading-snug">{voiceError}</span>
          <button
            onClick={dismissError}
            className="text-error hover:text-[#7f1d1d] transition-colors flex-shrink-0"
            title="Dismiss"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Voice Status Label — shown while actively in a voice state */}
      {(voiceState === 'LISTENING' || voiceState === 'PROCESSING' || voiceState === 'SPEAKING') && (
        <div className="px-4 py-1.5 bg-lavender-tint border-t border-primary-fixed flex items-center justify-between flex-shrink-0">
          <span className="text-[11px] font-semibold text-primary font-inter animate-pulse">
            {voiceState === 'LISTENING' && '🎙 Listening…'}
            {voiceState === 'PROCESSING' && '⚙️ Thinking…'}
            {voiceState === 'SPEAKING' && '🔊 AgentGuard is speaking…'}
          </span>
          {voiceState === 'SPEAKING' && (
            <button
              onClick={stopSpeaking}
              className="text-[11px] text-secondary hover:text-primary font-semibold flex items-center gap-1 transition-colors"
              title="Stop speaking"
            >
              <StopCircle className="w-3.5 h-3.5" />
              <span>Stop</span>
            </button>
          )}
        </div>
      )}

      {/* Input Bar */}
      <div className="p-3.5 sm:p-4 bg-white border-t border-surface-container flex items-center gap-2 flex-shrink-0">
        {/* Mic Button — Phase 5.5C real STT */}
        {voiceState === 'IDLE' && (
          isSTTSupported ? (
            <button
              onClick={startListening}
              disabled={isConversationalQuerying}
              className="p-2.5 text-secondary hover:bg-secondary-fixed/50 rounded-full transition-all flex-shrink-0 disabled:opacity-40"
              title="Talk to AgentGuard (voice input)"
            >
              <Mic className="w-4 h-4" />
            </button>
          ) : (
            <button
              disabled
              className="p-2.5 text-on-surface-variant rounded-full flex-shrink-0 opacity-40 cursor-not-allowed"
              title="Voice input is not supported in this browser. Use Chrome for voice."
            >
              <MicOff className="w-4 h-4" />
            </button>
          )
        )}

        {voiceState === 'LISTENING' && (
          <button
            onClick={stopListening}
            className="p-2.5 text-error bg-[#FEF2F2] hover:bg-[#FEE2E2] rounded-full transition-all flex-shrink-0 animate-pulse"
            title="Stop listening"
          >
            <MicOff className="w-4 h-4" />
          </button>
        )}

        {(voiceState === 'PROCESSING' || voiceState === 'SPEAKING') && (
          <button
            disabled
            className="p-2.5 text-primary rounded-full flex-shrink-0 opacity-60 cursor-not-allowed"
            title={voiceState === 'SPEAKING' ? 'AgentGuard is speaking' : 'Processing…'}
          >
            <Activity className="w-4 h-4 animate-spin" />
          </button>
        )}

        {voiceState === 'ERROR' && (
          <button
            onClick={dismissError}
            className="p-2.5 text-error hover:bg-[#FEF2F2] rounded-full transition-all flex-shrink-0"
            title="Voice error — click to dismiss"
          >
            <MicOff className="w-4 h-4" />
          </button>
        )}

        {/* Text Input */}
        <input
          ref={inputRef}
          type="text"
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(inputQuery);
            }
          }}
          disabled={isConversationalQuerying || voiceState === 'LISTENING' || voiceState === 'PROCESSING'}
          placeholder={
            voiceState === 'LISTENING'
              ? 'Listening… speak your question'
              : voiceState === 'PROCESSING'
              ? 'Processing your question…'
              : voiceState === 'SPEAKING'
              ? 'AgentGuard is speaking…'
              : 'Ask AgentGuard architecture, threats, or live state…'
          }
          className="flex-1 bg-surface-container-low text-on-surface text-xs px-4 py-2.5 rounded-full border border-surface-container focus:outline-none focus:border-secondary transition-colors font-inter disabled:opacity-60"
        />

        {/* Send Button */}
        <button
          onClick={() => handleSubmit(inputQuery)}
          disabled={isConversationalQuerying || !inputQuery.trim() || voiceState === 'LISTENING' || voiceState === 'PROCESSING'}
          className="p-2.5 bg-primary hover:bg-secondary disabled:opacity-40 text-white rounded-full transition-all shadow-sm flex items-center justify-center flex-shrink-0 active:scale-95"
          title="Send query"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
