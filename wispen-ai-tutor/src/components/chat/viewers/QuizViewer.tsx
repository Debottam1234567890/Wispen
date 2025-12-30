import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import MarkdownRenderer from '../MarkdownRenderer';
import { API_BASE_URL } from '../../../config';

interface QuizViewerProps {
    onClose: () => void;
    quizData?: {
        title: string;
        questions: any[];
    };
}

const DEFAULT_QUIZ = [
    {
        id: 1,
        question: "Please wait while we prepare your quiz...",
        options: ["Loading...", "Loading...", "Loading...", "Loading..."],
        correct: 0,
        explanation: "The quiz is being fetched from the database."
    }
];

const QuizViewer: React.FC<QuizViewerProps> = ({ onClose, quizData }) => {
    const questions = quizData?.questions || DEFAULT_QUIZ;
    const [currentQIndex, setCurrentQIndex] = useState(0);
    const [selectedOption, setSelectedOption] = useState<number | null>(null);
    const [isAnswered, setIsAnswered] = useState(false);
    const [score, setScore] = useState(0);
    const [showResults, setShowResults] = useState(false);

    const currentQuestion = questions[currentQIndex];

    const handleOptionClick = (index: number) => {
        if (isAnswered) return;
        setSelectedOption(index);
        setIsAnswered(true);
        if (index === currentQuestion.correct) {
            setScore((prev: number) => prev + 1);
        }
    };

    const handleNext = async () => {
        if (currentQIndex < questions.length - 1) {
            setCurrentQIndex((prev: number) => prev + 1);
            setSelectedOption(null);
            setIsAnswered(false);
        } else {
            setShowResults(true);
            // PERSISTENCE: Save score to backend
            try {
                // Extract session ID from URL if possible
                const params = new URLSearchParams(window.location.search);
                const sessionId = params.get('session_id');
                const quizId = (questions as any).id || questions[0]?.quizId; // Fallback to check if ID exists

                await fetch(`${API_BASE_URL}/quizzes/score`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    },
                    body: JSON.stringify({
                        quizId: quizId || 'manual_gen',
                        sessionId: sessionId,
                        score: score + (selectedOption === currentQuestion.correct ? 1 : 0), // Include last answer
                        total: questions.length
                    })
                });
            } catch (err) {
                console.error("Failed to save quiz score:", err);
            }
        }
    };

    if (showResults) {
        return (
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100%',
                    background: 'radial-gradient(circle at center, #fdfbf7 0%, #e5e7eb 100%)',
                    zIndex: 20,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontFamily: '"Outfit", sans-serif'
                }}
            >
                <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', overflow: 'hidden', pointerEvents: 'none' }}>
                    {/* Simple confetti dots */}
                    {[...Array(20)].map((_, i) => (
                        <motion.div
                            key={i}
                            initial={{ y: -50, x: Math.random() * window.innerWidth }}
                            animate={{ y: window.innerHeight + 50, rotate: 360 }}
                            transition={{ duration: 2 + Math.random() * 2, repeat: Infinity, ease: 'linear' }}
                            style={{
                                position: 'absolute',
                                width: '10px',
                                height: '10px',
                                background: ['#f87171', '#60a5fa', '#34d399', '#fbbf24'][Math.floor(Math.random() * 4)],
                                borderRadius: '50%'
                            }}
                        />
                    ))}
                </div>

                <button
                    onClick={onClose}
                    style={{
                        position: 'absolute',
                        top: '20px',
                        right: '20px',
                        background: 'rgba(0,0,0,0.05)',
                        border: 'none',
                        borderRadius: '50%',
                        width: '40px',
                        height: '40px',
                        fontSize: '1.2rem',
                        cursor: 'pointer',
                        zIndex: 30
                    }}
                >
                    ✕
                </button>
                <div style={{ textAlign: 'center', zIndex: 1 }}>
                    <motion.h1
                        initial={{ scale: 0 }}
                        animate={{ scale: 1, rotate: [0, -10, 10, -10, 10, 0] }}
                        transition={{ type: 'spring', delay: 0.2 }}
                        style={{ fontSize: '5rem', marginBottom: '10px' }}
                    >
                        {score === questions.length ? '🌟' : score > questions.length / 2 ? '👍' : '📚'}
                    </motion.h1>
                    <h2 style={{ fontSize: '3rem', color: '#1f2937', fontFamily: '"Indie Flower", cursive' }}>Quiz Complete!</h2>
                    <p style={{ fontSize: '1.5rem', color: '#4b5563', marginTop: '10px', fontFamily: '"Outfit", sans-serif' }}>
                        You scored <span style={{ color: '#3b82f6', fontWeight: 'bold' }}>{score}</span> out of {questions.length}
                    </p>
                    <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={onClose}
                        style={{
                            marginTop: '40px',
                            padding: '16px 40px',
                            background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '50px',
                            fontSize: '1.2rem',
                            cursor: 'pointer',
                            fontWeight: 600,
                            boxShadow: '0 10px 20px rgba(37, 99, 235, 0.3)'
                        }}
                    >
                        Back to Factory
                    </motion.button>
                </div>
            </motion.div>
        );
    }

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
                background: '#fff',
                zIndex: 20,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                padding: '40px',
                fontFamily: '"Inter", sans-serif',
                overflowY: 'auto'
            }}
        >
            <button
                onClick={onClose}
                style={{
                    position: 'absolute',
                    top: '20px',
                    right: '20px',
                    background: 'rgba(0,0,0,0.05)',
                    border: 'none',
                    borderRadius: '50%',
                    width: '40px',
                    height: '40px',
                    fontSize: '1.2rem',
                    cursor: 'pointer',
                    zIndex: 30
                }}
            >
                ✕
            </button>

            <div style={{ width: '100%', maxWidth: '800px', marginTop: '40px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px', color: '#666' }}>
                    <span>Question {currentQIndex + 1} of {questions.length}</span>
                    <span>Score: {score}</span>
                </div>

                <div style={{ width: '100%', height: '6px', background: '#e5e7eb', borderRadius: '3px', marginBottom: '40px' }}>
                    <motion.div
                        style={{ height: '100%', background: '#3b82f6', borderRadius: '3px' }}
                        animate={{ width: `${((currentQIndex + 1) / questions.length) * 100}%` }}
                    />
                </div>

                <div style={{ fontSize: '2rem', color: '#111827', marginBottom: '30px', fontFamily: '"Indie Flower", cursive' }}>
                    <MarkdownRenderer content={currentQuestion.question} />
                </div>

                <div style={{ display: 'grid', gap: '15px' }}>
                    {currentQuestion.options.map((option: string, index: number) => {
                        let borderColor = 'rgba(0,0,0,0.05)';
                        let bgColor = 'white';
                        let textColor = '#374151';

                        if (isAnswered) {
                            if (index === currentQuestion.correct) {
                                borderColor = '#22c55e'; // Green
                                bgColor = '#dcfce7';
                                textColor = '#166534';
                            } else if (index === selectedOption) {
                                borderColor = '#ef4444'; // Red
                                bgColor = '#fee2e2';
                                textColor = '#991b1b';
                            }
                        }

                        return (
                            <motion.button
                                key={index}
                                onClick={() => handleOptionClick(index)}
                                disabled={isAnswered}
                                whileHover={!isAnswered ? { scale: 1.02, x: 5, backgroundColor: '#f9fafb' } : {}}
                                whileTap={!isAnswered ? { scale: 0.98 } : {}}
                                animate={isAnswered && index === currentQuestion.correct ? { scale: [1, 1.05, 1], backgroundColor: '#dcfce7' } : {}}
                                style={{
                                    padding: '24px',
                                    borderRadius: '16px',
                                    border: `2px solid ${isAnswered ? borderColor : selectedOption === index ? '#3b82f6' : 'rgba(0,0,0,0.05)'}`,
                                    background: bgColor,
                                    color: textColor,
                                    fontSize: '1.2rem',
                                    textAlign: 'left',
                                    cursor: isAnswered ? 'default' : 'pointer',
                                    transition: 'border-color 0.2s',
                                    fontFamily: '"Outfit", sans-serif',
                                    boxShadow: '0 2px 4px rgba(0,0,0,0.02)',
                                    display: 'flex',
                                    alignItems: 'center'
                                }}
                            >
                                <span style={{ marginRight: '15px', opacity: 0.5, fontWeight: 'bold', flexShrink: 0 }}>{String.fromCharCode(65 + index)}.</span>
                                <div style={{ flex: 1 }}>
                                    <MarkdownRenderer content={option} />
                                </div>
                            </motion.button>
                        );
                    })}
                </div>

                <AnimatePresence>
                    {isAnswered && (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            style={{
                                marginTop: '30px',
                                background: '#f8fafc',
                                padding: '20px',
                                borderRadius: '12px',
                                borderLeft: '4px solid #3b82f6'
                            }}
                        >
                            <h4 style={{ margin: '0 0 10px 0', color: '#333' }}>Explanation</h4>
                            <div style={{ margin: 0, color: '#666', lineHeight: '1.5' }}>
                                <MarkdownRenderer content={currentQuestion.explanation} />
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {isAnswered && (
                    <div style={{ marginTop: '30px', textAlign: 'right' }}>
                        <button
                            onClick={handleNext}
                            style={{
                                padding: '12px 30px',
                                background: '#3b82f6',
                                color: 'white',
                                border: 'none',
                                borderRadius: '8px',
                                fontSize: '1rem',
                                cursor: 'pointer',
                                fontWeight: '500'
                            }}
                        >
                            {currentQIndex === questions.length - 1 ? 'Finish Quiz' : 'Next Question →'}
                        </button>
                    </div>
                )}
            </div>
        </motion.div>
    );
};

export default QuizViewer;
