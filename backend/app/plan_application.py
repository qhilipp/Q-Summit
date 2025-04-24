# import module-function
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests
import secrets_
from bs4 import BeautifulSoup
from duckduckgo_search.exceptions import DuckDuckGoSearchException
from googlesearch import search
from langchain.prompts import ChatPromptTemplate
from langchain_community.tools import BraveSearch, DuckDuckGoSearchResults, Tool
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper, SearxSearchWrapper
from langchain_openai import AzureChatOpenAI
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

llm = AzureChatOpenAI(
    deployment_name=secrets_.AZURE_OPENAI_DEPLOYMENT_NAME,
    openai_api_key=secrets_.AZURE_OPENAI_API_KEY,
    azure_endpoint=secrets_.AZURE_OPENAI_ENDPOINT,
    openai_api_version="2023-05-15",
)


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


def google(query: str, num_results: int = 10):
    google_search = search(query, advanced=True, num_results=num_results)
    return [
        SearchResult(title=result.title, url=result.url, snippet=result.description)
        for result in google_search
    ]


def scrape_text_from_url(url: str):
    response = requests.get(url)
    return BeautifulSoup(response.text, "html.parser").get_text()


class WorkflowState(TypedDict):
    query: str
    search_results: List[SearchResult]
    relevant_results: List[SearchResult]
    universities: List[str]
    program: str
    application_info: Dict[str, Dict[str, str]]
    messages: List[str]


def extract_program_from_query(query: str) -> str:
    programs = [
        "erasmus",
        "erasmus+",
        "freemover",
        "overseas",
        "exchange",
        "study abroad",
        "international exchange",
    ]
    query_lower = query.lower()
    for prog in programs:
        if prog in query_lower:
            return prog
    return ""


def is_relevant_search_result(result: SearchResult, program: str) -> bool:
    prompt = ChatPromptTemplate.from_template("""
    Ist dieses Suchergebnis relevant für Partneruniversitäten des {program} Programms?
    Titel: {title}
    Beschreibung: {snippet}
    Antwort: [JA/NEIN]""")

    chain = prompt | llm
    response = chain.invoke(
        {"program": program.upper(), "title": result.title, "snippet": result.snippet}
    )
    return "JA" in response.content.upper()


def select_partner_university(universities: list) -> str:
    if universities:
        return universities[0]
    return None


def extract_partner_universities(text: str, program: str) -> List[str]:
    prompt = ChatPromptTemplate.from_template("""
    Extrahiere Partneruniversitäten aus dem Text für das {program} Programm:
    {text}
    Gib nur die Namen zurück, je Zeile einer.""")

    chain = prompt | llm
    response = chain.invoke({"program": program, "text": text[:3000]})
    return [line.strip() for line in response.content.split("\n") if line.strip()]


# LangGraph Nodes
def search_node(state: WorkflowState) -> WorkflowState:
    print("Führe Suche durch...")
    query = state["query"]
    results = google(query)
    program = extract_program_from_query(query)

    return {
        **state,
        "search_results": results,
        "program": program,
        "messages": [
            *state.get("messages", []),
            f"Suche abgeschlossen: {len(results)} Ergebnisse",
        ],
    }


def relevance_filter_node(state: WorkflowState) -> WorkflowState:
    print("Filtere relevante Ergebnisse...")
    program = state["program"]
    relevant = [
        r for r in state["search_results"] if is_relevant_search_result(r, program)
    ]

    return {
        **state,
        "relevant_results": relevant,
        "messages": [
            *state["messages"],
            f"{len(relevant)} relevante Ergebnisse gefunden",
        ],
    }


def extraction_node(state: WorkflowState) -> WorkflowState:
    print("Extrahiere Partnerunis und Bewerbungsdetails...")
    program = state["program"]
    universities = []
    # 1. Extrahiere Partnerunis aus Original-Suchergebnissen
    for result in state["relevant_results"]:
        try:
            text = scrape_text_from_url(result.url)
            unis = extract_partner_universities(text, program)
            universities.extend(unis)
        except Exception as e:
            print(f"Fehler bei {result.url}: {e}")

    unique_unis = list(dict.fromkeys(u for u in universities if u))

    if not unique_unis:
        return {
            **state,
            "universities": [],
            "messages": [*state["messages"], "Keine Partnerunis gefunden."],
        }

    # 2. Wähle Uni und führe Zusatzsuche durch
    selected_university = unique_unis[0]
    detail_query = f"{selected_university} Bewerbungsfristen Sprachvoraussetzungen Academic Calendar GPA"

    # 3. Neue Google-Suche für Bewerbungsdetails
    print(f"Führe Detail-Suche durch für: {selected_university}")
    detail_results = google(detail_query)

    # 4. Extrahiere Details aus den Detail-Ergebnissen
    details_text = ""
    for result in detail_results:
        try:
            text = scrape_text_from_url(result.url)
            prompt = ChatPromptTemplate.from_template("""
Extrahiere folgende Bewerbungsdetails aus dem Text:
- Bewerbungsfristen (konkrete Daten/Zeiträume)
- Semesterzeiten (Academic Calendar)
- Sprachzertifikate (mit Mindestpunktzahlen)
- Notendurchschnittsanforderungen (GPA)

Format:
Universität: {university}
Bewerbungsdeadline: [Datum/Zeitraum]
Academic Calendar: [Semesterzeiten]
Sprachkenntnisse: [Anforderungen]
GPA-Anforderung: [Mindestnote]

Antworte NUR mit diesen Feldern. Keine Erklärungen.
Text:
{text}
            """)
            chain = prompt | llm
            response = chain.invoke(
                {"university": selected_university, "text": text[:4000]}
            )

            # Validiere Antwortformat
            if all(
                keyword in response.content
                for keyword in [
                    "Bewerbungsdeadline:",
                    "Academic Calendar:",
                    "Sprachkenntnisse:",
                ]
            ):
                details_text = response.content.strip()
                break

        except Exception as e:
            print(f"Fehler bei Detail-URL {result.url}: {e}")

    # 5. Fallback: Durchsuche Original-Ergebnisse
    if not details_text:
        for result in state["relevant_results"]:
            try:
                text = scrape_text_from_url(result.url)
                prompt = ChatPromptTemplate.from_template("""
Extrahiere aus dem Text Bewerbungsdetails für {university}:
{text}
                """)
                chain = prompt | llm
                response = chain.invoke(
                    {"university": selected_university, "text": text[:4000]}
                )
                if "Bewerbungsdeadline:" in response.content:
                    details_text = response.content.strip()
                    break
            except Exception as e:
                print(f"Fehler bei {result.url}: {e}")

    # 6. Finaler Fallback
    if not details_text:
        details_text = f"""Universität: {selected_university}
Bewerbungsdeadline: Unbekannt
Academic Calendar: Unbekannt
Sprachkenntnisse: Unbekannt
GPA-Anforderung: Unbekannt"""

    # 7. Speichern
    with open("bewerbungsdetails.txt", "w", encoding="utf-8") as f:
        f.write(details_text)

    return {
        **state,
        "universities": unique_unis,
        "selected_university": selected_university,
        "application_info": details_text,
        "messages": [
            *state["messages"],
            f"Details für {selected_university} gespeichert",
            f"Verwendete Detail-Query: {detail_query}",
        ],
    }


workflow = StateGraph(WorkflowState)
workflow.add_node("search", search_node)
workflow.add_node("filter", relevance_filter_node)
workflow.add_node("extract", extraction_node)
workflow.set_entry_point("search")
workflow.add_edge("search", "filter")
workflow.add_edge("filter", "extract")
workflow.add_edge("extract", END)
app = workflow.compile()


def save_details_to_txt(details_text, filename="bewerbungsdetails.txt"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(details_text)
    print(f"Bewerbungsdetails gespeichert in {filename}")


if __name__ == "__main__":
    initial_state = WorkflowState(
        query="Erasmus Partneruniversitäten Informatik Uni Münster",
        search_results=[],
        relevant_results=[],
        universities=[],
        program="",
        application_info={},
        messages=[],
    )
    result = app.invoke(initial_state)
    print("\nGefundene Partneruniversitäten:")
    print("\n".join(result["universities"]))
    print("\nBewerbungsdetails (auch in bewerbungsdetails.txt):")
    print(result["application_info"])
