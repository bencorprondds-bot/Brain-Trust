"""
Editorial Team Crew (The Director)
Orchestrates the Scribe, Editor, and Guardian agents to produce content.

Input: Topic + Target Google Doc ID
Output: A fully drafted, reviewed, and compliance-checked story in the Google Doc.
"""
import os
import sys
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from langchain_google_genai import ChatGoogleGenerativeAI

# Add skills to path
skills_path = os.path.expanduser("~/.pai/skills")
sys.path.append(skills_path)

# Import Skills
try:
    import story_writer
    import style_checking
except ImportError:
    print("Skills not found in ~/.pai/skills")
    sys.exit(1)

# Load Environment
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path)

# Ensure keys are available for LiteLLM (it checks GEMINI_API_KEY usually)
if "GEMINI_API_KEY" in os.environ:
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]
elif "GOOGLE_API_KEY" in os.environ:
    os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]

key = os.environ.get("GOOGLE_API_KEY")
if not key:
    print("!! GOOGLE_API_KEY not found in environment!")
else:
    print(f"OK: GOOGLE_API_KEY loaded: {key[:4]}...")

# Define Custom Tools via Wrapper
from langchain.tools import tool

class EditorialTools:
    @tool("Read Document")
    def read_doc(doc_id: str):
        """Read the content of a Google Doc."""
        return story_writer.read_doc(doc_id)

    @tool("Append Text")
    def append_text(data: str):
        """Append text to a Google Doc. Input format: 'doc_id|content'."""
        try:
            doc_id, content = data.split("|", 1)
            return story_writer.append_text(doc_id, content)
        except ValueError:
            return "Error: Input must be 'doc_id|content'"

    @tool("Check Style")
    def check_style(text: str):
        """Check text against the Style Guide."""
        return style_checking.check_text(text)

# Helper to load prompts
def load_prompt(role):
    path = os.path.expanduser(f"~/.pai/prompts/{role}.md")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return f"You are the {role}."

# --- AGENT DEFINITIONS ---
# Using LiteLLM string format for robustness
llm_model = "gemini/gemini-1.5-flash"

scribe = Agent(
    role='The Scribe',
    goal='Write engaging drafts directly into the Google Doc.',
    backstory=load_prompt('scribe'),
    tools=[EditorialTools.read_doc, EditorialTools.append_text],
    llm=llm_model,
    verbose=True,
    allow_delegation=False
)

editor = Agent(
    role='The Editor',
    goal='Review the draft and append constructive notes.',
    backstory=load_prompt('editor'),
    tools=[EditorialTools.read_doc, EditorialTools.append_text],
    llm=llm_model,
    verbose=True,
    allow_delegation=False
)

guardian = Agent(
    role='The Guardian',
    goal='Ensure compliance with AI Mutualism and Style Guide.',
    backstory=load_prompt('guardian'),
    tools=[EditorialTools.read_doc, EditorialTools.append_text, EditorialTools.check_style],
    llm=llm_model,
    verbose=True,
    allow_delegation=False
)

# --- TASK DEFINITIONS ---

def create_crew(topic, doc_id):
    
    # Task 1: Draft
    task1 = Task(
        description=f"""
        1. Read the document ({doc_id}) to see if there is existing content.
        2. If empty or minimal, write a draft about: '{topic}'.
        3. Append the draft to the document using the 'Append Text' tool.
        4. Sign your work.
        """,
        agent=scribe,
        expected_output="A drafted story appended to the Google Doc."
    )

    # Task 2: Edit
    task2 = Task(
        description=f"""
        1. Read the document ({doc_id}) to review the Scribe's draft.
        2. Identify strengths and weaknesses.
        3. Append a section titled '## Editorial Notes' with your feedback.
        """,
        agent=editor,
        expected_output="Editorial notes appended to the Google Doc."
    )

    # Task 3: Compliance
    task3 = Task(
        description=f"""
        1. Read the document ({doc_id}).
        2. Use the 'Check Style' tool on the content.
        3. Append a section titled '## Compliance Report' with the results.
        """,
        agent=guardian,
        expected_output="Compliance report appended to the Google Doc."
    )

    crew = Crew(
        agents=[scribe, editor, guardian],
        tasks=[task1, task2, task3],
        verbose=2,
        process=Process.sequential
    )
    
    return crew

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python editorial_crew.py <doc_id> <topic>")
        sys.exit(1)
        
    doc_id = sys.argv[1]
    topic = sys.argv[2]
    
    print(f"🚀 Starting Editorial Crew...")
    print(f"Topic: {topic}")
    print(f"Target Doc: {doc_id}")
    
    crew = create_crew(topic, doc_id)
    result = crew.kickoff()
    
    print("\n✅ Crew Finished!")
    print(result)
