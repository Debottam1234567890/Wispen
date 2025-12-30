import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const VIDEOS = [
    { id: 'angry', src: '/videos/mascot/angry.mp4', color: '#ff6b6b', text: "Stressed & Overwhelemed?", sub: "We've all been there." },
    { id: 'focused', src: '/videos/mascot/focused.mp4', color: '#4ecdc4', text: "Finding Focus...", sub: "Wispen guides the way." },
    { id: 'happy', src: '/videos/mascot/happy.mp4', color: '#ffe66d', text: "Achieving Goals!", sub: "Celebrate your wins." }
];

const VideoSlide = ({ src, onEnded }: { src: string; onEnded: () => void }) => {
    const videoRef = useRef<HTMLVideoElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const animationFrameRef = useRef<number | null>(null);
    const [needsManualPlay, setNeedsManualPlay] = useState(false);

    // Canvas Rendering Loop
    useEffect(() => {
        const video = videoRef.current;
        const canvas = canvasRef.current;
        if (!video || !canvas) return;

        console.log(`[VideoSlide] Mounting for src: ${src}`);

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const render = () => {
            if (video && !video.paused && !video.ended) {
                // Check if video has data
                if (video.readyState >= 2) {
                    const vidW = video.videoWidth;
                    const vidH = video.videoHeight;
                    const canvasW = canvas.width;
                    const canvasH = canvas.height;

                    if (vidW > 0 && vidH > 0 && canvasW > 0 && canvasH > 0) {
                        const vidRatio = vidW / vidH;
                        const canvasRatio = canvasW / canvasH;

                        let drawWidth = canvasW;
                        let drawHeight = canvasH;
                        let offsetX = 0;
                        let offsetY = 0;

                        if (canvasRatio > vidRatio) {
                            drawHeight = canvasW / vidRatio;
                            offsetY = (canvasH - drawHeight) / 2;
                        } else {
                            drawWidth = canvasH * vidRatio;
                            offsetX = (canvasW - drawWidth) / 2;
                        }

                        ctx.drawImage(video, offsetX, offsetY, drawWidth, drawHeight);
                    }
                }
            }
            animationFrameRef.current = requestAnimationFrame(render);
        };

        render();

        return () => {
            if (animationFrameRef.current) {
                cancelAnimationFrame(animationFrameRef.current);
            }
        };
    }, [src]);

    // Handle Resize
    useEffect(() => {
        const handleResize = () => {
            if (canvasRef.current && canvasRef.current.parentElement) {
                const parent = canvasRef.current.parentElement;
                canvasRef.current.width = parent.clientWidth;
                canvasRef.current.height = parent.clientHeight;
            }
        };

        window.addEventListener('resize', handleResize);
        handleResize();

        return () => window.removeEventListener('resize', handleResize);
    }, []);

    // Ensure Play
    useEffect(() => {
        if (videoRef.current) {
            // Explicitly set muted for Safari
            videoRef.current.muted = true;

            console.log(`[VideoSlide] Attempting to play: ${src}`);
            const playPromise = videoRef.current.play();

            if (playPromise !== undefined) {
                playPromise
                    .then(() => {
                        console.log(`[VideoSlide] Playing: ${src}`);
                        setNeedsManualPlay(false);
                    })
                    .catch((e) => {
                        console.error(`[VideoSlide] Playback failed for ${src}:`, e);
                        setNeedsManualPlay(true);
                    });
            } else {
                // Older browsers
                setNeedsManualPlay(true);
            }

            // Log video errors
            videoRef.current.onerror = () => {
                console.error(`[VideoSlide] Video error for ${src}:`, videoRef.current?.error);
            };
        }
    }, [src]);

    const handleManualPlay = () => {
        if (videoRef.current) {
            videoRef.current.muted = true;
            videoRef.current.play()
                .then(() => setNeedsManualPlay(false))
                .catch(e => console.error("Manual play failed:", e));
        }
    };

    return (
        <>
            <video
                ref={videoRef}
                src={src}
                muted
                playsInline
                loop={false}
                onEnded={onEnded}
                style={{ position: 'absolute', width: 0, height: 0, opacity: 0, pointerEvents: 'none' }}
                crossOrigin="anonymous"
            />
            <canvas
                ref={canvasRef}
                style={{
                    width: '100%',
                    height: '100%',
                    display: 'block'
                }}
            />

            {needsManualPlay && (
                <div
                    onClick={handleManualPlay}
                    style={{
                        position: 'absolute', top: 0, left: 0, width: '100%', height: '100%',
                        background: 'rgba(0,0,0,0.4)', display: 'flex', flexDirection: 'column',
                        justifyContent: 'center', alignItems: 'center', cursor: 'pointer', zIndex: 10
                    }}
                >
                    <div style={{ fontSize: '4rem', color: 'white' }}>▶️</div>
                    <div style={{ color: 'white', fontFamily: 'Indie Flower', fontSize: '1.5rem', marginTop: '10px' }}>
                        Tap to Play
                    </div>
                </div>
            )}
        </>
    );
};

const VideoCarousel = () => {
    const [index, setIndex] = useState(0);

    const handleVideoEnded = () => {
        setIndex((prev) => (prev + 1) % VIDEOS.length);
    };

    return (
        <div style={{ width: '100%', height: '100%', position: 'relative', background: 'black' }}>
            <AnimatePresence mode="wait">
                <motion.div
                    key={index}
                    initial={{ opacity: 1 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 1 }}
                    style={{
                        width: '100%',
                        height: '100%',
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        overflow: 'hidden'
                    }}
                >
                    <VideoSlide src={VIDEOS[index].src} onEnded={handleVideoEnded} />
                </motion.div>
            </AnimatePresence>
        </div>
    );
};

export default VideoCarousel;
