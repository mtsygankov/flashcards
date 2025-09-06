# Chinese-English Flashcard Web Application

A comprehensive web application for learning Chinese vocabulary through interactive flashcards with adaptive learning algorithms and progress tracking.

## Features

- **User Management**: Create and manage multiple user profiles
- **Deck Organization**: Create themed flashcard decks
- **Interactive Learning**: Flip cards and take quizzes
- **Adaptive Algorithm**: Smart spacing based on individual performance
- **Progress Tracking**: Detailed statistics and learning analytics
- **CSV Import/Export**: Bulk card management
- **Responsive Design**: Works on desktop and mobile
- **Self-hosting Ready**: Easy deployment with Docker

## Technology Stack

- **Backend**: FastAPI (Python 3.10+)
- **Database**: Supabase (PostgreSQL)
- **Authentication**: Supabase Auth
- **Frontend**: Server-side rendering with Jinja2 templates
- **Interactivity**: HTMX for dynamic interactions
- **Styling**: Tailwind CSS
- **Fonts**: Noto Sans SC for Chinese characters

## Quick Start

### 1. Prerequisites

- Python 3.10 or higher
- A Supabase account and project
- Git

### 2. Clone the Repository

```bash
git clone <repository-url>
cd flashcards
```

### 3. Environment Setup

Create a `.env` file in the root directory:

```bash
cp .env.example .env
```

Edit `.env` with your Supabase credentials:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key
SUPABASE_ANON_KEY=your_anon_key
SECRET_KEY=your_super_secret_key_here_change_this_in_production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENVIRONMENT=development
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Database Setup

The application will automatically create the necessary tables on first run. Ensure your Supabase project is accessible.

### 6. Run the Application

```bash
python main.py
```

The application will be available at `http://localhost:8000`

## Supabase Configuration

### 1. Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Create a new project
3. Note your project URL and service role key

### 2. Database Schema

The application automatically creates the required tables:

- `users` - User profiles
- `user_statistics` - User learning statistics
- `decks` - Flashcard decks
- `cards` - Individual flashcards
- `user_card_progress` - User-specific card learning progress
- `study_sessions` - Study session tracking
- `card_interactions` - Individual card interactions

### 3. Row Level Security (Optional)

For enhanced security, enable RLS on your Supabase tables:

```sql
-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE decks ENABLE ROW LEVEL SECURITY;
ALTER TABLE cards ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_card_progress ENABLE ROW LEVEL SECURITY;

-- Example policies (customize as needed)
CREATE POLICY "Users can view all users" ON users FOR SELECT USING (true);
CREATE POLICY "Users can update own profile" ON users FOR UPDATE USING (auth.uid()::text = id::text);
CREATE POLICY "Users can manage own decks" ON decks FOR ALL USING (auth.uid()::text = user_id::text);
```

## API Documentation

Once the application is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Main Endpoints

#### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `POST /api/auth/logout` - Logout user
- `GET /api/auth/me` - Get current user info

#### Users
- `GET /api/users/` - List all users
- `GET /api/users/with-stats` - Users with statistics
- `GET /api/users/me` - Current user profile
- `PUT /api/users/me` - Update user profile

#### Decks
- `POST /api/decks/` - Create deck
- `GET /api/decks/` - List user decks
- `GET /api/decks/{deck_id}` - Get deck details
- `PUT /api/decks/{deck_id}` - Update deck
- `DELETE /api/decks/{deck_id}` - Delete deck

#### Cards
- `POST /api/decks/{deck_id}/cards/` - Create card
- `GET /api/decks/{deck_id}/cards/` - List deck cards
- `GET /api/cards/{card_id}` - Get card details
- `PUT /api/cards/{card_id}` - Update card
- `DELETE /api/cards/{card_id}` - Delete card

## Development

### Project Structure

```
flashcards/
├── app/
│   ├── api/
│   │   ├── routes/          # API route handlers
│   │   └── dependencies/    # FastAPI dependencies
│   ├── auth/                # Authentication logic
│   ├── core/                # Core configuration and database
│   ├── models/              # SQLAlchemy database models
│   ├── schemas/             # Pydantic request/response schemas
│   ├── services/            # Business logic services
│   ├── static/              # Static assets (CSS, JS, images)
│   ├── templates/           # Jinja2 HTML templates
│   └── main.py             # FastAPI application factory
├── tests/                  # Test files
├── requirements.txt        # Python dependencies
├── pyproject.toml         # Project configuration
├── .env.example           # Environment variables template
└── README.md              # This file
```

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black app/ tests/
```

## Deployment

### Docker Deployment

1. Build the Docker image:

```bash
docker build -t flashcards-app .
```

2. Run the container:

```bash
docker run -p 8000:8000 --env-file .env flashcards-app
```

### Production Considerations

1. **Environment Variables**: Ensure all production environment variables are properly set
2. **Database**: Use a production-grade PostgreSQL instance
3. **Security**: Generate a strong `SECRET_KEY` and enable HTTPS
4. **Performance**: Consider using a reverse proxy (nginx) for static files
5. **Monitoring**: Set up logging and monitoring for the application

## Usage Guide

### Creating Your First Deck

1. Register an account or log in
2. Click "Create Deck" from the dashboard
3. Give your deck a name and description
4. Add cards with Chinese characters (hanzi), pinyin, and English translation

### Study Sessions

1. Select a deck from your dashboard
2. Choose study direction (Chinese→English or English→Chinese)
3. Use flip mode to review cards or quiz mode for active recall
4. The adaptive algorithm will prioritize difficult cards

### CSV Import/Export

Import cards in bulk using CSV format:
```csv
hanzi,pinyin,english
你好,nǐ hǎo,hello
谢谢,xiè xiè,thank you
再见,zài jiàn,goodbye
```

### Progress Tracking

View your learning progress:
- Overall statistics on the dashboard
- Per-deck progress and accuracy rates
- Individual card mastery levels
- Study time tracking

## Learning Algorithm

The application uses an adaptive spaced repetition algorithm:

- **New cards** (mastery level 0): Appear frequently
- **Learning cards** (level 1): Reduced frequency after correct answers
- **Review cards** (level 2): Scheduled based on performance
- **Mastered cards** (level 3): Minimal appearance unless accuracy drops

Card difficulty scores adjust based on:
- Answer accuracy
- Response time
- Consecutive correct answers
- Historical performance

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify Supabase URL and keys are correct
   - Check network connectivity
   - Ensure Supabase project is not paused

2. **Authentication Issues**
   - Verify `SECRET_KEY` is set and consistent
   - Check token expiration settings
   - Ensure Supabase Auth is enabled

3. **Performance Issues**
   - Check database query performance
   - Monitor memory usage for large decks
   - Consider database indexing for frequently queried fields

### Logs

The application logs important events and errors. In development mode, logs appear in the console. For production, configure proper log aggregation.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with FastAPI and Supabase
- Chinese font support by Google Fonts (Noto Sans SC)
- Interactive features powered by HTMX
- Styling with Tailwind CSS