"""Generate 20 test images for benchmarking"""
import os, sys
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image, ImageDraw

OUT = "static/uploads/experiment"
os.makedirs(OUT, exist_ok=True)

S = 512  # image size

def save(name, draw_fn):
    img = Image.new("RGBA", (S, S), (255,255,255,0))
    draw = ImageDraw.Draw(img)
    draw_fn(draw)
    path = os.path.join(OUT, f"{name}.png")
    img.save(path)
    print(f"  {path}")
    return path

# === HÌNH HỌC (Geometry) ===
def hinh_tron(d):
    d.ellipse([56,56,456,456], fill=(60,120,220,255))
def hinh_vuong(d):
    d.rectangle([56,56,456,456], fill=(220,80,60,255))
def hinh_tamgiac(d):
    d.polygon([(256,56),(56,456),(456,456)], fill=(60,200,80,255))
def hinh_sao(d):
    pts = []
    for i in range(10):
        r = 200 if i%2==0 else 80
        a = i*36 - 90
        pts.append((256+r*__import__('math').cos(a*3.14159/180), 256+r*__import__('math').sin(a*3.14159/180)))
    d.polygon(pts, fill=(255,200,50,255))
def hinh_lucgiac(d):
    pts = [(256+180*__import__('math').cos(i*60*3.14159/180), 256+180*__import__('math').sin(i*60*3.14159/180)) for i in range(6)]
    d.polygon(pts, fill=(140,80,220,255))

# === ĐỒ VẬT (Objects) ===
def qua_tao(d):
    d.ellipse([156,200,356,400], fill=(200,50,50,255))
    d.rectangle([246,140,266,200], fill=(80,160,60,255))
    d.ellipse([236,150,276,175], fill=(60,140,40,255))
def qua_chuoi(d):
    d.arc([100,180,300,380], 200, 340, fill=(240,220,50,255), width=40)
    d.arc([180,160,350,340], 200, 340, fill=(240,220,50,255), width=35)
def trai_cam(d):
    d.ellipse([156,180,356,380], fill=(255,165,0,255))
    d.ellipse([240,150,272,195], fill=(50,180,50,255))
    for _ in range(15):
        x,y = __import__('random').randint(180,332), __import__('random').randint(200,360)
        d.point((x,y), fill=(255,200,100,200))
def cai_coc(d):
    d.polygon([(180,100),(332,100),(352,420),(160,420)], fill=(100,180,255,220))
    d.ellipse([155,410,357,440], fill=(100,180,255,220))
def chai_nuoc(d):
    d.rectangle([220,80,292,160], fill=(60,160,80,230))
    d.rectangle([200,160,312,400], fill=(60,160,80,230))
    d.rectangle([210,400,302,420], fill=(60,160,80,230))

# === HỌC TẬP (Study) ===
def quyen_sach(d):
    d.rectangle([150,80,370,420], fill=(200,50,50,255))
    d.rectangle([160,90,360,410], fill=(255,240,200,255))
    d.line([160,100,360,100], fill=(100,100,100,255), width=2)
    d.line([160,120,320,120], fill=(100,100,100,255), width=2)
    d.line([160,140,280,140], fill=(100,100,100,255), width=2)
def cay_viet(d):
    d.rectangle([248,80,256,380], fill=(220,200,100,255))
    d.polygon([(248,80),(248,120),(220,120),(252,60),(284,120),(260,120),(260,80)], fill=(50,50,50,255))
    d.ellipse([244,50,260,66], fill=(230,220,180,255))
def thuoc_ke(d):
    d.rectangle([60,220,460,260], fill=(255,220,100,255))
    for i in range(10):
        x = 80 + i*40
        d.line([(x,220),(x,240)], fill=(50,50,50,255), width=2)
    d.text((200,225), "cm", fill=(50,50,50,255))
def qua_dia(d):
    d.ellipse([130,100,382,352], fill=(60,140,220,255))
    d.ellipse([200,200,312,312], fill=(40,100,180,255))
    d.arc([130,100,382,352], 0, 360, fill=(60,200,100,255), width=8)
    d.rectangle([240,80,272,130], fill=(150,100,50,255))
    d.polygon([(256,130),(240,170),(272,170)], fill=(150,100,50,255))

# === KHOA HỌC (Science) ===
def binh_cau(d):
    d.polygon([(200,80),(312,80),(332,300),(180,300)], fill=(200,220,255,200))
    d.ellipse([175,295,337,330], fill=(200,220,255,200))
    d.rectangle([170,80,342,100], fill=(180,180,180,255))
    d.rectangle([230,300,282,420], fill=(200,220,255,200))
def banh_rang(d):
    cx,cy,r1,r2 = 256,256,180,140
    pts = []
    for i in range(36):
        r = r1 if i%2==0 else r2
        a = i*10
        pts.append((cx+r*__import__('math').cos(a*3.14159/180), cy+r*__import__('math').sin(a*3.14159/180)))
    d.polygon(pts, fill=(180,180,190,255))
    d.ellipse([216,216,296,296], fill=(255,255,255,255))
    d.ellipse([236,236,276,276], fill=(180,180,190,255))
def mach_dien(d):
    d.rectangle([60,200,200,220], fill=(50,50,50,255))
    d.rectangle([200,100,220,320], fill=(50,50,50,255))
    d.rectangle([220,100,380,120], fill=(50,50,50,255))
    d.ellipse([180,80,240,140], fill=(255,220,50,255))
    d.ellipse([140,280,280,340], fill=(200,200,255,255))
def phan_tu(d):
    d.ellipse([130,130,210,210], fill=(255,80,80,200))
    d.ellipse([302,130,382,210], fill=(80,80,255,200))
    d.ellipse([216,280,296,360], fill=(80,255,80,200))
    d.rectangle([210,166,302,174], fill=(100,100,100,200))
    d.rectangle([246,210,266,280], fill=(100,100,100,200))

# === TỰ NHIÊN (Nature) ===
def chiec_la(d):
    pts = [(256,60)]
    for i in range(1,20):
        t = i/19
        x = 256 + (200*__import__('math').sin(t*3.14159))*(1-2*t)
        y = 60 + t*360
        pts.append((x,y))
    d.polygon(pts, fill=(60,200,80,255))
    d.line([(256,60),(256,420)], fill=(40,120,40,255), width=3)
def bong_hoa(d):
    colors = [(255,100,150),(255,150,50),(255,255,100),(255,100,255),(100,150,255)]
    for i,c in enumerate(colors):
        a = i*72 - 90
        cx = 256 + 80*__import__('math').cos(a*3.14159/180)
        cy = 256 + 80*__import__('math').sin(a*3.14159/180)
        d.ellipse([cx-40,cy-40,cx+40,cy+40], fill=c+(230,))
    d.ellipse([226,226,286,286], fill=(255,255,50,255))
    d.rectangle([250,286,262,420], fill=(60,160,40,255))

# Generate all
tests = [
    ("hinh_tron", hinh_tron, "geometry"),
    ("hinh_vuong", hinh_vuong, "geometry"),
    ("hinh_tamgiac", hinh_tamgiac, "geometry"),
    ("hinh_sao", hinh_sao, "geometry"),
    ("hinh_lucgiac", hinh_lucgiac, "geometry"),
    ("qua_tao", qua_tao, "botany"),
    ("qua_chuoi", qua_chuoi, "botany"),
    ("trai_cam", trai_cam, "botany"),
    ("cai_coc", cai_coc, "lab"),
    ("chai_nuoc", chai_nuoc, "lab"),
    ("quyen_sach", quyen_sach, "tools"),
    ("cay_viet", cay_viet, "tools"),
    ("thuoc_ke", thuoc_ke, "tools"),
    ("qua_dia", qua_dia, "earth"),
    ("binh_cau", binh_cau, "chemistry"),
    ("banh_rang", banh_rang, "physics"),
    ("mach_dien", mach_dien, "physics"),
    ("phan_tu", phan_tu, "chemistry"),
    ("chiec_la", chiec_la, "botany"),
    ("bong_hoa", bong_hoa, "botany"),
]

print("Generating 20 test images...")
paths = []
for name, fn, cat in tests:
    p = save(name, fn)
    paths.append((name, cat, p))
print(f"\nDone! {len(paths)} images in {OUT}/")
