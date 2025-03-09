# HMLS Backend Server

A FastAPI-based backend server for the HMLS (Home Mobile Luxury Service) project. This server provides user authentication and appointment scheduling functionality.

## Features

- User Authentication
  - Registration with email verification
  - JWT-based authentication
  - Secure password hashing
  - User profile management

- Appointment Scheduling
  - Create, read, update, and delete appointments
  - Timezone-aware scheduling
  - Double-booking prevention
  - Status tracking (pending, confirmed, completed, cancelled)
  - Vehicle information management

## Tech Stack

- FastAPI
- PostgreSQL
- SQLAlchemy
- Pydantic
- JWT Authentication
- Python 3.8+

## Prerequisites

- Python 3.8+
- PostgreSQL
- pip (Python package manager)

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd hmls-server
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a PostgreSQL database:
```bash
createdb hmls
```

5. Create a `.env` file in the root directory:
```env
DATABASE_URL=postgresql://user:password@localhost/hmls
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

6. Run the server:
```bash
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000

## API Documentation

Once the server is running, you can access:
- Interactive API documentation: http://localhost:8000/docs
- Alternative API documentation: http://localhost:8000/redoc

### Available Endpoints

#### Authentication
- POST /auth/register - Register a new user
- POST /auth/token - Login and get access token

#### Appointments
- POST /appointments/ - Create a new appointment
- GET /appointments/ - List all appointments (with filters)
- GET /appointments/{id} - Get specific appointment
- PUT /appointments/{id} - Update appointment status
- DELETE /appointments/{id} - Cancel appointment

## Development

The project follows a modular structure:
```
app/
├── database/     # Database configuration
├── models/       # SQLAlchemy models
├── routers/      # API routes
├── schemas/      # Pydantic models
└── utils/        # Utility functions
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details 