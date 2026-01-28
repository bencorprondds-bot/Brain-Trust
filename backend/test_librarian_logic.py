import sys
import os
import io

# Fix Windows console encoding for Unicode characters
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.core.workflow_parser import WorkflowParser

def test_librarian_prompt_injection():
    print("Testing Librarian Prompt Injection...")

    # Mock Workflow Data
    mock_workflow = {
        "nodes": [
            {
                "id": "librarian",
                "type": "agentNode",
                "data": {
                    "role": "Librarian",
                    "backstory": "I am a librarian.",
                    "goal": "Help users find information.",
                    "model": "gemini-2.0-flash"
                }
            }
        ],
        "edges": []
    }

    parser = WorkflowParser(mock_workflow)
    crew = parser.parse_graph()
    agent = crew.agents[0]
    task = crew.tasks[0]

    print("\n[Agent Backstory Preview]")
    print(agent.backstory[:500] + "..." if len(agent.backstory) > 500 else agent.backstory)

    print("\n[Task Description Preview]")
    print(task.description)

    # Check 1: TELOS context injection (AGENT INSTRUCTIONS header from context_loader)
    backstory_ok = "AGENT INSTRUCTIONS" in agent.backstory

    # Check 2: Librarian-specific instructions in task description
    task_ok = "<FETCHED_FILES>" in task.description

    print("\n--- Test Results ---")
    if backstory_ok:
        print("✅ PASS: TELOS context injected into backstory (AGENT INSTRUCTIONS found)")
    else:
        print("❌ FAIL: TELOS context missing from backstory")

    if task_ok:
        print("✅ PASS: Librarian file tagging instructions in task description")
    else:
        print("❌ FAIL: <FETCHED_FILES> instruction missing from task description")

    if backstory_ok and task_ok:
        print("\n✅ ALL TESTS PASSED")
    else:
        print("\n❌ SOME TESTS FAILED")

if __name__ == "__main__":
    test_librarian_prompt_injection()
