#!/bin/bash
# Setup script for Nitpick VS Code extension development

set -e

echo "🚀 Setting up Nitpick VS Code Extension..."

# Check if in correct directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Must run from editors/vscode directory"
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Error: Node.js not found. Please install Node.js 18+ from https://nodejs.org"
    exit 1
fi

echo "📦 Installing dependencies..."
npm install

echo "🔨 Compiling TypeScript..."
npm run compile

# Check for nitpick-ls binary
if [ ! -f "bin/linux/nitpick-ls" ]; then
    echo "⚠️  Warning: nitpick-ls binary not found in bin/linux/"
    echo "   Run from nitpick root: cp build/nitpick-ls editors/vscode/bin/linux/"
fi

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Open this folder in VS Code"
echo "  2. Press F5 to launch Extension Development Host"
echo "  3. Open sample.npk to test syntax highlighting"
echo "  4. Verify LSP features (hover, diagnostics, go-to-definition)"
echo ""
echo "To package:"
echo "  npm run package"
