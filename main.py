from pydoc import classname
from ultralytics import YOLO
import cv2 # para tempo real
import math
import cvzone # pra colocar a caixa de texto com o fundo
import torch
import numpy as np
from sort import *
cap = cv2.VideoCapture(0)
# cap = cv2.VideoCapture("2026-03-17 17-20-03_000000s.jpg")

cap.set(3, 1280) 
cap.set(4, 720) 

model = YOLO(r"C:\Users\pedro\runs\detect\runs\treino\mercadinho_experimento82\weights\best.pt")


tracker = Sort(max_age= 20, min_hits=3, iou_threshold=0.3)

limits = [375,650,270,620,350,560]
totalContados = []

while True:
    suucccess, imagem = cap.read()
    if not suucccess:
        break
    results = model(imagem, 
                    stream=True,
                    conf = 0.35 )  
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
            # cvzone.cornerRect(imagem,(x1,y1,w,h),l=5) # COMENTADO: Evita desenhar a caixa 2 vezes (YOLO + Tracker)
            # cv2.rectangle(imagem, (x1,y1),(x2,y2),(255,0, 255),3)
            # cv2.putText(imagem, "Objeto", (x1,y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255,0,255), 2)
            conf = math.ceil(box.conf[0] *100)/100
            currentArray =np.array([x1,y1,x2,y2,conf])
            deteccoes=np.vstack((deteccoes,currentArray))

    resultsTracker = tracker.update(deteccoes)


    pts = np.array([[limits[0], limits[1]], [limits[2], limits[3]], [limits[4], limits[5]], [limits[0], limits[5]]], np.int32)
    pts = pts.reshape((-1, 1, 2))

    cv2.polylines(imagem, [pts], True, (0, 0, 255), 4)


    for results in resultsTracker:
        x1, y1, x2, y2, id = results
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        w, h = x2 - x1, y2 - y1
        cvzone.cornerRect(imagem,(x1,y1,w,h),l=5)
        iden = int(id)
        cvzone.putTextRect(imagem, f'{iden} {conf}',(max(0, x1),max(20, y1)), scale= 1, thickness=1, offset=5)

    
        centrox, centroy = x1 + w//2, y1 + h//2 
        #circulo no centro
        cv2.circle(imagem, (centrox, centroy), 5, (255, 0, 255), cv2.FILLED)
        
        result = cv2.pointPolygonTest(pts, (centrox, centroy), False)
        
        if result >= 0:
            cv2.polylines(imagem, [pts], True, (0, 255, 0), 4)
            
            if iden not in totalContados:
                totalContados.append(iden)
            
    cvzone.putTextRect(imagem, f'Total: {len(totalContados)}',(50,50), scale= 1.5, thickness=2, offset=10)

    cv2.imshow("Video", imagem)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
