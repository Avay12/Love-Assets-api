# Wish2Love API - FastAPI Backend

A production-ready FastAPI backend designed for the **Wish2Love** application. Built with modular Python architecture, Uvicorn, async SQLAlchemy ORM, SQLite database, and local media file management.

---

## 🌟 Key Features

- **Standard Modular Structure**: Clean separation of `api/`, `core/`, `db/`, `schemas/`, `services/`, and `utils/`.
- **FastAPI & Uvicorn**: High-performance async web server with auto-reload capabilities.
- **Async SQLAlchemy & SQLite**: Embedded zero-config database (`sqlite+aiosqlite`) working out-of-the-box.
- **Local File Uploads**: Photo & media upload handling with automatic unique naming served statically under `/uploads/...`.
- **CORS Configured**: CORS enabled for all origins (`*`) by default, ready for frontend integration on `localhost:5173`, `localhost:3000`, or custom ports.
- **Interactive Swagger Docs**: OpenAPI & Redoc available out of the box at `/docs` and `/redoc`.
- **Complete Test Suite**: Automated pytest test suite covering API endpoints and CRUD workflows.

---

## 📁 Project Structure

```text
loveAssets-api/
├── app/
│   ├── api/
│   │   ├── router.py               # Main API Router
│   │   └── v1/
│   │       ├── router.py          # V1 Router aggregator
│   │       └── endpoints/
│   │           ├── health.py      # Health check endpoint
│   │           ├── letters.py     # Love & Birthday letter CRUD
│   │           ├── templates.py   # Letter reveal template catalog
│   │           ├── music.py       # Track search & featured songs
│   │           ├── media.py       # Photo & asset upload handler
│   │           └── delivery.py    # Delivery scheduling
│   ├── core/
│   │   ├── config.py              # Pydantic Settings & Env loader
│   │   └── database.py            # SQLAlchemy async engine & session
│   ├── db/
│   │   ├── base.py                # Model metadata registration
│   │   └── models/
│   │       ├── letter.py          # Letter database model
│   │       └── template.py        # Template database model
│   ├── schemas/
│   │   ├── letter.py              # Letter Pydantic schemas
│   │   ├── template.py            # Template Pydantic schemas
│   │   ├── music.py               # Music Pydantic schemas
│   │   ├── delivery.py            # Delivery Pydantic schemas
│   │   └── media.py               # Media Pydantic schemas
│   ├── services/
│   │   ├── letter_service.py      # Letter business logic & slug generator
│   │   ├── template_service.py    # Template catalog provider
│   │   ├── music_service.py       # Track search & preview logic
│   │   └── delivery_service.py    # Dispatch logic
│   ├── utils/
│   │   └── storage.py             # File upload helper
│   └── main.py                    # FastAPI app initialization & CORS setup
├── uploads/                       # Local media storage directory
├── tests/
│   ├── conftest.py                # Test fixtures & async client
│   └── test_api.py                # Integration unit tests
├── .env                           # Environment configuration
├── .env.example                   # Example configuration
├── .gitignore
├── requirements.txt               # Dependencies
├── README.md                      # Documentation
└── run.py                         # Uvicorn entry point
```

---

## 🚀 Quick Start

### 1. Set Up Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate on Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Activate on Linux/macOS
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Launch with Uvicorn

```bash
python run.py
```
*Or using uvicorn directly:*
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🌐 API Documentation

Once the server is running, visit:
- **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc UI**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 📌 API Endpoints Overview

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Root welcome message |
| `GET` | `/api/v1/health` | System health check |
| `POST` | `/api/v1/letters/` | Create a new letter |
| `GET` | `/api/v1/letters/` | List all letters (with optional `type` filter) |
| `GET` | `/api/v1/letters/{slug}` | Get letter details by unique slug |
| `PUT` | `/api/v1/letters/{slug}` | Update letter content or metadata |
| `DELETE` | `/api/v1/letters/{slug}` | Delete letter |
| `GET` | `/api/v1/templates/` | List available templates |
| `GET` | `/api/v1/templates/{id}` | Get template details by ID |
| `GET` | `/api/v1/music/featured` | List featured romantic & birthday tracks |
| `GET` | `/api/v1/music/search` | Search tracks by query |
| `POST` | `/api/v1/media/upload` | Upload photo/image asset to `/uploads/` |
| `POST` | `/api/v1/delivery/schedule` | Schedule letter delivery (link, email, sms, call) |

---

## 🧪 Running Tests

Run pytest to execute the full integration test suite:

```bash
pytest
```
