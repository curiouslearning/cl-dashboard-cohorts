# Set the build mode (default to remote)
ARG BUILD_MODE=remote
FROM python:3.12.3-bookworm

ARG BUILD_MODE
ENV BUILD_MODE=${BUILD_MODE}

# Install required tools
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    python3-pip \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Set the workdir to a neutral temp folder first
WORKDIR /tmp/build-context

# Clone OR copy conditionally
RUN if [ "$BUILD_MODE" = "remote" ]; then \
      git clone https://github.com/curiouslearning/cl-dashboard-cohorts.git /cl-dashboard-cohorts ; \
    fi

# Copy only if local
COPY . /tmp/local-copy
RUN if [ "$BUILD_MODE" = "local" ]; then \
      cp -r /tmp/local-copy /cl-dashboard-cohorts ; \
    fi

WORKDIR /cl-dashboard-cohorts

RUN pip3 install --no-cache-dir -r requirements.txt

ENV PORT=8501

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
