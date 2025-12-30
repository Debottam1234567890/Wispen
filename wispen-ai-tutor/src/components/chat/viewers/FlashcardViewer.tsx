import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { auth } from '../../../firebase';
import MarkdownRenderer from '../MarkdownRenderer';
import { API_BASE_URL } from '../../../config';

interface Flashcard {
    id: string | number;
    front: string;
    back: string;
    category?: string;
}

interface FlashcardViewerProps {
    onClose: () => void;
    cards?: Flashcard[];
    title?: string;
}

const FlashcardViewer: React.FC<FlashcardViewerProps> = ({ onClose, cards, title }) => {
    const [flashcards, setFlashcards] = useState<Flashcard[]>(cards || []);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [isFlipped, setIsFlipped] = useState(false);
    const [loading, setLoading] = useState(!cards);
    const [error, setError] = useState<string | null>(null);

    // Fetch flashcards if not provided via props
    React.useEffect(() => {
        if (!cards) {
            const fetchFlashcards = async () => {
                try {
                    const user = auth.currentUser;
                    if (!user) return;

                    const token = await user.getIdToken();
                    const response = await fetch(`${API_BASE_URL}/flashcards`, {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });

                    if (response.ok) {
                        const data = await response.json();
                        // Get the latest set or all cards
                        if (data.length > 0) {
                            // If the latest item has a 'cards' array (new format)
                            if (data[0].cards) {
                                setFlashcards(data[0].cards);
                            } else {
                                setFlashcards(data);
                            }
                        }
                    } else {
                        setError("Failed to load flashcards");
                    }
                } catch (err) {
                    setError("Error connecting to server");
                } finally {
                    setLoading(false);
                }
            };
            fetchFlashcards();
        }
    }, [cards]);

    const handleNext = (e: React.MouseEvent) => {
        e.stopPropagation();
        if (currentIndex < flashcards.length - 1) {
            setCurrentIndex(prev => prev + 1);
            setIsFlipped(false);
        }
    };

    const handlePrev = (e: React.MouseEvent) => {
        e.stopPropagation();
        if (currentIndex > 0) {
            setCurrentIndex(prev => prev - 1);
            setIsFlipped(false);
        }
    };

    const handleCardClick = () => {
        setIsFlipped(!isFlipped);
    };

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                background: '#f3f4f6',
                zIndex: 20,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                fontFamily: '"Inter", sans-serif'
            }}
        >
            {/* Minimal Header */}
            <div style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '80px',
                padding: '0 32px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                borderBottom: '1px solid #f9fafb',
                backgroundColor: 'rgba(255, 255, 255, 0.8)',
                backdropFilter: 'blur(12px)',
                zIndex: 35
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <div style={{ width: '40px', height: '40px', backgroundColor: '#F6D365', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.25rem' }}>📇</div>
                    <div>
                        <h1 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#111827', margin: 0, lineHeight: 1, fontFamily: '"Outfit", sans-serif' }}>{title || "Flashcards"}</h1>
                        <span style={{ fontSize: '0.75rem', color: '#FDA085', fontWeight: 500, letterSpacing: '0.05em', textTransform: 'uppercase', fontFamily: '"Outfit", sans-serif' }}>Wispen Flashcard Agent</span>
                    </div>
                </div>
                <button
                    onClick={onClose}
                    style={{
                        width: '48px',
                        height: '48px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        borderRadius: '16px',
                        backgroundColor: 'transparent',
                        border: 'none',
                        cursor: 'pointer',
                        color: '#9ca3af',
                        transition: 'all 0.2s'
                    }}
                    onMouseOver={(e) => { e.currentTarget.style.backgroundColor = '#f3f4f6'; e.currentTarget.style.color = '#111827'; }}
                    onMouseOut={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; e.currentTarget.style.color = '#9ca3af'; }}
                >
                    <svg style={{ width: '24px', height: '24px' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>

            <div style={{ position: 'absolute', top: '100px', width: '100%', textAlign: 'center' }}>
                <span style={{ fontSize: '1rem', color: '#6b7280', fontFamily: '"Outfit", sans-serif', opacity: 0.8 }}>
                    ({flashcards.length > 0 ? currentIndex + 1 : 0} / {flashcards.length})
                </span>
            </div>

            {loading ? (
                <div style={{ padding: '40px', textAlign: 'center' }}>
                    <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1 }} style={{ fontSize: '3rem' }}>⚙️</motion.div>
                    <p style={{ marginTop: '20px', fontFamily: '"Indie Flower", cursive', fontSize: '1.5rem' }}>Gathering your flashcards...</p>
                </div>
            ) : error ? (
                <div style={{ padding: '40px', textAlign: 'center', color: '#dc2626' }}>
                    <p style={{ fontSize: '1.2rem' }}>⚠️ {error}</p>
                    <button onClick={onClose} style={{ marginTop: '20px', padding: '12px 24px', borderRadius: '12px', border: 'none', background: '#3b82f6', color: 'white', cursor: 'pointer', fontFamily: '"Outfit", sans-serif', fontWeight: 600 }}>Close Viewer</button>
                </div>
            ) : flashcards.length === 0 ? (
                <div style={{ padding: '40px', textAlign: 'center' }}>
                    <p style={{ fontSize: '1.2rem', color: '#666' }}>No flashcards found. Create some in the Factory! 🏭</p>
                    <button onClick={onClose} style={{ marginTop: '20px', padding: '12px 24px', borderRadius: '12px', border: 'none', background: '#3b82f6', color: 'white', cursor: 'pointer', fontFamily: '"Outfit", sans-serif', fontWeight: 600 }}>Close Viewer</button>
                </div>
            ) : (
                <>
                    <div style={{ position: 'relative', width: '600px', height: '360px', perspective: '1200px' }}>
                        <motion.div
                            style={{
                                width: '100%',
                                height: '100%',
                                position: 'relative',
                                transformStyle: 'preserve-3d',
                                cursor: 'pointer'
                            }}
                            animate={{ rotateY: isFlipped ? 180 : 0 }}
                            transition={{ duration: 0.6, type: "spring", stiffness: 200, damping: 20 }}
                            onClick={handleCardClick}
                        >
                            {/* Front */}
                            <div style={{
                                position: 'absolute',
                                width: '100%',
                                height: '100%',
                                backfaceVisibility: 'hidden',
                                background: 'linear-gradient(135deg, #ffffff 0%, #f9fafb 100%)',
                                borderRadius: '24px',
                                boxShadow: '0 20px 40px -5px rgba(0,0,0,0.1), 0 10px 10px -5px rgba(0,0,0,0.04), inset 0 0 0 1px rgba(0,0,0,0.05)',
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'center',
                                justifyContent: 'center',
                                padding: '40px',
                                textAlign: 'center',
                                color: '#1f2937'
                            }}>
                                <span style={{
                                    position: 'absolute',
                                    top: '20px',
                                    left: '30px',
                                    fontSize: '0.8rem',
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.1em',
                                    color: '#9ca3af',
                                    fontWeight: 600,
                                    fontFamily: '"Outfit", sans-serif'
                                }}>
                                    {flashcards[currentIndex].category || "Topic"}
                                </span>

                                <div style={{ fontSize: '1.8rem', fontWeight: '600', fontFamily: '"Outfit", sans-serif', margin: 0 }}>
                                    <MarkdownRenderer content={flashcards[currentIndex].front} />
                                </div>

                                <div style={{
                                    position: 'absolute',
                                    bottom: '25px',
                                    fontSize: '0.9rem',
                                    color: '#9ca3af',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '6px',
                                    fontFamily: '"Outfit", sans-serif'
                                }}>
                                    <span>Tap to flip</span> ↻
                                </div>
                            </div>

                            {/* Back */}
                            <div style={{
                                position: 'absolute',
                                width: '100%',
                                height: '100%',
                                backfaceVisibility: 'hidden',
                                background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
                                borderRadius: '24px',
                                boxShadow: '0 20px 40px -5px rgba(59, 130, 246, 0.4)',
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'center',
                                justifyContent: 'center',
                                padding: '40px',
                                textAlign: 'center',
                                color: 'white',
                                transform: 'rotateY(180deg)'
                            }}>
                                <span style={{
                                    position: 'absolute',
                                    top: '20px',
                                    left: '30px',
                                    fontSize: '0.8rem',
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.1em',
                                    color: 'rgba(255,255,255,0.6)',
                                    fontWeight: 600,
                                    fontFamily: '"Outfit", sans-serif'
                                }}>
                                    Answer
                                </span>

                                <div style={{ fontSize: '1.4rem', lineHeight: '1.6', fontFamily: '"Outfit", sans-serif' }}>
                                    <MarkdownRenderer content={flashcards[currentIndex].back} />
                                </div>
                            </div>
                        </motion.div>
                    </div>

                    <div style={{ marginTop: '30px', display: 'flex', gap: '20px' }}>
                        <button
                            onClick={handlePrev}
                            disabled={currentIndex === 0}
                            style={{
                                padding: '10px 20px',
                                borderRadius: '8px',
                                border: 'none',
                                background: currentIndex === 0 ? '#e5e7eb' : '#fff',
                                color: currentIndex === 0 ? '#9ca3af' : '#333',
                                cursor: currentIndex === 0 ? 'default' : 'pointer',
                                boxShadow: currentIndex === 0 ? 'none' : '0 2px 5px rgba(0,0,0,0.05)',
                                fontSize: '1rem'
                            }}
                        >
                            Previous
                        </button>
                        <button
                            onClick={handleNext}
                            disabled={currentIndex === flashcards.length - 1}
                            style={{
                                padding: '10px 20px',
                                borderRadius: '8px',
                                border: 'none',
                                background: currentIndex === flashcards.length - 1 ? '#e5e7eb' : '#3b82f6',
                                color: currentIndex === flashcards.length - 1 ? '#9ca3af' : '#fff',
                                cursor: currentIndex === flashcards.length - 1 ? 'default' : 'pointer',
                                boxShadow: currentIndex === flashcards.length - 1 ? 'none' : '0 2px 5px rgba(0,0,0,0.05)',
                                fontSize: '1rem'
                            }}
                        >
                            Next
                        </button>
                    </div>
                </>
            )}

        </motion.div>
    );
};

export default FlashcardViewer;
