#!/usr/bin/env python3
# NAME: web_search
# DESCRIPTION: Search the web using DuckDuckGo and return top results
# PARAM: query (str) - The search query

import sys
from duckduckgo_search import DDGS

def main():
    if len(sys.argv) < 2:
        print("ERROR: Missing required argument 'query'")
        sys.exit(1)
    
    query = sys.argv[1]
    
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
            
            if not results:
                print(f"No results found for: {query}")
                return
            
            print(f"Search results for: {query}\n")
            for i, result in enumerate(results, 1):
                print(f"{i}. {result['title']}")
                print(f"   {result['href']}")
                print(f"   {result['body'][:150]}...\n")
    
    except Exception as e:
        print(f"ERROR: Search failed - {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
