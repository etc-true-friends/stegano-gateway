FROM python:3.10-slim-bookworm

ARG INSTALL_ALETHEIA=true

RUN apt-get update && apt-get install -y \
    ca-certificates \
    git \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY 2_API_Gateway/requirements.txt .

RUN pip install --no-cache-dir \
    torch torchvision \
    --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir python-multipart

RUN if [ "$INSTALL_ALETHEIA" = "true" ]; then \
      git clone --depth 1 --filter=blob:none --sparse https://github.com/daniellerch/aletheia /opt/aletheia && \
      cd /opt/aletheia && \
      git sparse-checkout set --no-cone /aletheia.py /aletheialib /requirements.txt /setup.py /setup.cfg /octave-requirements.txt /other-requirements.txt && \
      pip install --no-cache-dir imageio scipy pandas ; \
    fi

ENV PYTHONPATH="/opt/aletheia:${PYTHONPATH}"

COPY 2_API_Gateway/ .
COPY 1_AI_Engine/ ./1_AI_Engine/

EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
