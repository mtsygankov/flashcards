# Developer Guide

This guide provides comprehensive instructions for setting up the development environment and contributing to the Chinese Flashcards application.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Local Development](#local-development)
4. [Project Structure](#project-structure)
5. [Development Workflow](#development-workflow)
6. [Database Management](#database-management)
7. [Testing](#testing)
8. [Code Style and Standards](#code-style-and-standards)
9. [Debugging](#debugging)
10. [Contributing Guidelines](#contributing-guidelines)

## Prerequisites

### System Requirements
- **Python 3.13.3** (confirmed required version)
- **Docker** and **Docker Compose** (for containerized development)
- **Git** (for version control)
- **Node.js** (if working on frontend components)

### Accounts and Services
- **Supabase Account**: Create a project at [supabase.com](https://supabase.com)
- **GitHub Account**: For code repository access

### Recommended Tools
- **VS Code** with Python extension
- **Postman** or **Insomnia** for API testing
- **pgAdmin** or **DBeaver** for database management
- **Docker Desktop** for container management

## Environment Setup

### 1. Clone the Repository
```bash
git clone https://github.com/your-repo/chinese-flashcards.git
cd chinese-flashcards
```

### 2. Python Environment Setup
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the project root:

```bash
# Copy example environment file
cp .env.example .env
```

Edit `.env` with your configuration:
```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
SUPABASE_ANON_KEY=your-anon-key

# Authentication
SECRET_KEY=your-development-secret-key-at-least-32-characters
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Application
ENVIRONMENT=development
DEBUG=true
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080

# Optional
LOG_LEVEL=DEBUG
```

### 4. Supabase Setup
In your Supabase dashboard:

1. **Create required tables** by running the SQL from `docs/database-schema.sql`
2. **Configure Row Level Security (RLS)** policies
3. **Set up authentication** settings
4. **Get your API keys** from Settings > API

### 5. Verify Installation
```bash
# Test the application
python main.py

# In another terminal, test the API
curl http://localhost:8000/health
```

## Local Development

### Running the Application

#### Option 1: Direct Python Execution
```bash
# Activate virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Run the application
python main.py
```

#### Option 2: Docker Compose (Recommended)
```bash
# Build and run
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f flashcards
```

### Development URLs
- **API Server**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **OpenAPI Spec**: http://localhost:8000/openapi.json
- **Health Check**: http://localhost:8000/health

### Hot Reload
The application supports hot reload in development mode. Changes to Python files will automatically restart the server.

## Project Structure

```
flashcards/
├── app/
│   ├── api/routes/          # API route handlers
│   │   ├── users.py
│   │   ├── decks.py
│   │   ├── csv.py
│   │   ├── study.py
│   │   └── statistics.py
│   ├── auth/                # Authentication logic
│   │   ├── auth_service.py
│   │   ├── dependencies.py
│   │   └── router.py
│   ├── core/                # Core configuration
│   │   ├── config.py
│   │   └── database.py
│   ├── models/              # Database models
│   │   └── database.py
│   ├── schemas/             # Pydantic schemas
│   │   └── schemas.py
│   ├── services/            # Business logic
│   │   ├── user_service.py
│   │   ├── deck_service.py
│   │   ├── card_service.py
│   │   ├── csv_service.py
│   │   ├── learning_service.py
│   │   ├── study_service.py
│   │   └── statistics_service.py
│   ├── static/              # Static files
│   │   ├── css/
│   │   └── js/
│   ├── templates/           # HTML templates
│   │   ├── base.html
│   │   ├── index.html
│   │   └── dashboard.html
│   └── main.py              # Application entry point
├── tests/                   # Test files
│   └── test_main.py
├── docs/                    # Documentation
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose setup
├── .env.example            # Environment template
├── .gitignore              # Git ignore rules
└── README.md               # Project README
```

### Key Directories

#### `/app/api/routes/`
Contains API route handlers organized by functionality:
- **users.py**: User management endpoints
- **decks.py**: Deck CRUD operations
- **csv.py**: Import/export functionality
- **study.py**: Study session management
- **statistics.py**: Learning analytics

#### `/app/services/`
Business logic layer with service classes:
- **user_service.py**: User operations and statistics
- **deck_service.py**: Deck management logic
- **card_service.py**: Card CRUD and search
- **learning_service.py**: Adaptive learning algorithm
- **study_service.py**: Study session orchestration

#### `/app/models/`
SQLAlchemy ORM models defining database schema and relationships.

#### `/app/schemas/`
Pydantic models for API request/response validation and serialization.

## Development Workflow

### 1. Creating New Features

#### API Endpoint Development
```bash
# 1. Create or modify route handler
echo "# Add new endpoint" >> app/api/routes/decks.py

# 2. Add business logic in service layer
echo "# Add service method" >> app/services/deck_service.py

# 3. Define request/response schemas
echo "# Add Pydantic models" >> app/schemas/schemas.py

# 4. Write tests
echo "# Add test cases" >> tests/test_decks.py

# 5. Test the endpoint
python -m pytest tests/test_decks.py -v
```

#### Database Model Changes
```bash
# 1. Modify models in app/models/database.py
# 2. Update Pydantic schemas in app/schemas/schemas.py  
# 3. Update service layer logic
# 4. Test changes thoroughly
# 5. Document the changes
```

### 2. Code Quality Checks
```bash
# Format code
black app/ tests/

# Check type hints
mypy app/

# Lint code
flake8 app/ tests/

# Check imports
isort app/ tests/

# Run all tests
python -m pytest tests/ -v --cov=app
```

### 3. Database Development

#### Working with Supabase
```python
# Direct database queries for debugging
from app.core.database import get_supabase_client

client = get_supabase_client()

# Test queries
result = client.table("users").select("*").limit(5).execute()
print(result.data)
```

#### Database Migrations
Since we're using Supabase, database schema changes are typically handled through the Supabase dashboard or SQL editor. For local development:

```sql
-- Example migration script
-- Save as migrations/001_add_new_field.sql

ALTER TABLE cards 
ADD COLUMN difficulty_level INTEGER DEFAULT 1;

-- Update existing data if needed
UPDATE cards SET difficulty_level = 1 WHERE difficulty_level IS NULL;
```

## Testing

### Running Tests
```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=app

# Run specific test file
python -m pytest tests/test_main.py -v

# Run with detailed output
python -m pytest -v -s

# Run tests matching pattern
python -m pytest -k "test_user" -v
```

### Writing Tests
```python
# Example test structure
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_create_deck(auth_headers):
    response = client.post(
        "/api/decks/",
        json={"name": "Test Deck", "description": "A test deck"},
        headers=auth_headers
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Test Deck"
```

### Test Fixtures
```python
# conftest.py
@pytest.fixture
def auth_headers():
    # Create test user and return auth headers
    return {"Authorization": "Bearer test-token"}

@pytest.fixture
def sample_deck():
    return {
        "name": "Sample Deck",
        "description": "A sample deck for testing"
    }
```

## Code Style and Standards

### Python Code Style
- **PEP 8**: Follow Python style guidelines
- **Type Hints**: Use type hints throughout the codebase
- **Docstrings**: Document all public functions and classes
- **Black**: Use Black for code formatting
- **isort**: Sort imports consistently

### Example Code Style
```python
from typing import Optional, List
from datetime import datetime
import uuid

class DeckService:
    """Service for managing flashcard decks."""
    
    def __init__(self, supabase: Client) -> None:
        """Initialize the deck service.
        
        Args:
            supabase: The Supabase client instance
        """
        self.supabase = supabase
    
    async def create_deck(
        self, 
        user_id: uuid.UUID, 
        deck_data: DeckCreate
    ) -> Optional[DeckResponse]:
        """Create a new deck for the specified user.
        
        Args:
            user_id: The ID of the user creating the deck
            deck_data: The deck creation data
            
        Returns:
            The created deck data or None if creation failed
        """
        try:
            # Implementation here
            pass
        except Exception as e:
            logger.error(f"Failed to create deck: {e}")
            return None
```

### API Design Standards
- **RESTful URLs**: Use standard REST conventions
- **HTTP Status Codes**: Use appropriate status codes
- **Error Responses**: Consistent error response format
- **Documentation**: Comprehensive OpenAPI documentation

## Debugging

### Development Debugging
```python
# Add debug logging
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug("Debug message")
logger.info("Info message")
logger.error("Error message")
```

### Database Debugging
```python
# Enable SQL query logging
engine = create_async_engine(
    database_url,
    echo=True,  # This enables SQL logging
    echo_pool=True  # This enables connection pool logging
)
```

### API Debugging
```bash
# Test API endpoints with curl
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "password": "test123"}'

# Use httpie for better formatting
http POST localhost:8000/api/auth/login username=test password=test123
```

### Container Debugging
```bash
# Access running container
docker-compose exec flashcards bash

# View container logs
docker-compose logs -f flashcards

# Check container resource usage
docker stats

# Debug network issues
docker-compose exec flashcards ping supabase.com
```

## Contributing Guidelines

### 1. Development Process
1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/new-feature`
3. **Develop** your feature with tests
4. **Test** thoroughly: `python -m pytest`
5. **Format** code: `black app/ tests/`
6. **Commit** with descriptive messages
7. **Push** to your fork: `git push origin feature/new-feature`
8. **Submit** a pull request

### 2. Commit Message Format
```
type(scope): description

body (optional)

footer (optional)
```

Examples:
```
feat(auth): add password reset functionality
fix(deck): resolve deck deletion cascade issue
docs(api): update authentication documentation
test(cards): add comprehensive card service tests
```

### 3. Pull Request Requirements
- [ ] All tests pass
- [ ] Code coverage maintained or improved
- [ ] Documentation updated
- [ ] Type hints added
- [ ] Error handling implemented
- [ ] API documentation updated (if applicable)

### 4. Code Review Process
1. **Automated Checks**: CI/CD pipeline runs tests and linting
2. **Peer Review**: At least one team member reviews the code
3. **Testing**: Manual testing of new features
4. **Documentation**: Review of updated documentation
5. **Merge**: Approved changes are merged to main branch

### 5. Release Process
1. **Version Bump**: Update version numbers
2. **Changelog**: Document changes and new features
3. **Testing**: Comprehensive testing on staging environment
4. **Deployment**: Deploy to production
5. **Monitoring**: Monitor for issues post-deployment

## Additional Resources

### Documentation
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Supabase Documentation](https://supabase.com/docs)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pydantic Documentation](https://pydantic-docs.helpmanual.io/)

### Tools and Extensions
- **VS Code Extensions**:
  - Python
  - Python Docstring Generator
  - REST Client
  - Docker
  - GitLens

### Community
- [FastAPI GitHub Discussions](https://github.com/tiangolo/fastapi/discussions)
- [Supabase Discord](https://discord.supabase.com/)
- [Python Discord](https://discord.gg/python)

---

For questions or issues not covered in this guide, please check the existing documentation or open an issue on GitHub.