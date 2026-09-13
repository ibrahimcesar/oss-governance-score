"""Evidência de locus de coordenação fora do GitHub (instrumento DESCRITIVO).

Registro: docs/decisions/2026-09-13-catalogo-v2-reparo-d1-d5.md, seção
"Instrumentos complementares". Varre as mensagens de commit já em cache
(`data/raw/<owner>__<repo>/commits_12m_p*.json`, páginas REST coletadas na
amostragem de 2026-07-20 — nunca reconsulta a API) em busca de trailers que
denunciam revisão em outra plataforma:

- Gerrit: `Reviewed-on:` (acompanhado de `Change-Id:`);
- Phabricator: `Differential Revision:`;
- Piper/Copybara (Google): `PiperOrigin-RevId:`;
- lista de e-mail do kernel: `Link: https://lore.kernel.org/...`.

`Signed-off-by:` e committer ≠ autor NÃO são discriminativos e entram só como
contexto: o DCO (`Signed-off-by`) é adotado por projetos que revisam no
próprio GitHub, e merges/squashes pela interface web registram
`GitHub <noreply@github.com>` como committer. A regra de sinalização é a do
registro: espelho declarado na descrição OU share ≥ 0,5 de um trailer de
plataforma (Gerrit, Phabricator, Piper).

Limites declarados: as páginas em cache são as da classificação de
arquétipos (early stop ao confirmar Federação; teto de páginas) — a share é
calculada sobre os commits EM CACHE, não sobre toda a janela. Nada aqui
altera scores: uma regra de D3 estrutural para espelhos reverteria a decisão
"mantido" de 2026-09-12 sobre a mesma evidência. O cenário
`sem_locus_externo` da robustez usa o conjunto PRÉ-REGISTRADO
(`robustness.LOCUS_EXTERNAL_REPOS ∪ MIRROR_REPOS`); esta tabela serve para
auditar esse conjunto, não para redefini-lo.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# Trailers procurados em cada mensagem (início de linha, multilinha).
TRAILER_PATTERNS: dict[str, re.Pattern] = {
    "reviewed_on": re.compile(r"^Reviewed-on:", re.M),
    "change_id": re.compile(r"^Change-Id:", re.M),
    "differential_revision": re.compile(r"^Differential Revision:", re.M),
    "piper_origin": re.compile(r"^PiperOrigin-RevId:", re.M),
    "lore_link": re.compile(r"^Link: https?://lore\.kernel\.org", re.M),
    "signed_off_by": re.compile(r"^Signed-off-by:", re.M),
}
# Só estes três discriminam plataforma de revisão (regra do registro).
PLATFORM_TRAILERS = ("reviewed_on", "differential_revision", "piper_origin")
# Contexto, não discriminativos (ver docstring do módulo).
CONTEXT_SIGNALS = ("change_id", "lore_link", "signed_off_by",
                   "committer_neq_author")
MIRROR_DESCRIPTION = re.compile(r"mirror|read-only|publish-only", re.I)
EXTERNAL_SHARE_MIN = 0.5

SHARE_KEYS = tuple(TRAILER_PATTERNS) + ("committer_neq_author",)


def _repo_dir(cache_root: Path | str, repo: str) -> Path:
    return Path(cache_root) / repo.replace("/", "__")


def _load_data(path: Path):
    """Conteúdo `data` de um arquivo de cache do GitHubClient (None em 404)."""
    payload = json.loads(path.read_text())
    return payload.get("data") if isinstance(payload, dict) else payload


def iter_cached_commits(cache_root: Path | str, repo: str) -> list[dict]:
    """Concatena as páginas `commits_12m_p*.json` em cache (ordem numérica).
    Páginas com `data` nulo (404/409 cacheado) são ignoradas."""
    items: list[dict] = []
    for f in sorted(_repo_dir(cache_root, repo).glob("commits_12m_p*.json")):
        data = _load_data(f)
        if isinstance(data, list):
            items.extend(data)
    return items


def commit_trailer_shares(commits: list[dict]) -> dict:
    """Shares (0–1) de cada trailer e de committer ≠ autor sobre os commits
    dados; None quando não há commits. Compara e-mails de `commit.author` e
    `commit.committer` (os logins de `author`/`committer` podem ser nulos
    quando o e-mail não está vinculado a uma conta — por isso não são usados).
    """
    n = len(commits)
    counts = {k: 0 for k in TRAILER_PATTERNS}
    neq = 0
    for c in commits:
        meta = c.get("commit") or {}
        msg = meta.get("message") or ""
        for key, pat in TRAILER_PATTERNS.items():
            if pat.search(msg):
                counts[key] += 1
        author = ((meta.get("author") or {}).get("email") or "").strip().lower()
        committer = ((meta.get("committer") or {}).get("email") or "").strip().lower()
        if author != committer:
            neq += 1
    shares: dict = {k: (v / n if n else None) for k, v in counts.items()}
    shares["committer_neq_author"] = neq / n if n else None
    shares["n_commits"] = n
    return shares


def is_external_locus(row: dict) -> bool:
    """Regra pré-registrada: espelho declarado OU share ≥ 0,5 de um trailer de
    plataforma (Reviewed-on, Differential Revision, PiperOrigin-RevId).
    `signed_off_by` e `committer_neq_author` NÃO participam (ver módulo)."""
    if row.get("mirror_declared"):
        return True
    return max((row.get(k) or 0.0) for k in PLATFORM_TRAILERS) >= EXTERNAL_SHARE_MIN


def scan_commit_messages(cache_root: Path | str, repo: str) -> dict:
    """Linha de evidência de um repositório a partir do cache (sem rede).

    Chaves: repo, n_commits, shares (SHARE_KEYS), has_issues, mirror_declared
    (descrição casa /mirror|read-only|publish-only/i), mirror_url (informativo,
    não pontua na regra) e external_locus (is_external_locus).
    """
    row: dict = {"repo": repo, **commit_trailer_shares(
        iter_cached_commits(cache_root, repo))}
    meta_path = _repo_dir(cache_root, repo) / "repo_metadata.json"
    meta = (_load_data(meta_path) if meta_path.exists() else None) or {}
    row["has_issues"] = meta.get("has_issues")
    row["mirror_declared"] = bool(
        MIRROR_DESCRIPTION.search(meta.get("description") or ""))
    row["mirror_url"] = meta.get("mirror_url")
    row["external_locus"] = is_external_locus(row)
    return row


def locus_table(cache_root: Path | str, repos: list) -> list[dict]:
    """Uma linha por repositório. `repos` aceita nomes (`owner/name`) ou
    entradas da amostra (`{"repo": ..., "archetype": ...}`), caso em que o
    arquétipo é carregado para o relatório."""
    rows = []
    for entry in repos:
        repo = entry["repo"] if isinstance(entry, dict) else entry
        row = scan_commit_messages(cache_root, repo)
        if isinstance(entry, dict) and entry.get("archetype"):
            row["archetype"] = entry["archetype"]
        rows.append(row)
    return rows


def _s(v) -> str:
    return "—" if v is None else f"{v:.2f}"


def _yn(v) -> str:
    return "—" if v is None else ("sim" if v else "não")


def flag_reasons(row: dict) -> list[str]:
    """Motivos nominais da sinalização (para a lista do relatório)."""
    reasons = []
    if row.get("mirror_declared"):
        reasons.append("espelho declarado na descrição")
    labels = {"reviewed_on": "Reviewed-on (Gerrit)",
              "differential_revision": "Differential Revision (Phabricator)",
              "piper_origin": "PiperOrigin-RevId (Piper)"}
    for k in PLATFORM_TRAILERS:
        if (row.get(k) or 0.0) >= EXTERNAL_SHARE_MIN:
            reasons.append(f"{labels[k]} em {row[k]:.0%} dos commits")
    return reasons


def report(rows: list[dict]) -> str:
    """Markdown PT-BR para results/locus_evidence.md. Descritivo: lista a
    evidência, os sinalizados e a conferência com o conjunto pré-registrado
    do cenário `sem_locus_externo`. Não altera score algum."""
    from govscore.robustness import LOCUS_EXTERNAL_REPOS, MIRROR_REPOS

    lines = ["# Evidência de locus de coordenação (instrumento descritivo — "
             "catálogo v2)", "",
             "Fonte: mensagens de commit em cache (`commits_12m_p*.json`, "
             "páginas da amostragem de 2026-07-20 — early stop/teto de "
             "páginas: a share é sobre os commits EM CACHE) e "
             "`repo_metadata.json`. Registro: "
             "`docs/decisions/2026-09-13-catalogo-v2-reparo-d1-d5.md`. "
             "**Nenhum score é alterado por esta tabela.**", "",
             "Regra de sinalização (pré-registrada): espelho declarado na "
             "descrição (`/mirror|read-only|publish-only/i`) OU share ≥ "
             f"{EXTERNAL_SHARE_MIN:.1f} de um trailer de plataforma — "
             "`Reviewed-on:` (Gerrit), `Differential Revision:` "
             "(Phabricator), `PiperOrigin-RevId:` (Piper). `Signed-off-by:` "
             "e committer ≠ autor NÃO discriminam (DCO em projetos revisados "
             "no GitHub; merges pela interface web têm `GitHub` como "
             "committer) — colunas de contexto, assim como `Change-Id:` e "
             "`Link: lore.kernel.org`.", "",
             "| repo | arquétipo | commits | Reviewed-on | Change-Id | "
             "Diff. Revision | PiperOrigin | lore | Signed-off | "
             "committer≠autor | issues | espelho declarado | sinal |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda x: (not x.get("external_locus"),
                                         x["repo"].lower())):
        lines.append(
            f"| `{r['repo']}` | {r.get('archetype') or '—'} | "
            f"{r.get('n_commits', 0)} | {_s(r.get('reviewed_on'))} | "
            f"{_s(r.get('change_id'))} | {_s(r.get('differential_revision'))} "
            f"| {_s(r.get('piper_origin'))} | {_s(r.get('lore_link'))} | "
            f"{_s(r.get('signed_off_by'))} | "
            f"{_s(r.get('committer_neq_author'))} | "
            f"{_yn(r.get('has_issues'))} | {_yn(r.get('mirror_declared'))} | "
            f"{'**sim**' if r.get('external_locus') else 'não'} |")
    lines.append("")

    flagged = [r for r in rows if r.get("external_locus")]
    lines += [f"## Repositórios sinalizados ({len(flagged)})", ""]
    if flagged:
        lines += [f"- `{r['repo']}` — " + "; ".join(flag_reasons(r))
                  for r in sorted(flagged, key=lambda x: x["repo"].lower())]
    else:
        lines.append("Nenhum.")
    lines.append("")

    pre = set(LOCUS_EXTERNAL_REPOS) | set(MIRROR_REPOS)
    seen = {r["repo"] for r in rows}
    flagged_names = {r["repo"] for r in flagged}
    extra = sorted(flagged_names - pre)
    missing = sorted((pre & seen) - flagged_names)
    lines += ["## Conferência com o conjunto pré-registrado "
              "(`sem_locus_externo`)", "",
              "Conjunto do registro (LOCUS_EXTERNAL_REPOS ∪ MIRROR_REPOS): "
              + ", ".join(f"`{x}`" for x in sorted(pre)) + ".", "",
              "- Sinalizados fora do conjunto: "
              + (", ".join(f"`{x}`" for x in extra) if extra else "nenhum")
              + ".",
              "- No conjunto sem sinal nos commits em cache: "
              + (", ".join(f"`{x}`" for x in missing) if missing else "nenhum")
              + ".", "",
              "Divergências são reportadas, não corrigidas: o conjunto do "
              "cenário é o pré-registrado (ajuste = novo registro).", ""]
    return "\n".join(lines)
