Ministério da Educação
Universidade Federal do Agreste de Pernambuco
Bacharelado em Ciência da Computação

Disciplina: Laboratório de Ciência de Dados

2026.2

Prof. Ryan Azevedo

# PROJETO 1

O projeto deve ser desenvolvido em **Python**:

1. O relatório de análise deve ser **apresentado por meio de um sistema web** desenvolvido em ***Python*** (sugestão: ***Flask***; o grupo pode usar outro framework, desde que justifique). O sistema deve funcionar como o **relatório do projeto**, exibindo, para cada item do enunciado:

   - [x] **(a) os resultados** — tabelas e gráficos; → `projeto-1/dashboards/templates/`, `dashboards/analysis/plots.py`
   - [x] **(b) a interpretação textual** — a análise crítica dos resultados. → `projeto-1/dashboards/analysis/texto.py`

**Exigências mínimas do sistema:**

- [x] Deve exibir, no mínimo: (i) o dicionário de dados; (ii) as medidas descritivas por variável e por time; (iii) os gráficos produzidos (Boxplot e gráfico de barras comparativo); (iv) a seção de síntese/interpretação; e (v) a discussão dos métodos de qualidade dos dados (*missing*, *outliers*, inconsistências). → `/`, `/descritiva`, `/qualidade`, `/outliers`, `/sintese`
- [x] Deve ser **navegável e interativo**: o usuário deve poder selecionar o time e/ou a variável e ver os resultados correspondentes atualizados. → `dashboards/templates/base.html` (filtro GET)
- [x] **Todos os gráficos** devem ter título, eixos rotulados, unidades e legendas. → `dashboards/analysis/plots.py`
- [x] **Todas as tabelas** devem ser padronizadas (mesmas casas decimais, mesmas unidades). → `dashboards/web/painel.py` (`tab`, 2 decimais); footer em `base.html`
- [ ] O sistema deve estar **hospedado e acessível por link público** no momento da avaliação. Se a hospedagem gratuita sair do ar, o grupo é responsável por restabelecê-la. Alternativa aceita: instruções claras de execução local no `README.md` (com `requirements.txt` e comando único). → [x] alternativa local: `projeto-1/README.md`, `projeto-1/requirements.txt`; link público pendente

**Observação**: o sistema **substitui o relatório em PDF/notebook**. Não é necessário entregar um documento separado — o conteúdo analítico deve estar **dentro do sistema web**, organizado por seções correspondentes aos itens do enunciado.

Entregar via Classroom:

- [x] Código-fonte enviado pelo Google Classroom da disciplina, em arquivo .zip ou link de repositório (GitHub/GitLab). → `https://github.com/datasci-g8/projeto-1`
- [ ] Link da aplicação informado no campo de submissão do Classroom.
- [ ] Critérios de avaliação: ver rubrica em anexo. (Ou: "a rubrica será apresentada em sala".)

**Observação sobre decisões metodológicas:** itens não especificados neste enunciado devem ser decididos pelo grupo e justificados no relatório. Dúvidas devem ser levadas ao professor.

## DESENVOLVIMENTO

Apresente:

- [x] O número de linhas e colunas, o nome das colunas e o que elas representam dentro do contexto (Cliente? Vendedor, Jogador?). Crie um Apêndice/Dicionário e informe o que significa cada coluna da Base. → `projeto-1/dashboards/prep/loader.py` (`tabela_dicionario`), `projeto-1/docs/tratamento.md`, `projeto-1/README.md`
- [x] Os tipos de dados de cada coluna? Quais são numéricas, categóricas, datas, texto, binárias? Apresente para o usuários os tipos de dados de cada coluna. Para um gestor talvez não seja necessário, mas para a equipe de desenvolvimento possivelmente é importante. → `projeto-1/dashboards/prep/loader.py`, `projeto-1/docs/tratamento.md`; UI #6
- [x] Tamanho da Base/Dataset, como tratar os campos do tipo Data? Na base, você deve tratar o campo data. → `projeto-1/dashboards/prep/loader.py`, `projeto-1/docs/tratamento.md`
- [x] Altere o nome das colunas com novos nomes intuitivos. → `projeto-1/config.py` (`RENOMEAR`), `projeto-1/dashboards/prep/loader.py`
- [x] Algumas colunas estão como categóricas e precisam ser numéricas, trate isso e informe como tratou. Ex; W e L. Verifique se a base possui algum campo do tipo Data e se o mesmo necessita de algum tratamento. → `projeto-1/docs/tratamento.md`
- [x] Exclua colunas que não servem para previsões usando modelos de aprendizado de máquina e aprendizado profundo. (Os grupos devem entender do contexto da base de dados). → `projeto-1/dashboards/prep/loader.py` (`colunas_modelagem`), `projeto-1/docs/tratamento.md`
- [x] Verifique a existência de Valores especiais: zeros, negativos, duplicados, valores fora de domínio (ex.: idade = 999). → `projeto-1/dashboards/prep/cleaning.py`, `projeto-1/docs/tratamento.md`
- [x] Qual a quantidade de campos com valores ausentes por coluna? Explique os mecanismos MCAR, MAR e MNAR (mecanismos clássicos que descrevem por que os dados estão faltando em um conjunto de dados) → `projeto-1/dashboards/analysis/missing.py`, `projeto-1/docs/ausentes.md`, `/api/missing/summary`
  - [x] Como e por que utilizar os seguintes testes:
    - [x] Teste de Little (Little's MCAR test), teste de Jamshidian-Jala → `projeto-1/dashboards/analysis/missing.py`, `projeto-1/docs/ausentes.md`
    - [x] Teste de Listing e Schlitgen (LS), Regressão Logística de Fairclough. → idem, `/api/missing/tests`
- [x] Para cada coluna qual a quantidade de campos com valores inconsistentes ou outliers? → qualidade: `projeto-1/dashboards/prep/cleaning.py`; outliers: `projeto-1/dashboards/analysis/outliers.py`
  - [x] Você deve implementar e explicar a teoria dos métodos abaixo:
    - [x] Z-score usando o desvio padrão da média ou outro limiar, pode utilizar IQR (Intervalo Interquartil) /Boxplot e verificar os extremos. → `projeto-1/dashboards/analysis/outliers.py`, `projeto-1/docs/outliers.md`
    - [x] Teste de Grubbs → idem
    - [x] ECOD (Empirical Cumulative Distribution-based Outlier Detection) → idem
    - [x] K-NN (K-Nearest Neighbors) para anomalias → idem
    - [x] DBSCAN (Density-Based Spatial Clustering of Applications with Noise) → idem
    - [x] LOF (Local Outlier Factor) → idem
    - [x] Você pode utilizar métodos de Machine Learning para dados de alta dimensionalidade e padrões complexos, por enquanto não utilizaremos.

## Estatística Descritiva: (Por enquanto Análise Univariada)

Apresente:

- [x] As medidas de tendência central para: Pontos, Rebotes, Assistências, STL, BLK, PF e FG3M, dos times selecionados para o seu grupo de trabalho: → `projeto-1/config.py` (`VARIAVEIS_ANALISE`, `TIMES_GRUPO`), `projeto-1/dashboards/analysis/descriptive.py`
  - [x] Média, Mediana e Moda → idem
  - [x] Outliers (Quantos e quais são) → `lista_outliers`, `/api/descriptive/outliers`
  - [x] Menos valor, Maior Valor, Amplitude, Desvio Padrão e Variância → `tabela_medidas`
  - [x] Quartis (Q1, Q3) → idem; `config.METODO_QUARTIS`
  - [x] Apresente um gráfico Boxplot com as medidas encontradas para cada variável pedida, o gráfico deve conter Outliers Superiores, Limite Superior, Q3, Média, Mediana, Moda, Q1, Limite Inferior e Outliers Inferiores. → `/descritiva`, `plots.boxplot`
  - [x] Construa um gráfico de barras que possibilite comparar os dados pedidos para os times do seu grupo, onde o z-score poderia entrar? → `plots.barras_comparativas`
- [x] Verificar a Assimetria (skewness) → Para cada uma das variáveis (Pontos, Rebotes, Assistências, STL, BLK, PF e FG3M) e para cada time do grupo: → `tabela_assimetria`, `docs/descriptive.md`
  - [x] Calcule o coeficiente de assimetria e informe explicitamente qual fórmula/implementação utilizou (ex.: coeficiente de momento de Pearson, coeficiente ajustado de Fisher-Pearson ou coeficiente de Bowley). Justifique a escolha. → Fisher-Pearson em `descriptive.py`
  - [x] Classifique a distribuição quanto à direção (simétrica, assimétrica à direita/positiva ou à esquerda/negativa), com base no sinal do coeficiente. → idem
  - [x] Classifique a intensidade da assimetria (aproximadamente simétrica, moderada ou forte), informando o critério adotado (ex.: |g1| < 0,5; 0,5 ≤ |g1| < 1; |g1| ≥ 1 — ou outro critério justificado). → idem
  - [x] Confirme visualmente a assimetria com um histograma com curva de densidade (KDE) sobreposto e com o Boxplot já construído. Comente se o coeficiente e os gráficos contam a mesma história; se houver divergência, discuta o motivo. → `/assimetria`
  - [x] Compare os resultados entre variáveis e entre times. Destaque quais variáveis são mais assimétricas e se o padrão se repete nos times do grupo. → `/assimetria`, `texto_assimetria`
  - [x] Discuta a implicação prática da assimetria encontrada: nessa variável, a média ou a mediana representa melhor o valor típico? Há indício de que transformações (ex.: log) ou métodos robustos seriam apropriados em análises posteriores → `/assimetria`
- [x] Coeficiente de Variação (CV) → Para cada uma das variáveis (Pontos, Rebotes, Assistências, STL, BLK, PF e FG3M) e para cada time do grupo: → `tabela_cv`, `quadro_cv`
  - [x] Calcule o CV e informe explicitamente a fórmula utilizada, incluindo se o desvio padrão é amostral (n – 1) ou populacional, e se o resultado é apresentado em fração ou em percentual. Mantenha a mesma convenção adotada nas demais medidas do projeto. → `config.DDOF`, `docs/descriptive.md`
  - [x] Verifique a condição de validade do CV para cada variável: a variável é de razão? A média é positiva e suficientemente distante de zero? Se a média for muito pequena (caso típico de BLK e STL), explique por que o CV fica inflado e deve ser interpretado com cautela. → flags `valido`, `media_pequena`
  - [x] Interprete o valor obtido: o que um CV alto ou baixo significa, em termos práticos, para aquela estatística do time (ex.: "o time tem pontuação muito irregular de um jogo para outro" vs. "o time é consistente"). → `/cv`, `texto_cv`
  - [x] Use o CV para comparar dispersão entre variáveis de escalas diferentes. Destaque quais variáveis são relativamente mais dispersas e quais são mais estáveis, justificando por que o desvio padrão bruto não permitiria essa comparação (escalas distintas) e o CV permite (medida adimensional). → `/cv`
  - [x] Compare os times do grupo quanto à homogeneidade/regularidade: qual time é o mais consistente e qual é o mais irregular em cada variável? O padrão se mantém entre variáveis ou muda? → `/cv`
  - [x] Confronte o CV com o desvio padrão e com a assimetria já calculada. Em variáveis com assimetria forte, discuta se o CV (baseado na média e no desvio) é uma medida adequada ou se uma alternativa robusta (ex.: coeficiente de variação baseado na mediana, ou razão entre IQR e mediana) seria mais apropriada. → `/cv` (`cv_robusto_pct`)
  - [x] Apresente um quadro-resumo (linhas = variáveis, colunas = times, células = CV) para facilitar a comparação, e comente os destaques. → `/cv`
- [x] Intervalo Interquartil (IQR) → Para cada uma das variáveis (Pontos, Rebotes, Assistências, STL, BLK, PF e FG3M) e para cada time do grupo: → `tabela_iqr`, `quadro_iqr`
  - [x] Calcule o IQR como IQR = Q3 − Q1 e informe explicitamente qual método de cálculo dos quartis foi utilizado (ex.: método de Tukey, de Moore & McCabe, ou interpolação linear, padrão de numpy/pandas). Mantenha o mesmo método adotado no item de quartis e no Boxplot, para garantir consistência. → `config.METODO_QUARTIS`, `config.K_IQR`
  - [x] Apresente Q1, Q3 e IQR lado a lado em uma tabela, por variável e por time, para deixar claro de onde o IQR vem. → `/api/descriptive/summary`
  - [x] Interprete o IQR em termos práticos: o que um IQR alto ou baixo significa para aquela estatística do time? (ex.: "50% central dos jogos do time ficou dentro de uma faixa de X pontos", o IQR é a largura da faixa central que contém 50% das observações). → `/iqr`, `texto_iqr`
  - [ ] Compare o IQR com a amplitude (já calculada) e com o desvio padrão (já calculado):
    - [x] Mostre em quais variáveis a amplitude é muito maior que o IQR e explique por que isso acontece (a amplitude é sensível a outliers; o IQR não). → `/iqr`
    - [x] Mostre em quais variáveis o desvio padrão é inflado por valores extremos, enquanto o IQR permanece estável, evidência de que o IQR é uma medida robusta. → `/iqr`
  - [x] Use o IQR para justificar a regra de detecção de outliers adotada no item anterior: deixe explícito se usou 1,5×IQR ou 3×IQR (ou outro critério) e recalcule os limites Q1−k×IQR e Q3+k×IQR, conferindo se os outliers listados coincidem com os que ficam fora desses limites no Boxplot. Comente eventuais divergências. → `/iqr`, `/descritiva`
  - [x] Compare os times do grupo quanto à dispersão central (largura da faixa de 50% central): qual time é mais concentrado e qual é mais espalhado em cada variável? O padrão se mantém entre variáveis? → `/iqr`
  - [x] Apresente um quadro-resumo (linhas = variáveis, colunas = times, células = IQR) e comente os destaques, articulando com a assimetria e o CV já calculados. → `/iqr`
