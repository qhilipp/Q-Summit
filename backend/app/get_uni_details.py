import time
from abc import ABC
from typing import List, Optional, Tuple    
import importantInformation
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
    ranking_info: str
    pricing_info: str
    academic_info: str


def get_uni_details(university_name: str, subject: str) -> UniversityDetails:
    """
    Get detailed information about a university by googling, scraping, and postprocessing relevant pages.

    Args:
        university_name: The name of the university to search for
        subject: The subject area to focus on

    Returns:
        UniversityDetails object containing quotes, ranking, pricing, and academic info
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
        
    # Get information from importantInformation module
    information = importantInformation.main(university_name, subject)
    details = fillDetails(information, university_name, subject)
        
    # Create and return UniversityDetails object with all information
    return UniversityDetails(
        quotes=all_quotes,
        ranking_info=details["ranking_info"],
        pricing_info=details["pricing_info"],
        academic_info=details["academic_info"]
    )

def fillDetails(information: Tuple[str, str], university_name: str, subject: str) -> dict:
    """
    Fill in university details based on scraped information.
    Uses LLM to extract pricing info from the first tuple element,
    and splits ranking and academic info from the second element.
    
    Args:
        information: Tuple containing (campus_life_info, ranking_research_info)
        university_name: Name of the university
        subject: Subject area
        
    Returns:
        Dictionary with pricing_info, ranking_info, and academic_info
    """
    # Extract campus life and ranking/research information
    campus_life_info = information[0]
    ranking_research_info = information[1]
    
    # Use LLM to extract pricing information from campus life info
    pricing_prompt = f"""
    Extract all information about costs, tuition fees, living expenses, and financial aspects
    from this text about campus life at {university_name}.
    
    Focus on:
    - Tuition fees for international students
    - Housing costs (on-campus and off-campus)
    - Average living expenses
    - Potential scholarships or financial aid for international students
    - Any cost-related challenges mentioned
    
    Format the information in a clear, structured paragraph.
    If specific amounts are mentioned, include them.
    If no specific pricing information is found, say "No specific pricing information available."
    
    Text: {campus_life_info}
    
    PRICING INFORMATION:
    """
    
    try:
        # Use the existing LLM from importantInformation module
        prompt = ChatPromptTemplate.from_template(pricing_prompt)
        chain = prompt | llm
        pricing_info = chain.invoke({}).content.strip()
    except Exception as e:
        print(f"Error extracting pricing info: {e}")
        pricing_info = "No pricing information available."
    
    # Use LLM to split ranking info and academic info from the ranking/research info
    split_prompt = f"""
    Split the following text about {university_name}'s ranking and research into two separate sections:
    
    1. RANKING INFORMATION: Information about university rankings, reputation, and standing.
    2. ACADEMIC INFORMATION: Information about research areas, academic strengths, professors, and facilities.
    
    Organize each section into a cohesive paragraph.
    
    Text: {ranking_research_info}
    
    RANKING INFORMATION:
    
    ACADEMIC INFORMATION:
    """
    
    try:
        prompt = ChatPromptTemplate.from_template(split_prompt)
        chain = prompt | llm
        split_result = chain.invoke({}).content.strip()
        
        # Extract the two sections
        if "RANKING INFORMATION:" in split_result and "ACADEMIC INFORMATION:" in split_result:
            parts = split_result.split("ACADEMIC INFORMATION:")
            ranking_info = parts[0].replace("RANKING INFORMATION:", "").strip()
            academic_info = parts[1].strip()
        else:
            # Fallback if the split didn't work as expected
            ranking_info = "Information about rankings could not be extracted."
            academic_info = "Information about academic areas could not be extracted."
    except Exception as e:
        print(f"Error splitting ranking and academic info: {e}")
        ranking_info = "Error extracting ranking information."
        academic_info = "Error extracting academic information."
    
    return {
        "pricing_info": pricing_info,
        "ranking_info": ranking_info,
        "academic_info": academic_info
    }

if __name__ == "__main__":
    import sys
    
    # Define some test universities and subjects for easy testing
    test_cases = [
        ("Stanford University", "Computer Science"),
        ("University of Oxford", "Economics"),
        ("Technical University of Munich", "Engineering"),
        ("University of Tokyo", "Physics")
    ]
    
    # Use command line arguments or ask for input
    if len(sys.argv) > 1:
        uni_name = sys.argv[1]
        subject = sys.argv[2] if len(sys.argv) > 2 else "Computer Science"
        test_single_case = True
    else:
        print("Select a test case:")
        for i, (uni, subj) in enumerate(test_cases, 1):
            print(f"{i}. {uni} - {subj}")
        print("5. Enter custom university and subject")
        
        choice = input("Enter your choice (1-5): ")
        
        if choice == "5":
            uni_name = input("Enter university name: ")
            subject = input("Enter subject: ")
            test_single_case = True
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(test_cases):
                    uni_name, subject = test_cases[idx]
                    test_single_case = True
                else:
                    print("Invalid choice, using default test case")
                    test_single_case = False
            except ValueError:
                print("Invalid input, using default test case")
                test_single_case = False
    
    # Function to nicely format and print university details
    def print_university_details(details, uni, subj):
        print("\n" + "="*80)
        print(f"UNIVERSITY DETAILS: {uni} - {subj}")
        print("="*80)
        
        # Print student quotes
        print("\n📚 STUDENT QUOTES:")
        if details.quotes:
            for i, quote in enumerate(details.quotes, 1):
                print(f"\n  {i}. \"{quote.quote}\"")
                print(f"     Source: {quote.source_link}")
        else:
            print("  No student quotes found.")
        
        # Print ranking information
        print("\n🏆 RANKING INFORMATION:")
        print(f"  {details.ranking_info}")
        
        # Print academic information
        print("\n🎓 ACADEMIC INFORMATION:")
        print(f"  {details.academic_info}")
        
        # Print pricing information
        print("\n💰 PRICING INFORMATION:")
        print(f"  {details.pricing_info}")
        
        print("\n" + "="*80)
    
    try:
        if test_single_case:
            # Test a single university
            print(f"\nFetching details for: {uni_name} - {subject}")
            details = get_uni_details(uni_name, subject)
            print_university_details(details, uni_name, subject)
        else:
            # Run through all test cases for comprehensive testing
            for uni_name, subject in test_cases:
                print(f"\nFetching details for: {uni_name} - {subject}")
                details = get_uni_details(uni_name, subject)
                print_university_details(details, uni_name, subject)
                
                # Ask whether to continue to the next test case
                if input("\nContinue to next test case? (y/n): ").lower() != 'y':
                    break
    
    except Exception as e:
        print(f"\n❌ Error fetching university details: {e}")
        import traceback
        traceback.print_exc()

