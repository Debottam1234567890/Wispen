"""
Advanced Research Agent using Tavily Search & Gemini REST API
==============================================================

A comprehensive research agent that:
1. Uses Tavily for web search and content extraction
2. Leverages Google's Gemini through REST API (same as main file)
3. Handles long context intelligently
4. Generates detailed, well-structured reports

Dependencies:
    pip install tavily-python colorama python-dotenv requests

Usage:
    from research_agent import ResearchAgent
    
    agent = ResearchAgent(
        tavily_api_key="your_tavily_key",
        gemini_api_key="your_gemini_key"
    )
    
    report = agent.research(
        query="Modern History of India and implications today",
        max_sources=5
    )
    print(report)

Direct execution:
    python research_agent.py
"""

import os
import json
import requests
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import time

from tavily import TavilyClient
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# Gemini API Configuration
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


@dataclass
class ResearchSource:
    """Represents a single research source"""
    url: str
    title: str
    content: str
    raw_content: str
    score: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ResearchReport:
    """Represents the final research report"""
    query: str
    executive_summary: str
    detailed_analysis: str
    key_findings: List[str]
    sources: List[ResearchSource]
    metadata: Dict[str, Any]
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_markdown(self) -> str:
        """Convert report to markdown format"""
        md = f"""# Research Report: {self.query}

*Generated: {self.generated_at}*

## Executive Summary

{self.executive_summary}

## Key Findings

"""
        for i, finding in enumerate(self.key_findings, 1):
            md += f"{i}. {finding}\n"
        
        md += f"\n## Detailed Analysis\n\n{self.detailed_analysis}\n"
        
        md += "\n## Sources\n\n"
        for i, source in enumerate(self.sources, 1):
            md += f"{i}. [{source.title}]({source.url})\n   - Relevance Score: {source.score:.2f}\n"
        
        return md


class ResearchAgent:
    """
    Advanced Research Agent using Tavily and Gemini REST API
    """
    
    def __init__(
        self,
        tavily_api_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        model_name: str = "gemini-2.0-flash",
        max_tokens_per_chunk: int = 30000,
        verbose: bool = True
    ):
        """
        Initialize the Research Agent
        
        Args:
            tavily_api_key: Tavily API key (or set TAVILY_API_KEY env var)
            gemini_api_key: Gemini API key (or set GEMINI_API_KEY env var)
            model_name: Gemini model to use
            max_tokens_per_chunk: Maximum tokens per content chunk
            verbose: Enable detailed logging
        """
        self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY")
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        
        if not self.tavily_api_key:
            raise ValueError("Tavily API key required. Set TAVILY_API_KEY or pass tavily_api_key")
        if not self.gemini_api_key:
            raise ValueError("Gemini API key required. Set GEMINI_API_KEY or pass gemini_api_key")
        
        self.tavily_client = TavilyClient(api_key=self.tavily_api_key)
        self.model_name = model_name
        self.max_tokens_per_chunk = max_tokens_per_chunk
        self.verbose = verbose
        
        self._log(f"✓ Research Agent initialized with {model_name}", Fore.GREEN)
    
    def _log(self, message: str, color=Fore.YELLOW):
        """Log message if verbose is enabled"""
        if self.verbose:
            print(f"{color}{message}{Style.RESET_ALL}")
    
    def search_web(
        self,
        query: str,
        max_results: int = 10,
        search_depth: str = "advanced",
        include_raw_content: bool = True
    ) -> List[ResearchSource]:
        """
        Search the web using Tavily
        
        Args:
            query: Search query
            max_results: Maximum number of results
            search_depth: Search depth (basic/advanced)
            include_raw_content: Include raw content
            
        Returns:
            List of ResearchSource objects
        """
        self._log(f"\n🔍 Searching: {query}")
        
        try:
            response = self.tavily_client.search(
                query=query,
                max_results=max_results,
                search_depth=search_depth,
                include_raw_content=include_raw_content,
                include_answer=True
            )
            
            sources = []
            for result in response.get('results', []):
                source = ResearchSource(
                    url=result.get('url', ''),
                    title=result.get('title', 'No Title'),
                    content=result.get('content', ''),
                    raw_content=result.get('raw_content', ''),
                    score=result.get('score', 0.0)
                )
                sources.append(source)
            
            self._log(f"✓ Found {len(sources)} sources", Fore.GREEN)
            return sources
            
        except Exception as e:
            self._log(f"❌ Search error: {str(e)}", Fore.RED)
            return []
    
    def extract_content(self, url: str) -> Optional[str]:
        """
        Extract full content from a URL using Tavily
        
        Args:
            url: URL to extract content from
            
        Returns:
            Extracted content or None
        """
        try:
            self._log(f"📄 Extracting: {url}")
            response = self.tavily_client.extract(urls=[url])
            
            if response and 'results' in response and len(response['results']) > 0:
                content = response['results'][0].get('raw_content', '')
                self._log(f"✓ Extracted {len(content)} characters", Fore.GREEN)
                return content
            
            return None
            
        except Exception as e:
            self._log(f"❌ Extraction error: {str(e)}", Fore.RED)
            return None
    
    def _chunk_content(self, content: str, max_chars: int = 100000) -> List[str]:
        """
        Split content into manageable chunks
        
        Args:
            content: Content to chunk
            max_chars: Maximum characters per chunk
            
        Returns:
            List of content chunks
        """
        if len(content) <= max_chars:
            return [content]
        
        chunks = []
        current_chunk = ""
        
        # Split by paragraphs
        paragraphs = content.split('\n\n')
        
        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= max_chars:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        self._log(f"📊 Split content into {len(chunks)} chunks")
        return chunks
    
    def _analyze_with_gemini(
        self,
        prompt: str,
        context: str,
        temperature: float = 0.7
    ) -> str:
        """
        Analyze content using Gemini REST API (same approach as main file)
        
        Args:
            prompt: Analysis prompt
            context: Context/content to analyze
            temperature: Generation temperature
            
        Returns:
            Analysis result
        """
        try:
            # Combine prompt and context
            full_prompt = f"""{prompt}

CONTEXT AND SOURCES:
{context}

Please provide a comprehensive, well-structured analysis."""
            
            # Make REST API request (same as main file)
            response = requests.post(
                f"{GEMINI_API_URL}?key={self.gemini_api_key}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": full_prompt}]}],
                    "generationConfig": {
                        "temperature": temperature,
                        "topK": 40,
                        "topP": 0.95,
                        "maxOutputTokens": 8192,
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
            
        except requests.exceptions.HTTPError as e:
            self._log(f"❌ Gemini HTTP error: {e.response.status_code}", Fore.RED)
            return f"Analysis error: HTTP {e.response.status_code}"
        except Exception as e:
            self._log(f"❌ Gemini API error: {str(e)}", Fore.RED)
            return f"Analysis error: {str(e)}"
    
    def research(
        self,
        query: str,
        max_sources: int = 5,
        extract_full_content: bool = True,
        search_depth: str = "advanced"
    ) -> ResearchReport:
        """
        Conduct comprehensive research on a query
        
        Args:
            query: Research query
            max_sources: Maximum sources to analyze
            extract_full_content: Extract full content from sources
            search_depth: Tavily search depth
            
        Returns:
            ResearchReport object
        """
        self._log(f"\n{'='*80}", Fore.CYAN)
        self._log(f"🔬 Starting Research: {query}", Fore.CYAN)
        self._log(f"{'='*80}", Fore.CYAN)
        
        start_time = time.time()
        
        # Step 1: Search for sources
        sources = self.search_web(
            query=query,
            max_results=max_sources,
            search_depth=search_depth
        )
        
        if not sources:
            self._log("❌ No sources found", Fore.RED)
            return self._create_empty_report(query)
        
        # Step 2: Extract full content if requested
        if extract_full_content:
            self._log(f"\n📚 Extracting full content from {len(sources)} sources...")
            for source in sources[:3]:  # Extract from top 3 sources
                full_content = self.extract_content(source.url)
                if full_content:
                    source.raw_content = full_content
        
        # Step 3: Prepare context for analysis
        context = self._prepare_context(sources)
        
        # Step 4: Generate executive summary
        self._log("\n📝 Generating executive summary...", Fore.CYAN)
        summary_prompt = f"""Based on the following research sources about "{query}", 
provide a concise executive summary (3-4 paragraphs) that captures the most important 
information and key insights."""
        
        executive_summary = self._analyze_with_gemini(
            summary_prompt,
            context,
            temperature=0.7
        )
        
        # Step 5: Extract key findings
        self._log("🔑 Extracting key findings...", Fore.CYAN)
        findings_prompt = f"""Based on the research about "{query}", identify and list 
the 5-8 most important key findings. Each finding should be a clear, concise statement.
Format as a numbered list."""
        
        findings_text = self._analyze_with_gemini(
            findings_prompt,
            context,
            temperature=0.6
        )
        
        key_findings = self._parse_key_findings(findings_text)
        
        # Step 6: Generate detailed analysis
        self._log("📊 Generating detailed analysis...", Fore.CYAN)
        analysis_prompt = f"""Provide a comprehensive, detailed analysis of "{query}" 
based on the research sources. Structure your analysis with:

1. Historical Context and Background
2. Current State and Recent Developments
3. Key Trends and Patterns
4. Implications and Significance
5. Future Outlook and Considerations

Use specific evidence and examples from the sources. Cite sources where appropriate."""
        
        detailed_analysis = self._analyze_with_gemini(
            analysis_prompt,
            context,
            temperature=0.7
        )
        
        # Step 7: Create report
        elapsed_time = time.time() - start_time
        
        report = ResearchReport(
            query=query,
            executive_summary=executive_summary,
            detailed_analysis=detailed_analysis,
            key_findings=key_findings,
            sources=sources,
            metadata={
                'num_sources': len(sources),
                'search_depth': search_depth,
                'extraction_enabled': extract_full_content,
                'processing_time_seconds': elapsed_time,
                'api_method': 'REST API'
            }
        )
        
        self._log(f"\n{'='*80}", Fore.GREEN)
        self._log(f"✅ Research completed in {elapsed_time:.2f} seconds", Fore.GREEN)
        self._log(f"{'='*80}\n", Fore.GREEN)
        
        return report
    
    def _prepare_context(self, sources: List[ResearchSource]) -> str:
        """Prepare context from sources for Gemini analysis"""
        context_parts = []
        
        for i, source in enumerate(sources, 1):
            content = source.raw_content if source.raw_content else source.content
            
            # Limit content length
            if len(content) > 10000:
                content = content[:10000] + "..."
            
            context_parts.append(f"""
SOURCE {i}: {source.title}
URL: {source.url}
Relevance Score: {source.score:.2f}

{content}

---
""")
        
        return "\n".join(context_parts)
    
    def _parse_key_findings(self, findings_text: str) -> List[str]:
        """Parse key findings from Gemini response"""
        findings = []
        lines = findings_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove numbering
            for prefix in ['1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '-', '*', '•']:
                if line.startswith(prefix):
                    line = line[len(prefix):].strip()
                    break
            
            if line and len(line) > 20:  # Valid finding
                findings.append(line)
        
        return findings[:8]  # Return max 8 findings
    
    def _create_empty_report(self, query: str) -> ResearchReport:
        """Create empty report when no sources found"""
        return ResearchReport(
            query=query,
            executive_summary="No research sources found for this query.",
            detailed_analysis="Unable to generate analysis due to lack of sources.",
            key_findings=[],
            sources=[],
            metadata={'error': 'No sources found'}
        )
    
    def save_report(self, report: ResearchReport, filepath: str, format: str = 'markdown'):
        """
        Save report to file
        
        Args:
            report: ResearchReport to save
            filepath: Output file path
            format: Output format (markdown/json)
        """
        try:
            if format == 'markdown':
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(report.to_markdown())
            elif format == 'json':
                with open(filepath, 'w', encoding='utf-8') as f:
                    # Convert to dict
                    report_dict = {
                        'query': report.query,
                        'executive_summary': report.executive_summary,
                        'detailed_analysis': report.detailed_analysis,
                        'key_findings': report.key_findings,
                        'sources': [
                            {
                                'url': s.url,
                                'title': s.title,
                                'score': s.score
                            }
                            for s in report.sources
                        ],
                        'metadata': report.metadata,
                        'generated_at': report.generated_at
                    }
                    json.dump(report_dict, f, indent=2, ensure_ascii=False)
            
            self._log(f"✓ Report saved to {filepath}", Fore.GREEN)
            
        except Exception as e:
            self._log(f"❌ Error saving report: {str(e)}", Fore.RED)


# Direct execution example
if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    print(f"{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}Advanced Research Agent - Demo Mode (REST API)")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    # Check for API keys
    tavily_key = os.getenv("TAVILY_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    if not tavily_key or not gemini_key:
        print(f"{Fore.RED}❌ Missing API keys!{Style.RESET_ALL}")
        print("\nPlease set the following environment variables:")
        print("  - TAVILY_API_KEY")
        print("  - GEMINI_API_KEY")
        print("\nOr create a .env file with these keys.")
        sys.exit(1)
    
    # Initialize agent
    agent = ResearchAgent(verbose=True)
    
    # Example research query
    query = "Modern History of India and implications that are prevalent today"
    
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        print(f"{Fore.YELLOW}Custom query: {query}{Style.RESET_ALL}\n")
    else:
        print(f"{Fore.YELLOW}Default query: {query}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}(Tip: Pass your own query as command line arguments){Style.RESET_ALL}\n")
    
    # Conduct research
    report = agent.research(
        query=query,
        max_sources=5,
        extract_full_content=True,
        search_depth="advanced"
    )
    
    # Display report
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}RESEARCH REPORT")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.GREEN}Query:{Style.RESET_ALL} {report.query}\n")
    
    print(f"{Fore.GREEN}EXECUTIVE SUMMARY:{Style.RESET_ALL}")
    print(report.executive_summary)
    
    print(f"\n{Fore.GREEN}KEY FINDINGS:{Style.RESET_ALL}")
    for i, finding in enumerate(report.key_findings, 1):
        print(f"{i}. {finding}")
    
    print(f"\n{Fore.GREEN}SOURCES ({len(report.sources)}):{Style.RESET_ALL}")
    for i, source in enumerate(report.sources, 1):
        print(f"{i}. {source.title}")
        print(f"   {Fore.BLUE}{source.url}{Style.RESET_ALL}")
        print(f"   Score: {source.score:.2f}\n")
    
    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    markdown_file = f"research_report_{timestamp}.md"
    json_file = f"research_report_{timestamp}.json"
    
    agent.save_report(report, markdown_file, format='markdown')
    agent.save_report(report, json_file, format='json')
    
    print(f"\n{Fore.GREEN}✅ Reports saved:{Style.RESET_ALL}")
    print(f"  - {markdown_file}")
    print(f"  - {json_file}")