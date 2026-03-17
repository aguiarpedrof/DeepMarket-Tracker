import cv2
import os
import glob

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES — ajuste aqui
# ══════════════════════════════════════════════════════════════════════════════

PASTA_VIDEOS = "Videos"
PASTA_SAIDA  = "frames_dataset"

# Extrair 1 frame a cada N segundos
# Vídeos de 3h com 10s → ~1.080 frames por vídeo (bom para anotar)
SEGUNDOS_POR_FRAME = 10

# ══════════════════════════════════════════════════════════════════════════════

def formatar_tempo(seg):
    h = int(seg // 3600)
    m = int((seg % 3600) // 60)
    s = int(seg % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def extrair_frames(caminho_video, pasta_saida, segundos_por_frame):
    cap = cv2.VideoCapture(caminho_video)
    if not cap.isOpened():
        print(f"  ❌ Não foi possível abrir: {caminho_video}")
        return 0

    fps          = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duracao_seg  = total_frames / fps if fps > 0 else 0
    estimativa   = int(duracao_seg / segundos_por_frame)

    nome_video = os.path.splitext(os.path.basename(caminho_video))[0]
    print(f"\n  📹 {nome_video}")
    print(f"     Duração: {formatar_tempo(duracao_seg)} | FPS: {fps:.1f}")
    print(f"     Intervalo: 1 frame a cada {segundos_por_frame}s → ~{estimativa} frames")

    contador     = 0
    t_atual_seg  = 0.0
    ultimo_pct   = -1

    while t_atual_seg <= duracao_seg:
        # ── Seek direto ao timestamp — não carrega frames intermediários ──
        cap.set(cv2.CAP_PROP_POS_MSEC, t_atual_seg * 1000)
        ret, frame = cap.read()

        if not ret:
            break

        nome_arquivo  = f"{nome_video}_{int(t_atual_seg):06d}s.jpg"
        caminho_saida = os.path.join(pasta_saida, nome_arquivo)
        cv2.imwrite(caminho_saida, frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
        contador += 1

        # Progresso a cada 5%
        if duracao_seg > 0:
            pct = int((t_atual_seg / duracao_seg) * 100)
            if pct % 5 == 0 and pct != ultimo_pct:
                barra = "█" * (pct // 5) + "░" * (20 - pct // 5)
                print(f"     [{barra}] {pct:3d}% | {contador} frames", end="\r")
                ultimo_pct = pct

        t_atual_seg += segundos_por_frame

    cap.release()
    print(f"     {'█' * 20}  100% | ✅ {contador} frames extraídos            ")
    return contador


if __name__ == "__main__":
    os.makedirs(PASTA_SAIDA, exist_ok=True)

    extensoes = ["*.mp4", "*.avi", "*.mov", "*.mkv",
                 "*.MP4", "*.AVI", "*.MOV", "*.MKV"]
    videos = []
    for ext in extensoes:
        videos.extend(glob.glob(os.path.join(PASTA_VIDEOS, ext)))

    if not videos:
        print(f"❌ Nenhum vídeo encontrado em '{PASTA_VIDEOS}'")
        print(f"   Coloque seus vídeos na pasta '{PASTA_VIDEOS}' e rode novamente.")
    else:
        print(f"🔍 {len(videos)} vídeo(s) encontrado(s)")
        print(f"📁 Frames serão salvos em: '{PASTA_SAIDA}'")
        print(f"⏱️  Intervalo: 1 frame a cada {SEGUNDOS_POR_FRAME}s")

        total_geral = 0
        for video in sorted(videos):
            total_geral += extrair_frames(video, PASTA_SAIDA, SEGUNDOS_POR_FRAME)

        print(f"\n{'='*52}")
        print(f"✅ Extração concluída! Total: {total_geral} frames")
        print(f"   Pasta: {os.path.abspath(PASTA_SAIDA)}")
        print(f"\n📌 Próximos passos:")
        print(f"   1. Acesse https://roboflow.com → seu projeto")
        print(f"   2. Upload das imagens de '{PASTA_SAIDA}'")
        print(f"   3. Anote as pessoas (bounding boxes)")
        print(f"   4. Exporte em formato YOLOv8")
        print(f"   5. python treinar_yolov8.py")
