"""
gerar_icone.py - Converte logo.png para logo.ico com todos os tamanhos
"""
import os, sys

try:
    from PIL import Image

    img = Image.open("logo.png").convert("RGBA")

    # Criar versões em vários tamanhos
    tamanhos = [(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)]
    imgs = []
    for t in tamanhos:
        imgs.append(img.resize(t, Image.LANCZOS))

    # Salvar .ico com todos os tamanhos
    imgs[0].save(
        "logo.ico",
        format="ICO",
        sizes=tamanhos,
        append_images=imgs[1:]
    )
    print("logo.ico gerado com sucesso!")

except Exception as e:
    print(f"Erro ao gerar icone: {e}")
    sys.exit(1)
