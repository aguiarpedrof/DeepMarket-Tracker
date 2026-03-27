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

load_dotenv()

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
    print("Conectado com o Banco")
except Exception as e:
    print(f" Conexão com banco falhou. {e}")

_cache_dim = {}  # cache para não repetir queries a cada frame

def _get_id_data(cur, data: datetime.date) -> int:
    """Retorna o id_data da dim_data para a data informada."""
    key = ('data', data)
    if key not in _cache_dim:
        cur.execute("SELECT id_data FROM dim_data WHERE data = %s", (data,))
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"Data {data} não encontrada em dim_data. Execute 02_populate_dims.sql.")
        _cache_dim[key] = row[0]
    return _cache_dim[key]

def _get_id_hora(cur, hora: int) -> int:
    """Retorna o id_hora da dim_hora para a hora (0-23) informada."""
    key = ('hora', hora)
    if key not in _cache_dim:
        cur.execute("SELECT id_hora FROM dim_hora WHERE hora = %s", (hora,))
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"Hora {hora} não encontrada em dim_hora. Execute 02_populate_dims.sql.")
        _cache_dim[key] = row[0]
    return _cache_dim[key]

# Guarda o id_sessao de cada track_id para poder fechar ao registrar saída
_sessao_aberta = {}

cap = cv2.VideoCapture(0)
#cap = cv2.VideoCapture("Videos\VideoTesteEntrandoPorBaixo.mp4")
# cap = cv2.VideoCapture("Videos\Video Project 4.mp4")

cap.set(3, 1280) 
cap.set(4, 720) 

model = YOLO(r"C:\Users\pedro\runs\detect\runs\treino\mercadinho_experimento85\weights\best.pt")

# tracker = Sort(max_age=2000, min_hits=3, iou_threshold=0.3)  # ANTERIOR: max_age alto causava IDs "fantasmas" por ~80s
tracker = Sort(
    max_age=100,          
    min_hits=2,          
    iou_threshold=0.15   
)

DIRECAO_ENTRADA = 1   # 👈 troque para -1 se estiver contando no sentido errado

LINHA_A       = None
LINHA_ENTRADA = None
LINHA_B       = None
#LINHA_A       = [(  552, 700), (610, 640)]
#LINHA_ENTRADA = [(  550, 610), (530, 530)]
#LINHA_B       = [(  290, 625), (350, 580)]


_pontos_interativos = []   # lista acumulada de pontos selecionados na tela (máx 6)
_CORES_LINHAS = [
    ((255, 165, 0), "Linha A (antes da entrada)"),
    ((0, 255, 0),   "Entrada (mercadinho)"),
    ((0, 0, 255),   "Linha B (passou reto)"),
]

def _mouse_callback_unico(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN and len(_pontos_interativos) < 6:
        _pontos_interativos.append((x, y))

def _definir_linhas_interativo(frame_base):

    global _pontos_interativos
    _pontos_interativos = []


    JANELA = "Defina as 3 linhas | Clique 6 pontos | R=desfazer | ENTER=confirmar"
    cv2.namedWindow(JANELA, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(JANELA, _mouse_callback_unico)

    while True:
        temp = frame_base.copy()
        n = len(_pontos_interativos)

        # Instrução no topo
        if n < 6:
            linha_idx = n // 2           # qual linha está sendo definida (0,1,2)
            ponto_idx = n % 2 + 1        # 1 ou 2 ponto da linha atual
            cor_atual, nome_atual = _CORES_LINHAS[linha_idx]
            msg = f"Clique o {ponto_idx}o ponto da {nome_atual}  [{n}/6]"
        else:
            msg = "6 pontos definidos ENTER=confirmar R=desfazer"
            cor_atual = (255, 255, 255)

        cv2.putText(temp, msg, (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 0), 4)
        cv2.putText(temp, msg, (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)

        # Desenha pontos e linhas que hja estao definidos
        for i, pt in enumerate(_pontos_interativos):
            cor, _ = _CORES_LINHAS[i // 2]
            cv2.circle(temp, pt, 8, cor, -1)
            cv2.circle(temp, pt, 9, (0, 0, 0), 1)  # borda preta

            # Par completo que desenha a linha
            if i % 2 == 1:
                cv2.line(temp, _pontos_interativos[i - 1], pt, cor, 3)

        # Legenda lateral
        for idx, (cor, nome) in enumerate(_CORES_LINHAS):
            status = "✓" if n >= (idx + 1) * 2 else ("..." if n >= idx * 2 else "aguardando")
            texto = f"{nome}: {status}"
            cv2.putText(temp, texto, (15, 70 + idx * 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3)
            cv2.putText(temp, texto, (15, 70 + idx * 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, cor, 1)

        cv2.imshow(JANELA, temp)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('r') and _pontos_interativos:
            removido = _pontos_interativos.pop()
            print(f"  🔄 Ponto removido: {removido}  ({len(_pontos_interativos)}/6)")

        elif key in [13, ord('\r'), ord('\n')]:  # ENTER
            if len(_pontos_interativos) == 6:
                break
            else:
                print(f"  ⚠️  Ainda faltam {6 - len(_pontos_interativos)} ponto(s)!")

    cv2.destroyWindow(JANELA)
    pts = _pontos_interativos
    return (
        [pts[0], pts[1]],   # LINHA_A
        [pts[2], pts[3]],   # LINHA_ENTRADA
        [pts[4], pts[5]],   # LINHA_B
    )

def lado_da_linha(ponto, p1, p2):
    x,  y  = ponto
    x1, y1 = p1
    x2, y2 = p2
    return (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)

def cruzou_linha(pos_atual, pos_anterior, linha):
    p1, p2 = linha
    lado_atual    = lado_da_linha(pos_atual,    p1, p2)
    lado_anterior = lado_da_linha(pos_anterior, p1, p2)

    # olha se houve mudança de lado em relação à linha INFINITA
    if lado_atual * lado_anterior >= 0:
        return 0

    
    lado_p1 = lado_da_linha(p1, pos_anterior, pos_atual)
    lado_p2 = lado_da_linha(p2, pos_anterior, pos_atual)
    if lado_p1 * lado_p2 > 0:
        return 0   # p1 e p2 no mesmo lado = cruzamento fora do segmento

    return 1 if lado_anterior > 0 else -1


estados = {}

total_entrou = 0   
total_passou = 0   

ids_ja_contados_entrada = set()
ids_ja_contados_passou  = set()


if LINHA_A is None or LINHA_ENTRADA is None or LINHA_B is None:
    ret, primeiro_frame = cap.read()
    if not ret:
        cap.release()
        cv2.destroyAllWindows()
        exit()
    LINHA_A, LINHA_ENTRADA, LINHA_B = _definir_linhas_interativo(primeiro_frame)
    print(f"   LINHA_A       = {LINHA_A}")
    print(f"   LINHA_ENTRADA = {LINHA_ENTRADA}")
    print(f"   LINHA_B       = {LINHA_B}")
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # volta ao início do vídeo

while True:
    suucccess, imagem = cap.read()
    if not suucccess:
        break

    results = model(imagem,
                    stream=True,
                    conf=0.30)

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

            conf = math.ceil(box.conf[0] * 100) / 100
            currentArray = np.array([x1, y1, x2, y2, conf])
            deteccoes = np.vstack((deteccoes, currentArray))

    resultsTracker = tracker.update(deteccoes)

    cv2.line(imagem, LINHA_A[0],       LINHA_A[1],       (255, 165, 0), 3)  #  Linha A laranja claro
    cv2.line(imagem, LINHA_ENTRADA[0], LINHA_ENTRADA[1], (0, 171, 6),   3)  # verde CDE6B3
    cv2.line(imagem, LINHA_B[0],       LINHA_B[1],       (0, 0, 255),   3)  # Linha B vermelha(passou reto)

    cv2.putText(imagem, "A", LINHA_A[0],cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 165, 0), 2)
    cv2.putText(imagem, "Entrada", LINHA_ENTRADA[0], cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0),   2)
    cv2.putText(imagem, "B",  LINHA_B[0],cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255),   2)


    for result in resultsTracker:
        x1, y1, x2, y2, id = result
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        w, h = x2 - x1, y2 - y1
        iden = int(id)

        cvzone.cornerRect(imagem, (x1, y1, w, h), l=7)

        # Mostra ID e estado atual da pessoa
        estado_atual = estados.get(iden, {}).get("estado", "NONE")
        cvzone.putTextRect(imagem, f'ID:{iden} [{estado_atual}]',
                           (max(0, x1), max(20, y1)), scale=0.8, thickness=1, offset=5)

        # centro inferior da bounding box (pés)
        centrox = x1 + w // 2
        centroy = y2
        cv2.circle(imagem, (centrox, centroy), 5, (255, 0, 255), cv2.FILLED)

        # result = cv2.pointPolygonTest(pts, (centrox, centroy), False)
        # if result >= 0:
        #     cv2.polylines(imagem, [pts], True, (0, 255, 0), 4)

        if iden not in estados: 
            estados[iden] = {
                "pos_anterior":    None,
                "estado":          "NONE",
                "contado_entrada": False,
                "cruzou_A":        False,
                "cruzou_B":        False,
                "frames_sem_ver":  0,      # conta frames ausente (para detectar saída de campo)
            }

        pos_atual     = (centrox, centroy)
        pos_anterior  = estados[iden]["pos_anterior"]
        
        #Logica de contagem e validaçao
        # Só processa cruzamento se temos posição anterior válida
        if pos_anterior is not None:

            cruzamento_A       = cruzou_linha(pos_atual, pos_anterior, LINHA_A)
            cruzamento_B       = cruzou_linha(pos_atual, pos_anterior, LINHA_B)
            cruzamento_entrada = cruzou_linha(pos_atual, pos_anterior, LINHA_ENTRADA)

            estado_atual = estados[iden]["estado"]

            if cruzamento_A != 0:
                estados[iden]["cruzou_A"] = True
            if cruzamento_B != 0:
                estados[iden]["cruzou_B"] = True

            if estado_atual == "NONE" and (estados[iden]["cruzou_A"] or estados[iden]["cruzou_B"]):
                estados[iden]["estado"] = "CANDIDATO"
                estado_atual = "CANDIDATO"

            if cruzamento_entrada == DIRECAO_ENTRADA:
                if estado_atual in ("CANDIDATO", "NONE") and iden not in ids_ja_contados_entrada:
                    ids_ja_contados_entrada.add(iden)
                    estados[iden]["estado"] = "ENTROU"
                    estados[iden]["contado_entrada"] = True
                    total_entrou += 1

                    # --- REGISTRA ENTRADA NO BANCO (Star Schema) ---
                    if conexao_db and cursor_db:
                        try:
                            agora = datetime.datetime.now()
                            id_data = _get_id_data(cursor_db, agora.date())
                            id_hora = _get_id_hora(cursor_db, agora.hour)

                            # 1) Evento atômico em fato_fluxo
                            cursor_db.execute(
                                """
                                INSERT INTO fato_fluxo (id_data, id_hora, track_id, event_type, event_time, direction)
                                VALUES (%s, %s, %s, 'ENTRADA', %s, 'IN')
                                """,
                                (id_data, id_hora, iden, agora)
                            )

                            # 2) Abre sessão em fato_sessao
                            cursor_db.execute(
                                """
                                INSERT INTO fato_sessao (id_data, track_id, entrada_time, converteu)
                                VALUES (%s, %s, %s, TRUE)
                                RETURNING id_sessao
                                """,
                                (id_data, iden, agora)
                            )
                            id_sessao = cursor_db.fetchone()[0]
                            _sessao_aberta[iden] = id_sessao

                            conexao_db.commit()
                        except Exception as e:
                            conexao_db.rollback()

            elif estado_atual == "CANDIDATO":
                if estados[iden]["cruzou_A"] and estados[iden]["cruzou_B"]:
                    if iden not in ids_ja_contados_passou:
                        ids_ja_contados_passou.add(iden)
                        estados[iden]["estado"] = "PASSOU"
                        total_passou += 1

            if cruzamento_entrada == -DIRECAO_ENTRADA:
                if estados[iden]["estado"] not in ("SAIU",):
                    estados[iden]["estado"] = "SAIU"

                    if conexao_db and cursor_db:
                        try:
                            agora = datetime.datetime.now()
                            id_data = _get_id_data(cursor_db, agora.date())
                            id_hora = _get_id_hora(cursor_db, agora.hour)

                            cursor_db.execute(
                                """
                                INSERT INTO fato_fluxo (id_data, id_hora, track_id, event_type, event_time, direction)
                                VALUES (%s, %s, %s, 'SAIDA', %s, 'OUT')
                                """,
                                (id_data, id_hora, iden, agora)
                            )
                            if iden in _sessao_aberta:
                                cursor_db.execute(
                                    """
                                    UPDATE fato_sessao
                                    SET saida_time = %s,
                                        tempo_permanencia_seg = EXTRACT(EPOCH FROM (%s - entrada_time))::INT
                                    WHERE id_sessao = %s
                                    """,
                                    (agora, agora, _sessao_aberta[iden])
                                )
                                del _sessao_aberta[iden]

                            conexao_db.commit()
                        except Exception as e:
                            conexao_db.rollback()

        # Atualiza posição anterior e reseta contador de ausência
        estados[iden]["pos_anterior"] = pos_atual
        estados[iden]["frames_sem_ver"] = 0   # está visível ai zera contador

    
    LIMIAR_DESAPARECIDO = 60   # ~2s a 30fps {frames tolerados antes de finalizar}

    ids_neste_frame = {int(r[4]) for r in resultsTracker}

    for iden_old, est in list(estados.items()):
        if iden_old in ids_neste_frame:
            continue   # está visível neste frame, ignora

        # Incrementa ausência
        est["frames_sem_ver"] = est.get("frames_sem_ver", 0) + 1

        # Quando ausente por tempo suficiente E era CANDIDATO e foi pra PASSOU (1 linha)
        if (
            est["frames_sem_ver"] == LIMIAR_DESAPARECIDO
            and est["estado"] == "CANDIDATO"
            and iden_old not in ids_ja_contados_passou
            and iden_old not in ids_ja_contados_entrada
        ):
            ids_ja_contados_passou.add(iden_old)
            est["estado"] = "PASSOU"
            total_passou += 1

            if conexao_db and cursor_db:
                try:
                    agora = datetime.datetime.now()
                    id_data = _get_id_data(cursor_db, agora.date())
                    id_hora = _get_id_hora(cursor_db, agora.hour)
                    cursor_db.execute(
                        """
                        INSERT INTO fato_fluxo (id_data, id_hora, track_id, event_type, event_time)
                        VALUES (%s, %s, %s, 'PASSAGEM', %s)
                        """,
                        (id_data, id_hora, iden_old, agora)
                    )
                    conexao_db.commit()
                except Exception as e:
                    conexao_db.rollback()
    #painel para contagem
    cvzone.putTextRect(imagem, 
                       f'Entraram: {total_entrou}',  
                       (20, 50),
                       scale=1.8, 
                       thickness=2, 
                       offset=10, 
                       colorR=(0, 180, 0))
    cvzone.putTextRect(imagem, 
                       f'Passaram na frente: {total_passou}',  
                       (20, 100),
                       scale=1.2, 
                       thickness=2, 
                       offset=8,  
                       colorR=(50, 50, 200))

    cv2.imshow("Video", imagem)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
#limpeza
if cursor_db: cursor_db.close()
if conexao_db: conexao_db.close()

cap.release()
cv2.destroyAllWindows()
