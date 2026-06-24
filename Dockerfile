FROM python:3.10-slim

ARG INSTALL_ALETHEIA=true

RUN apt-get update && apt-get install -y \
    ca-certificates \
    git \
    libmagic1 \
    build-essential \
    imagemagick \
    liboctave-dev \
    octave \
    octave-image \
    octave-nan \
    octave-signal \
    outguess \
    steghide \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY 2_API_Gateway/requirements.txt .

RUN pip install --no-cache-dir \
    torch torchvision \
    --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir python-multipart

RUN if [ "$INSTALL_ALETHEIA" = "true" ]; then \
      git clone --depth 1 https://github.com/daniellerch/aletheia /opt/aletheia && \
      pip install --no-cache-dir -r /opt/aletheia/requirements.txt && \
      pip install --no-cache-dir /opt/aletheia ; \
    fi

COPY 2_API_Gateway/ .
COPY 1_AI_Engine/ ./1_AI_Engine/

EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
