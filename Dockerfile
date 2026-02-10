FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Install Julia ────────────────────────────────────────────────────────────
ENV JULIA_VERSION=1.12.4
ENV JULIA_PATH=/opt/julia
ENV PATH="${JULIA_PATH}/bin:${PATH}"
# juliacall needs this to find Julia
ENV PYTHON_JULIACALL_HANDLE_SIGNALS=yes

RUN curl -fsSL "https://julialang-s3.julialang.org/bin/linux/x64/1.12/julia-${JULIA_VERSION}-linux-x86_64.tar.gz" \
    | tar -xz -C /opt \
    && mv /opt/julia-${JULIA_VERSION} ${JULIA_PATH}

# ── Install Python dependencies ──────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy Julia project and precompile ────────────────────────────────────────
COPY julia/ /app/julia/
RUN julia --project=/app/julia -e ' \
    using Pkg; \
    Pkg.instantiate(); \
    Pkg.precompile(); \
    '

# ── Copy application ────────────────────────────────────────────────────────
COPY . .

EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run streamlit (Julia threads default to number of cores)
ENV JULIA_NUM_THREADS=auto
ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
