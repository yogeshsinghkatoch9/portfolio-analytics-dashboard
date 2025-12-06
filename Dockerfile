FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY backend/requirements.txt .
COPY backend/requirements-langchain.txt .

# Install Python dependencies (both standard and LangChain)
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements-langchain.txt

# Copy backend code
COPY backend/ .

# Copy frontend files
COPY frontend/ ../frontend/

# Expose port
EXPOSE 8000

# Start the app with explicit shell
CMD ["bash", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
