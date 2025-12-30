
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import BackgroundDoodles from './BackgroundDoodles';
import ParticleSystem from './ParticleSystem';

const HowItWorks = () => {
    const navigate = useNavigate();

    const coreFeatures = [
        {
            title: "Personalized Explanations",
            description: "Get concepts explained YOUR way. Wispen adapts the difficulty level based on how well you understand — simpler if you're struggling, more advanced when you're ready.",
            color: "#4f46e5",
            emoji: "🎯"
        },
        {
            title: "AI-Powered Visual Learning",
            description: "Watch your textbooks come alive! Complex topics are transformed into stunning videos and visual explanations that stick in your memory.",
            color: "#0891b2",
            emoji: "🎬"
        },
        {
            title: "Smart Quiz Generator",
            description: "No more boring practice tests. Our AI creates personalized quizzes with step-by-step solutions that target exactly what you need to learn.",
            color: "#7c3aed",
            emoji: "📝"
        },
        {
            title: "Voice Narration",
            description: "Transform any explanation into podcast-style audio. Learn on-the-go with natural, engaging voice narration of your study material.",
            color: "#059669",
            emoji: "🎧"
        },
        {
            title: "Adaptive Learning Feedback",
            description: "Your AI tutor remembers everything. It tracks your progress and gives tailored recommendations to fill knowledge gaps.",
            color: "#d97706",
            emoji: "📊"
        },
        {
            title: "Multi-Subject Mastery",
            description: "From Science to Mathematics to History — Wispen handles it all. One intelligent tutor for all your academic needs.",
            color: "#dc2626",
            emoji: "🌍"
        }
    ];

    const workflowSteps = [
        { step: "1", title: "Ask Anything", desc: "Type your question in natural language. 'Explain photosynthesis for a 7th grader' or 'What is the Pythagoras theorem?'" },
        { step: "2", title: "Smart Understanding", desc: "Wispen identifies your topic and learning level instantly, preparing a tailored response just for you." },
        { step: "3", title: "Personalized Explanation", desc: "Receive clear, structured explanations adapted to your education level and preferred learning style." },
        { step: "4", title: "Visual Magic", desc: "Complex concepts transform into videos and diagrams — see photosynthesis happen, watch triangles solve themselves!" },
        { step: "5", title: "Test Your Knowledge", desc: "AI-generated quizzes appear automatically. Multiple choice, fill-in-the-blank, and reasoning questions with detailed solutions." },
        { step: "6", title: "Level Up", desc: "Based on your performance, future explanations adapt — getting smarter with every interaction." }
    ];

    const applications = [
        { icon: "🏫", title: "Schools & Colleges", desc: "Virtual AI tutor that adapts to every student's pace and understanding." },
        { icon: "📚", title: "Self-Learners", desc: "Perfect for exam prep or independent study with personalized feedback." },
        { icon: "🎓", title: "EdTech Integration", desc: "Seamlessly integrates with existing e-learning platforms for dynamic content." },
        { icon: "💼", title: "Corporate Training", desc: "Adaptive learning modules for employee skill development." }
    ];

    return (
        <div style={{
            minHeight: '100vh',
            background: '#ffffff',
            color: '#1e293b',
            fontFamily: '"Outfit", sans-serif',
            padding: '80px 20px',
            position: 'relative',
            overflowX: 'hidden'
        }}>
            {/* Background Decorations */}
            <BackgroundDoodles />
            <ParticleSystem />

            {/* Stationery Items */}
            <div className="stationery-container" style={{ position: 'fixed', inset: 0, pointerEvents: 'none', opacity: 0.5 }}>
                <div className="stationery-item pencil" style={{ top: '10%', left: '5%', transform: 'rotate(-20deg)', position: 'absolute' }} />
                <div className="stationery-item ruler" style={{ top: '60%', right: '5%', transform: 'rotate(15deg)', position: 'absolute' }} />
                <div className="stationery-item test-tube-1" style={{ bottom: '10%', left: '10%', position: 'absolute' }} />
                <div className="stationery-item protractor" style={{ top: '25%', right: '12%', position: 'absolute' }} />
            </div>

            <div style={{ maxWidth: '1200px', margin: '0 auto', position: 'relative', zIndex: 1 }}>

                {/* Hero Header */}
                <motion.div
                    initial={{ opacity: 0, y: -30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8 }}
                    style={{ textAlign: 'center', marginBottom: '60px' }}
                >
                    <h1 style={{
                        fontSize: '3.5rem',
                        fontWeight: 800,
                        marginBottom: '15px',
                        color: '#1e293b',
                        fontFamily: '"Indie Flower", cursive'
                    }}>
                        ✨ Meet Your AI Tutor
                    </h1>
                    <p style={{ fontSize: '1.3rem', color: '#64748b', maxWidth: '700px', margin: '0 auto', lineHeight: 1.6 }}>
                        Learning reimagined. An intelligent, adaptive assistant that explains concepts at YOUR level,
                        brings lessons to life with visuals, and tests you with personalized quizzes.
                    </p>
                </motion.div>

                {/* The Problem Section */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.3 }}
                    style={{
                        background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
                        padding: '40px',
                        borderRadius: '24px',
                        marginBottom: '60px',
                        textAlign: 'center'
                    }}
                >
                    <h2 style={{ fontSize: '1.8rem', fontWeight: 700, marginBottom: '15px', color: '#92400e' }}>
                        🤔 The Problem with Traditional Learning
                    </h2>
                    <p style={{ fontSize: '1.1rem', color: '#78350f', maxWidth: '800px', margin: '0 auto', lineHeight: 1.7 }}>
                        Static textbooks. One-size-fits-all videos. No feedback on what you actually need to study.
                        Traditional e-learning doesn't adapt to <strong>your</strong> pace, <strong>your</strong> comprehension,
                        or <strong>your</strong> learning style. Until now.
                    </p>
                </motion.div>

                {/* How It Works - Workflow */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.5 }}
                    style={{ marginBottom: '80px' }}
                >
                    <h2 style={{ textAlign: 'center', fontSize: '2.2rem', fontWeight: 700, marginBottom: '40px', color: '#1e293b' }}>
                        🚀 How The Magic Happens
                    </h2>
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                        gap: '25px'
                    }}>
                        {workflowSteps.map((item, i) => (
                            <motion.div
                                key={i}
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: 0.6 + i * 0.1 }}
                                style={{
                                    background: 'white',
                                    padding: '28px',
                                    borderRadius: '20px',
                                    boxShadow: '0 8px 25px rgba(0,0,0,0.04)',
                                    border: '1px solid #f1f5f9',
                                    position: 'relative'
                                }}
                            >
                                <div style={{
                                    position: 'absolute',
                                    top: '-15px',
                                    left: '20px',
                                    background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
                                    color: 'white',
                                    width: '36px',
                                    height: '36px',
                                    borderRadius: '50%',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    fontWeight: 700,
                                    fontSize: '1rem'
                                }}>
                                    {item.step}
                                </div>
                                <h4 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '8px', marginTop: '10px', color: '#1e293b' }}>
                                    {item.title}
                                </h4>
                                <p style={{ color: '#64748b', fontSize: '0.9rem', lineHeight: 1.5, margin: 0 }}>
                                    {item.desc}
                                </p>
                            </motion.div>
                        ))}
                    </div>
                </motion.div>

                {/* Core Features Grid */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.7 }}
                    style={{ marginBottom: '80px' }}
                >
                    <h2 style={{ textAlign: 'center', fontSize: '2.2rem', fontWeight: 700, marginBottom: '40px', color: '#1e293b' }}>
                        💡 Powerful Features
                    </h2>
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                        gap: '30px'
                    }}>
                        {coreFeatures.map((f, i) => (
                            <motion.div
                                key={i}
                                initial={{ opacity: 0, y: 30 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ duration: 0.5, delay: 0.8 + i * 0.1 }}
                                whileHover={{ scale: 1.02, boxShadow: '0 15px 40px rgba(0,0,0,0.08)' }}
                                style={{
                                    background: 'white',
                                    padding: '35px',
                                    borderRadius: '24px',
                                    boxShadow: '0 8px 25px rgba(0,0,0,0.04)',
                                    border: '1px solid #f1f5f9',
                                    cursor: 'default'
                                }}
                            >
                                <div style={{
                                    fontSize: '2.5rem',
                                    marginBottom: '18px'
                                }}>
                                    {f.emoji}
                                </div>
                                <h3 style={{ fontSize: '1.3rem', fontWeight: 700, marginBottom: '10px', color: f.color }}>
                                    {f.title}
                                </h3>
                                <p style={{ color: '#64748b', lineHeight: 1.6, fontSize: '0.95rem', margin: 0 }}>
                                    {f.description}
                                </p>
                            </motion.div>
                        ))}
                    </div>
                </motion.div>

                {/* Example Section */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.9 }}
                    style={{
                        background: 'linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%)',
                        padding: '50px 40px',
                        borderRadius: '28px',
                        marginBottom: '80px'
                    }}
                >
                    <h2 style={{ textAlign: 'center', fontSize: '2rem', fontWeight: 700, marginBottom: '30px', color: '#3730a3' }}>
                        🌟 See It In Action
                    </h2>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '30px' }}>
                        <div style={{ background: 'white', padding: '30px', borderRadius: '20px' }}>
                            <h4 style={{ color: '#4f46e5', marginBottom: '12px', fontSize: '1.1rem' }}>📗 Science Example</h4>
                            <p style={{ color: '#475569', fontSize: '0.9rem', marginBottom: '8px' }}>
                                <strong>You ask:</strong> "Explain photosynthesis for a 7th grader with visuals"
                            </p>
                            <p style={{ color: '#64748b', fontSize: '0.85rem', lineHeight: 1.5 }}>
                                <strong>Wispen delivers:</strong> A clear explanation, a video of sunlight hitting leaves
                                and oxygen bubbles forming, plus a quiz asking "What gas is released?" with full explanations.
                            </p>
                        </div>
                        <div style={{ background: 'white', padding: '30px', borderRadius: '20px' }}>
                            <h4 style={{ color: '#4f46e5', marginBottom: '12px', fontSize: '1.1rem' }}>📐 Math Example</h4>
                            <p style={{ color: '#475569', fontSize: '0.9rem', marginBottom: '8px' }}>
                                <strong>You ask:</strong> "Explain Pythagoras Theorem for 10th grade"
                            </p>
                            <p style={{ color: '#64748b', fontSize: '0.85rem', lineHeight: 1.5 }}>
                                <strong>Wispen delivers:</strong> Visual diagrams of right triangles with labeled sides,
                                the formula explained step-by-step, and practice problems like "If sides are 3 and 4, find the hypotenuse."
                            </p>
                        </div>
                    </div>
                </motion.div>

                {/* Applications Section */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 1.0 }}
                    style={{ marginBottom: '80px' }}
                >
                    <h2 style={{ textAlign: 'center', fontSize: '2rem', fontWeight: 700, marginBottom: '35px', color: '#1e293b' }}>
                        🎯 Who Is This For?
                    </h2>
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                        gap: '20px'
                    }}>
                        {applications.map((app, i) => (
                            <motion.div
                                key={i}
                                whileHover={{ y: -5 }}
                                style={{
                                    background: 'white',
                                    padding: '25px',
                                    borderRadius: '18px',
                                    textAlign: 'center',
                                    boxShadow: '0 5px 20px rgba(0,0,0,0.03)',
                                    border: '1px solid #f1f5f9'
                                }}
                            >
                                <div style={{ fontSize: '2.5rem', marginBottom: '12px' }}>{app.icon}</div>
                                <h4 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '8px', color: '#1e293b' }}>{app.title}</h4>
                                <p style={{ color: '#64748b', fontSize: '0.85rem', margin: 0, lineHeight: 1.5 }}>{app.desc}</p>
                            </motion.div>
                        ))}
                    </div>
                </motion.div>

                {/* CTA Section */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 1.1 }}
                    style={{
                        textAlign: 'center',
                        background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
                        padding: '50px 40px',
                        borderRadius: '28px',
                        color: 'white'
                    }}
                >
                    <h2 style={{ fontSize: '2rem', fontWeight: 700, marginBottom: '15px' }}>
                        Ready to Transform How You Learn?
                    </h2>
                    <p style={{ fontSize: '1.1rem', opacity: 0.9, marginBottom: '30px', maxWidth: '500px', margin: '0 auto 30px' }}>
                        Join thousands of students who've made learning engaging, effective, and actually fun.
                    </p>
                    <div style={{ display: 'flex', gap: '20px', justifyContent: 'center', flexWrap: 'wrap' }}>
                        <button
                            onClick={() => navigate('/')}
                            style={{
                                background: 'rgba(255,255,255,0.15)',
                                border: '2px solid rgba(255,255,255,0.4)',
                                color: 'white',
                                padding: '16px 40px',
                                borderRadius: '20px',
                                fontSize: '1rem',
                                fontWeight: 700,
                                cursor: 'pointer',
                                transition: 'all 0.2s'
                            }}
                        >
                            ← Back Home
                        </button>
                        <button
                            onClick={() => navigate('/login')}
                            style={{
                                background: 'white',
                                border: 'none',
                                color: '#6366f1',
                                padding: '16px 40px',
                                borderRadius: '20px',
                                fontSize: '1rem',
                                fontWeight: 700,
                                cursor: 'pointer',
                                boxShadow: '0 10px 25px rgba(0,0,0,0.15)',
                                transition: 'transform 0.2s'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
                            onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
                        >
                            Start Learning Free 🚀
                        </button>
                    </div>
                </motion.div>
            </div>

            <style dangerouslySetInnerHTML={{
                __html: `
                .stationery-item { width: 60px; height: 60px; background-size: contain; background-repeat: no-repeat; transform-origin: center; animation: float 6s ease-in-out infinite; }
                .pencil { background-image: url("https://cdn-icons-png.flaticon.com/512/588/588395.png"); }
                .ruler { background-image: url("https://cdn-icons-png.flaticon.com/512/2852/2852277.png"); }
                .test-tube-1 { background-image: url("https://cdn-icons-png.flaticon.com/512/2611/2611358.png"); }
                .protractor { background-image: url("https://cdn-icons-png.flaticon.com/512/2852/2852264.png"); }
                @keyframes float {
                    0%, 100% { transform: translateY(0) rotate(var(--rot, 0deg)); }
                    50% { transform: translateY(-20px) rotate(calc(var(--rot, 0deg) + 5deg)); }
                }
            `}} />
        </div>
    );
};

export default HowItWorks;
