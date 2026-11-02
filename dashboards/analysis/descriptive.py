from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

import config
from dashboards.analysis import outliers

ROTULOS = {
    "pontos": "Pontos",
    "rebotes": "Rebotes",
    "assistencias": "Assistências",
    "roubos": "Roubos (STL)",
    "tocos": "Tocos (BLK)",
    "faltas": "Faltas (PF)",
    "tres_pontos_conv": "Cestas de 3 (FG3M)",
}
UNIDADE = "por jogo"


def _iqr_serie(
    serie: pd.Series, k: float = config.K_IQR
) -> tuple[pd.Series, float, float, float, float]:
    """Flags IQR + Q1, Q3 e cercas de Tukey (mesma regra de outliers.limites_iqr)."""
    q1, q3 = (float(v) for v in serie.quantile([0.25, 0.75]))
    lim_inf, lim_sup = outliers.limites_iqr(serie, k)
    flags = (serie < lim_inf) | (serie > lim_sup)
    return flags, q1, q3, lim_inf, lim_sup


def moda(serie: pd.Series) -> str:
    valores = serie.mode()
    if len(valores) <= 3:
        return ", ".join(str(int(x)) for x in valores)
    return f"{int(valores.iloc[0])} (multimodal: {len(valores)} modas)"


def medidas(serie: pd.Series) -> dict:
    flags, q1, q3, lim_inf, lim_sup = _iqr_serie(serie)
    return {
        "n": int(serie.count()),
        "media": float(serie.mean()),
        "mediana": float(serie.median()),
        "moda": moda(serie),
        "minimo": float(serie.min()),
        "maximo": float(serie.max()),
        "amplitude": float(serie.max() - serie.min()),
        "desvio_padrao": float(serie.std(ddof=config.DDOF)),
        "variancia": float(serie.var(ddof=config.DDOF)),
        "q1": q1,
        "q3": q3,
        "iqr": q3 - q1,
        "limite_inf": lim_inf,
        "limite_sup": lim_sup,
        "n_outliers": int(flags.sum()),
        "outliers_sup": sorted((serie[serie > lim_sup]).tolist(), reverse=True),
        "outliers_inf": sorted((serie[serie < lim_inf]).tolist()),
    }


def tabela_medidas(
    df: pd.DataFrame, variaveis=config.VARIAVEIS_ANALISE
) -> pd.DataFrame:
    linhas = []
    for time, grupo in df.groupby("time", observed=True):
        for variavel in variaveis:
            linha = medidas(grupo[variavel])
            linha.update({"time": str(time), "variavel": variavel})
            linhas.append(linha)
    colunas = [
        "time", "variavel", "n", "media", "mediana", "moda", "minimo", "maximo",
        "amplitude", "desvio_padrao", "variancia", "q1", "q3", "iqr",
        "limite_inf", "limite_sup", "n_outliers", "outliers_inf", "outliers_sup",
    ]
    return pd.DataFrame(linhas)[colunas]


def lista_outliers(
    df: pd.DataFrame, variaveis=config.VARIAVEIS_ANALISE
) -> pd.DataFrame:
    """Outliers 1,5×IQR com jogo, data, adversário e valor."""
    linhas = []
    for time, grupo in df.groupby("time", observed=True):
        for variavel in variaveis:
            flags, _q1, _q3, lim_inf, lim_sup = _iqr_serie(grupo[variavel])
            for _, registro in grupo.loc[flags].iterrows():
                valor = registro[variavel]
                superior = valor > lim_sup
                linhas.append({
                    "time": str(time),
                    "variavel": variavel,
                    "data_jogo": pd.Timestamp(registro["data_jogo"]).strftime("%Y-%m-%d"),
                    "adversario": str(registro["adversario"]),
                    "em_casa": "casa" if registro["em_casa"] else "fora",
                    "valor": float(valor),
                    "lado": "superior" if superior else "inferior",
                    "limite": lim_sup if superior else lim_inf,
                })
    return pd.DataFrame(linhas)


def classificar_assimetria(g1: float) -> tuple[str, str]:
    if abs(g1) < 0.5:
        return "aproximadamente simétrica", "aproximadamente simétrica"
    direcao = (
        "assimétrica à direita (positiva)" if g1 > 0
        else "assimétrica à esquerda (negativa)"
    )
    intensidade = "moderada" if abs(g1) < 1 else "forte"
    return direcao, intensidade


def tabela_assimetria(
    df: pd.DataFrame, variaveis=config.VARIAVEIS_ANALISE
) -> pd.DataFrame:
    linhas = []
    for time, grupo in df.groupby("time", observed=True):
        for variavel in variaveis:
            serie = grupo[variavel]
            g1 = float(stats.skew(serie, bias=False))
            desvio = serie.std(ddof=config.DDOF)
            pearson2 = (
                float(3 * (serie.mean() - serie.median()) / desvio) if desvio else np.nan
            )
            q1, q2, q3 = (float(v) for v in serie.quantile([0.25, 0.5, 0.75]))
            bowley = (q3 + q1 - 2 * q2) / (q3 - q1) if q3 > q1 else np.nan
            direcao, intensidade = classificar_assimetria(g1)
            linhas.append({
                "time": str(time),
                "variavel": variavel,
                "g1_fisher_pearson": g1,
                "pearson_2": pearson2,
                "bowley": bowley,
                "direcao": direcao,
                "intensidade": intensidade,
                "media": float(serie.mean()),
                "mediana": float(serie.median()),
                "representante": "mediana" if abs(g1) >= 0.5 else "média",
            })
    return pd.DataFrame(linhas)


def classificar_cv(cv: float) -> str:
    if cv < 15:
        return "baixa dispersão (homogêneo)"
    if cv < 30:
        return "média dispersão"
    return "alta dispersão (heterogêneo)"


def tabela_cv(
    df: pd.DataFrame, variaveis=config.VARIAVEIS_ANALISE
) -> pd.DataFrame:
    linhas = []
    for time, grupo in df.groupby("time", observed=True):
        for variavel in variaveis:
            serie = grupo[variavel]
            media = float(serie.mean())
            desvio = float(serie.std(ddof=config.DDOF))
            cv = 100 * desvio / media if media else np.nan
            q1, q2, q3 = (float(v) for v in serie.quantile([0.25, 0.5, 0.75]))
            linhas.append({
                "time": str(time),
                "variavel": variavel,
                "media": media,
                "desvio_padrao": desvio,
                "cv_pct": cv,
                "cv_robusto_pct": 100 * (q3 - q1) / q2 if q2 else np.nan,
                "classificacao": classificar_cv(cv) if pd.notna(cv) else "indefinido",
                "media_pequena": media < 10,
                "valido": bool(serie.min() >= 0 and media > 0),
            })
    return pd.DataFrame(linhas)


def tabela_iqr(
    df: pd.DataFrame, variaveis=config.VARIAVEIS_ANALISE
) -> pd.DataFrame:
    linhas = []
    for time, grupo in df.groupby("time", observed=True):
        for variavel in variaveis:
            serie = grupo[variavel]
            flags, q1, q3, lim_inf, lim_sup = _iqr_serie(serie)
            amplitude = float(serie.max() - serie.min())
            iqr = q3 - q1
            desvio = float(serie.std(ddof=config.DDOF))
            linhas.append({
                "time": str(time),
                "variavel": variavel,
                "q1": q1,
                "q3": q3,
                "iqr": iqr,
                "amplitude": amplitude,
                "razao_amp_iqr": amplitude / iqr if iqr else np.nan,
                "desvio_padrao": desvio,
                "razao_dp_iqr": desvio / iqr if iqr else np.nan,
                "limite_inf": lim_inf,
                "limite_sup": lim_sup,
                "n_outliers": int(flags.sum()),
            })
    return pd.DataFrame(linhas)


def quadro_resumo(tab: pd.DataFrame, valor: str) -> pd.DataFrame:
    """Linhas = variáveis, colunas = times."""
    quadro = tab.pivot(index="variavel", columns="time", values=valor)
    quadro = quadro.reindex(list(config.VARIAVEIS_ANALISE))
    quadro.index = [ROTULOS[v] for v in quadro.index]
    return quadro


def z_score_times(
    df: pd.DataFrame, variaveis=config.VARIAVEIS_ANALISE
) -> pd.DataFrame:
    """Z-score da média de cada time vs. a liga (30 times)."""
    medias = df.groupby("time", observed=True)[list(variaveis)].mean()
    return (medias - medias.mean()) / medias.std(ddof=config.DDOF)


def _filtrar_times(df: pd.DataFrame, times: tuple[str, ...]) -> pd.DataFrame:
    recorte = df[df["time"].astype(str).isin(times)].copy()
    if hasattr(recorte["time"], "cat"):
        recorte["time"] = recorte["time"].cat.remove_unused_categories()
    return recorte


def analisar(
    df: pd.DataFrame,
    times=config.TIMES_GRUPO,
    variaveis=config.VARIAVEIS_ANALISE,
) -> dict:
    """Calcula as tabelas descritivas para o recorte de times."""
    grupo = _filtrar_times(df, tuple(times))
    medidas_tab = tabela_medidas(grupo, variaveis)
    assimetria_tab = tabela_assimetria(grupo, variaveis)
    cv_tab = tabela_cv(grupo, variaveis)
    iqr_tab = tabela_iqr(grupo, variaveis)
    return {
        "medidas": medidas_tab,
        "assimetria": assimetria_tab,
        "cv": cv_tab,
        "iqr": iqr_tab,
        "lista_outliers": lista_outliers(grupo, variaveis),
        "quadro_assimetria": quadro_resumo(assimetria_tab, "g1_fisher_pearson"),
        "quadro_cv": quadro_resumo(cv_tab, "cv_pct"),
        "quadro_iqr": quadro_resumo(iqr_tab, "iqr"),
        "zscore_liga": z_score_times(df, variaveis).loc[list(times)],
        "parametros": {
            "k_iqr": config.K_IQR,
            "ddof": config.DDOF,
            "quartis": config.METODO_QUARTIS,
            "assimetria": "Fisher-Pearson ajustado (scipy.stats.skew, bias=False)",
            "cv": "100 · s / média (s amostral)",
            "unidade": UNIDADE,
            "times": list(times),
            "variaveis": list(variaveis),
        },
        "rotulos": ROTULOS,
    }


if __name__ == "__main__":
    from dashboards.prep.cleaning import calcular_tratamento

    resultado = analisar(calcular_tratamento()["tratado"])
    print("Medidas:")
    print(resultado["medidas"].drop(columns=["outliers_inf", "outliers_sup"]).to_string(index=False))
    print("\nAssimetria:")
    print(resultado["assimetria"].to_string(index=False))
    print("\nCV:")
    print(resultado["cv"].to_string(index=False))
    print("\nIQR:")
    print(resultado["iqr"].to_string(index=False))
