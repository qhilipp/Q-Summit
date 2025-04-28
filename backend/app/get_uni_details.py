from typing import List
from attr import dataclass
from find_unis import SearchResult, google, scrape_text_from_url
from langchain.prompts import ChatPromptTemplate
from tools import llm


@dataclass
class Quote:
    """Represents a quote or excerpt from a university experience blog post.

    Attributes:
        quote (str): The exact text of the quote or excerpt.
        source_link (str): The URL of the blog post where the quote was found.
    """
    quote: str
    source_link: str


def get_quotes_from_blog(text: str, link: str) -> List[Quote]:
    """Extract interesting quotes from a blog post about university experiences.

    Args:
        text (str): The text content of the blog post.
        link (str): The URL of the blog post.

    Returns:
        List[Quote]: A list of Quote objects containing interesting excerpts from the blog post.
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

    import json
    try:
        response_text = result.content.strip()
        if "```" in response_text:
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:].strip()
        quotes_data = json.loads(response_text)
        quotes = [Quote(quote=quote["text"], source_link=link) for quote in quotes_data]
        return quotes
    
    except json.JSONDecodeError as e:
        print(f"Error parsing LLM response: {e}")
        print(f"Response was: {response_text}")
        return []


@dataclass
class UniversityDetails:
    """Holds detailed information about a university, including student quotes.

    Attributes:
        quotes (List[Quote]): A list of quotes or excerpts related to the university.
    """
    quotes: List[Quote]


def get_uni_details(university_name: str) -> UniversityDetails:
    """Retrieve detailed information about a university by searching, scraping, and analyzing relevant blog posts.

    Args:
        university_name (str): The name of the university to search for.

    Returns:
        UniversityDetails: An object containing a list of quotes about student experiences at the university.
    """
    query = f"{university_name} student experience blog article post"
    all_quotes = []

    try:
        search_results: List[SearchResult] = google(query)
    except Exception as e:
        print(f"Error during Google search for '{query}': {e}")

    sites_processed = 0
    for result in search_results:
        if sites_processed >= 2:
            break

        try:
            if not hasattr(result, "url") or not result.url:
                continue
            scraped_text = scrape_text_from_url(result.url)

            if not scraped_text or len(scraped_text) < 200:
                continue
            sites_processed += 1

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

    return UniversityDetails(quotes=all_quotes)


if __name__ == "__main__":
    import sys
    uni_name = sys.argv[1] if len(sys.argv) > 1 else "Stanford University"
    print(f"Fetching details for: {uni_name}")
    try:
        details = get_uni_details(uni_name)
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
