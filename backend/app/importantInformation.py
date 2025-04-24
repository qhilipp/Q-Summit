import os
import time
from dataclasses import dataclass
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
from googlesearch import search
from langchain.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI
from secrets_ import AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_NAME    
import threading
from functools import partial

llm = AzureChatOpenAI(
    deployment_name=AZURE_OPENAI_DEPLOYMENT_NAME,
    openai_api_key=AZURE_OPENAI_API_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    openai_api_version="2023-05-15",
)

# Set timeout for requests
TIMEOUT = 10  # seconds

class TimeoutError(Exception):
    pass

def timeout_handler():
    raise TimeoutError("Operation timed out")

def run_with_timeout(func, *args, timeout=TIMEOUT, **kwargs):
    """Run a function with a timeout."""
    result = [None]
    exception = [None]
    
    def target():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e
    
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout)
    
    if thread.is_alive():
        raise TimeoutError(f"Operation timed out after {timeout} seconds")
    
    if exception[0] is not None:
        raise exception[0]
    
    return result[0]

@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str

def google_search_with_timeout(query: str, num_results: int = 2, timeout: int = TIMEOUT) -> List[SearchResult]:
    """Perform a Google search with timeout."""
    try:
        def search_func():
            return list(search(query, advanced=True, num_results=num_results))
        
        results = run_with_timeout(search_func, timeout=timeout)
        return [
            SearchResult(title=result.title, url=result.url, snippet=result.description)
            for result in results
        ]
    except TimeoutError:
        print(f"Search timed out for query: {query}")
        return []
    except Exception as e:
        print(f"Error during Google search: {str(e)}")
        return []

def scrape_text_from_url(url: str, max_length: int = 5000, timeout: int = TIMEOUT) -> str:
    """Scrape text content from a URL with timeout."""
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=timeout)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Get text and limit its length
        text = soup.get_text()
        if len(text) > max_length:
            text = text[:max_length] + "... [Content truncated]"
        return text
    except requests.Timeout:
        print(f"Request timed out for URL: {url}")
        return ""
    except Exception as e:
        print(f"Error scraping URL {url}: {str(e)}")
        return ""

def analyze_content_with_llm(text: str, analysis_prompt: str, max_chunk_size: int = 30000) -> str:
    """Analyze content using the LLM with a specific prompt, handling large texts in chunks."""
    try:
        # Split text into chunks if it's too long
        if len(text) > max_chunk_size:
            chunks = [text[i:i+max_chunk_size] for i in range(0, len(text), max_chunk_size)]
            all_analyses = []
            
            # First analyze each chunk separately
            for i, chunk in enumerate(chunks):
                print(f"Analyzing chunk {i+1}/{len(chunks)}...")
                prompt = ChatPromptTemplate.from_template(analysis_prompt)
                chain = prompt | llm
                result = chain.invoke({"text": chunk})
                all_analyses.append(result.content)
            
            # If we have multiple analyses, create a meta-analysis to integrate them
            if len(all_analyses) > 1:
                print("Creating integrated summary from all chunks...")
                meta_prompt = """
                Below are several summary sections of the same topic from different text chunks.
                Integrate these summaries into ONE cohesive, fluid summary that captures all the important information.
                Do not structure this as a list of separate summaries - create ONE unified text.
                
                Summaries to integrate:
                {text}
                
                INTEGRATED SUMMARY:
                """
                meta_prompt_template = ChatPromptTemplate.from_template(meta_prompt)
                meta_chain = meta_prompt_template | llm
                final_result = meta_chain.invoke({"text": "\n\n".join(all_analyses)})
                return final_result.content
            else:
                return all_analyses[0]
        else:
            prompt = ChatPromptTemplate.from_template(analysis_prompt)
            chain = prompt | llm
            result = chain.invoke({"text": text})
            return result.content
    except Exception as e:
        print(f"Error during LLM analysis: {str(e)}")
        return ""

def campusLife(uni_name: str, subject: str) -> str:
    """Search and analyze information about campus life and student activities."""
    print(f"\nSearching for campus life information for {uni_name}...")
    
    # Search queries for campus life
    queries = [
        f"{uni_name} student life campus activities",
        f"{uni_name} student clubs organizations",
        f"{uni_name} campus facilities {subject}",
        f"{uni_name} student housing accommodation"
    ]
    
    # Collect all content first
    all_content = []
    max_retries = 2
    
    for i, query in enumerate(queries, 1):
        print(f"\nProcessing campus life query {i}/{len(queries)}: {query}")
        for retry in range(max_retries):
            try:
                results = google_search_with_timeout(query, num_results=2)
                print(f"Found {len(results)} results")
                
                for j, result in enumerate(results, 1):
                    print(f"Scraping result {j}/{len(results)}: {result.url}")
                    try:
                        content = scrape_text_from_url(result.url, max_length=5000)
                        if content:
                            all_content.append(content)
                            print("Successfully scraped content")
                        else:
                            print("No content found in URL")
                    except Exception as e:
                        print(f"Error scraping URL: {str(e)}")
                        continue
                    
                    # Add a small delay between requests
                    time.sleep(1)
                
                # If we got here, the query was successful
                break
            except Exception as e:
                print(f"Error processing query (attempt {retry + 1}/{max_retries}): {str(e)}")
                if retry < max_retries - 1:
                    print("Retrying...")
                    time.sleep(2)  # Wait before retrying
                else:
                    print("Max retries reached, moving to next query")
    
    if not all_content:
        return "Keine Informationen zum Campusleben gefunden."
    
    # Now analyze all collected content at once
    print("\nAnalyzing all campus life content with LLM...")
    analysis_prompt = f"""Analysiere den folgenden Text über Campusleben und studentische Aktivitäten an {uni_name}.

Erstelle eine präzise, informative Zusammenfassung für deutsche Austauschstudierende.

Berücksichtige besonders:
- Besondere Stärken des Campus (Infrastruktur, Ausstattung, Lage)
- Konkrete Wohnsituationen und Kosten
- Wichtigste Clubs oder Aktivitäten für internationale Studenten
- Besondere Veranstaltungen oder Traditionen

Vermeide allgemeine Floskeln und konzentriere dich auf spezifische, nützliche Details.
Beschreibe konkrete Beispiele und gib, wenn möglich, ungefähre Zahlen oder Daten an.
Verwende 8 - 10 Sätze für die gesamte Zusammenfassung.

Text: {{text}}

ZUSAMMENFASSUNG:"""
    
    try:
        # Limit the total combined text size to avoid token limit issues
        combined_text = "\n".join(all_content)
        if len(combined_text) > 100000:
            print("Content is very large, trimming to avoid token limits...")
            combined_text = combined_text[:100000] + "..."
            
        result = analyze_content_with_llm(combined_text, analysis_prompt, max_chunk_size=20000)
        print("Campus life analysis completed successfully")
        return result
    except Exception as e:
        print(f"Error during LLM analysis: {str(e)}")
        return "Fehler bei der Analyse des Campuslebens."

def rankingAndResearchAreas(uni_name: str, subject: str) -> str:
    """Search and analyze information about university rankings and research areas."""
    print(f"\nSearching for ranking and research information for {uni_name} in {subject}...")
    
    # Search queries for rankings and research
    queries = [
        f"{uni_name} {subject} department research areas",
        f"{uni_name} {subject} THE ranking",
        f"{uni_name} {subject} research centers",
        f"{uni_name} {subject} academic reputation"
    ]
    
    # Collect all content first
    all_content = []
    max_retries = 2
    
    for i, query in enumerate(queries, 1):
        print(f"\nProcessing ranking query {i}/{len(queries)}: {query}")
        for retry in range(max_retries):
            try:
                results = google_search_with_timeout(query, num_results=2)
                print(f"Found {len(results)} results")
                
                for j, result in enumerate(results, 1):
                    print(f"Scraping result {j}/{len(results)}: {result.url}")
                    try:
                        content = scrape_text_from_url(result.url, max_length=5000)
                        if content:
                            all_content.append(content)
                            print("Successfully scraped content")
                        else:
                            print("No content found in URL")
                    except Exception as e:
                        print(f"Error scraping URL: {str(e)}")
                        continue
                    
                    # Add a small delay between requests
                    time.sleep(1)
                
                # If we got here, the query was successful
                break
            except Exception as e:
                print(f"Error processing query (attempt {retry + 1}/{max_retries}): {str(e)}")
                if retry < max_retries - 1:
                    print("Retrying...")
                    time.sleep(2)  # Wait before retrying
                else:
                    print("Max retries reached, moving to next query")
    
    if not all_content:
        return "Keine Informationen zu Rankings und Forschungsbereichen gefunden."
    
    # Now analyze all collected content at once
    print("\nAnalyzing all ranking and research content with LLM...")
    analysis_prompt = f"""Analysiere den folgenden Text über Rankings und Forschungsbereiche an {uni_name} im Fach {subject}.

Erstelle eine faktenbasierte, präzise Zusammenfassung für Austauschstudierende.

Priorisiere folgende Aspekte in deiner Analyse:
- Konkrete Rankingposition für das THE Ranking
- 2-3 herausragende Forschungsbereiche mit konkreten Beispielen
- Besondere Ausstattung oder Ressourcen für Studierende
- Berühmte Professoren oder Forschungsprojekte
- Internationales Ansehen in spezifischen Teilbereichen

Nenne exakte Zahlen, Namen und Daten, wo immer möglich.
Behalte einen sachlichen, informativen Stil bei.
Verwende 8 - 10 Sätze für die gesamte Zusammenfassung.

Text: {{text}}

ZUSAMMENFASSUNG:"""
    
    try:
        combined_text = "\n".join(all_content)
        result = analyze_content_with_llm(combined_text, analysis_prompt, max_chunk_size=20000)
        print("Ranking and research analysis completed successfully")
        return result
    except Exception as e:
        print(f"Error during LLM analysis: {str(e)}")
        return "Fehler bei der Analyse der Rankings und Forschungsbereiche."


def main(uni_name: str, subject: str):
    """Main function to gather all information."""
    print("\n=== Campusleben und Aktivitäten ===")
    campus_info = campusLife(uni_name, subject)
    print(campus_info)
    
    print("\n=== Rankings und Forschungsbereiche ===")
    ranking_info = rankingAndResearchAreas(uni_name, subject)
    print(ranking_info)
    
    return (campus_info, ranking_info)

if __name__ == "__main__":
    main("University of California, Santa Barbara", "Computer Science")