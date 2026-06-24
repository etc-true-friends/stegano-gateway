# Aletheia EC2 Integration Plan

Aletheia is an open-source image steganalysis toolbox. The gateway already calls
an optional Aletheia CLI through `ALETHEIA_CMD`; if the command is missing, the
API continues with the SRNet ensemble only.

Official project:

```text
https://github.com/daniellerch/aletheia
```

## Why Add It

The SRNet ensemble is our project-trained model layer. Aletheia can be used as
an external steganalysis signal for additional coverage and final-presentation
explainability:

- AI ensemble score
- Aletheia external detector result
- CDR reconstruction result
- policy-engine finding for risky attachments

## Current Gateway Hook

`2_API_Gateway/api.py` resolves the command in this order:

```text
ALETHEIA_CMD
aletheia.py auto
aletheia auto
```

Recommended environment value:

```bash
ALETHEIA_CMD="python /opt/aletheia/aletheia.py auto"
```

## EC2 Installation Option A: Host Install

This is useful for quick testing, but less reproducible than baking it into the
Docker image.

```bash
sudo apt-get update
sudo apt-get install -y git octave octave-image octave-signal octave-nan liboctave-dev imagemagick steghide outguess
sudo mkdir -p /opt
sudo git clone https://github.com/daniellerch/aletheia /opt/aletheia
cd /opt/aletheia
python3 -m pip install -r requirements.txt
python3 -m pip install .
```

Then expose it to the API container either by baking it into the image or by
mounting `/opt/aletheia` into the container and setting `ALETHEIA_CMD`.

## EC2 Installation Option B: Docker Image Install

This is preferred for automatic deployment because GitHub Actions rebuilds the
API image and the container can find Aletheia without manual EC2 changes.

The project Dockerfile now supports this path by default:

```dockerfile
ARG INSTALL_ALETHEIA=true
```

It installs Aletheia into:

```text
/opt/aletheia
```

and `docker-compose.yml` passes:

```yaml
ALETHEIA_CMD=python /opt/aletheia/aletheia.py auto
ALETHEIA_TIMEOUT=8
```

If a quick or lightweight API build is needed, disable the detector during
manual builds:

```bash
docker compose build --build-arg INSTALL_ALETHEIA=false api-gateway
```

For the full detector build:

```bash
docker compose build api-gateway
```

## Caution

Aletheia pulls in heavy scientific and Octave dependencies. On the current
t3.small EC2, this can increase image build time, disk usage, and scan latency.
Before enabling it permanently, test:

```bash
docker compose build api-gateway
docker compose up -d api-gateway
docker compose logs api-gateway --tail=100 | grep -i aletheia
```

If latency is too high, keep Aletheia as an optional detector for final testing
or move AI/Aletheia scanning to a separate worker instance.
