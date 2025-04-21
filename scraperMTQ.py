import os
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin
from tqdm import tqdm
from datetime import datetime

# Configuration
BASE_URL = "https://www.rsr.transports.gouv.qc.ca/Dispositifs/Details.aspx"
IMAGE_DIR = "images_signaux"
CSV_FILE = "signaux_routiers.csv"
CID_FILE = "cid.csv"
HISTORY_FILE = "historique.log"

# Créer les dossiers nécessaires
os.makedirs(IMAGE_DIR, exist_ok=True)


def log_execution(mode):
    """
    Enregistre les détails de l'exécution dans un fichier d'historique.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(HISTORY_FILE, "a") as f:
        f.write(f"{timestamp} - Mode: {mode}\n")


def load_cid_data():
    """
    Charge les données des CID depuis cid.csv.
    Retourne un DataFrame Pandas.
    """
    if os.path.exists(CID_FILE):
        return pd.read_csv(CID_FILE)
    return pd.DataFrame(columns=["cid", "has_image"])


def save_cid_data(cid_df):
    """
    Sauvegarde les données des CID dans cid.csv.
    """
    cid_df.to_csv(CID_FILE, index=False)


def load_signal_data():
    """
    Charge les données existantes depuis signaux_routiers.csv.
    Retourne un DataFrame Pandas.
    """
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    return pd.DataFrame()


def update_signal_data(existing_df, new_data):
    """
    Met à jour les données existantes avec les nouvelles données.
    Si un CID existe déjà, ses données sont mises à jour.
    Sinon, une nouvelle ligne est ajoutée.
    """
    new_df = pd.DataFrame(new_data)
    combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    # Supprimer les doublons en gardant la dernière occurrence (mise à jour)
    combined_df = combined_df.drop_duplicates(subset=["cid"], keep="last")
    return combined_df


def check_image(cid):
    """
    Vérifie si un CID a une image.
    """
    url = f"{BASE_URL}?cid={cid}"
    response = requests.get(url)
    if response.status_code != 200:
        return False

    soup = BeautifulSoup(response.content, 'html.parser')
    image_container = soup.find("div", id="Image220Centrer")
    return bool(image_container and image_container.find("img"))


def scraper(cid_start, cid_end, mode="minimal"):
    """
    Scraper principal avec trois modes d'exécution :
    - "full" : Tous les CID sont traités.
    - "minimal" : Ignore les CID déjà dans cid.csv (par défaut).
    - "partial" : Ignore seulement les CID sans image.
    """
    # Charger les CID existants
    cid_df = load_cid_data()
    existing_cids = set(cid_df["cid"]) if not cid_df.empty else set()
    data_list = []

    # Charger les données existantes de signalisation routière
    existing_signal_data = load_signal_data()

    for cid in tqdm(range(cid_start, cid_end + 1), desc=f"Mode {mode}"):
        # Mode minimal : Ignorer les CID déjà dans cid.csv
        if mode == "minimal" and cid in existing_cids:
            print(f"CID {cid} déjà traité. Passage au suivant.")
            continue

        # Mode partiel : Ignorer les CID sans image
        if mode == "partial":
            if cid in existing_cids and cid_df.loc[cid_df["cid"] == cid, "has_image"].values[0] == False:
                print(f"CID {cid} sans image. Passage au suivant.")
                continue

        # Vérifier l'existence de l'image
        has_image = check_image(cid)
        if not has_image:
            print(f"Pas d'image trouvée pour CID {cid}. Ajout à cid.csv.")
            cid_df = pd.concat([cid_df, pd.DataFrame(
                {"cid": [cid], "has_image": [False]})], ignore_index=True)
            save_cid_data(cid_df)
            continue

        # Télécharger la page et extraire les données
        url = f"{BASE_URL}?cid={cid}"
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Erreur {response.status_code} pour CID {cid}")
            continue

        soup = BeautifulSoup(response.content, 'html.parser')

        # Initialiser un dictionnaire pour stocker les données
        data = {"cid": cid}

        try:
            # Extraire les données avec vérification de l'existence des champs
            data["Numero"] = soup.find(
                "span", id="ctl00_cphContenu_FicheDetails_txtNumero").text.strip().replace("\n", " ").replace("\r", "") \
                if soup.find("span", id="ctl00_cphContenu_FicheDetails_txtNumero") else "N/A"

            data["Nom"] = soup.find("span", id="ctl00_cphContenu_FicheDetails_txtNom").text.strip().replace("\n", " ").replace("\r", "") \
                if soup.find("span", id="ctl00_cphContenu_FicheDetails_txtNom") else "N/A"

            # Gestion des références (Tome V ou VHR)
            reference_tome_v = soup.find(
                "span", id="ctl00_cphContenu_FicheDetails_txtReferenceTomeV")
            reference_vhr = soup.find(
                "span", id="ctl00_cphContenu_FicheDetails_txtReferenceVHR")
            data["Reference_Tome_V"] = reference_tome_v.text.strip().replace(
                "\n", " ").replace("\r", "") if reference_tome_v else "N/A"
            data["Reference_VHR"] = reference_vhr.text.strip(
            ) if reference_vhr else "N/A"

            data["Description"] = soup.find(
                "span", id="ctl00_cphContenu_FicheDetails_txtDescription").text.strip().replace("\n", " ").replace("\r", "") \
                if soup.find("span", id="ctl00_cphContenu_FicheDetails_txtDescription") else "N/A"

            data["Usages"] = soup.find(
                "span", id="ctl00_cphContenu_FicheDetails_txtUsage").text.strip().replace("\n", " ").replace("\r", "") \
                if soup.find("span", id="ctl00_cphContenu_FicheDetails_txtUsage") else "N/A"

            data["Couleur"] = soup.find(
                "span", id="ctl00_cphContenu_FicheDetails_txtCouleur").text.strip().replace("\n", " ").replace("\r", "") \
                if soup.find("span", id="ctl00_cphContenu_FicheDetails_txtCouleur") else "N/A"

            data["Type_Pellicule"] = soup.find(
                "span", id="ctl00_cphContenu_FicheDetails_txtTypePellicule").text.strip().replace("\n", " ").replace("\r", "") \
                if soup.find("span", id="ctl00_cphContenu_FicheDetails_txtTypePellicule") else "N/A"

            # Extraire les dimensions
            dimensions = []
            table = soup.find("table", {
                              "summary": "Dimensions disponibles en milimètres pour ce dispositif suivi du code IMP correspondant."})
            if table:
                for row in table.find_all("tr", class_=["gris", ""])[1:]:
                    cols = row.find_all("td")
                    dimensions.append({
                        "Dimensions_mm": cols[0].text.strip(),
                        "Code_IMP": cols[1].text.strip()
                    })
            data["Dimensions"] = str(dimensions) if dimensions else "N/A"

            # Télécharger l'image
            img_url = soup.find("div", id="Image220Centrer").find("img")["src"]
            img_url = urljoin(BASE_URL, img_url)
            img_response = requests.get(img_url)
            if img_response.status_code == 200:
                img_filename = os.path.join(
                    IMAGE_DIR, f"{data['Numero']}-{data['cid']}.png")
                with open(img_filename, "wb") as f:
                    f.write(img_response.content)

            # Ajouter le CID à cid.csv avec has_image=True
            cid_df = pd.concat([cid_df, pd.DataFrame(
                {"cid": [cid], "has_image": [True]})], ignore_index=True)
            save_cid_data(cid_df)

            data_list.append(data)
            time.sleep(0.25)  # Respecter les serveurs

        except Exception as e:
            print(f"Erreur lors du traitement de CID {cid}: {e}")
            continue

    # Mettre à jour les données existantes
    if data_list:
        updated_signal_data = update_signal_data(
            existing_signal_data, data_list)
        updated_signal_data.to_csv(CSV_FILE, index=False)
        print(f"Les données ont été mises à jour dans {CSV_FILE}")

    # Enregistrer l'exécution dans l'historique
    log_execution(mode)


if __name__ == "__main__":
    # Paramètres modifiables
    CID_START = 13130  # Modifier ici
    CID_END = 13200    # Modifier ici
    MODE = "minimal"   # Options : "full", "minimal", "partial"

    scraper(CID_START, CID_END, mode=MODE)
