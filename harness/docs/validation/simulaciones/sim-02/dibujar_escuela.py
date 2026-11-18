"""TEMPORAL (T-01): dibuja la escuela con el modelo Python de epc_arch; no existe via soportada."""
import sys
from pathlib import Path
from epc_arch.model import Architecture, Wall, Opening, Room, Level
from epc_arch.drawing import build_drawing, load_style
from epc_arch.export.export_dxf import to_dxf
from epc_arch.sheets import iram_template
T=200.0; W,H=30000.0,12000.0; Y=6000.0
XN=[0,6000,14000,22000,27000,30000]; XS=[0,8000,16000,24000,30000]
def walls():
    w=[]
    def add(i,a,b): w.append(Wall(i,a,b,T,1.0,"authored"))
    add("W-S",(0,0),(W,0)); add("W-E",(W,0),(W,H)); add("W-N",(W,H),(0,H)); add("W-O",(0,H),(0,0)); add("W-I",(0,Y),(W,Y))
    for i,x in enumerate(XS[1:-1]): add(f"W-VS{i}",(x,0),(x,Y))
    for i,x in enumerate(XN[1:-1]): add(f"W-VN{i}",(x,Y),(x,H))
    return w
def door(i,wall,at,ang,wd,h,s): return Opening(i,"door",at,wd,ang,wall,1.0,"authored",h,s)
def win(i,wall,at,ang,wd): return Opening(i,"window",at,wd,ang,wall,1.0,"authored")
def openings():
    o=[door("D1","W-N",(3000,H),0,1200,(2400,H),(2400,H-1200)),
       door("D2","W-I",(4000,Y),0,900,(3550,Y),(3550,Y-900)), door("D3","W-I",(12000,Y),0,900,(11550,Y),(11550,Y-900)),
       door("D4","W-I",(20000,Y),0,900,(19550,Y),(19550,Y-900)), door("D5","W-I",(27000,Y),0,900,(26550,Y),(26550,Y-900)),
       door("D6","W-I",(10000,Y),0,900,(9550,Y),(9550,Y+900)), door("D7","W-I",(18000,Y),0,900,(17550,Y),(17550,Y+900)),
       door("D8","W-I",(24500,Y),0,900,(24050,Y),(24050,Y+900)), door("D9","W-I",(28500,Y),0,900,(28050,Y),(28050,Y+900))]
    for i,x in enumerate((4000,12000,20000)): o.append(win(f"V{i+1}","W-S",(x,0),0,2400))
    o.append(win("V4","W-O",(0,3000),90,1800)); o.append(win("V5","W-O",(0,9000),90,1800))
    o.append(win("V6","W-N",(10000,H),0,2400)); o.append(win("V7","W-N",(18000,H),0,2400))
    return o
B={"A":(0,0,8000,6000,"AU-01","Aula 1","CLASSROOM"),"B":(8000,0,16000,6000,"AU-02","Aula 2","CLASSROOM"),"C":(16000,0,24000,6000,"AU-03","Aula 3","CLASSROOM"),
   "D":(24000,0,30000,6000,"SE-01","Sala de tableros","ELECTRICAL_ROOM"),
   "E":(0,6000,6000,12000,"DI-01","Direccion","OFFICE"),"F":(6000,6000,14000,12000,"BI-01","Biblioteca","LIBRARY"),
   "G":(14000,6000,22000,12000,"CO-01","Comedor","DINING"),"H":(22000,6000,27000,12000,"CC-01","Cocina","KITCHEN"),"I":(27000,6000,30000,12000,"SA-01","Sanitarios","BATHROOM")}
def rooms():
    out=[]
    for k,(x0,y0,x1,y1,code,name,key) in B.items():
        r=(x0+100,y0+100,x1-100,y1-100); a=(r[2]-r[0])*(r[3]-r[1])
        out.append(Room(code,a,a/1e6,((r[0]+r[2])/2,(r[1]+r[3])/2),[r],name,key,code))
    return out
out=Path(sys.argv[1]); out.mkdir(parents=True,exist_ok=True)
style=load_style(); tpl=iram_template("A1")
arch=Architecture(source="PB.dxf",size=(W,H),units_per_metre=1000.0,scale_hint=None,wall_thickness=T,walls=walls(),openings=openings(),rooms=rooms(),level=Level("Planta Baja",0,"text","GROUND_FLOOR"))
d=build_drawing(arch,style=style,sheet="A1",template=tpl,document="PB.dxf",fields={"denominacion":"PLANTA BAJA"})
(out/"PB.dxf").write_text(to_dxf(d,style),encoding="utf-8"); print("ok",len(arch.rooms))
