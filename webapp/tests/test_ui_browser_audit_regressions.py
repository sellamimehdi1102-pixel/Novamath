"""
Régressions issues d'un audit navigateur réel (Playwright/Chromium, mission
"stabilisation UI/UX complète de Mathadap") — chaque bug ci-dessous a été
reproduit et mesuré dans un vrai navigateur (bounding boxes, scrollWidth du
body) avant d'être corrigé ; ce fichier fige la correction dans le code
source pour empêcher une régression silencieuse, sans dépendre d'un
navigateur en CI (assertions sur le CSS/HTML source, même convention que les
autres tests de régression de ce projet).
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def _read(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


def _rule_body(css, selector):
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", _strip_comments(css))
    assert match, f"Règle {selector} introuvable"
    return match.group(1)


class TestBanniereCookiesSousLesModales(unittest.TestCase):
    """Mesuré en navigateur réel : .cookie-banner (z-index:1000) s'affichait
    par-dessus .modal-overlay (z-index:100) au premier chargement, recouvrant
    les cases à cocher CGU/confidentialité et le bouton de validation du
    formulaire d'inscription — capture d'écran + bounding boxes confirmant le
    chevauchement, avant correction."""

    def setUp(self):
        self.css = _read("webapp/static/css/base.css")

    def test_cookie_banner_sous_les_modales_et_popups(self):
        cookie_z = int(re.search(r"z-index:\s*(\d+)", _rule_body(self.css, ".cookie-banner")).group(1))
        modal_z = int(re.search(r"z-index:\s*(\d+)", _rule_body(self.css, ".modal-overlay")).group(1))
        popup_z = int(re.search(r"z-index:\s*(\d+)", _rule_body(self.css, ".popup-overlay")).group(1))
        self.assertLess(cookie_z, modal_z)
        self.assertLess(cookie_z, popup_z)


class TestMainContentClippeLesDecorsDebordants(unittest.TestCase):
    """Mesuré en navigateur réel (Playwright, 1024px et 390px de large) :
    document.body.scrollWidth > viewport sur chapitres.html/cours.html/
    exercice.html — cause bissectée jusqu'à des pseudo-éléments décoratifs
    (ex. .chapters-grid::before { left:-48px; right:-48px }, .exercise-
    layout::before) jamais clippés par aucun ancêtre. Vérifié qu'ajouter
    overflow-x:hidden à .main-content supprime bien le débordement mesuré
    (avant de l'appliquer réellement)."""

    def test_main_content_a_overflow_x_hidden(self):
        css = _read("webapp/static/css/base.css")
        body = _rule_body(css, ".main-content")
        self.assertIn("overflow-x: hidden", body)


class TestVitrineChatbotClippeeHorizontalement(unittest.TestCase):
    """Mesuré en navigateur réel : .showcase-visual::before (halo décoratif,
    inset:-14% -10%) débordait de la page sur mobile (grid en une seule
    colonne sous 860px, voir .showcase-grid), provoquant un scroll horizontal
    de toute la landing page (confirmé : body.scrollWidth > viewport à 768/
    430/390px)."""

    def test_chatbot_showcase_clippe_le_halo_decoratif(self):
        css = _read("webapp/static/css/landing.css")
        body = _rule_body(css, "#chatbot-showcase")
        self.assertIn("overflow-x: hidden", body)


class TestHistoriqueSeriesProfilDefileHorizontalement(unittest.TestCase):
    """Mesuré en navigateur réel : sur profil.html, le tableau .history-table
    (10 colonnes) n'était enveloppé dans aucun conteneur overflow-x:auto
    (contrairement à l'équivalent sur dashboard.html) — provoquait un
    débordement de PAGE ENTIÈRE de 357px sur mobile (390px de large),
    confirmé par bisection DOM."""

    def test_le_tableau_est_dans_un_conteneur_scrollable(self):
        html = _read("webapp/static/profil.html")
        match = re.search(r'<div class="profile-card card"[^>]*>\s*<h3>.*?Historique des séries', html, re.DOTALL)
        self.assertIsNotNone(match, "bloc Historique des séries introuvable")
        self.assertIn("overflow-x:auto", match.group(0))


class TestIconeExerciceSurMesureTailleeCorrectement(unittest.TestCase):
    """Mesuré en navigateur réel (Playwright) : le SVG <h3><svg class="h3-icon">
    du bloc "Exercice sur mesure" (exercice.html) se rendait à 352×352px au
    lieu de ~16px — exercice.css ne définissait .h3-icon que scopé à
    .history-card, et exercice.html ne charge pas dashboard.css (seul fichier
    avec une règle .h3-icon non scopée). Correspond exactement au symptôme
    "bloc Exercice sur mesure au rendu disproportionné" signalé."""

    def setUp(self):
        self.css = _read("webapp/static/css/exercice.css")

    def test_custom_exercise_card_h3_icon_est_dimensionne(self):
        match = re.search(r"\.custom-exercise-card \.h3-icon\s*\{|,\s*\.custom-exercise-card \.h3-icon\s*\{", self.css)
        self.assertIsNotNone(match, ".custom-exercise-card .h3-icon non défini")

    def test_custom_exercise_card_h3_a_le_gap_flex(self):
        body = _rule_body(self.css, ".custom-exercise-card h3")
        self.assertIn("display: flex", body)
        self.assertIn("gap:", body)


class TestExerciceLayoutSempileSurMobile(unittest.TestCase):
    """Mesuré en navigateur réel (Playwright, 390px de large) :
    .exercise-layout-main et .exercise-layout-side (respectivement flex:2 et
    flex:1) restaient côte à côte au lieu de s'empiler — .exercise-layout-side
    ne faisait plus que ~108px de large, texte compressé caractère par
    caractère. Après correction (flex-basis:100% sous 640px), les deux
    colonnes font chacune la pleine largeur disponible (mesuré : 358px/358px)."""

    def test_flex_basis_100_sous_640px(self):
        css = _read("webapp/static/css/exercice.css")
        media_blocks = re.findall(r"@media \(max-width:\s*640px\)\s*\{(.*?)\n\}", css, re.DOTALL)
        self.assertTrue(media_blocks)
        found = any(
            re.search(r"\.exercise-layout-main,\s*\.exercise-layout-side\s*\{[^}]*flex-basis:\s*100%", block)
            for block in media_blocks
        )
        self.assertTrue(found, "flex-basis:100% pour .exercise-layout-main/.exercise-layout-side introuvable sous 640px")


class TestPopupSettingsHauteurFixeReellementEnDur(unittest.TestCase):
    """Mesuré en navigateur réel (Playwright, 1920/1440/1280/1024/768/430px,
    compte de test réel, clics successifs sur les 8 catégories + retour) :
    la bounding box de la popup Paramètres (#settings-popup-overlay
    .popup-card) est restée STRICTEMENT identique (x/y/largeur/hauteur)
    quelle que soit la catégorie affichée, à chaque résolution testée — la
    correction .popup-card--xl { height: 88vh } + .popup-body { flex: 1 1
    auto } fonctionne bel et bien. Ce test fige uniquement qu'elle reste bien
    committée : dans une mission précédente, ce correctif existait déjà dans
    l'arbre de travail local mais n'avait jamais été commité (HEAD ne
    contenait encore que `.popup-card--xl { max-width: 980px; }`, sans
    hauteur) — la version réellement livrée (dépôt distant/déploiement)
    conservait donc le bug malgré la correction locale."""

    def setUp(self):
        self.css = _read("webapp/static/css/base.css")

    def test_popup_card_xl_a_une_hauteur_fixe_committee(self):
        body = _rule_body(self.css, ".popup-card--xl")
        self.assertRegex(body, r"(?<!max-)height\s*:")

    def test_popup_body_extensible_committe(self):
        body = _rule_body(self.css, ".popup-body")
        self.assertIn("flex:", body)


class TestShowcaseWindowLabelNonEcraseParLesPointsDeChrome(unittest.TestCase):
    """Mesuré en navigateur réel (Playwright, getBoundingClientRect +
    getComputedStyle, 7 résolutions) : <span class="showcase-window-label">
    (badge "Exemple de conversation") est aussi un <span> enfant de
    .showcase-window-chrome ; la règle générique des 3 points du faux
    navigateur (.showcase-window-chrome span, spécificité classe+élément)
    écrasait son width/height (auto → 9px), le badge se retrouvant compressé
    à 26×10px (son seul padding+bordure) pendant que son texte
    "Exemple de conversation" (~87×59px) débordait visuellement hors de la
    fenêtre du mockup ("Exem.../de.../conv..." visibles à l'extérieur).
    Après correction : label mesuré à 171×28px, entièrement contenu dans la
    fenêtre, à toutes les résolutions testées."""

    def test_regle_des_points_exclut_le_badge_label(self):
        css = _read("webapp/static/css/landing.css")
        body = _rule_body(css, ".showcase-window-chrome span:not(.showcase-window-label)")
        self.assertIn("width: 9px", body)

    def test_le_badge_garde_sa_propre_regle_de_taille_auto(self):
        css = _read("webapp/static/css/landing.css")
        body = _rule_body(css, ".showcase-window-label")
        self.assertIn("width: auto", body)
        self.assertIn("height: auto", body)


if __name__ == "__main__":
    unittest.main()
