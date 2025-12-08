"""
Enhanced Mind Map Generator with AI-Powered 3D Styling
=======================================================

Features:
1. AI-generated color schemes that match content mood
2. Intelligent keyword highlighting in bold
3. Beautiful 3D card-style design
4. Deep hierarchies (up to 8 levels)
5. Retry logic with fallback styling

Dependencies:
    pip install graphviz colorama python-dotenv requests

Usage:
    python mindmap_visual.py --file document.txt --depth 8
"""

import os
import json
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
import textwrap
import html
import time
import re

try:
    from graphviz import Digraph
except ImportError:
    print("ERROR: graphviz not installed. Install with: pip install graphviz")
    print("Also install system Graphviz: https://graphviz.org/download/")
    exit(1)

from colorama import Fore, Style, init
from mindmap_generator import MindMapGenerator, MindMap, MindMapNode
from api_key_manager import APIKeyManager

init(autoreset=True)


class EnhancedMindMapGenerator(MindMapGenerator):
    """Extended generator with deeper hierarchies"""
    
    def _extract_hierarchy_from_chunk(
        self,
        chunk: str,
        chunk_info: str,
        depth: int
    ) -> Dict:
        """Extract DEEP hierarchical structure"""
        
        hierarchy_prompt = f"""Extract a DEEP and COMPREHENSIVE hierarchical mind map from this content.

{chunk_info}
Target Depth: {depth} levels (create ALL {depth} levels with rich detail)

Content:
{chunk}

Create a detailed hierarchy:
- Level 0: Main topic (1 node)
- Level 1: Major sections (3-6 nodes)
- Level 2: Key concepts (3-5 nodes each)
- Level 3: Sub-concepts (2-4 nodes each)
- Level 4+: Specific details, examples, techniques, methods

For EVERY node provide:
- label: Clear title (3-8 words)
- description: Detailed explanation (15-30 words)
- importance: 0.0-1.0 (how critical this concept is)
- tags: 3-5 relevant tags/keywords
- examples: 2-3 concrete examples from the content

Return ONLY valid JSON (no markdown):
{{
  "root": {{
    "label": "Main Topic Title",
    "description": "Comprehensive description of the main topic",
    "importance": 1.0,
    "tags": ["tag1", "tag2", "tag3"],
    "examples": ["example1", "example2"],
    "children": [
      {{
        "label": "Major Section",
        "description": "Detailed description",
        "importance": 0.9,
        "tags": ["subtag1", "subtag2"],
        "examples": ["ex1", "ex2"],
        "children": [
          {{
            "label": "Key Concept",
            "description": "In-depth explanation",
            "importance": 0.8,
            "tags": ["concept"],
            "examples": ["detailed example"],
            "children": [...]
          }}
        ]
      }}
    ]
  }}
}}

IMPORTANT: 
- Create ALL {depth} levels of hierarchy
- Include rich descriptions and multiple examples
- Be comprehensive - extract all important information"""
        
        for attempt in range(3):
            try:
                response = self._call_gemini(
                    hierarchy_prompt, 
                    temperature=0.6,
                    max_tokens=8192
                )
                response = self._clean_json_response(response)
                hierarchy = json.loads(response)
                
                if 'root' in hierarchy and isinstance(hierarchy['root'], dict):
                    return hierarchy
                
            except (json.JSONDecodeError, Exception) as e:
                if attempt < 2:
                    self._log(f"⚠️ Attempt {attempt + 1} failed, retrying...", Fore.YELLOW)
                    continue
        
        return {
            'root': {
                'label': 'Content Section',
                'description': 'Extracted content from document',
                'importance': 0.8,
                'tags': ['content', 'information'],
                'examples': ['See source material'],
                'children': []
            }
        }


class MindMapVisualizer:
    """AI-powered 3D visualization using Graphviz"""
    
    # Default fallback palette
    DEFAULT_LEVEL_STYLES = [
        {
            'gradient_start': '#667EEA',
            'gradient_end': '#764BA2',
            'text_color': '#FFFFFF',
            'border': '#5A67D8',
            'shadow': '#4C51BF',
        },
        {
            'gradient_start': '#F857A6',
            'gradient_end': '#FF5858',
            'text_color': '#FFFFFF',
            'border': '#EC4899',
            'shadow': '#DB2777',
        },
        {
            'gradient_start': '#48C6EF',
            'gradient_end': '#6F86D6',
            'text_color': '#FFFFFF',
            'border': '#3B82F6',
            'shadow': '#2563EB',
        },
        {
            'gradient_start': '#11998E',
            'gradient_end': '#38EF7D',
            'text_color': '#FFFFFF',
            'border': '#10B981',
            'shadow': '#059669',
        },
        {
            'gradient_start': '#FA8BFF',
            'gradient_end': '#2BD2FF',
            'text_color': '#FFFFFF',
            'border': '#EC4899',
            'shadow': '#DB2777',
        },
        {
            'gradient_start': '#FF6A00',
            'gradient_end': '#EE0979',
            'text_color': '#FFFFFF',
            'border': '#F97316',
            'shadow': '#EA580C',
        },
        {
            'gradient_start': '#C471F5',
            'gradient_end': '#FA71CD',
            'text_color': '#FFFFFF',
            'border': '#A855F7',
            'shadow': '#9333EA',
        },
        {
            'gradient_start': '#FFD200',
            'gradient_end': '#F7971E',
            'text_color': '#1F2937',
            'border': '#F59E0B',
            'shadow': '#D97706',
        },
    ]
    
    def __init__(self, mindmap: MindMap, generator: Optional[MindMapGenerator] = None):
        self.mindmap = mindmap
        self.graph = None
        self.generator = generator
        self.LEVEL_STYLES = None
        self.keyword_highlights = {}
    
    def _generate_ai_styling(self, title: str) -> Tuple[List[Dict], Dict[str, str]]:
        """Generate beautiful color scheme and keyword highlights using Gemini AI"""
        if not self.generator:
            print(f"{Fore.YELLOW}⚠️  No generator available, using default styling{Style.RESET_ALL}")
            return self.DEFAULT_LEVEL_STYLES, {}
        
        print(f"\n{Fore.CYAN}🎨 Generating AI-powered custom styling...{Style.RESET_ALL}")
        
        # Get sample content from mind map
        sample_nodes = []
        for node in list(self.mindmap.nodes.values())[:10]:
            sample_nodes.append({
                'label': node.label,
                'description': node.description,
                'tags': node.tags
            })
        
        style_prompt = f"""Design a beautiful, cohesive color scheme for a mind map about: "{title}"

Sample content:
{json.dumps(sample_nodes, indent=2)}

Requirements:
1. Create 8 gradient color combinations that:
   - Match the topic's mood and energy
   - Have excellent contrast and readability
   - Work harmoniously together
   - Use modern, vibrant colors
   - Each gradient flows smoothly (complementary colors)

2. Identify 5-10 important keywords to highlight in BOLD across the mind map

Return ONLY valid JSON:
{{
  "color_scheme": [
    {{
      "gradient_start": "#RRGGBB",
      "gradient_end": "#RRGGBB",
      "text_color": "#FFFFFF or #1F2937",
      "border": "#RRGGBB",
      "mood": "energetic/calm/professional/creative"
    }},
    ... (8 total)
  ],
  "keywords_to_highlight": ["keyword1", "keyword2", ...],
  "theme_description": "Brief description of the color theme"
}}

IMPORTANT: 
- All colors MUST be valid hex codes (#RRGGBB)
- Ensure text_color contrasts well with gradients
- Make it visually stunning and cohesive
- Keywords should be important technical terms or concepts
- Return ONLY JSON, no markdown"""
        
        for attempt in range(3):
            try:
                response = self.generator._call_gemini(style_prompt, temperature=0.8, max_tokens=2048)
                response = self.generator._clean_json_response(response)
                styling = json.loads(response)
                
                # Validate structure
                if 'color_scheme' in styling and len(styling['color_scheme']) >= 8:
                    color_scheme = styling['color_scheme'][:8]
                    keywords = styling.get('keywords_to_highlight', [])
                    theme_desc = styling.get('theme_description', 'Custom AI-generated theme')
                    
                    # Validate hex colors
                    valid_scheme = []
                    for style in color_scheme:
                        if all(key in style for key in ['gradient_start', 'gradient_end', 'text_color', 'border']):
                            # Basic hex validation
                            if all(style[key].startswith('#') and len(style[key]) == 7 
                                   for key in ['gradient_start', 'gradient_end', 'text_color', 'border']):
                                valid_scheme.append({
                                    'gradient_start': style['gradient_start'],
                                    'gradient_end': style['gradient_end'],
                                    'text_color': style['text_color'],
                                    'border': style['border'],
                                    'shadow': style['border'],
                                })
                    
                    if len(valid_scheme) >= 8:
                        print(f"{Fore.GREEN}✓ Generated custom color theme: {theme_desc}{Style.RESET_ALL}")
                        print(f"{Fore.GREEN}✓ Identified {len(keywords)} keywords for highlighting{Style.RESET_ALL}")
                        
                        # Create keyword highlight mapping
                        keyword_map = {}
                        highlight_color = '#FFD700'  # Gold highlight
                        for kw in keywords:
                            keyword_map[kw.lower()] = highlight_color
                        
                        return valid_scheme, keyword_map
                
            except (json.JSONDecodeError, Exception) as e:
                print(f"{Fore.YELLOW}⚠️  Styling attempt {attempt + 1} failed: {str(e)[:80]}{Style.RESET_ALL}")
                if attempt < 2:
                    time.sleep(1)
                continue
        
        print(f"{Fore.YELLOW}⚠️  Using default color scheme{Style.RESET_ALL}")
        return self.DEFAULT_LEVEL_STYLES, {}
    
    def _apply_keyword_highlighting(self, text: str) -> str:
        """Apply bold highlighting to important keywords"""
        if not self.keyword_highlights:
            return html.escape(text)
        
        # Escape HTML first
        escaped_text = html.escape(text)
        
        # Apply highlighting for each keyword
        for keyword, color in self.keyword_highlights.items():
            # Case-insensitive replacement with word boundaries
            pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
            
            def replace_func(match):
                original = match.group(0)
                return f'<B><FONT COLOR="{color}">{original}</FONT></B>'
            
            escaped_text = pattern.sub(replace_func, escaped_text)
        
        return escaped_text
    
    def _create_node_label(self, node: MindMapNode, detailed: bool = True) -> str:
        """Create stunning card-style label with proper escaping"""
        # For detailed view, use simple clean text with line breaks
        if detailed:
            lines = []
            
            # Icon based on level
            if node.level == 0:
                icon = '🎯'
            elif node.level == 1:
                icon = '💡'
            elif node.level == 2:
                icon = '📌'
            else:
                icon = '→'
            
            # Title
            title = f"{icon} {node.label}"
            lines.append(title)
            lines.append("─" * min(len(title), 30))
            
            # Description
            if node.description:
                desc_lines = textwrap.wrap(node.description, width=40)
                lines.extend(desc_lines)
            
            # Examples
            if node.examples:
                lines.append("")
                lines.append("✨ Examples:")
                for i, ex in enumerate(node.examples[:2], 1):
                    ex_lines = textwrap.wrap(f"{i}. {ex}", width=38)
                    lines.extend(ex_lines)
            
            # Tags
            if node.tags:
                lines.append("")
                tags_text = " • ".join([f"#{tag}" for tag in node.tags[:4]])
                lines.append(tags_text)
            
            return "\n".join(lines)
        else:
            # Minimal view - just title with icon
            if node.level == 0:
                icon = '🎯'
            elif node.level == 1:
                icon = '💡'
            elif node.level == 2:
                icon = '📌'
            else:
                icon = '→'
            return f"{icon} {node.label}"
    
    def _get_node_style(self, node: MindMapNode) -> Dict:
        """Get stunning 3D card-style with AI-generated colors"""
        # Ensure we have styles loaded
        if not self.LEVEL_STYLES:
            self.LEVEL_STYLES = self.DEFAULT_LEVEL_STYLES
        
        level = min(node.level, len(self.LEVEL_STYLES) - 1)
        style_config = self.LEVEL_STYLES[level]
        
        # Rich diagonal gradient for depth and dimension
        gradient = f'{style_config["gradient_start"]}:{style_config["gradient_end"]}'
        
        style = {
            'fillcolor': gradient,
            'gradientangle': '135',
            'color': style_config['border'],
            'fontcolor': style_config['text_color'],
            'style': 'filled,rounded,bold',
            'shape': 'box',
            'fontname': 'Helvetica Neue',
            'fontsize': '11',
            'margin': '0.4,0.3',
        }
        
        # Progressive sizing with visual hierarchy
        if node.level == 0:
            style.update({
                'penwidth': '4',
                'fontsize': '14',
                'margin': '0.6,0.4',
                'height': '1.8',
                'width': '4.5',
            })
        elif node.level == 1:
            style.update({
                'penwidth': '3.2',
                'fontsize': '12',
                'margin': '0.5,0.35',
                'height': '1.5',
                'width': '4.0',
            })
        elif node.level == 2:
            style.update({
                'penwidth': '2.6',
                'fontsize': '11',
                'margin': '0.4,0.3',
                'height': '1.3',
                'width': '3.5',
            })
        elif node.level == 3:
            style.update({
                'penwidth': '2.2',
                'fontsize': '10',
                'margin': '0.35,0.25',
                'height': '1.1',
                'width': '3.0',
            })
        else:
            style.update({
                'penwidth': '2',
                'fontsize': '9',
                'margin': '0.3,0.22',
                'height': '1.0',
                'width': '2.7',
            })
        
        return style
    
    def _add_node_recursive(
        self,
        node_id: str,
        visited: Set[str],
        show_details: bool = True
    ):
        """Recursively add nodes with modern styling"""
        if node_id in visited:
            return
        visited.add(node_id)
        
        node = self.mindmap.nodes[node_id]
        
        # Create node label
        label = self._create_node_label(node, detailed=show_details)
        
        # Get style
        style = self._get_node_style(node)
        
        # Add node
        self.graph.node(
            node_id,
            label=label,
            **style
        )
        
        # Add elegant, flowing edges to children
        for child_id in node.children:
            if child_id in self.mindmap.nodes:
                self._add_node_recursive(child_id, visited, show_details)
                
                # Rich, vibrant edges that complement the card colors
                level = min(node.level, len(self.LEVEL_STYLES) - 1)
                edge_color = self.LEVEL_STYLES[level]['border']
                
                # Dynamic edge width based on importance
                child_node = self.mindmap.nodes[child_id]
                edge_width = 2.0 + (child_node.importance * 1.5)
                
                edge_attrs = {
                    'color': f'{edge_color}AA',
                    'penwidth': str(edge_width),
                    'arrowsize': '0.8',
                    'arrowhead': 'vee',
                    'weight': '2',
                }
                
                self.graph.edge(node_id, child_id, **edge_attrs)
    
    def create_visualization(
        self,
        output_path: str,
        format: str = 'png',
        layout: str = 'dot',
        show_details: bool = True,
        dpi: int = 150,
        use_ai_styling: bool = True
    ) -> str:
        """Create beautiful 3D visualization with AI-powered styling"""
        
        # Generate AI styling if enabled
        if use_ai_styling and self.generator:
            self.LEVEL_STYLES, self.keyword_highlights = self._generate_ai_styling(self.mindmap.title)
        else:
            self.LEVEL_STYLES = self.DEFAULT_LEVEL_STYLES
            self.keyword_highlights = {}
        
        print(f"\n{Fore.CYAN}🎨 Creating 3D NotebookLM-style visualization...{Style.RESET_ALL}")
        
        # Create graph with modern settings
        self.graph = Digraph(
            name='MindMap',
            format=format,
            engine=layout
        )
        
        # Modern, premium graph settings
        self.graph.attr(
            rankdir='LR',
            splines='curved',
            nodesep='0.7',
            ranksep='1.1',
            bgcolor='#FAFBFC',
            dpi=str(dpi),
            pad='0.4',
            overlap='false',
            compound='true',
            concentrate='false',
            smoothing='triangle',
        )
        
        # Premium typography
        self.graph.attr('node',
            fontname='Helvetica Neue',
        )
        
        self.graph.attr('edge',
            fontname='Helvetica Neue',
            fontsize='9',
            fontcolor='#6B7280',
            arrowsize='0.8',
            labeldistance='2.5',
            labelangle='0',
        )
        
        # Add all nodes
        visited = set()
        self._add_node_recursive(self.mindmap.root_id, visited, show_details)
        
        # Render
        output_file = Path(output_path).stem
        output_dir = Path(output_path).parent
        
        try:
            result = self.graph.render(
                filename=output_file,
                directory=output_dir,
                cleanup=True,
                view=False
            )
            
            print(f"{Fore.GREEN}✓ Visualization saved: {result}{Style.RESET_ALL}")
            print(f"  {Fore.BLUE}Nodes: {len(visited)} | "
                  f"Format: {format.upper()} | "
                  f"Layout: {layout}{Style.RESET_ALL}")
            
            return result
            
        except Exception as e:
            print(f"{Fore.RED}❌ Visualization error: {str(e)}{Style.RESET_ALL}")
            print(f"  {Fore.YELLOW}Make sure Graphviz is installed: brew install graphviz{Style.RESET_ALL}")
            return None
    
    def create_multiformat(
        self,
        base_path: str,
        formats: List[str] = None,
        layouts: List[str] = None,
        use_ai_styling: bool = True
    ) -> List[str]:
        """Create multiple format outputs with AI styling"""
        if formats is None:
            formats = ['svg', 'png']
        if layouts is None:
            layouts = ['dot']
        
        results = []
        
        for fmt in formats:
            for layout in layouts:
                output_path = f"{base_path}_{layout}.{fmt}"
                dpi = 150
                result = self.create_visualization(
                    output_path,
                    format=fmt,
                    layout=layout,
                    show_details=True,
                    dpi=dpi,
                    use_ai_styling=use_ai_styling
                )
                if result:
                    results.append(result)
        
        return results
    
    def generate_stats_report(self) -> str:
        """Generate detailed statistics report"""
        nodes = self.mindmap.nodes.values()
        
        total_nodes = len(nodes)
        max_depth = max(n.level for n in nodes)
        avg_children = sum(len(n.children) for n in nodes) / total_nodes if total_nodes > 0 else 0
        
        # Nodes per level
        level_counts = {}
        for node in nodes:
            level_counts[node.level] = level_counts.get(node.level, 0) + 1
        
        # Most important nodes
        important_nodes = sorted(nodes, key=lambda n: n.importance, reverse=True)[:5]
        
        # Most connected nodes
        connected_nodes = sorted(nodes, key=lambda n: len(n.children), reverse=True)[:5]
        
        # Generate report
        report = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════════╗
║                    MIND MAP STATISTICS REPORT                    ║
╚══════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}

{Fore.YELLOW}📊 OVERALL STATISTICS{Style.RESET_ALL}
  • Total Nodes:           {total_nodes}
  • Maximum Depth:         {max_depth} levels
  • Average Children:      {avg_children:.2f}

{Fore.YELLOW}📈 NODES PER LEVEL{Style.RESET_ALL}
"""
        
        for level in sorted(level_counts.keys()):
            count = level_counts[level]
            bar = '█' * min(50, count)
            report += f"  Level {level}: {count:3d} {Fore.GREEN}{bar}{Style.RESET_ALL}\n"
        
        report += f"\n{Fore.YELLOW}⭐ TOP 5 MOST IMPORTANT NODES{Style.RESET_ALL}\n"
        for i, node in enumerate(important_nodes, 1):
            report += f"  {i}. {node.label[:50]:<50} ({node.importance:.2f})\n"
        
        report += f"\n{Fore.YELLOW}🔗 TOP 5 MOST CONNECTED NODES{Style.RESET_ALL}\n"
        for i, node in enumerate(connected_nodes, 1):
            connections = len(node.children)
            report += f"  {i}. {node.label[:50]:<50} ({connections} children)\n"
        
        # Tag analysis
        all_tags = {}
        for node in nodes:
            for tag in node.tags:
                all_tags[tag] = all_tags.get(tag, 0) + 1
        
        top_tags = sorted(all_tags.items(), key=lambda x: x[1], reverse=True)[:10]
        
        report += f"\n{Fore.YELLOW}🏷️  TOP 10 TAGS{Style.RESET_ALL}\n"
        for tag, count in top_tags:
            report += f"  • {tag:<20} ({count} occurrences)\n"
        
        return report


def read_file_content(file_path: Path) -> Optional[str]:
    """Read content from various file formats including PDF"""
    try:
        if not file_path.exists():
            print(f"{Fore.RED}❌ File not found: {file_path}{Style.RESET_ALL}")
            return None
        
        print(f"{Fore.YELLOW}📄 Reading file: {file_path.name}{Style.RESET_ALL}")
        
        # Text files
        if file_path.suffix.lower() in ['.txt', '.md']:
            content = file_path.read_text(encoding='utf-8')
        
        # PDF files
        elif file_path.suffix.lower() == '.pdf':
            try:
                import PyPDF2
                content = ""
                with open(file_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    total_pages = len(pdf_reader.pages)
                    print(f"{Fore.CYAN}  📑 Processing {total_pages} pages...{Style.RESET_ALL}")
                    
                    for i, page in enumerate(pdf_reader.pages, 1):
                        try:
                            content += page.extract_text() + "\n\n"
                        except Exception as e:
                            print(f"{Fore.YELLOW}  ⚠️  Page {i} extraction warning{Style.RESET_ALL}")
                        
                        if i % 50 == 0:
                            print(f"{Fore.CYAN}  Progress: {i}/{total_pages} pages{Style.RESET_ALL}")
                    
                    print(f"{Fore.GREEN}  ✓ Extracted text from {total_pages} pages{Style.RESET_ALL}")
                    
            except ImportError:
                print(f"{Fore.RED}❌ PyPDF2 not installed. Install: pip install PyPDF2{Style.RESET_ALL}")
                return None
            except Exception as e:
                print(f"{Fore.RED}❌ Error reading PDF: {str(e)}{Style.RESET_ALL}")
                return None
        
        # DOCX files
        elif file_path.suffix.lower() == '.docx':
            try:
                import docx
                doc = docx.Document(file_path)
                content = "\n".join([para.text for para in doc.paragraphs])
                print(f"{Fore.GREEN}  ✓ Extracted text from DOCX{Style.RESET_ALL}")
            except ImportError:
                print(f"{Fore.RED}❌ python-docx not installed. Install: pip install python-docx{Style.RESET_ALL}")
                return None
            except Exception as e:
                print(f"{Fore.RED}❌ Error reading DOCX: {str(e)}{Style.RESET_ALL}")
                return None
        
        else:
            print(f"{Fore.RED}❌ Unsupported format: {file_path.suffix}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}   Supported: .txt, .md, .pdf, .docx{Style.RESET_ALL}")
            return None
        
        # Success message
        size_kb = len(content) / 1024
        word_count = len(content.split())
        print(f"{Fore.GREEN}✓ Loaded {len(content):,} characters ({size_kb:.1f} KB, ~{word_count:,} words){Style.RESET_ALL}")
        
        # Warn about large content
        if len(content) > 500000:
            print(f"{Fore.YELLOW}⚠️  Large content detected! This will be chunked for processing.{Style.RESET_ALL}")
        
        return content
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error reading file: {str(e)}{Style.RESET_ALL}")
        return None


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="AI-Powered 3D Mind Map Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--file', '-f', required=True, help='Input file path')
    parser.add_argument('--depth', '-d', type=int, default=6, help='Maximum depth (default: 6, max: 8)')
    parser.add_argument('--output', '-o', default='mindmap', help='Output base name (default: mindmap)')
    parser.add_argument('--formats', nargs='+', choices=['png', 'svg', 'pdf'], 
                       default=['png', 'svg'], help='Output formats')
    parser.add_argument('--layout', choices=['dot', 'neato', 'fdp', 'circo'], 
                       default='dot', help='Graph layout engine')
    parser.add_argument('--no-ai-styling', action='store_true', 
                       help='Disable AI-powered color scheme generation')
    
    args = parser.parse_args()
    
    max_depth = max(2, min(8, args.depth))
    
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}{'🗺️  AI-POWERED 3D MIND MAP GENERATOR':^80}")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    # Read file
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"{Fore.RED}❌ File not found: {args.file}{Style.RESET_ALL}")
        return
    
    # Read content using the helper function
    content = read_file_content(file_path)
    if not content:
        return
    
    # Initialize generator
    try:
        generator = EnhancedMindMapGenerator(verbose=True)
    except ValueError as e:
        print(f"{Fore.RED}❌ {str(e)}{Style.RESET_ALL}")
        return
    
    # Generate mind map
    title = file_path.stem.replace('_', ' ').title()
    mindmap = generator.generate(
        content=content,
        title=title,
        max_depth=max_depth,
        identify_relationships=True
    )
    
    # Save text formats
    output_base = args.output
    generator.save_mindmap(mindmap, f"{output_base}.json", format="json")
    generator.save_mindmap(mindmap, f"{output_base}.md", format="markdown")
    generator.save_mindmap(mindmap, f"{output_base}.mmd", format="mermaid")
    
    # Create visualization
    visualizer = MindMapVisualizer(mindmap, generator=generator)
    
    # Generate all requested formats with AI styling
    use_ai_styling = not args.no_ai_styling
    results = visualizer.create_multiformat(
        output_base,
        formats=args.formats,
        layouts=[args.layout],
        use_ai_styling=use_ai_styling
    )
    
    # Generate statistics report
    print(visualizer.generate_stats_report())
    
    # Summary
    print(f"\n{Fore.GREEN}╔{'═'*78}╗")
    print(f"{Fore.GREEN}║{'✅ ALL OUTPUTS GENERATED SUCCESSFULLY':^78}║")
    print(f"{Fore.GREEN}╚{'═'*78}╝{Style.RESET_ALL}\n")
    
    print(f"{Fore.CYAN}Generated files:{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}▸{Style.RESET_ALL} JSON:      {output_base}.json")
    print(f"  {Fore.GREEN}▸{Style.RESET_ALL} Markdown:  {output_base}.md")
    print(f"  {Fore.GREEN}▸{Style.RESET_ALL} Mermaid:   {output_base}.mmd")
    for result in results:
        print(f"  {Fore.GREEN}▸{Style.RESET_ALL} Visual:    {Path(result).name}")
    
    print(f"\n{Fore.MAGENTA}✨ Open the SVG file in your browser for the best experience!{Style.RESET_ALL}")
    print(f"{Fore.BLUE}   AI-generated colors + bold keyword highlights = stunning visuals!{Style.RESET_ALL}\n")


if __name__ == "__main__":
    main()