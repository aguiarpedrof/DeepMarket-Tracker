# 📋 Documento de Referência (Reference)

Este documento contém especificações técnicas detalhadas, parâmetros de configuração, esquemas de dados e métricas do modelo do **DeepMarket Tracker**.

---

## 💻 Parâmetros e Argumentos de CLI

O arquivo principal [`main.py`](../main.py) aceita argumentos pela linha de comando e possui configurações estáticas que regulam a sensibilidade e o comportamento da detecção.

### Argumentos de Linha de Comando (CLI)

| Argumento | Tipo | Padrão | Descrição |
|---|---|---|---|
| `--model` | `str` | `'best.pt'` | Caminho relativo ou absoluto para o arquivo de pesos do modelo YOLOv8 treinado (`.pt`). |

### Variáveis de Configuração Estática (`main.py`)

Estas variáveis estão localizadas no cabeçalho de [`main.py`](../main.py) e podem ser ajustadas conforme a necessidade do local:

```python
CAMERA_ID = 0                 # ID do dispositivo OpenCV (0 para webcam integrada/USB padrão)
CAP_WIDTH = 1280              # Resolução horizontal de captura
CAP_HEIGHT = 720              # Resolução vertical de captura
CONFIDENCE_THRESHOLD = 0.30   # Limiar mínimo de confiança para detecção da classe pedestre
TRACKER_TYPE = "bytetrack.yaml" # Arquivo de configuração de tracking da Ultralytics
LIMIAR_DESAPARECIDO = 60      # Número de frames que o tracker aguarda antes de classificar um candidato oculto como PASSOU (~2s a 30fps)
DIRECAO_ENTRADA = 1           # Direção matemática do cruzamento da linha de entrada (pode ser 1 ou -1)
```

---

## 🤖 Hiperparâmetros e Métricas do Modelo (YOLOv8s)

O modelo customizado foi treinado para detectar a classe **pedestre/pessoa** nas condições específicas da câmera urbana instalada.

### Informações de Treinamento (`mercadinho_experimento815`)

- **Arquitetura**: YOLOv8s (Small)
- **Parâmetros**: 11.136.374
- **GFLOPs**: 28.6
- **Dataset**: 2.051 imagens de treino | 599 imagens de validação | 723 instâncias anotadas
- **Épocas**: 200
- **Batch Size**: 12 (AutoBatch a 60% VRAM)
- **Otimizador**: AdamW (Learning Rate inicial = `0.001`, final factor = `0.01`, weight decay = `0.0005`)

### Augmentations Utilizadas no Treino

O pipeline de augmentations da Ultralytics foi parametrizado no script de treino para lidar com condições de iluminação urbana diurna/noturna e variações de posicionamento:
- **Flip horizontal (`fliplr`)**: 70%
- **Flip vertical (`flipud`)**: Desativado (0.0)
- **Brilho HSV (`hsv_v`)**: 0.6
- **Saturação HSV (`hsv_s`)**: 0.8
- **Matiz HSV (`hsv_h`)**: 0.018
- **Rotação (`degrees`)**: 5.0 graus
- **Translação (`translate`)**: 0.15
- **Escala/Zoom (`scale`)**: 0.5
- **Mosaico (`mosaic`)**: 1.0 (100% de probabilidade)

### Métricas de Validação no Dataset de Teste

Métricas obtidas com o melhor checkpoint (`best.pt`) no conjunto de validação:

| Métrica | Valor | Descrição |
|---|---|---|
| **Precision (P)** | `0.911` | 91.1% das detecções feitas são pessoas reais. |
| **Recall (R)** | `0.884` | 88.4% de todas as pessoas reais na cena foram detectadas. |
| **mAP50** | `0.928` | Precisão média calculada em IoU de 50%. |
| **mAP50-95** | `0.577` | Precisão média calculada em múltiplos IoUs (de 50% a 95%). |
| **Tempo de Inferência** | `2.7ms` | Média de processamento por imagem (excluindo pré/pós-proc). |

---

## 🗄️ Esquema do Banco de Dados Relacional (Star Schema)

A modelagem de banco de dados abaixo foi desenhada no formato **Star Schema** para fins analíticos (OLAP) e conexões com dashboards (Streamlit / Power BI).

### 1. Tabela Dimensão: `dim_data`
Armazena a granularidade temporal de dias.
- `id_data` (INT, PK): Chave primária.
- `data` (DATE): Data no formato AAAA-MM-DD.
- `dia_semana` (VARCHAR): Ex: Segunda-feira, Terça-feira.
- `mes` (INT): Mês (1-12).
- `ano` (INT): Ano.

### 2. Tabela Dimensão: `dim_hora`
Armazena a granularidade de horas e turnos.
- `id_hora` (INT, PK): Chave primária.
- `hora` (INT): Valor da hora (0-23).
- `turno` (VARCHAR): Manhã, Tarde, Noite, Madrugada.

### 3. Tabela Fato: `fato_fluxo`
Registra eventos discretos de fluxo de entrada/saída ou passagem.
- `id_fluxo` (INT, PK): Chave primária.
- `id_data` (INT, FK -> `dim_data.id_data`)
- `id_hora` (INT, FK -> `dim_hora.id_hora`)
- `track_id` (INT): Identificação gerada pelo ByteTrack.
- `event_type` (VARCHAR): ENTRADA, SAIDA, PASSAGEM.
- `direction` (INT): Sentido da travessia (1 ou -1).

### 4. Tabela Fato: `fato_sessao`
Registra a duração e status de conversão de cada pedestre.
- `id_sessao` (INT, PK): Chave primária.
- `id_data` (INT, FK -> `dim_data.id_data`)
- `track_id` (INT): Identificação do pedestre.
- `entrada_time` (TIMESTAMP): Horário que o pedestre entrou no mercado.
- `saida_time` (TIMESTAMP): Horário de saída detectado.
- `permanencia` (INTERVAL): Tempo de permanência do cliente na loja.
- `converteu` (BOOLEAN): Indica se o pedestre foi qualificado como cliente (ENTROU).

### 5. Tabela Fato: `resumo_horario`
Armazena dados agregados pré-calculados para otimização de dashboards.
- `id_resumo` (INT, PK): Chave primária.
- `id_data` (INT, FK -> `dim_data.id_data`)
- `id_hora` (INT, FK -> `dim_hora.id_hora`)
- `total_entradas` (INT)
- `total_passantes` (INT)
- `taxa_conversao` (DECIMAL)
- `tempo_medio` (INTERVAL)

---

## 🔌 Especificações do Hardware

- **Câmera**: Logitech C920 Pro HD
  - Resolução nativa de vídeo: 1080p a 30fps
  - Tipo de lente: Vidro Full HD
  - Campo de visão (FoV): 78 graus
  - Tipo de conexão: USB 2.0 / 3.0
- **Suporte 3D**: Case customizado impresso em filamento PETG
  - Resistência térmica: até 80°C antes de sofrer deformação térmica
  - Resistência química/clima: Excelente contra umidade e radiação UV (solar)
  - Link do modelo fatiador: [`hardware/case_logitech_c920_externo.3mf`](../hardware/case_logitech_c920_externo.3mf)
