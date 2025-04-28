import requests
from typing import Dict
from bs4 import BeautifulSoup
from langchain.agents.agent_types import AgentType
from langchain.prompts import ChatPromptTemplate
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from tools.utils import llm


class ContentAnalysisSchema(BaseModel):
    """Schema for content analysis requests.
    
    Attributes:
        url: Webpage URL to scrape content from
        query: Search query to focus information extraction
        max_points: Maximum number of key points to return (default 5)
    """
    url: str = Field(..., description="The URL to scrape content from")
    query: str = Field(
        ..., description="The query to use for extracting relevant information"
    )
    max_points: int = Field(
        5, description="Maximum number of important points to extract"
    )


def scrape_text_from_url(url: str) -> str:
    """Extract plain text content from a webpage.
    
    Args:
        url: The URL of the webpage to scrape.

    Returns:
        The plain text content of the webpage.

    Raises:
        requests.exceptions.RequestException: If the HTTP request fails.
    """
    response = requests.get(url)
    return BeautifulSoup(response.text, "html.parser").get_text()


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
        scraped_text = scrape_text_from_url(url)
        max_text_length = 8000  # Adjust based on token limits of your LLM
        if len(scraped_text) > max_text_length:
            scraped_text = scraped_text[:max_text_length] + "... [text truncated]"

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


# Tool creation with explicit argument specification
content_analysis_tool = StructuredTool.from_function(
    func=extract_important_points,
    name="ContentAnalyzer",
    description="Scrapes content from a URL and extracts the most important points related to a query.",
    args_schema=ContentAnalysisSchema,
)
