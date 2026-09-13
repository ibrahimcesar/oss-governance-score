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

plt.rcParams["savefig.dpi"] = 300  # PNG de saída em 300 dpi (monografia)
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


def fig_sample_languages(sample_path: Path, out_stem: Path) -> None:
    """Empilhado por arquétipo (4 séries da paleta; linguagem é o eixo,
    nunca 10 cores — teto categórico)."""
    d = yaml.safe_load(sample_path.read_text())
    langs = sorted({e["language"] for e in d["full"]})
    counts = {a: [sum(1 for e in d["full"]
                      if e["archetype"] == a and e["language"] == lg)
                  for lg in langs] for a in ARCH_ORDER}

    fig, ax = plt.subplots(figsize=(7.2, 3.8), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    _style(ax)
    ax.grid(axis="x", visible=False)

    bottom = [0] * len(langs)
    for arch in ARCH_ORDER:
        ax.bar(langs, counts[arch], bottom=bottom, width=0.62,
               color=ARCH_COLOR[arch], edgecolor=SURFACE, linewidth=1.2,
               zorder=3, label=ARCH_LABEL[arch])
        bottom = [b + c for b, c in zip(bottom, counts[arch])]

    ax.set_ylabel("Repositórios na amostra", color=INK_2, fontsize=9)
    ax.set_ylim(0, max(bottom) + 1.5)
    ax.tick_params(axis="x", labelsize=8)
    ax.set_title("Composição da amostra: linguagem × arquétipo",
                 color=INK, fontsize=11, loc="left", pad=14)
    ax.text(0, 1.02, "n=100; máx. 4 por linguagem dentro de cada arquétipo "
            "(cap de diversidade)", transform=ax.transAxes,
            color=INK_2, fontsize=8)
    leg = ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=4,
                    fontsize=7.5, frameon=False)
    for txt in leg.get_texts():
        txt.set_color(INK_2)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(f"{out_stem}.{ext}", facecolor=SURFACE,
                    bbox_inches="tight")
    plt.close(fig)


def fig_pilot_ranking(scores_path: Path, out_stem: Path) -> None:
    """Barras horizontais ordenadas; 4 valores → rótulo direto em cada."""
    data = sorted(json.loads(scores_path.read_text()), key=lambda r: r["score"])

    fig, ax = plt.subplots(figsize=(7.2, 2.9), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    _style(ax)
    ax.grid(axis="y", visible=False)

    names = [f"{ARCH_LABEL[r['archetype']]} — {r['repo']}" for r in data]
    scores = [r["score"] for r in data]
    ax.barh(names, scores, height=0.55,
            color=[ARCH_COLOR[r["archetype"]] for r in data],
            edgecolor=SURFACE, linewidth=1.0, zorder=3)
    for i, s in enumerate(scores):
        ax.text(s + 1.2, i, f"{s:.1f}", va="center", color=INK_2,
                fontsize=8.5, fontweight="bold")

    ax.set_xlim(0, 100)
    ax.set_xlabel("Score de governança (0–100)", color=INK_2, fontsize=9)
    ax.tick_params(axis="y", labelsize=8.5)
    ax.set_title("Score composto dos pilotos", color=INK, fontsize=11,
                 loc="left", pad=14)
    ax.text(0, 1.03, "extração 2026-07-19, backend api+git; pesos da "
            "literatura (D1/D2 25%, D3 20%, D4/D5 15%)",
            transform=ax.transAxes, color=INK_2, fontsize=8)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(f"{out_stem}.{ext}", facecolor=SURFACE,
                    bbox_inches="tight")
    plt.close(fig)


def fig_score_boxplot(scores_csv: Path, out_stem: Path) -> None:
    """Boxplot de score por arquétipo + pontos individuais (n=25 cada)."""
    import numpy as np
    import pandas as pd
    df = pd.read_csv(scores_csv)

    fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    _style(ax)
    ax.grid(axis="x", visible=False)

    order = (df.groupby("archetype")["score"].median()
             .sort_values(ascending=False).index.tolist())
    rng = np.random.default_rng(42)  # jitter determinístico (reprodutível)
    for i, arch in enumerate(order):
        vals = df.loc[df.archetype == arch, "score"].dropna().values
        bp = ax.boxplot([vals], positions=[i], widths=0.5, patch_artist=True,
                        showfliers=False,
                        boxprops=dict(facecolor=ARCH_COLOR[arch], alpha=0.25,
                                      edgecolor=ARCH_COLOR[arch], linewidth=1.4),
                        whiskerprops=dict(color=ARCH_COLOR[arch], linewidth=1.2),
                        capprops=dict(color=ARCH_COLOR[arch], linewidth=1.2),
                        medianprops=dict(color=INK, linewidth=1.6))
        ax.scatter(rng.normal(i, 0.08, len(vals)), vals, s=14,
                   color=ARCH_COLOR[arch], edgecolors=SURFACE,
                   linewidths=0.5, zorder=3, alpha=0.9)

    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([f"{ARCH_LABEL[a]}\n(n=25)" for a in order],
                       color=INK_2, fontsize=9)
    ax.set_ylabel("Score de governança (0–100)", color=INK_2, fontsize=9)
    ax.set_ylim(0, 100)
    ax.set_title("Distribuição do score por arquétipo (n=100)",
                 color=INK, fontsize=11, loc="left", pad=14)
    ax.text(0, 1.02, "caixas: quartis e mediana; pontos: repositórios "
            "(variância intra-arquétipo não trivial — critério DSR §6.3)",
            transform=ax.transAxes, color=INK_2, fontsize=8)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(f"{out_stem}.{ext}", facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


def fig_dimension_heatmap(scores_csv: Path, out_stem: Path) -> None:
    """Heatmap de Spearman entre os sub-scores das 5 dimensões (divergente
    azul↔vermelho com ponto médio neutro; exclusão par a par de faltantes)."""
    import pandas as pd
    from matplotlib.colors import LinearSegmentedColormap, Normalize
    df = pd.read_csv(scores_csv)
    cols = {f"subscore_{k}": lbl.replace("\n", " ")
            for k, lbl in DIMENSIONS}
    corr = df[list(cols)].corr(method="spearman")

    cmap = LinearSegmentedColormap.from_list(
        "div", ["#e34948", "#f0efec", "#2a78d6"])  # pares divergentes da paleta
    norm = Normalize(-1, 1)

    fig, ax = plt.subplots(figsize=(6.4, 5.2), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    im = ax.imshow(corr.values, cmap=cmap, norm=norm)
    labels = [cols[c] for c in corr.columns]
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=7.5, color=INK_2, rotation=30,
                       ha="right")
    ax.set_yticklabels(labels, fontsize=7.5, color=INK_2)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    for i in range(len(labels)):
        for j in range(len(labels)):
            v = corr.values[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8,
                    color="#ffffff" if abs(v) > 0.55 else INK)
    cbar = fig.colorbar(im, shrink=0.8)
    cbar.ax.tick_params(labelsize=7, colors=MUTED)
    cbar.outline.set_visible(False)
    ax.set_title("Correlação (ρ de Spearman) entre dimensões, n=100",
                 color=INK, fontsize=11, loc="left", pad=12)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(f"{out_stem}.{ext}", facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


def _validation_scatter(ax, df, xcol, xlabel, log_x=False):
    _style(ax)
    for arch in ARCH_ORDER:
        sub = df[(df.archetype == arch) & df[xcol].notna()]
        ax.scatter(sub[xcol], sub.score, s=24, color=ARCH_COLOR[arch],
                   edgecolors=SURFACE, linewidths=0.6, zorder=3,
                   label=ARCH_LABEL[arch])
    if log_x:
        ax.set_xscale("log")
    ax.set_xlabel(xlabel, color=INK_2, fontsize=9)
    ax.set_ylabel("Score de governança", color=INK_2, fontsize=9)
    ax.set_ylim(0, 100)


def fig_validation_scatters(ext_csv: Path, validation_json: Path,
                            out_stem: Path) -> None:
    """Scatters score × Scorecard e score × stars (log), com ρ da família
    corrigida anotado (lidos de validation.json — nunca recalculados aqui)."""
    import pandas as pd
    df = pd.read_csv(ext_csv)
    val = json.loads(validation_json.read_text())["global"]

    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.9), dpi=200)
    fig.patch.set_facecolor(SURFACE)

    _validation_scatter(axes[0], df, "scorecard",
                        "OpenSSF Scorecard (0–10)")
    g = val["scorecard"]
    axes[0].text(0.03, 0.96, f"ρ = {g['rho']:.3f} (n={g['n']}, "
                 f"p aj. < 0,001)", transform=axes[0].transAxes,
                 fontsize=8, color=INK_2, va="top")

    _validation_scatter(axes[1], df, "stars", "Stars (log)", log_x=True)
    g = val["stars"]
    axes[1].text(0.03, 0.96, f"ρ = {g['rho']:.3f} (n={g['n']}, "
                 f"p aj. < 0,001)", transform=axes[1].transAxes,
                 fontsize=8, color=INK_2, va="top")

    axes[0].set_title("Validade convergente", color=INK, fontsize=10,
                      loc="left", pad=10)
    axes[1].set_title("Popularidade (proxy fraco — declarado)", color=INK,
                      fontsize=10, loc="left", pad=10)
    handles, lbls = axes[0].get_legend_handles_labels()
    leg = fig.legend(handles, lbls, loc="lower center", ncol=4, fontsize=7.5,
                     frameon=False, bbox_to_anchor=(0.5, -0.04))
    for txt in leg.get_texts():
        txt.set_color(INK_2)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(f"{out_stem}.{ext}", facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


def write_tcc_tables(scores_csv: Path, out_path: Path) -> None:
    """Tabelas consolidadas para as seções 4.2/4.3 (descritiva + extremos)."""
    import pandas as pd
    df = pd.read_csv(scores_csv)
    lines = ["# Tabelas para as seções 4.2/4.3", "",
             "## Estatística descritiva do score por arquétipo", "",
             "| Arquétipo | n | média | mediana | dp | mín | máx |",
             "|---|---|---|---|---|---|---|"]
    for arch in ["federation", "stadium", "club", "toy"]:
        s = df.loc[df.archetype == arch, "score"]
        lines.append(f"| {ARCH_LABEL[arch]} | {len(s)} | {s.mean():.1f} | "
                     f"{s.median():.1f} | {s.std():.1f} | {s.min():.1f} | "
                     f"{s.max():.1f} |")
    lines += ["", "## Extremos (5 maiores e 5 menores scores)", "",
              "| repo | arquétipo | linguagem | score |", "|---|---|---|---|"]
    ext = pd.concat([df.nlargest(5, "score"), df.nsmallest(5, "score")])
    for _, r in ext.iterrows():
        lines.append(f"| {r['repo']} | {ARCH_LABEL[r['archetype']]} | "
                     f"{r['language']} | {r['score']:.1f} |")
    lines += ["", "Sub-scores por dimensão, sensibilidade e validação: ver "
              "`results/qa_extracao.md`, `results/sensibilidade.md` e "
              "`results/validacao.md`.", ""]
    out_path.write_text("\n".join(lines))


SEQ_BLUE = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]


def fig_archetype_dimensions(scores_csv: Path, out_stem: Path) -> None:
    """Heatmap 4×5: sub-score médio por dimensão em cada arquétipo — a
    evidência visual de que boas práticas não são uniformes entre arquétipos."""
    import pandas as pd
    from matplotlib.colors import LinearSegmentedColormap, Normalize
    df = pd.read_csv(scores_csv)
    cols = [f"subscore_{k}" for k, _ in DIMENSIONS]
    order = (df.groupby("archetype")["score"].median()
             .sort_values(ascending=False).index.tolist())
    m = df.groupby("archetype")[cols].mean().loc[order]

    cmap = LinearSegmentedColormap.from_list("seq", SEQ_BLUE)
    fig, ax = plt.subplots(figsize=(6.8, 3.4), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    im = ax.imshow(m.values, cmap=cmap, norm=Normalize(0, 1), aspect="auto")
    ax.set_xticks(range(5), [lbl.replace("\n", " ") for _, lbl in DIMENSIONS],
                  fontsize=7.5, color=INK_2)
    ax.set_yticks(range(len(order)), [ARCH_LABEL[a] for a in order],
                  fontsize=8.5, color=INK_2)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            v = m.values[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8.5,
                    color="#ffffff" if v > 0.6 else INK)
    ax.set_title("Sub-score médio por dimensão e arquétipo (n=100)",
                 color=INK, fontsize=11, loc="left", pad=12)
    cbar = fig.colorbar(im, shrink=0.85)
    cbar.ax.tick_params(labelsize=7, colors=MUTED)
    cbar.outline.set_visible(False)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(f"{out_stem}.{ext}", facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


PRACTICES = [
    ("artifacts_readme", "README"),
    ("artifacts_license", "Licença"),
    ("security_ci_configured", "CI configurada"),
    ("artifacts_contributing", "CONTRIBUTING"),
    ("security_security_policy", "Política de segurança"),
    ("artifacts_code_of_conduct", "Código de conduta"),
    ("artifacts_issue_template", "Template de issue"),
    ("artifacts_pull_request_template", "Template de PR"),
    ("security_dependency_automation", "Automação de dependências"),
    ("artifacts_funding", "FUNDING"),
    ("artifacts_codeowners", "CODEOWNERS"),
    ("artifacts_governance", "GOVERNANCE"),
]


def fig_practice_prevalence(parquet: Path, out_stem: Path) -> None:
    """Dot plot: % de repositórios com cada prática, por arquétipo."""
    import pandas as pd
    df = pd.read_parquet(parquet)
    rows = []
    for col, label in PRACTICES:
        for arch in ARCH_ORDER:
            share = df.loc[df.archetype == arch, col].astype(bool).mean()
            rows.append((label, arch, share * 100))
    prev = pd.DataFrame(rows, columns=["practice", "arch", "pct"])
    order = (prev.groupby("practice")["pct"].mean()
             .sort_values().index.tolist())

    fig, ax = plt.subplots(figsize=(7.2, 4.8), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    _style(ax)
    ax.grid(axis="y", visible=False)
    for i, practice in enumerate(order):
        sub = prev[prev.practice == practice]
        ax.plot([sub.pct.min(), sub.pct.max()], [i, i], color=GRID,
                linewidth=1.2, zorder=1)
        for _, r in sub.iterrows():
            ax.scatter(r.pct, i, s=34, color=ARCH_COLOR[r.arch],
                       edgecolors=SURFACE, linewidths=0.6, zorder=3)
    ax.set_yticks(range(len(order)), order, fontsize=8, color=INK_2)
    ax.set_xlim(-3, 103)
    ax.set_xlabel("Repositórios com a prática (%)", color=INK_2, fontsize=9)
    ax.set_title("Prevalência das práticas de governança por arquétipo",
                 color=INK, fontsize=11, loc="left", pad=14)
    ax.text(0, 1.02, "n=25 por arquétipo; presença via API + herança de "
            "{org}/.github", transform=ax.transAxes, color=INK_2, fontsize=8)
    handles = [plt.Line2D([], [], marker="o", linestyle="", markersize=6,
                          color=ARCH_COLOR[a], label=ARCH_LABEL[a])
               for a in ARCH_ORDER]
    leg = ax.legend(handles=handles, loc="lower right", fontsize=7.5,
                    frameon=True, framealpha=0.92, facecolor=SURFACE,
                    edgecolor=GRID)
    for txt in leg.get_texts():
        txt.set_color(INK_2)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(f"{out_stem}.{ext}", facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


def _ecdf(ax, values, log_x=False):
    xs = sorted(v for v in values if v is not None and v == v)
    ys = [i / len(xs) for i in range(1, len(xs) + 1)]
    ax.step(xs, ys, where="post", color=INK, linewidth=1.4, zorder=3)
    if log_x:
        ax.set_xscale("log")
    ax.set_ylim(0, 1.02)


def fig_metrics_vs_thresholds(parquet: Path, metrics_yaml: Path,
                              out_stem: Path) -> None:
    """ECDFs das métricas contínuas com os limiares best/worst do catálogo
    sobrepostos — os limiares são anteriores aos dados, nunca ajustados."""
    import pandas as pd
    import yaml
    df = pd.read_parquet(parquet)
    cfg = yaml.safe_load(metrics_yaml.read_text())
    panels = [
        ("responsiveness_median_first_response_hours", "1ª resposta (h)",
         cfg["responsiveness"]["median_first_response_hours"], True),
        ("responsiveness_median_pr_merge_hours", "Merge de PR (h)",
         cfg["responsiveness"]["median_pr_merge_hours"], True),
        ("responsiveness_pr_review_coverage", "Cobertura de revisão",
         cfg["responsiveness"]["pr_review_coverage"], False),
        ("distribution_top1_share", "Share do top-1",
         cfg["distribution"]["top1_share"], False),
        ("distribution_elephant_factor", "Elephant factor",
         cfg["diversity"]["elephant_factor"], False),
        ("distribution_contributor_retention", "Retenção",
         cfg["diversity"]["contributor_retention"], False),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(8.2, 4.8), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    for ax, (col, label, th, log_x) in zip(axes.flat, panels):
        _style(ax)
        vals = df[col].dropna()
        _ecdf(ax, vals.tolist(), log_x=log_x)
        # rótulos escalonados em duas alturas: best acima, worst abaixo,
        # para não colidirem quando os limiares são próximos (ex.: elephant)
        for key, tag, y in (("best", "→1,0", 1.12), ("worst", "→0,0", 1.04)):
            ax.axvline(th[key], color=MUTED, linewidth=1.0, linestyle="--",
                       zorder=2)
            ax.text(th[key], y, f"{th[key]:g}{tag}", fontsize=6.2,
                    color=MUTED, ha="center")
        ax.set_title(f"{label} (n={len(vals)})", fontsize=8.5, color=INK_2,
                     pad=14, loc="left")
        ax.tick_params(labelsize=7)
    fig.suptitle("Distribuições empíricas × limiares absolutos do catálogo",
                 fontsize=11, color=INK, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    for ext in ("png", "pdf"):
        fig.savefig(f"{out_stem}.{ext}", facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


def fig_ranking_stability(full_metrics: Path, metrics_yaml: Path,
                          out_stem: Path) -> None:
    """Ranking base × ranking sob a variante de pesos MAIS disruptiva (±25%),
    para os 100 repositórios. Pontos na diagonal = posição preservada; a
    dispersão honesta em torno dela mostra que só vizinhos quase empatados
    trocam de lugar (o ρ global permanece altíssimo)."""
    import yaml

    from govscore.score.sensitivity import DIMENSIONS as DIMS
    from govscore.score.sensitivity import (
        perturbed_weights,
        scores_for,
        spearman,
    )
    data = json.loads(full_metrics.read_text())["results"]
    subs = [r["subscores"] for r in data]
    base_w = yaml.safe_load(metrics_yaml.read_text())["weights"]

    def ranks(weights):
        s = scores_for(subs, weights)
        order = sorted(range(len(s)), key=lambda i: -(s[i] or 0))
        pos = [0] * len(s)
        for rank, i in enumerate(order):
            pos[i] = rank + 1
        return s, pos

    base_s, base_r = ranks(base_w)
    worst = None
    for dim in DIMS:
        for f in (1.25, 0.75):
            w = perturbed_weights(base_w, dim, f)
            rho = spearman(base_s, scores_for(subs, w))
            if worst is None or rho < worst[0]:
                worst = (rho, dim, f, ranks(w)[1])
    rho, dim, factor, var_r = worst
    tag = f"{dim} {'+' if factor > 1 else '−'}25%"

    fig, ax = plt.subplots(figsize=(6.4, 6.0), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    _style(ax)
    ax.plot([0, 101], [0, 101], color=BASELINE, linewidth=1.0, zorder=1)
    for i in range(len(subs)):
        ax.scatter(base_r[i], var_r[i], s=20,
                   color=ARCH_COLOR[data[i]["archetype"]],
                   edgecolors=SURFACE, linewidths=0.4, zorder=3)
    ax.set_xlim(0, 101)
    ax.set_ylim(101, 0)
    ax.set_xlabel("Posição no ranking (pesos da literatura)", color=INK_2,
                  fontsize=9)
    ax.set_ylabel(f"Posição sob a variante mais disruptiva ({tag})",
                  color=INK_2, fontsize=9)
    ax.set_title("Estabilidade do ranking sob perturbação de pesos (n=100)",
                 color=INK, fontsize=11, loc="left", pad=14)
    ax.text(0, 1.02, f"pior caso entre as 10 variantes ±25%: ρ = {rho:.3f}; "
            "pontos na diagonal preservam a posição", transform=ax.transAxes,
            color=INK_2, fontsize=8)
    handles = [plt.Line2D([], [], marker="o", linestyle="", markersize=6,
                          color=ARCH_COLOR[a], label=ARCH_LABEL[a])
               for a in ARCH_ORDER]
    leg = ax.legend(handles=handles, loc="lower right", fontsize=7.5,
                    frameon=True, framealpha=0.92, facecolor=SURFACE,
                    edgecolor=GRID)
    for txt in leg.get_texts():
        txt.set_color(INK_2)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(f"{out_stem}.{ext}", facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


def _fisher_ci(rho: float, n: int) -> tuple[float, float]:
    """IC 95% aproximado para ρ de Spearman via Fisher-z (variância
    1,06/(n−3)) — aproximação declarada na figura."""
    import math
    z = math.atanh(max(min(rho, 0.999), -0.999))
    se = math.sqrt(1.06 / (n - 3))
    return math.tanh(z - 1.96 * se), math.tanh(z + 1.96 * se)


def fig_validation_forest(validation_json: Path, out_stem: Path) -> None:
    """Forest plot: ρ por indicador, global e por arquétipo, com IC 95%."""
    val = json.loads(validation_json.read_text())
    indicators = [("scorecard", "OpenSSF Scorecard"), ("forks", "Forks"),
                  ("stars", "Stars")]
    rows_order = [("global", None)] + [(a, a) for a in ARCH_ORDER]

    fig, axes = plt.subplots(1, 3, figsize=(8.4, 3.6), dpi=200, sharey=True)
    fig.patch.set_facecolor(SURFACE)
    for ax, (ind, title) in zip(axes, indicators):
        _style(ax)
        ax.grid(axis="y", visible=False)
        ax.axvline(0, color=BASELINE, linewidth=0.9, zorder=1)
        for y, (kind, arch) in enumerate(rows_order):
            g = (val["global"][ind] if kind == "global"
                 else val["by_archetype"][arch][ind])
            rho, n = g.get("rho"), g.get("n", 0)
            if rho is None or n < 4:
                ax.text(0, y, f"n={n} — sem teste", fontsize=6.5,
                        color=MUTED, ha="center", va="center")
                continue
            color = INK if kind == "global" else ARCH_COLOR[arch]
            lo, hi = _fisher_ci(rho, n)
            ax.plot([lo, hi], [y, y], color=color, linewidth=1.4, zorder=2)
            ax.scatter([rho], [y], s=26, color=color, zorder=3,
                       edgecolors=SURFACE, linewidths=0.5)
            ax.text(1.04, y, f"n={n}", fontsize=6.5, color=MUTED, va="center")
        ax.set_xlim(-1.05, 1.05)
        ax.set_ylim(len(rows_order) - 0.5, -0.5)
        ax.set_title(title, fontsize=9, color=INK_2, loc="left")
        ax.tick_params(labelsize=7)
    axes[0].set_yticks(range(len(rows_order)),
                       ["Global"] + [ARCH_LABEL[a] for a in ARCH_ORDER],
                       fontsize=8, color=INK_2)
    fig.suptitle("Validação externa: ρ de Spearman com IC 95% "
                 "(Fisher-z, aproximado; por arquétipo = exploratório)",
                 fontsize=10.5, color=INK, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    for ext in ("png", "pdf"):
        fig.savefig(f"{out_stem}.{ext}", facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


MISSING_METRICS = [
    ("security_release_notes_share", "Notas de release"),
    ("responsiveness_median_issue_close_hours", "Fechamento de issues*"),
    ("distribution_contributor_retention", "Retenção"),
    ("responsiveness_median_first_response_hours", "1ª resposta"),
    ("responsiveness_median_pr_merge_hours", "Merge de PR"),
    ("responsiveness_pr_review_coverage", "Cobertura de revisão"),
    ("responsiveness_pr_merge_ratio", "Razão de merge"),
]


def fig_missingness(parquet: Path, out_stem: Path) -> None:
    """Matriz de faltantes (% None) por métrica × arquétipo — apêndice QA."""
    import pandas as pd
    from matplotlib.colors import LinearSegmentedColormap, Normalize
    df = pd.read_parquet(parquet)
    m = pd.DataFrame({
        label: df.groupby("archetype")[col].apply(lambda s: s.isna().mean())
        for col, label in MISSING_METRICS
    }).T[list(ARCH_ORDER)] * 100

    cmap = LinearSegmentedColormap.from_list("miss", ["#fcfcfb"] + SEQ_BLUE)
    fig, ax = plt.subplots(figsize=(6.4, 3.6), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    im = ax.imshow(m.values, cmap=cmap, norm=Normalize(0, 100), aspect="auto")
    ax.set_xticks(range(4), [ARCH_LABEL[a] for a in ARCH_ORDER],
                  fontsize=8, color=INK_2)
    ax.set_yticks(range(len(m)), m.index, fontsize=8, color=INK_2)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            v = m.values[i, j]
            ax.text(j, i, f"{v:.0f}%", ha="center", va="center", fontsize=8,
                    color="#ffffff" if v > 55 else INK)
    ax.set_title("Métricas faltantes por arquétipo (omitidas do score, "
                 "nunca imputadas)", color=INK, fontsize=10.5, loc="left",
                 pad=12)
    ax.text(0, -0.14, "*extraída para comparabilidade com o piloto; fora do "
            "score", transform=ax.transAxes, color=MUTED, fontsize=7)
    cbar = fig.colorbar(im, shrink=0.85)
    cbar.ax.tick_params(labelsize=7, colors=MUTED)
    cbar.outline.set_visible(False)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(f"{out_stem}.{ext}", facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


DIM_LABEL = {"artifacts": "D1 Artefatos", "distribution": "D2 Distribuição",
             "responsiveness": "D3 Responsividade",
             "diversity": "D4 Diversidade", "security": "D5 Segurança"}


def fig_discriminant(robustness_json: Path, out_stem: Path) -> None:
    """Lollipop: ρ vs Scorecard do score cheio, do composto social D2/D3/D4
    e de cada dimensão — a evidência de validade discriminante."""
    d = json.loads(robustness_json.read_text())["discriminante"]
    rows = ([("Score (5 dimensões)", d["rho_score_cheio"], INK),
             ("Composto social D2/D3/D4", d["rho_composto_social"], INK_2)]
            + [(DIM_LABEL[k], v, "#2a78d6")
               for k, v in d["por_dimensao"].items()])

    fig, ax = plt.subplots(figsize=(6.8, 3.4), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    _style(ax)
    ax.grid(axis="y", visible=False)
    for i, (label, rho, color) in enumerate(rows):
        ax.plot([0, rho], [i, i], color=GRID, linewidth=1.2, zorder=1)
        ax.scatter(rho, i, s=42, color=color, edgecolors=SURFACE,
                   linewidths=0.6, zorder=3)
        ax.text(rho + 0.02, i, f"{rho:.3f}", va="center", fontsize=8,
                color=INK_2)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows], fontsize=8.5,
                  color=INK_2)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("ρ de Spearman vs OpenSSF Scorecard (n=53)",
                  color=INK_2, fontsize=9)
    ax.set_title("Validade discriminante: o que o score mede além do "
                 "Scorecard", color=INK, fontsize=11, loc="left", pad=14)
    ax.text(0, 1.02, "composto social < agregado (Steiger z=2,99, p=0,003): "
            "as dimensões sociais medem construto distinto",
            transform=ax.transAxes, color=INK_2, fontsize=8)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(f"{out_stem}.{ext}", facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


def main(data_dir: Path | None = None, results_dir: Path | None = None,
         fig_dir: Path | None = None, config_dir: Path | None = None) -> Path:
    """Gera todas as figuras a partir de `data_dir` (default data/processed)
    e `results_dir` (default results/), gravando em `fig_dir` (default
    figures/). Diretórios próprios permitem regenerar o catálogo v2 sem
    sobrescrever as figuras v1 arquivadas. Devolve `fig_dir`."""
    data_dir = Path(data_dir) if data_dir else ROOT / "data" / "processed"
    results_dir = Path(results_dir) if results_dir else ROOT / "results"
    fig_dir = Path(fig_dir) if fig_dir else FIG_DIR
    config_dir = Path(config_dir) if config_dir else ROOT / "config"
    fig_dir.mkdir(parents=True, exist_ok=True)

    fig_sample_map(config_dir / "sample_full.yaml",
                   fig_dir / "fig_amostra_classificacao")
    fig_pilot_subscores(data_dir / "pilot_scores.json",
                        fig_dir / "fig_pilotos_subscores")
    fig_sample_languages(config_dir / "sample_full.yaml",
                         fig_dir / "fig_amostra_linguagens")
    fig_pilot_ranking(data_dir / "pilot_scores.json",
                      fig_dir / "fig_pilotos_ranking")
    scores_csv = data_dir / "scores.csv"
    if scores_csv.exists():  # figuras da fase completa (itens 5–7)
        results_dir.mkdir(parents=True, exist_ok=True)
        fig_score_boxplot(scores_csv, fig_dir / "fig_score_boxplot")
        fig_dimension_heatmap(scores_csv, fig_dir / "fig_dimensoes_heatmap")
        fig_validation_scatters(
            data_dir / "external_indicators.csv",
            results_dir / "validation.json",
            fig_dir / "fig_validacao_scatters")
        write_tcc_tables(scores_csv, results_dir / "tabelas_tcc.md")
        parquet = data_dir / "metrics.parquet"
        full_metrics = data_dir / "full_metrics.json"
        metrics_yaml = config_dir / "metrics.yaml"
        validation_json = results_dir / "validation.json"
        fig_archetype_dimensions(scores_csv, fig_dir / "fig_dimensoes_arquetipo")
        fig_practice_prevalence(parquet, fig_dir / "fig_praticas_prevalencia")
        fig_metrics_vs_thresholds(parquet, metrics_yaml,
                                  fig_dir / "fig_metricas_limiares")
        fig_ranking_stability(full_metrics, metrics_yaml,
                              fig_dir / "fig_ranking_estabilidade")
        fig_validation_forest(validation_json,
                              fig_dir / "fig_validacao_forest")
        fig_missingness(parquet, fig_dir / "fig_faltantes")
        robustness_json = results_dir / "robustness.json"
        if robustness_json.exists():
            fig_discriminant(robustness_json,
                             fig_dir / "fig_validade_discriminante")
    print(f"figuras em {fig_dir}/")
    return fig_dir


def _cli(argv: list[str] | None = None) -> None:
    """`python -m govscore.figures [--data-dir] [--results-dir] [--fig-dir]`
    (alvo `make figures`); os mesmos flags existem em `govscore figures`."""
    import argparse
    ap = argparse.ArgumentParser(prog="govscore.figures")
    ap.add_argument("--data-dir", type=Path, default=None,
                    help="default: data/processed")
    ap.add_argument("--results-dir", type=Path, default=None,
                    help="default: results")
    ap.add_argument("--fig-dir", type=Path, default=None,
                    help="default: figures")
    args = ap.parse_args(argv)
    main(args.data_dir, args.results_dir, args.fig_dir)


if __name__ == "__main__":
    _cli()
