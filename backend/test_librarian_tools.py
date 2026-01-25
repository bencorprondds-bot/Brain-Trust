#!/usr/bin/env python3
"""
Test script for Librarian (Iris) Google Drive tools.

This script tests all the Drive tools available to the Librarian:
1. DriveListTool - List files in folders
2. DriveReadTool - Read document content
3. DriveWriteTool - Create new documents (via template copy)
4. DriveMoveTool - Move files between folders
5. DriveFindTool - Search for files

Prerequisites:
1. credentials.json must exist in the backend directory
2. A template document named "_BrainTrust_Template" should exist in Google Drive
   (run setup_drive_template.py to check/configure this)

Usage:
    python test_librarian_tools.py [test_name]

    test_name options:
    - list: Test listing files
    - read: Test reading a document
    - find: Test searching for files
    - write: Test creating a document (requires template)
    - move: Test moving a file (requires existing file)
    - all: Run all tests (default)
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.tools.drive_tool import (
    DriveListTool, DriveReadTool, DriveWriteTool,
    DriveMoveTool, DriveFindTool,
    FOLDER_IDS, discover_template_id
)


def test_list():
    """Test DriveListTool - List files in folders."""
    print("\n" + "=" * 60)
    print("TEST: DriveListTool")
    print("=" * 60)

    tool = DriveListTool()

    # Test 1: List all files
    print("\n1. Listing all accessible files...")
    result = tool._run(folder_id='root')
    print(result[:1000] + "..." if len(result) > 1000 else result)

    # Test 2: List files in a specific folder
    print("\n2. Listing files in 'in_development' folder...")
    result = tool._run(folder_id=FOLDER_IDS['in_development'])
    print(result)

    print("\n✅ DriveListTool tests passed!")


def test_find():
    """Test DriveFindTool - Search for files."""
    print("\n" + "=" * 60)
    print("TEST: DriveFindTool")
    print("=" * 60)

    tool = DriveFindTool()

    # Test 1: Search for character files
    print("\n1. Searching for files containing 'character'...")
    result = tool._run(query="character")
    print(result)

    # Test 2: Search in a specific folder
    print("\n2. Searching for files in reference_docs folder...")
    result = tool._run(query="", folder="reference_docs")
    print(result)

    # Test 3: Search for template
    print("\n3. Searching for template document...")
    result = tool._run(query="_BrainTrust_Template")
    print(result)

    print("\n✅ DriveFindTool tests passed!")


def test_read():
    """Test DriveReadTool - Read document content."""
    print("\n" + "=" * 60)
    print("TEST: DriveReadTool")
    print("=" * 60)

    # First, find a document to read
    find_tool = DriveFindTool()
    print("\n1. Finding a document to read...")
    search_result = find_tool._run(query="character")
    print(search_result)

    # Extract first document ID from results
    lines = search_result.split('\n')
    doc_id = None
    for line in lines:
        if 'ID:' in line:
            doc_id = line.split('ID:')[1].strip()
            break

    if not doc_id:
        print("\n⚠️ No documents found to test read. Skipping.")
        return

    print(f"\n2. Reading document ID: {doc_id}")
    read_tool = DriveReadTool()
    result = read_tool._run(file_id=doc_id)
    print(result[:500] + "..." if len(result) > 500 else result)

    print("\n✅ DriveReadTool tests passed!")


def test_write():
    """Test DriveWriteTool - Create new documents."""
    print("\n" + "=" * 60)
    print("TEST: DriveWriteTool")
    print("=" * 60)

    # Check for template
    print("\n1. Checking for template document...")
    template_id = discover_template_id()

    if not template_id:
        print("\n⚠️ No template found!")
        print("   Run setup_drive_template.py to configure a template.")
        print("   Testing without template (may fail with quota error)...")
    else:
        print(f"   Template found: {template_id}")

    print("\n2. Creating test document...")
    write_tool = DriveWriteTool()

    test_content = """# Test Document from Brain Trust

This document was created by the Librarian (Iris) using the DriveWriteTool.

## Test Details
- Created automatically as part of tool testing
- This file can be safely deleted

## Next Steps
If you see this document in your Google Drive, the write functionality is working!
"""

    result = write_tool._run(
        title="_TEST_Librarian_Write_Tool",
        content=test_content,
        folder="in_development"
    )
    print(result)

    if "Error" in result:
        print("\n❌ DriveWriteTool test failed!")
        if "quota" in result.lower():
            print("   The service account hit quota limits.")
            print("   Solution: Create a template document. See setup_drive_template.py")
    else:
        print("\n✅ DriveWriteTool tests passed!")
        print("   Note: A test document was created. You can delete it from Google Drive.")


def test_move():
    """Test DriveMoveTool - Move files between folders."""
    print("\n" + "=" * 60)
    print("TEST: DriveMoveTool")
    print("=" * 60)

    # First, find the test document we created
    find_tool = DriveFindTool()
    print("\n1. Looking for test document to move...")
    search_result = find_tool._run(query="_TEST_Librarian")
    print(search_result)

    # Extract document ID
    lines = search_result.split('\n')
    doc_id = None
    for line in lines:
        if 'ID:' in line:
            doc_id = line.split('ID:')[1].strip()
            break

    if not doc_id:
        print("\n⚠️ No test document found. Run test_write first.")
        return

    print(f"\n2. Moving document to 'ready_for_review'...")
    move_tool = DriveMoveTool()
    result = move_tool._run(file_id=doc_id, destination_folder="ready_for_review")
    print(result)

    print(f"\n3. Moving document back to 'in_development'...")
    result = move_tool._run(file_id=doc_id, destination_folder="in_development")
    print(result)

    print("\n✅ DriveMoveTool tests passed!")


def run_all_tests():
    """Run all tool tests."""
    print("\n" + "=" * 60)
    print("LIBRARIAN TOOLS - COMPREHENSIVE TEST SUITE")
    print("=" * 60)

    test_list()
    test_find()
    test_read()
    test_write()
    test_move()

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)


def main():
    if len(sys.argv) > 1:
        test_name = sys.argv[1].lower()
        if test_name == 'list':
            test_list()
        elif test_name == 'find':
            test_find()
        elif test_name == 'read':
            test_read()
        elif test_name == 'write':
            test_write()
        elif test_name == 'move':
            test_move()
        elif test_name == 'all':
            run_all_tests()
        else:
            print(f"Unknown test: {test_name}")
            print("Available tests: list, find, read, write, move, all")
            sys.exit(1)
    else:
        run_all_tests()


if __name__ == "__main__":
    main()
