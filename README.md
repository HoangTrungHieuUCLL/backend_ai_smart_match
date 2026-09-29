# Local Database Setup

This guide walks you through setting up the local development environment, which runs the frontend, backend, and a local SQL database together using Docker.

## Prerequisites

- [Git](https://git-scm.com/downloads)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

---

## Setup Instructions

### 1. Clone the backend repository

From inside the backend repo, clone it to your machine:

```
git clone https://github.com/HoangTrungHieuUCLL/backend_ai_smart_match
```

### 2. Clone the frontend repository

Clone the frontend repo **into the same parent folder** as the backend:

```
git clone https://github.com/HoangTrungHieuUCLL/frontend_ai_smart_match
```

Your folder structure should look like this:

```
projects/
├── backend_ai_smart_match/
└── frontend_ai_smart_match/
```

If you cloned the frontend under a different folder name, set `FRONTEND_PATH` in the backend's `.env` file, e.g. `FRONTEND_PATH=../my-frontend`.

### 3. Start the Docker containers

Open a terminal (on Mac: **Terminal**; on Windows: **Command Prompt** or **PowerShell**) and navigate to the backend repo folder:

```
cd backend_ai_smart_match
```

Then run:

```
docker compose up
```

This will build and start all three services.

---

## Services

Once running, the following are available locally:

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8000 |
| SQL Database | localhost:5434 |

---

## Stopping the Environment

To stop all running containers, press `Ctrl + C` in the terminal, then run:

```
docker compose down
```
