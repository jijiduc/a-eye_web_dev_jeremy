# OS (template)
FROM python:3.8.13

# directory & requirements
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# copy additional files
COPY . .

# environment variables and port forwarding
ENV FLASK_APP=.app.py
ENV FLASK_ENV=development
EXPOSE 5000

# entry point
CMD ["python", "app.py"]

# ------------------------------
# Docker utilities

# Build docker image
# docker build -t aeye .

# See docker images
# docker image ls or docker images

# Remove docker image
# docker rmi aeye

# Rebuild docker image
# docker build --no-cache -t aeye .

# Run docker container
# docker run -p 5000:5000 aeye

# See docker containers
# docker container ls or docker ps

# Remove docker container
# docker rm <container_id>