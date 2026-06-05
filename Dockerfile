# Use Python base image (full image for cryptography build support)
FROM python:3.11

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot source files
COPY main.py .
COPY commands.py .
COPY config_manager.py .
COPY permissions.py .
COPY stats.py .
COPY channel_filter.py .
COPY blacklist.py .
COPY moderation.py .
COPY embeds.py .
COPY easter_eggs.py .
COPY keyvault.py .

# Copy packages
COPY safety/ ./safety/
COPY enrichment/ ./enrichment/

# Copy config defaults
COPY config/ ./config/

# Run the bot
CMD ["python", "main.py"]
