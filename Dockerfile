# Multi-stage build for single container deployment
# Stage 1: Build React frontend (Vite 7 requires Node 20+)
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend-react

# Copy package files first for better caching
COPY frontend-react/package*.json ./
RUN npm ci

# Copy all frontend source files explicitly to ensure everything is included
COPY frontend-react/src ./src
COPY frontend-react/public ./public
COPY frontend-react/index.html ./
COPY frontend-react/vite.config.ts ./
COPY frontend-react/tsconfig*.json ./
COPY frontend-react/tailwind.config.js ./
COPY frontend-react/postcss.config.js ./
COPY frontend-react/eslint.config.js ./
COPY frontend-react/components.json ./

# Debug: Verify critical files exist before build
RUN echo "=== Checking file structure ===" && \
    ls -la /app/frontend-react/ | head -20 && \
    echo "=== Checking src directory ===" && \
    ls -la /app/frontend-react/src/ && \
    echo "=== Checking src/lib ===" && \
    ls -la /app/frontend-react/src/lib/ && \
    test -f /app/frontend-react/src/lib/api.ts && echo "✓ api.ts found" || echo "✗ api.ts NOT FOUND" && \
    test -f /app/frontend-react/src/lib/utils.ts && echo "✓ utils.ts found" || echo "✗ utils.ts NOT FOUND"

RUN npm run build

# Stage 2: Python backend with built frontend
FROM python:3.12-slim

# Install system dependencies and Playwright browser dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    fonts-unifont \
    fonts-liberation \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright browsers (required for scraping)
RUN pip install playwright==1.40.0 && \
    playwright install chromium

# Reduce image size by cleaning up apt cache
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY app/ ./app/

# Copy built frontend from builder stage
COPY --from=frontend-builder /app/frontend-react/dist ./frontend/

# Copy other necessary files
COPY counties.csv ./

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
