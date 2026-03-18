from pydoc import classname
from ultralytics import YOLO
import cv2 # para tempo real
import math
import cvzone # pra colocar a caixa de texto com o fundo
import torch
from sort import *
cap = cv2.VideoCapture(0)
# cap = cv2.VideoCapture("Videos/2026-03-17 17-20-03.mkv")

cap.set(3, 1280) 
cap.set(4, 720) 

model = YOLO(r"C:\Users\pedro\runs\detect\runs\treino\mercadinho_v1\weights\best.pt")


tracker = Sort(max_age= 20, min_hits=3, iou_threshold=0.3)

while True:
    suucccess, imagem = cap.read()
    
    if not suucccess:
        break
        
    results = model(imagem, 
                    stream=True,
                    conf = 0.25 )  # confianca minima para evitar detecoes fantasmas
    
    deteccoes = np.empty((0,5))
    for i in results:
        boxes = i.boxes

        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0]

            x1= int(x1)
            y1= int(y1)
            x2= int(x2)
            y2= int(y2)
            w, h = x2 - x1, y2 - y1
            cvzone.cornerRect(imagem,(x1,y1,w,h),l=5)
            # cv2.rectangle(imagem, (x1,y1),(x2,y2),(255,0, 255),3)
            # cv2.putText(imagem, "Objeto", (x1,y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255,0,255), 2)

            conf = math.ceil(box.conf[0] *100)/100
            
            # Como o modelo tem duas classes ('0' e 'Pessoas'), 
            # forçamos o nome visual para ficar padronizado na tela
            currentArray =np.array([x1,y1,x2,y2,conf])
            deteccoes=np.vstack((deteccoes,currentArray))

    resultsTracker = tracker.update(deteccoes)

    
    for results in resultsTracker:
        x1, y1, x2, y2, id = results
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        w, h = x2 - x1, y2 - y1
        cvzone.cornerRect(imagem,(x1,y1,w,h),l=5)
        iden = int(id)
        cvzone.putTextRect(imagem, f'{iden} {conf}',(max(0, x1),max(20, y1)), scale= 1, thickness=1, offset=5)

    
    cv2.imshow("Video", imagem)
    
    # 1 milissegundo de atraso, permite o vídeo rodar fluidamente.
    # Pressione a tecla 'q' para sair.
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

