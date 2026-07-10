# Jarvix v2.0 Deployment Guide

## Deploying to Vercel

### Prerequisites
- GitHub account with this repository
- Vercel account (free at vercel.com)

### Step 1: Prepare the Repository
✓ All necessary files have been updated:
- `app.py` - Fixed for relative paths and added error logging
- `requirements.txt` - Updated with all dependencies
- `vercel.json` - Configuration for Vercel
- `.vercelignore` - Files to exclude from deployment

### Step 2: Deploy to Vercel

#### Option A: Using Vercel CLI (Recommended)
```bash
# Install Vercel CLI
npm i -g vercel

# Login to Vercel
vercel login

# Deploy
vercel

# Deploy to production
vercel --prod
```

#### Option B: Using GitHub Integration (Easiest)
1. Go to https://vercel.com/import
2. Select "Import Git Repository"
3. Connect your GitHub account
4. Select `ellisfamilyhart-eng/ProjectKNOLLM`
5. Click "Import"
6. Vercel will automatically detect the Python app
7. Click "Deploy"

### Step 3: Verify Deployment
Once deployed, test these endpoints:
- `https://your-deployment.vercel.app/` - Main interface
- `https://your-deployment.vercel.app/api/health` - Health check

## Troubleshooting

### 500 Internal Server Error

**Check these:**
1. **View Logs in Vercel Dashboard**
   - Go to Vercel dashboard → Select your project
   - Click "Deployments" → Select the failed deployment
   - Click "Runtime logs" to see errors

2. **Common Issues:**
   - Missing dependencies → Check `requirements.txt`
   - Import errors → Check jarvix module exists
   - File paths → Now using relative paths (should be fixed)
   - Memory file → Automatically created in `data/` directory

### Import Errors
If you see `ModuleNotFoundError: No module named 'jarvix'`:
- Ensure `jarvix/` directory is in the repository
- Ensure `jarvix/__init__.py` exists
- Check that all jarvix submodules are present

### Template Not Found
If you see `TemplateNotFound: index.html`:
- Verify `templates/index.html` exists in the repository
- Templates are automatically copied during deployment

## Environment Variables (Optional)

You can set environment variables in Vercel:
1. Go to Project Settings → Environment Variables
2. Add any required variables
3. Redeploy

Example:
```
PYTHONUNBUFFERED=1
STORAGE_CONFIG={'data_file': '/tmp/jarvix_memory.json'}
```

## File Structure
```
ProjectKNOLLM/
├── app.py                 # Flask application (UPDATED)
├── requirements.txt       # Python dependencies (UPDATED)
├── vercel.json           # Vercel config (NEW)
├── .vercelignore         # Vercel ignore file (NEW)
├── jarvix/               # Jarvix module
│   ├── __init__.py
│   ├── config.py
│   ├── agent.py
│   └── ... (other modules)
├── templates/
│   └── index.html
├── data/                 # Created automatically on first run
│   └── jarvix_v2_memory.json
└── Dockerfile           # Still works for Docker deployment
```

## Monitoring

### Check Status
```bash
vercel status
```

### View Logs
```bash
vercel logs --prod
```

### Real-time Logs
```bash
vercel logs --follow
```

## Rollback
If a deployment breaks:
```bash
vercel rollback
```

## Useful Links
- Vercel Dashboard: https://vercel.com/dashboard
- Project Logs: https://vercel.com/dashboard/your-project/logs
- Vercel Python Runtime: https://vercel.com/docs/functions/python

---

**Need Help?**
Check `app.py` for detailed logging. The health check endpoint will show detailed error information if initialization fails.
