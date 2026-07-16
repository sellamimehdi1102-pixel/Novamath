# TODO — Prochaines améliorations possibles

> Le produit s'appelle désormais **NovaMath** (anciennement Lumis). Les repères "Depuis Lumis V2/V3"
> ci-dessous sont des jalons historiques réels et ne sont pas renommés, pour rester fidèles à quand
> chaque point a été identifié.

## Mode invité (depuis NovaMath v1.12)
- [ ] Pas de navigateur headless disponible pour vérifier visuellement le nouveau composant sidebar
      "Créer un compte" (glassmorphism, hover, clic) — à confirmer manuellement.
- [ ] La landing page (`/` et `/index.html`) est désormais l'unique déclencheur explicite de fin de session
      invité ; si d'autres points d'entrée statiques équivalents (ex: un futur alias `/accueil.html`) sont
      ajoutés un jour, il faudra les enregistrer sur la même vue `_serve_landing()` plutôt que de les laisser
      passer par le handler statique automatique de Flask.

## Mode invité (depuis NovaMath v1.11)
- [ ] Pas de navigateur headless disponible pour vérifier visuellement l'animation du flou du Dashboard,
      de la carte de déverrouillage et le responsive réel — à confirmer manuellement.
- [ ] L'expiration par inactivité (2h, `GUEST_IDLE_TTL_MINUTES`) n'est appliquée qu'à la prochaine requête
      de l'invité concerné, pas par une tâche planifiée — un invité inactif qui ne revient jamais laisse sa
      ligne en base jusqu'au prochain `cleanup_expired_guests()` (déclenché par une nouvelle entrée invité).
- [ ] Le cookie de session invité non persistant protège contre la fermeture complète du navigateur, mais
      pas contre la fermeture d'un seul onglet parmi plusieurs onglets ouverts (les cookies ne sont pas
      isolés par onglet) — l'expiration par inactivité reste le filet de sécurité dans ce cas.

## Mode invité (depuis NovaMath v1.10)
- [ ] Pas de navigateur headless disponible pour vérifier visuellement l'animation de la carte
      d'information du Dashboard, sa fermeture, et le responsive réel — à confirmer manuellement.
- [ ] La carte d'information du Dashboard revient si l'onglet est fermé puis rouvert (sessionStorage) — si un
      comportement "ne plus jamais réafficher, même après réouverture" est souhaité plus tard, il faudrait
      passer à un stockage côté compte invité plutôt que sessionStorage.

## Mode invité (depuis NovaMath v1.09)
- [ ] Pas de navigateur headless disponible pour vérifier visuellement l'animation du panneau flottant/de la
      carte premium ni le responsive réel — à confirmer manuellement (desktop/tablette/mobile).
- [ ] Le nettoyage des comptes invités expirés (`db.cleanup_expired_guests`) n'est déclenché qu'à l'entrée
      d'un nouvel invité — envisager un nettoyage périodique indépendant si le volume de visiteurs augmente.
- [ ] La limite de 2 chapitres en mode invité ne s'applique qu'à la sélection multi-chapitres pour
      l'évaluation ; le lancement direct d'une série ciblée sur une notion (depuis Chapitres) n'est pas
      concerné par cette limite — à clarifier si une restriction est aussi souhaitée à cet endroit.

## Sécurité (depuis NovaMath V8)
- [ ] `style-src 'unsafe-inline'` reste actif dans la CSP — migrer les styles inline générés en JS
      (`dashboard.js`, `profil.js`, `reviews.js`, `seriesview.js`...) vers des classes CSS permettrait de le
      retirer et d'avoir une CSP strict sur `style-src` aussi (déjà strict sur `script-src` via nonce).
- [ ] Pas de rate limiting générique par IP sur l'ensemble de l'API (seule `/api/auth/login` a un anti
      brute-force dédié) — envisager Flask-Limiter avant un déploiement public à fort trafic.
- [ ] Le flux de suppression de compte (modale profil.html/profil.js) n'a été vérifié que via l'API — à
      confirmer visuellement (activation du bouton après case cochée, affichage des erreurs de mot de passe).
- [ ] `secure=False` sur les cookies `nm_session`/`nm_csrf` — à activer avant tout déploiement public HTTPS.

## Comptes / Authentification (depuis NovaMath V7)
- [ ] Le scénario "changer de compte dans le même onglet" (garde `syncAccountScope` dans `store.js`) n'a été
      vérifié que via `curl`/inspection de base de données — à confirmer visuellement dans un vrai navigateur
      (créer compte A, faire des exercices, se déconnecter, créer compte B, vérifier un dashboard vide).
- [ ] Un avis de test ("Test Persistance") d'une session antérieure traîne dans `data/reviews.json` — à
      supprimer manuellement si confirmé qu'il ne s'agit pas d'un vrai avis.

## Comptes / Authentification (depuis NovaMath V6)
- [ ] Aucun envoi d'email réel n'est branché pour "mot de passe oublié" — le lien de réinitialisation est
      seulement affiché en console/réponse JSON (mode développement). Brancher un vrai fournisseur
      SMTP/API avant tout déploiement.
- [ ] Google OAuth est prêt architecturalement (`OAUTH_PROVIDERS`, table `oauth_accounts`, routes
      `/api/auth/google/start|callback`) mais nécessite `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` pour
      être réellement activé. Idem pour Microsoft/Apple/GitHub (ajouter une entrée + fonction d'échange).
- [ ] Cookie de session en `secure=False` (HTTP local) — à passer en `True` avant un déploiement public
      HTTPS.
- [ ] Le mode administrateur des avis (`X-Admin-Key`) pourrait maintenant s'appuyer sur un vrai rôle
      admin en base (`users.is_admin`) plutôt qu'une clé statique séparée, une fois les comptes en place.
- [ ] Pas de "supprimer mon compte" implémenté côté UI (mentionné dans la politique de confidentialité
      comme un droit de l'utilisateur) — à ajouter : route `DELETE /api/auth/me` + confirmation.
- [ ] Le nom d'utilisateur n'est pas modifiable depuis le profil (choix actuel) — envisager de l'autoriser
      avec une limite de fréquence si demandé plus tard.

## Avis (depuis NovaMath V3)
- [ ] Le mode administrateur repose sur une clé statique envoyée à chaque requête (`X-Admin-Key`), sans
      session ni expiration — suffisant en local mono-utilisateur, à remplacer par une vraie
      authentification (variable d'environnement + session) avant tout déploiement public.
- [ ] Les avatars sont stockés en base64 directement dans `data/reviews.json` — au-delà de quelques
      centaines d'avis avec photo, envisager un dossier `data/avatars/` avec des fichiers séparés plutôt
      que d'alourdir le JSON.
- [ ] Pas de navigateur headless disponible pour vérifier visuellement les interactions (survol des
      étoiles, responsive mobile/tablette réel, focus clavier) — à tester manuellement.

## Fiabilité des données
- [ ] Le champ `duration_s` n'existe que pour les réponses enregistrées depuis Lumis V2 — envisager un
      indicateur visuel ("donnée partielle") sur "Temps moyen" tant que l'historique est jeune.
- [ ] `hydrateFromServer()` écrase le local si le serveur a un historique plus long : ajouter une vraie
      fusion (merge par `id` de série) au lieu d'un simple "le plus long gagne", pour supporter plusieurs
      appareils sans perte de données.

## Entraînement
- [ ] "Objectif du jour" utilise actuellement le même pool que "Révisions" — lui donner une logique propre
      (ex : nombre d'exercices restants pour atteindre un objectif quotidien réglable).
- [ ] "Défi chronométré" pourrait afficher un résumé du temps moyen par question dans le récapitulatif.
- [ ] Mode "Erreurs précédentes" : une fois une erreur corrigée dans une série ultérieure, envisager de la
      retirer automatiquement du pool si elle a été réussie 2 fois de suite.

## Chapitres
- [ ] Le calcul du "temps estimé restant" (`remaining × 3 min`) reste une estimation grossière — le remplacer
      par la moyenne réelle observée (`duration_s`) une fois suffisamment de données disponibles.

## Dashboard / Profil
- [ ] Ajouter un export CSV/PDF de l'historique des séries.
- [ ] Le graphique de progression pourrait proposer un filtre par chapitre en plus du zoom temporel.
- [ ] Ajouter une pagination ou un "charger plus" sur le radar de compétences quand le nombre de chapitres
      travaillés devient important (actuellement lisible jusqu'à ~12).

## Versionnement
- [ ] Ajouter une commande `diff` (ou un simple `git`-like) pour comparer deux dossiers `versions/Lumis_V*`
      et lister les fichiers modifiés, en complément du CHANGELOG rédigé manuellement.
- [ ] Envisager de git-initialiser le projet pour bénéficier d'un vrai contrôle de version en plus des
      snapshots (le versionnement actuel est un instantané complet, pas un diff).

## Qualité
- [ ] Mettre en place un test end-to-end automatisé (ex: Playwright) une fois un environnement avec
      navigateur headless disponible — actuellement la vérification UI est manuelle.

## Depuis Lumis V3
- [ ] Le bouton "Aller au chapitre" ne pré-sélectionne une notion faible que pour les chapitres "à revoir" —
      envisager un comportement similaire pour les chapitres maîtrisés (ex: la notion la moins pratiquée).
- [ ] Une seule série "en cours" à la fois (clé unique `lumis:series_in_progress`) : si l'élève démarre une
      nouvelle série sans terminer la précédente, l'ancienne est silencieusement remplacée. Envisager un
      avertissement ("Une série est déjà en cours, la reprendre ou l'abandonner ?") avant de la remplacer.
- [ ] `js/icons.js` et les icônes inline dupliquées dans les fichiers HTML utilisent le même tracé SVG à deux
      endroits (JS et HTML statique) — envisager de tout centraliser via un sprite `<svg><symbol>` chargé une
      fois par page, pour n'avoir qu'une seule source de vérité par icône.
