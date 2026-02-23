#!/usr/bin/env bash
# Obtém e renderiza o QR code do WhatsApp direto no terminal
set -euo pipefail

YELLOW='\033[1;33m'; NC='\033[0m'
warn() { echo -e "${YELLOW}!${NC} $*"; }

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

# Instala ferramentas se necessário (silencioso)
if ! command -v qrencode &>/dev/null || ! command -v zbarimg &>/dev/null; then
  warn "Instalando qrencode e zbar-tools para renderizar QR no terminal..."
  apt-get install -y -qq qrencode zbar-tools 2>/dev/null || \
    { warn "Sem permissão para instalar. Tente: sudo apt install qrencode zbar-tools"; }
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
    warn "Não foi possível decodificar o PNG. URL da imagem:"
    echo "  $QR_PATH"
  fi
else
  warn "Ferramentas não disponíveis. URL da imagem:"
  echo "  $QR_PATH"
fi

echo ""
echo -e "${YELLOW}  O código expira em ~30s. Rode novamente se necessário.${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""