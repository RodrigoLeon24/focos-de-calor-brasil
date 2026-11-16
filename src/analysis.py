"""
Métricas agregadas e exportação de figuras para o artigo.

Funções puras (recebem o DataFrame processado e devolvem DataFrames/dicts) para que o
notebook e o script de build do artigo usem exatamente a mesma lógica.

Uso:
    python -m src.analysis      # gera docs/assets/*.png e docs/assets/figures.json
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

from src.etl import ROOT, load_processed  # noqa: E402

ASSETS = ROOT / "docs" / "assets"
BIOMAS = ["Amazônia", "Cerrado", "Mata Atlântica", "Caatinga", "Pantanal", "Pampa"]
BIOMA_COR = {
    "Amazônia": "#1b7837", "Cerrado": "#d6a419", "Mata Atlântica": "#4393c3",
    "Caatinga": "#b2182b", "Pantanal": "#7b3294", "Pampa": "#878787",
}
MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
RISCO_ORDEM = ["Mínimo", "Baixo", "Médio", "Alto", "Crítico"]


# ----------------------------------------------------------------------------- métricas
def gini(values: np.ndarray) -> float:
    x = np.sort(np.asarray(values, dtype=float))
    n = len(x)
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))


def anual_por_bioma(df: pd.DataFrame) -> pd.DataFrame:
    return (df.groupby(["ano", "bioma"], observed=True).size()
              .unstack(fill_value=0).reindex(columns=BIOMAS))


def matriz_ano_mes(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby(["ano", "mes"]).size().unstack(fill_value=0)


def indice_anomalia_bioma(df: pd.DataFrame) -> pd.DataFrame:
    """Focos do ano / média 2012–2021 do próprio bioma (1,0 = ano típico)."""
    t = anual_por_bioma(df)
    return t / t.mean()


def tendencia_anual(df: pd.DataFrame) -> dict:
    a = df.groupby("ano").size()
    tau = stats.kendalltau(a.index, a.values)
    lr = stats.linregress(a.index, a.values)
    return {"media": float(a.mean()), "cv": float(a.std() / a.mean()),
            "ano_max": int(a.idxmax()), "max": int(a.max()),
            "ano_min": int(a.idxmin()), "min": int(a.min()),
            "kendall_tau": float(tau.statistic), "kendall_p": float(tau.pvalue),
            "slope_ano": float(lr.slope), "slope_p": float(lr.pvalue)}


def concentracao_municipios(df: pd.DataFrame) -> dict:
    mu = df.groupby(["uf", "municipio"], observed=True).size().sort_values(ascending=False)
    acum = mu.cumsum() / mu.sum()
    top = mu.head(15).reset_index(name="focos")
    nome = top["municipio"].str.title().str.replace(r"\b(Do|Da|De|Dos|Das|E)\b",
                                                     lambda m: m.group(1).lower(), regex=True)
    top["rotulo"] = nome + " (" + top["uf"].astype(str) + ")"
    lorenz_y = np.concatenate([[0], np.sort(mu.values).cumsum() / mu.sum()])
    lorenz_x = np.linspace(0, 1, len(lorenz_y))
    idx = np.unique(np.linspace(0, len(lorenz_x) - 1, 200).astype(int))
    return {
        "n_municipios": int(len(mu)),
        "mun_50pct": int((acum < 0.5).sum() + 1),
        "share_top1pct": float(mu.head(int(len(mu) * 0.01)).sum() / mu.sum()),
        "gini": gini(mu.values),
        "top15": top,
        "lorenz": (lorenz_x[idx], lorenz_y[idx]),
    }


def grade_espacial(df: pd.DataFrame, res: float = 0.5) -> pd.DataFrame:
    g = df.assign(lat=(np.floor(df.latitude / res) * res + res / 2).round(2),
                  lon=(np.floor(df.longitude / res) * res + res / 2).round(2))
    return g.groupby(["lat", "lon"]).size().reset_index(name="focos")


def meteo_vs_frp(df: pd.DataFrame) -> dict:
    """RQ3 — usa apenas 2018–2021 (anos com FRP) e linhas com meteorologia válida."""
    f = df[df.ano >= 2018].dropna(subset=["frp", "riscofogo", "diasemchuva", "precipitacao"])
    rho = {c: stats.spearmanr(f[c], f["frp"]) for c in ["riscofogo", "diasemchuva", "precipitacao"]}
    box = []
    for cls in RISCO_ORDEM:
        s = f.loc[f.classe_risco == cls, "frp"]
        q1, med, q3 = s.quantile([.25, .5, .75])
        iqr = q3 - q1
        box.append({"classe": cls, "n": int(len(s)), "q1": q1, "mediana": med, "q3": q3,
                    "lower": float(max(s.min(), q1 - 1.5 * iqr)),
                    "upper": float(min(s.max(), q3 + 1.5 * iqr)), "p99": float(s.quantile(.99)),
                    "media": float(s.mean())})
    q1, q3 = f.frp.quantile([.25, .75])
    lim = q3 + 1.5 * (q3 - q1)
    return {
        "n": int(len(f)),
        "spearman": {k: {"rho": float(v.statistic), "p": float(v.pvalue)} for k, v in rho.items()},
        "box": pd.DataFrame(box),
        "frp_outlier_lim": float(lim),
        "frp_outlier_share": float((f.frp > lim).mean()),
        "frp_top1_energy_share": float(f.frp.nlargest(int(len(f) * 0.01)).sum() / f.frp.sum()),
        "frp_mediana_bioma": f.groupby("bioma", observed=True).frp.median().reindex(BIOMAS),
    }


def meteo_mensal(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    m = df[df.ano >= 2014]
    g = m.groupby("ano_mes").agg(focos=("ano", "size"), risco_medio=("riscofogo", "mean"),
                                 dsc_mediana=("diasemchuva", "median"),
                                 prec_media=("precipitacao", "mean"), mes=("mes", "first"))
    out = {c: stats.spearmanr(g[c], g["focos"]) for c in ["risco_medio", "dsc_mediana", "prec_media"]}
    return g.reset_index(), {k: {"rho": float(v.statistic), "p": float(v.pvalue)} for k, v in out.items()}


def resumo(df: pd.DataFrame) -> dict:
    m = df[df.ano >= 2014]
    return {
        "total": int(len(df)),
        "municipios": int(df.groupby(["uf", "municipio"], observed=True).ngroups),
        "share_bioma": df.bioma.value_counts(normalize=True).reindex(BIOMAS).round(4).to_dict(),
        "share_regiao": df.regiao.value_counts(normalize=True).round(4).to_dict(),
        "top_uf": df.uf.value_counts().head(10).to_dict(),
        "share_top5_uf": float(df.uf.value_counts().head(5).sum() / len(df)),
        "share_mes": (df.mes.value_counts(normalize=True).sort_index() * 100).round(2).to_dict(),
        "share_jun_out": float(df.estacao_seca.mean()),
        "share_ago_set": float(df.mes.isin([8, 9]).mean()),
        "share_risco_critico": float((m.classe_risco == "Crítico").mean()),
        "share_risco_alto_critico": float((m.riscofogo >= 0.7).mean()),
        "share_prec_zero": float((m.precipitacao == 0).mean()),
    }


# ----------------------------------------------------------------------------- figuras estáticas
def _style():
    plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 200, "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.titleweight": "bold"})


def salvar_figuras_estaticas(df: pd.DataFrame, out: Path = ASSETS) -> list[Path]:
    _style()
    out.mkdir(parents=True, exist_ok=True)
    paths = []

    t = anual_por_bioma(df)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    bottom = np.zeros(len(t))
    for b in BIOMAS:
        ax.bar(t.index, t[b] / 1000, bottom=bottom, color=BIOMA_COR[b], label=b)
        bottom += t[b].values / 1000
    ax.set(xlabel="Ano", ylabel="Focos (milhares)", title="Focos de calor por ano e bioma (AQUA_M-T)")
    ax.set_xticks(t.index)
    ax.legend(ncol=3, frameon=False, fontsize=8)
    paths.append(out / "fig1_anual_bioma.png"); fig.tight_layout(); fig.savefig(paths[-1]); plt.close(fig)

    mm = matriz_ano_mes(df)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    im = ax.imshow(mm.values / 1000, cmap="YlOrRd", aspect="auto")
    ax.set_xticks(range(12), MESES); ax.set_yticks(range(len(mm)), mm.index)
    for i in range(mm.shape[0]):
        for j in range(12):
            v = mm.values[i, j] / 1000
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7,
                    color="white" if v > 35 else "#333")
    fig.colorbar(im, ax=ax, label="Focos (milhares)")
    ax.set_title("Sazonalidade: focos por mês e ano")
    paths.append(out / "fig2_heatmap_ano_mes.png"); fig.tight_layout(); fig.savefig(paths[-1]); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 7))
    hb = ax.hexbin(df.longitude, df.latitude, gridsize=110, bins="log", cmap="inferno", mincnt=1)
    ax.set(xlabel="Longitude", ylabel="Latitude", title="Densidade espacial de focos (2012–2021)")
    ax.set_aspect("equal")
    fig.colorbar(hb, ax=ax, label="Focos por célula (escala log)", shrink=0.7)
    paths.append(out / "fig3_mapa_densidade.png"); fig.tight_layout(); fig.savefig(paths[-1]); plt.close(fig)

    c = concentracao_municipios(df)
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.8))
    top = c["top15"].iloc[::-1]
    axs[0].barh(top.rotulo, top.focos / 1000, color="#c0392b")
    axs[0].set(xlabel="Focos (milhares)", title="15 municípios com mais focos")
    x, y = c["lorenz"]
    axs[1].plot(x, y, color="#c0392b", lw=2, label=f"Curva de Lorenz (Gini = {c['gini']:.2f})")
    axs[1].plot([0, 1], [0, 1], "--", color="gray", label="Igualdade perfeita")
    axs[1].set(xlabel="Fração acumulada de municípios", ylabel="Fração acumulada de focos",
               title="Concentração municipal")
    axs[1].legend(frameon=False)
    paths.append(out / "fig4_concentracao_municipios.png"); fig.tight_layout(); fig.savefig(paths[-1]); plt.close(fig)

    an = indice_anomalia_bioma(df)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for b in BIOMAS:
        ax.plot(an.index, an[b], marker="o", color=BIOMA_COR[b], label=b, lw=2 if b == "Pantanal" else 1.2)
    ax.axhline(1, color="gray", ls="--", lw=1)
    ax.set(xlabel="Ano", ylabel="Índice (1 = média do bioma)", title="Anomalia anual relativa por bioma")
    ax.set_xticks(an.index); ax.legend(ncol=3, frameon=False, fontsize=8)
    paths.append(out / "fig5_anomalia_bioma.png"); fig.tight_layout(); fig.savefig(paths[-1]); plt.close(fig)

    mv = meteo_vs_frp(df)
    f = df[df.ano >= 2018].dropna(subset=["frp", "riscofogo"])
    fig, ax = plt.subplots(figsize=(8, 4.5))
    data = [f.loc[f.classe_risco == k, "frp"].values for k in RISCO_ORDEM]
    ax.boxplot(data, tick_labels=RISCO_ORDEM, showfliers=False, patch_artist=True,
               boxprops={"facecolor": "#f5b041"}, medianprops={"color": "#7b241c"})
    ax.set(xlabel="Classe de risco de fogo (INPE)", ylabel="FRP (MW)",
           title=f"Intensidade (FRP) por classe de risco — 2018–2021 (n = {mv['n']:,})".replace(",", "."))
    paths.append(out / "fig6_frp_risco.png"); fig.tight_layout(); fig.savefig(paths[-1]); plt.close(fig)

    g, rho = meteo_mensal(df)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    sc = ax.scatter(g.risco_medio, g.focos / 1000, c=g.mes, cmap="twilight", s=30)
    ax.set(xlabel="Risco de fogo médio do mês", ylabel="Focos no mês (milhares)",
           title=f"Risco médio × nº de focos por mês (2014–2021), ρ de Spearman = {rho['risco_medio']['rho']:.2f}")
    fig.colorbar(sc, ax=ax, label="Mês")
    paths.append(out / "fig7_risco_mensal.png"); fig.tight_layout(); fig.savefig(paths[-1]); plt.close(fig)
    return paths


# ----------------------------------------------------------------------------- dados p/ Plotly
def _r(x, n=4):
    return [None if pd.isna(v) else round(float(v), n) for v in x]


def exportar_json_plotly(df: pd.DataFrame, out: Path = ASSETS) -> dict:
    t = anual_por_bioma(df)
    mm = matriz_ano_mes(df)
    an = indice_anomalia_bioma(df)
    c = concentracao_municipios(df)
    grid = grade_espacial(df)
    mv = meteo_vs_frp(df)
    g, rho_m = meteo_mensal(df)
    payload = {
        "resumo": resumo(df),
        "tendencia": tendencia_anual(df),
        "anual_bioma": {"anos": t.index.tolist(), "series": {b: t[b].tolist() for b in BIOMAS},
                         "cores": BIOMA_COR},
        "heatmap": {"anos": mm.index.tolist(), "meses": MESES, "z": mm.values.tolist()},
        "anomalia": {"anos": an.index.tolist(), "series": {b: _r(an[b], 3) for b in BIOMAS}},
        "municipios": {"top15": c["top15"][["rotulo", "focos"]].to_dict(orient="list"),
                        "lorenz_x": _r(c["lorenz"][0]), "lorenz_y": _r(c["lorenz"][1]),
                        "gini": c["gini"], "n": c["n_municipios"], "mun_50pct": c["mun_50pct"],
                        "share_top1pct": c["share_top1pct"]},
        "grade": {"lat": grid.lat.tolist(), "lon": grid.lon.tolist(), "focos": grid.focos.tolist()},
        "frp_box": mv["box"].round(2).to_dict(orient="list"),
        "frp_stats": {"n": mv["n"], "spearman": mv["spearman"], "outlier_lim": mv["frp_outlier_lim"],
                      "outlier_share": mv["frp_outlier_share"],
                      "top1_energy_share": mv["frp_top1_energy_share"],
                      "mediana_bioma": mv["frp_mediana_bioma"].round(1).to_dict()},
        "mensal": {"ano_mes": g.ano_mes.tolist(), "focos": g.focos.tolist(),
                    "risco": _r(g.risco_medio, 3), "prec": _r(g.prec_media, 3), "mes": g.mes.tolist(),
                    "spearman": rho_m},
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "figures.json").write_text(json.dumps(payload, ensure_ascii=False, default=float), encoding="utf-8")
    return payload


if __name__ == "__main__":
    data = load_processed()
    for p in salvar_figuras_estaticas(data):
        print("figura:", p.relative_to(ROOT))
    exportar_json_plotly(data)
    print("dados interativos: docs/assets/figures.json")
