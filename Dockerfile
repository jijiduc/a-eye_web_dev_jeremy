# Base image
FROM python:3.10

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Docker CLI
RUN apt-get update && apt-get install -y docker.io \
    && rm -rf /var/lib/apt/lists/*

# Copy the rest of the application
COPY . .

# Set environment variables
ENV FLASK_DEBUG=1

# Expose port
EXPOSE 5000

# Run the app (development)
# -w 4 means 4 worker processes will be created.
# Each worker can handle requests independently, so this lets your app serve multiple requests in parallel.
# A common formula: workers = 2 x (CPU cores) + 1
# debi has 18 cores and pet3 has 8 => 37 and 17 workers respectively
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]


# ------------------------------
# Docker utilities

# Build docker image
# docker build -t aeyeweb .

# See docker images
# docker image ls or docker images

# Remove docker image
# docker rmi aeyeweb

# Rebuild docker image
# docker build --no-cache -t aeyeweb .

# Run docker container
# docker run -p 5000:5000 aeyeweb

# See docker containers
# docker container ls or docker ps

# Remove docker container
# docker rm <container_id>