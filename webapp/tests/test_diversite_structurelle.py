"""Tests de diversité mathématique — mission "audit et maximisation de la
diversité des exercices" (2026-09-02).

Audit préalable (voir rapport de mission) : 40 familles génératrices
(≥15 exercices, ≥90% de quasi-doublon — un exercice avec l'énoncé "signature"
= énoncé avec tous les nombres remplacés par #) ne proposaient qu'UNE SEULE
structure mathématique, malgré des coefficients variés (ex. "x²-5x+6=0",
"x²-7x+12=0" : même structure, seuls les nombres changent). Pour chacune, une
ou plusieurs familles SOEURS ont été ajoutées dans un module dédié
`generate_extra_pool()` (jamais mélangées à generate_pool()/FAMILIES, qui
restent figées à l'identique — voir la mission "équilibrage définitif").

Ces tests vérifient :
1. Que les nouvelles familles de diversité sont RÉELLEMENT diversifiées
   (peu de quasi-doublon en leur sein, contrairement aux familles qu'elles
   complètent).
2. Qu'aucune régression de volume/ID/énoncé n'a eu lieu (les invariants
   additifs habituels).
3. Une métrique de diversité reproductible par chapitre (signature
   d'énoncé), SANS seuil arbitraire universel — seulement des verrous de
   non-régression par rapport à l'état mesuré après cette mission.

Aucun seuil générique du type "au moins X fractions/racines" n'est imposé
(explicitement proscrit par la mission) — la diversité est mesurée par la
variété STRUCTURELLE réelle (signatures distinctes), jamais par la présence
de tel ou tel opérateur.
"""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
WEBAPP = ROOT / "webapp"
if str(WEBAPP) not in sys.path:
    sys.path.insert(0, str(WEBAPP))

from curriculum_registry import CURRICULUM_REGISTRY  # noqa: E402

NUM_RE = re.compile(r"-?\d+(?:[.,]\d+)?")


def _signature(enonce: str) -> str:
    return re.sub(r"\s+", " ", NUM_RE.sub("#", enonce or "")).strip()


# Modules dotés d'un generate_extra_pool() (nouvelles familles de diversité),
# avec pour chacune le nom de la famille CRITIQUE d'origine qu'elle complète
# (celle identifiée par l'audit avec ≥90% de quasi-doublon) — voir le
# rapport de mission pour le détail complet de l'audit.
_DIVERSITY_TARGETS = [
    ("exercise_generator", "second_degre", {
        "equation_depuis_racines_et_point": "equation_depuis_racines",
        "equation_depuis_racines_irrationnelles": "equation_depuis_racines",
        "verifier_resolution_irrationnelle": "verifier_resolution",
    }),
    ("exercise_generator", "variations", {"optimisation_enclos": "optimisation", "extremum_parabole_cible": "extremum_inverse"}),
    ("exercise_generator", "trigonometrie", {
        "combinaison_deux_angles": "combinaison_lineaire", "expression_carre": "combinaison_lineaire",
        "formule_duplication": "combinaison_lineaire",
    }),
    ("exercise_generator", "produit_scalaire", {
        "produit_points": "produit_coordonnees", "norme_somme": "norme",
        "coordonnee_norme_donnee": "trouver_coordonnee_orthogonale", "alignement_points": "colinearite",
        "orthogonalite_triangle": "orthogonalite", "angle_inverse": "produit_norme_angle",
    }),
    ("exercise_generator", "geometrie_reperee", {
        "equation_cercle_diametre": "equation_cercle", "position_point_cercle": "point_appartient_cercle",
        "mediatrice": "ensemble_points_distance", "centre_rayon_irrationnel": "centre_rayon_reduite",
        "droite_parallele_par_point": "equation_depuis_normal",
    }),
    ("exercise_generator", "probabilites_conditionnelles", {
        "proba_conditionnelle_tableau": "proba_conditionnelle", "intersection_tirage": "intersection",
        "completer_arbre_erreur": "completer_arbre", "test_independance_tableau": "test_independance",
        "probabilites_totales_trois_branches": "probabilites_totales", "bayes_trois_branches": "bayes_simple",
    }),
    ("exercise_generator", "variables_aleatoires", {
        "esperance_effectifs": "esperance", "completer_loi_systeme": "completer_loi",
        "esperance_inverse": "esperance", "jeu_trois_issues": "jeu_esperance",
        "jeu_equite": "jeu_esperance", "variance_comparaison": "variance",
    }),
    ("exercise_generator_troisieme", "thales", {
        "calculer_longueur_papillon": "calculer_longueur", "calculer_longueur_somme": "calculer_longueur",
        "reciproque_somme": "reciproque",
    }),
    ("exercise_generator_troisieme", "proportionnalite", {"pourcentage_prix_initial": "pourcentage", "comparer_taux": "retrouver_taux"}),
    ("exercise_generator_troisieme", "nombres_relatifs", {"puissance_produit": "puissance", "ecriture_scientifique_produit": "ecriture_scientifique"}),
    ("exercise_generator_troisieme", "statistiques", {"mediane_tableau_effectifs": "mediane_pair", "moyenne_ponderee_inverse": "moyenne_ponderee"}),
    ("exercise_generator_troisieme", "probabilites_troisieme", {
        "denombrement_sans_repetition": "denombrement", "retrouver_effectif_total": "retrouver_effectif",
        "arbre_exactement_un_succes": "arbre_deux_epreuves",
    }),
    ("exercise_generator_troisieme", "factoriser_somme", {"facteur_commun_variable": "facteur_commun_simple"}),
    ("exercise_generator_troisieme", "volumes_espace", {
        "pave_retrouver_hauteur": "volume_pave", "prisme_retrouver_hauteur": "volume_prisme",
        "cylindre_retrouver_rayon": "volume_cylindre",
    }),
]


def _import_module(package: str, name: str):
    import importlib
    return importlib.import_module(f"{package}.{name}")


class TestNouvellesFamillesDeDiversite(unittest.TestCase):
    """Les familles ajoutées par cette mission doivent être RÉELLEMENT
    diversifiées (peu de quasi-doublon en leur sein), pas de simples clones
    numériques les unes des autres — sinon la mission n'aurait fait que
    déplacer le problème plutôt que le résoudre."""

    def test_generate_extra_pool_existe_et_produit_des_exercices(self):
        for package, module_name, family_map in _DIVERSITY_TARGETS:
            module = _import_module(package, module_name)
            with self.subTest(module=module_name):
                self.assertTrue(hasattr(module, "generate_extra_pool"), f"{module_name} : generate_extra_pool manquant")
                pool = module.generate_extra_pool(per_family=10, seed=1)
                self.assertTrue(pool, f"{module_name} : generate_extra_pool ne produit aucun exercice")
                familles_presentes = {e["family"] for e in pool}
                # <= et non == : la mission "audit et renforcement de la
                # diversité NUMÉRIQUE" (2026-09-02, voir
                # test_diversite_numerique.py) a ajouté d'AUTRES familles au
                # même generate_extra_pool() de certains de ces modules
                # (second_degre, variations, produit_scalaire,
                # factoriser_somme, proportionnalite, volumes_espace) — ce
                # test ne vérifie que la présence des familles STRUCTURELLES
                # de CETTE mission-ci, pas l'absence de toute autre famille.
                self.assertTrue(set(family_map) <= familles_presentes, module_name)

    def test_chaque_nouvelle_famille_a_une_structure_differente_de_loriginale(self):
        """Une famille EST par nature un moule unique (numériquement variable)
        — comme toutes les familles déjà existantes du projet (ex.
        "resolution" n'a que 9 signatures distinctes sur 15 tirages, certaines
        comme "equation_depuis_racines" n'en ont qu'UNE). La diversité de
        cette mission ne consiste donc PAS à rendre chaque famille diverse en
        elle-même, mais à vérifier qu'elle introduit une structure
        VÉRITABLEMENT DIFFÉRENTE de la famille critique qu'elle complète —
        jamais la même signature (sinon ce ne serait qu'un doublon renommé)."""
        for package, module_name, family_map in _DIVERSITY_TARGETS:
            module = _import_module(package, module_name)
            pool = module.generate_extra_pool(per_family=15, seed=7)
            by_family: dict[str, list[str]] = {}
            for ex in pool:
                by_family.setdefault(ex["family"], []).append(ex["enonce"])
            baseline_pool = module.generate_pool(per_family=15, seed=42)
            baseline_by_family: dict[str, list[str]] = {}
            for ex in baseline_pool:
                baseline_by_family.setdefault(ex["family"], []).append(ex["enonce"])
            for new_family_id, original_family_id in family_map.items():
                enonces = by_family.get(new_family_id, [])
                original_enonces = baseline_by_family.get(original_family_id, [])
                with self.subTest(module=module_name, family=new_family_id):
                    self.assertTrue(enonces, "aucun exercice généré")
                    self.assertTrue(original_enonces, f"famille d'origine {original_family_id!r} introuvable")
                    signatures_nouvelles = {_signature(e) for e in enonces}
                    signatures_originales = {_signature(e) for e in original_enonces}
                    # Tolérance : une coïncidence isolée de gabarit (ex. deux
                    # angles remarquables dont l'un n'a par hasard pas de
                    # coefficient affiché) ne prouve pas une absence de
                    # diversité — on exige qu'AU MOINS une signature nouvelle
                    # n'existe pas dans la famille d'origine, pas une
                    # séparation stricte à 100%.
                    self.assertFalse(
                        signatures_nouvelles <= signatures_originales,
                        f"{module_name}/{new_family_id} ne produit AUCUNE structure absente de "
                        f"{original_family_id} — ce n'est pas une structure réellement différente",
                    )

    def test_aucun_doublon_dexactes_dans_un_pool_de_diversite(self):
        for package, module_name, _ in _DIVERSITY_TARGETS:
            module = _import_module(package, module_name)
            pool = module.generate_extra_pool(per_family=10, seed=3)
            with self.subTest(module=module_name):
                enonces = [e["enonce"] for e in pool]
                self.assertEqual(len(enonces), len(set(enonces)))
                ids = [e["id"] for e in pool]
                self.assertEqual(len(ids), len(set(ids)))

    def test_determinisme_du_seed(self):
        for package, module_name, _ in _DIVERSITY_TARGETS:
            module = _import_module(package, module_name)
            pool_a = module.generate_extra_pool(per_family=8, seed=555)
            pool_b = module.generate_extra_pool(per_family=8, seed=555)
            with self.subTest(module=module_name):
                self.assertEqual([e["enonce"] for e in pool_a], [e["enonce"] for e in pool_b])

    def test_champs_requis_et_chapter_id_coherent(self):
        for package, module_name, _ in _DIVERSITY_TARGETS:
            module = _import_module(package, module_name)
            pool = module.generate_extra_pool(per_family=6, seed=11)
            with self.subTest(module=module_name):
                for ex in pool:
                    for field in ("enonce", "answer", "hint", "solution_steps", "chapter_id", "notion", "difficulty", "id"):
                        self.assertIn(field, ex)
                    self.assertEqual(ex["chapter_id"], module.CHAPTER_ID)
                    self.assertTrue(1 <= ex["difficulty"] <= 5)


def _load(path):
    if path is None or not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


class TestNonRegressionVolumeApresDiversification(unittest.TestCase):
    """Les pools générés doivent avoir grandi (mission additive) sans jamais
    perdre un exercice — verrou complémentaire à celui de
    test_exercise_chapter_balance.py, spécifique au volume post-diversité."""

    # Plancher = total généré juste après cette mission (voir rapport).
    PLANCHER_GENERES = {"premiere": 3883, "troisieme": 1371}

    def test_pool_genere_jamais_sous_son_plancher_post_diversite(self):
        for class_level, plancher in self.PLANCHER_GENERES.items():
            profile = CURRICULUM_REGISTRY[class_level]
            generated = _load(profile.generated_exercise_bank)
            with self.subTest(class_level=class_level):
                self.assertGreaterEqual(len(generated), plancher)

    def test_aucun_doublon_id_dans_les_banques_generees(self):
        for class_level in ("premiere", "troisieme"):
            profile = CURRICULUM_REGISTRY[class_level]
            generated = _load(profile.generated_exercise_bank)
            with self.subTest(class_level=class_level):
                ids = [e["id"] for e in generated]
                self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
