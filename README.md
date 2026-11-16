# 🔥 Focos de Calor no Brasil (2012–2021): dinâmica temporal, concentração espacial e condicionantes meteorológicos

![Python](https://img.shields.io/badge/Python-3.13-3776ab?logo=python&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-3.0.5-150458?logo=pandas)
![Licença do código](https://img.shields.io/badge/código-MIT-2e7d32)
![Licença dos dados](https://img.shields.io/badge/dados%20%26%20texto-CC%20BY%204.0-ef6c00)
![FAIR](https://img.shields.io/badge/FAIR-compliant-1565c0)
![Fonte](https://img.shields.io/badge/fonte-INPE%20BDQueimadas-8e2424)

**Artigo interativo (GitHub Pages):** https://rodrigoleon24.github.io/focos-de-calor-brasil/

| | |
|---|---|
| **Autores** | Rodrigo Leon de Andrade Silva |
| **Curso** | Bacharelado em Sistemas de Informação — 6º Período |
| **Disciplina** | Linguagem de Programação (Análise e Visualização de Dados com Python) |
| **Instituição** | Unilasalle - RJ |
| **Semestre** | 2026/2 |

## Resumo executivo

Pipeline reprodutível em Python que integra, limpa e analisa **1.867.179 focos de calor** detectados pelo satélite de referência AQUA (INPE) entre 2012 e 2021, respondendo a três perguntas de pesquisa:

| Pergunta | Principal achado |
|---|---|
| **RQ1** — Como os focos se distribuem no tempo? | Sem tendência monotônica (τ de Kendall = 0,07; p = 0,86), mas sazonalidade rígida: **agosto e setembro concentram 50,2%** dos focos. O **Pantanal em 2020** registrou **3,2×** sua média decenal. |
| **RQ2** — Onde os focos se concentram? | Amazônia (46,3%) e Cerrado (33,8%) somam 80%; cinco UFs somam 57,7%; **161 municípios (~3%) concentram metade dos focos** (Gini = 0,83). |
| **RQ3** — A meteorologia explica frequência e intensidade? | Forte associação com a frequência mensal (ρ = 0,68 para risco de fogo), mas fraca com a intensidade individual/FRP (ρ = 0,22): o clima abre a janela; o uso humano do fogo define onde e quanto se queima. |

**Palavras-chave:** focos de calor; queimadas; biomas brasileiros; sensoriamento remoto; análise exploratória de dados; princípios FAIR.

## Fonte dos dados

- **Produtor primário:** INPE — Programa Queimadas / BDQueimadas — https://terrabrasilis.dpi.inpe.br/queimadas/bdqueimadas/
- **Redistribuição utilizada (link perene):** Kaggle `jsppimentel99/focos-de-calor-brasil-20122021` — https://www.kaggle.com/datasets/jsppimentel99/focos-de-calor-brasil-20122021
- 10 CSVs anuais, ~200 MB, 1 linha = 1 foco (pixel ~1 km², sensor MODIS, satélite AQUA_M-T).
- Metadados completos: [`data/data_dictionary.md`](data/data_dictionary.md).

## Estrutura do repositório

```
focos-de-calor-brasil/
├── README.md
├── LICENSE                         # MIT (código) + CC BY 4.0 (dados derivados e texto)
├── requirements.txt                # dependências com versões congeladas
├── .gitignore
├── data/
│   ├── raw/
│   │   └── download_data.py        # baixa os CSVs brutos (>50 MB, não versionados)
│   ├── processed/
│   │   ├── focos_2012_2021.csv.gz  # dataset tratado (24 colunas)
│   │   └── quality_report.json     # contagens de cada tratamento aplicado
│   └── data_dictionary.md          # dicionário de variáveis (FAIR)
├── notebooks/
│   └── analise_exploratoria.ipynb  # exploração, prototipação e validação (executado)
├── src/
│   ├── __init__.py
│   ├── etl.py                      # extract → transform → load
│   ├── analysis.py                 # métricas, estatísticas e figuras
│   └── build_docs.py               # injeta os dados dos gráficos no artigo
└── docs/                           # GitHub Pages
    ├── index.html                  # artigo científico (HTML5 + Plotly.js)
    └── assets/                     # figuras PNG (200 dpi) e figures.json
```

## Como reproduzir

Pré-requisito: Python 3.13 (testado com 3.13.18).

```bash
# 1. Clonar e preparar o ambiente
git clone https://github.com/RodrigoLeon24/focos-de-calor-brasil.git
cd focos-de-calor-brasil
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Baixar os dados brutos (dataset público — não exige conta nem token)
python data/raw/download_data.py
#    Alternativa manual: baixe o .zip no Kaggle e extraia os CSVs em data/raw/

# 3. Rodar o pipeline completo
python -m src.etl          # ~1 min → data/processed/focos_2012_2021.csv.gz + quality_report.json
python -m src.analysis     # → docs/assets/fig*.png + docs/assets/figures.json
python -m src.build_docs   # → atualiza os gráficos interativos de docs/index.html

# 4. Explorar
jupyter lab notebooks/analise_exploratoria.ipynb
```

O pipeline é determinístico: mesma entrada ⇒ mesmos arquivos de saída (ordenação estável e gzip com timestamp fixo).

### Publicação no GitHub Pages

*Settings → Pages → Build and deployment → Source: Deploy from a branch → Branch: `main` / pasta `/docs`*.

## Tratamento de dados (resumo)

| Problema | Ocorrências | Tratamento |
|---|---:|---|
| Sentinela `-999` em `diasemchuva` | 10.611 | → `NaN` + `flag_meteo_ausente` |
| Sentinela `-999` em `riscofogo` | 8.130 | → `NaN` + `flag_meteo_ausente` |
| Meteorologia ausente em 2012–2013 / FRP antes de 2018 | estrutural | **sem imputação**; análises restritas ao período coberto |
| `diasemchuva` > 365 | 693 | mantido + `flag_diasemchuva_extremo` |
| Duplicatas exatas | 2 | removidas |

## Licenças e citação

- **Código:** MIT — ver [`LICENSE`](LICENSE).
- **Dados processados, figuras e texto do artigo:** CC BY 4.0.
- **Dados brutos:** INPE, Programa Queimadas. Cite: *INPE. Banco de Dados de Queimadas (BDQueimadas). São José dos Campos: INPE.*
