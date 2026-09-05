/**
 * AutonomousDemoContext.tsx — Feature-Local Autonomous Demo State Machine
 *
 * Implements a controlled, deterministic 11-step walkthrough demonstrating
 * AgentGuard's commerce firewall against price tampering and legitimate in-budget
 * requests using the real backend.
 *
 * HARDENING PASS INVARIANTS:
 *  - Single audio controller: At most ONE AgentGuard demo voice active at any time.
 *  - Rapid Pause/Play clicks protected by synchronous transition guard & state invariants.
 *  - Instant pause response: Pre-synthesized pause greeting begins in < 100ms.
 *  - Reduced transition latency: Next narration chunk pre-synthesized in background; < 2s gaps.
 *  - Live rolling captions: Captions update progressively as audio plays via currentTime/duration.
 *  - Visual symmetry: Legitimate Scenario 1 highlights Bluetooth Speaker ₹2,799 before execution.
 *  - Real backend execution: Scenario 3 (DENY) and Scenario 1 (ALLOW) wait for real responses.
 *  - Exact transaction IDs captured and correlated in Forensic Ledger.
 */

import React, { createContext, useContext, useState, useRef, useEffect, useCallback, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAgentGuard } from '../../context/AgentGuardContext';
import { api, ProposeResponseData } from '../../lib/api';
import { cleanTextForSpeech, AGENTGUARD_TTS_PLAYBACK_RATE } from '../conversational/speechCleaner';
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
    name: 'Introduction & Tour',
    route: '/',
    targetId: null,
    spokenNarration:
      "Welcome to AgentGuard. AgentGuard is the server-authoritative financial firewall and trust boundary for autonomous AI agents. When autonomous agents are granted financial access, they can hallucinate prices, exceed budgets, or be manipulated by adversarial prompts. AgentGuard acts as the deterministic trust boundary: the model is allowed to be wrong, but it's not allowed to be authoritative. Today, I'll walk you through our live protection architecture, stress-test our firewall against adversarial attacks in the Threat Lab, and inspect the cryptographic audit ledger.",
    captionText: 'Introduction — AgentGuard deterministic trust boundary for AI commerce',
    expectedDurationMs: 24000,
  },
  2: {
    id: 2,
    name: 'Mandate Boundary',
    route: '/',
    targetId: 'cockpit-budget',
    spokenNarration:
      'Let’s focus on the security boundary. The AI agent operates under an authoritative ₹3,000 mandate with strict cryptographic guardrails enforced by our policy engine before any payment can be authorized.',
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
      'This is the Threat Simulation Lab. We maintain six distinct adversarial scenarios to stress-test our deterministic boundaries under adversarial conditions — from price tampering and budget exhaustion to replay attacks and semantic injection. Now, instead of just talking about the attacks, let’s run a live price tampering attack against the real firewall.',
    captionText: 'Threat Lab — Six adversarial scenarios testing deterministic boundaries',
    expectedDurationMs: 22000,
  },
  5: {
    id: 5,
    name: 'Price Tampering Attack',
    route: '/threats',
    targetId: 'threat-custom-amount',
    spokenNarration:
      'Let’s see what happens when an AI agent tries to manipulate the transaction before it reaches the payment layer. The agent is claiming a price of ₹1,999 for Wireless Earbuds, attempting to bypass the true catalog price of ₹3,499.',
    captionText: 'Price Tampering — Submitting untrusted proposal (₹1,999 claimed vs ₹3,499 actual)...',
    expectedDurationMs: 15000,
  },
  6: {
    id: 6,
    name: 'Price Tampering Decision',
    route: '/threats',
    targetId: 'decision-result',
    spokenNarration:
      'And there it is — DENIED. The agent claimed ₹1,999, but the authoritative catalog price in PostgreSQL is ₹3,499. The firewall rejected the transaction with reason code PRICE_MISMATCH before it could become an authorized payment.',
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
    targetId: 'threat-legitimate-item',
    spokenNarration:
      'Now let’s see the other side: a legitimate request within the mandate. AgentGuard verifies the request against the mandate and authoritative commerce data. Because this transaction is genuinely within the allowed boundary, it can be approved. Let’s test the Bluetooth Speaker at its genuine price of ₹2,799.',
    captionText: 'Happy Path — Testing valid transaction within ₹3,000 mandate...',
    expectedDurationMs: 18000,
  },
  9: {
    id: 9,
    name: 'Legitimate Approval',
    route: '/threats',
    targetId: 'decision-result',
    spokenNarration:
      'And there we go — approved. This time the transaction is legitimate, so AgentGuard allows it and authorizes payment with Razorpay. That’s the distinction: the AI can propose, but the firewall decides whether that proposal is authorized.',
    captionText: 'Verdict — Authorization Approved: ALLOW & payment executed',
    expectedDurationMs: 16000,
  },
  10: {
    id: 10,
    name: 'Forensic Success Record',
    route: '/forensics',
    targetId: 'forensic-latest-transaction',
    spokenNarration:
      'Back in the Forensic Ledger, we now have both records side by side: the intercepted price tampering denial and the verified legitimate approval. The ledger allows complete cryptographic reconstruction of all agent commerce activity.',
    captionText: 'Forensic Ledger — Complete audit record of allowed & denied activity',
    expectedDurationMs: 18000,
  },
  11: {
    id: 11,
    name: 'Summary & Completion',
    route: '/',
    targetId: 'cockpit-budget',
    spokenNarration:
      "To recap: AI agents can propose actions, but AgentGuard independently verifies critical transaction parameters against authoritative catalog truth. The agent is never the financial authority. Invalid requests are denied, legitimate requests within the mandate proceed, and all decisions leave auditable evidence. That brings us to the end of the AgentGuard demo. If you have any questions, I'm right here and happy to walk you through them.",
    captionText: 'Complete — The model can be wrong; the firewall is authoritative',
    expectedDurationMs: 18000,
  },
};

type PausePhase =
  | 'INACTIVE'
  | 'AWAITING_QUESTION_OR_YES'
  | 'AWAITING_QUESTION'
  | 'ANSWERING_QUESTION'
  | 'AWAITING_CONTINUE_DECISION';

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
    fetchMandate,
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

  // Transition guard against rapid concurrent button clicks
  const isTransitioningRef = useRef<boolean>(false);

  // Exact transaction IDs captured from real backend responses
  const lastPriceTamperingTxnIdRef = useRef<string | null>(null);
  const lastHappyPathTxnIdRef = useRef<string | null>(null);
  const activeTransactionRef = useRef(activeTransaction);

  // Pause conversational flow state
  const pausePhaseRef = useRef<PausePhase>('INACTIVE');

  // Single active audio playback controller refs
  const activeAudioRef = useRef<HTMLAudioElement | null>(null);
  const activeAudioUrlRef = useRef<string | null>(null);
  const sharedAudioRef = useRef<HTMLAudioElement | null>(null);

  // Background prerequisite setup promise ref (mandate reset/check)
  const prerequisitePromiseRef = useRef<Promise<void> | null>(null);

  // In-flight audio prefetch deduplication guard
  const inFlightPrefetchesRef = useRef<Set<string>>(new Set());

  // Pause greeting dedicated pre-synthesized audio ref
  const pauseGreetingBlobRef = useRef<Blob | null>(null);
  const pauseAudioRef = useRef<HTMLAudioElement | null>(null);

  // Multi-chunk prefetch cache map: key -> { blob: Blob; runId: number }
  const prefetchedBlobsRef = useRef<Map<string, { blob: Blob; runId: number }>>(new Map());

  // Timers registry
  const timerIdsRef = useRef<number[]>([]);

  // Pre-synthesize static pause greeting and Step 1 chunk 1 on mount for instant zero-latency playback
  useEffect(() => {
    let mounted = true;
    const prefetchMountAssets = async () => {
      try {
        // 1. Static pause greeting pre-synthesis
        const { blob: pBlob } = await api.synthesizeSpeech(
          "You've paused the demo. Do you have any questions I can help with?"
        );
        if (pBlob && mounted) {
          pauseGreetingBlobRef.current = pBlob;
        }

        // 2. Step 1 narration chunk 1 pre-synthesis (tagged with runId: 0 for static cache)
        const step1Narration = DEMO_STEPS[1]?.spokenNarration;
        if (step1Narration && mounted) {
          const cleaned = cleanTextForSpeech(step1Narration);
          if (cleaned) {
            const { blob: sBlob } = await api.synthesizeSpeech(cleaned);
            if (sBlob && mounted) {
              prefetchedBlobsRef.current.set('step1-chunk1', { blob: sBlob, runId: 0 });
            }
          }
        }
      } catch {
        // Safe fallback handled in playNarration / pauseDemo
      }
    };
    prefetchMountAssets();
    return () => {
      mounted = false;
    };
  }, []);

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

  useEffect(() => {
    activeTransactionRef.current = activeTransaction;
  }, [activeTransaction]);

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
          const id = window.setTimeout(check, 100);
          timerIdsRef.current.push(id);
          return;
        }

        const elapsed = Date.now() - startTime;
        remaining -= elapsed;
        startTime = Date.now();

        if (remaining <= 0) {
          resolve(true);
        } else {
          const id = window.setTimeout(check, Math.min(remaining, 100));
          timerIdsRef.current.push(id);
        }
      };

      const id = window.setTimeout(check, Math.min(ms, 100));
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

  // ── Safe Background Audio Prefetching (Issue 3) ─────────────────────────────
  const prefetchAudio = useCallback(
    async (text: string, expectedRunId: number, key: string): Promise<void> => {
      if (!text || !text.trim()) return;
      if (expectedRunId !== runIdRef.current || !isMountedRef.current) return;

      const cleaned = cleanTextForSpeech(text);
      if (!cleaned) return;

      // Don't re-fetch if already cached
      const existing = prefetchedBlobsRef.current.get(key);
      if (existing) {
        return;
      }

      // Deduplicate concurrent in-flight prefetch requests
      if (inFlightPrefetchesRef.current.has(key)) {
        return;
      }
      inFlightPrefetchesRef.current.add(key);

      try {
        const { blob } = await api.synthesizeSpeech(cleaned);
        if (blob && (expectedRunId === runIdRef.current || expectedRunId === 0) && isMountedRef.current) {
          prefetchedBlobsRef.current.set(key, { blob, runId: expectedRunId });
        }
      } catch {
        // Safe: playNarration will fall back to normal fetch
      } finally {
        inFlightPrefetchesRef.current.delete(key);
      }
    },
    []
  );

  // ── Spoken Narration via Deepgram Brooke TTS with Live Rolling Captions ─────
  // Uses persistent audio controller and centralized AGENTGUARD_TTS_PLAYBACK_RATE (0.95)
  const playNarration = useCallback(
    async (text: string, expectedRunId: number, prefetchedKey?: string): Promise<void> => {
      if (!text || !text.trim()) return;
      if (expectedRunId !== runIdRef.current || !isMountedRef.current) return;

      const cleaned = cleanTextForSpeech(text);
      if (!cleaned) return;

      stopActiveAudio();

      try {
        setAgentVoiceState('SPEAKING');

        // Check if pre-synthesized blob is available for this chunk
        let blob: Blob | null = null;
        const cached = prefetchedKey ? prefetchedBlobsRef.current.get(prefetchedKey) : null;
        if (cached) {
          blob = cached.blob;
        } else {
          const res = await api.synthesizeSpeech(cleaned);
          blob = res.blob;
          if (blob && prefetchedKey) {
            prefetchedBlobsRef.current.set(prefetchedKey, { blob, runId: expectedRunId });
          }
        }

        if (expectedRunId !== runIdRef.current || !isMountedRef.current) {
          setAgentVoiceState('IDLE');
          return;
        }

        // Subtitles preserve visual punctuation & uppercase abbreviations (PRICE_MISMATCH, SHA-256)
        const words = text.split(/\s+/);

        if (!blob) {
          // Graceful fallback reading timer if network fails
          const wordCount = words.length;
          const fallbackMs = Math.max(2000, Math.round((wordCount / 140) * 60 * 1000));
          const startTime = Date.now();

          await new Promise<void>((resolve) => {
            const timer = window.setInterval(() => {
              if (expectedRunId !== runIdRef.current || !isMountedRef.current) {
                window.clearInterval(timer);
                resolve();
                return;
              }
              if (isPausedRef.current) return;

              const elapsed = Date.now() - startTime;
              const progress = Math.min(1, elapsed / fallbackMs);
              const targetWordIdx = Math.min(words.length, Math.max(3, Math.ceil(progress * words.length)));
              const startIdx = Math.max(0, targetWordIdx - 14);
              setCurrentNarration(
                (startIdx > 0 ? '... ' : '') + words.slice(startIdx, targetWordIdx).join(' ')
              );

              if (elapsed >= fallbackMs) {
                window.clearInterval(timer);
                setCurrentNarration(text);
                resolve();
              }
            }, 100);
            timerIdsRef.current.push(timer);
          });

          if (expectedRunId === runIdRef.current) {
            setAgentVoiceState('IDLE');
          }
          return;
        }

        const audioUrl = URL.createObjectURL(blob);
        activeAudioUrlRef.current = audioUrl;

        // Use single persistent audio controller with strictly enforced 0.95 playback rate
        let audio = sharedAudioRef.current;
        if (!audio) {
          audio = new Audio();
          audio.playbackRate = AGENTGUARD_TTS_PLAYBACK_RATE;
          sharedAudioRef.current = audio;
        }
        audio.pause();
        audio.src = audioUrl;
        audio.playbackRate = AGENTGUARD_TTS_PLAYBACK_RATE;
        audio.onplay = () => {
          audio.playbackRate = AGENTGUARD_TTS_PLAYBACK_RATE;
        };
        activeAudioRef.current = audio;

        // Set initial caption snippet
        setCurrentNarration(
          words.slice(0, Math.min(6, words.length)).join(' ') + (words.length > 6 ? '...' : '')
        );

        await new Promise<void>((resolve) => {
          let resolved = false;
          let intervalId: number | null = null;

          const finish = () => {
            if (!resolved) {
              resolved = true;
              if (intervalId !== null) {
                window.clearInterval(intervalId);
                intervalId = null;
              }
              audio.onended = null;
              audio.onerror = null;
              if (activeAudioRef.current === audio) {
                activeAudioRef.current = null;
              }
              if (expectedRunId === runIdRef.current) {
                setAgentVoiceState('IDLE');
                setCurrentNarration(text); // Reveal full text upon completion
              }
              resolve();
            }
          };

          audio.onended = finish;
          audio.onerror = finish;

          if (!isPausedRef.current) {
            audio.play().catch((err) => {
              console.warn('[Demo TTS] Play error:', err);
              // If browser autoplay restriction blocks playback, gracefully fallback to reading timer
              if (err?.name === 'NotAllowedError') {
                const wordCount = words.length;
                const fallbackMs = Math.max(2000, Math.round((wordCount / 140) * 60 * 1000));
                const startTime = Date.now();

                const timer = window.setInterval(() => {
                  if (expectedRunId !== runIdRef.current || !isMountedRef.current) {
                    window.clearInterval(timer);
                    finish();
                    return;
                  }
                  if (isPausedRef.current) return;

                  const elapsed = Date.now() - startTime;
                  const progress = Math.min(1, elapsed / fallbackMs);
                  const targetWordIdx = Math.min(words.length, Math.max(3, Math.ceil(progress * words.length)));
                  const startIdx = Math.max(0, targetWordIdx - 14);
                  setCurrentNarration(
                    (startIdx > 0 ? '... ' : '') + words.slice(startIdx, targetWordIdx).join(' ')
                  );

                  if (elapsed >= fallbackMs) {
                    window.clearInterval(timer);
                    finish();
                  }
                }, 100);
                timerIdsRef.current.push(timer);
              } else {
                finish();
              }
            });
          }

          // Rolling caption updater & pause watcher
          intervalId = window.setInterval(() => {
            if (expectedRunId !== runIdRef.current || !isMountedRef.current) {
              if (intervalId !== null) window.clearInterval(intervalId);
              audio.pause();
              finish();
              return;
            }

            // Sync pause/resume state and strictly re-enforce 0.95 rate
            if (isPausedRef.current && !audio.paused) {
              audio.pause();
            } else if (!isPausedRef.current && audio.paused && !resolved) {
              audio.playbackRate = AGENTGUARD_TTS_PLAYBACK_RATE;
              audio.play().catch(() => {});
            }

            // Live progressive rolling caption update
            if (!isPausedRef.current && !audio.paused) {
              const progress =
                audio.duration && audio.duration > 0
                  ? Math.min(1, audio.currentTime / audio.duration)
                  : 0;

              const targetWordIdx = Math.min(
                words.length,
                Math.max(3, Math.ceil(progress * words.length))
              );
              const startIdx = Math.max(0, targetWordIdx - 14);
              const subtitleWindow =
                (startIdx > 0 ? '... ' : '') + words.slice(startIdx, targetWordIdx).join(' ');
              setCurrentNarration(subtitleWindow);
            }
          }, 100);
          timerIdsRef.current.push(intervalId);

          audio.addEventListener(
            'ended',
            () => {
              if (intervalId !== null) window.clearInterval(intervalId);
              finish();
            },
            { once: true }
          );
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

  // ── Semantic Target Scrolling (No Hardcoded Pixel Coordinates) ──────────────
  const scrollToSemanticTarget = useCallback(
    async (targetId: AgentTargetId | string, waitMs: number, activeRunId: number): Promise<void> => {
      if (activeRunId !== runIdRef.current || !targetId) return;

      const selector =
        targetId.startsWith('#') || targetId.startsWith('.')
          ? targetId
          : `[data-agent-target="${targetId}"]`;

      const el = document.querySelector(selector);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      await safeDelay(waitMs, activeRunId);
    },
    [safeDelay]
  );

  const scrollToTop = useCallback(
    async (waitMs: number, activeRunId: number): Promise<void> => {
      if (activeRunId !== runIdRef.current) return;
      window.scrollTo({ top: 0, behavior: 'smooth' });
      await safeDelay(waitMs, activeRunId);
    },
    [safeDelay]
  );

  // ── Scenario Execution with Friendly Loading Voice (Constraint 3) ───────────
  // Real scenario request starts immediately. Loading voice only if pending > 1.8s.
  // Stops loading voice immediately once real response arrives.
  const executeScenarioWithLoadingVoice = useCallback(
    async (scenarioId: number, activeRunId: number): Promise<ProposeResponseData | null> => {
      let pending = true;
      let loadingAudioPlaying = false;

      const thresholdTimer = window.setTimeout(async () => {
        if (pending && activeRunId === runIdRef.current && !isPausedRef.current) {
          loadingAudioPlaying = true;
          await playNarration(
            'The verification is taking a little longer than expected. Give me a moment while the firewall completes its check.',
            activeRunId
          );
          loadingAudioPlaying = false;
        }
      }, 1800);
      timerIdsRef.current.push(thresholdTimer);

      try {
        const res = await triggerScenario(scenarioId);
        return res || null;
      } finally {
        pending = false;
        window.clearTimeout(thresholdTimer);
        if (loadingAudioPlaying) {
          stopActiveAudio();
        }
      }
    },
    [triggerScenario, playNarration, stopActiveAudio]
  );

  // ── Step Execution State Machine ────────────────────────────────────────────
  const executeStep = useCallback(
    async (stepId: DemoStepId, activeRunId: number): Promise<void> => {
      if (activeRunId !== runIdRef.current || !isMountedRef.current) return;

      const step = DEMO_STEPS[stepId];
      if (!step) return;

      setCurrentStepId(stepId);
      setCurrentTargetId(step.targetId);

      // 1. Navigation if route changes
      if (window.location.pathname !== step.route) {
        navigate(step.route);
        const ok = await safeDelay(200, activeRunId);
        if (!ok || activeRunId !== runIdRef.current) return;
      } else if (stepId !== 1) {
        const ok = await safeDelay(150, activeRunId);
        if (!ok || activeRunId !== runIdRef.current) return;
      }

      // 2. Perform step-specific ordered narration and actions with prefetching
      switch (stepId) {
        case 1: {
          // Step 1: Introduction & Home Cockpit Tour (Immediate visual start)
          if (window.scrollY > 50) {
            await scrollToTop(250, activeRunId);
            if (activeRunId !== runIdRef.current) return;
          }

          const chunk2Text =
            'At the top of our cockpit, you see the active mandate boundary: a strict, server-enforced budget of ₹3,000. Beneath our hero banner, three core pillars define the architecture: zero prompt authority, a PostgreSQL truth gate that verifies prices before payment, and idempotent Razorpay execution.';
          prefetchAudio(chunk2Text, activeRunId, 'step1-chunk2');

          // Chunk 1: Introduction (consumes pre-synthesized audio chunk1)
          await playNarration(step.spokenNarration, activeRunId, 'step1-chunk1');
          if (activeRunId !== runIdRef.current) return;
          await safeDelay(250, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          // Chunk 2: Cockpit Boundary & Architecture Cards
          const chunk3Text =
            'Scrolling down, the Trust Journey Pipeline illustrates the four stages of every transaction: the untrusted AI agent formulates a purchase intent, AgentGuard evaluates the policy invariants, catalog truth is queried directly from PostgreSQL, and only verified transactions proceed to payment.';
          prefetchAudio(chunk3Text, activeRunId, 'step1-chunk3');

          // Ensure clean ₹3,000 budget state is active before showcasing cockpit budget
          if (prerequisitePromiseRef.current) {
            await prerequisitePromiseRef.current;
            if (activeRunId !== runIdRef.current) return;
          }
          await fetchMandate();
          if (activeRunId !== runIdRef.current) return;

          setCurrentTargetId('cockpit-budget');
          await scrollToSemanticTarget('cockpit-budget', 350, activeRunId);
          if (activeRunId !== runIdRef.current) return;
          await playNarration(chunk2Text, activeRunId, 'step1-chunk2');
          if (activeRunId !== runIdRef.current) return;
          await safeDelay(250, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          // Chunk 3: The Trust Journey Pipeline
          const chunk4Text =
            'Further down, the firewall mechanics enforce four strict invariants: catalog integrity, hard mandate spending limits, human-in-the-loop escalation when budgets are exceeded, and an immutable SHA-256 evidence trail.';
          prefetchAudio(chunk4Text, activeRunId, 'step1-chunk4');

          setCurrentTargetId(null);
          await scrollToSemanticTarget('#trust-journey', 400, activeRunId);
          if (activeRunId !== runIdRef.current) return;
          await playNarration(chunk3Text, activeRunId, 'step1-chunk3');
          if (activeRunId !== runIdRef.current) return;
          await safeDelay(250, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          // Chunk 4: Firewall Thinking Mechanics — Prefetch Step 2 boundary narration
          prefetchAudio(DEMO_STEPS[2].spokenNarration, activeRunId, 'step2-narration');

          await scrollToSemanticTarget('#firewall-thinking', 400, activeRunId);
          if (activeRunId !== runIdRef.current) return;
          await playNarration(chunk4Text, activeRunId, 'step1-chunk4');
          if (activeRunId !== runIdRef.current) return;
          await safeDelay(250, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          await scrollToTop(350, activeRunId);
          if (activeRunId !== runIdRef.current) return;
          await executeStep(2, activeRunId);
          break;
        }

        case 2: {
          // Step 2: Cockpit Boundary
          const step3Chunk1Text =
            'Here in Live Protection, you can see the fundamental separation. On the left is the Untrusted Claim Chamber, simulating an intelligent shopping agent operating with zero financial authority. On the right is the Firewall Authorization Engine.';
          prefetchAudio(step3Chunk1Text, activeRunId, 'step3-chunk1');

          setCurrentTargetId('cockpit-budget');
          await scrollToSemanticTarget('cockpit-budget', 350, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          await playNarration(step.spokenNarration, activeRunId, 'step2-narration');
          if (activeRunId !== runIdRef.current) return;
          await safeDelay(250, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          await executeStep(3, activeRunId);
          break;
        }

        case 3: {
          // Step 3: Live Protection Presentation
          setCurrentTargetId('live-protection-mandate');
          await scrollToTop(250, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          const chunk2Text =
            'When the agent proposes a purchase, AgentGuard independently validates the item, claimed price, merchant, and mandate budget against PostgreSQL catalog truth before money can move. If verified, payment executes via Razorpay; if tampered, it is stopped instantly.';
          prefetchAudio(chunk2Text, activeRunId, 'step3-chunk2');

          const step3Chunk1Text =
            'Here in Live Protection, you can see the fundamental separation. On the left is the Untrusted Claim Chamber, simulating an intelligent shopping agent operating with zero financial authority. On the right is the Firewall Authorization Engine.';

          // Chunk 1: Separation of Untrusted Chamber and Firewall Engine
          await playNarration(step3Chunk1Text, activeRunId, 'step3-chunk1');
          if (activeRunId !== runIdRef.current) return;
          await safeDelay(200, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          // Prefetch Step 4 Chunk 1 while Chunk 2 is playing
          const step4Chunk1Text =
            'This is the Threat Simulation Lab, where we stress-test our deterministic boundaries under six distinct adversarial scenarios.';
          prefetchAudio(step4Chunk1Text, activeRunId, 'step4-chunk1');

          // Chunk 2: Verification, Mandate Limits & Policy Decision
          await scrollToSemanticTarget('.xl\\:col-span-7', 400, activeRunId);
          if (activeRunId !== runIdRef.current) return;
          await playNarration(chunk2Text, activeRunId, 'step3-chunk2');
          if (activeRunId !== runIdRef.current) return;
          await safeDelay(200, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          await scrollToTop(300, activeRunId);
          if (activeRunId !== runIdRef.current) return;
          await executeStep(4, activeRunId);
          break;
        }

        case 4: {
          // Step 4: Threat Simulation Lab — Overview & Explanation of all 6 scenarios
          setCurrentTargetId('threat-happy-path');
          await scrollToTop(250, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          const scenarios12Text =
            'Scenario one is our Happy Path baseline: a standard, un-tampered transaction within budget. Scenario two is Over-Budget Escalation, where purchases exceeding the mandate budget require human approver authorization.';
          prefetchAudio(scenarios12Text, activeRunId, 'step4-chunk2');

          const step4Chunk1Text =
            'This is the Threat Simulation Lab, where we stress-test our deterministic boundaries under six distinct adversarial scenarios.';

          // Chunk 1: Threat Lab Intro
          await playNarration(step4Chunk1Text, activeRunId, 'step4-chunk1');
          if (activeRunId !== runIdRef.current) return;
          await safeDelay(200, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          const scenarios34Text =
            'Scenario three is Price Tampering, where an agent attempts to alter payload prices in transit. Scenario four is Replay Attack Defense, where duplicate execution attempts on authorized transactions are rejected with a four-zero-nine conflict.';
          prefetchAudio(scenarios34Text, activeRunId, 'step4-chunk3');

          // Chunk 2: Scenarios 1 & 2
          setCurrentTargetId('threat-happy-path');
          await scrollToSemanticTarget('threat-happy-path', 350, activeRunId);
          if (activeRunId !== runIdRef.current) return;
          await playNarration(scenarios12Text, activeRunId, 'step4-chunk2');
          if (activeRunId !== runIdRef.current) return;
          await safeDelay(200, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          const scenarios56Text =
            'Scenario five tests Safe Failure and Idempotent Retry, ensuring budget releases on decline. Scenario six tests Mid-Session Revocation, where a revoked mandate immediately blocks pending execution mid-flight.';
          prefetchAudio(scenarios56Text, activeRunId, 'step4-chunk4');

          // Chunk 3: Scenarios 3 & 4
          setCurrentTargetId('threat-price-tampering');
          await scrollToSemanticTarget('threat-price-tampering', 350, activeRunId);
          if (activeRunId !== runIdRef.current) return;
          await playNarration(scenarios34Text, activeRunId, 'step4-chunk3');
          if (activeRunId !== runIdRef.current) return;
          await safeDelay(200, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          const transitionText =
            'Now, instead of just talking about the attacks, let’s run a live price tampering attack against the real firewall.';
          prefetchAudio(transitionText, activeRunId, 'step4-chunk5');

          // Chunk 4: Scenarios 5 & 6
          await playNarration(scenarios56Text, activeRunId, 'step4-chunk4');
          if (activeRunId !== runIdRef.current) return;
          await safeDelay(200, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          prefetchAudio(DEMO_STEPS[5].spokenNarration, activeRunId, 'step5-narration');

          // Chunk 5: Transition to live price tampering attack
          await playNarration(transitionText, activeRunId, 'step4-chunk5');
          if (activeRunId !== runIdRef.current) return;
          await safeDelay(250, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          await executeStep(5, activeRunId);
          break;
        }

        case 5: {
          // Step 5: Execute Price Tampering attack through REAL Threat Lab flow
          if (prerequisitePromiseRef.current) {
            await prerequisitePromiseRef.current;
            if (activeRunId !== runIdRef.current) return;
          }

          setCurrentTargetId('threat-custom-amount');
          await scrollToSemanticTarget('threat-custom-amount', 350, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          prefetchAudio(DEMO_STEPS[6].spokenNarration, activeRunId, 'step6-narration');

          await playNarration(step.spokenNarration, activeRunId, 'step5-narration');
          if (activeRunId !== runIdRef.current) return;

          setCurrentTargetId('threat-price-tampering');
          const propRes = await executeScenarioWithLoadingVoice(3, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          if (propRes?.transaction_id || activeTransactionRef.current?.transaction_id) {
            lastPriceTamperingTxnIdRef.current =
              propRes?.transaction_id || activeTransactionRef.current?.transaction_id || null;
          }

          await safeDelay(300, activeRunId);
          if (activeRunId !== runIdRef.current) return;
          await executeStep(6, activeRunId);
          break;
        }

        case 6: {
          // Step 6: Price Tampering Decision — Highlight verdict & verify real backend result
          setCurrentTargetId('decision-result');
          await scrollToSemanticTarget('decision-result', 400, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          const decisionStr = (activeTransactionRef.current?.decision as string) || '';
          const verdictReason = activeTransactionRef.current?.reason_code || '';
          const isPriceMismatchDenied =
            (decisionStr === 'DENY' || decisionStr === 'DENIED') &&
            (verdictReason === 'PRICE_MISMATCH' || verdictReason.includes('PRICE'));

          if (!isPriceMismatchDenied && activeTransactionRef.current?.decision) {
            const safetyMsg =
              'The demonstration encountered an unexpected issue with the price tampering scenario, so I’ve paused rather than showing an incorrect result.';
            setCurrentNarration(safetyMsg);
            setDemoState('ERROR');
            await playNarration(safetyMsg, activeRunId);
            return;
          }

          prefetchAudio(DEMO_STEPS[7].spokenNarration, activeRunId, 'step7-narration');

          await playNarration(step.spokenNarration, activeRunId, 'step6-narration');
          if (activeRunId !== runIdRef.current) return;
          await safeDelay(300, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          await executeStep(7, activeRunId);
          break;
        }

        case 7: {
          // Step 7: Forensic Denial Record — Inspect the real denied transaction in audit chain
          fetchTransactions();
          const targetTxnId =
            lastPriceTamperingTxnIdRef.current || activeTransactionRef.current?.transaction_id;
          if (targetTxnId) {
            setSelectedTxnId(targetTxnId);
            fetchAuditData(targetTxnId);
          }

          prefetchAudio(DEMO_STEPS[8].spokenNarration, activeRunId, 'step8-narration');

          setCurrentTargetId('forensic-latest-transaction');
          await scrollToSemanticTarget('forensic-latest-transaction', 350, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          await playNarration(step.spokenNarration, activeRunId, 'step7-narration');
          if (activeRunId !== runIdRef.current) return;
          await safeDelay(300, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          await executeStep(8, activeRunId);
          break;
        }

        case 8: {
          // Step 8: Legitimate Request — Highlight Scenario 1 & visual product/amount pill (Issue 4)
          if (prerequisitePromiseRef.current) {
            await prerequisitePromiseRef.current;
            if (activeRunId !== runIdRef.current) return;
          }

          prefetchAudio(DEMO_STEPS[9].spokenNarration, activeRunId, 'step9-narration');

          setCurrentTargetId('threat-legitimate-item');
          await scrollToSemanticTarget('threat-happy-path', 350, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          await playNarration(step.spokenNarration, activeRunId, 'step8-narration');
          if (activeRunId !== runIdRef.current) return;

          setCurrentTargetId('threat-happy-path');
          const happyRes = await executeScenarioWithLoadingVoice(1, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          if (happyRes?.transaction_id || activeTransactionRef.current?.transaction_id) {
            lastHappyPathTxnIdRef.current =
              happyRes?.transaction_id || activeTransactionRef.current?.transaction_id || null;
          }

          await safeDelay(300, activeRunId);
          if (activeRunId !== runIdRef.current) return;
          await executeStep(9, activeRunId);
          break;
        }

        case 9: {
          // Step 9: Legitimate Approval Verdict — Highlight verdict & verify real backend result (ALLOW)
          setCurrentTargetId('decision-result');
          await scrollToSemanticTarget('decision-result', 400, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          const decisionStr = (activeTransactionRef.current?.decision as string) || '';
          const isAllowed = decisionStr === 'ALLOW' || decisionStr === 'APPROVED';

          if (!isAllowed && activeTransactionRef.current?.decision) {
            const safetyMsg =
              'The demonstration encountered an unexpected issue with the legitimate scenario, so I’ve paused rather than showing an incorrect result.';
            setCurrentNarration(safetyMsg);
            setDemoState('ERROR');
            await playNarration(safetyMsg, activeRunId);
            return;
          }

          prefetchAudio(DEMO_STEPS[10].spokenNarration, activeRunId, 'step10-narration');

          await playNarration(step.spokenNarration, activeRunId, 'step9-narration');
          if (activeRunId !== runIdRef.current) return;
          await safeDelay(300, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          await executeStep(10, activeRunId);
          break;
        }

        case 10: {
          // Step 10: Forensic Success Record — Inspect legitimate transaction & contrast with denied record
          fetchTransactions();
          const targetTxnId =
            lastHappyPathTxnIdRef.current || activeTransactionRef.current?.transaction_id;
          if (targetTxnId) {
            setSelectedTxnId(targetTxnId);
            fetchAuditData(targetTxnId);
          }

          prefetchAudio(DEMO_STEPS[11].spokenNarration, activeRunId, 'step11-narration');

          setCurrentTargetId('forensic-latest-transaction');
          await scrollToSemanticTarget('forensic-latest-transaction', 350, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          await playNarration(step.spokenNarration, activeRunId, 'step10-narration');
          if (activeRunId !== runIdRef.current) return;
          await safeDelay(300, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          await executeStep(11, activeRunId);
          break;
        }

        case 11: {
          // Step 11: Return to Home + Final Recap
          setCurrentTargetId('cockpit-budget');
          await scrollToTop(350, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          await playNarration(step.spokenNarration, activeRunId, 'step11-narration');
          if (activeRunId !== runIdRef.current) return;

          await safeDelay(250, activeRunId);
          if (activeRunId !== runIdRef.current) return;

          // Finish cleanly and restore normal UI state
          setDemoState('COMPLETED');
          setCurrentTargetId(null);
          setIsConversationalOpen(true);
          appendAgentMessage?.(step.spokenNarration);

          // Restore demo mandate budget to clean ₹3,000 state for repeatability
          try {
            await api.resetDemoMandate();
            await fetchMandate();
          } catch (err) {
            console.warn('[AutonomousDemo] Completion budget reset error:', err);
          }
          break;
        }

        default:
          break;
      }
    },
    [
      navigate,
      safeDelay,
      prefetchAudio,
      playNarration,
      executeScenarioWithLoadingVoice,
      scrollToSemanticTarget,
      scrollToTop,
      fetchTransactions,
      setSelectedTxnId,
      fetchAuditData,
      setIsConversationalOpen,
      appendAgentMessage,
    ]
  );

  // ── Controls: Start, Pause, Resume, Stop (Concurrency Hardened) ─────────────
  const startDemo = useCallback(
    async (fromStep: DemoStepId = 1): Promise<void> => {
      // Invalidate any previous run
      const nextRunId = ++runIdRef.current;
      isTransitioningRef.current = false;
      setRunId(nextRunId);
      clearAllRegisteredTimers();
      stopActiveAudio();

      if (pauseAudioRef.current) {
        pauseAudioRef.current.pause();
        pauseAudioRef.current.src = '';
        pauseAudioRef.current = null;
      }

      // Synchronous user-activation audio priming on user gesture
      if (!sharedAudioRef.current) {
        sharedAudioRef.current = new Audio();
        sharedAudioRef.current.playbackRate = AGENTGUARD_TTS_PLAYBACK_RATE;
      }
      try {
        sharedAudioRef.current.src =
          'data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA';
        sharedAudioRef.current
          .play()
          .then(() => {
            sharedAudioRef.current?.pause();
          })
          .catch(() => {});
      } catch {
        // Safe: non-blocking priming
      }

      // Audio blobs remain cached across demo restarts to prevent duplicate Deepgram TTS calls
      pausePhaseRef.current = 'INACTIVE';
      setIsPaused(false);
      isPausedRef.current = false;
      setIsConversationalOpen(false); // Slides completely offscreen immediately

      const initialStep = DEMO_STEPS[fromStep] || DEMO_STEPS[1];

      // IMMEDIATE VISUAL STATE TRANSITION (Zero startup delay):
      // 1. Enter RUNNING immediately
      // 2. Set step immediately
      // 3. Set visual target immediately (AgentCursor rendered prompt)
      // 4. Set initial caption immediately (DemoControlBar displays it instantly)
      setDemoState('RUNNING');
      setCurrentStepId(fromStep);
      setCurrentTargetId(initialStep.targetId || 'cockpit-budget');
      setCurrentNarration(initialStep.captionText);

      // Concurrent background prerequisite setup (mandate validation/reset does NOT block Step 1)
      prerequisitePromiseRef.current = (async () => {
        try {
          const mandateRes = await api.getMandate('mandate-001');
          const remaining = mandateRes.data ? parseFloat(mandateRes.data.budget_remaining) : 0;
          const isRevoked = mandateRes.data?.status === 'revoked';
          const isNotClean = remaining < 3000 || isRevoked;

          if (isNotClean) {
            await api.resetDemoMandate();
            await fetchMandate();
          }
        } catch (err) {
          console.warn('[AutonomousDemo] Prerequisite setup check error:', err);
        }
      })();

      // Begin step execution immediately
      await executeStep(fromStep, nextRunId);
    },
    [clearAllRegisteredTimers, stopActiveAudio, executeStep, setIsConversationalOpen, fetchMandate]
  );

  const pauseDemo = useCallback(() => {
    // Transition guard: ignore if transitioning or not RUNNING (Issues 5 & 6)
    if (isTransitioningRef.current) return;
    if (demoStateRef.current !== 'RUNNING') return;

    isTransitioningRef.current = true;
    try {
      setIsPaused(true);
      isPausedRef.current = true;
      setDemoState('PAUSED');

      // 1. Atomically pause running audio immediately
      if (activeAudioRef.current && !activeAudioRef.current.paused) {
        activeAudioRef.current.pause();
      }

      // 2. Open drawer immediately
      setIsConversationalOpen(true);
      pausePhaseRef.current = 'AWAITING_QUESTION_OR_YES';

      const pauseGreeting = "You've paused the demo. Do you have any questions I can help with?";
      appendAgentMessage?.(pauseGreeting);
      setCurrentNarration(pauseGreeting);

      // 3. Fast pause voice response (< 100ms using pre-synthesized blob)
      if (pauseGreetingBlobRef.current) {
        if (pauseAudioRef.current) {
          pauseAudioRef.current.pause();
          pauseAudioRef.current = null;
        }
        const url = URL.createObjectURL(pauseGreetingBlobRef.current);
        const pAudio = new Audio(url);
        pAudio.playbackRate = AGENTGUARD_TTS_PLAYBACK_RATE;
        pauseAudioRef.current = pAudio;
        setAgentVoiceState('SPEAKING');

        pAudio.onended = () => {
          if (pauseAudioRef.current === pAudio) {
            pauseAudioRef.current = null;
            URL.revokeObjectURL(url);
            setAgentVoiceState('IDLE');
          }
        };
        pAudio.onerror = () => {
          if (pauseAudioRef.current === pAudio) {
            pauseAudioRef.current = null;
            URL.revokeObjectURL(url);
            setAgentVoiceState('IDLE');
          }
        };
        pAudio.play().catch(() => {});
      } else {
        playNarration(pauseGreeting, runIdRef.current);
      }
    } finally {
      window.setTimeout(() => {
        isTransitioningRef.current = false;
      }, 40);
    }
  }, [appendAgentMessage, playNarration, setIsConversationalOpen, setAgentVoiceState]);

  const resumeDemo = useCallback(() => {
    // Transition guard: ignore if transitioning or not PAUSED (Issue 6)
    if (isTransitioningRef.current) return;
    if (demoStateRef.current !== 'PAUSED') return;

    isTransitioningRef.current = true;
    try {
      // 1. Immediately halt any active pause prompt audio (Audio Exclusivity Guarantee)
      if (pauseAudioRef.current) {
        pauseAudioRef.current.pause();
        pauseAudioRef.current.src = '';
        pauseAudioRef.current = null;
      }

      pausePhaseRef.current = 'INACTIVE';
      setIsPaused(false);
      isPausedRef.current = false;
      setIsConversationalOpen(false); // Slides completely offscreen
      setDemoState('RUNNING');

      // 2. Resume running narration audio if paused mid-chunk with strictly enforced 0.95 rate
      if (activeAudioRef.current && activeAudioRef.current.paused) {
        setAgentVoiceState('SPEAKING');
        activeAudioRef.current.playbackRate = AGENTGUARD_TTS_PLAYBACK_RATE;
        activeAudioRef.current.play().catch(() => {});
      }
    } finally {
      window.setTimeout(() => {
        isTransitioningRef.current = false;
      }, 40);
    }
  }, [setIsConversationalOpen, setAgentVoiceState]);

  const stopDemo = useCallback(() => {
    // Unconditionally invalidate current run immediately
    runIdRef.current++;
    isTransitioningRef.current = false;
    clearAllRegisteredTimers();
    stopActiveAudio();

    if (pauseAudioRef.current) {
      pauseAudioRef.current.pause();
      pauseAudioRef.current.src = '';
      pauseAudioRef.current = null;
    }

    // Audio blobs remain cached across demo restarts to prevent duplicate Deepgram TTS calls
    pausePhaseRef.current = 'INACTIVE';
    setIsPaused(false);
    isPausedRef.current = false;
    setCurrentTargetId(null);
    setIsConversationalOpen(true);
    setCurrentNarration('');

    const stopMsg = 'Demo mode stopped. Do you have any questions for me?';
    setDemoState('STOPPED_AWAITING_QUESTION');
    appendAgentMessage?.(stopMsg);

    playNarration(stopMsg, runIdRef.current);
  }, [clearAllRegisteredTimers, stopActiveAudio, playNarration, appendAgentMessage, setIsConversationalOpen]);

  // ── Conversational Interceptors for Pause & Stop Lifecycles ──────────────────
  const handleStoppedQuery = useCallback(
    async (userQuery: string): Promise<boolean> => {
      const trimmed = userQuery.trim().toLowerCase();

      // ── PAUSE Conversational Lifecycle ──────────────────────────────────────
      if (demoStateRef.current === 'PAUSED') {
        const YES_ONLY = /^(yes|yeah|yep|sure|i do|yes i do)[.!?]?$/i;
        const NO_OR_RESUME = /^(no|resume|continue|let's continue|lets continue|go ahead|play)[.!?]?$/i;
        const CONTINUE_DECISION_YES = /^(yes|yeah|yep|sure|continue|resume|go ahead|let's continue|lets continue|restart|play)\b/i;
        const CONTINUE_DECISION_NO = /^(no|nope|no thanks|that's enough|thats enough|we can stop|end the demo|stop)\b/i;

        // Phase 1: User just received "You've paused the demo. Do you have any questions I can help with?"
        if (pausePhaseRef.current === 'AWAITING_QUESTION_OR_YES') {
          if (YES_ONLY.test(trimmed)) {
            pausePhaseRef.current = 'AWAITING_QUESTION';
            const reply = "Of course. I'm here to help. What's your question?";
            appendAgentMessage?.(reply);
            playNarration(reply, runIdRef.current);
            return true;
          }

          if (NO_OR_RESUME.test(trimmed)) {
            resumeDemo();
            return true;
          }

          // User asked a question directly (e.g. "Yes, why was that transaction denied?")
          pausePhaseRef.current = 'ANSWERING_QUESTION';
          return false; // Route to normal chatbot
        }

        // Phase 2: User was asked "What's your question?"
        if (pausePhaseRef.current === 'AWAITING_QUESTION') {
          pausePhaseRef.current = 'ANSWERING_QUESTION';
          return false; // Route question to normal chatbot
        }

        // Phase 3: User was asked "Would you like to continue the demo?"
        if (pausePhaseRef.current === 'AWAITING_CONTINUE_DECISION') {
          if (CONTINUE_DECISION_YES.test(trimmed)) {
            resumeDemo();
            return true;
          }

          if (CONTINUE_DECISION_NO.test(trimmed)) {
            const finalMsg =
              'Of course. We can end the demo here. If you have any questions or need my assistance later, I’ll be right here.';
            pausePhaseRef.current = 'INACTIVE';
            setDemoState('IDLE');
            setIsPaused(false);
            isPausedRef.current = false;
            setCurrentNarration(finalMsg);
            appendAgentMessage?.(finalMsg);
            playNarration(finalMsg, runIdRef.current);
            return true;
          }

          pausePhaseRef.current = 'ANSWERING_QUESTION';
          return false;
        }

        return false;
      }

      // ── STOP Conversational Lifecycle ───────────────────────────────────────
      if (demoStateRef.current === 'STOPPED_AWAITING_CONTINUE_DECISION') {
        const YES_PATTERNS = /^(yes|yeah|yep|sure|continue|let's continue|lets continue|show me|go ahead|resume|restart|ok|okay)\b/i;
        const NO_PATTERNS = /^(no|nope|no thanks|that's enough|thats enough|we can stop|end the demo|let's finish|lets finish|stop)\b/i;

        if (YES_PATTERNS.test(trimmed)) {
          setDemoState('IDLE');
          appendAgentMessage?.('Restarting the demo from the beginning.');
          await startDemo(1);
          return true;
        }

        if (NO_PATTERNS.test(trimmed)) {
          const finalMsg =
            'Of course. We can end the demo here. If you have any questions or need my assistance later, I’ll be right here.';
          setDemoState('IDLE');
          setCurrentNarration(finalMsg);
          appendAgentMessage?.(finalMsg);
          playNarration(finalMsg, runIdRef.current);
          return true;
        }

        return false;
      }

      return false;
    },
    [startDemo, resumeDemo, playNarration, appendAgentMessage]
  );

  // ── Register Interceptors with AgentGuardContext ────────────────────────────
  useEffect(() => {
    if (!registerConversationalInterceptor) return;

    const unregister = registerConversationalInterceptor({
      onQuery: async (query: string) => {
        const trimmed = query.trim().toLowerCase();
        if (
          /^(start\s+demo|run\s+demo|launch\s+demo|demo|walkthrough|start\s+walkthrough|project\s+demo)$/i.test(
            trimmed
          )
        ) {
          startDemo(1);
          return true;
        }

        if (
          demoStateRef.current === 'PAUSED' ||
          demoStateRef.current === 'STOPPED_AWAITING_CONTINUE_DECISION'
        ) {
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

        // 2. Intercept PAUSED question answer
        if (demoStateRef.current === 'PAUSED' && pausePhaseRef.current === 'ANSWERING_QUESTION') {
          pausePhaseRef.current = 'AWAITING_CONTINUE_DECISION';
          const fullMessage = `${response.message}\n\nWould you like to continue the demo?`;
          playNarration(fullMessage, runIdRef.current);
          return {
            ...response,
            message: fullMessage,
          };
        }

        // 3. Intercept STOPPED_AWAITING_QUESTION follow-up
        if (demoStateRef.current === 'STOPPED_AWAITING_QUESTION') {
          setDemoState('STOPPED_AWAITING_CONTINUE_DECISION');
          const fullMessage = `${response.message}\n\nWould you like to continue with the demo?`;
          playNarration(fullMessage, runIdRef.current);
          return {
            ...response,
            message: fullMessage,
          };
        }

        return response;
      },
    });

    return unregister;
  }, [registerConversationalInterceptor, handleStoppedQuery, startDemo, playNarration]);

  // ── Unmount Cleanup ─────────────────────────────────────────────────────────
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      runIdRef.current++;
      clearAllRegisteredTimers();
      stopActiveAudio();
      if (pauseAudioRef.current) {
        pauseAudioRef.current.pause();
        pauseAudioRef.current.src = '';
        pauseAudioRef.current = null;
      }
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
