.PHONY: run server mailer stop

# roda o server e o mailer em paralelo
run:
	@$(MAKE) server &
	@$(MAKE) mailer &
	wait

server:
	@echo "Iniciando servidor..."
	uv run iaserver.py

mailer:
	@echo "Iniciando mailer..."
	uv run mailer.py
stop:
	@pkill -f "python3 iaserver.py" || true
	@pkill -f "python3 mailer.py" || true
