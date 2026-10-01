"""
Script de génération des assets NIBRAS pour Open WebUI.
Génère tous les formats d'icônes, logos, splash screens et favicons
à partir d'un logo source (par défaut: logo Chat nibras.png).
"""

import os
from PIL import Image

def generate_assets(src_path="logo Chat nibras.png", dest_dir="static/static"):
    if not os.path.exists(src_path):
        raise FileNotFoundError(f"Source logo not found at: {src_path}")
    
    os.makedirs(dest_dir, exist_ok=True)
    src = Image.open(src_path).convert("RGBA")

    def make_square_fit(img, size, padding_ratio=0.08):
        target_w, target_h = size
        max_w = int(target_w * (1 - 2 * padding_ratio))
        max_h = int(target_h * (1 - 2 * padding_ratio))
        
        scale = min(max_w / img.width, max_h / img.height)
        new_w = max(1, int(img.width * scale))
        new_h = max(1, int(img.height * scale))
        
        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
        offset_x = (target_w - new_w) // 2
        offset_y = (target_h - new_h) // 2
        canvas.paste(resized, (offset_x, offset_y), resized)
        return canvas

    targets = {
        "logo.png": ((500, 500), 0.08),
        "favicon.png": ((512, 512), 0.05),
        "favicon-96x96.png": ((96, 96), 0.05),
        "apple-touch-icon.png": ((180, 180), 0.08),
        "web-app-manifest-192x192.png": ((192, 192), 0.08),
        "web-app-manifest-512x512.png": ((512, 512), 0.08),
        "splash.png": ((500, 500), 0.1),
        "splash-dark.png": ((500, 500), 0.1),
    }

    for filename, (dim, padding) in targets.items():
        out_img = make_square_fit(src, dim, padding)
        out_path = os.path.join(dest_dir, filename)
        out_img.save(out_path)
        print(f"Generated: {out_path} ({dim[0]}x{dim[1]})")

    # Favicon ICO multi-resolution
    ico_img = make_square_fit(src, (256, 256), 0.05)
    ico_path = os.path.join(dest_dir, "favicon.ico")
    ico_img.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    print(f"Generated: {ico_path} (multi-size ICO)")

if __name__ == "__main__":
    generate_assets()
