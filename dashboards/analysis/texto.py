"""Geração das interpretações textuais a partir dos resultados numéricos."""
from __future__ import annotations

import pandas as pd

from dashboards.analysis.descriptive import ROTULOS


def _r(var: str) -> str:
    return ROTULOS[var]


def _f(x, d=2) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def texto_descritiva(tab: pd.DataFrame, var: str) -> list[str]:
    t = tab[tab["variavel"] == var].set_index("time")
    paragrafos = []
    for time, r in t.iterrows():
        paragrafos.append(
            f"<b>{time}</b>: média de {_f(r['media'])} e mediana de {_f(r['mediana'])} "
            f"{_r(var).lower()} por jogo (moda: {r['moda']}). "
            f"Os valores variam de {_f(r['minimo'], 0)} a {_f(r['maximo'], 0)} "
            f"(amplitude {_f(r['amplitude'], 0)}), com desvio padrão de {_f(r['desvio_padrao'])}. "
            f"A metade central dos jogos fica entre Q1 = {_f(r['q1'])} e Q3 = {_f(r['q3'])}. "
            + (
                f"Pela regra 1,5×IQR há {r['n_outliers']} outlier(s): superiores "
                f"{r['outliers_sup'] or '—'}, inferiores {r['outliers_inf'] or '—'}."
                if r["n_outliers"]
                else "Não há outliers pela regra 1,5×IQR: todos os jogos ficam dentro dos limites do boxplot."
            )
        )
    if len(t) > 1:
        maior = t["media"].idxmax()
        menor = t["media"].idxmin()
        disp = t["desvio_padrao"].idxmax()
        paragrafos.append(
            f"Comparando os times, <b>{maior}</b> tem a maior média ({_f(t.loc[maior, 'media'])}) "
            f"e <b>{menor}</b> a menor ({_f(t.loc[menor, 'media'])}); "
            f"a diferença é de {_f(t.loc[maior, 'media'] - t.loc[menor, 'media'])} "
            f"{_r(var).lower()} por jogo. "
            f"<b>{disp}</b> é o time com maior variação jogo a jogo nessa estatística "
            f"(DP = {_f(t.loc[disp, 'desvio_padrao'])})."
        )
    return paragrafos


def texto_assimetria(tab: pd.DataFrame, var: str) -> dict:
    t = tab[tab["variavel"] == var].set_index("time")
    por_time = []
    for time, r in t.iterrows():
        g1 = r["g1_fisher_pearson"]
        if g1 > 0.1:
            rel = "média > mediana, cauda à direita (alguns jogos com valores muito altos)"
        elif g1 < -0.1:
            rel = "média < mediana, cauda à esquerda (alguns jogos com valores muito baixos)"
        else:
            rel = "média ≈ mediana"
        por_time.append(
            f"<b>{time}</b>: g1 = {_f(g1, 3)} → distribuição {r['direcao']}, "
            f"intensidade <b>{r['intensidade']}</b> ({rel}). "
            f"Pearson 2 = {_f(r['pearson_2'], 3)} e Bowley = {_f(r['bowley'], 3)} "
            f"{'concordam no sinal' if (r['pearson_2'] >= 0) == (g1 >= 0) else 'divergem no sinal'}. "
            f"Valor típico melhor representado pela <b>{r['representante']}</b>"
            + (
                ", e transformação logarítmica ou métodos robustos são recomendáveis."
                if abs(g1) >= 1
                else "."
            )
        )
    g = tab.copy()
    g["abs"] = g["g1_fisher_pearson"].abs()
    rank = g.groupby("variavel")["abs"].mean().sort_values(ascending=False)
    mais = [_r(v) for v in rank.index[:2]]
    menos = [_r(v) for v in rank.index[-2:]]
    sinal = g.groupby("variavel")["g1_fisher_pearson"].apply(
        lambda s: "mesmo sinal em todos os times" if (s > 0).all() or (s < 0).all()
        else "sinais diferentes entre times"
    )
    repete = [_r(v) for v, s in sinal.items() if s.startswith("mesmo")]
    geral = (
        f"Entre as sete variáveis, as mais assimétricas são <b>{' e '.join(mais)}</b>; "
        f"as mais simétricas são <b>{' e '.join(menos)}</b>. "
        f"O sinal se repete em todos os times para: "
        f"{', '.join(repete) if repete else 'nenhuma variável'}."
    )
    return {"por_time": por_time, "geral": geral}


def texto_cv(tab: pd.DataFrame, var: str) -> dict:
    t = tab[tab["variavel"] == var].set_index("time")
    por_time = []
    for time, r in t.iterrows():
        aviso = (
            " <i>Atenção: média pequena (&lt; 10) — interprete o CV com cautela.</i>"
            if r["media_pequena"]
            else ""
        )
        por_time.append(
            f"<b>{time}</b>: CV = {_f(r['cv_pct'], 1)}% → {r['classificacao']}. "
            f"CV robusto (IQR/mediana) = {_f(r['cv_robusto_pct'], 1)}%.{aviso}"
        )
    piv = tab.pivot(index="variavel", columns="time", values="cv_pct")
    media_var = piv.mean(axis=1).sort_values()
    estaveis = [_r(v) for v in media_var.index[:2]]
    dispersas = [_r(v) for v in media_var.index[-2:]]
    consistente = {
        v: (piv.loc[v].idxmin(), piv.loc[v].idxmax()) for v in piv.index
    }
    geral = (
        f"Variáveis mais estáveis: <b>{' e '.join(estaveis)}</b>; "
        f"mais dispersas: <b>{' e '.join(dispersas)}</b>. "
        f"O CV compara escalas distintas; o DP bruto não seria comparável entre pontos e tocos."
    )
    if len(t) > 1:
        geral += (
            f" Para <b>{_r(var)}</b>, o time mais regular é <b>{t['cv_pct'].idxmin()}</b> "
            f"e o mais irregular é <b>{t['cv_pct'].idxmax()}</b>."
        )
    return {"por_time": por_time, "geral": geral, "consistente": consistente}


def texto_iqr(tab: pd.DataFrame, var: str) -> dict:
    t = tab[tab["variavel"] == var].set_index("time")
    por_time = []
    for time, r in t.iterrows():
        por_time.append(
            f"<b>{time}</b>: IQR = {_f(r['iqr'])} ({_r(var).lower()} por jogo). "
            f"Amplitude/IQR = {_f(r['razao_amp_iqr'], 1)}; DP/IQR = {_f(r['razao_dp_iqr'], 2)}. "
            f"Limites 1,5×IQR: [{_f(r['limite_inf'])}; {_f(r['limite_sup'])}] → "
            f"{r['n_outliers']} outlier(s)."
        )
    geral = (
        "A regra adotada foi 1,5×IQR, a mesma do boxplot; a lista de outliers coincide com os bigodes."
    )
    if len(t) > 1:
        geral += (
            f" Para <b>{_r(var)}</b>, o time mais concentrado é <b>{t['iqr'].idxmin()}</b> "
            f"e o mais espalhado é <b>{t['iqr'].idxmax()}</b>."
        )
    return {"por_time": por_time, "geral": geral}


def texto_sintese(
    med: pd.DataFrame, ass: pd.DataFrame, cv: pd.DataFrame, _iq: pd.DataFrame
) -> list[str]:
    paragrafos = []
    times = list(med["time"].unique())
    for time in times:
        m = med[med["time"] == time].set_index("variavel")
        c = cv[cv["time"] == time].set_index("variavel")
        a = ass[ass["time"] == time].set_index("variavel")
        paragrafos.append(
            f"<b>{time}</b> — média de {_f(m.loc['pontos', 'media'], 1)} pontos por jogo. "
            f"CV mais baixo: {_r(c['cv_pct'].idxmin())}; mais alto: {_r(c['cv_pct'].idxmax())}. "
            f"Mais assimétrica: {_r(a['g1_fisher_pearson'].abs().idxmax())}. "
            f"Outliers (1,5×IQR) nas sete variáveis: {int(m['n_outliers'].sum())}."
        )
    if len(times) > 1:
        cvm = cv.groupby("time")["cv_pct"].mean()
        paragrafos.append(
            f"Time mais consistente (média dos CVs): <b>{cvm.idxmin()}</b> "
            f"({_f(cvm.min(), 1)}%)."
        )
    paragrafos.append(
        "Contagens baixas (tocos, roubos, cestas de 3) tendem a assimetria positiva e CV alto: "
        "prefira mediana e IQR. Outliers refletem jogos reais, não erros de registro."
    )
    return paragrafos
