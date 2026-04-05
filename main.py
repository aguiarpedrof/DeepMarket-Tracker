import time
from ultralytics import YOLO
import cv2
import math
import cvzone
import torch
import numpy as np

cap = cv2.VideoCapture(0)
# cap = cv2.VideoCapture("Video teste.mp4")

cap.set(3, 1280)
cap.set(4, 720)

model = YOLO(r"C:\Users\pedro\runs\detect\runs\treino\mercadinho_experimento89\weights\best.pt")

DIRECAO_ENTRADA = 1   # troque para -1 se estiver contando no sentido errado

LINHA_A       = None
LINHA_ENTRADA = None
LINHA_B       = None

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
            linha_idx = n // 2
            ponto_idx = n % 2 + 1
            cor_atual, nome_atual = _CORES_LINHAS[linha_idx]
            msg = f"Clique o {ponto_idx}o ponto da {nome_atual}  [{n}/6]"
        else:
            msg = "6 pontos definidos ENTER=confirmar R=desfazer"
            cor_atual = (255, 255, 255)

        cv2.putText(temp, msg, (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 0), 4)
        cv2.putText(temp, msg, (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)

        # Desenha pontos e linhas já definidos
        for i, pt in enumerate(_pontos_interativos):
            cor, _ = _CORES_LINHAS[i // 2]
            cv2.circle(temp, pt, 8, cor, -1)
            cv2.circle(temp, pt, 9, (0, 0, 0), 1)

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
            print(f"  Ponto removido: {removido}  ({len(_pontos_interativos)}/6)")

        elif key in [13, ord('\r'), ord('\n')]:  # ENTER
            if len(_pontos_interativos) == 6:
                break
            else:
                print(f"  Ainda faltam {6 - len(_pontos_interativos)} ponto(s)!")

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
        return 0
        # p1 e p2 no mesmo lado = cruzamento fora do segmento


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
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

pTime = 0

while True:
    suucccess, imagem = cap.read()
    if not suucccess:
        break

    results = model.track(imagem,
                          persist=True,
                          conf=0.30,
                          tracker="bytetrack.yaml")

    cv2.line(imagem, LINHA_A[0],       LINHA_A[1],       (255, 165, 0), 3)
    cv2.line(imagem, LINHA_ENTRADA[0], LINHA_ENTRADA[1], (0, 171, 6),   3)
    cv2.line(imagem, LINHA_B[0],       LINHA_B[1],       (0, 0, 255),   3)

    cv2.putText(imagem, "A",       LINHA_A[0],       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 165, 0), 2)
    cv2.putText(imagem, "Entrada", LINHA_ENTRADA[0], cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0),   2)
    cv2.putText(imagem, "B",       LINHA_B[0],       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255),   2)

    # Extrai detecções com IDs do ByteTrack
    resultsTracker = []
    for r in results:
        if r.boxes.id is None:
            continue
        for box, tid, conf in zip(r.boxes.xyxy, r.boxes.id, r.boxes.conf):
            x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
            resultsTracker.append((x1, y1, x2, y2, int(tid), float(conf)))

    for (x1, y1, x2, y2, iden, conf) in resultsTracker:
        w, h = x2 - x1, y2 - y1

        cvzone.cornerRect(imagem, (x1, y1, w, h), l=15, colorC=(255, 255, 255), colorR=(66, 124, 168))

        estado_atual = estados.get(iden, {}).get("estado", "NONE")
        # cvzone.putTextRect(imagem, f'{iden} [{estado_atual}]',
        #                    (max(0, x1), max(20, y1)), scale=0.8, thickness=1, offset=5, colorR=(77, 77, 77))

        cvzone.putTextRect(imagem, f'[{estado_atual}] {conf:.0%}',
                           (max(0, x1), max(20, y1)), scale=1, thickness=1, offset=5, colorR=(77, 77, 77))

        centrox = x1 + w // 2
        centroy = y2
        cv2.circle(imagem, (centrox, centroy), 5, (255, 255, 255), cv2.FILLED)

        if iden not in estados:
            estados[iden] = {
                "pos_anterior":    None,
                "estado":          "Sem Classificacao",
                "contado_entrada": False,
                "cruzou_A":        False,
                "cruzou_B":        False,
                "frames_sem_ver":  0,
            }

        pos_atual    = (centrox, centroy)
        pos_anterior = estados[iden]["pos_anterior"]

        if pos_anterior is not None:

            cruzamento_A       = cruzou_linha(pos_atual, pos_anterior, LINHA_A)
            cruzamento_B       = cruzou_linha(pos_atual, pos_anterior, LINHA_B)
            cruzamento_entrada = cruzou_linha(pos_atual, pos_anterior, LINHA_ENTRADA)

            estado_atual = estados[iden]["estado"]

            if cruzamento_A != 0:
                estados[iden]["cruzou_A"] = True
            if cruzamento_B != 0:
                estados[iden]["cruzou_B"] = True

            if estado_atual == "Sem Classificacao" and (estados[iden]["cruzou_A"] or estados[iden]["cruzou_B"]):
                estados[iden]["estado"] = "CANDIDATO"
                estado_atual = "CANDIDATO"

            if cruzamento_entrada == DIRECAO_ENTRADA:
                if estado_atual in ("CANDIDATO", "Sem Classificacao") and iden not in ids_ja_contados_entrada:
                    ids_ja_contados_entrada.add(iden)
                    estados[iden]["estado"] = "ENTROU"
                    estados[iden]["contado_entrada"] = True
                    total_entrou += 1
                    print(f"[ENTRADA] ID {iden} | Total: {total_entrou}")

            elif estado_atual == "CANDIDATO":
                if estados[iden]["cruzou_A"] and estados[iden]["cruzou_B"]:
                    if iden not in ids_ja_contados_passou:
                        ids_ja_contados_passou.add(iden)
                        estados[iden]["estado"] = "PASSOU"
                        total_passou += 1
                        print(f"[PASSOU] ID {iden} | Total: {total_passou}")

            if cruzamento_entrada == -DIRECAO_ENTRADA:
                if estados[iden]["estado"] not in ("SAIU",):
                    estados[iden]["estado"] = "SAIU"

        estados[iden]["pos_anterior"] = pos_atual
        estados[iden]["frames_sem_ver"] = 0


    LIMIAR_DESAPARECIDO = 60   # ~2s a 30fps

    ids_neste_frame = {iden for (_, _, _, _, iden, _conf) in resultsTracker}

    for iden_old, est in list(estados.items()):
        if iden_old in ids_neste_frame:
            continue

        est["frames_sem_ver"] = est.get("frames_sem_ver", 0) + 1

        if (
            est["frames_sem_ver"] == LIMIAR_DESAPARECIDO
            and est["estado"] == "CANDIDATO"
            and iden_old not in ids_ja_contados_passou
            and iden_old not in ids_ja_contados_entrada
        ):
            ids_ja_contados_passou.add(iden_old)
            est["estado"] = "PASSOU"
            total_passou += 1
            print(f"[PASSOU-timeout] ID {iden_old} | Total: {total_passou}")

    cTime = time.time()
    fps = 1 / (cTime - pTime) if pTime > 0 else 0
    pTime = cTime

    cvzone.putTextRect(imagem,
                       f'Entraram: {total_entrou}  |  Passaram: {total_passou}  |  FPS: {int(fps)}',
                       (20, 50),
                       scale=1.5,
                       thickness=2,
                       offset=10,
                       colorR=(61, 61, 61))

    cv2.imshow("Video", imagem)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
