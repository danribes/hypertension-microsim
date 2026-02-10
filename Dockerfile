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

# juliacall signal handling (required for Python↔Julia interop)
ENV PYTHON_JULIACALL_HANDLE_SIGNALS=yes

# Use all available cores for Julia threading
ENV JULIA_NUM_THREADS=auto

RUN curl -fsSL "https://julialang-s3.julialang.org/bin/linux/x64/1.12/julia-${JULIA_VERSION}-linux-x86_64.tar.gz" \
    | tar -xz -C /opt \
    && mv /opt/julia-${JULIA_VERSION} ${JULIA_PATH}

# ── Install Python dependencies ──────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy Julia project and precompile ────────────────────────────────────────
# Copy Julia project first (changes less often → better layer caching)
COPY julia/ /app/julia/
RUN julia --project=/app/julia -e ' \
    using Pkg; \
    Pkg.instantiate(); \
    Pkg.precompile(); \
    '

# ── Precompile juliacall/PythonCall bridge ───────────────────────────────────
# This avoids a multi-minute delay on the first request in the container.
# juliacall discovers Julia on PATH, installs PythonCall.jl, and precompiles.
# We also warm-load HypertensionSim so the module is fully cached.
COPY scripts/warmup_julia.py /tmp/warmup_julia.py
RUN python /tmp/warmup_julia.py && rm /tmp/warmup_julia.py

# ── Copy application ────────────────────────────────────────────────────────
COPY . .

EXPOSE 8501

# Health check — Julia init is precompiled, but Streamlit still needs ~15s
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
