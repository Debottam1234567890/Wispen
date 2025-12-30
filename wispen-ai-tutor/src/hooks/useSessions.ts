import { useState, useEffect } from 'react';
import { auth } from '../firebase';
import { onAuthStateChanged } from 'firebase/auth';

import { API_BASE_URL } from '../config';

const API_URL = API_BASE_URL;

export interface Session {
    id: string;
    subject: string;
    duration: string;
    date: string;
}

export const useSessions = () => {
    const [sessions, setSessions] = useState<Session[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const getToken = async () => {
        if (auth.currentUser) return await auth.currentUser.getIdToken();
        return null;
    };

    const fetchSessions = async () => {
        try {
            const token = await getToken();
            if (!token) {
                console.log('[useSessions] No auth token available');
                return;
            }

            console.log('[useSessions] Fetching sessions...');
            const response = await fetch(`${API_URL}/sessions`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            console.log('[useSessions] Response status:', response.status);
            if (response.ok) {
                const data = await response.json();
                console.log('[useSessions] Sessions received:', data);
                setSessions(data);
                setError(null);
            } else {
                const errorText = await response.text();
                console.error('[useSessions] API Error:', response.status, errorText);
                setError(`Failed to load sessions (${response.status})`);
            }
        } catch (error) {
            console.error("[useSessions] Failed to fetch sessions:", error);
            setError('Network error while fetching sessions');
        } finally {
            setLoading(false);
        }
    };

    const addSession = async (subject: string, duration: string) => {
        try {
            const token = await getToken();
            if (!token) return;

            const newSession = { subject, duration };
            const response = await fetch(`${API_URL}/sessions`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(newSession)
            });

            if (response.ok) {
                const saved = await response.json();
                setSessions(prev => [saved, ...prev]);
            }
        } catch (error) {
            console.error("Failed to add session:", error);
        }
    };

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, (user) => {
            if (user) {
                fetchSessions();
            } else {
                setSessions([]);
                setLoading(false);
            }
        });
        return () => unsubscribe();
    }, []);

    const deleteSession = async (sessionId: string) => {
        try {
            const token = await getToken();
            if (!token) return;

            const response = await fetch(`${API_URL}/sessions/${sessionId}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                setSessions(prev => prev.filter(s => s.id !== sessionId));
            }
        } catch (error) {
            console.error("Failed to delete session:", error);
        }
    };

    const updateSession = async (sessionId: string, updates: Partial<Session>) => {
        try {
            const token = await getToken();
            if (!token) return;

            const response = await fetch(`${API_URL}/sessions/${sessionId}`, {
                method: 'PATCH',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(updates)
            });

            if (response.ok) {
                setSessions(prev => prev.map(s =>
                    s.id === sessionId ? { ...s, ...updates } : s
                ));
            }
        } catch (error) {
            console.error("Failed to update session:", error);
        }
    };

    return { sessions, loading, error, addSession, deleteSession, updateSession };
};
