# Loud Fits API Documentation

This document provides an overview of the Loud Fits API, including instructions for testing and auditing the codebase, as well as details about the Google Sign-In integration.

## Overview

The Loud Fits API is built using Django and Django REST Framework. It provides endpoints for managing user authentication, product listings, and order processing.

## Installation and Setup

To set up the Loud Fits API locally, follow these steps:

1. Clone the repository:
1. Install and activate a virtual environment:

    ```bash
    python -m venv venv
    source venv/Scripts/activate  # On Windows
    
    # On macOS/Linux
    source venv/bin/activate 
    ```

    Optionally, upgrade pip:

    ```bash
    pip install --upgrade pip
    ```

1. Install the required dependencies:

   ```bash
    pip install -r requirements.txt
   ```

1. Apply database migrations:

    ```bash
    python manage.py migrate
    ```

1. Create a superuser account:

    ```bash
    python manage.py createsuperuser
    ```

1. Start the development server:

    ```bash
    python manage.py runserver
    ```

## Running with Docker

The API can be run fully in Docker or with just the database in Docker and Django running locally.

### Docker Environment Variables

Docker Compose uses the following env vars (all have sensible defaults):

| Variable             | Default          | Description              |
| -------------------- | ---------------- | ------------------------ |
| `DB_CONTAINER_NAME`  | `loud_fits_db`   | Postgres container name  |
| `DB_NAME`            | `loud_fits`      | Database name            |
| `DB_USER`            | `loud_fits_user` | Database user            |
| `DB_PASSWORD`        | `loud_fits_pass` | Database password        |
| `API_CONTAINER_NAME` | `loud_fits_api`  | API container name       |
| `API_APP_PORT`       | `8000`           | Host port for the API    |

### Full Stack (API + Database)

Runs both the API and Postgres in Docker:

```bash
docker compose up -d --build
```

The API will be available at `http://localhost:8000`.

To stop all services:

```bash
docker compose down
```

### Database Only (Local Development)

Runs just Postgres in Docker so you can run Django locally against it:

```bash
docker compose up -d db
```

Then add the following to your `.env`:

```env
DATABASE_ENGINE=django.db.backends.postgresql
DATABASE_NAME=loud_fits
DATABASE_USER=loud_fits_user
DATABASE_PASSWORD=loud_fits_pass
DATABASE_HOST=localhost
DATABASE_PORT=5432
```

And run the server as normal:

```bash
python manage.py migrate
python manage.py runserver
```

To stop the database:

```bash
docker compose down
```

> **Note:** When no `DATABASE_ENGINE` is set, the API falls back to SQLite — no Docker required.

## Add New Dependencies

To add new dependencies to the Loud Fits API project, follow these steps:

1. Activate your virtual environment if it's not already active.
1. Install the new dependency using pip. For example, to install `requests`, run:

    ```bash
    pip install requests
    ```

1. After installing the new dependency, update the `requirements.txt` file to include the new package and its version. You can do this by running:

    ```bash
     pip freeze > requirements.txt
     ```

## Testing

To run the test suite for the Loud Fits API, use the following command:

```bash
python manage.py test
```

This will execute all the tests defined in the project and provide a summary of the results.

To run tests for a specific app, use:

```bash
python manage.py test <app_name>
```

Replace `<app_name>` with the name of the app you want to test.

For more detailed output, you can add the `-v 2` flag:

```bash
python manage.py test -v 2
```

### Test Coverage

To measure test coverage, use the `coverage` package. The project includes a `.coveragerc` config file for simplified commands:

1. Run tests with coverage tracking:

    ```bash
    coverage run manage.py test
    ```

2. View the coverage report in the terminal:

    ```bash
    coverage report
    ```

3. Generate an HTML report for detailed browsing:

    ```bash
    coverage html
    ```

    Open `htmlcov/index.html` in your browser to view the interactive report.

## Auditing

To audit the codebase for security vulnerabilities we use `pip-audit`. To run an audit, use the following command:

```bash
pip-audit
```

To fix any vulnerabilities that are found, you can use the `--fix` option:

```bash
pip-audit --fix
```

This will scan the installed packages in your environment and report any known vulnerabilities.
More information can be found in the [pip-audit documentation](https://pypi.org/project/pip-audit/).

## Google Sign-In Integration

The API includes an endpoint for Google Sign-In, allowing users to authenticate using their Google accounts.
This is implemented in the `GoogleLoginView` class located in `api/views.py`. The view handles the verification of Google ID tokens and the creation or retrieval of user accounts based on the provided Google account information.
