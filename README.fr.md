<img src="icon.png" alt="Icône Endfield Check-in" width="88" align="right">

# Endfield Check-in pour Unraid

[English](README.md) · [Signaler un problème](https://github.com/MrPatates/endfield-checkin/issues)

Un conteneur Docker qui récupère automatiquement les récompenses de connexion quotidienne d'**Arknights: Endfield** sur la [page de check-in SKPORT](https://game.skport.com/endfield/sign-in). Tu connectes ton compte une fois depuis l'interface web, puis le bot récupère la récompense chaque jour pour tous les personnages liés au compte.

Projet communautaire, non affilié à GRYPHLINE, Hypergryph ou SKPORT.

![Interface web avec le calendrier mensuel des récompenses](docs/screenshot.png)

## Fonctionnalités

- Connexion par **jeton de compte** (`ACCOUNT_TOKEN`) ou par **e-mail + mot de passe**.
- Plusieurs comptes, et tous les personnages Endfield de chaque compte (détection automatique du serveur).
- Vérification toutes les 2 h par défaut : la récompense est récupérée dès qu'elle est disponible, quelle que soit l'heure de réinitialisation de la région du serveur. Après une erreur réseau ou serveur, nouvel essai au bout de 15 min.
- Interface web dans les 27 langues proposées par Unraid, choisie automatiquement selon le navigateur ou fixée avec `UI_LANGUAGE` ; l'arabe s'affiche de droite à gauche. Elle montre le calendrier du mois, le bonus des trois premières connexions, les dernières récompenses, l'historique et un bouton « Récupérer maintenant ».
- Chaque compte prend automatiquement le nom du pseudo en jeu.
- Notifications Discord optionnelles : récompenses, erreurs, jeton expiré.
- Image légère (~50 Mo), Python sans aucune dépendance externe. Le conteneur passe en utilisateur `99:100` (nobody:users) après le démarrage.

## Fonctionnement

Le bot fait les mêmes appels que la page web officielle :

1. `ACCOUNT_TOKEN` → code OAuth (`as.gryphline.com`) ;
2. code → `cred` et jeton de signature (`zonai.skport.com`) ;
3. liste des personnages Endfield liés au compte ;
4. statut du check-in (`hasToday`) ; si la récompense n'est pas encore prise, envoi du check-in signé (HMAC-SHA256 puis MD5, comme sur le site).

Chaque vérification coûte une requête légère par personnage. La session est gardée en mémoire et renouvelée automatiquement à partir du jeton.

## Installation sur Unraid

1. Ouvre l'onglet **Apps** (Community Applications) et cherche **Endfield Check-in**.
2. Clique sur **Install**. Choisis éventuellement la langue des récompenses (`fr_FR`), un webhook Discord ou un mot de passe d'interface, puis clique sur **Apply**.
3. Ouvre la **WebUI** depuis l'onglet Docker (`http://<ip-unraid>:8080`) et connecte ton compte.

Les mises à jour sont proposées dans l'onglet Docker, comme pour les autres conteneurs.

## Connecter son compte

**Méthode du jeton (recommandée)**

1. Ouvre <https://game.skport.com/endfield/sign-in> et connecte-toi.
2. Appuie sur **F12**. Dans Chrome/Edge, va dans **Application → Cookies** ; dans Firefox, va dans **Stockage → Cookies**.
3. Sélectionne `https://game.skport.com` et copie la valeur du cookie **`ACCOUNT_TOKEN`**.
4. Colle-la dans l'interface web, puis clique sur **Connecter le compte**. Le jeton est vérifié avant d'être enregistré, le compte prend le nom de ton pseudo en jeu, puis une première récupération démarre.

**Méthode e-mail + mot de passe**

Le bot se connecte une fois et ne garde que le jeton obtenu. Si tu coches « Mémoriser », l'e-mail et le mot de passe sont aussi stockés dans `/config` pour se reconnecter automatiquement quand le jeton expire. Les comptes créés avec Google, Apple, etc. n'ont pas de mot de passe : utilise alors le jeton.

Quand un jeton expire sans mot de passe enregistré, l'interface affiche **Action requise** et Discord te prévient (une seule fois). Il suffit de reconnecter le compte.

## Réglages (variables du template)

| Variable | Défaut | Rôle |
| --- | --- | --- |
| `CHECK_INTERVAL` | `120` | Minutes entre deux vérifications (30–720). |
| `UI_LANGUAGE` | `auto` | Langue de l'interface web et des notifications Discord. `auto` suit la langue de chaque navigateur ; sinon, une des langues d'Unraid : `ar_AR`, `bn_BN`, `ca_CA`, `cs_CZ`, `da_DA`, `de_DE`, `el_GR`, `en_US`, `es_ES`, `fr_FR`, `hr_HR`, `hu_HU`, `it_IT`, `ja_JA`, `ko_KO`, `lv_LV`, `nl_NL`, `no_NO`, `pl_PL`, `pt_BR`, `pt_PT`, `ro_RO`, `ru_RU`, `sv_SE`, `uk_UA`, `zh_CN`, `zh_TW`. En `auto`, les notifications suivent `SKPORT_LANGUAGE`. |
| `SKPORT_LANGUAGE` | `en` | Langue des noms de récompenses, selon ce que propose SKPORT : `en`, `fr_FR`, `de_DE`, `it_IT`, `es_MX`, `pt_BR`, `ru_RU`, `ja`, `ko`, `zh_Hans`, `zh_Hant`, `id_ID`, `th_TH`, `vi_VN`. |
| `DISCORD_WEBHOOK` | vide | URL de webhook Discord (optionnelle). |
| `NOTIFY` | `all` | `all` = récompenses et erreurs, `errors` = erreurs seulement, `none` = aucune notification. |
| `WEBUI_PASSWORD` | vide | Protège l'interface par un mot de passe (n'importe quel nom d'utilisateur). |
| `ACCOUNT_TOKEN` | vide | Avancé : jeton(s) séparés par des virgules, à la place de l'interface web. |
| `ACCOUNT_NAME` | vide | Nom affiché pour les comptes définis par `ACCOUNT_TOKEN`. Vide : le pseudo en jeu est utilisé. |
| `RETRY_INTERVAL` | `15` | Minutes avant un nouvel essai après une erreur (5–240). |
| `PUID` / `PGID` | `99` / `100` | Propriétaire des fichiers de `/config`. |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`. |

Unraid transmet `TZ` automatiquement : les heures affichées et les logs suivent le fuseau du serveur.

## Sécurité

- Le jeton `ACCOUNT_TOKEN` donne accès à ton compte, comme un mot de passe. Il est stocké dans `/config/accounts.json` en mode `0600`, n'apparaît jamais dans les logs et n'est jamais renvoyé par l'interface, qui n'affiche que ses 4 derniers caractères.
- L'interface est prévue pour ton réseau local. Ne l'expose pas sur Internet ; définis `WEBUI_PASSWORD` si d'autres personnes utilisent ton réseau.
- Les actions de l'interface sont protégées contre le CSRF (jeton + JSON obligatoire + contrôle de l'origine), et une politique CSP stricte est appliquée.
- Les requêtes vont uniquement vers `as.gryphline.com`, `zonai.skport.com`, et vers ton webhook Discord si tu en configures un. Les icônes des récompenses sont chargées par ton navigateur depuis `static.skport.com`.

## Traductions

Les catalogues de l'interface sont dans [`app/endfield_checkin/static/lang/`](app/endfield_checkin/static/lang/), un fichier JSON par langue d'Unraid, avec `en_US.json` comme référence. Une entrée manquante ou vide s'affiche en anglais. La plupart des traductions ont été générées automatiquement et n'ont pas été relues par des locuteurs natifs : les corrections sont bienvenues. Garde les clés et les balises comme `{n}` ou `{name}` intactes, utilise du texte brut uniquement, puis lance les tests.

## Limites

Ce bot repose sur l'API non documentée du site SKPORT, analysée à partir de la page officielle et de projets open source. Il peut cesser de fonctionner si SKPORT modifie son API. L'automatisation peut aussi être contraire aux conditions d'utilisation du service : utilise-le à tes risques.

## Développement

```bash
cd tests && python3 -m unittest discover -s . -t . -v   # faux serveur SKPORT inclus
podman build --format docker -t endfield-checkin:dev .  # ou docker build
```

Le workflow GitHub [`docker.yml`](.github/workflows/docker.yml) lance les tests, puis publie `ghcr.io/mrpatates/endfield-checkin` (amd64 + arm64) à chaque push sur `main` ou à chaque tag `v*`. Après la première publication, rends le paquet GHCR **public** pour qu'Unraid puisse le télécharger sans identifiants.

Licence : GPL-3.0-or-later.
