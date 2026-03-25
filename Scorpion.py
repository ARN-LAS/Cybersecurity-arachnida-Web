import os
import sys
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
from PIL import Image, ExifTags, PngImagePlugin
import piexif

SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".bmp")

# --------------------------------------------
# Fonctions métadonnées
# --------------------------------------------
def is_valid_image(path):
    try:
        img = Image.open(path)
        img.verify()
        return True
    except Exception:
        return False

def get_exif_data(image_path):
    """Récupère les métadonnées EXIF ou équivalent."""
    try:
        ext = os.path.splitext(image_path)[1].lower()
        img = Image.open(image_path)
        data = {}

        if ext in [".jpg", ".jpeg"]:
            info = img._getexif() if hasattr(img, "_getexif") else None
            if info:
                for tag, value in info.items():
                    decoded = ExifTags.TAGS.get(tag, tag)
                    data[decoded] = value

        elif ext == ".png":
            data.update(img.info)

        elif ext == ".gif":
            comment = img.info.get("comment", b"")
            if comment:
                data["Commentaire"] = comment.decode(errors="ignore")

        return data
    except Exception as e:
        print(f"Erreur lecture métadonnées pour {image_path}: {e}")
        return {}

def save_modified_exif(image_path, modified_data):
    """Sauvegarde EXIF pour JPEG et métadonnées texte pour PNG/GIF."""
    try:
        ext = os.path.splitext(image_path)[1].lower()

        if ext in [".jpg", ".jpeg"]:
            try:
                exif_dict = piexif.load(image_path)
            except Exception:
                exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}, "thumbnail": None}

            # Stockage sécurisé : tout dans ImageDescription pour compatibilité
            for tag_name, value in modified_data.items():
                if tag_name == "ImageDescription":
                    exif_dict["0th"][piexif.ImageIFD.ImageDescription] = str(value).encode("utf-8")

            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, image_path)

        elif ext == ".png":
            with Image.open(image_path) as img:
                meta = PngImagePlugin.PngInfo()
                for k, v in modified_data.items():
                    meta.add_text(k, str(v))
                img.save(image_path, pnginfo=meta)

        elif ext == ".gif":
            with Image.open(image_path) as img:
                comment = modified_data.get("Commentaire", "")
                img.info["comment"] = comment.encode()
                img.save(image_path)

        else:
            print(f"Format non supporté pour sauvegarde: {image_path}")

    except Exception as e:
        print(f"Erreur sauvegarde métadonnées pour {image_path}: {e}")

def delete_metadata(image_path):
    """Supprime les métadonnées pour tous les formats pris en charge."""
    try:
        ext = os.path.splitext(image_path)[1].lower()
        img = Image.open(image_path)

        if ext in [".jpg", ".jpeg"]:
            data = list(img.getdata())
            img_no_exif = Image.new(img.mode, img.size)
            img_no_exif.putdata(data)
            img_no_exif.save(image_path)
        elif ext == ".png" or ext == ".gif":
            img.save(image_path)  # supprime infos PNG/GIF
        print(f"Métadonnées supprimées: {image_path}")
    except Exception as e:
        print(f"Erreur suppression métadonnées pour {image_path}: {e}")

# --------------------------------------------
# GUI
# --------------------------------------------
class ScorpionGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Scorpion Metadata Manager")
        self.images = []
        self.current_image = None

        # Boutons
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Ouvrir Images", command=self.load_images).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Supprimer Metadata", command=self.delete_metadata_gui).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="Modifier Metadata", command=self.modify_metadata).grid(row=0, column=2, padx=5)

        # Liste images
        self.tree_images = ttk.Treeview(root, columns=("file",), show="headings", selectmode="browse")
        self.tree_images.heading("file", text="Fichier")
        self.tree_images.pack(fill="x", padx=5, pady=5)
        self.tree_images.bind("<<TreeviewSelect>>", self.on_image_select)

        # Tableau EXIF
        self.tree_exif = ttk.Treeview(root, columns=("tag", "value"), show="headings")
        self.tree_exif.heading("tag", text="Tag")
        self.tree_exif.heading("value", text="Valeur")
        self.tree_exif.pack(fill="both", expand=True, padx=5, pady=5)

        # Gestion fermeture
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_images(self):
        files = filedialog.askopenfilenames(filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.gif")])
        self.images.clear()
        for i in self.tree_images.get_children():
            self.tree_images.delete(i)
        for f in files:
            if f.lower().endswith(SUPPORTED_EXTENSIONS) and is_valid_image(f):
                self.images.append(f)
                self.tree_images.insert("", "end", values=(os.path.basename(f),))

    def on_image_select(self, event):
        sel = self.tree_images.selection()
        if not sel:
            return
        idx = self.tree_images.index(sel[0])
        self.current_image = self.images[idx]
        self.show_exif(self.current_image)

    def show_exif(self, image_path):
        for i in self.tree_exif.get_children():
            self.tree_exif.delete(i)
        exif = get_exif_data(image_path)
        if not exif:
            self.tree_exif.insert("", "end", values=("Aucune métadonnée trouvée", ""))
            return
        for k, v in exif.items():
            self.tree_exif.insert("", "end", values=(k, v))

    def delete_metadata_gui(self):
        if not self.current_image:
            messagebox.showwarning("Attention", "Sélectionnez une image")
            return
        delete_metadata(self.current_image)
        self.show_exif(self.current_image)

    def modify_metadata(self):
        if not self.current_image:
            messagebox.showwarning("Attention", "Sélectionnez une image")
            return
        exif = get_exif_data(self.current_image)

        top = tk.Toplevel(self.root)
        top.title("Modifier Metadata")
        tree_mod = ttk.Treeview(top, columns=("tag", "value"), show="headings")
        tree_mod.heading("tag", text="Tag")
        tree_mod.heading("value", text="Valeur")
        tree_mod.pack(fill="both", expand=True, padx=5, pady=5)

        if not exif:
            tree_mod.insert("", "end", values=("ImageDescription", ""))
        else:
            for k, v in exif.items():
                tree_mod.insert("", "end", values=(k, v))

        def edit_selected():
            sel = tree_mod.selection()
            if not sel: return
            for s in sel:
                tag, val = tree_mod.item(s)["values"]
                new_val = simpledialog.askstring("Modifier valeur", f"{tag}:", initialvalue=val)
                if new_val is not None:
                    tree_mod.item(s, values=(tag, new_val))

        def add_new_tag():
            tag = simpledialog.askstring("Nouveau Tag", "Nom du tag:")
            if tag:
                tree_mod.insert("", "end", values=(tag, ""))

        def save_changes():
            modified = {tree_mod.item(i)["values"][0]: tree_mod.item(i)["values"][1] for i in tree_mod.get_children()}
            save_modified_exif(self.current_image, modified)
            self.show_exif(self.current_image)
            top.destroy()

        btn_frame = tk.Frame(top)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Modifier Sélection", command=edit_selected).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Ajouter Tag", command=add_new_tag).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Sauvegarder", command=save_changes).pack(side="left", padx=5)

    def on_close(self):
        self.root.destroy()
        sys.exit(0)

# --------------------------------------------
# Entrée principale
# --------------------------------------------
def main():
    root = tk.Tk()
    app = ScorpionGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
