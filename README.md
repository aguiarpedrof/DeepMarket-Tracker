# 🛒 DeepMarket Tracker

![Python](https://img.shields.io/badge/python-3670A0?style=flat-square&logo=python&logoColor=ffdd54)
![OpenCV](https://img.shields.io/badge/opencv-%23white.svg?style=flat-square&logo=opencv&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-%23EE4C2C.svg?style=flat-square&logo=PyTorch&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)

> **Visão computacional aplicada ao varejo de bairro** — contagem inteligente de clientes em um mercado autônomo usando YOLOv8, tracking multi-objeto e análise de dados em tempo real.

---

### 📹 Sistema em operação — (4x)

<video src="https://github.com/aguiarpedrof/DeepMarket-Tracker/raw/design-interface/.github/images/Video4x.mp4" controls="controls" muted="muted" style="max-width: 100%;">
  O vídeo está disponível em: <a href="https://github.com/aguiarpedrof/DeepMarket-Tracker/raw/design-interface/.github/images/Video4x.mp4">baixar vídeo</a>
</video>

<details>
<summary>🔗 <b>Se o player não aparecer acima, clique aqui</b></summary>
<br>

O arquivo fonte está em: [`.github/images/Video4x.mp4`](https://github.com/aguiarpedrof/DeepMarket-Tracker/raw/design-interface/.github/images/Video4x.mp4)

</details>

> [!IMPORTANT]
> **⚖️ Nota de Privacidade e Ética / Privacy & Ethics Notice**
>
> 🇧🇷 As imagens e vídeos apresentados neste repositório são utilizados **exclusivamente para fins didáticos e acadêmicos**. O sistema realiza apenas **detecção e contagem de pessoas** — não há qualquer intenção ou capacidade de identificação individual. Nenhum dado biométrico é coletado ou armazenado.
> Para mais detalhes sobre os princípios éticos aplicados, consulte o [Guia de Explicações](docs/explanation.md#⚖️-nota-de-privacidade-e-ética-ethics--privacy).

---

## 📖 Documentação (Metodologia Diátaxis)

A documentação deste projeto está organizada de forma sistemática utilizando a estrutura **Diátaxis**, separada em quatro objetivos distintos:

| Pilar | Descrição | Link de Acesso |
|---|---|---|
| 🏁 **Tutoriais** | Guia passo a passo prático para configurar o ambiente e rodar o projeto pela primeira vez. | [Acessar Tutorial](docs/tutorials.md) |
| 💡 **Guias de Como-Fazer** | Receitas diretas para tarefas comuns (extrair frames, treinar modelos, imprimir case 3D). | [Acessar Como-Fazer](docs/how_to_guides.md) |
| 📋 **Referência** | Especificações técnicas de hardware, argumentos de linha de comando, métricas do modelo e esquema do banco de dados. | [Acessar Referência](docs/reference.md) |
| 🧠 **Explicações** | Aprofundamento teórico na máquina de estados, lógica de 3 linhas, superação da mureta de oclusão e discussões arquiteturais. | [Acessar Explicações](docs/explanation.md) |

---

## 🛠️ Stack Tecnológica

| Tecnologia | Uso |
|---|---|
| **YOLOv8s** (Ultralytics) | Detecção de pessoas — fine-tuned no dataset local |
| **ByteTrack** | Rastreamento multi-objeto robusto entre frames |
| **OpenCV / cvzone** | Captura de vídeo, processamento geométrico e renderização da UI |
| **PyTorch + CUDA** | Aceleração de hardware para inferência e treinamento |
| **Roboflow** | Processamento de datasets e rotulação de imagens |
| **PETG 3D Case** | Hardware de proteção física da câmera contra chuva e UV |

---

## 📁 Estrutura do Projeto

```
DeepMarket-Tracker/
│
├── docs/                      # 📑 Documentação estruturada (Diátaxis)
│   ├── tutorials.md           # ← Como rodar o sistema pela primeira vez
│   ├── how_to_guides.md       # ← Como extrair frames, treinar e fabricar case 3D
│   ├── reference.md           # ← Métricas de treino, CLI e modelagem DB
│   └── explanation.md         # ← Teoria das 3 linhas, FSM e oclusão
│
├── main.py                    # ← Pipeline principal (detecção + tracking + FSM)
├── treinar_yolov8.py          # ← Script de treinamento da YOLOv8s
├── extrair_frames.py          # ← Utilitário de amostragem de vídeo para dataset
├── data.yaml                  # ← Configuração do dataset
│
├── hardware/
│   └── case_logitech_c920_externo.3mf  # ← Modelo 3D (PETG)
│
└── requirements.txt           # ← Dependências do sistema
```

---

## 🗺️ Roadmap do Projeto

- [x] Detecção com YOLOv8 fine-tuned no ambiente real
- [x] Tracking com ByteTrack + máquina de estados
- [x] Contagem de entradas e passantes em tempo real
- [x] Case 3D em PETG para câmera externa Logitech C920
- [x] Interface interativa para definição espacial das linhas
- [ ] Persistência em banco de dados PostgreSQL (Star Schema)
- [ ] Dashboard Streamlit com métricas de conversão e fluxo
- [ ] Integração Power BI para análise histórica de varejo
- [ ] Registro analítico de tempo médio de permanência

---

## 📜 Licença

Este projeto está licenciado sob a licença MIT.

---

<div align="center">

**Feito com curiosidade, café e uma câmera apontada pra rua. ☕**

*"O que a ciência dos dados pode dizer sobre um mercadinho de bairro?"*

</div>
