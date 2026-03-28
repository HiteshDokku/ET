#!/bin/bash
set -e

# Target directory: /app/media/fonts inside container, backend/media/fonts on host
FONT_DIR="$(dirname "$0")/../media/fonts"
mkdir -p "$FONT_DIR"

echo "Downloading multilingual Noto fonts to $FONT_DIR..."

declare -A fonts=(
    ["NotoSansDevanagari-Bold.ttf"]="https://github.com/notofonts/devanagari/raw/main/fonts/variable/NotoSansDevanagari%5Bwdth%2Cwght%5D.ttf"
    ["NotoSansBengali-Bold.ttf"]="https://github.com/notofonts/bengali/raw/main/fonts/NotoSansBengali/hinted/ttf/NotoSansBengali-Bold.ttf"
    ["NotoSansTelugu-Bold.ttf"]="https://github.com/notofonts/telugu/raw/main/fonts/NotoSansTelugu/hinted/ttf/NotoSansTelugu-Bold.ttf"
    ["NotoSansTamil-Bold.ttf"]="https://github.com/notofonts/tamil/raw/main/fonts/NotoSansTamil/hinted/ttf/NotoSansTamil-Bold.ttf"
    ["NotoSansGujarati-Bold.ttf"]="https://github.com/notofonts/gujarati/raw/main/fonts/NotoSansGujarati/hinted/ttf/NotoSansGujarati-Bold.ttf"
    ["NotoSansKannada-Bold.ttf"]="https://github.com/notofonts/kannada/raw/main/fonts/NotoSansKannada/hinted/ttf/NotoSansKannada-Bold.ttf"
    ["NotoSansMalayalam-Bold.ttf"]="https://github.com/notofonts/malayalam/raw/main/fonts/NotoSansMalayalam/hinted/ttf/NotoSansMalayalam-Bold.ttf"
    ["NotoSansGurmukhi-Bold.ttf"]="https://github.com/notofonts/gurmukhi/raw/main/fonts/NotoSansGurmukhi/hinted/ttf/NotoSansGurmukhi-Bold.ttf"
    ["NotoNastaliqUrdu-Bold.ttf"]="https://github.com/notofonts/arabic/raw/main/fonts/NotoNastaliqUrdu/hinted/ttf/NotoNastaliqUrdu-Bold.ttf"
)

for font_name in "${!fonts[@]}"; do
    url="${fonts[$font_name]}"
    target_file="$FONT_DIR/$font_name"
    if [ ! -f "$target_file" ]; then
        echo "Downloading $font_name..."
        curl -L -s "$url" -o "$target_file"
    else
        echo "$font_name already exists, skipping."
    fi
done

echo "All fonts downloaded successfully."
