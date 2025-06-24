#!/bin/bash
# Script to run API Developer Portal locally on Mac

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}=== API Developer Portal - Local Development ===${NC}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running${NC}"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: docker-compose is not installed${NC}"
    echo "Install it with: brew install docker-compose"
    exit 1
fi

# Function to show menu
show_menu() {
    echo -e "${BLUE}
What would you like to do?
1) Start all services (with frontend)
2) Start backend services only
3) Stop all services
4) View logs (all services)
5) View frontend logs
6) View backend logs
7) Reset everything (careful!)
8) Check service status
9) Exit
${NC}"
}

# Function to create env files
create_env_files() {
    if [ ! -f .env ]; then
        echo -e "${YELLOW}Creating .env file...${NC}"
        cat > .env << EOF
POSTGRES_DB=devportal
POSTGRES_USER=devportal_user
POSTGRES_PASSWORD=local_dev_password_123
DATABASE_URL=postgresql+asyncpg://devportal_user:local_dev_password_123@postgres:5432/devportal
REDIS_URL=redis://redis:6379/0
SECRET_KEY=local-secret-key-$(date +%s)
JWT_SECRET_KEY=local-jwt-key-$(date +%s)
EOF
    fi

    if [ ! -f .env.dev ]; then
        echo -e "${YELLOW}Creating .env.dev file...${NC}"
        cp .env .env.dev
    fi
}

# Change to project root
cd "$(dirname "$0")/.."
echo -e "${YELLOW}Working directory: $(pwd)${NC}"

# Create env files if they don't exist
create_env_files

# Main loop
while true; do
    show_menu
    read -p "Enter your choice: " choice

    case $choice in
        1)
            echo -e "${GREEN}Starting all services...${NC}"
            if [ -f "docker-compose.prod.yml" ]; then
                docker-compose -f docker-compose.prod.yml up -d
            else
                docker-compose --profile frontend up -d
            fi
            echo -e "${GREEN}Services starting! Frontend build may take 3-5 minutes.${NC}"
            echo "Frontend: http://localhost:3000"
            echo "Backend: http://localhost:8000"
            echo "API Docs: http://localhost:8000/docs"
            ;;
        2)
            echo -e "${GREEN}Starting backend services only...${NC}"
            docker-compose up -d postgres redis backend
            echo -e "${GREEN}Backend services started!${NC}"
            echo "Backend: http://localhost:8000"
            echo "API Docs: http://localhost:8000/docs"
            ;;
        3)
            echo -e "${YELLOW}Stopping all services...${NC}"
            docker-compose down
            echo -e "${GREEN}All services stopped!${NC}"
            ;;
        4)
            echo -e "${BLUE}Showing logs (Ctrl+C to exit)...${NC}"
            docker-compose logs -f
            ;;
        5)
            echo -e "${BLUE}Showing frontend logs (Ctrl+C to exit)...${NC}"
            docker-compose logs -f frontend
            ;;
        6)
            echo -e "${BLUE}Showing backend logs (Ctrl+C to exit)...${NC}"
            docker-compose logs -f backend
            ;;
        7)
            echo -e "${RED}This will delete all containers, volumes, and data!${NC}"
            read -p "Are you sure? (yes/no): " confirm
            if [ "$confirm" = "yes" ]; then
                echo -e "${YELLOW}Resetting everything...${NC}"
                docker-compose down -v
                rm -f .env .env.dev
                echo -e "${GREEN}Reset complete!${NC}"
            else
                echo -e "${YELLOW}Reset cancelled${NC}"
            fi
            ;;
        8)
            echo -e "${BLUE}Service Status:${NC}"
            docker-compose ps
            ;;
        9)
            echo -e "${GREEN}Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice. Please try again.${NC}"
            ;;
    esac

    echo -e "\n${YELLOW}Press Enter to continue...${NC}"
    read
done