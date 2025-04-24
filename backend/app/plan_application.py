import os
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
from tools import content_analysis_tool, google_search_tool

llm = AzureChatOpenAI(
    deployment_name=secrets_.AZURE_OPENAI_DEPLOYMENT_NAME,
    openai_api_key=secrets_.AZURE_OPENAI_API_KEY,
    azure_endpoint=secrets_.AZURE_OPENAI_ENDPOINT,
    openai_api_version="2023-05-15",
)


def review_plan(
    plan: str, home_university: str, target_university: str, major: str
) -> Dict:
    """
    Reviews the generated plan for completeness, accuracy, and quality.
    Suggests improvements or identifies missing important information.
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
    """
    Plans a semester abroad application for a given home university, target university, and major.
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

    # After getting the initial plan, pass it to the reviewer
    plan_result = result["output"]
    review_result = review_plan(plan_result, home_university, target_university, major)

    # Incorporate review feedback into final plan
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
    """
    Let llm make a markdown document from the plan to give a good overview.
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
