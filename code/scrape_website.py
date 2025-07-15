def scrape_website(url):
    """Fetch the full HTML content of a webpage."""
    import requests
    from bs4 import BeautifulSoup
    response = requests.get(url, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup.prettify()  # Return the full HTML, not truncated
