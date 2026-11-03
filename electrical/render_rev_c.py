"""Rev C: one battery-master Pololu, complete wiring and phone-size maps.

Requires the existing project Python environment: reportlab, pymupdf, Pillow.
Rev A/B artifacts and generators remain historical references.
"""
from pathlib import Path
import pymupdf as fitz
from reportlab.graphics import renderPDF, renderSVG
from reportlab.graphics.shapes import Drawing, Rect, Line, Circle, String
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
W, H = 1200, 1080
INK, MUTED = '#182D3A', '#4E6472'
RED, GROUND, BLUE = '#BE3434', '#344655', '#176CA9'
d = Drawing(W, H)


def text(x, y, value, size=20, bold=False, color=INK):
    d.add(String(x, H-y, value, fontName='Helvetica-Bold' if bold else 'Helvetica',
                 fontSize=size, fillColor=colors.HexColor(color)))


def box(x, y, w, h, title, detail='', fill='#F6F8FA', stroke='#CBD5DD'):
    d.add(Rect(x, H-y-h, w, h, rx=8, ry=8, fillColor=colors.HexColor(fill),
               strokeColor=colors.HexColor(stroke), strokeWidth=1.5))
    text(x+13, y+(h/2+7 if not detail else 25), title, 19, True)
    if detail:
        text(x+13, y+47, detail, 14, color=MUTED)


def wire(points, color):
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        d.add(Line(x1, H-y1, x2, H-y2, strokeColor=colors.HexColor(color), strokeWidth=3))


def dot(x, y, color):
    d.add(Circle(x, H-y, 4, fillColor=colors.HexColor(color), strokeColor=None))


d.add(Rect(0, 0, W, H, fillColor=colors.white, strokeColor=None))
text(35, 48, 'Rev C | ONE Pololu battery master switch', 32, True)
text(35, 81, 'Prepared design: rewire and bench checks pending. No additional electronic components.', 18, color=MUTED)
text(35, 123, 'POSITIVE | servo current passes through the Pololu, never through the XIAO', 20, True)
box(35, 158, 220, 70, 'Battery RCY + / red', 'Raw battery + goes ONLY to VIN')
wire([(255, 193), (300, 193)], RED)
box(300, 158, 250, 70, 'Pololu 2810 LV', 'VIN  -> switched path ->  VOUT', '#E7F0E7', '#4E8158')
wire([(550, 193), (590, 193)], RED)
box(590, 158, 210, 70, 'J1 SWITCHED +', '4-way physical positive bus', '#FBE9E8', RED)
wire([(800, 193), (825, 193), (825, 323)], RED)
for y, title, detail in [
    (193, 'XIAO BAT+ pad', 'Underside pad; one branch wire'),
    (258, 'Lower servo J_S1 / +', 'Red wire in existing 3-pin plug'),
    (323, 'Upper servo J_S2 / +', 'Red wire in existing 3-pin plug')]:
    wire([(825, y), (855, y)], RED); dot(825, y, RED)
    box(855, y-30, 310, 60, title, detail)
text(35, 272, 'ON / SW control pads: NO wires.', 19, True)
text(35, 300, 'Use the physical slide only. No D2 override.', 17)
text(35, 363, 'Charging (switch ON): USB -> XIAO charger -> J1 -> Pololu VOUT -> VIN -> battery.', 17, True)

text(35, 416, 'GROUND | one common return, including the Pololu', 20, True)
box(35, 525, 220, 60, 'Battery RCY - / black')
wire([(255, 555), (300, 555)], GROUND)
box(300, 520, 250, 70, 'J2 COMMON GND', '5-way physical negative bus', '#E6ECF0', GROUND)
wire([(550, 555), (825, 555)], GROUND)
wire([(825, 460), (825, 655)], GROUND)
for y, title in [(460, 'Pololu GND'), (525, 'XIAO BAT- or GND'),
                 (590, 'Lower servo J_S1 / GND'), (655, 'Upper servo J_S2 / GND')]:
    wire([(825, y), (855, y)], GROUND); dot(825, y, GROUND)
    box(855, y-25, 310, 50, title)
dot(825, 555, GROUND)

text(35, 720, 'PWM | these signal wires share the same existing three-pin servo plugs', 20, True)
for y, pin, endpoint in [(768, 'XIAO D0 / marked 0', 'Lower servo J_S1 / SIG'),
                         (831, 'XIAO D1 / marked 1', 'Upper servo J_S2 / SIG')]:
    box(35, y-25, 250, 50, pin)
    wire([(285, y), (855, y)], BLUE)
    box(855, y-25, 310, 50, endpoint)
text(35, 886, 'D2 remains UNUSED. XIAO 3V3 and 5V/VBUS are NOT connected to servo power.', 17, True)
box(35, 910, 1130, 132, '', fill='#FFF2DF', stroke='#E4B568')
text(52, 939, 'CHARGE: switch ON + USB connected + ./robot charge (firmware 0.3).', 21, True)
text(52, 969, 'Charge mode stops PWM, not servo power; idle current and charging completion need measurement.', 17)
text(52, 999, 'STORAGE OFF: unplug USB AND slide OFF. OFF + USB isolates the cell but may power the servos.', 17, True)
text(52, 1027, 'No routine connector access. Disconnect battery AND USB before soldering or servicing.', 16)
text(35, 1064, 'Connection map, not a physical pad layout. Verify board labels. Steps and sources: electrical/README.md', 13, color=MUTED)

renderSVG.drawToFile(d, str(OUT/'REV_C_WIRING.svg'))
pdf = OUT/'REV_C_WIRING.pdf'
c = canvas.Canvas(str(pdf), pagesize=(792, 792))
c.setTitle('2DOF robot - Rev C single Pololu master switch and PWM-off charging')
scale = min(768/W, 768/H)
c.translate((792-W*scale)/2, (792-H*scale)/2); c.scale(scale, scale)
renderPDF.draw(d, c, 0, 0); c.showPage(); c.save()
with fitz.open(pdf) as doc:
    assert len(doc)==1 and all(t in doc[0].get_text() for t in ('D0', 'D1', 'D2', 'VOUT', 'VIN', './robot charge'))
    doc[0].get_pixmap(matrix=fitz.Matrix(2, 2)).save(str(OUT/'REV_C_WIRING.png'))

FONT = Path('/System/Library/Fonts/Supplemental')


def phone_text(draw, x, y, value, size=30, bold=False, color=INK):
    f = ImageFont.truetype(str(FONT/('Arial Bold.ttf' if bold else 'Arial.ttf')), size)
    draw.text((x,y), value, font=f, fill=color, anchor='lm')


def card(draw, y, title, rows, color=INK):
    height = 75+48*len(rows)
    draw.rounded_rectangle((30,y,970,y+height), radius=12, fill='white', outline='#CBD5DD', width=2)
    phone_text(draw, 55, y+38, title, 32, True, color)
    for i, row in enumerate(rows):
        phone_text(draw, 55, y+90+i*48, row, 28)
    return y+height+22


im = Image.new('RGB', (1000, 1740), '#F6F8FA'); draw = ImageDraw.Draw(im)
phone_text(draw, 40, 52, 'REV C - ONE POLOLU', 43, True)
phone_text(draw, 40, 105, 'Proposed rewire; check before applying power.', 29)
y = card(draw, 145, '1  RAW BATTERY POSITIVE', ['Battery +  ->  Pololu VIN only'], RED)
y = card(draw, y, '2  SWITCHED POSITIVE BUS / J1', ['Join: Pololu VOUT', '       XIAO underside BAT+', '       Lower servo red / +', '       Upper servo red / +'], RED)
y = card(draw, y, '3  COMMON GROUND BUS / J2', ['Join: battery negative', '       Pololu GND', '       XIAO GND or BAT- (one connection)', '       Lower servo ground', '       Upper servo ground'], GROUND)
y = card(draw, y, '4  ONLY TWO SIGNAL WIRES', ['XIAO D0 / 0  ->  lower servo signal', 'XIAO D1 / 1  ->  upper servo signal', 'D2, Pololu ON and SW: no wires'], BLUE)
y = card(draw, y, 'OPERATING RULE', ['Charge: ON + USB + ./robot charge', 'PWM OFF; servo power stays connected.', 'Storage: USB unplugged + switch OFF.', 'USB alone does not prove net charging.'])
assert y < 1740
im.save(OUT/'REV_C_PHONE_WIRING.png')
print('Wrote Rev C SVG, vector PDF, PNG and phone wiring map.')
