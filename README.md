# Projeto 1 — Laboratório de Ciência de Dados (UFAPE 2026.2)

Sistema web em Python para a análise univariada das estatísticas por jogo da
temporada regular da NBA 2025-26. O recorte do Grupo 8 é formado por
**Golden State Warriors** e **Orlando Magic**.

O projeto reúne a base tratada, a homologação da qualidade dos dados, a API
JSON e o painel de consulta. A camada de dados é separada da camada de
apresentação para que as análises seguintes usem a mesma base sem duplicar
regras de leitura.

## Stack

- Python 3.11+ (testado em 3.14)
- Flask para a aplicação web
- pandas e numpy para o tratamento
- pytest para os testes
- Plotly previsto para os gráficos do painel

Flask foi escolhido por ser a sugestão do enunciado e por manter a aplicação
simples de executar e hospedar. A camada de dados (config, loader e cleaning)
é independente do framework: pode ser importada por outro framework ou por um
script de análise sem mudança.

## Estrutura

| Caminho | Conteúdo |
|---|---|
| main.py | aplicação Flask, monta /static e registra o blueprint de qualidade |
| config.py | caminhos, times do grupo, variáveis, renomeação e constantes |
| dashboards/prep/loader.py | leitura, validação das 28 colunas, tipagem, data e colunas derivadas |
| dashboards/prep/cleaning.py | duplicatas, 30 regras de inconsistência, registros afetados, relatório, base limpa e base de modelagem |
| dashboards/api/quality.py | rotas /api/quality/summary, /issues, /regras e /api/health |
| dashboards/analysis/missing.py | ausentes por coluna/time e padrões na base original; testes de Little, Jamshidian-Jalal, Listing-Schlittgen e Fairclough |
| dashboards/analysis/outliers.py | z-score, IQR, Grubbs, ECOD, K-NN, LOF e DBSCAN com interface comum |
| dashboards/api/missing.py, routes_outliers.py | rotas /api/missing/* e /api/outliers* |
| dashboards/static/index.html | página inicial mínima com links para a API |
| tests/ | fixtures sintéticas e testes do loader, das regras e da API |
| data/ | CSV bruto (não alterar), data/clean/base_tratada.csv e data/clean/base_modelagem.csv (gerados) |
| docs/tratamento.md | regras, decisões, justificativas e contrato da API |
| docs/ausentes.md | teoria dos mecanismos e dos testes de MCAR, resultado na base original e validação |
| docs/outliers.md | teoria de cada método, resultados e comparação entre métodos |

## Como rodar

    python -m venv .venv
    source .venv/bin/activate        # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    python main.py

Acesse http://localhost:5000. A porta pode ser trocada com a variável PORT.

Para gerar a base limpa e a base de modelagem sem subir o servidor:

    python -m dashboards.prep.cleaning

A API é read-only: ela não grava data/clean. A gravação acontece no comando
acima ou em uma chamada explícita a executar_tratamento().

## Como testar

    pytest -q

Os testes usam uma base sintética de 2 times e 4 jogos. Os testes de
integração leem o CSV real apenas para conferir que ele não é alterado, que a
base não tem inconsistências e que a base limpa é idempotente.

## API

| Rota | Descrição |
|---|---|
| GET /api/health | status da aplicação e caminho relativo da base |
| GET /api/quality/summary | relatório antes/depois, contagem por regra e decisões |
| GET /api/quality/issues | registros afetados; aceita ?regra= e ?time= |
| GET /api/quality/regras | catálogo de regras e decisão adotada |
| GET /api/missing/summary | ausentes por coluna, por time e padrões de ausência |
| GET /api/missing/tests | testes de MCAR sobre a base original |
| GET /api/outliers/summary | tabela coluna × método, multivariado, normalidade, sensibilidade |
| GET /api/outliers | registros marcados; ?method=, ?team=, ?modo=coluna\|multivariado |

Exemplo:

    curl http://localhost:5000/api/quality/summary

Parâmetros inválidos em /issues retornam 400 com mensagem e lista de valores
válidos. As rotas de leitura usam cache invalidado por mtime/tamanho do CSV e
não gravam a base limpa; os registros removidos por duplicata aparecem em
/issues com a regra que motivou a remoção.

## Base de dados

| Métrica | Valor |
|---|---|
| Linhas (bruto → limpo) | 2.238 → 2.238 |
| Colunas (bruto → limpo) | 28 → 33 (27 originais + 6 derivadas) |
| Colunas da base de modelagem | 26 (sem IDs, acumulados, minutos e data) |
| Times | 30 |
| Jogos distintos | 1.119 |
| Período | 2025-10-21 a 2026-03-29 |
| Valores ausentes | 0 |
| Duplicatas exatas removidas | 0 |
| Duplicatas (time, jogo) removidas | 0 |
| Inconsistências encontradas | 0 |

A base é internamente consistente: não há duplicata, ausente, negativo,
percentual fora de [0, 1] ou violação aritmética. O pipeline cobre 30 regras (incluindo regras de negócio como o limite de 82 jogos e 3PT ⊂ arremessos de quadra),
incluindo as verificações entre as duas linhas do mesmo jogo. As regras são
testadas com mutações sintéticas, para que a ausência de problemas na base
real não seja confundida com ausência de verificação.

## Próximos passos

- Estatística descritiva, assimetria, coeficiente de variação e IQR.
- Painel completo com dicionário, tabelas, boxplot, barras, histogramas e
  síntese interpretativa.
- Integração contínua com testes de contrato e de consistência entre as
  camadas.
