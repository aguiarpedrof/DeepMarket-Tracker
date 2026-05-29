from ultralytics import YOLO
import torch

if __name__ == '__main__':

    dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"{'GPU (CUDA)' if dispositivo == 'cuda' else 'CPU'}")

    model = YOLO("Yolo-Weights/yolov8s.pt")
    model.train(
        data="data.yaml",
        epochs=200,
        imgsz=640,
        device=dispositivo,
        workers=0,  
        project="runs/treino",
        name="mercadinho_experimento8",
        exist_ok=False
    )


