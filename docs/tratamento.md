# Tratamento e homologação dos dados

## 1. Objetivo e escopo

Carregar o CSV bruto, validar o contrato das 28 colunas, converter tipos,
renomear para nomes intuitivos, criar as colunas derivadas, remover duplicatas,
verificar regras de inconsistência, registrar cada ocorrência com a decisão
adotada e gravar uma versão limpa em data/clean.

O resultado é usado pelas análises de outliers e de estatística descritiva.
A análise de ausentes parte da base bruta.

## 2. Base e contrato

| Item | Valor |
|---|---|
| Linhas | 2.238 |
| Colunas brutas | 28 |
| Colunas tratadas | 33 (27 originais + 6 derivadas) |
| Times | 30 |
| Jogos distintos | 1.119 (2 linhas por jogo, uma por time) |
| Período | 2025-10-21 a 2026-03-29 |
| Unidade | um time em um jogo (box score coletivo) |

O contrato é validado em dashboards/prep/loader.py. Coluna faltando ou coluna
extra interrompe a execução com ErroBaseDados; tipo inválido também. A leitura
não escreve no arquivo original.

### Renomeação

As 28 colunas originais viram nomes em português (Team_ID → id_time,
GAME_DATE → data_jogo, PTS → pontos etc.). O dicionário completo, com tipo,
significado e situação, está em loader.tabela_dicionario() e pode ser exposto
pela interface.

### Data

GAME_DATE chega como texto ISO. É convertida para datetime64 com formato
AAAA-MM-DD e origina mes (1–12) e dia_semana (0 = segunda). A base é ordenada
por time, data e jogo.

### Categóricas e binárias

- WL já chega como 1/0; mantida como vitoria (binária), sem conversão forçada.
- MATCHUP é texto composto. Foi decomposto em:
  - em_casa: 1 para "vs." (mandante), 0 para "@" (visitante);
  - adversario: sigla do adversário;
  - sigla: sigla do próprio time.
- MIN (240/265/290) virou prorrogacao (1 quando MIN > 240). O valor bruto de
  MIN continua na base para auditoria, mas é excluído da modelagem.

### Colunas excluídas da modelagem

| Coluna | Justificativa |
|---|---|
| id_time, id_jogo | identificadores; não generalizam para jogos futuros |
| vitorias_acum, derrotas_acum, pct_vitorias_acum | acumulados da temporada até o jogo; vazamento de informação |
| minutos | quase constante; a prorrogação já está em prorrogacao |
| data_jogo | serve para ordenar; como preditor permite vazamento temporal |

A função loader.colunas_modelagem() aplica a exclusão. A base limpa mantém
essas colunas para auditoria; as análises escolhem o recorte.

## 3. Regras de qualidade

A detecção está em dashboards/prep/cleaning.py. Cada violação gera uma linha
com id_jogo, id_time, time, data_jogo, regra, detalhe e decisao.

### Duplicatas (única transformação destrutiva)

| Regra | Decisão | Justificativa |
|---|---|---|
| duplicata_exata | remover | linha idêntica em todas as colunas não acrescenta informação |
| duplicata_time_jogo | remover | o mesmo time não pode ter duas linhas para o mesmo jogo |
| duplicata_time_data | sinalizar | dois jogos do mesmo time na mesma data podem ser erro de data ou de calendário; exige conferência |
| duplicata_confronto_data | sinalizar | mesmo par de times e data com Game_IDs diferentes sugere ID trocado; não remover sem saber qual é o correto |

As linhas removidas por duplicata_exata ou duplicata_time_jogo continuam
aparecendo em /api/quality/issues, com a regra que motivou a remoção. Assim,
duplicatas_removidas e por_regra contam a mesma história e o registro removido
não desaparece do relatório.

### Integridade aritmética

| Regra | Decisão |
|---|---|
| pontos_formula (PTS = 2*FGM + FG3M + FTM) | sinalizar |
| rebotes_formula (REB = OREB + DREB) | sinalizar |
| pct_arremessos, pct_tres_pontos, pct_lances_livres | sinalizar (tolerância de 0,001 para arredondamento) |
| convertidos_maior_tentados | sinalizar |
| minutos_invalidos (fora de 240, 265, 290, 315, 340) | sinalizar |
| pct_vitorias_acumulado (W_PCT = W/(W+L)) | sinalizar |
| acumulado_ordem (W+L = número do jogo do time) | sinalizar |
| acumulado_incremento (W/L crescem conforme os resultados) | sinalizar |

### Regras de negócio (limites do domínio)

Os limites vêm das regras do basquete/NBA, não de cortes estatísticos — valores
extremos mas possíveis ficam para a análise de outliers.

| Regra | Restrição | Decisão |
|---|---|---|
| contagem_nao_inteira | contagens (pontos, rebotes, arremessos, faltas, W, L, MIN…) só admitem inteiros | sinalizar |
| tres_maior_arremessos | a cesta de 3 é um arremesso de quadra: FG3M ≤ FGM e FG3A ≤ FGA | sinalizar |
| limite_temporada | a temporada regular tem 82 jogos por time: W+L ≤ 82 e no máximo 82 linhas por time | sinalizar |

**Zeros não são sinalizados.** Zero é informação legítima no contexto: há
35 linhas com W, L ou W_PCT = 0 (início da temporada), 33 jogos com BLK = 0
e 1 jogo com STL = 0. Um teste garante que zero não gera issue.

### Domínio e identidade

| Regra | Decisão |
|---|---|
| valor_ausente | sinalizar; a #1 não imputa |
| valor_negativo | sinalizar |
| fora_dominio (percentual fora de [0, 1]; binária fora de 0/1) | sinalizar |
| time_desconhecido | sinalizar |
| time_id_divergente | sinalizar |
| abreviacao_time | sinalizar |
| adversario_divergente | sinalizar |
| local_inconsistente | sinalizar |
| jogo_incompleto | sinalizar |
| jogo_sem_vencedor | sinalizar |
| vencedor_pontos | sinalizar |
| data_divergente, minutos_divergente | sinalizar |

### Regras entre as duas linhas do mesmo jogo

A base tem uma linha por time em cada jogo. Por isso as verificações mais
fortes são entre pares:

- cada Game_ID precisa ter exatamente 2 linhas;
- exatamente um WL = 1 e um WL = 0;
- o vencedor tem PTS maior que o perdedor;
- as duas linhas têm a mesma data e a mesma duração;
- exatamente um mandante e um visitante;
- a sigla do adversário de uma linha é a sigla da outra;
- a data não se repete para o mesmo time;
- o mesmo confronto não aparece duas vezes na mesma data com IDs diferentes.

Essas regras detectariam, por exemplo, um jogo em que o placar foi invertido
ou uma linha copiada do jogo errado — algo que as regras coluna a coluna não
pegam.

## 4. Resultado na base real

| Métrica | Antes | Depois |
|---|---|---|
| Linhas | 2.238 | 2.238 |
| Colunas | 28 | 33 |
| Ausentes | 0 | 0 |
| Duplicatas exatas | 0 | 0 |
| Duplicatas (time, jogo) | 0 | 0 |
| Linhas com flag | 0 | 0 |
| Issues | 0 | 0 |

Nenhuma das 30 regras foi violada. O resultado é consistente com a inspeção
manual: a base é internamente coerente, os IDs oficiais batem, os acumulados
crescem um jogo por vez e as duas linhas de cada jogo concordam.

Isso significa que o valor da #1 está no contrato e na homologação, não em
corrigir registros. Os testes provam que o pipeline detecta cada problema em
uma base sintética, para que a ausência de issues não seja confundida com
ausência de verificação.

## 5. Idempotência, cache e preservação do bruto

- calcular_tratamento() executa o pipeline e devolve o resultado, sem gravar
  arquivo. É a função usada pela API.
- executar_tratamento() chama calcular_tratamento() e grava a base limpa em
  data/clean/base_tratada.csv e a base de modelagem em
  data/clean/base_modelagem.csv, com data em AAAA-MM-DD e sem índice. É a
  função usada pelo CLI.
- A API cacheia o resultado pela assinatura do CSV (caminho, mtime e tamanho)
  e não grava em GET; se o arquivo mudar, o cache é invalidado.
- executar_tratamento() sempre parte do CSV bruto, nunca da base limpa.
- Rodar duas vezes produz arquivos idênticos byte a byte (teste
  test_tratamento_idempotente).
- O SHA-256 do CSV bruto é comparado antes e depois; o teste
  test_arquivo_original_nao_e_alterado falha se o arquivo mudar.

## 6. Contrato da API

### GET /api/quality/summary

Retorna base (arquivo, times, jogos, período), antes, depois,
duplicatas_removidas, por_regra, regras (com descrição e decisão),
colunas_excluidas_modelagem e modelagem (arquivo, linhas, colunas e
colunas_mantidas). É read-only: não grava a base limpa e usa cache
invalidado por mtime/tamanho do CSV.

### GET /api/quality/issues

Retorna total, filtros e a lista de issues, incluindo as linhas removidas por
duplicata. Parâmetros opcionais:

- regra: uma das chaves de REGRAS; valor inválido → 400;
- time: um dos 30 nomes oficiais; valor inválido → 400.

### GET /api/quality/regras

Catálogo de regras com descrição e decisão.

## 7. Testes

A suíte cobre:

- contrato do loader (colunas obrigatórias, coluna extra, renomeação, data,
  derivadas, dicionário, exclusão de modelagem);
- uma mutação sintética por regra, verificando que a regra é detectada;
- base sintética válida sem nenhuma issue;
- remoção de duplicata exata e de duplicata (time, jogo), com o registro
  removido aparecendo em issues e em por_regra;
- relatório antes/depois e caminho bruto customizado;
- calcular_tratamento() sem gravar arquivo;
- base real sem issues;
- arquivo original inalterado;
- idempotência;
- contrato HTTP (200, 400, 404, 500 JSON, filtro por time e página inicial).

Rodar com:

    pytest -q

## 8. Decisão de framework

O projeto usa Flask porque:

1. o enunciado sugere Flask explicitamente;
2. o grupo já tem um painel Flask funcional, que será reaproveitado no
   painel e nas análises seguintes;
3. a camada de dados não depende do framework — config, loader e cleaning
   podem ser importados por FastAPI sem mudança.

Se a decisão for revertida, basta criar os routers FastAPI chamando
calcular_tratamento() para leitura e manter os mesmos contratos JSON.

Observação: o projeto usa requirements.txt, que é o padrão do ecossistema
Python e o arquivo referenciado pelo README.

## 9. Limitações e próximos passos

- A #1 não imputa valores: decisão consciente, porque a base não tem ausentes.
  Se tivesse, a política seria sinalizar e tratar no eixo #2.
- As regras de duplicata de confronto/data precisam de decisão humana; o
  pipeline apenas sinaliza.
- O frontend atual é uma página mínima; o painel completo é o eixo #6.
- A análise de ausentes (#2) deve usar a base bruta; as análises #3 e #4 usam
  a base limpa gerada aqui.
