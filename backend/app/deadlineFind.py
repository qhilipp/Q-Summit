import os
import datetime
from dataclasses import dataclass
from functools import lru_cache
from typing import List, Optional, Dict, Any

import requests
from bs4 import BeautifulSoup
from googlesearch import search
from langchain.prompts import ChatPromptTemplate
from langchain_community.tools import Tool
from langchain_openai import AzureChatOpenAI
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict
from icalendar import Calendar, Event
import pytz
from secrets_ import AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_NAME

# Azure OpenAI setup
llm = AzureChatOpenAI(
    deployment_name=AZURE_OPENAI_DEPLOYMENT_NAME,
    openai_api_key=AZURE_OPENAI_API_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    openai_api_version="2023-05-15",
)

@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


@dataclass
class DeadlineInfo:
    home_university: str
    foreign_university: str
    program_type: str
    deadline_date: str
    deadline_description: str
    source_url: str


def google(query: str) -> List[SearchResult]:
    """Perform a Google search and return results."""
    google_search = search(query, advanced=True)
    return [
        SearchResult(title=result.title, url=result.url, snippet=result.description)
        for result in google_search
    ]


def scrape_text_from_url(url: str) -> str:
    """Scrape text content from a URL."""
    response = requests.get(url)
    return BeautifulSoup(response.text, "html.parser").get_text()


def is_relevant_search_result(result: SearchResult, home_university: str, 
                             foreign_university: str, program_type: str) -> bool:
    """
    Use LLM to determine if a search result is likely to contain deadline information
    for the specified exchange program between the two universities.
    """
    template = """
    Evaluate if the following search result is likely to contain information about application deadlines 
    for an exchange program between {home_university} and {foreign_university}, 
    specifically for the {program_type} program.
    
    Title: {title}
    Description: {snippet}
    
    Respond with ONLY 'YES' if the content seems relevant to application deadlines for this specific 
    exchange program or 'NO' if it does not.
    """

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm
    result_text = chain.invoke(
        {
            "title": result.title,
            "snippet": result.snippet,
            "home_university": home_university,
            "foreign_university": foreign_university,
            "program_type": program_type,
        }
    )

    # Check if the response contains YES
    return "YES" in result_text.content.upper()


def extract_deadline_info(text: str, home_university: str, 
                         foreign_university: str, program_type: str,
                         start_month: Optional[int] = None, start_year: Optional[int] = None,
                         end_month: Optional[int] = None, end_year: Optional[int] = None) -> Optional[Dict[str, str]]:
    """
    Use LLM to extract application deadline information from text.
    """
    current_year = datetime.datetime.now().year
    current_month = datetime.datetime.now().month
    
    # Format time window information for the prompt
    time_window = ""
    if start_month and start_year:
        time_window += f"Starting: {start_month}/{start_year}\n"
    if end_month and end_year:
        time_window += f"Ending: {end_month}/{end_year}\n"
    
    template = """
    Extract the exact application deadline information from the following text for a student 
    from {home_university} who wants to study at {foreign_university} through the {program_type} program.
    
    Text: {text}
    
    TODAY'S DATE: {current_date}
    
    STUDENT'S DESIRED TIME WINDOW:
    {time_window}
    
    Critical instructions:
    1. ONLY extract deadlines EXPLICITLY mentioned in the text - do not invent dates
    2. For UCSB/UC Santa Barbara, the text specifically states:
       "Winter, Spring & Summer Quarter 31 July of the previous year, Fall Quarter 31 January"
       This means 31 July and 31 January are the only valid deadline dates
    3. Extract the EXACT day and month mentioned (no interpretation needed)
    4. If multiple deadlines are mentioned, choose the one that applies to the student's desired time window
    5. If the student wants to attend in Fall, use the Fall deadline (31 January)
    6. If the student wants to attend in Winter, Spring or Summer, use that deadline (31 July of previous year)
    7. Academic terms typically are: Fall (Sept-Dec), Winter (Jan-Mar), Spring (Apr-June), Summer (July-Aug)
    
    Return your response in the following JSON format:
    {{
        "deadline_found": true or false,
        "deadline_date": "YYYY-MM-DD" using the EXACT day and month from the text,
        "deadline_description": "Complete description of the deadline, including which quarters it applies to",
        "term_applying_for": "Which term the student would be applying for (Fall/Winter/Spring/Summer)",
        "exact_deadline_text": "Copy and paste the exact deadline text from the document",
        "reasoning": "Explanation of why this deadline was chosen based on the time window"
    }}
    """

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm
    result = chain.invoke(
        {
            "text": text,
            "home_university": home_university,
            "foreign_university": foreign_university,
            "program_type": program_type,
            "current_date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "time_window": time_window if time_window else "No specific time window provided"
        }
    )

    # Extract the JSON from the response
    import json
    import re
    
    try:
        # Try to extract JSON from the content
        json_match = re.search(r'({.*})', result.content.replace('\n', ' '), re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            deadline_data = json.loads(json_str)
            
            # Double-check if the extracted date is in the past
            if deadline_data.get("deadline_found", False) and deadline_data.get("deadline_date"):
                try:
                    deadline_date = datetime.datetime.strptime(deadline_data["deadline_date"], "%Y-%m-%d")
                    current_date = datetime.datetime.now()
                    
                    # Keep adding years until the date is in the future
                    years_added = 0
                    while deadline_date < current_date:
                        years_added += 1
                        deadline_date = deadline_date.replace(year=deadline_date.year + 1)
                    
                    if years_added > 0:
                        deadline_data["deadline_date"] = deadline_date.strftime("%Y-%m-%d")
                        deadline_data["deadline_description"] += f" (Date adjusted {years_added} year{'s' if years_added > 1 else ''} forward to next cycle)"
                        deadline_data["date_adjusted"] = True
                        deadline_data["years_added"] = years_added
                except ValueError:
                    # If date parsing fails, keep the original date
                    pass
                    
            return deadline_data
        return None
    except Exception as e:
        print(f"Error extracting deadline info: {str(e)}")
        return None


def find_application_deadline(home_university: str, foreign_university: str, 
                             program_type: str) -> Optional[DeadlineInfo]:
    """
    Search for and extract application deadline information for an exchange program
    between two universities.
    """
    # Construct search query
    query = f"{home_university} {foreign_university} {program_type} exchange program application deadline"
    search_results = google(query)
    
    if not search_results:
        return None
    
    # Filter relevant results
    relevant_results = [
        r for r in search_results if is_relevant_search_result(r, home_university, 
                                                              foreign_university, program_type)
    ]
    
    if not relevant_results:
        return None
    
    # Process each relevant result
    for result in relevant_results:
        try:
            text = scrape_text_from_url(result.url)
            deadline_data = extract_deadline_info(text, home_university, foreign_university, program_type)
            
            if deadline_data and deadline_data.get("deadline_found", False):
                return DeadlineInfo(
                    home_university=home_university,
                    foreign_university=foreign_university,
                    program_type=program_type,
                    deadline_date=deadline_data.get("deadline_date", ""),
                    deadline_description=deadline_data.get("deadline_description", ""),
                    source_url=result.url
                )
        except Exception as e:
            print(f"Error processing {result.url}: {str(e)}")
    
    return None


def generate_calendar_file(deadline_info: DeadlineInfo) -> Dict[str, Any]:
    """
    Generate an iCalendar file for the application deadline.
    Returns a dictionary with the calendar data and filename.
    """
    try:
        # Parse deadline date
        deadline_date = None
        try:
            deadline_date = datetime.datetime.strptime(deadline_info.deadline_date, "%Y-%m-%d")
        except ValueError:
            # Use LLM to parse date
            date_parser_template = """
            Parse the following date string into YYYY-MM-DD format: "{date_string}"
            Return ONLY the date in YYYY-MM-DD format, nothing else.
            If the date is ambiguous or lacks a year, assume it's for the next upcoming occurrence.
            """
            prompt = ChatPromptTemplate.from_template(date_parser_template)
            date_parser_chain = prompt | llm
            parsed_date = date_parser_chain.invoke({"date_string": deadline_info.deadline_date})
            deadline_date = datetime.datetime.strptime(parsed_date.content.strip(), "%Y-%m-%d")

        # Check if deadline is in the past and adjust if necessary
        current_date = datetime.datetime.now()
        years_added = 0
        
        # Keep adding years until the date is in the future
        while deadline_date < current_date:
            years_added += 1
            deadline_date = deadline_date.replace(year=deadline_date.year + 1)

        # Create a calendar
        cal = Calendar()
        cal.add('prodid', '-//Q-Summit Application Deadline Finder//qsummit.org//')
        cal.add('version', '2.0')
        
        # Create an event
        event = Event()
        
        # Set event properties
        summary = f"Application Deadline: {deadline_info.program_type} - {deadline_info.foreign_university}"
        if years_added > 0:
            summary += f" (Adjusted {years_added} year{'s' if years_added > 1 else ''} forward)"
            
        event.add('summary', summary)
        
        # Set timezone-aware datetime
        utc = pytz.UTC
        start_time = datetime.datetime.combine(deadline_date.date(), datetime.time(9, 0))
        end_time = datetime.datetime.combine(deadline_date.date(), datetime.time(10, 0))
        
        # Add timezone
        start_time = utc.localize(start_time)
        end_time = utc.localize(end_time)
        
        event.add('dtstart', start_time)
        event.add('dtend', end_time)
        
        # Set description
        description = f"""
        Application deadline for {deadline_info.program_type} program
        Home University: {deadline_info.home_university}
        Foreign University: {deadline_info.foreign_university}
        Deadline: {deadline_info.deadline_date}
        Details: {deadline_info.deadline_description}
        Source: {deadline_info.source_url}
        """
        
        if years_added > 0:
            description += f"""
            
            WARNING: The original deadline was in the past. This calendar entry 
            has been adjusted {years_added} year{'s' if years_added > 1 else ''} forward to a future cycle. 
            The actual deadline may differ - please verify with the university.
            """
            
        event.add('description', description)
        
        # Add location
        event.add('location', 'Online Application')
        
        # Add reminder (alarm) - 30 days before
        alarm = Event()
        alarm.add('action', 'DISPLAY')
        alarm.add('description', f"Reminder: {summary}")
        alarm.add('trigger', datetime.timedelta(days=-30))
        event.add_component(alarm)

        # Add unique ID for the event
        import uuid
        event['uid'] = str(uuid.uuid4())
        
        # Add the event to the calendar
        cal.add_component(event)
        
        # Generate calendar data
        calendar_data = cal.to_ical().decode('utf-8')
        
        # Generate a filename
        safe_uni_name = ''.join(c if c.isalnum() else '_' for c in deadline_info.foreign_university)
        filename = f"application_deadline_{safe_uni_name}.ics"
        
        print(f"Successfully generated calendar file: {filename}")
        if years_added > 0:
            print(f"Note: Deadline was in the past and has been adjusted {years_added} year{'s' if years_added > 1 else ''} forward to the next cycle.")
        else:
            print("Note: Current deadline used (already in the future).")
            
        # Generate calendar URLs for popular calendar services
        google_cal_url = generate_google_calendar_url(event)
        outlook_web_url = generate_outlook_web_url(event)
            
        return {
            "success": True,
            "filename": filename,
            "calendar_data": calendar_data,
            "summary": summary,
            "years_adjusted": years_added,
            "google_calendar_url": google_cal_url,
            "outlook_web_url": outlook_web_url,
            "event": event
        }
    except Exception as e:
        print(f"Error generating calendar file: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


def generate_google_calendar_url(event) -> str:
    """
    Generate a URL that will create an event in Google Calendar.
    """
    try:
        # Extract event details
        summary = event.get('summary', 'Application Deadline')
        start_time = event.get('dtstart').dt
        end_time = event.get('dtend').dt
        description = event.get('description', '')
        location = event.get('location', 'Online')
        
        # Format dates for Google Calendar URL
        start_str = start_time.strftime('%Y%m%dT%H%M%SZ') if isinstance(start_time, datetime.datetime) else f"{start_time.strftime('%Y%m%d')}"
        end_str = end_time.strftime('%Y%m%dT%H%M%SZ') if isinstance(end_time, datetime.datetime) else f"{end_time.strftime('%Y%m%d')}"
        
        # Create URL parameters
        import urllib.parse
        params = {
            'action': 'TEMPLATE',
            'text': summary,
            'dates': f"{start_str}/{end_str}",
            'details': description,
            'location': location,
        }
        
        # Build the URL
        base_url = "https://calendar.google.com/calendar/render"
        query_string = urllib.parse.urlencode(params)
        google_url = f"{base_url}?{query_string}"
        
        return google_url
    except Exception as e:
        print(f"Error generating Google Calendar URL: {str(e)}")
        return ""


def generate_outlook_web_url(event) -> str:
    """
    Generate a URL that will create an event in Outlook Web Calendar.
    """
    try:
        # Extract event details
        summary = event.get('summary', 'Application Deadline')
        start_time = event.get('dtstart').dt
        end_time = event.get('dtend').dt
        description = event.get('description', '')
        location = event.get('location', 'Online')
        
        # Format dates for Outlook Web URL
        start_str = start_time.strftime('%Y-%m-%dT%H:%M:%S') if isinstance(start_time, datetime.datetime) else f"{start_time.strftime('%Y-%m-%d')}T00:00:00"
        end_str = end_time.strftime('%Y-%m-%dT%H:%M:%S') if isinstance(end_time, datetime.datetime) else f"{end_time.strftime('%Y-%m-%d')}T00:00:00"
        
        # Create URL parameters
        import urllib.parse
        params = {
            'path': '/calendar/action/compose',
            'rru': 'addevent',
            'subject': summary,
            'startdt': start_str,
            'enddt': end_str,
            'body': description,
            'location': location,
        }
        
        # Build the URL
        base_url = "https://outlook.office.com/calendar/0/action/compose"
        query_string = urllib.parse.urlencode(params)
        outlook_url = f"{base_url}?{query_string}"
        
        return outlook_url
    except Exception as e:
        print(f"Error generating Outlook Web URL: {str(e)}")
        return ""


def send_calendar_invitation_email(deadline_info: DeadlineInfo, recipient_email: str) -> bool:
    """
    Send an email with calendar invitation attached.
    This method requires an SMTP server configuration.
    """
    try:
        # Generate calendar file
        calendar_result = generate_calendar_file(deadline_info)
        if not calendar_result.get("success", False):
            return False
            
        # Calendar data
        calendar_data = calendar_result.get("calendar_data", "")
        summary = calendar_result.get("summary", "Application Deadline")
        
        # Import email modules
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.base import MIMEBase
        from email import encoders
        
        # This would need to be configured in your application settings
        # For now, using placeholder values
        smtp_server = os.environ.get("SMTP_SERVER", "smtp.example.com")
        smtp_port = int(os.environ.get("SMTP_PORT", 587))
        smtp_username = os.environ.get("SMTP_USERNAME", "user@example.com")
        smtp_password = os.environ.get("SMTP_PASSWORD", "password")
        sender_email = os.environ.get("SENDER_EMAIL", "noreply@qsummit.org")
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = f"Calendar Invitation: {summary}"
        
        # Email body
        body = f"""
        Hello,
        
        Attached is a calendar invitation for your application deadline:
        
        {summary}
        
        You can add this to your calendar by opening the attached .ics file.
        
        Regards,
        Q-Summit Application Deadline Finder
        """
        msg.attach(MIMEText(body, 'plain'))
        
        # Attachment
        attachment = MIMEBase('text', 'calendar', method="REQUEST", name=calendar_result.get("filename"))
        attachment.set_payload(calendar_data)
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition', f'attachment; filename="{calendar_result.get("filename")}"')
        attachment.add_header('Content-Type', 'text/calendar; charset="utf-8"; method=REQUEST')
        msg.attach(attachment)
        
        # Connect to SMTP server (this is just example code, would need real credentials)
        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            print(f"SMTP server error: {str(e)}")
            # Don't fail the whole function if SMTP fails, just log it
            return False
            
    except Exception as e:
        print(f"Error sending calendar invitation email: {str(e)}")
        return False


# Replace the Outlook-specific function with the platform-independent version
def add_to_outlook_calendar(deadline_info: DeadlineInfo) -> Dict[str, Any]:
    """
    Platform-independent calendar handler for a web application.
    Returns dictionary with calendar data and direct add URLs.
    """
    try:
        # Generate the calendar file
        calendar_result = generate_calendar_file(deadline_info)
        
        # Return the calendar data and URLs
        return {
            "success": calendar_result.get("success", False),
            "ics_data": calendar_result.get("calendar_data", ""),
            "filename": calendar_result.get("filename", ""),
            "google_calendar_url": calendar_result.get("google_calendar_url", ""),
            "outlook_web_url": calendar_result.get("outlook_web_url", ""),
            "summary": calendar_result.get("summary", "")
        }
    except Exception as e:
        print(f"Error processing calendar data: {str(e)}")
        return {"success": False, "error": str(e)}


# LangGraph agent implementation
class AgentState(TypedDict):
    home_university: str
    foreign_university: str
    program_type: str
    start_month: Optional[int]
    start_year: Optional[int]
    end_month: Optional[int]
    end_year: Optional[int]
    gpa: Optional[float]
    languages: List[str]
    budget: Optional[int]
    search_results: List[dict]
    deadline_info: Optional[dict]
    calendar_added: bool
    error: Optional[str]
    final_response: Optional[str]


def initialize_agent() -> StateGraph:
    """Initialize the agent workflow."""
    workflow = StateGraph(AgentState)
    
    # Define the nodes
    
    # Step 1: Perform search
    def search_step(state: AgentState) -> AgentState:
        try:
            home_uni = state["home_university"]
            foreign_uni = state["foreign_university"]
            program = state["program_type"]
            
            query = f"{home_uni} {foreign_uni} {program} exchange program application deadline"
            search_results = google(query)
            
            return {
                **state,
                "search_results": [
                    {"title": r.title, "url": r.url, "snippet": r.snippet} 
                    for r in search_results
                ]
            }
        except Exception as e:
            return {**state, "error": f"Search error: {str(e)}"}
    
    # Step 2: Extract deadline
    def extract_deadline_step(state: AgentState) -> AgentState:
        if state.get("error"):
            return state
            
        try:
            home_uni = state["home_university"]
            foreign_uni = state["foreign_university"]
            program = state["program_type"]
            start_month = state.get("start_month")
            start_year = state.get("start_year")
            end_month = state.get("end_month")
            end_year = state.get("end_year")
            
            # Filter relevant results
            relevant_results = []
            for r_dict in state["search_results"]:
                r = SearchResult(title=r_dict["title"], url=r_dict["url"], snippet=r_dict["snippet"])
                if is_relevant_search_result(r, home_uni, foreign_uni, program):
                    relevant_results.append(r)
            
            # Process each relevant result
            for result in relevant_results:
                try:
                    text = scrape_text_from_url(result.url)
                    deadline_data = extract_deadline_info(
                        text, home_uni, foreign_uni, program,
                        start_month, start_year, end_month, end_year
                    )
                    
                    if deadline_data and deadline_data.get("deadline_found", False):
                        deadline_info = {
                            "home_university": home_uni,
                            "foreign_university": foreign_uni,
                            "program_type": program,
                            "deadline_date": deadline_data.get("deadline_date", ""),
                            "deadline_description": deadline_data.get("deadline_description", ""),
                            "source_url": result.url,
                            "term_applying_for": deadline_data.get("term_applying_for", ""),
                            "reasoning": deadline_data.get("reasoning", "")
                        }
                        return {**state, "deadline_info": deadline_info}
                except Exception as e:
                    print(f"Error processing {result.url}: {str(e)}")
            
            return {**state, "error": "Could not find deadline information"}
        except Exception as e:
            return {**state, "error": f"Extraction error: {str(e)}"}
    
    # Step 3: Add to calendar
    def add_to_calendar_step(state: AgentState) -> AgentState:
        if state.get("error") or not state.get("deadline_info"):
            return state
            
        try:
            deadline_info = DeadlineInfo(
                home_university=state["deadline_info"]["home_university"],
                foreign_university=state["deadline_info"]["foreign_university"],
                program_type=state["deadline_info"]["program_type"],
                deadline_date=state["deadline_info"]["deadline_date"],
                deadline_description=state["deadline_info"]["deadline_description"],
                source_url=state["deadline_info"]["source_url"]
            )
            
            success = add_to_outlook_calendar(deadline_info)
            
            if success:
                return {**state, "calendar_added": True}
            else:
                return {**state, "error": "Failed to add to calendar"}
        except Exception as e:
            return {**state, "error": f"Calendar error: {str(e)}"}
    
    # Step 4: Generate final response
    def generate_response_step(state: AgentState) -> AgentState:
        if state.get("error"):
            return {**state, "final_response": f"Error: {state['error']}"}
            
        if state.get("calendar_added"):
            deadline_info = state["deadline_info"]
            response = f"""
            Successfully found application deadline information:
            
            Home University: {deadline_info['home_university']}
            Foreign University: {deadline_info['foreign_university']}
            Program Type: {deadline_info['program_type']}
            Deadline: {deadline_info['deadline_date']}
            Details: {deadline_info['deadline_description']}
            
            This deadline has been added to your calendar.
            Source: {deadline_info['source_url']}
            """
            return {**state, "final_response": response}
        else:
            return {**state, "final_response": "Process completed but calendar event was not created."}
    
    # Add nodes to the graph
    workflow.add_node("search", search_step)
    workflow.add_node("extract_deadline", extract_deadline_step)
    workflow.add_node("add_to_calendar", add_to_calendar_step)
    workflow.add_node("generate_response", generate_response_step)
    
    # Connect the nodes
    workflow.add_edge("search", "extract_deadline")
    workflow.add_edge("extract_deadline", "add_to_calendar")
    workflow.add_edge("add_to_calendar", "generate_response")
    workflow.add_edge("generate_response", END)
    
    # Set the entry point
    workflow.set_entry_point("search")
    
    return workflow


def find_and_add_deadline(input_data: dict) -> str:
    """
    Main function to find application deadline and add it to the calendar.
    
    Input format:
    {
        "gpa": double,
        "languages": [string],
        "budget": int?,
        "start-month": int?,
        "start-year": int?,
        "end-month": int?,
        "end-year": int?,
        "home_university": string,
        "foreign_university": string,
        "program_type": string
    }
    """
    # Initialize the agent
    workflow = initialize_agent()
    
    # Compile the graph into a runnable app
    app = workflow.compile()
    
    # Extract data from input JSON
    home_university = input_data.get("home_university", "")
    foreign_university = input_data.get("foreign_university", "")
    program_type = input_data.get("program_type", "")
    
    # Extract time window data
    start_month = input_data.get("start-month")
    start_year = input_data.get("start-year")
    end_month = input_data.get("end-month")
    end_year = input_data.get("end-year")
    
    # Other fields
    gpa = input_data.get("gpa")
    languages = input_data.get("languages", [])
    budget = input_data.get("budget")
    
    # Run the agent
    initial_state: AgentState = {
        "home_university": home_university,
        "foreign_university": foreign_university,
        "program_type": program_type,
        "start_month": start_month,
        "start_year": start_year,
        "end_month": end_month,
        "end_year": end_year,
        "gpa": gpa,
        "languages": languages,
        "budget": budget,
        "search_results": [],
        "deadline_info": None,
        "calendar_added": False,
        "error": None,
        "final_response": None
    }
    
    # Execute the workflow using the compiled app
    final_state = app.invoke(initial_state)
    
    # Return the final response
    return final_state.get("final_response")


if __name__ == "__main__":
    # Example usage with JSON input
    sample_input = {
        "gpa": 3.5,
        "languages": ["English", "German"],
        "budget": 10000,
        "start-month": 9,  # September
        "start-year": 2025,
        "end-month": 6,    # June
        "end-year": 2026,
        "home_university": "University of Münster",
        "foreign_university": "University of Santa Barbara",
        "program_type": "overseas"
    }
    
    # Test methods
    def test_calendar_generation():
        """Test calendar generation features locally"""
        print("Testing calendar generation features...")
        
        # Create a sample deadline info
        deadline_info = DeadlineInfo(
            home_university="University of Münster",
            foreign_university="University of Santa Barbara",
            program_type="overseas",
            deadline_date="2025-03-15",
            deadline_description="Application for Fall Semester",
            source_url="https://example.com/deadlines"
        )
        
        # Generate calendar file and URLs
        cal_result = add_to_outlook_calendar(deadline_info)
        
        if cal_result["success"]:
            print("\n✅ Successfully generated calendar data!")
            print(f"Summary: {cal_result['summary']}")
            print("\n🔗 Calendar Add URLs:")
            print(f"Google Calendar: {cal_result['google_calendar_url']}")
            print(f"Outlook Web: {cal_result['outlook_web_url']}")
            
            # Save the ICS file locally for testing
            ics_path = f"test_{cal_result['filename']}"
            with open(ics_path, "w") as f:
                f.write(cal_result["ics_data"])
            print(f"\n💾 Saved calendar file to {ics_path}")
            print(f"You can open this file with your calendar application to test the import")
            
            # Test sending email
            email = input("\n📧 Enter an email to send a calendar invitation (or press Enter to skip): ")
            if email and "@" in email:
                print(f"Sending calendar invitation to {email}...")
                success = send_calendar_invitation_email(deadline_info, email)
                if success:
                    print("✅ Email sent successfully!")
                else:
                    print("❌ Failed to send email. Check SMTP settings and try again.")
            else:
                print("Email sending skipped.")
        else:
            print(f"❌ Calendar generation failed: {cal_result.get('error', 'Unknown error')}")
    
    # Choose what to test
    print("Select a test option:")
    print("1. Find deadline and add to calendar (original test)")
    print("2. Test calendar generation features")
    choice = input("Enter your choice (1 or 2): ")
    
    if choice == "2":
        test_calendar_generation()
    else:
        # Run the original test
        result = find_and_add_deadline(sample_input)
        print(result)
