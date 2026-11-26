"""Data app | Pobreza e desigualdades no Brasil (Parte 2 do projeto ICD).

Reúne os resultados exportados pelas partes 1 e 3 (pasta resultados/).
O app só lê esses arquivos: não recalcula taxas nacionais nem retreina modelos.

Execução: streamlit run app.py
"""
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

RES = Path(__file__).parent / "resultados"
ARQUIVOS = {
    "dados": "dados_tratados.csv",
    "perfis": "perfis_clusters.csv",
    "metricas": "metricas_modelos.csv",
    "resumo": "resumo_modelagem.json",
    "kpis": "indicadores.json",
}
URL_IBGE = (
    "https://ftp.ibge.gov.br/Estatisticas_de_Genero/"
    "Indicadores_sociais_das_mulheres_no_Brasil_3a_edicao/xls/1_Empoderamento_Economico_xls.zip"
)
MEDIDAS = {
    "Pobreza (< US$ 6,85/dia)": ("pobreza", "cv_pobreza"),
    "Extrema pobreza (< US$ 2,15/dia)": ("extrema", "cv_extrema"),
}
COR_SEXO = {"Total": "#555555", "Homem": "#226b88", "Mulher": "#d1495b"}
COR_CLUSTER = {"Menor pobreza": "#2a9d8f", "Maior pobreza": "#e76f51", "Ruído (fora dos grupos)": "#9a9a9a"}

st.set_page_config(page_title="Pobreza e desigualdades no Brasil", page_icon="📊", layout="wide")


# ----------------------------------------------------------------------------
# Carregamento dos dados
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner="Carregando resultados das partes 1 e 3...")
def carregar():
    dados = pd.read_csv(RES / ARQUIVOS["dados"], encoding="utf-8-sig")
    perfis = pd.read_csv(RES / ARQUIVOS["perfis"], encoding="utf-8-sig")
    metricas = pd.read_csv(RES / ARQUIVOS["metricas"])
    resumo = json.loads((RES / ARQUIVOS["resumo"]).read_text(encoding="utf-8"))
    kpis = json.loads((RES / ARQUIVOS["kpis"]).read_text(encoding="utf-8"))
    return dados, perfis, metricas, resumo, kpis


faltando = [a for a in ARQUIVOS.values() if not (RES / a).exists()]
if faltando:
    st.error(
        "Arquivos ausentes em `resultados/`: " + ", ".join(faltando)
        + ". Execute os notebooks das partes 1 e 3 (ver README.md) e reinicie o app."
    )
    st.stop()

dados, perfis, metricas, resumo, kpis_exportados = carregar()
ANOS = sorted(int(a) for a in dados["ano"].unique())


# ----------------------------------------------------------------------------
# Funções de cálculo
# ----------------------------------------------------------------------------
def taxa(ano, segmento, sexo, col):
    """Taxa publicada pelo IBGE para um ano, segmento e sexo (nunca média de categorias)."""
    linha = dados[(dados.ano == ano) & (dados.segmento == segmento) & (dados.sexo == sexo)]
    return float(linha[col].iloc[0])


def indicadores(ano):
    """KPIs do ano: taxas oficiais e diferenças (taxa A - taxa B) em pontos percentuais."""
    return {
        "pobreza": taxa(ano, "Total", "Total", "pobreza"),
        "extrema": taxa(ano, "Total", "Total", "extrema"),
        "gap_sexo": taxa(ano, "Total", "Mulher", "pobreza") - taxa(ano, "Total", "Homem", "pobreza"),
        "gap_raca": taxa(ano, "Pretos ou pardos", "Total", "pobreza") - taxa(ano, "Brancos", "Total", "pobreza"),
        "gap_rural": taxa(ano, "Rural", "Total", "pobreza") - taxa(ano, "Urbana", "Total", "pobreza"),
        "crianca": taxa(ano, "0 a 14 anos", "Total", "pobreza"),
    }


def rotular_clusters(df, col):
    """Nomes legíveis para os rótulos numéricos (arbitrários) dos clusters, ordenados pela pobreza média."""
    medias = df[df[col] != -1].groupby(col)["pobreza"].mean().sort_values()
    n = len(medias)
    if n == 2:
        nomes = dict(zip(medias.index, ["Menor pobreza", "Maior pobreza"]))
    else:
        nomes = {c: f"Grupo {i + 1} de {n}" for i, c in enumerate(medias.index)}
    nomes[-1] = "Ruído (fora dos grupos)"
    return df[col].map(nomes)


def pp(valor):
    return f"{valor:.2f} p.p."


# ----------------------------------------------------------------------------
# Barra lateral: filtros globais
# ----------------------------------------------------------------------------
st.sidebar.header("Filtros")
ano = st.sidebar.select_slider(
    "Ano de referência",
    options=ANOS,
    value=max(ANOS),
    help="Muda os KPIs (e a variação em relação ao ano anterior), as barras por recorte e a tabela de dados. "
    "Não altera a aba de perfis, que usa apenas 2022.",
)
medida_nome = st.sidebar.radio(
    "Medida de pobreza",
    list(MEDIDAS),
    help="Troca a linha de pobreza usada nos gráficos de evolução e de recortes. Os KPIs têm definição fixa.",
)
col_taxa, col_cv = MEDIDAS[medida_nome]
grupos = [g for g in dados["grupo"].unique() if g != "Geral"]
dimensao = st.sidebar.selectbox(
    "Dimensão demográfica",
    grupos,
    help="Escolhe o recorte (cor ou raça, idade, ocupação ou domicílio) da aba 'Recortes e sexo'.",
)
st.sidebar.caption(
    "Dados históricos do IBGE (PNAD Contínua). A taxa de 2022 não descreve a situação atual. "
    "A fonte não tem recorte estadual: não há estimativas para São Paulo."
)

# ----------------------------------------------------------------------------
# Cabeçalho
# ----------------------------------------------------------------------------
st.title("Pobreza e desigualdades no Brasil")
st.markdown(
    "Painel das partes 1 e 3 do projeto: indicadores nacionais do IBGE (2012 a 2022), comparações por sexo, "
    "cor ou raça, idade, ocupação e domicílio, e uma segmentação exploratória de perfis (K-means e DBSCAN). "
    "Use a barra lateral para filtrar."
)

aba_geral, aba_recortes, aba_perfis, aba_dados = st.tabs(
    ["Visão geral", "Recortes e sexo", "Perfis (clusters)", "Dados e fonte"]
)

# ----------------------------------------------------------------------------
# Aba 1: visão geral
# ----------------------------------------------------------------------------
with aba_geral:
    st.subheader(f"Indicadores nacionais | Brasil, {ano}")
    atual = indicadores(ano)
    anterior = indicadores(ano - 1) if ano - 1 in ANOS else None

    def delta(chave):
        if anterior is None:
            return None
        return f"{atual[chave] - anterior[chave]:+.2f} p.p. vs. {ano - 1}"

    c1, c2, c3 = st.columns(3)
    c1.metric("Pobreza nacional", f"{atual['pobreza']:.2f}%", delta("pobreza"), delta_color="inverse",
              help="% da população com renda domiciliar per capita abaixo de US$ 6,85/dia (PPC 2017).")
    c2.metric("Extrema pobreza nacional", f"{atual['extrema']:.2f}%", delta("extrema"), delta_color="inverse",
              help="% da população com renda domiciliar per capita abaixo de US$ 2,15/dia (PPC 2017).")
    c3.metric("Gap mulheres − homens", pp(atual["gap_sexo"]), delta("gap_sexo"), delta_color="inverse",
              help="Taxa de pobreza das mulheres menos a dos homens, em pontos percentuais.")
    c4, c5, c6 = st.columns(3)
    c4.metric("Gap pretos/pardos − brancos", pp(atual["gap_raca"]), delta("gap_raca"), delta_color="inverse",
              help="Diferença entre as taxas de pobreza dos dois grupos, em pontos percentuais.")
    c5.metric("Gap rural − urbana", pp(atual["gap_rural"]), delta("gap_rural"), delta_color="inverse",
              help="Diferença entre as taxas de pobreza dos dois domicílios, em pontos percentuais.")
    c6.metric("Pobreza de 0 a 14 anos", f"{atual['crianca']:.2f}%", delta("crianca"), delta_color="inverse",
              help="Denominador: população de 0 a 14 anos, não a população total.")
    st.caption(
        "Gap é uma diferença entre taxas, em pontos percentuais (p.p.), e não um percentual. "
        "A variação ao lado de cada valor compara com o ano anterior; seta verde = queda."
    )

    st.subheader(f"Evolução 2012–2022 | {medida_nome}")
    serie = dados[(dados.segmento == "Total")].sort_values("ano")
    fig = px.line(
        serie, x="ano", y=col_taxa, color="sexo", markers=True, color_discrete_map=COR_SEXO,
        labels={"ano": "Ano", col_taxa: "População (%)", "sexo": "Sexo"},
    )
    fig.add_vline(x=ano, line_dash="dot", line_color="#888", annotation_text=str(ano))
    fig.update_xaxes(dtick=1)
    fig.update_yaxes(rangemode="tozero")
    fig.update_layout(hovermode="x unified", margin=dict(t=30))
    st.plotly_chart(fig, width="stretch")

    seg = dados[(dados.ano == ano) & (dados.sexo == "Total") & (dados.segmento != "Total")].sort_values(col_taxa)
    mais, menos = seg.iloc[-1], seg.iloc[0]
    st.markdown(
        f"**Leitura de {ano} ({medida_nome.split(' (')[0].lower()}):** a maior taxa entre os recortes é a de "
        f"**{mais.segmento}** ({mais[col_taxa]:.1f}%) e a menor é a de **{menos.segmento}** ({menos[col_taxa]:.1f}%). "
        "São associações descritivas entre recortes sobrepostos, sem relação causal."
    )

# ----------------------------------------------------------------------------
# Aba 2: recortes e sexo
# ----------------------------------------------------------------------------
with aba_recortes:
    st.subheader(f"{dimensao} | {medida_nome}, {ano}")
    opcoes = list(dados.loc[dados.grupo == dimensao, "segmento"].unique())
    escolhidos = st.multiselect(
        "Segmentos exibidos", opcoes, default=opcoes,
        help="Restringe as barras, a tabela de diferenças e as linhas de evolução desta aba aos segmentos marcados.",
    )
    if not escolhidos:
        st.info("Selecione ao menos um segmento.")
    else:
        mostrar_ic = st.toggle(
            "Mostrar intervalo de confiança aproximado (95%)", value=False,
            help="Barra de erro = ±1,96 × taxa × CV. O CV publicado pelo IBGE mede o erro amostral de cada taxa.",
        )
        base = dados[
            (dados.ano == ano) & (dados.grupo == dimensao) & dados.segmento.isin(escolhidos)
            & dados.sexo.isin(["Homem", "Mulher"])
        ].copy()
        base["erro_95"] = 1.96 * base[col_taxa] * base[col_cv] / 100

        esq, dir_ = st.columns([3, 2])
        with esq:
            fig = px.bar(
                base, x="segmento", y=col_taxa, color="sexo", barmode="group", color_discrete_map=COR_SEXO,
                error_y="erro_95" if mostrar_ic else None,
                labels={"segmento": "", col_taxa: "População do recorte (%)", "sexo": "Sexo"},
                hover_data={"erro_95": ":.2f"} if mostrar_ic else None,
            )
            fig.update_yaxes(rangemode="tozero")
            fig.update_layout(margin=dict(t=30))
            st.plotly_chart(fig, width="stretch")
        with dir_:
            tab = base.pivot(index="segmento", columns="sexo", values=col_taxa).reindex(escolhidos)
            tab["Gap M − H (p.p.)"] = tab["Mulher"] - tab["Homem"]
            st.markdown("**Taxas e diferença entre mulheres e homens**")
            st.dataframe(
                tab.round(2), width="stretch",
                column_config={"Homem": "Homem (%)", "Mulher": "Mulher (%)"},
            )
            menor_fem = tab.index[tab["Gap M − H (p.p.)"] < 0].tolist()
            if menor_fem:
                st.caption("A taxa feminina é menor em: " + ", ".join(menor_fem) + ".")
            else:
                st.caption("A taxa feminina é maior ou igual em todos os segmentos exibidos.")

        st.subheader("Evolução por segmento")
        sexo_serie = st.radio("Sexo", ["Total", "Homem", "Mulher"], horizontal=True,
                              help="Seleciona qual série de sexo aparece no gráfico de linhas abaixo.")
        ev = dados[(dados.grupo == dimensao) & dados.segmento.isin(escolhidos) & (dados.sexo == sexo_serie)]
        fig = px.line(
            ev.sort_values("ano"), x="ano", y=col_taxa, color="segmento", markers=True,
            labels={"ano": "Ano", col_taxa: "População do recorte (%)", "segmento": "Segmento"},
        )
        fig.add_vline(x=ano, line_dash="dot", line_color="#888")
        fig.update_xaxes(dtick=1)
        fig.update_yaxes(rangemode="tozero")
        fig.update_layout(hovermode="x unified", margin=dict(t=30))
        st.plotly_chart(fig, width="stretch")
        st.caption(
            "Os recortes se sobrepõem (uma mulher aparece em idade, raça e domicílio) e a tabela não informa o tamanho "
            "da amostra. Não some nem calcule médias simples das taxas para obter a taxa nacional."
        )

# ----------------------------------------------------------------------------
# Aba 3: perfis (clusters)
# ----------------------------------------------------------------------------
with aba_perfis:
    st.subheader("Segmentação exploratória de 20 perfis (2022)")
    st.markdown(
        "Cada ponto é um perfil agregado (segmento × sexo), descrito por duas taxas padronizadas. "
        "Os modelos **não preveem** pobreza: agrupam perfis parecidos (aprendizado não supervisionado). "
        "O filtro de ano da barra lateral não se aplica aqui."
    )
    modelo_escolhido = st.radio(
        "Algoritmo", ["K-means", "DBSCAN"], horizontal=True,
        help="K-means agrupa por centroides e atribui todos os perfis a um grupo. "
        "DBSCAN agrupa por densidade e pode marcar perfis como ruído.",
    )
    col_cluster, nome_modelo = (
        ("cluster_kmeans", resumo["kmeans"]) if modelo_escolhido == "K-means" else ("cluster_dbscan", resumo["dbscan"])
    )
    p = perfis.copy()
    p["Grupo"] = rotular_clusters(p, col_cluster)
    p["Perfil"] = p["segmento"] + " / " + p["sexo"]

    linha = metricas[metricas.modelo == nome_modelo].iloc[0]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Silhouette", f"{linha.silhouette:.3f}", help="Maior é melhor. Para DBSCAN, exclui os pontos de ruído.")
    m2.metric("Davies-Bouldin", f"{linha.davies_bouldin:.3f}", help="Menor é melhor.")
    m3.metric("Cobertura", f"{linha.cobertura:.0%}", help="Parcela dos 20 perfis atribuída a algum grupo.")
    m4.metric("Perfis como ruído", f"{int(linha.ruido)}", help="Perfil sem vizinhança densa suficiente. Não é erro.")
    st.caption(f"Configuração selecionada pelo maior silhouette: **{nome_modelo}**.")

    esq, dir_ = st.columns([3, 2])
    with esq:
        rotulos = st.toggle("Mostrar nome dos perfis no gráfico", value=False)
        fig = px.scatter(
            p, x="extrema", y="pobreza", color="Grupo", color_discrete_map=COR_CLUSTER,
            text="Perfil" if rotulos else None, hover_name="Perfil",
            hover_data={"extrema": ":.2f", "pobreza": ":.2f", "Grupo": False},
            labels={"extrema": "Extrema pobreza (%)", "pobreza": "Pobreza (%)"},
        )
        fig.update_traces(marker=dict(size=13, line=dict(width=1, color="white")), textposition="top center")
        fig.update_layout(margin=dict(t=30), legend_title_text="")
        st.plotly_chart(fig, width="stretch")
    with dir_:
        resumo_grupos = (
            p.groupby("Grupo")
            .agg(Perfis=("Perfil", "size"), **{"Extrema média (%)": ("extrema", "mean"), "Pobreza média (%)": ("pobreza", "mean")})
            .round(2)
        )
        st.markdown("**Resumo dos grupos** (média simples dos perfis, não de pessoas)")
        st.dataframe(resumo_grupos, width="stretch")
        for grupo, g in p.groupby("Grupo"):
            with st.expander(f"{grupo} ({len(g)} perfis)"):
                st.write("; ".join(g["Perfil"]))

    with st.expander("Estabilidade e comparação de todas as configurações testadas"):
        s = resumo["sensibilidade"]
        e1, e2, e3 = st.columns(3)
        e1.metric("ARI entre sementes (mín.)", f"{s['ari_min_sementes']:.2f}",
                  help="K-means com 20 sementes. 1 = partições idênticas.")
        e2.metric("ARI entre sementes (média)", f"{s['ari_medio_sementes']:.2f}")
        e3.metric("ARI sem padronização", f"{s['ari_sem_padronizacao']:.2f}",
                  help="Concordância com o K-means sem padronizar as taxas: o resultado depende da escala.")
        tabela = metricas.copy()
        tabela.insert(0, "selecionado", tabela["modelo"].eq(nome_modelo))
        st.dataframe(tabela.round(3), width="stretch", hide_index=True)
        st.caption("Índices internos, calculados na mesma base usada na busca: são otimistas e não validam o modelo.")

    st.warning(
        "Uso adequado: levantar perguntas sobre quais recortes merecem investigação. "
        "Uso inadequado: selecionar beneficiários, atribuir causas, prever efeitos de políticas "
        "ou afirmar taxas para São Paulo. Os números dos grupos são arbitrários e não indicam prioridade."
    )

# ----------------------------------------------------------------------------
# Aba 4: dados e fonte
# ----------------------------------------------------------------------------
with aba_dados:
    st.subheader("Fonte e definições")
    st.markdown(
        f"""
- **Fonte:** IBGE, *Estatísticas de Gênero: Indicadores sociais das mulheres no Brasil*, 3ª edição (2024), Tabela 1.16.
  Origem primária: PNAD Contínua. [Arquivo original]({URL_IBGE}) (o `.xls` está em `dados/originais/`).
- **Carregamento:** o app lê os CSV e JSON de `resultados/`, gerados pelos notebooks das partes 1 e 3
  ({len(dados)} estimativas agregadas, {len(ANOS)} anos, {dados.segmento.nunique()} segmentos incluindo o total).
- **Linhas de pobreza:** extrema pobreza abaixo de US$ 2,15/dia e pobreza abaixo de US$ 6,85/dia, em PPC 2017. A pobreza inclui a extrema pobreza.
- **Unidade:** cada linha é uma estimativa publicada por segmento × sexo × ano, não uma pessoa.
- **CV:** coeficiente de variação (%), indicador do erro amostral de cada taxa.
        """
    )
    with st.expander("Limitações"):
        st.markdown(
            "- A tabela não tem recorte estadual ou municipal: não há estimativas para São Paulo.\n"
            "- Não publica amarelos, indígenas nem cor ou raça sem declaração; exclui pensionistas e empregados domésticos "
            "e seus parentes na condição no domicílio.\n"
            "- Os recortes se sobrepõem e não há covariâncias para testar diferenças entre eles.\n"
            "- Os dados são históricos (até 2022) e não representam a situação atual.\n"
            "- A clusterização usa 20 perfis agregados e é demonstrativa."
        )

    st.subheader(f"Tabela de dados | {ano}")
    filtrado = dados[dados.ano == ano]
    st.dataframe(filtrado, width="stretch", hide_index=True)
    st.download_button(
        f"Baixar dados de {ano} (CSV)", filtrado.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"pobreza_brasil_{ano}.csv", mime="text/csv",
    )
