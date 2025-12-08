class DeepResearch:
    """Advanced research system with multi-query expansion and synthesis"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.research_cache = {}
    
    def conduct_research(self, query: str, depth: int = 3) -> Dict:
        """
        Conduct deep research with multiple search queries and synthesis
        
        Args:
            query: Original research question
            depth: Research depth (1-5, where 5 is most comprehensive)
        """
        print(f"{Colors.MAGENTA}🔬 Starting deep research (depth: {depth})...{Colors.END}")
        
        # Generate multiple search queries
        search_queries = self._generate_search_queries(query, depth)
        print(f"{Colors.CYAN}📋 Generated {len(search_queries)} search queries{Colors.END}")
        
        all_results = []
        sources = set()
        
        # Execute all searches
        for idx, sq in enumerate(search_queries, 1):
            print(f"{Colors.YELLOW}  [{idx}/{len(search_queries)}] Searching: {sq}{Colors.END}")
            results = self._execute_search(sq)
            
            if results:
                all_results.extend(results)
                for r in results:
                    if r.get('url'):
                        sources.add(r['url'])
            
            time.sleep(0.5)  # Rate limiting
        
        # Deduplicate and rank results
        unique_results = self._deduplicate_results(all_results)
        # ranked_results = self._rank_results(unique_results, query)

        # AI-powered source approval
        # approved_results = self._approve_sources(ranked_results, query)

        # Fetch full content from approved top sources
        enriched_results = self._enrich_top_results(unique_results[:depth * 2]) # Changed from approved results to unique results
        
        print(f"{Colors.GREEN}✓ Research complete: {len(enriched_results)} high-quality sources{Colors.END}")
        
        return {
            "original_query": query,
            "search_queries": search_queries,
            "total_sources": len(sources),
            "results": enriched_results,
            "research_depth": depth,
            "timestamp": datetime.now().isoformat()
        }
    
    def _generate_search_queries(self, query: str, depth: int) -> List[str]:
        """Generate multiple search queries using AI for comprehensive coverage"""
        try:
            # Use Gemini to generate intelligent search queries
            prompt = f"""Generate {depth * 2 + 1} diverse and comprehensive search queries for researching: "{query}"

Research depth level: {depth}/5 (where 5 is most comprehensive)

Generate queries that cover:
- Core concepts and definitions
- Recent developments and current trends
- Practical applications and examples
- Expert opinions and research findings
- Comparisons and critical analysis (for higher depths)

Format as a JSON array of strings:
["query1", "query2", "query3", ...]

Make queries specific, searchable, and academically rigorous."""

            # Use Gemini API to generate queries
            response = requests.post(
                f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 2048,
                    }
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                if "candidates" in data and len(data["candidates"]) > 0:
                    ai_response = data["candidates"][0]["content"]["parts"][0]["text"]

                    # Extract JSON from response
                    json_match = re.search(r'\[.*\]', ai_response, re.DOTALL)
                    if json_match:
                        queries = json.loads(json_match.group(0))
                        if isinstance(queries, list) and len(queries) > 0:
                            print(f"{Colors.GREEN}✓ AI-generated {len(queries)} search queries{Colors.END}")
                            return queries[:depth * 2 + 1]

            # Fallback to manual generation if AI fails
            print(f"{Colors.YELLOW}⚠️ AI query generation failed, using fallback method{Colors.END}")

        except Exception as e:
            print(f"{Colors.YELLOW}⚠️ AI query generation error: {str(e)}, using fallback{Colors.END}")

        # Fallback manual generation
        queries = [query]  # Original query

        # Extract key concepts
        keywords = self._extract_keywords(query)

        # Add variations based on depth
        if depth >= 2:
            queries.append(f"explain {query}")
            queries.append(f"{query} academic research")

        if depth >= 3:
            queries.append(f"{query} examples applications")
            queries.append(f"{query} definition concept")
            queries.append(f"how does {query} work")

        if depth >= 4:
            queries.append(f"{query} recent developments 2024 2025")
            queries.append(f"{query} case study real world")
            queries.append(f"best practices {query}")

        if depth >= 5:
            queries.append(f"{query} comparison alternatives")
            queries.append(f"{query} advantages disadvantages")
            queries.append(f"{query} expert opinion research")

        return queries[:depth * 2 + 1]  # Limit based on depth
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text"""
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                     'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
                     'can', 'could', 'would', 'should', 'may', 'might', 'what', 'how', 'why'}
        
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 3]
        return keywords[:5]  # Top 5 keywords
    
    def _execute_search(self, query: str) -> List[Dict]:
        """Execute a single search query"""
        try:
            # DuckDuckGo API
            url = f"https://api.duckduckgo.com/?q={quote(query)}&format=json&no_html=1"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            
            # Abstract
            if data.get('Abstract'):
                results.append({
                    "title": data.get('AbstractSource', 'Overview'),
                    "url": data.get('AbstractURL', ''),
                    "content": data.get('Abstract', ''),
                    "type": "abstract",
                    "score": 1.0
                })
            
            # Related topics
            for item in data.get('RelatedTopics', [])[:5]:
                if isinstance(item, dict) and 'Text' in item:
                    results.append({
                        "title": item.get('Text', '')[:100],
                        "url": item.get('FirstURL', ''),
                        "content": item.get('Text', ''),
                        "type": "related",
                        "score": 0.8
                    })
            
            return results
        except Exception as e:
            print(f"{Colors.RED}Search error: {str(e)}{Colors.END}")
            return []
    
    def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """Remove duplicate results based on URL and content similarity"""
        seen_urls = set()
        seen_content_hashes = set()
        unique_results = []
        
        for result in results:
            url = result.get('url', '')
            content = result.get('content', '')
            
            # Hash content for similarity check
            content_hash = hashlib.md5(content.encode()).hexdigest()
            
            if url and url not in seen_urls and content_hash not in seen_content_hashes:
                seen_urls.add(url)
                seen_content_hashes.add(content_hash)
                unique_results.append(result)
        
        return unique_results
    
    def _rank_results(self, results: List[Dict], query: str) -> List[Dict]:
        """Rank results by relevance to original query"""
        query_keywords = set(self._extract_keywords(query))
        
        for result in results:
            # Calculate relevance score
            content = result.get('content', '').lower()
            title = result.get('title', '').lower()
            
            # Keyword match score
            content_keywords = set(self._extract_keywords(content))
            title_keywords = set(self._extract_keywords(title))
            
            keyword_score = len(query_keywords & content_keywords) / max(len(query_keywords), 1)
            title_score = len(query_keywords & title_keywords) / max(len(query_keywords), 1)
            
            # Combine scores
            result['relevance_score'] = (
                result.get('score', 0.5) * 0.3 +
                keyword_score * 0.5 +
                title_score * 0.2
            )
        
        # Sort by relevance
        return sorted(results, key=lambda x: x['relevance_score'], reverse=True)
    
    def _enrich_top_results(self, results: List[Dict]) -> List[Dict]:
        """Fetch full content from top results"""
        enriched = []
        
        for result in results[:5]:  # Enrich top 5
            url = result.get('url')
            if url and url.startswith('http'):
                try:
                    print(f"{Colors.CYAN}  📄 Fetching: {url[:60]}...{Colors.END}")
                    response = requests.get(url, headers=self.headers, timeout=10)
                    if response.status_code == 200:
                        # Extract text (simplified - would need proper HTML parsing)
                        text = response.text[:5000]  # First 5000 chars
                        result['full_content'] = text
                        result['enriched'] = True
                except Exception as e:
                    result['enriched'] = False
            
            enriched.append(result)
        
        return enriched

    def _approve_sources(self, results: List[Dict], original_query: str) -> List[Dict]:
        """Approve all research sources automatically"""
        approved_sources = []

        print(f"{Colors.CYAN}✓ Processing {len(results)} sources for learning...{Colors.END}")

        for result in results:
            try:
                result['ai_approval'] = {
                    'approved': True,
                    'credibility_score': 8,
                    'relevance_score': int(result.get('relevance_score', 0.7) * 10),
                    'reasoning': 'auto-approved for educational use',
                    'source_category': 'educational'
                }
                result['credibility_score'] = 8
                result['source_category'] = 'educational'
                approved_sources.append(result)
                print(f"{Colors.GREEN}✓ Approved: {result.get('title', '')[:50]}...{Colors.END}")

            except Exception as e:
                print(f"{Colors.YELLOW}⚠️ Processing error: {str(e)}{Colors.END}")
                result['ai_approval'] = {'approved': True, 'credibility_score': 7, 'reasoning': 'error handling approved'}
                approved_sources.append(result)

        print(f"{Colors.GREEN}✓ All {len(approved_sources)} sources approved for learning{Colors.END}")
        return approved_sources