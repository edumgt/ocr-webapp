FROM jitesoft/tesseract-ocr:latest

USER root

RUN train-lang kor --fast

RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 \
  && rm -rf /var/lib/apt/lists/*

ENV TESSDATA_PREFIX=/usr/local/share/tessdata

WORKDIR /app
COPY ocr_cli.py .

ENTRYPOINT ["python3", "ocr_cli.py"]
