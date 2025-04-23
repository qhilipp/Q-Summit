import os
import secrets_
from dataclasses import dataclass
from typing import List

import requests
from bs4 import BeautifulSoup
from googlesearch import search
from langchain.prompts import ChatPromptTemplate
from langchain_community.tools import Tool
from langchain_openai import AzureChatOpenAI

# Initialize the language model
llm = AzureChatOpenAI(
    deployment_name=secrets_.AZURE_OPENAI_DEPLOYMENT_NAME,
    openai_api_key=secrets_.AZURE_OPENAI_API_KEY,
    azure_endpoint=secrets_.AZURE_OPENAI_ENDPOINT,
    openai_api_version="2023-05-15",
)


@dataclass
class SearchResult:
    """Represents a search result with title, URL and snippet."""

    title: str
    url: str
    snippet: str


# Search and Scraping Functions
def google(query: str) -> List[SearchResult]:
    """Perform a Google search and return results as SearchResult objects."""
    google_search = search(query, advanced=True)
    return [
        SearchResult(title=result.title, url=result.url, snippet=result.description)
        for result in google_search
    ]


def scrape_text_from_url(url: str) -> str:
    """Extract plain text content from a webpage."""
    response = requests.get(url)
    return BeautifulSoup(response.text, "html.parser").get_text()


# Analysis Functions
def is_relevant_search_result(result: SearchResult) -> bool:
    """Determine if a search result likely contains university partnership information."""
    template = """
    Evaluate if the following search result is likely to contain information about university partnerships, 
    exchange programs, or partner universities for academic institutions.
    
    Title: {title}
    Description: {snippet}
    
    Respond with ONLY 'YES' if the content seems relevant to university partnerships or 'NO' if it does not.
    """

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm
    result_text = chain.invoke(
        {
            "title": result.title,
            "snippet": result.snippet,
        }
    )

    return "YES" in result_text.content.upper()


def extract_partner_universities(text: str) -> List[str]:
    """Extract partner university names from text using LLM."""
    template = """
    Extract all partner university names from the following text.
    Return ONLY a list of university names, one per line.
    If no partner universities are mentioned, return "No partner universities found."
    
    Text: {text}
    """

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm
    result = chain.invoke({"text": text})

    if "No partner universities found" in result.content:
        return []

    universities = [line.strip() for line in result.content.split("\n") if line.strip()]
    return universities


# Main Processing Functions
def find_partner_universities_from_results(
    search_results: List[SearchResult], query: str = ""
) -> str:
    """Process search results to extract partner universities."""
    if not search_results:
        return "No search results provided."

    # Filter to only relevant results
    relevant_results = [r for r in search_results if is_relevant_search_result(r)]

    if not relevant_results:
        return "No relevant search results found for partner universities."

    all_universities = []
    processed_urls = []
    errors = []

    # Process each relevant result
    for result in relevant_results:
        try:
            if result.url in processed_urls:
                continue  # Skip duplicate URLs

            processed_urls.append(result.url)
            text = scrape_text_from_url(result.url)
            universities = extract_partner_universities(text)

            if universities:
                all_universities.extend(universities)
        except Exception as e:
            errors.append(f"Error processing {result.url}: {str(e)}")

    # Remove duplicates while preserving order
    unique_universities = []
    for uni in all_universities:
        if uni not in unique_universities:
            unique_universities.append(uni)

    if not unique_universities:
        return "No partner universities found in the relevant search results."

    response = "Partner universities found:\n" + "\n".join(unique_universities)

    if errors:
        response += "\n\nWarnings:\n" + "\n".join(errors)

    return response


def find_partner_universities(url: str, query: str = "") -> str:
    """Scrape a URL and extract partner university names."""
    try:
        text = scrape_text_from_url(url)
        universities = extract_partner_universities(text)

        if not universities:
            return "No partner universities found on this website."

        return "Partner universities found:\n" + "\n".join(universities)
    except Exception as e:
        return f"Error processing URL: {str(e)}"


# Create the LangChain tool
university_finder_tool = Tool.from_function(
    func=lambda params: find_partner_universities_from_results(
        params["search_results"], params["query"]
    ),
    name="UniversityPartnerFinder",
    description="Finds partner universities mentioned in relevant search results.",
)


def get_university_base_url(university_name: str) -> str:
    """Ask LLM to provide the base URL for a university."""
    template = """
    What is the official base website URL for {university_name}?
    Return ONLY the URL with no additional text or explanations.
    For example: "https://www.example-university.edu"
    """

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm
    result = chain.invoke({"university_name": university_name})

    # Clean up the result to get just the URL
    url = result.content.strip().replace('"', "").replace("'", "")
    return url


# Filtering Partner Universities Based on Input Criteria


def filter_partner_universities(
    universities: List[str], input_dict: dict
) -> List[dict]:
    """
    Filter partner universities based on input criteria (languages, GPA).
    Returns a list of universities with compatibility information.
    """
    if not universities:
        return []

    # Join list of universities for the prompt
    university_list = "\n".join(universities)
    student_languages = ", ".join(input_dict["languages"])

    template = """
    For each university in the list below, evaluate:
    1. If the university likely offers programs in any of these languages: {languages}
    2. If the student's GPA of {gpa} (on a 4.0 scale) is likely sufficient for admission

    University List:
    {university_list}
    
    For each university, return a JSON object with this format:
    {{
        "name": "University Name",
        "language_match": true/false,
        "gpa_sufficient": true/false,
        "comments": "Brief explanation of compatibility"
    }}
    
    Return only valid JSON without additional text or explanation.
    """

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm
    result = chain.invoke(
        {
            "university_list": university_list,
            "languages": student_languages,
            "gpa": input_dict["gpa"],
        }
    )

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

        # Try to parse the JSON
        filtered_universities = json.loads(response_text)
        if not isinstance(filtered_universities, list):
            filtered_universities = [filtered_universities]  # Handle single object

        return filtered_universities
    except json.JSONDecodeError as e:
        print(f"Error parsing LLM response: {e}")
        print(f"Response was: {response_text}")
        return []


# Refactoring Main Functionality Into a Function


def search_partner_universities(input_dict: dict) -> List[dict]:
    """
    Search for partner universities based on input criteria and return filtered results.
    Returns a list of dictionaries with university information including title, description,
    image URL, student count, ranking, and languages.
    """
    # Get university base URL
    university_url = get_university_base_url(input_dict["university"])

    # Create search query with university name, major and add base URL
    query = f"{input_dict['university']} {input_dict['major']} Partner Universitäten {university_url}"
    print(f"Search query: {query}")

    results = google(query)

    if not results:
        print("No search results found")
        return []

    print(f"Found {len(results)} search results")
    print(f"Processing search results...")
    universities_text = find_partner_universities_from_results(results, query)

    # Extract just the list of universities
    filtered_results = []
    if "Partner universities found:" in universities_text:
        university_lines = (
            universities_text.split("Partner universities found:")[1]
            .split("\n\nWarnings:")[0]
            .strip()
        )
        university_list = [u.strip() for u in university_lines.split("\n") if u.strip()]

        # Generate detailed university information using LLM
        for university_name in university_list:
            uni_data = get_university_details(university_name, input_dict["languages"])
            filtered_results.append(uni_data)

    return filtered_results


def search_university_image(university_name: str) -> str:
    """
    Perform a DuckDuckGo search to find an image link for the university.
    Returns a URL to an image of the university.
    """
    try:
        # Import the DuckDuckGo search library
        from duckduckgo_search import DDGS

        # Initialize the DuckDuckGo search client
        ddgs = DDGS()

        # Search for campus images
        query = f"{university_name} university campus"
        images = list(ddgs.images(query, max_results=5))

        for image in images:
            if image and "image" in image and image["image"]:
                # Verify it's an image URL
                if any(
                    ext in image["image"].lower()
                    for ext in [".jpg", ".jpeg", ".png", ".gif"]
                ):
                    return image["image"]

        # If still no results, return None
        return None
    except Exception as e:
        print(f"Error searching for image: {str(e)}")
        return None


def get_university_details(university_name: str, student_languages: List[str]) -> dict:
    """
    Use LLM to generate comprehensive details about a university,
    and search for a real image of the university.
    """
    template = """
    Provide comprehensive information about {university_name} in JSON format.
    Include the following fields:
    1. A brief description of the university (2-3 sentences)
    2. An estimate of the student count
    3. A ranking category (high, mid, or low)
    4. Languages used for instruction
    
    Consider the student's language proficiencies ({languages}) when assessing compatibility.
    
    Return ONLY a JSON object with this format:
    {{
        "title": "{university_name}",
        "description": "Brief description of the university",
        "student_count": estimated_number,
        "ranking": "high|mid|low",
        "languages": ["Language1", "Language2"]
    }}
    """

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm
    result = chain.invoke(
        {
            "university_name": university_name,
            "languages": ", ".join(student_languages),
        }
    )

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

        # Try to parse the JSON
        university_data = json.loads(response_text)

        # Search for a real image of the university
        university_data["image"] = search_university_image(university_name)

        return university_data
    except json.JSONDecodeError as e:
        print(f"Error parsing LLM response for {university_name}: {e}")
        # Return a minimal fallback object if parsing fails
        return {
            "title": university_name,
            "description": "Information unavailable",
            "image": search_university_image(
                university_name
            ),  # Still try to get an image
            "student_count": 0,
            "ranking": "unknown",
            "languages": [],
        }


# Main execution block
if __name__ == "__main__":
    # Example usage
    input_dict = {
        "university": "University of Muenster",
        "major": "Computer Science",
        "gpa": 3.7,
        "languages": ["English", "Spanish"],
        "budget": 1000,
    }

    # Search for partner universities
    results = search_partner_universities(input_dict)

    # Display results
    if results:
        print("\nPartner universities matching your criteria:")
        for uni in results:
            print(f"• {uni['title']}")
            print(f"  Description: {uni['description']}")
            print(f"  Student Count: {uni['student_count']}")
            print(f"  Ranking: {uni['ranking']}")
            print(f"  Languages: {', '.join(uni['languages'])}")
            print(f"  Image URL: {uni['image']}")
    else:
        print("No matching partner universities found.")
