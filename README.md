# Pobreza e desigualdades no Brasil | Data app (Parte 2)

Aplicação Streamlit que reúne os resultados das partes 1 (análise e indicadores) e 3 (clusterização K-means e DBSCAN).
Fonte: IBGE, Estatísticas de Gênero, 3ª edição (2024), Tabela 1.16, PNAD Contínua, 2012 a 2022.

## Como executar localmente

Requer Python 3.13 (a mesma versão dos notebooks).

```bash
cd Projeto_ICD_Partes_1_e_3
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
streamlit run app.py
```

O app abre em http://localhost:8501. Ele lê os arquivos de `resultados/` e não precisa de internet.
Se algum arquivo estiver ausente, o app mostra quais são. Para gerá-los de novo, execute `Parte_1_Analise.ipynb` e depois
`Parte_3_Modelagem.ipynb` (instruções em `LEIA-ME.txt`).

## Deploy (opcional) no Streamlit Community Cloud

1. Publique a pasta em um repositório do GitHub, incluindo `app.py`, `requirements.txt` e `resultados/`.
2. Em https://share.streamlit.io, crie um app apontando para o repositório e para `app.py`.
3. Em *Advanced settings*, escolha Python 3.13.

O app não usa `modelos.joblib`, então a versão do scikit-learn não afeta a execução.

## Estrutura da tela

| Aba | Conteúdo |
|---|---|
| Visão geral | 6 KPIs do ano escolhido, evolução 2012–2022 por sexo e leitura automática do recorte de maior e de menor taxa. |
| Recortes e sexo | Taxas de homens e mulheres por segmento, diferença em pontos percentuais, intervalo de confiança opcional e evolução por segmento. |
| Perfis (clusters) | Dispersão dos 20 perfis de 2022, métricas do modelo, resumo e membros dos grupos, estabilidade e todas as configurações testadas. |
| Dados e fonte | Definições, limitações, tabela do ano com download em CSV. |

## Filtros e como eles influenciam o app

| Widget | Onde fica | O que altera |
|---|---|---|
| `st.select_slider` Ano de referência | Barra lateral | Valor dos KPIs e variação em relação ao ano anterior, barras da aba 2, tabela da aba 4 e a linha vertical dos gráficos de evolução. Não altera a aba de perfis (só 2022). |
| `st.radio` Medida de pobreza | Barra lateral | Alterna entre pobreza (US$ 6,85) e extrema pobreza (US$ 2,15) nos gráficos de evolução e de recortes, na tabela de diferenças e no texto de leitura. Os KPIs têm definição fixa. |
| `st.selectbox` Dimensão demográfica | Barra lateral | Define o recorte da aba 2 (cor ou raça, idade, ocupação ou domicílio) e as opções do filtro de segmentos. |
| `st.multiselect` Segmentos exibidos | Aba 2 | Restringe barras, tabela e linhas aos segmentos marcados. |
| `st.radio` Sexo | Aba 2 | Escolhe a série (Total, Homem ou Mulher) do gráfico de evolução por segmento. |
| `st.radio` Algoritmo | Aba 3 | Troca K-means por DBSCAN: muda cores do gráfico, métricas, resumo e membros dos grupos. |
| `st.toggle` (2) | Abas 2 e 3 | Intervalo de confiança nas barras; nome dos perfis no gráfico de dispersão. |

## Justificativa dos componentes

| Componente | Função na análise |
|---|---|
| `st.metric` | Mostra as taxas oficiais e os gaps em pontos percentuais com a variação sobre o ano anterior. O sinal indica se a desigualdade aumentou ou diminuiu. Também mostra silhouette, Davies-Bouldin, cobertura e ruído do modelo. |
| `st.select_slider` (ano) | Os anos são uma sequência ordenada e discreta. O controle impede escolher um ano inexistente. |
| `st.radio` (medida, sexo, algoritmo) | Poucas opções mutuamente exclusivas, todas visíveis ao mesmo tempo, o que facilita a comparação. |
| `st.selectbox` (dimensão) | Quatro dimensões excludentes. Mostrar uma por vez evita um gráfico com todos os segmentos sobrepostos. |
| `st.multiselect` (segmentos) | O número de segmentos varia por dimensão e o usuário pode comparar só alguns. |
| `st.toggle` | Opções de exibição (intervalo de confiança, rótulos) que não mudam os dados, só a leitura. |
| `st.tabs` | Separa os quatro blocos de análise sem rolagem longa. |
| `st.sidebar` | Mantém os filtros globais visíveis em todas as abas. |
| `st.columns` | Coloca gráfico e tabela lado a lado, e os KPIs em grade. |
| `st.dataframe` | Permite ordenar e inspecionar os números por trás de cada gráfico. |
| `st.expander` | Guarda detalhes (membros dos grupos, estabilidade, limitações) sem poluir a leitura principal. |
| `st.download_button` | Exporta os dados do ano filtrado. |
| `st.warning`, `st.caption`, `st.markdown`, `st.info` | Textos explicativos, limites de uso e avisos de seleção vazia. |
| `st.cache_data` | Lê os arquivos uma vez e evita reler a cada interação. |
| `st.plotly_chart` | Gráficos interativos (zoom, hover, legenda clicável). |

## Gráficos

1. Linhas: evolução nacional por sexo (aba 1).
2. Barras agrupadas: taxa de homens e mulheres por segmento (aba 2).
3. Linhas: evolução por segmento (aba 2).
4. Dispersão: perfis coloridos por cluster (aba 3).

São quatro gráficos Plotly de três tipos: dois de linha, um de barras e um de dispersão.

## Observações sobre os resultados

- A modelagem é **não supervisionada**: agrupa perfis parecidos e não prevê pobreza. As métricas são internas e otimistas.
- Os 20 perfis são estimativas agregadas e sobrepostas, não pessoas.
- A fonte não tem recorte estadual. Os resultados não valem para São Paulo.
- Os dados vão até 2022 e não descrevem a situação atual.
- Rótulos 0 e 1 dos clusters são arbitrários. O app os nomeia por pobreza média ("Menor pobreza" e "Maior pobreza").
- O intervalo de confiança do app é aproximado (±1,96 × taxa × CV) e não considera covariâncias.
