# IA SMART QUOTE
O IA SMART QUOTE é módulo do projecto que contém a parte de IA e é reponsável pela análise de emails e anexos.

## Como rodar o projecto?
### Passo 1: Instalação do UV
ATT: Caso já tenha instalado vá directamente para o passo 2.

Para Linux:

``` sh
curl -LsSf https://astral.sh/uv/install.sh | sh

```

Para windows:

``` sh
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Para outras opções pode consultar a [documentação oficial do UV](https://docs.astral.sh/uv/getting-started/installation/)

### Passo 2: Rodar o projecto
O uv automaticamente define a versão do python, activa o ambiente virtual e baixa as dependências

``` python
uv run iaserver.py
```

