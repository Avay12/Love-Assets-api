import sys

import uvicorn

from app.core.config import settings

if __name__ == "__main__":
    # A Windows console defaults to cp1252, which cannot encode emoji: the
    # previous banner raised UnicodeEncodeError before the server ever started.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print(f"Starting {settings.PROJECT_NAME} at http://{settings.HOST}:{settings.PORT}")
    print(f"Interactive API docs at http://localhost:{settings.PORT}/docs")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
