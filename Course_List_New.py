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
    top_home_courses: List[Course]
    top_foreign_courses: List[Course]
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

def determine_credit_conversion(home_courses: List[Course], foreign_courses: List[Course]) -> float:
    """Determine the credit conversion ratio between universities."""
    template = """
    Determine the credit conversion ratio between {home_university} and {foreign_university} based on the following course credit information:
    
    {home_university} courses:
    {home_credits}
    
    {foreign_university} courses:
    {foreign_credits}
    
    Based on this information, estimate the conversion ratio as a single number:
    1 {foreign_university} credit = ? {home_university} credits
    
    Consider standard credit systems like ECTS (European Credit Transfer System) if applicable.
    Return ONLY the numerical ratio as a decimal number (e.g., 1.5, 0.75, etc.).
    """

    # Sample up to 5 courses from each university for the analysis
    home_sample = home_courses[:5]
    foreign_sample = foreign_courses[:5]
    
    home_university = home_sample[0].university if home_sample else "Home University"
    foreign_university = foreign_sample[0].university if foreign_sample else "Foreign University"
    
    home_credits_text = "\n".join([f"{course.course_id} - {course.title}: {course.credits} credits" for course in home_sample])
    foreign_credits_text = "\n".join([f"{course.course_id} - {course.title}: {course.credits} credits" for course in foreign_sample])

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm
    result = chain.invoke({
        "home_university": home_university,
        "foreign_university": foreign_university,
        "home_credits": home_credits_text,
        "foreign_credits": foreign_credits_text
    })

    # Extract the ratio from the response
    try:
        ratio = float(re.search(r'(\d+\.\d+|\d+)', result.content).group(0))
        return ratio
    except:
        print("Could not determine credit conversion ratio, using 1.0")
        return 1.0

def calculate_course_similarity(home_course: Course, foreign_course: Course, credit_ratio: float) -> Dict[str, Any]:
    """Calculate similarity between two courses based on description and credits."""
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
    
    Consider:
    1. Content similarity (topics covered)
    2. Learning outcomes
    3. Depth and breadth of material
    4. Credit equivalence (after conversion)
    
    Return a JSON object:
    {{
        "similarity_score": A number between 0-100,
        "content_overlap": "Description of content similarities and differences",
        "credit_match": true/false,
        "recommendation": "Recommend/Do not recommend for credit transfer"
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

def select_top_courses_by_name_similarity(courses: List[Course], target_subject: str, limit: int = 5) -> List[Course]:
    """Select top courses most relevant to the target subject based on course name."""
    template = """
    Rate how relevant the following course is to the subject "{target_subject}" on a scale of 0-100:
    
    Course: {course_title}
    Description: {course_description}
    
    Return ONLY a number between 0-100 representing the relevance score.
    """

    course_scores = []
    
    for course in courses[:10]:  # Limit initial analysis to 10 courses
        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | llm
        result = chain.invoke({
            "target_subject": target_subject,
            "course_title": course.title,
            "course_description": course.description
        })
        
        # Extract score from response
        try:
            score = int(re.search(r'(\d+)', result.content).group(0))
            course_scores.append((course, score))
        except:
            course_scores.append((course, 0))
    
    # Sort by score (descending) and return top courses
    course_scores.sort(key=lambda x: x[1], reverse=True)
    return [course for course, _ in course_scores[:limit]]

# Agent steps
def find_departments_step(state: AgentState) -> AgentState:
    """Find relevant departments at the foreign university"""
    try:
        foreign_university = state["foreign_university"]
        foreign_subject = state["foreign_subject"]
        
        print(f"Searching for departments at {foreign_university} related to {foreign_subject}...")
        
        # Search for departments that offer courses in the subject
        query = f"{foreign_university} {foreign_subject} department course catalog"
        results = google(query)
        
        # Filter for relevance
        relevant_results = [r for r in results if is_relevant_department_page(r, foreign_university, foreign_subject)]
        print(f"Found {len(relevant_results)} relevant search results")
        
        # Extract departments from each relevant result
        all_departments = []
        for result in relevant_results[:3]:  # Limit to first 3 results
            text = scrape_text_from_url(result.url)
            departments = extract_departments(text, foreign_university, foreign_subject)
            all_departments.extend(departments)
        
        # Remove duplicates by department name
        unique_departments = []
        dept_names = set()
        for dept in all_departments:
            name = dept["department_name"]
            if name not in dept_names:
                dept_names.add(name)
                unique_departments.append(dept)
        
        print(f"Found {len(unique_departments)} departments at {foreign_university}")
        
        # Filter to departments with high or medium relevance
        relevant_departments = [
            dept for dept in unique_departments 
            if dept.get("relevance_to_subject", "Low") in ["High", "Medium"]
        ]
        
        if not relevant_departments:
            # If no relevant departments found, use all unique departments
            relevant_departments = unique_departments
        
        return {**state, "departments_found": relevant_departments}
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
                ),
                Course(
                    title="Database Systems for Business",
                    description="Design and implementation of database systems for business applications, including data modeling and SQL.",
                    credits=6.0,
                    department=home_department,
                    university=home_university,
                    course_id="BI-203"
                ),
                Course(
                    title="Business Process Management",
                    description="Modeling, analysis, and optimization of business processes using information technology.",
                    credits=6.0,
                    department=home_department,
                    university=home_university,
                    course_id="BI-301"
                ),
                Course(
                    title="IT Project Management",
                    description="Planning, executing, and controlling IT projects in business contexts.",
                    credits=6.0,
                    department=home_department,
                    university=home_university,
                    course_id="BI-302"
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
                ),
                Course(
                    title="Data Structures and Algorithms",
                    description="Advanced data structures and algorithms for efficient problem solving.",
                    credits=4.0,
                    department="Computer Science",
                    university=foreign_university,
                    course_id="CS170"
                ),
                Course(
                    title="Software Engineering",
                    description="Principles and practices of software development, including design patterns and project management.",
                    credits=4.0,
                    department="Computer Science",
                    university=foreign_university,
                    course_id="CS169"
                ),
                Course(
                    title="Artificial Intelligence",
                    description="Introduction to AI concepts including search, knowledge representation, and machine learning.",
                    credits=4.0,
                    department="Computer Science",
                    university=foreign_university,
                    course_id="CS188"
                )
            ]
        
        # Determine credit conversion ratio
        credit_ratio = 1.0
        if home_courses and foreign_courses:
            credit_ratio = determine_credit_conversion(home_courses, foreign_courses)
            print(f"Credit conversion ratio: {credit_ratio}")
        
        # Select top 5 courses from each university based on subject relevance
        top_home_courses = select_top_courses_by_name_similarity(
            home_courses, state["home_subject"], 5
        )
        
        top_foreign_courses = select_top_courses_by_name_similarity(
            foreign_courses, state["foreign_subject"], 5
        )
            
        return {
            **state, 
            "home_courses": home_courses,
            "foreign_courses": foreign_courses,
            "top_home_courses": top_home_courses,
            "top_foreign_courses": top_foreign_courses,
            "credit_conversion_ratio": credit_ratio
        }
    except Exception as e:
        import traceback
        print(f"Error in find_courses_step: {str(e)}")
        print(traceback.format_exc())
        return {**state, "error": f"Course search error: {str(e)}"}

def compare_courses_step(state: AgentState) -> AgentState:
    """Compare the top 5 courses from each university"""
    if state.get("error"):
        return state
        
    try:
        top_home_courses = state["top_home_courses"]
        top_foreign_courses = state["top_foreign_courses"]
        credit_ratio = state.get("credit_conversion_ratio", 1.0)
        
        if not top_home_courses or not top_foreign_courses:
            return {**state, "error": "No top courses found to compare"}
            
        # Compare each top home course with each top foreign course
        all_comparisons = []
        
        print(f"Comparing {len(top_home_courses)} home courses with {len(top_foreign_courses)} foreign courses")
        
        for home_course in top_home_courses:
            for foreign_course in top_foreign_courses:
                print(f"Comparing {home_course.title} with {foreign_course.title}")
                comparison = calculate_course_similarity(home_course, foreign_course, credit_ratio)
                all_comparisons.append(comparison)
        
        # Sort by similarity score (descending)
        all_comparisons.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        # Take top 3 matches instead of 5
        top_matches = all_comparisons[:3]
        
        # Simplify for final output
        simplified_matches = []
        for match in top_matches:
            simplified_matches.append({
                "home_course": match["home_course"]["title"],
                "foreign_course": match["foreign_course"]["title"],
                "similarity_score": match["similarity_score"],
                "recommendation": match["recommendation"]
            })
            
        return {**state, "matched_courses": simplified_matches}
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
        "top_home_courses": [],
        "top_foreign_courses": [],
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
    
    # Parse the JSON into an object if needed
    try:
        result_obj = json.loads(result)
        print(f"Found {len(result_obj.get('matches', []))} course matches")
    except json.JSONDecodeError:
        print("Could not parse result as JSON")
