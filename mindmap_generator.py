"""
AI-Powered Mind Map Generator with Enhanced Error Handling
==========================================================

Enhanced version with:
1. Large content support (chunking for big files)
2. Robust JSON parsing and retry logic
3. Beautiful console output with progress indicators
4. Comprehensive error recovery
5. API key rotation support

Dependencies:
    pip install requests colorama python-dotenv

Usage:
    from mindmap_generator import MindMapGenerator
    
    generator = MindMapGenerator()
    mindmap = generator.generate(content="Your study material here")
"""

import os
import json
import requests
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import time
import uuid
import re

# from colorama import Fore, Style, init (Removed for Render compatibility)
from api_key_manager import APIKeyManager, call_gemini_with_retry

# Dummy classes to replace colorama
class Fore:
    CYAN = ""
    GREEN = ""
    YELLOW = ""
    RED = ""
    BLUE = ""
    RESET = ""

class Style:
    RESET_ALL = ""

# init(autoreset=True)

# Gemini API Configuration
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# Content chunking settings
MAX_CONTENT_SIZE = 200000  # ~200KB per chunk
MAX_ANALYSIS_SIZE = 150000  # ~150KB for analysis


@dataclass
class MindMapNode:
    """Represents a single node in the mind map"""
    id: str
    label: str
    description: str
    level: int
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    related_nodes: List[str] = field(default_factory=list)
    importance: float = 0.5
    tags: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'label': self.label,
            'description': self.description,
            'level': self.level,
            'parent_id': self.parent_id,
            'children': self.children,
            'related_nodes': self.related_nodes,
            'importance': self.importance,
            'tags': self.tags,
            'examples': self.examples
        }


@dataclass
class MindMap:
    """Represents a complete mind map"""
    title: str
    root_id: str
    nodes: Dict[str, MindMapNode]
    metadata: Dict[str, Any]
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'title': self.title,
            'root_id': self.root_id,
            'nodes': {node_id: node.to_dict() for node_id, node in self.nodes.items()},
            'metadata': self.metadata,
            'generated_at': self.generated_at
        }
    
    def to_markdown(self) -> str:
        """Convert to beautiful markdown format"""
        md = f"# 🗺️  Mind Map: {self.title}\n\n"
        md += f"*Generated: {self.generated_at}*\n"
        md += f"*Total Nodes: {len(self.nodes)} | Max Depth: {self.metadata.get('max_depth', 0)}*\n\n"
        md += "---\n\n"
        
        def render_node(node_id: str, indent: int = 0):
            node = self.nodes[node_id]
            prefix = "  " * indent
            
            # Node with emoji based on level
            emoji = "🎯" if indent == 0 else "📌" if indent == 1 else "🔹" if indent == 2 else "▫️"
            result = f"{prefix}{emoji} **{node.label}**"
            
            if node.description:
                result += f"\n{prefix}  *{node.description}*"
            
            result += "\n"
            
            # Examples
            if node.examples:
                result += f"{prefix}  💡 Examples:\n"
                for example in node.examples[:2]:  # Limit to 2
                    result += f"{prefix}    - {example}\n"
            
            # Tags
            if node.tags:
                result += f"{prefix}  🏷️  Tags: {', '.join(node.tags[:4])}\n"
            
            result += "\n"
            
            # Render children
            for child_id in node.children:
                result += render_node(child_id, indent + 1)
            
            return result
        
        md += render_node(self.root_id)
        
        # Add relationships section
        relationships = [(node.label, [self.nodes[rid].label for rid in node.related_nodes if rid in self.nodes]) 
                        for node in self.nodes.values() if node.related_nodes]
        
        if relationships:
            md += "---\n\n"
            md += "## 🔗 Key Relationships\n\n"
            for node_label, related_labels in relationships:
                if related_labels:
                    md += f"- **{node_label}** ↔️ {', '.join(related_labels)}\n"
        
        return md
    
    def to_mermaid(self) -> str:
        """Convert to Mermaid diagram format"""
        mermaid = "graph TD\n"
        
        # Add styled nodes
        for node_id, node in self.nodes.items():
            safe_id = node_id.replace('-', '_')
            label = node.label.replace('"', "'")[:50]  # Limit length
            
            # Style based on level
            if node.level == 0:
                mermaid += f'    {safe_id}["{label}"]:::root\n'
            elif node.level == 1:
                mermaid += f'    {safe_id}["{label}"]:::level1\n'
            else:
                mermaid += f'    {safe_id}["{label}"]\n'
        
        mermaid += "\n"
        
        # Add hierarchical connections
        for node_id, node in self.nodes.items():
            safe_id = node_id.replace('-', '_')
            for child_id in node.children:
                safe_child_id = child_id.replace('-', '_')
                mermaid += f'    {safe_id} --> {safe_child_id}\n'
        
        # Add related connections (dotted)
        for node_id, node in self.nodes.items():
            safe_id = node_id.replace('-', '_')
            for related_id in node.related_nodes:
                if related_id in self.nodes:
                    safe_related_id = related_id.replace('-', '_')
                    mermaid += f'    {safe_id} -.-> {safe_related_id}\n'
        
        # Add styling
        mermaid += "\n"
        mermaid += "    classDef root fill:#e1f5ff,stroke:#01579b,stroke-width:3px\n"
        mermaid += "    classDef level1 fill:#fff3e0,stroke:#e65100,stroke-width:2px\n"
        
        return mermaid


class MindMapGenerator:
    """
    Enhanced Mind Map Generator with robust error handling
    """
    
    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        api_key_manager: Optional[APIKeyManager] = None,
        model_name: str = "gemini-2.0-flash",
        verbose: bool = True
    ):
        """Initialize the Mind Map Generator"""
        self.model_name = model_name
        self.verbose = verbose
        
        if api_key_manager:
            self.api_key_manager = api_key_manager
        else:
            try:
                self.api_key_manager = APIKeyManager()
            except ValueError:
                if gemini_api_key:
                    self.api_key_manager = None
                    self.gemini_api_key = gemini_api_key
                else:
                    raise ValueError(
                        "Gemini API key required. Set GEMINI_API_KEY1 and GEMINI_API_KEY2 "
                        "in environment or pass gemini_api_key"
                    )
        
        key_count = len(self.api_key_manager.get_key_list()) if self.api_key_manager else 1
        self._log(
            f"✓ Mind Map Generator initialized with {model_name} ({key_count} API key(s))",
            Fore.GREEN
        )
    
    def _log(self, message: str, color=Fore.YELLOW):
        """Log message if verbose is enabled"""
        if self.verbose:
            print(f"{color}{message}{Style.RESET_ALL}")
    
    def _print_progress(self, current: int, total: int, prefix: str = "Progress"):
        """Print a beautiful progress indicator"""
        if not self.verbose:
            return
        
        bar_length = 40
        filled = int(bar_length * current / total)
        bar = "█" * filled + "░" * (bar_length - filled)
        percent = f"{100 * current / total:.1f}%"
        
        print(f"\r{Fore.CYAN}{prefix}: {Fore.GREEN}|{bar}| {percent}{Style.RESET_ALL}", end="", flush=True)
        
        if current == total:
            print()  # New line when complete
    
    def _clean_json_response(self, response: str) -> str:
        """Clean and extract JSON from API response"""
        response = response.strip()
        
        # Remove markdown code blocks
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]
        
        if response.endswith("```"):
            response = response[:-3]
        
        response = response.strip()
        
        # Find JSON boundaries
        if response.startswith('{'):
            depth = 0
            last_valid = -1
            for i, char in enumerate(response):
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        last_valid = i
                        break
            if last_valid > 0:
                response = response[:last_valid + 1]
        
        return response
    
    def _call_gemini(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 8192
    ) -> str:
        """Call Gemini API with automatic retry"""
        if self.api_key_manager:
            def api_call(api_key: str) -> str:
                response = requests.post(
                    f"{GEMINI_API_URL}?key={api_key}",
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": temperature,
                            "topK": 40,
                            "topP": 0.95,
                            "maxOutputTokens": max_tokens,
                        }
                    },
                    timeout=60
                )
                
                response.raise_for_status()
                data = response.json()
                
                if "candidates" in data and len(data["candidates"]) > 0:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    return "Error: No response generated from Gemini"
            
            return call_gemini_with_retry(
                api_call,
                self.api_key_manager,
                verbose=self.verbose,
                max_retries=2
            )
        else:
            try:
                response = requests.post(
                    f"{GEMINI_API_URL}?key={self.gemini_api_key}",
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": temperature,
                            "topK": 40,
                            "topP": 0.95,
                            "maxOutputTokens": max_tokens,
                        }
                    },
                    timeout=60
                )
                
                response.raise_for_status()
                data = response.json()
                
                if "candidates" in data and len(data["candidates"]) > 0:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    return "Error: No response generated from Gemini"
                
            except Exception as e:
                self._log(f"❌ Gemini API error: {str(e)}", Fore.RED)
                return f"Error: {str(e)}"
    
    def _chunk_content(self, content: str, max_size: int) -> List[str]:
        """Split large content into manageable chunks"""
        if len(content) <= max_size:
            return [content]
        
        chunks = []
        paragraphs = content.split('\n\n')
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= max_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # Force split if still too large
        final_chunks = []
        for chunk in chunks:
            if len(chunk) <= max_size:
                final_chunks.append(chunk)
            else:
                for i in range(0, len(chunk), max_size):
                    final_chunks.append(chunk[i:i + max_size])
        
        return final_chunks
    
    def _analyze_structure(self, content: str) -> Dict[str, Any]:
        """Analyze content structure with retry logic"""
        self._log("\n🔍 Step 1: Analyzing content structure...", Fore.CYAN)
        
        sample = content[:MAX_ANALYSIS_SIZE] if len(content) > MAX_ANALYSIS_SIZE else content
        self._log(f"  Analyzing {len(sample):,} characters", Fore.BLUE)
        
        analysis_prompt = f"""Analyze this content to create a mind map structure.

Content sample:
{sample}

Provide JSON response with:
1. main_topic: Central topic/theme (5-10 words)
2. major_themes: List of 3-6 major themes
3. estimated_depth: Recommended depth (2-5)
4. complexity: "simple", "moderate", "complex"
5. content_type: "educational", "technical", "conceptual", etc.

IMPORTANT: Return ONLY valid JSON, no markdown, no extra text.

Example format:
{{"main_topic": "...", "major_themes": ["...", "..."], "estimated_depth": 3, "complexity": "moderate", "content_type": "educational"}}"""
        
        for attempt in range(3):
            try:
                response = self._call_gemini(analysis_prompt, temperature=0.3)
                response = self._clean_json_response(response)
                analysis = json.loads(response)
                
                self._log(f"✓ Main Topic: {analysis.get('main_topic', 'Unknown')}", Fore.GREEN)
                self._log(f"✓ Major Themes: {len(analysis.get('major_themes', []))}", Fore.GREEN)
                self._log(f"✓ Recommended Depth: {analysis.get('estimated_depth', 3)}", Fore.GREEN)
                
                return analysis
                
            except (json.JSONDecodeError, Exception) as e:
                self._log(f"⚠️ Analysis attempt {attempt + 1} failed: {str(e)[:80]}", Fore.YELLOW)
                if attempt < 2:
                    time.sleep(1)
                continue
        
        # Fallback
        self._log("⚠️ Using default analysis", Fore.YELLOW)
        return {
            'main_topic': 'Main Topic',
            'major_themes': ['Theme 1', 'Theme 2', 'Theme 3'],
            'estimated_depth': 3,
            'complexity': 'moderate',
            'content_type': 'general'
        }
    
    def _extract_hierarchy_from_chunk(
        self,
        chunk: str,
        chunk_info: str,
        depth: int
    ) -> Dict:
        """Extract hierarchical structure from a single chunk"""
        
        hierarchy_prompt = f"""Extract hierarchical mind map structure from this content.

{chunk_info}
Target Depth: {depth} levels

Content:
{chunk}

Create a hierarchy with:
- Level 0: Main topic (1 node)
- Level 1: Major sections (2-5 nodes)
- Level 2+: Key concepts (2-4 nodes each)

For each node:
- label: Brief title (2-6 words)
- description: One sentence (10-20 words)
- importance: 0.0-1.0
- tags: 2-4 tags
- examples: 1-2 examples

Return JSON:
{{
  "root": {{
    "label": "Main Topic",
    "description": "Brief description",
    "importance": 1.0,
    "tags": ["tag1", "tag2"],
    "examples": ["example1"],
    "children": [
      {{
        "label": "Subtopic",
        "description": "Description",
        "importance": 0.8,
        "tags": ["tag"],
        "examples": ["ex"],
        "children": [...]
      }}
    ]
  }}
}}

IMPORTANT: Return ONLY valid JSON, no markdown."""
        
        for attempt in range(3):
            try:
                response = self._call_gemini(hierarchy_prompt, temperature=0.5, max_tokens=8192)
                response = self._clean_json_response(response)
                hierarchy = json.loads(response)
                
                # Validate structure
                if 'root' in hierarchy and isinstance(hierarchy['root'], dict):
                    return hierarchy
                
            except (json.JSONDecodeError, Exception) as e:
                if attempt < 2:
                    time.sleep(0.5)
                continue
        
        # Minimal fallback
        return {
            'root': {
                'label': 'Content Node',
                'description': 'Extracted content',
                'importance': 0.8,
                'tags': ['content'],
                'examples': [],
                'children': []
            }
        }
    
    def _extract_hierarchy(
        self,
        content: str,
        analysis: Dict,
        max_depth: int = 4
    ) -> Dict:
        """Extract hierarchical structure with chunking support"""
        self._log("\n🌳 Step 2: Extracting hierarchical structure...", Fore.CYAN)
        
        depth = min(max_depth, analysis.get('estimated_depth', 3))
        chunks = self._chunk_content(content, MAX_CONTENT_SIZE)
        
        self._log(f"  Processing {len(chunks)} chunk(s)", Fore.BLUE)
        
        if len(chunks) == 1:
            # Single chunk - direct processing
            chunk_info = f"Main Topic: {analysis.get('main_topic')}\nThemes: {', '.join(analysis.get('major_themes', []))}"
            return self._extract_hierarchy_from_chunk(chunks[0], chunk_info, depth)
        
        # Multiple chunks - process and merge
        all_hierarchies = []
        
        for i, chunk in enumerate(chunks):
            self._print_progress(i, len(chunks), "Extracting hierarchy")
            
            chunk_info = f"Section {i+1}/{len(chunks)} of: {analysis.get('main_topic')}"
            hierarchy = self._extract_hierarchy_from_chunk(chunk, chunk_info, depth - 1)
            
            if hierarchy and 'root' in hierarchy:
                all_hierarchies.append(hierarchy['root'])
        
        self._print_progress(len(chunks), len(chunks), "Extracting hierarchy")
        
        # Merge hierarchies under single root
        merged_root = {
            'label': analysis.get('main_topic', 'Main Topic'),
            'description': f"Comprehensive overview covering {len(chunks)} sections",
            'importance': 1.0,
            'tags': analysis.get('major_themes', ['topic'])[:4],
            'examples': [],
            'children': all_hierarchies
        }
        
        self._log(f"✓ Merged {len(all_hierarchies)} sections", Fore.GREEN)
        
        return {'root': merged_root}
    
    def _build_mindmap_from_hierarchy(
        self,
        hierarchy: Dict,
        title: str
    ) -> MindMap:
        """Build MindMap object from hierarchical structure"""
        self._log("\n🗺️  Step 3: Building mind map...", Fore.CYAN)
        
        nodes = {}
        root_id = str(uuid.uuid4())
        
        def process_node(node_data: Dict, level: int = 0, parent_id: Optional[str] = None) -> str:
            """Recursively process nodes"""
            node_id = str(uuid.uuid4())
            
            node = MindMapNode(
                id=node_id,
                label=str(node_data.get('label', 'Node'))[:100],  # Limit length
                description=str(node_data.get('description', ''))[:300],
                level=level,
                parent_id=parent_id,
                importance=float(node_data.get('importance', 0.5)),
                tags=list(node_data.get('tags', []))[:6],
                examples=list(node_data.get('examples', []))[:3]
            )
            
            # Process children
            children_data = node_data.get('children', [])
            if isinstance(children_data, list):
                for child_data in children_data:
                    if isinstance(child_data, dict):
                        child_id = process_node(child_data, level + 1, node_id)
                        node.children.append(child_id)
            
            nodes[node_id] = node
            return node_id
        
        # Process root
        root_data = hierarchy.get('root', {})
        root_id = process_node(root_data, 0, None)
        
        self._log(f"✓ Built mind map with {len(nodes)} nodes", Fore.GREEN)
        
        return MindMap(
            title=title,
            root_id=root_id,
            nodes=nodes,
            metadata={
                'total_nodes': len(nodes),
                'max_depth': max(node.level for node in nodes.values()) if nodes else 0,
                'generation_method': 'agentic_ai_v2'
            }
        )
    
    def _identify_relationships(
        self,
        nodes: Dict[str, MindMapNode],
        content: str
    ) -> Dict[str, List[str]]:
        """Identify cross-connections with error handling"""
        self._log("\n🔗 Step 4: Identifying relationships...", Fore.CYAN)
        
        # Limit nodes for relationship analysis
        node_labels = {node_id: node.label for node_id, node in list(nodes.items())[:30]}
        
        relationship_prompt = f"""Identify relationships between these concepts (beyond parent-child):

Concepts:
{json.dumps(node_labels, indent=2)}

Return JSON mapping node IDs to related node IDs:
{{"node_id_1": ["related_id_2", "related_id_3"], "node_id_2": ["related_id_4"]}}

Only significant relationships. ONLY JSON, no markdown."""
        
        for attempt in range(2):
            try:
                response = self._call_gemini(relationship_prompt, temperature=0.4)
                response = self._clean_json_response(response)
                relationships = json.loads(response)
                
                if isinstance(relationships, dict):
                    total_rels = sum(len(rels) for rels in relationships.values())
                    self._log(f"✓ Identified {total_rels} relationships", Fore.GREEN)
                    return relationships
                
            except (json.JSONDecodeError, Exception):
                if attempt == 0:
                    time.sleep(0.5)
                continue
        
        self._log("⚠️ Skipping relationship identification", Fore.YELLOW)
        return {}
    
    def generate(
        self,
        content: str,
        title: str = "Generated Mind Map",
        max_depth: int = 4,
        identify_relationships: bool = True
    ) -> MindMap:
        """Generate mind map with robust error handling"""
        
        # Beautiful header
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}{'🗺️  MIND MAP GENERATOR':^80}")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
        print(f"{Fore.YELLOW}Title:{Style.RESET_ALL} {title}")
        print(f"{Fore.YELLOW}Content Size:{Style.RESET_ALL} {len(content):,} characters")
        print(f"{Fore.YELLOW}Max Depth:{Style.RESET_ALL} {max_depth} levels\n")
        
        start_time = time.time()
        
        # Step 1: Analyze
        analysis = self._analyze_structure(content)
        
        # Step 2: Extract hierarchy
        hierarchy = self._extract_hierarchy(content, analysis, max_depth)
        
        # Step 3: Build mind map
        mindmap = self._build_mindmap_from_hierarchy(hierarchy, title)
        
        # Step 4: Relationships
        if identify_relationships and len(mindmap.nodes) > 3:
            relationships = self._identify_relationships(mindmap.nodes, content[:MAX_ANALYSIS_SIZE])
            
            for node_id, related_ids in relationships.items():
                if node_id in mindmap.nodes:
                    mindmap.nodes[node_id].related_nodes = [
                        rid for rid in related_ids if rid in mindmap.nodes
                    ]
        
        # Update metadata
        elapsed_time = time.time() - start_time
        mindmap.metadata.update({
            'processing_time_seconds': elapsed_time,
            'content_size': len(content),
            'content_analysis': analysis,
            'api_method': 'REST API with retry'
        })
        
        # Beautiful summary
        print(f"\n{Fore.GREEN}{'='*80}")
        print(f"{Fore.GREEN}{'✅ GENERATION COMPLETE':^80}")
        print(f"{Fore.GREEN}{'='*80}{Style.RESET_ALL}\n")
        print(f"{Fore.GREEN}📊 Statistics:{Style.RESET_ALL}")
        print(f"   Total Nodes: {len(mindmap.nodes)}")
        print(f"   Max Depth: {mindmap.metadata['max_depth']} levels")
        print(f"   Relationships: {sum(len(n.related_nodes) for n in mindmap.nodes.values())}")
        print(f"   Processing Time: {elapsed_time:.2f}s\n")
        
        return mindmap
    
    def save_mindmap(
        self,
        mindmap: MindMap,
        filepath: str,
        format: str = "json"
    ):
        """Save mind map with error handling"""
        try:
            if format == "json":
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(mindmap.to_dict(), f, indent=2, ensure_ascii=False)
            
            elif format == "markdown":
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(mindmap.to_markdown())
            
            elif format == "mermaid":
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(mindmap.to_mermaid())
            
            self._log(f"✓ Mind map saved to {filepath}", Fore.GREEN)
            
        except Exception as e:
            self._log(f"❌ Error saving: {str(e)}", Fore.RED)