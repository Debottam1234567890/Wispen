#!/bin/bash

# Wispen AI Tutor Setup Script

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Wispen Setup...${NC}"

# 0. Load .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo -e "${GREEN}✅ Loaded environment variables from .env${NC}"
else
    echo -e "${YELLOW}⚠️  .env file not found. Using defaults.${NC}"
    OPENSEARCH_PASSWORD="YourStrongPassword123!"
fi

# 1. Check for Docker
if ! docker info &> /dev/null
then
    echo -e "${RED}❌ Docker daemon is not running.${NC}"
    echo -e "${YELLOW}💡 Action: Please start Docker Desktop on your Mac and wait for it to be ready.${NC}"
    echo -e "${YELLOW}Then, re-run this script.${NC}"
    exit 1
else
    echo -e "${GREEN}✅ Docker is running.${NC}"
    # Start OpenSearch
    echo -e "${BLUE}📦 Starting OpenSearch via Docker...${NC}"
    
    # Check if container already exists
    if [ "$(docker ps -aq -f name=wispen-opensearch)" ]; then
        echo -e "${YELLOW}🔄 Container 'wispen-opensearch' already exists. Starting it...${NC}"
        docker start wispen-opensearch
    else
        docker run -d --name wispen-opensearch -p 9200:9200 -p 9600:9600 \
          -e "discovery.type=single-node" \
          -e "OPENSEARCH_INITIAL_ADMIN_PASSWORD=$OPENSEARCH_PASSWORD" \
          opensearchproject/opensearch:latest
    fi
    echo -e "${GREEN}✅ OpenSearch container is initializing.${NC}"
fi

# 2. Setup Backend
echo -e "${BLUE}🐍 Setting up Backend...${NC}"
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created.${NC}"
fi
source venv/bin/activate
echo -e "${BLUE}📦 Installing Python dependencies...${NC}"
pip install -r requirements.txt
cd ..

# 3. Setup Frontend
echo -e "${BLUE}⚛️ Setting up Frontend...${NC}"
cd wispen-ai-tutor
echo -e "${BLUE}📦 Installing Node dependencies...${NC}"
npm install
cd ..

echo -e "${GREEN}🎉 Setup Complete!${NC}"
echo -e "${BLUE}To start the application, run:${NC}"
echo -e "${GREEN}chmod +x start_wispen.sh && ./start_wispen.sh${NC}"
