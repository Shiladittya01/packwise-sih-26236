# Website deployment

Deployment is live from the private GitHub repository [`Shiladittya01/packwise-sih-26236`](https://github.com/Shiladittya01/packwise-sih-26236), branch `main`. The initial production deployment used commit `4c8aa73`; provider integrations deploy subsequent updates from `main`.

## Live endpoints

- Website: https://packwise-sih-26236.vercel.app
- Render API base: https://packwise-api-26236.onrender.com
- Health check: https://packwise-api-26236.onrender.com/api/health
- Recommendation: `POST https://packwise-api-26236.onrender.com/api/recommend`

## Render API service

- Service: `packwise-api-26236` (free instance, 0.1 CPU / 512 MB RAM)
- Repository branch: `main`; root directory is the repository root.
- Runtime: Python 3.13.3 from `.python-version`.
- Build: `pip install -r backend/requirements.txt`
- Start: `uvicorn backend.packwise_api:app --host 0.0.0.0 --port $PORT`
- Health check path: `/api/health`
- Environment: `PACKWISE_ALLOWED_ORIGINS=https://packwise-sih-26236.vercel.app`

The model, preprocessing pipeline, packaging database and FoodOn name-reference snapshot are included in the repository. The model API requires no API keys. Render free instances sleep after inactivity and can take about 50 seconds or more to wake.

## Vercel website project

- Project: `packwise-sih-26236` on the Hobby plan.
- Repository: the same GitHub repo and `main` branch.
- Root directory: `frontend` (Vite).
- Build and output: `npm run build`, `dist`, configured in `frontend/vercel.json`.
- Environment: `VITE_API_URL=https://packwise-api-26236.onrender.com` for Production and Preview.

## Production flow and verification

Browser → Vercel website → HTTPS Render API → validation and preprocessing → saved property-only supervised model → separate suitability check → packaging database → JSON response → website.

Commit `1ef6ada` was pushed to the existing `main` branch on 2026-09-25, and both providers deployed it. Live verification confirmed:

- The Vercel site returned HTTP 200; its JavaScript points to the Render API and contains `Built by 4Bit-Coders`.
- The Render `/api/health` endpoint returned HTTP 200 with model `prototype-2.0`, 331 training rows, eight features, `commodity_name_used_by_model: false`, and the 12,655-term FoodOn reference.
- The Vercel-origin CORS preflight returned HTTP 200 with the exact allowed origin.
- Direct production requests for Apple, Banana and Dragon Fruit returned HTTP 200. Dragon Fruit was marked `valid_unseen_commodity` and returned a preliminary model candidate.
- `custom:jjjgjghghg` and `abcxyz123` returned HTTP 422 without a material result. Invalid pH and humidity also returned HTTP 422.
- A valid Dragon Fruit profile outside the training feature ranges returned HTTP 200 with extrapolation warnings.

If the Vercel production hostname changes, update `PACKWISE_ALLOWED_ORIGINS` in Render to that exact origin and redeploy/restart the API. If the Render hostname changes, update Vercel's `VITE_API_URL` and redeploy the frontend.
