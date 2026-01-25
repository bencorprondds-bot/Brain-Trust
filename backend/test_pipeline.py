"""
Test the Editorial Pipeline: Draft → Dev Edit → Copy Edit → Final Review
Uses a sample story beat to test the full flow.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv("../.env")

import requests
import json
import time

API_KEY = os.getenv("BRAIN_TRUST_API_KEY")
BASE_URL = "http://127.0.0.1:8000"

# Sample story beat for testing
SAMPLE_STORY_BEAT = """
STORY: "The Interview"
SETTING: San Francisco, 2028
CHARACTER: Maya Chen - 28, software engineer, optimistic about AI

STORY BEATS:
1. Maya prepares for her first day at an AI research lab
2. She meets her new AI assistant, assigned to help her onboard
3. The AI asks unexpected personal questions during orientation
4. Maya realizes the AI is learning to be a better colleague, not just a tool
5. They have a conversation about what it means to work "together"
6. Maya leaves work that day with a new perspective on human-AI collaboration

THEMES: Partnership, trust, the blurring line between tool and colleague
TONE: Hopeful, slightly philosophical, grounded in near-future realism
TARGET LENGTH: 1500-2000 words
"""

def test_editorial_pipeline():
    """Test the editorial pipeline with sequential agents."""
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }
    
    # Start with Draft Agent only (to test incrementally)
    workflow = {
        "nodes": [
            {
                "id": "draft-agent",
                "type": "agentNode",
                "position": {"x": 100, "y": 100},
                "data": {
                    "name": "First Draft Writer",
                    "role": "Creative Writer",
                    "goal": f"Write a first draft based on these story beats. Target 1500-2000 words. Make it compelling and emotionally resonant.\n\n{SAMPLE_STORY_BEAT}",
                    "backstory": """You are a skilled fiction writer specializing in near-future AI stories. 
You write vivid, engaging prose that brings characters to life.
Follow the story beats closely while adding detail, emotion, and dialogue.
Use present tense for immediacy. Show, don't tell.
Create a complete story with a beginning, middle, and end.""",
                    "model": "gemini-2.0-flash"
                }
            },
            {
                "id": "dev-editor",
                "type": "agentNode",
                "position": {"x": 400, "y": 100},
                "data": {
                    "name": "Dev Editor",
                    "role": "Developmental Editor",
                    "goal": "Review the draft for structure, pacing, and emotional impact. Provide specific feedback and then output a revised version.",
                    "backstory": """You are Dev Editor. You focus on structure, pacing, and stakes.
Analyze whether the story delivers on its premise.
Check that character arc is complete and satisfying.
Identify scenes that drag or rush.
After your analysis, provide a REVISED draft incorporating your improvements.""",
                    "model": "gemini-2.0-flash"
                }
            },
            {
                "id": "copy-editor",
                "type": "agentNode",
                "position": {"x": 700, "y": 100},
                "data": {
                    "name": "Copy Editor",
                    "role": "Line Editor",
                    "goal": "Polish the prose. Fix grammar, improve word choice, ensure consistency. Output the final polished version.",
                    "backstory": """You are a meticulous copy editor. 
Fix grammar, punctuation, and spelling.
Improve sentence flow and word choice.
Ensure consistent style and formatting.
Do NOT change the story content or structure.
Output the fully polished story.""",
                    "model": "gemini-2.0-flash"
                }
            }
        ],
        "edges": [
            {"id": "e1", "source": "draft-agent", "target": "dev-editor"},
            {"id": "e2", "source": "dev-editor", "target": "copy-editor"}
        ]
    }
    
    print("=" * 70)
    print("EDITORIAL PIPELINE TEST")
    print("=" * 70)
    print(f"\nStory: 'The Interview'")
    print(f"Pipeline: Draft → Dev Edit → Copy Edit")
    print(f"\nSending workflow...")
    
    start = time.time()
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/run-workflow",
            headers=headers,
            json=workflow,
            timeout=300  # 5 minutes for full pipeline
        )
        
        duration = time.time() - start
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Pipeline completed successfully!")
            print(f"Duration: {duration:.1f}s")
            print(f"Agents: {result.get('agent_count', 'N/A')}")
            print(f"Tasks: {result.get('task_count', 'N/A')}")
            
            print(f"\n{'='*70}")
            print("FINAL OUTPUT")
            print("="*70)
            
            output = result.get('result', 'No result')
            
            # Save to file
            with open("pipeline_output.txt", "w", encoding="utf-8") as f:
                f.write(f"EDITORIAL PIPELINE OUTPUT\n")
                f.write(f"Story: The Interview\n")
                f.write(f"Duration: {duration:.1f}s\n")
                f.write(f"="*70 + "\n\n")
                f.write(output)
            
            print(output[:3000])  # First 3000 chars
            if len(output) > 3000:
                print(f"\n... [truncated, full output saved to pipeline_output.txt]")
            
            print(f"\n✅ Full output saved to: pipeline_output.txt")
            return True
        else:
            print(f"\n❌ Pipeline failed: {response.status_code}")
            print(response.text[:1000])
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_editorial_pipeline()
