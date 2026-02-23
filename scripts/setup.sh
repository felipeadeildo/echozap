#!/usr/bin/env bash
# echozap setup — guia o usuário pelo primeiro boot do projeto
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

info()    { echo -e "${CYAN}==>${NC} $*"; }
success() { echo -e "${GREEN}✓${NC} $*"; }
warn()    { echo -e "${YELLOW}!${NC} $*"; }
die()     { echo -e "${RED}✗ $*${NC}" >&2; exit 1; }

# Requisições HTTP dentro do container whatsapp (sem porta exposta no host)
wa_get()  { docker compose exec -T whatsapp wget -qO- "$1"; }
wa_post() {
  local url="$1" data="$2"
  docker compose exec -T whatsapp wget -qO- \
    --post-data="$data" \
    --header="Content-Type: application/json" \
    "$url"
}
wa_get_h() {
  local url="$1" header="$2"
  docker compose exec -T whatsapp wget -qO- \
    --header="$header" \
    "$url"
}

# ── Pré-requisitos ────────────────────────────────────────────────────────────
command -v docker &>/dev/null || die "'docker' não encontrado. Instale e tente novamente."
docker compose version &>/dev/null || die "'docker compose' plugin não encontrado."

# ── .env ──────────────────────────────────────────────────────────────────────
if [[ ! -f .env ]]; then
  cp .env.example .env
  info "Arquivo .env criado. Preencha as variáveis obrigatórias:"
  echo ""
  echo "  DB_PASS        → senha do PostgreSQL (qualquer string segura)"
  echo "  WEBHOOK_SECRET → secret HMAC compartilhado com o container WhatsApp"
  echo "  DOMAIN         → seu domínio público (ex: brain.example.com)"
  echo ""
  warn "Edite o .env agora e pressione ENTER quando terminar."
  read -r
else
  success ".env já existe, pulando."
fi

# Validar variáveis mínimas
# shellcheck source=/dev/null
source .env
[[ -z "${DB_PASS:-}"        ]] && die "DB_PASS não definido no .env"
[[ -z "${WEBHOOK_SECRET:-}" ]] && die "WEBHOOK_SECRET não definido no .env"

DEVICE_ID="${WHATSAPP_DEVICE_ID:-brain}"

# ── Subir infra base ──────────────────────────────────────────────────────────
info "Iniciando postgres, redis e whatsapp..."
docker compose up -d postgres redis whatsapp
echo ""

# Aguardar WhatsApp API (via wget dentro do container)
info "Aguardando WhatsApp API..."
for i in $(seq 1 30); do
  if wa_get "http://localhost:3000/devices" &>/dev/null; then
    break
  fi
  [[ $i -eq 30 ]] && die "WhatsApp API não respondeu após 30s. Verifique: docker compose logs whatsapp"
  sleep 1
done
success "WhatsApp API disponível."

# ── Device WhatsApp ───────────────────────────────────────────────────────────
STATE=$(wa_get "http://localhost:3000/devices/${DEVICE_ID}" 2>/dev/null \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('results',{}).get('state','not_found'))" 2>/dev/null || echo "not_found")

if [[ "$STATE" == "logged_in" ]]; then
  success "Device '${DEVICE_ID}' já está conectado ao WhatsApp."
else
  # Criar device se não existir
  if [[ "$STATE" == "not_found" ]]; then
    info "Criando device '${DEVICE_ID}'..."
    wa_post "http://localhost:3000/devices" "{\"device_id\": \"${DEVICE_ID}\"}" > /dev/null
  fi

  info "Obtendo QR code para conectar o WhatsApp..."
  LOGIN=$(wa_get_h "http://localhost:3000/app/login" "X-Device-Id: ${DEVICE_ID}")
  QR_TEXT=$(echo "$LOGIN" | python3 -c "import sys,json; r=json.load(sys.stdin)['results']; print(r.get('qr_code') or r.get('qr_link',''))" 2>/dev/null || echo "")
  QR_URL=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin)['results'].get('qr_link',''))" 2>/dev/null || echo "")

  echo ""
  echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${YELLOW}  Escaneie o QR code com o WhatsApp:${NC}"
  echo -e "${YELLOW}  Dispositivos vinculados → Vincular dispositivo${NC}"
  echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""

  # Renderiza QR no terminal se qrencode estiver disponível e tiver o dado bruto
  if command -v qrencode &>/dev/null && [[ -n "$QR_TEXT" ]] && [[ "$QR_TEXT" != http* ]]; then
    qrencode -t UTF8 "$QR_TEXT"
  else
    warn "qrencode não encontrado — exibindo URL da imagem."
    echo ""
    echo "  $QR_URL"
    echo ""
    warn "Para instalar: apt install qrencode  (Ubuntu/Debian)"
  fi

  echo ""
  echo -e "${YELLOW}  O código expira em ~30s. Se expirar: make whatsapp-login${NC}"
  echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""

  info "Aguardando conexão WhatsApp (até 90s)..."
  for i in $(seq 1 18); do
    sleep 5
    STATE=$(wa_get "http://localhost:3000/devices/${DEVICE_ID}" 2>/dev/null \
      | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('results',{}).get('state',''))" 2>/dev/null || echo "")
    if [[ "$STATE" == "logged_in" ]]; then
      break
    fi
    echo -n "."
  done
  echo ""

  if [[ "$STATE" != "logged_in" ]]; then
    die "WhatsApp não conectou. Rode 'make whatsapp-login' para tentar novamente."
  fi
  success "WhatsApp conectado!"
fi

# ── Subir stack completa ──────────────────────────────────────────────────────
info "Subindo stack completa (migrator + brain)..."
docker compose up -d || true

echo ""
success "Setup concluído!"
echo ""
echo "  Health check : curl http://localhost:8000/health"
echo "  Logs         : docker compose logs -f brain"
echo "  Parar tudo   : docker compose down"
echo ""
