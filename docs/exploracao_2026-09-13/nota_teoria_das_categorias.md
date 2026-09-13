# Formalization note — what category theory buys in the governance-score study

**Scope.** "Load-bearing" here means: the formulation yields (a) a computable invariant not already in `results/`, (b) a law that the n=100 data or the pipeline can violate, or (c) a constraint on the instrument's design. Everything else is renaming. All verifications below are against `src/govscore/score/scoring.py` (mean of available metrics per dimension; weights renormalized over available dimensions), `normalize.py` (clamped linear interpolation, `None` passes through) and `sampling.classify` (2×2 on stars × active contributors).

---

## 1. The score as a monotone map on partial vectors; the missing-data rule as a non-universal extension

**Definition.** Let I be the 25 metric coordinates. An object is a partial vector x: J → [0,1], J ⊆ I (normalized values on the observed coordinates). Two morphism classes, kept separate because they behave differently:

- *Improvement* x ≤ y: same domain J, x_i ≤ y_i coordinate-wise (product order on [0,1]^J).
- *Extension* x ⊑ y: J_x ⊆ J_y and y restricted to J_x equals x ("one more observation, nothing else changes").

Both are preorders, hence thin categories (identities and composition trivial). Let `score` be the function in `scoring.py`, viewed as a map to the poset (ℝ, ≤).

**Law 1 (holds by construction).** `score` is a functor on the improvement category: positive weights + clamped linear normalization + means ⇒ x ≤ y implies score(x) ≤ score(y). Trivial, but it fixes the only order the score is *obliged* to respect. Comparability under this order is the compensation ratio: 4.0% of pairs on the 25 coordinates (65 complete cases), 38.7% on the five sub-scores. On the remaining pairs the score *decides* rather than *reports*. Report this number; do not present it as a defect (comparability decays exponentially with dimension — compare against a column-permutation null before interpreting).

**Law 2 (fails).** Along extension, the three candidate rules behave as follows, for any extension x ⊑ y adding coordinate i with value v ∈ [0,1]:

| rule for missing i | behaviour along ⊑ |
|---|---|
| impute 0 (worst case) | monotone (v ≥ 0 can only raise) — a functor |
| impute 1 (best case) | antitone (v ≤ 1 can only lower) — a contravariant functor |
| omit-and-renormalize (current) | neither: sign depends on v vs. the mean of the observed coordinates |

The current rule is numerically identical to imputing the weighted mean of the available dimensions (linux: 56.8945 both ways). It is therefore the unique one of the three that is *not* a functor in either variance. The categorical reading of "impute 0 / impute 1": for the inclusion J ↪ I of discrete categories and x: J → [0,1], the left Kan extension at i ∉ J is the colimit of the empty diagram (bottom, 0) and the right Kan extension the limit (top, 1). Note: the angle-5 text and cluster C3 state this correctly in the discrete-inclusion framing; in the extension-poset framing the orientation flips (Lan = sup over total extensions = impute 1). Use one framing. Either way the interval [impute 0, impute 1] is exactly Manski's no-assumption identification region — name it that in the thesis, and Kan only in a footnote.

**Testable proposition.** *Reachable* silence pays: for a repo r and a dimension d that can become entirely unobserved by a reachable state (D3: zero closed issues and PRs; D5's release metrics: zero releases), score(r with d omitted) > score(r). Unlike the metric-level counts (63/44/39), dimension-level omission of D3 is a reachable counterfactual (the four D3-absent repos are real). Prototype: 22 repos would gain from D3 absence.

```
for r in metrics.parquet:
    s0 = compute_score(compute_subscores(r), w)
    for d in {responsiveness, security}:          # reachable-omission dims
        s1 = compute_score({**sub, d: None}, w)
        gain[r,d] = s1 - s0                        # >0  => silence pays
    lo = score(r, missing->worst threshold); hi = score(r, missing->best)
    undecided_pairs = #{(a,b): lo[a] <= hi[b] and lo[b] <= hi[a]}   # 287/4950
    quartile_undecidable[r] = archetype Q1/Q3 falls inside [lo,hi]  # 21 repos
```

**What it adds.** A design constraint stated as a law rather than a sensitivity: the omit rule rewards non-engagement relative to worst-case imputation, and the 4.3.5 reference quartiles are undecidable for 21 repos under any assumption-free rule. This directly extends critique 2 (3-repo imputation test) to all 35 repos with missingness. **Risk.** A committee reads "your rule rewards silence" as self-inflicted; the "every repo has a dimension whose deletion raises its score" version is a tautology of weighted means and must not be used. Present only reachable omissions and the interval.

---

## 2. Practices as a Galois connection: concept lattice, implications, and the score as a linear extension

**Definition (standard: Ganter & Wille).** Formal context K = (R, M, I), R = 100 repos, M = crisp attributes: the informative binaries (drop `readme` constant, `issue_template` defective, `governance` at 2/100) plus, for each continuous metric, `m@best` (normalized = 1). Derivation operators A ↦ A' = {m : ∀r ∈ A, rIm} and B ↦ B' form an antitone Galois connection between (2^R, ⊆) and (2^M, ⊆); i.e., an adjunction between thin categories, with unit A ⊆ A'' and counit B ⊆ B''. Fixed points are the formal concepts; (extent, intent) pairs form a complete lattice 𝔅(K). This is verified machinery; nothing to check.

**Exclude by construction:** archetype coordinates and the D2/D4 attributes (they are the sampling classifier's inputs); `missing` coded as absent only for structurally missing metrics, otherwise remove the attribute from that object's row (three-valued context), consistent with Law 2.

**Law 3 (order-theoretic).** Restrict the score to the binary sub-vector s_bin(r). If intent(r) ⊆ intent(s) then s_bin(r) ≤ s_bin(s): the score's binary part is a monotone map 𝔅(K_bin) → [0,1], hence a linear extension of the concept order. It cannot be injective on incomparable intents. The invariant: **compensation loss** = number (and list) of pairs with incomparable intents and |Δscore| < ε. Bootstrap the count.

**Law 4 (Guttman as a lattice condition).** The practice set is a *ladder* iff 𝔅(K_bin) is a chain, iff every repo's intent is a down-set of one total order on M. Guttman errors count violations of the down-set property; Loevinger's H is the normalized version. Pooled H = 0.49 but within-stratum H = 0.29/0.27 (club/stadium): the "ladder" is a between-archetype gradient, not a within-stratum scale. Report it as such — the lattice is *not* a chain, and that is the finding.

**Implications.** The Duquenne–Guigues stem base is the canonical generating set of the closure system {B : B'' = B}; use it, but report lift against consequent base rate (ci 0.84, merge_hours@half 0.88 give lift ≈ 1.15 at confidence 1.0) and validate on a split-half; the 2^|M| premise space has no multiplicity control.

```
K = crisp context (repos x attrs), attrs = binaries + m@best, no D2/D4, no archetype
concepts = NextClosure(K)                       # hand-rolled; ~10^2-10^3 concepts
basis = DuquenneGuigues(K); rules = [(P,Q,supp,conf,lift) for Luxenburger(K, conf>=.8, supp>=10)]
H_pooled, H_stratum = loevinger(K_bin), {a: loevinger(K_bin[arch==a])}
loss = [(r,s) for r<s if incomparable(intent r, intent s) and |score r - score s| < 3]
factor test (2x2 balanced): for each attr, fit logit(attr ~ users_high + contrib_high)
   factors through pi_contrib  <=>  P(fed)=P(club) and P(stadium)=P(toy)  (two equality tests)
```

**On the archetype "factorization" test.** The base is the Boolean 2×2 B = {users_high} × {contrib_high}; a function f on B factors through the projection π_contrib iff f(fed) = f(club) and f(stadium) = f(toy). With 25 per cell this is a balanced factorial, so the two contrasts are orthogonal main effects — *not* confounded by construction, contrary to one verdict. What is true is that only club vs stadium separate the factors, and the club stratum sits in 6% of its stars band. Report as main effects with Holm, restricted to D1/D3/D5 attributes.

**What it adds.** The literal "padrões" the title promises, computed from the same measurement decisions as the score, plus a quantified statement of what the compensatory index forgets. **Risk.** FCA on 100 objects is standard data mining; the Galois-connection framing is textbook (and Duquenne 1995 already read Guttman data through lattices). Cite in one sentence; do not claim the adjunction as a contribution.

---

## 3. Locality typing of the catalogue over covers of the window (a cosheaf/sheaf distinction, not cohomology)

**Definition.** Site: the poset P of sub-intervals of the 12-month window under inclusion (or top-level directories of the tree), with the disjoint covers {quarters} or {modules}. For each metric m define m_U = the metric recomputed on data restricted to U. Three types:

- *cosheaf-typed*: m_{U⊔V} = m_U + m_V for disjoint U, V (commit counts, release counts, contributor sets under union) — m preserves the colimit (disjoint union);
- *constant-sheaf section*: m_U = m_X for all U (D1/D5 file presence at HEAD);
- *non-local*: neither (top1_share, HHI, truck factor, entropy, elephant factor, retention, all medians and ratios) — m_X is not a function of {m_U}.

**Law 5 (compositionality).** Only cosheaf-typed quantities can be aggregated across windows, modules, or dependency chains; the five sub-scores and the score are non-local and therefore *cannot be composed* — any future "ecosystem score" summing repo scores is ill-typed. This is a constraint on the instrument's use, stated as a law. **Invariant:** the gluing defect δ(m) = m_X − mean_U m_U over the quarterly cover.

**Honest negative results, to be written into the CotC theory file.** (i) The presheaf of commit records U ↦ Commits(U) *is* a sheaf and is flabby (every local section extends by union), so Čech Ȟ^1 = 0 identically — there is nothing to compute. (ii) The concentration/entropy assignment U ↦ m_U is not even a presheaf into a poset (marginal entropy is not monotone under restriction), so "ℋ is not a sheaf" (CotC Prop. 4.3.1) is true for a trivial reason: it has no restriction maps. Its entire empirical content is δ(m).

```
for repo with complete 12m commit cache (54 today; federations need re-clone):
    year = D2D4(commits);  q = [D2D4(commits in Q_k) for Q_k with >=5 commits]
    defect[repo] = year - mean(q)                         # club +0.09, stadium +0.02 prototype
    jaccard[repo] = mean over k of |A_k ∩ A_{k+1}| / |A_k ∪ A_{k+1}|   # sequential vs concurrent authors
report defect by archetype with bootstrap CI where n>=15; label as window sensitivity
```

**What it adds.** A one-paragraph typing lemma and a robustness statistic that answers the open D2/D4-fusion item with a mechanism (sequential pluralism read as concurrent). **Risk.** The REST commit cache is truncated for 24/25 federations, so the cache-only defect is a truncation artefact there; do not report federation defects without the re-clone. Modest effect (median 0.012 sub-score). A reviewer will call the sheaf language heavy for "ratios are not additive" — keep the lemma to three lines and cite window sensitivity of truck factor (Ferreira et al. 2019; Jabrayilzade et al. 2022) as the empirical precedent.

---

## 4. Rankings with intervals as an interval order (small, but a real structural change)

Given intervals [lo_r, hi_r] from §1 (missing-data bounds) or window resampling, define r ≻ s iff lo_r > hi_s. Strict interval orders are irreflexive and transitive (Fishburn), so this is a genuine partial order — a thin category on repos replacing the chain the point score imposes. **Invariant:** density of ≻ within archetypes (88.8% under resampling bands) and the Hasse diagram (Brüggemann–Patil). **Law:** any published ranking must be a linear extension of ≻; the 21 undecidable quartile placements are the pairs it refuses to order. Cite Fishburn and Brüggemann–Patil; no categorical vocabulary needed in the text.

---

## Decorative — do not use

- **Lenses for "points per missing practice"**: the get/put laws are trivial for a linear map; marginal points are constants (2.78 per D1 binary, 3.0 per D5 binary).
- **Monoidal categories / decorated cospans**: aggregation is a renormalized weighted mean, not associative; no dependency graph in the cache (dependents n=5).
- **Lawvere metric spaces**: the score is 1-Lipschitz for the weighted L¹ metric — true and empty.
- **Ologs**: documentation only.
- **fsQCA as the Gödel lattice / Goguen's L-fuzzy sets**: correct identification of min/max/≤, but consistency ≈ stratum base rate on these data (cluster C2 refuted twice); the lattice adds nothing to a refuted design.
- **Necessity ceilings as limits/pullbacks**: Y ≤ min_i f_i(S_i) is a meet in a poset; calling it "the governance functor preserves limits" is a pun, not a theorem.
- **Span Openers ← Threads → Responders**: V_R/V_D is a ratio of image cardinalities; the span adds no law.
- **Stadium as terminal object**: even in the free category on the six declared arrows, Stadium ⇄ Federation gives infinitely many paths to Stadium, so uniqueness fails; in the thin quotient Stadium ≅ Federation. The star-graph reading (one sink) is a graph statistic, not terminality.
- **Fibration over the locus base (C9)**: "the score is defined only on the github-native fibre" is a partial function with a stated domain; a Grothendieck construction adds nothing.
- **Apposition K_form | K_use as "decoupling = extent of K_form that is not an extent of the apposition"**: *false as stated*. For B ⊆ M_form, B' is computed identically in K_form and in the apposition, so every extent of K_form remains an extent of the apposed context. Decoupling would instead be near-independence of the two derivation operators (𝔅(K_form|K_use) ≈ product of the two lattices) — computable, but it is a contingency-table statement.
- **Čech H^n of the governance presheaf 𝒢**: Set-valued with subtraction in the coboundary and `len()` for dim — undefined; see §3 for the only residue.

---

## Bridge to *categories-of-the-commons*

**Minimal definitions under which govscore is an instance of the framework:**

1. **Site.** Replace CotC's three incompatible base spaces by one poset site: sub-windows of the 12-month interval (or sub-trees), with the disjoint covers of §3. The "quadrant cover" is a cover of the *set of projects*, a different space; keep it as the 2×2 base B of §2, used only as an indexed family (four fibres, no restriction maps between them, because the data supply none).
2. **Presheaf.** Replace 𝒢(U) = (rules, procedures, monitoring) by the sheaf of platform records 𝒞(U) = {commits, issues, PRs, comments dated in U}; restriction = filtering by date. This is a sheaf and it is flabby (§3).
3. **Metrics as non-natural functionals.** Each catalogue metric is a function m_U: 𝒞(U) → ℝ that is *not* natural in U unless cosheaf-typed. The govscore instrument is the evaluation of these functionals at the top element X only, followed by the (non-functorial along extension, §1) aggregation. This is why no cohomology exists to compute: the study never leaves the global section.
4. **Archetypes.** `sampling.classify` is a function Repos → B; the reference-quartile tables are the fibres. CotC's "OSS category" with six arrows has no instance here: a cross-section observes no transitions, so neither the arrows nor the "Main Theorem" H_VSM ∘ F = H_OSS are instantiated. The one check govscore *can* run is the necessary condition for H_OSS to be a functor to (ℝ, ≤): monotonicity along the declared arrow Federation → Stadium requires mean entropy(Fed) ≤ mean entropy(Stadium) (column `distribution_commit_entropy` by archetype); CotC's own numbers (0.769 > 0.474) already violate it.
5. **Entropy presheaf.** ℋ becomes the non-local metric `commit_entropy` of §3; Prop. 4.3.1 reduces to the measured gluing defect. Nothing else in the sheaf-cohomology file has an empirical counterpart.

**Statement.** Under 1–5 the governance score is an instance of CotC only in the degenerate sense of evaluating a non-natural functional on the global section of a flabby sheaf over a poset site, indexed by a 2×2 base. It is *not* an instance of the governance presheaf 𝒢, the adjunction Spec ⊣ Free, the natural transformation α: F ⇒ G, the spectral sequence, or the terminal-object claim, because none of those objects has a definition that survives the checks above (no hom-sets, no restriction maps, Set-valued cohomology, non-unique paths). The productive direction for CotC is the reverse of the one drafted: take the four laws here (monotonicity along improvement, non-functoriality of the missing rule along extension, linear extension of the concept order, cosheaf typing) as the framework's actual content, and let the sheaf and functor language be earned by data — a second wave for arrows, per-module touches for a genuine cover — rather than asserted.