
import os
import sys
from pathlib import Path
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.tools.script_execution_tool import ScriptExecutionTool

def test_story_writer():
    print("=" * 60)
    print("TESTING STORY WRITER SKILL")
    print("=" * 60)
    
    # Path to skill
    skill_path = Path.home() / ".pai" / "skills" / "story_writer.py"
    
    if not skill_path.exists():
        print(f"❌ Skill not found at {skill_path}")
        return
        
    tool = ScriptExecutionTool(
        name="story_writer",
        description="Editor Tool",
        script_path=skill_path,
        timeout=60
    )
    
    import time
    
    # 1. Create Doc
    print("\n1. Creating Test Document...")
    time.sleep(2)
    try:
        output = tool._run(
            action="create", 
            title="Brain Trust Test Doc", 
            content="Initial content from test script.",
            folder_id="1fKYixOC9aDcm-XHAIHhfGj3rKlRg5b-i"  # 02_In_Development
        )
        print(output)
        
        # Parse ID from output: "Created document 'Brain Trust Test Doc' (ID: 123...)"
        if "Created document" not in output:
            print(f"❌ Failed to create document. Output: {output}")
            return
            
        doc_id = output.split("(ID: ")[1].split(")")[0]
        print(f"   ✅ Doc ID: {doc_id}")
        
    except Exception as e:
        print(f"❌ Error creating doc: {e}")
        return

    # 2. Append Text
    print("\n2. Appending Text...")
    time.sleep(2)
    try:
        output = tool._run(
            action="append",
            doc_id=doc_id,
            content="This is a new paragraph added by the editor agent."
        )
        print(output)
    except Exception as e:
        print(f"❌ Error appending text: {e}")

    # 3. Read Doc
    print("\n3. Reading Document...")
    time.sleep(2)
    try:
        content = tool._run(
            action="read",
            doc_id=doc_id
        )
        print(f"--- Content Start ---\n{content}\n--- Content End ---")
        
        if "Initial content" in content and "added by the editor agent" in content:
            print("\n✅ Verification SUCCESS: All content found.")
        else:
            print("\n❌ Verification FAILED: Content missing.")
            
    except Exception as e:
        print(f"❌ Error reading doc: {e}")

if __name__ == "__main__":
    test_story_writer()
