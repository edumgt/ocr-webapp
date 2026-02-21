FROM jitesoft/tesseract-ocr:latest

USER root

# ✅ (jitesoft 권장 방식) 한국어 traineddata 설치
# 기본 이미지에는 eng만 있음 → kor 추가 필요
RUN train-lang kor --fast

# ✅ python/venv 세팅 (Ubuntu/Debian 계열 기준)
RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 python3-pip python3-venv \
  && rm -rf /var/lib/apt/lists/*

ENV VENV_PATH=/opt/venv
RUN python3 -m venv ${VENV_PATH}
ENV PATH="${VENV_PATH}/bin:${PATH}"

# (선택) tessdata 경로를 명시해두면 진단이 쉬움
ENV TESSDATA_PREFIX=/usr/local/share/tessdata

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /app
COPY app.py .

# ✅ 베이스 이미지 ENTRYPOINT 제거 (이미 한 번 겪은 문제)
ENTRYPOINT []

EXPOSE 8001
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]