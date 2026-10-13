#!/usr/bin/env bash
# Télécharge le binaire Tailwind CSS v4 standalone (pas besoin de Node).
set -euo pipefail
VERSION="${TAILWIND_VERSION:-v4.3.3}"
case "$(uname -s)-$(uname -m)" in
  Linux-x86_64)  ASSET=tailwindcss-linux-x64 ;;
  Linux-aarch64) ASSET=tailwindcss-linux-arm64 ;;
  Darwin-arm64)  ASSET=tailwindcss-macos-arm64 ;;
  Darwin-x86_64) ASSET=tailwindcss-macos-x64 ;;
  *) echo "Plateforme non reconnue, télécharger manuellement depuis GitHub" ; exit 1 ;;
esac
curl -sL "https://github.com/tailwindlabs/tailwindcss/releases/download/${VERSION}/${ASSET}" -o tailwindcss
chmod +x tailwindcss
echo "Tailwind ${VERSION} installé : ./tailwindcss"
