import { useState, useEffect } from 'react';
import type { EventType } from '../../hooks/useCalendarData';

interface AddItemModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (subject: string, note: string) => void;
    type: EventType | null;
}

const AddItemModal = ({ isOpen, onClose, onSave, type }: AddItemModalProps) => {
    const [subject, setSubject] = useState('');
    const [note, setNote] = useState('');

    useEffect(() => {
        if (isOpen) {
            setSubject('');
            setNote('');
        }
    }, [isOpen]);

    if (!isOpen) return null;

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (subject.trim()) {
            onSave(subject, note);
        }
    };

    const getTitle = () => {
        switch (type) {
            case 'test': return 'Add New Test 📝';
            case 'homework': return 'Add Homework 📚';
            case 'project': return 'Add Project 🚀';
            default: return 'Add Item';
        }
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="add-modal" onClick={e => e.stopPropagation()}>
                <h2 className="modal-title">{getTitle()}</h2>
                <form onSubmit={handleSubmit}>
                    <input
                        className="modal-input"
                        type="text"
                        placeholder="Subject (e.g. Math)"
                        value={subject}
                        onChange={e => setSubject(e.target.value)}
                        autoFocus
                    />
                    <input
                        className="modal-input"
                        type="text"
                        placeholder="Details (e.g. Chapter 5)"
                        value={note}
                        onChange={e => setNote(e.target.value)}
                    />
                    <div className="modal-actions">
                        <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
                        <button type="submit" className="btn-primary">Save to Calendar</button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default AddItemModal;
