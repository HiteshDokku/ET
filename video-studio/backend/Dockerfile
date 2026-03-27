FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV IMAGEMAGICK_BINARY=/usr/bin/convert

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    imagemagick \
    fonts-liberation \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Fix ImageMagick policy for MoviePy text rendering
RUN sed -i 's/rights="none" pattern="@\*"/rights="read|write" pattern="@*"/' /etc/ImageMagick-6/policy.xml || true
RUN sed -i '/<policy domain="path" rights="none" pattern="@\*"/d' /etc/ImageMagick-6/policy.xml || true

# Download Montserrat font
RUN mkdir -p /app/fonts && \
    wget -q -O /app/fonts/Montserrat-Bold.ttf \
    "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Bold.ttf" && \
    wget -q -O /app/fonts/Montserrat-ExtraBold.ttf \
    "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-ExtraBold.ttf" && \
    wget -q -O /app/fonts/Montserrat-SemiBold.ttf \
    "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-SemiBold.ttf"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# Create output directory
RUN mkdir -p /app/output /app/tmp

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
