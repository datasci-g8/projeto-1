import warnings
from typing import Callable

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import DBSCAN
from sklearn.neighbors import LocalOutlierFactor, NearestNeighbors

import config

Metodo = Callable[[pd.DataFrame], pd.Series]


def padronizar(X: pd.DataFrame) -> pd.DataFrame:
    return (X - X.mean()) / X.std(ddof=config.DDOF).replace(0, 1)


def _por_coluna(X: pd.DataFrame, regra: Callable[[pd.Series], pd.Series]) -> pd.Series:
    return pd.concat([regra(X[c]) for c in X.columns], axis=1).any(axis=1)


def limite_tukey(scores: np.ndarray, k: float = config.K_IQR) -> float:
    q1, q3 = np.percentile(scores, [25, 75])
    return float(q3 + k * (q3 - q1))


def zscore(X: pd.DataFrame, limiar: float = config.Z_LIMIAR) -> pd.Series:
    def regra(serie: pd.Series) -> pd.Series:
        desvio = serie.std(ddof=config.DDOF)
        if not desvio:
            return pd.Series(False, index=serie.index)
        return ((serie - serie.mean()) / desvio).abs() > limiar
    return _por_coluna(X, regra)


def limites_iqr(serie: pd.Series, k: float = config.K_IQR) -> tuple[float, float]:
    q1, q3 = serie.quantile([0.25, 0.75])
    return float(q1 - k * (q3 - q1)), float(q3 + k * (q3 - q1))


def iqr(X: pd.DataFrame, k: float = config.K_IQR) -> pd.Series:
    def regra(serie: pd.Series) -> pd.Series:
        inf, sup = limites_iqr(serie, k)
        return (serie < inf) | (serie > sup)
    return _por_coluna(X, regra)


def grubbs_critico(n: int, alpha: float = config.ALPHA_GRUBBS) -> float:
    t = stats.t.ppf(1 - alpha / (2 * n), n - 2)
    return float((n - 1) / np.sqrt(n) * np.sqrt(t**2 / (n - 2 + t**2)))


def grubbs_serie(serie: pd.Series, alpha: float = config.ALPHA_GRUBBS) -> pd.Series:
    restante = serie.dropna().astype(float)
    marcas = pd.Series(False, index=serie.index)
    while len(restante) >= 3:
        desvio = restante.std(ddof=1)
        if not desvio:
            break
        desvios = (restante - restante.mean()).abs()
        if desvios.max() / desvio <= grubbs_critico(len(restante), alpha):
            break
        indice = desvios.idxmax()
        marcas[indice] = True
        restante = restante.drop(indice)
    return marcas


def grubbs(X: pd.DataFrame, alpha: float = config.ALPHA_GRUBBS) -> pd.Series:
    return _por_coluna(X, lambda s: grubbs_serie(s, alpha))


def normalidade(serie: pd.Series, alpha: float = config.ALPHA_TESTES) -> dict:
    estatistica, p = stats.shapiro(serie.dropna())
    return {"shapiro_w": round(float(estatistica), 4), "p_valor": float(p), "normal": bool(p >= alpha)}


def ecod_scores(X: pd.DataFrame) -> np.ndarray:
    valores = X.to_numpy(float)
    n = len(valores)
    o_esq = -np.log(stats.rankdata(valores, method="max", axis=0) / n)
    o_dir = -np.log(stats.rankdata(-valores, method="max", axis=0) / n)
    o_auto = np.where(stats.skew(valores, axis=0) < 0, o_esq, o_dir)
    return np.max([o_esq.sum(1), o_dir.sum(1), o_auto.sum(1)], axis=0)


def ecod(X: pd.DataFrame) -> pd.Series:
    scores = ecod_scores(X)
    return pd.Series(scores > limite_tukey(scores), index=X.index)


def knn_scores(X: pd.DataFrame, k: int = config.K_VIZINHOS_KNN) -> np.ndarray:
    Z = padronizar(X).to_numpy(float)
    k = min(k, len(Z) - 1)
    distancias, _ = NearestNeighbors(n_neighbors=k + 1).fit(Z).kneighbors(Z)
    return distancias[:, k]


def knn(X: pd.DataFrame, k: int = config.K_VIZINHOS_KNN) -> pd.Series:
    scores = knn_scores(X, k)
    return pd.Series(scores > limite_tukey(scores), index=X.index)


def lof_scores(X: pd.DataFrame, k: int = config.K_VIZINHOS_LOF) -> np.ndarray:
    Z = padronizar(X).to_numpy(float)
    modelo = LocalOutlierFactor(n_neighbors=min(k, len(Z) - 1))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        modelo.fit(Z)
    return -modelo.negative_outlier_factor_


def lof(X: pd.DataFrame, k: int = config.K_VIZINHOS_LOF) -> pd.Series:
    return pd.Series(lof_scores(X, k) > config.LOF_LIMIAR, index=X.index)


def min_amostras_dbscan(dimensoes: int) -> int:
    return max(config.DBSCAN_MIN_AMOSTRAS_POR_DIM * dimensoes, config.DBSCAN_MIN_AMOSTRAS_MINIMO)


def k_distancias(X: pd.DataFrame, min_amostras: int | None = None) -> tuple[np.ndarray, float]:
    """Curva de k-distância ordenada"""
    Z = padronizar(X).to_numpy(float)
    m = min_amostras or min_amostras_dbscan(Z.shape[1])
    distancias, _ = NearestNeighbors(n_neighbors=m).fit(Z).kneighbors(Z)
    curva = np.sort(distancias[:, -1])
    amplitude = curva[-1] - curva[0]
    y = (curva - curva[0]) / amplitude if amplitude else np.zeros_like(curva)
    eps = float(curva[int(np.argmax(np.abs(y - np.linspace(0, 1, len(curva)))))])
    if eps <= 0:
        positivos = curva[curva > 0]
        eps = float(positivos[0]) if len(positivos) else 1e-6
    return curva, eps


def dbscan(X: pd.DataFrame, min_amostras: int | None = None) -> pd.Series:
    Z = padronizar(X)
    m = min_amostras or min_amostras_dbscan(Z.shape[1])
    _, eps = k_distancias(X, m)
    rotulos = DBSCAN(eps=eps, min_samples=m).fit_predict(Z.to_numpy(float))
    return pd.Series(rotulos == -1, index=X.index)


METODOS: dict[str, Metodo] = {
    "zscore": zscore,
    "iqr": iqr,
    "grubbs": grubbs,
    "ecod": ecod,
    "knn": knn,
    "lof": lof,
    "dbscan": dbscan,
}
UNIVARIADOS = ("zscore", "iqr", "grubbs")
MULTIVARIADOS = ("ecod", "knn", "lof", "dbscan")


def consenso(X: pd.DataFrame) -> pd.Series:
    """Quantos métodos multivariados marcam cada jogo."""
    return pd.concat([METODOS[m](X) for m in MULTIVARIADOS], axis=1).sum(axis=1).astype(int)


def _dados_time(df: pd.DataFrame, time: str, variaveis) -> pd.DataFrame:
    return df.loc[df["time"] == time, list(variaveis)].dropna()


def marcar_por_coluna(df: pd.DataFrame, metodo: str, times=config.TIMES_GRUPO,
                      variaveis=config.VARIAVEIS_ANALISE) -> pd.DataFrame:
    linhas = []
    for time in times:
        dados = _dados_time(df, time, variaveis)
        for coluna in variaveis:
            mascara = METODOS[metodo](dados[[coluna]])
            for indice in mascara.index[mascara]:
                linhas.append({"indice": indice, "time": time, "coluna": coluna,
                               "valor": float(dados.at[indice, coluna])})
    return pd.DataFrame(linhas, columns=["indice", "time", "coluna", "valor"])


def marcar_multivariado(df: pd.DataFrame, metodo: str, times=config.TIMES_GRUPO,
                        variaveis=config.VARIAVEIS_ANALISE) -> pd.DataFrame:
    linhas = []
    for time in times:
        dados = _dados_time(df, time, variaveis)
        mascara = METODOS[metodo](dados)
        votos = consenso(dados)
        linhas.extend({"indice": i, "time": time, "n_metodos": int(votos[i])}
                      for i in mascara.index[mascara])
    return pd.DataFrame(linhas, columns=["indice", "time", "n_metodos"])


def sensibilidade(df: pd.DataFrame, times=config.TIMES_GRUPO,
                  variaveis=config.VARIAVEIS_ANALISE) -> pd.DataFrame:
    """Contagem 1D de K-NN, LOF e DBSCAN para vários valores do parâmetro."""
    chamadas = {
        "knn": lambda X, v: knn(X, k=v),
        "lof": lambda X, v: lof(X, k=v),
        "dbscan": lambda X, v: dbscan(X, min_amostras=v),
    }
    linhas = []
    for time in times:
        dados = _dados_time(df, time, variaveis)
        for coluna in variaveis:
            for metodo, valores in config.SENSIBILIDADE.items():
                contagens = [int(chamadas[metodo](dados[[coluna]], v).sum()) for v in valores]
                linhas.append({"time": time, "coluna": coluna, "metodo": metodo,
                               "parametros": list(valores), "outliers": contagens,
                               "amplitude": max(contagens) - min(contagens)})
    return pd.DataFrame(linhas)


def univariado_liga(df: pd.DataFrame, variaveis=config.VARIAVEIS_ANALISE) -> pd.DataFrame:
    """z-score, IQR e Grubbs por coluna para os 30 times, como referência da liga."""
    linhas = []
    for time in sorted(df["time"].astype(str).unique()):
        dados = _dados_time(df, time, variaveis)
        for coluna in variaveis:
            inf, sup = limites_iqr(dados[coluna])
            linha = {"time": time, "coluna": coluna, "n": len(dados),
                     "limite_inf": round(inf, 2), "limite_sup": round(sup, 2)}
            linha.update({m: int(METODOS[m](dados[[coluna]]).sum()) for m in UNIVARIADOS})
            linhas.append(linha)
    return pd.DataFrame(linhas)


def analisar(df: pd.DataFrame, times=config.TIMES_GRUPO,
             variaveis=config.VARIAVEIS_ANALISE) -> dict:
    por_coluna, multivariado, normal, dbscan_params = [], [], [], []
    for time in times:
        dados = _dados_time(df, time, variaveis)
        for coluna in variaveis:
            linha = {"time": time, "coluna": coluna, "n": len(dados)}
            linha.update({nome: int(metodo(dados[[coluna]]).sum()) for nome, metodo in METODOS.items()})
            por_coluna.append(linha)
            normal.append({"time": time, "coluna": coluna, **normalidade(dados[coluna])})

        votos = consenso(dados)
        linha = {"time": time, "n": len(dados)}
        linha.update({nome: int(METODOS[nome](dados).sum()) for nome in MULTIVARIADOS})
        linha["consenso_2+"] = int((votos >= 2).sum())
        multivariado.append(linha)

        m = min_amostras_dbscan(len(variaveis))
        curva, eps = k_distancias(dados, m)
        dbscan_params.append({"time": time, "eps": round(eps, 4), "min_samples": m,
                              "k_distancias": [round(float(v), 4) for v in curva]})

    return {
        "por_coluna": pd.DataFrame(por_coluna),
        "sensibilidade": sensibilidade(df, times, variaveis),
        "multivariado": pd.DataFrame(multivariado),
        "univariado_liga": univariado_liga(df, variaveis),
        "normalidade": pd.DataFrame(normal),
        "dbscan": dbscan_params,
        "parametros": {
            "z_limiar": config.Z_LIMIAR,
            "k_iqr": config.K_IQR,
            "alpha_grubbs": config.ALPHA_GRUBBS,
            "k_knn": config.K_VIZINHOS_KNN,
            "k_lof": config.K_VIZINHOS_LOF,
            "limiar_scores": f"Q3 + {config.K_IQR}·IQR dos scores (ECOD, K-NN); LOF > {config.LOF_LIMIAR}",
            "min_samples_dbscan": "max(2 × dimensões, 4); eps no cotovelo da k-distância",
            "consenso": "jogos marcados por 2 ou mais dos 4 métodos multivariados",
            "padronizacao": "z-score com desvio amostral, por time",
            "quartis": config.METODO_QUARTIS,
        },
    }


if __name__ == "__main__":
    from dashboards.prep.cleaning import calcular_tratamento

    resultado = analisar(calcular_tratamento()["tratado"])
    print("Outliers por coluna:")
    print(resultado["por_coluna"].to_string(index=False))
    print("\nJogos anômalos (7 variáveis juntas):")
    print(resultado["multivariado"].to_string(index=False))
    print("\nNormalidade (Shapiro-Wilk):")
    print(resultado["normalidade"].to_string(index=False))
