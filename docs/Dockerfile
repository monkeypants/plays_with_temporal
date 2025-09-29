FROM python:3.12-slim

# Install system dependencies for PlantUML
RUN apt-get update && apt-get install -y \
    default-jre-headless \
    graphviz \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Download PlantUML jar
RUN wget -O /usr/local/bin/plantuml.jar \
    https://github.com/plantuml/plantuml/releases/download/v1.2024.6/plantuml-1.2024.6.jar

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies directly to system Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create docs directory structure
RUN mkdir -p /app/docs

# Set the working directory to docs
WORKDIR /app/docs

# Expose port for sphinx-autobuild
EXPOSE 8000

# Command to run sphinx-autobuild with watching
CMD ["sphinx-autobuild", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--watch", "/app/docs/source", \
     "--watch", "/app/docs/img", \
     "--watch", "/app/sample", \
     "--watch", "/app/julee_example", \
     "--watch", "/app/util", \
     "--ignore", "**/__pycache__", \
     "--ignore", "**/*.pyc", \
     "--ignore", "/app/docs/build", \
     "source", \
     "build/html"]