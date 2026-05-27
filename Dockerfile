# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Hugging Face provides PORT 7860 by default
ENV PORT=7860

# Set the working directory in the container
WORKDIR /app

# Install system dependencies (build-essential, db drivers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies globally before switching user
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create a user with UID 1000 (recommended for Hugging Face Spaces)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Copy the rest of the application code and set ownership to 'user'
COPY --chown=user . .

# Expose the port (informative only for Docker)
EXPOSE 7860

# Start the application using python manage.py (as this is a Django project)
# Shell form is used to allow running migrations before starting
CMD python manage.py migrate && python manage.py runserver 0.0.0.0:7860
