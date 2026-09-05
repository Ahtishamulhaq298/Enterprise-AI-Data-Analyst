FROM python:3.11-slim

WORKDIR /app

# System deps some Python packages need to build (xgboost/lightgbm/chromadb)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# Storage dir must exist before the app starts (config.py also creates it,
# this just guarantees it survives even before that runs)
RUN mkdir -p storage/uploads storage/models storage/reports storage/chroma storage/logs

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]