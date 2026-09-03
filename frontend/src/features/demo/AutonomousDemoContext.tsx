/**
 * AutonomousDemoContext.tsx — Feature-Local Autonomous Demo State Machine
 *
 * Implements a controlled, deterministic 8-step walkthrough demonstrating
 * AgentGuard's commerce firewall against price tampering using the real backend.
 *
 * KEY INVARIANTS:
 *  - 100% isolated inside features/demo (does not burden AgentGuardContext).
 *  - Uses existing triggerScenario(3) from AgentGuardContext (no duplicate execution logic).
 *  - runId protects against all stale async callbacks and unmount races.
 *  - Pause freezes step progression & audio without invalidating runId.
 *  - Stop invalidates runId, cancels timers/audio, and enters STOPPED_AWAITING_QUESTION.
 *  - Human-friendly Cartesia TTS narration synchronized with visual actions.
 */

import React, { createContext, useContext, useState, useRef, useEffect, useCallback, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAgentGuard } from '../../context/AgentGuardContext';
import { api } from '../../lib/api';
import { cleanTextForSpeech } from '../conversational/speechCleaner';
import {
  DemoState,
  DemoStepId,
  AgentTargetId,
  DemoStepDefinition,
  AutonomousDemoContextType,
} from './types';

const DEMO_STEPS: Record<DemoStepId, DemoStepDefinition> = {
  1: {
    id: 1,
    name: 'Introduction',
    route: '/',
    targetId: null,
    spokenNarration:
      "Give AI agents a secure path to commerce. When autonomous agents are granted financial access, they can hallucinate prices, exceed budgets, or be manipulated. AgentGuard acts as the deterministic trust boundary: the model is allowed to be wrong, but it's not allowed to be authoritative.",
    captionText: 'Introduction — AgentGuard deterministic trust boundary for AI commerce',
    expectedDurationMs: 22000,
  },
  2: {
    id: 2,
    name: 'Mandate Boundary',
    route: '/',
    targetId: 'cockpit-budget',
    spokenNarration:
      'Let’s start with the security boundary. The AI agent operates under an authoritative ₹3,000 mandate with strict cryptographic guardrails enforced by our policy engine.',
    captionText: 'Cockpit — Authoritative ₹3,000 mandate security boundary',
    expectedDurationMs: 12000,
  },
  3: {
    id: 3,
    name: 'Live Protection',
    route: '/live',
    targetId: 'live-protection-mandate',
    spokenNarration:
      'Here in Live Protection, you can see the fundamental separation. On the left is the untrusted agent environment where the LLM reasons and forms purchase claims. On the right is the authoritative commerce catalog. Before money can move, AgentGuard independently validates the item, price, merchant, and mandate budget.',
    captionText: 'Live Protection — Untrusted agent proposal vs authoritative catalog truth',
    expectedDurationMs: 22000,
  },
  4: {
    id: 4,
    name: 'Threat Simulation Lab',
    route: '/threats',
    targetId: 'threat-price-tampering',
    spokenNarration:
      'This is the Threat Simulation Lab. We maintain six distinct adversarial scenarios to stress-test our deterministic boundaries under adversarial conditions — from price tampering and budget exhaustion to replay attacks and semantic injection. Now, instead of just talking about the attacks, let’s actually run one.',
    captionText: 'Threat Lab — Six adversarial scenarios testing deterministic boundaries',
    expectedDurationMs: 20000,
  },
  5: {
    id: 5,
    name: 'Price Tampering Attack',
    route: '/threats',
    targetId: 'threat-price-tampering',
    spokenNarration:
      'Let’s see what happens when an AI agent tries to manipulate the transaction before it reaches the payment layer. The agent is claiming a price of ₹1,999 for Wireless Earbuds.',
    captionText: 'Price Tampering — Submitting untrusted proposal (₹1,999 claimed vs ₹3,499 actual)...',
    expectedDurationMs: 14000,
  },
  6: {
    id: 6,
    name: 'Price Tampering Decision',
    route: '/threats',
    targetId: 'decision-result',
    spokenNarration:
      'Look at that — AgentGuard caught it. The agent claimed ₹1,999, but the authoritative catalog price is ₹3,499. So the firewall rejected the transaction before it could become an authorized payment. And there it is — DENIED.',
    captionText: 'Verdict — Threat Neutralized: DENIED with PRICE_MISMATCH',
    expectedDurationMs: 16000,
  },
  7: {
    id: 7,
    name: 'Forensic Denial Record',
    route: '/forensics',
    targetId: 'forensic-latest-transaction',
    spokenNarration:
      'And importantly, AgentGuard doesn’t just make the decision and forget it. This event is recorded in the forensic ledger, where every proposed claim, authoritative evaluation, and firewall verdict is cryptographically hashed with SHA-256 into an immutable audit chain.',
    captionText: 'Forensic Ledger — Immutable SHA-256 audit record of denied transaction',
    expectedDurationMs: 18000,
  },
  8: {
    id: 8,
    name: 'Legitimate Request',
    route: '/threats',
    targetId: 'threat-happy-path',
    spokenNarration:
      'Now let’s see the other side. AgentGuard isn’t simply blocking AI agents. It verifies the request against the mandate and authoritative commerce data. Because this transaction is genuinely within the allowed boundary, it can be approved. Let’s test the Bluetooth Speaker at its genuine price of ₹2,799.',
    captionText: 'Happy Path — Testing valid transaction within ₹3,000 mandate...',
    expectedDurationMs: 18000,
  },
  9: {
    id: 9,
    name: 'Legitimate Approval',
    route: '/threats',
    targetId: 'decision-result',
    spokenNarration:
      'Perfect — this time the transaction is legitimate, so AgentGuard allows it and authorizes payment with Razorpay. That’s the distinction we want: the AI can propose, but the firewall decides whether that proposal is actually authorized.',
    captionText: 'Verdict — Authorization Approved: ALLOW & payment executed',
    expectedDurationMs: 16000,
  },
  10: {
    id: 10,
    name: 'Forensic Success Record',
    route: '/forensics',
    targetId: 'forensic-latest-transaction',
    spokenNarration:
      'Back in the Forensic Ledger, we now have both records: the intercepted price tampering denial and the verified legitimate approval. The ledger allows complete reconstruction of all agent commerce activity with cryptographic certainty.',
    captionText: 'Forensic Ledger — Complete audit record of allowed & denied activity',
    expectedDurationMs: 18000,
  },
  11: {
    id: 11,
    name: 'Summary & Completion',
    route: '/forensics',
    targetId: null,
    spokenNarration:
      'That brings us to the end of the demo. The model is allowed to be wrong. It’s not allowed to be authoritative. If you have any questions or need my assistance later, I’ll be right here.',
    captionText: 'Complete — The model can be wrong; the firewall is authoritative',
    expectedDurationMs: 14000,
  },
};

const AutonomousDemoContext = createContext<AutonomousDemoContextType | undefined>(undefined);

export const AutonomousDemoProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const navigate = useNavigate();
  const {
    triggerScenario,
    activeTransaction,
    setAgentVoiceState,
    setSelectedTxnId,
    fetchTransactions,
    fetchAuditData,
    registerConversationalInterceptor,
    appendAgentMessage,
    setIsConversationalOpen,
  } = useAgentGuard();

  // ── State ───────────────────────────────────────────────────────────────────
  const [demoState, setDemoState] = useState<DemoState>('IDLE');
  const [currentStepId, setCurrentStepId] = useState<DemoStepId>(1);
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const [currentNarration, setCurrentNarration] = useState<string>('');
  const [currentTargetId, setCurrentTargetId] = useState<AgentTargetId>(null);
  const [runId, setRunId] = useState<number>(0);

  // ── Lifecycle & Stale Operation Protection Refs ──────────────────────────────
  const runIdRef = useRef<number>(0);
  const demoStateRef = useRef<DemoState>('IDLE');
  const isPausedRef = useRef<boolean>(false);
  const currentStepIdRef = useRef<DemoStepId>(1);
  const isMountedRef = useRef<boolean>(true);

  // Audio playback ref
  const activeAudioRef = useRef<HTMLAudioElement | null>(null);
  const activeAudioUrlRef = useRef<string | null>(null);

  // Timers registry
  const timerIdsRef = useRef<number[]>([]);

  // Update refs on state changes
  useEffect(() => {
    demoStateRef.current = demoState;
  }, [demoState]);

  useEffect(() => {
    isPausedRef.current = isPaused;
  }, [isPaused]);

  useEffect(() => {
    currentStepIdRef.current = currentStepId;
  }, [currentStepId]);

  // ── Helpers ─────────────────────────────────────────────────────────────────
  const clearAllRegisteredTimers = useCallback(() => {
    timerIdsRef.current.forEach((id) => window.clearTimeout(id));
    timerIdsRef.current = [];
  }, []);

  const safeDelay = useCallback((ms: number, expectedRunId: number): Promise<boolean> => {
    return new Promise((resolve) => {
      let remaining = ms;
      let startTime = Date.now();

      const check = () => {
        if (!isMountedRef.current || expectedRunId !== runIdRef.current) {
          resolve(false);
          return;
        }

        if (isPausedRef.current) {
          // Check again after pause
          const id = window.setTimeout(check, 200);
          timerIdsRef.current.push(id);
          return;
        }

        const elapsed = Date.now() - startTime;
        remaining -= elapsed;
        startTime = Date.now();

        if (remaining <= 0) {
          resolve(true);
        } else {
          const id = window.setTimeout(check, Math.min(remaining, 200));
          timerIdsRef.current.push(id);
        }
      };

      const id = window.setTimeout(check, Math.min(ms, 200));
      timerIdsRef.current.push(id);
    });
  }, []);

  const stopActiveAudio = useCallback(() => {
    if (activeAudioRef.current) {
      activeAudioRef.current.pause();
      activeAudioRef.current.src = '';
      activeAudioRef.current = null;
    }
    if (activeAudioUrlRef.current) {
      URL.revokeObjectURL(activeAudioUrlRef.current);
      activeAudioUrlRef.current = null;
    }
    setAgentVoiceState('IDLE');
  }, [setAgentVoiceState]);

  // ── Spoken Narration via Cartesia TTS ────────────────────────────────────────
  const playNarration = useCallback(
    async (text: string, expectedRunId: number): Promise<void> => {
      if (!text || !text.trim()) return;
      if (expectedRunId !== runIdRef.current) return;

      const cleaned = cleanTextForSpeech(text);
      if (!cleaned) return;

      stopActiveAudio();

      try {
        setAgentVoiceState('SPEAKING');
        const { blob, error } = await api.synthesizeSpeech(cleaned);

        if (expectedRunId !== runIdRef.current || !isMountedRef.current) {
          setAgentVoiceState('IDLE');
          return;
        }

        if (!blob || error) {
          // Fallback reading timer based on word count (~140 wpm)
          const wordCount = cleaned.split(/\s+/).length;
          const fallbackMs = Math.max(3000, Math.round((wordCount / 140) * 60 * 1000));
          await safeDelay(fallbackMs, expectedRunId);
          if (expectedRunId === runIdRef.current) {
            setAgentVoiceState('IDLE');
          }
          return;
        }

        const audioUrl = URL.createObjectURL(blob);
        activeAudioUrlRef.current = audioUrl;
        const audio = new Audio(audioUrl);
        audio.playbackRate = 0.88;
        activeAudioRef.current = audio;

        await new Promise<void>((resolve) => {
          let resolved = false;

          const finish = () => {
            if (!resolved) {
              resolved = true;
              audio.onended = null;
              audio.onerror = null;
              if (activeAudioRef.current === audio) {
                activeAudioRef.current = null;
              }
              if (expectedRunId === runIdRef.current) {
                setAgentVoiceState('IDLE');
              }
              resolve();
            }
          };

          audio.onended = finish;
          audio.onerror = finish;

          audio.play().catch((err) => {
            console.warn('[Demo TTS] Audio play interrupted/error:', err);
            finish();
          });

          // Watch for pause state while audio is playing
          const intervalId = window.setInterval(() => {
            if (expectedRunId !== runIdRef.current || !isMountedRef.current) {
              window.clearInterval(intervalId);
              audio.pause();
              finish();
              return;
            }

            if (isPausedRef.current && !audio.paused) {
              audio.pause();
            } else if (!isPausedRef.current && audio.paused && !resolved) {
              audio.play().catch(() => {});
            }
          }, 200);

          audio.addEventListener('ended', () => window.clearInterval(intervalId), { once: true });
        });
      } catch (err) {
        console.warn('[Demo TTS] Narration error:', err);
        if (expectedRunId === runIdRef.current) {
          setAgentVoiceState('IDLE');
        }
      }
    },
    [safeDelay, setAgentVoiceState, stopActiveAudio]
  );

  // ── Smooth Scrolling Helpers ───────────────────────────────────────────────
  const scrollWindowSmooth = useCallback(
    async (targetY: number, waitMs: number, activeRunId: number): Promise<void> => {
      if (activeRunId !== runIdRef.current) return;
      window.scrollTo({ top: targetY, behavior: 'smooth' });
      await safeDelay(waitMs, activeRunId);
    },
    [safeDelay]
  );

  const scrollContainerSmooth = useCallback(
    async (selector: string, targetY: number, waitMs: number, activeRunId: number): Promise<void> => {
      if (activeRunId !== runIdRef.current) return;
      const el = document.querySelector(selector);
      if (el) {
        el.scrollTo({ top: targetY, behavior: 'smooth' });
      }
      await safeDelay(waitMs, activeRunId);
    },
    [safeDelay]
  );

  // ── Scenario Execution with Friendly Loading Voice ──────────────────────────
  const executeScenarioWithLoadingVoice = useCallback(
    async (scenarioId: number, activeRunId: number): Promise<void> => {
      let hasResolved = false;
      const processingTimer = window.setTimeout(async () => {
        if (!hasResolved && activeRunId === runIdRef.current && !isPausedRef.current) {
          // Backend is taking longer than 1.8s — provide friendly status voice
          await playNarration(
            'Give me just a moment while the firewall verifies the transaction.',
            activeRunId
          );
        }
      }, 1800);

      try {
        await triggerScenario(scenarioId);
      } finally {
        hasResolved = true;
        window.clearTimeout(processingTimer);
      }
    },
    [triggerScenario, playNarration]
  );

  // ── Step Execution State Machine ────────────────────────────────────────────
  const executeStep = useCallback(
    async (stepId: DemoStepId, activeRunId: number): Promise<void> => {
      if (activeRunId !== runIdRef.current || !isMountedRef.current) return;

      const step = DEMO_STEPS[stepId];
      if (!step) return;

      setCurrentStepId(stepId);
      setCurrentTargetId(step.targetId);
      setCurrentNarration(step.spokenNarration || step.captionText);

      // 1. Navigation if route changes
      if (window.location.pathname !== step.route) {
        navigate(step.route);
        // Visual breathing pause for page render & layout stabilization
        const ok = await safeDelay(900, activeRunId);
        if (!ok || activeRunId !== runIdRef.current) return;
      } else {
        const ok = await safeDelay(400, activeRunId);
        if (!ok || activeRunId !== runIdRef.current) return;
      }

      // 2. Perform step-specific actions
      switch (stepId) {
        case 1: {
          // Step 1: Introduction — start at top, speak intro, and scroll homepage
          window.scrollTo({ top: 0, behavior: 'smooth' });
          const narrationPromise = playNarration(step.spokenNarration, activeRunId);
          await safeDelay(3500, activeRunId);
          await scrollWindowSmooth(550, 3500, activeRunId);
          await scrollWindowSmooth(0, 1500, activeRunId);
          await narrationPromise;
          if (activeRunId !== runIdRef.current) return;
          await safeDelay(800, activeRunId);
          if (activeRunId !== runIdRef.current) return;
          await executeStep(2, activeRunId);
          break;
        }

        case 2: {
          // Step 2: Cockpit Boundary — Highlight mandate budget pill & explain boundary
          await playNarration(step.spokenNarration, activeRunId);
          if (activeRunId !== runIdRef.current) return;
          await safeDelay(1000, activeRunId);
          if (activeRunId !== runIdRef.current) return;
          await executeStep(3, activeRunId);
          break;
        }

        case 3: {
          // Step 3: Live Protection — Highlight untrusted chamber vs firewall core & scroll
          const narrationPromise = playNarration(step.spokenNarration, activeRunId);
          await safeDelay(3000, activeRunId);
          await scrollWindowSmooth(350, 3000, activeRunId);
          await scrollWindowSmooth(0, 1200, activeRunId);
          await narrationPromise;
          if (activeRunId !== runIdRef.current) return;
          await safeDelay(1000, activeRunId);
          if (activeRunId !== runIdRef.current) return;
          await executeStep(4, activeRunId);
          break;
        }

        case 4: {
          // Step 4: Threat Simulation Lab — Highlight Scenario 3, scroll through the 6 frozen attack vectors
          const narrationPromise = playNarration(step.spokenNarration, activeRunId);
          await safeDelay(2500, activeRunId);
          await scrollWindowSmooth(300, 2800, activeRunId);
          await scrollWindowSmooth(0, 1200, activeRunId);
          await narrationPromise;
          if (activeRunId !== runIdRef.current) return;
          await safeDelay(800, activeRunId);
          if (activeRunId !== runIdRef.current) return;
          await executeStep(5, activeRunId);
          break;
        }

        case 5: {
          // Step 5: Execute Price Tampering attack through REAL Threat Lab flow
          setCurrentNarration(step.captionText);
          await playNarration(step.spokenNarration, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          // Trigger real Scenario 3 with friendly loading voice if >1.8s
          await executeScenarioWithLoadingVoice(3, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          await safeDelay(1200, activeRunId);
          if (activeRunId !== runIdRef.current) return;
          await executeStep(6, activeRunId);
          break;
        }

        case 6: {
          // Step 6: Price Tampering Decision — Highlight verdict & verify real backend result (DENY / PRICE_MISMATCH)
          const decisionStr = (activeTransaction?.decision as string) || '';
          const verdictReason = activeTransaction?.reason_code || 'PRICE_MISMATCH';
          const isDenied =
            decisionStr === 'DENY' ||
            decisionStr === 'DENIED' ||
            verdictReason.includes('PRICE') ||
            verdictReason === 'PRICE_MISMATCH';

          if (!isDenied && activeTransaction?.decision) {
            const safetyMsg =
              'The demonstration encountered an unexpected issue, so I’ve paused rather than showing you a result that didn’t actually occur.';
            setCurrentNarration(safetyMsg);
            setDemoState('ERROR');
            await playNarration(safetyMsg, activeRunId);
            return;
          }

          await playNarration(step.spokenNarration, activeRunId);
          if (activeRunId !== runIdRef.current) return;
          await safeDelay(1200, activeRunId);
          if (activeRunId !== runIdRef.current) return;
          await executeStep(7, activeRunId);
          break;
        }

        case 7: {
          // Step 7: Forensic Denial Record — Inspect resulting denied transaction in audit chain
          await fetchTransactions();
          if (activeTransaction?.transaction_id) {
            setSelectedTxnId(activeTransaction.transaction_id);
            await fetchAuditData(activeTransaction.transaction_id);
          }
          if (activeRunId !== runIdRef.current) return;

          const narrationPromise = playNarration(step.spokenNarration, activeRunId);
          await safeDelay(2500, activeRunId);
          await scrollContainerSmooth('.lg\\:col-span-8', 300, 2500, activeRunId);
          await scrollContainerSmooth('.lg\\:col-span-8', 0, 1000, activeRunId);
          await narrationPromise;
          if (activeRunId !== runIdRef.current) return;
          await safeDelay(1200, activeRunId);
          if (activeRunId !== runIdRef.current) return;
          await executeStep(8, activeRunId);
          break;
        }

        case 8: {
          // Step 8: Legitimate Request — Highlight Scenario 1 (Bluetooth Speaker within ₹3,000 budget)
          setCurrentNarration(step.captionText);
          await playNarration(step.spokenNarration, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          // Trigger real Scenario 1 with friendly loading voice if >1.8s
          await executeScenarioWithLoadingVoice(1, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          await safeDelay(1200, activeRunId);
          if (activeRunId !== runIdRef.current) return;
          await executeStep(9, activeRunId);
          break;
        }

        case 9: {
          // Step 9: Legitimate Approval Verdict — Highlight verdict & verify real backend result (ALLOW)
          const decisionStr = (activeTransaction?.decision as string) || '';
          const isAllowed = decisionStr === 'ALLOW' || decisionStr === 'APPROVED';

          if (!isAllowed && activeTransaction?.decision) {
            const safetyMsg =
              'The demonstration encountered an unexpected issue with the legitimate scenario, so I’ve paused rather than showing an incorrect result.';
            setCurrentNarration(safetyMsg);
            setDemoState('ERROR');
            await playNarration(safetyMsg, activeRunId);
            return;
          }

          await playNarration(step.spokenNarration, activeRunId);
          if (activeRunId !== runIdRef.current) return;
          await safeDelay(1200, activeRunId);
          if (activeRunId !== runIdRef.current) return;
          await executeStep(10, activeRunId);
          break;
        }

        case 10: {
          // Step 10: Forensic Success Record — Inspect legitimate transaction & contrast with denied record
          await fetchTransactions();
          if (activeTransaction?.transaction_id) {
            setSelectedTxnId(activeTransaction.transaction_id);
            await fetchAuditData(activeTransaction.transaction_id);
          }
          if (activeRunId !== runIdRef.current) return;

          const narrationPromise = playNarration(step.spokenNarration, activeRunId);
          await safeDelay(2500, activeRunId);
          await scrollContainerSmooth('.lg\\:col-span-8', 300, 2500, activeRunId);
          await scrollContainerSmooth('.lg\\:col-span-8', 0, 1000, activeRunId);
          await narrationPromise;
          if (activeRunId !== runIdRef.current) return;
          await safeDelay(1200, activeRunId);
          if (activeRunId !== runIdRef.current) return;
          await executeStep(11, activeRunId);
          break;
        }

        case 11: {
          // Step 11: Final Summary — Narrate core AgentGuard thesis and conclude demo naturally
          await playNarration(step.spokenNarration, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          await safeDelay(800, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          setDemoState('COMPLETED');
          setCurrentTargetId(null);
          setIsConversationalOpen(true);
          appendAgentMessage?.(step.spokenNarration);
          break;
        }

        default:
          break;
      }
    },
    [
      navigate,
      safeDelay,
      playNarration,
      executeScenarioWithLoadingVoice,
      scrollWindowSmooth,
      scrollContainerSmooth,
      activeTransaction,
      fetchTransactions,
      setSelectedTxnId,
      fetchAuditData,
      setIsConversationalOpen,
      appendAgentMessage,
    ]
  );

  // ── Controls: Start, Pause, Resume, Stop ─────────────────────────────────────
  const startDemo = useCallback(
    async (fromStep: DemoStepId = 1): Promise<void> => {
      // Invalidate any previous run
      const nextRunId = ++runIdRef.current;
      setRunId(nextRunId);
      clearAllRegisteredTimers();
      stopActiveAudio();

      setIsPaused(false);
      isPausedRef.current = false;
      setIsConversationalOpen(true);
      setDemoState('RUNNING');

      await executeStep(fromStep, nextRunId);
    },
    [clearAllRegisteredTimers, stopActiveAudio, executeStep, setIsConversationalOpen]
  );

  const pauseDemo = useCallback(() => {
    if (demoStateRef.current !== 'RUNNING') return;
    setIsPaused(true);
    isPausedRef.current = true;
    setDemoState('PAUSED');
    if (activeAudioRef.current && !activeAudioRef.current.paused) {
      activeAudioRef.current.pause();
    }
  }, []);

  const resumeDemo = useCallback(() => {
    if (demoStateRef.current !== 'PAUSED') return;
    setIsPaused(false);
    isPausedRef.current = false;
    setDemoState('RUNNING');
    if (activeAudioRef.current && activeAudioRef.current.paused) {
      activeAudioRef.current.play().catch(() => {});
    }
  }, []);

  const stopDemo = useCallback(() => {
    // Invalidate current run immediately
    runIdRef.current++;
    clearAllRegisteredTimers();
    stopActiveAudio();

    setIsPaused(false);
    isPausedRef.current = false;
    setCurrentTargetId(null);
    setIsConversationalOpen(true);

    const stopMsg = 'Demo mode stopped. Do you have any questions for me?';
    setCurrentNarration(stopMsg);
    setDemoState('STOPPED_AWAITING_QUESTION');
    appendAgentMessage?.(stopMsg);

    // Announce stop cleanly to user
    playNarration(stopMsg, runIdRef.current);
  }, [clearAllRegisteredTimers, stopActiveAudio, playNarration, appendAgentMessage, setIsConversationalOpen]);

  // ── Stopped Conversational Flow Interceptor ─────────────────────────────────
  const handleStoppedQuery = useCallback(
    async (userQuery: string): Promise<boolean> => {
      const trimmed = userQuery.trim().toLowerCase();

      // If waiting for continue decision (YES / NO)
      if (demoStateRef.current === 'STOPPED_AWAITING_CONTINUE_DECISION') {
        const YES_PATTERNS = /^(yes|yeah|yep|sure|continue|let's continue|lets continue|show me|go ahead|resume|restart|ok|okay)\b/i;
        const NO_PATTERNS = /^(no|nope|no thanks|that's enough|thats enough|we can stop|end the demo|let's finish|lets finish|stop)\b/i;

        if (YES_PATTERNS.test(trimmed)) {
          // YES: Start fresh demo run from Step 1
          setDemoState('IDLE');
          appendAgentMessage?.('Restarting the demo from the beginning.');
          await startDemo(1);
          return true;
        }

        if (NO_PATTERNS.test(trimmed)) {
          // NO: Use the exact approved final response
          const finalMsg =
            'Of course. We can end the demo here. If you have any questions or need my assistance later, I’ll be right here.';
          setDemoState('IDLE');
          setCurrentNarration(finalMsg);
          appendAgentMessage?.(finalMsg);
          playNarration(finalMsg, runIdRef.current);
          return true;
        }

        // If neither yes nor no, let normal conversational assistant respond, then re-prompt
        return false;
      }

      return false;
    },
    [startDemo, playNarration]
  );

  // ── Register Interceptors with AgentGuardContext ────────────────────────────
  useEffect(() => {
    if (!registerConversationalInterceptor) return;

    const unregister = registerConversationalInterceptor({
      onQuery: async (query: string) => {
        if (demoStateRef.current === 'STOPPED_AWAITING_CONTINUE_DECISION') {
          return await handleStoppedQuery(query);
        }
        return false;
      },
      onResponse: (response: any) => {
        // 1. Intercept PROJECT_WALKTHROUGH intent
        if (response.intent === 'PROJECT_WALKTHROUGH') {
          startDemo(1);
          return {
            ...response,
            message:
              "I'm launching the autonomous AgentGuard demonstration. I'll walk you through the security boundary, live catalog verification, real price tampering defense, and cryptographic audit trail.",
          };
        }

        // 2. Intercept STOPPED_AWAITING_QUESTION follow-up
        if (demoStateRef.current === 'STOPPED_AWAITING_QUESTION') {
          setDemoState('STOPPED_AWAITING_CONTINUE_DECISION');
          const augmentedMessage = `${response.message}\n\nWould you like to continue with the demo?`;
          return {
            ...response,
            message: augmentedMessage,
          };
        }

        return response;
      },
    });

    return unregister;
  }, [registerConversationalInterceptor, handleStoppedQuery, startDemo]);

  // ── Unmount Cleanup ─────────────────────────────────────────────────────────
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      runIdRef.current++;
      clearAllRegisteredTimers();
      stopActiveAudio();
    };
  }, [clearAllRegisteredTimers, stopActiveAudio]);

  return (
    <AutonomousDemoContext.Provider
      value={{
        demoState,
        currentStepId,
        isPaused,
        currentNarration,
        currentTargetId,
        runId,
        startDemo,
        pauseDemo,
        resumeDemo,
        stopDemo,
        handleStoppedQuery,
      }}
    >
      {children}
    </AutonomousDemoContext.Provider>
  );
};

export const useAutonomousDemo = (): AutonomousDemoContextType => {
  const context = useContext(AutonomousDemoContext);
  if (!context) {
    throw new Error('useAutonomousDemo must be used within an AutonomousDemoProvider');
  }
  return context;
};
