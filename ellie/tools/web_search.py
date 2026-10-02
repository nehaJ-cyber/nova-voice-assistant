"""Web search and querying tools for Ellie."""
import logging
import webbrowser
import urllib.parse
import urllib.request
import json
from ellie.tools import register

logger = logging.getLogger(__name__)

def web_search(step: dict) -> str:
    """Perform a generic web search in the browser."""
    try:
        query = step.get('query')
        if not query:
            return "Error: No query provided."
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://www.google.com/search?q={encoded_query}"
        webbrowser.open(url)
        return f"Searching for {query}"
    except Exception as e:
        logger.error(f"Error in web search: {e}")
        return f"Error in web search: {e}"

def wikipedia_summary(step: dict) -> str:
    """Fetch Wikipedia summary via REST API."""
    try:
        title = step.get('title')
        if not title:
            return "Error: No title provided."
        
        encoded_title = urllib.parse.quote(title.replace(' ', '_'))
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_title}"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'EllieAssistant/1.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            extract = data.get('extract', '')
            if not extract:
                return "No summary found."
            
            # Return first 3 sentences
            sentences = [s for s in extract.split('. ') if s]
            summary = '. '.join(sentences[:3])
            if not summary.endswith('.'):
                summary += '.'
            return summary
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return f"Wikipedia page not found for '{title}'."
        return f"HTTP error fetching Wikipedia: {e}"
    except Exception as e:
        logger.error(f"Error in wikipedia summary: {e}")
        return f"Error in wikipedia summary: {e}"

def answer_question(step: dict) -> str:
    """Pass-through for the executor LLM's generated answer."""
    text = step.get('text', '')
    return text if text else "Error: No text provided."

# Register web search tools
register('web_search', web_search)
register('wikipedia_summary', wikipedia_summary)
register('answer_question', answer_question)
