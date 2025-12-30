import { useState, useRef, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { auth, db } from '../../firebase';
import { collection, query, onSnapshot, Timestamp } from 'firebase/firestore';
import MarkdownRenderer from './MarkdownRenderer';
import { useTTS } from '../../hooks/useTTS';
import VoiceMode from './VoiceMode';
import { API_BASE_URL } from '../../config';

interface ChatCosmosProps {
    sessionId?: string;
    onOpenFlashcards?: (cards: any[]) => void;
}

interface Message {
    id: string;
    sender: 'user' | 'wispen';
    content: string;
    type: 'text' | 'card' | 'quiz' | 'loading' | 'card_ready';
    timestamp: Date;
    attachment?: any;
    isGradient?: boolean;
}

const WELCOME_MESSAGE_CONTENT = "Hey! Ready to learn? What are we exploring today?";

const ChatCosmos = ({ sessionId, onOpenFlashcards }: ChatCosmosProps) => {
    const [messages, setMessages] = useState<Message[]>([]);
    const [inputValue, setInputValue] = useState('');
    const [isGenerating, setIsGenerating] = useState(false);
    const [speakingMessageId, setSpeakingMessageId] = useState<string | null>(null);
    const [isVoiceModeOpen, setIsVoiceModeOpen] = useState(false);
    const chatContainerRef = useRef<HTMLDivElement>(null);
    const messageIdsRef = useRef<Set<string>>(new Set());

    // TTS Hook
    const { speak, stop, isSpeaking, isSupported: ttsSupported, ttsStatus } = useTTS();

    // Helper to strip emojis and format math for TTS
    const cleanTextForTTS = (text: string) => {
        let clean = text
            .replace(/[\u{1F600}-\u{1F64F}]/gu, '')
            .replace(/[\u{1F300}-\u{1F5FF}]/gu, '')
            .replace(/[\u{1F680}-\u{1F6FF}]/gu, '')
            .replace(/[\u{1F1E0}-\u{1F1FF}]/gu, '')
            .replace(/[\u{2700}-\u{27BF}]/gu, '')
            .replace(/[\u{FE00}-\u{FE0F}]/gu, '')
            .replace(/[\u{1F900}-\u{1F9FF}]/gu, '')
            .replace(/[*#]/g, '');

        // Fix Math Pronunciation
        clean = clean
            .replace(/\^2/g, ' squared')
            .replace(/²/g, ' squared')
            .replace(/\^3/g, ' cubed')
            .replace(/³/g, ' cubed')
            .replace(/\\frac{(\d+)}{(\d+)}/g, '$1 over $2')
            .replace(/[$]/g, '')
            .replace(/\\/g, '');

        return clean;
    };

    // Handle TTS button click
    const handleSpeak = (messageId: string, content: string) => {
        if (speakingMessageId === messageId && (isSpeaking || ttsStatus.includes('fetching') || ttsStatus.includes('loading'))) {
            stop();
            setSpeakingMessageId(null);
        } else {
            stop();
            setSpeakingMessageId(messageId);
            speak(cleanTextForTTS(content));
        }
    };

    // Reset speaking state when TTS stops
    useEffect(() => {
        if (!isSpeaking && speakingMessageId && !ttsStatus.includes('fetching') && !ttsStatus.includes('loading')) {
            setSpeakingMessageId(null);
        }
    }, [isSpeaking, ttsStatus]);

    // Debug state changes
    useEffect(() => {
        console.log(`[ChatCosmos] Current messages state: ${messages.length} messages`);
        if (messages.length > 0) {
            console.log(`[ChatCosmos] Latest message:`, messages[messages.length - 1]);
        }
    }, [messages]);

    // Smart Scroll Logic
    const smartScrollToBottom = (force = false) => {
        if (!chatContainerRef.current) return;
        const { scrollHeight, scrollTop, clientHeight } = chatContainerRef.current;
        const isNearBottom = scrollHeight - scrollTop - clientHeight < 150;
        if (force || isNearBottom) {
            chatContainerRef.current.scrollTo({
                top: scrollHeight,
                behavior: force ? 'smooth' : 'auto'
            });
        }
    };

    // Simplified: Clearing state and fetching moved into one effect for reliability

    // Unified Fetch & Listen
    useEffect(() => {
        if (!sessionId || !auth.currentUser) {
            setMessages([]);
            messageIdsRef.current.clear();
            return;
        }

        console.log(`[ChatCosmos] Session changed to ${sessionId}. Clearing state and starting fetch.`);
        setMessages([]);
        messageIdsRef.current.clear();

        const uid = auth.currentUser.uid;
        const messagesRef = collection(db, 'users', uid, 'sessions', sessionId, 'messages');
        const q = query(messagesRef);

        const unsubscribe = onSnapshot(q, (snapshot) => {
            console.log(`[ChatCosmos] Snapshot received: ${snapshot.size} docs`);
            const updates: Message[] = snapshot.docs.map(doc => {
                const data = doc.data();
                let timestamp: Date;
                if (data.timestamp instanceof Timestamp) {
                    timestamp = data.timestamp.toDate();
                } else if (data.timestamp) {
                    timestamp = new Date(data.timestamp);
                } else {
                    timestamp = new Date();
                }

                return {
                    id: doc.id,
                    sender: data.sender === 'user' ? 'user' : 'wispen',
                    content: data.content || '',
                    type: data.type || 'text',
                    timestamp: timestamp,
                    attachment: data.attachment,
                    isGradient: data.sender !== 'user'
                };
            });

            setMessages(prev => {
                const refreshedMsgs = [...prev];
                updates.forEach(m => {
                    const idx = refreshedMsgs.findIndex(existing => existing.id === m.id);
                    if (idx !== -1) {
                        if (refreshedMsgs[idx].content !== m.content) {
                            refreshedMsgs[idx] = { ...refreshedMsgs[idx], ...m };
                        }
                    } else {
                        refreshedMsgs.push(m);
                        messageIdsRef.current.add(m.id);
                    }
                });

                const uniqueMsgs = Array.from(new Map(refreshedMsgs.map(item => [item.id, item])).values());
                const sorted = uniqueMsgs.sort((a, b) => (a.timestamp?.getTime() || 0) - (b.timestamp?.getTime() || 0));
                console.log(`[ChatCosmos] State Update (Snapshot): ${prev.length} -> ${sorted.length}`);
                return sorted;
            });

            setTimeout(() => smartScrollToBottom(true), 150);
        }, (error) => {
            if (error.code === 'permission-denied') {
                console.warn("[ChatCosmos] Firestore access denied (Permissions). Relying on backend fallback.");
            } else {
                console.error("[ChatCosmos] Firestore Error:", error);
            }
        });

        // Backend fallback fetch
        const fetchHistory = async () => {
            try {
                const user = auth.currentUser;
                if (!user) return;
                const token = await user.getIdToken();
                const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/messages`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });

                if (response.ok) {
                    const data = await response.json();
                    console.log(`[ChatCosmos] Backend fetch success: ${data.length} messages`);
                    const history: Message[] = data.map((msg: any) => ({
                        id: msg.id,
                        sender: msg.sender === 'user' ? 'user' : 'wispen',
                        content: msg.content || '',
                        type: msg.type || 'text',
                        timestamp: new Date(msg.timestamp),
                        attachment: msg.attachment,
                        isGradient: msg.sender !== 'user'
                    }));

                    setMessages(prev => {
                        const newMsgs = [...prev];
                        history.forEach(m => {
                            if (!messageIdsRef.current.has(m.id)) {
                                newMsgs.push(m);
                                messageIdsRef.current.add(m.id);
                            }
                        });
                        const sorted = [...newMsgs].sort((a, b) => (a.timestamp?.getTime() || 0) - (b.timestamp?.getTime() || 0));
                        console.log(`[ChatCosmos] State Update (Backend): ${prev.length} -> ${sorted.length}`);
                        return sorted;
                    });
                }
            } catch (err) {
                console.error("[ChatCosmos] History fetch error:", err);
            }
        };

        fetchHistory();
        return () => unsubscribe();
    }, [sessionId, auth.currentUser]);

    // Voice Message Handler
    const handleVoiceMessageSent = useCallback((userMsg: string, aiMsg: string, userMsgId?: string, aiMsgId?: string) => {
        const uniqueId = Date.now().toString() + Math.random().toString(36).substr(2, 5);
        const finalUserMsgId = userMsgId || 'voice-user-' + uniqueId;
        const finalAiMsgId = aiMsgId || 'voice-ai-' + uniqueId;

        const userMessage: Message = {
            id: finalUserMsgId,
            sender: 'user',
            content: userMsg,
            type: 'text',
            timestamp: new Date()
        };
        const aiMessage: Message = {
            id: finalAiMsgId,
            sender: 'wispen',
            content: aiMsg,
            type: 'text',
            timestamp: new Date(),
            isGradient: true
        };

        setMessages(prev => {
            if (messageIdsRef.current.has(finalUserMsgId)) return prev;
            messageIdsRef.current.add(finalUserMsgId);
            messageIdsRef.current.add(finalAiMsgId);
            return [...prev, userMessage, aiMessage];
        });

        setTimeout(() => smartScrollToBottom(true), 100);
    }, [sessionId]);

    // Send message
    const handleSendMessage = async () => {
        if (!inputValue.trim() || !sessionId) return;

        const userMessageId = 'user-' + Date.now().toString() + Math.random().toString(36).substr(2, 5);
        const aiMessageId = 'ai-' + Date.now().toString() + Math.random().toString(36).substr(2, 5);

        const userMessage: Message = {
            id: userMessageId,
            sender: 'user',
            content: inputValue.trim(),
            type: 'text',
            timestamp: new Date()
        };

        setMessages(prev => [...prev, userMessage]);
        messageIdsRef.current.add(userMessageId);
        setInputValue('');
        setIsGenerating(true);
        smartScrollToBottom(true);

        try {
            const token = await auth.currentUser!.getIdToken();
            const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/messages`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    id: userMessageId,
                    aiMessageId: aiMessageId,
                    sender: 'user',
                    content: userMessage.content,
                    type: 'text'
                })
            });

            if (!response.ok) throw new Error('Network response was not ok');

            const aiMessage: Message = {
                id: aiMessageId,
                sender: 'wispen',
                content: '',
                type: 'text',
                timestamp: new Date(),
                isGradient: true
            };
            setMessages(prev => [...prev, aiMessage]);
            messageIdsRef.current.add(aiMessageId);

            const reader = response.body?.getReader();
            if (!reader) return;

            const decoder = new TextDecoder();
            let aiContent = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const step = 15;
                for (let i = 0; i < chunk.length; i += step) {
                    aiContent += chunk.slice(i, i + step);
                    setMessages(prev => prev.map(msg =>
                        msg.id === aiMessageId ? { ...msg, content: aiContent } : msg
                    ));
                    await new Promise(resolve => setTimeout(resolve, 1));
                    if (i % 30 === 0) smartScrollToBottom(false);
                }
                smartScrollToBottom(true);
            }

        } catch (err: any) {
            console.error('Failed to send message:', err);
            setMessages(prev => [...prev, {
                id: 'error-' + Date.now().toString(),
                sender: 'wispen',
                content: "I'm having trouble connecting to my brain right now. Please try again.",
                type: 'text',
                timestamp: new Date(),
                isGradient: true
            }]);
        } finally {
            setIsGenerating(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            style={{
                display: 'flex',
                flexDirection: 'column',
                height: '100%',
                background: 'linear-gradient(135deg, rgba(255,245,235,0.9) 0%, rgba(255,250,245,0.95) 100%)',
                borderRadius: '20px',
                overflow: 'hidden',
                boxShadow: '0 10px 40px rgba(0,0,0,0.1)'
            }}
        >
            {/* Floating Chat Header */}
            <div style={{
                position: 'absolute',
                top: '15px',
                left: '25px',
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                zIndex: 10
            }}>
                <div style={{
                    width: '45px',
                    height: '45px',
                    borderRadius: '50%',
                    background: 'linear-gradient(135deg, #f3e7e9 0%, #e3eeff 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '1.5rem',
                    boxShadow: '0 4px 15px rgba(0,0,0,0.1)'
                }}>
                    ✏️
                </div>
                <div>
                    <h3 style={{ margin: 0, fontFamily: '"Indie Flower", cursive', fontSize: '1.3rem', color: '#333' }}>Wispen AI</h3>
                    <span style={{ fontSize: '0.75rem', color: '#888' }}>Online & Ready</span>
                </div>
            </div>

            {/* Messages Area */}
            <div
                ref={chatContainerRef}
                style={{
                    flex: 1,
                    overflowY: 'auto',
                    padding: '80px 25px 20px 25px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '15px',
                    minHeight: 0
                }}
            >
                {/* Welcome Message (Only if history is empty) */}
                {messages.length === 0 && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        style={{
                            alignSelf: 'flex-start',
                            maxWidth: '75%',
                            display: 'flex',
                            flexDirection: 'column'
                        }}
                    >
                        <div style={{
                            background: 'linear-gradient(135deg, #f3e7e9 0%, #e3eeff 99%, #e3eeff 100%)',
                            color: '#333',
                            padding: '15px 25px 15px 25px',
                            borderRadius: '20px 20px 20px 2px',
                            boxShadow: '0 4px 15px rgba(0,0,0,0.05)',
                            border: '1px solid #fff',
                            fontFamily: '"Indie Flower", cursive',
                            fontSize: '1.2rem',
                            lineHeight: '1.6'
                        }}>
                            {WELCOME_MESSAGE_CONTENT}
                        </div>
                    </motion.div>
                )}
                {messages.map((msg) => (
                    <motion.div
                        key={msg.id}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        style={{
                            alignSelf: msg.sender === 'user' ? 'flex-end' : 'flex-start',
                            maxWidth: '75%',
                            display: 'flex',
                            flexDirection: 'column'
                        }}
                    >
                        <div
                            role="article"
                            style={{
                                background: msg.sender === 'user'
                                    ? 'white'
                                    : (msg.isGradient ? 'linear-gradient(135deg, #f3e7e9 0%, #e3eeff 99%, #e3eeff 100%)' : 'rgba(255,255,255,0.9)'),
                                color: '#333',
                                padding: '15px 25px 35px 25px',
                                borderRadius: msg.sender === 'user' ? '20px 20px 2px 20px' : '20px 20px 20px 2px',
                                boxShadow: '0 4px 15px rgba(0,0,0,0.05)',
                                border: msg.sender === 'user' ? '1px solid #eee' : '1px solid #fff',
                                fontFamily: msg.sender === 'user' ? '"Caveat", cursive' : '"Indie Flower", cursive',
                                fontSize: '1.2rem',
                                lineHeight: '1.6',
                                position: 'relative',
                                overflowWrap: 'break-word',
                                wordBreak: 'break-word',
                                minWidth: '100px'
                            }}>
                            <MarkdownRenderer content={msg.content} isUser={msg.sender === 'user'} />

                            {msg.type === 'card_ready' && msg.attachment?.cards && onOpenFlashcards && (
                                <motion.div
                                    initial={{ opacity: 0, scale: 0.9 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    style={{ marginTop: '15px' }}
                                >
                                    <button
                                        onClick={() => onOpenFlashcards(msg.attachment.cards)}
                                        style={{
                                            background: 'linear-gradient(135deg, #F6D365 0%, #FDA085 100%)',
                                            color: 'white',
                                            border: 'none',
                                            padding: '10px 20px',
                                            borderRadius: '12px',
                                            fontWeight: 'bold',
                                            cursor: 'pointer',
                                            boxShadow: '0 4px 15px rgba(253, 160, 133, 0.4)',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '8px',
                                            fontFamily: '"Outfit", sans-serif'
                                        }}
                                    >
                                        <span>View Flashcards</span>
                                        <span style={{ fontSize: '1.2rem' }}>📇</span>
                                    </button>
                                </motion.div>
                            )}

                            {/* TTS Speaker Button for ALL messages */}
                            {ttsSupported && (
                                <div style={{ position: 'absolute', bottom: '6px', right: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>

                                    {/* Loading Progress Bar */}
                                    {speakingMessageId === msg.id && (ttsStatus === 'fetching audio...' || ttsStatus.includes('loading')) && (
                                        <div style={{
                                            width: '60px',
                                            height: '4px',
                                            background: 'rgba(0,0,0,0.1)',
                                            borderRadius: '2px',
                                            overflow: 'hidden',
                                            position: 'relative'
                                        }}>
                                            <motion.div
                                                initial={{ x: '-100%' }}
                                                animate={{ x: '100%' }}
                                                transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
                                                style={{
                                                    width: '50%',
                                                    height: '100%',
                                                    background: 'linear-gradient(90deg, #6C63FF, #4834d4)',
                                                    borderRadius: '2px'
                                                }}
                                            />
                                        </div>
                                    )}

                                    <button
                                        onClick={() => handleSpeak(msg.id, msg.content)}
                                        disabled={speakingMessageId === msg.id && (ttsStatus.includes('fetching') || ttsStatus.includes('loading'))}
                                        title={speakingMessageId === msg.id && isSpeaking ? 'Stop speaking' : 'Read aloud'}
                                        style={{
                                            background: speakingMessageId === msg.id && isSpeaking
                                                ? 'linear-gradient(135deg, #6C63FF, #4834d4)'
                                                : 'rgba(100,100,100,0.15)',
                                            border: 'none',
                                            borderRadius: '50%',
                                            width: '26px',
                                            height: '26px',
                                            cursor: 'pointer',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            fontSize: '0.85rem',
                                            transition: 'all 0.2s ease',
                                            color: speakingMessageId === msg.id && isSpeaking ? 'white' : '#555',
                                            opacity: speakingMessageId === msg.id && (ttsStatus.includes('fetching') || ttsStatus.includes('loading')) ? 0.7 : 1
                                        }}
                                    >
                                        {speakingMessageId === msg.id && isSpeaking ? '⏹' : '🔊'}
                                    </button>
                                </div>
                            )}
                        </div>
                        <span style={{
                            fontSize: '0.7rem',
                            color: '#999',
                            marginTop: '5px',
                            alignSelf: msg.sender === 'user' ? 'flex-end' : 'flex-start'
                        }}>
                            {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                    </motion.div>
                ))}

                {isGenerating && messages[messages.length - 1]?.sender === 'user' && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        style={{ alignSelf: 'flex-start', color: '#888', fontStyle: 'italic', marginLeft: '10px' }}
                    >
                        Wispen is thinking... 💭
                    </motion.div>
                )}
            </div>

            {/* Input Area */}
            <div style={{ padding: '20px', background: 'rgba(255,255,255,0.4)', borderTop: '1px solid rgba(0,0,0,0.05)', backdropFilter: 'blur(5px)' }}>
                <div style={{ position: 'relative', display: 'flex', gap: '10px', alignItems: 'flex-end' }}>
                    {/* Mic Button for Voice Mode */}
                    <button
                        onClick={() => setIsVoiceModeOpen(true)}
                        title="Voice Mode"
                        style={{
                            background: 'linear-gradient(135deg, #4ECDC4, #44A08D)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '50%',
                            width: '50px',
                            height: '50px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '1.5rem',
                            boxShadow: '0 4px 15px rgba(78, 205, 196, 0.4)',
                            flexShrink: 0
                        }}
                    >
                        🎤
                    </button>

                    <div style={{ position: 'relative', flex: 1 }}>
                        <textarea
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Ask anything or generate study aids..."
                            style={{
                                width: '100%',
                                background: 'white',
                                border: '1px solid #eee',
                                borderRadius: '16px',
                                padding: '15px 50px 15px 20px',
                                fontFamily: '"Caveat", cursive',
                                fontSize: '1.2rem',
                                resize: 'none',
                                outline: 'none',
                                minHeight: '60px',
                                boxShadow: 'inset 0 2px 5px rgba(0,0,0,0.02)'
                            }}
                        />
                        <button
                            onClick={handleSendMessage}
                            style={{
                                position: 'absolute',
                                right: '10px',
                                bottom: '15px',
                                background: 'var(--dream-purple)',
                                color: 'white',
                                border: 'none',
                                borderRadius: '50%',
                                width: '40px',
                                height: '40px',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                boxShadow: '0 2px 8px rgba(0,0,0,0.2)'
                            }}
                        >
                            ➤
                        </button>
                    </div>
                </div>
            </div>

            {/* Voice Mode Overlay */}
            <VoiceMode
                isOpen={isVoiceModeOpen}
                onClose={() => setIsVoiceModeOpen(false)}
                sessionId={sessionId}
                onMessageSent={handleVoiceMessageSent}
            />
        </motion.div>
    );
};

export default ChatCosmos;
