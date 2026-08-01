import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    print(f"🚀 Starting {settings.PROJECT_NAME} at http://{settings.HOST}:{settings.PORT}")
    print(f"📖 Interactive API Docs available at http://localhost:{settings.PORT}/docs")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
