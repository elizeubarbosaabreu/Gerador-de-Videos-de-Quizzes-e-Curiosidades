#!/home/elizeu/.local/share/videoenv/bin/python3

# app.py - gera vídeo vertical 1080x1920 com áudio gTTS (sem legendas)
# Adaptado para: estilo imagem central + fundo borrado, sem legendas.

import os
import sys
import time
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional

import requests
from gtts import gTTS
from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    CompositeVideoClip,
    concatenate_videoclips,
)
from pydub import AudioSegment
from PIL import Image, ImageFilter

# ---------------- CONFIGURAÇÃO ----------------
PEXELS_API_KEY = "sua chave"
FPS = 24
OUT_WIDTH = 1080
OUT_HEIGHT = 1920
CENTER_IMG_MAX_WIDTH = 900  # largura máxima da imagem central
ZOOM_FACTOR = 1.5 # zoom leve durante cada clipe
TEMP_DIR = Path("temp_assets")
TEMP_DIR.mkdir(exist_ok=True)


# ---------------- UTILITÁRIOS ----------------
def gerar_texto_ollama(assunto: str):
    """Gera o texto com Ollama (igual ao seu fluxo atual)."""
    cmd = (
        f"ollama run gemma3:1b 'Primeiramente diga o que é {assunto}. "
        f"Depois cite 5 fatos curiosos sobre {assunto}. Retorne apenas a resposta pura em formato de texto - não quero marcadores, pronto para ser exibido em uma api. "
        f"No último parágrafo escreva: Inscreva-se e ative o sininho para sempre receber curiosidades e fatos relevantes sobre tudo. E não esqueça daquele like maroto!' > texto.txt"
    )
    print("Gerando texto com Ollama...")
    os.system(cmd)
    print(f"Arquivo de texto gerado: texto.txt")


def gerar_audio_gtts(texto: str, arquivo_mp3: str):
    print("Gerando áudio com gTTS...")
    tts = gTTS(text=texto, lang="pt-br")
    tts.save(arquivo_mp3)
    print(f"Áudio salvo: {arquivo_mp3}")
    return arquivo_mp3


def buscar_imagens_picsum(total: int = 10, salvar_pasta: str = "imagens"):
    """
    Baixa imagens verticais 1080x1920 do Lorem Picsum (sempre funcionam).
    Não depende de API key e não dá erro 503.
    """
    import random

    os.makedirs(salvar_pasta, exist_ok=True)
    imagens_baixadas = []

    print(f"🖼️ Baixando {total} imagens 1080x1920 do Lorem Picsum...")

    for i in range(1, total + 1):
        # Cada chamada com um seed gera uma imagem diferente
        seed = random.randint(1, 999999)
        url = f"https://picsum.photos/seed/{seed}/1080/1920"
        destino = os.path.join(salvar_pasta, f"img_{i}.jpg")

        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                with open(destino, "wb") as f:
                    f.write(r.content)
                imagens_baixadas.append(destino)
                print(f"Imagem salva: {destino}")
            else:
                print(f"Erro ao baixar imagem {i}: status {r.status_code}")
        except Exception as e:
            print(f"Falha ao baixar imagem {i}: {e}")

    return imagens_baixadas

def buscar_imagens_pexels_vertical(query: str, total: int = 10, salvar_pasta: str = "imagens",
                                   retries: int = 5, delay: int = 3):
    """
    Baixa imagens verticais do Pexels relacionadas ao tema.
    Filtra imagens preferencialmente verticais.
    Mantém nomes img_1, img_2, ... para compatibilidade com o fluxo atual.
    """

    os.makedirs(salvar_pasta, exist_ok=True)

    url = f"https://api.pexels.com/v1/search?query={query}&per_page=80"
    headers = {"Authorization": PEXELS_API_KEY}

    print(f"🔍 Buscando imagens relacionadas a '{query}' no Pexels...")

    fotos = None

    # Tentativas para buscar os resultados da API
    for i in range(retries):
        try:
            r = requests.get(url, headers=headers, timeout=20)
            if r.status_code == 200:
                fotos = r.json().get("photos", [])
                break
            else:
                print(f"Tentativa {i+1}/{retries} falhou ({r.status_code}). Retentando...")
        except Exception as e:
            print(f"Erro ao buscar imagens ({e}). Tentando novamente...")

        time.sleep(delay)

    if not fotos:
        print("❌ Nenhuma imagem encontrada no Pexels.")
        return []

    # Filtra imagens verticais (altura maior que largura)
    imagens_verticais = [
        f for f in fotos if f["height"] > f["width"]
    ]

    # Se não houver verticais, usa todas mesmo assim
    selecionadas = imagens_verticais if imagens_verticais else fotos
    selecionadas = selecionadas[:total]

    imagens_salvas = []

    print(f"📥 Baixando {len(selecionadas)} imagens verticais do Pexels...")

    for idx, photo in enumerate(selecionadas, start=1):
        # Melhor tamanho disponível
        img_url = photo["src"].get("large2x") or photo["src"].get("large") or photo["src"]["original"]

        destino = os.path.join(salvar_pasta, f"img_{idx}.jpg")

        try:
            r_img = requests.get(img_url, timeout=20)
            if r_img.status_code == 200:
                with open(destino, "wb") as f:
                    f.write(r_img.content)
                imagens_salvas.append(destino)
                print(f"✔ Imagem salva: {destino}")
            else:
                print(f"⚠ Erro ao baixar imagem {idx}: status {r_img.status_code}")

        except Exception as e:
            print(f"⚠ Falha ao baixar imagem {idx}: {e}")

    return imagens_salvas



def create_vertical_clip_for_image(
    image_path: str,
    dur: float,
    zoom_factor: float = ZOOM_FACTOR,
):
    """
    Cria um clipe vertical 1080x1920 SEM fundo borrado.
    A imagem é redimensionada para preencher a tela vertical.
    """
    img = Image.open(image_path)
    w, h = img.size
    img_ratio = w / h
    target_ratio = OUT_WIDTH / OUT_HEIGHT

    # Ajuste mantendo proporção
    if img_ratio > target_ratio:
        # imagem mais larga → ajusta pela altura
        new_h = OUT_HEIGHT
        new_w = int(new_h * img_ratio)
    else:
        # imagem mais alta → ajusta pela largura
        new_w = OUT_WIDTH
        new_h = int(new_w / img_ratio)

    # Cria o clip ajustado
    clip = (
        ImageClip(image_path)
        .set_duration(dur)
        .resize((new_w, new_h))
        .set_position(("center", "center"))
    )

    # Aplicar zoom suave (Ken Burns)
    start = 1.0
    end = zoom_factor
    clip = clip.resize(lambda t: 1 + (end - 1) * (t / dur))

    return clip.crop(
        x_center=new_w // 2,
        y_center=new_h // 2,
        width=OUT_WIDTH,
        height=OUT_HEIGHT
    )



def criar_video_com_zoom_sem_legenda(
    imagens: List[str],
    arquivo_audio: str,
    arquivo_saida: str = "video_final_vertical.mp4",
):
    """
    Cria o vídeo vertical concatenando clipes com ZOOM + FADE entre imagens,
    sincronizando com o áudio final.
    """

    if not imagens:
        print("Nenhuma imagem fornecida.")
        return

    audio = AudioFileClip(arquivo_audio)
    duracao_total = audio.duration
    dur_por_img = duracao_total / len(imagens)

    FADE_DUR = 1.5  # duração da transição fade in/out

    print("Criando clipes com zoom e fade entre imagens...")
    clips = []

    for img in imagens:
        clip = create_vertical_clip_for_image(img, dur_por_img)

        # aplica fade in/out em cada imagem
        clip = clip.fadein(FADE_DUR).fadeout(FADE_DUR)
        clips.append(clip)

    # concatenar com transição suave via padding negativo
    video = concatenate_videoclips(
        clips,
        method="compose",
        padding=-FADE_DUR  # sobreposição para transição
    ).set_audio(audio)

    video = video.set_fps(FPS)

    final = video.set_duration(duracao_total)

    print("Renderizando vídeo final com transições...")
    final.write_videofile(
        arquivo_saida,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="medium"
    )

    print("Vídeo final salvo em:", arquivo_saida)



# ---------------- PRINCIPAL ----------------
def main():
    assunto = input("Assunto: ").strip()
    if not assunto:
        print("Forneça um assunto.")
        return

    # 1) gerar texto com ollama (mesma lógica original)
    gerar_texto_ollama(assunto)

    with open("texto.txt", "r", encoding="utf-8") as f:
        texto_completo = f.read().strip()

    # 2) gerar audio
    nome_audio = f"{assunto}.mp3"
    gerar_audio_gtts(texto_completo, nome_audio)

  
    # 3) baixar imagens (Pexels → fallback Picsum)
    imagens_baixadas = buscar_imagens_pexels_vertical(query=assunto)

    if not imagens_baixadas:
        print("⚠ Pexels falhou ou não retornou imagens. Usando Picsum...")
        imagens_baixadas = buscar_imagens_picsum(total=10, salvar_pasta="imagens")


    # 4) criar vídeo vertical SEM legendas
    out_vid = f"{assunto}.mp4"
    criar_video_com_zoom_sem_legenda(imagens_baixadas, nome_audio, arquivo_saida=out_vid)
    print("Concluído. Arquivo final:", out_vid)


if __name__ == "__main__":
    main()
