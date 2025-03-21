FROM python:3.10-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install uv
RUN uv sync --only-group=iiif
ENV PATH="/app/.venv/bin:$PATH"

COPY manifest_fetcher.py .

CMD ["python", "manifest_fetcher.py"]