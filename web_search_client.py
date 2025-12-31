# from colorama import Fore, Style, init
from tavily import TavilyClient
import json

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

class WebSearchClient:
    """A reusable class for performing web searches using the Tavily API."""

    def __init__(self, api_key: str):
        """
        Initialize the WebSearchClient with the Tavily API key.

        Args:
            api_key (str): Tavily API key for authentication.
        """
        # init(autoreset=True)  # Initialize colorama for colored output
        self.tavily_client = TavilyClient(api_key=api_key)

    def search(self, query: str, include_raw_content: bool = True, include_answer: bool = True, search_depth: str = "advanced", max_results: int = 10) -> dict:
        """
        Perform a web search using the Tavily API.

        Args:
            query (str): The search query.
            include_raw_content (bool): Whether to include raw content in the results.
            include_answer (bool): Whether to include an AI-generated answer.
            search_depth (str): The search depth ("basic", "intermediate", "advanced").
            max_results (int): Maximum number of results to return.

        Returns:
            dict: The full response from the Tavily API.
        """
        print(Fore.YELLOW + f"🔍 Searching for: {query}" + Style.RESET_ALL)
        try:
            response = self.tavily_client.search(
                query=query,
                include_raw_content=include_raw_content,
                include_answer=include_answer,
                search_depth=search_depth,
                max_results=max_results
            )
            
            if response and response.get('answer'):
                print(Fore.GREEN + f"✓ Found AI answer from Tavily" + Style.RESET_ALL)
            
            return response
        except Exception as e:
            print(Fore.RED + f"❌ Search error: {str(e)}" + Style.RESET_ALL)
            return {}

    def process_results(self, response: dict) -> None:
        """
        Process and display the search results.

        Args:
            response (dict): The response from the Tavily API.
        """
        print(Fore.YELLOW + "=" * 80)
        print(f"QUERY: {response.get('query', 'N/A')}")
        print("=" * 80 + Style.RESET_ALL)

        # Display AI-generated answer if available
        if response.get('answer'):
            print(Fore.GREEN + f"\nANSWER:\n{response['answer']}" + Style.RESET_ALL)

        print(Fore.CYAN + f"\n{'=' * 80}")
        print(f"RESULTS ({len(response.get('results', []))} sources)")
        print("=" * 80 + Style.RESET_ALL)

        # Process each result
        for i, result in enumerate(response.get('results', []), 1):
            print(Fore.MAGENTA + f"\n[{i}] {result.get('title', 'No Title')}")
            print(Fore.BLUE + f"URL: {result.get('url', 'N/A')}")
            print(f"Score: {result.get('score', 'N/A')}" + Style.RESET_ALL)

            # Try to get the most complete content available
            content = result.get('raw_content') or result.get('content', 'N/A')

            # Ensure content is fully displayed (no truncation)
            if content != 'N/A':
                if len(content) > 0 and not content.endswith(('.', '!', '?', '"', "'")):
                    print(Fore.YELLOW + "[Note: Content may be truncated by the API]" + Style.RESET_ALL)

                print(Fore.WHITE + f"Content:\n{content}" + Style.RESET_ALL)
                print(Fore.CYAN + f"Content length: {len(content)} characters" + Style.RESET_ALL)
            else:
                print(Fore.RED + "No content available" + Style.RESET_ALL)

        # Display follow-up questions if available
        if response.get('follow_up_questions'):
            print(Fore.YELLOW + f"\n{'=' * 80}")
            print("FOLLOW-UP QUESTIONS:")
            print("=" * 80 + Style.RESET_ALL)
            for q in response['follow_up_questions']:
                print(Fore.CYAN + f"• {q}" + Style.RESET_ALL)

    def save_response(self, response: dict, filename: str = "search_results.json") -> None:
        """
        Save the full response to a JSON file.

        Args:
            response (dict): The response from the Tavily API.
            filename (str): The name of the file to save the response to.
        """
        print(Fore.YELLOW + f"\n{'=' * 80}")
        print(f"Saving full response to '{filename}' for inspection...")
        print("=" * 80 + Style.RESET_ALL)

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(response, f, indent=2, ensure_ascii=False)
            print(Fore.GREEN + f"✓ Full response saved to {filename}" + Style.RESET_ALL)
        except Exception as e:
            print(Fore.RED + f"❌ Error saving response: {str(e)}" + Style.RESET_ALL)