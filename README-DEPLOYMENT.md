# Deployment to Google Cloud Run

This project is configured to deploy to Google Cloud Run using Cloud Build.

## Prerequisites

1. Google Cloud Project with billing enabled
2. Cloud Build API enabled
3. Cloud Run API enabled
4. Container Registry or Artifact Registry API enabled

## Setup

### 1. Set up Cloud Build Trigger (Recommended)

1. Go to Cloud Build > Triggers
2. Create a new trigger
3. Connect to your repository (GitHub, GitLab, or Cloud Source Repositories)
4. Set the configuration file to `cloudbuild.yaml`
5. Add substitution variables:
   - `_SUPABASE_URL`: Your Supabase project URL
   - `_SUPABASE_KEY`: Your Supabase anon key

### 2. Manual Deployment

```bash
# Authenticate
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Build and deploy
gcloud builds submit --config cloudbuild.yaml \
  --substitutions=_SUPABASE_URL="https://xxx.supabase.co",_SUPABASE_KEY="your-key"

# Or set environment variables in Secret Manager (recommended for production)
# Then reference them in cloudbuild.yaml:
# --set-secrets=SUPABASE_URL=supabase-url:latest,SUPABASE_KEY=supabase-key:latest
```

### 3. Using Secret Manager (Recommended for Production)

```bash
# Create secrets
echo -n "https://xxx.supabase.co" | gcloud secrets create supabase-url --data-file=-
echo -n "your-anon-key" | gcloud secrets create supabase-key --data-file=-

# Grant Cloud Run access
gcloud secrets add-iam-policy-binding supabase-url \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding supabase-key \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

Then update `cloudbuild.yaml` to use secrets:
```yaml
- '--set-secrets'
- 'SUPABASE_URL=supabase-url:latest,SUPABASE_KEY=supabase-key:latest'
```

## Configuration

### Memory and CPU
- Default: 2Gi memory, 2 CPU
- Adjust in `cloudbuild.yaml` based on your scraping workload
- For heavy scraping: Increase to 4Gi memory, 4 CPU

### Timeout
- Default: 300 seconds (5 minutes)
- Increase if running batch scrapes that take longer

### Concurrency
- Cloud Run defaults to 80 concurrent requests per instance
- Adjust in Cloud Run console if needed

## Frontend

The frontend is served from the same container:
- Static files: `/static/*`
- Main app: `/app` or `/`
- API endpoints: `/scrape/*`, `/agencies/*`, `/lists/*`

All served from port 8000 in a single container.

## Adding React/Shadcn UI (Optional)

If you want to add React + Shadcn UI:

1. Add a build stage to `Dockerfile`:
```dockerfile
# Stage 1: Build React app
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Stage 2: Python backend
FROM python:3.12-slim
# ... existing setup ...
# Copy built frontend
COPY --from=frontend-builder /app/frontend/dist ./frontend/
```

2. Update `cloudbuild.yaml` to handle npm dependencies if needed
3. The container will still be single-container, just with a build step

## Environment Variables

Set these in Cloud Run or via Cloud Build substitutions:
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase anon/service role key

## Monitoring

View logs:
```bash
gcloud run services logs read agency-scraper --region us-central1
```

View in console:
- Cloud Run > agency-scraper > Logs tab

