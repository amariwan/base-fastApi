FROM ghcr.io/uvorg/uv:latest

WORKDIR /app
COPY . .

RUN chown -R containeruser /app

USER containeruser

RUN uv sync

# Expose port
EXPOSE 8000

# call binary explizit
CMD ["/usr/local/bin/uv", "run",  "--no-sync", "-m" , "uvicorn", "app.asgi:app", "--host", "0.0.0.0", "--port", "8000"]
