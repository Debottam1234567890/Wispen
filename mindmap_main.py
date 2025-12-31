"""
Main Script for Mind Map Generator with Beautiful UI
====================================================

Enhanced version with:
1. Beautiful progress indicators
2. Colorful console output
3. File upload support (TXT, PDF, DOCX, MD)
4. Interactive visualization
5. Batch processing

Dependencies:
    pip install requests colorama python-dotenv PyPDF2 python-docx

Usage:
    python mindmap_main.py
    python mindmap_main.py --file notes.txt
    python mindmap_main.py --file textbook.pdf --depth 5
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Optional
import time

# from colorama import Fore, Style, init (Removed for Render compatibility)
from dotenv import load_dotenv

from mindmap_generator import MindMapGenerator
from api_key_manager import APIKeyManager

# Dummy classes to replace colorama
class Fore:
    CYAN = ""
    GREEN = ""
    YELLOW = ""
    RED = ""
    BLUE = ""
    RESET = ""
    MAGENTA = ""
    WHITE = ""

class Style:
    RESET_ALL = ""

# init(autoreset=True)


class MindMapApp:
    """Main application with beautiful UI"""
    
    def __init__(self):
        """Initialize the application"""
        load_dotenv()
        
        # Print beautiful banner
        self._print_banner()
        
        try:
            api_key_manager = APIKeyManager()
            self.generator = MindMapGenerator(api_key_manager=api_key_manager, verbose=True)
        except ValueError:
            gemini_key = os.getenv("GEMINI_API_KEY")
            if not gemini_key:
                print(f"{Fore.RED}╔{'═'*78}╗")
                print(f"{Fore.RED}║{' '*78}║")
                print(f"{Fore.RED}║{'❌ API KEYS NOT FOUND':^78}║")
                print(f"{Fore.RED}║{' '*78}║")
                print(f"{Fore.RED}╚{'═'*78}╝{Style.RESET_ALL}\n")
                print("Please set environment variables:")
                print(f"  {Fore.CYAN}▸{Style.RESET_ALL} GEMINI_API_KEY1 (primary)")
                print(f"  {Fore.CYAN}▸{Style.RESET_ALL} GEMINI_API_KEY2 (fallback)")
                print(f"\nOr set {Fore.YELLOW}GEMINI_API_KEY{Style.RESET_ALL} for backward compatibility")
                sys.exit(1)
            self.generator = MindMapGenerator(gemini_api_key=gemini_key, verbose=True)
    
    def _print_banner(self):
        """Print beautiful startup banner"""
        banner = f"""
{Fore.CYAN}╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║                        {Fore.GREEN}🗺️  AI MIND MAP GENERATOR{Fore.CYAN}                             ║
║                                                                               ║
║                   {Fore.YELLOW}Transform Knowledge into Visual Structures{Fore.CYAN}                   ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
        print(banner)
    
    def _print_section_header(self, title: str, icon: str = "📋"):
        """Print beautiful section header"""
        print(f"\n{Fore.CYAN}╔{'═'*78}╗")
        print(f"{Fore.CYAN}║ {icon} {title:<74}║")
        print(f"{Fore.CYAN}╚{'═'*78}╝{Style.RESET_ALL}\n")
    
    def read_file(self, filepath: str) -> Optional[str]:
        """Read content from various file formats"""
        try:
            file_path = Path(filepath)
            
            if not file_path.exists():
                print(f"{Fore.RED}❌ File not found: {filepath}{Style.RESET_ALL}")
                return None
            
            print(f"{Fore.YELLOW}📄 Reading file...{Style.RESET_ALL}")
            print(f"   Path: {Fore.BLUE}{filepath}{Style.RESET_ALL}")
            
            # Text files
            if file_path.suffix in ['.txt', '.md']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            # PDF files
            elif file_path.suffix == '.pdf':
                try:
                    import PyPDF2
                    content = ""
                    with open(file_path, 'rb') as f:
                        pdf_reader = PyPDF2.PdfReader(f)
                        total_pages = len(pdf_reader.pages)
                        print(f"   Pages: {total_pages}")
                        
                        for i, page in enumerate(pdf_reader.pages, 1):
                            content += page.extract_text() + "\n"
                            if i % 10 == 0:
                                print(f"   Progress: {i}/{total_pages} pages", end='\r')
                        
                        print(f"   Progress: {total_pages}/{total_pages} pages")
                        
                except ImportError:
                    print(f"{Fore.YELLOW}⚠️  PyPDF2 not installed. Install: pip install PyPDF2{Style.RESET_ALL}")
                    return None
            
            # DOCX files
            elif file_path.suffix == '.docx':
                try:
                    import docx
                    doc = docx.Document(file_path)
                    content = "\n".join([para.text for para in doc.paragraphs])
                except ImportError:
                    print(f"{Fore.YELLOW}⚠️  python-docx not installed. Install: pip install python-docx{Style.RESET_ALL}")
                    return None
            
            else:
                print(f"{Fore.RED}❌ Unsupported format: {file_path.suffix}{Style.RESET_ALL}")
                return None
            
            # Success message
            size_kb = len(content) / 1024
            print(f"{Fore.GREEN}✓ Successfully read {len(content):,} characters ({size_kb:.1f} KB){Style.RESET_ALL}\n")
            return content
            
        except Exception as e:
            print(f"{Fore.RED}❌ Error reading file: {str(e)}{Style.RESET_ALL}")
            return None
    
    def generate_from_file(
        self,
        filepath: str,
        max_depth: int = 4,
        identify_relationships: bool = True,
        output_formats: list = None,
        output_dir: str = "."
    ):
        """Generate mind map from a file"""
        if output_formats is None:
            output_formats = ['json', 'markdown', 'mermaid']
        
        # Read file
        content = self.read_file(filepath)
        if not content:
            return
        
        # Generate title
        file_path = Path(filepath)
        title = file_path.stem.replace('_', ' ').replace('-', ' ').title()
        
        # Generate mind map
        mindmap = self.generator.generate(
            content=content,
            title=title,
            max_depth=max_depth,
            identify_relationships=identify_relationships
        )
        
        # Save results
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        base_name = file_path.stem
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # Save with beautiful output
        self._print_section_header("SAVING OUTPUTS", "💾")
        
        saved_files = []
        
        if 'json' in output_formats:
            json_file = output_path / f"{base_name}_mindmap_{timestamp}.json"
            self.generator.save_mindmap(mindmap, str(json_file), format="json")
            saved_files.append(('JSON', json_file))
        
        if 'markdown' in output_formats:
            md_file = output_path / f"{base_name}_mindmap_{timestamp}.md"
            self.generator.save_mindmap(mindmap, str(md_file), format="markdown")
            saved_files.append(('Markdown', md_file))
        
        if 'mermaid' in output_formats:
            mermaid_file = output_path / f"{base_name}_mindmap_{timestamp}.mmd"
            self.generator.save_mindmap(mindmap, str(mermaid_file), format="mermaid")
            saved_files.append(('Mermaid', mermaid_file))
        
        # Display preview
        self._display_mindmap_preview(mindmap)
        
        # Final summary
        print(f"\n{Fore.GREEN}╔{'═'*78}╗")
        print(f"{Fore.GREEN}║{'✅ FILES SAVED SUCCESSFULLY':^78}║")
        print(f"{Fore.GREEN}╚{'═'*78}╝{Style.RESET_ALL}\n")
        
        for format_name, filepath in saved_files:
            print(f"  {Fore.CYAN}▸{Style.RESET_ALL} {format_name:10} → {Fore.BLUE}{filepath.name}{Style.RESET_ALL}")
    
    def _display_mindmap_preview(self, mindmap):
        """Display beautiful preview of mind map"""
        self._print_section_header("MIND MAP PREVIEW", "🔍")
        
        def display_node(node_id: str, indent: int = 0, max_indent: int = 2):
            if indent > max_indent:
                return
            
            node = mindmap.nodes[node_id]
            
            # Visual indicators
            if indent == 0:
                prefix = f"{Fore.GREEN}●"
                connector = ""
            elif indent == 1:
                prefix = f"{Fore.YELLOW}  ├─"
                connector = "  │ "
            else:
                prefix = f"{Fore.BLUE}    ├─"
                connector = "    │ "
            
            # Node display
            print(f"{prefix} {Fore.WHITE}{node.label}{Style.RESET_ALL}")
            
            # Description (first 60 chars)
            if node.description and indent < 2:
                desc = node.description[:60] + "..." if len(node.description) > 60 else node.description
                print(f"{Fore.CYAN}{connector}  {desc}{Style.RESET_ALL}")
            
            # Tags
            if node.tags and indent < 2:
                tags_str = ", ".join(node.tags[:3])
                print(f"{Fore.MAGENTA}{connector}  🏷️  {tags_str}{Style.RESET_ALL}")
            
            # Examples
            if node.examples and indent == 1:
                print(f"{Fore.YELLOW}{connector}  💡 {node.examples[0]}{Style.RESET_ALL}")
            
            # Children (limit for preview)
            children_to_show = node.children[:4]
            for child_id in children_to_show:
                display_node(child_id, indent + 1, max_indent)
            
            if len(node.children) > 4:
                more_count = len(node.children) - 4
                print(f"{Fore.YELLOW}{connector}  ... and {more_count} more subtopic(s){Style.RESET_ALL}")
        
        display_node(mindmap.root_id)
        
        # Statistics box
        total_rels = sum(len(n.related_nodes) for n in mindmap.nodes.values())
        
        print(f"\n{Fore.CYAN}┌{'─'*78}┐")
        print(f"│ {Fore.WHITE}Quick Stats:{' '*66}{Fore.CYAN}│")
        print(f"│ {Fore.GREEN}▸ Nodes: {len(mindmap.nodes):<5} {Fore.YELLOW}▸ Depth: {mindmap.metadata['max_depth']:<5} {Fore.MAGENTA}▸ Relationships: {total_rels:<5}{' '*35}{Fore.CYAN}│")
        print(f"└{'─'*78}┘{Style.RESET_ALL}")
    
    def batch_process(
        self,
        file_pattern: str,
        max_depth: int = 4,
        output_formats: list = None,
        output_dir: str = "./mindmap_output"
    ):
        """Batch process multiple files"""
        import glob
        
        if output_formats is None:
            output_formats = ['json', 'markdown']
        
        files = glob.glob(file_pattern)
        
        if not files:
            print(f"{Fore.RED}❌ No files found matching: {file_pattern}{Style.RESET_ALL}")
            return
        
        self._print_section_header(f"BATCH PROCESSING - {len(files)} Files", "📦")
        
        for i, filepath in enumerate(files, 1):
            print(f"\n{Fore.YELLOW}╔{'═'*78}╗")
            print(f"{Fore.YELLOW}║ [{i}/{len(files)}] Processing: {Path(filepath).name:<62}║")
            print(f"{Fore.YELLOW}╚{'═'*78}╝{Style.RESET_ALL}")
            
            self.generate_from_file(filepath, max_depth, True, output_formats, output_dir)
        
        print(f"\n{Fore.GREEN}╔{'═'*78}╗")
        print(f"{Fore.GREEN}║{'✅ BATCH PROCESSING COMPLETE':^78}║")
        print(f"{Fore.GREEN}╚{'═'*78}╝{Style.RESET_ALL}")
    
    def interactive_mode(self):
        """Run interactive CLI mode with beautiful UI"""
        self._print_section_header("INTERACTIVE MODE", "🎮")
        
        # Input method selection
        print(f"{Fore.YELLOW}Choose your input method:{Style.RESET_ALL}\n")
        print(f"  {Fore.GREEN}1.{Style.RESET_ALL} 📁 Upload a file (TXT, PDF, DOCX, MD)")
        print(f"  {Fore.GREEN}2.{Style.RESET_ALL} ✍️  Paste text directly")
        print(f"  {Fore.GREEN}3.{Style.RESET_ALL} 🚪 Exit\n")
        
        choice = input(f"{Fore.CYAN}➤ Your choice (1-3): {Style.RESET_ALL}").strip()
        
        if choice == "3":
            print(f"\n{Fore.YELLOW}👋 Thanks for using Mind Map Generator!{Style.RESET_ALL}\n")
            return
        
        content = None
        title = "Generated Mind Map"
        
        if choice == "1":
            print()
            filepath = input(f"{Fore.CYAN}➤ Enter file path: {Style.RESET_ALL}").strip()
            content = self.read_file(filepath)
            if content:
                title = Path(filepath).stem.replace('_', ' ').title()
        
        elif choice == "2":
            print(f"\n{Fore.YELLOW}Paste your content below{Style.RESET_ALL}")
            print(f"{Fore.BLUE}(Press Ctrl+D on Unix/Mac or Ctrl+Z on Windows when done){Style.RESET_ALL}\n")
            lines = []
            try:
                while True:
                    line = input()
                    lines.append(line)
            except EOFError:
                content = "\n".join(lines)
            
            if content:
                print()
                title = input(f"{Fore.CYAN}➤ Enter a title: {Style.RESET_ALL}").strip() or title
        
        if not content:
            print(f"\n{Fore.RED}❌ No content provided!{Style.RESET_ALL}")
            return
        
        # Get preferences
        self._print_section_header("CONFIGURATION", "⚙️")
        
        # Max depth
        print(f"{Fore.YELLOW}Maximum hierarchy depth:{Style.RESET_ALL}")
        print(f"  {Fore.BLUE}Recommended: 3-4 levels{Style.RESET_ALL}")
        depth_input = input(f"{Fore.CYAN}➤ Depth (2-6, default 4): {Style.RESET_ALL}").strip()
        try:
            max_depth = int(depth_input) if depth_input else 4
            max_depth = max(2, min(6, max_depth))
        except ValueError:
            max_depth = 4
        
        # Relationships
        print(f"\n{Fore.YELLOW}Identify cross-relationships?{Style.RESET_ALL}")
        print(f"  {Fore.BLUE}(Finds connections between different branches){Style.RESET_ALL}")
        rel_input = input(f"{Fore.CYAN}➤ (y/n, default y): {Style.RESET_ALL}").strip().lower()
        identify_relationships = rel_input != 'n'
        
        # Output formats
        print(f"\n{Fore.YELLOW}Select output formats:{Style.RESET_ALL}")
        print(f"  {Fore.GREEN}1.{Style.RESET_ALL} JSON (structured data)")
        print(f"  {Fore.GREEN}2.{Style.RESET_ALL} Markdown (readable text)")
        print(f"  {Fore.GREEN}3.{Style.RESET_ALL} Mermaid (diagram code)")
        print(f"  {Fore.GREEN}4.{Style.RESET_ALL} All formats")
        
        format_input = input(f"\n{Fore.CYAN}➤ Choice (1-4, default 4): {Style.RESET_ALL}").strip() or "4"
        
        if format_input == "4":
            output_formats = ['json', 'markdown', 'mermaid']
        else:
            format_map = {"1": "json", "2": "markdown", "3": "mermaid"}
            selected = [format_map.get(c.strip(), 'json') for c in format_input.split(',')]
            output_formats = list(set(selected))
        
        # Generate mind map
        mindmap = self.generator.generate(
            content=content,
            title=title,
            max_depth=max_depth,
            identify_relationships=identify_relationships
        )
        
        # Display preview
        self._display_mindmap_preview(mindmap)
        
        # Save files
        self._print_section_header("SAVING FILES", "💾")
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title.replace(' ', '_')
        
        saved_files = []
        
        if 'json' in output_formats:
            json_file = f"{safe_title}_{timestamp}.json"
            self.generator.save_mindmap(mindmap, json_file, format="json")
            saved_files.append(('JSON', json_file))
        
        if 'markdown' in output_formats:
            md_file = f"{safe_title}_{timestamp}.md"
            self.generator.save_mindmap(mindmap, md_file, format="markdown")
            saved_files.append(('Markdown', md_file))
        
        if 'mermaid' in output_formats:
            mermaid_file = f"{safe_title}_{timestamp}.mmd"
            self.generator.save_mindmap(mindmap, mermaid_file, format="mermaid")
            saved_files.append(('Mermaid', mermaid_file))
        
        print(f"\n{Fore.GREEN}╔{'═'*78}╗")
        print(f"{Fore.GREEN}║{'✅ GENERATION COMPLETE':^78}║")
        print(f"{Fore.GREEN}╚{'═'*78}╝{Style.RESET_ALL}\n")
        
        print(f"{Fore.CYAN}Saved files:{Style.RESET_ALL}")
        for format_name, filename in saved_files:
            print(f"  {Fore.GREEN}▸{Style.RESET_ALL} {format_name:10} → {Fore.BLUE}{filename}{Style.RESET_ALL}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="AI-Powered Mind Map Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
{Fore.CYAN}Examples:{Style.RESET_ALL}
  %(prog)s                                    # Interactive mode
  %(prog)s --file notes.txt                   # Generate from file
  %(prog)s --file textbook.pdf --depth 5      # Deep hierarchy
  %(prog)s --batch "lectures/*.txt"           # Batch process
  %(prog)s --file notes.txt --format mermaid  # Specific format
        """
    )
    
    parser.add_argument('--file', '-f', help='Input file path')
    parser.add_argument('--batch', '-b', help='Batch process files (glob pattern)')
    parser.add_argument('--depth', '-d', type=int, default=4, help='Maximum hierarchy depth (default: 4)')
    parser.add_argument(
        '--format',
        nargs='+',
        choices=['json', 'markdown', 'mermaid', 'all'],
        default=['all'],
        help='Output format(s) (default: all)'
    )
    parser.add_argument('--no-relationships', action='store_true', help='Skip relationship identification')
    parser.add_argument('--output', '-o', default='.', help='Output directory')
    
    args = parser.parse_args()
    
    # Process format argument
    if 'all' in args.format:
        output_formats = ['json', 'markdown', 'mermaid']
    else:
        output_formats = args.format
    
    # Initialize app
    app = MindMapApp()
    
    # Handle different modes
    if args.batch:
        app.batch_process(args.batch, args.depth, output_formats, args.output)
    elif args.file:
        app.generate_from_file(
            args.file,
            args.depth,
            not args.no_relationships,
            output_formats,
            args.output
        )
    else:
        app.interactive_mode()


if __name__ == "__main__":
    main()