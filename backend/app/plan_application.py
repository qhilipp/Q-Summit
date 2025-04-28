from typing import Dict
from langchain.agents import initialize_agent
from langchain.agents.agent_types import AgentType
from langchain.prompts import ChatPromptTemplate
from tools import content_analysis_tool, google_search_tool, llm


def review_plan(
    plan: str, home_university: str, target_university: str, major: str
) -> Dict:
    """Reviews and improves a semester abroad application plan.

    Args:
        plan (str): The initial application plan to review.
        home_university (str): Name of the student's home university.
        target_university (str): Name of the target exchange university.
        major (str): The student's academic major.

    Returns:
        dict[str, Any]: Dictionary containing review feedback with keys:
            - 'strengths': List of plan strengths
            - 'improvements': List of suggested improvements
            - 'missing_info': List of missing critical information
            - 'deadline_check': Boolean indicating deadline validity

    Notes:
        Uses a reviewer agent with search capabilities to validate information.
    """
    reviewer_agent = initialize_agent(
        [google_search_tool, content_analysis_tool],
        llm,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        max_execution_time=4,
        early_stopping_method="generate",
    )

    result = reviewer_agent.invoke(
        {
            "input": f"""
        Review the following semester abroad application plan for a student from "{home_university}" 
        to "{target_university}" majoring in "{major}".
        
        PLAN TO REVIEW:
        {plan}
        
        Your task is to:
        1. Verify the accuracy of any factual information (dates, requirements, etc.)
        2. Identify any critical missing information
        3. Suggest improvements to make the plan more comprehensive and actionable
        4. Highlight any potential challenges or considerations specific to this university pair
        
        Format your review as constructive feedback with specific suggestions for improvement.
        """
        }
    )

    return result["output"]


def plan_semester_abroad_application(
    home_university: str, target_university: str, major: str
) -> Dict:
    """Generates a comprehensive semester abroad application plan.

    Args:
        home_university (str): Name of the student's home institution.
        target_university (str): Name of the target exchange university.
        major (str): The student's academic major.

    Returns:
        dict[str, Any]: Structured application plan containing:
            - 'timeline': Key dates and deadlines
            - 'requirements': List of application requirements
            - 'financial_plan': Cost breakdown and funding options
            - 'academic_prep': Course mapping and credit transfer info
            - 'housing_options': Available housing solutions

    Note:
        Combines automated research with LLM analysis for optimal results.
    """
    agent = initialize_agent(
        [google_search_tool, content_analysis_tool],
        llm,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        max_execution_time=8,
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
    
    plan_result = result["output"]
    review_result = review_plan(plan_result, home_university, target_university, major)
    
    final_plan_agent = initialize_agent(
        [],
        llm,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
    )

    final_result = final_plan_agent.invoke(
        {
            "input": f"""
        ORIGINAL PLAN:
        {plan_result}
        
        REVIEW FEEDBACK:
        {review_result}
        
        Create an improved final plan that addresses the review feedback while maintaining 
        the organization and clarity of the original plan.
        """
        }
    )

    return final_result["output"]


def make_markdown_from_plan(plan: str) -> str:
    """Converts an application plan into a structured Markdown document.

    Args:
        plan (str): Raw text of the application plan.

    Returns:
        str: Well-formatted Markdown document with:
            - Hierarchical headers
            - Checklists and timelines
            - Highlighted key information
            - Tables for complex data
            - Emphasis on critical dates/requirements

    Example:
        Returns markdown with sections like:
        # Application Timeline
        ## 6 Months Before Departure
        - [ ] Submit initial paperwork...
    """
    template = """
    You are an expert Markdown writer. Convert the following study abroad application plan into a 
    well-organized, visually appealing Markdown document. The Markdown should:
    
    1. Have a clean, professional structure
    2. Include appropriate sections with headings
    3. Use lists, tables, or emphasis where appropriate
    4. Include a timeline or checklist section if possible
    5. Use a readable, hierarchical layout
    6. Utilize Markdown formatting features (bold, italic, headers, etc.)
    
    Here's the plan to convert:
    {plan}
    
    Return ONLY the complete Markdown content.
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
    markdown_plan = make_markdown_from_plan(result)
    print(markdown_plan)
