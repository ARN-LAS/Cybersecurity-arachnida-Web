from urllib.parse import urljoin
from bs4 import BeautifulSoup
import requests
import sys
import os

def html_parser(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        print("Erreur lors de la requête :", e)
        return None
    return BeautifulSoup(response.text, "html.parser")

def extract_img(soup):
    return [img_tag["src"] for img_tag in soup.find_all("img", src=True)]

def download_images(images, base_url, folder="images", limit=None):
    allowed_ext = (".jpg", ".jpeg", ".png", ".gif", ".bmp")
    if not os.path.exists(folder):
        os.makedirs(folder)

    count = 0
    idx = 1

    for img_url in images:
        if limit is not None and count >= limit:
            break

        full_url = img_url if img_url.startswith("http") else urljoin(base_url, img_url)
        filename = os.path.basename(img_url.split("?")[0].split("#")[0])
        ext = os.path.splitext(filename)[1].lower()

        if ext not in allowed_ext:
            continue

        if not filename:
            filename = f"image_{idx}{ext if ext else '.jpg'}"
        else:
            filename = f"{idx}_{filename}"

        path = os.path.join(folder, filename)

        try:
            response = requests.get(full_url, stream=True)
            response.raise_for_status()
            with open(path, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print(f"Téléchargé: {path}")
            count += 1
            idx += 1
        except requests.RequestException:
            # On ignore les erreurs de téléchargement et on ne compte pas l'image
            continue

def main():
    folder = "images"
    flags = {}
    url = None
    i = 1

    # Analyse des arguments
    while i < len(sys.argv):
        param = sys.argv[i]

        if param.startswith("-"):
            for char in param[1:]:
                if char == "r":
                    flags["r"] = True
                elif char == "l":
                    if i + 1 < len(sys.argv) and sys.argv[i + 1].isdigit():
                        flags["l"] = int(sys.argv[i + 1])
                        i += 1
                    else:
                        print("Erreur : -l doit être suivi d'un nombre")
                        return
                elif char == "p":
                    if i + 1 < len(sys.argv):
                        folder = sys.argv[i + 1]
                        i += 1
                    else:
                        print("Erreur : -p doit être suivi d'un chemin")
                        return
                else:
                    print(f"Option inconnue : -{char}")
        elif param.startswith("http://") or param.startswith("https://"):
            url = param
        else:
            print(f"Argument inconnu ignoré : {param}")
        i += 1

    if url is None:
        print("Erreur : URL obligatoire")
        return

    soup = html_parser(url)
    if soup is None:
        return

    images = extract_img(soup)

    limit = flags.get("l") if "l" in flags else None

    if "r" in flags or "l" in flags:
        download_images(images, base_url=url, folder=folder, limit=limit)

if __name__ == "__main__":
    main()
