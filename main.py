from pydoc import classname
from ultralytics import YOLO
import cv2 # para tempo real
import math
import cvzone # pra colocar a caixa de texto com o fundo
import torch
cap = cv2.VideoCapture(0)
cap.set(3, 1280) 
cap.set(4, 720) 

model = YOLO("../yOLO-Weights/yolov8m.pt")


while True:
    suucccess, imagem = cap.read()
    results = model(imagem, 
                    stream=True,
                    classes = 0,
                    conf = 0.15 )
    

    for i in results:
        boxes = i.boxes

        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0]

            x1= int(x1)
            y1= int(y1)
            x2= int(x2)
            y2= int(y2)

            cv2.rectangle(imagem, (x1,y1),(x2,y2),(255,0, 255),3)
            cv2.putText(imagem, "Objeto", (x1,y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255,0,255), 2)

            conf = math.ceil(box.conf[0] *100)/100
            print(conf)
            cls = int(box.cls[0])
            classNames = model.names
            nome_Classe = classNames[cls]

            cvzone.putTextRect(imagem, f'{nome_Classe} {conf}',(max(0, x1),max(20, y1)))

    cv2.imshow("Video", imagem)
    cv2.waitKey(1)



