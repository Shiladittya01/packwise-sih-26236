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

Browser → Vercel website → HTTPS Render API → validation and preprocessing → saved supervised model → separate suitability check → packaging database → JSON response → website.

Live check on 2026-09-25: the website returned HTTP 200 and its deployed JavaScript references the documented Render API URL; the API health endpoint returned HTTP 200 and reported `prototype-1.0` with 295 training rows; the Vercel-origin CORS preflight returned HTTP 200 with the exact allowed origin. The deployed JavaScript does not yet contain the team footer. Direct production requests also confirmed the current defect: `custom:jjjgjghghg` returned HTTP 200 with a material result, and `custom:Dragon Fruit` returned HTTP 200 but was marked `out_of_training_scope`.

The local working tree now contains the property-only `prototype-2.0` model, 331-row dataset, FoodOn name validation and updated website. These changes are not in the deployed services: they remain uncommitted on local `main`. After an approved commit/deployment, the expected health response is 331 rows and `prototype-2.0`; `custom:jjjgjghghg` should return HTTP 422, while `Dragon Fruit` with supported measured properties should return HTTP 200 with `prediction_scope: valid_unseen_commodity`. The local API tests cover these cases; production must be checked again after deployment.

If the Vercel production hostname changes, update `PACKWISE_ALLOWED_ORIGINS` in Render to that exact origin and redeploy/restart the API. If the Render hostname changes, update Vercel's `VITE_API_URL` and redeploy the frontend.
