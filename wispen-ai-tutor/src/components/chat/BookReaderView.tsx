import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import { auth } from '../../firebase';
import MarkdownRenderer from './MarkdownRenderer';
import { API_BASE_URL } from '../../config';

// Configure PDF.js worker for react-pdf v9
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
    'pdfjs-dist/build/pdf.worker.min.mjs',
    import.meta.url
).toString();

interface StickyNote {
    id: string;
    content: string;
    page?: number;
}

interface Highlight {
    id: string;
    page: number;
    text: string;
    explanation: string;
    boundingBox: { x: number; y: number; width: number; height: number };
    color: string;
}

interface BookReaderViewProps {
    bookId?: string;
    bookTitle: string;
    bookPath: string;
    fileType?: 'pdf' | 'image' | 'video' | 'text' | 'other';
    initialStickyNotes?: StickyNote[];
    initialHighlights?: Highlight[];
    onClose: () => void;
    sessionId?: string;
}

const BookReaderView = ({ bookId, bookTitle, bookPath, fileType, initialStickyNotes = [], initialHighlights = [], onClose, sessionId }: BookReaderViewProps) => {
    const [currentPage, setCurrentPage] = useState(1);
    const [numPages, setNumPages] = useState<number | null>(null);
    const [containerWidth, setContainerWidth] = useState(window.innerWidth * 0.6); // Start with a safe estimate
    const [leftSidebarOpen, setLeftSidebarOpen] = useState(true);
    const [rightSidebarOpen, setRightSidebarOpen] = useState(true);

    // Text Selection States
    const [selectedText, setSelectedText] = useState('');
    const [selectionMenu, setSelectionMenu] = useState<{ x: number; y: number } | null>(null);
    const [selectionBoundingBox, setSelectionBoundingBox] = useState<DOMRect | null>(null);
    const [showInlineChat, setShowInlineChat] = useState(false);
    const [inlineChatPosition, setInlineChatPosition] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
    const [aiResponse, setAiResponse] = useState('');
    const [isGenerating, setIsGenerating] = useState(false);
    const pdfContainerRef = useRef<HTMLDivElement>(null);

    // Annotations State (Real persistence)
    const [stickyNotes, setStickyNotes] = useState<StickyNote[]>(initialStickyNotes);
    const [highlights, setHighlights] = useState<Highlight[]>(initialHighlights);
    const [hoveredHighlight, setHoveredHighlight] = useState<string | null>(null);

    // Add Note Input State
    const [isAddingNote, setIsAddingNote] = useState(false);
    const [newNoteContent, setNewNoteContent] = useState('');

    // Text File State
    const [textContent, setTextContent] = useState<string>('');
    const [isTextLoading, setIsTextLoading] = useState(false);

    // Save annotations to backend
    const saveAnnotations = async (updatedNotes: StickyNote[], updatedHighlights: Highlight[]) => {
        if (!auth.currentUser || !bookId) return;
        try {
            const token = await auth.currentUser.getIdToken();
            const url = sessionId
                ? `${API_BASE_URL}/sessions/${sessionId}/bookshelf/${bookId}`
                : `${API_BASE_URL}/bookshelf/${bookId}`;

            await fetch(url, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    stickyNotes: updatedNotes,
                    highlights: updatedHighlights
                })
            });
        } catch (err) {
            console.error("Failed to save annotations", err);
        }
    };

    const handleAddStickyNote = () => {
        if (!newNoteContent.trim()) return;
        const newNote: StickyNote = {
            id: Date.now().toString(),
            content: newNoteContent,
            page: currentPage
        };
        const updatedNotes = [...stickyNotes, newNote];
        setStickyNotes(updatedNotes);
        setNewNoteContent('');
        setIsAddingNote(false);
        saveAnnotations(updatedNotes, highlights);
    };

    // Aggressively force HTTPS for Render backend to avoid Mixed Content errors
    // The previous check was too strict. We want to upgrade ANY Render URL to HTTPS.
    const secureBookPath = bookPath && bookPath.includes('onrender.com')
        ? bookPath.replace('http://', 'https://')
        : bookPath;

    const isPDF = useMemo(() => fileType === 'pdf' || (!fileType && secureBookPath.toLowerCase().endsWith('.pdf')), [secureBookPath, fileType]);
    const isImage = useMemo(() => fileType === 'image' || (!fileType && /\.(jpg|jpeg|png|gif|webp|bmp|svg)$/i.test(secureBookPath)), [secureBookPath, fileType]);
    const isVideo = useMemo(() => fileType === 'video' || (!fileType && /\.(mp4|webm|ogg)$/i.test(secureBookPath)), [secureBookPath, fileType]);
    const isText = useMemo(() => fileType === 'text' || (!fileType && /\.(txt|md|json|csv|xml)$/i.test(secureBookPath)), [secureBookPath, fileType]);

    // Fetch text content
    useEffect(() => {
        if (isText && secureBookPath) {
            setIsTextLoading(true);
            fetch(secureBookPath)
                .then(res => res.text())

                .then(text => {
                    setTextContent(text);
                    setIsTextLoading(false);
                })
                .catch(err => {
                    console.error("Failed to load text file", err);
                    setTextContent("Failed to load text content.");
                    setIsTextLoading(false);
                });
        }
    }, [isText, bookPath]);

    const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
        setNumPages(numPages);
    };

    const handleNextPage = () => {
        if (numPages && currentPage < numPages) {
            setCurrentPage(currentPage + 1);
        }
    };

    const handlePrevPage = () => {
        if (currentPage > 1) {
            setCurrentPage(currentPage - 1);
        }
    };

    const [pdfError, setPdfError] = useState<Error | null>(null);

    const onDocumentLoadError = useCallback((error: Error) => {
        console.error('PDF Load Error:', error);
        console.log('Attempted path:', bookPath);
        setPdfError(error);
    }, [bookPath]);

    const options = useMemo(() => ({
        cMapUrl: `https://unpkg.com/pdfjs-dist@${pdfjs.version}/cmaps/`,
        cMapPacked: true,
        standardFontDataUrl: `https://unpkg.com/pdfjs-dist@${pdfjs.version}/standard_fonts/`,
    }), []);

    const loadingComponent = useMemo(() => (
        <div style={{
            fontFamily: '"Indie Flower", cursive',
            fontSize: '1.5rem',
            color: '#666',
            textAlign: 'center',
            padding: '50px'
        }}>
            <div style={{ fontSize: '3rem', marginBottom: '20px' }}>📄</div>
            Loading PDF...
            <div style={{ fontSize: '0.9rem', marginTop: '10px', opacity: 0.6 }}>
                {bookPath}
            </div>
        </div>
    ), [bookPath]);

    const errorComponent = useMemo(() => (
        <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            width: '100%',
            color: '#ef4444',
            textAlign: 'center',
            padding: '20px'
        }}>
            <div style={{ fontSize: '3rem', marginBottom: '10px' }}>⚠️</div>
            <div style={{ fontWeight: 'bold', marginBottom: '5px' }}>Failed to load PDF</div>
            <div style={{ fontSize: '0.95rem', maxWidth: '400px', marginBottom: '15px' }}>
                {pdfError?.message?.includes('Invalid') ?
                    "The file couldn't be read. It might be missing from the server or corrupted." :
                    (pdfError?.message || 'Unknown error')}
            </div>
            <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={onClose}
                style={{
                    padding: '8px 20px',
                    background: '#ef4444',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    fontFamily: '"Caveat", cursive',
                    fontSize: '1.1rem'
                }}
            >
                Retry Re-upload
            </motion.button>
            <div style={{ fontSize: '0.8rem', marginTop: '20px', color: '#888', opacity: 0.7 }}>
                Path: {bookPath}
            </div>

        </div>
    ), [pdfError, bookPath]);

    // Handle text selection - only on mouseup to avoid jitter
    useEffect(() => {
        const handleSelection = () => {
            // Small delay to ensure selection is fully complete
            setTimeout(() => {
                const selection = window.getSelection();
                const text = selection?.toString().trim();

                if (text && text.length > 0) {
                    const anchorNode = selection?.anchorNode;

                    // Check if selection is within PDF container
                    let isInPdfContainer = false;

                    // Method 1: Direct container check
                    if (pdfContainerRef.current?.contains(anchorNode || null)) {
                        isInPdfContainer = true;
                    }

                    // Method 2: Check if any parent has react-pdf text layer class
                    if (!isInPdfContainer && anchorNode) {
                        let element = anchorNode.nodeType === Node.TEXT_NODE
                            ? anchorNode.parentElement
                            : anchorNode as HTMLElement;

                        let depth = 0;
                        while (element && depth < 20) {
                            // Check for react-pdf text layer classes
                            if (element.classList?.contains('react-pdf__Page__textContent') ||
                                element.classList?.contains('react-pdf__Page') ||
                                element.classList?.contains('react-pdf__Document') ||
                                element.getAttribute?.('data-page-number')) {
                                isInPdfContainer = true;
                                break;
                            }
                            // Also check if we've reached our container ref
                            if (element === pdfContainerRef.current) {
                                isInPdfContainer = true;
                                break;
                            }
                            element = element.parentElement;
                            depth++;
                        }
                    }

                    if (isInPdfContainer) {
                        setSelectedText(text);

                        // Get selection position
                        const range = selection?.getRangeAt(0);
                        const rect = range?.getBoundingClientRect();

                        if (rect) {
                            // Save bounding box for highlight creation
                            setSelectionBoundingBox(rect);
                            setSelectionMenu({
                                x: rect.left + rect.width / 2,
                                y: rect.top - 10
                            });
                        }
                    } else {
                        setSelectionMenu(null);
                    }
                } else {
                    setSelectionMenu(null);
                }
            }, 100); // 100ms delay to ensure selection is complete
        };

        // ONLY use mouseup - selectionchange causes jitter during dragging
        document.addEventListener('mouseup', handleSelection);

        return () => {
            document.removeEventListener('mouseup', handleSelection);
        };
    }, []);

    useEffect(() => {
        if (!pdfContainerRef.current) return;

        let timeoutId: any;
        const observer = new ResizeObserver((entries) => {
            // Debounce the resize to prevent jittering during transitions
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                for (const entry of entries) {
                    const newWidth = Math.floor(entry.contentRect.width - 40);
                    if (newWidth > 0) setContainerWidth(newWidth);
                }
            }, 100);
        });

        observer.observe(pdfContainerRef.current);
        return () => {
            observer.disconnect();
            clearTimeout(timeoutId);
        };
    }, [leftSidebarOpen, rightSidebarOpen]);

    // Handle scroll to top on page change

    // Generate AI explanation for selected text (LEGACY MOCK - REMOVED)
    // const generateExplanation = useCallback((text: string): string => ...);

    const handleExplainThis = useCallback(async () => {
        if (!selectedText || !selectionBoundingBox || isGenerating) return;

        // Get PDF container position for relative positioning
        const containerRect = pdfContainerRef.current?.getBoundingClientRect();
        if (!containerRect) return;

        // Store selected text and bounding box before clearing overlay
        const textToExplain = selectedText;
        const rect = selectionBoundingBox;

        if (selectionMenu) {
            setInlineChatPosition({ x: selectionMenu.x, y: selectionMenu.y });
        }

        // Clear selection overlay immediately to show responsiveness
        setSelectionMenu(null);
        setSelectedText('');
        setSelectionBoundingBox(null);
        window.getSelection()?.removeAllRanges();

        setIsGenerating(true);
        setShowInlineChat(true);
        setAiResponse('');
        // Calculate position relative to PDF container (as percentage)
        const relativeX = ((rect.left - containerRect.left) / containerRect.width) * 100;
        const relativeY = ((rect.top - containerRect.top) / containerRect.height) * 100;
        const relativeWidth = (rect.width / containerRect.width) * 100;
        const relativeHeight = (rect.height / containerRect.height) * 100;

        try {
            const currentUser = auth.currentUser;
            if (!currentUser) throw new Error("User not authenticated");

            const token = await currentUser.getIdToken();
            const response = await fetch(`${API_BASE_URL}/explain`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    text: textToExplain,
                    bookTitle: bookTitle,
                    bookId: bookId
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: "Internal Server Error" }));
                throw new Error(errorData.error || "Failed to get explanation");
            }
            const data = await response.json();
            const explanation = data.explanation;

            setAiResponse(explanation);

            // Create new highlight
            const newHighlight: Highlight = {
                id: `highlight-${Date.now()}`,
                page: currentPage,
                text: textToExplain,
                explanation: explanation,
                boundingBox: {
                    x: relativeX,
                    y: relativeY,
                    width: relativeWidth,
                    height: relativeHeight
                },
                color: 'rgba(255, 235, 59, 0.3)' // Semi-transparent yellow
            };

            // Add to highlights and save
            const updatedHighlights = [...highlights, newHighlight];
            setHighlights(updatedHighlights);
            await saveAnnotations(stickyNotes, updatedHighlights);
        } catch (err) {
            console.error("Explanation error:", err);
            setAiResponse(`❌ **Error**: ${err instanceof Error ? err.message : 'Failed to get explanation. Please try again.'}`);
        } finally {
            setIsGenerating(false);
        }
    }, [selectedText, selectionBoundingBox, currentPage, highlights, stickyNotes, saveAnnotations, bookTitle, bookId, isGenerating]);

    // Delete highlight
    const handleDeleteHighlight = useCallback(async (id: string) => {
        const updatedHighlights = highlights.filter(h => h.id !== id);
        setHighlights(updatedHighlights);
        await saveAnnotations(stickyNotes, updatedHighlights);
    }, [highlights, stickyNotes, saveAnnotations]);

    const handleCopyText = () => {
        if (selectedText) {
            navigator.clipboard.writeText(selectedText);
            setSelectionMenu(null);
            window.getSelection()?.removeAllRanges();
        }
    };

    const closeInlineChat = () => {
        setShowInlineChat(false);
        setAiResponse('');
        window.getSelection()?.removeAllRanges();
    };

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{
                position: 'fixed',
                top: 0,
                left: 0,
                width: '100vw',
                height: '100vh',
                background: '#f4f6f9',
                zIndex: 1000,
                display: 'flex',
                flexDirection: 'column'
            }}
        >
            {/* Header */}
            <div style={{
                height: '70px',
                background: 'rgba(255,255,255,0.9)',
                backdropFilter: 'blur(10px)',
                borderBottom: '1px solid rgba(0,0,0,0.05)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0 30px',
                boxShadow: '0 2px 10px rgba(0,0,0,0.05)'
            }}>
                <h2 style={{ margin: 0, fontFamily: '"Caveat", cursive', fontSize: '1.8rem', color: '#333' }}>
                    📖 {bookTitle}
                </h2>
                <button
                    onClick={onClose}
                    style={{
                        background: 'white',
                        border: '1px solid #ddd',
                        borderRadius: '12px',
                        padding: '10px 20px',
                        cursor: 'pointer',
                        fontFamily: '"Caveat", cursive',
                        fontSize: '1.2rem',
                        color: '#555'
                    }}
                >
                    ✕ Close
                </button>
            </div>

            {/* Main Content */}
            <div style={{
                flex: 1,
                display: 'grid',
                gridTemplateColumns: `${leftSidebarOpen ? '260px' : '0px'} 1fr ${rightSidebarOpen ? '280px' : '0px'}`,
                gap: '0px',
                padding: '20px',
                height: 'calc(100vh - 70px)',
                overflow: 'hidden',
                transition: 'grid-template-columns 0.4s cubic-bezier(0.4, 0, 0.2, 1)'
            }}>
                {/* Left Panel - 3D Sticky Notes on Wall */}
                <AnimatePresence mode="wait">
                    {leftSidebarOpen && (
                        <motion.div
                            initial={{ x: -260, opacity: 0 }}
                            animate={{ x: 0, opacity: 1 }}
                            exit={{ x: -260, opacity: 0 }}
                            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                            style={{
                                width: '260px',
                                background: 'linear-gradient(135deg, #f5f3f0 0%, #e8e6e3 100%)', // Wall texture
                                backgroundImage: `
                                    linear-gradient(90deg, rgba(0,0,0,0.02) 1px, transparent 1px),
                                    linear-gradient(rgba(0,0,0,0.02) 1px, transparent 1px)
                                `,
                                backgroundSize: '20px 20px',
                                borderRadius: '20px',
                                padding: '20px',
                                overflowY: 'auto',
                                overflowX: 'hidden',
                                border: '1px solid rgba(200,200,200,0.4)',
                                boxShadow: 'inset 0 0 50px rgba(0,0,0,0.05), 0 4px 20px rgba(0,0,0,0.08)',
                                zIndex: 10,
                                marginRight: leftSidebarOpen ? '20px' : '0px'
                            }}
                        >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <h3 style={{ fontFamily: '"Indie Flower", cursive', color: '#333', marginTop: 0, textShadow: '2px 2px 4px rgba(255,255,255,0.8)' }}>
                                    📌 My Notes
                                </h3>
                                <button
                                    onClick={() => setIsAddingNote(true)}
                                    style={{
                                        background: 'white',
                                        border: '1px solid #ddd',
                                        borderRadius: '50%',
                                        width: '32px',
                                        height: '32px',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        fontSize: '1.2rem',
                                        boxShadow: '0 2px 5px rgba(0,0,0,0.1)'
                                    }}
                                >
                                    +
                                </button>
                            </div>

                            <div style={{ display: 'flex', flexDirection: 'column', gap: '15px', marginTop: '20px' }}>
                                {/* Input for new note */}
                                <AnimatePresence>
                                    {isAddingNote && (
                                        <motion.div
                                            initial={{ scale: 0.8, opacity: 0 }}
                                            animate={{ scale: 1, opacity: 1 }}
                                            exit={{ scale: 0.8, opacity: 0 }}
                                            style={{
                                                background: '#fef08a',
                                                padding: '15px',
                                                borderRadius: '2px',
                                                boxShadow: '5px 5px 15px rgba(0,0,0,0.1)',
                                                transform: 'rotate(-2deg)',
                                                marginBottom: '20px'
                                            }}
                                        >
                                            <textarea
                                                value={newNoteContent}
                                                onChange={(e) => setNewNoteContent(e.target.value)}
                                                placeholder="Type your note..."
                                                autoFocus
                                                style={{
                                                    width: '100%',
                                                    height: '100px',
                                                    background: 'transparent',
                                                    border: 'none',
                                                    fontFamily: '"Caveat", cursive',
                                                    fontSize: '1.1rem',
                                                    outline: 'none',
                                                    resize: 'none'
                                                }}
                                            />
                                            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                                                <button onClick={() => setIsAddingNote(false)} style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontFamily: '"Caveat", cursive' }}>Cancel</button>
                                                <button onClick={handleAddStickyNote} style={{ background: '#333', color: 'white', border: 'none', padding: '4px 12px', borderRadius: '4px', cursor: 'pointer', fontFamily: '"Caveat", cursive' }}>Save</button>
                                            </div>
                                        </motion.div>
                                    )}
                                </AnimatePresence>

                                {/* List of notes organized by page */}
                                {[...Array(numPages || 0)].map((_, i) => {
                                    const page = i + 1;
                                    const pageNotes = stickyNotes.filter((n: StickyNote) => n.page === page);
                                    const isCurrentPage = page === currentPage;

                                    if (pageNotes.length === 0) return null;

                                    return (
                                        <div key={page} style={{ marginBottom: '10px' }}>
                                            <div style={{
                                                fontSize: '0.95rem',
                                                color: isCurrentPage ? '#6C63FF' : '#666',
                                                fontFamily: '"Caveat", cursive',
                                                marginBottom: '10px',
                                                fontWeight: isCurrentPage ? 'bold' : 'normal',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '5px'
                                            }}>
                                                {isCurrentPage && '👉'} Page {page}
                                            </div>
                                            {pageNotes.map((note: StickyNote) => (
                                                <motion.div
                                                    key={note.id}
                                                    whileHover={{
                                                        scale: 1.03,
                                                        rotateZ: 0,
                                                        y: -3,
                                                        boxShadow: '0 8px 20px rgba(0,0,0,0.2)'
                                                    }}
                                                    onClick={() => note.page && setCurrentPage(note.page)}
                                                    transition={{ type: 'spring', stiffness: 300 }}
                                                    style={{
                                                        background: isCurrentPage ? '#fef08a' : '#fef3c7',
                                                        padding: '12px',
                                                        borderRadius: '2px',
                                                        boxShadow: `
                                                        0 3px 6px rgba(0,0,0,0.1),
                                                        inset 0 0 20px rgba(255,255,255,0.3)
                                                    `,
                                                        fontFamily: '"Caveat", cursive',
                                                        fontSize: '1rem',
                                                        color: '#333',
                                                        cursor: 'pointer',
                                                        border: 'none',
                                                        position: 'relative',
                                                        marginBottom: '8px',
                                                        backgroundImage: 'linear-gradient(to bottom, rgba(255,255,255,0.2) 0%, transparent 100%)'
                                                    }}
                                                >
                                                    {/* Pin effect at top */}
                                                    <div style={{
                                                        position: 'absolute',
                                                        top: '-6px',
                                                        left: '50%',
                                                        transform: 'translateX(-50%)',
                                                        width: '24px',
                                                        height: '12px',
                                                        background: isCurrentPage ? 'rgba(255,100,100,0.4)' : 'rgba(200,200,200,0.3)',
                                                        borderRadius: '2px',
                                                        boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
                                                    }} />
                                                    {note.content}
                                                </motion.div>
                                            ))}
                                        </div>
                                    );
                                })}
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Center Panel - PDF Viewer with Journal Effect */}
                <motion.div
                    initial={{ scale: 0.95, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ delay: 0.1 }}
                    style={{
                        flex: 1,
                        background: 'linear-gradient(to right, #f4f1e8 0%, #fdfbf7 50%, #f4f1e8 100%)',
                        borderRadius: '20px',
                        padding: '30px',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'flex-start',
                        position: 'relative',
                        boxShadow: `
                            0 10px 40px rgba(0,0,0,0.15),
                            inset -5px 0 10px rgba(0,0,0,0.05),
                            inset 5px 0 10px rgba(0,0,0,0.05)
                        `,
                        overflow: 'auto',
                        backgroundImage: `
                            linear-gradient(90deg, rgba(0,0,0,0.05) 1px, transparent 1px),
                            linear-gradient(rgba(0,0,0,0.02) 1px, transparent 1px)
                        `,
                        backgroundSize: '50% 100%, 100% 20px',
                        backgroundPosition: 'center, 0 0'
                    }}
                >
                    {/* Document Display Area */}
                    <div style={{
                        flex: 1,
                        width: '100%',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'flex-start',
                        paddingTop: '60px',
                        paddingBottom: '60px',
                        position: 'relative',
                        minHeight: '100%'
                    }}>
                        {isPDF ? (
                            <div ref={pdfContainerRef} style={{ position: 'relative', width: '100%', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-start' }}>
                                <Document
                                    file={secureBookPath}
                                    onLoadSuccess={onDocumentLoadSuccess}
                                    onLoadError={onDocumentLoadError}
                                    options={options}
                                    loading={loadingComponent}
                                    error={errorComponent}
                                >
                                    <Page
                                        pageNumber={currentPage}
                                        width={containerWidth}
                                        renderTextLayer={true}
                                        renderAnnotationLayer={true}
                                    />

                                    {/* Persistent Highlights with Hover Tooltips */}
                                    {highlights.filter(h => h.page === currentPage).map((highlight, index) => (
                                        <motion.div
                                            key={highlight.id}
                                            initial={{ opacity: 0, scale: 0.95 }}
                                            animate={{ opacity: 1, scale: 1 }}
                                            exit={{ opacity: 0, scale: 0.95 }}
                                            transition={{ delay: index * 0.05 }}
                                            onMouseEnter={() => setHoveredHighlight(highlight.id)}
                                            onMouseLeave={() => setHoveredHighlight(null)}
                                            style={{
                                                position: 'absolute',
                                                left: `${highlight.boundingBox.x}%`,
                                                top: `${highlight.boundingBox.y}%`,
                                                width: `${highlight.boundingBox.width}%`,
                                                height: `${highlight.boundingBox.height}%`,
                                                background: highlight.color,
                                                border: '2px solid rgba(255, 193, 7, 0.6)',
                                                borderRadius: '3px',
                                                cursor: 'pointer',
                                                zIndex: 5,
                                                transition: 'all 0.2s ease',
                                                boxShadow: hoveredHighlight === highlight.id
                                                    ? '0 4px 12px rgba(255, 193, 7, 0.4)'
                                                    : '0 1px 3px rgba(0,0,0,0.1)'
                                            }}
                                        >
                                            {/* Delete button */}
                                            <motion.button
                                                initial={{ opacity: 0 }}
                                                animate={{ opacity: hoveredHighlight === highlight.id ? 1 : 0 }}
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    handleDeleteHighlight(highlight.id);
                                                }}
                                                style={{
                                                    position: 'absolute',
                                                    top: '-8px',
                                                    right: '-8px',
                                                    width: '20px',
                                                    height: '20px',
                                                    borderRadius: '50%',
                                                    background: '#f87171',
                                                    border: '2px solid white',
                                                    color: 'white',
                                                    fontSize: '12px',
                                                    fontWeight: 'bold',
                                                    cursor: 'pointer',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'center',
                                                    boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
                                                    zIndex: 10,
                                                    pointerEvents: hoveredHighlight === highlight.id ? 'auto' : 'none'
                                                }}
                                            >
                                                ×
                                            </motion.button>

                                            {/* Hover tooltip with explanation */}
                                            <AnimatePresence>
                                                {hoveredHighlight === highlight.id && (
                                                    <motion.div
                                                        initial={{ opacity: 0, y: 10, scale: 0.95 }}
                                                        animate={{ opacity: 1, y: 0, scale: 1 }}
                                                        exit={{ opacity: 0, y: 10, scale: 0.95 }}
                                                        transition={{ duration: 0.2 }}
                                                        style={{
                                                            position: 'absolute',
                                                            bottom: '100%',
                                                            left: '50%',
                                                            transform: 'translateX(-50%)',
                                                            marginBottom: '10px',
                                                            minWidth: '250px',
                                                            maxWidth: '350px',
                                                            background: '#fffbeb',
                                                            border: '2px solid #fbbf24',
                                                            borderRadius: '8px',
                                                            padding: '12px 16px',
                                                            boxShadow: '0 8px 20px rgba(0,0,0,0.15)',
                                                            zIndex: 1000,
                                                            pointerEvents: 'none',
                                                            fontFamily: '"Indie Flower", cursive',
                                                            fontSize: '0.95rem',
                                                            lineHeight: '1.5',
                                                            color: '#333',
                                                            whiteSpace: 'pre-wrap'
                                                        }}
                                                    >
                                                        <div style={{
                                                            fontWeight: 'bold',
                                                            marginBottom: '8px',
                                                            color: '#92400e',
                                                            fontSize: '0.85rem',
                                                            borderBottom: '1px dashed #fbbf24',
                                                            paddingBottom: '6px'
                                                        }}>
                                                            📝 "{highlight.text.substring(0, 30)}{highlight.text.length > 30 ? '...' : ''}"
                                                        </div>
                                                        <MarkdownRenderer content={highlight.explanation} />

                                                        <div style={{
                                                            position: 'absolute',
                                                            bottom: '-10px',
                                                            left: '50%',
                                                            transform: 'translateX(-50%)',
                                                            width: 0,
                                                            height: 0,
                                                            borderLeft: '10px solid transparent',
                                                            borderRight: '10px solid transparent',
                                                            borderTop: '10px solid #fbbf24'
                                                        }} />
                                                    </motion.div>
                                                )}
                                            </AnimatePresence>
                                        </motion.div>
                                    ))}
                                </Document>
                            </div>
                        ) : (
                            isImage ? (
                                <img
                                    src={secureBookPath}
                                    alt={bookTitle}
                                    style={{
                                        maxWidth: '100%',
                                        maxHeight: '100%',
                                        objectFit: 'contain',
                                        borderRadius: '8px',
                                        boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                                    }}
                                />
                            ) : isVideo ? (
                                <div style={{
                                    width: '100%',
                                    height: '100%',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    background: '#000',
                                    borderRadius: '12px',
                                    overflow: 'hidden'
                                }}>
                                    <video
                                        src={secureBookPath}
                                        controls
                                        autoPlay
                                        style={{
                                            maxWidth: '100%',
                                            maxHeight: '100%'
                                        }}
                                    />
                                </div>
                            ) : isText ? (
                                <div style={{
                                    width: '100%',
                                    height: '100%',
                                    background: '#fff',
                                    borderRadius: '8px',
                                    padding: '30px',
                                    overflowY: 'auto',
                                    boxShadow: '0 4px 15px rgba(0,0,0,0.05)',
                                    fontFamily: '"Courier New", Courier, monospace',
                                    fontSize: '0.9rem',
                                    color: '#333',
                                    whiteSpace: 'pre-wrap',
                                    lineHeight: '1.6'
                                }}>
                                    {isTextLoading ? (
                                        <div style={{ textAlign: 'center', padding: '20px', color: '#666', fontFamily: '"Indie Flower", cursive', fontSize: '1.2rem' }}>
                                            ⏳ Reading text...
                                        </div>
                                    ) : (
                                        textContent
                                    )}
                                </div>
                            ) : (
                                <div style={{
                                    fontFamily: '"Indie Flower", cursive',
                                    fontSize: '1.2rem',
                                    color: '#666',
                                    textAlign: 'center',
                                    padding: '50px'
                                }}>
                                    <div style={{ fontSize: '3rem', marginBottom: '20px' }}>📁</div>
                                    Unsupported file format
                                    <div style={{ fontSize: '0.9rem', marginTop: '10px', opacity: 0.6 }}>
                                        {bookPath}
                                    </div>
                                    <div style={{ fontSize: '0.8rem', marginTop: '5px', opacity: 0.5 }}>
                                        Type: {fileType || 'Unknown'}
                                    </div>
                                </div>
                            )
                        )}
                    </div>
                </motion.div >

                {/* Right Panel - Wispen AI Responses */}
                <AnimatePresence mode="wait">
                    {rightSidebarOpen && (
                        <motion.div
                            initial={{ x: 300, opacity: 0 }}
                            animate={{ x: 0, opacity: 1 }}
                            exit={{ x: 300, opacity: 0 }}
                            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                            style={{
                                width: '280px',
                                background: 'rgba(255,255,255,0.6)',
                                backdropFilter: 'blur(10px)',
                                borderRadius: '20px',
                                padding: '20px',
                                overflowY: 'auto',
                                overflowX: 'hidden',
                                border: '1px solid rgba(255,255,255,0.8)',
                                boxShadow: '0 4px 20px rgba(0,0,0,0.05)',
                                zIndex: 10,
                                marginLeft: rightSidebarOpen ? '20px' : '0px'
                            }}
                        >
                            <h3 style={{ fontFamily: '"Indie Flower", cursive', color: '#333', marginTop: 0 }}>
                                🎓 Wispen Explains
                            </h3>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                                {/* Show current page highlights first */}
                                {highlights.filter(h => h.page === currentPage).length > 0 && (
                                    <>
                                        <div style={{ fontSize: '0.9rem', color: '#666', fontFamily: '"Caveat", cursive', marginBottom: '5px' }}>
                                            💡 For This Page:
                                        </div>
                                        {highlights.filter(h => h.page === currentPage).map((highlight: Highlight) => (
                                            <motion.div
                                                key={highlight.id}
                                                initial={{ scale: 0.9 }}
                                                animate={{ scale: 1 }}
                                                whileHover={{ scale: 1.02 }}
                                                style={{
                                                    background: 'linear-gradient(135deg, #f3e7e9 0%, #e3eeff 100%)',
                                                    padding: '15px',
                                                    borderRadius: '12px',
                                                    boxShadow: '0 3px 10px rgba(0,0,0,0.1)',
                                                    cursor: 'pointer',
                                                    border: '2px solid #6C63FF'
                                                }}
                                            >
                                                <div style={{
                                                    fontFamily: '"Caveat", cursive',
                                                    fontSize: '1.1rem',
                                                    fontWeight: 'bold',
                                                    color: '#555',
                                                    marginBottom: '8px'
                                                }}>
                                                    "{highlight.text.substring(0, 50)}{highlight.text.length > 50 ? '...' : ''}"
                                                </div>
                                                <div style={{
                                                    fontFamily: '"Indie Flower", cursive',
                                                    fontSize: '1rem',
                                                    color: '#333',
                                                    lineHeight: '1.5'
                                                }}>
                                                    <MarkdownRenderer content={highlight.explanation} />
                                                </div>
                                            </motion.div>
                                        ))}
                                        <div style={{ borderTop: '1px dashed #ddd', margin: '10px 0' }} />
                                    </>
                                )}

                                {/* All highlights */}
                                <div style={{ fontSize: '0.9rem', color: '#666', fontFamily: '"Caveat", cursive', marginBottom: '5px' }}>
                                    📚 All Explanations:
                                </div>
                                {highlights.map((highlight: Highlight) => (
                                    <motion.div
                                        key={highlight.id}
                                        whileHover={{ scale: 1.02 }}
                                        onClick={() => highlight.page && setCurrentPage(highlight.page)}
                                        style={{
                                            background: 'linear-gradient(135deg, #f3e7e9 0%, #e3eeff 100%)',
                                            padding: '15px',
                                            borderRadius: '12px',
                                            boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
                                            cursor: 'pointer'
                                        }}
                                    >
                                        <div style={{
                                            fontFamily: '"Caveat", cursive',
                                            fontSize: '1.1rem',
                                            fontWeight: 'bold',
                                            color: '#555',
                                            marginBottom: '8px'
                                        }}>
                                            Page {highlight.page}: "{highlight.text.substring(0, 30)}..."
                                        </div>
                                        <div style={{
                                            fontFamily: '"Indie Flower", cursive',
                                            fontSize: '1rem',
                                            color: '#333',
                                            lineHeight: '1.5'
                                        }}>
                                            <MarkdownRenderer content={highlight.explanation} />
                                        </div>
                                        {highlight.page && (
                                            <div style={{
                                                fontSize: '0.8rem',
                                                marginTop: '8px',
                                                opacity: 0.6,
                                                fontFamily: '"Caveat", cursive'
                                            }}>
                                                📄 → Page {highlight.page}
                                            </div>
                                        )}
                                    </motion.div>
                                ))}
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Sidebar Toggle Buttons */}
                <div style={{
                    position: 'fixed',
                    bottom: '25px',
                    left: '25px',
                    zIndex: 1000
                }}>
                    <button
                        onClick={() => setLeftSidebarOpen(!leftSidebarOpen)}
                        style={{
                            background: 'white',
                            border: '2px solid #6C63FF',
                            borderRadius: '50%',
                            width: '45px',
                            height: '45px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '1.2rem',
                            boxShadow: '0 4px 12px rgba(108, 99, 255, 0.2)',
                            transition: 'all 0.3s ease'
                        }}
                    >
                        {leftSidebarOpen ? '📒' : '📖'}
                    </button>
                </div>

                <div style={{
                    position: 'fixed',
                    bottom: '25px',
                    right: '25px',
                    zIndex: 1000
                }}>
                    <button
                        onClick={() => setRightSidebarOpen(!rightSidebarOpen)}
                        style={{
                            background: 'white',
                            border: '2px solid #6C63FF',
                            borderRadius: '50%',
                            width: '45px',
                            height: '45px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '1.2rem',
                            boxShadow: '0 4px 12px rgba(108, 99, 255, 0.2)',
                            transition: 'all 0.3s ease'
                        }}
                    >
                        {rightSidebarOpen ? '🎓' : '✨'}
                    </button>
                </div>

                {/* Page Navigation - Fixed Bottom Bar */}
                {isPDF && (
                    <div style={{
                        position: 'fixed',
                        bottom: '25px',
                        left: '50%',
                        transform: 'translateX(-50%)',
                        background: 'rgba(255,255,255,0.9)',
                        backdropFilter: 'blur(10px)',
                        padding: '12px 24px',
                        borderRadius: '16px',
                        display: 'flex',
                        gap: '20px',
                        alignItems: 'center',
                        boxShadow: '0 8px 32px rgba(0,0,0,0.1)',
                        border: '2px solid #6C63FF',
                        zIndex: 1001
                    }}>
                        <button
                            onClick={handlePrevPage}
                            disabled={currentPage === 1}
                            style={{
                                background: currentPage === 1 ? '#eee' : 'linear-gradient(135deg, #6C63FF 0%, #4834d4 100%)',
                                color: currentPage === 1 ? '#999' : 'white',
                                border: 'none',
                                borderRadius: '12px',
                                padding: '8px 20px',
                                cursor: currentPage === 1 ? 'not-allowed' : 'pointer',
                                fontFamily: '"Caveat", cursive',
                                fontSize: '1.1rem',
                                fontWeight: 'bold',
                                transition: 'all 0.2s ease'
                            }}
                        >
                            ← Prev
                        </button>
                        <span style={{
                            fontFamily: '"Indie Flower", cursive',
                            fontSize: '1.1rem',
                            color: '#333',
                            fontWeight: 'bold',
                            minWidth: '100px',
                            textAlign: 'center'
                        }}>
                            Page {currentPage} / {numPages || '...'}
                        </span>
                        <button
                            onClick={handleNextPage}
                            disabled={!numPages || currentPage === numPages}
                            style={{
                                background: (!numPages || currentPage === numPages) ? '#eee' : 'linear-gradient(135deg, #6C63FF 0%, #4834d4 100%)',
                                color: (!numPages || currentPage === numPages) ? '#999' : 'white',
                                border: 'none',
                                borderRadius: '12px',
                                padding: '8px 20px',
                                cursor: (!numPages || currentPage === numPages) ? 'not-allowed' : 'pointer',
                                fontFamily: '"Caveat", cursive',
                                fontSize: '1.1rem',
                                fontWeight: 'bold',
                                transition: 'all 0.2s ease'
                            }}
                        >
                            Next →
                        </button>
                    </div>
                )}
            </div >

            {/* Text Selection Context Menu - Google AI Style */}
            <AnimatePresence>
                {
                    selectionMenu && !showInlineChat && (
                        <motion.div
                            initial={{ opacity: 0, scale: 0.9, y: -10 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.9 }}
                            transition={{ duration: 0.2 }}
                            style={{
                                position: 'fixed',
                                left: selectionMenu.x,
                                top: selectionMenu.y,
                                transform: 'translate(-50%, -100%)',
                                zIndex: 10000,
                                display: 'flex',
                                gap: '8px',
                                background: 'white',
                                borderRadius: '12px',
                                padding: '8px',
                                boxShadow: '0 4px 20px rgba(0,0,0,0.15), 0 0 0 1px rgba(0,0,0,0.05)',
                                backdropFilter: 'blur(10px)'
                            }}
                        >
                            <button
                                onClick={handleExplainThis}
                                style={{
                                    background: 'linear-gradient(135deg, #6C63FF 0%, #4834d4 100%)',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '8px',
                                    padding: '8px 16px',
                                    fontFamily: '"Caveat", cursive',
                                    fontSize: '1rem',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '6px',
                                    fontWeight: 'bold',
                                    transition: 'transform 0.2s'
                                }}
                                onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.05)'}
                                onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
                            >
                                ✨ Explain this
                            </button>
                            <button
                                onClick={handleCopyText}
                                style={{
                                    background: 'white',
                                    color: '#333',
                                    border: '1px solid #ddd',
                                    borderRadius: '8px',
                                    padding: '8px 16px',
                                    fontFamily: '"Caveat", cursive',
                                    fontSize: '1rem',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '6px',
                                    transition: 'transform 0.2s'
                                }}
                                onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.05)'}
                                onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
                            >
                                📋 Copy
                            </button>
                        </motion.div>
                    )
                }
            </AnimatePresence >

            {/* Inline Chat - Copilot Style */}
            <AnimatePresence>
                {
                    showInlineChat && (
                        <motion.div
                            initial={{ opacity: 0, y: -20, scale: 0.95 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            exit={{ opacity: 0, y: -20, scale: 0.95 }}
                            transition={{ duration: 0.3, type: 'spring' }}
                            style={{
                                position: 'fixed',
                                left: Math.min(inlineChatPosition.x, window.innerWidth - 420),
                                top: Math.min(inlineChatPosition.y, window.innerHeight - 300),
                                width: '400px',
                                maxHeight: '250px',
                                background: 'linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%)',
                                borderRadius: '16px',
                                boxShadow: '0 10px 40px rgba(0,0,0,0.2), 0 0 0 1px rgba(108,99,255,0.1)',
                                zIndex: 10001,
                                overflow: 'hidden',
                                border: '2px solid #6C63FF'
                            }}
                        >
                            {/* Header */}
                            <div style={{
                                background: 'linear-gradient(135deg, #6C63FF 0%, #4834d4 100%)',
                                color: 'white',
                                padding: '12px 16px',
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center'
                            }}>
                                <div style={{
                                    fontFamily: '"Indie Flower", cursive',
                                    fontSize: '1.1rem',
                                    fontWeight: 'bold',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px'
                                }}>
                                    🤖 Wispen AI
                                    {isGenerating && (
                                        <motion.span
                                            animate={{ rotate: 360 }}
                                            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                                            style={{ display: 'inline-block' }}
                                        >
                                            ⚡
                                        </motion.span>
                                    )}
                                </div>
                                <button
                                    onClick={closeInlineChat}
                                    style={{
                                        background: 'transparent',
                                        border: 'none',
                                        color: 'white',
                                        fontSize: '1.3rem',
                                        cursor: 'pointer',
                                        padding: '4px',
                                        lineHeight: '1'
                                    }}
                                >
                                    ✕
                                </button>
                            </div>

                            {/* Content */}
                            <div style={{
                                padding: '16px',
                                maxHeight: '180px',
                                overflowY: 'auto',
                                fontFamily: '"Indie Flower", cursive',
                                fontSize: '1rem',
                                color: '#333',
                                lineHeight: '1.6'
                            }}>
                                {isGenerating ? (
                                    <div style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '12px',
                                        color: '#666'
                                    }}>
                                        <motion.div
                                            animate={{ scale: [1, 1.2, 1] }}
                                            transition={{ duration: 1, repeat: Infinity }}
                                        >
                                            💭
                                        </motion.div>
                                        <span>Thinking...</span>
                                    </div>
                                ) : (
                                    <MarkdownRenderer content={aiResponse} />
                                )}
                            </div>
                        </motion.div>
                    )
                }
            </AnimatePresence >
        </motion.div >
    );
};

export default BookReaderView;

