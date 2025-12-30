import { useEffect } from 'react';
import { auth } from '../firebase';
import { onAuthStateChanged } from 'firebase/auth';

import { API_BASE_URL } from '../config';
const API_URL = API_BASE_URL;

export const useHeartbeat = () => {
    useEffect(() => {
        const sendHeartbeat = async () => {
            if (!auth.currentUser) return;
            try {
                const token = await auth.currentUser.getIdToken();
                await fetch(`${API_URL}/stats/heartbeat`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}` }
                });
            } catch (error) {
                console.error("Heartbeat failed:", error);
            }
        };

        const unsubscribe = onAuthStateChanged(auth, (user) => {
            if (user) {
                // Initial pulse
                sendHeartbeat();
                // Recurring pulse every 60s
                const interval = setInterval(sendHeartbeat, 60000);
                return () => clearInterval(interval);
            }
        });

        return () => unsubscribe();
    }, []);
};
