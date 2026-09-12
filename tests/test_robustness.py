"""Testes das análises de robustez (casos conhecidos)."""
import math

import yaml

from govscore.robustness import (
    CONTENT_REPOS,
    _perturb_cfg,
    exclusion_scenarios,
    imputation_sensitivity,
    reclassification_sensitivity,
    social_composite,
    steiger_z,
    stratum_rho,
    threshold_sensitivity,
)

CFG = yaml.safe_load(open("config/metrics.yaml"))


def _repo(repo, first_resp, arch="toy"):
    return {
        "repo": repo, "archetype": arch, "score": None,
        "artifacts": {"readme": True, "license": True, "contributing": False,
                      "code_of_conduct": False, "issue_template": False,
                      "pull_request_template": False, "codeowners": False,
                      "governance": False, "funding": False},
        "security": {"security_policy": True, "ci_configured": True,
                     "dependency_automation": False, "releases_12m": 3,
                     "release_notes_share": 1.0},
        "distribution": {"top1_share": 0.5, "hhi": 0.3, "truck_factor": 2,
                         "contributors_5plus": 4, "commit_entropy": 0.5,
                         "elephant_factor": 1, "contributor_retention": 0.3},
        "responsiveness": {"median_first_response_hours": first_resp,
                           "median_pr_merge_hours": 100.0,
                           "pr_merge_ratio": 0.5, "pr_review_coverage": 0.5,
                           "n_issues_sampled": 10,
                           "n_first_responses": 0 if first_resp is None else 5},
        "subscores": {},
    }


def test_perturb_cfg_escala_somente_os_alvos():
    mod = _perturb_cfg(CFG, [("responsiveness",
                              "median_first_response_hours")], 1.5)
    assert mod["responsiveness"]["median_first_response_hours"]["best"] == 72
    assert mod["responsiveness"]["median_first_response_hours"]["worst"] == 1080
    # intocados: outros limiares e pesos
    assert mod["responsiveness"]["median_pr_merge_hours"] == \
        CFG["responsiveness"]["median_pr_merge_hours"]
    assert mod["weights"] == CFG["weights"]


def test_threshold_sensitivity_identidade_em_ranking_uniforme():
    # dois repos com métricas idênticas exceto escala monotônica → ranking
    # invariante a qualquer perturbação de limiar
    results = [_repo("a/1", 10.0), _repo("b/2", 500.0)]
    results[1]["distribution"]["top1_share"] = 0.9
    out = threshold_sensitivity(results, CFG, deltas=(0.25,))
    # com n=2 o ρ é degenerado (None ou ±1); só garante que roda e estrutura
    assert "±25%" in out["per_metric"] and "±25%" in out["joint"]


def test_steiger_z_zero_quando_correlacoes_iguais():
    z, p = steiger_z(0.7, 0.7, 0.5, 50)
    assert math.isclose(z, 0.0, abs_tol=1e-12) and math.isclose(p, 1.0)
    z2, _ = steiger_z(0.75, 0.60, 0.8, 53)
    assert z2 > 0  # r13 > r23 → z positivo


def test_social_composite_renormaliza():
    r = _repo("a/1", 10.0)
    from govscore.score.scoring import compute_subscores
    r["subscores"] = compute_subscores(r, CFG)
    (comp,) = social_composite([r], CFG["weights"])
    subs = r["subscores"]
    w = {"distribution": 0.25, "responsiveness": 0.20, "diversity": 0.15}
    esperado = 100 * sum(w[d] * subs[d] for d in w) / sum(w.values())
    assert math.isclose(comp, esperado)


def test_reclassification_federacao_vira_indeterminada_ao_subir_limiar():
    entries = [
        {"repo": "f/1", "archetype": "federation",
         "active_contributors_2plus": 104, "stars": 50_000},
        {"repo": "t/1", "archetype": "toy",
         "active_contributors_2plus": 2, "stars": 100},
    ]
    t = {"min_commits_per_contributor": 2,
         "federation_min_contributors": 100, "stadium_max_contributors": 10,
         "club_min_contributors": 20, "toy_max_contributors": 3,
         "stars_high_min": 10_000, "club_stars_max": 5_000,
         "toy_stars_max": 500}
    out = reclassification_sensitivity(entries, t)
    v = out["federation_min_contributors +50%"]
    assert v["federacoes_indeterminadas"] == 1  # contagem é piso — não avalia
    assert out["conjunto −50%"]["preservados"] >= 1  # toy segue toy


def test_stratum_rho_caso_conhecido_e_exclusao_par_a_par():
    rows = [{"repo": f"s/{i}", "archetype": "stadium", "score": s, "forks": f}
            for i, (s, f) in enumerate([(10, 400), (20, 300), (30, 200),
                                        (40, 100), (50, None)])]
    rows.append({"repo": "t/1", "archetype": "toy", "score": 99, "forks": 1})
    out = stratum_rho(rows, "stadium", "forks")
    assert out["n"] == 4                      # None e outro estrato fora
    assert math.isclose(out["rho"], -1.0)     # monotônica decrescente
    assert stratum_rho(rows[:2], "stadium", "forks")["rho"] is None  # n<3


def test_exclusion_scenarios_remove_os_conjuntos():
    content = CONTENT_REPOS[0]
    results = [{"repo": r, "archetype": "stadium", "score": s,
                "stars": 10, "forks": f}
               for r, s, f in [("a/1", 10, 4), ("a/2", 20, 3), ("a/3", 30, 2),
                               ("a/4", 40, 1), (content, 5, 999)]]
    out = exclusion_scenarios(results, {}, heuristic=["a/4"])
    assert out["completa"]["n"] == 5
    assert out["sem_conteudo"]["n"] == 4
    assert out["sem_heuristica"]["n"] == 4
    assert out["sem_todos"]["n"] == 3
    assert math.isclose(out["sem_conteudo"]["estratos"]["stadium×forks"]["rho"],
                        -1.0)


def test_imputation_sensitivity_penaliza_silencio_observado():
    silencioso = _repo("s/1", None)     # issues existem, nenhuma resposta
    normal = _repo("n/1", 10.0)
    out = imputation_sensitivity([silencioso, normal], CFG)
    assert out["n_informativos"] == 1
    assert "s/1" in out["taxonomia"]["d3_informativo"]
    assert out["medias_por_arquetipo"]["toy"]["imputacao"] <= \
        out["medias_por_arquetipo"]["toy"]["omissao"]
