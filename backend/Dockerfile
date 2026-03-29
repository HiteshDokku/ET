FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV IMAGEMAGICK_BINARY=/usr/bin/convert

# System dependencies (ffmpeg for video, imagemagick for text rendering, chromium for scraping)
# Full Indic/CJK font coverage: Noto Sans for Devanagari, Telugu, Kannada, Tamil, Bengali, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    imagemagick \
    fonts-liberation \
    fonts-noto-core \
    fonts-noto-ui-core \
    fonts-noto-extra \
    fonts-noto-cjk \
    fonts-indic \
    fontconfig \
    wget \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Fix ImageMagick policy for MoviePy text rendering
RUN sed -i 's/rights="none" pattern="@\*"/rights="read|write" pattern="@*"/' /etc/ImageMagick-6/policy.xml || true
RUN sed -i '/<policy domain="path" rights="none" pattern="@\*"/d' /etc/ImageMagick-6/policy.xml || true

# Download Montserrat font for video overlays
RUN mkdir -p /app/fonts && \
    wget -q -O /app/fonts/Montserrat-Bold.ttf \
    "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Bold.ttf" && \
    wget -q -O /app/fonts/Montserrat-ExtraBold.ttf \
    "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-ExtraBold.ttf" && \
    wget -q -O /app/fonts/Montserrat-SemiBold.ttf \
    "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-SemiBold.ttf" && \
    wget -q -O /app/fonts/Montserrat-Medium.ttf \
    "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Medium.ttf" && \
    wget -q -O /app/fonts/Montserrat-Regular.ttf \
    "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Regular.ttf"

# Symlink system Noto Sans Indic fonts into /app/fonts for easy access
RUN ln -sf /usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf /app/fonts/NotoSansDevanagari-Bold.ttf || true && \
    ln -sf /usr/share/fonts/truetype/noto/NotoSansTelugu-Bold.ttf /app/fonts/NotoSansTelugu-Bold.ttf || true && \
    ln -sf /usr/share/fonts/truetype/noto/NotoSansKannada-Bold.ttf /app/fonts/NotoSansKannada-Bold.ttf || true && \
    ln -sf /usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf /app/fonts/NotoSansDevanagari-Regular.ttf || true && \
    ln -sf /usr/share/fonts/truetype/noto/NotoSansTelugu-Regular.ttf /app/fonts/NotoSansTelugu-Regular.ttf || true && \
    ln -sf /usr/share/fonts/truetype/noto/NotoSansKannada-Regular.ttf /app/fonts/NotoSansKannada-Regular.ttf || true

# Rebuild system font cache + matplotlib font cache so they pick up Noto Sans
RUN fc-cache -f -v 2>/dev/null || true
RUN python -c "import matplotlib.font_manager; matplotlib.font_manager._load_fontmanager(try_read_cache=False)" || true

# Set Chrome env for Selenium
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY media/ ./media/

# Create output directories
RUN mkdir -p /app/output /app/tmp

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
