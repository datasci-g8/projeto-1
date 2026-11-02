import warnings

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression, LogisticRegression

import config

MECANISMOS = ("MCAR", "MAR", "MNAR")
TESTES = ("little", "jamshidian_jalal", "listing_schlittgen", "fairclough")

ROTULOS_TESTES = {
    "little": "Little (teste MCAR)",
    "jamshidian_jalal": "Jamshidian–Jalal",
    "listing_schlittgen": "Listing e Schlittgen",
    "fairclough": "Regressão logística (Fairclough)",
}

NOME_ORIGINAL = {novo: original for original, novo in config.RENOMEAR.items()}
VARIAVEIS_ORIGINAIS = [NOME_ORIGINAL[v] for v in config.VARIAVEIS_ANALISE]

REJEITA_MCAR = "rejeita MCAR"
NAO_REJEITA_MCAR = "não rejeita MCAR"
NAO_APLICAVEL = "não aplicável: não há ausentes (ou padrões) para comparar"

CONCLUSAO_SEM_AUSENTES = (
    "A base não tem valores ausentes: não há mecanismo de ausência a identificar, "
    "nenhuma imputação é necessária e os testes de MCAR não se aplicam "
    "(não existe grupo com falta para comparar)."
)
CONCLUSAO_MCAR_REJEITADO = (
    "MCAR rejeitado por {testes}: a ausência está associada a valores observados, "
    "compatível com MAR. MNAR não pode ser descartado nem confirmado só com os "
    "dados observados."
)
CONCLUSAO_MCAR_NAO_REJEITADO = (
    "Nenhum teste rejeitou MCAR: não há evidência de que a ausência dependa dos "
    "valores observados. Isso não prova MCAR, e MNAR não é testável."
)


def contar_ausentes(df: pd.DataFrame) -> pd.DataFrame:
    ausentes = df.isna().sum()
    percentual = ausentes / max(len(df), 1) * 100
    return pd.DataFrame({
        "coluna": ausentes.index,
        "ausentes": ausentes.to_numpy().astype(int),
        "percentual": percentual.round(2).to_numpy(),
    })


def contar_por_time(df: pd.DataFrame, coluna_time: str = "time") -> pd.DataFrame:
    linhas = []
    for time, jogos_do_time in df.groupby(coluna_time, observed=True):
        ausentes = jogos_do_time.isna().sum()
        linhas.append({
            "time": str(time),
            "linhas": len(jogos_do_time),
            "ausentes": int(ausentes.sum()),
            "colunas_com_ausentes": {c: int(n) for c, n in ausentes.items() if n > 0},
        })
    return pd.DataFrame(linhas)


def padroes_ausencia(df: pd.DataFrame) -> pd.DataFrame:
    colunas_ausentes_por_linha = df.isna().apply(lambda linha: tuple(linha.index[linha]), axis=1)
    frequencia = colunas_ausentes_por_linha.value_counts()
    return pd.DataFrame({
        "colunas_ausentes": [list(colunas) for colunas in frequencia.index],
        "linhas": frequencia.to_numpy().astype(int),
    })


def _chance_crescente_com(valores: pd.Series, proporcao_media: float) -> np.ndarray:
    posicao_relativa = valores.rank(pct=True).to_numpy()
    return np.clip(2 * proporcao_media * posicao_relativa, 0, 1)


def _chance_de_faltar(df, mecanismo, coluna, causa, proporcao) -> np.ndarray:
    if mecanismo == "MCAR":
        return np.full(len(df), proporcao)
    if mecanismo == "MAR":
        return _chance_crescente_com(df[causa], proporcao)
    if mecanismo == "MNAR":
        return _chance_crescente_com(df[coluna], proporcao)
    raise ValueError(f"Mecanismo desconhecido: {mecanismo}")


def simular_ausencia(
    df: pd.DataFrame,
    mecanismo: str,
    coluna: str = config.COLUNA_ALVO_AUSENCIA,
    causa: str = config.COLUNA_CAUSA_MAR,
    proporcao: float = config.PROPORCAO_AUSENTE,
    semente: int = config.SEMENTE,
) -> pd.DataFrame:
    chance = _chance_de_faltar(df, mecanismo, coluna, causa, proporcao)
    sorteio = np.random.default_rng(semente).random(len(df))
    com_ausencia = df.copy()
    com_ausencia.loc[sorteio < chance, coluna] = np.nan
    return com_ausencia


def _resultado(estatistica, gl, p_valor, alpha: float = config.ALPHA_TESTES, **detalhes) -> dict:
    if p_valor is None:
        conclusao = NAO_APLICAVEL
    elif p_valor < alpha:
        conclusao = REJEITA_MCAR
    else:
        conclusao = NAO_REJEITA_MCAR
    return {
        "estatistica": None if estatistica is None else round(float(estatistica), 4),
        "gl": gl,
        "p_valor": None if p_valor is None else float(p_valor),
        "conclusao": conclusao,
        **detalhes,
    }


def _nao_aplicavel(**detalhes) -> dict:
    return _resultado(None, 0, None, **detalhes)


def _numericas(df: pd.DataFrame) -> pd.DataFrame:
    return df.select_dtypes("number")


def _colunas_com_ausentes(dados: pd.DataFrame) -> pd.Index:
    return dados.columns[dados.isna().any()]


def _padrao_de_cada_linha(dados: pd.DataFrame) -> pd.Series:
    return dados.isna().apply(tuple, axis=1)


def _bonferroni(menor_p_valor: float, quantidade_de_testes: int) -> float:
    return min(1.0, menor_p_valor * quantidade_de_testes)


def _padronizar(df: pd.DataFrame) -> pd.DataFrame:
    return (df - df.mean()) / df.std(ddof=config.DDOF)


def _completar_pela_esperanca_condicional(bloco, observadas, mu, sigma):
    faltantes = ~observadas
    completo = bloco.copy()
    variancia_nao_explicada = np.zeros_like(sigma)
    if not observadas.any():
        completo[:] = mu
        return completo, sigma.copy()
    if faltantes.any():
        regressao = sigma[np.ix_(faltantes, observadas)] @ np.linalg.pinv(sigma[np.ix_(observadas, observadas)])
        completo[:, faltantes] = mu[faltantes] + (bloco[:, observadas] - mu[observadas]) @ regressao.T
        variancia_nao_explicada[np.ix_(faltantes, faltantes)] = (
            sigma[np.ix_(faltantes, faltantes)] - regressao @ sigma[np.ix_(observadas, faltantes)]
        )
    return completo, variancia_nao_explicada


def _iteracao_em(X, padroes, padrao_da_linha, mu, sigma):
    n, p = X.shape
    soma = np.zeros(p)
    soma_dos_produtos = np.zeros((p, p))
    for indice, observadas in enumerate(padroes):
        bloco = X[padrao_da_linha == indice]
        completo, variancia_nao_explicada = _completar_pela_esperanca_condicional(bloco, observadas, mu, sigma)
        soma += completo.sum(axis=0)
        soma_dos_produtos += completo.T @ completo + len(bloco) * variancia_nao_explicada
    nova_media = soma / n
    nova_covariancia = soma_dos_produtos / n - np.outer(nova_media, nova_media)
    return nova_media, nova_covariancia


def _mudou_menos_que(tolerancia, *pares) -> bool:
    return all(np.abs(novo - antigo).max() < tolerancia for novo, antigo in pares)


def estimar_em(X: np.ndarray, iteracoes: int = 200, tolerancia: float = 1e-8) -> tuple[np.ndarray, np.ndarray]:
    padroes, padrao_da_linha = np.unique(~np.isnan(X), axis=0, return_inverse=True)
    padrao_da_linha = padrao_da_linha.ravel()
    mu = np.nanmean(X, axis=0)
    sigma = np.diag(np.nanvar(X, axis=0))
    for _ in range(iteracoes):
        nova_media, nova_covariancia = _iteracao_em(X, padroes, padrao_da_linha, mu, sigma)
        estabilizou = _mudou_menos_que(tolerancia, (nova_media, mu), (nova_covariancia, sigma))
        mu, sigma = nova_media, nova_covariancia
        if estabilizou:
            break
    return mu, sigma


def _mahalanobis_ao_quadrado(diferenca: np.ndarray, covariancia: np.ndarray) -> float:
    return float(diferenca @ np.linalg.pinv(covariancia) @ diferenca)


def teste_little(df: pd.DataFrame) -> dict:
    dados = _numericas(df)
    padroes = _padrao_de_cada_linha(dados)
    total_de_padroes = int(padroes.nunique())
    total_de_colunas = dados.shape[1]
    colunas_observadas_por_padrao = [total_de_colunas - sum(padrao) for padrao in padroes.unique()]
    graus_de_liberdade = sum(colunas_observadas_por_padrao) - total_de_colunas
    if graus_de_liberdade <= 0:
        return _nao_aplicavel(padroes=total_de_padroes)

    mu, sigma = estimar_em(dados.to_numpy(float))
    d2 = 0.0
    for padrao, linhas in dados.groupby(padroes):
        observadas = ~np.array(padrao)
        if not observadas.any():
            continue
        media_do_padrao = linhas.to_numpy(float)[:, observadas].mean(axis=0)
        diferenca = media_do_padrao - mu[observadas]
        d2 += len(linhas) * _mahalanobis_ao_quadrado(diferenca, sigma[np.ix_(observadas, observadas)])

    p_valor = stats.chi2.sf(d2, graus_de_liberdade)
    return _resultado(d2, graus_de_liberdade, p_valor, padroes=total_de_padroes)


def _ajustar_logistica_sem_penalizacao(X: np.ndarray, y: np.ndarray) -> LogisticRegression:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return LogisticRegression(C=np.inf, max_iter=2000).fit(X, y)


def _erros_padrao(X: np.ndarray, probabilidade: np.ndarray) -> np.ndarray:
    com_intercepto = np.column_stack([np.ones(len(X)), X])
    pesos = probabilidade * (1 - probabilidade)
    informacao_de_fisher = com_intercepto.T @ (com_intercepto * pesos[:, None])
    return np.sqrt(np.diag(np.linalg.pinv(informacao_de_fisher)))


def _log_verossimilhanca(y: np.ndarray, probabilidade: np.ndarray) -> float:
    return float(np.sum(y * np.log(probabilidade) + (1 - y) * np.log(1 - probabilidade)))


def _logistica(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    modelo = _ajustar_logistica_sem_penalizacao(X, y)
    probabilidade = np.clip(modelo.predict_proba(X)[:, 1], 1e-12, 1 - 1e-12)
    coeficientes = np.concatenate([modelo.intercept_, modelo.coef_.ravel()])
    return coeficientes, _erros_padrao(X, probabilidade), _log_verossimilhanca(y, probabilidade)


def _log_verossimilhanca_so_intercepto(y: np.ndarray) -> float:
    return _log_verossimilhanca(y, np.full(len(y), y.mean()))


def _regressao_da_ausencia(dados: pd.DataFrame, coluna: str) -> dict | None:
    preditoras = dados.drop(columns=coluna).dropna(axis=1, how="any")
    if preditoras.empty:
        return None
    faltou = dados[coluna].isna().astype(int).to_numpy()
    X = _padronizar(preditoras).to_numpy()
    coeficientes, erros, log_verossimilhanca = _logistica(X, faltou)
    razao_de_verossimilhanca = 2 * (log_verossimilhanca - _log_verossimilhanca_so_intercepto(faltou))
    betas, z = coeficientes[1:], coeficientes[1:] / erros[1:]
    return {
        "coluna": coluna,
        "lr": round(razao_de_verossimilhanca, 4),
        "gl": X.shape[1],
        "p_valor": float(stats.chi2.sf(razao_de_verossimilhanca, X.shape[1])),
        "coeficientes": [
            {"variavel": nome, "beta": round(float(beta), 4), "z": round(float(z_beta), 3),
             "p_valor": float(2 * stats.norm.sf(abs(z_beta)))}
            for nome, beta, z_beta in zip(preditoras.columns, betas, z)
        ],
    }


def teste_fairclough(df: pd.DataFrame) -> dict:
    dados = _numericas(df)
    regressoes = [_regressao_da_ausencia(dados, coluna) for coluna in _colunas_com_ausentes(dados)]
    regressoes = [r for r in regressoes if r is not None]
    if not regressoes:
        return _nao_aplicavel(por_coluna=[])
    mais_significativa = min(regressoes, key=lambda r: r["p_valor"])
    p_valor = _bonferroni(mais_significativa["p_valor"], len(regressoes))
    return _resultado(mais_significativa["lr"], mais_significativa["gl"], p_valor, por_coluna=regressoes)


def _comparar_com_e_sem_falta(dados: pd.DataFrame, coluna: str):
    faltou = dados[coluna].isna()
    for outra in dados.columns.drop(coluna):
        com_falta = dados.loc[faltou, outra].dropna()
        sem_falta = dados.loc[~faltou, outra].dropna()
        if len(com_falta) < 2 or len(sem_falta) < 2:
            continue
        u, p_valor = stats.mannwhitneyu(com_falta, sem_falta, alternative="two-sided")
        yield {"coluna_ausente": coluna, "variavel": outra, "u": float(u), "p_valor": float(p_valor)}


def teste_listing_schlittgen(df: pd.DataFrame) -> dict:
    dados = _numericas(df)
    comparacoes = [
        comparacao
        for coluna in _colunas_com_ausentes(dados)
        for comparacao in _comparar_com_e_sem_falta(dados, coluna)
    ]
    if not comparacoes:
        return _nao_aplicavel(comparacoes=[])
    mais_significativa = min(comparacoes, key=lambda c: c["p_valor"])
    p_valor = _bonferroni(mais_significativa["p_valor"], len(comparacoes))
    return _resultado(mais_significativa["u"], None, p_valor, comparacoes=comparacoes)


def _imputar_por_regressao_com_ruido(dados: pd.DataFrame, rng: np.random.Generator, rodadas: int = 5) -> pd.DataFrame:
    faltava = dados.isna()
    imputado = dados.fillna(dados.mean())
    for _ in range(rodadas):
        for coluna in _colunas_com_ausentes(dados):
            preditoras = imputado.drop(columns=coluna)
            observado, ausente = ~faltava[coluna], faltava[coluna]
            regressao = LinearRegression().fit(preditoras[observado], imputado.loc[observado, coluna])
            residuos = imputado.loc[observado, coluna] - regressao.predict(preditoras[observado])
            desvio_residual = residuos.std(ddof=preditoras.shape[1] + 1)
            ruido = rng.normal(0, desvio_residual, int(ausente.sum()))
            imputado.loc[ausente, coluna] = regressao.predict(preditoras[ausente]) + ruido
    return imputado


def _m_de_box(X: np.ndarray, grupos: np.ndarray) -> float:
    rotulos = np.unique(grupos)
    total, quantidade_de_grupos = len(X), len(rotulos)
    soma_log_det = 0.0
    covariancia_combinada = np.zeros((X.shape[1], X.shape[1]))
    for rotulo in rotulos:
        linhas = X[grupos == rotulo]
        covariancia = np.cov(linhas, rowvar=False, ddof=1)
        soma_log_det += (len(linhas) - 1) * np.linalg.slogdet(covariancia)[1]
        covariancia_combinada += (len(linhas) - 1) * covariancia
    covariancia_combinada /= total - quantidade_de_grupos
    return float((total - quantidade_de_grupos) * np.linalg.slogdet(covariancia_combinada)[1] - soma_log_det)


def _padronizar_matriz(X: np.ndarray) -> np.ndarray:
    return (X - X.mean(axis=0)) / X.std(axis=0, ddof=1)


def _p_valor_por_permutacao(X, grupos, observado, rng, permutacoes) -> float:
    permutados = np.array([_m_de_box(X, rng.permutation(grupos)) for _ in range(permutacoes)])
    return (1 + np.sum(permutados >= observado)) / (permutacoes + 1)


def teste_jamshidian_jalal(
    df: pd.DataFrame,
    permutacoes: int = config.PERMUTACOES_JJ,
    semente: int = config.SEMENTE,
) -> dict:
    dados = _numericas(df)
    padroes = _padrao_de_cada_linha(dados)
    padrao_com_covariancia_estimavel = padroes.map(padroes.value_counts()) > dados.shape[1] + 1
    padroes_usados = padroes[padrao_com_covariancia_estimavel]
    if padroes_usados.nunique() < 2:
        return _nao_aplicavel(padroes_usados=int(padroes_usados.nunique()))

    rng = np.random.default_rng(semente)
    imputado = _imputar_por_regressao_com_ruido(dados, rng)[padrao_com_covariancia_estimavel]
    X = _padronizar_matriz(imputado.to_numpy(float))
    grupos = pd.factorize(padroes_usados)[0]
    m_observado = _m_de_box(X, grupos)
    p_valor = _p_valor_por_permutacao(X, grupos, m_observado, rng, permutacoes)
    return _resultado(m_observado, None, p_valor,
                      padroes_usados=int(len(np.unique(grupos))), permutacoes=permutacoes)


def executar_testes(df: pd.DataFrame) -> dict:
    return {
        "little": teste_little(df),
        "jamshidian_jalal": teste_jamshidian_jalal(df),
        "listing_schlittgen": teste_listing_schlittgen(df),
        "fairclough": teste_fairclough(df),
    }


def conclusao_mecanismo(df: pd.DataFrame, testes: dict) -> str:
    if not df.isna().any().any():
        return CONCLUSAO_SEM_AUSENTES
    rejeitaram = [nome for nome, resultado in testes.items() if resultado["conclusao"] == REJEITA_MCAR]
    if rejeitaram:
        return CONCLUSAO_MCAR_REJEITADO.format(testes=", ".join(rejeitaram))
    return CONCLUSAO_MCAR_NAO_REJEITADO


def analisar(df_original: pd.DataFrame) -> dict:
    testes = executar_testes(df_original[VARIAVEIS_ORIGINAIS])
    return {
        "base": {
            "arquivo": config.RAW_CSV.name,
            "linhas": len(df_original),
            "colunas": int(df_original.shape[1]),
        },
        "por_coluna": contar_ausentes(df_original),
        "por_time": contar_por_time(df_original, coluna_time="TEAM_NAME"),
        "padroes": padroes_ausencia(df_original),
        "variaveis_testadas": VARIAVEIS_ORIGINAIS,
        "testes": testes,
        "conclusao": conclusao_mecanismo(df_original, testes),
    }


if __name__ == "__main__":
    from dashboards.prep.loader import carregar_bruto

    resultado = analisar(carregar_bruto())
    base = resultado["base"]
    print(f"{base['arquivo']}: {base['linhas']} linhas x {base['colunas']} colunas")
    print(f"Ausentes: {int(resultado['por_coluna']['ausentes'].sum())}")
    print(resultado["conclusao"])
    print()
    for nome, teste in resultado["testes"].items():
        print(f"{nome:20s} p={teste['p_valor']}  {teste['conclusao']}")
