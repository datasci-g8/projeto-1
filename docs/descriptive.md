# Estatística descritiva (#4)

Código: `dashboards/analysis/descriptive.py` · Rotas: `/api/descriptive/summary`,
`/api/descriptive/outliers` · Testes: `tests/test_descriptive.py`
· Rodar: `python -m dashboards.analysis.descriptive`

## 1. Objetivo e recorte

Análise univariada por variável × time sobre a **base tratada** (saída da #1),
não sobre o CSV bruto. O recorte padrão é o Grupo 8: Golden State Warriors e
Orlando Magic. As sete variáveis estão em `config.VARIAVEIS_ANALISE`.

## 2. Convenções (todas em `config.py`)

| Convenção | Valor |
|---|---|
| Quartis | interpolação linear (padrão pandas/numpy) |
| Desvio / variância | amostrais (`ddof = 1`) |
| Outliers na descritiva | regra de Tukey `1,5 × IQR` (`K_IQR`) |
| Assimetria | Fisher-Pearson ajustado (`scipy.stats.skew`, `bias=False`) |
| CV | `100 · s / média`, com s amostral |
| Unidade | por jogo |

A mesma `K_IQR` e o mesmo `limites_iqr` de `dashboards/analysis/outliers.py`
são reutilizados, para a #3 e a #4 não divergirem na regra do boxplot.

## 3. O que cada tabela entrega

### Medidas (`medidas`)
n, média, mediana, moda, mín, máx, amplitude, desvio, variância, Q1, Q3, IQR,
limites de Tukey e contagem/valores de outliers.

### Assimetria (`assimetria`)
- `g1_fisher_pearson`: coeficiente principal
- `pearson_2` e `bowley`: checagens auxiliares
- classificação de direção e intensidade (|g1| < 0,5 / 0,5–1 / ≥ 1)
- representante sugerido (média ou mediana)

### Coeficiente de variação (`cv`)
CV clássico (%), CV robusto `100 · IQR / mediana`, classificação de dispersão
e flag de validade (média > 0; cautela quando a média é pequena, ex. tocos).

### IQR (`iqr`)
Q1, Q3, IQR, amplitude, razões amplitude/IQR e DP/IQR, limites e n de outliers.

### Lista de outliers (`lista_outliers`)
Cada ponto fora das cercas 1,5×IQR com data, adversário, local e lado
(superior/inferior). Não remove linhas — só sinaliza.

### Z-score entre times (`zscore_liga`)
Z-score da **média** de cada time em relação às médias dos 30 times da liga,
útil para o gráfico de barras comparativo do frontend (#6).

## 4. API

### `GET /api/descriptive/summary`
Aceita `?team=` e `?var=`. Devolve medidas, assimetria, CV, IQR, quadros-resumo
e z-scores da liga. Time fora do grupo ou variável inválida → 400.

### `GET /api/descriptive/outliers`
Lista os outliers 1,5×IQR com os mesmos filtros. A detecção multi-método
continua em `/api/outliers`.

## 5. Relação com os outros eixos

| Eixo | Papel |
|---|---|
| #1 qualidade | fornece a base tratada |
| #3 outliers | métodos z/IQR/Grubbs/ECOD/KNN/LOF/DBSCAN |
| #4 descritiva (este) | resumo estatístico + outliers do boxplot |
| #6 frontend | consome estas rotas para tabelas e gráficos |
