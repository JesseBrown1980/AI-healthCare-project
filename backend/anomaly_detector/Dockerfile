
# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY backend/anomaly_detector/requirements.txt /app/requirements.txt

# Install python dependencies
# Note: Installing torch cpu-only to keep image size small for this demo. 
# For GPU, use the official pytorch image or different pip index.
RUN pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# Copy the entire backend directory so imports work (e.g. backend.anomaly_detector)
COPY backend /app/backend

# Set PYTHONPATH so python can find the 'backend' package
ENV PYTHONPATH=/app

# Expose the port the app runs on
EXPOSE 8001

# Command to run the application
CMD ["uvicorn", "backend.anomaly_detector.main:app", "--host", "0.0.0.0", "--port", "8001"]
