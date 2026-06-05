# 💡 Guias de Como-Fazer (How-to Guides)

Este documento contém guias passo a passo focados em tarefas específicas e avançadas do ecossistema do **DeepMarket Tracker**.

---

## 📸 Como Extrair Frames de Novos Vídeos de Monitoramento

Para expandir o dataset ou criar um dataset para uma nova câmera, você precisa extrair frames em intervalos regulares para rotulação (evitando imagens quase idênticas de frames consecutivos).

### Passo 1: Organizar os vídeos
Crie uma pasta chamada `Videos` na raiz do projeto e coloque os arquivos brutos gravados da câmera (formatos suportados: `.mp4`, `.avi`, `.mov`, `.mkv`).

### Passo 2: Configurar o script de extração
Abra o arquivo [extrair_frames.py](../extrair_frames.py) e configure os parâmetros na seção inicial:
```python
PASTA_VIDEOS       = "Videos"
PASTA_SAIDA        = "novos_frames"  # Pasta onde as imagens JPG serão salvas
SEGUNDOS_POR_FRAME = 5               # Extrai 1 frame a cada N segundos de vídeo
```

### Passo 3: Executar a extração
Rode o script no terminal:
```bash
python extrair_frames.py
```
O script processará todos os vídeos da pasta, exibirá uma barra de progresso e criará a pasta de saída com os frames prontos para upload em plataformas de rotulação como o Roboflow.

---

## 🤖 Como Treinar um Novo Modelo Customizado YOLOv8

Caso queira re-treinar o modelo com novas imagens ou classes (ex: diferenciar patinetes, carrinhos de bebê):

### Passo 1: Organizar o dataset no formato YOLOv8
O dataset deve seguir a seguinte estrutura de pastas:
```
├── train/
│   ├── images/  (fotos JPG)
│   └── labels/  (arquivos txt com anotações YOLO)
├── valid/
│   ├── images/
│   └── labels/
└── test/
    ├── images/
    └── labels/
```
E as configurações devem ser apontadas no arquivo [data.yaml](../data.yaml).

### Passo 2: Configurar o script de treinamento
No arquivo [treinar_yolov8.py](../treinar_yolov8.py), ajuste os hiperparâmetros desejados dentro do método `model.train()`:
- `epochs`: número de épocas (ex: `200` para convergência robusta).
- `batch`: tamanho do lote (`-1` para detecção automática com base na memória VRAM ou valores como `8`, `16`, `32`).
- `device`: se o CUDA estiver ativo, usará a placa gráfica automaticamente.

### Passo 3: Executar o treinamento
```bash
python treinar_yolov8.py
```
Os checkpoints, métricas e gráficos gerados serão salvos em `runs/treino/mercadinho_experimento[N]`. Os melhores pesos de detecção serão salvos em `runs/treino/mercadinho_experimento[N]/weights/best.pt`.

---

## 🛠️ Como Fabricar e Montar o Case Externo 3D para Câmera

Para usar a webcam Logitech C920 em ambiente externo, exposta à chuva e ao sol, é necessário imprimir um case de proteção.

### Passo 1: Obter o arquivo de modelagem
O modelo do case foi projetado especificamente para a Logitech C920. O arquivo `.3mf` está no diretório:
[`hardware/case_logitech_c920_externo.3mf`](../hardware/case_logitech_c920_externo.3mf)

### Passo 2: Configurações de Fatiamento (Slicer)
- **Material recomendado**: **PETG** (altamente recomendado pela resistência a intempéries, raios UV e calor). Evite usar PLA em áreas externas pois ele deforma com o calor do sol.
- **Preenchimento (Infill)**: Mínimo de `20%` a `30%`, padrão Grid ou Gyroid para maior resistência mecânica.
- **Suportes**: Ative suportes para as áreas salientes do encaixe.
- **Paredes (Perimeters)**: Pelo menos 3 ou 4 linhas de contorno para garantir vedação e resistência.

### Passo 3: Montagem
1. Desmonte a presilha articulada original da Logitech C920 (revelando o corpo da câmera).
2. Encaixe a câmera cuidadosamente no trilho interno do case impresso.
3. Use uma fina película de silicone ou fita isolante nas junções caso queira vedação extra contra umidade severa.
4. Monte o suporte articulado na parede ou janela usando parafusos.
