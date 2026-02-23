#!/usr/bin/env bash
# Obtém e renderiza o QR code do WhatsApp direto no terminal
set -euo pipefail

YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
warn() { echo -e "${YELLOW}!${NC} $*"; }

# Detecta gerenciador de pacotes do OS
install_hint() {
  local pkg_qr="qrencode" pkg_zbar="zbar-tools"
  echo ""
  warn "Para renderizar o QR no terminal, instale:"
  if command -v apt &>/dev/null; then
    echo "    sudo apt install ${pkg_qr} ${pkg_zbar}"
  elif command -v dnf &>/dev/null; then
    echo "    sudo dnf install ${pkg_qr} zbar"
  elif command -v pacman &>/dev/null; then
    echo "    sudo pacman -Syu ${pkg_qr} zbar"
  elif command -v zypper &>/dev/null; then
    echo "    sudo zypper in ${pkg_qr} zbar"
  else
    echo "    qrencode  zbar-tools  (via gerenciador de pacotes do sistema)"
  fi
  echo ""
}

DEVICE_ID=$(grep WHATSAPP_DEVICE_ID .env 2>/dev/null | cut -d= -f2 || echo brain)

LOGIN=$(docker compose exec -T whatsapp wget -qO- \
  --header="X-Device-Id: ${DEVICE_ID}" \
  "http://localhost:3000/app/login")

QR_PATH=$(echo "$LOGIN" | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['results']['qr_link'])" 2>/dev/null || echo "")

if [[ -z "$QR_PATH" ]]; then
  echo "Erro: não foi possível obter o QR code da API."
  exit 1
fi

echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}  Escaneie com o WhatsApp → Dispositivos vinculados → Vincular${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if command -v qrencode &>/dev/null && command -v zbarimg &>/dev/null; then
  # Baixa o PNG de dentro do container e decodifica o QR
  TMPFILE=$(mktemp /tmp/qr-XXXXXX.png)
  trap 'rm -f "$TMPFILE"' EXIT

  docker compose exec -T whatsapp wget -qO- "http://localhost:3000${QR_PATH#*3000}" > "$TMPFILE" 2>/dev/null || \
  docker compose exec -T whatsapp wget -qO- "$QR_PATH" > "$TMPFILE" 2>/dev/null || true

  QR_TEXT=$(zbarimg --quiet --raw "$TMPFILE" 2>/dev/null || echo "")

  if [[ -n "$QR_TEXT" ]]; then
    qrencode -t UTF8 "$QR_TEXT"
  else
    warn "Não foi possível decodificar o PNG."
    echo -e "  ${CYAN}${QR_PATH}${NC}"
    install_hint
  fi
else
  echo -e "  ${CYAN}${QR_PATH}${NC}"
  install_hint
fi

echo -e "${YELLOW}  O código expira em ~30s. Rode novamente se necessário.${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
