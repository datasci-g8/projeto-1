"""Configuração central do Projeto 1 (Lab. Ciência de Dados, UFAPE 2026.2).

Tudo o que é "convenção do projeto" fica aqui: caminhos, times do grupo,
variáveis de análise, mapeamento de colunas, domínios e constantes estatísticas.
As demais análises (#2, #3, #4) devem importar daqui — nunca repetir o valor
de k, do limiar z ou do método de quartis.
"""
from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_CSV = DATA_DIR / "stats_times_regular_final.csv"
CLEAN_DIR = DATA_DIR / "clean"
CLEAN_CSV = CLEAN_DIR / "base_tratada.csv"
MODEL_CSV = CLEAN_DIR / "base_modelagem.csv"  # base limpa sem COLUNAS_EXCLUIDAS_MODELAGEM
STATIC_DIR = BASE_DIR / "dashboards" / "static"
DOCS_DIR = BASE_DIR / "docs"

# ---------------------------------------------------------------------------
# Escopo do grupo (Grupo 8)
# ---------------------------------------------------------------------------
TIMES_GRUPO = ("Golden State Warriors", "Orlando Magic")

# Variáveis-alvo da análise descritiva (nomes já tratados, em pt-BR)
VARIAVEIS_ANALISE = (
    "pontos",
    "rebotes",
    "assistencias",
    "roubos",
    "tocos",
    "faltas",
    "tres_pontos_conv",
)

# ---------------------------------------------------------------------------
# Contrato da base bruta (28 colunas)
# ---------------------------------------------------------------------------
COLUNAS_ESPERADAS = [
    "Team_ID",
    "Game_ID",
    "GAME_DATE",
    "MATCHUP",
    "WL",
    "W",
    "L",
    "W_PCT",
    "MIN",
    "FGM",
    "FGA",
    "FG_PCT",
    "FG3M",
    "FG3A",
    "FG3_PCT",
    "FTM",
    "FTA",
    "FT_PCT",
    "OREB",
    "DREB",
    "REB",
    "AST",
    "STL",
    "BLK",
    "TOV",
    "PF",
    "PTS",
    "TEAM_NAME",
]

RENOMEAR = {
    "Team_ID": "id_time",
    "Game_ID": "id_jogo",
    "GAME_DATE": "data_jogo",
    "MATCHUP": "confronto",
    "WL": "vitoria",
    "W": "vitorias_acum",
    "L": "derrotas_acum",
    "W_PCT": "pct_vitorias_acum",
    "MIN": "minutos",
    "FGM": "arremessos_conv",
    "FGA": "arremessos_tent",
    "FG_PCT": "pct_arremessos",
    "FG3M": "tres_pontos_conv",
    "FG3A": "tres_pontos_tent",
    "FG3_PCT": "pct_tres_pontos",
    "FTM": "lances_livres_conv",
    "FTA": "lances_livres_tent",
    "FT_PCT": "pct_lances_livres",
    "OREB": "rebotes_ofensivos",
    "DREB": "rebotes_defensivos",
    "REB": "rebotes",
    "AST": "assistencias",
    "STL": "roubos",
    "BLK": "tocos",
    "TOV": "erros",
    "PF": "faltas",
    "PTS": "pontos",
    "TEAM_NAME": "time",
}

# Colunas numéricas (após renomear) que devem ser validadas como números.
COLUNAS_NUMERICAS = [
    "id_time",
    "id_jogo",
    "vitoria",
    "vitorias_acum",
    "derrotas_acum",
    "pct_vitorias_acum",
    "minutos",
    "arremessos_conv",
    "arremessos_tent",
    "pct_arremessos",
    "tres_pontos_conv",
    "tres_pontos_tent",
    "pct_tres_pontos",
    "lances_livres_conv",
    "lances_livres_tent",
    "pct_lances_livres",
    "rebotes_ofensivos",
    "rebotes_defensivos",
    "rebotes",
    "assistencias",
    "roubos",
    "tocos",
    "erros",
    "faltas",
    "pontos",
]

# Colunas que são contagens de eventos: por regra de negócio só admitem
# inteiros >= 0 (zero é válido — ex.: um jogo sem tocos).
COLUNAS_CONTAGEM = [
    "vitorias_acum",
    "derrotas_acum",
    "minutos",
    "arremessos_conv",
    "arremessos_tent",
    "tres_pontos_conv",
    "tres_pontos_tent",
    "lances_livres_conv",
    "lances_livres_tent",
    "rebotes_ofensivos",
    "rebotes_defensivos",
    "rebotes",
    "assistencias",
    "roubos",
    "tocos",
    "erros",
    "faltas",
    "pontos",
]

COLUNAS_DERIVADAS = ["mes", "dia_semana", "em_casa", "prorrogacao", "adversario", "sigla"]

# Versão para modelagem: remove identificadores e vazamento de informação.
COLUNAS_EXCLUIDAS_MODELAGEM = {
    "id_time": "Identificador do time; redundante com 'time' e sem valor preditivo.",
    "id_jogo": "Identificador do jogo; não generaliza para jogos futuros.",
    "vitorias_acum": "Acumulado da temporada até o jogo; vazamento de informação.",
    "derrotas_acum": "Acumulado da temporada até o jogo; vazamento de informação.",
    "pct_vitorias_acum": "Derivado de W/L acumulados; vazamento de informação.",
    "minutos": "Quase constante (240/265/290); a prorrogação já está em 'prorrogacao'.",
    "data_jogo": "Data do jogo; útil para ordenar, mas não como preditor (e permite vazamento temporal).",
}

# ---------------------------------------------------------------------------
# Convenções estatísticas (usar em todas as análises)
# ---------------------------------------------------------------------------
K_IQR = 1.5                 # fator dos limites de Tukey (boxplot e outliers)
Z_LIMIAR = 3.0              # |z| > 3 para z-score
ALPHA_GRUBBS = 0.05         # nível de significância do teste de Grubbs
JOGOS_TEMPORADA_REGULAR = 82  # cada time da NBA joga 82 partidas na temporada regular
MINUTOS_REGULAMENTARES = 240
MINUTOS_VALIDOS = (MINUTOS_REGULAMENTARES, 265, 290, 315, 340)  # regulamentar + prorrogações
PONTOS_CESTA = 2            # pontos de um arremesso de quadra convertido
TOLERANCIA_PCT = 1e-3       # tolerância para percentuais arredondados (3 casas)
TOLERANCIA_PONTOS = 1e-6    # pontos são contagens inteiras
METODO_QUARTIS = "interpolacao_linear"  # padrão pandas/numpy (tipo 7 de Hyndman-Fan)
DDOF = 1                    # desvio padrão e variância amostrais

# ---------------------------------------------------------------------------
# Times da NBA: nome oficial -> abreviação usada em MATCHUP
# ---------------------------------------------------------------------------
TIME_ABREV = {
    "Atlanta Hawks": "ATL",
    "Boston Celtics": "BOS",
    "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA",
    "Chicago Bulls": "CHI",
    "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL",
    "Denver Nuggets": "DEN",
    "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW",
    "Houston Rockets": "HOU",
    "Indiana Pacers": "IND",
    "Los Angeles Clippers": "LAC",
    "Los Angeles Lakers": "LAL",
    "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA",
    "Milwaukee Bucks": "MIL",
    "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP",
    "New York Knicks": "NYK",
    "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL",
    "Philadelphia 76ers": "PHI",
    "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR",
    "Sacramento Kings": "SAC",
    "San Antonio Spurs": "SAS",
    "Toronto Raptors": "TOR",
    "Utah Jazz": "UTA",
    "Washington Wizards": "WAS",
}

ID_TIME = {
    "Atlanta Hawks": 1610612737,
    "Boston Celtics": 1610612738,
    "Brooklyn Nets": 1610612751,
    "Charlotte Hornets": 1610612766,
    "Chicago Bulls": 1610612741,
    "Cleveland Cavaliers": 1610612739,
    "Dallas Mavericks": 1610612742,
    "Denver Nuggets": 1610612743,
    "Detroit Pistons": 1610612765,
    "Golden State Warriors": 1610612744,
    "Houston Rockets": 1610612745,
    "Indiana Pacers": 1610612754,
    "Los Angeles Clippers": 1610612746,
    "Los Angeles Lakers": 1610612747,
    "Memphis Grizzlies": 1610612763,
    "Miami Heat": 1610612748,
    "Milwaukee Bucks": 1610612749,
    "Minnesota Timberwolves": 1610612750,
    "New Orleans Pelicans": 1610612740,
    "New York Knicks": 1610612752,
    "Oklahoma City Thunder": 1610612760,
    "Orlando Magic": 1610612753,
    "Philadelphia 76ers": 1610612755,
    "Phoenix Suns": 1610612756,
    "Portland Trail Blazers": 1610612757,
    "Sacramento Kings": 1610612758,
    "San Antonio Spurs": 1610612759,
    "Toronto Raptors": 1610612761,
    "Utah Jazz": 1610612762,
    "Washington Wizards": 1610612764,
}
