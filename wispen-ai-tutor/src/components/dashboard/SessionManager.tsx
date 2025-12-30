import { motion } from 'framer-motion';
import { useSessions } from '../../hooks/useSessions';
import { auth } from '../../firebase';
import { API_BASE_URL } from '../../config';

interface SessionManagerProps {
    onStartSession?: (sessionId: string) => void;
}

const SessionManager = ({ onStartSession }: SessionManagerProps) => {
    // Real Sessions Hook
    const { sessions, loading, error: sessionsError, deleteSession } = useSessions();

    const handleStartSession = async () => {
        if (!onStartSession) return;

        try {
            // Get current user token if possible, but here we might rely on the cookie/auth state managed by firebase/backend
            // Since we are in frontend, we need to send the token.
            // But wait, the backend uses `get_user_from_token` which usually expects Authorization header.
            // Let's assume global auth state or simplistic fetch for now as in other components.
            // Actually, we need the auth token.
            const user = auth.currentUser;
            if (!user) {
                alert("Please log in to start a session");
                return;
            }
            const token = await user.getIdToken();

            const response = await fetch(`${API_BASE_URL}/sessions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    subject: 'Untitled', // Default subject
                    duration: '0m' // Start with 0m
                })
            });

            if (response.ok) {
                const data = await response.json();
                onStartSession(data.id);
            } else {
                console.error('Failed to create session');
                alert('Could not create session. Please try again.');
            }
        } catch (error) {
            console.error('Error creating session:', error);
            alert('Error creating session.');
        }
    };

    const formatDate = (dateStr: string) => {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        // Simple "Today", "Yesterday" or Date string logic could be added here
        // For now, standard locale string
        return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    };

    const handleDelete = (e: React.MouseEvent, sessionId: string) => {
        e.stopPropagation();
        if (confirm('Are you sure you want to delete this session?')) {
            deleteSession(sessionId);
        }
    };

    return (
        <div className="session-section">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <h3 style={{ margin: 0 }}>Focus Session ⏱️</h3>
            </div>

            <motion.button
                className="session-btn"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleStartSession}
            >
                <span>▶</span> Start New Session
            </motion.button>

            <div className="previous-sessions">
                <h4 style={{ margin: '0 0 10px 0', fontSize: '0.9rem', color: '#888', textTransform: 'uppercase', letterSpacing: '1px' }}>
                    Previous Sessions
                </h4>
                {loading ? (
                    <div style={{ color: '#999', fontSize: '0.9rem' }}>Loading...</div>
                ) : sessionsError ? (
                    <div style={{ color: '#f66', fontSize: '0.9rem' }}>{sessionsError}</div>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                        {sessions.length === 0 ? (
                            <div style={{ color: '#aaa', fontStyle: 'italic', fontSize: '0.9rem' }}>No sessions yet. Time to study!</div>
                        ) : (
                            sessions.map(session => (
                                <motion.div
                                    key={session.id}
                                    className="prev-session-item"
                                    onClick={() => onStartSession && onStartSession(session.id)}
                                    whileHover={{ backgroundColor: '#f9f9f9', scale: 1.01 }}
                                    style={{ cursor: 'pointer', position: 'relative' }}
                                >
                                    <div style={{ flex: 1 }}>
                                        <span style={{ fontWeight: 'bold', color: '#555', display: 'block' }}>{session.subject}</span>
                                        <div style={{ display: 'flex', gap: '10px', fontSize: '0.85rem' }}>
                                            <span>{session.duration}</span>
                                            <span style={{ opacity: 0.5 }}>{formatDate(session.date)}</span>
                                        </div>
                                    </div>
                                    <button
                                        className="delete-session-btn"
                                        onClick={(e) => handleDelete(e, session.id)}
                                        title="Delete Session"
                                        style={{
                                            background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.1rem',
                                            opacity: 0.3, transition: 'opacity 0.2s', padding: '5px'
                                        }}
                                        onMouseEnter={(e) => (e.currentTarget.style.opacity = '1')}
                                        onMouseLeave={(e) => (e.currentTarget.style.opacity = '0.3')}
                                    >
                                        🗑️
                                    </button>
                                </motion.div>
                            ))
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default SessionManager;
