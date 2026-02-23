.PHONY: setup up down logs build shell whatsapp-login migrate

# Primeiro boot — cria .env, conecta WhatsApp, sobe tudo
setup:
	@bash scripts/setup.sh

# Sobe a stack completa em background
up:
	docker compose up -d

# Para e remove os containers (preserva volumes)
down:
	docker compose down

# Build das imagens
build:
	docker compose build

# Logs do brain em tempo real
logs:
	docker compose logs -f brain

# Shell dentro do container brain (prod)
shell:
	docker compose exec brain bash

# Renova o QR code do WhatsApp (exec dentro do container, sem porta exposta)
whatsapp-login:
	@DEVICE_ID=$$(grep WHATSAPP_DEVICE_ID .env 2>/dev/null | cut -d= -f2 || echo brain); \
	LOGIN=$$(docker compose exec -T whatsapp wget -qO- --header="X-Device-Id: $$DEVICE_ID" "http://localhost:3000/app/login"); \
	QR_TEXT=$$(echo "$$LOGIN" | python3 -c "import sys,json; r=json.load(sys.stdin)['results']; print(r.get('qr_code') or r.get('qr_link',''))" 2>/dev/null || echo ""); \
	QR_URL=$$(echo "$$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin)['results'].get('qr_link',''))" 2>/dev/null || echo ""); \
	echo ""; \
	echo "Escaneie com o WhatsApp → Dispositivos vinculados → Vincular dispositivo"; \
	echo ""; \
	if command -v qrencode >/dev/null 2>&1 && [ -n "$$QR_TEXT" ] && [ "$${QR_TEXT#http}" = "$$QR_TEXT" ]; then \
	  qrencode -t UTF8 "$$QR_TEXT"; \
	else \
	  echo "$$QR_URL"; \
	  echo "(instale qrencode para ver o QR direto no terminal: apt install qrencode)"; \
	fi; \
	echo ""

# Roda migrations manualmente (sem subir o brain)
migrate:
	docker compose run --rm migrator
