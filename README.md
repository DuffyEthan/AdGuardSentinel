# AdGuard Anomaly Detection

## Prerequisites

- [Docker & Docker Compose](https://docs.docker.com/get-docker/)
- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js & npm](https://nodejs.org/) — required for the React frontend
## Getting Started

### 1. Clone the repository

```bash
git clone <repo-url>
cd sweng26_group20-adguardanomalydetection
```

### 2. Set up environment files

```bash
cp .secrets/.env.example .secrets/.env
```

Edit this file if you need to change the default credentials. The defaults work out of the box for local development.

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

or (depending on how your python is setup)

```bash
pip3 install -r requirements.txt
```

### 3a. Install React frontend dependencies

```bash
cd app/frontend
npm install
```

### 4. Start Backend Services

```bash
docker compose up --build -d
```

This command starts the database, FastAPI backend, and the data orchestrator. The orchestrator will automatically begin seeding the database with sample data, so no manual seeding is required.

Wait a few seconds for the services to initialize.

### 5. Run the app

**Run the React frontend:**
```bash
cd app/frontend
npm run dev
```

The dashboard is available at http://localhost:5173.

## CI Pipeline

The CI pipeline automatically:

1. Starts a fresh TimescaleDB container
2. Installs Python dependencies
3. Runs pytest — **pipeline fails if any test fails**

No manual database setup is needed in CI.

# Running Fast API server

1. Navigate to the project directory
2. Create environment configuration - copied from .secrets\.env.example
3. Copy the env file to the db folder (.\.secrets\.env .\db\.env)
4. Start the database and FastAPI services: "docker-compose down", "docker compose build --no-cache", "docker-compose up fastapi"
5. Verify its working, open http://localhost:8000, should see "{"Hello":"World"}"
6. To stop the services: "docker-compose down"


## Contributors

- Alexander Nevin
- Alex Leung
- Zofia Marta Sekulska
- Thomas Shanahan
