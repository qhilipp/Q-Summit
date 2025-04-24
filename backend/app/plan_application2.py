# import module-function
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests
import secrets_
from bs4 import BeautifulSoup
from duckduckgo_search.exceptions import DuckDuckGoSearchException
from find_unis import SearchResult, google, scrape_text_from_url
from googlesearch import search
from langchain.prompts import ChatPromptTemplate
from langchain_community.tools import BraveSearch, DuckDuckGoSearchResults, Tool
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper, SearxSearchWrapper
from langchain_core.tools import StructuredTool
from langchain_openai import AzureChatOpenAI
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

llm = AzureChatOpenAI(
    deployment_name=secrets_.AZURE_OPENAI_DEPLOYMENT_NAME,
    openai_api_key=secrets_.AZURE_OPENAI_API_KEY,
    azure_endpoint=secrets_.AZURE_OPENAI_ENDPOINT,
    openai_api_version="2023-05-15",
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
    search_results = google(query, num_results=15)

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
    args_schema={"query": str, "filter_query": str},
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
    args_schema={"url": str, "query": str, "max_points": int},
)


# Define the state for our application planning agent
class ApplicationPlannerState(TypedDict):
    """State for the Application Planner Agent."""

    home_university: str
    target_university: str
    major: str
    search_results: List[Dict]
    analyzed_content: List[Dict]
    deadlines: List[Dict]
    documents: List[Dict]
    tasks: List[Dict]
    final_plan: Optional[Dict]


# Node functions for the application planner agent
def search_exchange_information(
    state: ApplicationPlannerState,
) -> ApplicationPlannerState:
    """
    Search for information about exchange programs between the two universities.
    """
    home_uni = state["home_university"]
    target_uni = state["target_university"]
    major = state["major"]

    # Create search queries
    queries = [
        f'"{home_uni}" exchange program semester abroad "{target_uni}"',
    ]

    # Store all search results
    all_results = []

    for query in queries:
        results = google_search_tool.invoke(
            {
                "query": query,
                "filter_query": "application process deadlines documents requirements",
            }
        )
        all_results.extend(results)

    # Remove duplicates based on URL
    unique_results = []
    seen_urls = set()

    for result in all_results:
        if result["url"] not in seen_urls:
            unique_results.append(result)
            seen_urls.add(result["url"])

    return {**state, "search_results": unique_results}


def analyze_search_results(state: ApplicationPlannerState) -> ApplicationPlannerState:
    """
    Analyze the search results to extract important information.
    """
    search_results = state["search_results"]
    home_uni = state["home_university"]
    target_uni = state["target_university"]
    major = state["major"]

    analyzed_content = []

    # Limit to top 5 most relevant results to avoid excessive processing
    for result in search_results[:5]:
        url = result["url"]

        try:
            # Use a single, combined extraction to avoid multiple tool calls
            combined_query = f"""
            For {home_uni} students applying to {target_uni} in {major}, provide information about:
            1. Application deadlines
            2. Required documents and application materials
            3. Step-by-step application process
            """

            # Extract information with a single call
            extraction = extract_important_points(
                url=url, query=combined_query, max_points=15
            )

            # Split the extracted points into categories based on content
            all_points = extraction.get("important_points", [])
            deadline_points = []
            document_points = []
            process_points = []

            for point in all_points:
                point_lower = point.lower()
                if (
                    "deadline" in point_lower
                    or "due" in point_lower
                    or "date" in point_lower
                ):
                    deadline_points.append(point)
                elif (
                    "document" in point_lower
                    or "application form" in point_lower
                    or "submit" in point_lower
                ):
                    document_points.append(point)
                else:
                    process_points.append(point)

            analyzed_content.append(
                {
                    "url": url,
                    "title": result["title"],
                    "deadline_info": deadline_points,
                    "document_info": document_points,
                    "process_info": process_points,
                }
            )

        except Exception as e:
            print(f"Error analyzing {url}: {str(e)}")
            # Add empty result to avoid breaking the flow
            analyzed_content.append(
                {
                    "url": url,
                    "title": result["title"],
                    "deadline_info": [],
                    "document_info": [],
                    "process_info": [],
                }
            )

    return {**state, "analyzed_content": analyzed_content}


def organize_information(state: ApplicationPlannerState) -> ApplicationPlannerState:
    """
    Organize the analyzed information into structured categories.
    """
    analyzed_content = state["analyzed_content"]

    # Extract and organize deadlines
    all_deadline_points = []
    for content in analyzed_content:
        all_deadline_points.extend(content["deadline_info"])

    # Extract and organize required documents
    all_document_points = []
    for content in analyzed_content:
        all_document_points.extend(content["document_info"])

    # Extract and organize tasks/steps
    all_process_points = []
    for content in analyzed_content:
        all_process_points.extend(content["process_info"])

    # Use LLM to clean up and remove duplicates
    template = """
    You are helping organize information about a semester abroad application process.
    
    Here is a list of extracted points about {category}:
    {points}
    
    Please:
    1. Remove any duplicates or highly similar points
    2. Organize them in a logical order (e.g., chronological for deadlines/tasks)
    3. Format each point as a JSON object with these fields:
       - description: The main information
       - source: The approximate source (if mentioned)
       - date: Any specific dates mentioned (if applicable)
       - priority: High/Medium/Low based on importance
    
    Return a list of JSON objects with these fields, and nothing else.
    """

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm

    # Process deadlines
    deadlines_result = chain.invoke(
        {"category": "application deadlines", "points": "\n".join(all_deadline_points)}
    )

    # Process documents
    documents_result = chain.invoke(
        {"category": "required documents", "points": "\n".join(all_document_points)}
    )

    # Process tasks
    tasks_result = chain.invoke(
        {
            "category": "application process steps",
            "points": "\n".join(all_process_points),
        }
    )

    # Parse results (basic parsing, may need more robust handling in production)
    import json

    try:
        deadlines = json.loads(deadlines_result.content)
    except:
        deadlines = [
            {
                "description": "Could not parse deadlines",
                "source": "N/A",
                "date": "N/A",
                "priority": "High",
            }
        ]

    try:
        documents = json.loads(documents_result.content)
    except:
        documents = [
            {
                "description": "Could not parse documents",
                "source": "N/A",
                "date": "N/A",
                "priority": "High",
            }
        ]

    try:
        tasks = json.loads(tasks_result.content)
    except:
        tasks = [
            {
                "description": "Could not parse tasks",
                "source": "N/A",
                "date": "N/A",
                "priority": "High",
            }
        ]

    return {**state, "deadlines": deadlines, "documents": documents, "tasks": tasks}


def create_final_plan(state: ApplicationPlannerState) -> ApplicationPlannerState:
    """
    Create a final, structured application plan.
    """
    home_uni = state["home_university"]
    target_uni = state["target_university"]
    major = state["major"]
    deadlines = state["deadlines"]
    documents = state["documents"]
    tasks = state["tasks"]

    # Create a comprehensive application plan
    template = """
    You are an expert advisor for international study abroad programs.
    
    Create a comprehensive application plan for a student from {home_uni} studying {major}
    who wants to do a semester abroad at {target_uni}.
    
    Use the following information:
    
    DEADLINES:
    {deadlines}
    
    REQUIRED DOCUMENTS:
    {documents}
    
    APPLICATION STEPS:
    {tasks}
    
    Create a structured application plan with these sections:
    1. Summary: Brief overview of the application process
    2. Timeline: Chronological list of deadlines and when tasks should be completed
    3. Document Checklist: List of all required documents with descriptions
    4. Step-by-Step Guide: Detailed steps to complete the application
    5. Tips and Recommendations: Advice for a successful application
    
    Format the response as a JSON object with these 5 sections as keys.
    For the timeline, organize events chronologically with specific dates when available.
    """

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm

    import json

    plan_result = chain.invoke(
        {
            "home_uni": home_uni,
            "target_uni": target_uni,
            "major": major,
            "deadlines": json.dumps(deadlines),
            "documents": json.dumps(documents),
            "tasks": json.dumps(tasks),
        }
    )

    # Parse the final plan
    try:
        final_plan = json.loads(plan_result.content)
    except:
        # Fallback if parsing fails
        final_plan = {
            "summary": "Error creating formatted plan. Please see raw data.",
            "timeline": deadlines,
            "document_checklist": documents,
            "step_by_step_guide": tasks,
            "tips_and_recommendations": [
                "Could not generate tips due to processing error."
            ],
        }

    return {**state, "final_plan": final_plan}


# Create the application planner agent
def create_application_planner_agent():
    """
    Create and return the application planner agent.
    """
    # Create a new graph
    workflow = StateGraph(ApplicationPlannerState)

    # Add nodes
    workflow.add_node("search", search_exchange_information)
    workflow.add_node("analyze", analyze_search_results)
    workflow.add_node("organize", organize_information)
    workflow.add_node("plan", create_final_plan)

    # Add edges
    workflow.add_edge(START, "search")
    workflow.add_edge("search", "analyze")
    workflow.add_edge("analyze", "organize")
    workflow.add_edge("organize", "plan")
    workflow.add_edge("plan", END)

    # Compile the graph
    app_planner = workflow.compile()

    return app_planner


# Function to run the application planner
def plan_semester_abroad_application(
    home_university: str, target_university: str, major: str
) -> Dict:
    """
    Plan the application process for a semester abroad.

    Args:
        home_university: The university where the student is enrolled
        target_university: The university where the student wants to study abroad
        major: The student's field of study

    Returns:
        A structured application plan with timeline, documents, steps, and tips
    """
    # Create the agent
    app_planner = create_application_planner_agent()

    # Initialize the state
    initial_state = {
        "home_university": home_university,
        "target_university": target_university,
        "major": major,
        "search_results": [],
        "analyzed_content": [],
        "deadlines": [],
        "documents": [],
        "tasks": [],
        "final_plan": None,
    }

    # Run the agent
    result = app_planner.invoke(initial_state)

    # Return the final plan
    return result["final_plan"]


# Test the application planner if running this file directly
if __name__ == "__main__":
    import json
    import time

    # Test parameters
    home_university = "University of Toronto"
    target_university = "University of California Berkeley"
    major = "Computer Science"

    print(f"\n{'=' * 80}")
    print(
        f"Planning semester abroad application from {home_university} to {target_university}"
    )
    print(f"Major: {major}")
    print(f"{'=' * 80}\n")

    # Start the timer
    start_time = time.time()

    print("Searching and analyzing information. This may take a few minutes...\n")

    # Run the planner
    plan = plan_semester_abroad_application(
        home_university=home_university,
        target_university=target_university,
        major=major,
    )

    # Calculate elapsed time
    elapsed_time = time.time() - start_time

    # Print the plan in a nicely formatted way
    print(f"\n{'=' * 80}")
    print("APPLICATION PLAN SUMMARY")
    print(f"{'=' * 80}\n")

    # Print summary section
    print("📋 SUMMARY")
    print(f"{'-' * 80}")
    print(plan.get("summary", "No summary available."))
    print()

    # Print timeline section
    print("📅 TIMELINE")
    print(f"{'-' * 80}")
    timeline = plan.get("timeline", [])
    if isinstance(timeline, list):
        for i, item in enumerate(timeline, 1):
            date = item.get("date", "No date specified")
            desc = item.get("description", "No description")
            print(f"{i}. [{date}] {desc}")
    else:
        print(timeline)
    print()

    # Print document checklist
    print("📄 DOCUMENT CHECKLIST")
    print(f"{'-' * 80}")
    documents = plan.get("document_checklist", [])
    if isinstance(documents, list):
        for i, doc in enumerate(documents, 1):
            desc = doc.get("description", "No description")
            priority = doc.get("priority", "")
            print(f"{i}. {desc} {f'[{priority}]' if priority else ''}")
    else:
        print(documents)
    print()

    # Print step-by-step guide
    print("🔍 STEP-BY-STEP GUIDE")
    print(f"{'-' * 80}")
    steps = plan.get("step_by_step_guide", [])
    if isinstance(steps, list):
        for i, step in enumerate(steps, 1):
            desc = step.get("description", "No description")
            print(f"{i}. {desc}")
    else:
        print(steps)
    print()

    # Print tips and recommendations
    print("💡 TIPS AND RECOMMENDATIONS")
    print(f"{'-' * 80}")
    tips = plan.get("tips_and_recommendations", [])
    if isinstance(tips, list):
        for i, tip in enumerate(tips, 1):
            if isinstance(tip, dict):
                print(f"{i}. {tip.get('description', str(tip))}")
            else:
                print(f"{i}. {tip}")
    else:
        print(tips)

    print(f"\n{'=' * 80}")
    print(f"Plan generated in {elapsed_time:.2f} seconds")
    print(f"{'=' * 80}")

    # Option to save the plan to a file
    save_option = input("\nWould you like to save this plan to a file? (y/n): ")
    if save_option.lower() == "y":
        filename = f"semester_abroad_plan_{home_university.replace(' ', '_')}_to_{target_university.replace(' ', '_')}.json"
        with open(filename, "w") as f:
            json.dump(plan, f, indent=2)
        print(f"Plan saved to {filename}")
