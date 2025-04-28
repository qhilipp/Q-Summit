from typing import List, Optional, Union
from find_unis import search_partner_universities
from get_uni_details import get_uni_details
from plan_application import (
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


class UniversitySearchInput(BaseModel):
    """Input model for searching partner universities.

    Attributes:
        university (str): Name of the student's home university.
        major (str): Student's major.
        gpa (float): Student's GPA (grade point average).
        languages (List[str]): List of languages the student speaks.
        budget (Optional[float]): Optional monthly or total budget.
        start_month (Optional[int]): Optional start month for the exchange.
        start_year (Optional[int]): Optional start year for the exchange.
        end_month (Optional[int]): Optional end month for the exchange.
        end_year (Optional[int]): Optional end year for the exchange.
    """

    university: str
    major: str
    gpa: float
    languages: List[str]
    budget: Optional[float] = None
    start_month: Optional[int] = None
    start_year: Optional[int] = None
    end_month: Optional[int] = None
    end_year: Optional[int] = None


class UniversityResult(BaseModel):
    """Response model for a university search result.

    Attributes:
        title (str): University name.
        description (str): Brief description of the university.
        image (Optional[str]): Optional image URL.
        student_count (int): Number of students at the university.
        ranking (str): Ranking category (e.g., high, mid, low).
        languages (List[str]): Languages of instruction.
    """

    title: str
    description: str
    image: Optional[str] = None
    student_count: int
    ranking: str
    languages: List[str]


class QuoteModel(BaseModel):
    """Model representing a student quote.

    Attributes:
        quote (str): The quote text.
        source_link (str): URL of the source blog or article.
    """

    quote: str
    source_link: str


class UniversityDetailsResponse(BaseModel):
    """Response model for university details including student quotes.

    Attributes:
        quotes (List[QuoteModel]): List of student quotes.
    """

    quotes: List[QuoteModel]


class ApplicationPlanInput(BaseModel):
    """Input model for creating a semester abroad application plan.

    Attributes:
        home_university (str): Name of the student's home university.
        target_university (str): Name of the target university.
        major (str): Student's major.
    """

    home_university: str
    target_university: str
    major: str


class ApplicationPlanResponse(BaseModel):
    """Response model for an application plan.

    Attributes:
        plan (str): The raw application plan text.
        markdown (str): Markdown-formatted version of the plan.
    """

    plan: str
    markdown: str


@app.post("/search_universities", response_model=List[UniversityResult])
def search_universities(input_data: UniversitySearchInput):
    """Search for partner universities based on the provided criteria.

    Args:
        input_data (UniversitySearchInput): Search criteria including university, major, GPA, languages, etc.

    Returns:
        List[UniversityResult]: List of universities with detailed information including
            description, image, student count, ranking, and supported languages.
    """
    input_dict = input_data.dict()
    results = search_partner_universities(input_dict)
    return results


@app.get(
    "/university_details/{university_name}", response_model=UniversityDetailsResponse
)
def university_details(university_name: str):
    """Get detailed information about a university, including student quotes.

    Args:
        university_name (str): The name of the university to get details for.

    Returns:
        UniversityDetailsResponse: Object with a list of student quotes.
    """
    details = get_uni_details(university_name)
    return UniversityDetailsResponse(
        quotes=[
            QuoteModel(quote=q.quote, source_link=q.source_link) for q in details.quotes
        ]
    )


@app.post("/application_plan", response_model=ApplicationPlanResponse)
def create_application_plan(input_data: ApplicationPlanInput):
    """Create a semester abroad application plan with both raw text and markdown formats.

    Args:
        input_data (ApplicationPlanInput): Contains home_university, target_university, and major.

    Returns:
        ApplicationPlanResponse: JSON object with both raw plan text and markdown-formatted plan.
    """
    plan = plan_semester_abroad_application(
        home_university=input_data.home_university,
        target_university=input_data.target_university,
        major=input_data.major,
    )

    markdown_plan = make_markdown_from_plan(plan)
    return ApplicationPlanResponse(plan=plan, markdown=markdown_plan)
