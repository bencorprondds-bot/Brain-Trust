"""Quick test to verify TELOS context loading works."""
from app.core.context_loader import ContextLoader

def test_telos():
    loader = ContextLoader()
    
    try:
        context = loader.load_context()
        print("✅ TELOS Context Loaded Successfully!")
        print(f"\n📋 MISSION ({len(context.mission)} chars):")
        print(context.mission[:200] + "..." if len(context.mission) > 200 else context.mission)
        print(f"\n🎯 GOALS ({len(context.goals)} chars):")
        print(context.goals[:200] + "..." if len(context.goals) > 200 else context.goals)
        print(f"\n💭 BELIEFS ({len(context.beliefs)} chars):")
        print(context.beliefs[:200] + "..." if len(context.beliefs) > 200 else context.beliefs)
        print(f"\n👤 IDENTITY ({len(context.identity)} chars):")
        print(context.identity[:200] + "..." if len(context.identity) > 200 else context.identity)
        print(f"\n🔐 Checksum: {context.checksum}")
        return True
    except Exception as e:
        print(f"❌ TELOS Context Error: {e}")
        return False

if __name__ == "__main__":
    test_telos()
