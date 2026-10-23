.DEFAULT_GOAL := help
.NOTPARALLEL:

ROOT_PYTHON ?= .venv/bin/python
ORCHESTRATION_PYTHON ?= orchestration/.venv/bin/python
RUFF ?= $(ROOT_PYTHON) -B -m ruff

ROOT_FAST_TESTS := \
	tests/test_apresentacao.py \
	tests/test_final_evaluation_metrics.py \
	tests/test_temporal_diagnostic.py \
	tests/test_final_evaluation_preflight.py \
	tests/test_channel_partitions.py

.PHONY: help lint format-check test-fast test-graph-fast check test-root test-orchestration test demo-mcp demo-creatives resultado metricas campanha

help: ## Mostra os comandos de manutenção disponíveis
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_-]+:.*## / {printf "%-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

lint: ## Verifica estilo Python sem alterar arquivos
	$(RUFF) check scripts tests orchestration/galaxies_orchestration orchestration/tests

format-check: ## Verifica formatação Python sem alterar arquivos
	$(RUFF) format --check scripts tests orchestration/galaxies_orchestration orchestration/tests

test-fast: ## Executa testes rápidos públicos da raiz
	$(ROOT_PYTHON) -B -m pytest $(ROOT_FAST_TESTS)

test-graph-fast: ## Executa somente o grafo local com Worker simulado
	cd orchestration && $(abspath $(ORCHESTRATION_PYTHON)) -B -m pytest tests/test_graph.py

check: lint format-check test-fast test-graph-fast ## Executa verificações rápidas de qualidade e testes

test-root: ## Executa a suíte completa da raiz
	$(ROOT_PYTHON) -B -m pytest

test-orchestration: ## Executa a suíte completa do grafo (integrações requerem ambos ambientes)
	cd orchestration && GALAXIES_ROOT_PYTHON=$(abspath $(ROOT_PYTHON)) $(abspath $(ORCHESTRATION_PYTHON)) -B -m pytest

test: test-root test-orchestration ## Executa as duas suítes completas em sequência

demo-mcp: ## Executa a demonstração sintética MCP explícita
	$(ROOT_PYTHON) -B -m scripts.apresentacao mcp

demo-creatives: ## Executa a demonstração de criativos sintéticos
	$(ROOT_PYTHON) -B -m scripts.demo_creatives

resultado: ## Exibe o resultado público preservado
	$(ROOT_PYTHON) -B -m scripts.apresentacao resultado

metricas: ## Exibe métricas agregadas preservadas
	$(ROOT_PYTHON) -B -m scripts.apresentacao metricas

campanha: ## Exibe a campanha fictícia com resultados salvos
	$(ROOT_PYTHON) -B -m scripts.apresentacao campanha
