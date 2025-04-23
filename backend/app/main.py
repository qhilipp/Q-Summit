from typing import List, Optional, Union

from app.find_unis import search_partner_universities
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

origins = [
    "http://localhost:3000",  # Your frontend dev server
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Can also use ["*"] for all origins (not for production)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc)
    allow_headers=["*"],  # Allow all headers
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


# Define response model
class UniversityResult(BaseModel):
    name: str
    description: str


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id * 2, "q": q}


@app.post("/search_universities", response_model=List[UniversityResult])
def search_universities(input_data: UniversitySearchInput):
    """
    Search for partner universities based on the provided criteria.
    Returns a list of universities with compatibility information.
    """
    # Convert the Pydantic model to a dictionary for our function
    input_dict = input_data.dict()

    # Call the search function
    results = search_partner_universities(input_dict)

    return results
