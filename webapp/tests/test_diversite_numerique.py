"""Tests de diversité NUMÉRIQUE — mission "audit et renforcement de la
diversité numérique des exercices" (2026-09-02).

Contexte : la mission précédente ("audit et maximisation de la diversité
des exercices", voir test_diversite_structurelle.py) a diversifié les
STRUCTURES DE RAISONNEMENT (types de problèmes). Un second audit, portant
cette fois sur les TYPES DE NOMBRES réellement produits, a été fait en
lisant directement le CODE SOURCE de chaque générateur suspect (pas
seulement le texte des énoncés, qui sous-compte les résultats irrationnels/
fractionnaires visibles seulement dans la réponse) — voir le rapport de
mission pour le détail complet de l'audit et des faux positifs écartés.

7 gaps réels ont été confirmés par lecture du code (preuve = ligne de code
qui empêche structurellement un type de nombre d'apparaître) :

1. `exercise_generator/second_degre.py::resolution` (et 5 familles sœurs) —
   les racines sont toujours choisies entières AVANT de calculer b,c : le
   discriminant est donc toujours un carré parfait, aucune racine
   irrationnelle n'existe dans tout Chapitre_2 (Première).
2. `exercise_generator/variations.py::calcul_deg3` — filtre explicite
   `if not all(r.is_rational...): return None`.
3. `exercise_generator/produit_scalaire.py` — coordonnées toujours entières
   (`_nz`), jamais fractionnaires.
4. `exercise_generator_troisieme/factoriser_somme.py` — coefficients
   toujours entiers, jamais un facteur commun fractionnaire.
5. `exercise_generator_troisieme/proportionnalite.py::pourcentage` /
   `retrouver_taux` — taux toujours choisi dans une liste de valeurs
   rondes, filtre explicite pour forcer un résultat entier.
6. `exercise_generator_troisieme/volumes_espace.py` — dimensions toujours
   entières (`randint`).
7. `exercise_generator_seconde/pourcentages_evolutions.py` — même défaut
   que (5), taux toujours entier.

Pour chacun, une nouvelle famille sœur a été ajoutée dans
`generate_extra_pool()` (Première/Troisième) ou son équivalent Seconde
(jamais mélangée à `generate_pool()`/`FAMILIES`, qui restent figées à
l'identique). Ces tests verrouillent que chaque nouvelle famille produit
BIEN, et de façon quasi systématique, le type numérique pour lequel elle a
été créée — ce n'est PAS une règle générique imposant fractions/racines/
décimales à toutes les familles (explicitement proscrit par la mission),
seulement un verrou de non-régression sur les familles créées précisément
pour combler ce manque précis.
"""
import importlib
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
WEBAPP = ROOT / "webapp"
if str(WEBAPP) not in sys.path:
    sys.path.insert(0, str(WEBAPP))

_SQRT_RE = re.compile(r"\\sqrt")
_FRAC_RE = re.compile(r"\\frac|\\dfrac")
_DECIMAL_RE = re.compile(r"\d,\d")

# (package, module, famille, texte_a_scanner, regex, taux_minimal)
_NUMERIC_TARGETS = [
    ("exercise_generator", "second_degre", "resolution_irrationnelle", "answer", _SQRT_RE, 0.95),
    ("exercise_generator", "variations", "calcul_deg3_irrationnel", "answer", _SQRT_RE, 0.95),
    ("exercise_generator", "produit_scalaire", "produit_coordonnees_fractionnaires", "enonce", _FRAC_RE, 0.95),
    ("exercise_generator_troisieme", "factoriser_somme", "facteur_commun_fractionnaire", "answer", _FRAC_RE, 0.95),
    ("exercise_generator_troisieme", "proportionnalite", "pourcentage_taux_decimal", "enonce", _DECIMAL_RE, 0.95),
    ("exercise_generator_troisieme", "volumes_espace", "volume_pave_dimension_decimale", "enonce", _DECIMAL_RE, 0.95),
    ("exercise_generator_seconde", "pourcentages_evolutions", "evolution_taux_decimal", "enonce", _DECIMAL_RE, 0.95),
    # Mission "chantier final : diversification numérique maximale" (2026-09-02)
    ("exercise_generator", "geometrie_reperee", "vecteur_normal_unitaire", "answer", _SQRT_RE, 0.90),
    ("exercise_generator_troisieme", "developper_distributivite", "calcul_direct_fractionnaire", "enonce", _FRAC_RE, 0.95),
]


def _import_module(package: str, name: str):
    return importlib.import_module(f"{package}.{name}")


class TestNouvellesFamillesDeDiversiteNumerique(unittest.TestCase):
    """Chaque nouvelle famille doit produire, de façon quasi systématique
    (>=95% des tirages), le type numérique pour lequel elle a été créée —
    sinon la mission n'aurait fait qu'ajouter des exercices sans combler le
    manque identifié par l'audit."""

    def test_generate_extra_pool_contient_la_famille_et_produit_le_type_numerique_cible(self):
        for package, module_name, family_id, field, regex, min_rate in _NUMERIC_TARGETS:
            module = _import_module(package, module_name)
            with self.subTest(module=module_name, family=family_id):
                self.assertTrue(hasattr(module, "generate_extra_pool"), f"{module_name} : generate_extra_pool manquant")
                pool = module.generate_extra_pool(per_family=20, seed=1)
                exs = [e for e in pool if e["family"] == family_id]
                self.assertTrue(exs, f"{module_name}/{family_id} : aucun exercice généré")
                matches = sum(1 for e in exs if regex.search(str(e.get(field, ""))))
                rate = matches / len(exs)
                self.assertGreaterEqual(
                    rate, min_rate,
                    f"{module_name}/{family_id} : seulement {rate:.0%} des exercices contiennent le motif "
                    f"attendu dans {field!r} (attendu >= {min_rate:.0%})",
                )

    def test_aucun_doublon_dans_les_nouveaux_pools(self):
        seen_packages = set()
        for package, module_name, _, _, _, _ in _NUMERIC_TARGETS:
            key = (package, module_name)
            if key in seen_packages:
                continue
            seen_packages.add(key)
            module = _import_module(package, module_name)
            pool = module.generate_extra_pool(per_family=10, seed=3)
            with self.subTest(module=module_name):
                enonces = [e["enonce"] for e in pool]
                self.assertEqual(len(enonces), len(set(enonces)))
                ids = [e["id"] for e in pool]
                self.assertEqual(len(ids), len(set(ids)))

    def test_determinisme_du_seed(self):
        seen_packages = set()
        for package, module_name, _, _, _, _ in _NUMERIC_TARGETS:
            key = (package, module_name)
            if key in seen_packages:
                continue
            seen_packages.add(key)
            module = _import_module(package, module_name)
            pool_a = module.generate_extra_pool(per_family=8, seed=555)
            pool_b = module.generate_extra_pool(per_family=8, seed=555)
            with self.subTest(module=module_name):
                self.assertEqual([e["enonce"] for e in pool_a], [e["enonce"] for e in pool_b])

    def test_resolution_irrationnelle_racines_verifiees_directement(self):
        """Recalcule indépendamment (via sympy, sans reparser le LaTeX rendu)
        que chaque exercice produit a bien deux racines réelles irrationnelles
        — appel direct au générateur interne de la famille, seule source de
        vérité déjà utilisée par le module lui-même."""
        second_degre = _import_module("exercise_generator", "second_degre")
        rng = second_degre.random.Random(2026)
        produced = 0
        for _ in range(200):
            notes = second_degre._gen_resolution_irrationnelle(rng)
            if notes is None:
                continue
            produced += 1
            self.assertIn("\\sqrt", notes["answer"])
        self.assertGreaterEqual(produced, 50)


def _load(path):
    if path is None or not path.exists():
        return []
    import json
    return json.loads(path.read_text(encoding="utf-8"))


class TestNonRegressionApresDiversiteNumerique(unittest.TestCase):
    """Verrou complémentaire à test_diversite_structurelle.py, spécifique au
    volume post-diversité NUMÉRIQUE (mission 2026-09-02)."""

    from curriculum_registry import CURRICULUM_REGISTRY

    # Plancher = total juste après cette mission (voir rapport). Seconde
    # inclus cette fois (exercises_bank.json, pas de fichier "generated"
    # fusionné pour cette classe — voir tools/generate_seconde_curated_additions.py).
    PLANCHER_GENERES = {"premiere": 3971, "troisieme": 1427}
    PLANCHER_SECONDE_BANK = 2275

    def test_pool_genere_jamais_sous_son_plancher_post_diversite_numerique(self):
        for class_level, plancher in self.PLANCHER_GENERES.items():
            profile = self.CURRICULUM_REGISTRY[class_level]
            generated = _load(profile.generated_exercise_bank)
            with self.subTest(class_level=class_level):
                self.assertGreaterEqual(len(generated), plancher)

    def test_banque_seconde_jamais_sous_son_plancher(self):
        profile = self.CURRICULUM_REGISTRY["seconde"]
        bank = _load(profile.exercise_bank)
        self.assertGreaterEqual(len(bank), self.PLANCHER_SECONDE_BANK)

    def test_aucun_doublon_id_dans_les_banques(self):
        for class_level in ("premiere", "troisieme"):
            profile = self.CURRICULUM_REGISTRY[class_level]
            generated = _load(profile.generated_exercise_bank)
            with self.subTest(class_level=class_level):
                ids = [e["id"] for e in generated]
                self.assertEqual(len(ids), len(set(ids)))
        bank = _load(self.CURRICULUM_REGISTRY["seconde"].exercise_bank)
        ids = [e["id"] for e in bank]
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
