"""
Main Script for Flashcard Generator with File Upload Support
============================================================

This script provides:
1. File upload support (TXT, PDF, DOCX, MD)
2. Interactive CLI interface
3. Batch processing capabilities
4. Advanced customization options

Dependencies:
    pip install requests colorama python-dotenv PyPDF2 python-docx

Usage:
    python flashcard_main.py
    python flashcard_main.py --file notes.txt --difficulty hard
    python flashcard_main.py --batch folder/*.txt
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Optional
import time

from colorama import Fore, Style, init
from dotenv import load_dotenv

# Import the flashcard generator and API key manager
from flashcard_generator import FlashcardGenerator
from api_key_manager import APIKeyManager

init(autoreset=True)


class FlashcardApp:
    """
    Main application for flashcard generation with file support
    """
    
    def __init__(self):
        """Initialize the application"""
        load_dotenv()
        
        try:
            api_key_manager = APIKeyManager()
            self.generator = FlashcardGenerator(api_key_manager=api_key_manager, verbose=True)
        except ValueError:
            gemini_key = os.getenv("GEMINI_API_KEY")
            if not gemini_key:
                print(f"{Fore.RED}❌ API keys not found!{Style.RESET_ALL}")
                print("\nPlease set environment variables:")
                print("  - GEMINI_API_KEY1 (primary)")
                print("  - GEMINI_API_KEY2 (fallback)")
                print("\nOr set GEMINI_API_KEY for backward compatibility")
                sys.exit(1)
            self.generator = FlashcardGenerator(gemini_api_key=gemini_key, verbose=True)
    
    def read_file(self, filepath: str) -> Optional[str]:
        """
        Read content from various file formats
        
        Args:
            filepath: Path to file
            
        Returns:
            File content as string
        """
        try:
            file_path = Path(filepath)
            
            if not file_path.exists():
                print(f"{Fore.RED}❌ File not found: {filepath}{Style.RESET_ALL}")
                return None
            
            print(f"{Fore.YELLOW}📄 Reading: {filepath}{Style.RESET_ALL}")
            
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
                        for page in pdf_reader.pages:
                            content += page.extract_text() + "\n"
                except ImportError:
                    print(f"{Fore.YELLOW}⚠️ PyPDF2 not installed. Install with: pip install PyPDF2{Style.RESET_ALL}")
                    return None
            
            # DOCX files
            elif file_path.suffix == '.docx':
                try:
                    import docx
                    doc = docx.Document(file_path)
                    content = "\n".join([para.text for para in doc.paragraphs])
                except ImportError:
                    print(f"{Fore.YELLOW}⚠️ python-docx not installed. Install with: pip install python-docx{Style.RESET_ALL}")
                    return None
            
            else:
                print(f"{Fore.RED}❌ Unsupported file format: {file_path.suffix}{Style.RESET_ALL}")
                return None
            
            print(f"{Fore.GREEN}✓ Read {len(content)} characters{Style.RESET_ALL}")
            return content
            
        except Exception as e:
            print(f"{Fore.RED}❌ Error reading file: {str(e)}{Style.RESET_ALL}")
            return None
    
    def generate_from_file(
        self,
        filepath: str,
        difficulty: str = "mixed",
        card_count: str = "auto",
        custom_count: Optional[int] = None,
        output_dir: str = "."
    ):
        """
        Generate flashcards from a file
        
        Args:
            filepath: Path to input file
            difficulty: Difficulty level
            card_count: Card count preference
            custom_count: Custom card count
            output_dir: Output directory
        """
        # Read file
        content = self.read_file(filepath)
        
        if not content:
            return
        
        # Generate title from filename
        file_path = Path(filepath)
        title = file_path.stem.replace('_', ' ').replace('-', ' ').title()
        
        # Generate flashcards
        flashcard_set = self.generator.generate(
            content=content,
            title=title,
            difficulty=difficulty,
            card_count=card_count,
            custom_count=custom_count
        )
        
        # Save results
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        base_name = file_path.stem
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        json_file = output_path / f"{base_name}_flashcards_{timestamp}.json"
        md_file = output_path / f"{base_name}_flashcards_{timestamp}.md"
        csv_file = output_path / f"{base_name}_flashcards_{timestamp}.csv"
        
        self.generator.save_flashcards(flashcard_set, str(json_file), format="json")
        self.generator.save_flashcards(flashcard_set, str(md_file), format="markdown")
        self.generator.save_flashcards(flashcard_set, str(csv_file), format="csv")
        
        # Print summary
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}GENERATION SUMMARY")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
        print(f"{Fore.GREEN}Total Cards: {len(flashcard_set.cards)}{Style.RESET_ALL}")
        print(f"Easy: {flashcard_set.metadata['difficulty_counts']['easy']}")
        print(f"Medium: {flashcard_set.metadata['difficulty_counts']['medium']}")
        print(f"Hard: {flashcard_set.metadata['difficulty_counts']['hard']}")
        print(f"\n{Fore.GREEN}Output Files:{Style.RESET_ALL}")
        print(f"  - {json_file}")
        print(f"  - {md_file}")
        print(f"  - {csv_file}")
    
    def batch_process(
        self,
        file_pattern: str,
        difficulty: str = "mixed",
        card_count: str = "auto",
        output_dir: str = "./flashcard_output"
    ):
        """
        Batch process multiple files
        
        Args:
            file_pattern: File pattern (e.g., "*.txt")
            difficulty: Difficulty level
            card_count: Card count preference
            output_dir: Output directory
        """
        import glob
        
        files = glob.glob(file_pattern)
        
        if not files:
            print(f"{Fore.RED}❌ No files found matching: {file_pattern}{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}BATCH PROCESSING: {len(files)} files")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
        
        for i, filepath in enumerate(files, 1):
            print(f"\n{Fore.YELLOW}[{i}/{len(files)}] Processing: {filepath}{Style.RESET_ALL}")
            self.generate_from_file(filepath, difficulty, card_count, None, output_dir)
        
        print(f"\n{Fore.GREEN}✅ Batch processing complete!{Style.RESET_ALL}")
    
    def interactive_mode(self):
        """Run interactive CLI mode"""
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}INTERACTIVE FLASHCARD GENERATOR")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
        
        # Get input method
        print("Choose input method:")
        print("1. Upload file")
        print("2. Paste text directly")
        print("3. Exit")
        
        choice = input(f"\n{Fore.YELLOW}Enter choice (1-3): {Style.RESET_ALL}").strip()
        
        if choice == "3":
            print("Goodbye!")
            return
        
        content = None
        title = "Generated Flashcards"
        
        if choice == "1":
            filepath = input(f"{Fore.YELLOW}Enter file path: {Style.RESET_ALL}").strip()
            content = self.read_file(filepath)
            if content:
                title = Path(filepath).stem.replace('_', ' ').title()
        
        elif choice == "2":
            print(f"\n{Fore.YELLOW}Paste your content (press Ctrl+D or Ctrl+Z when done):{Style.RESET_ALL}")
            lines = []
            try:
                while True:
                    line = input()
                    lines.append(line)
            except EOFError:
                content = "\n".join(lines)
            
            if content:
                title = input(f"\n{Fore.YELLOW}Enter a title for this flashcard set: {Style.RESET_ALL}").strip() or title
        
        if not content:
            print(f"{Fore.RED}No content provided!{Style.RESET_ALL}")
            return
        
        # Get preferences
        print(f"\n{Fore.CYAN}Flashcard Preferences:{Style.RESET_ALL}")
        
        print("\nDifficulty level:")
        print("1. Easy")
        print("2. Medium")
        print("3. Hard")
        print("4. Mixed (recommended)")
        
        diff_choice = input(f"{Fore.YELLOW}Choice (1-4, default 4): {Style.RESET_ALL}").strip() or "4"
        difficulty_map = {"1": "easy", "2": "medium", "3": "hard", "4": "mixed"}
        difficulty = difficulty_map.get(diff_choice, "mixed")
        
        print("\nNumber of cards:")
        print("1. Auto (AI-determined)")
        print("2. Few (10-20)")
        print("3. Normal (20-40)")
        print("4. Many (40-80)")
        print("5. Custom amount")
        
        count_choice = input(f"{Fore.YELLOW}Choice (1-5, default 1): {Style.RESET_ALL}").strip() or "1"
        count_map = {"1": "auto", "2": "few", "3": "normal", "4": "many"}
        card_count = count_map.get(count_choice, "auto")
        custom_count = None
        
        if count_choice == "5":
            custom_input = input(f"{Fore.YELLOW}Enter number of cards: {Style.RESET_ALL}").strip()
            try:
                custom_count = int(custom_input)
                card_count = "auto"
            except ValueError:
                print(f"{Fore.YELLOW}Invalid number, using auto{Style.RESET_ALL}")
        
        # Generate flashcards
        print(f"\n{Fore.CYAN}Generating flashcards...{Style.RESET_ALL}\n")
        
        flashcard_set = self.generator.generate(
            content=content,
            title=title,
            difficulty=difficulty,
            card_count=card_count,
            custom_count=custom_count
        )
        
        # Save files
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title.replace(' ', '_')
        
        json_file = f"{safe_title}_{timestamp}.json"
        md_file = f"{safe_title}_{timestamp}.md"
        
        self.generator.save_flashcards(flashcard_set, json_file, format="json")
        self.generator.save_flashcards(flashcard_set, md_file, format="markdown")
        
        # Display sample
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}SAMPLE FLASHCARDS (First 3)")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
        
        for i, card in enumerate(flashcard_set.cards[:3], 1):
            print(f"{Fore.GREEN}Card {i} [{card.difficulty.upper()}]{Style.RESET_ALL}")
            print(f"Q: {card.front}")
            print(f"A: {card.back}")
            print()
        
        print(f"\n{Fore.GREEN}✅ Generated {len(flashcard_set.cards)} flashcards!{Style.RESET_ALL}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="AI-Powered Flashcard Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Interactive mode
  %(prog)s --file notes.txt                   # Generate from file
  %(prog)s --file notes.txt --difficulty hard # Generate hard cards
  %(prog)s --batch "lectures/*.txt"           # Batch process
  %(prog)s --file notes.txt --count 50        # Generate 50 cards
        """
    )
    
    parser.add_argument('--file', '-f', help='Input file path')
    parser.add_argument('--batch', '-b', help='Batch process files (glob pattern)')
    parser.add_argument(
        '--difficulty', '-d',
        choices=['easy', 'medium', 'hard', 'mixed'],
        default='mixed',
        help='Difficulty level (default: mixed)'
    )
    parser.add_argument(
        '--card-count', '-c',
        choices=['auto', 'few', 'normal', 'many'],
        default='auto',
        help='Number of cards (default: auto)'
    )
    parser.add_argument('--count', type=int, help='Custom card count')
    parser.add_argument('--output', '-o', default='.', help='Output directory')
    
    args = parser.parse_args()
    
    # Initialize app
    app = FlashcardApp()
    
    # Handle different modes
    if args.batch:
        app.batch_process(args.batch, args.difficulty, args.card_count, args.output)
    elif args.file:
        app.generate_from_file(args.file, args.difficulty, args.card_count, args.count, args.output)
    else:
        app.interactive_mode()


if __name__ == "__main__":
    main()