# Outliers (#3)

Código: `dashboards/analysis/outliers.py` · Rotas: `/api/outliers/summary`,
`/api/outliers?method=&team=&modo=` · Testes: `tests/test_outliers.py`
· Rodar: `python -m dashboards.analysis.outliers`

## 1. Outlier ≠ inconsistência

| | Inconsistência | Outlier |
|---|---|---|
| O que é | erro: viola regra aritmética ou de negócio | valor extremo, mas possível |
| Exemplo | REB ≠ OREB + DREB; FG3M > FGM | 62 rebotes; 15 tocos em um jogo |
| Onde | `dashboards/prep/cleaning.py` (#1) — **0 na base** | este módulo |
| Decisão | sinalizar para correção | sinalizar e discutir; **nunca remover** aqui |

## 2. Recorte e convenções

- Times: Golden State Warriors (75 jogos) e Orlando Magic (74), **separados**.
- Variáveis: pontos, rebotes, assistências, roubos, tocos, faltas, cestas de 3.
- Constantes em `config.py`, as mesmas da estatística descritiva (#4):
  |z| > 3; k = 1,5 no IQR; quartis por interpolação linear; α = 0,05;
  desvio amostral (ddof = 1).
- **Interface comum:** todo método é `metodo(X: DataFrame) -> Series[bool]`.
  - Aplicado a **uma coluna** → contagem por coluna (os 7 métodos).
  - Aplicado às **7 colunas juntas** → contagem por **jogo** (só os
    multivariados). As duas contagens não são comparáveis.

## 3. Os métodos

### Z-score
- **Teoria:** z = (x − x̄)/s mede quantos desvios o valor está da média. Sob
  normalidade, |z| > 3 tem probabilidade ≈ 0,27%.
- **Limitações:** a média e o desvio são puxados pelo próprio outlier
  (*mascaramento*); com n = 75, o maior |z| possível é (n−1)/√n ≈ 8,5, mas
  na prática quase nada passa de 3. Supõe normalidade.

### IQR / Boxplot (Tukey)
- **Teoria:** cercas em Q1 − 1,5·IQR e Q3 + 1,5·IQR. Para uma normal, isso
  equivale a ≈ ±2,7σ (0,7% dos dados).
- **Vantagens:** robusto (quartis não se movem com extremos), sem supor
  distribuição; é o mesmo critério dos pontos isolados do boxplot da #4.

### Teste de Grubbs
- **Teoria:** teste de hipótese. H0: não há outlier. G = max|x − x̄|/s,
  comparado a G_crit = (n−1)/√n · √(t²/(n−2+t²)), t = t_{α/(2n), n−2}.
  Se G > G_crit, retira o ponto e repete (versão iterativa).
- **Pressuposto:** normalidade — verificada com Shapiro-Wilk. Falha em
  `tocos` (os dois times), `roubos` e `tres_pontos_conv` (GSW) e
  `tres_pontos_conv` (ORL); nesses casos o resultado do Grubbs é indicativo.
- **Validação:** valores críticos conferidos com a tabela (n=10 → 2,290;
  n=30 → 2,908).

### ECOD (Li et al., 2022)
- **Teoria:** para cada coluna estima a distribuição acumulada empírica e
  calcula a probabilidade de cauda de cada valor ("que fração dos jogos é
  tão ou mais extrema?"). O score é a soma de −log dessas probabilidades,
  escolhendo a cauda pela assimetria da coluna.
- **Vantagens:** sem parâmetros, sem supor distribuição, rápido.
- **Limitação:** trata cada coluna separadamente — **não enxerga
  correlação** (um jogo comum em cada eixo, mas raro na combinação, passa;
  há um teste que demonstra isso). Em 1D sempre marca ≈ 5% das caudas.

### K-NN para anomalias
- **Teoria:** score = distância (padronizada) ao k-ésimo vizinho mais próximo
  (k = 5). Pontos normais têm vizinhos perto; outliers estão isolados.
- **Limitação:** distância global — numa região naturalmente esparsa, todos
  parecem outliers.

### LOF — Local Outlier Factor (Breunig et al., 2000)
- **Teoria:** compara a densidade local do ponto com a dos seus k vizinhos
  (k = 20). LOF ≈ 1: tão denso quanto a vizinhança; LOF > 1,5: bem mais
  isolado. Por ser *relativo*, detecta outliers locais.
- **Limiar:** LOF > 1,5 (o mesmo do `contamination="auto"` do sklearn).

### DBSCAN (Ester et al., 1996)
- **Teoria:** ponto "núcleo" tem ≥ min_samples vizinhos a até eps; núcleos
  conectados formam clusters; o que não entra em nenhum é **ruído = outlier**.
- **Parâmetros:** min_samples = max(2 × dimensões, 4) (Sander et al., 1998);
  eps no **cotovelo do gráfico de k-distância** (distância de cada ponto ao
  seu (min_samples−1)-ésimo vizinho, ordenada).

### Escolha dos limiares (importante)
Bibliotecas como o pyod marcam por padrão os 10% maiores scores
(`contamination=0.1`): a quantidade de outliers vira escolha do parâmetro.
Aqui ECOD e K-NN usam **Q3 + 1,5·IQR dos próprios scores** e o LOF usa 1,5.
Com contaminação fixa de 5%, os 30 times teriam exatamente 4 outliers em
ECOD, K-NN e LOF (5% de ~75), e a contagem não diria nada sobre os dados.
Os 4 métodos multivariados foram implementados com scikit-learn/scipy (o
ECOD à mão, ~10 linhas), sem dependência nova.

## 4. Resultados

### Por coluna (cada método em uma coluna por vez)

| Time | Coluna | z | IQR | Grubbs | ECOD | K-NN | LOF | DBSCAN |
|---|---|---|---|---|---|---|---|---|
| GSW | pontos | 0 | 0 | 0 | 3 | 5 | 2 | 2 |
| GSW | rebotes | 1 | 3 | 1 | 2 | 6 | 10 | 4 |
| GSW | assistências | 0 | 0 | 0 | 2 | 2 | 6 | 12 |
| GSW | roubos | 0 | 1 | 0 | 4 | 1 | 13 | 7 |
| GSW | tocos | 1 | 1 | 1 | 6 | 12 | 5 | 1 |
| GSW | faltas | 0 | 0 | 0 | 5 | 2 | 7 | 0 |
| GSW | cestas de 3 | 0 | 0 | 0 | 0 | 0 | 4 | 5 |
| ORL | pontos | 0 | 0 | 0 | 4 | 11 | 5 | 10 |
| ORL | rebotes | 0 | 0 | 0 | 3 | 5 | 4 | 4 |
| ORL | assistências | 1 | 1 | 0 | 5 | 4 | 12 | 5 |
| ORL | roubos | 0 | 0 | 0 | 3 | 14 | 6 | 0 |
| ORL | tocos | 1 | 3 | 1 | 4 | 12 | 8 | 3 |
| ORL | faltas | 0 | 0 | 0 | 4 | 2 | 8 | 2 |
| ORL | cestas de 3 | 1 | 1 | 1 | 4 | 5 | 10 | 2 |

### Por jogo (7 variáveis juntas, padronizadas)

| Time | ECOD | K-NN | LOF | DBSCAN | Consenso (2+ métodos) |
|---|---|---|---|---|---|
| GSW | 4 | 1 | 0 | 0 | 0 |
| ORL | 2 | 5 | 0 | 3 | 3 |

O **consenso** conta quantos dos 4 métodos marcam cada jogo (`n_metodos` em
`/api/outliers?modo=multivariado`). No ORL, os 3 jogos do DBSCAN (DET
28/11/2025, SAC 19/02/2026 e PHX 21/02/2026) também são marcados pelo K-NN.

### Referência da liga (univariados, 30 times)

`univariado_liga` no `/summary` aplica z-score, IQR e Grubbs a cada coluna de
cada um dos 30 times, com os limites de Tukey. No total: z-score 40, IQR 198 e
Grubbs 19 marcações em 210 combinações time × coluna. Serve para situar GSW e
ORL: os dois ficam dentro do padrão da liga.

### Onde os métodos concordam e divergem

- **Concordância forte (z, IQR e Grubbs):** GSW 62 rebotes vs MIA
  (19/11/2025) e 12 tocos vs CHI (10/03/2026); ORL 15 tocos vs PHX
  (21/02/2026) e 27 cestas de 3 vs SAC (19/02/2026). São os outliers mais
  confiáveis da análise.
- **Multivariado confirma:** o K-NN e o DBSCAN também marcam, para o ORL, os
  jogos de 19/02 (SAC) e 21/02 (PHX) — extremos em uma variável continuam
  isolados no espaço das 7, e são os jogos com consenso de 2+ métodos.
- **O IQR marca mais que z e Grubbs** (10 vs 5 vs 4) porque as cercas de
  Tukey (≈ 2,7σ) são mais estreitas que |z| > 3 e não sofrem mascaramento.
- **K-NN, LOF e DBSCAN em 1D divergem muito** e de forma instável. Motivo:
  as variáveis são contagens inteiras com muitos empates e n ≈ 75; as
  distâncias aos vizinhos ficam "em degraus" e os métodos acabam marcando
  *lacunas no meio da distribuição*, não extremos. A tabela `sensibilidade`
  (no `/summary`) mostra isso: mudando k (KNN 5/10/20, LOF 10/20/35) ou
  min_samples (DBSCAN 4/8/12), a contagem de uma mesma coluna varia em média
  5 a 9 jogos. **Conclusão:** em 1D, prefira IQR/z/Grubbs; os métodos de
  vizinhança fazem sentido no modo multivariado.
- **ECOD** marca sempre ≈ 5% por coluna (é a definição dele: caudas
  empíricas) e, no multivariado, destaca jogos extremos em várias colunas ao
  mesmo tempo (ex.: GSW 140 pts e 39 ast vs UTA), mas não combinações raras.

## 5. Representação no frontend

- **Heatmap coluna × método** (cor = contagem) a partir de `por_coluna`, com
  seletor de time.
- **Boxplot por variável** com os pontos marcados por cada método sobrepostos
  (cores/formas diferentes) — mostra visualmente a concordância.
- **Gráfico de k-distância** do DBSCAN (`dbscan[].k_distancias`) com a linha
  horizontal do eps escolhido.
- **Dispersão 2D** (PCA das 7 variáveis padronizadas, ou duas variáveis
  escolhidas) colorida pelo método multivariado; tooltip com data,
  adversário e valores, vindos de `/api/outliers?modo=multivariado`.
- **Tabela de sensibilidade** com a amplitude destacada quando ≥ 5, como
  alerta de instabilidade.
