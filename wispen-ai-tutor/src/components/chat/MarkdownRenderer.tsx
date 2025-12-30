import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css'; // Import Katex CSS for math styling

interface MarkdownRendererProps {
    content: string;
    isUser?: boolean;
}

const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, isUser }) => {
    return (
        <div className={`markdown-content ${isUser ? 'user-markdown' : 'ai-markdown'}`}>
            <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkMath]}
                rehypePlugins={[rehypeKatex]}
                components={{
                    h1: ({ node, ...props }) => <h1 style={{ fontSize: '1.5em', fontWeight: 'bold', margin: '0.5em 0' }} {...props} />,
                    h2: ({ node, ...props }) => <h2 style={{ fontSize: '1.3em', fontWeight: 'bold', margin: '0.4em 0' }} {...props} />,
                    h3: ({ node, ...props }) => <h3 style={{ fontSize: '1.1em', fontWeight: 'bold', margin: '0.3em 0' }} {...props} />,
                    p: ({ node, ...props }) => <p style={{ margin: '0.5em 0', lineHeight: '1.6' }} {...props} />,
                    ul: ({ node, ...props }) => <ul style={{ paddingLeft: '1.5em', margin: '0.5em 0' }} {...props} />,
                    ol: ({ node, ...props }) => <ol style={{ paddingLeft: '1.5em', margin: '0.5em 0' }} {...props} />,
                    li: ({ node, ...props }) => <li style={{ marginBottom: '0.3em' }} {...props} />,
                    code: ({ node, ...props }) => (
                        <code style={{
                            background: isUser ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.5)',
                            padding: '2px 5px',
                            borderRadius: '4px',
                            fontFamily: 'monospace',
                            fontSize: '0.9em'
                        }} {...props} />
                    ),
                    pre: ({ node, ...props }) => (
                        <pre style={{
                            background: 'rgba(0,0,0,0.8)',
                            color: 'white',
                            padding: '10px',
                            borderRadius: '8px',
                            overflowX: 'auto',
                            margin: '10px 0'
                        }} {...props} />
                    ),
                    blockquote: ({ node, ...props }) => (
                        <blockquote style={{
                            borderLeft: '4px solid #ccc',
                            paddingLeft: '10px',
                            fontStyle: 'italic',
                            margin: '10px 0',
                            color: '#666'
                        }} {...props} />
                    ),
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
};

export default MarkdownRenderer;
