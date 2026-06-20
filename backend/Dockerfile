FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn uvicorn

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Start command
CMD ["gunicorn", "-c", "gunicorn_config.py", "main:app"]
