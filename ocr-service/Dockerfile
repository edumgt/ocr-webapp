FROM jitesoft/tesseract-ocr:latest

USER root
RUN apk add --no-cache python3 py3-pip

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --break-system-packages --no-cache-dir -r /tmp/requirements.txt

WORKDIR /app
COPY app.py .

EXPOSE 8001
CMD ["python3", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
