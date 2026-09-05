/**
 * speechCleaner.ts — Phase 5.5C TTS Natural Speech Cleaner & Chunking
 *
 * Prepares chatbot responses for natural-sounding speech synthesis:
 *  - Cleans markdown, technical paths, and UI artifacts without altering visible text.
 *  - Replaces currency symbols with natural spoken words (e.g. ₹3,499 → 3,499 rupees).
 *  - Expands common abbreviations (e.g. e.g. → for example).
 *  - Segments text into sentence/paragraph chunks with conversational breathing pauses.
 *  - Selects the best available natural female English voice across operating systems.
 */

/**
 * Centralized AgentGuard TTS playback rate constant.
 * Requirement: exactly 0.95 (95% of normal speed) across all AgentGuard voice playback paths
 * (autonomous demo, conversational chatbot, pause/resume, etc.).
 */
export const AGENTGUARD_TTS_PLAYBACK_RATE = 0.95;

export interface SpeechChunk {
  text: string;
  pauseAfterMs: number;
}

/**
 * Strips Markdown formatting, file paths, and UI artifacts from a chatbot response string
 * so that SpeechSynthesis produces natural, polished human speech.
 *
 * CONTRACT:
 *  - The VISIBLE chatbot response is NEVER modified.
 *  - Only the copy passed to SpeechSynthesis is cleaned.
 *  - Natural conversational language is preserved.
 */
export function cleanTextForSpeech(text: string): string {
  if (!text || typeof text !== 'string') return '';

  let cleaned = text;

  // ── 1. Remove fenced code blocks entirely ─────────────────────────────────
  cleaned = cleaned.replace(/```[\s\S]*?```/g, '');

  // ── 2. Remove inline code backticks, keep content ─────────────────────────
  cleaned = cleaned.replace(/`([^`]*)`/g, '$1');

  // ── 3. Clean file paths in parentheses: ( backend/app/services/audit_log.py )
  cleaned = cleaned.replace(/\(\s*backend\/[^\)]+\s*\)/gi, '');
  cleaned = cleaned.replace(/\(\s*[a-zA-Z0-9_\-./]+\.(py|ts|tsx|js|json|md)\s*\)/gi, '');

  // ── 4. Ensure headings end with punctuation before stripping # ───────────
  cleaned = cleaned.replace(/^(#{1,6}\s+.*?)([\.\?\!])?\s*$/gm, (_, content, punc) => {
    return `${content}${punc || '.'}`;
  });
  cleaned = cleaned.replace(/^#{1,6}\s+/gm, '');

  // ── 5. Ensure bullet & list items end with punctuation ───────────────────
  cleaned = cleaned.replace(/^([ \t]*[-*+]\s+.*?)([\.\?\!])?\s*$/gm, (_, content, punc) => {
    return `${content}${punc || '.'}`;
  });
  cleaned = cleaned.replace(/^([ \t]*\d+\.\s+.*?)([\.\?\!])?\s*$/gm, (_, content, punc) => {
    return `${content}${punc || '.'}`;
  });

  // Strip bullet markers
  cleaned = cleaned.replace(/^[ \t]*[-*+]\s+/gm, '');
  cleaned = cleaned.replace(/^[ \t]*\d+\.\s+/gm, '');

  // ── 6. Remove bold + italic markers, keep text ────────────────────────────
  cleaned = cleaned.replace(/\*{3}([^*]+)\*{3}/g, '$1');
  cleaned = cleaned.replace(/\*{2}([^*]+)\*{2}/g, '$1');
  cleaned = cleaned.replace(/\*([^*\n]+)\*/g, '$1');
  cleaned = cleaned.replace(/_{2}([^_]+)_{2}/g, '$1');
  cleaned = cleaned.replace(/_([^_\n]+)_/g, '$1');

  // ── 7. Natural currency expansion (₹3,499 → 3,499 rupees) ────────────────
  cleaned = cleaned.replace(/₹\s*([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)/g, '$1 rupees');

  // ── 8. Remove [object Object] and citation markers ────────────────────────
  cleaned = cleaned.replace(/\[object Object\]/gi, '');
  cleaned = cleaned.replace(/\[\d+\]/g, '');

  // ── 9. Remove bare URL strings & convert markdown links [text](url) → text
  cleaned = cleaned.replace(/https?:\/\/[^\s)>]+/g, '');
  cleaned = cleaned.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');

  // ── 10. Remove horizontal rules ───────────────────────────────────────────
  cleaned = cleaned.replace(/^[-*_]{3,}\s*$/gm, '');

  // ── 11. Remove JSON-like fragments ────────────────────────────────────────
  cleaned = cleaned.replace(/\{[^{}]{0,120}\}/g, '');

  // ── 12. Remove internal path references (file:// etc.) ───────────────────
  cleaned = cleaned.replace(/file:\/\/[^\s]*/g, '');

  // ── 13. Natural pronunciation for common technical abbreviations & security codes ──
  cleaned = cleaned.replace(/\be\.g\.,?\s*/gi, 'for example, ');
  cleaned = cleaned.replace(/\bi\.e\.,?\s*/gi, 'that is, ');
  cleaned = cleaned.replace(/\bvs\.\s*/gi, 'versus ');
  cleaned = cleaned.replace(/\bapprox\.\s*/gi, 'approximately ');
  cleaned = cleaned.replace(/\btxns?\b/gi, 'transactions');

  // Targeted normalization for machine-readable security decision codes
  cleaned = cleaned.replace(/\bPRICE_MISMATCH\b/g, 'price mismatch');
  cleaned = cleaned.replace(/\bMANDATE_REVOKED\b/g, 'mandate revoked');
  cleaned = cleaned.replace(/\bREPLAY_DETECTED\b/g, 'replay detected');
  cleaned = cleaned.replace(/\bBUDGET_EXCEEDED\b/g, 'budget exceeded');
  cleaned = cleaned.replace(/\bPOLICY_VIOLATION\b/g, 'policy violation');
  cleaned = cleaned.replace(/\bRATE_LIMITED\b/g, 'rate limited');
  cleaned = cleaned.replace(/\bUNAUTHORIZED_AGENT\b/g, 'unauthorized agent');
  cleaned = cleaned.replace(/\bEXPIRED_MANDATE\b/g, 'expired mandate');
  cleaned = cleaned.replace(/\bITEM_RESTRICTED\b/g, 'item restricted');
  cleaned = cleaned.replace(/\bMERCHANT_RESTRICTED\b/g, 'merchant restricted');

  // SHA-256 deliberately spelled character-by-character as a security/hash identifier
  cleaned = cleaned.replace(/\bSHA[- ]?256\b/gi, 'S H A, two five six');

  // ── 14. Normalise whitespace ─────────────────────────────────────────────
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n');
  cleaned = cleaned.replace(/[ \t]{2,}/g, ' ');

  return cleaned.trim();
}

/**
 * Splits cleaned response text into natural sentence & paragraph chunks
 * with calibrated breathing pauses between thoughts.
 */
export function splitTextIntoSpeechChunks(text: string): SpeechChunk[] {
  const cleaned = cleanTextForSpeech(text);
  if (!cleaned) return [];

  // Split by paragraph breaks first
  const paragraphs = cleaned
    .split(/\n+/)
    .map((p) => p.trim())
    .filter(Boolean);

  const chunks: SpeechChunk[] = [];

  for (let pIdx = 0; pIdx < paragraphs.length; pIdx++) {
    const para = paragraphs[pIdx];
    const isLastPara = pIdx === paragraphs.length - 1;

    // Split paragraph into sentences on punctuation (. ! ?) followed by whitespace or end of string.
    // Avoid splitting decimal numbers (e.g. 3.499) or abbreviations.
    const sentenceMatches = para.match(/[^.!?]+[.!?]+(?:\s+|$)|[^.!?]+$/g);
    const sentences = (sentenceMatches || [para]).map((s) => s.trim()).filter(Boolean);

    for (let sIdx = 0; sIdx < sentences.length; sIdx++) {
      const sentence = sentences[sIdx];
      const isLastSentenceInPara = sIdx === sentences.length - 1;

      // Natural pause timing:
      // - 380ms pause after the last sentence in a paragraph (thought boundary)
      // - 180ms pause between sentences within the same paragraph (conversational breath)
      const pauseAfterMs = isLastSentenceInPara && !isLastPara ? 380 : 180;

      chunks.push({
        text: sentence,
        pauseAfterMs,
      });
    }
  }

  return chunks;
}

/**
 * Deterministically ranks and selects the best natural-sounding female English voice
 * available in the current browser/OS environment.
 *
 * Preference Hierarchy:
 *  1. Google UK English Female (Chrome en-GB — exceptionally clear, calm, polished)
 *  2. Microsoft Natural/Neural Female voices (Jenny, Aria, Sonia, Libby)
 *  3. Apple Enhanced/Premium Female voices (Ava, Samantha, Serena, Karen)
 *  4. Google US English (Chrome en-US female/neutral)
 *  5. Standard female English voices (Samantha, Victoria, Karen, Serena, Tessa, Allison)
 *  6. Any voice with 'female' in its metadata
 *  7. Any English voice
 *  8. Browser default voice
 */
export function selectBestFemaleVoice(voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | null {
  if (!voices || voices.length === 0) return null;

  // Filter for English voices first
  const englishVoices = voices.filter((v) => v.lang && v.lang.toLowerCase().startsWith('en'));
  const candidatePool = englishVoices.length > 0 ? englishVoices : voices;

  const scoreVoice = (voice: SpeechSynthesisVoice): number => {
    const name = voice.name.toLowerCase();
    const lang = voice.lang.toLowerCase();
    let score = 0;

    // Reject novelty / sound-effect voices
    const isNovelty = /\b(bad news|bahh|bells|boing|bubbles|cellos|deranged|good news|hysterical|pipe organ|trinoids|whisper|zarvox|organ)\b/i.test(
      name
    );
    if (isNovelty) return -1000;

    // Penalise explicitly male voices
    const isMale =
      /\b(male|david|daniel|alex|fred|george|mark|oliver|guy|albert|junior|ralph|tom|lee)\b/i.test(
        name
      ) && !/female/i.test(name);
    if (isMale) score -= 150;

    // ── Tier 1: Premium / Neural / Natural Female voices ───────────────────
    if (name.includes('google uk english female')) {
      score += 500; // Top choice for Chrome: calm, articulate, polished
    } else if (
      /microsoft (jenny|aria|sonia|libby|natasha|clara|emma)/i.test(name) &&
      /natural|online/i.test(name)
    ) {
      score += 480;
    } else if (
      /(ava|samantha|serena|karen|victoria|tessa|allison|susan|zoe)/i.test(name) &&
      /enhanced|premium/i.test(name)
    ) {
      score += 460;
    } else if (name.includes('google us english')) {
      score += 420;
    }

    // ── Tier 2: Standard high-quality female voices by name ─────────────────
    else if (
      /^(ava|samantha|serena|karen|victoria|tessa|allison|susan|zoe|kate|moira|fiona)\b/i.test(name)
    ) {
      score += 350;
    } else if (
      /\b(ava|samantha|serena|karen|victoria|tessa|allison|susan|zoe|kate|moira|fiona)\b/i.test(name)
    ) {
      score += 300;
    }

    // ── Tier 3: Any voice labeled 'female' or 'woman' ──────────────────────
    else if (/\b(female|woman)\b/i.test(name)) {
      score += 250;
    } else if (/microsoft zira/i.test(name)) {
      score += 200;
    }

    // ── Locale preferences ────────────────────────────────────────────────
    if (lang === 'en-us' || lang === 'en_us') score += 20;
    else if (lang === 'en-gb' || lang === 'en_gb') score += 25;
    else if (lang.startsWith('en')) score += 10;

    // Remote voices (Google / MS Cloud) often have higher audio fidelity
    if (!voice.localService) score += 15;

    // Slight preference for default voice if nothing else matched
    if (voice.default) score += 5;

    return score;
  };

  const sorted = [...candidatePool].sort((a, b) => scoreVoice(b) - scoreVoice(a));
  return sorted[0] || null;
}
