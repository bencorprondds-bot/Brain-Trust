#!/bin/bash
# Setup pytest for Brain-Trust development

echo "🧪 Setting up pytest environment..."

# Install test dependencies
echo "📦 Installing pytest and plugins..."
pip install pytest>=8.0.0 \
    pytest-asyncio>=0.23.0 \
    pytest-cov>=4.1.0 \
    pytest-timeout>=2.2.0 \
    pytest-mock>=3.12.0 \
    requests-mock>=1.11.0

echo ""
echo "✅ Pytest setup complete!"
echo ""
echo "Quick start commands:"
echo "  pytest                    # Run all tests"
echo "  pytest -v                 # Verbose output"
echo "  pytest -m unit            # Run only unit tests"
echo "  pytest -m integration     # Run integration tests"
echo "  pytest -k librarian       # Run tests matching 'librarian'"
echo ""
echo "📖 See TESTING.md for full documentation"
