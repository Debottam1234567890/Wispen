import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { CalendarEvent } from '../../hooks/useCalendarData';
import { useJournalData } from '../../hooks/useJournalData';

const Journal = () => {
    const [isCoverOpen, setIsCoverOpen] = useState(false);
    const [pageIndex, setPageIndex] = useState(0);

    // Live Data Hook
    const { entries: historyData, addEntry, deleteEntry } = useJournalData();

    // Writing Mode State
    const [isWriting, setIsWriting] = useState(false);
    const [writingTargetDate, setWritingTargetDate] = useState<Date | null>(null); // If null, means creating NEW page

    // Form States
    const [newEntryType, setNewEntryType] = useState<'homework' | 'test' | 'project'>('homework');
    const [newEntrySubject, setNewEntrySubject] = useState('');
    const [newEntryDetails, setNewEntryDetails] = useState('');

    // New Page Date States
    const [newPageDay, setNewPageDay] = useState(new Date().getDate());
    const [newPageMonth, setNewPageMonth] = useState(new Date().getMonth());
    const [newPageYear, setNewPageYear] = useState(new Date().getFullYear());

    // Group items by date to create "Pages"
    // Sorted Chronologically (Oldest First)
    const sortedHistory = [...historyData].sort((a, b) => a.date.getTime() - b.date.getTime());

    // Grouping by Date
    const groupedPages: { date: string; dateObj: Date; items: CalendarEvent[] }[] = [];
    sortedHistory.forEach(item => {
        const dateStr = item.date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
        const existingPage = groupedPages.find(p => p.date === dateStr);
        if (existingPage) {
            existingPage.items.push(item);
        } else {
            groupedPages.push({ date: dateStr, dateObj: item.date, items: [item] });
        }
    });

    const totalPages = groupedPages.length;
    const currentPageData = groupedPages[pageIndex];

    const handleNextPage = (e: React.MouseEvent) => {
        e.stopPropagation();
        if (pageIndex < totalPages) setPageIndex(p => p + 1);
    };

    const handlePrevPage = (e: React.MouseEvent) => {
        e.stopPropagation();
        if (pageIndex > 0) setPageIndex(p => p - 1);
    };

    const startWriting = (e: React.MouseEvent, targetDate: Date | null) => {
        e.stopPropagation();
        setWritingTargetDate(targetDate);
        setIsWriting(true);
        // Reset form
        setNewEntryType('homework');
        setNewEntrySubject('');
        setNewEntryDetails('');
    };

    const handleDeleteEntry = async (e: React.MouseEvent, eventId: string) => {
        e.stopPropagation();
        if (window.confirm("Are you sure you want to delete this entry?")) {
            await deleteEntry(eventId);
        }
    };

    const handleDeletePage = async (e: React.MouseEvent) => {
        e.stopPropagation();
        if (!currentPageData) return;
        if (window.confirm(`Are you sure you want to delete the entire page for ${currentPageData.date}? All entries will be lost.`)) {
            // Delete all items on this page
            for (const item of currentPageData.items) {
                await deleteEntry(item.id);
            }
            // Adjust page index if necessary
            if (pageIndex >= totalPages - 1 && pageIndex > 0) {
                setPageIndex(p => p - 1);
            }
        }
    };

    const handleSaveEntry = async () => {
        if (!newEntrySubject || !newEntryDetails) return;

        // Determine Date
        let entryDate: Date;
        if (writingTargetDate) {
            entryDate = writingTargetDate;
        } else {
            // Construct date from inputs
            entryDate = new Date(newPageYear, newPageMonth, newPageDay);
        }

        await addEntry(entryDate, newEntryType, newEntrySubject, newEntryDetails);

        setIsWriting(false);

        // Navigation Logic after Save
        if (!writingTargetDate) {
            // Navigate to the end (new page likely added)
            // We wait a tick to allow data refresh to find the new group
            setTimeout(() => setPageIndex(groupedPages.length), 300);
        }
    };

    // Calculate Day of Week for New Page Form
    const getCalculatedDayOfWeek = () => {
        const d = new Date(newPageYear, newPageMonth, newPageDay);
        return d.toLocaleDateString('en-US', { weekday: 'long' });
    };

    return (
        <div className="diary-viewport">
            <div className="diary-binding">
                {[...Array(20)].map((_, i) => (
                    <div key={i} className="binding-ring" />
                ))}
            </div>

            <div className="diary-book">
                <AnimatePresence mode='wait'>
                    {!isCoverOpen ? (
                        <motion.div
                            key="cover"
                            className="diary-cover-front"
                            onClick={() => setIsCoverOpen(true)}
                            initial={{ rotateY: -90, opacity: 0 }}
                            animate={{ rotateY: 0, opacity: 1 }}
                            exit={{ rotateY: -100, opacity: 0, transition: { duration: 0.5 } }}
                        >
                            <div className="diary-title-card">
                                <h1 style={{ margin: 0, fontSize: '3rem' }}>My Journal</h1>
                                <p style={{ margin: 0, fontSize: '1.2rem' }}>Wispen AI Tutor</p>
                            </div>
                            {/* Clean cover, no emojis */}
                            <p style={{ color: '#aaa', marginTop: 'auto', marginBottom: '20px' }}>(Click to Open)</p>
                        </motion.div>
                    ) : (
                        <motion.div
                            key="pages"
                            className="diary-paper"
                            initial={{ rotateY: 90, opacity: 0 }}
                            animate={{ rotateY: 0, opacity: 1 }}
                            transition={{ duration: 0.6 }}
                            style={{ display: 'flex', flexDirection: 'column' }}
                        >
                            {!isWriting ? (
                                <>
                                    {/* Page Header */}
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '2px solid red', paddingBottom: '10px', marginBottom: '20px' }}>
                                        <div style={{ display: 'flex', gap: '10px', alignItems: 'baseline' }}>
                                            <span style={{ color: '#888', fontStyle: 'italic' }}>Date:</span>
                                            <span style={{ fontWeight: 'bold', fontSize: '1.5rem' }}>{currentPageData?.date || "End of Journal"}</span>
                                        </div>

                                        {/* Delete Page Button */}
                                        {currentPageData && (
                                            <button
                                                onClick={handleDeletePage}
                                                style={{ background: 'none', border: '1px solid #ff6b6b', color: '#ff6b6b', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem', padding: '2px 8px', display: 'flex', alignItems: 'center', gap: '4px' }}
                                                title="Delete this entire page"
                                            >
                                                📄 🗑️
                                            </button>
                                        )}
                                    </div>

                                    {/* Diary Entries or Empty State */}
                                    <div style={{ flex: 1, overflowY: 'auto' }}>
                                        {currentPageData ? currentPageData.items.map((item) => (
                                            <div key={item.id} style={{ marginBottom: '30px', borderBottom: '1px dashed #ddd', paddingBottom: '15px' }}>
                                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '5px' }}>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                                        <span style={{ background: item.subject.includes('AI Tutor') ? '#6c5ce7' : '#fab1a0', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '0.9rem', fontWeight: 'bold' }}>
                                                            {item.subject}
                                                        </span>
                                                        <span style={{ fontWeight: 'bold', fontSize: '0.9rem', color: '#666' }}>{item.type.toUpperCase()}</span>
                                                    </div>

                                                    {/* Delete Entry Button */}
                                                    <button
                                                        onClick={(e) => handleDeleteEntry(e, item.id)}
                                                        style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1rem', opacity: 0.6 }}
                                                        title="Delete entry"
                                                    >
                                                        🗑️
                                                    </button>
                                                </div>
                                                <p style={{ margin: 0, fontFamily: 'Indie Flower', fontSize: '1.3rem' }}>
                                                    {item.note}
                                                </p>
                                            </div>
                                        )) : (
                                            <div style={{ textAlign: 'center', color: '#999', marginTop: '50px' }}>
                                                <p style={{ fontFamily: 'Indie Flower', fontSize: '1.5rem' }}>You've reached the last page.</p>
                                                <button
                                                    onClick={(e) => startWriting(e, null)}
                                                    style={{ background: 'var(--dream-pink)', color: 'white', border: 'none', padding: '15px 30px', borderRadius: '30px', cursor: 'pointer', fontSize: '1.2rem', fontFamily: 'Indie Flower', marginTop: '20px', boxShadow: '0 4px 10px rgba(0,0,0,0.2)' }}
                                                >
                                                    ✍️ Start New Page
                                                </button>
                                            </div>
                                        )}
                                    </div>

                                    {/* Navigation */}
                                    <div style={{ position: 'absolute', bottom: '20px', width: '100%', display: 'flex', justifyContent: 'center', gap: '20px', left: 0 }}>
                                        <button
                                            onClick={handlePrevPage}
                                            disabled={pageIndex === 0}
                                            style={{ opacity: pageIndex === 0 ? 0.3 : 1, cursor: pageIndex === 0 ? 'default' : 'pointer', background: 'none', border: 'none', fontSize: '2rem' }}
                                        >
                                            ⬅️
                                        </button>
                                        <span style={{ alignSelf: 'center', color: '#888' }}>
                                            Page {pageIndex + 1} of {totalPages + 1}
                                        </span>
                                        <button
                                            onClick={handleNextPage}
                                            disabled={pageIndex >= totalPages} // Allow going one past end to write
                                            style={{ opacity: pageIndex >= totalPages ? 0.3 : 1, cursor: pageIndex >= totalPages ? 'pointer' : 'pointer', background: 'none', border: 'none', fontSize: '2rem' }}
                                        >
                                            ➡️
                                        </button>

                                        {/* Quick Write Button used to add entry to CURRENT page */}
                                        {currentPageData && (
                                            <button
                                                onClick={(e) => startWriting(e, currentPageData.dateObj)}
                                                style={{ position: 'absolute', right: '40px', background: 'none', border: 'none', fontSize: '1.5rem', cursor: 'pointer' }}
                                                title="Add another entry to this page"
                                            >
                                                ✍️
                                            </button>
                                        )}
                                    </div>
                                </>
                            ) : (
                                /* Writing Mode */
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    style={{ display: 'flex', flexDirection: 'column', height: '100%' }}
                                >
                                    <h2 style={{ color: 'var(--dream-pink)', borderBottom: '2px solid red', paddingBottom: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                        <span>Dear Diary...</span>
                                        {writingTargetDate && <span style={{ fontSize: '0.8rem', color: '#666' }}>{writingTargetDate.toDateString()}</span>}
                                    </h2>

                                    {/* New Page Date Logic (Only if NO target date) */}
                                    {!writingTargetDate && (
                                        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '15px', background: 'rgba(0,0,0,0.02)', padding: '10px', borderRadius: '8px' }}>
                                            <select value={newPageMonth} onChange={(e) => setNewPageMonth(Number(e.target.value))} style={{ fontFamily: 'Indie Flower', fontSize: '1rem', padding: '5px' }}>
                                                {["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].map((m, i) => (
                                                    <option key={m} value={i}>{m}</option>
                                                ))}
                                            </select>
                                            <input
                                                type="number" min="1" max="31"
                                                value={newPageDay} onChange={(e) => setNewPageDay(Number(e.target.value))}
                                                style={{ width: '50px', fontFamily: 'Indie Flower', fontSize: '1rem', padding: '5px' }}
                                            />
                                            <input
                                                type="number"
                                                value={newPageYear} onChange={(e) => setNewPageYear(Number(e.target.value))}
                                                style={{ width: '70px', fontFamily: 'Indie Flower', fontSize: '1rem', padding: '5px' }}
                                            />
                                            <span style={{ marginLeft: '10px', color: 'var(--dream-purple)', fontWeight: 'bold' }}>
                                                {getCalculatedDayOfWeek()}
                                            </span>
                                        </div>
                                    )}

                                    <div style={{ marginBottom: '15px', display: 'flex', gap: '10px' }}>

                                        <div style={{ flex: 1 }}>
                                            <label style={{ display: 'block', marginBottom: '5px', color: '#666' }}>Subject</label>
                                            <input
                                                type="text"
                                                value={newEntrySubject}
                                                onChange={(e) => setNewEntrySubject(e.target.value)}
                                                style={{ width: '100%', padding: '10px', fontSize: '1.1rem', fontFamily: 'Indie Flower', border: 'none', background: 'rgba(0,0,0,0.05)', borderRadius: '8px' }}
                                                placeholder="e.g. Math Quiz"
                                            />
                                        </div>

                                        <div style={{ width: '120px' }}>
                                            <label style={{ display: 'block', marginBottom: '5px', color: '#666' }}>Type</label>
                                            <select
                                                value={newEntryType}
                                                onChange={(e) => setNewEntryType(e.target.value as any)}
                                                style={{ width: '100%', padding: '10px', fontSize: '1rem', fontFamily: 'Indie Flower', border: 'none', background: 'rgba(0,0,0,0.05)', borderRadius: '8px' }}
                                            >
                                                <option value="homework">Homework</option>
                                                <option value="test">Test</option>
                                                <option value="project">Project</option>
                                            </select>
                                        </div>
                                    </div>

                                    <div style={{ flex: 1, marginBottom: '15px' }}>
                                        <label style={{ display: 'block', marginBottom: '5px', color: '#666' }}>Details</label>
                                        <textarea
                                            value={newEntryDetails}
                                            onChange={(e) => setNewEntryDetails(e.target.value)}
                                            style={{ width: '100%', height: '80%', padding: '10px', fontSize: '1.2rem', fontFamily: 'Indie Flower', border: 'none', background: 'rgba(0,0,0,0.05)', borderRadius: '8px', resize: 'none', lineHeight: '30px' }}
                                            placeholder="Tell me about it..."
                                        />
                                    </div>

                                    <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                                        <button
                                            onClick={() => setIsWriting(false)}
                                            style={{ background: '#eee', border: 'none', padding: '10px 20px', borderRadius: '15px', cursor: 'pointer', fontFamily: 'Indie Flower', fontSize: '1.1rem' }}
                                        >
                                            Cancel
                                        </button>
                                        <button
                                            onClick={handleSaveEntry}
                                            style={{ background: 'var(--dream-pink)', color: 'white', border: 'none', padding: '10px 20px', borderRadius: '15px', cursor: 'pointer', fontFamily: 'Indie Flower', fontSize: '1.1rem' }}
                                        >
                                            Save Entry
                                        </button>
                                    </div>
                                </motion.div>
                            )}

                            <button
                                onClick={() => setIsCoverOpen(false)}
                                style={{ position: 'absolute', top: '10px', right: '10px', background: 'none', border: 'none', fontSize: '1.5rem', cursor: 'pointer' }}
                                title="Close Book"
                            >
                                ✖️
                            </button>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
};

export default Journal;
