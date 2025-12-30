import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { CalendarEvent } from '../../hooks/useCalendarData';

interface CalendarProps {
    currentDate: Date;
    events: CalendarEvent[];
    onDateClick: (date: Date) => void;
    onMonthChange: (direction: number) => void;
    isSelectionMode: boolean;
    onDeleteEvent: (id: string) => void;
}

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
];

const Calendar = ({ currentDate, events, onDateClick, onMonthChange, isSelectionMode, onDeleteEvent }: CalendarProps) => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();

    // Hover State for "Stylized Window"
    const [hoveredEvent, setHoveredEvent] = useState<{ event: CalendarEvent; x: number; y: number } | null>(null);

    // Calendar Generation Logic
    const getDaysInMonth = (y: number, m: number) => new Date(y, m + 1, 0).getDate();
    const getFirstDayOfMonth = (y: number, m: number) => new Date(y, m, 1).getDay();

    const daysInMonth = getDaysInMonth(year, month);
    const firstDay = getFirstDayOfMonth(year, month);

    // Create grid array (padding + days)
    const daysArray = [];
    for (let i = 0; i < firstDay; i++) daysArray.push(null);
    for (let i = 1; i <= daysInMonth; i++) daysArray.push(new Date(year, month, i));

    const getEventsForDate = (date: Date) => {
        return events.filter(e =>
            e.date.getDate() === date.getDate() &&
            e.date.getMonth() === date.getMonth() &&
            e.date.getFullYear() === date.getFullYear()
        );
    };

    const isToday = (date: Date) => {
        const today = new Date();
        return date.getDate() === today.getDate() &&
            date.getMonth() === today.getMonth() &&
            date.getFullYear() === today.getFullYear();
    };

    const getLoadClass = (count: number) => {
        if (count === 0) return '';
        if (count <= 2) return 'load-low';
        return 'load-high';
    };

    return (
        <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            {/* Header / Config */}
            <div className="calendar-header-controls">
                <button className="nav-btn" onClick={() => onMonthChange(-1)}>←</button>
                <h2 style={{ minWidth: '200px', textAlign: 'center', margin: 0 }}>
                    {MONTH_NAMES[month]} {year}
                </h2>
                <button className="nav-btn" onClick={() => onMonthChange(1)}>→</button>

                {isSelectionMode && (
                    <div style={{ marginLeft: 'auto', background: 'var(--dream-pink)', color: 'white', padding: '5px 15px', borderRadius: '20px', fontWeight: 'bold' }}>
                        Select a date to add item...
                    </div>
                )}
            </div>

            {/* Grid */}
            <div className="calendar-month-grid">
                {DAYS.map(day => (
                    <div key={day} className="weekday-header">{day}</div>
                ))}

                <AnimatePresence mode="popLayout">
                    {daysArray.map((date, i) => {
                        if (!date) return <div key={`empty-${i}`} className="calendar-cell empty" style={{ background: 'transparent', boxShadow: 'none' }} />;

                        const dayEvents = getEventsForDate(date);
                        const isCurrentDay = isToday(date);
                        const loadClass = getLoadClass(dayEvents.length);

                        return (
                            <motion.div
                                key={date.toISOString()}
                                className={`calendar-cell ${loadClass} ${isSelectionMode ? 'date-selectable' : ''} ${isCurrentDay ? 'today' : ''}`}
                                onClick={() => onDateClick(date)}
                                initial={{ opacity: 0, scale: 0.9 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ delay: i * 0.01 }}
                            >
                                <div className={`cell-date-num ${date.getDay() === 0 || date.getDay() === 6 ? 'pale' : ''}`}>
                                    {date.getDate()}
                                </div>

                                {/* Events Container */}
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                    {dayEvents.map(event => (
                                        <div
                                            key={event.id}
                                            className={`event-item event-${event.type}`}
                                            // Removed 'title' attribute to use custom popup
                                            onMouseEnter={(e) => {
                                                const rect = e.currentTarget.getBoundingClientRect();
                                                setHoveredEvent({
                                                    event,
                                                    x: rect.left + window.scrollX + 20,
                                                    y: rect.top + window.scrollY - 80
                                                });
                                            }}
                                            onMouseLeave={() => setHoveredEvent(null)}
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                if (confirm(`Delete ${event.subject}?`)) {
                                                    onDeleteEvent(event.id);
                                                }
                                            }}
                                            style={{ display: 'flex', alignItems: 'center', gap: '4px', justifyContent: 'center' }}
                                        >
                                            {event.completed && <span>✓</span>}
                                            {event.subject}
                                        </div>
                                    ))}
                                </div>
                            </motion.div>
                        );
                    })}
                </AnimatePresence>
            </div>

            {/* Global Calendar Hover Popup */}
            <AnimatePresence>
                {hoveredEvent && (
                    <motion.div
                        className="calendar-hover-popup"
                        style={{ top: hoveredEvent.y, left: hoveredEvent.x }}
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.8 }}
                    >
                        <strong style={{ color: 'var(--dream-pink)' }}>{hoveredEvent.event.subject}</strong>
                        <div style={{ fontSize: '0.85rem', color: '#666', marginTop: '5px' }}>
                            {hoveredEvent.event.note || 'No details added.'}
                        </div>
                        <div style={{ fontSize: '0.7rem', color: '#999', marginTop: '8px', fontStyle: 'italic' }}>
                            {hoveredEvent.event.type.toUpperCase()} • {hoveredEvent.event.completed ? 'DONE' : 'PENDING'}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default Calendar;
