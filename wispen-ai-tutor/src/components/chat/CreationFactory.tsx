import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import QuizViewer from './viewers/QuizViewer';
import VideoViewer from './viewers/VideoViewer';
import { auth, db } from '../../firebase';
import { collection, onSnapshot } from 'firebase/firestore';
import { API_BASE_URL } from '../../config';

const FOLDERS = [
    { id: 'mindmap', title: 'Mindmaps', count: 3, icon: '🧠', gradient: 'linear-gradient(135deg, #FF9A9E 0%, #FAD0C4 100%)' },
    { id: 'flashcards', title: 'Flashcards', count: 5, icon: '📇', gradient: 'linear-gradient(135deg, #F6D365 0%, #FDA085 100%)' },
    { id: 'quizzes', title: 'Quizzes', count: 4, icon: '❓', gradient: 'linear-gradient(135deg, #A8EDEA 0%, #FED6E3 100%)' },
    { id: 'video', title: 'Videos', count: 1, icon: '🎥', gradient: 'linear-gradient(135deg, #E0C3FC 0%, #8EC5FC 100%)' },
];

const containerVariants = {
    hidden: { opacity: 0 },
    show: {
        opacity: 1,
        transition: {
            staggerChildren: 0.1
        }
    }
};

const itemVariants = {
    hidden: { opacity: 0, x: -20 },
    show: { opacity: 1, x: 0 }
};

interface CreationFactoryProps {
    sessionId?: string;
    refreshKey?: number;
    onOpenMindmap?: (prompt: string) => void;
    onOpenFlashcards?: (cards: any[]) => void;
}

const CreationFactory: React.FC<CreationFactoryProps> = ({ onOpenMindmap, onOpenFlashcards, sessionId, refreshKey }) => {
    const [generatingItem, setGeneratingItem] = useState<string | null>(null);
    const [viewItem, setViewItem] = useState<string | null>(null);

    // Flashcard Prompt State
    const [showPromptModal, setShowPromptModal] = useState(false);
    const [showQuizPromptModal, setShowQuizPromptModal] = useState(false);
    const [showVideoPromptModal, setShowVideoPromptModal] = useState(false);
    const [prompt, setPrompt] = useState("");
    const [videoPrompt, setVideoPrompt] = useState("");
    const [pendingQuizTopic, setPendingQuizTopic] = useState<string | null>(null);
    const [pendingVideoTopic, setPendingVideoTopic] = useState<string | null>(null);
    const [isGenerating, setIsGenerating] = useState(false);

    const [flashcards, setFlashcards] = useState<any[]>([]);
    const [mindmaps, setMindmaps] = useState<any[]>([]);
    const [quizzes, setQuizzes] = useState<any[]>([]);
    const [videos, setVideos] = useState<any[]>([]);
    const [activeQuiz, setActiveQuiz] = useState<any | null>(null);
    const [activeVideo, setActiveVideo] = useState<any | null>(null);
    const [showAllOutput, setShowAllOutput] = useState(false);



    const fetchFromBackend = async (currentUser = auth.currentUser) => {
        if (!sessionId || !currentUser) return;

        try {
            const token = await currentUser.getIdToken();

            // Fetch Flashcards
            const fcRes = await fetch(`${API_BASE_URL}/sessions/${sessionId}/flashcards`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (fcRes.ok) {
                const data = await fcRes.json();
                console.log("CreationFactory: Backend Flashcards Received:", data.length, data);
                setFlashcards(prev => {
                    const merged = [...prev];
                    data.forEach((item: any) => {
                        if (!merged.find(m => m.id === item.id)) merged.push(item);
                    });
                    return merged.sort((a, b) => {
                        const tA = a.timestamp ? new Date(a.timestamp).getTime() : 0;
                        const tB = b.timestamp ? new Date(b.timestamp).getTime() : 0;
                        if (tA === tB) return 0;
                        return tB - tA; // Sort by newest first
                    });
                });
            }

            // Fetch Mindmaps
            const mmRes = await fetch(`${API_BASE_URL}/sessions/${sessionId}/mindmaps`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (mmRes.ok) {
                const data = await mmRes.json();
                console.log("CreationFactory: Backend Mindmaps Received:", data.length);
                setMindmaps(prev => {
                    const merged = [...prev];
                    data.forEach((item: any) => {
                        if (!merged.find(m => m.id === item.id)) merged.push(item);
                    });
                    return merged.sort((a, b) => {
                        const tA = a.timestamp ? new Date(a.timestamp).getTime() : 0;
                        const tB = b.timestamp ? new Date(b.timestamp).getTime() : 0;
                        if (tA === tB) return 0;
                        return tB - tA;
                    });
                });
            }
            // Fetch Global Flashcards (fallback/legacy)
            const globalFcRes = await fetch(`${API_BASE_URL}/flashcards`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (globalFcRes.ok) {
                const data = await globalFcRes.json();
                console.log("CreationFactory: Global Backend Flashcards:", data.length);
                setFlashcards(prev => {
                    const merged = [...prev];
                    data.forEach((item: any) => {
                        if (!merged.find(m => m.id === item.id)) merged.push(item);
                    });
                    return merged.sort((a, b) => {
                        const tA = a.timestamp ? new Date(a.timestamp).getTime() : 0;
                        const tB = b.timestamp ? new Date(b.timestamp).getTime() : 0;
                        return tB - tA;
                    });
                });
            }

            // Fetch Quizzes
            const qRes = await fetch(`${API_BASE_URL}/sessions/${sessionId}/quizzes`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (qRes.ok) {
                const data = await qRes.json();
                console.log("CreationFactory: Backend Quizzes Received:", data.length);
                setQuizzes(prev => {
                    const merged = [...prev];
                    data.forEach((item: any) => {
                        if (!merged.find(m => m.id === item.id)) merged.push(item);
                    });
                    return merged.sort((a: any, b: any) => {
                        const tA = a.timestamp ? new Date(a.timestamp).getTime() : 0;
                        const tB = b.timestamp ? new Date(b.timestamp).getTime() : 0;
                        return tB - tA;
                    });
                });
            }

            // Fetch Videos
            const vRes = await fetch(`${API_BASE_URL}/sessions/${sessionId}/videos`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (vRes.ok) {
                const data = await vRes.json();
                console.log("CreationFactory: Backend Videos Received:", data.length);
                setVideos(prev => {
                    const merged = [...prev];
                    data.forEach((item: any) => {
                        if (!merged.find(m => m.id === item.id)) merged.push(item);
                    });
                    return merged.sort((a, b) => {
                        const tA = a.timestamp ? new Date(a.timestamp).getTime() : 0;
                        const tB = b.timestamp ? new Date(b.timestamp).getTime() : 0;
                        return tB - tA;
                    });
                });
            }
        } catch (err) {
            console.error("CreationFactory: Backend fetch failed:", err);
        }
    };

    useEffect(() => {
        if (!sessionId) return;

        // Reset state on session change to avoid stale data
        setFlashcards([]);
        setMindmaps([]);
        setQuizzes([]);
        setVideos([]);

        let unsubFC: (() => void) | null = null;
        let unsubGlobalFC: (() => void) | null = null;
        let unsubMM: (() => void) | null = null;
        let unsubQ: (() => void) | null = null;
        let unsubGlobalQ: (() => void) | null = null;
        let unsubV: (() => void) | null = null;

        const unsubscribeAuth = auth.onAuthStateChanged((user) => {
            if (!user) {
                if (unsubFC) unsubFC();
                if (unsubMM) unsubMM();
                return;
            }

            // 1. Fetch initially from backend once auth is ready
            fetchFromBackend(user);

            const uid = user.uid;

            // 2. Setup real-time listeners for live updates
            const fcRef = collection(db, 'users', uid, 'sessions', sessionId, 'flashcards');
            unsubFC = onSnapshot(fcRef, (snapshot) => {
                const items = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
                console.log("CreationFactory: Firestore Flashcards Updated:", items.length, items);
                setFlashcards(prev => {
                    const map = new Map();
                    // Merge previous and new items, newest items from snapshot overwrite same-id previous items
                    [...prev, ...items].forEach(item => map.set(item.id, item));
                    return Array.from(map.values()).sort((a: any, b: any) => {
                        const tA = a.timestamp ? new Date(a.timestamp).getTime() : 0;
                        const tB = b.timestamp ? new Date(b.timestamp).getTime() : 0;
                        return tB - tA;
                    });
                });
            }, (err) => {
                if (err.code === 'permission-denied') {
                    console.warn("CreationFactory: Firestore FC denied (using backend fallback)");
                } else {
                    console.error("CreationFactory: Firestore FC error:", err);
                }
            });

            // 3. Global Flashcards Listener
            const globalFcRef = collection(db, 'users', uid, 'flashcards');
            unsubGlobalFC = onSnapshot(globalFcRef, (snapshot) => {
                const items = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
                console.log("CreationFactory: Global Flashcards Updated:", items.length);
                setFlashcards(prev => {
                    const map = new Map();
                    [...prev, ...items].forEach(item => map.set(item.id, item));
                    return Array.from(map.values()).sort((a: any, b: any) => {
                        const tA = a.timestamp ? new Date(a.timestamp).getTime() : 0;
                        const tB = b.timestamp ? new Date(b.timestamp).getTime() : 0;
                        return tB - tA;
                    });
                });
            }, (err) => {
                if (err.code === 'permission-denied') {
                    console.warn("CreationFactory: Global FC denied (using backend fallback)");
                } else {
                    console.error("CreationFactory: Global FC error:", err);
                }
            });

            // Listener for Mindmaps
            const mmRef = collection(db, 'users', uid, 'sessions', sessionId, 'mindmaps');
            unsubMM = onSnapshot(mmRef, (snapshot) => {
                const items = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
                console.log("CreationFactory: Firestore Mindmaps Updated:", items.length);
                setMindmaps(prev => {
                    const map = new Map();
                    [...prev, ...items].forEach(item => map.set(item.id, item));
                    return Array.from(map.values()).sort((a: any, b: any) => {
                        const tA = a.timestamp ? new Date(a.timestamp).getTime() : 0;
                        const tB = b.timestamp ? new Date(b.timestamp).getTime() : 0;
                        return tB - tA;
                    });
                });
            }, (err) => {
                if (err.code === 'permission-denied') {
                    console.warn("CreationFactory: Firestore MM denied (using backend fallback)");
                } else {
                    console.error("CreationFactory: Firestore MM error:", err);
                }
            });

            // 4. Global Quizzes Listener
            const globalQRef = collection(db, 'users', uid, 'quizzes');
            unsubGlobalQ = onSnapshot(globalQRef, (snapshot) => {
                const items = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
                console.log("CreationFactory: Global Quizzes Updated:", items.length);
                setQuizzes(prev => {
                    const map = new Map();
                    [...prev, ...items].forEach(item => map.set(item.id, item));
                    return Array.from(map.values()).sort((a: any, b: any) => {
                        const tA = a.timestamp ? new Date(a.timestamp).getTime() : 0;
                        const tB = b.timestamp ? new Date(b.timestamp).getTime() : 0;
                        return tB - tA;
                    });
                });
            }, (err) => {
                if (err.code === 'permission-denied') {
                    console.warn("CreationFactory: Global Quiz denied (using backend fallback)");
                } else {
                    console.error("CreationFactory: Global Quiz error:", err);
                }
            });

            // Session Quizzes Listener
            if (sessionId && sessionId !== 'undefined') {
                const qRef = collection(db, 'users', uid, 'sessions', sessionId, 'quizzes');
                unsubQ = onSnapshot(qRef, (snapshot) => {
                    const items = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
                    console.log("CreationFactory: Session Quizzes Updated:", items.length);

                    setQuizzes(prev => {
                        const map = new Map();
                        [...prev, ...items].forEach(item => map.set(item.id, item));
                        const merged = Array.from(map.values()).sort((a: any, b: any) => {
                            const tA = a.timestamp ? new Date(a.timestamp).getTime() : 0;
                            const tB = b.timestamp ? new Date(b.timestamp).getTime() : 0;
                            return tB - tA;
                        });
                        return merged;
                    });
                }, (err) => {
                    if (err.code === 'permission-denied') {
                        console.warn("CreationFactory: Session Quiz denied (using backend fallback)");
                    } else {
                        console.error("CreationFactory: Session Quiz error:", err);
                    }
                });
            }

            // Session Videos Listener
            if (sessionId && sessionId !== 'undefined') {
                const vRef = collection(db, 'users', uid, 'sessions', sessionId, 'videos');
                unsubV = onSnapshot(vRef, (snapshot) => {
                    const items = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
                    console.log("CreationFactory: Session Videos Updated:", items.length);
                    setVideos(prev => {
                        const map = new Map();
                        [...prev, ...items].forEach(item => map.set(item.id, item));
                        return Array.from(map.values()).sort((a: any, b: any) => {
                            const tA = a.timestamp ? new Date(a.timestamp).getTime() : 0;
                            const tB = b.timestamp ? new Date(b.timestamp).getTime() : 0;
                            return tB - tA;
                        });
                    });
                }, (err) => {
                    if (err.code === 'permission-denied') {
                        console.warn("CreationFactory: Session Video denied (using backend fallback)");
                    } else {
                        console.error("CreationFactory: Session Video error:", err);
                    }
                });
            }
        });

        return () => {
            unsubscribeAuth();
            if (unsubFC) unsubFC();
            if (unsubGlobalFC) unsubGlobalFC();
            if (unsubMM) unsubMM();
            if (unsubQ) unsubQ();
            if (unsubGlobalQ) unsubGlobalQ();
            if (unsubV) unsubV();
        };
    }, [sessionId]);
    // Refetch when refreshKey changes
    useEffect(() => {
        fetchFromBackend();
    }, [refreshKey]);

    useEffect(() => {
        if (pendingQuizTopic && quizzes.length > 0) {
            const latestQuiz = quizzes[0];
            const quizTime = new Date(latestQuiz.timestamp).getTime();
            const now = Date.now();

            if (latestQuiz.title.toLowerCase() === pendingQuizTopic.toLowerCase() && (now - quizTime) < 120000) {
                console.log("CreationFactory: Found pending quiz, auto-opening!", latestQuiz.id);
                setActiveQuiz(latestQuiz);
                setViewItem('quizzes');
                setPendingQuizTopic(null);
                setIsGenerating(false);
            }
        }
    }, [quizzes, pendingQuizTopic]);

    // Auto-open video when it appears
    useEffect(() => {
        if (pendingVideoTopic && videos.length > 0) {
            const latestVideo = videos[0];
            const videoTime = latestVideo.timestamp ? new Date(latestVideo.timestamp).getTime() : Date.now();
            const now = Date.now();

            if (latestVideo.topic?.toLowerCase() === pendingVideoTopic.toLowerCase() && (now - videoTime) < 120000) {
                console.log("CreationFactory: Found pending video, auto-opening!", latestVideo.id);
                setActiveVideo(latestVideo);
                setViewItem('video');
                setPendingVideoTopic(null);
                setIsGenerating(false);
            }
        }
    }, [videos, pendingVideoTopic]);

    const handleFolderClick = (id: string) => {
        console.log("Folder clicked in Factory:", id);
        if (id === 'mindmap') {
            if (onOpenMindmap) {
                onOpenMindmap("");
            }
            return;
        }

        if (id === 'flashcards') {
            setShowPromptModal(true);
            return;
        }

        if (id === 'quizzes') {
            setShowQuizPromptModal(true);
            return;
        }


        if (id === 'video') {
            setShowVideoPromptModal(true);
            return;
        }

        setGeneratingItem(id);
        setTimeout(() => {
            setGeneratingItem(null);
            setViewItem(id);
        }, 1500);
    };

    const handleGenerateFlashcards = async () => {
        if (!prompt.trim()) return;

        setIsGenerating(true);
        setGeneratingItem('flashcards');
        setShowPromptModal(false);

        try {
            const user = auth.currentUser;
            if (!user) throw new Error("Not authenticated");

            const token = await user.getIdToken();
            const response = await fetch(`${API_BASE_URL}/flashcards/generate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    topic: prompt,
                    sessionId: sessionId,
                    content: ""
                })
            });

            if (response.ok) {
                console.log("Flashcard generation started...");
            } else {
                console.error("Failed to start flashcard generation");
            }
        } catch (err) {
            console.error("Error generating flashcards:", err);
        } finally {
            setTimeout(() => {
                setGeneratingItem(null);
                setIsGenerating(false);
                setPrompt("");
            }, 2000);
        }
    };

    const handleGenerateQuizzes = async () => {
        if (!prompt.trim()) return;

        setIsGenerating(true);
        setGeneratingItem('quizzes');
        setPendingQuizTopic(prompt);
        setShowQuizPromptModal(false);

        try {
            const user = auth.currentUser;
            if (!user) throw new Error("Not authenticated");

            const token = await user.getIdToken();
            const response = await fetch(`${API_BASE_URL}/quizzes/generate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    topic: prompt,
                    sessionId: sessionId,
                    content: ""
                })
            });

            if (response.ok) {
                console.log("Quiz generation started...");
            } else {
                console.error("Failed to start quiz generation");
            }
        } catch (err) {
            console.error("Error generating quiz:", err);
        } finally {
            setTimeout(() => {
                setGeneratingItem(null);
                setIsGenerating(false);
                setPrompt("");
            }, 2000);
        }
    };

    const handleGenerateVideo = async () => {
        if (!videoPrompt.trim()) return;

        setIsGenerating(true);
        setGeneratingItem('video');
        setPendingVideoTopic(videoPrompt);
        setShowVideoPromptModal(false);

        try {
            const user = auth.currentUser;
            if (!user) throw new Error("Not authenticated");

            const token = await user.getIdToken();
            const response = await fetch(`${API_BASE_URL}/videos/generate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    topic: videoPrompt,
                    sessionId: sessionId
                })
            });

            if (response.ok) {
                console.log("Video generation started in background...");
            } else {
                console.error("Failed to start video generation");
            }
        } catch (err) {
            console.error("Error generating video:", err);
        } finally {
            setTimeout(() => {
                setGeneratingItem(null);
                setIsGenerating(false);
                setVideoPrompt("");
            }, 2000);
        }
    };

    const handleCloseViewer = () => {
        setViewItem(null);
    };

    return (
        <>
            <AnimatePresence>
                {/* Generating Overlay */}
                {generatingItem && (
                    <motion.div
                        key="generating-overlay"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        style={{
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            width: '100%',
                            height: '100%',
                            background: 'rgba(255,255,255,0.95)',
                            zIndex: 50,
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            justifyContent: 'center',
                            backdropFilter: 'blur(5px)'
                        }}
                    >
                        <motion.div
                            animate={{ rotate: 360 }}
                            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                            style={{ fontSize: '3rem', marginBottom: '20px' }}
                        >
                            ⚙️
                        </motion.div>
                        <h3 style={{ fontFamily: '"Indie Flower", cursive', fontSize: '1.8rem', color: '#1f2937' }}>
                            Generating {FOLDERS.find(f => f.id === generatingItem)?.title}...
                        </h3>
                    </motion.div>
                )}

                {/* Viewers */}
                {viewItem === 'quizzes' && (
                    <QuizViewer
                        key="quiz-viewer"
                        onClose={handleCloseViewer}
                        quizData={activeQuiz}
                    />
                )}
                {viewItem === 'video' && activeVideo && (
                    <VideoViewer
                        key="video-viewer"
                        video={activeVideo}
                        onClose={handleCloseViewer}
                    />
                )}


                {/* Flashcard Prompt Modal */}
                {showPromptModal && (
                    <motion.div
                        key="flashcard-prompt-overlay"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        style={{
                            position: 'fixed',
                            inset: 0,
                            backgroundColor: 'rgba(0, 0, 0, 0.4)',
                            backdropFilter: 'blur(4px)',
                            zIndex: 2000,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            padding: '16px'
                        }}
                    >
                        <motion.div
                            initial={{ scale: 0.9, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.9, opacity: 0 }}
                            style={{
                                width: '100%',
                                maxWidth: '512px',
                                backgroundColor: 'white',
                                borderRadius: '24px',
                                padding: '32px',
                                boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
                                display: 'flex',
                                flexDirection: 'column',
                                fontFamily: '"Outfit", sans-serif'
                            }}
                        >
                            <h2 style={{ fontSize: '1.875rem', fontWeight: 700, color: '#1f2937', marginBottom: '12px', marginTop: 0 }}>Flashcard Prompt</h2>
                            <p style={{ color: '#6b7280', marginBottom: '24px', fontSize: '1rem' }}>Enter a topic to generate a set of study flashcards from your sources.</p>

                            <input
                                type="text"
                                value={prompt}
                                onChange={(e) => setPrompt(e.target.value)}
                                placeholder="e.g. Key terms of Photosynthesis, French Revolution..."
                                style={{
                                    width: '100%',
                                    padding: '16px',
                                    backgroundColor: '#f9fafb',
                                    border: '1px solid #f3f4f6',
                                    borderRadius: '16px',
                                    marginBottom: '24px',
                                    outline: 'none',
                                    fontSize: '1.125rem',
                                    fontFamily: '"Outfit", sans-serif',
                                    boxSizing: 'border-box'
                                }}
                                onKeyDown={(e) => e.key === 'Enter' && !isGenerating && prompt.trim() && handleGenerateFlashcards()}
                            />

                            <div style={{ display: 'flex', gap: '16px' }}>
                                <button
                                    onClick={() => { setShowPromptModal(false); setPrompt(""); }}
                                    style={{
                                        flex: 1,
                                        padding: '16px',
                                        color: '#6b7280',
                                        fontWeight: 600,
                                        border: 'none',
                                        background: 'none',
                                        cursor: 'pointer',
                                        borderRadius: '16px',
                                        transition: 'all 0.2s',
                                        fontFamily: '"Outfit", sans-serif'
                                    }}
                                    onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#f9fafb'}
                                    onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleGenerateFlashcards}
                                    disabled={!prompt.trim() || isGenerating}
                                    style={{
                                        flex: 1,
                                        padding: '16px',
                                        backgroundColor: (prompt.trim() && !isGenerating) ? '#2563eb' : '#e5e7eb',
                                        color: 'white',
                                        fontWeight: 600,
                                        borderRadius: '16px',
                                        border: 'none',
                                        cursor: (prompt.trim() && !isGenerating) ? 'pointer' : 'default',
                                        boxShadow: (prompt.trim() && !isGenerating) ? '0 10px 15px -3px rgba(37, 99, 235, 0.2)' : 'none',
                                        transition: 'all 0.2s',
                                        fontFamily: '"Outfit", sans-serif',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        gap: '8px'
                                    }}
                                    onMouseOver={(e) => {
                                        if (prompt.trim() && !isGenerating) e.currentTarget.style.backgroundColor = '#1d4ed8';
                                    }}
                                    onMouseOut={(e) => {
                                        if (prompt.trim() && !isGenerating) e.currentTarget.style.backgroundColor = '#2563eb';
                                    }}
                                >
                                    {isGenerating ? (
                                        <>
                                            <motion.div
                                                animate={{ rotate: 360 }}
                                                transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                                                style={{ width: '16px', height: '16px', border: '2px solid white', borderTopColor: 'transparent', borderRadius: '50%' }}
                                            />
                                            Working...
                                        </>
                                    ) : (
                                        "Generate Cards"
                                    )}
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}

                {/* Quiz Prompt Modal */}
                {showQuizPromptModal && (
                    <motion.div
                        key="quiz-prompt-overlay"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        style={{
                            position: 'fixed',
                            inset: 0,
                            backgroundColor: 'rgba(0, 0, 0, 0.4)',
                            backdropFilter: 'blur(4px)',
                            zIndex: 2000,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            padding: '16px'
                        }}
                    >
                        <motion.div
                            initial={{ scale: 0.9, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.9, opacity: 0 }}
                            style={{
                                width: '100%',
                                maxWidth: '512px',
                                backgroundColor: 'white',
                                borderRadius: '24px',
                                padding: '32px',
                                boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
                                display: 'flex',
                                flexDirection: 'column',
                                fontFamily: '"Outfit", sans-serif'
                            }}
                        >
                            <h2 style={{ fontSize: '1.875rem', fontWeight: 700, color: '#1f2937', marginBottom: '12px', marginTop: 0 }}>Quiz Prompt</h2>
                            <p style={{ color: '#6b7280', marginBottom: '24px', fontSize: '1rem' }}>Enter a topic to generate an interactive quiz from your sources.</p>

                            <input
                                type="text"
                                value={prompt}
                                onChange={(e) => setPrompt(e.target.value)}
                                placeholder="e.g. Calculus Basics, Periodic Table..."
                                style={{
                                    width: '100%',
                                    padding: '16px',
                                    backgroundColor: '#f9fafb',
                                    border: '1px solid #f3f4f6',
                                    borderRadius: '16px',
                                    marginBottom: '24px',
                                    outline: 'none',
                                    fontSize: '1.125rem',
                                    fontFamily: '"Outfit", sans-serif',
                                    boxSizing: 'border-box'
                                }}
                                onKeyDown={(e) => e.key === 'Enter' && !isGenerating && prompt.trim() && handleGenerateQuizzes()}
                            />

                            <div style={{ display: 'flex', gap: '16px' }}>
                                <button
                                    onClick={() => { setShowQuizPromptModal(false); setPrompt(""); }}
                                    style={{
                                        flex: 1,
                                        padding: '16px',
                                        color: '#6b7280',
                                        fontWeight: 600,
                                        border: 'none',
                                        background: 'none',
                                        cursor: 'pointer',
                                        borderRadius: '16px',
                                        transition: 'all 0.2s',
                                        fontFamily: '"Outfit", sans-serif'
                                    }}
                                    onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#f9fafb'}
                                    onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleGenerateQuizzes}
                                    disabled={!prompt.trim() || isGenerating}
                                    style={{
                                        flex: 1,
                                        padding: '16px',
                                        backgroundColor: (prompt.trim() && !isGenerating) ? '#3b82f6' : '#e5e7eb',
                                        color: 'white',
                                        fontWeight: 600,
                                        borderRadius: '16px',
                                        border: 'none',
                                        cursor: (prompt.trim() && !isGenerating) ? 'pointer' : 'default',
                                        boxShadow: (prompt.trim() && !isGenerating) ? '0 10px 15px -3px rgba(59, 130, 246, 0.2)' : 'none',
                                        transition: 'all 0.2s',
                                        fontFamily: '"Outfit", sans-serif',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        gap: '8px'
                                    }}
                                >
                                    {isGenerating ? "Working..." : "Generate Quiz"}
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}

                {/* Video Prompt Modal */}
                {showVideoPromptModal && (
                    <motion.div
                        key="video-prompt-overlay"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        style={{
                            position: 'fixed',
                            inset: 0,
                            backgroundColor: 'rgba(255, 255, 255, 0.4)',
                            backdropFilter: 'blur(20px)',
                            zIndex: 2000,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            padding: '16px'
                        }}
                    >
                        <motion.div
                            initial={{ scale: 0.9, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.9, opacity: 0 }}
                            style={{
                                width: '100%',
                                maxWidth: '512px',
                                backgroundColor: 'rgba(255, 255, 255, 0.9)',
                                borderRadius: '32px',
                                padding: '40px',
                                boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.1)',
                                display: 'flex',
                                flexDirection: 'column',
                                fontFamily: '"Outfit", sans-serif',
                                border: '1px solid rgba(255, 255, 255, 0.5)'
                            }}
                        >
                            <h2 style={{ fontSize: '2.2rem', fontWeight: 700, color: '#111827', marginBottom: '16px', marginTop: 0, textAlign: 'center' }}>🎬 Create Video</h2>
                            <p style={{ color: '#4b5563', marginBottom: '32px', fontSize: '1.1rem', textAlign: 'center', lineHeight: 1.5 }}>
                                Describe the educational process you want to visualize. We'll generate a custom video for you.
                            </p>

                            <textarea
                                value={videoPrompt}
                                onChange={(e) => setVideoPrompt(e.target.value)}
                                placeholder="e.g. Explaining the phases of Mitosis with labels..."
                                style={{
                                    width: '100%',
                                    padding: '20px',
                                    backgroundColor: 'white',
                                    border: '2px solid #f3f4f6',
                                    borderRadius: '20px',
                                    marginBottom: '32px',
                                    outline: 'none',
                                    fontSize: '1.1rem',
                                    fontFamily: '"Outfit", sans-serif',
                                    boxSizing: 'border-box',
                                    minHeight: '120px',
                                    resize: 'none',
                                    transition: 'border-color 0.2s'
                                }}
                                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && !isGenerating && videoPrompt.trim() && handleGenerateVideo()}
                            />

                            <div style={{ display: 'flex', gap: '16px' }}>
                                <button
                                    onClick={() => { setShowVideoPromptModal(false); setVideoPrompt(""); }}
                                    style={{
                                        flex: 1,
                                        padding: '18px',
                                        color: '#6b7280',
                                        fontWeight: 600,
                                        border: 'none',
                                        background: '#f3f4f6',
                                        cursor: 'pointer',
                                        borderRadius: '18px',
                                        transition: 'all 0.2s',
                                        fontFamily: '"Outfit", sans-serif'
                                    }}
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleGenerateVideo}
                                    disabled={!videoPrompt.trim() || isGenerating}
                                    style={{
                                        flex: 2,
                                        padding: '18px',
                                        backgroundColor: (videoPrompt.trim() && !isGenerating) ? '#6366f1' : '#e5e7eb',
                                        color: 'white',
                                        fontWeight: 600,
                                        borderRadius: '18px',
                                        border: 'none',
                                        cursor: (videoPrompt.trim() && !isGenerating) ? 'pointer' : 'default',
                                        transition: 'all 0.2s',
                                        fontFamily: '"Outfit", sans-serif',
                                        fontSize: '1.1rem'
                                    }}
                                >
                                    {isGenerating ? "Generating..." : "Generate Video"}
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}

                {/* All Output Overlay */}
                {showAllOutput && (
                    <motion.div
                        key="all-output"
                        initial={{ opacity: 0, x: 50, scale: 0.95 }}
                        animate={{ opacity: 1, x: 0, scale: 1 }}
                        exit={{ opacity: 0, x: 50, scale: 0.95 }}
                        style={{
                            position: 'absolute',
                            top: '0',
                            left: '0',
                            width: '100%',
                            height: '100%',
                            background: 'rgba(255, 255, 255, 0.98)',
                            backdropFilter: 'blur(10px)',
                            zIndex: 100,
                            display: 'flex',
                            flexDirection: 'column',
                            borderRadius: '20px',
                            padding: '24px',
                            boxShadow: '0 20px 50px rgba(0,0,0,0.1)'
                        }}
                    >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                            <h2 style={{ color: '#111827', fontFamily: '"Indie Flower", cursive', margin: 0, fontSize: '1.8rem' }}>
                                All Your Creations 📦
                            </h2>
                            <button
                                onClick={() => setShowAllOutput(false)}
                                style={{
                                    border: 'none',
                                    background: '#f3f4f6',
                                    width: '32px',
                                    height: '32px',
                                    borderRadius: '50%',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    cursor: 'pointer',
                                    color: '#6b7280'
                                }}
                            >✕</button>
                        </div>

                        <div style={{ flex: 1, overflowY: 'auto', paddingRight: '8px' }}>
                            {mindmaps.length > 0 && (
                                <div style={{ marginBottom: '24px' }}>
                                    <h4 style={{ fontSize: '0.8rem', color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px', fontFamily: '"Outfit", sans-serif' }}>Mindmaps</h4>
                                    {mindmaps.map(mm => {
                                        const displayTitle = mm.title || (mm.root_id && mm.root_id !== 'root' ? mm.root_id : "Mindmap Concepts");
                                        return (
                                            <motion.div
                                                key={mm.id}
                                                whileHover={{ x: 5, backgroundColor: '#f9fafb' }}
                                                onClick={() => { if (onOpenMindmap) onOpenMindmap(mm.id); setShowAllOutput(false); }}
                                                style={{ padding: '12px', borderRadius: '12px', cursor: 'pointer', border: '1px solid #eee', marginBottom: '8px', background: 'white' }}
                                            >
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                                    <span style={{ fontSize: '1.2rem' }}>🧠</span>
                                                    <div>
                                                        <div style={{ fontWeight: 600, color: '#111827', fontSize: '0.95rem' }}>{displayTitle}</div>
                                                        <div style={{ fontSize: '0.75rem', color: '#9ca3af' }}>{new Date(mm.timestamp).toLocaleDateString()}</div>
                                                    </div>
                                                </div>
                                            </motion.div>
                                        );
                                    })}
                                </div>
                            )}

                            {flashcards.length > 0 && (
                                <div style={{ marginBottom: '24px' }}>
                                    <h4 style={{ fontSize: '0.8rem', color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px', fontFamily: '"Outfit", sans-serif' }}>Flashcards</h4>
                                    {flashcards.map(fc => (
                                        <motion.div
                                            key={fc.id}
                                            whileHover={{ x: 5, backgroundColor: '#f9fafb' }}
                                            onClick={() => {
                                                if (onOpenFlashcards) onOpenFlashcards(fc.cards || []);
                                                setShowAllOutput(false);
                                            }}
                                            style={{ padding: '12px', borderRadius: '12px', cursor: 'pointer', border: '1px solid #eee', marginBottom: '8px', background: 'white' }}
                                        >
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                                <span style={{ fontSize: '1.2rem' }}>📇</span>
                                                <div>
                                                    <div style={{ fontWeight: 600, color: '#111827', fontSize: '0.95rem' }}>{fc.title || "Subject Flashcards"}</div>
                                                    <div style={{ fontSize: '0.75rem', color: '#9ca3af' }}>{fc.cards?.length || 0} cards • {new Date(fc.timestamp).toLocaleDateString()}</div>
                                                </div>
                                            </div>
                                        </motion.div>
                                    ))}
                                </div>
                            )}

                            {quizzes.length > 0 && (
                                <div style={{ marginBottom: '24px' }}>
                                    <h4 style={{ fontSize: '0.8rem', color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px', fontFamily: '"Outfit", sans-serif' }}>Quizzes</h4>
                                    {quizzes.map(quiz => (
                                        <motion.div
                                            key={quiz.id}
                                            whileHover={{ x: 5, backgroundColor: '#f9fafb' }}
                                            onClick={() => {
                                                setActiveQuiz(quiz);
                                                setViewItem('quizzes');
                                                setShowAllOutput(false);
                                            }}
                                            style={{ padding: '12px', borderRadius: '12px', cursor: 'pointer', border: '1px solid #eee', marginBottom: '8px', background: 'white' }}
                                        >
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                                <span style={{ fontSize: '1.2rem' }}>❓</span>
                                                <div>
                                                    <div style={{ fontWeight: 600, color: '#111827', fontSize: '0.95rem' }}>{quiz.title || "Subject Quiz"}</div>
                                                    <div style={{ fontSize: '0.75rem', color: '#9ca3af' }}>{quiz.questions?.length || 0} questions • {new Date(quiz.timestamp).toLocaleDateString()}</div>
                                                </div>
                                            </div>
                                        </motion.div>
                                    ))}
                                </div>
                            )}

                            {videos.length > 0 && (
                                <div style={{ marginBottom: '24px' }}>
                                    <h4 style={{ fontSize: '0.8rem', color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px', fontFamily: '"Outfit", sans-serif' }}>Videos</h4>
                                    {videos.map(video => (
                                        <motion.div
                                            key={video.id}
                                            whileHover={{ x: 5, backgroundColor: '#f9fafb' }}
                                            onClick={() => {
                                                // Play in-app
                                                setActiveVideo(video);
                                                setViewItem('video');
                                                setShowAllOutput(false);
                                            }}
                                            style={{
                                                padding: '12px',
                                                borderRadius: '12px',
                                                cursor: 'pointer',
                                                border: '1px solid #eee',
                                                marginBottom: '8px',
                                                background: 'white',
                                                display: 'flex',
                                                alignItems: 'center',
                                                justifyContent: 'space-between'
                                            }}
                                        >
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                                <span style={{ fontSize: '1.2rem' }}>🎬</span>
                                                <div>
                                                    <div style={{ fontWeight: 600, color: '#111827', fontSize: '0.95rem' }}>{video.title || "Subject Video"}</div>
                                                    <div style={{ fontSize: '0.75rem', color: '#9ca3af' }}>{video.steps?.length || 0} steps • {video.timestamp ? new Date(video.timestamp).toLocaleDateString() : 'Just now'}</div>
                                                </div>
                                            </div>
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    const videoUrl = video.videoUrl || video.video_url || video.url || video.fileUrl;
                                                    if (videoUrl) {
                                                        const fullUrl = videoUrl.startsWith('http') ? videoUrl : `${API_BASE_URL}${videoUrl}`;
                                                        window.open(fullUrl, '_blank');
                                                    }
                                                }}
                                                title="Download Video"
                                                style={{
                                                    background: 'none',
                                                    border: 'none',
                                                    cursor: 'pointer',
                                                    fontSize: '1.1rem',
                                                    padding: '8px',
                                                    borderRadius: '50%',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'center',
                                                    color: '#6b7280'
                                                }}
                                                onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#f3f4f6'}
                                                onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                                            >
                                                📥
                                            </button>
                                        </motion.div>
                                    ))}
                                </div>
                            )}

                            {mindmaps.length === 0 && flashcards.length === 0 && quizzes.length === 0 && videos.length === 0 && (
                                <div style={{ textAlign: 'center', padding: '40px', color: '#9ca3af' }}>
                                    <div style={{ fontSize: '3rem', marginBottom: '10px' }}>🏜️</div>
                                    <p style={{ fontFamily: '"Indie Flower", cursive', fontSize: '1.2rem' }}>No creations yet...</p>
                                </div>
                            )}
                        </div>
                    </motion.div>
                )}

            </AnimatePresence>

            <motion.div
                className="realm-card factory"
                style={{
                    width: '100%',
                    height: '100%',
                    background: 'rgba(255, 255, 255, 0.4)',
                    backdropFilter: 'blur(10px)',
                    borderRadius: '20px',
                    border: '1px solid rgba(255, 255, 255, 0.6)',
                    padding: '20px',
                    display: 'flex',
                    flexDirection: 'column',
                    boxShadow: '0 10px 30px rgba(0, 0, 0, 0.05)'
                }}
                initial={{ opacity: 0, x: 50 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.8 }}
                whileHover={{ boxShadow: '0 15px 40px rgba(0, 0, 0, 0.08)' }}
            >
                <h2 style={{ color: '#111827', fontFamily: '"Indie Flower", cursive', marginTop: 0, display: 'flex', alignItems: 'center', gap: '10px', fontSize: '2rem', marginBottom: '20px' }}>
                    <span style={{ fontSize: '2rem' }}>🏭</span> Creation Factory
                </h2>

                <motion.div
                    variants={containerVariants}
                    initial="hidden"
                    animate="show"
                    style={{ flex: 1, overflowY: 'auto', display: 'grid', gridTemplateColumns: '1fr', gap: '12px', alignContent: 'start', paddingRight: '5px' }}
                >
                    {FOLDERS.map((folder) => {
                        const count = folder.id === 'mindmap' ? mindmaps.length :
                            folder.id === 'flashcards' ? flashcards.length :
                                folder.id === 'quizzes' ? quizzes.length :
                                    folder.id === 'video' ? videos.length : 0;

                        return (
                            <motion.div
                                key={folder.id}
                                variants={itemVariants}
                                onClick={() => handleFolderClick(folder.id)}
                                style={{
                                    background: 'rgba(255,255,255,0.7)',
                                    borderRadius: '14px',
                                    padding: '12px 16px',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    border: '1px solid rgba(255,255,255,0.8)',
                                    boxShadow: '0 2px 10px rgba(0,0,0,0.02)',
                                    transition: 'all 0.2s',
                                    backdropFilter: 'blur(4px)'
                                }}
                                whileHover={{ scale: 1.02, backgroundColor: 'rgba(255,255,255,0.95)', boxShadow: '0 8px 20px rgba(0,0,0,0.08)' }}
                                whileTap={{ scale: 0.98 }}
                            >
                                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: '#374151' }}>
                                    <div style={{
                                        background: folder.gradient,
                                        width: '36px',
                                        height: '36px',
                                        borderRadius: '10px',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        fontSize: '1.2rem',
                                        boxShadow: '0 2px 5px rgba(0,0,0,0.1)'
                                    }}>
                                        {folder.icon}
                                    </div>
                                    <span style={{ fontSize: '1rem', fontFamily: '"Outfit", sans-serif', fontWeight: 500 }}>{folder.title}</span>
                                </div>
                                <div style={{
                                    background: '#f3f4f6',
                                    padding: '4px 10px',
                                    borderRadius: '10px',
                                    fontSize: '0.85rem',
                                    color: '#6b7280',
                                    fontWeight: 700
                                }}>
                                    {count}
                                </div>
                            </motion.div>
                        );
                    })}
                </motion.div>

                <motion.button
                    whileHover={{ scale: 1.02, backgroundColor: '#f9fafb' }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => setShowAllOutput(true)}
                    style={{
                        marginTop: '20px',
                        background: 'white',
                        border: '1px solid #e5e7eb',
                        color: '#374151',
                        padding: '14px',
                        borderRadius: '16px',
                        cursor: 'pointer',
                        fontSize: '0.95rem',
                        width: '100%',
                        fontFamily: '"Outfit", sans-serif',
                        fontWeight: 600,
                        transition: 'all 0.2s',
                        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '8px'
                    }}
                >
                    <span>View All Output</span>
                    <span style={{ fontSize: '1.1rem' }}>📦</span>
                </motion.button>
            </motion.div>
        </>
    );
};

export default CreationFactory;
