# Valores ausentes

Código: `dashboards/analysis/missing.py` · Rotas: `/api/missing/summary`, `/api/missing/tests`
· Testes: `tests/test_missing.py` · Rodar: `python -m dashboards.analysis.missing`

## 1. Resultado (base original)

A análise roda sobre o CSV original (`data/stats_times_regular_final.csv`),
com os nomes originais das colunas — antes de qualquer tratamento.

| Métrica | Valor |
|---|---|
| Base | 2.238 linhas × 28 colunas |
| Ausentes no total | **0** (todas as 28 colunas, todos os 30 times) |
| Padrões de ausência | 1 (a linha completa) |
| Variáveis testadas | PTS, REB, AST, STL, BLK, PF, FG3M |
| Testes de MCAR | **não aplicáveis**: não há grupo "com falta" para comparar |

Conclusão: não há mecanismo de ausência a identificar nem imputação a fazer.

Os testes usam só as 7 variáveis de análise porque colunas como REB
(= OREB + DREB) e PTS (= 2·FGM + FG3M + FTM) são combinações exatas de
outras e tornariam a matriz de covariância singular.

## 2. Os três mecanismos (Rubin, 1976)

Seja R o indicador "o valor faltou". O mecanismo diz do que P(R) depende.

| Mecanismo | P(R) depende de… | Exemplo na NBA | Consequência |
|---|---|---|---|
| **MCAR** — completamente ao acaso | nada | o sistema caiu e perdeu linhas aleatórias | apagar linhas só reduz n, sem viés |
| **MAR** — ao acaso, dado o observado | outras colunas **observadas** | em jogos de muitos pontos o digitador esquece as assistências | apagar linhas gera viés; imputar usando as outras colunas corrige |
| **MNAR** — não ao acaso | o **próprio valor** que faltou | assistências altas demais ficam "em revisão" e somem | nem imputar corrige: a pista sumiu junto com o valor |

Ponto central: **todos os testes abaixo têm H0 = MCAR**. Eles podem rejeitar
MCAR, mas nunca confirmá-lo (p alto = falta de evidência contra), e **nenhum
distingue MAR de MNAR** — para isso seria preciso conhecer os valores que
faltaram.

## 3. Validação dos testes (só nos testes automatizados)

Como a base não tem ausentes, a implementação dos testes é validada em
`tests/test_missing.py` com cópias da base em que 15% de `assistencias` são
apagados com mecanismo conhecido. **Esses números não fazem parte do
relatório** nem da API — servem apenas para provar que os testes funcionam:

- **MCAR:** cada linha tem 15% de chance;
- **MAR:** a chance cresce com o rank de `pontos` (de ~0% a ~30%);
- **MNAR:** a chance cresce com o rank da própria `assistencias`.

Semente fixa (`config.SEMENTE`), então o resultado é reprodutível.

## 4. Os testes

### Little (1988) — compara médias
- **Ideia:** separa as linhas por padrão de ausência. Sob MCAR, as linhas onde
  faltou `assistencias` são uma amostra aleatória, então a média das outras
  colunas nesse grupo deve ser igual à média geral, estimada por máxima
  verossimilhança com o algoritmo **EM** (`estimar_em`).
- **Estatística:** d² = Σⱼ nⱼ (x̄ⱼ − μⱼ)ᵀ Σⱼ⁻¹ (x̄ⱼ − μⱼ) ~ χ²(Σⱼ pⱼ − p).
- **Pressupostos:** normalidade multivariada aproximada; padrões com n razoável.
- **Quando usar:** primeiro teste, global, para várias colunas ao mesmo tempo.
- **Limitação:** só olha médias; diferenças apenas de variância passam.
- **EM:** alterna entre preencher os ausentes pela esperança condicional
  (regressão nas colunas observadas, mais a correção de covariância) e
  reestimar μ e Σ, até convergir. Sem ausentes, coincide com a média e a
  covariância amostrais (divisor n).

### Jamshidian e Jalal (2010) — compara covariâncias
- **Ideia:** imputa os ausentes supondo MCAR; se MCAR for verdade, todo padrão
  de ausência, depois de imputado, tem a mesma matriz de covariância.
- **Estatística:** M de Box entre os grupos de padrão; p-valor por
  **permutação** dos rótulos de padrão (199 permutações), o que dispensa
  normalidade — importante para contagens discretas.
- **Detalhe crucial:** a imputação usa regressão **+ ruído**. Sem o ruído, o
  grupo imputado teria variância artificialmente menor e o teste acusaria
  diferença até sob MCAR.
- **Quando usar:** complemento ao Little; pega casos em que a falta muda a
  dispersão sem mudar a média.
- **Simplificação adotada:** uma imputação e M de Box, no lugar de múltiplas
  imputações e teste de Hawkins do artigo.

### Listing e Schlittgen (1998) — não paramétrico
- **Ideia:** para cada coluna com falta, compara a distribuição de cada outra
  variável entre "faltou" e "observou" com Wilcoxon-Mann-Whitney (postos).
- **Estatística:** U de Mann-Whitney; p-valores combinados por Bonferroni.
- **Pressupostos:** nenhum sobre a forma da distribuição.
- **Quando usar:** variáveis assimétricas ou discretas (tocos, roubos), onde
  a normalidade do Little é duvidosa.
- **Adaptação:** o teste original é para *dropout* em dados longitudinais;
  aqui comparamos grupos em dados transversais.

### Regressão logística de Fairclough — modela a falta
- **Ideia:** cria R = 1 se faltou e ajusta logit P(R = 1) = β₀ + β·X com as
  demais variáveis padronizadas. Sob MCAR, todos os β são zero.
- **Estatística:** razão de verossimilhança LR = 2(ℓ_modelo − ℓ_nulo) ~ χ²(k);
  z de Wald para cada β.
- **Vantagem didática:** além de rejeitar MCAR, **aponta qual variável explica
  a falta** — no cenário MAR, `pontos` aparece com o maior |z|.
- **Quando usar:** quando se quer saber *por que* falta (útil para escolher as
  variáveis do modelo de imputação).

## 5. Resultado da validação (α = 0,05)

| Cenário | Little | Jamshidian-Jalal | Listing-Schlittgen | Fairclough |
|---|---|---|---|---|
| MCAR | p = 0,96 · não rejeita | p = 0,67 · não rejeita | p = 1,00 · não rejeita | p = 0,96 · não rejeita |
| MAR | p ≈ 2e-26 · rejeita | p = 0,035 · rejeita | p ≈ 2e-30 · rejeita | p ≈ 5e-27 · rejeita |
| MNAR | p ≈ 6e-12 · rejeita | p = 0,06 · não rejeita | p ≈ 3e-12 · rejeita | p ≈ 6e-12 · rejeita |

Leitura:

1. **MCAR:** nenhum teste rejeita — acertam.
2. **MAR:** todos rejeitam — acertam. O JJ rejeita por margem pequena: a
   seleção mexe mais nas médias que nas covariâncias, e ele só olha covariâncias.
3. **MNAR:** três testes rejeitam porque `assistencias` é correlacionada com
   `pontos`: quando somem as assistências altas, somem jogos de muitos pontos,
   e isso aparece nas colunas observadas. Mas o resultado é **idêntico ao do
   MAR** — os testes não sabem dizer qual dos dois é. Se a variável ausente
   não tivesse correlação com nenhuma observada, o MNAR passaria invisível.

## 6. Painel web

A rota `/quality` mostra a contagem de ausentes por coluna (base bruta),
a conclusão textual, as verificações de limpeza e a tabela dos testes MCAR
(`GET /api/missing/tests`). Com a base completa, os testes aparecem como
não aplicáveis ou não rejeitam MCAR, conforme `docs/missing.md` e o código
em `dashboards/analysis/missing.py`.
