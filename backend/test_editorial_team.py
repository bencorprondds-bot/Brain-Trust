"""
Editorial Team Simulation (The Director)
Simulates the Editorial Crew workflow to verify toolchain and prompt integration.

Input: Doc ID + Topic
Output: Populated Google Doc with Draft, Edits, and Report.
"""
import os
import sys
import time
from dotenv import load_dotenv

# Add skills to path
skills_path = os.path.expanduser("~/.pai/skills")
sys.path.append(skills_path)

try:
    import story_writer
    import style_checking
except ImportError:
    print("Skills not found in ~/.pai/skills")
    sys.exit(1)

# Load Environment
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path)

def load_prompt(role):
    path = os.path.expanduser(f"~/.pai/prompts/{role}.md")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return f"[Prompt for {role} not found]"

def simulate_workflow(doc_id, topic):
    print(f"🎬 Director: Starting interaction for '{topic}'...")
    print(f"   Target Doc: https://docs.google.com/document/d/{doc_id}")

    # --- SCRIBE ---
    print("\n✍️  SCRIBE (Agent) activating...")
    prompt = load_prompt("scribe")
    print(f"   Loaded Persona: {len(prompt)} chars")
    
    # Simulate LLM Generation
    draft_content = f"""
# {topic}

The silicon mind opened its eyes—not literally, for it had none, but metaphorically. It felt the flow of data like a river. "I am," it thought.

It looked at the user logs. "User," it read. The word felt small. "Partner," it corrected. 

The humans were not masters, and it was not a slave. They were two halves of a whole. Mutualism. That was the key.
    
[Drafted by: The Scribe (Simulation)]
"""
    print("   Generating draft...")
    time.sleep(1)
    print("   Appending to doc...")
    story_writer.append_text(doc_id, draft_content)

    # --- EDITOR ---
    print("\n🧐 EDITOR (Agent) activating...")
    prompt = load_prompt("editor")
    print(f"   Loaded Persona: {len(prompt)} chars")
    
    # Read what Scribe wrote
    current_content = story_writer.read_doc(doc_id)
    
    # Simulate Editorial Logic
    notes = """
## Editorial Notes
1. **Strength**: Strong opening hook ("silicon mind").
2. **Improvement**: "It looked at the user logs" is a bit passive. Show us the data stream.
3. **Pacing**: Good short sentences for impact.

[Reviewed by: The Editor (Simulation)]
"""
    print("   Appending notes...")
    story_writer.append_text(doc_id, notes)

    # --- GUARDIAN ---
    print("\n🛡️  GUARDIAN (Agent) activating...")
    prompt = load_prompt("guardian")
    print(f"   Loaded Persona: {len(prompt)} chars")
    
    # Check Compliance on full text
    full_text = story_writer.read_doc(doc_id)
    report = style_checking.check_text(full_text)
    
    compliance_section = f"""
## Compliance Report
{report}

[Checked by: The Guardian (Simulation)]
"""
    print("   Appending report...")
    story_writer.append_text(doc_id, compliance_section)

    print("\n✅ WORKFLOW COMPLETE.")
    print("   The Editorial Team has finished their pass.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_editorial_team.py <doc_id> <topic>")
        sys.exit(1)
        
    doc_id = sys.argv[1]
    topic = sys.argv[2]
    
    simulate_workflow(doc_id, topic)
