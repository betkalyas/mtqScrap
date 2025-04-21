# Scraper de Signalisation Routière du Québec

## Description

Ce script permet d'extraire des données de signalisation routière du ministère des Transports du Québec (MTQ) à partir des pages individuelles de chaque dispositif. Il télécharge également les images associées en les renommant avec le numéro de référence du panneau.

## Nouveautés

- **Lecture du fichier CSV** : Le script vérifie les CID déjà traités pour éviter de rescaper les données existantes.
- **Gestion des images manquantes** : Seules les pages contenant une image sont traitées.
- **Robustesse accrue** : Chaque champ est vérifié avant extraction pour éviter les erreurs.

## Fonctionnalités
- **Gestion de plage de numéros (CID) personnalisable**
- **Limitation de vitesse pour respecter les serveurs**
- **Scraping de données structurées** : Numéro, nom, dimensions, couleurs, usages, etc.
- **Téléchargement automatisé des images** : Les images sont sauvegardées dans un dossier dédié.
- **Gestion des doublons** : Utilisation d'un fichier `cid.csv` pour éviter de rescaper les mêmes données.
- **Modes d'exécution flexibles** :
  - **`full`** : Traite tous les CID dans la plage spécifiée.
  - **`minimal`** : Ignore les CID déjà traités (par défaut).
  - **`partial`** : Ignore uniquement les CID sans image.
- **Fichier d'historique** : Enregistre les détails des exécutions précédentes (date, heure, mode).

## Prérequis
- Python 3.8 ou supérieur
- Bibliothèques Python : `requests`, `beautifulsoup4`, `pandas`, `tqdm`

Installez les dépendances avec :
```bash
pip install -r requirements.txt
