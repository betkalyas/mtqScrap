import os
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin
from tqdm import tqdm

# Configuration
BASE_URL = "https://www.rsr.transports.gouv.qc.ca/Dispositifs/Details.aspx"
BASE_URL_IMG = "https://www.rsr.transports.gouv.qc.ca/Gestionnaires/ObtenirImage.ashx?imgId="
IMAGE_DIR = "images_signaux"
CSV_FILE = "signaux_routiers.csv"

# Créer le dossier pour les images
os.makedirs(IMAGE_DIR, exist_ok=True)


def check_robots_txt():
    """
    Vérifie le fichier robots.txt du site pour connaître les règles de scraping.
    """
    robots_url = "https://www.rsr.transports.gouv.qc.ca/robots.txt"
    response = requests.get(robots_url)
    if response.status_code == 200:
        print("Contenu de robots.txt :")
        print(response.text)
    else:
        print(
            f"Erreur {response.status_code} lors de la récupération de robots.txt")


def load_existing_data():
    """
    Charge les données existantes depuis le fichier CSV.
    Retourne un set des CID déjà traités.
    """
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        return set(df["cid"].unique())
    return set()


def scraper(cid_start, cid_end):
    # Charger les CID déjà traités
    existing_cids = load_existing_data()
    data_list = []

    for cid in tqdm(range(cid_start, cid_end + 1), desc="Scraping pages"):
        # Vérifier si le CID a déjà été traité
        if cid in existing_cids:
            print(f"CID {cid} déjà traité. Passage au suivant.")
            continue

        url = f"{BASE_URL}?cid={cid}"
        response = requests.get(url)

        # Skip si la page retourne une erreur ou est inaccessible
        if response.status_code != 200:
            print(f"Erreur {response.status_code} pour CID {cid}")
            continue

        soup = BeautifulSoup(response.content, 'html.parser')

        # Vérifier l'existence de l'image avant de continuer
        image_container = soup.find("div", id="Image220Centrer")
        if not image_container or not image_container.find("img"):
            print(f"Pas d'image trouvée pour CID {cid}. Passage au suivant.")
            continue

        # Télécharger l'image
        img_url = image_container.find("img")["src"]
        img_url = urljoin(BASE_URL, img_url)
        img_response = requests.get(img_url)
        if img_response.status_code != 200:
            print(
                f"Impossible de télécharger l'image pour CID {cid}. Passage au suivant.")
            continue

        # Initialiser un dictionnaire pour stocker les données
        data = {"cid": cid}

        try:
            # Extraire les données avec vérification de l'existence des champs
            data["Numero"] = soup.find("span", id="ctl00_cphContenu_FicheDetails_txtNumero").text.strip() \
                if soup.find("span", id="ctl00_cphContenu_FicheDetails_txtNumero") else "N/A"

            data["Nom"] = soup.find("span", id="ctl00_cphContenu_FicheDetails_txtNom").text.strip() \
                if soup.find("span", id="ctl00_cphContenu_FicheDetails_txtNom") else "N/A"

            # Gestion des références (Tome V ou VHR)
            reference_tome_v = soup.find(
                "span", id="ctl00_cphContenu_FicheDetails_txtReferenceTomeV")
            reference_vhr = soup.find(
                "span", id="ctl00_cphContenu_FicheDetails_txtReferenceVHR")
            data["Reference_Tome_V"] = reference_tome_v.text.strip(
            ) if reference_tome_v else "N/A"
            data["Reference_VHR"] = reference_vhr.text.strip(
            ) if reference_vhr else "N/A"

            data["Description"] = soup.find("span", id="ctl00_cphContenu_FicheDetails_txtDescription").text.strip() \
                if soup.find("span", id="ctl00_cphContenu_FicheDetails_txtDescription") else "N/A"

            data["Usages"] = soup.find("span", id="ctl00_cphContenu_FicheDetails_txtUsage").text.strip() \
                if soup.find("span", id="ctl00_cphContenu_FicheDetails_txtUsage") else "N/A"

            data["Couleur"] = soup.find("span", id="ctl00_cphContenu_FicheDetails_txtCouleur").text.strip() \
                if soup.find("span", id="ctl00_cphContenu_FicheDetails_txtCouleur") else "N/A"

            data["Type_Pellicule"] = soup.find("span", id="ctl00_cphContenu_FicheDetails_txtTypePellicule").text.strip() \
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

            # Sauvegarder l'image téléchargée
            img_filename = os.path.join(
                IMAGE_DIR, f"{data['Numero']}-{data['cid']}.png")
            with open(img_filename, "wb") as f:
                f.write(img_response.content)

            data_list.append(data)
            time.sleep(0.25)  # Respecter les serveurs

        except Exception as e:
            print(f"Erreur lors du traitement de CID {cid}: {e}")
            continue

    # Ajouter les nouvelles données au fichier CSV existant
    if data_list:
        new_df = pd.DataFrame(data_list)
        if os.path.exists(CSV_FILE):
            existing_df = pd.read_csv(CSV_FILE)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df
        combined_df.to_csv(CSV_FILE, index=False)
        print(f"Les données ont été sauvegardées dans {CSV_FILE}")


if __name__ == "__main__":
    # Vérifier robots.txt avant de scraper
    check_robots_txt()

    # Paramètres modifiables
    CID_START = 13000  # Modifier ici 12392
    CID_END = 13099    # Modifier ici 18392

    scraper(CID_START, CID_END)
