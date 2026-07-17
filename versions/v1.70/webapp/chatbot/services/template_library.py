"""
Bibliothèque de variantes de formulation par intention "donnée locale"
(progression/statistique/dashboard/profil/paramètres/série — Phase O/P). Pas
une bibliothèque de centaines de textes figés (cf. cahier des charges,
section 8 : "un véritable moteur de génération", pas une liste statique) :
3 à 5 variantes par intention, combinées par response_composer.py avec les
variables réelles (variable_resolver.py) et l'habillage mode/longueur — le
nombre de sorties concrètes dépasse largement la centaine sans dupliquer de
texte, et ajouter une nuance de formulation ne coûte qu'une ligne.
"""
from . import intent_service

TEMPLATES = {
    intent_service.PROGRESSION: [
        "D'après tes résultats, tu maîtrises : {chapitres_maitrises}. Je te conseille de revoir : {chapitres_non_maitrises}. Ton accuracy globale est de {accuracy}%.",
        "Voici ta progression : chapitres maîtrisés — {chapitres_maitrises} ; à retravailler — {chapitres_non_maitrises}. Tu es à {progression}% de maîtrise globale.",
        "Ton meilleur chapitre est {meilleur_chapitre}, et {chapitre_le_plus_faible} mérite un peu plus d'entraînement.",
        "Bilan de ta progression : {progression}% des chapitres travaillés sont maîtrisés. Chapitres maîtrisés : {chapitres_maitrises}.",
        "Continue comme ça, {prenom} ! Chapitres déjà solides : {chapitres_maitrises}. À consolider : {chapitres_non_maitrises}.",
    ],
    intent_service.STATISTIQUE: [
        "Tes statistiques : accuracy globale {accuracy}%, {nombre_exercices} exercices réalisés, {nombre_quiz} séries terminées.",
        "Voici tes chiffres : précision {precision}%, temps total {temps_total} (dont {temps_semaine} cette semaine).",
        "Tu as travaillé {temps_jour} aujourd'hui, {temps_semaine} cette semaine, {temps_total} au total. Précision actuelle : {accuracy}%.",
        "Statistiques actuelles — accuracy : {accuracy}% · exercices faits : {nombre_exercices} · temps total : {temps_total}.",
    ],
    intent_service.DASHBOARD: [
        "Vue d'ensemble : niveau {niveau}, accuracy {accuracy}%, objectif du jour {objectif}. Chapitres en cours : {chapitres_en_cours}.",
        "Sur ton dashboard : {chapitres_en_cours} en cours, {chapitres_maitrises} maîtrisés, objectif du jour {objectif}.",
        "Résumé rapide, {prenom} : niveau {niveau}, {progression}% de progression globale, objectif du jour {objectif}.",
    ],
    intent_service.PROFIL: [
        "Ton profil : {prenom}, niveau {niveau}. Favoris : {favoris}.",
        "Voici ton profil NovaMath : niveau {niveau}, précision {precision}%, favoris enregistrés : {favoris}.",
        "{prenom}, niveau {niveau}. Chapitres favoris : {favoris}.",
    ],
    intent_service.PARAMETRES: [
        "Paramètres actifs : mode {learning_mode}, longueur de réponse {response_length}.",
        "Tes réglages actuels : mode {learning_mode}, réponses en format {response_length}.",
    ],
    intent_service.SERIE: [
        "Série en cours : {serie_actuelle}.",
        "Tu es actuellement sur : {serie_actuelle}.",
        "Ta série active : {serie_actuelle}. Dernier chapitre travaillé : {dernier_chapitre}.",
    ],
}
