FROM python:3.10-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install uv
RUN uv sync --group iiif

COPY manifest_fetcher.py .

CMD ["python", "manifest_fetcher.py"]