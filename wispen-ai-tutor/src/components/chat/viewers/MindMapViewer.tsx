import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { auth } from '../../../firebase';
import MarkdownRenderer from '../MarkdownRenderer';
import { API_BASE_URL } from '../../../config';

interface MindMapNode {
    id: string;
    label: string;
    description: string;
    children: string[];
    hasMore?: boolean;
    collapsed?: boolean;
    x?: number;
    y?: number;
    level?: number;
}

interface MindMapData {
    root_id: string;
    nodes: Record<string, MindMapNode>;
}

interface MindMapViewerProps {
    onClose: () => void;
    initialPrompt?: string;
    mindmapId?: string;
    sessionId?: string;
}

const MindMapViewer: React.FC<MindMapViewerProps> = ({ onClose, initialPrompt = "", mindmapId, sessionId }) => {
    const [data, setData] = useState<MindMapData | null>(null);
    const [loading, setLoading] = useState(false);
    const [expanding, setExpanding] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [prompt, setPrompt] = useState(initialPrompt);
    const [showPromptInput, setShowPromptInput] = useState(!initialPrompt);
    const [zoom, setZoom] = useState(1); // Zoom level (1 = 100%)
    const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
    const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

    const handleZoomIn = () => setZoom(prev => Math.min(prev + 0.1, 2)); // Max 200%
    const handleZoomOut = () => setZoom(prev => Math.max(prev - 0.1, 0.5)); // Min 50%

    const NODE_WIDTH = 250; // Increased width slightly
    const NODE_HEIGHT = 120; // Increased height to fit more text
    const HORIZONTAL_GAP = 320;
    const VERTICAL_GAP = 140;

    const COLORS = [
        { main: '#3b82f6', light: '#eff6ff', border: '#bfdbfe', text: '#1e3a8a', gradient: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)' }, // Blue (Root)
        { main: '#10b981', light: '#ecfdf5', border: '#a7f3d0', text: '#064e3b', gradient: 'linear-gradient(135deg, #10b981 0%, #059669 100%)' }, // Emerald (L1)
        { main: '#f59e0b', light: '#fffbeb', border: '#fde68a', text: '#78350f', gradient: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)' }, // Amber (L2)
        { main: '#8b5cf6', light: '#f5f3ff', border: '#ddd6fe', text: '#4c1d95', gradient: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)' }, // Purple (L3)
        { main: '#ec4899', light: '#fdf2f8', border: '#fbcfe8', text: '#831843', gradient: 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)' }, // Pink (L4)
        { main: '#6366f1', light: '#eef2ff', border: '#c7d2fe', text: '#312e81', gradient: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)' }, // Indigo (L5)
    ];

    const getNodeColor = (level: number) => COLORS[level] || COLORS[COLORS.length - 1];

    useEffect(() => {
        if (mindmapId) {
            fetchExistingMap(mindmapId);
        } else if (initialPrompt && !showPromptInput) {
            generateMap(initialPrompt);
        }
    }, [initialPrompt, mindmapId]);

    const fetchExistingMap = async (mid: string) => {
        setLoading(true);
        setError(null);
        setShowPromptInput(false);
        try {
            const token = await auth.currentUser?.getIdToken();
            const url = sessionId
                ? `${API_BASE_URL}/sessions/${sessionId}/mindmaps/${mid}`
                : `${API_BASE_URL}/mindmaps/${mid}`;

            const response = await fetch(url, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const result = await response.json();
            if (result.error) throw new Error(result.error);

            calculateLayout(result.root_id, result.nodes);
            setData(result);
            if (result.title) setPrompt(result.title);
        } catch (err: any) {
            setError(err.message || 'Failed to fetch mindmap');
        } finally {
            setLoading(false);
        }
    };

    const generateMap = async (p: string) => {
        setLoading(true);
        setError(null);
        setShowPromptInput(false);
        try {
            const token = await auth.currentUser?.getIdToken();
            const response = await fetch(`${API_BASE_URL}/mindmap`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ prompt: p, sessionId })
            });
            const result = await response.json();
            if (result.error) throw new Error(result.error);

            calculateLayout(result.root_id, result.nodes);
            setData(result);
        } catch (err: any) {
            setError(err.message || 'Failed to generate mindmap');
        } finally {
            setLoading(false);
        }
    };

    const calculateLayout = (rootId: string, nodes: Record<string, MindMapNode>) => {
        const levels: Record<number, number> = {};
        console.log("MindMapViewer: Calculating layout starting from:", rootId, "Total nodes:", Object.keys(nodes).length);

        // Reset positions for all nodes to ensure collapsed nodes are hidden
        Object.values(nodes).forEach(node => {
            node.x = undefined;
            node.y = undefined;
        });

        const traverse = (id: string, level: number) => {
            const node = nodes[id];
            if (!node) {
                console.warn("MindMapViewer: Node not found in traverse:", id);
                return;
            }
            node.level = level;
            node.x = level * HORIZONTAL_GAP + 100;

            if (!levels[level]) levels[level] = 0;
            node.y = levels[level] * VERTICAL_GAP + 150; // Increased spacing for deep maps
            levels[level]++;

            console.log(`MindMapViewer: Laid out node ${id} at (${node.x}, ${node.y}) level ${level}`);

            // Safety check: ensure children exists and is an array
            // COLLAPSE LOGIC: Do not traverse children if collapsed
            if (node.children && Array.isArray(node.children) && !node.collapsed) {
                node.children.forEach(childId => traverse(childId, level + 1));
            }
        };

        traverse(rootId, 0);
    };

    const handleExpand = async (nodeId: string) => {
        if (!data) return;

        const node = data.nodes[nodeId];
        console.log("MindMapViewer: Expanding node:", nodeId, node.label);

        // 1. If node has children, just toggle collapse
        if (node.children && node.children.length > 0) {
            console.log("MindMapViewer: Toggling collapse for:", nodeId);
            const updatedNodes = { ...data.nodes };
            updatedNodes[nodeId] = {
                ...node,
                collapsed: !node.collapsed
            };

            const updatedData = { ...data, nodes: updatedNodes };
            calculateLayout(updatedData.root_id, updatedData.nodes);
            setData(updatedData);
            return;
        }

        // 2. If no children but has more, fetch them
        if (expanding) return;
        setExpanding(nodeId);
        try {
            const token = await auth.currentUser?.getIdToken();
            const response = await fetch(`${API_BASE_URL}/mindmap/expand`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    nodeId,
                    nodeLabel: node.label,
                    sessionId,
                    mindmapId: (data as any).id || mindmapId // Use ID from data or prop
                })
            });
            const result = await response.json();
            console.log("MindMapViewer: Expansion API result:", result);

            if (result.error) throw new Error(result.error);

            // Create a deep enough copy to avoid mutations
            const updatedNodes = { ...data.nodes };
            const parentChildren = [...(updatedNodes[nodeId].children || [])];

            if (result.children && result.children.length > 0) {
                result.children.forEach((child: any) => {
                    const childId = child.id || `node-${Math.random().toString(36).substr(2, 9)}`;
                    updatedNodes[childId] = {
                        ...child,
                        id: childId,
                        children: [],
                        level: (node.level || 0) + 1,
                        collapsed: false // specific children start uncollapsed
                    };
                    if (!parentChildren.includes(childId)) {
                        parentChildren.push(childId);
                    }
                });
            }

            // Update the parent node with new children and set hasMore to false
            updatedNodes[nodeId] = {
                ...updatedNodes[nodeId],
                children: parentChildren,
                hasMore: false,
                collapsed: false
            };

            const updatedData = { ...data, nodes: updatedNodes };

            // Recalculate layout with the new nodes list
            calculateLayout(updatedData.root_id, updatedData.nodes);
            console.log("MindMapViewer: Layout recalculated. Node count:", Object.keys(updatedNodes).length);
            setData(updatedData);

        } catch (err) {
            console.error('MindMapViewer: Expansion failed:', err);
        } finally {
            setExpanding(null);
        }
    };

    if (showPromptInput) {
        return (
            <div style={{
                position: 'fixed',
                inset: 0,
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                zIndex: 2000,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backdropFilter: 'blur(4px)',
                padding: '16px'
            }}>
                <motion.div
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    style={{
                        backgroundColor: 'white',
                        borderRadius: '24px',
                        padding: '32px',
                        width: '100%',
                        maxWidth: '512px',
                        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)'
                    }}
                >
                    <h2 style={{ fontSize: '1.875rem', fontWeight: 700, color: '#1f2937', marginBottom: '24px', fontFamily: '"Outfit", sans-serif' }}>Mindmap Prompt</h2>
                    <p style={{ color: '#6b7280', marginBottom: '24px' }}>Enter a topic to generate a dynamic mindmap from your sources.</p>
                    <input
                        type="text"
                        value={prompt}
                        onChange={(e) => setPrompt(e.target.value)}
                        placeholder="e.g. Quantum Computing Basics"
                        style={{
                            width: '100%',
                            padding: '16px',
                            backgroundColor: '#f9fafb',
                            border: '1px solid #f3f4f6',
                            borderRadius: '16px',
                            marginBottom: '24px',
                            outline: 'none',
                            fontSize: '1.125rem',
                            fontFamily: '"Outfit", sans-serif',
                            boxSizing: 'border-box'
                        }}
                        onKeyDown={(e) => e.key === 'Enter' && generateMap(prompt)}
                    />
                    <div style={{ display: 'flex', gap: '16px' }}>
                        <button
                            onClick={onClose}
                            style={{
                                flex: 1,
                                padding: '16px',
                                color: '#6b7280',
                                fontWeight: 600,
                                border: 'none',
                                background: 'none',
                                cursor: 'pointer',
                                borderRadius: '16px',
                                transition: 'all 0.2s'
                            }}
                            onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#f9fafb'}
                            onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                        >
                            Cancel
                        </button>
                        <button
                            onClick={() => generateMap(prompt)}
                            disabled={!prompt.trim() || loading}
                            style={{
                                flex: 1,
                                padding: '16px',
                                backgroundColor: (!prompt.trim() || loading) ? '#e5e7eb' : '#2563eb',
                                color: 'white',
                                fontWeight: 600,
                                borderRadius: '16px',
                                border: 'none',
                                cursor: (!prompt.trim() || loading) ? 'default' : 'pointer',
                                boxShadow: (!prompt.trim() || loading) ? 'none' : '0 10px 15px -3px rgba(37, 99, 235, 0.2)',
                                transition: 'all 0.2s'
                            }}
                            onMouseOver={(e) => {
                                if (prompt.trim() && !loading) e.currentTarget.style.backgroundColor = '#1d4ed8';
                            }}
                            onMouseOut={(e) => {
                                if (prompt.trim() && !loading) e.currentTarget.style.backgroundColor = '#2563eb';
                            }}
                        >
                            Generate Map
                        </button>
                    </div>
                </motion.div>
            </div>
        );
    }

    if (loading) {
        return (
            <div style={{
                position: 'fixed',
                inset: 0,
                backgroundColor: '#0a0a0f',
                zIndex: 2000,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexDirection: 'column',
                color: 'white'
            }}>
                <motion.div
                    animate={{
                        scale: [1, 1.2, 1],
                        rotate: [0, 180, 360],
                    }}
                    transition={{ repeat: Infinity, duration: 3 }}
                    style={{ fontSize: '3.75rem', marginBottom: '32px' }}
                >
                    🧠
                </motion.div>
                <h3 style={{ fontSize: '1.5rem', fontWeight: 300, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '8px' }}>Analyzing Sources</h3>
                <div style={{ width: '192px', height: '4px', backgroundColor: 'rgba(255, 255, 255, 0.1)', borderRadius: '9999px', overflow: 'hidden' }}>
                    <motion.div
                        initial={{ x: '-100%' }}
                        animate={{ x: '100%' }}
                        transition={{ repeat: Infinity, duration: 1.5, ease: "easeInOut" }}
                        style={{ width: '100%', height: '100%', backgroundColor: '#3b82f6' }}
                    />
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div style={{
                position: 'fixed',
                inset: 0,
                backgroundColor: 'white',
                zIndex: 2000,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexDirection: 'column',
                padding: '40px',
                fontFamily: '"Outfit", sans-serif'
            }}>
                <div style={{ fontSize: '6rem', marginBottom: '24px', filter: 'drop-shadow(0 10px 8px rgba(0, 0, 0, 0.1))' }}>🧩</div>
                <h2 style={{
                    fontSize: '1.875rem',
                    fontWeight: 700,
                    color: '#111827',
                    marginBottom: '16px',
                    background: 'linear-gradient(to right, #dc2626, #ea580c)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent'
                }}>
                    A bit too complex!
                </h2>
                <div style={{ backgroundColor: 'rgba(254, 242, 242, 0.5)', padding: '24px', borderRadius: '24px', border: '1px solid rgba(254, 226, 226, 0.5)', marginBottom: '32px', maxWidth: '448px', textAlign: 'center' }}>
                    <p style={{ color: '#ef4444', fontWeight: 500, fontSize: '0.875rem', lineHeight: 1.625 }}>{error}</p>
                </div>
                <button
                    onClick={onClose}
                    style={{
                        padding: '16px 40px',
                        background: 'linear-gradient(to right, #111827, #1f2937)',
                        color: 'white',
                        borderRadius: '16px',
                        border: 'none',
                        cursor: 'pointer',
                        fontWeight: 700,
                        letterSpacing: '0.025em',
                        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
                        transition: 'all 0.2s'
                    }}
                    onMouseOver={(e) => e.currentTarget.style.transform = 'scale(1.05)'}
                    onMouseOut={(e) => e.currentTarget.style.transform = 'scale(1)'}
                >
                    Return to Factory
                </button>
            </div>
        );
    }

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            style={{
                position: 'fixed',
                inset: 0,
                backgroundColor: '#f8fafc',
                zIndex: 2000,
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
                userSelect: 'none',
                fontFamily: '"Outfit", sans-serif'
            }}
        >
            <style>
                {`
                    .dot-grid {
                        background-image: radial-gradient(#e2e8f0 1px, transparent 1px);
                        background-size: 32px 32px;
                    }
                    @keyframes flow {
                        from { stroke-dashoffset: 20; }
                        to { stroke-dashoffset: 0; }
                    }
                `}
            </style>
            {/* Minimal Header */}
            <div style={{
                height: '80px',
                padding: '0 32px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                borderBottom: '1px solid #f9fafb',
                backgroundColor: 'rgba(255, 255, 255, 0.8)',
                backdropFilter: 'blur(12px)'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <div style={{ width: '40px', height: '40px', backgroundColor: '#2563eb', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.25rem' }}>🗺️</div>
                    <div>
                        <h1 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#111827', margin: 0, lineHeight: 1 }}>{prompt}</h1>
                        <span style={{ fontSize: '0.75rem', color: '#3b82f6', fontWeight: 500, letterSpacing: '0.05em', textTransform: 'uppercase' }}>Wispen Mindmap Agent</span>
                    </div>
                </div>
                <button
                    onClick={onClose}
                    style={{
                        width: '48px',
                        height: '48px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        borderRadius: '16px',
                        backgroundColor: 'transparent',
                        border: 'none',
                        cursor: 'pointer',
                        color: '#9ca3af',
                        transition: 'all 0.2s'
                    }}
                    onMouseOver={(e) => { e.currentTarget.style.backgroundColor = '#f3f4f6'; e.currentTarget.style.color = '#111827'; }}
                    onMouseOut={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; e.currentTarget.style.color = '#9ca3af'; }}
                >
                    <svg style={{ width: '24px', height: '24px' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>

            {/* Main Canvas Area */}
            <div
                className="dot-grid"
                style={{
                    flex: 1,
                    overflow: 'auto',
                    padding: '120px',
                    cursor: 'grab',
                    backgroundColor: '#f8fafc',
                    position: 'relative'
                }}
            >
                <div style={{
                    position: 'relative',
                    minWidth: '3000px',
                    minHeight: '2000px',
                    transform: `scale(${zoom})`,
                    transformOrigin: 'top left',
                    transition: 'transform 0.2s ease-out'
                }}>
                    <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none' }}>
                        {data && Object.values(data.nodes).map(node => (
                            node.children.map(childId => {
                                const child = data.nodes[childId];
                                // Don't render if parent is collapsed OR coords not set
                                if (node.collapsed || !child || node.x === undefined || node.y === undefined || child.x === undefined || child.y === undefined) return null;
                                const color = getNodeColor(node.level || 0);
                                const startX = node.x + NODE_WIDTH;
                                const startY = node.y + NODE_HEIGHT / 2;
                                const endX = child.x;
                                const endY = child.y + NODE_HEIGHT / 2;

                                return (
                                    <g key={`${node.id}-${childId}`}>
                                        <motion.path
                                            d={`M ${startX} ${startY} C ${startX + 120} ${startY}, ${endX - 120} ${endY}, ${endX} ${endY}`}
                                            stroke={color.main}
                                            strokeWidth="2.5"
                                            strokeOpacity="0.3"
                                            fill="none"
                                            initial={{ pathLength: 0, opacity: 0 }}
                                            animate={{ pathLength: 1, opacity: 1 }}
                                            transition={{ duration: 1.2, ease: "easeOut" }}
                                        />
                                        <motion.path
                                            d={`M ${startX} ${startY} C ${startX + 120} ${startY}, ${endX - 120} ${endY}, ${endX} ${endY}`}
                                            stroke={color.main}
                                            strokeWidth="2.5"
                                            strokeDasharray="8 12"
                                            fill="none"
                                            strokeOpacity="0.6"
                                            style={{ animation: 'flow 2s linear infinite' }}
                                        />
                                    </g>
                                );
                            })
                        ))}
                    </svg>

                    {data && Object.values(data.nodes).map(node => (
                        <motion.div
                            key={node.id}
                            initial={{ scale: 0.8, opacity: 0, y: 20 }}
                            animate={{ scale: 1, opacity: 1, y: 0 }}
                            whileHover={{ scale: 1.02, y: -2 }}
                            style={{
                                position: 'absolute',
                                left: node.x || 0,
                                top: node.y || 0,
                                width: NODE_WIDTH,
                                height: NODE_HEIGHT,
                                display: (node.x !== undefined) ? 'flex' : 'none', // Hide if not laid out
                                backgroundColor: 'white',
                                borderRadius: '20px',
                                border: `1.5px solid ${getNodeColor(node.level || 0).border}`,
                                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 10px 15px -3px rgba(0, 0, 0, 0.03)',
                                padding: '20px',
                                flexDirection: 'column',
                                justifyContent: 'center',
                                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                                cursor: 'pointer',
                                overflow: 'visible'
                            }}
                            onMouseEnter={(e) => {
                                const color = getNodeColor(node.level || 0);
                                e.currentTarget.style.borderColor = color.main;
                                e.currentTarget.style.boxShadow = `0 20px 25px -5px ${color.main}15, 0 8px 10px -6px ${color.main}10`;
                                setHoveredNodeId(node.id);
                            }}
                            onMouseMove={(e) => {
                                setMousePos({ x: e.clientX, y: e.clientY });
                            }}
                            onMouseLeave={(e) => {
                                const color = getNodeColor(node.level || 0);
                                e.currentTarget.style.borderColor = color.border;
                                e.currentTarget.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 10px 15px -3px rgba(0, 0, 0, 0.03)';
                                setHoveredNodeId(null);
                            }}
                        >
                            <div style={{
                                position: 'absolute',
                                top: 0,
                                left: 0,
                                width: '6px',
                                height: '100%',
                                background: getNodeColor(node.level || 0).gradient,
                                borderRadius: '20px 0 0 20px'
                            }} />
                            <div style={{
                                fontWeight: 800,
                                color: getNodeColor(node.level || 0).text,
                                fontSize: '0.925rem',
                                marginBottom: '6px',
                                lineHeight: 1.3,
                                overflow: 'hidden',
                                display: '-webkit-box',
                                WebkitLineClamp: 3,
                                WebkitBoxOrient: 'vertical',
                                letterSpacing: '-0.01em'
                            }}>
                                <MarkdownRenderer content={node.label} />
                            </div>
                            <div style={{
                                fontSize: '11px',
                                color: '#64748b',
                                margin: 0,
                                overflow: 'hidden',
                                display: '-webkit-box',
                                WebkitLineClamp: 2,
                                WebkitBoxOrient: 'vertical',
                                lineHeight: 1.4
                            }}>
                                <MarkdownRenderer content={node.description} />
                            </div>

                            {/* Show Button if hasMore OR has children (to toggle collapse) */}
                            {((node.hasMore !== false) || (node.children && node.children.length > 0)) && (
                                <button
                                    onClick={() => handleExpand(node.id)}
                                    style={{
                                        position: 'absolute',
                                        right: '-12px',
                                        top: '50%',
                                        transform: 'translateY(-50%)',
                                        width: '28px',
                                        height: '28px',
                                        backgroundColor: 'white',
                                        borderRadius: '9999px',
                                        border: '1px solid #e5e7eb',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        cursor: 'pointer',
                                        transition: 'all 0.2s',
                                        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                                        color: '#6b7280'
                                    }}
                                    onMouseOver={(e) => {
                                        const color = getNodeColor(node.level || 0);
                                        e.currentTarget.style.backgroundColor = color.main;
                                        e.currentTarget.style.borderColor = color.main;
                                        e.currentTarget.style.color = 'white';
                                        e.currentTarget.style.transform = 'translateY(-50%) scale(1.15)';
                                        e.currentTarget.style.boxShadow = `0 10px 15px -3px ${color.main}40`;
                                    }}
                                    onMouseOut={(e) => {
                                        e.currentTarget.style.backgroundColor = 'white';
                                        e.currentTarget.style.borderColor = '#e2e8f0';
                                        e.currentTarget.style.color = '#64748b';
                                        e.currentTarget.style.transform = 'translateY(-50%) scale(1)';
                                        e.currentTarget.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.1)';
                                    }}
                                >
                                    {expanding === node.id ? (
                                        <motion.div
                                            animate={{ rotate: 360 }}
                                            transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                                            style={{ width: '12px', height: '12px', border: '2px solid currentColor', borderTopColor: 'transparent', borderRadius: '50%' }}
                                        />
                                    ) : (
                                        <svg style={{ width: '14px', height: '14px' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            {/* Show MINUS if expanded (children > 0 and NOT collapsed), else PLUS */}
                                            {(node.children.length > 0 && !node.collapsed) ?
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M20 12H4" /> :
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M12 4v16m8-8H4" />
                                            }
                                        </svg>
                                    )}
                                </button>
                            )}
                        </motion.div>
                    ))}
                </div>
            </div>

            {/* Floating Zoom/UI Controls */}
            <div style={{
                position: 'absolute',
                bottom: '48px',
                left: '50%',
                transform: 'translateX(-50%)',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                backgroundColor: 'rgba(255, 255, 255, 0.7)',
                backdropFilter: 'blur(20px)',
                padding: '12px 20px',
                borderRadius: '24px',
                boxShadow: '0 20px 40px -12px rgba(0, 0, 0, 0.15)',
                border: '1px solid rgba(255, 255, 255, 0.5)'
            }}>
                <span style={{ fontSize: '0.875rem', fontWeight: 700, color: '#9ca3af', padding: '0 8px', textTransform: 'uppercase', letterSpacing: '-0.025em' }}>Wispen V1.0</span>
                <div style={{ width: '1px', height: '24px', backgroundColor: '#f3f4f6', margin: '0 8px' }} />
                <button onClick={handleZoomIn} style={{ padding: '8px', background: 'none', border: 'none', cursor: 'pointer', borderRadius: '12px', color: '#4b5563', transition: 'all 0.2s' }} onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#f3f4f6'} onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'transparent'}>
                    <svg style={{ width: '20px', height: '20px' }} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M12 4v16m8-8H4" strokeWidth="2" strokeLinecap="round" /></svg>
                </button>
                <span style={{ fontSize: '0.875rem', fontWeight: 700, width: '48px', textAlign: 'center', color: '#1f2937' }}>{Math.round(zoom * 100)}%</span>
                <button onClick={handleZoomOut} style={{ padding: '8px', background: 'none', border: 'none', cursor: 'pointer', borderRadius: '12px', color: '#4b5563', transition: 'all 0.2s' }} onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#f3f4f6'} onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'transparent'}>
                    <svg style={{ width: '20px', height: '20px' }} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M20 12H4" strokeWidth="2" strokeLinecap="round" /></svg>
                </button>
            </div>
            {/* Hover Tooltip */}
            <AnimatePresence>
                {hoveredNodeId && data?.nodes[hoveredNodeId] && (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95, y: 10 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: 10 }}
                        style={{
                            position: 'fixed',
                            left: mousePos.x + 20,
                            top: mousePos.y + 20,
                            backgroundColor: 'white',
                            borderRadius: '12px',
                            padding: '16px',
                            maxWidth: '300px',
                            boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.05)',
                            border: `2px solid ${getNodeColor(data.nodes[hoveredNodeId].level || 0).main}`,
                            zIndex: 3000,
                            pointerEvents: 'none'
                        }}
                    >
                        <div style={{ margin: '0 0 8px 0', fontSize: '0.9rem', fontWeight: 800, color: getNodeColor(data.nodes[hoveredNodeId].level || 0).text }}>
                            <MarkdownRenderer content={data.nodes[hoveredNodeId].label} />
                        </div>
                        <div style={{ margin: 0, fontSize: '0.85rem', color: '#4b5563', lineHeight: 1.5 }}>
                            <MarkdownRenderer content={data.nodes[hoveredNodeId].description} />
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div >
    );
};

export default MindMapViewer;
