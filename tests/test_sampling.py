"""Testes da amostragem estratificada (plano §3.1–3.2)."""
from govscore.sampling import classify, commit_author_counts, screen

T = {
    "min_commits_per_contributor": 2,
    "federation_min_contributors": 100,
    "stadium_max_contributors": 10,
    "club_min_contributors": 20,
    "toy_max_contributors": 3,
    "stars_high_min": 10000,
    "club_stars_max": 5000,
    "toy_stars_max": 500,
}


# ------------------------------------------------------------- classificação
def test_classify_matriz_da_secao_3_1():
    assert classify(500, 100_000, T) == "federation"   # caso kubernetes
    assert classify(5, 60_000, T) == "stadium"         # caso express
    assert classify(40, 2_000, T) == "club"            # caso astropy
    assert classify(1, 100, T) == "toy"


def test_classify_zonas_ambiguas_retornam_none():
    assert classify(50, 20_000, T) is None      # 11–99 ativos com stars altas
    assert classify(10, 7_000, T) is None       # stars entre 5k e 10k
    assert classify(10, 300, T) is None         # 4–19 ativos com stars baixas
    assert classify(25, 6_000, T) is None       # clube exige < 5000 stars


def test_classify_clube_aceita_stars_baixas():
    # nicho com comunidade ativa: < 500 stars mas ≥20 contribuidores é Clube
    assert classify(30, 400, T) == "club"


# ------------------------------------------------------------------- triagem
EXCL = {
    "topics": ["awesome", "tutorial"],
    "name_patterns": ["^awesome[-_.]", "interview"],
    "repos": ["kubernetes/kubernetes"],
}


def _item(**kw):
    base = {"full_name": "org/repo", "fork": False, "archived": False,
            "is_template": False, "mirror_url": None, "language": "Python",
            "topics": []}
    base.update(kw)
    return base


def test_screen_aceita_software_comum():
    assert screen(_item(), EXCL) is None


def test_screen_exclui_nao_software_e_pilotos():
    assert screen(_item(topics=["cli", "awesome"]), EXCL) is not None
    assert screen(_item(full_name="x/awesome-python"), EXCL) is not None
    assert screen(_item(full_name="x/interview-prep"), EXCL) is not None
    assert screen(_item(language=None), EXCL) is not None
    assert screen(_item(fork=True), EXCL) is not None
    assert screen(_item(archived=True), EXCL) is not None
    assert screen(_item(full_name="kubernetes/kubernetes"), EXCL) is not None


# ----------------------------------------------------- contagem de autores
def _commit(login=None, email=None):
    c = {"author": {"login": login} if login else None,
         "commit": {"author": {"email": email or "x@x.com"}}}
    return c


def test_commit_author_counts_exclui_bots_e_usa_fallback_email():
    pages = [[
        _commit(login="alice"), _commit(login="alice"),
        _commit(login="dependabot[bot]"), _commit(login="renovate-bot"),
        _commit(login=None, email="bob@corp.com"),
        _commit(login=None, email="bob@corp.com"),
    ]]
    counts = commit_author_counts(pages)
    assert counts["alice"] == 2
    assert counts["bob@corp.com"] == 2
    assert not any("bot" in k for k in counts)
    # proxy da §3.1: autores com ≥2 commits
    assert sum(1 for v in counts.values() if v >= 2) == 2
