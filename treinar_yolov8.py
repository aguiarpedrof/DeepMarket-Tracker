from ultralytics import YOLO
import torch

# ── OBRIGATÓRIO NO WINDOWS: evita erro de multiprocessing ──────────────────
if __name__ == '__main__':

    # ── Verificação de GPU ──────────────────────────────────────────────────
    dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Dispositivo detectado: {'GPU (CUDA)' if dispositivo == 'cuda' else 'CPU'}")

    # ── Modelo base ─────────────────────────────────────────────────────────
    # yolov8n = nano  (mais rápido, menos preciso)
    # yolov8s = small (bom equilíbrio para datasets pequenos/médios)
    # yolov8m = medium
    model = YOLO("Yolo-Weights/yolov8n.pt")

    # ── Treino ───────────────────────────────────────────────────────────────
    # O Ultralytics aplica augmentation automaticamente a cada época na memória/GPU.
    # Não é necessário gerar variações em disco — mais eficiente e rápido.
    results = model.train(
        # Dataset
        data="data.yaml",          # aponta para train/valid/test e nomes de classes

        # Configurações gerais
        epochs=100,                 # aumente para 100 se o dataset for grande
        imgsz=640,
        batch=16,                  # reduza para 8 se der OOM na GPU
        device=dispositivo,
        workers=4,                 # threads de carregamento de dados
        project="runs/treino",     # pasta onde os resultados serão salvos
        name="mercadinho_v1",      # subpasta com métricas, pesos e gráficos
        exist_ok=True,             # permite reescrever sem erro se já existir

        # Augmentations (além do que o Roboflow já fez)
        flipud=0.0,                # Flip vertical — desativado (pessoa de cabeça pra baixo não faz sentido)
        fliplr=0.5,                # Flip horizontal — 50% das imagens
        hsv_v=0.4,                 # Variação de brilho (simula dia/noite)
        hsv_s=0.7,                 # Variação de saturação
        hsv_h=0.015,               # Leve variação de matiz
        degrees=5.0,               # Rotação leve (câmeras ligeiramente tortas)
        translate=0.1,             # Translação leve
        scale=0.5,                 # Zoom aleatório
        mosaic=1.0,                # Junta 4 imagens numa — muito eficiente para generalização
        mixup=0.0,                 # Mixup desativado (funciona melhor com datasets maiores)
        copy_paste=0.0,            # Copy-paste desativado por padrão

        # Otimizador
        optimizer="AdamW",
        lr0=0.001,                 # learning rate inicial
        lrf=0.01,                  # fator final (lr0 * lrf = lr final)
        weight_decay=0.0005,
        warmup_epochs=3,           # épocas de warm-up

        # Outros
        save_period=10,            # salva checkpoint a cada 10 épocas
        val=True,                  # valida ao final de cada época
        plots=True,                # gera gráficos de loss, mAP etc.
        verbose=True,
    )

    print("\n✅ Treino concluído!")
    print(f"Pesos salvos em: runs/treino/mercadinho_v1/weights/best.pt")
    print("Use o best.pt no main.py para detecção em tempo real.")
