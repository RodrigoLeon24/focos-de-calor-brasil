# Dicionário de Dados — Focos de Calor no Brasil (2012–2021)

Documento de metadados exigido pelo princípio **Interoperable** (FAIR).

## 1. Identificação do conjunto

| Campo | Valor |
|---|---|
| Título | Focos de Calor Brasil 2012–2021 (satélite de referência AQUA_M-T) |
| Produtor primário | Instituto Nacional de Pesquisas Espaciais (INPE) — Programa Queimadas / BDQueimadas |
| Fonte primária | https://terrabrasilis.dpi.inpe.br/queimadas/bdqueimadas/ |
| Redistribuição utilizada | Kaggle — `jsppimentel99/focos-de-calor-brasil-20122021` — https://www.kaggle.com/datasets/jsppimentel99/focos-de-calor-brasil-20122021 |
| Cobertura temporal | 01/01/2012 a 31/12/2021 |
| Cobertura espacial | Território brasileiro (27 UFs, 6 biomas) |
| Granularidade | 1 linha = 1 foco de calor (pixel ~1 km² do sensor MODIS) detectado em uma passagem do satélite AQUA (tarde) |
| Volume bruto | 10 arquivos CSV anuais, 1.867.181 linhas, ~200 MB |
| Volume processado | `data/processed/focos_2012_2021.csv.gz`, 1.867.179 linhas, 24 colunas |
| Codificação / separador | UTF-8 / vírgula, aspas duplas, ausente = `NA` |
| Licença de reuso | Dados públicos do INPE (Lei de Acesso à Informação); derivados deste repositório sob CC-BY 4.0 |

> **Por que só o AQUA_M-T?** O INPE adota o satélite AQUA (passagem da tarde) como *satélite de referência*: o mesmo sensor e horário ao longo dos anos tornam as séries temporais comparáveis. O número absoluto de focos de um único satélite **não** é o número total de queimadas; é um indicador relativo e consistente.

## 2. Variáveis do arquivo bruto (`data/raw/Focos_AAAA-01-01_AAAA-12-31.csv`)

| Variável | Tipo bruto | Descrição | Observações de qualidade |
|---|---|---|---|
| `datahora` | texto `AAAA/MM/DD HH:MM:SS` | Data e hora da passagem do satélite (UTC) | Sem falhas de parsing |
| `satelite` | texto | Satélite/sensor que detectou o foco | Constante `AQUA_M-T` |
| `pais` | texto | País | Constante `Brasil` |
| `estado` | texto | Unidade da Federação, caixa alta, sem acentos | 27 valores |
| `municipio` | texto | Município, caixa alta, sem acentos | 5.434 pares UF–município distintos |
| `bioma` | texto | Bioma IBGE do pixel | 6 valores, sem acentos |
| `diasemchuva` | numérico | Dias consecutivos sem chuva até a data do foco | Ausente em 2012–2013; `-999` = não calculado (10.611) |
| `precipitacao` | numérico (mm) | Precipitação acumulada no dia | Ausente em 2012–2013 |
| `riscofogo` | numérico [0, 1] | Risco de fogo do modelo do INPE | Ausente em 2012–2013; `-999` = não calculado (8.130) |
| `latitude` | numérico (graus decimais, WGS84) | Latitude do centro do pixel | 3 casas até 2020, 5 casas em 2021 |
| `longitude` | numérico (graus decimais, WGS84) | Longitude do centro do pixel | idem |
| `frp` | numérico (MW) | *Fire Radiative Power*: potência radiativa do fogo | Disponível apenas a partir de 2018 |

## 3. Variáveis do arquivo processado (`data/processed/focos_2012_2021.csv.gz`)

| # | Variável | Tipo (pandas) | Formato / domínio | Significado | Origem |
|---|---|---|---|---|---|
| 1 | `datahora_utc` | `datetime64[UTC]` | ISO 8601 `AAAA-MM-DDTHH:MM:SSZ` | Instante da detecção | `datahora` convertido |
| 2 | `data` | `string` | `AAAA-MM-DD` | Data no fuso de Brasília (America/Sao_Paulo) | derivada |
| 3 | `ano` | `int` | 2012–2021 | Ano da detecção | derivada |
| 4 | `mes` | `int` | 1–12 | Mês da detecção | derivada |
| 5 | `ano_mes` | `string` | `AAAA-MM` | Chave para séries mensais | derivada |
| 6 | `dia_ano` | `int` | 1–366 | Dia juliano | derivada |
| 7 | `estacao_seca` | `bool` | True/False | Mês entre junho e outubro (estação seca do Brasil central) | derivada |
| 8 | `satelite` | `category` | `AQUA_M-T` | Satélite de referência | bruta |
| 9 | `pais` | `category` | `Brasil` | País | bruta |
| 10 | `regiao` | `category` | Norte, Nordeste, Centro-Oeste, Sudeste, Sul | Grande região IBGE | derivada (de `uf`) |
| 11 | `estado` | `category` | nome sem acento, caixa alta | Unidade da Federação | bruta normalizada |
| 12 | `uf` | `category` | sigla com 2 letras | Sigla da UF | derivada |
| 13 | `municipio` | `string` | nome sem acento, caixa alta | Município | bruta normalizada |
| 14 | `bioma` | `category` | Amazônia, Cerrado, Mata Atlântica, Caatinga, Pantanal, Pampa | Bioma IBGE (com acentuação) | bruta normalizada |
| 15 | `latitude` | `float64` | [-34, 5,5], 5 casas | Latitude (WGS84) | bruta |
| 16 | `longitude` | `float64` | [-74,5, -32], 5 casas | Longitude (WGS84) | bruta |
| 17 | `diasemchuva` | `float64` | ≥ 0, `NaN` se ausente | Dias sem chuva | bruta; `-999` → `NaN` |
| 18 | `precipitacao` | `float64` | ≥ 0 mm | Precipitação diária | bruta |
| 19 | `riscofogo` | `float64` | [0, 1] | Risco de fogo INPE | bruta; `-999` → `NaN` |
| 20 | `classe_risco` | `category` ordenada | Mínimo (≤0,15), Baixo (≤0,40), Médio (≤0,70), Alto (≤0,95), Crítico (>0,95) | Classe de risco segundo as faixas do INPE | derivada |
| 21 | `frp` | `float64` | ≥ 0 MW | Potência radiativa do fogo | bruta |
| 22 | `flag_meteo_ausente` | `bool` | True/False | Alguma variável meteorológica ausente/sentinela | derivada (rastreabilidade) |
| 23 | `flag_diasemchuva_extremo` | `bool` | True/False | `diasemchuva` > 365 (valor mantido, mas sinalizado) | derivada (rastreabilidade) |
| 24 | `arquivo_origem` | `category` | nome do CSV | Arquivo bruto de onde veio a linha | derivada (proveniência) |

## 4. Regras de tratamento aplicadas (`src/etl.py`)

1. Tipagem explícita na leitura; `NA` e vazio → ausente.
2. `datahora` → `datetime` UTC com formato fixo (linhas inválidas seriam removidas e contadas: 0).
3. Textos: `strip`, espaços colapsados, remoção de acentos e caixa alta em `estado`/`municipio`; `bioma` recebe rótulo acentuado.
4. Sentinela `-999` → `NaN` em `diasemchuva`, `precipitacao`, `riscofogo`, `frp` (contagens no relatório).
5. Validação de domínio: `riscofogo` fora de [0,1] e `frp` < 0 → `NaN` (0 casos); coordenadas fora do envelope do Brasil removidas (0 casos).
6. Duplicatas exatas removidas (2 linhas, em 24/08/2018).
7. **Não há imputação**: a ausência de meteorologia (2012–2013) e de FRP (2012–2017) é estrutural da fonte; imputá-la criaria dados inexistentes. As análises que dependem dessas variáveis restringem o período.
8. Todas as contagens ficam em `data/processed/quality_report.json`.

## 5. Arquivos de apoio

| Arquivo | Conteúdo |
|---|---|
| `data/processed/quality_report.json` | Relatório de qualidade gerado pelo ETL (linhas, sentinelas, duplicatas, % de nulos) |
| `docs/assets/figures.json` | Agregações usadas nos gráficos interativos do artigo |
| `docs/assets/fig*.png` | Figuras estáticas em 200 dpi |
