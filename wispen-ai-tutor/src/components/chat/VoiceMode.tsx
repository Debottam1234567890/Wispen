import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { auth, storage } from '../../firebase';
import { ref, uploadBytes, getDownloadURL } from 'firebase/storage';
import { useTTS } from '../../hooks/useTTS';
import { API_BASE_URL } from '../../config';

interface VoiceModeProps {
    isOpen: boolean;
    onClose: () => void;
    sessionId?: string;
    onMessageSent?: (userMessage: string, aiResponse: string) => void;
}

interface VoiceRecording {
    id: string;
    url: string;
    duration: number;
    timestamp: Date;
}

type VoiceState = 'idle' | 'listening' | 'processing' | 'speaking';

const VoiceMode = ({ isOpen, onClose, sessionId, onMessageSent }: VoiceModeProps) => {
    const [voiceState, setVoiceState] = useState<VoiceState>('idle');
    const [transcript, setTranscript] = useState('');
    const [_aiResponse, setAiResponse] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [isRecording, setIsRecording] = useState(false);
    const [_savedRecording, setSavedRecording] = useState<VoiceRecording | null>(null);
    const [_isSaving, setIsSaving] = useState(false);

    const recognitionRef = useRef<any>(null);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);
    const recordingStartTime = useRef<Date | null>(null);

    // Refs to track latest values for timer callback (avoid stale closures)
    const transcriptRef = useRef('');
    const voiceStateRef = useRef<VoiceState>('idle');
    const hasSentRef = useRef(false);

    // Silence timer ref for auto-send
    const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const SILENCE_THRESHOLD_MS = 5500; // 5.5 seconds

    const { speak, stop: stopTTS, isSpeaking, pause, resume, isPaused } = useTTS();

    // Waveform animation
    const [waveformBars, setWaveformBars] = useState<number[]>(new Array(40).fill(5));

    // Keep refs in sync with state
    useEffect(() => {
        transcriptRef.current = transcript;
    }, [transcript]);

    useEffect(() => {
        voiceStateRef.current = voiceState;
    }, [voiceState]);

    // Core function to send transcript to AI
    const sendToAI = useCallback(async (messageText: string) => {
        setError(null); // Clear previous errors
        if (!messageText.trim() || !sessionId) {
            setVoiceState('idle');
            return;
        }

        const userMsgId = 'voice-user-' + Date.now().toString() + Math.random().toString(36).substr(2, 5);
        const aiMsgId = 'voice-ai-' + Date.now().toString() + Math.random().toString(36).substr(2, 5);

        try {
            const user = auth.currentUser;
            if (!user) {
                setError('Not authenticated');
                setVoiceState('idle');
                return;
            }

            const token = await user.getIdToken();
            const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/messages`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    id: userMsgId,
                    aiMessageId: aiMsgId,
                    sender: 'user',
                    content: messageText,
                    type: 'text'
                })
            });

            if (!response.ok) throw new Error('Network response was not ok');

            // Handle Streaming Response
            const reader = response.body?.getReader();
            const decoder = new TextDecoder();
            let fullContent = '';

            if (reader) {
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    fullContent += decoder.decode(value, { stream: true });
                }
            }

            // Helper to strip emojis and format math for TTS
            const cleanTextForTTS = (text: string) => {
                let clean = text
                    .replace(/[\u{1F600}-\u{1F64F}]/gu, '')
                    .replace(/[\u{1F300}-\u{1F5FF}]/gu, '')
                    .replace(/[\u{1F680}-\u{1F6FF}]/gu, '')
                    .replace(/[\u{1F1E0}-\u{1F1FF}]/gu, '')
                    .replace(/[\u{2700}-\u{27BF}]/gu, '')
                    .replace(/[\u{FE00}-\u{FE0F}]/gu, '')
                    .replace(/[\u{1F900}-\u{1F9FF}]/gu, '')
                    .replace(/[*#]/g, '');

                // Fix Math Pronunciation
                clean = clean
                    .replace(/\^2/g, ' squared')
                    .replace(/²/g, ' squared')
                    .replace(/\^3/g, ' cubed')
                    .replace(/³/g, ' cubed')
                    .replace(/\\frac{(\d+)}{(\d+)}/g, '$1 over $2') // Simple fractions
                    .replace(/[$]/g, '') // Remove LaTeX delimiters
                    .replace(/\\/g, ''); // Remove backslashes

                return clean;
            };

            console.log('AI Response complete:', fullContent.substring(0, 50));
            if (!fullContent.trim()) {
                console.warn('AI Response is empty');
                setError('AI returned no response');
                setVoiceState('idle');
                return;
            }

            setAiResponse(fullContent);
            setVoiceState('speaking');

            const cleaned = cleanTextForTTS(fullContent);
            console.log('Speaking (cleaned):', cleaned.substring(0, 50));
            speak(cleaned);

            (onMessageSent as any)?.(messageText, fullContent, userMsgId, aiMsgId);
        } catch (err) {
            console.error('Error sending voice message:', err);
            setError('Failed to send message');
            setVoiceState('idle');
        }


    }, [sessionId, speak, onMessageSent]);

    // Clear silence timer
    const clearSilenceTimer = useCallback(() => {
        if (silenceTimerRef.current) {
            clearTimeout(silenceTimerRef.current);
            silenceTimerRef.current = null;
        }
    }, []);

    // Auto-send function using refs for latest values
    const triggerAutoSend = useCallback(() => {
        const currentTranscript = transcriptRef.current;
        const currentVoiceState = voiceStateRef.current;

        console.log('Auto-send check:', { currentTranscript, currentVoiceState, hasSent: hasSentRef.current });

        if (currentTranscript && currentTranscript.trim() && currentVoiceState === 'listening' && !hasSentRef.current) {
            console.log('Silence detected, auto-sending:', currentTranscript);
            hasSentRef.current = true;

            // Stop recognition and send
            try {
                recognitionRef.current?.stop();
            } catch (e) {
                // Ignore
            }
            clearSilenceTimer();
            setVoiceState('processing');

            // Trigger the send
            sendToAI(currentTranscript);
        }
    }, [clearSilenceTimer, sendToAI]);

    // Start/reset silence timer
    const resetSilenceTimer = useCallback(() => {
        clearSilenceTimer();
        silenceTimerRef.current = setTimeout(() => {
            triggerAutoSend();
        }, SILENCE_THRESHOLD_MS);
    }, [clearSilenceTimer, triggerAutoSend]);

    // Initialize speech recognition
    useEffect(() => {
        if (!isOpen) return;

        hasSentRef.current = false;

        const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

        if (SpeechRecognition) {
            recognitionRef.current = new SpeechRecognition();
            recognitionRef.current.continuous = true;
            recognitionRef.current.interimResults = true;
            recognitionRef.current.lang = 'en-US';

            recognitionRef.current.onresult = (event: any) => {
                let finalTranscript = '';
                let interimTranscript = '';

                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const result = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        finalTranscript += result;
                    } else {
                        interimTranscript += result;
                    }
                }

                const newTranscript = finalTranscript || interimTranscript;
                if (newTranscript) {
                    setTranscript(newTranscript);
                    // Reset silence timer every time we get speech input
                    resetSilenceTimer();
                }
            };

            recognitionRef.current.onerror = (event: any) => {
                console.error('Speech recognition error:', event.error);
                if (event.error !== 'no-speech' && event.error !== 'aborted') {
                    setError(`Recognition error: ${event.error}`);
                }
            };

            recognitionRef.current.onend = () => {
                // If recognition ended naturally and we have content, auto-send
                const currentTranscript = transcriptRef.current;
                const currentVoiceState = voiceStateRef.current;

                if (currentVoiceState === 'listening' && currentTranscript && !hasSentRef.current) {
                    console.log('Recognition ended, sending:', currentTranscript);
                    hasSentRef.current = true;
                    clearSilenceTimer();
                    setVoiceState('processing');
                    sendToAI(currentTranscript);
                }
            };
        }

        return () => {
            if (recognitionRef.current) {
                try {
                    recognitionRef.current.stop();
                } catch (e) {
                    // Ignore stop errors
                }
            }
            clearSilenceTimer();
            stopTTS();
        };
    }, [isOpen, resetSilenceTimer, clearSilenceTimer, sendToAI, stopTTS]);

    // Animate waveform based on state
    useEffect(() => {
        let interval: ReturnType<typeof setInterval>;

        if (voiceState === 'speaking' || isSpeaking) {
            // Active waveform animation when AI is speaking
            interval = setInterval(() => {
                setWaveformBars(prev => prev.map(() => Math.random() * 60 + 10));
            }, 100);
        } else if (voiceState === 'listening') {
            // Subtle animation when listening
            interval = setInterval(() => {
                setWaveformBars(prev => prev.map(() => Math.random() * 20 + 5));
            }, 150);
        } else {
            // Static when idle
            setWaveformBars(new Array(40).fill(5));
        }

        return () => clearInterval(interval);
    }, [voiceState, isSpeaking]);



    // Start listening
    const startListening = useCallback(() => {
        if (!recognitionRef.current) {
            setError('Speech recognition not supported in this browser');
            return;
        }

        setTranscript('');
        setAiResponse('');
        setError(null);
        setVoiceState('listening');
        hasSentRef.current = false;

        try {
            recognitionRef.current.start();

            // Start recording for saving
            navigator.mediaDevices.getUserMedia({ audio: true })
                .then(stream => {
                    const recorder = new MediaRecorder(stream);
                    mediaRecorderRef.current = recorder;
                    audioChunksRef.current = [];

                    recorder.ondataavailable = (e) => {
                        audioChunksRef.current.push(e.data);
                    };

                    recorder.onstop = () => {
                        stream.getTracks().forEach(track => track.stop());
                    };

                    recorder.start();
                    setIsRecording(true);
                    recordingStartTime.current = new Date();
                })
                .catch(err => {
                    console.error('Microphone access error:', err);
                });
        } catch (e) {
            console.error('Error starting recognition:', e);
        }
    }, []);

    // Stop everything
    const handleStop = useCallback(() => {
        try {
            recognitionRef.current?.stop();
        } catch (e) {
            // Ignore
        }
        stopTTS();
        clearSilenceTimer();

        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
        }

        setVoiceState('idle');
    }, [stopTTS, isRecording, clearSilenceTimer]);

    // Main Button Click Handler
    const handleMainButtonClick = useCallback(() => {
        if (voiceState === 'idle') {
            startListening();
        } else if (voiceState === 'speaking' || isSpeaking) {
            // Toggle Play/Pause instead of Stop
            if (isPaused) {
                resume();
            } else {
                pause();
            }
        } else if (voiceState === 'listening') {
            handleStop();
        } else {
            handleStop();
        }
    }, [voiceState, isSpeaking, isPaused, startListening, handleStop, resume, pause]);

    // Save recording to Firebase
    const saveRecordingToFirebase = useCallback(async () => {
        if (audioChunksRef.current.length === 0) return null;

        const user = auth.currentUser;
        if (!user || !sessionId) return null;

        try {
            setIsSaving(true);

            // Create audio blob
            const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
            const duration = recordingStartTime.current
                ? Math.round((Date.now() - recordingStartTime.current.getTime()) / 1000)
                : 0;

            // Upload to Firebase Storage
            const recordingId = `voice_${Date.now()}`;
            const storageRef = ref(storage, `voice_recordings/${user.uid}/${sessionId}/${recordingId}.webm`);

            await uploadBytes(storageRef, audioBlob);
            const downloadUrl = await getDownloadURL(storageRef);

            const recording: VoiceRecording = {
                id: recordingId,
                url: downloadUrl,
                duration,
                timestamp: new Date()
            };

            setSavedRecording(recording);
            console.log('Recording saved:', downloadUrl);

            return recording;
        } catch (err) {
            console.error('Failed to save recording:', err);
            setError('Failed to save recording');
            return null;
        } finally {
            setIsSaving(false);
        }
    }, [sessionId]);

    // Close voice mode with save
    const handleClose = useCallback(async () => {
        handleStop();

        // Save recording before closing (if there's content)
        if (audioChunksRef.current.length > 0) {
            await saveRecordingToFirebase();
        }

        // Reset state
        setTranscript('');
        setAiResponse('');
        setSavedRecording(null);
        audioChunksRef.current = [];

        onClose();
    }, [handleStop, onClose, saveRecordingToFirebase]);

    // Effect when TTS finishes speaking
    useEffect(() => {
        if (!isSpeaking && voiceState === 'speaking') {
            // AI finished speaking, go back to idle (user can speak again)
            setTimeout(() => {
                setVoiceState('idle');
                setTranscript('');
                hasSentRef.current = false;
            }, 500);
        }
    }, [isSpeaking, voiceState]);

    if (!isOpen) return null;

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    width: '100vw',
                    height: '100vh',
                    background: '#fcfcfc', // White background
                    zIndex: 9999,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#333',
                    fontFamily: '"Indie Flower", cursive',
                    overflow: 'hidden'
                }}
            >
                {/* Floating Doodles Background */}
                <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', opacity: 0.15 }}>
                    <motion.div
                        animate={{ y: [0, -20, 0], rotate: [0, 5, 0] }}
                        transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
                        style={{ position: 'absolute', top: '20%', left: '15%', fontSize: '3rem' }}>✏️</motion.div>
                    <motion.div
                        animate={{ y: [0, 20, 0], rotate: [0, -10, 0] }}
                        transition={{ duration: 6, repeat: Infinity, ease: "easeInOut", delay: 1 }}
                        style={{ position: 'absolute', top: '15%', right: '20%', fontSize: '2.5rem' }}>📏</motion.div>
                    <motion.div
                        animate={{ x: [0, 15, 0], rotate: [0, 15, 0] }}
                        transition={{ duration: 7, repeat: Infinity, ease: "easeInOut", delay: 2 }}
                        style={{ position: 'absolute', bottom: '25%', left: '25%', fontSize: '3rem' }}>📝</motion.div>
                    <motion.div
                        animate={{ y: [0, -15, 0], rotate: [0, -5, 0] }}
                        transition={{ duration: 5.5, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}
                        style={{ position: 'absolute', bottom: '20%', right: '15%', fontSize: '2.8rem' }}>📐</motion.div>
                    <motion.div
                        animate={{ x: [0, -10, 0], rotate: [0, 10, 0] }}
                        transition={{ duration: 8, repeat: Infinity, ease: "easeInOut", delay: 1.5 }}
                        style={{ position: 'absolute', top: '50%', left: '10%', fontSize: '2rem' }}>✂️</motion.div>
                    <motion.div
                        animate={{ y: [0, 10, 0], rotate: [0, -8, 0] }}
                        transition={{ duration: 6.5, repeat: Infinity, ease: "easeInOut", delay: 2.5 }}
                        style={{ position: 'absolute', top: '40%', right: '8%', fontSize: '2.4rem' }}>📎</motion.div>
                </div>

                {/* Close Button */}
                <motion.button
                    whileHover={{ scale: 1.1, rotate: 90 }}
                    whileTap={{ scale: 0.9 }}
                    onClick={handleClose}
                    style={{
                        position: 'absolute',
                        top: '40px',
                        right: '40px',
                        background: 'white',
                        border: '1px solid #eee',
                        borderRadius: '50%',
                        width: '60px',
                        height: '60px',
                        color: '#555',
                        fontSize: '1.5rem',
                        cursor: 'pointer',
                        boxShadow: '0 5px 20px rgba(0,0,0,0.05)',
                        zIndex: 10,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                    }}
                >
                    ✕
                </motion.button>

                {/* Status Text (Minimal) */}
                <div style={{ marginBottom: '60px', fontSize: '1.8rem', color: '#555', fontWeight: 'bold' }}>
                    {voiceState === 'idle' && 'Tap the mic to start'}
                    {voiceState === 'listening' && 'Listening...'}
                    {voiceState === 'processing' && 'Thinking...'}
                    {voiceState === 'speaking' && 'Wispen Speaking...'}
                </div>

                {/* Waveform Visualizer */}
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '6px',
                    height: '120px',
                    marginBottom: '60px'
                }}>
                    {waveformBars.map((height, index) => (
                        <motion.div
                            key={index}
                            animate={{ height: `${height * 1.5}px` }} // Taller bars
                            transition={{ duration: 0.1 }}
                            style={{
                                width: '8px',
                                background: voiceState === 'speaking' || isSpeaking
                                    ? `linear-gradient(180deg, #6C63FF 0%, #a29bfe 100%)`
                                    : voiceState === 'listening'
                                        ? 'linear-gradient(180deg, #ff7675, #fab1a0)' // Pastel red/orange
                                        : '#eee',
                                borderRadius: '4px',
                            }}
                        />
                    ))}
                </div>

                {/* Main Action Button */}
                <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={handleMainButtonClick}
                    style={{
                        width: '140px',
                        height: '140px',
                        borderRadius: '50%',
                        border: 'none',
                        background: voiceState === 'listening'
                            ? 'linear-gradient(135deg, #ff7675, #d63031)' // Soft Red
                            : voiceState === 'speaking'
                                ? 'linear-gradient(135deg, #6C63FF, #a29bfe)' // Soft Purple
                                : 'linear-gradient(135deg, #00b894, #55efc4)', // Soft Teal
                        color: 'white',
                        fontSize: '3.5rem',
                        cursor: 'pointer',
                        boxShadow: '0 15px 40px rgba(0,0,0,0.15)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        position: 'relative',
                        zIndex: 5
                    }}
                >
                    {voiceState === 'idle' && '🎤'}
                    {voiceState === 'listening' && '⏹'}
                    {voiceState === 'processing' && '⏳'}
                    {(voiceState === 'speaking' || isSpeaking) && (isPaused ? '▶' : '⏸')}
                </motion.button>

                {/* Error Display */}
                {error && (
                    <div style={{
                        position: 'absolute',
                        bottom: '50px',
                        color: '#e17055',
                        fontSize: '1rem',
                        background: '#fff0f0',
                        padding: '10px 20px',
                        borderRadius: '20px'
                    }}>
                        {error}
                    </div>
                )}
            </motion.div>
        </AnimatePresence>
    );
};

export default VoiceMode;
