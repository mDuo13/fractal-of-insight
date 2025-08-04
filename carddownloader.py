#!/usr/bin/env python

from os import makedirs
import os.path
from time import sleep
import requests
from datalayer import carddata

## Saves every card image to this dir
CARD_IMG_DIR = "data/cardimages/"
# makedirs(CARD_IMG_DIR, exist_ok=True)

def save_img_from_url(url, save_to):
    print(f"Downloading: {url}")
    resp = requests.get(url)
    if resp.status_code == 200:
        #print(f"Saving to {save_to}")
        folder, file = os.path.split(save_to)
        makedirs(folder, exist_ok=True)
        with open(save_to, "wb") as f:
            f.write(resp.content)
    else:
        print(f"Downloading failed with status code {resp.status_code}")
    sleep(0.25)

for cardname, card in carddata.items():
    for ced in carddata[cardname]["result_editions"]:
        out_path = os.path.join(CARD_IMG_DIR, ced["set"]["prefix"], ced["slug"]+".jpg")
        if os.path.exists(out_path):
            print(f"Skipping already-downloaded file: {out_path}")
        else:
            img_url = f"https://api.gatcg.com{ced['image']}"
            save_img_from_url(img_url, out_path)

        if ced.get("other_orientations"):
            for oo in ced.get("other_orientations"):
                ooed = oo["edition"]
                out_path = os.path.join(CARD_IMG_DIR, ooed["set"]["prefix"], ooed["slug"]+".jpg")
                if os.path.exists(out_path):
                    #print(f"Skipping already-downloaded file: {out_path}")
                    pass
                else:
                    img_url = f"https://api.gatcg.com{ooed['image']}"
                    save_img_from_url(img_url, out_path)
        
        for circ in ced.get("circulations", []):
            if circ.get("variants", []):
                for variant in circ["variants"]:
                    card_fname = os.path.basename(variant["image"])
                    out_path = os.path.join(CARD_IMG_DIR, ced["set"]["prefix"], card_fname)
                    if os.path.exists(out_path):
                        #print(f"Skipping already-downloaded file: {out_path}")
                        pass
                    else:
                        img_url = f"https://api.gatcg.com{variant['image']}"
                        save_img_from_url(img_url, out_path)
        
