#!/usr/bin/env python3
# NAME: file_analyzer
# DESCRIPTION: Analyze a file and return statistics (size, lines, type)
# PARAM: filepath (str) - Path to the file to analyze

import sys
import os
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("ERROR: Missing required argument 'filepath'")
        sys.exit(1)
    
    filepath = Path(sys.argv[1])
    
    if not filepath.exists():
        print(f"ERROR: File not found: {filepath}")
        sys.exit(1)
    
    try:
        # Get file stats
        stats = filepath.stat()
        size_bytes = stats.st_size
        
        # Determine file type
        suffix = filepath.suffix.lower()
        file_type = "Unknown"
        if suffix in ['.py', '.js', '.java', '.cpp', '.c']:
            file_type = "Code"
        elif suffix in ['.txt', '.md', '.rst']:
            file_type = "Text"
        elif suffix in ['.json', '.yaml', '.yml', '.xml']:
            file_type = "Data"
        
        # Count lines if text file
        line_count = 0
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                line_count = sum(1 for _ in f)
        except:
            pass
        
        # Output results
        print(f"File Analysis: {filepath.name}")
        print(f"  Type: {file_type}")
        print(f"  Size: {size_bytes:,} bytes ({size_bytes / 1024:.2f} KB)")
        if line_count > 0:
            print(f"  Lines: {line_count:,}")
        print(f"  Modified: {stats.st_mtime}")
    
    except Exception as e:
        print(f"ERROR: Analysis failed - {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
