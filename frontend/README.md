- Node.js 20.9 or newer with npm
From this directory:
# AI Campus Navigator Web

Next.js App Router frontend for the FastAPI campus navigation service.

## Requirements

- Node.js 20.9 or newer with npm
- Python environment and backend packages from the repository root `requirements.txt`
- Tesseract OCR installed on the backend host for room-sign recognition

## Run the backend

From the repository root, activate the Python environment that has the backend dependencies installed, then run:

```powershell
python -m uvicorn api.main:app --reload --port 8000
```

The API initializes `data/campus.db` from the CSV files on startup. It allows the default frontend origins `http://localhost:3000` and `http://127.0.0.1:3000`. Set `CAMPUS_CORS_ORIGINS` to a comma-separated origin list to override them.

## Run the frontend

From this directory:

```powershell
npm install
Copy-Item .env.local.example .env.local
npm run dev
```

Open <http://localhost:3000>. Set `NEXT_PUBLIC_CAMPUS_API_URL` in `.env.local` if the API is not at `http://localhost:8000`.

## Checks

```powershell
npm run typecheck
npm run lint
npm run build
```
