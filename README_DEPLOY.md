# RootEd Deployment Guide 🚀

This guide explains how to deploy the RootEd application using a hybrid stack: **Vercel** for the frontend and **Render** for the backend.

---

## 1. Backend Deployment (Render.com)

1.  **Create a New Web Service:** Connect your GitHub repository.
2.  **Runtime:** Python 3.
3.  **Build Command:** `pip install -r requirements.txt`
4.  **Start Command:** `uvicorn api:app --host 0.0.0.0 --port $PORT`
5.  **Environment Variables:** Add the following:
    *   `GOOGLE_API_KEY`: Your Gemini API key.
    *   `SUPABASE_URL`: Your Supabase project URL.
    *   `SUPABASE_KEY`: Your Supabase anon/service key.
    *   `ALLOWED_ORIGINS`: Set this to your Vercel URL once deployed (e.g., `https://rooted-ai.vercel.app`).
    *   `GOOGLE_MODEL`: `gemini-1.5-flash` (or your preferred model).

---

## 2. Frontend Deployment (Vercel)

1.  **Create a New Project:** Connect your GitHub repository.
2.  **Root Directory:** Set this to `frontend`.
3.  **Framework Preset:** Astro (should be auto-detected).
4.  **Environment Variables:** Add the following:
    *   `PUBLIC_API_URL`: The URL of your Render backend (e.g., `https://rooted-backend.onrender.com/api`). **Crucial: Include the `/api` suffix.**

---

## 3. Local Development

To run locally after these changes:
1.  **Backend:** `python api.py`
2.  **Frontend:** `cd frontend && npm run dev`
    *   By default, the frontend will look for the backend at `http://localhost:8000/api`.

---

## 4. Production Release Workflow

1.  Commit changes to your feature branch.
2.  Merge the feature branch into `main`.
3.  Vercel and Render will automatically pick up the changes and redeploy!
