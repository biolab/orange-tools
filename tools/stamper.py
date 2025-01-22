# Blaz Zupan blaz.zupan at fri.uni-lj.si
# Ver 1.0: July 2010
# Ver 2.0: Aug 2011 (no more font and text, just same images in PIL and Qt)
from __future__ import print_function, division

import sys
import functools
import os.path
import io


from AnyQt.QtCore import (
    QPoint, QPointF, Qt, QRectF, QBuffer, QByteArray, QIODevice
)

from AnyQt.QtWidgets import (
    QApplication, QDialog, QFileDialog, QGraphicsItem, QGraphicsScene,
    QGraphicsPixmapItem, QGraphicsView, QHBoxLayout, QMenu, QMessageBox,
    QPushButton, QVBoxLayout, QSizePolicy
)

from AnyQt.QtGui import (QCursor, QTransform, QPainter, QPixmap)

from AnyQt.QtSvg import QSvgRenderer

# import PIL last or risk AnyQt conflicts
from PIL import Image


# file name prefixes
ORG = "orig"  # input image file
NUM = "stamped"  # text file with tags and positions
TAG = "tags"  # stamped file

AppName = "Stamper"
PointSize = 17
Dirty = True
MAC = True


# TODO insert stamp here as string
STAMP_SVG = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   width="6mm"
   height="6mm"
   viewBox="0 0 6 6"
   version="1.1"
   xmlns="http://www.w3.org/2000/svg">
  <defs
     id="defs2" />
  <g
     id="layer1">
    <circle
       style="fill:#000000;stroke-width:0.102628"
       id="path844"
       cx="3"
       cy="3"
       r="3" />
    <text
       xml:space="preserve"
       style="font-size:5.64444px;fill:#ffffff;fill-opacity:1"
       x="3.0000014"
       y="5.0178876"
       id="text900" font-family="sans-serif" text-anchor="middle">NUMBER</text>
  </g>
</svg>
"""
STAMP_SIZE = 20


class GraphicsView(QGraphicsView):
    
    def __init__(self, parent=None):
        super(GraphicsView, self).__init__(parent)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.TextAntialiasing)

    def keyPressEvent(self, event):
        def moveSelectedTags(dx, dy):
            items = [item for item in self.scene().selectedItems()]
            for item in items:
                if dx: item.setX(item.pos().x() + dx)
                if dy: item.setY(item.pos().y() + dy)
            global Dirty; Dirty = True

        if (event.key() in (Qt.Key_Backspace, Qt.Key_Delete)):
            self.deleteItems()
        elif event.key() == Qt.Key_Left:
            moveSelectedTags(-1, 0)
        elif event.key() == Qt.Key_Right:
            moveSelectedTags(1, 0)
        elif event.key() == Qt.Key_Up:
            moveSelectedTags(0, -1)
        elif event.key() == Qt.Key_Down:
            moveSelectedTags(0, 1)
        elif event.modifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_B:
                self.dialog.alignBottom()
            if event.key() == Qt.Key_L:
                self.dialog.alignLeft()
            if event.key() == Qt.Key_S:
                self.dialog.save()
        else:
            super(GraphicsView, self).keyPressEvent(event)

    def mouseDoubleClickEvent(self, e):
        if not self.scene().selectedItems():
            self.dialog.addTag()

    def deleteItems(self):
        items = self.scene().selectedItems()
        while items:
            item = items.pop()
            self.scene().removeItem(item)
            del item
        self.dialog.renumberTags()
        global Dirty
        Dirty = True


def save_png(filename, xy, pixelRatio=1):
    print("Saving to %s-%s.png ..." % (filename, NUM))
    if os.path.exists("%s-%s.png" % (filename, ORG)):
        background = Image.open("%s-%s.png" % (filename, ORG))
    else:
        background = Image.open(filename + ".png")
    if background.mode not in ["RGB", "RGBA"]:
        background = background.convert("RGB")
    for i, (x,y) in enumerate(xy):
        x = int(x*pixelRatio)
        y = int(y*pixelRatio)

        pm = ith_stamp_pixmap(i, int(STAMP_SIZE*pixelRatio), int(STAMP_SIZE*pixelRatio))

        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.WriteOnly)
        pm.save(buffer, 'PNG')

        string_io = io.BytesIO(buffer.data())
        overlay = Image.open(string_io)

        background.paste(overlay, (int(x + overlay.size[0]//2),
                                     int(y + overlay.size[1]//2)),
                         overlay)
    background.save(os.path.splitext(filename)[0] + "-" + NUM + ".png",
                    dpi=background.info.get("dpi", (72, 72)))
    print("done.")


class MainForm(QDialog):
    def __init__(self, parent=None, filename=None):
        super(MainForm, self).__init__(parent)

        self.view = GraphicsView()
        background = QPixmap(filename)
        # assume screnshots were taken on the same system stamper is being used on
        # DPI check might be more robust, can be added if needed
        background.setDevicePixelRatio(self.devicePixelRatioF())

        self.filename = os.path.splitext(filename)[0]
        if ("-%s" % ORG) in self.filename:
            self.filename = self.filename[:-len(ORG)-5] + ".png"

        self.scene = QGraphicsScene(self)
        self.scene.addPixmap(background)
        global scene
        scene = self.scene
        self.view.dialog = self
        self.view.setScene(self.scene)
        self.prevPoint = QPoint()
        self.lastStamp = -1 

        buttonLayout = QVBoxLayout()
        for text, slot in (
                ("&Tag", self.addTag),
                ("Align &bottom", self.alignBottom),
                ("Align &left", self.alignLeft),
                ("&Save", self.save),
                ("&Quit", self.accept)):
            button = QPushButton(text)
            button.clicked.connect(slot)
            if not MAC:
                button.setFocusPolicy(Qt.NoFocus)
                self.lineedit.returnPressed.connect(self.updateUi)
            if text == "&Save":
                buttonLayout.addStretch(5)
            if text == "&Quit":
                buttonLayout.addStretch(1)
            buttonLayout.addWidget(button)
        buttonLayout.addStretch()

        size = background.size() / background.devicePixelRatioF()
        self.view.resize(size.width(), size.height())
        self.scene.setSceneRect(0, 0, size.width(), size.height())
        self.view.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        layout = QHBoxLayout()
        layout.addWidget(self.view, 1)
        layout.addLayout(buttonLayout)
        self.setLayout(layout)

        self.setWindowTitle(AppName)
        
        info_name = self.filename + "-" + TAG + ".txt"
            
        if os.path.exists(info_name):
            for tag, x, y in [line.strip().split("\t") for line in
                              open(info_name, "rt").readlines()]:
                self.addTag(int(tag), QPointF(int(x), int(y)),
                            adjust_position=False)
        global Dirty; Dirty = False
        self.show()
        self.raise_()

    def reject(self):
        self.accept()

    def accept(self):
        self.offerSave()
        QDialog.accept(self)
        
    def offerSave(self):
        if (Dirty and QMessageBox.question(self, "%s - Unsaved Changes" % AppName, "Save unsaved changes?",
                                           QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes):
            self.save()

    def position(self):
        return QPointF(self.view.mapFromGlobal(QCursor.pos()))
    
    def addTag(self, stamp=None, position=None, adjust_position=True):
        if not position: position = self.position()
        if stamp is not None:
            self.lastStamp = stamp
        else:
            self.lastStamp += 1
        item = StampItem(self.lastStamp, position, self.scene,
                         adjust_position=adjust_position)
        item.update()
        global Dirty; Dirty = True

    def save(self):
        vals = sorted([(item.stamp, item.pos().x(), item.pos().y()) for item in
                       self.scene.items() if isinstance(item, StampItem)])
        info_name = "%s-%s.txt" %(self.filename, TAG)
        f = open(info_name, "wt")
        for tag, x, y in vals:
            f.write("%s\t%d\t%d\n" % (tag, x, y))
        f.close()
        save_png(self.filename, [(x-STAMP_SIZE/2, y-STAMP_SIZE/2) for _, x, y in vals],
                 self.devicePixelRatioF())
        global Dirty; Dirty = False

    def renumberTags(self):
        """Number the tags by skipping the missing values"""
        vals = sorted([(item.stamp, item) for item in self.scene.items() if
                       isinstance(item, StampItem)])
        for i, (_, v) in enumerate(vals):
            v.setStamp(i)
        if not vals: i = -1
        self.lastStamp = i
        global Dirty; Dirty = True
        
    def alignBottom(self):
        """Align tags horizontally, use bottom margin as a reference"""
        items = [item for item in self.scene.selectedItems() if
                 isinstance(item, StampItem)]
        if items:
            ref_y = max(item.pos().y() for item in items)
            for item in items:
                item.setY(ref_y)
            global Dirty; Dirty = True
                
    def alignLeft(self):
        """Align tags vertically, use left margin as a reference"""
        items = [item for item in self.scene.selectedItems() if
                 isinstance(item, StampItem)]
        if items:
            ref_x = min(item.pos().x() for item in items)
            for item in items:
                item.setX(ref_x)
            global Dirty; Dirty = True


def svg_to_pixmap(svg_str, width, height):
    renderer = QSvgRenderer(svg_str.encode("utf8"))
    pm = QPixmap(width, height)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    renderer.render(painter, QRectF(pm.rect()))
    painter.end()
    return pm


def ith_stamp_pixmap(i, width, height):
    return svg_to_pixmap(STAMP_SVG.replace("NUMBER", str(i + 1)), width, height)


class StampItem(QGraphicsPixmapItem):
    def __init__(self, stamp, position, scene, adjust_position=True,
                 matrix=QTransform()):
        super(StampItem, self).__init__()
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
        self.setStamp(stamp)
        self.setPos(position)
        self.setTransform(matrix)
        scene.clearSelection()
        scene.addItem(self)
        self.setSelected(True)
        if adjust_position:
            bb = self.boundingRect()
            self.moveBy(-(bb.width()//2 + 3), -(bb.height()//2 + 3))

    def setStamp(self, stamp):
        self.stamp = stamp
        pm = ith_stamp_pixmap(self.stamp, STAMP_SIZE, STAMP_SIZE)
        self.setPixmap(pm)
        
    def parentWidget(self):
        return self.scene().views()[0]

    def itemChange(self, change, variant):
        if change != QGraphicsItem.ItemSelectedChange:
            global Dirty; Dirty = True
        return QGraphicsPixmapItem.itemChange(self, change, variant)
    
    def promote(self, direction):
        items = dict([(item.stamp, item) for item in self.scene().items() if
                      isinstance(item, StampItem)])
        new_stamp = self.stamp + direction
        if new_stamp in items:
            items[new_stamp].setStamp(self.stamp)
            self.setStamp(new_stamp)
            global Dirty; Dirty = True
        
    def contextMenuEvent(self, event):
        wrapped = []
        menu = QMenu(self.parentWidget())
        for text, param in (
                ("Promote", 1),
                ("Demote", -1)):
            wrapper = functools.partial(self.promote, param)
            wrapped.append(wrapper)
            menu.addAction(text, wrapper)
        menu.exec_(event.screenPos())

    def mouseDoubleClickEvent(self, event):
        pass


def usage(argv):
    print("%s filename" % argv[0])
    print("  Helps stamp PNG files with numbered labels, ")
    print("  outputs a new PNG ready for documentation.")
    print()
    print("  expected filename format: name-%s.png or name.png" % ORG)
    print("  output: %s-name.txt (info file), %s-name.png (number-marked png)" %
          (TAG, NUM))
    print()
    print("Example:")
    print("% python %s File.png")
    print()
    print("Files and extensions:")
    print("*-%s.png  input image file" % ORG)
    print("*-%s.png  tagged image file" % NUM)
    print("*-%s.txt  coordinates of tags" % TAG)


def main(argv=sys.argv):
    if len(argv) == 1:
        filename = None
    else:
        if argv[1] in ["-h", "--help"]:
            usage(argv)
            return 0
        else:
            filename = argv[1]
    
    app = QApplication(argv)

    # list available fonts
    #from AnyQt.QtGui import QFontDatabase
    #print(QFontDatabase.families())

    if filename is None:
        filename, _ = QFileDialog.getOpenFileName(
            None, "Image file", os.path.expanduser("~/Documents"),
            "Image (*.png)")
        if not filename:
            return 1
        print(filename)

    form = MainForm(filename=filename)
    form.show()
    form.raise_()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
