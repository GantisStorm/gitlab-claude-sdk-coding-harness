# Coding Harness TUI - Dockerfile
# ================================
#
# Builds a container with the TUI and all dependencies including Claude CLI.
#
# Usage:
#   docker build -t coding-harness .
#   docker run -it --env-file .env -v /path/to/projects:/projects coding-harness
#
# Security: Ensure .dockerignore excludes .env, .git, and other sensitive files
# See: .dockerignore in project root

FROM python:3.11-slim

# Image metadata
LABEL org.opencontainers.image.title="Coding Harness"
LABEL org.opencontainers.image.description="Human-in-the-Loop AI Coding Agent with GitLab Integration"
LABEL org.opencontainers.image.source="https://github.com/coding-harness"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (required for Claude CLI)
# Note: Using NodeSource setup script - verified source: https://github.com/nodesource/distributions
ARG NODE_MAJOR=20
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_MAJOR}.x -o nodesource_setup.sh \
    && bash nodesource_setup.sh \
    && rm nodesource_setup.sh \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Pin Claude CLI version for reproducible builds
# Update version periodically to get latest features
ARG CLAUDE_CLI_VERSION=latest
RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CLI_VERSION}

# Set up working directory
WORKDIR /app

# Use bash shell with pipefail for better error handling
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for mounting projects and daemon state
RUN mkdir -p /projects /app/.data

# Create non-root user for security
# Note: Using UID 1000 to match common host user for bind mounts
RUN groupadd --gid 1000 harness \
    && useradd --uid 1000 --gid harness --shell /bin/bash --create-home harness \
    && chown -R harness:harness /app /projects

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV TERM=xterm-256color

# Copy entrypoint script
COPY docker-entrypoint.sh /entrypoint.sh
RUN chmod 755 /entrypoint.sh

# Health check - verify daemon is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD test -S /tmp/coding-harness-daemon.sock || exit 1

# Switch to non-root user
USER harness

# Entry point
ENTRYPOINT ["/entrypoint.sh"]
