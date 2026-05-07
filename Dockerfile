# # FROM python:3.11-slim

# # WORKDIR /app

# # # Install dependencies
# # COPY requirements.txt .
# # RUN pip install --no-cache-dir -r requirements.txt

# # # Copy application code
# # COPY main.py .

# # # Run the application on port 8080 (Cloud Run default)
# # CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]  


# # Use a slim Python image for a smaller footprint
# FROM python:3.11-slim

# # Set environment variables
# ENV PYTHONDONTWRITEBYTECODE 1
# ENV PYTHONUNBUFFERED 1
# ENV PORT 8080

# WORKDIR /app

# # Install system dependencies required for some Python packages
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential \
#     libpq-dev \
#     && rm -rf /var/lib/apt/lists/*

# # Install Python dependencies
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy application files
# # Note: Ensure main.py and index.html are in the same folder as this Dockerfile
# COPY main.py .
# COPY index.html .

# # Create a non-root user for security
# RUN adduser --disabled-password --gecos "" appuser
# USER appuser

# # Run the application
# CMD uvicorn main:app --host 0.0.0.0 --port $PORT


# Use official lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port 8080 (standard for Cloud Run)
EXPOSE 8080

# Use Gunicorn as the production-grade WSGI server
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]


