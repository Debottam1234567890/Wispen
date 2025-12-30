import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { auth } from '../../firebase';

import EducationBackground from './EducationBackground';
import { API_BASE_URL } from '../../config';
import BookshelfNebula from './BookshelfNebula';
import ChatCosmos from './ChatCosmos';
import CreationFactory from './CreationFactory';
import SessionTimer from './SessionTimer';
import MindMapViewer from './viewers/MindMapViewer';
import FlashcardViewer from './viewers/FlashcardViewer';

const ChatInterface = () => {
    const navigate = useNavigate();
    const [searchParams, setSearchParams] = useSearchParams();
    const sessionId = searchParams.get('session_id') || searchParams.get('sessionId') || undefined;
    const [creationsRefreshKey, setCreationsRefreshKey] = useState(0); // Trigger refetch of creations
    const [sessionTitle, setSessionTitle] = useState('Untitled');
    const [isEditingTitle, setIsEditingTitle] = useState(false);
    const [titleInput, setTitleInput] = useState('Untitled');

    // Auto-create session if missing
    useEffect(() => {
        const checkAndCreateSession = async () => {
            if (sessionId) return;

            const user = auth.currentUser;
            if (!user) return; // Wait for auth

            try {
                const token = await user.getIdToken();
                // Create a new default session
                const response = await fetch(`${API_BASE_URL}/sessions`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({
                        subject: 'Untitled', // Default subject
                        duration: '0m',
                        date: new Date().toISOString()
                    })
                });

                if (response.ok) {
                    const data = await response.json();
                    if (data.id) {
                        // Update URL without reload
                        setSearchParams({ session_id: data.id });
                    }
                }
            } catch (err) {
                console.error("Failed to create session:", err);
            }
        };

        checkAndCreateSession();
    }, [sessionId, auth.currentUser]);

    // Fetch Session Title metadata
    useEffect(() => {
        const fetchSessionMetadata = async () => {
            if (!sessionId || !auth.currentUser) return;
            try {
                const token = await auth.currentUser.getIdToken();
                const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (response.ok) {
                    const data = await response.json();
                    if (data.subject) {
                        setSessionTitle(data.subject);
                        setTitleInput(data.subject);
                    }
                }
            } catch (err) {
                console.error("Failed to fetch session metadata:", err);
            }
        };
        fetchSessionMetadata();
    }, [sessionId, auth.currentUser]);

    const handleSaveTitle = async () => {
        if (!sessionId || !auth.currentUser || !titleInput.trim()) {
            setIsEditingTitle(false);
            return;
        }

        const oldTitle = sessionTitle;
        setSessionTitle(titleInput); // Optimistic update
        setIsEditingTitle(false);

        try {
            const token = await auth.currentUser.getIdToken();
            const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ subject: titleInput.trim() })
            });

            if (!response.ok) throw new Error('Failed to update title');
        } catch (err) {
            console.error("Failed to save title:", err);
            setSessionTitle(oldTitle); // Rollback
            setTitleInput(oldTitle);
        }
    };

    const onExit = () => {
        const uid = auth.currentUser?.uid;
        if (uid) {
            navigate(`/${uid}/dashboard`);
        } else {
            navigate('/');
        }
    };
    // Panel Visibility States
    const [showNebula, setShowNebula] = useState(true);
    const [showFactory, setShowFactory] = useState(true);
    const [showMindmap, setShowMindmap] = useState(false);
    const [mindmapPrompt, setMindmapPrompt] = useState("");
    const [mindmapId, setMindmapId] = useState<string | null>(null);
    const [showFlashcards, setShowFlashcards] = useState(false);
    const [flashcardData, setFlashcardData] = useState<any[] | null>(null);

    // Calculate Grid Template based on visibility
    // Default: 320px 1fr 300px
    // If Nebula Hidden: 0px 1fr 300px
    // If Factory Hidden: 320px 1fr 0px
    // If Both Hidden: Chat expands to full screen
    const getGridTemplate = () => {
        if (!showNebula && !showFactory) {
            return '0px 1fr 0px'; // Full screen chat
        }
        const left = showNebula ? '320px' : '0px';
        const right = showFactory ? '300px' : '0px';
        return `${left} 1fr ${right}`;
    };

    return (
        <div style={{ width: '100vw', height: '100vh', position: 'relative', overflow: 'hidden', color: '#333', fontFamily: '"Indie Flower", cursive' }}>
            {/* Background Layer */}
            <EducationBackground />

            {/* Top Navigation Bar */}
            <div style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '70px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0 25px',
                zIndex: 100,
                background: 'rgba(255,255,255,0.7)',
                backdropFilter: 'blur(10px)',
                borderBottom: '1px solid rgba(0,0,0,0.05)',
                boxShadow: '0 4px 20px rgba(0,0,0,0.02)'
            }}>
                {sessionId && <SessionTimer sessionId={sessionId} />}
                <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>

                    {/* Nebula Toggle (Left) */}
                    <button
                        onClick={() => setShowNebula(!showNebula)}
                        style={{
                            background: showNebula ? 'var(--dream-purple, #6C63FF)' : 'transparent',
                            color: showNebula ? 'white' : '#666',
                            border: '1px solid #ddd',
                            borderRadius: '12px',
                            padding: '8px 12px',
                            cursor: 'pointer',
                            fontSize: '1.2rem',
                            display: 'flex', alignItems: 'center', gap: '5px',
                            fontFamily: '"Caveat", cursive',
                            transition: 'all 0.3s ease'
                        }}
                    >
                        {showNebula ? '◀' : '▶'} 📚 <span style={{ fontSize: '1rem' }}>Library</span>
                    </button>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {isEditingTitle ? (
                            <input
                                autoFocus
                                value={titleInput}
                                onChange={(e) => setTitleInput(e.target.value)}
                                onBlur={handleSaveTitle}
                                onKeyDown={(e) => e.key === 'Enter' && handleSaveTitle()}
                                style={{
                                    fontSize: '1.4rem',
                                    fontWeight: 'bold',
                                    color: '#444',
                                    fontFamily: '"Caveat", cursive',
                                    border: 'none',
                                    background: 'rgba(255,255,255,0.8)',
                                    borderRadius: '8px',
                                    padding: '2px 8px',
                                    outline: 'none',
                                    boxShadow: '0 0 0 2px var(--dream-purple, #6C63FF)'
                                }}
                            />
                        ) : (
                            <h2
                                onClick={() => setIsEditingTitle(true)}
                                title="Click to rename"
                                style={{
                                    margin: 0,
                                    fontSize: '1.4rem',
                                    fontWeight: 'bold',
                                    color: '#444',
                                    fontFamily: '"Caveat", cursive',
                                    cursor: 'pointer',
                                    padding: '2px 8px',
                                    borderRadius: '8px',
                                    transition: 'background 0.2s'
                                }}
                                onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(0,0,0,0.05)'}
                                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                            >
                                {sessionTitle}
                            </h2>
                        )}
                    </div>
                </div>

                <div style={{ display: 'flex', gap: '15px' }}>
                    {/* Factory Toggle (Right) */}
                    <button
                        onClick={() => setShowFactory(!showFactory)}
                        style={{
                            background: showFactory ? 'var(--dream-purple, #6C63FF)' : 'transparent',
                            color: showFactory ? 'white' : '#666',
                            border: '1px solid #ddd',
                            borderRadius: '12px',
                            padding: '8px 12px',
                            cursor: 'pointer',
                            fontSize: '1.2rem',
                            display: 'flex', alignItems: 'center', gap: '5px',
                            fontFamily: '"Caveat", cursive',
                            transition: 'all 0.3s ease'
                        }}
                    >
                        <span style={{ fontSize: '1rem' }}>Factory</span> 🏭 {showFactory ? '▶' : '◀'}
                    </button>

                    <button
                        onClick={onExit}
                        style={{
                            background: 'white',
                            border: '1px solid #ddd',
                            color: '#555',
                            padding: '8px 16px',
                            borderRadius: '12px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            fontWeight: 'bold',
                            boxShadow: '0 2px 5px rgba(0,0,0,0.05)'
                        }}
                    >
                        📊 Dashboard
                    </button>
                </div>
            </div>

            {/* Main Content Layout - 3 Realms Grid */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: getGridTemplate(),
                gap: '20px',
                padding: '90px 20px 20px 20px', // Top padding for header
                height: '100vh',
                width: '100vw', // Ensure full width
                boxSizing: 'border-box', // Fixes the overflow issue!
                maxWidth: '100%',
                transition: 'grid-template-columns 0.5s cubic-bezier(0.4, 0, 0.2, 1)', // Smooth layout transition
                zIndex: 10,
                position: 'relative'
            }}>

                {/* Left Realm: Bookshelf */}
                {showNebula && (
                    <AnimatePresence>
                        <motion.div
                            initial={{ opacity: 0, x: -50 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -50 }}
                            transition={{ duration: 0.4 }}
                            style={{ height: '100%', overflow: 'hidden', gridColumn: '1' }}
                        >
                            <BookshelfNebula sessionId={sessionId} />
                        </motion.div>
                    </AnimatePresence>
                )}

                {/* Center Realm: Chat */}
                <div style={{ height: '100%', minWidth: '0', width: '100%', gridColumn: '2', overflow: 'hidden' }}>
                    <ChatCosmos
                        sessionId={sessionId}
                        onOpenFlashcards={(cards) => {
                            setFlashcardData(cards);
                            setShowFlashcards(true);
                        }}
                    />
                </div>

                {/* Right Realm: Factory */}
                {showFactory && (
                    <AnimatePresence>
                        <motion.div
                            initial={{ opacity: 0, x: 50 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: 50 }}
                            transition={{ duration: 0.4 }}
                            style={{ height: '100%', overflow: 'hidden', gridColumn: '3' }}
                        >
                            <CreationFactory
                                sessionId={sessionId}
                                refreshKey={creationsRefreshKey}
                                onOpenMindmap={(val: string) => {
                                    // If it looks like an ID (no spaces and long), set mindmapId
                                    if (val && !val.includes(' ') && val.length > 10) {
                                        setMindmapId(val);
                                        setMindmapPrompt("");
                                    } else {
                                        setMindmapPrompt(val || "");
                                        setMindmapId(null);
                                    }
                                    setShowMindmap(true);
                                }}
                                onOpenFlashcards={(cards) => {
                                    setFlashcardData(cards);
                                    setShowFlashcards(true);
                                }}
                            />
                        </motion.div>
                    </AnimatePresence>
                )}
            </div>

            {/* Quick Access Orbs (Floating) - Removed per user request */}

            {/* Overlays - Global Scope */}
            <AnimatePresence>
                {showMindmap && (
                    <MindMapViewer
                        onClose={() => {
                            setShowMindmap(false);
                            setMindmapId(null);
                            // Trigger CreationFactory to refetch
                            setCreationsRefreshKey(prev => prev + 1);
                        }}
                        initialPrompt={mindmapPrompt}
                        mindmapId={mindmapId || undefined}
                        sessionId={sessionId}
                    />
                )}
                {showFlashcards && (
                    <FlashcardViewer
                        onClose={() => setShowFlashcards(false)}
                        cards={flashcardData || undefined}
                    />
                )}
            </AnimatePresence>
        </div>
    );
};

export default ChatInterface;
