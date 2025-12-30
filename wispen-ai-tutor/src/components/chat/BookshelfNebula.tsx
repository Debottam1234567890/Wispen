import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import BookReaderView from './BookReaderView';
import { auth } from '../../firebase';
import { API_BASE_URL } from '../../config';
import { pdfjs } from 'react-pdf';

// Configure worker
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
    'pdfjs-dist/build/pdf.worker.min.mjs',
    import.meta.url
).toString();

interface Book {
    id: string;
    title: string;
    color: string;
    pages: number;
    concepts: number;
    filePath?: string;
    storageUrl?: string; // Firebase Storage URL
    fileType: 'pdf' | 'image' | 'video' | 'text' | 'other';
    stickyNotes?: any[];
    highlights?: any[];
}

interface BookshelfNebulaProps {
    sessionId?: string;
}

const BookshelfNebula: React.FC<BookshelfNebulaProps> = ({ sessionId }) => {
    const [books, setBooks] = useState<Book[]>([]);
    const [isUploading, setIsUploading] = useState(false);
    const [selectedBook, setSelectedBook] = useState<Book | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Fetch bookshelf from backend
    useEffect(() => {
        const fetchBooks = async () => {
            if (!auth.currentUser || !sessionId) return;
            try {
                const token = await auth.currentUser.getIdToken();
                const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/bookshelf`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (response.ok) {
                    const data = await response.json();
                    setBooks(data);
                }
            } catch (err) {
                console.error("Failed to fetch bookshelf", err);
            }
        };
        fetchBooks();
    }, [sessionId]);

    const handleUploadClick = () => {
        fileInputRef.current?.click();
    };

    const getPDFPageCount = async (file: File): Promise<number> => {
        try {
            const buffer = await file.arrayBuffer();
            const pdf = await pdfjs.getDocument(buffer).promise;
            return pdf.numPages;
        } catch (e) {
            console.error("Error counting PDF pages", e);
            return 0;
        }
    };

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        console.log('🔥 handleFileChange CALLED!', e.target.files);

        const file = e.target.files?.[0];
        console.log('📁 File selected:', file?.name, file?.size);

        if (!file) {
            console.error('❌ No file selected!');
            alert('No file selected!');
            return;
        }

        if (!auth.currentUser) {
            console.error('❌ User not authenticated!', auth.currentUser);
            alert('Please log in first!');
            return;
        }

        console.log('✅ User authenticated:', auth.currentUser.uid);

        // Check file size (support up to 200MB)
        const maxSize = 200 * 1024 * 1024; // 200MB
        if (file.size > maxSize) {
            const sizeMB = (file.size / 1024 / 1024).toFixed(2);
            console.error(`❌ File too large: ${sizeMB}MB`);
            alert(`File too large! Please upload files smaller than 200MB. Your file: ${sizeMB}MB`);
            return;
        }

        setIsUploading(true);
        console.log('🚀 Starting upload for:', file.name, 'Size:', (file.size / 1024 / 1024).toFixed(2), 'MB');

        // Determine type
        let type: 'pdf' | 'image' | 'video' | 'text' | 'other' = 'other';
        const name = file.name.toLowerCase();
        const mime = file.type.toLowerCase();

        if (mime.startsWith('image/')) type = 'image';
        else if (mime.startsWith('video/')) type = 'video';
        else if (mime === 'application/pdf' || name.endsWith('.pdf')) type = 'pdf';
        else if (mime.startsWith('text/') || name.endsWith('.txt') || name.endsWith('.md')) type = 'text';

        console.log('📋 File type detected:', type);

        try {
            // Get actual page count for PDFs
            let pageCount = 0;
            if (type === 'pdf') {
                console.log('📊 Counting PDF pages...');
                pageCount = await getPDFPageCount(file);
                console.log('✅ Page count:', pageCount);
            } else {
                pageCount = 1;
            }

            // Upload via Backend Proxy (Bypassing CORS)
            console.log('☁️ Uploading via Backend Proxy...');
            const token = await auth.currentUser.getIdToken();

            const formData = new FormData();
            formData.append('file', file);

            const uploadResponse = await fetch(`${API_BASE_URL}/upload`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                    // Content-Type is set automatically with FormData
                },
                body: formData
            });

            if (!uploadResponse.ok) {
                const errorText = await uploadResponse.text();
                throw new Error(`Upload failed: ${uploadResponse.status} ${errorText}`);
            }

            const uploadData = await uploadResponse.json();
            const downloadURL = uploadData.url;
            console.log('✅ Upload complete. URL:', downloadURL);

            const newBook = {
                title: file.name.split('.')[0] || 'New Upload',
                color: '#' + Math.floor(Math.random() * 16777215).toString(16),
                pages: pageCount || 1,
                concepts: Math.max(1, Math.floor(pageCount / 3)),
                fileType: type,
                storageUrl: downloadURL,
                stickyNotes: [],
                highlights: []
            };

            console.log('📦 Prepared book object:', { ...newBook });

            // Save to backend
            console.log('📤 Sending POST to /bookshelf...');
            if (!sessionId) {
                alert("No active session! Cannot save book.");
                return;
            }
            const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/bookshelf`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(newBook)
            });

            console.log('📥 Response status:', response.status, response.statusText);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('❌ Backend error:', errorText);
                throw new Error(`Save failed: ${response.status} ${errorText}`);
            }

            const saved = await response.json();
            console.log('✅ Upload successful! Saved ID:', saved.id);

            saved.filePath = downloadURL; // For immediate display
            setBooks(prev => [saved, ...prev]);

            console.log('🎉 Book added to UI!');
            console.log(`✅ Upload successful! ${file.name} (${(file.size / 1024 / 1024).toFixed(2)}MB)`);
        } catch (err) {
            console.error("💥 Upload failed with error:", err);
            alert(`Failed to upload file: ${err instanceof Error ? err.message : 'Unknown error'}`);
        } finally {
            setIsUploading(false);
            console.log('🏁 Upload process complete');
        }
    };

    return (
        <>
            <AnimatePresence>
                {selectedBook && (
                    <BookReaderView
                        bookId={selectedBook.id}
                        bookTitle={selectedBook.title}
                        bookPath={selectedBook.storageUrl || selectedBook.filePath || ''}
                        fileType={selectedBook.fileType as any}
                        initialStickyNotes={selectedBook.stickyNotes || []}
                        initialHighlights={selectedBook.highlights || []}
                        onClose={() => setSelectedBook(null)}
                        sessionId={sessionId}
                    />
                )}
            </AnimatePresence>

            <div style={{
                height: '100%',
                padding: '30px',
                backgroundImage: 'radial-gradient(circle at 10% 20%, rgb(161, 205, 255) 0%, rgb(255,252,251) 90%)',
                overflowY: 'auto',
                position: 'relative'
            }}>
                {/* Title */}
                <h2 style={{
                    fontFamily: '"Indie Flower", cursive',
                    fontSize: '2.5rem',
                    color: '#333',
                    marginBottom: '20px',
                    textAlign: 'center',
                    textShadow: '2px 2px 4px rgba(0,0,0,0.1)'
                }}>
                    📚 The Bookshelf Nebula
                </h2>

                {/* Upload Button */}
                <div style={{ textAlign: 'center', marginBottom: '30px' }}>
                    <input
                        type="file"
                        hidden
                        ref={fileInputRef}
                        onChange={handleFileChange}
                        accept="*"
                    />
                    {isUploading ? (
                        <p style={{ margin: 0 }}>⏳ Uploading...</p>
                    ) : (
                        <motion.button
                            whileHover={{ scale: 1.05, y: -2 }}
                            whileTap={{ scale: 0.98 }}
                            onClick={handleUploadClick}
                            style={{
                                padding: '12px 30px',
                                fontSize: '1.1rem',
                                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                color: 'white',
                                border: 'none',
                                borderRadius: '25px',
                                cursor: 'pointer',
                                boxShadow: '0 4px 15px rgba(102,126,234,0.4)',
                                fontFamily: '"Indie Flower", cursive'
                            }}
                        >
                            📤 Upload Source
                        </motion.button>
                    )}
                    <p style={{ fontSize: '0.9rem', color: '#666', marginTop: '10px' }}>
                        💡 Drag & Drop or Click to Upload
                    </p>
                </div>

                {/* Bookshelf */}
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
                    gap: '20px',
                    perspective: '1000px'
                }}>
                    {books.map((book, index) => (
                        <motion.div
                            key={book.id}
                            initial={{ opacity: 0, y: 50, rotateY: -20 }}
                            animate={{ opacity: 1, y: 0, rotateY: 0 }}
                            transition={{ delay: index * 0.1, type: 'spring' }}
                            whileHover={{ scale: 1.05, rotateY: 5, z: 50 }}
                            onClick={() => setSelectedBook(book)}
                            style={{
                                background: book.color,
                                borderRadius: '15px 5px 5px 15px', // Adjusted for spine on left
                                padding: '10px 20px', // Horizontal padding
                                cursor: 'pointer',
                                boxShadow: '2px 4px 10px rgba(0,0,0,0.2), inset 5px 0 5px rgba(0,0,0,0.2)', // Spine shadow on left
                                position: 'relative',
                                transformStyle: 'preserve-3d',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                minHeight: '80px' // Ensure some height
                            }}
                        >
                            <div style={{
                                // writingMode: 'vertical-rl', // REMOVED
                                textAlign: 'center',
                                color: 'white',
                                fontWeight: 'bold',
                                fontSize: '1rem',
                                fontFamily: '"Indie Flower", cursive',
                                textShadow: '1px 1px 2px rgba(0,0,0,0.5)',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                display: '-webkit-box',
                                WebkitLineClamp: 2,
                                WebkitBoxOrient: 'vertical'
                            }}>
                                {book.title}
                            </div>
                            <div style={{
                                position: 'absolute',
                                bottom: '5px',
                                right: '10px',
                                fontSize: '0.7rem',
                                color: 'rgba(255,255,255,0.8)'
                            }}>
                                {book.pages}p
                            </div>
                        </motion.div>
                    ))}
                </div>
            </div>
        </>
    );
};

export default BookshelfNebula;
