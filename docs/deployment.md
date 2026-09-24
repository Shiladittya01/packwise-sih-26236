# Website deployment

Deployment has not been performed from this workspace: no Vercel/Render CLI or deployment credentials were available at build time. The repository is configured for the requested website architecture. `.python-version` pins the Render runtime to Python 3.13.3, matching the local model build, and the production requirements pin the serialized-model runtime libraries.

## Render API

1. Create an empty GitHub repository. The local project is initialized on `main` but has no commit or remote. From `D:\Packwise Project`, run `git add -A`, `git commit -m "Build Packwise research prototype"`, `git remote add origin https://github.com/<account>/<repository>.git`, and `git push -u origin main`.
2. In Render, create a Blueprint from that repository and apply `render.yaml`.
3. Set the Blueprint environment variable `PACKWISE_ALLOWED_ORIGINS` to the exact deployed Vercel origin, for example `https://packwise-example.vercel.app` (no trailing slash). Add any production custom domain as another comma-separated origin.
4. Wait for the build, then verify `https://<render-service>.onrender.com/api/health`. The response must have `status: "ok"` and `model_loaded: true`.

The model files and packaging database are included in the repository. No API keys are required by the model service.

## Vercel website

1. Import the same GitHub repository into Vercel.
2. Set the project Root Directory to `frontend`.
3. Set the build command to `npm run build` and output directory to `dist` (also specified by `frontend/vercel.json`).
4. Set the build environment variable `VITE_API_URL` to `https://<render-service>.onrender.com` (no trailing slash), then deploy.
5. Check the website status chip, submit at least one example, and inspect the browser network panel for a successful `POST /api/recommend` response.
6. If the Vercel URL changes, update Render's `PACKWISE_ALLOWED_ORIGINS` and restart the service.

Production path: browser → Vercel static website → HTTPS Render API → validation/preprocessing → saved supervised model → suitability check → JSON response → website.
