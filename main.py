import argparse
import time
from typing import List, Tuple, Any, Dict, Set
from ultralytics import YOLO
import cv2
import cvzone
import os

# --- ARGUMENTOS DE LINHA DE COMANDO ---
parser = argparse.ArgumentParser(description="DeepMarket Tracker - Contagem de pessoas com YOLOv8")
parser.add_argument('--model', type=str, default='Yolo-Weights/best.pt', help='Caminho para o modelo YOLOv8 treinado (.pt)')
args = parser.parse_args()

# --- CONFIGURAÇÕES ---
CAMERA_ID = 0
CAP_WIDTH = 1280
CAP_HEIGHT = 720
MODEL_PATH = args.model
CONFIDENCE_THRESHOLD = 0.30
TRACKER_TYPE = "bytetrack.yaml"
LIMIAR_DESAPARECIDO = 60   # ~2s a 30fps
DIRECAO_ENTRADA = 1        # Troque para -1 se estiver contando no sentido inverso

_pontos_interativos = []   
_CORES_LINHAS = [
    ((255, 165, 0), "Linha A (antes da entrada)"),
    ((0, 255, 0),   "Entrada (mercadinho)"),
    ((0, 0, 255),   "Linha B (passou reto)"),
]

def _mouse_callback_unico(event: int, x: int, y: int, flags: int, param: Any) -> None:
    if event == cv2.EVENT_LBUTTONDOWN and len(_pontos_interativos) < 6:
        _pontos_interativos.append((x, y))

def _definir_linhas_interativo(frame_base: Any) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]], List[Tuple[int, int]]]:

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

def lado_da_linha(ponto: Tuple[int, int], p1: Tuple[int, int], p2: Tuple[int, int]) -> int:

    x,  y  = ponto
    x1, y1 = p1
    x2, y2 = p2
    return (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)

def cruzou_linha(pos_atual: Tuple[int, int], pos_anterior: Tuple[int, int], linha: List[Tuple[int, int]]) -> int:
    """
    Verifica se o deslocamento entre pos_anterior e pos_atual intercepta o segmento de reta 'linha'.
    Retorna 1 ou -1 dependendo da direção do cruzamento, e 0 se não cruzou.
    """
    p1, p2 = linha
    lado_atual    = lado_da_linha(pos_atual,    p1, p2)
    lado_anterior = lado_da_linha(pos_anterior, p1, p2)

    # Olha se houve mudança de lado em relação à linha INFINITA
    if lado_atual * lado_anterior >= 0:
        return 0

    lado_p1 = lado_da_linha(p1, pos_anterior, pos_atual)
    lado_p2 = lado_da_linha(p2, pos_anterior, pos_atual)
    if lado_p1 * lado_p2 > 0:
        return 0
        # p1 e p2 no mesmo lado = cruzamento fora do segmento

    return 1 if lado_anterior > 0 else -1


class RetailFlowTracker:
    """
    Gerencia o rastreamento de pedestres e a máquina de estados para contagem inteligente.
    Responsável por classificar e gerenciar a transição de estados dos pedestres:
    NONE -> Sem Classificacao -> CANDIDATO -> ENTROU / PASSOU -> SAIU.
    """
    def __init__(self, limiar_desaparecido: int = 60, direcao_entrada: int = 1):
        self.limiar_desaparecido = limiar_desaparecido
        self.direcao_entrada = direcao_entrada
        
        self.estados: Dict[int, Dict[str, Any]] = {}
        
        self.total_entrou: int = 0
        self.total_passou: int = 0
        
        self.ids_ja_contados_entrada: Set[int] = set()
        self.ids_ja_contados_passou: Set[int] = set()

    def update_states(self, results_tracker: List[Tuple[int, int, int, int, int, float]], 
                      linha_a: List[Tuple[int, int]], 
                      linha_entrada: List[Tuple[int, int]], 
                      linha_b: List[Tuple[int, int]]) -> None:
        """
        Atualiza o estado de todos os rastreamentos ativos no frame atual e 
        executa as transições da máquina de estados com tratamento geométrico.
        """
        for (x1, y1, x2, y2, iden, conf) in results_tracker:
            w, h = x2 - x1, y2 - y1
            centrox = x1 + w // 2
            centroy = y2  
            pos_atual = (centrox, centroy)

            if iden not in self.estados:
                self.estados[iden] = {
                    "pos_anterior": None,
                    "estado": "Sem Classificacao",
                    "contado_entrada": False,
                    "cruzou_A": False,
                    "cruzou_B": False,
                    "frames_sem_ver": 0,
                }

            pos_anterior = self.estados[iden]["pos_anterior"]
            self.estados[iden]["frames_sem_ver"] = 0 
            if pos_anterior is not None:
                cruzamento_a = cruzou_linha(pos_atual, pos_anterior, linha_a)
                cruzamento_b = cruzou_linha(pos_atual, pos_anterior, linha_b)
                cruzamento_entrada = cruzou_linha(pos_atual, pos_anterior, linha_entrada)

                if cruzamento_a != 0:
                    self.estados[iden]["cruzou_A"] = True
                if cruzamento_b != 0:
                    self.estados[iden]["cruzou_B"] = True

                estado_atual = self.estados[iden]["estado"]

                #Sem Classificacao -> CANDIDATO
                if estado_atual == "Sem Classificacao" and (self.estados[iden]["cruzou_A"] or self.estados[iden]["cruzou_B"]):
                    self.estados[iden]["estado"] = "CANDIDATO"
                    estado_atual = "CANDIDATO"

                #contagem de ENTRADA
                if cruzamento_entrada == self.direcao_entrada:
                    if estado_atual in ("CANDIDATO", "Sem Classificacao") and iden not in self.ids_ja_contados_entrada:
                        self.ids_ja_contados_entrada.add(iden)
                        self.estados[iden]["estado"] = "ENTROU"
                        self.estados[iden]["contado_entrada"] = True
                        self.total_entrou += 1
                        print(f"[ENTRADA] ID {iden} | Total: {self.total_entrou}")

                # PASSOU (passou reto pelas duas linhas limites)
                elif estado_atual == "CANDIDATO":
                    if self.estados[iden]["cruzou_A"] and self.estados[iden]["cruzou_B"]:
                        if iden not in self.ids_ja_contados_passou:
                            self.ids_ja_contados_passou.add(iden)
                            self.estados[iden]["estado"] = "PASSOU"
                            self.total_passou += 1
                            print(f"[PASSOU] ID {iden} | Total: {self.total_passou}")

                # SAIU
                if cruzamento_entrada == -self.direcao_entrada:
                    if self.estados[iden]["estado"] != "SAIU":
                        self.estados[iden]["estado"] = "SAIU"

            self.estados[iden]["pos_anterior"] = pos_atual

    def handle_timeouts(self, ids_neste_frame: Set[int]) -> None:
        """
        Incrementa contadores de desaparecimento para IDs não detectados no frame atual
        e aplica o timeout para candidatos que passaram sem cruzar a entrada.
        """
        for iden_old, est in list(self.estados.items()):
            if iden_old in ids_neste_frame:
                continue

            est["frames_sem_ver"] = est.get("frames_sem_ver", 0) + 1

            # Se some da visão como candidato, assume "PASSOU"
            # após o limite de tolerância 
            if (
                est["frames_sem_ver"] == self.limiar_desaparecido
                and est["estado"] == "CANDIDATO"
                and iden_old not in self.ids_ja_contados_passou
                and iden_old not in self.ids_ja_contados_entrada
            ):
                self.ids_ja_contados_passou.add(iden_old)
                est["estado"] = "PASSOU"
                self.total_passou += 1
                print(f"[PASSOU-timeout] ID {iden_old} | Total: {self.total_passou}")

    def get_counts(self) -> Tuple[int, int]:
        """Retorna a contagem acumulada atualizada de (total_entrou, total_passou)."""
        return self.total_entrou, self.total_passou


def main():
    cap = cv2.VideoCapture(CAMERA_ID)
    # cap = cv2.VideoCapture("Video teste.mp4")

    cap.set(3, CAP_WIDTH)
    cap.set(4, CAP_HEIGHT)

    # Inicializa modelo YOLO com verificação amigável e tolerância a caminhos de ambiente
    if not os.path.exists(MODEL_PATH):
        model = YOLO("yolov8s.pt")
    else:
        model = YOLO(MODEL_PATH)

    ret, primeiro_frame = cap.read()
    if not ret:
        cap.release()
        exit()

    linha_a, linha_entrada, linha_b = _definir_linhas_interativo(primeiro_frame)
    print(f"\n✔ Calibração concluída:")
    print(f"  LINHA_A       = {linha_a}")
    print(f"  LINHA_ENTRADA = {linha_entrada}")
    print(f"  LINHA_B       = {linha_b}\n")
    
    # Reinicia reprodução de vídeo para o frame 0 (relevante ao rodar arquivos gravados)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    # Instancia o controlador encapsulado da máquina de estados
    tracker_manager = RetailFlowTracker(
        limiar_desaparecido=LIMIAR_DESAPARECIDO,
        direcao_entrada=DIRECAO_ENTRADA
    )

    p_time = 0

    while True:
        success, imagem = cap.read()
        if not success:
            break

        # Executa inferência e tracking contínuo
        results = model.track(
            imagem,
            persist=True,
            conf=CONFIDENCE_THRESHOLD,
            tracker=TRACKER_TYPE
        )

        # Desenha na tela as linhas demarcadoras
        cv2.line(imagem, linha_a[0],       linha_a[1],       (255, 165, 0), 3)
        cv2.line(imagem, linha_entrada[0], linha_entrada[1], (0, 171, 6),   3)
        cv2.line(imagem, linha_b[0],       linha_b[1],       (0, 0, 255),   3)

        cv2.putText(imagem, "A",       linha_a[0],       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 165, 0), 2)
        cv2.putText(imagem, "Entrada", linha_entrada[0], cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0),   2)
        cv2.putText(imagem, "B",       linha_b[0],       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255),   2)

        # Extrai detecções com IDs associados do tracker ByteTrack
        results_tracker = []
        for r in results:
            if r.boxes.id is None:
                continue
            for box, tid, conf in zip(r.boxes.xyxy, r.boxes.id, r.boxes.conf):
                x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
                results_tracker.append((x1, y1, x2, y2, int(tid), float(conf)))

        # Atualiza a Máquina de Estados Geométrica
        tracker_manager.update_states(results_tracker, linha_a, linha_entrada, linha_b)

        # Renderiza visualmente as caixas delimitadoras e os rótulos de estado
        for (x1, y1, x2, y2, iden, conf) in results_tracker:
            w, h = x2 - x1, y2 - y1

            cvzone.cornerRect(imagem, (x1, y1, w, h), l=15, colorC=(255, 255, 255), colorR=(66, 124, 168))

            estado_atual = tracker_manager.estados.get(iden, {}).get("estado", "NONE")
            cvzone.putTextRect(
                imagem, 
                f'[{estado_atual}] {conf:.0%}',
                (max(0, x1), max(20, y1)), 
                scale=1, 
                thickness=1, 
                offset=5, 
                colorR=(77, 77, 77)
            )

            centrox = x1 + w // 2
            centroy = y2
            cv2.circle(imagem, (centrox, centroy), 5, (255, 255, 255), cv2.FILLED)

        # Trata os timeouts de IDs que saíram da visão
        ids_neste_frame = {iden for (_, _, _, _, iden, _) in results_tracker}
        tracker_manager.handle_timeouts(ids_neste_frame)

        # Calcula a taxa de quadros por segundo (FPS)
        c_time = time.time()
        fps = 1 / (c_time - p_time) if p_time > 0 else 0
        p_time = c_time

        # Plota os contadores gerais na tela
        total_entrou, total_passou = tracker_manager.get_counts()
        cvzone.putTextRect(
            imagem,
            f'Entraram: {total_entrou}  |  Passaram: {total_passou}  |  FPS: {int(fps)}',
            (20, 50),
            scale=1.5,
            thickness=2,
            offset=10,
            colorR=(61, 61, 61)
        )

        cv2.imshow("Video", imagem)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

