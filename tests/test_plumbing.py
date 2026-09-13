"""Encanamento de diretórios (catálogo v2, M4): `--data-dir`/`--results-dir`
nas análises, retomada filtrada por `catalog_version`, validação sem rede.

Tudo roda em diretórios temporários; nada é escrito sob data/ ou results/.
"""
import json
import random
import shutil

import pytest
import yaml

from govscore import cli
from govscore.run_full import load_progress, run_sample
from govscore.score.scoring import compute_score, compute_subscores

CFG = yaml.safe_load(open("config/metrics.yaml"))
ARCHETYPES = ("federation", "stadium", "club", "toy")


# ------------------------------------------------------------ (c) progresso
def test_load_progress_filtra_catalog_version(tmp_path):
    p = tmp_path / "p.jsonl"
    recs = [{"repo": "a/v1-implicito", "backend": "api+git", "score": 1},
            {"repo": "b/v1", "backend": "api+git", "score": 2,
             "catalog_version": "v1"},
            {"repo": "c/v2", "backend": "api+git", "score": 3,
             "catalog_version": "v2"},
            {"repo": "d/v1-nulo", "backend": "api+git", "score": 4,
             "catalog_version": None}]
    p.write_text("\n".join(json.dumps(r) for r in recs) + "\n")
    assert set(load_progress(p)) == {"a/v1-implicito", "b/v1", "c/v2",
                                     "d/v1-nulo"}
    # sem a chave (ou com null explícito) conta como v1 — registros
    # anteriores ao reparo
    assert set(load_progress(p, catalog_version="v1")) == {
        "a/v1-implicito", "b/v1", "d/v1-nulo"}
    assert set(load_progress(p, catalog_version="v2")) == {"c/v2"}
    # combinado com o filtro de backend já existente
    assert load_progress(p, expected_backend="git", catalog_version="v2") == {}


def test_run_sample_retoma_so_o_catalogo_pedido(tmp_path):
    p = tmp_path / "p.jsonl"
    p.write_text(json.dumps({"repo": "a/b", "backend": "api+git", "score": 9,
                             "catalog_version": "v2"}) + "\n")
    calls = []

    def extract(repo):
        calls.append(repo)
        return _synthetic_results(1)[0]

    run_sample([{"repo": "a/b"}], extract, CFG, progress_path=p,
               expected_backend="api+git", catalog_version="v1")
    assert calls == ["a/b"]  # registro v2 não serve como retomada de v1


# --------------------------------------------------------------- fixtures
def _synthetic_results(n_per_arch: int = 3, seed: int = 7) -> list[dict]:
    """Dataset sintético determinístico com a mesma estrutura de
    full_metrics.json (4 arquétipos), pontuado com o catálogo congelado."""
    rng = random.Random(seed)
    out = []
    for arch in ARCHETYPES:
        for _ in range(n_per_arch):
            i = len(out)
            m = {
                "repo": f"org{i}/proj{i}", "archetype": arch,
                "language": rng.choice(["python", "go", "rust"]),
                "stars": rng.randint(50, 50_000), "forks": rng.randint(5, 5_000),
                "extracted_at": "2026-07-24", "backend": "api+git",
                "artifacts": {item: rng.random() < 0.6
                              for item in CFG["artifacts"]["items"]},
                "security": {item: rng.random() < 0.5
                             for item in CFG["security"]["items"]},
                "distribution": {
                    "top1_share": rng.uniform(0.1, 0.9),
                    "hhi": rng.uniform(0.05, 0.8),
                    "truck_factor": rng.randint(1, 10),
                    "contributors_5plus": rng.randint(0, 50),
                    "commit_entropy": rng.uniform(0.2, 0.95),
                    "elephant_factor": rng.randint(1, 5),
                    "contributor_retention": rng.uniform(0.1, 0.9)},
                "responsiveness": {
                    "median_first_response_hours": rng.uniform(1, 500),
                    "median_pr_merge_hours": rng.uniform(1, 800),
                    "pr_merge_ratio": rng.uniform(0.2, 0.9),
                    "pr_review_coverage": rng.uniform(0.1, 1.0),
                    "n_issues_sampled": 20, "n_first_responses": 10},
            }
            m["artifacts"]["health_percentage"] = 50
            m["security"]["releases_12m"] = rng.randint(0, 30)
            m["security"]["release_notes_share"] = rng.random()
            m["subscores"] = compute_subscores(m, CFG)
            m["score"] = compute_score(m["subscores"], CFG["weights"])
            out.append(m)
    return out


def _write_dataset(data_dir, results):
    data_dir.mkdir(parents=True)
    (data_dir / "full_metrics.json").write_text(
        json.dumps({"results": results, "errors": []}))
    # scorecard para 2 de cada 3; dependentes só para alguns
    lines = ["repo,scorecard,dependents"]
    for i, r in enumerate(results):
        sc = "" if i % 3 == 2 else f"{3 + (i * 7) % 6 + 0.1 * i:.2f}"
        dep = str(100 * i) if i % 4 == 0 else ""
        lines.append(f"{r['repo']},{sc},{dep}")
    (data_dir / "external_indicators.csv").write_text("\n".join(lines) + "\n")


# ------------------------------------------------------ (b) robustez/sensib.
def test_run_all_usa_diretorios_informados(tmp_path):
    from govscore.robustness import run_all
    data_dir, results_dir = tmp_path / "processed", tmp_path / "results"
    _write_dataset(data_dir, _synthetic_results())
    res = run_all(data_dir=data_dir, results_dir=results_dir)
    for key in ("limiar_normalizacao", "reclassificacao", "discriminante",
                "suspeitos", "imputacao", "cobertura_scorecard",
                "stars_flags", "valores_referencia"):
        assert key in res
    assert (results_dir / "robustez.md").read_text().startswith("# Robustez")
    dumped = json.loads((results_dir / "robustness.json").read_text())
    assert dumped["valores_referencia"].keys() == set(ARCHETYPES)
    # sem results_dir nada é gravado (apenas cálculo): nenhum arquivo novo
    before = set(tmp_path.rglob("*"))
    again = run_all(data_dir=data_dir)
    assert set(tmp_path.rglob("*")) == before
    assert json.dumps(again, sort_keys=True) == json.dumps(res, sort_keys=True)
    # config_dir é lido de fato (catálogo, amostra e limiares de arquétipo)
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    for name in ("metrics.yaml", "sample_full.yaml", "sampling.yaml"):
        shutil.copy(cli.ROOT / "config" / name, cfg_dir / name)
    same = run_all(data_dir=data_dir, config_dir=cfg_dir)
    assert json.dumps(same, sort_keys=True) == json.dumps(res, sort_keys=True)
    with pytest.raises(FileNotFoundError):
        run_all(data_dir=data_dir, config_dir=tmp_path / "sem-config")


def test_cmd_robustness_e_sensitivity_gravam_em_results_dir(tmp_path, capsys):
    data_dir, results_dir = tmp_path / "processed", tmp_path / "out" / "results"
    _write_dataset(data_dir, _synthetic_results())
    cli.cmd_sensitivity(data_dir, results_dir)
    assert (results_dir / "sensibilidade.md").exists()
    sens = json.loads((results_dir / "sensitivity.json").read_text())
    assert sens["n"] == 12
    cli.cmd_robustness(data_dir, results_dir)
    assert (results_dir / "robustness.json").exists()
    assert "# Robustez" in capsys.readouterr().out


# ----------------------------------------------------------- (b) validação
def _seed_external_cache(raw_dir, results, fetched_at="2026-07-25T10:00:00Z"):
    for i, r in enumerate(results):
        d = raw_dir / r["repo"].replace("/", "__")
        d.mkdir(parents=True)
        data = None if i % 3 == 2 else {"score": 2.0 + i * 0.5}
        (d / "openssf_scorecard.json").write_text(json.dumps(
            {"url": "x", "fetched_at": fetched_at, "data": data}))


@pytest.fixture
def no_network(monkeypatch):
    """Qualquer tentativa de GET falha o teste — a validação v2 é offline."""
    from govscore.validate import external

    def _boom(*a, **kw):
        raise AssertionError("chamada de rede indevida")
    monkeypatch.setattr(external.requests, "get", _boom)
    return external


def test_cached_get_json_offline_exige_cache(tmp_path, no_network, monkeypatch):
    external = no_network
    monkeypatch.setattr(external, "RAW_DIR", tmp_path / "raw")
    with pytest.raises(external.CacheMissError):
        external.fetch_scorecard("a/b", offline=True)
    # com cache, offline devolve o valor sem tocar a rede
    d = tmp_path / "raw" / "a__b"  # _cache_path já criou o diretório
    d.mkdir(parents=True, exist_ok=True)
    (d / "openssf_scorecard.json").write_text(json.dumps(
        {"url": "x", "fetched_at": "2026-07-25T10:00:00Z", "data": {"score": 7.5}}))
    assert external.fetch_scorecard("a/b", offline=True) == 7.5
    assert external.cache_fetched_dates("a/b") == ["2026-07-25"]
    assert external.external_fetched_range(["a/b", "c/d"]) == "2026-07-25"
    assert external.external_fetched_range(["c/d"]) is None


def test_cmd_validate_offline_e_epoca_externa(tmp_path, no_network, monkeypatch):
    external = no_network
    monkeypatch.setattr(external, "RAW_DIR", tmp_path / "raw")
    results = _synthetic_results()
    for r in results:
        r["language"] = None  # sem ecossistema → só o Scorecard é consultado
    data_dir, results_dir = tmp_path / "processed", tmp_path / "results"
    _write_dataset(data_dir, results)
    _seed_external_cache(tmp_path / "raw", results)

    # época derivada do fetched_at do cache (nunca date.today())
    res = cli.cmd_validate(data_dir, results_dir, offline=True)
    assert res["meta"]["external_fetched_at"] == "2026-07-25"
    assert res["meta"]["stars_snapshot"] == "2026-07-24→2026-07-24"
    assert res["global"]["scorecard"]["n"] == 8
    saved = json.loads((results_dir / "validation.json").read_text())
    assert saved["meta"]["external_fetched_at"] == "2026-07-25"
    assert (results_dir / "validacao.md").exists()
    assert (data_dir / "external_indicators.csv").exists()

    # override explícito (carregar a data v1 para o relatório v2)
    res = cli.cmd_validate(data_dir, results_dir,
                           external_fetched_at="2026-07-26", offline=True)
    assert res["meta"]["external_fetched_at"] == "2026-07-26"

    # cache incompleto em modo offline é erro, não consulta
    (tmp_path / "raw" / "org0__proj0" / "openssf_scorecard.json").unlink()
    with pytest.raises(external.CacheMissError):
        cli.cmd_validate(data_dir, results_dir, offline=True)


def test_cmd_validate_sem_cache_algum_avisa_data_de_hoje(tmp_path, no_network,
                                                        monkeypatch, capsys):
    """Só sem indicador algum em cache a época recai em hoje — com aviso em
    stderr, nunca em silêncio. Dataset vazio: nenhuma consulta é feita."""
    from datetime import date
    external = no_network
    monkeypatch.setattr(external, "RAW_DIR", tmp_path / "raw")
    data_dir, results_dir = tmp_path / "processed", tmp_path / "results"
    _write_dataset(data_dir, [])
    res = cli.cmd_validate(data_dir, results_dir, offline=True)
    assert res["meta"]["external_fetched_at"] == date.today().isoformat()
    assert "external_fetched_at" in capsys.readouterr().err


# -------------------------------------------------------------- (b) figuras
def test_figures_main_usa_diretorios_informados(tmp_path):
    from govscore import figures
    data_dir, fig_dir = tmp_path / "processed", tmp_path / "figs"
    data_dir.mkdir()
    pilot = [{"repo": f"p/{a}", "archetype": a, "score": 20.0 * (i + 1),
              "subscores": {d: 0.2 * (i + 1) for d, _ in figures.DIMENSIONS}}
             for i, a in enumerate(ARCHETYPES)]
    (data_dir / "pilot_scores.json").write_text(json.dumps(pilot))
    out = figures.main(data_dir=data_dir, results_dir=tmp_path / "results",
                       fig_dir=fig_dir)
    assert out == fig_dir
    for stem in ("fig_amostra_classificacao", "fig_pilotos_subscores",
                 "fig_amostra_linguagens", "fig_pilotos_ranking"):
        assert (fig_dir / f"{stem}.png").exists()
        assert (fig_dir / f"{stem}.pdf").exists()
    # sem scores.csv não há fase completa: results_dir não é criado
    assert not (tmp_path / "results").exists()


# --------------------------------------------------------------- argparse
def test_parser_opcoes_de_diretorio():
    ap = cli.build_parser()
    for cmd in ("validate", "sensitivity", "robustness", "figures"):
        a = ap.parse_args([cmd])
        assert a.data_dir == cli.DEFAULT_DATA_DIR
        assert a.results_dir == cli.DEFAULT_RESULTS_DIR
        a = ap.parse_args([cmd, "--data-dir", "d/v2", "--results-dir", "r/v2"])
        assert str(a.data_dir) == "d/v2" and str(a.results_dir) == "r/v2"
    a = ap.parse_args(["validate", "--external-fetched-at", "2026-07-25",
                       "--offline"])
    assert a.external_fetched_at == "2026-07-25" and a.offline is True
    assert ap.parse_args(["validate"]).external_fetched_at is None
    assert ap.parse_args(["validate"]).offline is False
    assert str(ap.parse_args(["figures", "--fig-dir", "f/v2"]).fig_dir) == "f/v2"
    assert ap.parse_args(["figures"]).fig_dir is None
