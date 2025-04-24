# import module-function
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Union

import secrets_
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


class GoogleSearchSchema(BaseModel):
    query: str = Field(..., description="The search query to use for Google search")
    filter_query: Optional[str] = Field(
        None, description="Additional query terms to use for filtering results"
    )

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        if isinstance(obj, dict):
            # Handle when query is a dict from LangChain
            if (
                "query" in obj
                and isinstance(obj["query"], dict)
                and "description" in obj["query"]
            ):
                obj["query"] = obj["query"]["description"]

            # Handle when filter_query is a dict
            if (
                "filter_query" in obj
                and isinstance(obj["filter_query"], dict)
                and "description" in obj["filter_query"]
            ):
                obj["filter_query"] = obj["filter_query"]["description"]

        return super().model_validate(obj, *args, **kwargs)


def google_search_with_filter(query: str, filter_query: str = None) -> List[Dict]:
    """
    Perform a Google search using the query and filter results based on relevance.

    Args:
        query: The search query to use for Google search
        filter_query: Additional query terms to use for filtering results

    Returns:
        List of dictionaries with filtered search results
    """
    # Handle case where query is a dict instead of a string (occurs in some LangChain outputs)
    if isinstance(query, dict) and "description" in query:
        query = query["description"]
    elif isinstance(query, dict) and "query" in query:
        query = query["query"]

    # Handle filter_query similarly
    if isinstance(filter_query, dict) and "description" in filter_query:
        filter_query = filter_query["description"]

    # Get search results from Google - these are returned as strings (URLs)
    search_results = list(search(query, num_results=9))

    # Create result objects with available information
    formatted_results = []
    for url in search_results:
        # Extract a simple title from the URL
        title = url.split("/")[-1].replace("-", " ").replace("_", " ")
        if not title or title.endswith((".html", ".htm", ".php", ".asp")):
            # Use domain if path is empty or ends with file extension
            domain = url.split("/")[2]
            title = f"Result from {domain}"

        # Create a result object with the URL as both title and snippet for now
        formatted_results.append(
            {
                "title": title,
                "url": url,
                "snippet": f"URL: {url}",  # Use URL as snippet since we don't have actual snippets
            }
        )

    # If no filter query provided, return all results
    if not filter_query:
        return formatted_results

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

    target_university = ""
    match = re.search(r'"([^"]*)".*"([^"]*)"', query)
    if match:
        # Assuming second quoted term is the target university
        target_university = match.group(2)

    for result in formatted_results:
        try:
            evaluation = chain.invoke(
                {
                    "filter_query": filter_query,
                    "title": result["title"],
                    "snippet": result["snippet"],
                    "target_university": target_university,
                }
            )

            if "HIGHLY RELEVANT" in evaluation.content.upper():
                filtered_results.append(result)
        except Exception as e:
            print(f"Error evaluating result {result['title']}: {str(e)}")

    # Double-check for relevance based on URL patterns that indicate official sources
    if target_university:
        for result in formatted_results:
            # Skip if already included
            if any(r["url"] == result["url"] for r in filtered_results):
                continue

            # Check if URL is from an official university domain or education authority
            url_lower = result["url"].lower()
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
                filtered_results.append(result)

    return filtered_results


google_search_tool = StructuredTool.from_function(
    func=google_search_with_filter,
    name="GoogleSearchFilter",
    description="Searches Google with the provided query and filters results based on relevance to a filter query.",
    args_schema=GoogleSearchSchema,
)
