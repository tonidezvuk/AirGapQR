#!/bin/bash
set -e

echo "============================================"
echo " AirGapQR v0.5.0 - Debian 13 Build"
echo "============================================"
echo

echo "[1/4] Provera Python-a..."
python3 --version

echo "[2/4] Pravim build okruzenje..."
if [ ! -d ".buildenv" ]; then
    python3 -m venv .buildenv
fi

echo "[3/4] Instaliram build zavisnosti..."
.buildenv/bin/python -m pip install --upgrade pip

.buildenv/bin/python -m pip install \
    PySide6==6.9.1 \
    opencv-python==4.12.0.88 \
    qrcode==8.2 \
    Pillow==11.3.0 \
    numpy==2.2.6 \
    pyinstaller==6.15.0

echo "[4/4] Gradim AirGapQR..."

rm -rf build dist

.buildenv/bin/pyinstaller \
    --noconfirm \
    --clean \
    --windowed \
    --name AirGapQR \
    --collect-all PySide6 \
    --collect-all cv2 \
    --collect-all qrcode \
    --add-data "AirGapQR_icon.png:." \
    --add-data "novac.png:." \
    app.py

echo
echo "============================================"
echo " BUILD GOTOV"
echo "============================================"
echo
echo "Program:"
echo "dist/AirGapQR/AirGapQR"
echo