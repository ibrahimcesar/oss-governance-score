"""Figuras para as seções 4.2/4.3 do TCC (matplotlib, PT-BR).

Método de dataviz: forma antes de cor; paleta categórica validada (4 slots,
CVD-safe em todos os pares); cores de série nunca em texto (texto usa tons de
tinta); grid recessivo; rótulos diretos seletivos.

fig1 — mapa da amostra: dispersão contribuidores ativos × stars (log-log) com
       as regiões dos arquétipos da §3.1; ambíguos em cinza como contexto.
fig2 — perfil de governança dos pilotos: subscores por dimensão, barras
       agrupadas por arquétipo.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import yaml  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FIG_DIR = ROOT / "figures"

# Paleta categórica validada (validate_palette.js, light, --pairs all: PASS).
# Cor segue a entidade: ordem fixa por arquétipo.
ARCH_COLOR = {
    "federation": "#2a78d6",  # slot 1 azul
    "stadium": "#008300",     # slot 2 verde
    "club": "#e87ba4",        # slot 3 magenta
    "toy": "#eda100",         # slot 4 amarelo
}
ARCH_LABEL = {
    "federation": "Federação",
    "stadium": "Estádio",
    "club": "Clube",
    "toy": "Brinquedo",
}
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"


def _style(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(BASELINE)
        ax.spines[side].set_linewidth(0.8)
    ax.tick_params(colors=MUTED, labelsize=8, length=3)
    ax.grid(True, color=GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)


def fig_sample_map(sample_path: Path, out_stem: Path) -> None:
    d = yaml.safe_load(sample_path.read_text())
    t = d["thresholds"]

    fig, ax = plt.subplots(figsize=(7.2, 5.0), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    _style(ax)
    ax.set_xscale("log")
    ax.set_yscale("log")
    xmin, xmax = 0.4, 3000
    ymin, ymax = 4, 600_000
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)

    # Regiões da matriz §3.1 (wash da cor do arquétipo; o texto usa tinta)
    regions = {
        "federation": (t["federation_min_contributors"], xmax,
                       t["stars_high_min"], ymax),
        "stadium": (xmin, t["stadium_max_contributors"],
                    t["stars_high_min"], ymax),
        "club": (t["club_min_contributors"], xmax, ymin, t["club_stars_max"]),
        "toy": (xmin, t["toy_max_contributors"], ymin, t["toy_stars_max"]),
    }
    label_pos = {"federation": (600, 300_000), "stadium": (0.55, 300_000),
                 "club": (600, 30), "toy": (0.55, 30)}
    for arch, (x0, x1, y0, y1) in regions.items():
        ax.fill_betweenx([y0, y1], x0, x1, color=ARCH_COLOR[arch],
                         alpha=0.07, zorder=0, linewidth=0)
        ax.text(*label_pos[arch], ARCH_LABEL[arch], color=INK_2, fontsize=9,
                fontweight="bold", ha="left", va="top")

    # Ambíguos como contexto (cinza), selecionados por cima com anel branco
    amb = [e for e in d["ambiguous"]
           if not e.get("reason", "").startswith("sem commits")]
    ax.scatter([max(e["active_contributors_2plus"], 0.5) for e in amb],
               [max(e["stars"], ymin) for e in amb],
               s=10, color=MUTED, alpha=0.4, linewidths=0, zorder=2,
               label=f"fora das faixas / truncados (n={len(amb)})")
    for arch in ARCH_COLOR:
        pts = [e for e in d["full"] if e["archetype"] == arch]
        ax.scatter([max(e["active_contributors_2plus"], 0.5) for e in pts],
                   [e["stars"] for e in pts],
                   s=26, color=ARCH_COLOR[arch], edgecolors=SURFACE,
                   linewidths=0.6, zorder=3,
                   label=f"{ARCH_LABEL[arch]} (n={len(pts)})")

    ax.set_xlabel("Contribuidores com ≥2 commits em 12 meses (log)",
                  color=INK_2, fontsize=9)
    ax.set_ylabel("Stars (log)", color=INK_2, fontsize=9)
    ax.set_title("Amostra estratificada: classificação pelos limiares da §3.1",
                 color=INK, fontsize=11, loc="left", pad=14)
    ax.text(0, 1.015, "n=100 selecionados; cinza = candidatos classificados "
            "fora das faixas (zonas deliberadas da matriz)",
            transform=ax.transAxes, color=INK_2, fontsize=8)
    leg = ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.11), ncol=3,
                    fontsize=7.5, frameon=False)
    for txt in leg.get_texts():
        txt.set_color(INK_2)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(f"{out_stem}.{ext}", facecolor=SURFACE,
                    bbox_inches="tight")
    plt.close(fig)


DIMENSIONS = [("artifacts", "D1\nArtefatos"), ("distribution", "D2\nDistribuição"),
              ("responsiveness", "D3\nResponsividade"), ("diversity", "D4\nDiversidade"),
              ("security", "D5\nSegurança")]
ARCH_ORDER = ["federation", "stadium", "club", "toy"]


def fig_pilot_subscores(scores_path: Path, out_stem: Path) -> None:
    data = json.loads(scores_path.read_text())
    by_arch = {r["archetype"]: r for r in data}

    fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    _style(ax)
    ax.grid(axis="x", visible=False)

    n = len(ARCH_ORDER)
    width = 0.19
    for i, arch in enumerate(ARCH_ORDER):
        r = by_arch[arch]
        xs = [j + (i - (n - 1) / 2) * width for j in range(len(DIMENSIONS))]
        ys = [r["subscores"].get(k) or 0 for k, _ in DIMENSIONS]
        ax.bar(xs, ys, width=width * 0.94, color=ARCH_COLOR[arch],
               edgecolor=SURFACE, linewidth=1.0, zorder=3,
               label=f"{ARCH_LABEL[arch]} — {r['repo']}")

    ax.set_xticks(range(len(DIMENSIONS)))
    ax.set_xticklabels([lbl for _, lbl in DIMENSIONS], color=INK_2, fontsize=8)
    ax.set_ylim(0, 1.06)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_ylabel("Sub-score da dimensão (0–1)", color=INK_2, fontsize=9)
    ax.set_title("Perfil de governança dos pilotos por dimensão",
                 color=INK, fontsize=11, loc="left", pad=14)
    ax.text(0, 1.02, "extração 2026-07-19, backend api+git (catálogo expandido)",
            transform=ax.transAxes, color=INK_2, fontsize=8)
    leg = ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2,
                    fontsize=7.5, frameon=False)
    for txt in leg.get_texts():
        txt.set_color(INK_2)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(f"{out_stem}.{ext}", facecolor=SURFACE,
                    bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    FIG_DIR.mkdir(exist_ok=True)
    fig_sample_map(ROOT / "config" / "sample_full.yaml",
                   FIG_DIR / "fig_amostra_classificacao")
    fig_pilot_subscores(ROOT / "data" / "processed" / "pilot_scores.json",
                        FIG_DIR / "fig_pilotos_subscores")
    print(f"figuras em {FIG_DIR}/")


if __name__ == "__main__":
    main()
