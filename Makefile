.DEFAULT_GOAL = help
help: ## display list of commands
	@sed -rn 's/^([a-zA-Z_-]+):.*?## (.*)$$/"\1" "\2"/p' < $(MAKEFILE_LIST) | xargs printf "make %-20s# %s\n"
.PHONY: help

run: ## run bot
	bot
.PHONY: run

start-env: ## start new python env
	python -m venv .venv
	source .venv/bin/activate
	pip install -r requirements.txt
.PHONY: start-env

setup: requirements.txt ## install requirements
	pip install -r requirements.txt
.PHONY: setup

clean: ## clean project
	rm -rf __pycache__
	rm -rf *.egg-info
	rm -rf .venv
.PHONY: clean

