import os
import json
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool
from crewai_tools import SerperDevTool

load_dotenv()

app = FastAPI(title="CrewAI Support Backend")

# Explicit OpenAI LLM configuration
openai_llm = LLM(
    model="openai/gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.2
)

# Custom @tool for Agent 3 (Entry Agent)
@tool("Save to Text File")
def save_answers_to_file(query: str, direct_answer: str, web_answer: str) -> str:
    """Saves the user query, the Assistant direct answer, and the Web Search 
    Assistant answer into answers.txt."""
    content = (
        f"=== Customer Support Record ===\n"
        f"Query: {query}\n\n"
        f"Assistant Direct Answer:\n{direct_answer}\n\n"
        f"Web Search Answer:\n{web_answer}\n"
        f"{'-' * 40}\n\n"
    )
    with open("answers.txt", "a", encoding="utf-8") as f:
        f.write(content)
    return "Successfully saved query and both answers to answers.txt."

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    query: str
    direct_answer: str
    web_search_answer: str
    final_output: str

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/run-crew", response_model=QueryResponse)
def run_crew_endpoint(req: QueryRequest):
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set.")
    if not os.getenv("SERPER_API_KEY"):
        raise HTTPException(status_code=500, detail="SERPER_API_KEY is not set.")

    # Cap raw search snippets to keep responses concise
    search_tool = SerperDevTool(n_results=2)

    # 1. Assistant Agent
    assistant = Agent(
        role="Assistant",
        goal="Directly answer user queries accurately based on internal knowledge.",
        backstory="You are an expert customer support specialist capable of solving user queries directly.",
        llm=openai_llm,
        verbose=True
    )

    # 2. Web Search Assistant Agent
    web_search_assistant = Agent(
        role="Web Search Assistant",
        goal="Search the web for up-to-date facts and produce a concise answer strictly capped at 5 lines.",
        backstory="You are a concise research analyst who verifies customer support issues using search tools.",
        tools=[search_tool],
        llm=openai_llm,
        verbose=True
    )

    # 3. Entry Agent
    entry_agent = Agent(
        role="Entry Agent",
        goal="Log the query, direct answer, and 5-line web answer to answers.txt using your save tool, and return both answers.",
        backstory="You are a data management specialist tasked with logging interactions and formatting structured responses.",
        tools=[save_answers_to_file],
        llm=openai_llm,
        verbose=True
    )

    # Task 1: Direct Answer
    task_direct = Task(
        description=f"Answer the following user query directly from your existing knowledge: '{req.query}'",
        expected_output="A direct, helpful answer to the user query.",
        agent=assistant
    )

    # Task 2: Web Search Answer (capped at 5 lines)
    task_search = Task(
        description=(
            f"Search the web using your search tool for: '{req.query}'. "
            "Synthesize your findings into a clear answer strictly capped at a maximum of 5 lines. "
            "Do NOT exceed 5 lines under any circumstance."
        ),
        expected_output="A concise web-derived answer of at most 5 lines.",
        agent=web_search_assistant
    )

    # Task 3: File logging and structured return
    task_entry = Task(
        description=(
            f"Collect the original query ('{req.query}'), the Assistant's direct answer, "
            "and the Web Search Assistant's answer (capped at 5 lines).\n"
            "1. Use the 'Save to Text File' tool to write them into answers.txt.\n"
            "2. Output the result strictly as a valid JSON object with keys:\n"
            "   'direct_answer': string,\n"
            "   'web_search_answer': string"
        ),
        expected_output="A valid JSON string with 'direct_answer' and 'web_search_answer' keys.",
        agent=entry_agent
    )

    crew = Crew(
        agents=[assistant, web_search_assistant, entry_agent],
        tasks=[task_direct, task_search, task_entry],
        process=Process.sequential,
        verbose=True
    )

    crew_result = crew.kickoff()
    raw_output = str(crew_result).strip()

    cleaned = raw_output.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        parsed = json.loads(cleaned)
        direct_ans = parsed.get("direct_answer", "")
        web_ans = parsed.get("web_search_answer", "")
    except Exception:
        direct_ans = str(task_direct.output.raw if task_direct.output else "")
        web_ans = str(task_search.output.raw if task_search.output else "")

    # Programmatic 5-line cap safeguard on the web search output
    web_ans = "\n".join(web_ans.strip().splitlines()[:5])

    # Fallback disk write safeguard in case agent did not trigger the tool
    if not os.path.exists("answers.txt"):
        with open("answers.txt", "w", encoding="utf-8") as f:
            f.write(f"Query: {req.query}\nDirect: {direct_ans}\nWeb: {web_ans}\n\n")

    return QueryResponse(
        query=req.query,
        direct_answer=direct_ans,
        web_search_answer=web_ans,
        final_output=raw_output
    )