# Atajos de desarrollo local (readme, sección 1.4). El CI usa los comandos directos.
# Las recetas van indentadas con tabulador. .env se lee con -include: sus valores no
# deben llevar $, # ni comillas, porque make los interpreta distinto que el shell.
SHELL := /bin/bash
.DEFAULT_GOAL := help
-include .env
# Sin "export": las recetas usan los valores con $(...) y docker compose lee .env por su
# cuenta. Exportarlos haría que compose prefiriera la copia de make, que en Windows (GNU Make
# de GnuWin32) cambia la codificación de los acentos: "Gerontológico" llegaba a web como
# "GerontolÃ³gico". También evita pasar las contraseñas a cada proceso hijo.

DC    := docker compose
# La contraseña de app_owner la lee el shell de .env al ejecutar la receta, no make: así ni el
# eco de la receta, ni make -n, ni --trace la muestran (solo la expresión sed). Con :=, $$ queda
# como $ y make no la expande. Las comillas protegen un valor con espacios, y tr quita el \r de
# un .env con fin de línea CRLF. make -p sí imprime los valores de .env, porque se incluye
# arriba para el candado de HB-10: límite aceptado (pendiente de HB-10).
OWNER := -e DB_USER=app_owner -e DB_PASSWORD="$$(sed -n 's/^DB_OWNER_PASSWORD=//p' .env | tr -d '\r')"
T ?=

.PHONY: help up down reset actualizar migrate superuser static mock test test-ci e2e lint format check-migrations shell psql openapi

help: ## Lista los comandos disponibles
	@grep -hE '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-17s %s\n", $$1, $$2}'

up: ## Levanta los contenedores
	$(DC) up -d --build
down: ## Detiene los contenedores
	$(DC) down
# Después de down -v, nginx no tiene estáticos: sin collectstatic, el login sale sin estilos
reset: ## Borra la base LOCAL y la recrea con las migraciones (solo desarrollo)
	$(DC) down -v && $(DC) up -d --build && ./scripts/migrate.sh && $(DC) exec web python manage.py collectstatic --noinput
actualizar: ## Pone al día imagen, migraciones y estáticos tras traer cambios
	$(DC) up -d --build && ./scripts/migrate.sh && $(DC) exec web python manage.py collectstatic --noinput
migrate: ## Aplica las migraciones como app_owner
	./scripts/migrate.sh
superuser: ## Crea el usuario Administrador
	$(DC) exec web python manage.py createsuperuser
static: ## Ejecuta collectstatic
	$(DC) exec web python manage.py collectstatic --noinput
mock: ## Carga el dataset mock (solo en una base recién migrada)
	$(DC) cp app/fixtures/mock/. db:/tmp/mock/
	$(DC) exec db sh -c 'psql -U app_owner -d "$$POSTGRES_DB" -v ON_ERROR_STOP=1 -f /tmp/mock/cargar_mock.sql'
test: ## Corre los tests (uno solo: make test T=ruta::nombre_del_test)
	$(DC) exec $(OWNER) web pytest -q $(T)
test-ci: ## Corre lo mismo que el CI en cada PR, con cobertura
	$(DC) exec $(OWNER) web pytest -m "not e2e and not lento" --cov=apps --cov-fail-under=80
e2e: ## Corre las pruebas de extremo a extremo con Playwright
	$(DC) exec $(OWNER) -e DJANGO_ALLOW_ASYNC_UNSAFE=true web pytest -m e2e e2e/ -q
lint: ## Revisa Python (ruff) y plantillas (djLint) sin modificar archivos
	$(DC) exec web ruff check . && $(DC) exec web ruff format --check .
	$(DC) exec web djlint . --check && $(DC) exec web djlint . --lint
# djlint --reformat termina con 1 cuando cambia algún archivo: aquí no es un error
format: ## Formatea Python (ruff) y plantillas (djLint)
	$(DC) exec web ruff format . && $(DC) exec web ruff check --fix .
	$(DC) exec web djlint . --reformat --quiet || true
check-migrations: ## Comprueba que no falten migraciones
	$(DC) exec web python manage.py makemigrations --check --dry-run
shell: ## Abre el shell de Django (como app_user)
	$(DC) exec web python manage.py shell
psql: ## Abre psql como app_owner
	$(DC) exec db psql -U app_owner -d "$(POSTGRES_DB)"
openapi: ## Valida el contrato OpenAPI
	npx @redocly/cli lint docs/api/openapi.yaml
