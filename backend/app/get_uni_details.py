import time
from abc import ABC
from typing import List, Optional

import requests
import secrets_
from attr import dataclass
from find_unis import SearchResult, google, scrape_text_from_url
from langchain.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI
from requests.exceptions import RequestException, Timeout

llm = AzureChatOpenAI(
    deployment_name=secrets_.AZURE_OPENAI_DEPLOYMENT_NAME,
    openai_api_key=secrets_.AZURE_OPENAI_API_KEY,
    azure_endpoint=secrets_.AZURE_OPENAI_ENDPOINT,
    openai_api_version="2023-05-15",
)


@dataclass
class Quote:
    quote: str
    source_link: str


def get_quotes_from_blog(text: str, link: str) -> List[Quote]:
    """
    Get most interesting quotes from a blog post about university experiences.

    Args:
        text: The text content of the blog post
        link: The URL of the blog post

    Returns:
        A list of Quote objects containing interesting excerpts
    """
    template = """
    Extract the 3-5 most interesting quotes or excerpts from this blog post about university experiences.
    Focus on quotes that discuss:
    - Student experiences at the university
    - Exchange program benefits
    - Campus life
    - Academic quality
    - Cultural aspects
    
    For each quote:
    1. Extract the exact text (1-3 sentences)
    2. Identify the author if mentioned
    3. Provide a brief context about what the quote discusses
    
    Return the results as a JSON array with this format:
    [
        {{
            "text": "The exact quote text",
        }}
    ]
    
    Blog text:
    {text}
    
    Return only valid JSON without additional text or explanation.
    """

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm

    try:
        result = chain.invoke({"text": text})
    except Exception as e:
        print(f"LLM error while processing quotes: {e}")
        return []

    # Process the returned JSON
    import json

    try:
        # The LLM might wrap the response in ```json and ``` or other formatting
        response_text = result.content.strip()
        if "```" in response_text:
            # Extract content between code blocks
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:].strip()

        # Parse the JSON
        quotes_data = json.loads(response_text)

        # Convert to Quote objects
        quotes = [Quote(quote=quote["text"], source_link=link) for quote in quotes_data]

        return quotes
    except json.JSONDecodeError as e:
        print(f"Error parsing LLM response: {e}")
        print(f"Response was: {response_text}")
        return []


@dataclass
class UniversityDetails:
    quotes: List[Quote]


def get_uni_details(university_name: str) -> UniversityDetails:
    """
    Get detailed information about a university by googling, scraping, and postprocessing relevant pages.

    Args:
        university_name: The name of the university to search for

    Returns:
        UniversityDetails object containing quotes
    """
    # Search queries
    query = f"{university_name} student experience blog article post"
    all_quotes = []

    # Process each search query
    try:
        # Get search results with timeout
        search_results: List[SearchResult] = google(query)
    except Exception as e:
        print(f"Error during Google search for '{query}': {e}")

    sites_processed = 0
    for result in search_results:
        if sites_processed >= 2:
            break

        try:
            # Ensure we have a valid URL - use url attribute from SearchResult
            if not hasattr(result, "url") or not result.url:
                continue

            # Scrape text from the URL with timeout
            scraped_text = scrape_text_from_url(result.url)

            # Skip if we couldn't get useful text
            if not scraped_text or len(scraped_text) < 200:
                continue

            sites_processed += 1

            # Process for quotes based on the query type
            if (
                "experience" in query.lower()
                or "stories" in query.lower()
                or "life" in query.lower()
            ):
                quotes = get_quotes_from_blog(scraped_text, result.url)
                all_quotes.extend(quotes)

        except Exception as e:
            print(
                f"Error processing URL {result.url if hasattr(result, 'url') else 'unknown'}: {e}"
            )
            continue

    # Create and return UniversityDetails object
    return UniversityDetails(quotes=all_quotes)


if __name__ == "__main__":
    import sys

    # Get university name from command line or use default
    uni_name = sys.argv[1] if len(sys.argv) > 1 else "Stanford University"

    print(f"Fetching details for: {uni_name}")
    try:
        details = get_uni_details(uni_name)

        # Print quotes
        print("\n===== STUDENT QUOTES =====")
        if details.quotes:
            for i, quote in enumerate(details.quotes, 1):
                print(f"\n{i}. {quote.quote}")
                print(f"   Source: {quote.source_link}")
        else:
            print("No quotes found.")

    except Exception as e:
        print(f"Error fetching university details: {e}")
        import traceback

        traceback.print_exc()
