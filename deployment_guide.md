# 🚀 Deployment Guide for Wispen AI Tutor

This guide will walk you through deploying your application for **free** using [Render](https://render.com) (Backend) and [Vercel](https://vercel.com) (Frontend).

---

## 🏗️ Architecture
Your app has two parts that need to be deployed separately:
1.  **Backend (Python/Flask)**: Handles AI logic, database, and API. -> Deployed on **Render**.
2.  **Frontend (React/Vite)**: The user interface. -> Deployed on **Vercel**.

---

## ✅ Prerequisites
1.  **GitHub Account**: Your code must be pushed to a GitHub repository.
2.  **Render Account**: Sign up at [render.com](https://render.com).
3.  **Vercel Account**: Sign up at [vercel.com](https://vercel.com).
4.  **Firebase Project**: You already have this configured.

---

## 🛠️ Step 1: Deploy Backend (Render)

1.  **Dashboard**: Go to your Render Dashboard and click **"New +"** -> **"Web Service"**.
2.  **Connect Repo**: Select your GitHub repository.
3.  **Settings**:
    *   **Name**: `wispen-backend` (or similar)
    *   **Region**: Choose closest to you (e.g., Singapore, Frankfurt, Oregon).
    *   **Branch**: `main` (or your working branch).
    *   **Root Directory**: Leave empty (or `.` if asked).
    *   **Runtime**: **Python 3**
    *   **Build Command**: `pip install -r requirements.txt` (I created this file for you!)
    *   **Start Command**: `python backend/app.py`
    *   **Instance Type**: **Free**
4.  **Environment Variables**:
    You MUST add these variables in the "Environment" tab:
    *   `GROQ_API_KEY`: (Your key)
    *   `TAVILY_API_KEY`: (Your key)
    *   `POLLINATIONS_API_KEY`: (Your key if needed)
    *   `OPENAI_API_KEY`: (If used)
    *   **`FIREBASE_CREDENTIALS_BASE64`**: (See below)

    > **🔥 IMPORTANT: Firebase Credentials**
    > Since you cannot easily upload the JSON file to Render, you should encode it:
    > 1. Run this in your local terminal: `base64 -i wispen-f4a94-firebase-adminsdk-fbsvc-f1e0e701d7.json`
    > 2. Copy the long output string.
    > 3. Add it as the value for `FIREBASE_CREDENTIALS_BASE64` on Render.

5.  **Deploy**: Click "Create Web Service". Wait for it to build.
6.  **Get URL**: Once live, copy your backend URL (e.g., `https://wispen-backend.onrender.com`).

---

## 🎨 Step 2: Deploy Frontend (Vercel)

1.  **Dashboard**: Go to Vercel Dashboard -> **"Add New..."** -> **"Project"**.
2.  **Connect Repo**: Select the same repository.
3.  **Configure Project**:
    *   **Framework Preset**: **Vite**
    *   **Root Directory**: Click "Edit" and select `wispen-ai-tutor` (This is crucial!).
4.  **Environment Variables**:
    *   Add `VITE_API_URL` -> Paste your **Render Backend URL** (no trailing slash, e.g., `https://wispen-backend.onrender.com`).
5.  **Deploy**: Click "Deploy".

---

## ⚠️ Step 3: Critical Code Update
Before deployment works fully, your frontend code needs to know the Backend URL. currently, it processes `http://localhost:5000` in many places.

1.  **Update `src/config.ts`**:
    Double check it has:
    ```typescript
    export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';
    ```

2.  **Search & Replace**:
    You need to go through your `src` files (like `VoiceMode.tsx`, `ChatCosmos.tsx`, etc.) and replace `'http://localhost:5000'` with `API_BASE_URL` (imported from config).
    *   *Search*: `http://localhost:5000`
    *   *Replace*: Import `API_BASE_URL` and use it.
    
    *Example:*
    ```typescript
    // OLD
    fetch('http://localhost:5000/sessions/...')
    
    // NEW
    import { API_BASE_URL } from '../../config'; // (Adjust path as needed)
    fetch(`${API_BASE_URL}/sessions/...`)
    ```

Without this step, your deployed website will try to contact `localhost` (your user's computer) and fail!

---

## 🚀 Done!
Once both are active, your Wispen Tutor will be live on the web!
