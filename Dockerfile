FROM python:3.11-slim

# Set up a new user named "user" with user ID 1000
RUN useradd -m -u 1000 user

# Switch to the "user" user
USER user

# Set home to the user's home directory
ENV HOME=/home/user \
  PATH=/home/user/.local/bin:$PATH

# Set the working directory to the user's home directory
WORKDIR $HOME/app

# Copy and install dependencies as the user
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy the current directory contents into the container
COPY --chown=user:user . $HOME/app

# Run the Fast API server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]
