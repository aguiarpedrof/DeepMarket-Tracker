# DeepMarket Tracker

Projeto de visão computacional para detecção de pessoas em um mercadinho, usando YOLOv8.

## O que faz

Detecta pessoas em tempo real via webcam ou arquivo de vídeo, exibindo bounding boxes e o nome da classe com nível de confiança.

## Estrutura

```
main.py            — detecção em tempo real
extrair_frames.py  — extrai frames de vídeos para montar o dataset
treinar_yolov8.py  — treina o modelo com o dataset exportado do Roboflow
data.yaml          — configuração do dataset (gerado pelo Roboflow)
```

## Como usar

**Requisitos**

```
pip install ultralytics opencv-python cvzone
```

**Detecção em tempo real**

Altere o caminho do modelo em `main.py` para o seu `best.pt` e rode:

```
python main.py
```

Para usar um vídeo em vez da webcam, descomente e ajuste a linha comentada no início de `main.py`.

**Treinar um novo modelo**

1. Exporte seu dataset do Roboflow no formato YOLOv8
2. Extraia o zip na raiz do projeto (vai criar `train/`, `valid/`, `test/` e `data.yaml`)
3. Rode:

```
python treinar_yolov8.py
```

O modelo treinado ficará em `runs/treino/mercadinho_v1/weights/best.pt`.

## Processo de desenvolvimento

O projeto começou como um experimento simples com webcam usando pesos genéricos do COCO. A ideia era depois afinar o modelo para o contexto específico do mercadinho.

**Coleta de dados**: os frames foram extraídos de vídeos gravados no local usando `extrair_frames.py`, que amostra 1 frame a cada N frames para evitar redundância.

**Rotulação**: tentamos usar a API do Gemini Vision para auto-rotular as ~1800 imagens, mas o limite gratuito de requisições foi atingido antes de concluir. A solução foi rotular manualmente pelo Roboflow, o que levou algumas horas mas garantiu qualidade.

**Treinamento**: o treino rodou localmente em uma RTX 3060 por cerca de 22 minutos, 100 épocas, com o modelo `yolov8n`. Resultado final: mAP50 de 78,5%.

**Dificuldades**:
- O limite de créditos de auto-rotulação forçou rotulação manual
- O comando de download do Roboflow (`curl -L`) não funciona no PowerShell do Windows — é necessário usar `Invoke-WebRequest`
- O dataset exportado inicialmente veio no formato COCO por engano. Foi necessário re-exportar em YOLOv8

## Resultado

```
Precision: 0.83   Recall: 0.75   mAP50: 0.785   mAP50-95: 0.275
```
