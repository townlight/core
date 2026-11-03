# syntax=docker/dockerfile:1.7

FROM --platform=linux/amd64 python:3.13-slim-bookworm@sha256:bb73517d48bd32016e15eade0c009b2724ec3a025a9975b5cd9b251d0dcadb33

ARG TOWNLIGHT_CORE_REPO_URL=https://github.com/townlight/core.git
ARG TOWNLIGHT_CORE_COMMIT
ARG COSIGN_VERSION=v3.0.6
ARG COSIGN_SHA256=c956e5dfcac53d52bcf058360d579472f0c1d2d9b69f55209e256fe7783f4c74

LABEL org.opencontainers.image.title="Townlight Core CO-6 cleanroom harness"
LABEL org.opencontainers.image.description="Pinned cleanroom image for Townlight Core release and provenance verification."

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN test -n "${TOWNLIGHT_CORE_COMMIT}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        build-essential \
        ca-certificates \
        curl \
        git \
        gzip \
        openssl \
        tar \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL \
        "https://github.com/sigstore/cosign/releases/download/${COSIGN_VERSION}/cosign-linux-amd64" \
        -o /usr/local/bin/cosign \
    && echo "${COSIGN_SHA256}  /usr/local/bin/cosign" | sha256sum -c - \
    && chmod 0755 /usr/local/bin/cosign \
    && cosign version

RUN git clone --filter=blob:none "${TOWNLIGHT_CORE_REPO_URL}" /workspace/townlight_core \
    && cd /workspace/townlight_core \
    && git fetch --depth 1 origin "${TOWNLIGHT_CORE_COMMIT}" \
    && git checkout --detach "${TOWNLIGHT_CORE_COMMIT}" \
    && test "$(git rev-parse HEAD)" = "${TOWNLIGHT_CORE_COMMIT}"

WORKDIR /workspace/townlight_core

RUN python -m pip install --upgrade pip \
    && python -m pip install -e .[dev]

COPY scripts/cleanroom/townlight_core-cleanroom-runner.sh /usr/local/bin/townlight_core-cleanroom-runner
RUN chmod 0755 /usr/local/bin/townlight_core-cleanroom-runner

ENV TOWNLIGHT_CORE_REPO_URL="${TOWNLIGHT_CORE_REPO_URL}"
ENV TOWNLIGHT_CORE_COMMIT="${TOWNLIGHT_CORE_COMMIT}"
ENV CLEANROOM_BASE_IMAGE="python:3.13-slim-bookworm"
ENV CLEANROOM_BASE_IMAGE_DIGEST="sha256:bb73517d48bd32016e15eade0c009b2724ec3a025a9975b5cd9b251d0dcadb33"
ENV CLEANROOM_COSIGN_VERSION="${COSIGN_VERSION}"
ENV CLEANROOM_COSIGN_SHA256="${COSIGN_SHA256}"

ENTRYPOINT ["townlight_core-cleanroom-runner"]
CMD ["online"]
