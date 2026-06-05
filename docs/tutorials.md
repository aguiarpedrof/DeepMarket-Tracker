# 🏁 Tutorial: Primeiros Passos no DeepMarket Tracker

Bem-vindo ao tutorial de introdução do **DeepMarket Tracker**! Este guia foi feito para ajudar você a configurar seu ambiente e colocar o sistema de contagem para rodar pela primeira vez na sua máquina.

---

## 🛠️ 1. Preparação do Ambiente

Antes de começar, certifique-se de que você tem o **Python 3.8** (ou superior) instalado no seu sistema.

### Passo 1: Clonar o repositório
Abra o terminal/PowerShell e execute:
```bash
git clone https://github.com/aguiarpedrof/DeepMarket-Tracker.git
cd DeepMarket-Tracker
```

### Passo 2: Instalar as dependências
Instale as bibliotecas necessárias para processamento de imagem, visão computacional e aprendizado de máquina:
```bash
pip install ultralytics opencv-python cvzone torch
```

> [!NOTE]
> Se você possui uma placa de vídeo NVIDIA compatível e quer usar aceleração por GPU (CUDA) para o rastreamento ou treinamento em tempo real, certifique-se de instalar a versão correta do PyTorch com suporte a CUDA disponível em [pytorch.org](https://pytorch.org/).

---

## 🚀 2. Rodando o Sistema de Contagem

### Passo 1: Baixar os pesos do modelo
Certifique-se de que você tem os pesos do modelo treinado (por exemplo, `best.pt`) na raiz do projeto ou na pasta `Yolo-Weights/`. Se o seu modelo padrão estiver em outra pasta, passe o caminho por parâmetro.

### Passo 2: Iniciar o script
Execute o arquivo principal:
```bash
python main.py --model Yolo-Weights/yolov8s.pt
```
*(Substitua `Yolo-Weights/yolov8s.pt` pelo caminho do seu arquivo de pesos, caso seja diferente)*.

---

## 📐 3. Interface de Desenho das Linhas (Interativo)

Na primeira execução, o sistema abrirá uma janela de vídeo congelada no primeiro frame para que você desenhe as **3 linhas virtuais** de monitoramento.

Siga os passos na janela interativa:

1. **Linha A (Laranja - Antes da entrada)**: Clique em dois pontos na calçada/rua para definir por onde os pedestres chegam na área de interesse.
2. **Entrada (Verde - Acesso ao mercado)**: Clique em dois pontos na soleira/portão do mercadinho para definir a entrada real.
3. **Linha B (Vermelho - Passagem reta)**: Clique em dois pontos na calçada adiante para rastrear quem passou direto pela calçada sem entrar.

### Comandos da interface:
- **Clique com Botão Esquerdo**: Adiciona um ponto.
- **Teclado `R`**: Remove o último ponto selecionado (desfazer).
- **Teclado `ENTER`**: Confirma as 3 linhas (somente após marcar todos os 6 pontos).

Após pressionar `ENTER`, o vídeo começará a rodar e a contagem se iniciará automaticamente na tela.

---

## 📹 4. Testar com um Vídeo Gravado (Em vez da Webcam)

Por padrão, o script tenta abrir a webcam principal do computador (`CAMERA_ID = 0`). Se você quiser rodar a simulação em cima de um arquivo de vídeo gravado:

1. Abra o arquivo [main.py](../main.py) no seu editor de código.
2. Procure pela linha `cap = cv2.VideoCapture(CAMERA_ID)`.
3. Comente essa linha e descomente a linha do vídeo, ou altere o parâmetro para o caminho do seu arquivo:
   ```python
   # Para rodar com um arquivo de vídeo
   cap = cv2.VideoCapture("Caminho/Para/Seu/Video.mp4")
   ```
4. Salve o arquivo e execute `python main.py` novamente.
