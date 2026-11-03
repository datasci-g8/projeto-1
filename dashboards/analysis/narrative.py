"""Geração das interpretações textuais a partir dos resultados numéricos."""
from __future__ import annotations

import pandas as pd

from dashboards.analysis.descriptive import ROTULOS


def _r(var: str) -> str:
    return ROTULOS[var]


def _f(x, d=2) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def _tex(body: str) -> str:
    return rf"\({body}\)"


def _arrow() -> str:
    return _tex(r"\Rightarrow")


_REGRA_IQR = _tex(r"1{,}5 \times \mathrm{IQR}")


def descriptive(tab: pd.DataFrame, var: str) -> list[str]:
    t = tab[tab["variavel"] == var].set_index("time")
    paragrafos = []
    for time, r in t.iterrows():
        paragrafos.append(
            f"<strong>{time}</strong>: média de {_f(r['media'])} e mediana de {_f(r['mediana'])} "
            f"{_r(var).lower()} por jogo (moda: {r['moda']}). "
            f"Os valores variam de {_f(r['minimo'], 0)} a {_f(r['maximo'], 0)} "
            f"(amplitude {_f(r['amplitude'], 0)}), com desvio padrão {_tex('s')} = {_f(r['desvio_padrao'])}. "
            f"A metade central dos jogos fica entre {_tex('Q_1')} = {_f(r['q1'])} e {_tex('Q_3')} = {_f(r['q3'])}. "
            + (
                f"Pela regra {_REGRA_IQR} há {r['n_outliers']} outlier(s): superiores "
                f"{r['outliers_sup'] or 'n/d'}, inferiores {r['outliers_inf'] or 'n/d'}."
                if r["n_outliers"]
                else f"Não há outliers pela regra {_REGRA_IQR}: todos os jogos ficam dentro dos limites do boxplot."
            )
        )
    if len(t) > 1:
        maior = t["media"].idxmax()
        menor = t["media"].idxmin()
        disp = t["desvio_padrao"].idxmax()
        paragrafos.append(
            f"Comparando os times, <strong>{maior}</strong> tem a maior média ({_f(t.loc[maior, 'media'])}) "
            f"e <strong>{menor}</strong> a menor ({_f(t.loc[menor, 'media'])}); "
            f"a diferença é de {_f(t.loc[maior, 'media'] - t.loc[menor, 'media'])} "
            f"{_r(var).lower()} por jogo. "
            f"<strong>{disp}</strong> é o time com maior variação jogo a jogo nessa estatística "
            f"({_tex('s')} = {_f(t.loc[disp, 'desvio_padrao'])})."
        )
    return paragrafos


def skewness(tab: pd.DataFrame, var: str) -> dict:
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
        g1_tex = _tex("G_1 = " + _f(g1, 3))
        por_time.append(
            f"<strong>{time}</strong>: {g1_tex} {_arrow()} distribuição {r['direcao']}, "
            f"intensidade <strong>{r['intensidade']}</strong> ({rel}). "
            f"Pearson 2 = {_f(r['pearson_2'], 3)} e Bowley = {_f(r['bowley'], 3)} "
            f"{'concordam no sinal' if (r['pearson_2'] >= 0) == (g1 >= 0) else 'divergem no sinal'}. "
            f"Valor típico melhor representado pela <strong>{r['representante']}</strong>"
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
        f"Entre as sete variáveis, as mais assimétricas são <strong>{' e '.join(mais)}</strong>; "
        f"as mais simétricas são <strong>{' e '.join(menos)}</strong>. "
        f"O sinal se repete em todos os times para: "
        f"{', '.join(repete) if repete else 'nenhuma variável'}."
    )
    return {"por_time": por_time, "geral": geral}


def cv(tab: pd.DataFrame, var: str) -> dict:
    t = tab[tab["variavel"] == var].set_index("time")
    por_time = []
    for time, r in t.iterrows():
        aviso = (
            ' <span class="cautela">Atenção: média pequena (&lt; 10). Interprete o CV com cautela.</span>'
            if r["media_pequena"]
            else ""
        )
        cv_tex = _tex("\\mathrm{CV} = " + _f(r["cv_pct"], 1) + "\\%")
        cv_rob_tex = _tex(
            "\\mathrm{CV}_{\\mathrm{rob}} = " + _f(r["cv_robusto_pct"], 1) + "\\%"
        )
        por_time.append(
            f"<strong>{time}</strong>: {cv_tex} {_arrow()} "
            f"{r['classificacao']}. "
            f"{cv_rob_tex} (IQR/mediana).{aviso}"
        )
    piv = tab.pivot(index="variavel", columns="time", values="cv_pct")
    media_var = piv.mean(axis=1).sort_values()
    estaveis = [_r(v) for v in media_var.index[:2]]
    dispersas = [_r(v) for v in media_var.index[-2:]]
    consistente = {
        v: (piv.loc[v].idxmin(), piv.loc[v].idxmax()) for v in piv.index
    }
    geral = (
        f"Variáveis mais estáveis: <strong>{' e '.join(estaveis)}</strong>; "
        f"mais dispersas: <strong>{' e '.join(dispersas)}</strong>. "
        f"O CV compara escalas distintas; o DP bruto não seria comparável entre pontos e tocos."
    )
    if len(t) > 1:
        geral += (
            f" Para <strong>{_r(var)}</strong>, o time mais regular é <strong>{t['cv_pct'].idxmin()}</strong> "
            f"e o mais irregular é <strong>{t['cv_pct'].idxmax()}</strong>."
        )
    return {"por_time": por_time, "geral": geral, "consistente": consistente}


def iqr(tab: pd.DataFrame, var: str) -> dict:
    t = tab[tab["variavel"] == var].set_index("time")
    por_time = []
    for time, r in t.iterrows():
        iqr_tex = _tex("\\mathrm{IQR} = " + _f(r["iqr"]))
        por_time.append(
            f"<strong>{time}</strong>: {iqr_tex} "
            f"({_r(var).lower()} por jogo). "
            f"Amplitude/IQR = {_f(r['razao_amp_iqr'], 1)}; DP/IQR = {_f(r['razao_dp_iqr'], 2)}. "
            f"Limites {_REGRA_IQR}: "
            f"[{_f(r['limite_inf'])}; {_f(r['limite_sup'])}] {_arrow()} "
            f"{r['n_outliers']} outlier(s)."
        )
    geral = (
        f"A regra adotada foi {_REGRA_IQR}, a mesma do boxplot; "
        "a lista de outliers coincide com os bigodes."
    )
    if len(t) > 1:
        geral += (
            f" Para <strong>{_r(var)}</strong>, o time mais concentrado é <strong>{t['iqr'].idxmin()}</strong> "
            f"e o mais espalhado é <strong>{t['iqr'].idxmax()}</strong>."
        )
    return {"por_time": por_time, "geral": geral}


def synthesis(
    med: pd.DataFrame, ass: pd.DataFrame, cv: pd.DataFrame, _iq: pd.DataFrame
) -> list[str]:
    paragrafos = []
    times = list(med["time"].unique())
    for time in times:
        m = med[med["time"] == time].set_index("variavel")
        c = cv[cv["time"] == time].set_index("variavel")
        a = ass[ass["time"] == time].set_index("variavel")
        paragrafos.append(
            f"<strong>{time}</strong>: média de {_f(m.loc['pontos', 'media'], 1)} pontos por jogo. "
            f"CV mais baixo: {_r(c['cv_pct'].idxmin())}; mais alto: {_r(c['cv_pct'].idxmax())}. "
            f"Mais assimétrica: {_r(a['g1_fisher_pearson'].abs().idxmax())}. "
            f"Outliers ({_REGRA_IQR}) nas sete variáveis: {int(m['n_outliers'].sum())}."
        )
    if len(times) > 1:
        cvm = cv.groupby("time")["cv_pct"].mean()
        paragrafos.append(
            f"Time mais consistente (média dos CVs): <strong>{cvm.idxmin()}</strong> "
            f"({_f(cvm.min(), 1)}%)."
        )
    paragrafos.append(
        "Contagens baixas (tocos, roubos, cestas de 3) tendem a assimetria positiva e CV alto: "
        "prefira mediana e IQR. Outliers refletem jogos reais, não erros de registro."
    )
    return paragrafos
