import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import type { EventType } from '../../hooks/useCalendarData';
import SessionManager from './SessionManager';
import { useUserStats } from '../../hooks/useUserStats';
import { auth } from '../../firebase';
import { API_BASE_URL } from '../../config';

interface Quest {
    subject: string;
    task: string;
}

interface SidebarProps {
    onInitiateAdd: (type: EventType) => void;
    onEnterChat?: (sessionId: string) => void;
    onExit?: () => void;
}

const Sidebar = ({ onInitiateAdd, onEnterChat, onExit }: SidebarProps) => {
    // Real Stats Hook
    const { stats, error: statsError } = useUserStats();

    // AI-Generated Quests
    const [quests, setQuests] = useState<Quest[]>([]);
    const [questsLoading, setQuestsLoading] = useState(true);

    // Fetch AI-generated quests
    useEffect(() => {
        const fetchQuests = async () => {
            if (!auth.currentUser) return;
            try {
                const token = await auth.currentUser.getIdToken();
                const response = await fetch(`${API_BASE_URL}/daily_quests`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (response.ok) {
                    const data = await response.json();
                    setQuests(data.quests || []);
                }
            } catch (err) {
                console.error('Failed to fetch quests:', err);
            } finally {
                setQuestsLoading(false);
            }
        };

        const unsubscribe = auth.onAuthStateChanged((user) => {
            if (user) fetchQuests();
        });

        return () => unsubscribe();
    }, []);

    // XP Logic
    const nextLevel = 1000; // Fixed next level for now
    const progress = Math.min((stats.xp / nextLevel) * 100, 100);
    const level = Math.floor(stats.xp / 1000) + 1;

    // Time Formatting
    const formatTime = (minutes: number) => {
        if (minutes < 60) return `${minutes}m`;
        const hrs = Math.floor(minutes / 60);
        const mins = minutes % 60;
        return `${hrs}h ${mins}m`;
    };

    return (
        <div className="dashboard-sidebar">
            <div className="sidebar-scroll-area">
                {/* Home Button (Top Right equivalent) */}
                <div style={{ padding: '0 0 15px 0', borderBottom: '1px solid #eee', marginBottom: '15px' }}>
                    <button
                        onClick={onExit}
                        style={{
                            width: '100%',
                            background: 'white',
                            border: '1px solid #ddd',
                            color: '#555',
                            padding: '10px',
                            borderRadius: '12px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '8px',
                            fontWeight: 'bold',
                            boxShadow: '0 2px 5px rgba(0,0,0,0.05)',
                            fontFamily: '"Outfit", sans-serif'
                        }}
                    >
                        🏠 Home
                    </button>
                </div>

                {/* Profile / XP Section */}
                <div className="sidebar-section">
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '15px' }}>
                        <div style={{ width: '50px', height: '50px', borderRadius: '50%', background: '#eee', marginRight: '15px', fontSize: '2rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            🧙‍♂️
                        </div>
                        <div>
                            <h3 style={{ margin: 0 }}>Level {level} Scholar</h3>
                            <div style={{ fontSize: '0.8rem', color: statsError ? '#f66' : '#666' }}>
                                {statsError || `${stats.xp}/${nextLevel} XP`}
                            </div>
                        </div>
                    </div>
                    <div style={{ width: '100%', height: '10px', background: '#eee', borderRadius: '5px', overflow: 'hidden' }}>
                        <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${progress}%` }}
                            transition={{ duration: 1.5, ease: "easeOut" }}
                            style={{ height: '100%', background: 'linear-gradient(90deg, #ff9a9e 0%, #fecfef 99%, #fecfef 100%)' }}
                        />
                    </div>
                </div>

                {/* Streak Section */}
                <motion.div
                    className="streak-card"
                    whileHover={{ scale: 1.02 }}
                >
                    <div style={{ fontSize: '2rem', marginBottom: '5px' }}>🔥 {stats.streak} Days</div>
                    <div>Streak! Keep it up!</div>
                    <div style={{ marginTop: '10px', fontSize: '1rem', fontWeight: 'bold', color: '#fff', textShadow: '0 1px 2px rgba(0,0,0,0.1)' }}>
                        {formatTime(stats.time_spent_today)} studied today
                    </div>
                </motion.div>

                {/* Today's Quests - AI Generated */}
                <div className="sidebar-section">
                    <h3 style={{ marginTop: 0 }}>Today's Quest 🛡️</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        {questsLoading ? (
                            <div style={{ padding: '15px', textAlign: 'center', color: '#999', fontSize: '0.9rem' }}>
                                ✨ Crafting your quests...
                            </div>
                        ) : quests.length > 0 ? (
                            quests.map((quest, idx) => (
                                <QuestItem key={idx} subject={quest.subject} task={quest.task} />
                            ))
                        ) : (
                            <div style={{ padding: '15px', textAlign: 'center', color: '#999', fontSize: '0.9rem' }}>
                                No quests yet. Start studying!
                            </div>
                        )}
                    </div>
                </div>

                {/* Session Manager (New & Previous Sessions) */}
                <SessionManager onStartSession={onEnterChat} />
            </div>

            {/* Quick Actions - Sticky Footer */}
            <div className="quick-add-container">
                <h3 style={{ marginTop: 0, position: 'relative', zIndex: 1 }}>Quick Add</h3>
                <button
                    className="quick-add-btn"
                    onClick={() => onInitiateAdd('homework')}
                    style={{ background: 'linear-gradient(135deg, #f6d365 0%, #fda085 100%)' }}
                    title="Ctrl + H"
                >
                    <span>📚</span> Add Homework
                </button>
                <button
                    className="quick-add-btn"
                    onClick={() => onInitiateAdd('project')}
                    style={{ background: 'linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%)' }}
                    title="Ctrl + P"
                >
                    <span>🚀</span> Add Project
                </button>
                <button
                    className="quick-add-btn"
                    onClick={() => onInitiateAdd('test')}
                    style={{ background: 'linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%)' }}
                    title="Ctrl + T"
                >
                    <span>📝</span> Add Test
                </button>
                <div style={{ fontSize: '0.8rem', color: '#999', textAlign: 'center', marginTop: '5px' }}>
                    (Shortcuts: Ctrl + H/P/T)
                </div>
            </div>
        </div>
    );
};

interface QuestItemProps {
    subject: string;
    task: string;
}

const QuestItem = ({ subject, task }: QuestItemProps) => {
    // Dynamic colors based on subject keywords
    const getSubjectColor = (subject: string) => {
        const s = subject.toLowerCase();
        if (s.includes('math') || s.includes('algebra') || s.includes('geometry')) return 'var(--subject-math, #4dabf7)';
        if (s.includes('science') || s.includes('physics') || s.includes('chemistry') || s.includes('biology')) return 'var(--subject-science, #69db7c)';
        if (s.includes('english') || s.includes('language') || s.includes('writing')) return 'var(--subject-english, #ffd43b)';
        if (s.includes('history') || s.includes('social')) return '#da77f2';
        return '#adb5bd';
    };

    return (
        <div
            className="task-card"
            style={{
                borderLeftColor: getSubjectColor(subject),
                position: 'relative'
            }}
        >
            <div style={{ fontWeight: 'bold' }}>• {subject}</div>
            <div style={{ paddingLeft: '10px', color: '#555' }}>{task}</div>
        </div>
    );
};

export default Sidebar;
