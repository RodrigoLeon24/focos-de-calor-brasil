"""
Baixa os 10 CSVs brutos (~200 MB) do Kaggle para data/raw/.

O dataset é público: o kagglehub faz o download sem credenciais.
Uso (a partir da raiz do repositório):
    python data/raw/download_data.py
Alternativa manual: baixe o .zip em
https://www.kaggle.com/datasets/jsppimentel99/focos-de-calor-brasil-20122021
e extraia os CSVs nesta pasta.
"""
import shutil
from pathlib import Path

import kagglehub

DATASET = "jsppimentel99/focos-de-calor-brasil-20122021"
DEST = Path(__file__).resolve().parent

if __name__ == "__main__":
    cache = Path(kagglehub.dataset_download(DATASET))
    print("Cache do kagglehub:", cache)
    files = sorted(cache.rglob("Focos_*.csv"))
    for f in files:
        shutil.copy2(f, DEST / f.name)
        print("copiado", f.name)
    assert len(files) == 10, f"Esperados 10 arquivos, encontrados {len(files)}"
    print(f"{len(files)} arquivos em {DEST}")
