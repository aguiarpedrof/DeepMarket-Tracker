import cv2
import os
import glob
import time

# ═══════════════════════════════════════════════════
# CONFIGURACOES
# ═══════════════════════════════════════════════════
PASTA_VIDEOS       = "Videos"
PASTA_SAIDA        = "novos_frames5"
SEGUNDOS_POR_FRAME = 5    # 1 frame a cada N segundos
# ═══════════════════════════════════════════════════


def formatar_tempo(seg):
    seg = max(0, float(seg))
    h = int(seg // 3600)
    m = int((seg % 3600) // 60)
    s = int(seg % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def extrair_frames(caminho_video, pasta_saida, segundos_por_frame):
    cap = cv2.VideoCapture(caminho_video)
    if not cap.isOpened():
        print(f"  Nao foi possivel abrir: {caminho_video}")
        return 0

    fps          = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duracao_seg  = float(total_frames) / fps if total_frames > 0 else 0.0

    # Fallback para MKV/OBS onde FRAME_COUNT vem corrompido
    if duracao_seg <= 0:
        cap.set(cv2.CAP_PROP_POS_AVI_RATIO, 1)
        duracao_ms  = cap.get(cv2.CAP_PROP_POS_MSEC)
        duracao_seg = float(duracao_ms) / 1000.0 if duracao_ms > 0 else 0.0
        cap.set(cv2.CAP_PROP_POS_MSEC, 0)

    # Intervalo em numero de frames
    intervalo  = max(1, int(fps * segundos_por_frame))
    estimativa = int(duracao_seg / segundos_por_frame) if duracao_seg > 0 else "?"

    nome_video = os.path.splitext(os.path.basename(caminho_video))[0]
    print(f"\n  {nome_video}")
    print(f"     Duracao: {formatar_tempo(duracao_seg)} | FPS: {fps:.1f}")
    print(f"     Intervalo: 1 frame a cada {segundos_por_frame}s -> ~{estimativa} frames")

    contador    = 0
    frame_idx   = 0
    ultimo_pct  = -1

    # Testa se o video e legivel antes de entrar no loop
    ret_teste, _ = cap.read()
    if not ret_teste:
        cap.release()
        print(f"     AVISO: video nao pode ser lido (container corrompido). Pulando.")
        return 0
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # volta ao inicio

    # Leitura frame a frame — funciona com qualquer formato (MKV, MP4, AVI...)
    start_time_read = time.time()
    
    while True:
        try:
            ret, frame = cap.read()
        except cv2.error as e:
            print("Erro de leitura do cv2. Fim do arquivo antecipado.")
            break
            
        if not ret:
            break
            
        # timeout preventivo    
        if time.time() - start_time_read > 300: # 5 minutos lendo um unico video 
             print("Aviso: Tempo excedido. Verifique corrupsao no container MKV.")
             break

        if frame_idx % intervalo == 0:
            t_seg         = float(frame_idx) / fps
            nome_arquivo  = f"{nome_video}_{int(t_seg):06d}s.jpg"
            caminho_saida = os.path.join(pasta_saida, nome_arquivo)
            cv2.imwrite(caminho_saida, frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            contador += 1
            start_time_read = time.time() # Reseta timer de leitura.
            
            if duracao_seg > 0:
                pct = min(int((t_seg / duracao_seg) * 100), 99)
                if pct % 5 == 0 and pct != ultimo_pct:
                    barra = "=" * (pct // 5) + "-" * (20 - pct // 5)
                    print(f"     [{barra}] {pct:3d}% | {contador} frames", end="\r")
                    ultimo_pct = pct

        frame_idx += 1

    cap.release()
    print(f"     {'=' * 20}  100% | {contador} frames extraidos            ")
    return contador


if __name__ == "__main__":
    os.makedirs(PASTA_SAIDA, exist_ok=True)

    extensoes = ["*.mp4", "*.avi", "*.mov", "*.mkv"]
    videos_set = set()
    for ext in extensoes:
       # glob acha duplicado no windows se colocar *.MP4 e *.mp4
       for path in glob.glob(os.path.join(PASTA_VIDEOS, ext)):
             videos_set.add(path)
       for path in glob.glob(os.path.join(PASTA_VIDEOS, ext.upper())):
             videos_set.add(path)

    videos = list(videos_set)

    if not videos:
        print(f"Nenhum video encontrado em '{PASTA_VIDEOS}'")
    else:
        print(f"{len(videos)} video(s) encontrado(s)")
        print(f"Frames serao salvos em: '{PASTA_SAIDA}'")
        print(f"Intervalo: 1 frame a cada {SEGUNDOS_POR_FRAME}s")

        total_geral = 0
        for video in sorted(videos):
            total_geral += extrair_frames(video, PASTA_SAIDA, SEGUNDOS_POR_FRAME)

        print(f"\n{'=' * 52}")
        print(f"Extracao concluida! Total: {total_geral} frames")
        print(f"Pasta: {os.path.abspath(PASTA_SAIDA)}")
