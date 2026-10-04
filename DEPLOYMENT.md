
# Deployment Guide - Free Tier

Complete instructions for deploying AquaLens to free hosting tiers.

## Architecture

- **Backend:** Render / Hugging Face Spaces (Docker)
- **Frontend:** Vercel / Cloudflare Pages
- **Database:** PostgreSQL (Render free tier or Supabase)
- **Storage:** Local disk (backend container) or Supabase Storage

---

## Backend Deployment

### Option A: Render (Recommended)

**Why Render:**
- Free tier includes 750 hours/month
- Built-in PostgreSQL free tier
- Auto-deploys from GitHub
- Simple environment variable management
- Spins down after 15 min idle (use warm_server.py before demos)

**Steps:**

1. **Sign up:** https://render.com (GitHub login recommended)

2. **Create PostgreSQL Database:**
   - Dashboard → "New +" → "PostgreSQL"
   - Name: `aqualens-db`
   - Database: `aqualens`
   - User: `aqualens` (or auto-generated)
   - Region: Choose closest to you
   - Plan: **Free**
   - Click "Create Database"
   - **Copy Internal Database URL** (starts with `postgresql://`)

3. **Create Web Service:**
   - Dashboard → "New +" → "Web Service"
   - Connect your GitHub repo
   - Name: `aqualens-api`
   - Region: Same as database
   - Branch: `main`
   - Root Directory: `backend`
   - Runtime: **Docker**
   - Plan: **Free**
   
4. **Configure Environment Variables:**
   Click "Environment" tab and add:
   
   ```
   DATABASE_URL=<paste Internal Database URL from step 2>
   GROQ_API_KEY=<your Groq API key from console.groq.com>
   GROQ_VISION_MODEL=llama-3.2-11b-vision-preview
   AI_PROVIDER_CHAIN=groq,cache,mock
   SLEEP_SECONDS=30
   EXPERT_PIN=<generate strong random value>
   FHIR_SERVER_URL=https://hapi.fhir.org/baseR4
   FHIR_CODESYSTEM_URL=https://example.org/aqualens/CodeSystem/stream-observation
   CORS_ORIGINS=https://your-frontend-url.vercel.app
   STORAGE_BACKEND=local
   UPLOAD_DIR=/app/uploads
   AI_CACHE_DIR=/app/cache/ai
   ```
   
   **Generate EXPERT_PIN:**
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

5. **Deploy:**
   - Click "Create Web Service"
   - Wait 5-10 minutes for first build
   - Note your backend URL: `https://aqualens-api.onrender.com`

6. **Seed Demo Data:**
   - After first deploy, open Shell in Render dashboard
   - Run: `python scripts/seed.py`

**What You Must Do Manually on Render:**
- ✅ Create account
- ✅ Connect GitHub repository
- ✅ Create PostgreSQL database
- ✅ Copy database internal URL
- ✅ Create web service
- ✅ Add all environment variables (11 total)
- ✅ Wait for initial deploy
- ✅ Run seed script via Shell

---

### Option B: Hugging Face Spaces

**Why Hugging Face:**
- Free GPU-accelerated spaces
- Good for AI-heavy apps
- No spin-down (stays warm)
- Community-friendly

**Steps:**

1. **Sign up:** https://huggingface.co

2. **Create Space:**
   - Dashboard → "New Space"
   - Name: `aqualens-api`
   - License: MIT
   - SDK: **Docker**
   - Hardware: CPU basic (free)
   - Visibility: Public

3. **Upload Files:**
   - Upload entire `backend/` directory
   - Upload `backend/Dockerfile` as `Dockerfile` (root level)
   - Upload `scripts/seed.py`

4. **Configure Secrets:**
   Settings → Repository secrets → Add:
   ```
   DATABASE_URL=sqlite:////data/aqualens.db
   GROQ_API_KEY=<your key>
   GROQ_VISION_MODEL=llama-3.2-11b-vision-preview
   AI_PROVIDER_CHAIN=groq,cache,mock
   EXPERT_PIN=<strong random value>
   CORS_ORIGINS=https://your-frontend.vercel.app
   ```

5. **Add Persistent Storage:**
   - Settings → Persistent Storage → Enable
   - Mount path: `/data`
   - This keeps SQLite database across restarts

6. **Deploy:** Space builds automatically

**Limitations:**
- SQLite only (no Postgres on free tier)
- Limited storage (5GB)
- Photos stored in container (lost on rebuild)

**What You Must Do Manually on HF Spaces:**
- ✅ Create account
- ✅ Create new Space (select Docker SDK)
- ✅ Upload backend code files
- ✅ Add secrets (6 required)
- ✅ Enable persistent storage
- ✅ Wait for build

---

## Frontend Deployment

### Option A: Vercel (Recommended)

**Why Vercel:**
- Zero-config for Vite/React
- Auto-deploy from GitHub
- Free SSL
- Global CDN
- 100GB bandwidth/month free

**Steps:**

1. **Sign up:** https://vercel.com (GitHub login)

2. **Import Project:**
   - Dashboard → "Add New..." → "Project"
   - Import your GitHub repo
   - Framework Preset: **Vite** (auto-detected)
   - Root Directory: `frontend`

3. **Configure Build:**
   - Build Command: `npm run build`
   - Output Directory: `dist`
   - Install Command: `npm install`

4. **Environment Variables:**
   ```
   VITE_API_BASE=https://aqualens-api.onrender.com
   ```

5. **Deploy:** Click "Deploy"
   - First deploy takes 2-3 minutes
   - Note your frontend URL: `https://aqualens.vercel.app`

6. **Update Backend CORS:**
   - Go back to Render dashboard
   - Update `CORS_ORIGINS` to include your Vercel URL
   - Format: `https://aqualens.vercel.app,https://aqualens-preview.vercel.app`
   - Render will redeploy automatically

**What You Must Do Manually on Vercel:**
- ✅ Create account
- ✅ Import GitHub repository
- ✅ Set root directory to `frontend`
- ✅ Add VITE_API_BASE environment variable
- ✅ Deploy
- ✅ Copy deployment URL
- ✅ Update backend CORS setting

---

### Option B: Cloudflare Pages

**Why Cloudflare:**
- Unlimited bandwidth
- Faster edge network
- More generous limits

**Steps:**

1. **Sign up:** https://dash.cloudflare.com

2. **Create Project:**
   - Workers & Pages → "Create application" → "Pages"
   - Connect to Git → Select repo
   - Production branch: `main`
   - Build command: `npm run build`
   - Build output directory: `dist`
   - Root directory: `frontend`

3. **Environment Variables:**
   ```
   VITE_API_BASE=https://aqualens-api.onrender.com
   NODE_VERSION=20
   ```

4. **Deploy:** Click "Save and Deploy"

5. **Update Backend CORS:** (same as Vercel)

**What You Must Do Manually on Cloudflare:**
- ✅ Create account
- ✅ Create Pages project
- ✅ Connect GitHub
- ✅ Set build settings (command, output dir, root dir)
- ✅ Add environment variables (2 total)
- ✅ Deploy
- ✅ Update backend CORS

---

## Database: PostgreSQL

### Option A: Render PostgreSQL (with backend)

Already covered in Backend → Render steps.

**Connection String Format:**
```
postgresql://user:password@host:5432/database
```

### Option B: Supabase

**Why Supabase:**
- 500MB database free
- Includes storage buckets
- Built-in auth (future)
- Real-time subscriptions

**Steps:**

1. **Sign up:** https://supabase.com

2. **Create Project:**
   - Dashboard → "New project"
   - Name: `aqualens`
   - Database password: (generate strong one)
   - Region: Choose closest
   - Plan: Free

3. **Get Connection String:**
   - Project Settings → Database
   - Copy "Connection string" (URI mode)
   - Replace `[YOUR-PASSWORD]` with actual password

4. **Use in Backend:**
   - Add to Render/HF environment variables as `DATABASE_URL`

**What You Must Do Manually on Supabase:**
- ✅ Create account
- ✅ Create project
- ✅ Set database password
- ✅ Copy connection string
- ✅ Replace password placeholder
- ✅ Add to backend environment

---

## Environment Variables Reference

### Backend (Required)

| Variable | Example | Where to Get |
|----------|---------|--------------|
| `DATABASE_URL` | `postgresql://user:pass@host:5432/db` | Render DB or Supabase |
| `GROQ_API_KEY` | `gsk_...` | console.groq.com → API Keys |
| `GROQ_VISION_MODEL` | `llama-3.2-11b-vision-preview` | Groq docs (current model) |
| `AI_PROVIDER_CHAIN` | `groq,cache,mock` | Fixed value |
| `EXPERT_PIN` | (random 32+ chars) | `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `CORS_ORIGINS` | `https://your-app.vercel.app` | Your frontend URL from Vercel/CF |

### Backend (Optional)

| Variable | Default | Purpose |
|----------|---------|---------|
| `SLEEP_SECONDS` | `30` | Rate limit between AI calls |
| `FHIR_SERVER_URL` | `https://hapi.fhir.org/baseR4` | FHIR test server |
| `FHIR_CODESYSTEM_URL` | (example.org) | FHIR code system URI |
| `STORAGE_BACKEND` | `local` | `local` or `supabase` |
| `UPLOAD_DIR` | `/app/uploads` | Photo storage path |
| `AI_CACHE_DIR` | `/app/cache/ai` | AI response cache |

### Frontend (Required)

| Variable | Example | Where to Get |
|----------|---------|--------------|
| `VITE_API_BASE` | `https://aqualens-api.onrender.com` | Your backend URL |

---

## Post-Deployment

### 1. Seed Demo Data

**On Render:**
- Dashboard → Your service → "Shell" tab
- Run: `python scripts/seed.py`

**On Hugging Face:**
- Clone space locally
- SSH into space (if enabled)
- Or trigger via API endpoint (custom script)

### 2. Warm Server Before Demo

```bash
python scripts/warm_server.py https://aqualens-api.onrender.com
```

This pings the server until it responds quickly (<2s). Run 5 minutes before a demo presentation.

### 3. Run Smoke Test

```bash
python scripts/smoke_test.py https://aqualens-api.onrender.com your-expert-pin
```

Verifies:
- Health check
- Form schema
- Sites list
- Create observation
- FHIR export
- Map list
- Expert queue

---

## Deployment Checklist

### Initial Setup
- [ ] Backend deployed (Render/HF)
- [ ] Frontend deployed (Vercel/CF)
- [ ] Database created (Render Postgres/Supabase)
- [ ] All environment variables set
- [ ] CORS configured correctly
- [ ] Seed script run successfully
- [ ] Smoke test passes

### Before Every Demo
- [ ] Run warm_server.py (5 min before)
- [ ] Test one observation flow in browser
- [ ] Check expert queue is accessible
- [ ] Verify map shows pins

### Monitoring
- [ ] Check Render/HF logs for errors
- [ ] Monitor database size (Render: 1GB free, Supabase: 500MB free)
- [ ] Check bandwidth usage (Vercel: 100GB/month)

---

## Troubleshooting

### Backend won't start
- Check DATABASE_URL format (no typos)
- Verify all required env vars set
- Check Render logs for Python errors
- Ensure Dockerfile exists in backend/

### Frontend can't reach backend
- Check VITE_API_BASE has https:// and no trailing slash
- Verify CORS_ORIGINS on backend includes frontend URL
- Check browser console for CORS errors
- Test backend health endpoint directly

### Database connection failed
- Verify DATABASE_URL includes password
- Check database is running (Render: not paused)
- Ensure SSL mode correct (Render uses `require`)
- Test connection with psql locally

### Photos not saving
- Check UPLOAD_DIR exists in container
- Verify STORAGE_BACKEND=local
- Ensure container has write permissions
- For Supabase: check SUPABASE_URL, KEY, BUCKET env vars

### Expert PIN not working
- Verify EXPERT_PIN matches in backend and smoke test
- Check for extra spaces or quotes in env var
- Try regenerating: `secrets.token_urlsafe(32)`
- Restart backend service after changing

---

## Cost Estimates (Free Tiers)

| Service | Free Limit | Estimated Usage | Cost if Exceed |
|---------|------------|-----------------|----------------|
| Render Web | 750 hrs/mo | ~720 hrs (always on) | $7/mo for 100 hrs |
| Render DB | 1GB + 90 days | ~200MB | $7/mo for 5GB |
| Vercel | 100GB bandwidth | <1GB | $20/mo for pro |
| Groq API | 7,000 req/day | ~50/day | Free (generous) |

**Total: $0/month** for typical demo usage

---

## Production Checklist (Beyond Free Tier)

When ready to launch for real users:

- [ ] Move to paid database (auto-backups, more storage)
- [ ] Enable Supabase Storage for photos (CDN, secure URLs)
- [ ] Add real authentication (Auth0, Clerk, Supabase Auth)
- [ ] Set up error monitoring (Sentry)
- [ ] Configure analytics (PostHog, Plausible)
- [ ] Enable auto-scaling (Render: paid plans)
- [ ] Add rate limiting (Cloudflare, backend middleware)
- [ ] Custom domain + SSL
- [ ] Regular backups (automated via Render/Supabase)
- [ ] Load testing (k6, Artillery)

---

## GitHub Actions (Optional CI/CD)

Add `.github/workflows/deploy.yml`:

```yaml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: cd backend && pip install -r requirements.txt
      - run: cd backend && pytest

  deploy-backend:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - run: echo "Render auto-deploys from main"

  deploy-frontend:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - run: echo "Vercel auto-deploys from main"
```

---

## Summary: What You Click/Configure Manually

### Render (Backend)
1. Create account → Connect GitHub
2. Create PostgreSQL database → Copy internal URL
3. Create Web Service → Select repo → Set root to `backend` → Choose Docker
4. Add 11 environment variables
5. Deploy → Wait 10 min
6. Open Shell → Run `python scripts/seed.py`

### Vercel (Frontend)
1. Create account → Import repo
2. Set root directory: `frontend`
3. Add 1 environment variable: `VITE_API_BASE`
4. Deploy → Wait 3 min
5. Copy deployment URL → Go back to Render → Update CORS_ORIGINS

### Total Manual Steps: ~20 clicks + 12 env vars to paste

**Time: 30-45 minutes for first deployment**
