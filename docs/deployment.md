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

## Release and post-deployment checks

Production flow: Browser → Vercel frontend → HTTPS Render API → request validation → optional saved Gradient Boosting prediction plus property-based compatibility ranking → JSON estimate and explanation → browser result view. Model class and compatibility recommendation are separate outputs. Suitability is a weighted estimate from available inputs and ordinal material profiles; coverage reports evidence availability. Sustainability is a limited design proxy, not an LCA.

Vercel builds the frontend and Render builds the API from GitHub `main`. This release does not require a Vercel build, root-directory, rewrite or API URL change. It does not require a Render start-command, Python dependency or environment-variable change; the existing `render.yaml` service already runs the backend from the repository root. Pushing frontend, backend, material database and documentation changes to `main` starts the connected provider deployments.

After each release, verify both services:

1. Open the public Vercel site and confirm the updated result labels, data-coverage display, dynamic reasons and material illustrations load.
2. Confirm `GET /api/health` returns HTTP 200 with the model loaded. The recommendation endpoint can fall back to compatibility ranking if model inference fails, but health remains HTTP 503 when the model is unavailable.
3. Send known-food and valid custom/unseen-food requests to `POST /api/recommend`; confirm each returns finite suitability and sustainability scores from 0 to 100, a material recommendation, an explanation and data coverage.
4. Confirm invalid food names and invalid physical inputs still return HTTP 422, and check the Vercel-origin CORS response.

Production verification recorded on 25 September 2026:

| Release commit | Deployment check | Result |
| --- | --- | --- |
| `e66671038dec774e6805c0a29734e9a5fb6f2146` (`feat: ship estimated packaging recommendations`) | Vercel production deployment | Ready at https://packwise-sih-26236.vercel.app |
| `e66671038dec774e6805c0a29734e9a5fb6f2146` | Render `packwise-api-26236` | Deployed and live; `/api/health` returned HTTP 200 with the model loaded |
| `e66671038dec774e6805c0a29734e9a5fb6f2146` | Production API and browser smoke checks | `Milk`: HDPE bottle, 91% estimated suitability, 68% estimated sustainability index, 57% suitability coverage. `Homemade Pickle` with measured properties and omitted respiration/shelf-life fields: metallized flexible laminate, 69% estimated suitability, 38% estimated sustainability index, 44% suitability coverage. The public website displayed the custom-food result, material explanation, missing-data coverage and sustainability limitations. |

If the Vercel production hostname changes, update `PACKWISE_ALLOWED_ORIGINS` in Render and redeploy/restart the API. If the Render hostname changes, update Vercel's `VITE_API_URL` and redeploy the frontend.
