# 🚀 How to Deploy to Vercel

This guide will help you deploy the **FIRMS LINE Bot** to Vercel for free.

## Prerequisites

1.  **Vercel Account**: Sign up at [vercel.com](https://vercel.com/)
2.  **GitHub Account**: Your code must be on GitHub.

---

## ☁️ Step 1: Push to GitHub

1.  Login to GitHub and create a new repository (e.g., `firms-line-bot`).
2.  Push your code to this repository:
    ```bash
    git init
    git add .
    git commit -m "Initial commit for Vercel deployment"
    git branch -M main
    git remote add origin https://github.com/YOUR_USERNAME/firms-line-bot.git
    git push -u origin main
    ```

---

## 📦 Step 2: Deploy to Vercel

1.  Go to **Vercel Dashboard** > **Add New...** > **Project**
2.  Import your GitHub Repository (`firms-line-bot`).
3.  **Project Name**: You can leave it as default.
4.  **Framework Preset**: Select `Other`.
5.  **Root Directory**: Leave as `./`.

---

## 🔧 Step 3: Environment Variables

In the **Environment Variables** section, add the following secrets (copy from your local `.env`, but DO NOT add `DATABASE_URL` yet):

| Key | Value | Description |
| :--- | :--- | :--- |
| `APP_NAME` | `FIRMS LINE Bot` | |
| `APP_ENV` | `production` | |
| `DEBUG` | `false` | Disable debug on prod |
| `FIRMS_MAP_KEY` | `xxxxxxx` | Your NASA Key |
| `LINE_CHANNEL_ACCESS_TOKEN` | `xxxxxxx` | Your LINE Token |
| `LINE_CHANNEL_SECRET` | `xxxxxxx` | Your LINE Secret |
| `LINE_GROUP_ID` | `xxxxxxx` | Your Group ID (Without spaces!) |
| `TIMEZONE` | `Asia/Bangkok` | |
| `VERCEL` | `1` | **Important**: Disables local scheduler |

---

## 🗄️ Step 4: Setup Vercel Postgres

1.  Click **Deploy** first (it might fail or use SQLite initially, don't worry).
2.  Go to your Project Dashboard > **Storage** tab.
3.  Click **Create Database** > Select **Postgres**.
4.  Accept terms -> Create.
5.  Once created, go to the **.env.local** (or settings) tab in Storage needed? NO.
6.  Just go to **Project Settings** > **Environment Variables**.
7.  Vercel automatically adds `POSTGRES_URL`, `POSTGRES_USER`, etc. to your environment. **You don't need to add DATABASE_URL manually.** The code is smart enough to use these.

> **Note**: Our `app/database.py` is configured to read `DATABASE_URL` or fallback to Vercel's `POSTGRES_URL` structure (postgres://) automatically. Wait, verify you added `DATABASE_URL` linked to `POSTGRES_URL`?
> -> **Simplest way**: In Vercel Env Vars, find `POSTGRES_URL` -> Copy its value -> Create a new Env Var named `DATABASE_URL` and paste it there.

---

## ⏰ Step 5: Setup Cron Job

We already added `vercel.json` with a Cron Job setup:
```json
"crons": [
    {
      "path": "/api/check-now",
      "schedule": "*/10 * * * *"
    }
]
```
This tells Vercel to hit `https://your-app.vercel.app/api/check-now` every 10 minutes.

**Verify**:
1.  After deployment, go to **Settings** > **Cron Jobs**.
2.  You should see the job listed there.

---

## ✅ Step 6: Test

1.  Open your Vercel URL (e.g., `https://firms-line-bot.vercel.app`).
2.  You should see the Dashboard.
3.  Click **Check Now** to test manually.
4.  Wait 10 minutes to see if the Cron Job works (check Line group).

---

## 🐞 Troubleshooting

*   **Logs**: Go to **Deployment** > **Logs** to see errors.
*   **Database**: If errors say "relation not found", it means tables weren't created. The `lifespan` in `main.py` is set to auto-create tables on startup, so it should be fine.
*   **Timezone**: If times are off, ensure `TIMEZONE` env var is set to `Asia/Bangkok`.
