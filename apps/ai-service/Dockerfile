FROM python:3.12-slim

# Hugging Face Docker Spaces expect uid 1000. Local Compose still works.
RUN useradd -m -u 1000 user \
  && apt-get update \
  && apt-get install -y --no-install-recommends curl tesseract-ocr tesseract-ocr-eng \
  && TESSDIR="$(dirname "$(find /usr/share -name eng.traineddata | head -1)")" \
  && test -d "$TESSDIR" \
  && ln -sfn "$TESSDIR" /opt/tessdata \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app

RUN pip install --no-cache-dir . \
  && mkdir -p /data/uploads \
  && chown -R user:user /app /data /home/user

USER user
ENV HOME=/home/user
ENV PORT=8000
ENV TESSDATA_PREFIX=/opt/tessdata
ENV ENABLE_OCR=true
EXPOSE 8000

HEALTHCHECK --interval=20s --timeout=5s --start-period=20s --retries=5 \
  CMD curl -fsS http://127.0.0.1:${PORT}/health || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
