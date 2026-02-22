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
	QR=$$(echo "$$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin)['results']['qr_link'])"); \
	echo ""; \
	echo "Escaneie o QR code com o WhatsApp (Dispositivos vinculados → Vincular):"; \
	echo "$$QR"; \
	echo ""

# Roda migrations manualmente (sem subir o brain)
migrate:
	docker compose run --rm migrator
