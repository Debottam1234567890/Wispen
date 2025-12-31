#!/usr/bin/env bash
# exit on error
set -o errexit

echo "🚀 Starting Custom Build Script"

# Build Frontend
echo "📦 Installing Frontend Dependencies..."
cd wispen-ai-tutor
npm install

echo "🛠️  Building Frontend..."
npm run build
cd ..

# Install Backend Dependencies
echo "🐍 Installing Backend Dependencies..."
pip install -r requirements.txt

echo "✅ Build Complete!"
