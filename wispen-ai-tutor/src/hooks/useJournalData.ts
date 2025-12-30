import { useState, useEffect } from 'react';
import { auth } from '../firebase';
import { onAuthStateChanged } from 'firebase/auth';
import type { CalendarEvent } from './useCalendarData';

import { API_BASE_URL } from '../config';

const API_URL = API_BASE_URL;

export const useJournalData = () => {
    const [entries, setEntries] = useState<CalendarEvent[]>([]);
    const [loading, setLoading] = useState(true);

    const getToken = async () => {
        if (auth.currentUser) {
            return await auth.currentUser.getIdToken();
        }
        return null;
    };

    const fetchEntries = async () => {
        try {
            const token = await getToken();
            if (!token) return;

            const response = await fetch(`${API_URL}/journal`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const data = await response.json();
                // Parse dates
                const parsed = data.map((e: any) => ({
                    ...e,
                    date: new Date(e.date)
                }));
                setEntries(parsed);
            }
        } catch (error) {
            console.error("Failed to fetch journal entries:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, (user) => {
            if (user) {
                fetchEntries();
            } else {
                setEntries([]);
                setLoading(false);
            }
        });
        return () => unsubscribe();
    }, []);

    const addEntry = async (date: Date, type: 'homework' | 'test' | 'project', subject: string, note: string) => {
        try {
            const token = await getToken();
            if (!token) return;

            // Journal entries are usually "completed" if they are just logs, 
            // but we can reuse the boolean if needed or ignore it.
            const newEntry = {
                date: date.toISOString(),
                type,
                subject,
                note,
                completed: true
            };

            const response = await fetch(`${API_URL}/journal`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(newEntry)
            });

            if (response.ok) {
                const saved = await response.json();
                setEntries(prev => [...prev, { ...saved, date: new Date(saved.date) }]);
            }
        } catch (error) {
            console.error("Failed to add journal entry:", error);
        }
    };

    const deleteEntry = async (id: string) => {
        try {
            const token = await getToken();
            if (!token) return;

            const response = await fetch(`${API_URL}/journal/${id}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                setEntries(prev => prev.filter(e => e.id !== id));
            }
        } catch (error) {
            console.error("Failed to delete journal entry:", error);
        }
    };

    // Deleting a "Page" essentially means deleting multiple items.
    // The frontend can loop through IDs and call deleteEntry for now.

    return {
        entries,
        loading,
        addEntry,
        deleteEntry,
        refresh: fetchEntries
    };
};
