import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { onAuthStateChanged } from 'firebase/auth';
import { auth } from '../../firebase';
// Force Refresh
import './Dashboard.css';
import Calendar from './Calendar';
import Sidebar from './Sidebar';
import AddItemModal from './AddItemModal';
import Journal from './Journal';
import { useCalendarData, type EventType } from '../../hooks/useCalendarData';

interface DashboardProps {
    onEnterChat?: (sessionId: string) => void;
    onExit?: () => void;
}

const Dashboard = ({ onEnterChat, onExit }: DashboardProps) => {
    const navigate = useNavigate();
    // State for Calendar View
    const [currentDate, setCurrentDate] = useState(new Date());

    // State for Tabs
    const [activeTab, setActiveTab] = useState<'tasks' | 'journal'>('tasks');

    // Auth State
    const [userName, setUserName] = useState<string | null>(null);

    // State for Interaction
    const [interactionMode, setInteractionMode] = useState<'view' | 'selecting'>('view');
    const [pendingItemType, setPendingItemType] = useState<EventType | null>(null);
    const [selectedDate, setSelectedDate] = useState<Date | null>(null);
    const [isModalOpen, setIsModalOpen] = useState(false);

    // Data Hook
    const { events, addEvent, deleteEvent } = useCalendarData();

    // Auth Protection
    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, (user) => {
            if (user) {
                setUserName(user.displayName || 'Explorer');
            } else {
                // Not logged in -> Redirect to Login
                navigate('/login');
            }
        });

        return () => unsubscribe();
    }, [navigate]);

    // Handlers
    const handleMonthChange = (direction: number) => {
        const newDate = new Date(currentDate);
        newDate.setMonth(currentDate.getMonth() + direction);
        setCurrentDate(newDate);
    };

    const handleInitiateAdd = (type: EventType) => {
        setPendingItemType(type);
        setInteractionMode('selecting');
        // If in journal tab, maybe switch to tasks to pick date? 
        // Or just let user pick date. 
        // For now, let's switch to tasks to make it obvious
        setActiveTab('tasks');
    };

    const handleDateClick = (date: Date) => {
        if (interactionMode === 'selecting') {
            setSelectedDate(date);
            setInteractionMode('view');
            setIsModalOpen(true);
        }
    };

    const handleSaveItem = (subject: string, note: string) => {
        if (selectedDate && pendingItemType) {
            addEvent(selectedDate, pendingItemType, subject, note);
            setIsModalOpen(false);
            setPendingItemType(null);
            setSelectedDate(null);
        }
    };

    const handleCancelAdd = () => {
        setIsModalOpen(false);
        setPendingItemType(null);
        setSelectedDate(null);
        setInteractionMode('view');
    };

    // Keyboard Shortcuts
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            // Ignore if input is focused
            if (['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement).tagName)) return;

            if (e.ctrlKey || e.metaKey) {
                switch (e.key.toLowerCase()) {
                    case 'h':
                        e.preventDefault();
                        handleInitiateAdd('homework');
                        break;
                    case 't':
                        e.preventDefault();
                        handleInitiateAdd('test');
                        break;
                    case 'p':
                        e.preventDefault();
                        handleInitiateAdd('project');
                        break;
                }
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, []);

    return (
        <div className="dashboard-container">
            {/* Main Canvas */}
            <main className="dashboard-main">
                <header style={{ marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h1 style={{ fontFamily: 'Indie Flower', fontSize: '2rem', color: '#333', margin: 0 }}>
                        Welcome back, {userName}!
                    </h1>
                </header>

                {/* Tabs */}
                <div className="dashboard-tabs">
                    <button
                        className={`tab-btn ${activeTab === 'tasks' ? 'active' : ''}`}
                        onClick={() => setActiveTab('tasks')}
                    >
                        My Calendar
                    </button>
                    <button
                        className={`tab-btn ${activeTab === 'journal' ? 'active' : ''}`}
                        onClick={() => setActiveTab('journal')}
                    >
                        My Journal
                    </button>
                </div>

                <div className="dashboard-content" style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden' }}>
                    {activeTab === 'tasks' ? (
                        <Calendar
                            currentDate={currentDate}
                            events={events}
                            onDateClick={handleDateClick}
                            onMonthChange={handleMonthChange}
                            isSelectionMode={interactionMode === 'selecting'}
                            onDeleteEvent={deleteEvent}
                        />
                    ) : (
                        <Journal />
                    )}
                </div>
            </main>

            {/* Right Sidebar */}
            <Sidebar onInitiateAdd={handleInitiateAdd} onEnterChat={onEnterChat} onExit={onExit} />

            {/* Modal */}
            <AddItemModal
                isOpen={isModalOpen}
                onClose={handleCancelAdd}
                onSave={handleSaveItem}
                type={pendingItemType}
            />

            {/* Toast / Cursor Instruction */}
            {interactionMode === 'selecting' && (
                <div style={{
                    position: 'fixed',
                    bottom: '30px',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    background: 'rgba(0,0,0,0.8)',
                    color: 'white',
                    padding: '10px 20px',
                    borderRadius: '30px',
                    zIndex: 200,
                    pointerEvents: 'none',
                    animation: 'pop-in 0.3s'
                }}>
                    Select a date on the calendar to add {pendingItemType}...
                </div>
            )}
        </div>
    );
};

export default Dashboard;
