import os
import json
import hashlib
from typing import List, Dict, Optional, Tuple
import re
import pickle
import time
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False

class DocumentChunker:
    """Intelligent document chunking for large files"""
    
    def __init__(self, chunk_size: int = 2000, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_by_tokens(self, text: str) -> List[Dict]:
        """Simple token-based chunking with overlap"""
        # Rough token estimation (4 chars ≈ 1 token)
        words = text.split()
        chunks = []
        
        current_chunk = []
        current_size = 0
        
        for word in words:
            word_size = len(word) // 4 + 1  # Rough token count
            
            if current_size + word_size > self.chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    'text': chunk_text,
                    'start_idx': len(chunks),
                    'token_count': current_size
                })
                # Keep overlap
                overlap_words = int(len(current_chunk) * (self.overlap / self.chunk_size))
                current_chunk = current_chunk[-overlap_words:] if overlap_words > 0 else []
                current_size = sum(len(w) // 4 + 1 for w in current_chunk)
            
            current_chunk.append(word)
            current_size += word_size
        
        if current_chunk:
            chunks.append({
                'text': ' '.join(current_chunk),
                'start_idx': len(chunks),
                'token_count': current_size
            })
        
        return chunks
    
    def chunk_python_code(self, code: str) -> List[Dict]:
        """Semantic chunking for Python code - preserves structure"""
        chunks = []
        
        # Split by top-level definitions (classes, functions)
        pattern = r'(?:^|\n)(class |def |import |from )'
        parts = re.split(pattern, code)
        
        current_chunk = []
        current_size = 0
        
        for i in range(0, len(parts), 2):
            if i + 1 < len(parts):
                segment = parts[i + 1] + parts[i + 2] if i + 2 < len(parts) else parts[i + 1]
            else:
                segment = parts[i]
            
            segment_size = len(segment) // 4  # Token estimate
            
            if current_size + segment_size > self.chunk_size and current_chunk:
                chunk_text = ''.join(current_chunk)
                chunks.append({
                    'text': chunk_text,
                    'type': 'code',
                    'start_idx': len(chunks),
                    'token_count': current_size
                })
                current_chunk = []
                current_size = 0
            
            current_chunk.append(segment)
            current_size += segment_size
        
        if current_chunk:
            chunks.append({
                'text': ''.join(current_chunk),
                'type': 'code',
                'start_idx': len(chunks),
                'token_count': current_size
            })
        
        return chunks


class EmbeddingCache:
    """Simple file-based caching for embeddings"""
    
    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.memory_cache = {}
        self.ttl_seconds = 86400  # 24 hours
    
    def get_cache_path(self, key: str) -> Path:
        """Get cache file path for a key"""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.pkl"
    
    def get(self, key: str) -> Optional[Dict]:
        """Retrieve from cache"""
        if key in self.memory_cache:
            cached, timestamp = self.memory_cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.ttl_seconds):
                return cached
            else:
                del self.memory_cache[key]
        
        cache_path = self.get_cache_path(key)
        if cache_path.exists():
            try:
                with open(cache_path, 'rb') as f:
                    cached, timestamp = pickle.load(f)
                    if datetime.now() - timestamp < timedelta(seconds=self.ttl_seconds):
                        self.memory_cache[key] = (cached, timestamp)
                        return cached
                    else:
                        cache_path.unlink()
            except:
                pass
        return None
    
    def set(self, key: str, value: Dict):
        """Store in cache"""
        timestamp = datetime.now()
        self.memory_cache[key] = (value, timestamp)
        
        try:
            cache_path = self.get_cache_path(key)
            with open(cache_path, 'wb') as f:
                pickle.dump((value, timestamp), f)
        except:
            pass
    
    def clear(self):
        """Clear all caches"""
        self.memory_cache.clear()
        for cache_file in self.cache_dir.glob("*.pkl"):
            cache_file.unlink()


class HybridEmbedding:
    """Hybrid embedding system combining keyword and semantic search"""
    
    def __init__(self, use_semantic: bool = True):
        self.use_semantic = use_semantic and SENTENCE_TRANSFORMERS_AVAILABLE
        self.model = None
        self.cache = EmbeddingCache()
        
        if self.use_semantic:
            try:
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
            except Exception as e:
                print(f"Warning: Could not load sentence transformer: {e}")
                self.use_semantic = False
    
    def extract_keywords(self, text: str, top_n: int = 20) -> Dict[str, int]:
        """Extract important keywords with frequency"""
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 
            'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 
            'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 
            'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it',
            'we', 'they', 'what', 'which', 'who', 'when', 'where', 'why', 'how'
        }
        
        words = re.findall(r'\b\w+\b', text.lower())
        freq = {}
        for word in words:
            if len(word) > 3 and word not in stop_words:
                freq[word] = freq.get(word, 0) + 1
        
        top_keywords = dict(sorted(freq.items(), key=lambda x: x[1], reverse=True)[:top_n])
        return top_keywords
    
    def get_semantic_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get semantic embedding using sentence transformers"""
        if not self.use_semantic or not self.model:
            return None
        
        cache_key = f"embedding_{hashlib.md5(text.encode()).hexdigest()}"
        cached = self.cache.get(cache_key)
        if cached:
            return np.array(cached['embedding'])
        
        try:
            embedding = self.model.encode(text[:5000], convert_to_numpy=True)
            self.cache.set(cache_key, {'embedding': embedding.tolist()})
            return embedding
        except Exception as e:
            print(f"Embedding error: {e}")
            return None
    
    def calculate_similarity(self, keywords1: Dict[str, int], keywords2: Dict[str, int]) -> float:
        """Calculate keyword-based similarity"""
        if not keywords1 or not keywords2:
            return 0.0
        
        common = set(keywords1.keys()) & set(keywords2.keys())
        if not common:
            return 0.0
        
        score = 0.0
        total_weight1 = sum(keywords1.values())
        total_weight2 = sum(keywords2.values())
        
        for keyword in common:
            weight1 = keywords1[keyword] / total_weight1
            weight2 = keywords2[keyword] / total_weight2
            score += min(weight1, weight2)
        
        return score
    
    def calculate_semantic_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between embeddings"""
        if embedding1 is None or embedding2 is None:
            return 0.0
        
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(np.dot(embedding1, embedding2) / (norm1 * norm2))
    
    def hybrid_similarity(self, text1: str, text2: str, keyword_weight: float = 0.4) -> float:
        """Combine keyword and semantic similarity"""
        kw1 = self.extract_keywords(text1)
        kw2 = self.extract_keywords(text2)
        keyword_sim = self.calculate_similarity(kw1, kw2)
        
        if self.use_semantic:
            emb1 = self.get_semantic_embedding(text1)
            emb2 = self.get_semantic_embedding(text2)
            semantic_sim = self.calculate_semantic_similarity(emb1, emb2)
            return keyword_weight * keyword_sim + (1 - keyword_weight) * semantic_sim
        
        return keyword_sim


class DocumentIndex:
    """Index for efficient chunk retrieval with hybrid search"""
    
    def __init__(self, use_semantic: bool = True):
        self.chunks = []
        self.chunk_keywords = []
        self.chunk_embeddings = []
        self.metadata = {}
        self.embedding_model = HybridEmbedding(use_semantic=use_semantic)
    
    def add_document(self, filepath: str, chunks: List[Dict]):
        """Add document chunks to index"""
        doc_id = hashlib.md5(filepath.encode()).hexdigest()[:8]
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_{i}"
            keywords = self.embedding_model.extract_keywords(chunk['text'])
            embedding = self.embedding_model.get_semantic_embedding(chunk['text'])
            
            self.chunks.append({
                'id': chunk_id,
                'doc_id': doc_id,
                'filepath': filepath,
                'chunk_idx': i,
                'text': chunk['text'],
                'metadata': chunk
            })
            self.chunk_keywords.append(keywords)
            self.chunk_embeddings.append(embedding)
        
        self.metadata[doc_id] = {
            'filepath': filepath,
            'num_chunks': len(chunks),
            'total_tokens': sum(c.get('token_count', 0) for c in chunks)
        }
    
    def search(self, query: str, top_k: int = 5, use_hybrid: bool = True) -> List[Dict]:
        """Search for most relevant chunks using hybrid or keyword-only search"""
        scores = []
        
        if use_hybrid and self.embedding_model.use_semantic:
            query_embedding = self.embedding_model.get_semantic_embedding(query)
            query_keywords = self.embedding_model.extract_keywords(query)
            
            for i in range(len(self.chunks)):
                keyword_score = self.embedding_model.calculate_similarity(
                    query_keywords, self.chunk_keywords[i]
                )
                semantic_score = self.embedding_model.calculate_semantic_similarity(
                    query_embedding, self.chunk_embeddings[i]
                )
                hybrid_score = 0.4 * keyword_score + 0.6 * semantic_score
                scores.append((hybrid_score, i))
        else:
            query_keywords = self.embedding_model.extract_keywords(query)
            for i, chunk_keywords in enumerate(self.chunk_keywords):
                score = self.embedding_model.calculate_similarity(query_keywords, chunk_keywords)
                scores.append((score, i))
        
        scores.sort(reverse=True, key=lambda x: x[0])
        top_chunks = []
        
        for score, idx in scores[:top_k]:
            if score > 0:
                chunk = self.chunks[idx].copy()
                chunk['relevance_score'] = float(score)
                top_chunks.append(chunk)
        
        return top_chunks
    
    def get_document_summary(self, doc_id: str) -> Dict:
        """Get metadata summary for a document"""
        return self.metadata.get(doc_id, {})


class WebSearchIntegration:
    """Integration with Tavily for web search"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY", "")
        self.client = None
        self.cache = EmbeddingCache()
        
        if self.api_key and TAVILY_AVAILABLE:
            try:
                self.client = TavilyClient(api_key=self.api_key)
            except Exception as e:
                print(f"Warning: Could not initialize Tavily: {e}")
    
    def search(self, query: str, include_raw_content: bool = True) -> Optional[Dict]:
        """Search the web using Tavily"""
        if not self.client:
            return None
        
        cache_key = f"web_search_{hashlib.md5(query.encode()).hexdigest()}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        try:
            response = self.client.search(
                query=query,
                include_raw_content=include_raw_content,
                include_answer=True,
                search_depth="advanced"
            )
            
            self.cache.set(cache_key, response)
            return response
        except Exception as e:
            print(f"Web search error: {e}")
            return None
    
    def extract_results(self, search_response: Dict) -> List[Dict]:
        """Extract structured results from Tavily response"""
        if not search_response:
            return []
        
        results = []
        for item in search_response.get('results', []):
            results.append({
                'source': item.get('url', ''),
                'title': item.get('title', ''),
                'content': item.get('raw_content') or item.get('content', ''),
                'score': item.get('score', 0),
                'type': 'web'
            })
        
        return results


class RAGDocumentProcessor:
    """Main RAG processor for handling large documents with multi-source querying"""
    
    def __init__(self, use_semantic: bool = True, tavily_api_key: Optional[str] = None):
        self.chunker = DocumentChunker(chunk_size=2000, overlap=200)
        self.index = DocumentIndex(use_semantic=use_semantic)
        self.web_search = WebSearchIntegration(api_key=tavily_api_key)
        self.processed_docs = {}
        self.cache = EmbeddingCache()
    
    def process_file(self, filepath: str, file_type: str = 'text') -> str:
        """Process a file and add to index"""
        if not os.path.exists(filepath):
            return f"Error: File not found - {filepath}"
        
        # Read file content
        try:
            if file_type == 'code' or filepath.endswith('.py'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                chunks = self.chunker.chunk_python_code(content)
            else:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                chunks = self.chunker.chunk_by_tokens(content)
            
            # Add to index
            self.index.add_document(filepath, chunks)
            
            # Store metadata
            doc_id = hashlib.md5(filepath.encode()).hexdigest()[:8]
            self.processed_docs[doc_id] = {
                'filepath': filepath,
                'num_chunks': len(chunks),
                'file_type': file_type
            }
            
            return f"✓ Processed: {filepath} → {len(chunks)} chunks indexed"
        
        except Exception as e:
            return f"Error processing file: {str(e)}"
    
    def query(self, user_query: str, top_k: int = 3, include_web: bool = False, use_hybrid: bool = True) -> Dict:
        """Query indexed documents and optionally search the web
        
        Args:
            user_query: The search query
            top_k: Number of results to return from local documents
            include_web: Whether to include web search results
            use_hybrid: Use hybrid search (keyword + semantic)
        """
        results = {
            'found': False,
            'local_context': '',
            'web_context': '',
            'local_sources': [],
            'web_sources': [],
            'total_results': 0,
            'sources': []
        }
        
        relevant_chunks = self.index.search(user_query, top_k=top_k, use_hybrid=use_hybrid)
        
        if relevant_chunks:
            context_parts = []
            for chunk in relevant_chunks:
                context_parts.append(f"[Local Source: {chunk['filepath']} - Chunk {chunk['chunk_idx']}]")
                context_parts.append(f"Relevance: {chunk['relevance_score']:.2f}")
                context_parts.append(f"{chunk['text']}\n")
            
            results['local_context'] = "\n".join(context_parts)
            results['local_sources'] = [c['filepath'] for c in relevant_chunks]
            results['found'] = True
        
        if include_web and self.web_search.client:
            web_results = self.web_search.search(user_query)
            if web_results:
                web_items = self.web_search.extract_results(web_results)
                web_context_parts = []
                
                for item in web_items[:top_k]:
                    web_context_parts.append(f"[Web Source: {item['title']}]")
                    web_context_parts.append(f"URL: {item['source']}")
                    web_context_parts.append(f"Score: {item['score']:.2f}")
                    web_context_parts.append(f"{item['content'][:2000]}\n")
                
                results['web_context'] = "\n".join(web_context_parts)
                results['web_sources'] = [item['source'] for item in web_items[:top_k]]
                results['found'] = True
        
        if results['found']:
            results['sources'] = results['local_sources'] + results['web_sources']
            results['total_results'] = len(relevant_chunks) + len(results['web_sources'])
        
        return results
    
    def multi_document_query(self, user_query: str, doc_ids: Optional[List[str]] = None, 
                            top_k: int = 3) -> Dict:
        """Query across multiple specific documents
        
        Args:
            user_query: The search query
            doc_ids: List of document IDs to search across (None = all documents)
            top_k: Number of results per document
        """
        results = self.query(user_query, top_k=top_k)
        
        if doc_ids:
            filtered_sources = []
            for chunk_source in results.get('local_sources', []):
                if any(doc_id in chunk_source for doc_id in doc_ids):
                    filtered_sources.append(chunk_source)
            
            results['local_sources'] = filtered_sources
            results['documents_searched'] = doc_ids
        else:
            results['documents_searched'] = list(self.processed_docs.keys())
        
        return results
    
    def generate_hierarchical_summary(self, filepath: str) -> Dict:
        """Generate multi-level summary of document"""
        doc_id = hashlib.md5(filepath.encode()).hexdigest()[:8]
        
        if doc_id not in self.processed_docs:
            return {'error': 'Document not processed'}
        
        # Get all chunks for this document
        doc_chunks = [c for c in self.index.chunks if c['doc_id'] == doc_id]
        
        # Create summary structure
        summary = {
            'filepath': filepath,
            'total_chunks': len(doc_chunks),
            'overview': f"Document contains {len(doc_chunks)} semantic sections",
            'sections': []
        }
        
        # Group chunks and create section summaries
        for chunk in doc_chunks[:10]:  # Limit to first 10 for brevity
            # Extract first few lines as summary
            lines = chunk['text'].split('\n')[:3]
            section_preview = '\n'.join(lines)
            
            summary['sections'].append({
                'chunk_idx': chunk['chunk_idx'],
                'preview': section_preview + '...',
                'length': len(chunk['text'])
            })
        
        return summary


# Example usage and integration
class EnhancedFileProcessor:
    """Enhanced version of FileProcessor with RAG capabilities and web search"""
    
    def __init__(self, tavily_api_key: Optional[str] = None, use_semantic: bool = True):
        self.rag_processor = RAGDocumentProcessor(use_semantic=use_semantic, tavily_api_key=tavily_api_key)
        self.simple_processor = None
    
    def process_file(self, filepath: str) -> Dict:
        """Process file with RAG indexing"""
        file_ext = os.path.splitext(filepath)[1].lower()
        
        if file_ext == '.py':
            file_type = 'code'
        elif file_ext in ['.txt', '.md']:
            file_type = 'text'
        else:
            file_type = 'binary'
        
        result = self.rag_processor.process_file(filepath, file_type)
        summary = self.rag_processor.generate_hierarchical_summary(filepath)
        
        return {
            'status': 'success',
            'message': result,
            'filepath': filepath,
            'file_type': file_type,
            'summary': summary,
            'indexed': True
        }
    
    def query_documents(self, user_query: str, include_web: bool = False, use_hybrid: bool = True) -> Dict:
        """Query indexed documents with optional web search
        
        Args:
            user_query: The search query
            include_web: Include web search results
            use_hybrid: Use hybrid search (keyword + semantic)
        """
        result = self.rag_processor.query(user_query, top_k=5, include_web=include_web, use_hybrid=use_hybrid)
        
        return {
            'local_context': result.get('local_context', ''),
            'web_context': result.get('web_context', ''),
            'found': result.get('found', False),
            'local_sources': result.get('local_sources', []),
            'web_sources': result.get('web_sources', []),
            'total_results': result.get('total_results', 0)
        }
    
    def query_multi_documents(self, user_query: str, doc_ids: Optional[List[str]] = None) -> Dict:
        """Query across multiple documents
        
        Args:
            user_query: The search query
            doc_ids: Specific document IDs to query (None = all)
        """
        result = self.rag_processor.multi_document_query(user_query, doc_ids=doc_ids, top_k=5)
        
        return {
            'context': result.get('local_context', ''),
            'found': result.get('found', False),
            'sources': result.get('local_sources', []),
            'documents_searched': result.get('documents_searched', []),
            'total_results': result.get('total_results', 0)
        }
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            'cache_dir': str(self.rag_processor.cache.cache_dir),
            'memory_cache_size': len(self.rag_processor.cache.memory_cache),
            'ttl_seconds': self.rag_processor.cache.ttl_seconds
        }
    
    def clear_cache(self):
        """Clear all caches"""
        self.rag_processor.cache.clear()
        if self.rag_processor.index.embedding_model.cache:
            self.rag_processor.index.embedding_model.cache.clear()


# Demo
if __name__ == "__main__":
    print("=== Enhanced RAG Document Processor Demo ===\n")
    
    tavily_key = os.getenv("TAVILY_API_KEY", "")
    
    processor = EnhancedFileProcessor(tavily_api_key=tavily_key, use_semantic=True)
    
    print("1. Processing documents...")
    result = processor.process_file("example_code.py")
    print(f"   {result['message']}\n")
    
    print("2. Querying with Keyword-based search...")
    query = "What does the FileProcessor class do?"
    result_keyword = processor.query_documents(query, include_web=False, use_hybrid=False)
    print(f"   Query: {query}")
    print(f"   Found: {result_keyword['found']}")
    print(f"   Results: {result_keyword['total_results']}\n")
    
    print("3. Querying with Hybrid search (keyword + semantic)...")
    result_hybrid = processor.query_documents(query, include_web=False, use_hybrid=True)
    print(f"   Found: {result_hybrid['found']}")
    print(f"   Results: {result_hybrid['total_results']}\n")
    
    if tavily_key:
        print("4. Querying with web search enabled...")
        result_web = processor.query_documents(query, include_web=True, use_hybrid=True)
        print(f"   Found: {result_web['found']}")
        print(f"   Local sources: {len(result_web['local_sources'])}")
        print(f"   Web sources: {len(result_web['web_sources'])}\n")
    
    print("5. Cache statistics:")
    stats = processor.get_cache_stats()
    print(f"   Cache dir: {stats['cache_dir']}")
    print(f"   Memory cache size: {stats['memory_cache_size']}\n")
    
    print("6. This enhanced context can now be sent to Gemini for better answers!")