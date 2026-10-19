# Touchline AI — local Docker and Azure Container Apps

## Local test (Docker Desktop required)

1. Copy `.env.example` to `.env` and add your Microsoft Foundry endpoint, deployment name and API key. Never commit `.env`.
2. Run `docker compose up --build`.
3. Open http://localhost:8080 and click **ANALYSE MATCH**.
4. Verify backend health at http://localhost:8000/api/health.
5. Stop with `docker compose down`.

The React UI is unchanged. Nginx serves React and forwards `/api/` to the Python service. Python listens on port 8000.

## Azure deployment outline (after local success)

1. Check `az login` works with the intended subscription. Pluralsight lab accounts may not allow CLI access or persist after the lab ends.
2. Build and publish the backend and frontend images to a container registry accessible to Azure Container Apps (Azure Container Registry, Docker Hub, or another supported registry). You do not need to grant Azure access to GitHub.
3. Deploy backend Container App with target port `8000`, external ingress enabled, and secrets `AZURE_OPENAI_API_KEY` plus environment values `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_DEPLOYMENT`. Keep the API key out of the frontend image and repository.
4. Deploy frontend Container App with target port `80`, external ingress enabled, and environment values `BACKEND_SCHEME=https`, `BACKEND_HOST=<backend-app-FQDN>`, `BACKEND_PORT=443`. Use the host name without `https://`.
5. Test the frontend's `/api/health` and `/api/scan` and the full UI before connecting the Cloudflare custom subdomain.
6. Configure `touchline-ai.dineshsonachalam.com` as a custom domain on the frontend Container App and add the DNS validation records Azure requests in Cloudflare. Do not change the existing domain nameservers.

**Important:** Pluralsight lab resources may expire; confirm terms and persistence before using them for your permanent public portfolio.

## GitHub

After verifying no secrets are included: `git init`, `git add .`, `git commit -m "Initial Touchline AI deployment"`. Create a public repo in your personal GitHub account and push. GitHub is not required for the manual Azure deployment.
