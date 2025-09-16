# LinkedIn Analytics Backend API

A FastAPI-based backend service for managing LinkedIn post analytics with user authentication, post scheduling, and comprehensive analytics tracking.

## Features

- **User Authentication**: JWT-based authentication with role-based access control (Admin/User)
- **Post Management**: Create, update, delete, and schedule LinkedIn posts
- **Post Scheduling**: Background scheduler for automated post publishing
- **Analytics Tracking**: Comprehensive analytics for post performance including:
  - Reactions (like, praise, empathy, interest, appreciation)
  - Engagement metrics (shares, comments, impressions)
  - Engagement rates and total engagement calculations
- **Admin Dashboard**: Admin-only endpoints for managing all users and posts
- **Data Visualization**: Graph-ready analytics data for frontend charts

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: JWT tokens with OAuth2
- **Background Tasks**: Asyncio-based scheduler
- **API Documentation**: Automatic OpenAPI/Swagger documentation

## Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL database
- Virtual environment (recommended)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd linkedin-analytics-backend
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
# Create .env file in the root directory with:
DATABASE_URL=postgresql://username:password@localhost/dbname
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

5. Initialize the database:
```bash
cd app
python init_db.py
```

6. Start the server:
```bash
cd app
python main.py
```

Or using uvicorn directly:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker Setup (Alternative)

If you prefer using Docker:

1. Build and run with Docker Compose:
```bash
docker-compose up --build
```

This will start both the FastAPI application and PostgreSQL database.

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## API Endpoints

### Authentication (`/api/v1/auth`)
- `POST /register` - Register new user
- `POST /login` - User login
- `GET /me` - Get current user info
- `GET /users` - Get all users (admin only)

### Posts (`/api/v1/posts`)
- `POST /` - Create new post
- `GET /` - Get posts with filtering options
- `GET /{post_id}` - Get specific post
- `PUT /{post_id}` - Update post
- `DELETE /{post_id}` - Delete post
- `POST /{post_id}/schedule` - Schedule post
- `POST /{post_id}/unschedule` - Unschedule post

### Analytics (`/api/v1/analytics`)
- `POST /{post_id}` - Create analytics for post
- `GET /{post_id}` - Get post analytics
- `PUT /{post_id}` - Update post analytics
- `DELETE /{post_id}` - Delete post analytics
- `GET /posts/top` - Get top engaging posts
- `GET /posts/{post_id}/graph` - Get graph data for post

### Admin Endpoints
- `GET /posts/user/{user_id}` - Get user's posts (admin only)
- `GET /posts/admin/scheduler-stats` - Scheduler statistics
- `GET /posts/admin/overdue` - Overdue scheduled posts
- `GET /analytics/admin/all` - All analytics data

## User Roles

- **User**: Can manage their own posts and analytics
- **Admin**: Full access to all posts, analytics, and user management

## Background Scheduler

The application includes a background scheduler that:
- Automatically publishes scheduled posts at the specified time
- Runs every 30 seconds to check for posts ready to publish
- Handles overdue posts and maintains post status consistency

## Post Status Flow

```
DRAFT → SCHEDULED → PUBLISHED
   ↑        ↓
   └────────┘ (unschedule)
```

## Analytics Data Structure

Each post can track:
- **Reactions**: Like, Praise, Empathy, Interest, Appreciation
- **Engagement**: Shares, Comments, Impressions
- **Calculated Metrics**: Total engagement, Engagement rate
- **Time-series Data**: Creation and update timestamps

## Development

### Running in Development Mode

1. **Local Development**:
```bash
cd app
python main.py
```

2. **With Auto-reload**:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

3. **Using Docker**:
```bash
docker-compose up --build
```

### Environment Configuration

The application uses environment variables for configuration. Key variables:

- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: JWT token signing key  
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration time
- `PYTHONPATH`: Should include the app directory

### Database Management

- **Initialize Database**: `python app/init_db.py`
- **Migrations**: Located in `app/migrations/`
- **Models**: Defined in `app/models/`

### Project Structure
```
linkedin-analytics-backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app and startup
│   ├── config.py            # Configuration settings
│   ├── database.py          # Database configuration
│   ├── init_db.py           # Database initialization
│   ├── migrations/          # Database migration files
│   ├── models/              # SQLAlchemy models
│   ├── routers/
│   │   ├── auth.py         # Authentication endpoints
│   │   ├── post.py         # Post management endpoints
│   │   └── analytics.py    # Analytics endpoints
│   ├── schemas/            # Pydantic schemas
│   └── utils/              # Utility functions
│       ├── auth.py        # Authentication utilities
│       └── scheduler_service.py  # Background scheduler
├── venv/                   # Virtual environment
├── .env                    # Environment variables
├── .gitignore             # Git ignore rules
├── .dockerignore          # Docker ignore rules
├── docker-compose.yml     # Docker Compose configuration
├── Dockerfile             # Docker configuration
└── requirements.txt       # Python dependencies
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Health Check

- `GET /` - Basic API information
- `GET /health` - Health status check

## License

[Add your license information here]

## Support

For issues and questions, please create an issue in the repository or contact [your-contact-info].
