import os
from waitress import serve
from app import app

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))

    print(f"NEP-TIME ABIT running on http://127.0.0.1:{port}")

    serve(
        app,
        host=host,
        port=port,
        threads=8
    )