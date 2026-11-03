"""Rotas HTML do relatório (templates Jinja e gráficos Plotly)."""
from __future__ import annotations

from functools import lru_cache

import pandas as pd
from flask import Flask, redirect, render_template, request

import config
from dashboards.analysis import descriptive, missing, narrative, outliers, plots
from dashboards.api.quality import resultado_atual
from dashboards.prep.loader import carregar_bruto, tabela_dicionario
from dashboards.web import report_tables as rt

TEORIA_OUTLIERS = {
    "Z-score": (
        "Padroniza cada valor: z = (x − x̄)/s. Valores com |z| acima do limiar "
        f"({config.Z_LIMIAR}) são marcados."
    ),
    "IQR / Boxplot": (
        f"Outliers fora de Q1 − {config.K_IQR}·IQR e Q3 + {config.K_IQR}·IQR "
        f"({config.METODO_QUARTIS})."
    ),
    "Grubbs": "Teste iterativo de um outlier por vez, assumindo normalidade.",
    "ECOD": "Detecção por caudas da distribuição empírica em cada dimensão.",
    "K-NN": f"Distância ao {config.K_VIZINHOS_KNN}º vizinho no espaço padronizado.",
    "DBSCAN": "Pontos de baixa densidade (ruído) no espaço multivariado.",
    "LOF": f"Fator de outlier local (k = {config.K_VIZINHOS_LOF}).",
}


def _dataframe_tratado() -> pd.DataFrame:
    return resultado_atual()["tratado"]


def _todos_times(df: pd.DataFrame) -> list[str]:
    if hasattr(df["time"], "cat"):
        return list(df["time"].cat.categories)
    return sorted(df["time"].astype(str).unique())


def selection(df: pd.DataFrame) -> tuple[tuple[str, ...], str]:
    todos = _todos_times(df)
    times = [t for t in request.args.getlist("times") if t in todos] or list(config.TIMES_GRUPO)
    var = request.args.get("var", "pontos")
    if var not in config.VARIAVEIS_ANALISE:
        var = "pontos"
    return tuple(times), var


@lru_cache(maxsize=64)
def _resultados(times: tuple[str, ...]) -> dict:
    df = _dataframe_tratado()
    grupo = df[df["time"].astype(str).isin(times)].copy()
    if hasattr(grupo["time"], "cat"):
        grupo["time"] = grupo["time"].cat.remove_unused_categories()
    analise_out = outliers.analisar(df, times=times)
    return {
        "df": grupo,
        "medidas": descriptive.tabela_medidas(grupo),
        "lista_outliers": descriptive.lista_outliers(grupo),
        "assimetria": descriptive.tabela_assimetria(grupo),
        "cv": descriptive.tabela_cv(grupo),
        "iqr": descriptive.tabela_iqr(grupo),
        "uni": analise_out["por_coluna"],
        "multi": analise_out["multivariado"],
        "multi_det": _consenso_multivariado(df, times),
    }


_COLUNAS_CONSENSO = ("time", "indice", "n_metodos")


def _consenso_multivariado(df: pd.DataFrame, times: tuple[str, ...]) -> pd.DataFrame:
    linhas = []
    for time in times:
        dados = outliers._dados_time(df, time, config.VARIAVEIS_ANALISE)
        votos = outliers.consenso(dados)
        for indice in votos.index[votos >= 2]:
            linhas.append({
                "time": time,
                "indice": int(indice),
                "n_metodos": int(votos[indice]),
            })
    if not linhas:
        return pd.DataFrame(columns=_COLUNAS_CONSENSO)
    return pd.DataFrame(linhas, columns=_COLUNAS_CONSENSO)


def _redirect_legacy(path_en: str):
    qs = request.query_string.decode()
    dest = path_en + (f"?{qs}" if qs else "")
    return redirect(dest, code=301)


def register_panel(app: Flask) -> None:
    df_global = _dataframe_tratado()
    todos_times = _todos_times(df_global)
    zscores = descriptive.z_score_times(df_global)

    @app.context_processor
    def contexto():
        times, var = selection(df_global)
        return dict(
            todos_times=todos_times,
            times_sel=list(times),
            var_sel=var,
            variaveis=config.VARIAVEIS_ANALISE,
            rotulos=descriptive.ROTULOS,
            grupo=config.TIMES_GRUPO,
        )

    @app.get("/")
    def index():
        times, _ = selection(df_global)
        amostra = df_global[df_global["time"].astype(str).isin(times)].head(8)
        n_por_time = (
            df_global["time"].astype(str).value_counts().rename_axis("time").reset_index(name="jogos")
        )
        return render_template(
            "index.html",
            shape=df_global.shape,
            dicionario=rt.tab_relatorio(tabela_dicionario(), classes="tabela tabela-texto"),
            excluidas=config.COLUNAS_EXCLUIDAS_MODELAGEM,
            amostra=rt.tab_amostra(amostra),
            n_por_time=rt.tab_relatorio(n_por_time),
            datas=(df_global["data_jogo"].min().date(), df_global["data_jogo"].max().date()),
        )

    @app.get("/quality")
    def quality_view():
        miss = missing.analisar(carregar_bruto())
        qual = resultado_atual()
        resumo = qual["resumo"]
        depois = resumo["depois"]
        antes = resumo["antes"]
        dup = resumo["duplicatas_removidas"]
        regras = resumo["regras"]
        violacoes = [r for r in regras if r["violacoes"] > 0]
        issues_df = qual["issues"]
        testes = [
            (missing.ROTULOS_TESTES.get(chave, chave), resultado)
            for chave, resultado in miss["testes"].items()
        ]
        return render_template(
            "quality.html",
            ausentes=rt.tab_relatorio(miss["por_coluna"]),
            resumo_qual=depois,
            resumo_antes=antes,
            dup_removidas=dup,
            n_regras=len(regras),
            violacoes_regras=violacoes,
            issues_tabela=rt.tab_relatorio(issues_df.head(50), classes="tabela tabela-texto")
            if not issues_df.empty
            else None,
            testes=testes,
            conclusao_ausentes=miss["conclusao"],
            inconsistencias=depois["issues"],
        )

    @app.get("/qualidade")
    def qualidade_legacy():
        return _redirect_legacy("/quality")

    @app.get("/outliers")
    def outliers_view():
        times, var = selection(df_global)
        r = _resultados(times)
        uni = r["uni"]
        consenso = r["multi_det"]
        if not consenso.empty:
            consenso = consenso.sort_values(
                ["time", "n_metodos"], ascending=[True, False]
            )
        lista = r["lista_outliers"][r["lista_outliers"]["variavel"] == var]
        return render_template(
            "outliers.html",
            teoria=TEORIA_OUTLIERS,
            uni=rt.tab_relatorio(uni),
            multi=rt.tab_relatorio(r["multi"]),
            consenso=rt.tab_relatorio(consenso),
            lista=rt.tab_lista_outliers(lista, omit_var=True),
        )

    @app.get("/descriptive")
    def descriptive_view():
        times, var = selection(df_global)
        r = _resultados(times)
        m = r["medidas"]
        mv = m[m["variavel"] == var].drop(columns=["variavel"])
        zs = zscores.loc[list(times)].reset_index()
        return render_template(
            "descriptive.html",
            medidas_var=rt.tab_relatorio(mv, omit_var=True),
            medidas_todas=rt.tab_relatorio(
                m.drop(columns=["outliers_inf", "outliers_sup"]),
            ),
            boxplot=plots.boxplot(r["df"], var),
            barras=plots.barras_comparativas(r["df"], config.VARIAVEIS_ANALISE, zscores),
            serie=plots.serie_temporal(r["df"], var),
            interpretacao=narrative.descriptive(m, var),
            lista=rt.tab_lista_outliers(
                r["lista_outliers"][r["lista_outliers"]["variavel"] == var],
                omit_var=True,
            ),
            zs=rt.tab_relatorio(zs, dec=2, classes="tabela tabela-full"),
        )

    @app.get("/descritiva")
    def descritiva_legacy():
        return _redirect_legacy("/descriptive")

    @app.get("/skewness")
    def skewness_view():
        times, var = selection(df_global)
        r = _resultados(times)
        a = r["assimetria"]
        txt = narrative.skewness(a, var)
        return render_template(
            "skewness.html",
            tabela=rt.tab_relatorio(a[a["variavel"] == var], dec=3, omit_var=True),
            tabela_todas=rt.tab_relatorio(a.drop(columns=["media", "mediana"]), dec=3),
            quadro=rt.tab_quadro(descriptive.quadro_resumo(a, "g1_fisher_pearson"), dec=3),
            hist=plots.histograma_kde(r["df"], var),
            boxplot=plots.boxplot(r["df"], var),
            txt=txt,
        )

    @app.get("/assimetria")
    def assimetria_legacy():
        return _redirect_legacy("/skewness")

    @app.get("/cv")
    def cv_view():
        times, var = selection(df_global)
        r = _resultados(times)
        c = r["cv"]
        return render_template(
            "cv.html",
            tabela=rt.tab_relatorio(c[c["variavel"] == var], omit_var=True),
            tabela_todas=rt.tab_relatorio(c),
            quadro=rt.tab_quadro(descriptive.quadro_resumo(c, "cv_pct")),
            quadro_rob=rt.tab_quadro(descriptive.quadro_resumo(c, "cv_robusto_pct")),
            quadro_ass=rt.tab_quadro(
                descriptive.quadro_resumo(r["assimetria"], "g1_fisher_pearson"), dec=3
            ),
            txt=narrative.cv(c, var),
        )

    @app.get("/iqr")
    def iqr_view():
        times, var = selection(df_global)
        r = _resultados(times)
        i = r["iqr"]
        return render_template(
            "iqr.html",
            tabela=rt.tab_relatorio(i[i["variavel"] == var], omit_var=True),
            tabela_todas=rt.tab_relatorio(i),
            quadro=rt.tab_quadro(descriptive.quadro_resumo(i, "iqr")),
            quadro_cv=rt.tab_quadro(descriptive.quadro_resumo(r["cv"], "cv_pct")),
            quadro_ass=rt.tab_quadro(
                descriptive.quadro_resumo(r["assimetria"], "g1_fisher_pearson"), dec=3
            ),
            boxplot=plots.boxplot(r["df"], var),
            txt=narrative.iqr(i, var),
            lista=rt.tab_lista_outliers(
                r["lista_outliers"][r["lista_outliers"]["variavel"] == var],
                omit_var=True,
            ),
        )

    @app.get("/synthesis")
    def synthesis_view():
        times, _ = selection(df_global)
        r = _resultados(times)
        return render_template(
            "synthesis.html",
            paragrafos=narrative.synthesis(r["medidas"], r["assimetria"], r["cv"], r["iqr"]),
            quadro_cv=rt.tab_quadro(descriptive.quadro_resumo(r["cv"], "cv_pct")),
            quadro_iqr=rt.tab_quadro(descriptive.quadro_resumo(r["iqr"], "iqr")),
            quadro_ass=rt.tab_quadro(
                descriptive.quadro_resumo(r["assimetria"], "g1_fisher_pearson"), dec=3
            ),
            quadro_out=rt.tab_quadro(descriptive.quadro_resumo(r["medidas"], "n_outliers"), dec=0),
        )

    @app.get("/sintese")
    def sintese_legacy():
        return _redirect_legacy("/synthesis")
