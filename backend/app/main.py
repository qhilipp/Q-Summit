from typing import List, Optional, Union

from app.find_unis import search_partner_universities
from app.get_uni_details import get_uni_details
from app.plan_application import (
    make_markdown_from_plan,
    plan_semester_abroad_application,
)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc)
    allow_headers=["*"],  # Allow all headers
    allow_origins=["*"],
)


# Define input model with type hints
class UniversitySearchInput(BaseModel):
    university: str
    major: str
    gpa: float
    languages: List[str]
    budget: Optional[float] = None
    start_month: Optional[int] = None
    start_year: Optional[int] = None
    end_month: Optional[int] = None
    end_year: Optional[int] = None


# Define updated response model to match new output format
class UniversityResult(BaseModel):
    title: str
    description: str
    image: Optional[str] = None
    student_count: int
    ranking: str
    languages: List[str]


# Define models for university details endpoint
class QuoteModel(BaseModel):
    quote: str
    source_link: str


class UniversityDetailsResponse(BaseModel):
    quotes: List[QuoteModel]


# Define model for application plan request
class ApplicationPlanInput(BaseModel):
    home_university: str
    target_university: str
    major: str


# Define model for application plan response
class ApplicationPlanResponse(BaseModel):
    plan: str
    markdown: str


# Define model for deadline find response
class DeadlineFindResponse(BaseModel):
    deadline_info: str


@app.post("/deadline_find", response_model=DeadlineFindResponse)
def deadline_find(input_data: UniversitySearchInput):
    return deadline_find(input_data)


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id * 2, "q": q}


@app.post("/search_universities", response_model=List[UniversityResult])
def search_universities(input_data: UniversitySearchInput):
    """
    Search for partner universities based on the provided criteria.
    Returns a list of universities with detailed information including
    description, image, student count, ranking, and supported languages.
    """
    # Convert the Pydantic model to a dictionary for our function
    input_dict = input_data.dict()

    # Call the search function
    results = search_partner_universities(input_dict)

    return results


@app.get(
    "/university_details/{university_name}/{subject}", response_model=UniversityDetailsResponse
)
def university_details(university_name: str, subject: str):
    """
    Get detailed information about a university, including student quotes.

    Args:
        university_name: The name of the university to get details for

    Returns:
        UniversityDetailsResponse object with quotes
    """
    # Call the get_uni_details function
    details = get_uni_details(university_name, subject)

    # Convert the dataclass objects to Pydantic models
    return UniversityDetailsResponse(
        quotes=[
            QuoteModel(quote=q.quote, source_link=q.source_link) for q in details.quotes
        ]
    )


@app.post("/application_plan", response_model=ApplicationPlanResponse)
def create_application_plan(input_data: ApplicationPlanInput):
    """
    Create a semester abroad application plan with both raw text and markdown formats.

    Args:
        input_data: ApplicationPlanInput containing home_university, target_university, and major

    Returns:
        JSON object with both raw plan text and markdown-formatted plan
    """
    # Generate the application plan
    plan = plan_semester_abroad_application(
        home_university=input_data.home_university,
        target_university=input_data.target_university,
        major=input_data.major,
    )

    # Convert the plan to markdown
    markdown_plan = make_markdown_from_plan(plan)

    # Return both formats
    return ApplicationPlanResponse(plan=plan, markdown=markdown_plan)
