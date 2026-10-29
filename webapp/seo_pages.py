"""Pages publiques de présentation des classes (référencement naturel).

Une page par classe publiée, servie sans compte à une URL descriptive
(/maths-quatrieme, ...). Le HTML est rendu ICI, côté serveur, pour que les
moteurs de recherche lisent le contenu sans exécuter de JavaScript.

Ces pages n'affichent que des informations déjà publiques : titres des
chapitres et des notions (déjà servis sans compte par /api/chapters),
compteurs (déjà servis par /api/site/stats) et textes de présentation
rédigés ci-dessous. Aucun cours, exercice, donnée élève ni conversation.

Le gabarit (webapp/static/maths-classe.html) passe par le build Vite pour
recevoir les feuilles de style hashées ; ce module remplace ses deux
marqueurs <!--SEO:HEAD--> et <!--SEO:BODY-->.
"""

import json
import re
from html import escape
from pathlib import Path

SITE_URL = "https://mathadap.com"
OG_IMAGE_URL = f"{SITE_URL}/og-image.png"

HEAD_MARKER = "<!--SEO:HEAD-->"
BODY_MARKER = "<!--SEO:BODY-->"

# Titres de secours des chapitres (« Chapitre 3 » → « Dérivation : ... »),
# déduits des notions — même table que l'application (cartes de chapitres,
# lecteur de cours) : lue directement dans ce fichier JS pour ne jamais
# maintenir deux copies divergentes.
_CHAPTER_TITLE_JS = Path(__file__).parent / "static" / "js" / "chapterTitleByNotions.js"
_GENERIC_TITLE_RE = re.compile(r"^chapitre\s+\d+$", re.IGNORECASE)
_NOTION_THEME_ENTRY_RE = re.compile(r'^\s*("(?:[^"\\]|\\.)*")\s*:\s*("(?:[^"\\]|\\.)*")\s*,?\s*$')
_notion_theme_cache = None


def _notion_theme():
    global _notion_theme_cache
    if _notion_theme_cache is None:
        source = _CHAPTER_TITLE_JS.read_text(encoding="utf-8")
        start = source.index("const NOTION_THEME = {")
        end = source.index("};", start)
        table = {}
        for line in source[start:end].splitlines()[1:]:
            match = _NOTION_THEME_ENTRY_RE.match(line)
            if match:
                table[json.loads(match.group(1))] = json.loads(match.group(2))
        _notion_theme_cache = table
    return _notion_theme_cache


def resolve_chapter_title(raw_title, notion_labels):
    """Port fidèle de chapterTitleByNotions.js::resolveChapterTitle : garde le
    titre fourni s'il n'est pas générique, sinon le thème le plus fréquent
    parmi les notions (premier rencontré en cas d'égalité)."""
    if raw_title and not _GENERIC_TITLE_RE.match(raw_title):
        return raw_title
    themes = _notion_theme()
    counts = {}
    for label in notion_labels or []:
        theme = themes.get(label)
        if theme:
            counts[theme] = counts.get(theme, 0) + 1
    best, best_count = None, 0
    for theme, count in counts.items():
        if count > best_count:
            best, best_count = theme, count
    return best or raw_title


def marketing_count(value):
    """Même arrondi que landing.js::roundedMarketingLabel (« Plus de 5 250 »)."""
    floor50 = (value // 50) * 50
    if floor50 >= 50:
        return "Plus de " + f"{floor50:,}".replace(",", " ")
    return str(value)


# ── Contenu éditorial par classe ─────────────────────────────────────────────
# `class_level` = identifiant du registre (curriculum_registry.py), jamais
# modifié. Chaque texte est propre à son niveau ; seuls les blocs « Comment
# Mathadap t'aide » et le pied de page sont communs.
CLASS_PAGES = {
    "quatrieme": {
        "slug": "maths-quatrieme",
        "nav_label": "Quatrième",
        "stage": "Collège",
        "title": "Maths 4e : cours et exercices corrigés de Quatrième | Mathadap",
        "description": (
            "Cours et exercices de maths de Quatrième corrigés pas à pas : nombres relatifs, fractions, "
            "puissances, Pythagore, Thalès, calcul littéral. Adaptés à ton niveau."
        ),
        "h1": "Maths en Quatrième : cours et exercices corrigés",
        "lead": (
            "Nombres relatifs, fractions, puissances, théorème de Pythagore, calcul littéral : la Quatrième "
            "pose les bases du calcul algébrique et de la géométrie du collège. Mathadap t'entraîne chapitre "
            "par chapitre avec des exercices qui s'adaptent à ton niveau."
        ),
        "focus_title": "Bien réussir son année de Quatrième",
        "focus": [
            ("Automatiser le calcul",
             "Les règles sur les nombres relatifs, les fractions et les puissances reviennent dans presque "
             "tous les chapitres : des séries ciblées t'aident à les appliquer sans hésiter."),
            ("Entrer dans le calcul littéral",
             "Développer, réduire, résoudre une équation : chaque étape de la méthode est expliquée pour que "
             "l'algèbre devienne un réflexe."),
            ("Rédiger en géométrie",
             "Pythagore, Thalès, cosinus, triangles égaux : les corrections détaillent le raisonnement "
             "attendu, pas seulement le résultat."),
        ],
        "faq": [
            ("Quels chapitres de maths de Quatrième sont couverts ?",
             "Les {chapters} chapitres présentés sur cette page : le calcul (nombres relatifs, fractions, "
             "puissances, calcul littéral, équations), la géométrie (Pythagore, Thalès, cosinus, "
             "translations, triangles égaux, espace), ainsi que les fonctions, les statistiques et les "
             "probabilités."),
            ("Je bloque sur les fractions, par où commencer ?",
             "Commence par le chapitre « Fractions : comparer, additionner et soustraire », puis enchaîne "
             "avec « Fractions : multiplier et diviser ». La difficulté des exercices s'ajuste à tes "
             "réponses au fil de l'entraînement."),
        ],
    },
    "troisieme": {
        "slug": "maths-troisieme",
        "nav_label": "Troisième",
        "stage": "Collège",
        "title": "Maths 3e : cours et exercices corrigés de Troisième | Mathadap",
        "description": (
            "Cours et exercices de maths de Troisième corrigés pas à pas : fonctions affines, Thalès, "
            "trigonométrie, probabilités. Révise le programme de 3e avant le brevet."
        ),
        "h1": "Maths en Troisième : cours et exercices corrigés",
        "lead": (
            "Fonctions affines, théorème de Thalès, trigonométrie, équations et inéquations : la Troisième "
            "fait le bilan des maths du collège avant le brevet et prépare l'entrée au lycée. Mathadap t'aide "
            "à consolider chaque chapitre, à ton rythme."
        ),
        "focus_title": "Bien réussir son année de Troisième",
        "focus": [
            ("Consolider les bases du collège",
             "Nombres entiers, fractions, calcul littéral : les exercices repèrent les notions fragiles et "
             "te les font retravailler jusqu'à ce qu'elles soient solides."),
            ("Comprendre les fonctions",
             "Notion de fonction, fonctions affines, lecture graphique : le cours et les exercices "
             "construisent pas à pas cette notion centrale pour le lycée."),
            ("Réviser avant le brevet",
             "Les modes Révisions, Examen blanc et Erreurs précédentes t'aident à revoir l'ensemble du "
             "programme et à cibler tes points faibles."),
        ],
        "faq": [
            ("Mathadap aide-t-il à préparer le brevet de maths ?",
             "Mathadap couvre les {chapters} chapitres de Troisième présentés sur cette page, avec des "
             "exercices corrigés et des modes de révision. Il ne propose pas de sujets d'annales du brevet : "
             "il t'aide à maîtriser les notions sur lesquelles tu seras évalué."),
            ("La trigonométrie me pose problème, que faire ?",
             "Le chapitre « Triangles rectangles : trigonométrie » reprend le cosinus, le sinus et la "
             "tangente avec des exercices de difficulté progressive, chacun accompagné d'un indice et d'une "
             "méthode détaillée."),
        ],
    },
    "seconde": {
        "slug": "maths-seconde",
        "nav_label": "Seconde",
        "stage": "Lycée",
        "title": "Maths Seconde : cours et exercices corrigés de 2nde | Mathadap",
        "description": (
            "Cours et exercices de maths de Seconde corrigés pas à pas : vecteurs, fonctions de référence, "
            "droites, inéquations, probabilités. Adaptés à ton niveau."
        ),
        "h1": "Maths en Seconde : cours et exercices corrigés",
        "lead": (
            "Vecteurs, fonctions de référence, équations de droites, inéquations : l'entrée au lycée demande "
            "plus d'abstraction et de rigueur. Mathadap t'accompagne dans cette transition avec des exercices "
            "adaptés et des méthodes expliquées pas à pas."
        ),
        "focus_title": "Bien réussir son année de Seconde",
        "focus": [
            ("Réussir la transition avec le collège",
             "Calcul littéral, intervalles, inégalités : les automatismes du collège sont repris et "
             "approfondis pour aborder sereinement les nouveaux chapitres."),
            ("Apprivoiser les fonctions",
             "Fonctions de référence, variations, extremums, signe : trois chapitres pour lire, étudier et "
             "représenter une fonction."),
            ("Préparer la suite du lycée",
             "Vecteurs, droites du plan, évolutions, statistiques et probabilités : des bases qui seront "
             "réutilisées en Première."),
        ],
        "faq": [
            ("Quels chapitres de maths de Seconde sont couverts ?",
             "Les {chapters} chapitres présentés sur cette page, des nombres et du calcul littéral jusqu'aux "
             "statistiques et aux probabilités, en passant par la géométrie, les vecteurs et les fonctions."),
            ("Je suis en difficulté sur les fonctions, par où commencer ?",
             "Commence par « Généralités sur les fonctions, fonctions de référence », puis enchaîne avec "
             "« Variations et extremums » et « Signe d'une fonction ». La difficulté des exercices s'ajuste à "
             "tes réponses."),
        ],
    },
    "premiere": {
        "slug": "maths-premiere-specialite",
        "nav_label": "Première spécialité",
        "stage": "Lycée",
        "title": "Maths Première spécialité : cours et exercices corrigés | Mathadap",
        "description": (
            "Cours et exercices corrigés de maths de Première spécialité : suites, second degré, dérivation, "
            "exponentielle, trigonométrie, produit scalaire, probabilités."
        ),
        "h1": "Maths en Première spécialité : cours et exercices corrigés",
        "lead": (
            "Suites, second degré, dérivation, fonction exponentielle, trigonométrie, produit scalaire, "
            "probabilités conditionnelles : la spécialité mathématiques de Première introduit de nombreux "
            "outils nouveaux. Mathadap t'aide à les maîtriser un par un."
        ),
        "focus_title": "Bien réussir sa Première spécialité maths",
        "focus": [
            ("Maîtriser la dérivation",
             "Nombre dérivé, tangente, fonction dérivée, puis variations et extremums : deux chapitres pour "
             "étudier une fonction de bout en bout."),
            ("Découvrir de nouvelles fonctions",
             "Polynômes du second degré, fonction exponentielle, cosinus et sinus : chaque fonction est "
             "travaillée en calcul et en lecture graphique."),
            ("Raisonner en géométrie et en probabilités",
             "Produit scalaire, géométrie repérée, probabilités conditionnelles et variables aléatoires : "
             "des exercices guidés pour structurer ton raisonnement."),
        ],
        "faq": [
            ("Quelle différence avec la Première spécifique ?",
             "La Première spécialité porte sur les grands thèmes de l'enseignement de spécialité "
             "mathématiques. La Première spécifique est un parcours distinct, construit sur le périmètre de "
             "l'ancienne Première ES/L. Chaque classe a ses propres cours, exercices et progression."),
            ("Quels chapitres sont abordés ?",
             "Les {chapters} chapitres présentés sur cette page : suites, second degré, dérivation, "
             "variations, exponentielle, trigonométrie, produit scalaire, géométrie repérée, probabilités "
             "conditionnelles et variables aléatoires."),
        ],
    },
    "premiere_specifique": {
        "slug": "maths-premiere-specifique",
        "nav_label": "Première spécifique",
        "stage": "Lycée",
        "title": "Maths Première spécifique (ex-ES/L) : cours et exercices | Mathadap",
        "description": (
            "Pourcentages, second degré, statistiques, dérivation, suites, loi binomiale : cours et exercices "
            "corrigés de Première, sur le périmètre de l'ex-1re ES/L."
        ),
        "h1": "Maths en Première spécifique : cours et exercices corrigés",
        "lead": (
            "Pourcentages et taux d'évolution, fonctions, second degré, statistiques, dérivation, suites, "
            "variables aléatoires et loi binomiale : un parcours de Première complet, avec des exercices "
            "corrigés qui s'adaptent à ton niveau."
        ),
        "notice": (
            "Origine du contenu : ce parcours reprend le périmètre de l'ancienne Première ES/L. Il ne "
            "correspond pas au programme officiel actuellement en vigueur. Il est indépendant de la Première "
            "spécialité, avec ses propres cours, exercices et progression."
        ),
        "focus_title": "Ce que tu travailles en Première spécifique",
        "focus": [
            ("Calculer avec les pourcentages",
             "Proportions, taux d'évolution, coefficient multiplicateur, évolutions successives et indices "
             "base 100 : des outils utiles bien au-delà des maths."),
            ("Étudier une fonction",
             "Fonctions de référence, second degré, dérivation et variations : la méthode complète pour "
             "étudier une fonction."),
            ("Analyser des données et le hasard",
             "Statistiques (quartiles, écart-type), variables aléatoires, loi binomiale et règle de "
             "décision."),
        ],
        "faq": [
            ("Ce parcours suit-il le programme officiel ?",
             "Non. Il est construit sur le périmètre de l'ancienne Première ES/L, qui n'est plus le programme "
             "officiel en vigueur. Pour la spécialité mathématiques, consulte la page Première spécialité."),
            ("Quels chapitres sont abordés ?",
             "Les {chapters} chapitres présentés sur cette page : pourcentages, fonctions numériques, "
             "polynômes du second degré, statistiques, dérivation, dérivation et variations, suites "
             "numériques, variables aléatoires, loi de Bernoulli et loi binomiale."),
        ],
    },
}

SLUG_TO_CLASS_LEVEL = {page["slug"]: level for level, page in CLASS_PAGES.items()}


def page_url(class_level):
    return f"{SITE_URL}/{CLASS_PAGES[class_level]['slug']}"


# ── Rendu ────────────────────────────────────────────────────────────────────
def _e(text):
    return escape(str(text), quote=True)


def _json_ld(data):
    # `</` échappé : un titre ne peut jamais fermer la balise <script>.
    return json.dumps(data, ensure_ascii=False, indent=2).replace("</", "<\\/")


def render_head(class_level):
    page = CLASS_PAGES[class_level]
    url = page_url(class_level)
    breadcrumb = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebPage",
                "@id": f"{url}#page",
                "url": url,
                "name": page["title"],
                "description": page["description"],
                "inLanguage": "fr",
                "isPartOf": {"@type": "WebSite", "name": "Mathadap", "url": f"{SITE_URL}/"},
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Accueil", "item": f"{SITE_URL}/"},
                    {"@type": "ListItem", "position": 2, "name": f"Maths {page['nav_label']}", "item": url},
                ],
            },
        ],
    }
    return "\n".join([
        f"<title>{_e(page['title'])}</title>",
        f'<meta name="description" content="{_e(page["description"])}" />',
        f'<link rel="canonical" href="{url}" />',
        '<meta property="og:type" content="website" />',
        '<meta property="og:site_name" content="Mathadap" />',
        '<meta property="og:locale" content="fr_FR" />',
        f'<meta property="og:url" content="{url}" />',
        f'<meta property="og:title" content="{_e(page["title"])}" />',
        f'<meta property="og:description" content="{_e(page["description"])}" />',
        f'<meta property="og:image" content="{OG_IMAGE_URL}" />',
        '<meta name="twitter:card" content="summary_large_image" />',
        f'<meta name="twitter:title" content="{_e(page["title"])}" />',
        f'<meta name="twitter:description" content="{_e(page["description"])}" />',
        f'<script type="application/ld+json">\n{_json_ld(breadcrumb)}\n</script>',
    ])


def _cta_buttons(class_level, logged_in, size="btn-lg"):
    label = CLASS_PAGES[class_level]["nav_label"]
    if logged_in:
        return (
            f'<a class="btn btn-primary {size}" href="/chapitres.html" data-set-class="{_e(class_level)}">'
            f"Continuer en {_e(label)}</a>"
        )
    return (
        f'<button class="btn btn-primary {size} js-open-signup" type="button" data-set-class="{_e(class_level)}">'
        "Créer un compte gratuit</button>\n"
        f'<button class="btn btn-secondary {size} js-open-login" type="button">Se connecter</button>'
    )


def _other_levels(class_level):
    items = []
    for level, page in CLASS_PAGES.items():
        if level == class_level:
            continue
        items.append(
            f'<li><a class="seo-level-link card" href="/{page["slug"]}">'
            f'<span class="seo-level-stage">{_e(page["stage"])}</span>'
            f'<span class="seo-level-name">Maths {_e(page["nav_label"])}</span></a></li>'
        )
    return "\n".join(items)


def _footer(logo_img=""):
    links = "\n".join(
        f'<li><a href="/{page["slug"]}">Maths {_e(page["nav_label"])}</a></li>' for page in CLASS_PAGES.values()
    )
    return f"""<footer class="site-footer">
  <div class="footer-grid">
    <div class="footer-col">
      <a class="brand" href="/">{logo_img}Mathadap</a>
      <p class="seo-footer-tagline">Cours et exercices de maths adaptatifs, du collège au lycée.</p>
    </div>
    <div class="footer-col">
      <h4>Classes</h4>
      <ul>
{links}
      </ul>
    </div>
    <div class="footer-col">
      <h4>Mathadap</h4>
      <ul>
        <li><a href="/">Accueil</a></li>
        <li><a href="/#tarifs">Tarifs</a></li>
        <li><a href="/#faq">FAQ</a></li>
      </ul>
    </div>
    <div class="footer-col">
      <h4>Légal</h4>
      <ul>
        <li><a href="/mentions-legales.html">Mentions légales</a></li>
        <li><a href="/confidentialite.html">Politique de confidentialité</a></li>
        <li><a href="/cgu.html">CGU</a></li>
      </ul>
    </div>
  </div>
  <div class="footer-bottom">
    <span>© 2026 Mathadap — Projet pédagogique.</span>
    <span>Fait avec soin pour les collégiens et les lycéens.</span>
  </div>
</footer>"""


def render_body(class_level, chapters, stats, logged_in, logo_src=None):
    """`chapters` : liste de {"title", "notions"} dans l'ordre du programme.
    `stats` : {"totalExercises", "notions", "difficultyLevels"} (mêmes sources que
    /api/site/stats)."""
    page = CLASS_PAGES[class_level]
    label = page["nav_label"]
    chapter_count = len(chapters)
    # Même compteur que le bandeau de l'accueil (/api/site/stats).
    notion_count = stats.get("notions") or sum(len(ch["notions"]) for ch in chapters)

    chapter_cards = []
    for index, chapter in enumerate(chapters, start=1):
        notions = "".join(f"<li>{_e(n)}</li>" for n in chapter["notions"])
        chapter_cards.append(
            f'<li class="seo-chapter card">\n'
            f'  <h3><span class="seo-chapter-num">{index}</span> {_e(chapter["title"])}</h3>\n'
            f'  <ul class="seo-notions">{notions}</ul>\n'
            f"</li>"
        )

    focus = "\n".join(
        f'<div class="seo-focus card"><h3>{_e(title)}</h3><p>{_e(text)}</p></div>' for title, text in page["focus"]
    )
    faq_items = list(page["faq"]) + [
        ("Mathadap est-il gratuit ?",
         "Oui. Les cours complets, les exercices, les corrections, les révisions et le suivi de progression sont "
         "gratuits, sans carte bancaire ni engagement. Seul l'assistant IA est limité à un nombre de messages par jour."),
    ]
    faq = "\n".join(
        f'<details class="seo-faq-item"><summary>{_e(q)}</summary>'
        f"<p>{_e(a.format(chapters=chapter_count))}</p></details>"
        for q, a in faq_items
    )
    notice = (
        f'<aside class="seo-notice" role="note"><p>{_e(page["notice"])}</p></aside>' if page.get("notice") else ""
    )
    logo_img = f'<img src="{_e(logo_src)}" alt="" /> ' if logo_src else ""
    exercises_label = marketing_count(stats.get("totalExercises", 0))
    difficulty_levels = stats.get("difficultyLevels", 0)

    return f"""<nav class="topnav">
  <div class="topnav-left">
    <a href="/" class="brand">{logo_img}Mathadap</a>
  </div>
  <div class="nav-links">
    <a href="#programme">Programme</a>
    <a href="#methode">Méthode</a>
    <a href="#faq">FAQ</a>
    <a href="#autres-classes">Autres classes</a>
  </div>
  <div class="nav-actions">
    <button class="theme-toggle" id="theme-toggle" type="button" aria-label="Changer de thème">
      <svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></svg>
      <svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8Z" /></svg>
    </button>
    {"" if logged_in else '<button class="btn btn-ghost btn-sm js-open-login" type="button">Se connecter</button>'}
  </div>
</nav>

<main class="seo-page">
  <nav class="seo-breadcrumb" aria-label="Fil d'Ariane">
    <ol>
      <li><a href="/">Accueil</a></li>
      <li aria-current="page">Maths {_e(label)}</li>
    </ol>
  </nav>

  <header class="seo-hero">
    <span class="badge badge--indigo">{_e(page["stage"])} · {_e(label)}</span>
    <h1>{_e(page["h1"])}</h1>
    <p class="seo-lead">{_e(page["lead"])}</p>
    {notice}
    <div class="seo-cta">
{_cta_buttons(class_level, logged_in)}
    </div>
    <p class="seo-cta-note">Gratuit, sans carte bancaire ni engagement.</p>
  </header>

  <section class="seo-stats" aria-label="Mathadap en {_e(label)} en chiffres">
    <div class="seo-stat"><strong>{chapter_count}</strong><span>chapitres</span></div>
    <div class="seo-stat"><strong>{notion_count}</strong><span>notions</span></div>
    <div class="seo-stat"><strong>{_e(exercises_label)}</strong><span>exercices</span></div>
    <div class="seo-stat"><strong>{difficulty_levels}</strong><span>niveaux de difficulté</span></div>
  </section>

  <section class="seo-section" id="programme">
    <div class="section-header">
      <span class="section-tag">Programme</span>
      <h2>Les {chapter_count} chapitres de maths en {_e(label)}</h2>
      <p>Chaque chapitre propose un cours et des séries d'exercices par notion.</p>
    </div>
    <ol class="seo-chapters">
{chr(10).join(chapter_cards)}
    </ol>
  </section>

  <section class="seo-section" id="objectifs">
    <div class="section-header">
      <span class="section-tag">Objectifs</span>
      <h2>{_e(page["focus_title"])}</h2>
    </div>
    <div class="seo-focus-grid">
{focus}
    </div>
  </section>

  <section class="seo-section" id="methode">
    <div class="section-header">
      <span class="section-tag">Méthode</span>
      <h2>Comment Mathadap t'aide en {_e(label)}</h2>
    </div>
    <ul class="seo-features">
      <li><strong>Une difficulté qui suit tes résultats.</strong> Pour chaque notion, la difficulté monte ou descend selon tes réponses, par blocs de 5 exercices ; les révisions reprennent en priorité tes notions les plus fragiles.</li>
      <li><strong>Une méthode pas à pas.</strong> Chaque exercice propose un indice, la méthode détaillée et la solution.</li>
      <li><strong>Un cours par chapitre.</strong> Définitions, propriétés, exemples et démonstrations, gratuits pour tous.</li>
      <li><strong>Un assistant IA.</strong> Il répond à tes questions sur l'exercice en cours, dans la limite d'un nombre de messages par jour.</li>
      <li><strong>Un suivi de progression.</strong> Chapitres maîtrisés, notions à revoir et historique de tes réponses.</li>
    </ul>
  </section>

  <section class="seo-section" id="faq">
    <div class="section-header">
      <span class="section-tag">FAQ</span>
      <h2>Questions fréquentes sur les maths en {_e(label)}</h2>
    </div>
    <div class="seo-faq">
{faq}
    </div>
  </section>

  <section class="seo-section">
    <div class="cta-final">
      <h2>Commence à progresser en {_e(label)}</h2>
      <p>Crée ton compte gratuitement et retrouve ta progression d'une session à l'autre.</p>
      <div class="seo-cta seo-cta--center">
{_cta_buttons(class_level, logged_in)}
      </div>
    </div>
  </section>

  <section class="seo-section" id="autres-classes">
    <div class="section-header">
      <span class="section-tag">Autres classes</span>
      <h2>Mathadap dans les autres classes</h2>
    </div>
    <ul class="seo-levels">
{_other_levels(class_level)}
      <li><a class="seo-level-link card" href="/"><span class="seo-level-stage">Mathadap</span><span class="seo-level-name">Retour à l'accueil</span></a></li>
    </ul>
  </section>
</main>

{_footer(logo_img)}"""


def render_page(template_html, class_level, chapters, stats, logged_in):
    if HEAD_MARKER not in template_html or BODY_MARKER not in template_html:
        raise ValueError("gabarit maths-classe.html sans marqueurs SEO")
    # Logo : même fichier (hashé par Vite) que l'icône déclarée dans le gabarit.
    icon = re.search(r'<link rel="icon" href="([^"]+)"', template_html)
    logo_src = icon.group(1) if icon else None
    html = template_html.replace(HEAD_MARKER, render_head(class_level), 1)
    return html.replace(BODY_MARKER, render_body(class_level, chapters, stats, logged_in, logo_src), 1)
