import os
import time
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

import requests
from bs4 import BeautifulSoup
from googlesearch import search
from langchain.prompts import ChatPromptTemplate
from langchain_community.tools import Tool
from langchain_openai import AzureChatOpenAI
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

# Azure OpenAI settings
os.environ["AZURE_OPENAI_API_KEY"] = (
    "3dGOevJLCqCICD702vTM0IhgtOIOUYo0knUBg2CrDry7HxVIixJyJQQJ99BDAC5RqLJXJ3w3AAABACOGtVw3"
)
os.environ["AZURE_OPENAI_ENDPOINT"] = (
    "https://openairesourcetest123123.openai.azure.com/"
)
os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "gpt-4o-mini"

llm = AzureChatOpenAI(
    deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
    openai_api_key=os.environ["AZURE_OPENAI_API_KEY"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    openai_api_version="2023-05-15",
)

# Data structures
@dataclass
class Course:
    title: str
    description: str
    credits: float
    department: str
    university: str
    course_id: str
    url: Optional[str] = None

@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str

class AgentState(TypedDict):
    home_university: str
    home_department: str
    foreign_university: str
    study_terms: List[str]
    home_subject: str
    foreign_subject: str
    credit_conversion_ratio: Optional[float]
    departments_found: List[Dict[str, Any]]
    home_courses: List[Course]
    foreign_courses: List[Course]
    matched_courses: List[Dict[str, Any]]
    error: Optional[str]
    final_response: Optional[str]

# Helper functions
def google(query: str):
    google_search = search(query, advanced=True)
    return [
        SearchResult(title=result.title, url=result.url, snippet=result.description)
        for result in google_search
    ]

def scrape_text_from_url(url: str):
    try:
        response = requests.get(url, timeout=10)
        return BeautifulSoup(response.text, "html.parser").get_text()
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return ""

def is_relevant_department_page(result: SearchResult, foreign_university: str, subject: str) -> bool:
    """Use LLM to determine if a search result is likely to contain department information."""
    template = """
    Evaluate if the following search result is likely to contain information about academic departments, 
    course listings, or course catalogs for the subject {subject} at {university}.
    
    Title: {title}
    Description: {snippet}
    URL: {url}
    
    Respond with ONLY 'YES' if the content seems relevant to finding course information or 'NO' if it does not.
    """

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm
    result_text = chain.invoke({
        "title": result.title,
        "snippet": result.snippet,
        "url": result.url,
        "university": foreign_university,
        "subject": subject
    })

    return "YES" in result_text.content.upper()

def extract_departments(text: str, university: str, subject: str) -> List[Dict[str, Any]]:
    """Use LLM to extract department information."""
    template = """
    Extract all academic departments or schools at {university} that might offer courses related to {subject}.
    For each department, identify its name, website URL (if present in the text), and any mention of course catalogs.
    
    Text: {text}
    
    Return your response as a JSON array of departments:
    [
        {{
            "department_name": "Department name",
            "department_url": "URL if available, otherwise null",
            "course_catalog_url": "URL to course listings if available, otherwise null",
            "relevance_to_subject": "High/Medium/Low"
        }}
    ]
    
    If no departments are found, return an empty array.
    """

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm
    result = chain.invoke({"text": text, "university": university, "subject": subject})

    # Extract JSON from response
    try:
        departments = json.loads(re.search(r'\[.*\]', result.content, re.DOTALL).group(0))
        return departments
    except:
        return []

def extract_courses(text: str, department: str, university: str) -> List[Course]:
    """Use LLM to extract course information from text."""
    template = """
    Extract all courses from the {department} at {university} in the following text.
    For each course, identify:
    1. Course title
    2. Course ID/code
    3. Credits/units
    4. Description
    
    Text: {text}
    
    Return your response as a JSON array of courses:
    [
        {{
            "course_id": "Course code",
            "title": "Course title",
            "credits": "Number of credits as a number (convert to numerical format)",
            "description": "Course description"
        }}
    ]
    
    If no courses are found, return an empty array.
    """

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm
    result = chain.invoke({"text": text, "department": department, "university": university})

    # Extract JSON from response
    try:
        course_data = json.loads(re.search(r'\[.*\]', result.content, re.DOTALL).group(0))
        courses = []
        for data in course_data:
            try:
                # Convert credits to float
                credits = float(data.get("credits", 0))
            except:
                credits = 0.0
                
            courses.append(Course(
                title=data.get("title", ""),
                description=data.get("description", ""),
                credits=credits,
                department=department,
                university=university,
                course_id=data.get("course_id", "")
            ))
        return courses
    except Exception as e:
        print(f"Error extracting courses: {str(e)}")
        return []

def calculate_course_similarity(home_course: Course, foreign_course: Course, credit_ratio: float) -> Dict[str, Any]:
    """Calculate similarity between two courses with enhanced scoring."""
    template = """
    Compare the following two courses and determine their similarity:
    
    COURSE 1 ({home_university}):
    ID: {home_id}
    Title: {home_title}
    Credits: {home_credits}
    Description: {home_description}
    
    COURSE 2 ({foreign_university}):
    ID: {foreign_id}
    Title: {foreign_title}
    Credits: {foreign_credits} (equivalent to {converted_credits} {home_university} credits)
    Description: {foreign_description}
    
    Consider the following factors with the given weights:
    1. Subject matter overlap (50%): Assess how similar the core topics and content areas are
    2. Academic level (20%): Whether both are introductory, intermediate, or advanced courses
    3. Learning objectives (20%): Similarity in what students are expected to learn
    4. Credit equivalence (10%): How close the credit values are after conversion
    
    Analyze specific keywords, topics, and concepts that appear in both descriptions.
    
    Return a JSON object:
    {{
        "similarity_score": A number between 0-100, with detailed justification for the score,
        "content_overlap": "Detailed analysis of specific shared topics and concepts",
        "key_differences": "Important differences in content or approach",
        "credit_match": true/false,
        "recommendation": "Strongly recommend/Recommend/Do not recommend for credit transfer with explicit reasoning"
    }}
    """

    # Convert foreign credits to home university equivalent
    converted_credits = foreign_course.credits * credit_ratio

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm
    result = chain.invoke({
        "home_university": home_course.university,
        "foreign_university": foreign_course.university,
        "home_id": home_course.course_id,
        "home_title": home_course.title,
        "home_credits": home_course.credits,
        "home_description": home_course.description,
        "foreign_id": foreign_course.course_id,
        "foreign_title": foreign_course.title,
        "foreign_credits": foreign_course.credits,
        "converted_credits": converted_credits,
        "foreign_description": foreign_course.description
    })

    # Extract JSON from response
    try:
        similarity_data = json.loads(re.search(r'{.*}', result.content, re.DOTALL).group(0))
        return {
            "home_course": {
                "university": home_course.university,
                "course_id": home_course.course_id,
                "title": home_course.title,
                "credits": home_course.credits
            },
            "foreign_course": {
                "university": foreign_course.university,
                "course_id": foreign_course.course_id,
                "title": foreign_course.title, 
                "credits": foreign_course.credits,
                "converted_credits": converted_credits
            },
            "similarity_score": similarity_data.get("similarity_score", 0),
            "content_overlap": similarity_data.get("content_overlap", ""),
            "key_differences": similarity_data.get("key_differences", ""),
            "credit_match": similarity_data.get("credit_match", False),
            "recommendation": similarity_data.get("recommendation", "")
        }
    except Exception as e:
        print(f"Error parsing similarity result: {str(e)}")
        return {
            "home_course": {"university": home_course.university, "course_id": home_course.course_id, "title": home_course.title},
            "foreign_course": {"university": foreign_course.university, "course_id": foreign_course.course_id, "title": foreign_course.title},
            "similarity_score": 0,
            "content_overlap": "Error analyzing similarity",
            "credit_match": False,
            "recommendation": "No recommendation due to error"
        }

def select_top_courses_by_relevance(courses: List[Course], subject: str) -> List[Course]:
    """Select top courses based on relevance to subject using improved selection."""
    template = """
    Rank the following courses based on their relevance to {subject}:
    
    {course_list}
    
    For each course, consider:
    1. How directly the course title relates to {subject}
    2. How many key concepts from {subject} appear in the description
    3. Whether the course provides fundamental or specialized knowledge in {subject}
    
    Return only a JSON array with the course IDs ranked from most to least relevant:
    [
      "ID1",
      "ID2",
      "ID3",
      ...
    ]
    """
    
    # Create a formatted list of courses with their details
    course_details = []
    for i, course in enumerate(courses):
        course_details.append(f"Course {i+1}:\nID: {course.course_id}\nTitle: {course.title}\nDescription: {course.description}\n")
    
    course_list = "\n".join(course_details)
    
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm
    result = chain.invoke({
        "subject": subject,
        "course_list": course_list
    })
    
    try:
        # Extract JSON array of course IDs
        ranked_ids = json.loads(re.search(r'\[.*\]', result.content, re.DOTALL).group(0))
        
        # Match IDs to courses and create ranked list
        id_to_course = {course.course_id: course for course in courses}
        ranked_courses = [id_to_course[course_id] for course_id in ranked_ids if course_id in id_to_course]
        
        # Return top 5 (or all if fewer)
        return ranked_courses[:5]
    except Exception as e:
        print(f"Error ranking courses: {str(e)}")
        # Fallback to random selection
        import random
        random_courses = courses.copy()
        random.shuffle(random_courses)
        return random_courses[:min(5, len(random_courses))]

def determine_credit_conversion(home_courses: List[Course], foreign_courses: List[Course]) -> float:
    """Determine credit conversion ratio more accurately using academic standards research."""
    template = """
    Determine the credit conversion ratio between {home_university} and {foreign_university} based on:
    
    Home University ({home_university}) course credits:
    {home_credits}
    
    Foreign University ({foreign_university}) course credits:
    {foreign_credits}
    
    Consider:
    1. The typical ranges of credits at each university
    2. International credit standards (ECTS in Europe, semester hours in US)
    3. The typical workload represented by each credit
    
    Return only a JSON object:
    {{
      "conversion_ratio": The numerical ratio to convert from foreign to home credits,
      "explanation": "Brief explanation of your calculation"
    }}
    """
    
    # Extract credit ranges
    home_credit_examples = [f"{course.title}: {course.credits}" for course in home_courses[:5]]
    foreign_credit_examples = [f"{course.title}: {course.credits}" for course in foreign_courses[:5]]
    
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm
    result = chain.invoke({
        "home_university": home_courses[0].university if home_courses else "Home University",
        "foreign_university": foreign_courses[0].university if foreign_courses else "Foreign University",
        "home_credits": "\n".join(home_credit_examples),
        "foreign_credits": "\n".join(foreign_credit_examples)
    })
    
    try:
        conversion_data = json.loads(re.search(r'{.*}', result.content, re.DOTALL).group(0))
        ratio = float(conversion_data.get("conversion_ratio", 1.0))
        print(f"Credit conversion ratio: {ratio} - {conversion_data.get('explanation', '')}")
        return ratio
    except Exception as e:
        print(f"Error determining credit conversion: {str(e)}")
        # Fallback to standard conversion
        # If no direct conversion possible, estimate based on averages
        avg_home = sum(c.credits for c in home_courses) / len(home_courses) if home_courses else 3.0
        avg_foreign = sum(c.credits for c in foreign_courses) / len(foreign_courses) if foreign_courses else 3.0
        return avg_home / avg_foreign if avg_foreign > 0 else 1.0

# Agent workflow nodes
def find_departments_step(state: AgentState) -> AgentState:
    """Find relevant departments at the foreign university"""
    try:
        foreign_university = state["foreign_university"]
        foreign_subject = state["foreign_subject"]
        
        # Search for departments
        query = f"{foreign_university} {foreign_subject} department courses catalog"
        search_results = google(query)
        
        # Filter relevant results
        relevant_results = [
            r for r in search_results 
            if is_relevant_department_page(r, foreign_university, foreign_subject)
        ]
        
        all_departments = []
        for result in relevant_results[:3]:  # Limit to top 3 to avoid rate limits
            try:
                text = scrape_text_from_url(result.url)
                departments = extract_departments(text, foreign_university, foreign_subject)
                all_departments.extend(departments)
            except Exception as e:
                print(f"Error processing {result.url}: {str(e)}")
                
        # Remove duplicates based on department name
        unique_departments = []
        department_names = set()
        for dept in all_departments:
            if dept["department_name"] not in department_names:
                department_names.add(dept["department_name"])
                unique_departments.append(dept)
        
        return {**state, "departments_found": unique_departments}
    except Exception as e:
        return {**state, "error": f"Department search error: {str(e)}"}

def find_courses_step(state: AgentState) -> AgentState:
    """Find courses for both home and foreign universities"""
    if state.get("error"):
        return state
        
    try:
        home_university = state["home_university"]
        home_department = state["home_department"] 
        foreign_university = state["foreign_university"]
        departments_found = state["departments_found"]
        
        print(f"Searching for courses at {home_university} and {foreign_university}...")
        
        # Get home university courses
        home_query = f"{home_university} {home_department} course catalog descriptions"
        print(f"Searching for home courses: {home_query}")
        home_results = google(home_query)
        print(f"Found {len(home_results)} home university search results")
        
        home_courses = []
        for result in home_results[:3]:  # Try more results
            print(f"Processing {result.url}")
            text = scrape_text_from_url(result.url)
            if text:
                courses = extract_courses(text, home_department, home_university)
                if courses:
                    print(f"Found {len(courses)} courses at {result.url}")
                    home_courses.extend(courses)
        
        # If no courses found, try a more general search
        if not home_courses:
            print("No home courses found, trying alternate search...")
            alt_query = f"{home_university} course catalog {home_department}"
            alt_results = google(alt_query)
            
            for result in alt_results[:3]:
                text = scrape_text_from_url(result.url)
                if text:
                    courses = extract_courses(text, home_department, home_university)
                    if courses:
                        home_courses.extend(courses)
        
        print(f"Total home courses found: {len(home_courses)}")
        
        # Get foreign university courses
        foreign_courses = []
        for dept in departments_found:
            dept_name = dept["department_name"]
            print(f"Searching for courses in {dept_name} at {foreign_university}")
            
            # First try course catalog URL if available
            if dept.get("course_catalog_url") and dept["course_catalog_url"] != "null":
                url = dept["course_catalog_url"]
                print(f"Using course catalog URL: {url}")
                text = scrape_text_from_url(url)
                if text:
                    courses = extract_courses(text, dept_name, foreign_university)
                    if courses:
                        print(f"Found {len(courses)} courses at {url}")
                        foreign_courses.extend(courses)
            
            # If no courses found from catalog URL, search for them
            if not foreign_courses:
                foreign_query = f"{foreign_university} {dept_name} courses syllabus"
                print(f"Searching for foreign courses: {foreign_query}")
                foreign_results = google(foreign_query)
                
                for result in foreign_results[:3]:
                    print(f"Processing {result.url}")
                    text = scrape_text_from_url(result.url)
                    if text:
                        courses = extract_courses(text, dept_name, foreign_university)
                        if courses:
                            print(f"Found {len(courses)} courses at {result.url}")
                            foreign_courses.extend(courses)
        
        print(f"Total foreign courses found: {len(foreign_courses)}")
        
        # If still no courses, use fake sample data for testing
        if not home_courses:
            print("WARNING: Using sample home courses for testing")
            home_courses = [
                Course(
                    title="Introduction to Business Informatics",
                    description="Fundamental concepts of business information systems, including database design, business processes, and information management.",
                    credits=6.0,
                    department=home_department,
                    university=home_university,
                    course_id="BI-101"
                ),
                Course(
                    title="Data Analytics for Business",
                    description="Statistical methods and tools for analyzing business data and making data-driven decisions.",
                    credits=6.0,
                    department=home_department,
                    university=home_university,
                    course_id="BI-202"
                )
            ]
        
        if not foreign_courses:
            print("WARNING: Using sample foreign courses for testing")
            foreign_courses = [
                Course(
                    title="Introduction to Computer Science",
                    description="Fundamentals of computer science, including programming, algorithms, and data structures.",
                    credits=4.0,
                    department="Computer Science",
                    university=foreign_university,
                    course_id="CS101"
                ),
                Course(
                    title="Database Systems",
                    description="Design and implementation of database systems, including data modeling, SQL, and transaction processing.",
                    credits=4.0,
                    department="Computer Science",
                    university=foreign_university,
                    course_id="CS186"
                )
            ]
        
        # Determine credit conversion ratio
        credit_ratio = 1.0
        if home_courses and foreign_courses:
            credit_ratio = determine_credit_conversion(home_courses, foreign_courses)
            print(f"Credit conversion ratio: {credit_ratio}")
            
        return {
            **state, 
            "home_courses": home_courses, 
            "foreign_courses": foreign_courses,
            "credit_conversion_ratio": credit_ratio
        }
    except Exception as e:
        import traceback
        print(f"Error in find_courses_step: {str(e)}")
        print(traceback.format_exc())
        return {**state, "error": f"Course search error: {str(e)}"}

def compare_courses_step(state: AgentState) -> AgentState:
    """Compare courses and find the best matches"""
    if state.get("error"):
        return state
        
    try:
        home_courses = state["home_courses"]
        foreign_courses = state["foreign_courses"]
        credit_ratio = state.get("credit_conversion_ratio", 1.0)
        
        if not home_courses or not foreign_courses:
            return {**state, "error": "No courses found to compare"}
            
        # Compare each home course with each foreign course (O(n²))
        all_comparisons = []
        
        # Limit to prevent too many API calls
        home_sample = home_courses[:5]
        foreign_sample = foreign_courses[:5]
        
        for home_course in home_sample:
            for foreign_course in foreign_sample:
                comparison = calculate_course_similarity(home_course, foreign_course, credit_ratio)
                all_comparisons.append(comparison)
        
        # Sort by similarity score (descending)
        all_comparisons.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        # Take top 12 matches
        top_matches = all_comparisons[:12]
            
        return {**state, "matched_courses": top_matches}
    except Exception as e:
        return {**state, "error": f"Course comparison error: {str(e)}"}

def generate_response_step(state: AgentState) -> AgentState:
    """Generate a final response with the matched courses"""
    if state.get("error"):
        return {**state, "final_response": f"Error: {state['error']}"}
        
    try:
        matches = state.get("matched_courses", [])
        home_university = state["home_university"]
        foreign_university = state["foreign_university"]
        credit_ratio = state.get("credit_conversion_ratio", 1.0)
        
        if not matches:
            return {**state, "final_response": "No matching courses found."}
            
        # Create summary response
        result = {
            "home_university": home_university,
            "foreign_university": foreign_university,
            "credit_conversion_ratio": credit_ratio,
            "matches": matches
        }
            
        return {**state, "final_response": json.dumps(result, indent=2)}
    except Exception as e:
        return {**state, "final_response": f"Error generating response: {str(e)}"}

# Initialize the agent workflow
def initialize_agent() -> StateGraph:
    """Initialize the agent workflow."""
    workflow = StateGraph(AgentState)
    
    # Define the nodes
    workflow.add_node("find_departments", find_departments_step)
    workflow.add_node("find_courses", find_courses_step)
    workflow.add_node("compare_courses", compare_courses_step)
    workflow.add_node("generate_response", generate_response_step)
    
    # Connect the nodes
    workflow.add_edge("find_departments", "find_courses")
    workflow.add_edge("find_courses", "compare_courses")
    workflow.add_edge("compare_courses", "generate_response")
    workflow.add_edge("generate_response", END)
    
    # Set the entry point
    workflow.set_entry_point("find_departments")
    
    return workflow

def find_similar_courses(input_data: dict) -> str:
    """
    Main function to find similar courses between universities.
    
    Input format:
    {
        "home_university": string,
        "home_department": string,
        "foreign_university": string,
        "study_terms": [string],
        "home_subject": string,
        "foreign_subject": string
    }
    """
    # Initialize the agent
    workflow = initialize_agent()
    
    # Compile the graph into a runnable app
    app = workflow.compile()
    
    # Run the agent
    initial_state: AgentState = {
        "home_university": input_data.get("home_university", ""),
        "home_department": input_data.get("home_department", ""),
        "foreign_university": input_data.get("foreign_university", ""),
        "study_terms": input_data.get("study_terms", []),
        "home_subject": input_data.get("home_subject", ""),
        "foreign_subject": input_data.get("foreign_subject", ""),
        "credit_conversion_ratio": None,
        "departments_found": [],
        "home_courses": [],
        "foreign_courses": [],
        "matched_courses": [],
        "error": None,
        "final_response": None
    }
    
    # Execute the workflow using the compiled app
    final_state = app.invoke(initial_state)
    
    # Return the final response
    return final_state.get("final_response", "Process completed without a response.")

if __name__ == "__main__":
    # Example usage
    sample_input = {
        "home_university": "University of Münster",
        "home_department": "Business Information Systems",
        "foreign_university": "University of California, Santa Barbara",
        "study_terms": ["Fall 2024"],
        "home_subject": "Business Informatics",
        "foreign_subject": "Computer Science"
    }
    
    result = find_similar_courses(sample_input)
    print(result)
