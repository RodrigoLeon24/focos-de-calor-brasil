"""
Pipeline de ETL — Focos de Calor no Brasil (2012–2021), satélite de referência AQUA_M-T (INPE).

Etapas (determinísticas e rastreáveis):
    1. extract()   -> lê os 10 CSVs anuais brutos de data/raw/ com tipagem explícita
    2. transform() -> normaliza textos, converte datas, trata sentinelas (-999), remove
                      duplicatas exatas, valida coordenadas e cria variáveis derivadas
    3. load()      -> persiste data/processed/focos_2012_2021.csv.gz e um relatório de
                      qualidade (data/processed/quality_report.json)

Nenhuma linha é descartada silenciosamente: cada remoção/alteração é contada e registrada
no relatório de qualidade.

Uso:
    python -m src.etl                 # a partir da raiz do repositório
"""
from __future__ import annotations

import json
import logging
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
OUTPUT_FILE = PROCESSED_DIR / "focos_2012_2021.csv.gz"
REPORT_FILE = PROCESSED_DIR / "quality_report.json"

SENTINEL = -999  # código do INPE para "valor não calculado"

RAW_DTYPES = {
    "datahora": "string",
    "satelite": "category",
    "pais": "category",
    "estado": "string",
    "municipio": "string",
    "bioma": "string",
    "diasemchuva": "float64",
    "precipitacao": "float64",
    "riscofogo": "float64",
    "latitude": "float64",
    "longitude": "float64",
    "frp": "float64",
}

UF_SIGLA = {
    "ACRE": "AC", "ALAGOAS": "AL", "AMAPA": "AP", "AMAZONAS": "AM", "BAHIA": "BA",
    "CEARA": "CE", "DISTRITO FEDERAL": "DF", "ESPIRITO SANTO": "ES", "GOIAS": "GO",
    "MARANHAO": "MA", "MATO GROSSO": "MT", "MATO GROSSO DO SUL": "MS",
    "MINAS GERAIS": "MG", "PARA": "PA", "PARAIBA": "PB", "PARANA": "PR",
    "PERNAMBUCO": "PE", "PIAUI": "PI", "RIO DE JANEIRO": "RJ",
    "RIO GRANDE DO NORTE": "RN", "RIO GRANDE DO SUL": "RS", "RONDONIA": "RO",
    "RORAIMA": "RR", "SANTA CATARINA": "SC", "SAO PAULO": "SP", "SERGIPE": "SE",
    "TOCANTINS": "TO",
}

REGIAO = {
    **dict.fromkeys(["AC", "AP", "AM", "PA", "RO", "RR", "TO"], "Norte"),
    **dict.fromkeys(["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"], "Nordeste"),
    **dict.fromkeys(["DF", "GO", "MT", "MS"], "Centro-Oeste"),
    **dict.fromkeys(["ES", "MG", "RJ", "SP"], "Sudeste"),
    **dict.fromkeys(["PR", "RS", "SC"], "Sul"),
}

BIOMA_LABEL = {
    "Amazonia": "Amazônia", "Cerrado": "Cerrado", "Mata Atlantica": "Mata Atlântica",
    "Caatinga": "Caatinga", "Pantanal": "Pantanal", "Pampa": "Pampa",
}

# Bounding box aproximado do território brasileiro (com margem)
LAT_RANGE = (-34.0, 5.5)
LON_RANGE = (-74.5, -32.0)

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger("etl")


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def _normalize_text(s: pd.Series) -> pd.Series:
    """Caixa alta, sem acentos e sem espaços duplicados — chave estável para joins."""
    return (
        s.astype("string")
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
        .map(lambda x: _strip_accents(x).upper() if isinstance(x, str) else x)
        .astype("string")
    )


def extract(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    files = sorted(raw_dir.glob("Focos_*.csv"))
    if not files:
        raise FileNotFoundError(
            f"Nenhum CSV encontrado em {raw_dir}. Rode `python data/raw/download_data.py` primeiro."
        )
    frames = []
    for f in files:
        part = pd.read_csv(
            f, sep=",", encoding="utf-8", dtype=RAW_DTYPES, na_values=["NA", ""],
            keep_default_na=False,
        )
        part["arquivo_origem"] = f.name
        log.info("Lido %-40s %9d linhas", f.name, len(part))
        frames.append(part)
    df = pd.concat(frames, ignore_index=True)
    log.info("Total bruto: %d linhas x %d colunas", *df.shape)
    return df


def transform(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    report: dict = {"linhas_brutas": int(len(df))}
    df = df.copy()

    # 1) Datas — formato fixo AAAA/MM/DD HH:MM:SS em UTC (padrão do BDQueimadas)
    df["datahora_utc"] = pd.to_datetime(df["datahora"], format="%Y/%m/%d %H:%M:%S",
                                        errors="coerce", utc=True)
    report["datas_invalidas"] = int(df["datahora_utc"].isna().sum())
    df = df.drop(columns="datahora")

    # 2) Textos
    for col in ["estado", "municipio"]:
        df[col] = _normalize_text(df[col])
    df["bioma"] = df["bioma"].str.strip().map(BIOMA_LABEL).astype("string")
    report["bioma_nao_mapeado"] = int(df["bioma"].isna().sum())

    # 3) Sentinelas -999 -> NaN, com flag de rastreabilidade
    report["sentinelas_-999"] = {}
    for col in ["diasemchuva", "precipitacao", "riscofogo", "frp"]:
        mask = df[col].eq(SENTINEL)
        report["sentinelas_-999"][col] = int(mask.sum())
        df.loc[mask, col] = np.nan
    df["flag_meteo_ausente"] = df[["diasemchuva", "precipitacao", "riscofogo"]].isna().any(axis=1)

    # 4) Validação de domínio
    report["riscofogo_fora_0_1"] = int((~df["riscofogo"].between(0, 1) & df["riscofogo"].notna()).sum())
    df.loc[~df["riscofogo"].between(0, 1), "riscofogo"] = np.nan
    report["frp_negativo"] = int((df["frp"] < 0).sum())
    df.loc[df["frp"] < 0, "frp"] = np.nan
    # diasemchuva > 365 é fisicamente possível no semiárido, mas improvável; apenas sinalizamos
    df["flag_diasemchuva_extremo"] = df["diasemchuva"] > 365
    report["diasemchuva_maior_365"] = int(df["flag_diasemchuva_extremo"].sum())

    coord_ok = df["latitude"].between(*LAT_RANGE) & df["longitude"].between(*LON_RANGE)
    report["coordenadas_fora_brasil_removidas"] = int((~coord_ok).sum())
    df = df[coord_ok]

    # 5) Duplicatas exatas (mesmo instante, mesma coordenada, mesmos atributos)
    key = [c for c in df.columns if c != "arquivo_origem"]
    dup = df.duplicated(subset=key, keep="first")
    report["duplicatas_removidas"] = int(dup.sum())
    df = df[~dup]

    report["linhas_sem_data_removidas"] = int(df["datahora_utc"].isna().sum())
    df = df[df["datahora_utc"].notna()]

    # 6) Variáveis derivadas
    df["uf"] = df["estado"].map(UF_SIGLA).astype("string")
    df["regiao"] = df["uf"].map(REGIAO).astype("string")
    report["uf_nao_mapeada"] = int(df["uf"].isna().sum())
    dt_local = df["datahora_utc"].dt.tz_convert("America/Sao_Paulo")
    df["data"] = dt_local.dt.date.astype("string")
    df["ano"] = dt_local.dt.year.astype("int16")
    df["mes"] = dt_local.dt.month.astype("int8")
    df["ano_mes"] = dt_local.dt.strftime("%Y-%m")
    df["dia_ano"] = dt_local.dt.dayofyear.astype("int16")
    # Estação seca típica do Brasil central (jun–out)
    df["estacao_seca"] = df["mes"].between(6, 10)
    df["classe_risco"] = pd.cut(
        df["riscofogo"], bins=[-0.001, 0.15, 0.4, 0.7, 0.95, 1.0],
        labels=["Mínimo", "Baixo", "Médio", "Alto", "Crítico"],
    )
    df["datahora_utc"] = df["datahora_utc"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    df[["latitude", "longitude"]] = df[["latitude", "longitude"]].round(5)
    df[["precipitacao", "riscofogo", "frp"]] = df[["precipitacao", "riscofogo", "frp"]].round(2)

    order = [
        "datahora_utc", "data", "ano", "mes", "ano_mes", "dia_ano", "estacao_seca",
        "satelite", "pais", "regiao", "estado", "uf", "municipio", "bioma",
        "latitude", "longitude", "diasemchuva", "precipitacao", "riscofogo", "classe_risco",
        "frp", "flag_meteo_ausente", "flag_diasemchuva_extremo", "arquivo_origem",
    ]
    df = df[order].sort_values(["datahora_utc", "latitude", "longitude"], kind="mergesort")
    df = df.reset_index(drop=True)

    report["linhas_finais"] = int(len(df))
    report["percentual_nulos_final"] = {c: round(float(v), 4) for c, v in df.isna().mean().items() if v > 0}
    return df, report


def load(df: pd.DataFrame, report: dict) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False, compression={"method": "gzip", "mtime": 0},
              encoding="utf-8")
    REPORT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("Salvo %s (%d linhas)", OUTPUT_FILE.relative_to(ROOT), len(df))
    log.info("Relatório de qualidade: %s", REPORT_FILE.relative_to(ROOT))


def load_processed(path: Path = OUTPUT_FILE) -> pd.DataFrame:
    """Leitura tipada do dataset processado (usada pelo notebook e pelas análises)."""
    df = pd.read_csv(
        path,
        dtype={"regiao": "category", "estado": "category", "uf": "category",
               "bioma": "category", "satelite": "category", "pais": "category",
               "municipio": "string", "ano_mes": "string", "data": "string",
               "arquivo_origem": "category", "classe_risco": "string"},
    )
    df["datahora_utc"] = pd.to_datetime(df["datahora_utc"], utc=True)
    df["classe_risco"] = pd.Categorical(
        df["classe_risco"], categories=["Mínimo", "Baixo", "Médio", "Alto", "Crítico"], ordered=True)
    return df


def run() -> pd.DataFrame:
    raw = extract()
    clean, report = transform(raw)
    load(clean, report)
    return clean


if __name__ == "__main__":
    run()
