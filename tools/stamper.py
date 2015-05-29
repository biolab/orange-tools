#!/usr/bin/env python

# Blaz Zupan blaz.zupan at fri.uni-lj.si
# Ver 1.0: July 2010
# Ver 2.0: Aug 2011 (no more font and text, just same images in PIL and Qt)
from __future__ import print_function, division

import sys
import random
import functools
import os.path
import pickle
import uu
import io

from PIL import Image, ImageQt

from PyQt4.QtCore import (
    QByteArray, QDataStream, QFile, QFileInfo,
    QIODevice, QPoint, QPointF, QRectF, Qt, SIGNAL
)

from PyQt4.QtGui import (
    QApplication, QCursor, QDialog,
    QDialogButtonBox, QFileDialog, QGraphicsItem, QGraphicsPixmapItem,
    QGraphicsScene, QGraphicsPixmapItem, QGraphicsView, QGridLayout,
    QHBoxLayout, QLabel, QMatrix, QMenu, QMessageBox, QPainter,
    QPen, QPixmap, QPushButton, QSpinBox,
    QStyle, QTextEdit, QVBoxLayout, QBrush, QSizePolicy
)

# file name prefixes
ORG = "orig" # input image file
NUM = "stamped" # text file with tags and positions
TAG = "tags" # stamped file

AppName = "Stamper"
PointSize = 17
Dirty = True
MAC = True


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
        # super(GraphicsView, self).mouseDoubleClickEvent(e)
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


def save_png(filename, xy):
    print("Saving to %s-%s.png ..." % (filename, NUM))
    if os.path.exists("%s-%s.png" % (filename, ORG)):
        background = Image.open("%s-%s.png" % (filename, ORG))
    else:
        background = Image.open(filename + ".png")
    if background.mode not in ["RGB", "RGBA"]:
        background = background.convert("RGB")
    for i, (x,y) in enumerate(xy):
        x = int(x); y = int(y)
        overlay = im_numbers[i]
        print(int(x + overlay.size[0]//2 - 2), int(y + overlay.size[1]//2 - 2))
        background.paste((0, 0, 0), (int(x + overlay.size[0]//2 - 2),
                                     int(y + overlay.size[1]//2 - 2)),
                         overlay)
    background.save(os.path.splitext(filename)[0] + "-" + NUM + ".png")
    print("done.")


class MainForm(QDialog):

    def __init__(self, parent=None, filename=None):
        super(MainForm, self).__init__(parent)

        self.view = GraphicsView()
        background = QPixmap(filename)

        self.filename = os.path.splitext(filename)[0]
        if ("-%s" % ORG) in self.filename:
            self.filename = self.filename[:-len(ORG)-5] + ".png"

        self.view.setBackgroundBrush(QBrush(background))
        # self.view.setCacheMode(QGraphicsView.CacheBackground)
        # self.view.setDragMode(QGraphicsView.ScrollHandDrag)

        self.scene = QGraphicsScene(self)
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
            if not MAC:
                button.setFocusPolicy(Qt.NoFocus)
            self.connect(button, SIGNAL("clicked()"), slot)
            if text == "&Save":
                buttonLayout.addStretch(5)
            if text == "&Quit":
                buttonLayout.addStretch(1)
            buttonLayout.addWidget(button)
        buttonLayout.addStretch()

        self.view.resize(background.width(), background.height())
        self.scene.setSceneRect(0, 0, background.size().width(), background.size().height())
        self.view.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        layout = QHBoxLayout()
        layout.addWidget(self.view, 1)
        layout.addLayout(buttonLayout)
        self.setLayout(layout)

        self.setWindowTitle(AppName)
        
        info_name = self.filename + "-" + TAG + ".txt"
            
        if os.path.exists(info_name):
            for tag, x, y in [line.strip().split("\t") for line in open(info_name, "rt").readlines()]:
                self.addTag(int(tag), QPointF(int(x), int(y)), adjust_position=False)
        global Dirty; Dirty=False
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
        item = StampItem(self.lastStamp, position, self.scene, adjust_position=adjust_position)
        item.update()
        global Dirty; Dirty = True

    def save(self):
        vals = sorted([(item.stamp, item.pos().x(), item.pos().y()) for item in self.scene.items() if isinstance(item, StampItem)])
        info_name = "%s-%s.txt" %(self.filename, TAG)
        f = open(info_name, "wt")
        for tag, x, y in vals:
            f.write("%s\t%d\t%d\n" % (tag, x, y))
        f.close()
        save_png(self.filename, [(x-5, y-5) for _, x, y in vals])
        global Dirty; Dirty = False
        
    def renumberTags(self):
        """Number the tags by skipping the missing values"""
        vals = sorted([(item.stamp, item) for item in self.scene.items() if isinstance(item, StampItem)])
        for i, (_, v) in enumerate(vals):
            v.setStamp(i)
        if not vals: i = -1
        self.lastStamp = i
        global Dirty; Dirty = True
        
    def alignBottom(self):
        """Align tags horizontally, use bottom margin as a reference"""
        items = [item for item in self.scene.selectedItems() if isinstance(item, StampItem)]
        if items:
            ref_y = max(item.pos().y() for item in items)
            for item in items:
                item.setY(ref_y)
            global Dirty; Dirty = True
                
    def alignLeft(self):
        """Align tags vertically, use left margin as a reference"""
        items = [item for item in self.scene.selectedItems() if isinstance(item, StampItem)]
        if items:
            ref_x = min(item.pos().x() for item in items)
            for item in items:
                item.setX(ref_x)
            global Dirty; Dirty = True

class StampItem(QGraphicsPixmapItem):
    def __init__(self, stamp, position, scene, adjust_position=True,
                 matrix=QMatrix()):
        super(StampItem, self).__init__()
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
        self.setStamp(stamp)
        self.setPos(position)
        self.setMatrix(matrix)
        scene.clearSelection()
        scene.addItem(self)
        self.setSelected(True)
        if adjust_position:
            bb = self.boundingRect()
            self.moveBy(-(bb.width()//2 + 3), -(bb.height()//2 + 3))

    def setStamp(self, stamp):
        self.stamp = stamp
        self.setPixmap(QPixmap.fromImage(ImageQt.ImageQt(im_numbers[stamp]), flags=Qt.AutoColor))
        
    def parentWidget(self):
        return self.scene().views()[0]

    def itemChange(self, change, variant):
        if change != QGraphicsItem.ItemSelectedChange:
            global Dirty; Dirty = True
        return QGraphicsPixmapItem.itemChange(self, change, variant)
    
    def promote(self, direction):
        items = dict([(item.stamp, item) for item in self.scene().items() if isinstance(item, StampItem)])
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


numbers_coded = br"""begin 666 -
M*&QP, I3)UQX.#E03D=<<EQN7'@Q85QN7'@P,%QX,#!<># P7'))2$127'@P
M,%QX,#!<># P7'@P95QX,#!<># P7'@P,%QX,&5<># X7'@P-EQX,#!<># P
M7'@P,%QX,69(+5QX9#%<># P7'@P,%QX,#!<='!(67-<># P7'@P,%QR7'AD
M-UQX,#!<># P7')<>&0W7'@P,4(H7'@Y8GA<># P7'@P,%QX,#!<>&5C241!
M5"A<>#$U7'@Y-5QX.3)<>&-D7'AA84%A7'@Q-%QX.#9<>#@U7'@Y.5QX831(
M7'AE.4Q<>&,X7'AE-%QX.&-<>#@Y7'@Y8V)X7'AE85Q<7'@X,EQX8F)P-T9&
M;D!<>&$W7%Q<>#@Q,C%<>#DQ7'@Y.5QX.#E<>#EF,UQX.3)<>#$Q7'AD82EU
M7'AF8SYO65QX9F%<>&(P7'@X.5QX8C=<>#%E7'AF8EU<>&5B6V]<>&1F7'AD
M92M<>&$Q7'@X,%QX8F9<>&$R7'AB-$M<>#DP7'@X-%QX,#5<>&5C7'AE,5QX
M83ER7'@Y8UQX9C9<>&4P7'@P,%QX8S<S7'AF9CQ<>#=F7'AE,5QX,#-\55QX
M83-<>&)B7'@P-5QX,&),7'AF,%QX,61<>&$W7'AD-EQX8V1<>&1F<%QX834B
M7'AD-5QX,&4L-%QX8S)<>#=F05QX9#E<>&4Y7'AE.6Q<>#!E7'1<>&(X:%QX
M.#!<>&(S4%QX9C-<>&0R7'AB9%QX,&9J7'AA-F%<>&4W6EQX.#!<>#@U7'AF
M-%Q<7'AC,5QX,3 J<'M<>&$S7'AC95QX83=<>#$P7'@P.$->7'AC-E%<>#!C
M+R)<>&(P=EQX9F%F,UQX.3AX7'@Y,%QX,68M7'AE-%QX,61<>&4Y7'AD-EQX
M.61<>#@R7'AF9'=27'AC8VIQ7'@Y95QX.#)<>&9A7'AA-BY<>&)C7'AA85QX
M8C8[7'AF.$E<>&(Q7'@P,5QX8F1<>#@V7'AF,5QX.#-<>&)F75QX8V5<>#DX
M7'@Y95QX8F5<>&9D2E4J7'@P9BQ<>&$X7'AC-5QX,#A<>&%B7'AF9EQX9C!<
M># U7'AF,%5<>#EA;EQX,&)<>#DV8%QX.#%<>#$Y7'AB95QX,&5<>&9A7'AF
M9EQX8F5<>&$T+%-<>&$Y1UQX.3-<)TM<>#@R2EQX9&1R1EQX,39<>&%E7'@P
M,%QX,#!<># P7'@P,$E%3D1<>&%E0F!<>#@R)PIP,0IA4R=<>#@Y4$Y'7')<
M;EQX,6%<;EQX,#!<># P7'@P,%QR24A$4EQX,#!<># P7'@P,%QX,&5<># P
M7'@P,%QX,#!<>#!E7'@P.%QX,#9<># P7'@P,%QX,#!<>#%F2"U<>&0Q7'@P
M,%QX,#!<># P7'1P2%ES7'@P,%QX,#!<<EQX9#=<># P7'@P,%QR7'AD-UQX
M,#%"*%QX.6)X7'@P,%QX,#!<># Q7'@Q8DE$050H7'@Q-5QX.&1<>#DR/TM"
M45QX,3A<>&,V7'@X-5QX,&(B2"%<>#@V4"Y!7'@P-EQX,&5.0EQX9#$N0EQX
M,68A7'AA8UQX9#%<>&%D7'AC,5QX,&9<>&4Q7'@Q,EQR7'@X9$XN7'AB83A<
M>#DV7'AD9EQX8S%<>&$Y(6I<>#!E7'AC,EQX839H*BU"7'AE.5QX.69<>&9D
M7'@Q93E<>&5F7'AE9'A<>&(Y7'@X-5QX,&9<>&9C/%QX8V9Y7'AD95QX9C-<
M>#EE<SA<>&1E(%QX,3%<>&%F7'@Q-5QX93(]7'AC.%QX8S%<>#$S?%QX8S%<
M>&)F*E-<>&)D7'@X-&]<>#DX.5QX9&5<>#$Y7'AF8EQX.3!<>#@W6#5(/UQX
M8S!<>#%A7'AA95QX9C!<>#AF7'AD95Q<7"=784%<>&)B7'AC8SY!33IQ7'@Q
M8C8@7'@P-5QX9F(P7'@P-5QX9#5<>&(T7'AD,5QX,6%<>#@T7'AB85QX8S%<
M>&0Y275<>&)C-EQX9#)<>#$U7'AA9D%<>&5A7'@X,5QX9#5<>&1B7'AF,UQX
M.#1<>#%F/5QX.#!<>#@U7'@Q85QX.6)<>&0P=5QX.3E<>#%E)5QR1VY<>&%E
M7'AF85QX,3!<>&4V7'AD,E5<>&9C1EQX9&9?7'AB.#5<)UQX.3$U65QX935<
M>#DU2&A<>#AD7'@Q9%QX9C(D7'@Y-%QX93!<<BQ<>&0W7'@X8EQX869"(EQX
M93-<>#@U*EQX8F5"7')<>&$T0UQX,3A<>#@S-6E<>&)C7'@X-5!<># S7'@Y
M8UQX,35<>#AF7'AF,5QX,#%<>#EC7'@X,EY17'AB8UQX.#!<>&0U7'AC9EQX
M9C!<>&$Q7'@X85QX8CA<=%QX83A87'@P.%QX9#-?7'AA,UQX9F987'AB-3M<
M>&0P8RU<>&4X7'@X,%QX.3EV7'AD-EQX9#5&7'@Q,5QX8C1<>&4Y/5QX96- 
M7'AA8S9)7'AC9EQX93%<>#$Y7'AE8VI<>#!F7'AF.%QX,39<>&4X7'AF8EU*
M6UQX86-:7'AF9FM<>&4U7'@P9EQX,&5<># P85QX8V9<># X7'1<>&(R7'@Q
M.%QX,#!<># P7'@P,%QX,#!)14Y$7'AA94)@7'@X,B<*<#(*85,G7'@X.5!.
M1UQR7&Y<>#%A7&Y<># P7'@P,%QX,#!<<DE(1%)<># P7'@P,%QX,#!<>#!E
M7'@P,%QX,#!<># P7'@P95QX,#A<># V7'@P,%QX,#!<># P7'@Q9D@M7'AD
M,5QX,#!<># P7'@P,%QT<$A9<UQX,#!<># P7')<>&0W7'@P,%QX,#!<<EQX
M9#=<># Q0BA<>#EB>%QX,#!<># P7'@P,2Q)1$%4*%QX,35<>#AD7'AD,EQX
M8V9*7'@P,E%<>#$T7'AC-UQX9C%<>&,Y,$)<=%QX9F%<)T@@0EQX.6)6+5QX
M83)<>&$R7'AD85QX9#0B05QX9&-<>&(U7'AE8B%<>#@R7'AD95QX8S%<>#@U
M7'@X9EQX93!<>&-A75QX96)<>#$P(5QX83)<>#$W7'@P."0B2%QX.#1<>#@X
M0G1<>#$Q7'@Q.2U<>&(R3"A<>&9A9UQX9&9<>&1F<&]<>&1C7'@X.2D\7'AF
M,%QX.3E[7'AC95QX8CE<>#=F9EQX8C@Z7'AE8UQX.#5<>&,W7'@Q.%QX961<
M>#$U)%QX9C!<>#@P3UQX9F-<>#%B7'@P8EQX8V-<>#EE7'AE,%QX,&)]7'AE
M,UQX.&1<>&(Q7'@X,EQX,3E<>#@T7'AC-BY<>&1D=UQX9#A<<C5<>&8R7'AA
M-E-<>&5B7'AC9%QX,3E<># T8EQX.3E<>&5A7'@P,UQX9&%<>&0T7'AC-EQX
M,6-<>&$V7'@Q,%QX8S,J7EQX83%<>&(Y.UQX83A<>&9F7'@Q,UQX93=D7'AF
M-DU<># U7'AF,EQT7'AB8UQX93!<>#$R7'@X83U<>&0X7'AF.5QX.3)<>&1F
M7'AE,5QX83%<>#!B7'AB,$U<>#AD7')<>#EC7'@Y.5QX9&5<>#$U7'AE,UQX
M,3!<>&8R7'AA-EQX9#9\7'@Q,WYD>5QX8F%<>#%B7'@Y-3]A7'@P8EQX9#-<
M>#DX7'@X-SY<>&0Q73-<>#$Y7'AA,5QX83%<>#!B7'AF.5QX,60C-%QX9#9<
M>&(Q7'@X-FM484-<># W7'AE.#Y<>&)C<5QX8CA<>&$W7'@Q9%)<>&5F7'@Y
M8EQX.65^7'AB9EQX,30V35QX861U7'AF87Q/;WQ<>&,T7'AB,5QN7'@Q,T=<
M>#AC.UQX83A<>&4S7'@Q-%QX9C=87'@X-%QX.&1<># S7'@Y8FA<>&0T7'AF
M-5QX96)<>#$V=5QX93)<># U-EQX,3!<>&,U*')<>&(X7'@X,5QX939T<7%<
M># T8EQX.6)<>&%A7'@P8BU<>#DP9UQX9C1<>#EC7'AB845<>&)E7'@X-%QX
M9#!(7'AD,RU<>&$S7'@P,WM<>&,P+7E<>#$Q7'AF85QX9F9<>#!E7'@Q-%QX
M8C-<>&%C2EQX9F5<>&(U7'AF,EQX,6)<>#AD7'AD95M<>&9A7'@Y8EQX,65<
M>&8U7'AB-EQX,#!<># P7'@P,%QX,#!)14Y$7'AA94)@7'@X,B<*<#,*85,B
M7'@X.5!.1UQR7&Y<>#%A7&Y<># P7'@P,%QX,#!<<DE(1%)<># P7'@P,%QX
M,#!<>#!E7'@P,%QX,#!<># P7'@P95QX,#A<># V7'@P,%QX,#!<># P7'@Q
M9D@M7'AD,5QX,#!<># P7'@P,%QT<$A9<UQX,#!<># P7')<>&0W7'@P,%QX
M,#!<<EQX9#=<># Q0BA<>#EB>%QX,#!<># P7'@P,5QX,3E)1$%4*%QX,35<
M>#AD7'@Y,EQX8C%*7'@P,U%<>#$P15=C)UQX.#)$7'@P,FI<>&$S7'AD.%A<
M>#%B7'@Y-%1<>&4Y;%QX9F-<># R7'AB9B!<>#@U7'@X9'Y)7'AC,"952%QX
M.3527'@Q-%-:6UQX9#E9*V)<>#AA1"Q<>#DR*"I<>#@X,5QX.6%<>#EC7'AF
M8EQX.3A<>#DQ7'@Y-V5<>#$U7'@P-UQX8V5<>&1E>7=F=C=<>#DS7'AC9"5<
M>&0Y7'AB,5QX.#!=7'@X,EQX,#)<>#!C7'AE,%QX,&)<>&9E7'@X8RU<>&%A
M5UQX9C!<<F-C7'@X.%QX.65<>&,S*F1<>&,V(5QX964G7'AF.%QX8S [7'AF
M.2ET7'AC8UQX9#-<>#DS=V$J=CA<>#AD7'AC,%QX.#=<>&$T1UQX9#9Q7'@Q
M,EQX9CE<>#AF7'AE-$M<>&4V7'@P-UQX8CE<>#AE7'@X85QX,6%<>&)A7'@X
M,%QX.3E025QX.3)X4%QX8C5<>&)A7'AF.6%<># Q7'AF,5QX.3-Z7'@Q-%9@
M7'AC9EQX,6%<>&0R7'@X,UQX9C=<>&8R9UQX83%H7'(N7'@Q-5QX,3)M7'AF
M-5QX9#A<>#AD7'@Y-%QX865S7'AC95QX8V9Q7'AD,4(\7'@Q820M.%QX.#-7
M,UQX9F)<>&4X,RQ<>&1A66]<>#$W9F1<>&8X7'AA8EQX.39<>&%D7'@Y.%QX
M.39<>#@S7'AA.%QX93<F+EY:05QX-V9<>&,Q7'@Y8G%K7')-7'AF-%QX,#-<
M>&9C7'AE-E5<>&8S7'@X,VQR7'AD-5QX.3!<>#$W7'AA-5QX9&107'@Y.5QX
M9&5<>&5A7'@Q9%QX9&5<>&)C7'AF.3]<>&(R3UQX9C9<># R/EQX86-<>&%F
M1UQX8F9-7UQX.&5<>&)C-FQ#9EQX86-<>&4Q:C%/7'AE,#=X(%QX869<>#@Q
M-EQX9F1<>&%F7'AD.%QX83!K7'AF.5QX8C=<>&-E7'1<>#$P7'@X.5A<>&-F
M7'AA8UQX9&1<>&4V7'@X.5QX,#!<># P7'@P,%QX,#!)14Y$7'AA94)@7'@X
M,B(*<#0*85,G7'@X.5!.1UQR7&Y<>#%A7&Y<># P7'@P,%QX,#!<<DE(1%)<
M># P7'@P,%QX,#!<>#!E7'@P,%QX,#!<># P7'@P95QX,#A<># V7'@P,%QX
M,#!<># P7'@Q9D@M7'AD,5QX,#!<># P7'@P,%QT<$A9<UQX,#!<># P7')<
M>&0W7'@P,%QX,#!<<EQX9#=<># Q0BA<>#EB>%QX,#!<># P7'@P,5QX,61)
M1$%4*%QX,35<>#AD7'@Y,3%+7'@X,E%<>#$T7'@X-D5<>&1D7'AC,EQX,#@C
M7'@P.%QX.3="7'@X-$9-7'@Y,EQX9#9<>#AC5EQX83= 7'AC,5QX8S5<>&$Y
M,5QX9F9<>#@W/UQX8S!<>&,Y7'AB9B B7'@P.%QX,&4M7'(Y*%QX.#A<>&(X
M5UQX9#@D3EQX.34Z7'@P.%QX.39<>&4V7'AF,T9<)UQX865<>&8R7'@Q-5QX
M8F5<>&8P?%QX93<]7'AE-UQX9&5<>&8S?5QX93=<>&1E+UQX93!<>&8S5EQX
M.#A<>&8R.5QX,6-<>&,P*RQ<>&4P7UQX.61<>&(R7'AD85QX.#$E?%QX9F0P
M7"=<>&0V(5QX,#)<>#EE*E)<>&9D7'@X,%QX,#%<>&(T-UQX,3A<>#DS7'AE
M8EQX8V)77'AB,%QX839<>#$T7'AD.5PG7'AE."M<>&(W7'@Q,%QX.# ]7'@X
M-UQX,#=<>&)C7'AD-D9<>&(P7'@P9EQX8F9<>&5A7'AE,VPT-29<>#EC7'AD
M8UQX96%<>#$V*UQX96%<>&8R7'@X,RX@7'AA95QX8S1<>&0Q7'@Q-%QX-V9<
M># S7'@P-5QX8CA<># W-5QX.3E<>&)E7'AC-U5C7'AD,BI.?%QX8S9<>&5B
M9G=<>&4P7'@Q,EQX86%@.EQX8S9<>#@T7'@Y-6A<>&,Q7'AC-E L05QX9#9<
M>&$Y7'AC-5QX9C!<>&0W3EQX865<>#%B7'AD9EQR7'AF,EQX93A<>#@Q*UQX
M.&1<>&$R,UQX.6%<>&8T7'AF-D=+7'@X.$\P7'AD,5QX83A<>&5F7'AD,%QX
M,#)37'@Q,UQX.3-<>#@W7'@P,5QX9&-!7'@Q-RY<>&,P7'AD-#!<>&$S>%QX
M,#(S7'AD,%QX83A<>&)A7'AF,C1H7'@Q82E<># S>EQX8CE<>&0V='9<>#ED
M>TTY7'AB,EQT:%QX.#-<>&0P7'@P9EQX9#=<>#AF7'AB-UQX9F-<># U7'@W
M9EQX,#9<>#EE.EQX83):7'@X,S=<>&(P7'@X-B%<>&)E7'@P8UQX8F%<>&4U
M7'AA9%QX,31E7'AD-UQX93%?.U=[=DU 7'AA-UQX9# H7'AC9EQX,#!<># P
M7'@P,%QX,#!)14Y$7'AA94)@7'@X,B<*<#4*85,G7'@X.5!.1UQR7&Y<>#%A
M7&Y<># P7'@P,%QX,#!<<DE(1%)<># P7'@P,%QX,#!<>#!E7'@P,%QX,#!<
M># P7'@P95QX,#A<># V7'@P,%QX,#!<># P7'@Q9D@M7'AD,5QX,#!<># P
M7'@P,%QT<$A9<UQX,#!<># P7')<>&0W7'@P,%QX,#!<<EQX9#=<># Q0BA<
M>#EB>%QX,#!<># P7'@P,2M)1$%4*%QX,35<>#AD7'@Y,DLK16%<>#$T7'@X
M-C=<)U)R<CU<>&,Y7'AC-"5<>#DW*45<># V9CI%7'@Q.2A<>#$S?EQX.#5<
M>&$Y7V$H7'@P,UQX-V9!,C<T7'@Y,%QX.#E<>#AC3%!<)UQX,#-<>&(Y7'@Q
M-%QX.3)27'AE95QX8V9<>&$S;VE<>#EF7'AD85QX931<>&%D9UQX-V9K7'AB
M9%QX9&9<>&1A:UQX869<>&9D7'AE9%U<>&-A7'@X85QX9#5<>#@V/5QR/7!<
M># W7'AE9EQX9C!<>&$W)EQX9#@]7'@X-%QX,&9<>&8X3%QX8F-<>&(P7'AE
M94)<>#%F7'@Q-&I<>#$U7'AF-UQX,35<>&)C7'AE,5QX,3E<>#!E7'AE,"1<
M>&4U>CY<>&(Y7&YU7'@Y82)[7'@P,UQX,&).85QX,3A<>&)A7'AA,5QX,#-F
M("9<>&(X(EQX965<>#@R7'@Q9EQX,61<>#$S7'AC-6A+7'AC-"-<>&8P7'@P
M,%QX93=<>&0P7'@P-'M<>#$P7'AF8EM<>&,T65QX,#-X7'@P,#<F7'AC.%QX
M8V4M7'AB,%QX,#)<>&)E;UQX,#5<>#$V7'AA,%QX,61"-5QX.#)!7'@Y,SE<
M>#@X;EQX.3=<>#%A7'AC.%QX.#9<>&8S,%QN7'@Y9'!<>#!F45QX93-<>&%A
M7'@Y-UQX8V1<>&4V7'AC8VM<<EQX8C1<># X7'@Q-EQX9&-<>#@R33937'AA
M95QX93=47'AE-48N1UQX,3!R7'AE8V9<>#$X2%QX.#9<># W45QX,#9<>#%B
M7'@X-%QX8V5<># X7'@Q92-<>&0Y7"=<>#@X45QX.39<>#@Y?5QX,#=<>#!F
M9EQX,6)<>#DT7'AC-5QX8C%<>&)F7'AF95QX961<>&$T7'AC8EQX,3A<>&%B
M7'AD9EQX8V5<>&-D7'@P8EQX,3A<>#@W7'@Q,CA<>&0Q7'@Q85QX8S1--FM<
M>#@U.EQX9CDD1UQX.#@B7'AB9EQX9#E3+EQX869<>#$Q3T)<>&$Q7'AF87%W
M(%QX-V9<>#AA7'@Y95QX9C1<># V7'AF.%QX9F9<>&9E2T-47'AF-5QX9F56
M7'AF.5QX,#5<>#$V>%1<>#%F7'AA-FQB7'AB85QX,#!<># P7'@P,%QX,#!)
M14Y$7'AA94)@7'@X,B<*<#8*85,B7'@X.5!.1UQR7&Y<>#%A7&Y<># P7'@P
M,%QX,#!<<DE(1%)<># P7'@P,%QX,#!<>#!E7'@P,%QX,#!<># P7'@P95QX
M,#A<># V7'@P,%QX,#!<># P7'@Q9D@M7'AD,5QX,#!<># P7'@P,%QT<$A9
M<UQX,#!<># P7')<>&0W7'@P,%QX,#!<<EQX9#=<># Q0BA<>#EB>%QX,#!<
M># P7'@P,5QX,&))1$%4*%QX,35<>#AD7'@Y,C%+7'@X,E%<>#$T7'@X-F\U
M9EQX,3%<>#DU("Y!2UQX.&)+7'AA,%QX8C1*7'(N7'AC9%QX8C5<>&8T7'@Q
M8EQX9F-<=%QX8V1<>&9E7'@P,5QX83=<>#DV?D%<># X7'AA94)(+C5%7'AA
M,UQX,3 Y25QX.#-87'AD."!49EQX8V8K7'AF-UQX8SA<>#$Q7'AA95QX9#%<
M>#@Q7'@X-UQX9C-<>&1E7'AF-UQX.6-<>&9B7'AD9'M<>#!F7'AD9EI(7'AC
M-UQX,#9<>&8V7'@Q,61A7'@P.%QX,3-<>&8X,UQX,&5<>&$Y7'AD95QX8S-<
M>#!F3"-<>#EF7'AE-%QX,#9<>&4T85QX,64K<UQX,35"7'@Q-5U<>#@S)UQX
M93=<>#DY7'AD8T5L7'AC,UQX,3E<>&(T7'AC8U0N7'AC,3=<>#!C7'AB-$A<
M>&,T7'@P-5QX.65N7'AF,%QN.UQX8F5<>&9E7'@Q.%QX,&)?7'AE-%M<>&,W
M96Q<>&)A)EQX9&)<>&0U7'AA9EQX83(W7'@Q8EQX.#!<>#DY/EQX96)<># V
M7'@P-2A<>#@R7'@W9EQX9C-<>#AB;5QX86,@7'AF8UQX,#9<>&0S7'AF-5QX
M9#AP7'@Y-UQX83A<>&5B7'AB9%QX93$X45QX9#!I7'@Q85QX8SA)7'AA,EQX
M839<>&0S-R%L)5QX.&%<>#!F*EQX,3!<>#EA7'AB,EQX9&1<>&,P<E=<>#@U
M57A<>#@W7'@X95QX,38N7'AD85%<>#DW7'@Y9&=<>&(R:4)<>&8Y7'@P,%QX
M8S9@7SU%9T!3-D]<>&8Y7'@Q.5QX9#9A(5QX8V597'@X9$!<<EQX,69<>#$Q
M7'AB9EQX83E<>#@W7'AA-UQT)V-<>#!F7'AF-UQX,#9<>&1E7'AC,#9<>&8U
M7'AD,5QX.6%<>&(P7'AF95QX9&9<>#=F7'AC-3Y=7'AB.65<>#ED7'AB9G9<
M>&(R6VE"7'AC.%QX,#)<>&,Q7'@P,%QX,#!<># P7'@P,$E%3D1<>&%E0F!<
M>#@R(@IP-PIA4R)<>#@Y4$Y'7')<;EQX,6%<;EQX,#!<># P7'@P,%QR24A$
M4EQX,#!<># P7'@P,%QX,&5<># P7'@P,%QX,#!<>#!E7'@P.%QX,#9<># P
M7'@P,%QX,#!<>#%F2"U<>&0Q7'@P,%QX,#!<># P7'1P2%ES7'@P,%QX,#!<
M<EQX9#=<># P7'@P,%QR7'AD-UQX,#%"*%QX.6)X7'@P,%QX,#!<># Q(TE$
M050H7'@Q-5QX.&1<>#DR7'AC9"I<>#@U45QX,31<>#@V3RA<>#%D7'@Q,CDI
M7'@Y.3A<>#DY7'@Y,%QX.#E<>#$T7'@Y.5QX,3DI.2-<>#$S7'@Q.5QX8CE<
M># T+EQX8S!<>&,P7'AD-%QX,35<>#$X7'AB.5QX,#$C*2Y<>&,Q1%QX,31#
M7'@X.2A<>#DQ7'@Y,5QX8F9<>#DR7'AF8WM<>#%E7'AE9'5<>&1A7'AA-SY<
M>&8R7'AD-EQX9#-<>&9A7'AD.6M<>&%F7'AB-5QX8F5<>&1D7'AD-UQ<*E9<
M># W7'AE.5QT7'AE.%QX.#%;7'AF.%QX.# _-5QX8V%<>&4Y7'@Q97Q<>&,R
M5UQX93)<>#$U7'AB8EQX,#5]4%QX83@E7'AB,F]<>#$P7'@Q-UQX,&5<>&8Q
M7'AC9EQX8C-<>&0X7'AC.5-<>&0P7'AA,'%<>&$R=UQX9C!<>&0R7'@Q-51A
M7'@Q.%QX.6,R7'1<>&%E7'AE85QX9#E<<E1<>&$P7'AA92-<>&)C7'@Y.%QX
M8C1<>#AC7'AE9EQX8C=<>&0Y7'AE.%QX,31<>&0T7'@P95QX8S1<>&8Y7'AB
M85QX.#DF7'AB,&A<>&,T(%QX93E<=%QX96(E7'AD-WY)7'AB.5QX8F)D-5QX
M9C5U7'AA-UQT7'AA,EQX.6)<>&8V7'@Q,EI<>&,Q7'@X-FTP7'@P-#9<>&,X
M:UQX8F%<>#ED:%QX93=<7%QX86)<># T+5QX8C!<># R7'@X8G!<>#!C7'@Q
M8EQX,3!<>&(R7'@X,5QX,6)<>#DU7'AB82!<>&5F7'AE-EQX.#-<>&-C95QX
M8CDJ7'AF96Q<>#$V7'@Y9EQX93!<>&9F?%QX93,]=EQX9#<@:5QX,#9<>&)B
M7'@P9EQX9#=P7'@P,%QX865>7'@X,UQX9#!V.%QX9&%!>%QX,#8G7'AB8EQX
M.6%<>#@U95QX93A<>#@T7'@P-5QX9C!<>&,Q/#M<>#@S=FA<>&0P/%QX9#$C
M7'AC-%QX9&%<>#!F7'AF.%QX9CE<>&$S7%Q<>#$P7'@X9D%<>&$Q7'AF85QX
M8SEN7'@X,EQX8V9<>#%F7')<7'E<<EQX9F-<>#=F7'AF9EQX835<># Q7'AA
M87I<>#=F7'AA8EQX9F-<># V7'AA94567'AA9%U<>&$P7'@Q,5QX.6%<># P
M7'@P,%QX,#!<># P245.1%QX865"8%QX.#(B"G X"F%3)UQX.#E03D=<<EQN
M7'@Q85QN7'@P,%QX,#!<># P7'))2$127'@P,%QX,#!<># P7'@P95QX,#!<
M># P7'@P,%QX,&5<># X7'@P-EQX,#!<># P7'@P,%QX,69(+5QX9#%<># P
M7'@P,%QX,#!<='!(67-<># P7'@P,%QR7'AD-UQX,#!<># P7')<>&0W7'@P
M,4(H7'@Y8GA<># P7'@P,%QX,#$J241!5"A<>#$U7'@X9%QX.3)<>&)B2EQX
M,#-!7'@Q-%QX.#9<>#$W(UQX,3)<>#$T02)<=%QX.3)&7'AB,5QX9#!&7'AF
M,%QX.#)<>#DW7'@Q-UQX8C!<>&(T7'@Q-U)<>&0Y7'@P8EQX,39<>&4R8RA6
M5EQX8F5<>#@P7'@Y-5A87'AD8EA<>#@X(")<>#@R7'@X,EQX,#%<>&0Q2EQX
M861<>#$T7'@X,B!<>&1E7'AF9%QX8F5<>&(P7"=L8%QX.3%<>&9C7'AF,%QX
M961<>&9C7'AE-UQX.6-<>&0Y.3M<>&(S4TA<>&8R7'AD-4]Z7'@P,5QX8V%<
M>&8P7'@P8UQX9&9<>&8P7'AA9EQX839<>&$Y7'@Y95QX8S)<>#!F7'AF8UQX
M839\,%QX,65 7'@Q-7)<>&(U1EQX9C9<>#$S?%QX83%<># Q1W!<='8S9UQX
M93=%:%QX9#-<>#%C7'AD,5QX,3<X7'AE,5QN7'@X-E)<>&)A7'@Q.%QX.3=<
M>&,P7'AA95QX9#9<>#EE8%QX,3!:7'AB85QX8S!97'@Y,%5<>#DX7'@X-W=<
M>&(P7'AA8EQX9&%<>#@S7'AA.%QX968V,SP\7'@X,$@Z5F C7'@Y,RM<>&4Q
M5S)<>&8Q7'@Q9#Y<>&4Y7'@X-EQX,3E-1EQX,3-<>&8X,W!<>#DQ:W!O7'@X
M9EQX,3!<>#%A7'AC,5QX.31<>&1C7'@X,UQX,#=<>#DR7'AD-3I<>#@Q7'@X
M-S)<># V?G)<>#!F7'AD."!<>&4T7'@X,EQX.65',EQX,#!<># V7'AC,5QX
M,&)<>&9E7'@P-EQX,&5<>&4Q7'@Q8WI<>&,Q?4=<>&)D7'@X96]<>&4Y7'@Q
M.%QX,3=<>#@U7'@Q87Y<;EYA7'@Q8EQX9#1<=$1]7'AA8EQX.3E)7'@Q9EQX
M93-<>#AC;VE<>&0Q7'@Q-5PG7'AC,4\L7'AC,B9<>&,T2UQX8C=<>&8X/FA<
M>&0S,E%<># S8EQX.3)<>&9F+"Y<>#@T7'AB.7M<>#DX7'@X-5Q<7')<>#DS
M7'AD9%QX,#=<>&8W7'@Q.5QX,&(\7'AE,'=<>&,P7'AF8EQX9&)<>#DQ1EQX
M.3E<>&4U7')<>&-A7'AD-5QX,69K7'@Q9E=<>&%F4%QX.3A<>#@Y7'@P-%QX
M,#!<># P7'@P,%QX,#!)14Y$7'AA94)@7'@X,B<*<#D*85,G7'@X.5!.1UQR
M7&Y<>#%A7&Y<># P7'@P,%QX,#!<<DE(1%)<># P7'@P,%QX,#!<>#!E7'@P
M,%QX,#!<># P7'@P95QX,#A<># V7'@P,%QX,#!<># P7'@Q9D@M7'AD,5QX
M,#!<># P7'@P,%QT<$A9<UQX,#!<># P7')<>&0W7'@P,%QX,#!<<EQX9#=<
M># Q0BA<>#EB>%QX,#!<># P7'@P,2))1$%4*%QX,35<>#AD7'@Y,EQX8S%*
M0E%<>#$T15QX835 7'AC,5QX.3!<>&(T2%QX86-<># V7'@X-5QX.3!<>#AE
M7'@Y,R1I7'AD8S\X;%QX93!<>&)C7'@W9EQX93@C7'@Q85QX9CE<># Q7'AA
M.6!<># X-EQX.&-&35QX,6$D-4\J7'@Y,'0@9B(D7'AA.5QX9#5<>&1A>5QX
M.65<>&4T7'AE,UQX,3EM6%QX96-[7'AF-WM<>&,W<UQX969Y+EQX9F%<>&)C
M7'@Q-2)<>&1E7'@X-S5<>&4X7'AC,%QX,3A<>&9E7'AD-"Y/;UQX93!<>#$S
M7'AB95QX.&-<>#!F7'AB8UQX,#)<>#%B7'AE,%QX83EC7'AD,B%<>&0T7'AA
M,%QX,&8J;%QX8S%<>&$U7'AB.3I<>#%F7'AC,EQX.&-<>&0R7'AE8UQX,#90
M7'AB,E1=+R!<># P7'1<>&8S*EQX865<>#%F6EQX.#5<>&$Y7'AE95A<>#ED
M7'AC,%QX8C(E*DQ"7'@P95QX9#1<>&8Y7'@P.'9 5UQX8SA<>&,S7'@X9C1<
M># P7'AE-SY77'@Y-EQX.35<>&-D7'@P8EQX9C9<>&%C:%QX9F)G7'AF8U%<
M>&5B7'@P-4AI7'AE,5QX.3)<>#AE)%QX.#5<)UQX939<>#AB7'@Y.#=<>&8Q
M;5A17'AA,5QX,#9<>&4R7'@Y-EQX9&9<># R7'AE-S,X7'AA95Q<7'AA-UQX
M,6)<>&$Y4%-T:UQX9&1<>#@R7'AB-EQX8V(W7'AD.3] 3UQX.#5=7'AB.%QX
M.#9<>&1F7'AD,EQX8F0S<%QX,#9O7'AE-EQX,#=X7'@Q-#1<>&1D7'AA.31<
M>&,Q=W!<>#@V7'AA,UQX83E<>&1E7'@X,CI<># W05QX.61<>&5E7'AA,5QX
M,&5+,%QX83,L.WUD7'@Y9&!<># T7'AB85QX.&)<>&,V7'AD9C!<>#=F7'AC
M,EQX9C=<>&,P4UM<>&$T7'AE-UQX9C!<;BI<>#$T+W!<;EQX9F%<>&9F7'AF
M94MQ7'AD95QX.&%<>&-D>UQX9C-<>#%B7'AD-%A&7'AC.5QX961<>&0R7&Y<
G;EQX,#!<># P7'@P,%QX,#!)14Y$7'AA94)@7'@X,B<*<#$P"F$N
 
end"""

def as_bytes(bytes_or_text):
    if isinstance(bytes_or_text, bytes):
        return bytes_or_text
    else:
        return bytes_or_text.encode("latin-1")

# retrieve image of numbers from uuencoded pickled objects

c_r = io.BytesIO()
uu.decode(io.BytesIO(numbers_coded), c_r)
c_r.seek(0)

if sys.version_info < (3, ):
    objs = pickle.load(c_r)
else:
    objs = pickle.load(c_r, encoding="latin-1")

im_numbers = [Image.open(io.BytesIO(as_bytes(obj))) for obj in objs]



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
    if filename is None:
        filename = QFileDialog.getOpenFileName(
            None, "Image file", os.path.expanduser("~/Documents"),
            "Image (*.png)")
        if not filename:
            return 1 

    form = MainForm(filename=filename)
    rect = QApplication.desktop().availableGeometry()
    form.show()
    form.raise_()
    return app.exec_()

if __name__ == "__main__":
    sys.exit(main())
