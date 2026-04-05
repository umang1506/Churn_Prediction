# Use Python 3.9 slim
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create necessary directories
RUN mkdir -p uploads scanned_datasets models

# Run the model training script to ensure model exists
RUN python train_model.py

# Expose port
EXPOSE 5000

# CMD to run the app
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
