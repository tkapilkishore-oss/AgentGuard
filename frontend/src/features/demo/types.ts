/**
 * Types for Autonomous Agent Demo Mode
 * Controlled state machine, step sequences, and semantic UI targets.
 */

export type DemoState =
  | 'IDLE'
  | 'RUNNING'
  | 'PAUSED'
  | 'STOPPED_AWAITING_QUESTION'
  | 'STOPPED_AWAITING_CONTINUE_DECISION'
  | 'COMPLETED'
  | 'ERROR';

export type DemoStepId = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11;

export type AgentTargetId =
  | 'cockpit-budget'
  | 'live-protection-mandate'
  | 'threat-price-tampering'
  | 'threat-happy-path'
  | 'decision-result'
  | 'forensic-latest-transaction'
  | null;

export interface DemoStepDefinition {
  id: DemoStepId;
  name: string;
  route: string;
  targetId: AgentTargetId;
  spokenNarration: string;
  captionText: string;
  expectedDurationMs?: number;
}

export interface CursorPosition {
  x: number;
  y: number;
  visible: boolean;
  pulsing: boolean;
  clicking: boolean;
  label: string;
}

export interface AutonomousDemoContextType {
  demoState: DemoState;
  currentStepId: DemoStepId;
  isPaused: boolean;
  currentNarration: string;
  currentTargetId: AgentTargetId;
  runId: number;
  startDemo: (fromStep?: DemoStepId) => Promise<void>;
  pauseDemo: () => void;
  resumeDemo: () => void;
  stopDemo: () => void;
  handleStoppedQuery: (userQuery: string) => Promise<boolean>;
}
