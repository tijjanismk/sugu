#!/usr/bin/env bash
# Télécharge le binaire Tailwind CSS v4 standalone (pas besoin de Node).
set -euo pipefail
VERSION="${TAILWIND_VERSION:-v4.3.3}"
OUT=tailwindcss
case "$(uname -s)-$(uname -m)" in
  MINGW*-x86_64|MSYS*-x86_64|CYGWIN*-x86_64)
    ASSET=tailwindcss-windows-x64.exe ; OUT=tailwindcss.exe ;;
  Linux-x86_64)  ASSET=tailwindcss-linux-x64 ;;
  Linux-aarch64) ASSET=tailwindcss-linux-arm64 ;;
  Darwin-arm64)  ASSET=tailwindcss-macos-arm64 ;;
  Darwin-x86_64) ASSET=tailwindcss-macos-x64 ;;
  *) echo "Plateforme non reconnue, télécharger manuellement depuis GitHub" ; exit 1 ;;
esac
curl -sSfL "https://github.com/tailwindlabs/tailwindcss/releases/download/${VERSION}/${ASSET}" -o "${OUT}"
chmod +x "${OUT}"
echo "Tailwind ${VERSION} installé : ./${OUT}"
