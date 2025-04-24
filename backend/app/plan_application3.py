# import module-function
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Union

import secrets_
from find_unis import SearchResult, google, scrape_text_from_url
from googlesearch import search
from langchain.agents import Tool, initialize_agent
from langchain.agents.agent_types import AgentType
from langchain.llms import OpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.tools import StructuredTool
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel, Field

llm = AzureChatOpenAI(
    deployment_name=secrets_.AZURE_OPENAI_DEPLOYMENT_NAME,
    openai_api_key=secrets_.AZURE_OPENAI_API_KEY,
    azure_endpoint=secrets_.AZURE_OPENAI_ENDPOINT,
    openai_api_version="2023-05-15",
)


# Define schema for Google search tool
class GoogleSearchSchema(BaseModel):
    query: str = Field(..., description="The search query to use for Google search")
    filter_query: Optional[str] = Field(
        None, description="Additional query terms to use for filtering results"
    )


# Google Search Tool with Filtering
def google_search_with_filter(query: str, filter_query: str = None) -> List[Dict]:
    """
    Perform a Google search using the query and filter results based on relevance.

    Args:
        query: The search query to use for Google search
        filter_query: Additional query terms to use for filtering results

    Returns:
        List of dictionaries with filtered search results
    """
    # Get search results from Google
    search_results = google(query, num_results=9)

    # If no filter query provided, return all results
    if not filter_query:
        return [
            {"title": r.title, "url": r.url, "snippet": r.snippet}
            for r in search_results
        ]

    # Filter results based on relevance to filter_query
    filtered_results = []

    # Use LLM to determine relevance with a much stricter prompt
    template = """
    You are an expert at evaluating search results for study abroad applications. 
    
    Carefully evaluate if the following search result is HIGHLY relevant to the query: "{filter_query}"
    
    Search result:
    Title: {title}
    Description: {snippet}
    
    RELEVANCE CRITERIA:
    1. The content must be about study abroad application processes, requirements, or deadlines
    2. The content must either:
       a) Be from an official university or education authority source, OR
       b) Contain specific, actionable information about "{target_university}" exchanges, OR
       c) Provide generally applicable guidance for all study abroad applications
    3. Content that only mentions study abroad in passing or is primarily about something else is NOT relevant
    4. Content about study abroad to universities other than the target university is NOT relevant
    5. Blog posts, personal experiences, or news articles are mostly NOT relevant unless they contain official information
    
    First, analyze how the result meets or fails the criteria above.
    Then respond with ONLY:
    - "HIGHLY RELEVANT" - if the result is clearly and directly relevant (meeting criteria 1 AND 2)
    - "NOT RELEVANT" - if the result fails to meet ANY of the criteria
    """

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm

    # Extract target university from the query
    import re

    target_university = ""
    match = re.search(r'"([^"]*)".*"([^"]*)"', query)
    if match:
        # Assuming second quoted term is the target university
        target_university = match.group(2)

    for result in search_results:
        try:
            evaluation = chain.invoke(
                {
                    "filter_query": filter_query,
                    "title": result.title,
                    "snippet": result.snippet,
                    "target_university": target_university,
                }
            )

            if "HIGHLY RELEVANT" in evaluation.content.upper():
                filtered_results.append(
                    {
                        "title": result.title,
                        "url": result.url,
                        "snippet": result.snippet,
                    }
                )
        except Exception as e:
            print(f"Error evaluating result {result.title}: {str(e)}")

    # Double-check for relevance based on URL patterns that indicate official sources
    if target_university:
        for result in search_results:
            # Skip if already included
            if any(r["url"] == result.url for r in filtered_results):
                continue

            # Check if URL is from an official university domain or education authority
            url_lower = result.url.lower()
            target_uni_words = [
                w.lower() for w in target_university.split() if len(w) > 2
            ]

            # If URL contains university domain patterns and target university keywords
            if (
                (
                    ".edu" in url_lower
                    or ".ac." in url_lower
                    or "university" in url_lower
                )
                and any(word in url_lower for word in target_uni_words)
                and (
                    "exchange" in url_lower
                    or "abroad" in url_lower
                    or "international" in url_lower
                )
            ):
                filtered_results.append(
                    {
                        "title": result.title,
                        "url": result.url,
                        "snippet": result.snippet,
                    }
                )

    return filtered_results


# Create the LangChain tool
google_search_tool = StructuredTool.from_function(
    func=google_search_with_filter,
    name="GoogleSearchFilter",
    description="Searches Google with the provided query and filters results based on relevance to a filter query.",
    args_schema=GoogleSearchSchema,
)


# Define schema for content extraction tool
class ContentAnalysisSchema(BaseModel):
    url: str = Field(..., description="The URL to scrape content from")
    query: str = Field(
        ..., description="The query to use for extracting relevant information"
    )
    max_points: int = Field(
        5, description="Maximum number of important points to extract"
    )


# URL Content Extraction Tool
def extract_important_points(url: str, query: str, max_points: int = 5) -> Dict:
    """
    Scrapes text from a URL and extracts the most important points related to a query.

    Args:
        url: The URL to scrape content from
        query: The query to use for extracting relevant information
        max_points: Maximum number of important points to extract (default: 5)

    Returns:
        Dictionary with the URL, query, and extracted important points
    """
    try:
        # Scrape text content from the URL
        scraped_text = scrape_text_from_url(url)

        # If the scraped text is too long, truncate it to prevent token limits
        max_text_length = 8000  # Adjust based on token limits of your LLM
        if len(scraped_text) > max_text_length:
            scraped_text = scraped_text[:max_text_length] + "... [text truncated]"

        # Create a prompt template for extracting important points
        template = """
        You are an expert at extracting and summarizing important information.
        
        I have the following text content from a webpage, and I need you to extract 
        the {max_points} most important points related to this query: "{query}"
        
        Webpage content:
        {text_content}
        
        Return ONLY a numbered list of the {max_points} most important and relevant points.
        Each point should be concise but informative (1-2 sentences each).
        If there are fewer than {max_points} relevant points, return only those that are relevant.
        """

        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | llm

        result = chain.invoke(
            {"query": query, "text_content": scraped_text, "max_points": max_points}
        )

        # Process the result to extract the points as a list
        points_text = result.content.strip()
        points_list = [line.strip() for line in points_text.split("\n") if line.strip()]

        return {
            "url": url,
            "query": query,
            "important_points": points_list,
            "source_length": len(scraped_text),
        }

    except Exception as e:
        return {"url": url, "query": query, "error": str(e), "important_points": []}


# Create Content Analysis Tool
content_analysis_tool = StructuredTool.from_function(
    func=extract_important_points,
    name="ContentAnalyzer",
    description="Scrapes content from a URL and extracts the most important points related to a query.",
    args_schema=ContentAnalysisSchema,
)


def plan_semester_abroad_application(
    home_university: str, target_university: str, major: str
) -> Dict:
    """
    Plans a semester abroad application for a given home university, target university, and major.
    """
    agent = initialize_agent(
        [google_search_tool, content_analysis_tool],
        llm,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        max_execution_time=6,
        early_stopping_method="generate",
    )
    result = agent.invoke(
        {
            "input": f"""
            Create a brief plan for applying to a semester abroad program from "{home_university}" to "{target_university}" for a student majoring in "{major}".
            
            Possible topics to research and outline:
            1. Application deadlines and important dates from both universities
            2. Required documents and application materials (transcripts, recommendations, language tests, etc.)
            3. Financial considerations (tuition, scholarships, living costs, insurance)
            4. Visa requirements and immigration processes
            5. Course equivalency and credit transfer policies
            6. Housing options at the target university
            7. Pre-departure preparations (health, orientation, packing)
            8. Academic considerations specific to the student's major
            9. Timeline with key milestones and application steps
            10. Common challenges and how to address them
            
            Use university websites and official sources whenever possible. The plan should be brief, actionable, and organized well.
            Don't take into account too many websites, just focus on the most important ones.
            """
        }
    )
    return result["output"]


def make_html_from_plan(plan: str) -> str:
    """
    Let llm make a html from the plan to give a good overview.
    """
    template = """
    You are an expert HTML designer. Convert the following study abroad application plan into a 
    well-organized, visually appealing HTML page. The HTML should:
    
    1. Have a clean, professional design
    2. Include appropriate sections with headings
    3. Use lists, tables, or cards where appropriate
    4. Include a timeline or checklist section if possible
    5. Use a readable, responsive layout
    6. Include basic CSS styling (embedded in style tags)
    
    Here's the plan to convert:
    {plan}
    
    Return ONLY the complete HTML code (including <!DOCTYPE>, <html>, <head>, and <body> tags).
    """

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm

    result = chain.invoke({"plan": plan})

    return result.content


if __name__ == "__main__":
    result = plan_semester_abroad_application(
        "Muenster",
        "UCSB",
        "Computer Science",
    )
    print(result)
