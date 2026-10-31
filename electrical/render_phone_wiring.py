"""Render large-text connection maps for a phone. Requires Pillow."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
INK, MUTED, PAPER = '#182D3A', '#4E6472', '#F6F8FA'
RED, GROUND, BLUE, PURPLE = '#BE3434', '#344655', '#176CA9', '#7952A5'
FONT = Path('/System/Library/Fonts/Supplemental')

def page(height):
    img = Image.new('RGB', (1000,height), PAPER)
    return img, ImageDraw.Draw(img)

def text(draw,x,y,value,size=31,bold=False,color=INK):
    font=ImageFont.truetype(str(FONT/('Arial Bold.ttf' if bold else 'Arial.ttf')),size)
    draw.text((x,y),value,font=font,fill=color,anchor='lm')

def card(draw,x,y,w,h,fill='white',stroke='#D3DCE3'):
    draw.rounded_rectangle((x,y,x+w,y+h),radius=14,fill=fill,outline=stroke,width=2)

def bus_group(draw,top,title,rows,color,fill):
    card(draw,35,top,930,105+len(rows)*98,fill,fill)
    text(draw,65,top+46,title,32,True,color)
    ys=[top+116+i*98 for i in range(len(rows))]
    draw.line((100,ys[0],100,ys[-1]),fill=color,width=8)
    for y,(label,detail) in zip(ys,rows):
        draw.line((100,y,168,y),fill=color,width=6)
        draw.ellipse((92,y-8,108,y+8),fill=color)
        card(draw,168,y-36,755,76)
        text(draw,192,y-6,label,34,True)
        text(draw,192,y+23,detail,23,color=MUTED)

img,draw=page(1735)
text(draw,45,55,'REV B - POWER WIRES',49,True)
text(draw,45,105,'Two buses. No Pololu. Keep the buses separate.',30,color=MUTED)
bus_group(draw,150,'1  BATTERY POSITIVE  /  J1',[
    ('Battery +','Red lead from the RCY mating harness'),
    ('XIAO BAT+','Battery pad on the underside of the XIAO'),
    ('Lower servo +','Red wire through existing 3-pin plug'),
    ('Upper servo +','Red wire through existing 3-pin plug'),
],RED,'#FBE9E8')
bus_group(draw,700,'2  COMMON GROUND  /  J2',[
    ('Battery −','Black lead from the RCY mating harness'),
    ('XIAO BAT− or GND','Connect one of these ground points'),
    ('Lower servo −','Brown / black ground wire'),
    ('Upper servo −','Brown / black ground wire'),
],GROUND,'#E6ECF0')
card(draw,35,1235,930,430,'#FFF0E0','#FFF0E0')
text(draw,65,1280,'USB charging / programming',37,True)
text(draw,65,1335,'Unplug BOTH complete servo plugs.',32,True)
text(draw,65,1385,'Keep battery connected for charging.',30)
text(draw,65,1450,'Full OFF = battery AND USB unplugged.',30,True)
text(draw,65,1500,'USB can still feed the BAT+ bus.',30)
text(draw,65,1565,'No servo power from XIAO 3V3 or 5V.',30)
text(draw,65,1615,'off / ! stop PWM; they do not cut power.',29)
img.save(OUT/'PHONE_WIRING_POWER.png')

img,draw=page(1040)
text(draw,45,55,'REV B - SIGNAL WIRES',49,True)
text(draw,45,105,'Use the labels on the actual boards.',31,color=MUTED)
text(draw,45,150,'XIAO markings 0 and 1 mean D0 and D1.',29,color=MUTED)
for y,pin,label,detail,color in [
    (260,'D0 / 0','LOWER SERVO','Yellow / orange signal',BLUE),
    (440,'D1 / 1','UPPER SERVO','Yellow / orange signal',BLUE),
]:
    card(draw,45,y-65,325,130)
    text(draw,75,y-23,'XIAO',29,color=MUTED)
    text(draw,75,y+20,pin,43,True,color)
    draw.line((385,y,590,y),fill=color,width=6)
    draw.polygon([(600,y),(578,y-13),(578,y+13)],fill=color)
    card(draw,615,y-65,340,130)
    text(draw,638,y-19,label,30,True)
    text(draw,638,y+23,detail,24,color=MUTED)
card(draw,35,570,930,160,'#E8EEF4','#E8EEF4')
text(draw,65,620,'D2 / 2 is UNUSED',39,True)
text(draw,65,680,'Remove its old Pololu ON wire completely.',30)
card(draw,35,770,930,230,'#FFF0E0','#FFF0E0')
text(draw,65,820,'off / ! = STOP PWM ONLY',36,True)
text(draw,65,875,'No electronic power disconnect remains.',30)
text(draw,65,935,'Unplug battery AND USB for full OFF.',30)
img.save(OUT/'PHONE_WIRING_SIGNALS.png')
print('Wrote phone power and signal diagrams.')
