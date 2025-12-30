import React, { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { API_BASE_URL } from '../../../config';

interface VideoLayer {
    type: 'text' | 'svg' | 'diagram' | 'annotation' | 'particles' | 'image';
    content?: string;
    url?: string; // New for images
    x: number;
    y: number;
    width?: number; // New for images
    height?: number; // New for images
    opacity?: number; // New for images
    font?: string;
    color?: string;
    shape?: 'circle' | 'rect' | 'arrow';
    r?: number;
    label?: string;
    targetX?: number;
    targetY?: number;
    source?: { x: number; y: number };
    target?: { x: number; y: number };
    count?: number;
    scale?: { from: number; to: number };
}

interface VideoStep {
    start: number;
    end: number;
    layers: VideoLayer[];
    narration?: string;
    audioUrl?: string;
}

interface VideoData {
    title: string;
    duration: number;
    steps: VideoStep[];
    background?: string;
    width?: number;
    height?: number;
    audioUrl?: string; // Global continuous audio
    videoUrl?: string; // Direct MP4 URL
    url?: string; // Standard Bookshelf URL
    fileUrl?: string; // Alternative Bookshelf URL
}

interface VideoViewerProps {
    video: VideoData;
    onClose: () => void;
}

const VideoViewer: React.FC<VideoViewerProps> = ({ video, onClose }) => {
    console.log("VideoViewer: Mounted with video:", video);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const audioRef = useRef<HTMLAudioElement | null>(null);
    const [currentTime, setCurrentTime] = useState(0);
    const [isPlaying, setIsPlaying] = useState(true);
    const [activeStepIndex, setActiveStepIndex] = useState(-1);
    const requestRef = useRef<number>(null!);
    const startTimeRef = useRef<number>(0);
    const imageCache = useRef<Map<string, HTMLImageElement>>(new Map());

    // Resolve video source - check multiple possible property names
    const videoSource = video.videoUrl || video.url || video.fileUrl || (video as any).video_url;
    console.log("VideoViewer: Resolved videoSource:", videoSource);

    // Resolve title - backend may use 'topic' instead of 'title'
    const videoTitle = video.title || (video as any).topic || 'Educational Video';

    // Duration: backend stores in seconds, convert to milliseconds for consistency
    const videoDuration = video.duration > 1000 ? video.duration : (video.duration * 1000);

    // Preload images
    useEffect(() => {
        if (!video.steps) return;
        video.steps.forEach(step => {
            step.layers.forEach(layer => {
                if (layer.type === 'image' && layer.url && !imageCache.current.has(layer.url)) {
                    const finalUrl = layer.url.startsWith('http') ? layer.url : `${API_BASE_URL}/static${layer.url}`;
                    const img = new Image();
                    img.src = finalUrl;
                    img.onload = () => {
                        imageCache.current.set(layer.url!, img);
                    };
                }
            });
        });
    }, [video.steps]);

    // Initialize Global Audio (if present)
    useEffect(() => {
        if (video.audioUrl) {
            const finalAudioUrl = video.audioUrl.startsWith('http') ? video.audioUrl : `${API_BASE_URL}/static${video.audioUrl}`;
            const audio = new Audio(finalAudioUrl);
            audioRef.current = audio;

            // Auto-play
            audio.play().catch(err => console.error("Global audio login failed:", err));

            // Loop if needed, or stop at end
            audio.onended = () => setIsPlaying(false);

            return () => {
                audio.pause();
                audioRef.current = null;
            };
        }
    }, [video.audioUrl]);

    // Backward Compatibility: Step-based Audio Sync logic
    useEffect(() => {
        // Only run this if NO global audio AND steps exist
        if (video.audioUrl || !video.steps) return;

        const stepIndex = video.steps.findIndex(s => currentTime >= s.start && currentTime <= s.end);

        if (stepIndex !== activeStepIndex) {
            setActiveStepIndex(stepIndex);

            // If new step has audio, play it
            if (stepIndex !== -1 && video.steps[stepIndex].audioUrl) {
                if (audioRef.current) {
                    audioRef.current.pause();
                }
                const audioUrl = video.steps[stepIndex].audioUrl!;
                const finalAudioUrl = audioUrl.startsWith('http') ? audioUrl : `${API_BASE_URL}/static${audioUrl}`;
                const audio = new Audio(finalAudioUrl);
                audioRef.current = audio;
                if (isPlaying) {
                    audio.play().catch(err => console.error("Audio playback error:", err));
                }
            }
        }
    }, [currentTime, activeStepIndex, video.steps, isPlaying, video.audioUrl]);

    // Handle isPlaying changes
    useEffect(() => {
        if (audioRef.current) {
            if (isPlaying) {
                audioRef.current.play().catch(() => { });
            } else {
                audioRef.current.pause();
            }
        }
    }, [isPlaying]);

    const render = (time: number) => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        ctx.save();

        // --- Ken Burns Effect (Subtle Zoom/Pan) ---
        const zoomSpeed = 0.05; // 5% zoom over duration
        const panSpeed = 10; // 10px pan
        const phase = (time % 20000) / 20000; // Slow 20s cycle
        const scale = 1 + (Math.sin(phase * Math.PI) * zoomSpeed);
        const translateX = Math.cos(phase * Math.PI * 2) * panSpeed;
        const translateY = Math.sin(phase * Math.PI * 2) * panSpeed;

        ctx.translate(canvas.width / 2 + translateX, canvas.height / 2 + translateY);
        ctx.scale(scale, scale);
        ctx.translate(-canvas.width / 2, -canvas.height / 2);

        // Clear and set background
        ctx.fillStyle = video.background || '#ffffff';
        ctx.fillRect(-20, -20, canvas.width + 40, canvas.height + 40);

        // Safe guard against missing steps
        if (!video.steps) return;

        // Find current step
        const currentStepIndex = video.steps.findIndex(s => time >= s.start && time <= s.end);
        const currentStep = video.steps[currentStepIndex];

        if (currentStep) {
            // --- Transition Logic ---
            const stepDuration = currentStep.end - currentStep.start;
            const progress = (time - currentStep.start) / stepDuration;

            // Fade in at start, fade out at end
            let opacity = 1;
            if (progress < 0.1) opacity = progress * 10;
            if (progress > 0.9) opacity = (1 - progress) * 10;

            ctx.globalAlpha = opacity;

            // Render layers
            currentStep.layers.forEach(layer => {
                ctx.save();

                if (layer.type === 'text') {
                    ctx.fillStyle = layer.color || '#ffffff';
                    ctx.font = layer.font || 'bold 28px "Outfit", sans-serif';
                    ctx.textAlign = 'center';

                    // Add subtle glow to text for premium feel
                    ctx.shadowColor = 'rgba(0,0,0,0.5)';
                    ctx.shadowBlur = 4;
                    ctx.fillText(layer.content || '', layer.x, layer.y);
                    ctx.shadowBlur = 0;
                }
                else if (layer.type === 'image' && layer.url) {
                    const img = imageCache.current.get(layer.url);
                    if (img) {
                        const w = layer.width || 640;
                        const h = layer.height || 360;
                        ctx.globalAlpha = (layer.opacity ?? 1.0) * opacity;
                        ctx.drawImage(img, layer.x - w / 2, layer.y - h / 2, w, h);
                    }
                }
                else if (layer.type === 'diagram') {
                    ctx.fillStyle = layer.color || '#3b82f6';
                    ctx.strokeStyle = layer.color || '#3b82f6';
                    ctx.lineWidth = 2;

                    if (layer.shape === 'circle') {
                        ctx.beginPath();
                        ctx.arc(layer.x, layer.y, layer.r || 10, 0, Math.PI * 2);
                        ctx.fill();
                        if (layer.label) {
                            ctx.fillStyle = 'white';
                            ctx.font = 'bold 12px "Outfit", sans-serif';
                            ctx.textAlign = 'center';
                            ctx.fillText(layer.label, layer.x, layer.y + 4);
                        }
                    } else if (layer.shape === 'rect') {
                        const w = layer.r ? layer.r * 2 : 50;
                        const h = layer.r ? layer.r * 1.5 : 30;
                        ctx.fillRect(layer.x - w / 2, layer.y - h / 2, w, h);
                        if (layer.label) {
                            ctx.fillStyle = 'white';
                            ctx.font = 'bold 12px "Outfit", sans-serif';
                            ctx.textAlign = 'center';
                            ctx.fillText(layer.label, layer.x, layer.y + 4);
                        }
                    } else if (layer.shape === 'arrow') {
                        const headlen = 10;
                        const fromX = layer.x;
                        const fromY = layer.y;
                        const toX = layer.targetX || fromX + 50;
                        const toY = layer.targetY || fromY;
                        const dx = toX - fromX;
                        const dy = toY - fromY;
                        const angle = Math.atan2(dy, dx);
                        ctx.beginPath();
                        ctx.moveTo(fromX, fromY);
                        ctx.lineTo(toX, toY);
                        ctx.lineTo(toX - headlen * Math.cos(angle - Math.PI / 6), toY - headlen * Math.sin(angle - Math.PI / 6));
                        ctx.moveTo(toX, toY);
                        ctx.lineTo(toX - headlen * Math.cos(angle + Math.PI / 6), toY - headlen * Math.sin(angle + Math.PI / 6));
                        ctx.stroke();
                    }
                }
                else if (layer.type === 'annotation') {
                    ctx.strokeStyle = '#64748b';
                    ctx.setLineDash([4, 4]);
                    ctx.beginPath();
                    ctx.moveTo(layer.x, layer.y);
                    ctx.lineTo(layer.targetX || layer.x, layer.targetY || layer.y);
                    ctx.stroke();
                    ctx.fillStyle = '#64748b';
                    ctx.font = '12px "Outfit"';
                    ctx.fillText(layer.label || '', layer.x, layer.y - 8);
                }
                else if (layer.type === 'particles') {
                    const stepProgress = (time % 2000) / 2000;
                    const count = layer.count || 5;
                    ctx.fillStyle = layer.color || '#f59e0b';
                    for (let i = 0; i < count; i++) {
                        const pP = (stepProgress + (i / count)) % 1;
                        const px = (layer.source?.x || 0) + ((layer.target?.x || 0) - (layer.source?.x || 0)) * pP;
                        const py = (layer.source?.y || 0) + ((layer.target?.y || 0) - (layer.source?.y || 0)) * pP;
                        ctx.beginPath();
                        ctx.arc(px, py, 2.5, 0, Math.PI * 2);
                        ctx.fill();
                    }
                }

                ctx.restore();
            });
        }

        ctx.restore();
    };

    const animate = (time: number) => {
        if (!startTimeRef.current) startTimeRef.current = time;
        const elapsed = time - startTimeRef.current;

        if (isPlaying) {
            let nextTime = elapsed % videoDuration;

            // If Global Audio is present, use its time as source of truth
            if (video.audioUrl && audioRef.current && !audioRef.current.paused) {
                nextTime = audioRef.current.currentTime * 1000;

                // Looping logic (optional, but good for short clips)
                if (nextTime >= videoDuration) {
                    // For now, let's just hold or loop. Audio usually stops.
                }
            }

            setCurrentTime(nextTime);
            render(nextTime);
        }

        requestRef.current = requestAnimationFrame(animate);
    };

    useEffect(() => {
        // Don't start animation loop for MP4 videos
        if (videoSource) return;

        requestRef.current = requestAnimationFrame(animate);
        return () => {
            if (requestRef.current) cancelAnimationFrame(requestRef.current);
        };
    }, [isPlaying, video, videoSource]);

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{
                position: 'fixed',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                background: 'rgba(0,0,0,0.9)',
                zIndex: 1000,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backdropFilter: 'blur(10px)'
            }}
        >
            <div style={{ position: 'relative', width: '800px', background: 'white', borderRadius: '24px', overflow: 'hidden', boxShadow: '0 25px 50px rgba(0,0,0,0.5)' }}>
                {/* Header */}
                <div style={{ padding: '20px 30px', borderBottom: '1px solid #eee', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <h3 style={{ margin: 0, fontFamily: '"Outfit", sans-serif', color: '#111827' }}>{videoTitle}</h3>
                        <span style={{ fontSize: '0.8rem', color: '#6b7280' }}>Scientific Video • Narrated Podcast Duo</span>
                    </div>
                    <button onClick={onClose} style={{ border: 'none', background: 'none', fontSize: '1.5rem', cursor: 'pointer', color: '#9ca3af' }}>✕</button>
                </div>

                {/* Canvas Area or Video Player */}
                <div style={{ background: '#f8fafc', display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '40px', minHeight: '400px', justifyContent: 'center' }}>
                    {/* MP4 Video Player Support */}
                    {videoSource ? (
                        <video
                            src={videoSource.startsWith('http') ? videoSource : `${API_BASE_URL}${videoSource}`}
                            controls
                            autoPlay
                            style={{
                                maxWidth: '100%',
                                maxHeight: '60vh',
                                borderRadius: '12px',
                                boxShadow: '0 10px 20px rgba(0,0,0,0.1)'
                            }}
                        >
                            Your browser does not support the video tag.
                        </video>
                    ) : (
                        /* Original Canvas Logic for legacy animations */
                        <>
                            <canvas
                                ref={canvasRef}
                                width={640}
                                height={360}
                                style={{ background: 'white', borderRadius: '12px', boxShadow: '0 10px 20px rgba(0,0,0,0.1)', maxWidth: '100%' }}
                            />

                            {/* Active Narration Tooltip */}
                            {activeStepIndex !== -1 && video.steps && video.steps[activeStepIndex]?.narration && (
                                <motion.div
                                    key={activeStepIndex}
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    style={{
                                        marginTop: '20px',
                                        padding: '12px 20px',
                                        background: 'white',
                                        border: '1px solid #e2e8f0',
                                        borderRadius: '12px',
                                        maxWidth: '80%',
                                        textAlign: 'center',
                                        fontStyle: 'italic',
                                        color: '#475569',
                                        fontSize: '0.95rem',
                                        boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)'
                                    }}
                                >
                                    "{video.steps[activeStepIndex].narration}"
                                </motion.div>
                            )}
                        </>
                    )}
                </div>

                {/* Controls */}
                <div style={{ padding: '20px 30px', background: 'white' }}>
                    <div style={{ height: '4px', width: '100%', background: '#f1f5f9', borderRadius: '2px', position: 'relative', cursor: 'pointer', marginBottom: '15px' }}>
                        <div style={{ position: 'absolute', height: '100%', background: '#6366f1', borderRadius: '2px', width: `${(currentTime / videoDuration) * 100}%` }} />
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
                            <button
                                onClick={() => setIsPlaying(!isPlaying)}
                                style={{ background: '#6366f1', color: 'white', border: 'none', padding: '10px 25px', borderRadius: '10px', fontWeight: 600, cursor: 'pointer' }}
                            >
                                {isPlaying ? 'Pause' : 'Play'}
                            </button>
                            <span style={{ fontSize: '0.9rem', color: '#64748b', fontFamily: 'monospace' }}>
                                {Math.floor(currentTime / 1000)}s / {Math.floor(videoDuration / 1000)}s
                            </span>
                        </div>

                        <div style={{ display: 'flex', gap: '8px' }}>
                            {video.steps && video.steps.map((_, idx) => (
                                <div
                                    key={idx}
                                    style={{
                                        width: '8px',
                                        height: '8px',
                                        borderRadius: '50%',
                                        background: idx === activeStepIndex ? '#6366f1' : '#e2e8f0'
                                    }}
                                />
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </motion.div>
    );
};

export default VideoViewer;
