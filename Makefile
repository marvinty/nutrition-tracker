.PHONY: dev logs stop

dev:
	docker compose up --build

logs:
	docker compose logs -f

stop:
	docker compose down
