"""Rotas do painel web (templates + Plotly)."""
from __future__ import annotations

from functools import lru_cache

import pandas as pd
from flask import Flask, render_template, request

import config
from dashboards.analysis import descriptive, missing, outliers, plots, texto
from dashboards.api.quality import resultado_atual
from dashboards.prep.loader import carregar_bruto, tabela_dicionario

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


def tab(df: pd.DataFrame, index: bool = False, dec: int = 2) -> str:
    return df.to_html(
        classes="tabela",
        index=index,
        float_format=lambda x: f"{x:.{dec}f}",
        border=0,
        na_rep="—",
    )


def _todos_times(df: pd.DataFrame) -> list[str]:
    if hasattr(df["time"], "cat"):
        return list(df["time"].cat.categories)
    return sorted(df["time"].astype(str).unique())


def selecao(df: pd.DataFrame) -> tuple[tuple[str, ...], str]:
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
    return pd.DataFrame(linhas)


def registrar_painel(app: Flask) -> None:
    df_global = _dataframe_tratado()
    todos_times = _todos_times(df_global)
    zscores = descriptive.z_score_times(df_global)

    @app.context_processor
    def contexto():
        times, var = selecao(df_global)
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
        times, _ = selecao(df_global)
        tipos = pd.DataFrame({
            "coluna": df_global.columns,
            "tipo_pandas": df_global.dtypes.astype(str).values,
        })
        amostra = df_global[df_global["time"].astype(str).isin(times)].head(8)
        n_por_time = (
            df_global["time"].astype(str).value_counts().rename_axis("time").reset_index(name="jogos")
        )
        return render_template(
            "index.html",
            shape=df_global.shape,
            dicionario=tab(tabela_dicionario()),
            tipos=tab(tipos),
            excluidas=config.COLUNAS_EXCLUIDAS_MODELAGEM,
            amostra=tab(amostra),
            n_por_time=tab(n_por_time),
            datas=(df_global["data_jogo"].min().date(), df_global["data_jogo"].max().date()),
        )

    @app.get("/qualidade")
    def qualidade_view():
        miss = missing.analisar(carregar_bruto())
        qual = resultado_atual()
        depois = qual["resumo"]["depois"]
        testes = miss["testes"]
        return render_template(
            "qualidade.html",
            ausentes=tab(miss["por_coluna"]),
            resumo_qual=depois,
            testes=testes,
            conclusao_ausentes=miss["conclusao"],
            inconsistencias=depois["issues"],
        )

    @app.get("/outliers")
    def outliers_view():
        times, var = selecao(df_global)
        r = _resultados(times)
        uni = r["uni"]
        consenso = r["multi_det"].sort_values(["time", "n_metodos"], ascending=[True, False])
        lista = r["lista_outliers"][r["lista_outliers"]["variavel"] == var]
        return render_template(
            "outliers.html",
            teoria=TEORIA_OUTLIERS,
            uni=tab(uni),
            multi=tab(r["multi"]),
            consenso=tab(consenso),
            lista=tab(lista),
        )

    @app.get("/descritiva")
    def descritiva_view():
        times, var = selecao(df_global)
        r = _resultados(times)
        m = r["medidas"]
        mv = m[m["variavel"] == var].drop(columns=["variavel"])
        zs = zscores.loc[list(times)].reset_index()
        return render_template(
            "descritiva.html",
            medidas_var=tab(mv),
            medidas_todas=tab(m.drop(columns=["outliers_inf", "outliers_sup"])),
            boxplot=plots.boxplot(r["df"], var),
            barras=plots.barras_comparativas(r["df"], config.VARIAVEIS_ANALISE, zscores),
            serie=plots.serie_temporal(r["df"], var),
            interpretacao=texto.texto_descritiva(m, var),
            lista=tab(r["lista_outliers"][r["lista_outliers"]["variavel"] == var]),
            zs=tab(zs, dec=2),
        )

    @app.get("/assimetria")
    def assimetria_view():
        times, var = selecao(df_global)
        r = _resultados(times)
        a = r["assimetria"]
        txt = texto.texto_assimetria(a, var)
        return render_template(
            "assimetria.html",
            tabela=tab(a[a["variavel"] == var].drop(columns=["variavel"]), dec=3),
            tabela_todas=tab(a.drop(columns=["media", "mediana"]), dec=3),
            quadro=tab(descriptive.quadro_resumo(a, "g1_fisher_pearson"), index=True, dec=3),
            hist=plots.histograma_kde(r["df"], var),
            boxplot=plots.boxplot(r["df"], var),
            txt=txt,
        )

    @app.get("/cv")
    def cv_view():
        times, var = selecao(df_global)
        r = _resultados(times)
        c = r["cv"]
        return render_template(
            "cv.html",
            tabela=tab(c[c["variavel"] == var].drop(columns=["variavel"])),
            tabela_todas=tab(c),
            quadro=tab(descriptive.quadro_resumo(c, "cv_pct"), index=True),
            quadro_rob=tab(descriptive.quadro_resumo(c, "cv_robusto_pct"), index=True),
            quadro_ass=tab(
                descriptive.quadro_resumo(r["assimetria"], "g1_fisher_pearson"), index=True, dec=3
            ),
            txt=texto.texto_cv(c, var),
        )

    @app.get("/iqr")
    def iqr_view():
        times, var = selecao(df_global)
        r = _resultados(times)
        i = r["iqr"]
        return render_template(
            "iqr.html",
            tabela=tab(i[i["variavel"] == var].drop(columns=["variavel"])),
            tabela_todas=tab(i),
            quadro=tab(descriptive.quadro_resumo(i, "iqr"), index=True),
            quadro_cv=tab(descriptive.quadro_resumo(r["cv"], "cv_pct"), index=True),
            quadro_ass=tab(
                descriptive.quadro_resumo(r["assimetria"], "g1_fisher_pearson"), index=True, dec=3
            ),
            boxplot=plots.boxplot(r["df"], var),
            txt=texto.texto_iqr(i, var),
            lista=tab(r["lista_outliers"][r["lista_outliers"]["variavel"] == var]),
        )

    @app.get("/sintese")
    def sintese_view():
        times, _ = selecao(df_global)
        r = _resultados(times)
        return render_template(
            "sintese.html",
            paragrafos=texto.texto_sintese(r["medidas"], r["assimetria"], r["cv"], r["iqr"]),
            quadro_cv=tab(descriptive.quadro_resumo(r["cv"], "cv_pct"), index=True),
            quadro_iqr=tab(descriptive.quadro_resumo(r["iqr"], "iqr"), index=True),
            quadro_ass=tab(
                descriptive.quadro_resumo(r["assimetria"], "g1_fisher_pearson"), index=True, dec=3
            ),
            quadro_out=tab(descriptive.quadro_resumo(r["medidas"], "n_outliers"), index=True, dec=0),
        )
