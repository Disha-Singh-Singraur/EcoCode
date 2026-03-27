FROM python:3.11-slim

# Create a non-root user (required by Hugging Face Spaces)
RUN useradd -m -u 1000 user

# Set working directory and ownership
WORKDIR /app
RUN chown user:user /app

# Configure environments and paths
ENV PYTHONPATH=/app \
  HOME=/home/user \
  PATH=/home/user/.local/bin:$PATH

# Switch to the non-root user
USER user

# Install dependencies privately to the user
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy entire project
COPY --chown=user:user . .

# Expose port for HF Spaces
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=5s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/')" || exit 1

# Run the server
CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]
