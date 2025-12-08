# Deploying to Streamlit Community Cloud

## Quick Deploy Steps

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Prepare for Streamlit Cloud deployment"
   git push origin main
   ```

2. **Deploy on Streamlit Cloud**
   - Go to https://share.streamlit.io/
   - Sign in with your GitHub account
   - Click "New app"
   - Select:
     - Repository: `cgalgano/NFL-QB-Analysis`
     - Branch: `main`
     - Main file path: `applications/custom_qb_ratings_app.py`
   - Click "Deploy"

3. **Wait for Initial Setup**
   - First deployment takes 5-10 minutes (data initialization)
   - The app automatically fetches data from nflfastR
   - Subsequent visits will be instant

4. **Your App URL**
   - Will be: `https://cgalgano-nfl-qb-analysis.streamlit.app` (or similar)
   - Share this link with anyone!

## What Happens on Deployment

1. Streamlit Cloud installs dependencies from `requirements.txt`
2. App detects missing data and runs `init_cloud_data.py`
3. Script fetches 2010-2025 play-by-play data from nflfastR
4. Generates database and QB ratings
5. App starts serving users

## Updating Data

To refresh with latest NFL data:
- Go to your app's dashboard on Streamlit Cloud
- Click "Reboot app" (clears data, triggers re-initialization)
- Or merge changes to main branch (auto-deploys)

## Important Notes

- Database (1.4GB) is NOT in git - generated on first run
- First-time setup takes 5-10 minutes
- Free tier has resource limits (may be slow during peak times)
- App goes to sleep after inactivity (wakes in 30s)

## Local Development

Run locally:
```bash
uv run streamlit run applications\custom_qb_ratings_app.py
```

Update data locally:
```bash
uv run python update_data.py
```
