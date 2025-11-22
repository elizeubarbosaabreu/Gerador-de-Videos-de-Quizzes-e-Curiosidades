#!/home/elizeu/.local/share/videoenv/bin/python3
"""
app.py - gera um vídeo de quiz vertical (1080x1920)
Lê 'dados.csv' com csv padrão (aspas permitindo vírgulas),
usa Picsum para imagens de fundo, aplica desfoque leve e zoom,
gTTS para áudio, MoviePy para render.
"""

import csv
import os
import tempfile
import requests
from pathlib import Path
from gtts import gTTS
from moviepy.editor import (
    ImageClip,
    TextClip,
    CompositeVideoClip,
    concatenate_videoclips,
    AudioFileClip,
)
from moviepy.video.fx.all import resize
from moviepy.audio.fx.all import audio_loop
from PIL import Image, ImageFilter

# --- CONFIGURAÇÃO ---
W, H = 1080, 1920
FPS = 24

BACKGROUND_BLUR_RADIUS = 4
ZOOM_RATE = 0.015
QUESTION_AUDIO_LANG = "pt"
QUESTION_DURATION_SPEECH_PAD = 0.3
TIMER_SECONDS = 8
ANSWER_SHOW_SECONDS = 4
PAUSE_AFTER_ANSWER = 5
TEXT_COLOR = "white"
TITLE_FONT = "DejaVu-Sans"
TITLE_FONT_SIZE = 82
ALT_FONT_SIZE = 64
TIMER_FONT_SIZE = 120
ANSWER_FONT_SIZE = 82

CSV_FILE = "dados.csv"
OUTPUT_FILE = "quiz_final.mp4"
TIC_TAC_FILE = "tic_tac.mp3"

STROKE_COLOR = "black"
STROKE_WIDTH = 2

# --- HELPERS ---


def baixar_imagem_picsum(width=W, height=H, idx=None, destino="bg.jpg"):
    url = f"https://picsum.photos/{width}/{height}"
    if idx is not None:
        url += f"?random={idx}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    with open(destino, "wb") as f:
        f.write(r.content)
    return destino


def blur_image(in_path, out_path, radius=BACKGROUND_BLUR_RADIUS):
    img = Image.open(in_path).convert("RGB")
    blurred = img.filter(ImageFilter.GaussianBlur(radius=radius))
    blurred.save(out_path)
    return out_path


def gerar_audio_texto(texto, arquivo_mp3, lang=QUESTION_AUDIO_LANG):
    tts = gTTS(text=texto, lang=lang)
    tts.save(arquivo_mp3)
    return arquivo_mp3


def carregar_perguntas_do_csv(caminho_csv):
    perguntas = []
    with open(caminho_csv, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            keys = {k.strip(): v for k, v in row.items()}
            perguntas.append({
                "pergunta": (keys.get("Pergunta") or keys.get("pergunta") or "").strip(),
                "a": (keys.get("a)") or keys.get("a") or "").strip(),
                "b": (keys.get("b)") or keys.get("b") or "").strip(),
                "c": (keys.get("c)") or keys.get("c") or "").strip(),
                "d": (keys.get("d)") or keys.get("d") or "").strip(),
                "correta": (keys.get("correta") or keys.get("Correta") or "").strip(),
            })
    return perguntas


def criar_clip_fundo(img_path, dur, zoom_rate=ZOOM_RATE):
    clip = ImageClip(img_path, duration=dur)

    def zoom(t):
        return 1 + zoom_rate * t

    clip = clip.resize(zoom)
    clip = clip.set_fps(FPS)
    return clip.set_duration(dur)


# -------------------------------------------------------------------------
# FUNÇÃO PRINCIPAL DE CRIAÇÃO DE CLIP PARA CADA PERGUNTA
# -------------------------------------------------------------------------

def criar_clipe_pergunta(pergunta_dict, index, tmpdir: Path):
    perg_text = pergunta_dict["pergunta"]
    alt_a = f"a) {pergunta_dict['a']}"
    alt_b = f"b) {pergunta_dict['b']}"
    alt_c = f"c) {pergunta_dict['c']}"
    alt_d = f"d) {pergunta_dict['d']}"
    resposta_text = pergunta_dict["correta"]

    # --- AUDIO ---
    pergunta_audio_path = tmpdir / f"q_{index}_pergunta.mp3"
    texto_para_falar = (
        f"Pergunta: {perg_text}. "
        f"Alternativas: {alt_a}, {alt_b}, {alt_c}, {alt_d}."
    )
    gerar_audio_texto(texto_para_falar, str(pergunta_audio_path))

    # fundo
    raw_bg = tmpdir / f"q_{index}_raw.jpg"
    bg_blurred = tmpdir / f"q_{index}_blur.jpg"
    baixar_imagem_picsum(W, H, idx=index, destino=str(raw_bg))
    blur_image(str(raw_bg), str(bg_blurred))

    fala = AudioFileClip(str(pergunta_audio_path))
    fala_duration = fala.duration + QUESTION_DURATION_SPEECH_PAD
    bloco_timer = TIMER_SECONDS
    bloco_answer = ANSWER_SHOW_SECONDS
    bloco_pause = PAUSE_AFTER_ANSWER

    dur_total = fala_duration + bloco_timer + bloco_answer + bloco_pause

    fundo = criar_clip_fundo(str(bg_blurred), dur=dur_total)

    # --- TEXTOS COM CONTORNO ---
    pergunta_clip = TextClip(
        perg_text,
        fontsize=TITLE_FONT_SIZE,
        font=TITLE_FONT,
        color=TEXT_COLOR,
        stroke_color=STROKE_COLOR,
        stroke_width=STROKE_WIDTH,
        method="caption",
        size=(W - 160, None),
    ).set_position(("center", 140)).set_duration(dur_total)

    alternativas_clip = TextClip(
        f"{alt_a}\n{alt_b}\n{alt_c}\n{alt_d}",
        fontsize=ALT_FONT_SIZE,
        font=TITLE_FONT,
        color=TEXT_COLOR,
        stroke_color=STROKE_COLOR,
        stroke_width=STROKE_WIDTH,
        method="caption",
        size=(W - 160, None),
    ).set_position(("center", 420)).set_duration(dur_total)

    # --- TIMER ---
    timer_clips = []
    for i in range(TIMER_SECONDS, 0, -1):
        tclip = TextClip(
            str(i),
            fontsize=TIMER_FONT_SIZE,
            font=TITLE_FONT,
            color=TEXT_COLOR,
            stroke_color=STROKE_COLOR,
            stroke_width=STROKE_WIDTH,
            method="label",
        ).set_position(("center", H - 300)).set_duration(1)
        timer_clips.append(tclip)

    timer_visual = concatenate_videoclips(timer_clips).set_start(fala_duration)

    # --- RESPOSTA ---
    resposta_start = fala_duration + bloco_timer
    resposta_clip = TextClip(
        f"Resposta: {resposta_text}",
        fontsize=ANSWER_FONT_SIZE,
        font=TITLE_FONT,
        color=TEXT_COLOR,
        stroke_color=STROKE_COLOR,
        stroke_width=STROKE_WIDTH,
        method="caption",
        size=(W - 160, None),
    ).set_position(("center", 1000)).set_duration(bloco_answer + bloco_pause).set_start(resposta_start)

    # --- LOGOTIPOS NO RODAPÉ ---
    logo_size = 150
    logo_spacing = 60
    margin_bottom = 40

    logo1_path = "logo1.png"
    logo2_path = "logo2.png"

    logo1 = None
    logo2 = None

    if os.path.exists(logo1_path) and os.path.exists(logo2_path):
        logo1 = ImageClip(logo1_path).resize((logo_size, logo_size)).set_duration(dur_total)
        logo2 = ImageClip(logo2_path).resize((logo_size, logo_size)).set_duration(dur_total)

        total_width = logo_size * 2 + logo_spacing
        x_base = (W - total_width) // 2

        logo1 = logo1.set_position((x_base, H - logo_size - margin_bottom))
        logo2 = logo2.set_position((x_base + logo_size + logo_spacing, H - logo_size - margin_bottom))

    # --- AUDIO COMPÓSITO ---
    resposta_audio_path = tmpdir / f"q_{index}_resposta.mp3"
    gerar_audio_texto(f"A resposta correta é: {resposta_text}", str(resposta_audio_path))

    audio_pergunta = AudioFileClip(str(pergunta_audio_path)).set_start(0)
    audio_resposta = AudioFileClip(str(resposta_audio_path)).set_start(resposta_start)

    from moviepy.audio.AudioClip import CompositeAudioClip
    audio_clips = [audio_pergunta, audio_resposta]

    # tic tac
    if os.path.exists(TIC_TAC_FILE):
        try:
            tic = AudioFileClip(TIC_TAC_FILE)
            if tic.duration < TIMER_SECONDS:
                tic = audio_loop(tic, duration=TIMER_SECONDS)
            tic = tic.set_start(fala_duration).set_duration(TIMER_SECONDS).volumex(0.6)
            audio_clips.append(tic)
        except Exception as e:
            print("Aviso tic_tac:", e)

    composite_audio = CompositeAudioClip(audio_clips)

    # --- LAYERS ---
    layers = [fundo, pergunta_clip, alternativas_clip, timer_visual, resposta_clip]

    if logo1:
        layers.append(logo1)
    if logo2:
        layers.append(logo2)

    comp = CompositeVideoClip(layers, size=(W, H)).set_duration(dur_total)
    comp = comp.set_audio(composite_audio)

    return comp


# -------------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------------

def main():
    if not os.path.exists(CSV_FILE):
        print(f"Arquivo {CSV_FILE} não encontrado.")
        return

    perguntas = carregar_perguntas_do_csv(CSV_FILE)
    if not perguntas:
        print("Nenhuma pergunta encontrada.")
        return

    clips = []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        for idx, p in enumerate(perguntas, start=1):
            print(f"Processando pergunta {idx}/{len(perguntas)}...")
            try:
                bloco = criar_clipe_pergunta(p, idx, tmp)
                clips.append(bloco)
            except Exception as e:
                print(f"Erro pergunta {idx}: {e}")

        if not clips:
            print("Nenhum clipe gerado.")
            return

        final = concatenate_videoclips(clips, method="compose")

        print("Renderizando vídeo final...")
        final.write_videofile(
            OUTPUT_FILE,
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
            threads=4,
            preset="medium",
            temp_audiofile="temp-audio.m4a",
            remove_temp=True,
            ffmpeg_params=["-crf", "18"],
        )
        print("Pronto:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
