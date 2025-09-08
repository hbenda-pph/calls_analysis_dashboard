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
EXPOSE 8080

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8080/_stcore/health

# Run Streamlit
CMD ["streamlit", "run", "dashboard.py", "--server.port=8080", "--server.headless=true"]
