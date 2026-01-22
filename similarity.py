import os
import imagehash
from PIL import Image
import json
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
import io

LOGO_DIR = "logos_downloaded"
HAMMING_THRESHOLD = 4

def convert_to_pil(path):
    ext = os.path.splitext(path)[1].lower()
    
    try:
        if ext == '.svg':
            drawing = svg2rlg(path)
            if drawing is None: return None
            mem_file = io.BytesIO()
            renderPM.drawToFile(drawing, mem_file, fmt='PNG')
            mem_file.seek(0)
            img = Image.open(mem_file)
        else:
            img = Image.open(path)

        if img.mode in ("P", "LA") or (img.mode == "P" and "transparency" in img.info):
            img = img.convert("RGBA")
        
        if img.mode == "RGBA":
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            return background
        
        return img.convert("RGB")
        
    except Exception as e:
        return None

def solve_similarity():
    database = {}
    
    print("Procesare și hashing...")
    
    for domain in os.listdir(LOGO_DIR):
        domain_path = os.path.join(LOGO_DIR, domain)
        if not os.path.isdir(domain_path): continue
        
        files = os.listdir(domain_path)
        if not files: continue
        
        logo_file = os.path.join(domain_path, files[0])
        
        img = convert_to_pil(logo_file)
        if img:
            hash_val = imagehash.phash(img)
            database[domain] = hash_val

    groups = []
    processed = set()
    domains = list(database.keys())

    for i in range(len(domains)):
        if domains[i] in processed: continue
        
        current_group = [domains[i]]
        processed.add(domains[i])
        
        for j in range(i + 1, len(domains)):
            if domains[j] in processed: continue
            
            if (database[domains[i]] - database[domains[j]]) <= HAMMING_THRESHOLD:
                current_group.append(domains[j])
                processed.add(domains[j])
        
        groups.append(current_group)

    with open("output_similarity.json", "w") as f:
        json.dump(groups, f, indent=4)
    
    print(f"Finalizat. Grupuri găsite: {len(groups)}")

if __name__ == "__main__":
    solve_similarity()