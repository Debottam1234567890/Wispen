import { useState, useEffect } from 'react';
import { auth } from '../firebase';
import { onAuthStateChanged } from 'firebase/auth';

export type EventType = 'test' | 'homework' | 'project';

export interface CalendarEvent {
    id: string;
    date: Date;
    type: EventType;
    subject: string;
    note?: string;
    completed: boolean;
}

import { API_BASE_URL } from '../config';

const API_URL = API_BASE_URL;

export const useCalendarData = () => {
    const [events, setEvents] = useState<CalendarEvent[]>([]);
    const [loading, setLoading] = useState(true);

    const getToken = async () => {
        if (auth.currentUser) {
            return await auth.currentUser.getIdToken();
        }
        return null;
    };

    const fetchEvents = async () => {
        try {
            const token = await getToken();
            if (!token) return;

            const response = await fetch(`${API_URL}/calendar`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const data = await response.json();
                // Parse dates back to Date objects
                const parsedEvents = data.map((e: any) => ({
                    ...e,
                    date: new Date(e.date)
                }));
                setEvents(parsedEvents);
            }
        } catch (error) {
            console.error("Failed to fetch events:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, (user) => {
            if (user) {
                fetchEvents();
            } else {
                setEvents([]);
                setLoading(false);
            }
        });
        return () => unsubscribe();
    }, []);

    const addEvent = async (date: Date, type: EventType, subject: string, note?: string) => {
        try {
            const token = await getToken();
            if (!token) return;

            const newEvent = {
                date: date.toISOString(), // Send as ISO string
                type,
                subject,
                note,
                completed: false
            };

            const response = await fetch(`${API_URL}/calendar`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(newEvent)
            });

            if (response.ok) {
                const savedEvent = await response.json();
                setEvents(prev => [...prev, { ...savedEvent, date: new Date(savedEvent.date) }]);
            }
        } catch (error) {
            console.error("Failed to add event:", error);
        }
    };

    const deleteEvent = async (id: string) => {
        try {
            const token = await getToken();
            if (!token) return;

            const response = await fetch(`${API_URL}/calendar/${id}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                setEvents(prev => prev.filter(e => e.id !== id));
            }
        } catch (error) {
            console.error("Failed to delete event:", error);
        }
    };

    const toggleComplete = async (id: string) => {
        try {
            const token = await getToken();
            if (!token) return;

            const event = events.find(e => e.id === id);
            if (!event) return;

            const response = await fetch(`${API_URL}/calendar/${id}`, {
                method: 'PATCH',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ completed: !event.completed })
            });

            if (response.ok) {
                setEvents(prev => prev.map(e => e.id === id ? { ...e, completed: !e.completed } : e));
            }
        } catch (error) {
            console.error("Failed to toggle complete:", error);
        }
    };

    const getEventsForDate = (date: Date) => {
        return events.filter(e =>
            e.date.getDate() === date.getDate() &&
            e.date.getMonth() === date.getMonth() &&
            e.date.getFullYear() === date.getFullYear()
        );
    };

    return {
        events,
        loading,
        addEvent,
        deleteEvent,
        toggleComplete,
        getEventsForDate,
        refresh: fetchEvents
    };
};
