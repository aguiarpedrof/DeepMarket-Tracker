from ultralytics import YOLO
import torch

if __name__ == '__main__':
    # Usar GPU se disponível
    dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
    
    # Carrega o modelo que você acabou de treinar (o seu Experimento V2)
    model = YOLO(r"C:\Users\pedro\runs\detect\runs\treino\mercadinho_experimento85\weights\best.pt")

    print("\n" + "="*50)
    print("        AVALIAÇÃO NO DATASET DE VALIDAÇÃO (VAL)     ")
    print("="*50)
    # AVALIAÇÃO: (As mesmas que você via ao final do treinamento)
    # O YOLO já salvou a matriz de confusão e loss lá na pasta do treino, mas podemos rodar forçadamente
    metricas_val = model.val(
        data="data.yaml",
        split="val",
        device=dispositivo,
        project="runs/avaliacao",
        name="validacao_experimento",
        plots=True # Gera os gráficos das matrizes de análise
    )
    
    # Exibir a loss e o mAP que ele encontrou no Valid
    print(f"[VAL] mAP50: {metricas_val.box.map50:.3f}")
    
    print("\n\n" + "="*50)
    print("           TESTE NO DATASET 'TESTE FINAL'           ")
    print("="*50)
    # TESTE: (Este dataset a Inteligência Artificial NUNCA VIU na vida, nem para validar erro)
    # Ideal para medir o desempenho cru perante a realidade.
    metricas_test = model.val(
        data="data.yaml",
        split="test",
        device=dispositivo,
        project="runs/avaliacao",
        name="teste_experimento",
        plots=True
    )
    
    print(f"[TESTE] mAP50: {metricas_test.box.map50:.3f}")
    
    print("\n✅ Métricas calculadas!")
    print("Os gráficos (Matriz de Confusão, Curvas P-R, F1) foram salvos nas pastas: runs/avaliacao/validacao_experimento/  e runs/avaliacao/teste_experimento/")
