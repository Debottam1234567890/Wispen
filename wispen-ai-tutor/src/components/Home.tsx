import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import WispenMascot from './WispenMascot';
import StickyNote from './StickyNote';
import { PaperBall, TornPaper, ScribbledFormula } from './ChaosItems';
import InkTrail from './InkTrail';
import ParticleSystem from './ParticleSystem';
import BackgroundDoodles from './BackgroundDoodles';
import SegmentedMascot from './SegmentedMascot';
import GoldenTicketButton from './GoldenTicketButton';


const SAD_NOTES = [
    "Too much homework!",
    "Failed my test.",
    "School is so hard.",
    "Feeling exhausted...",
    "Quiz tomorrow.",
    "I need a break.",
    "Overwhelmed with tasks."
];

const HAPPY_NOTES = [
    "Aced my test!",
    "Learning is fun!",
    "Feeling proud!",
    "This is exciting!",
    "Best day ever!",
    "Wispen is amazing!",
    "Flashcards are helpful.",
    "Mind maps make it easy.",
    "I think I can do this"
];

const EQUATIONS_AND_SHAPES = [
    "E = mc²",
    "sin²θ + cos²θ = 1",
    "∫ x² dx = x³/3 + C",
    "a² + b² = c²",
    "F = ma",
    "Δy = v₀t + ½at²",
    "PV = nRT",
    "λ = h/p",
    "Triangle Area = ½ × base × height",
    "Circle Area = πr²",
    "H₂O",
    "NaCl",
    "CO₂",
    "Velocity = Distance / Time"
];

import { auth } from '../firebase';

// ... (previous imports)

const Home = () => {
    const navigate = useNavigate();
    const [, setGlassesClicked] = useState(false);

    const randomPositions = useMemo(() => {
        const w = typeof window !== 'undefined' ? window.innerWidth : 0;
        const h = typeof window !== 'undefined' ? window.innerHeight : 0;
        const sadCount = SAD_NOTES.length;
        const happyCount = HAPPY_NOTES.length;
        const xPadding = 80;
        const sadStep = sadCount > 1 ? (w - xPadding * 2) / (sadCount - 1) : 0;
        const happyStep = happyCount > 1 ? (w - xPadding * 2) / (happyCount - 1) : 0;
        const sadHeight = h * 0.04; // container height
        const happyHeight = h * 0.24; // container height

        const sadNotes = SAD_NOTES.map((_, i) => ({
            x: xPadding + i * sadStep + (-15 + Math.random() * 30),
            y: Math.random() * (sadHeight - 40) + 20,
            rotation: -8 + Math.random() * 16,
            speed: 12 + Math.random() * 6
        }));

        const happyNotes = HAPPY_NOTES.map((_, i) => ({
            x: xPadding + i * happyStep + (-15 + Math.random() * 30),
            y: Math.random() * (happyHeight - 40) + 20,
            rotation: -8 + Math.random() * 16,
            speed: 12 + Math.random() * 6
        }));

        return {
            sadFront: sadNotes,
            happyFront: happyNotes
        };
    }, []);

    const handleGlassesClick = () => {
        setGlassesClicked(true);
        console.log("WISPEN's glasses clicked!");
    };

    const handleGetStartedClick = () => {
        const user = auth.currentUser;
        if (user) {
            navigate(`/${user.uid}/dashboard`);
        } else {
            navigate('/login');
        }
    };



    return (
        <div className="app">
            {/* Background Effects */}
            <BackgroundDoodles />
            <ParticleSystem />
            <InkTrail />
            <SegmentedMascot />

            <div className="stationery-container">
                <div
                    className="stationery-item pencil"
                    style={{ top: '12%', left: '8%', transform: 'rotate(-15deg)' }}
                />
                <div
                    className="stationery-item book"
                    style={{ top: '68%', right: '10%', transform: 'rotate(6deg)' }}
                />
                <div
                    className="stationery-item eraser"
                    style={{ bottom: '16%', left: '22%', transform: 'rotate(10deg)' }}
                />
                <div
                    className="stationery-item bookmark"
                    style={{ top: '22%', right: '18%', transform: 'rotate(-5deg)' }}
                />
                {/* Removed generic blank cards to reduce clutter */}

                {/* New Stationery Items */}
                <div className="stationery-item paperclip">
                    <svg width="30" height="60" viewBox="0 0 30 60">
                        <path d="M10,20 L10,50 A10,10 0 0,0 30,50 L30,10 A6,6 0 0,0 18,10 L18,40"
                            fill="none" stroke="#777" strokeWidth="3" opacity="0.8" strokeLinecap="round" />
                    </svg>
                </div>

                <div className="stationery-item ruler">
                    {[...Array(10)].map((_, i) => (
                        <div key={i} className="ruler-mark" />
                    ))}
                </div>

                <div className="stationery-item protractor">
                    <svg width="100" height="50" viewBox="0 0 100 50">
                        <path d="M10,40 A40,40 0 0,1 90,40" fill="none" stroke="#4A4A5E" strokeWidth="1" strokeDasharray="2,2" />
                        <line x1="50" y1="40" x2="50" y2="10" stroke="#4A4A5E" strokeWidth="1" />
                    </svg>
                </div>

                {/* Science Test Tubes */}
                <div className="stationery-item test-tube-1">
                    <svg width="40" height="120" viewBox="0 0 40 120">
                        <path d="M10,10 L10,100 A10,10 0 0,0 30,100 L30,10" fill="rgba(255, 255, 255, 0.4)" stroke="#4A4A5E" strokeWidth="2" />
                        <path d="M12,60 L12,98 A8,8 0 0,0 28,98 L28,60 Z" fill="#7fffd4" opacity="0.6" /> {/* Aquamarine liquid */}
                        <circle cx="16" cy="55" r="2" fill="#7fffd4" opacity="0.8" />
                        <circle cx="24" cy="50" r="3" fill="#7fffd4" opacity="0.6" />
                    </svg>
                </div>

                <div className="stationery-item test-tube-2">
                    <svg width="35" height="100" viewBox="0 0 35 100">
                        <path d="M8,10 L8,85 A9,9 0 0,0 26,85 L26,10" fill="rgba(255, 255, 255, 0.4)" stroke="#4A4A5E" strokeWidth="2" />
                        <path d="M10,40 L10,83 A7,7 0 0,0 24,83 L24,40 Z" fill="#ff69b4" opacity="0.6" /> {/* Pink liquid */}
                        <circle cx="17" cy="35" r="2" fill="#ff69b4" opacity="0.8" />
                    </svg>
                </div>
            </div>

            {/* Free-floating Equations and Shapes */}
            <div className="background-equations">
                {EQUATIONS_AND_SHAPES.map((item, index) => (
                    <motion.div
                        key={index}
                        className="equation"
                        initial={{
                            opacity: 0,
                            scale: 0.8,
                            x: Math.random() * window.innerWidth,
                            y: Math.random() * window.innerHeight
                        }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{
                            duration: 1,
                            delay: index * 0.2,
                            repeat: Infinity,
                            repeatType: "reverse"
                        }}
                    >
                        {item}
                    </motion.div>
                ))}
            </div>

            {/* Chaos Zone (Bad Sentiment) - Top */}
            <div className="chaos-zone">
                {randomPositions.sadFront.map((pos, i) => {
                    const content = SAD_NOTES[i % SAD_NOTES.length];
                    // Heuristic: If it has spaces (sentence), likely negative talk -> Torn Paper
                    // If it's short or looks math-y -> Scribble
                    const isSentence = content.includes(' ');

                    if (isSentence) {
                        return (
                            <TornPaper
                                key={`chaos-${i}`}
                                content={content}
                                x={pos.x}
                                y={pos.y}
                                rotation={pos.rotation}
                                delay={i * 0.1}
                            />
                        );
                    } else {
                        // Use random equation/scribble for variety if it's not specific negative text
                        // Mix of Scribbles and Paper Balls
                        const rand = Math.random();
                        if (rand < 0.6) {
                            const formulaContent = EQUATIONS_AND_SHAPES[i % EQUATIONS_AND_SHAPES.length];
                            return (
                                <ScribbledFormula
                                    key={`chaos-${i}`}
                                    content={formulaContent}
                                    x={pos.x}
                                    y={pos.y}
                                    rotation={pos.rotation}
                                    delay={i * 0.1}
                                />
                            );
                        } else {
                            return (
                                <PaperBall
                                    key={`chaos-${i}`}
                                    x={pos.x}
                                    y={pos.y}
                                    rotation={pos.rotation}
                                    delay={i * 0.1}
                                />
                            );
                        }
                    }
                })}
            </div>

            {/* Main Content */}
            <div className="content">
                <div className="center-backdrop" />
                {/* Header Section */}
                <motion.div
                    className="header-section"
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 1, type: "spring" }}
                >
                    <motion.h1
                        className="main-title"
                        animate={{ y: [0, -10, 0], rotate: [0, 1, -1, 0] }}
                        transition={{ duration: 3, repeat: Infinity }}
                    >
                        Meet Wispen
                    </motion.h1>

                    <motion.p
                        className="main-subtitle"
                        animate={{ scale: [1, 1.05, 1] }}
                        transition={{ duration: 2.5, repeat: Infinity }}
                    >
                        Your Academic Companion
                    </motion.p>
                </motion.div>

                <motion.p
                    className="emotional-line"
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 0.85, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.35 }}
                >
                    It’s okay to feel lost — learning isn’t supposed to be lonely.
                </motion.p>

                {/* Mascot Zone with Classroom Illustration */}
                <motion.div
                    className="mascot-zone-large"
                    initial={{ opacity: 0, y: 50 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, delay: 0.3, type: "spring" }}
                >
                    <WispenMascot
                        onGlassesClick={handleGlassesClick}
                    />
                    <img
                        src="/class.png"
                        alt="Classroom Illustration"
                        className="classroom-illustration"
                    />
                </motion.div>

                <motion.p
                    className="mascot-description"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.4 }}
                >
                    Turn study stress into momentum — Wispen turns scattered thoughts
                    into clarity and small wins.
                </motion.p>

                {/* Order Zone (Good Sentiment) - Under Mascot / Sides */}
                <div className="order-zone-container" style={{ position: 'relative', width: '100%', height: '300px', display: 'flex', justifyContent: 'center' }}>

                    {/* Left Side Highlights */}
                    <div className="highlight-group left" style={{ position: 'absolute', left: '10%', top: '20%' }}>
                        <motion.div
                            className="highlight-item"
                            animate={{ y: [0, -6, 0], rotate: [0, 2, -2, 0] }}
                            transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
                        >
                            <svg width="80" height="80" viewBox="0 0 80 80">
                                <circle cx="40" cy="40" r="32" fill="var(--vapor-cyan)" opacity="0.2" />
                                <circle cx="40" cy="40" r="30" fill="none" stroke="var(--ink-shadow)" strokeWidth="3" />
                                <text x="40" y="47" textAnchor="middle" fontSize="28" fill="var(--ink-shadow)" fontFamily="var(--font-title)">A+</text>
                            </svg>
                        </motion.div>

                        {/* Happy Sticky Notes Interspersed Left */}
                        <StickyNote
                            content={HAPPY_NOTES[0]}
                            initialX={0}
                            initialY={100}
                            driftSpeed={15}
                            rotation={-5}
                        />
                        <StickyNote
                            content={HAPPY_NOTES[1]}
                            initialX={80}
                            initialY={-20}
                            driftSpeed={18}
                            rotation={5}
                        />

                        <motion.div
                            className="highlight-item"
                            animate={{ y: [0, -5, 0], rotate: [0, -2, 2, 0] }}
                            transition={{ duration: 3.2, repeat: Infinity, ease: 'easeInOut' }}
                            style={{ marginLeft: '40px', marginTop: '60px' }}
                        >
                            {/* Removed White Box, kept icon logic if needed or removed entirely if it was just a box */}
                            <svg width="80" height="60" viewBox="0 0 80 60">
                                <path d="M60 30 L65 35 L75 25" stroke="var(--vapor-cyan)" strokeWidth="4" fill="none" strokeLinecap="round" />
                                <line x1="10" y1="20" x2="50" y2="20" stroke="var(--ink-shadow)" strokeWidth="2" opacity="0.6" strokeLinecap="round" />
                                <line x1="10" y1="35" x2="50" y2="35" stroke="var(--ink-shadow)" strokeWidth="2" opacity="0.6" strokeLinecap="round" />
                            </svg>
                        </motion.div>
                    </div>

                    {/* Right Side Highlights */}
                    <div className="highlight-group right" style={{ position: 'absolute', right: '10%', top: '20%' }}>
                        <motion.div
                            className="highlight-item"
                            animate={{ y: [0, -6, 0], rotate: [0, -2, 2, 0] }}
                            transition={{ duration: 3.1, repeat: Infinity, ease: 'easeInOut' }}
                        >
                            {/* Removed Box */}
                            <svg width="80" height="60" viewBox="0 0 80 60">
                                <path d="M20 30 L26 36 L36 24" stroke="var(--vapor-cyan)" strokeWidth="4" fill="none" strokeLinecap="round" />
                                <line x1="40" y1="20" x2="75" y2="20" stroke="var(--ink-shadow)" strokeWidth="2" opacity="0.6" strokeLinecap="round" />
                                <line x1="40" y1="35" x2="75" y2="35" stroke="var(--ink-shadow)" strokeWidth="2" opacity="0.6" strokeLinecap="round" />
                            </svg>
                        </motion.div>

                        {/* Happy Sticky Notes Interspersed Right */}
                        <StickyNote
                            content={HAPPY_NOTES[2]}
                            initialX={0}
                            initialY={100}
                            driftSpeed={16}
                            rotation={8}
                        />
                        <StickyNote
                            content={HAPPY_NOTES[3]}
                            initialX={-60}
                            initialY={-30}
                            driftSpeed={14}
                            rotation={-3}
                        />

                        <motion.div
                            className="highlight-item"
                            animate={{ y: [0, -5, 0] }}
                            transition={{ duration: 2.8, repeat: Infinity, ease: 'easeInOut' }}
                            style={{ marginLeft: '-30px', marginTop: '60px' }}
                        >
                            <svg width="70" height="70" viewBox="0 0 70 70">
                                <circle cx="35" cy="35" r="30" fill="none" stroke="var(--ink-shadow)" strokeWidth="3" />
                                <path d="M20 38 L32 48 L50 24" stroke="var(--dream-pink)" strokeWidth="5" fill="none" strokeLinecap="round" />
                            </svg>
                        </motion.div>
                        <motion.div
                            className="highlight-item"
                            animate={{ y: [0, -4, 0], rotate: [0, 2, -2, 0] }}
                            transition={{ duration: 3.4, repeat: Infinity, ease: 'easeInOut' }}
                            style={{ marginLeft: '40px' }}
                        >
                            <svg width="80" height="80" viewBox="0 0 80 80">
                                {/* Checkmark only, no box */}
                                <text x="40" y="55" textAnchor="middle" fontSize="40" fill="var(--ink-shadow)" fontFamily="var(--font-title)" style={{ filter: 'drop-shadow(2px 2px 0px rgba(255,255,255,0.5))' }}>✓</text>
                            </svg>
                        </motion.div>
                    </div>
                </div>

                {/* Buttons Section */}
                <motion.div
                    className="buttons-section"
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, delay: 0.9 }}
                >
                    <GoldenTicketButton onClick={handleGetStartedClick} />
                    <motion.button
                        className="marker-button new-session"
                        initial={{}}
                        animate={{ scale: [1, 1.01, 1] }}
                        transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut', repeatDelay: 3 }}
                        whileHover={{ rotate: [-1, 1, -1], scale: 1.04 }}
                        whileTap={{ scale: 0.96 }}
                        onClick={() => navigate('/how-it-works')}
                        aria-label="See How It Works"
                    >
                        See How It Works <motion.span animate={{ x: [0, 3, 0] }} transition={{ duration: 1.2, repeat: Infinity }}>→</motion.span>
                    </motion.button>
                </motion.div>
            </div>
        </div>
    );
};

export default Home;
