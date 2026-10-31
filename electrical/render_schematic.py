"""Generate the current Rev B SVG, vector PDF, and PNG. Requires reportlab, pymupdf."""
from pathlib import Path

import pymupdf as fitz
from reportlab.graphics import renderPDF, renderSVG
from reportlab.graphics.shapes import Drawing, Rect, Line, Circle, String
from reportlab.lib import colors
from reportlab.pdfgen import canvas

OUT = Path(__file__).resolve().parent
W, H = 1200, 950
INK, MUTED = '#182D3A', '#4E6472'
RED, GROUND, BLUE = '#BE3434', '#344655', '#176CA9'
d = Drawing(W, H)


def text(x, y, value, size=22, bold=False, color=INK):
    d.add(String(x, H-y, value, fontName='Helvetica-Bold' if bold else 'Helvetica',
                 fontSize=size, fillColor=colors.HexColor(color)))


def box(x, y, w, h, title, detail=None, fill='#F6F8FA', stroke='#CBD5DD'):
    d.add(Rect(x, H-y-h, w, h, rx=8, ry=8, fillColor=colors.HexColor(fill),
               strokeColor=colors.HexColor(stroke), strokeWidth=1.5))
    text(x+16, y+(h/2+7 if not detail else 26), title, 21, True)
    if detail:
        text(x+16, y+48, detail, 14, color=MUTED)


def wire(points, color, width=3):
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        d.add(Line(x1, H-y1, x2, H-y2, strokeColor=colors.HexColor(color), strokeWidth=width))


def dot(x, y, color):
    d.add(Circle(x, H-y, 4, fillColor=colors.HexColor(color), strokeColor=None))


d.add(Rect(0, 0, W, H, fillColor=colors.white, strokeColor=None))
text(35, 48, 'Rev B | direct battery power', 35, True)
text(35, 80, 'No Pololu board. Two insulated power buses. Two direct PWM wires. D2 is unused.', 18, color=MUTED)
text(35, 118, 'POWER | join all points on each bus; keep positive and ground separate', 20, True)

box(35, 180, 230, 50, 'Battery RCY + / red')
wire([(265, 205), (330, 205)], RED)
box(330, 170, 245, 70, 'J1  VBAT+ / 4-way', 'One physical positive junction', '#FBE9E8', RED)
wire([(575, 205), (640, 205)], RED)
wire([(640, 155), (640, 305)], RED)
for y, title, detail in [
    (155, 'XIAO BAT+ pad', 'Underside battery pad; one branch wire'),
    (230, 'Lower servo J_S1 / +', 'Red wire through its removable 3-pin plug'),
    (305, 'Upper servo J_S2 / +', 'Red wire through its removable 3-pin plug'),
]:
    wire([(640, y), (815, y)], RED)
    dot(640, y, RED)
    box(815, y-35, 350, 70, title, detail)
dot(640, 205, RED)

box(35, 445, 230, 50, 'Battery RCY - / black')
wire([(265, 470), (330, 470)], GROUND)
box(330, 435, 245, 70, 'J2  GND / 4-way', 'One physical negative junction', '#E6ECF0', GROUND)
wire([(575, 470), (640, 470)], GROUND)
wire([(640, 415), (640, 565)], GROUND)
for y, title, detail in [
    (415, 'XIAO BAT- or GND', 'Connect one ground point, not both'),
    (490, 'Lower servo J_S1 / GND', 'Brown or black ground wire'),
    (565, 'Upper servo J_S2 / GND', 'Brown or black ground wire'),
]:
    wire([(640, y), (815, y)], GROUND)
    dot(640, y, GROUND)
    box(815, y-35, 350, 70, title, detail)
dot(640, 470, GROUND)

text(35, 637, 'SIGNALS | the same J_S1 and J_S2 plugs also carry these PWM wires', 20, True)
for y, pin, label in [(685, 'XIAO D0 / marked 0', 'Lower servo J_S1 / SIG'),
                      (750, 'XIAO D1 / marked 1', 'Upper servo J_S2 / SIG')]:
    wire([(265, y), (815, y)], BLUE)
    box(35, y-25, 230, 50, pin)
    box(815, y-25, 350, 50, label)
text(35, 803, 'D2: remove its old ON wire and leave unconnected. XIAO 3V3 and 5V are not servo supplies.', 17, True)

box(35, 825, 1130, 93, '', fill='#FFF2DF', stroke='#E4B568')
text(52, 851, 'USB charging/programming: unplug BOTH complete 3-pin servo plugs.', 20, True)
text(52, 879, 'Battery unplug = full OFF only with USB unplugged too. USB can feed the shared BAT+ bus.', 17)
text(52, 904, 'off / ! stop PWM only. No electronic power cutoff remains. Keep the battery connected for charging.', 16)
text(35, 939, 'Connection map, not a physical pad layout. Sources and operating steps: electrical/README.md', 13, color=MUTED)

svg = OUT / 'REV_B_WIRING.svg'
pdf = OUT / 'REV_B_WIRING.pdf'
renderSVG.drawToFile(d, str(svg))
c = canvas.Canvas(str(pdf), pagesize=(792, 612))
c.setTitle('2DOF standing robot - Rev B direct-battery wiring')
c.setAuthor('2dof_standing project')
scale = min(768/W, 588/H)
c.translate((792-W*scale)/2, (612-H*scale)/2)
c.scale(scale, scale)
renderPDF.draw(d, c, 0, 0)
c.showPage()
c.save()
with fitz.open(pdf) as doc:
    assert len(doc) == 1
    page = doc[0]
    assert 'D2' in page.get_text() and 'USB charging/programming' in page.get_text()
    page.get_pixmap(matrix=fitz.Matrix(2, 2)).save(str(OUT/'REV_B_WIRING.png'))
print('Wrote Rev B SVG, vector PDF and PDF-rendered PNG.')
