/**
 * useVoiceIO — Phase 5.5C Voice I/O Hook (Cartesia Skylar TTS Integration)
 *
 * Encapsulates browser SpeechRecognition (STT) and backend-proxied Cartesia TTS (Skylar)
 * lifecycle for the AgentGuard conversational assistant.
 *
 * ARCHITECTURE:
 *  - Microphone input uses browser SpeechRecognition (STT) untouched.
 *  - All queries are routed through the EXISTING sendConversationalQuery().
 *  - The chatbot response is cleaned using speechCleaner.ts (visible text is never altered).
 *  - Audio is synthesized via server-proxied Cartesia TTS (Voice: Skylar - Friendly Guide, Model: sonic-3).
 *  - Audio playback is handled via HTML5 Audio with full state management & cancellation.
 *  - The existing AgentGuardContext agentVoiceState drives the waveform visualizer.
 *  - The Cartesia API key remains strictly server-side and is NEVER exposed to the frontend.
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import { AgentVoiceState } from '../../context/AgentGuardContext';
import { api, AssistantResponse } from '../../lib/api';
import { cleanTextForSpeech } from './speechCleaner';

// ── Local button/label state machine (separate from context waveform state) ──
export type VoiceIOState = 'IDLE' | 'LISTENING' | 'PROCESSING' | 'SPEAKING' | 'ERROR';

// ── SpeechRecognition browser type shims ──────────────────────────────────────
interface SpeechRecognitionResultItem {
  transcript: string;
  confidence: number;
}

interface SpeechRecognitionResult {
  [index: number]: SpeechRecognitionResultItem;
  isFinal: boolean;
  length: number;
}

interface SpeechRecognitionResultList {
  [index: number]: SpeechRecognitionResult;
  length: number;
}

interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type SpeechRecognitionConstructor = new () => SpeechRecognitionInstance;

interface SpeechRecognitionInstance {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start(): void;
  stop(): void;
  abort(): void;
  onstart: ((event: Event) => void) | null;
  onend: ((event: Event) => void) | null;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
}

// ── Feature detection ─────────────────────────────────────────────────────────
function getSpeechRecognitionConstructor(): SpeechRecognitionConstructor | null {
  if (typeof window === 'undefined') return null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const w = window as any;
  return w.SpeechRecognition || w.webkitSpeechRecognition || null;
}

// ── Hook options + return type ────────────────────────────────────────────────
export interface UseVoiceIOOptions {
  /** The existing conversational pipeline — must not be replaced. */
  sendConversationalQuery: (query: string) => Promise<AssistantResponse | null>;
  /** Context's agentVoiceState setter — drives waveform visualizer. */
  setAgentVoiceState: (state: AgentVoiceState) => void;
}

export interface UseVoiceIOReturn {
  /** Local button/label state — drives mic button UX. */
  voiceState: VoiceIOState;
  /** Human-readable error for display in the drawer. */
  voiceError: string | null;
  /** False when browser has no SpeechRecognition; mic button disabled. */
  isSTTSupported: boolean;
  /** True when Cartesia audio playback is supported. */
  isTTSSupported: boolean;
  /** Start speech recognition. No-op unless IDLE. */
  startListening: () => void;
  /** Stop recognition early (transitions to IDLE). */
  stopListening: () => void;
  /** Stop TTS playback and return to IDLE. */
  stopSpeaking: () => void;
  /** Clear a displayed error and return to IDLE. */
  dismissError: () => void;
}

// ── User-facing recognition error messages ────────────────────────────────────
function recognitionErrorMessage(error: string): string {
  switch (error) {
    case 'not-allowed':
    case 'permission-denied':
      return 'Microphone access denied. Please allow microphone access in your browser settings and try again.';
    case 'no-speech':
      return 'No speech was detected. Please speak clearly and try again.';
    case 'audio-capture':
      return 'No microphone found. Please connect a microphone and try again.';
    case 'network':
      return 'A network error occurred during speech recognition. Please check your connection and try again.';
    case 'service-not-allowed':
      return 'Speech recognition service is not available in this context.';
    case 'bad-grammar':
      return 'Speech recognition grammar error. Please try again.';
    case 'language-not-supported':
      return 'English speech recognition is not supported in this browser.';
    case 'aborted':
      return '';
    default:
      return `Speech recognition error (${error}). Please try again.`;
  }
}

// ── The hook ──────────────────────────────────────────────────────────────────
export function useVoiceIO({
  sendConversationalQuery,
  setAgentVoiceState,
}: UseVoiceIOOptions): UseVoiceIOReturn {
  const SpeechRecognitionAPI = getSpeechRecognitionConstructor();
  const isSTTSupported = SpeechRecognitionAPI !== null;
  const isTTSSupported = typeof window !== 'undefined' && typeof Audio !== 'undefined';

  // ── Local UI state ──────────────────────────────────────────────────────────
  const [voiceState, setVoiceState] = useState<VoiceIOState>('IDLE');
  const [voiceError, setVoiceError] = useState<string | null>(null);

  // ── Refs for lifecycle safety ───────────────────────────────────────────────
  const isMountedRef = useRef(true);
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const currentAudioUrlRef = useRef<string | null>(null);
  const ttsAbortControllerRef = useRef<AbortController | null>(null);

  // Ref mirror of voiceState to avoid stale closures in event handlers
  const voiceStateRef = useRef<VoiceIOState>('IDLE');

  // Playback session identifier to cleanly cancel in-flight audio fetches/playback
  const playbackSessionIdRef = useRef<number>(0);

  // ── Helpers ─────────────────────────────────────────────────────────────────
  const updateVoiceState = useCallback((next: VoiceIOState) => {
    voiceStateRef.current = next;
    setVoiceState(next);
  }, []);

  const cleanupActiveAudio = useCallback(() => {
    if (ttsAbortControllerRef.current) {
      ttsAbortControllerRef.current.abort();
      ttsAbortControllerRef.current = null;
    }
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current.onplay = null;
      currentAudioRef.current.onended = null;
      currentAudioRef.current.onerror = null;
      currentAudioRef.current.src = '';
      currentAudioRef.current = null;
    }
    if (currentAudioUrlRef.current) {
      URL.revokeObjectURL(currentAudioUrlRef.current);
      currentAudioUrlRef.current = null;
    }
  }, []);

  // ── TTS: Stop speaking & cleanup audio resources ───────────────────────────
  const stopSpeaking = useCallback(() => {
    playbackSessionIdRef.current++;
    cleanupActiveAudio();

    if (isMountedRef.current) {
      updateVoiceState('IDLE');
      setAgentVoiceState('IDLE');
      setVoiceError(null);
    }
  }, [cleanupActiveAudio, updateVoiceState, setAgentVoiceState]);

  // ── TTS: Synthesize with Cartesia Skylar & Play Audio ──────────────────────
  const speakText = useCallback(
    async (text: string) => {
      if (!isTTSSupported) {
        updateVoiceState('IDLE');
        return;
      }

      // Stop any ongoing playback
      stopSpeaking();

      const cleanedText = cleanTextForSpeech(text);
      if (!cleanedText) {
        updateVoiceState('IDLE');
        setAgentVoiceState('IDLE');
        return;
      }

      const currentSessionId = ++playbackSessionIdRef.current;
      const abortController = new AbortController();
      ttsAbortControllerRef.current = abortController;

      updateVoiceState('SPEAKING');
      setAgentVoiceState('SPEAKING');

      try {
        const { blob, error } = await api.synthesizeSpeech(cleanedText, abortController.signal);

        // Check if superseded or unmounted
        if (!isMountedRef.current || playbackSessionIdRef.current !== currentSessionId) {
          return;
        }

        if (!blob) {
          console.warn('[AgentGuard Cartesia TTS] Synthesis error:', error);
          cleanupActiveAudio();
          updateVoiceState('IDLE');
          setAgentVoiceState('IDLE');
          return;
        }

        const audioUrl = URL.createObjectURL(blob);
        currentAudioUrlRef.current = audioUrl;

        const audio = new Audio(audioUrl);
        audio.playbackRate = 0.85;
        currentAudioRef.current = audio;

        audio.onplay = () => {
          if (!isMountedRef.current || playbackSessionIdRef.current !== currentSessionId) return;
          updateVoiceState('SPEAKING');
          setAgentVoiceState('SPEAKING');
        };

        audio.onended = () => {
          if (!isMountedRef.current || playbackSessionIdRef.current !== currentSessionId) return;
          cleanupActiveAudio();
          updateVoiceState('IDLE');
          setAgentVoiceState('IDLE');
        };

        audio.onerror = () => {
          if (!isMountedRef.current || playbackSessionIdRef.current !== currentSessionId) return;
          cleanupActiveAudio();
          updateVoiceState('IDLE');
          setAgentVoiceState('IDLE');
        };

        await audio.play();
      } catch (err: any) {
        if (err?.name === 'AbortError' || abortController.signal.aborted) {
          return;
        }
        console.error('[AgentGuard Cartesia TTS] Audio playback error:', err);
        if (isMountedRef.current && playbackSessionIdRef.current === currentSessionId) {
          cleanupActiveAudio();
          updateVoiceState('IDLE');
          setAgentVoiceState('IDLE');
        }
      }
    },
    [isTTSSupported, stopSpeaking, cleanupActiveAudio, updateVoiceState, setAgentVoiceState]
  );

  // ── Transcript handler — sends through existing pipeline ───────────────────
  const handleTranscript = useCallback(
    async (transcript: string) => {
      if (!isMountedRef.current) return;

      updateVoiceState('PROCESSING');

      const response = await sendConversationalQuery(transcript);

      if (!isMountedRef.current) return;

      if (response && typeof response.message === 'string' && response.message.trim()) {
        // Route the human-readable assistant response to Cartesia TTS
        speakText(response.message);
      } else {
        updateVoiceState('IDLE');
      }
    },
    [sendConversationalQuery, speakText, updateVoiceState]
  );

  // ── STT: Start / Stop listening ─────────────────────────────────────────────
  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.abort();
      recognitionRef.current = null;
    }
    if (isMountedRef.current && voiceStateRef.current === 'LISTENING') {
      updateVoiceState('IDLE');
      setAgentVoiceState('IDLE');
    }
  }, [updateVoiceState, setAgentVoiceState]);

  const startListening = useCallback(() => {
    if (!isSTTSupported || !SpeechRecognitionAPI) return;
    if (voiceStateRef.current !== 'IDLE') return;

    // Abort any stale recognition session before creating a new one
    if (recognitionRef.current) {
      recognitionRef.current.abort();
      recognitionRef.current = null;
    }

    // Stop any ongoing TTS
    stopSpeaking();

    // Clear previous error
    setVoiceError(null);

    let transcriptReceived = false;

    const recognition = new SpeechRecognitionAPI();
    recognition.continuous = false;      // Single utterance model
    recognition.interimResults = false;  // Final result only
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      if (!isMountedRef.current) return;
      updateVoiceState('LISTENING');
      setAgentVoiceState('LISTENING');
    };

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      if (!isMountedRef.current) return;
      transcriptReceived = true;
      const transcript = event.results[0]?.[0]?.transcript?.trim() ?? '';
      if (transcript) {
        handleTranscript(transcript);
      } else {
        updateVoiceState('IDLE');
        setAgentVoiceState('IDLE');
      }
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      if (!isMountedRef.current) return;
      if (event.error === 'aborted') {
        return;
      }
      const msg = recognitionErrorMessage(event.error);
      if (msg) {
        setVoiceError(msg);
        updateVoiceState('ERROR');
        setAgentVoiceState('ERROR');
        setTimeout(() => {
          if (isMountedRef.current && voiceStateRef.current === 'ERROR') {
            setVoiceError(null);
            updateVoiceState('IDLE');
            setAgentVoiceState('IDLE');
          }
        }, 4000);
      }
    };

    recognition.onend = () => {
      recognitionRef.current = null;
      if (!isMountedRef.current) return;
      if (!transcriptReceived && voiceStateRef.current === 'LISTENING') {
        updateVoiceState('IDLE');
        setAgentVoiceState('IDLE');
      }
    };

    recognitionRef.current = recognition;

    try {
      recognition.start();
    } catch (err) {
      recognitionRef.current = null;
      const msg = 'Failed to start speech recognition. Please try again.';
      setVoiceError(msg);
      updateVoiceState('ERROR');
      setAgentVoiceState('ERROR');
      setTimeout(() => {
        if (isMountedRef.current && voiceStateRef.current === 'ERROR') {
          setVoiceError(null);
          updateVoiceState('IDLE');
          setAgentVoiceState('IDLE');
        }
      }, 3000);
    }
  }, [
    isSTTSupported,
    SpeechRecognitionAPI,
    stopSpeaking,
    handleTranscript,
    updateVoiceState,
    setAgentVoiceState,
  ]);

  // ── Error dismiss ────────────────────────────────────────────────────────────
  const dismissError = useCallback(() => {
    setVoiceError(null);
    updateVoiceState('IDLE');
    setAgentVoiceState('IDLE');
  }, [updateVoiceState, setAgentVoiceState]);

  // ── Cleanup on unmount ───────────────────────────────────────────────────────
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      playbackSessionIdRef.current++;
      cleanupActiveAudio();
      if (recognitionRef.current) {
        recognitionRef.current.abort();
        recognitionRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cleanupActiveAudio]);

  return {
    voiceState,
    voiceError,
    isSTTSupported,
    isTTSSupported,
    startListening,
    stopListening,
    stopSpeaking,
    dismissError,
  };
}
