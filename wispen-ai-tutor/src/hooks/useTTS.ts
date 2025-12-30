import { useState, useCallback, useRef, useEffect } from 'react';
import { API_BASE_URL } from '../config';

interface UseTTSReturn {
    speak: (text: string) => Promise<void>;
    stop: (reason?: string) => void;
    pause: () => void;
    resume: () => void;
    isSpeaking: boolean;
    isPaused: boolean;
    isSupported: boolean;
    voices: SpeechSynthesisVoice[];
    selectedVoice: SpeechSynthesisVoice | null;
    setVoice: (voice: SpeechSynthesisVoice) => void;
    ttsStatus: string;
}

/**
 * Custom hook for Text-to-Speech using Backend Groq API (PlayAI)
 * Replaces Web Speech API with high-quality AI voice
 */
export const useTTS = (): UseTTSReturn => {
    const [isSpeaking, setIsSpeaking] = useState(false);
    const [isPaused, setIsPaused] = useState(false);
    const [ttsStatus, setTtsStatus] = useState<string>('idle');
    const audioRef = useRef<HTMLAudioElement | null>(null);
    const abortControllerRef = useRef<AbortController | null>(null);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            console.log('[useTTS] Unmounting/Cleaning up - Stopping TTS');
            if (audioRef.current) {
                audioRef.current.pause();
                audioRef.current = null;
            }
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
        };
    }, []);

    const stop = useCallback((reason: string = 'manual') => {
        console.log(`[useTTS] Stopping TTS (Reason: ${reason})`);
        if (reason === 'manual') console.trace('Manual Stop Trace');
        if (audioRef.current) {
            audioRef.current.pause();
            audioRef.current.currentTime = 0;
        }
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
            abortControllerRef.current = null;
        }
        if ('speechSynthesis' in window) {
            speechSynthesis.cancel();
        }
        setIsSpeaking(false);
        setIsPaused(false);
        setTtsStatus(prev => prev === 'playing...' || prev === 'fetching audio...' ? 'cancelled' : prev);
    }, []);

    const speak = useCallback(async (text: string) => {
        if (!text) return;

        // Stop any current speech/fetch
        stop('starting new speech');
        setIsSpeaking(true);
        setIsPaused(false);

        const controller = new AbortController();
        abortControllerRef.current = controller;

        try {
            // Pre-process text (clean)
            let cleanText = text
                .replace(/```[\s\S]*?```/g, '') // remove code blocks entirely for speed
                .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
                .replace(/[*_~`]/g, '')
                .replace(/[#]/g, '')
                .replace(/(\d+)-(\d+)/g, '$1 minus $2') // 5-3 -> 5 minus 3
                .replace(/ - /g, ' minus ')             // x - y -> x minus y
                .replace(/-(\d+)/g, 'negative $1')      // -5 -> negative 5
                .replace(/\^2/g, ' squared')
                .replace(/²/g, ' squared')
                .replace(/\^3/g, ' cubed')
                .replace(/³/g, ' cubed')
                .replace(/\\frac{(\d+)}{(\d+)}/g, '$1 over $2')
                .trim();

            if (!cleanText) {
                setTtsStatus('error: empty text');
                setIsSpeaking(false);
                return;
            }

            // High-Speed Sentence Splitting
            const sentences = cleanText.match(/[^.!?]+[.!?]+(\s|$)|[^.!?]+$/g) || [cleanText];

            setTtsStatus('fetching audio...');

            // Queue for audio URLs
            const audioQueue: string[] = [];
            let isPlaying = false;
            let playedCount = 0;
            let fetchedCount = 0;
            let hasFetchError = false;

            const playNext = async () => {
                // Check if we are done:
                // If queue is empty AND we have fetched everything (or errored out on remainder), we are done.
                if (audioQueue.length === 0 && fetchedCount === sentences.length) {
                    setIsSpeaking(false);
                    setTtsStatus('idle');
                    return;
                }

                if (audioQueue.length > 0) {
                    const url = audioQueue.shift();
                    if (url) {
                        const audio = new Audio(url);
                        audioRef.current = audio;

                        audio.onended = () => {
                            URL.revokeObjectURL(url);
                            playedCount++;
                            playNext();
                        };

                        audio.onerror = () => {
                            console.error("Audio playback error");
                            playedCount++; // Count as played to avoid stall
                            playNext();
                        };

                        setTtsStatus('speaking...');
                        try {
                            await audio.play();
                        } catch (e) {
                            console.error("Play error", e);
                            setIsSpeaking(false);
                        }
                    }
                } else {
                    // Buffer underrun: Queue is empty, but we haven't fetched all sentences yet.
                    // We just set isPlaying = false and let the fetch loop trigger playNext when data arrives.
                    isPlaying = false;
                    setTtsStatus('buffering...');
                }
            };

            // Fetch Loop
            for (let i = 0; i < sentences.length; i++) {
                if (controller.signal.aborted) break;

                const sentence = sentences[i].trim();
                // If sentence is empty/spaces, just count it as fetched and continue
                if (!sentence) {
                    fetchedCount++;
                    continue;
                }

                try {
                    const response = await fetch(`${API_BASE_URL}/tts`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ text: sentence }),
                        signal: controller.signal
                    });

                    if (response.ok) {
                        const blob = await response.blob();
                        const url = URL.createObjectURL(blob);
                        audioQueue.push(url);
                        fetchedCount++;

                        // If not currently playing, start playing immediately
                        if (!isPlaying && audioRef.current?.paused !== false) {
                            isPlaying = true;
                            playNext();
                        }
                    } else {
                        console.error("Segment fetch failed", response.status);
                        fetchedCount++; // Skip this segment
                    }
                } catch (err: any) {
                    if (err.name !== 'AbortError') {
                        console.error("Segment fetch error", err);
                        fetchedCount++; // Skip
                        hasFetchError = true;
                    }
                }
            }

            // If we finished the loop and nothing was ever played (e.g. all errors), finish up
            if (fetchedCount === sentences.length && playedCount === 0 && !isPlaying && !hasFetchError) {
                // Nothing to play?
                setIsSpeaking(false);
                setTtsStatus('idle');
            }

        } catch (err: any) {
            if (err.name === 'AbortError') {
                setTtsStatus('cancelled');
            } else {
                console.error('TTS Error:', err);
                setTtsStatus('error');
            }
        }
    }, [stop]);

    const pause = useCallback(() => {
        if (audioRef.current && !audioRef.current.paused) {
            audioRef.current.pause();
            setIsPaused(true);
        }
    }, []);

    const resume = useCallback(() => {
        if (audioRef.current && audioRef.current.paused) {
            audioRef.current.play();
            setIsPaused(false);
        }
    }, []);

    // Dummy implementations for compatibility
    const voices: SpeechSynthesisVoice[] = [];
    const selectedVoice: SpeechSynthesisVoice | null = null;
    const setVoice = (_: SpeechSynthesisVoice) => { };

    return {
        speak,
        stop,
        pause,
        resume,
        isSpeaking,
        isPaused,
        isSupported: true,
        voices,
        selectedVoice,
        setVoice,
        ttsStatus
    };
};

export default useTTS;
