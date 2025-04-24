from dataclasses import dataclass
from typing import Any, Dict, List

import requests
import secrets_
from bs4 import BeautifulSoup
from googlesearch import search
from langchain.prompts import ChatPromptTemplate
from langchain_community.tools import Tool
from langchain_openai import AzureChatOpenAI

# LLM initialization
llm = AzureChatOpenAI(
    deployment_name=secrets_.AZURE_OPENAI_DEPLOYMENT_NAME,
    openai_api_key=secrets_.AZURE_OPENAI_API_KEY,
    azure_endpoint=secrets_.AZURE_OPENAI_ENDPOINT,
    openai_api_version="2023-05-15",
)


@dataclass
class SearchResult:
    """Represents a search result with title, URL and snippet.

    Attributes:
        title (str): The title of the search result.
        url (str): The URL of the search result.
        snippet (str): The snippet or description of the search result.2
    """

    title: str
    url: str
    snippet: str


# Search and Scraping Functions
def google(query: str, num_results: int = 10) -> List[SearchResult]:
    """Perform a Google search and return results as SearchResult objects.

    Args:
        query (str): The search query.
        num_results (int, optional): Number of results to return. Defaults to 10.

    Returns:
        List[SearchResult]: List of search results as SearchResult objects.
    """
    google_search = search(query, advanced=True, num_results=num_results)
    return [
        SearchResult(title=result.title, url=result.url, snippet=result.description)
        for result in google_search
    ]


def scrape_text_from_url(url: str) -> str:
    """Extract plain text content from a webpage.

    Args:
        url (str): The URL to scrape.

    Returns:
        str: The plain text content extracted from the page.
    """
    response = requests.get(url)
    return BeautifulSoup(response.text, "html.parser").get_text()


# Analysis Functions
def is_relevant_search_result(result: SearchResult) -> bool:
    """Determine if a search result likely contains university partnership information.

    Args:
        result (SearchResult): The search result to evaluate.

    Returns:
        bool: True if the result is relevant, False otherwise.
    """
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
    """Extract partner university names from text using LLM.

    Args:
        text (str): The text to analyze.

    Returns:
        List[str]: List of partner university names.
    """
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
    """Process search results to extract partner universities.

    Args:
        search_results (List[SearchResult]): List of search results.
        query (str, optional): Search query for context. Defaults to "".

    Returns:
        str: A formatted string listing partner universities found, or an error message.
    """
    if not search_results:
        return "No search results provided."

    relevant_results = [r for r in search_results if is_relevant_search_result(r)][:3]

    if not relevant_results:
        return "No relevant search results found for partner universities."

    all_universities = []
    processed_urls = []
    errors = []

    for result in relevant_results:
        try:
            if result.url in processed_urls:
                continue

            processed_urls.append(result.url)
            text = scrape_text_from_url(result.url)
            universities = extract_partner_universities(text)

            if universities:
                all_universities.extend(universities)
        except Exception as e:
            errors.append(f"Error processing {result.url}: {str(e)}")

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
    """Scrape a URL and extract partner university names.

    Args:
        url (str): The URL to scrape.
        query (str, optional): The query for context. Defaults to "".

    Returns:
        str: A formatted string listing partner universities found, or an error message.
    """
    try:
        text = scrape_text_from_url(url)
        universities = extract_partner_universities(text)

        if not universities:
            return "No partner universities found on this website."

        return "Partner universities found:\n" + "\n".join(universities)
    except Exception as e:
        return f"Error processing URL: {str(e)}"


# Create LangChain tool
university_finder_tool = Tool.from_function(
    func=lambda params: find_partner_universities_from_results(
        params["search_results"], params["query"]
    ),
    name="UniversityPartnerFinder",
    description="Finds partner universities mentioned in relevant search results.",
)


def get_university_base_url(university_name: str) -> str:
    """Ask LLM to provide the base URL for a university.

    Args:
        university_name (str): The name of the university.

    Returns:
        str: The official base URL of the university.
    """
    template = """
    What is the official base website URL for {university_name}?
    Return ONLY the URL with no additional text or explanations.
    For example: "https://www.example-university.edu"
    """

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm
    result = chain.invoke({"university_name": university_name})
    url = result.content.strip().replace('"', "").replace("'", "")
    return url


def filter_partner_universities(
    universities: List[str], input_dict: dict
) -> List[dict]:
    """Filter partner universities based on input criteria (languages, GPA).

    Args:
        universities (List[str]): List of university names.
        input_dict (dict): Dictionary with filter criteria (languages, gpa).

    Returns:
        List[dict]: List of universities with compatibility information.
    """
    if not universities:
        return []

    university_list = "\n".join(universities)
    student_languages = ", ".join(input_dict["languages"])

    template = """
    For each university in the list below, evaluate:
    0. (Important) If the university is not a real university, filter it out.
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

    import json

    try:
        response_text = result.content.strip()
        if "```" in response_text:
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:].strip()
        filtered_universities = json.loads(response_text)
        if not isinstance(filtered_universities, list):
            filtered_universities = [filtered_universities]  # Handle single object
        return filtered_universities

    except json.JSONDecodeError as e:
        print(f"Error parsing LLM response: {e}")
        print(f"Response was: {response_text}")
        return []


def search_university_image(university_name: str) -> str:
    """Perform a DuckDuckGo search to find an image link for the university.

    Args:
        university_name (str): The name of the university.

    Returns:
        str: URL to an image of the university, or None if not found.
    """
    try:
        from duckduckgo_search import DDGS

        ddgs = DDGS()
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
        return None

    except Exception as e:
        print(f"Error searching for image: {str(e)}")
        return None


def get_university_details(university_name: str, student_languages: List[str]) -> dict:
    """Use LLM to generate comprehensive details about a university and search for a real image.

    Args:
        university_name (str): Name of the university.
        student_languages (List[str]): List of languages the student knows.

    Returns:
        dict: Dictionary with university details, including title, description, image URL, student count, ranking, and languages.
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

    import json

    try:
        response_text = result.content.strip()
        if "```" in response_text:
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:].strip()
        university_data = json.loads(response_text)
        university_data["image"] = search_university_image(university_name)
        return university_data

    except json.JSONDecodeError as e:
        print(f"Error parsing LLM response for {university_name}: {e}")
        return {
            "title": university_name,
            "description": "Information unavailable",
            "image": search_university_image(university_name),
            "student_count": 0,
            "ranking": "unknown",
            "languages": [],
        }


class Agent:
    """Base class for all agents in the system.

    Attributes:
        name (str): The name of the agent.
    """

    def __init__(self, name: str):
        """Initialize the agent.

        Args:
            name (str): The agent's name.
        """
        self.name = name

    def run(self, *args, **kwargs):
        """Run the agent with the given inputs.

        Raises:
            NotImplementedError: If the method is not implemented in a subclass.
        """
        raise NotImplementedError("Subclasses must implement this method")


class SearchAgent(Agent):
    """Agent responsible for searching and finding partner universities."""

    def __init__(self):
        """Initialize the SearchAgent."""
        super().__init__("SearchAgent")

    def run(self, input_dict: Dict[str, Any]) -> List[str]:
        """Search for partner universities based on the input criteria.

        Args:
            input_dict (Dict[str, Any]): Dictionary containing university, major, etc.

        Returns:
            List[str]: List of university names.
        """
        print(f"[{self.name}] Searching for partner universities...")
        university_url = get_university_base_url(input_dict["university"])
        query = f"{input_dict['university']} {input_dict['major']} (Erasmus) Partner Universitäten {university_url}"
        print(f"[{self.name}] Search query: {query}")
        results = google(query, num_results=6)

        if not results:
            print(f"[{self.name}] No search results found")
            return []

        print(f"[{self.name}] Found {len(results)} search results")
        print(f"[{self.name}] Processing search results...")
        universities_text = find_partner_universities_from_results(results, query)

        if "Partner universities found:" in universities_text:
            university_lines = (
                universities_text.split("Partner universities found:")[1]
                .split("\n\nWarnings:")[0]
                .strip()
            )
            university_list = [
                u.strip() for u in university_lines.split("\n") if u.strip()
            ]
            university_list = university_list[:8]
            print(f"[{self.name}] Found {len(university_list)} partner universities")
            return university_list
        print(f"[{self.name}] No partner universities found")
        return []


class DetailAgent(Agent):
    """Agent responsible for retrieving detailed information about universities."""

    def __init__(self):
        """Initialize the DetailAgent."""
        super().__init__("DetailAgent")

    def run(self, university_name: str, student_languages: List[str]) -> Dict[str, Any]:
        """Get detailed information about a university.

        Args:
            university_name (str): Name of the university.
            student_languages (List[str]): List of languages the student knows.

        Returns:
            Dict[str, Any]: Dictionary with university details.
        """
        print(f"[{self.name}] Getting details for {university_name}...")
        return get_university_details(university_name, student_languages)


class MultiAgentUniSearchSystem:
    """Coordinator for the multiagent system.

    Attributes:
        search_agent (SearchAgent): Agent for searching universities.
        detail_agent (DetailAgent): Agent for retrieving university details.
    """

    def __init__(self):
        """Initialize the MultiAgentUniSearchSystem."""
        self.search_agent = SearchAgent()
        self.detail_agent = DetailAgent()

    def run(self, input_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run the multiagent system to search for partner universities and get details.

        Args:
            input_dict (Dict[str, Any]): Dictionary with input parameters.

        Returns:
            List[Dict[str, Any]]: List of dictionaries with university details.
        """
        print("Starting multiagent system...")
        university_names = self.search_agent.run(input_dict)
        if not university_names:
            print("No partner universities found to get details for")
            return []
        results = []
        for uni_name in university_names:
            uni_details = self.detail_agent.run(uni_name, input_dict["languages"])
            results.append(uni_details)
        print(
            f"Multiagent system completed. Found details for {len(results)} universities"
        )
        return results


def search_partner_universities(input_dict: dict) -> List[dict]:
    """Search for partner universities based on input criteria and return filtered results.

    Args:
        input_dict (dict): Dictionary with search criteria.

    Returns:
        List[dict]: List of dictionaries with university information including title,
            description, image URL, student count, ranking, and languages.
    """
    multiagent_system = MultiAgentUniSearchSystem()
    return multiagent_system.run(input_dict)


if __name__ == "__main__":
    input_dict = {
        "university": "University of Muenster",
        "major": "Computer Science",
        "gpa": 3.7,
        "languages": ["English", "Spanish"],
        "budget": 1000,
    }

    results = search_partner_universities(input_dict)
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
