"""TEMPORAL (T-01): dibuja el taller con el modelo Python de epc_arch; no existe via soportada."""
import sys
from pathlib import Path
from epc_arch.model import Architecture, Wall, Opening, Room, Level
from epc_arch.drawing import build_drawing, load_style
from epc_arch.export.export_dxf import to_dxf
from epc_arch.sheets import iram_template
T=200.0; W,H=36000.0,20000.0; Y=14000.0
def walls():
    w=[]
    def add(i,a,b): w.append(Wall(i,a,b,T,1.0,"authored"))
    add("W-S",(0,0),(W,0)); add("W-E",(W,0),(W,H)); add("W-N",(W,H),(0,H)); add("W-O",(0,H),(0,0))
    add("W-I",(0,Y),(W,Y)); add("W-V1",(26000,0),(26000,Y)); add("W-I2",(26000,7000),(W,7000))
    for i,x in enumerate((8000,14000,18000,28000)): add(f"W-VN{i}",(x,Y),(x,H))
    return w
def door(i,wall,at,ang,wd,h,s): return Opening(i,"door",at,wd,ang,wall,1.0,"authored",h,s)
def win(i,wall,at,ang,wd): return Opening(i,"window",at,wd,ang,wall,1.0,"authored")
def openings():
    o=[door("D1","W-S",(13000,0),0,4000,(11000,0),(11000,4000)),
       door("D2","W-V1",(26000,10500),90,1200,(26000,9900),(27200,9900)),
       door("D3","W-V1",(26000,3500),90,1200,(26000,2900),(27200,2900)),
       door("D4","W-I2",(31000,7000),0,900,(30550,7000),(30550,6100)),
       door("D5","W-I",(4000,Y),0,900,(3550,Y),(3550,Y-900)), door("D6","W-I",(11000,Y),0,900,(10550,Y),(10550,Y-900)),
       door("D7","W-I",(16000,Y),0,900,(15550,Y),(15550,Y-900)), door("D8","W-I",(23000,Y),0,1200,(22400,Y),(22400,Y-1200)),
       door("D9","W-I",(32000,Y),0,1200,(31400,Y),(31400,Y-1200))]
    for i,x in enumerate((5000,13000,21000)): o.append(win(f"V{i+1}","W-S",(x,0),0,2400))
    o.append(win("V4","W-O",(0,4000),90,1800)); o.append(win("V5","W-O",(0,10000),90,1800))
    o.append(win("V6","W-N",(4000,H),0,1800)); o.append(win("V7","W-N",(11000,H),0,1800))
    return o
B={"A":(0,0,26000,Y,"NP-01","Nave de produccion","FACTORY"),"B":(26000,0,36000,7000,"CC-01","Sala de compresores","MACHINE_ROOM"),
   "C":(26000,7000,36000,Y,"ST-01","Sala de tableros","ELECTRICAL_ROOM"),
   "D":(0,Y,8000,H,"OF-01","Oficina tecnica","OFFICE"),"E":(8000,Y,14000,H,"VE-01","Vestuarios","LOCKER_ROOM"),
   "F":(14000,Y,18000,H,"SA-01","Sanitarios","BATHROOM"),"G":(18000,Y,28000,H,"DE-01","Deposito","STORAGE"),
   "H":(28000,Y,36000,H,"TM-01","Taller de mantenimiento","WORKSHOP")}
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
