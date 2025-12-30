import { useState, useEffect } from 'react';
import { auth } from '../firebase';
import { onAuthStateChanged } from 'firebase/auth';

import { API_BASE_URL } from '../config';
const API_URL = API_BASE_URL;

export interface UserStats {
    streak: number;
    time_spent_today: number;
    xp: number;
}

export const useUserStats = () => {
    const [stats, setStats] = useState<UserStats>({ streak: 0, time_spent_today: 0, xp: 0 });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const getToken = async () => {
        if (auth.currentUser) return await auth.currentUser.getIdToken();
        return null;
    };

    const fetchStats = async () => {
        try {
            const token = await getToken();
            if (!token) {
                console.log('[useUserStats] No auth token available');
                return;
            }

            console.log('[useUserStats] Fetching stats...');
            const response = await fetch(`${API_URL}/stats`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            console.log('[useUserStats] Response status:', response.status);
            if (response.ok) {
                const data = await response.json();
                console.log('[useUserStats] Stats received:', data);
                setStats(data);
                setError(null);
            } else {
                const errorText = await response.text();
                console.error('[useUserStats] API Error:', response.status, errorText);
                setError(`Failed to load stats (${response.status})`);
            }
        } catch (error) {
            console.error("[useUserStats] Failed to fetch stats:", error);
            setError('Network error while fetching stats');
        } finally {
            setLoading(false);
        }
    };



    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, (user) => {
            if (user) {
                fetchStats();
                // Poll for updates every 60s (to reflect changes made by TimeTracker)
                const interval = setInterval(fetchStats, 120000); // Increased from 60s to 120s
                return () => clearInterval(interval);
            } else {
                setStats({ streak: 0, time_spent_today: 0, xp: 0 });
                setLoading(false);
            }
        });
        return () => unsubscribe();
    }, []);

    return { stats, loading, error };
};
