from pydoc import classname
from ultralytics import YOLO
import cv2 # para tempo real
import math
import cvzone # pra colocar a caixa de texto com o fundo
import torch
import numpy as np
from sort import *
import psycopg2
import datetime
import os
from dotenv import load_dotenv

load_dotenv() # Carrega .env

# --- CONFIGURAÇÕES DO BANCO DE DADOS ---
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

conexao_db = None
cursor_db = None
try:
    conexao_db = psycopg2.connect(
        host=POSTGRES_HOST, port=POSTGRES_PORT, dbname=POSTGRES_DB,
        user=POSTGRES_USER, password=POSTGRES_PASSWORD
    )
    cursor_db = conexao_db.cursor()
    print("✅ Conectado ao banco! O sistema agora vai enviar dados para a tabela tracker_events.")
except Exception as e:
    print(f" Conexão com banco falhou. Rodando sem salvar dados offline. Erro: {e}")

cap = cv2.VideoCapture(0)
# cap = cv2.VideoCapture("2026-03-17 17-20-03_000000s.jpg")

cap.set(3, 1280) 
cap.set(4, 720) 

model = YOLO(r"C:\Users\pedro\runs\detect\runs\treino\mercadinho_experimento85\weights\best.pt")

# tracker = Sort(max_age=2000, min_hits=3, iou_threshold=0.3)  # ANTERIOR: max_age alto causava IDs "fantasmas" por ~80s
tracker = Sort(
    max_age=30,          # 30 frames sem detecção → descarta o track (~1-2s). Evita IDs zumbis.
    min_hits=3,          # precisa de 3 detecções consecutivas para criar um track sólido
    iou_threshold=0.4    # matching mais exigente → menos troca de ID entre pessoas próximas
)


# =============================================================================
# ZONA: DEFINIÇÃO DAS LINHAS DE CONTAGEM
# =============================================================================
#
# Usamos 3 linhas virtuais:
#
#   LINHA_A:       Corta a rua ANTES da bifurcação.
#                  Todo mundo que entra no campo de visão útil cruza aqui primeiro.
#
#   LINHA_ENTRADA: Corta o caminho que vai para o mercadinho (a bifurcação).
#                  Quem cruza aqui NA DIREÇÃO CERTA = entrou no mercadinho.
#                  Quem sai do mercadinho cruza na direção CONTRÁRIA = NÃO conta.
#
#   LINHA_B:       Corta a rua DEPOIS da bifurcação (quem foi reto).
#                  Serve para confirmar quem passou sem entrar.
#
# DIREÇÃO DE ENTRADA:
#   A função cruzou_linha() retorna +1 ou -1 dependendo do sentido do cruzamento.
#   DIRECAO_ENTRADA = +1 significa: cruzou do lado "esquerdo" para o "direito" da linha
#                                   (determinado pela ordem dos pontos P1→P2).
#   Se a contagem estiver contando ao contrário, troque para -1.
#
DIRECAO_ENTRADA = 1   # 👈 troque para -1 se estiver contando no sentido errado

# --- OPÇÃO A: Coordenadas manuais ---
# Descomente e preencha com os valores reais do seu frame.
# Cada linha é definida por dois pontos: (x1, y1) e (x2, y2).
#
# LINHA_A       = [(  0, 400), (400, 500)]   # ✏️ COLOQUE AS COORDENADAS REAIS AQUI
# LINHA_ENTRADA = [(300, 350), (500, 600)]   # ✏️ COLOQUE AS COORDENADAS REAIS AQUI
# LINHA_B       = [(500, 400), (900, 500)]   # ✏️ COLOQUE AS COORDENADAS REAIS AQUI
#
# --- OPÇÃO B: Coordenadas definidas clicando na tela (ver abaixo) ---
# Deixe as variáveis como None e o modo interativo vai pedir que você clique.
LINHA_A       = [(  552, 700), (610, 640)]
LINHA_ENTRADA = [(  550, 610), (530, 530)]
LINHA_B       = [(  290, 625), (350, 580)]

# =============================================================================
# MODO INTERATIVO: Clique para definir as linhas
# =============================================================================
# Como usar:
#   1. O programa mostra o primeiro frame.
#   2. Para cada linha, você clica em 2 pontos.
#   3. Pressione ENTER para confirmar cada linha.
#   4. Pressione 'R' para refazer a linha atual.
#   5. Repita para as 3 linhas.

_pontos_clicados = []
_nome_linha_atual = ""

def _mouse_callback_linha(event, x, y, flags, param):
    global _pontos_clicados
    if event == cv2.EVENT_LBUTTONDOWN:
        if len(_pontos_clicados) < 2:
            _pontos_clicados.append((x, y))

def _definir_linha_interativa(frame_base, nome_linha, cor):
    """Abre uma janela e pede ao usuário que clique em 2 pontos para definir a linha."""
    global _pontos_clicados
    _pontos_clicados = []
    janela = f"Defina a {nome_linha} | Clique em 2 pontos | ENTER=confirmar | R=refazer"
    cv2.namedWindow(janela, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(janela, _mouse_callback_linha)

    print(f"\n📐 [{nome_linha}] Clique em 2 pontos para definir a linha. ENTER=confirmar | R=refazer")

    while True:
        temp = frame_base.copy()
        instrucao = f"{nome_linha}: clique em {2 - len(_pontos_clicados)} ponto(s)"
        cv2.putText(temp, instrucao, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        for pt in _pontos_clicados:
            cv2.circle(temp, pt, 7, cor, -1)

        if len(_pontos_clicados) == 2:
            cv2.line(temp, _pontos_clicados[0], _pontos_clicados[1], cor, 3)
            cv2.putText(temp, "ENTER=confirmar | R=refazer", (20, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, cor, 2)

        cv2.imshow(janela, temp)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('r'):
            _pontos_clicados = []
            print(f"  🔄 Refazendo {nome_linha}...")

        elif key in [13, ord('\r'), ord('\n')]:  # ENTER
            if len(_pontos_clicados) == 2:
                print(f"  ✅ {nome_linha} definida: {_pontos_clicados[0]} → {_pontos_clicados[1]}")
                break
            else:
                print(f"  ⚠️  Clique em 2 pontos antes de confirmar!")

    cv2.destroyWindow(janela)
    return (_pontos_clicados[0], _pontos_clicados[1])

# Se alguma linha não foi definida manualmente, entra no modo interativo
if LINHA_A is None or LINHA_ENTRADA is None or LINHA_B is None:
    print("\n================================================")
    print("MODO INTERATIVO - DEFINIÇÃO DAS LINHAS")
    print("Você vai definir 3 linhas clicando na tela.")
    print("================================================")

    sucesso, primeiro_frame = cap.read()
    if not sucesso:
        print("❌ Não foi possível capturar o primeiro frame. Verifique a câmera.")
        cap.release()
        exit()

    if LINHA_A is None:
        p1, p2 = _definir_linha_interativa(primeiro_frame, "LINHA A (antes da bifurcação)", (255, 165, 0))  # laranja
        LINHA_A = [p1, p2]

    if LINHA_ENTRADA is None:
        p1, p2 = _definir_linha_interativa(primeiro_frame, "LINHA ENTRADA (bifurcação → mercadinho)", (0, 255, 0))  # verde
        LINHA_ENTRADA = [p1, p2]

    if LINHA_B is None:
        p1, p2 = _definir_linha_interativa(primeiro_frame, "LINHA B (depois da bifurcação - quem foi reto)", (0, 0, 255))  # vermelho
        LINHA_B = [p1, p2]

    print("\n✅ Linhas definidas! Iniciando contagem...\n")
    print(f"   LINHA_A       = {LINHA_A}")
    print(f"   LINHA_ENTRADA = {LINHA_ENTRADA}")
    print(f"   LINHA_B       = {LINHA_B}")
    print("   (Copie esses valores para usar coordenadas fixas no futuro)\n")

# =============================================================================
# FUNÇÕES DE DETECÇÃO DE CRUZAMENTO
# =============================================================================

def lado_da_linha(ponto, p1, p2):
    """
    Retorna o lado em que o ponto está em relação à linha p1→p2.
    Baseado no sinal do produto vetorial (cross product).
    Positivo = um lado, Negativo = outro lado, Zero = sobre a linha.
    """
    x,  y  = ponto
    x1, y1 = p1
    x2, y2 = p2
    return (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)

def cruzou_linha(pos_atual, pos_anterior, linha):
    """
    Verifica se o ponto de (pos_anterior) até (pos_atual) cruzou a linha.
    Retorna:
      +1  se cruzou no sentido "positivo" (DIRECAO_ENTRADA padrão)
      -1  se cruzou no sentido inverso
       0  se não cruzou
    """
    p1, p2 = linha
    lado_atual    = lado_da_linha(pos_atual,    p1, p2)
    lado_anterior = lado_da_linha(pos_anterior, p1, p2)

    # Cruzou = sinais opostos (produto negativo)
    if lado_atual * lado_anterior < 0:
        return 1 if lado_anterior > 0 else -1
    return 0

# =============================================================================
# ESTADO POR PESSOA RASTREADA
# =============================================================================
#
# estados[id] = {
#   "pos_anterior": (cx, cy) ou None,   <- posição no frame anterior
#   "estado": "NONE" | "CANDIDATO" | "ENTROU" | "PASSOU",
#   "contado_entrada": False,           <- já foi contado como entrada?
#   "frames_sem_ver": 0                 <- quantos frames sem detectar (reservado)
# }
#
estados = {}

# Contadores globais
total_entrou = 0   # entrou no mercadinho
total_passou = 0   # seguiu reto sem entrar

# IDs já processados definitivamente (evita re-contagem dentro da mesma sessão)
ids_ja_contados_entrada = set()
ids_ja_contados_passou  = set()

# =============================================================================
# LINHA ANTIGA (comentada - era o polígono)
# =============================================================================
# ANTERIOR: contagem por polígono (substituída pelas linhas acima)
# limits = [375, 650, 270, 620, 350, 560]
# totalContados = []

# --- INÍCIO DA DEFINIÇÃO DO POLÍGONO INTERATIVO (substituído pelo modo de linhas) ---
# polygon_points = []
# def draw_polygon(event, x, y, flags, param):
#     ...
# (código completo comentado abaixo para referência)
#
# suucccess, first_frame = cap.read()
# if suucccess:
#     cv2.namedWindow('Definir Poligono')
#     cv2.setMouseCallback('Definir Poligono', draw_polygon)
#     ...
#     while True:
#         temp_frame = first_frame.copy()
#         if len(polygon_points) > 0:
#             cv2.polylines(temp_frame, [np.array(polygon_points, np.int32)], ...)
#             ...
#         cv2.imshow('Definir Poligono', temp_frame)
#         key = cv2.waitKey(1) & 0xFF
#         if key in [13, ord('q'), ord(' ')]:
#             break
#     cv2.destroyWindow('Definir Poligono')
#
# if len(polygon_points) < 3:
#     limits = [375, 650, 270, 620, 350, 560]
#     pts = np.array([...], np.int32)
# else:
#     pts = np.array(polygon_points, np.int32)
# pts = pts.reshape((-1, 1, 2))
# --- FIM DA DEFINIÇÃO DO POLÍGONO INTERATIVO ---

# =============================================================================
# LOOP PRINCIPAL
# =============================================================================
while True:
    suucccess, imagem = cap.read()
    if not suucccess:
        break

    results = model(imagem,
                    stream=True,
                    conf=0.40)

    deteccoes = np.empty((0, 5))
    for i in results:
        boxes = i.boxes
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0]
            x1 = int(x1)
            y1 = int(y1)
            x2 = int(x2)
            y2 = int(y2)
            w, h = x2 - x1, y2 - y1
            # cvzone.cornerRect(imagem,(x1,y1,w,h),l=5)  # COMENTADO: desenhado pelo tracker abaixo
            # cv2.rectangle(imagem, (x1,y1),(x2,y2),(255,0, 255),3)
            # cv2.putText(imagem, "Objeto", (x1,y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255,0,255), 2)
            conf = math.ceil(box.conf[0] * 100) / 100
            currentArray = np.array([x1, y1, x2, y2, conf])
            deteccoes = np.vstack((deteccoes, currentArray))

    resultsTracker = tracker.update(deteccoes)

    # --- Desenha as 3 linhas de contagem ---
    cv2.line(imagem, LINHA_A[0],       LINHA_A[1],       (255, 165, 0), 3)  # laranja = Linha A
    cv2.line(imagem, LINHA_ENTRADA[0], LINHA_ENTRADA[1], (0, 255, 0),   3)  # verde   = Entrada mercadinho
    cv2.line(imagem, LINHA_B[0],       LINHA_B[1],       (0, 0, 255),   3)  # vermelho= Linha B (passou reto)

    # Labels das linhas
    cv2.putText(imagem, "Linha A",       LINHA_A[0],       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 165, 0), 2)
    cv2.putText(imagem, "Entrada",       LINHA_ENTRADA[0], cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0),   2)
    cv2.putText(imagem, "Passou reto",   LINHA_B[0],       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255),   2)

    # --- ANTERIOR: desenhava polígono ---
    # cv2.polylines(imagem, [pts], True, (0, 0, 255), 4)  # substituído pelas linhas acima

    for result in resultsTracker:
        x1, y1, x2, y2, id = result
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        w, h = x2 - x1, y2 - y1
        iden = int(id)

        cvzone.cornerRect(imagem, (x1, y1, w, h), l=5)

        # Mostra ID e estado atual da pessoa
        estado_atual = estados.get(iden, {}).get("estado", "NONE")
        cvzone.putTextRect(imagem, f'ID:{iden} [{estado_atual}]',
                           (max(0, x1), max(20, y1)), scale=0.8, thickness=1, offset=5)

        # Ponto de referência: centro inferior da bounding box (pés)
        centrox = x1 + w // 2
        centroy = y2
        cv2.circle(imagem, (centrox, centroy), 5, (255, 0, 255), cv2.FILLED)

        # --- ANTERIOR: usava pointPolygonTest ---
        # result = cv2.pointPolygonTest(pts, (centrox, centroy), False)
        # if result >= 0:
        #     cv2.polylines(imagem, [pts], True, (0, 255, 0), 4)
        # --- substituído pela lógica de linhas abaixo ---

        # Inicializa estado para IDs novos
        if iden not in estados:
            estados[iden] = {
                "pos_anterior":      None,
                "estado":            "NONE",
                "contado_entrada":   False,
            }

        pos_atual     = (centrox, centroy)
        pos_anterior  = estados[iden]["pos_anterior"]

        # Só processa cruzamento se temos posição anterior válida
        if pos_anterior is not None:

            # =================================================================
            # MÁQUINA DE ESTADOS — DUAS MÃOS
            #
            # Regras:
            #   1. Cruzou LINHA_A OU LINHA_B (qualquer direção) → CANDIDATO
            #      - Vem da esquerda: cruza A primeiro
            #      - Vem da direita:  cruza B primeiro
            #      Ambos se tornam CANDIDATO → lógica funciona para dois sentidos.
            #
            #   2. CANDIDATO cruza LINHA_ENTRADA no sentido certo → ENTROU (+1)
            #
            #   3. CANDIDATO cruza a outra linha (A ou B) sem cruzar ENTRADA → PASSOU
            #
            #   4. LINHA_ENTRADA cruzada no sentido INVERSO = SAÍDA do mercadinho
            #      → NÃO conta como nova entrada (resolve ID perdido após 10min)
            # =================================================================

            cruzamento_A       = cruzou_linha(pos_atual, pos_anterior, LINHA_A)
            cruzamento_B       = cruzou_linha(pos_atual, pos_anterior, LINHA_B)
            cruzamento_entrada = cruzou_linha(pos_atual, pos_anterior, LINHA_ENTRADA)

            estado_atual = estados[iden]["estado"]

            # -----------------------------------------------------------------
            # PASSO 1: Qualquer cruzamento de A ou B → vira CANDIDATO
            # (independente do sentido, para suportar as duas mãos da rua)
            # -----------------------------------------------------------------
            if estado_atual == "NONE":
                if cruzamento_A != 0 or cruzamento_B != 0:
                    estados[iden]["estado"] = "CANDIDATO"
                    estado_atual = "CANDIDATO"
                    print(f"👀 [CANDIDATO] Pessoa ID {iden} entrou na zona de análise.")

            # -----------------------------------------------------------------
            # PASSO 2: CANDIDATO cruza LINHA_ENTRADA no sentido certo → ENTROU
            # -----------------------------------------------------------------
            if estado_atual == "CANDIDATO" and cruzamento_entrada == DIRECAO_ENTRADA:
                if iden not in ids_ja_contados_entrada:
                    ids_ja_contados_entrada.add(iden)
                    estados[iden]["estado"] = "ENTROU"
                    estados[iden]["contado_entrada"] = True
                    total_entrou += 1
                    print(f"🛒 [ENTRADA] Cliente ID {iden} entrou no mercadinho! Total: {total_entrou}")

                    # --- REGISTRA ENTRADA NO BANCO DE DADOS ---
                    if conexao_db and cursor_db:
                        try:
                            agora = datetime.datetime.now()
                            cursor_db.execute(
                                "INSERT INTO tracker_events (track_id, event_time, event_type, direction) VALUES (%s, %s, %s, %s)",
                                (iden, agora, 'ENTRADA', 'IN')
                            )
                            conexao_db.commit()
                            print(f"  💾 Salvo no banco de dados!")
                        except Exception as e:
                            print(f"  ❌ Erro ao salvar: {e}")
                            conexao_db.rollback()

            # -----------------------------------------------------------------
            # PASSO 3: CANDIDATO cruza A ou B sem ter entrado → PASSOU RETO
            # (veio pela esquerda e cruzou B sem entrar, ou vice-versa)
            # -----------------------------------------------------------------
            elif estado_atual == "CANDIDATO":
                # Verifica se cruzou a "outra" linha (completou a travessia sem entrar)
                if cruzamento_A != 0 or cruzamento_B != 0:
                    if iden not in ids_ja_contados_passou:
                        ids_ja_contados_passou.add(iden)
                        estados[iden]["estado"] = "PASSOU"
                        total_passou += 1
                        print(f"➡️  [PASSOU RETO] Pessoa ID {iden} passou sem entrar. Total passou: {total_passou}")

            # -----------------------------------------------------------------
            # PASSO 4 (qualquer estado): LINHA_ENTRADA cruzada no sentido INVERSO
            # = pessoa SAINDO do mercadinho → NÃO conta como nova entrada.
            # Solução para IDs perdidos: quando a pessoa sai com novo ID,
            # o cruzamento é no sentido contrário → ignorado pela contagem.
            # -----------------------------------------------------------------
            if cruzamento_entrada == -DIRECAO_ENTRADA:
                if estados[iden]["estado"] not in ("SAIU",):
                    print(f"🚪 [SAÍDA] Pessoa ID {iden} saiu do mercadinho.")
                    estados[iden]["estado"] = "SAIU"
                # Opcional: registrar saída no banco (descomente se quiser)
                # if conexao_db and cursor_db:
                #     try:
                #         agora = datetime.datetime.now()
                #         cursor_db.execute(
                #             "INSERT INTO tracker_events (track_id, event_time, event_type, direction) VALUES (%s, %s, %s, %s)",
                #             (iden, agora, 'SAIDA', 'OUT')
                #         )
                #         conexao_db.commit()
                #     except Exception as e:
                #         print(f"  ❌ Erro ao salvar saída: {e}")
                #         conexao_db.rollback()

        # Atualiza posição anterior para o próximo frame
        estados[iden]["pos_anterior"] = pos_atual

    # --- Painel de contagem ---
    # ANTERIOR: cvzone.putTextRect(imagem, f'Total: {len(totalContados)}',(50,50), ...)
    # Substituído pelo painel abaixo com mais informações:
    cvzone.putTextRect(imagem, f'Entrou: {total_entrou}',  (20, 50),  scale=1.8, thickness=2, offset=10, colorR=(0, 180, 0))
    cvzone.putTextRect(imagem, f'Passou: {total_passou}',  (20, 100), scale=1.2, thickness=2, offset=8,  colorR=(50, 50, 200))

    cv2.imshow("Video", imagem)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# --- Limpeza ---
if cursor_db: cursor_db.close()
if conexao_db: conexao_db.close()

cap.release()
cv2.destroyAllWindows()
