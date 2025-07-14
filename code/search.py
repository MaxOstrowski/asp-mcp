"""
Performs a Google search for the given query, retrieves the top 3 results,
fetches each page, and returns a list of dictionaries containing the title,
URL, and a summary (first paragraph) for each result.
"""



def google_search_summary(query: str) -> str:
    """Perform a Google search and return summaries of the top results."""
    from googlesearch import search
    import requests
    from bs4 import BeautifulSoup
    search_results = list(search(query, num_results=3, timeout=10))
    
    summaries = []
    
    for url in search_results:
        try:
            # Fetch the content of the page
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # Raise an error for bad responses
            
            # Parse the page content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract the title and a summary (first paragraph or a specific element)
            title = soup.title.string if soup.title else 'No title found'
            summary = soup.find('p').text if soup.find('p') else 'No summary found'
            
            summaries.append({'title': title, 'url': url, 'summary': summary})
        
        except Exception as e:
            summaries.append({'url': url, 'error': str(e)})
    
    return str(summaries)
