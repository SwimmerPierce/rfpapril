# BC Bids Lead Generation Platform

A lead generation platform that scrapes the BC Bids government website for unverified bid results.

## Setup

1.  **Clone the repository.**
2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    playwright install chromium
    ```
4.  **Setup environment variables:**
    ```bash
    cp .env.example .env
    ```
    Update `.env` with your database credentials.

5.  **Run migrations:**
    ```bash
    alembic upgrade head
    ```

## Development

-   Run tests: `pytest`
-   Format code: `black . && isort .`
