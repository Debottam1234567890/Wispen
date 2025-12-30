import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useSessions } from '../../hooks/useSessions';
import { auth } from '../../firebase';
import { API_BASE_URL } from '../../config';

interface SessionTimerProps {
    sessionId: string;
}

const SessionTimer = ({ sessionId }: SessionTimerProps) => {
    const { updateSession } = useSessions();

    // State
    const [seconds, setSeconds] = useState(0);
    const [isIdle, setIsIdle] = useState(false);
    const [isPaused, setIsPaused] = useState(false);

    // Refs for intervals and activity tracking
    const idleTimerRef = useRef<number>(0);
    const lastSyncTimeRef = useRef<number>(0);

    // Constants
    const IDLE_THRESHOLD = 600; // 10 minutes in seconds
    const SYNC_INTERVAL = 30; // Sync every 30 seconds

    // Helpers for time formatting
    const formatTimeForDisplay = (totalSeconds: number) => {
        const h = Math.floor(totalSeconds / 3600);
        const m = Math.floor((totalSeconds % 3600) / 60);
        const s = totalSeconds % 60;

        if (h > 0) return `${h}h ${m}m ${s}s`;
        if (m > 0) return `${m}m ${s}s`;
        return `${s}s`;
    };

    const formatTimeForBackend = (totalSeconds: number) => {
        const h = Math.floor(totalSeconds / 3600);
        const m = Math.floor((totalSeconds % 3600) / 60);
        // We generally store mostly minutes/hours for simple display, 
        // but let's store granular if we can, or just rounded m/h.
        // Let's stick to the "1h 25m" format key the user sees.

        if (h > 0) return `${h}h ${m}m`;
        return `${m}m`;
    };

    // Activity Listener
    useEffect(() => {
        const handleActivity = () => {
            if (isPaused) return; // Don't auto-resume on movement if paused via modal
            idleTimerRef.current = 0; // Reset idle timer
        };

        window.addEventListener('mousemove', handleActivity);
        window.addEventListener('keydown', handleActivity);
        window.addEventListener('click', handleActivity);
        window.addEventListener('scroll', handleActivity);

        return () => {
            window.removeEventListener('mousemove', handleActivity);
            window.removeEventListener('keydown', handleActivity);
            window.removeEventListener('click', handleActivity);
            window.removeEventListener('scroll', handleActivity);
        };
    }, [isPaused]);

    // Main Timer Loop
    useEffect(() => {
        const timer = setInterval(() => {
            if (isPaused) return;

            // Increment idle timer
            idleTimerRef.current += 1;

            // Check if idle
            if (idleTimerRef.current >= IDLE_THRESHOLD) {
                setIsPaused(true);
                setIsIdle(true);
                return;
            }

            // Increment session time
            setSeconds(prev => {
                const newTime = prev + 1;

                // Sync checking
                if (newTime - lastSyncTimeRef.current >= SYNC_INTERVAL) {
                    updateSession(sessionId, { duration: formatTimeForBackend(newTime) });
                    lastSyncTimeRef.current = newTime;
                }

                return newTime;
            });

        }, 1000);

        return () => clearInterval(timer);
    }, [sessionId, isPaused, updateSession]);

    // Handle initial load (maybe fetch current duration if continuing?)
    // For now starts at 0 for "current session" tracking, 
    // or we could fetch the session to get previous time if we want to "continue" counting.
    // User asked "count the time for only one particluar session". 
    // If they revisit an old session, they probably want to ADD to it.
    // But since we don't have the session data loaded here immediately, 
    // we might be overwriting "25m" with "0m" -> "1m" if we start at 0.
    // Ideally we should start at current session duration.
    // But `useSessions` loads ALL sessions. 
    // Let's assume for this iteration we just track "active time in this sitting" 
    // OR we should be careful about overwriting.
    // Actually, `updateSession` takes a formatted string. 
    // If I send "1m", it overwrites "25m". That's bad.

    // To fix: We need to know the initial duration.
    // We fetch the specific session to ensure we have the latest data, 
    // instead of relying solely on the cached list which might be stale or incomplete.

    const [isInitialized, setIsInitialized] = useState(false);

    useEffect(() => {
        const fetchCurrentSession = async () => {
            if (!auth.currentUser) return;
            try {
                const token = await auth.currentUser.getIdToken();
                const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (response.ok) {
                    const sessionData = await response.json();
                    // Parse "1h 20m" or "25m" to seconds
                    const durationStr = sessionData.duration || "0m";
                    const parts = durationStr.split(' ');
                    let totalSec = 0;
                    parts.forEach((p: string) => { // Type annotation added
                        if (p.includes('h')) totalSec += parseInt(p) * 3600;
                        if (p.includes('m')) totalSec += parseInt(p) * 60;
                    });

                    console.log(`[Timer] Initialized with ${totalSec}s from "${durationStr}"`);
                    setSeconds(totalSec);
                    lastSyncTimeRef.current = totalSec;
                    setIsInitialized(true);
                }
            } catch (e) {
                console.error("Failed to fetch session for timer", e);
            }
        };

        if (sessionId) {
            fetchCurrentSession();
        }
    }, [sessionId]);

    // Save on unmount
    useEffect(() => {
        const handleBeforeUnload = () => {
            // Attempt to save synchronously or via beacon if possible, but for now standard fetch
            // Note: fetch might be cancelled on unload, but often works for 'beforeunload' or 'unload' in modern browsers 
            // with keepalive: true
            if (auth.currentUser) {
                auth.currentUser.getIdToken().then(token => {
                    const currentSeconds = seconds; // Capture current state
                    const durationStr = formatTimeForBackend(currentSeconds);
                    console.log(`[Timer] Saving on unmount: ${durationStr}`);

                    fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
                        method: 'PATCH',
                        headers: {
                            'Authorization': `Bearer ${token}`,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ duration: durationStr }),
                        keepalive: true
                    });
                });
            }
        };

        // Component unmount
        return () => {
            if (isInitialized) { // Only save if we actually loaded something to avoid overwriting with 0 if fetch fails
                handleBeforeUnload();
            }
        };
    }, [sessionId, seconds, isInitialized]); // changing seconds triggers this effect re-creation, but return runs before new effect

    const handleResume = () => {
        setIsPaused(false);
        setIsIdle(false);
        idleTimerRef.current = 0;
    };

    if (!sessionId) return null;

    return (
        <>
            {/* Timer Display (Top Right usually, or embedded) */}
            <div style={{
                position: 'fixed',
                top: '80px', // Below header
                right: '25px',
                background: 'white',
                padding: '8px 15px',
                borderRadius: '20px',
                boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                zIndex: 90,
                fontFamily: 'monospace',
                fontSize: '1rem',
                border: '1px solid #eee'
            }}>
                <span style={{ animation: isPaused ? 'none' : 'pulse 2s infinite' }}>🔴</span>
                {formatTimeForDisplay(seconds)}
            </div>

            {/* Idle Popup */}
            <AnimatePresence>
                {isIdle && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        style={{
                            position: 'fixed',
                            top: 0, left: 0, width: '100%', height: '100%',
                            background: 'rgba(0,0,0,0.6)',
                            backdropFilter: 'blur(5px)',
                            zIndex: 1000,
                            display: 'flex', alignItems: 'center', justifyContent: 'center'
                        }}
                    >
                        <motion.div
                            initial={{ scale: 0.9, y: 20 }}
                            animate={{ scale: 1, y: 0 }}
                            exit={{ scale: 0.9, y: 20 }}
                            style={{
                                background: 'white',
                                padding: '40px',
                                borderRadius: '24px',
                                textAlign: 'center',
                                maxWidth: '400px',
                                boxShadow: '0 10px 40px rgba(0,0,0,0.2)'
                            }}
                        >
                            <div style={{ fontSize: '4rem', marginBottom: '20px' }}>🍵</div>
                            <h2 style={{ fontFamily: 'Indie Flower', fontSize: '2rem', margin: '0 0 10px 0' }}>Welcome Back!</h2>
                            <p style={{ color: '#666', marginBottom: '30px' }}>
                                You've been away for a while. Ready to jump back into the flow?
                            </p>
                            <button
                                onClick={handleResume}
                                style={{
                                    background: 'var(--dream-purple, #6C63FF)',
                                    color: 'white',
                                    border: 'none',
                                    padding: '15px 40px',
                                    fontSize: '1.2rem',
                                    borderRadius: '30px',
                                    cursor: 'pointer',
                                    fontFamily: 'Indie Flower',
                                    transition: 'transform 0.2s'
                                }}
                                onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.05)'}
                                onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
                            >
                                Resume Session
                            </button>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            <style>{`
                @keyframes pulse {
                    0% { opacity: 1; }
                    50% { opacity: 0.5; }
                    100% { opacity: 1; }
                }
            `}</style>
        </>
    );
};

export default SessionTimer;
