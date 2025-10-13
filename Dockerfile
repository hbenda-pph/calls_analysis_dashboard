# =============================================================================
# DOCKERFILE PARA STREAMLIT EN GOOGLE CLOUD RUN
# =============================================================================

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install gettext for translation compilation
RUN apt-get update && apt-get install -y gettext && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . .

# Compile translations
RUN python compile_translations.py

# Expose port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Run Streamlit
CMD ["streamlit", "run", "dashboard.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
