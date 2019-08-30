#!/usr/bin/env python
import sys

from PyQt5.QtCore import QRectF, QSize, QRect, QPoint, QSizeF, QPointF
from PyQt5.QtGui import QColor, QPainter, QPixmap, QImage
from PyQt5.QtWidgets import (
    QApplication,
    QGraphicsScene,
    QGraphicsView,
    QSizePolicy,
    QStyleOptionGraphicsItem,
    QHBoxLayout,
)

from Orange.canvas import config
from orangecanvas.canvas import items
from orangecanvas.registry import (
    global_registry,
    WidgetDescription,
    CategoryDescription,
)
from orangecanvas.registry.qt import QtWidgetRegistry

try:
    # QWebEngineWidgets must be imported before QCoreApplication is created.
    # It will fail with an import error if imported after.
    import PyQt5.QtWebEngineWidgets
except ImportError:
    pass

# init QApp, QScreen
app = QApplication([])

# init full widget registry
config_ = config.Config()
reg = QtWidgetRegistry(parent=app)
widget_discovery = config_.widget_discovery(reg)
widget_discovery.run(config.widgets_entry_points())


def save_widget_icon(
    widget_description: WidgetDescription,
    category: CategoryDescription,
    export_size=QSize(100, 100),
    format="png",
):
    item = items.NodeItem(reg.widget(widget_description.qualified_name))
    item.setWidgetCategory(category)
    iconItem = item.icon_item
    shapeItem = item.shapeItem

    shapeSize = export_size
    iconSize = QSize(export_size.width() * 3 / 4, export_size.height() * 3 / 4)

    rect = QRectF(
        QPointF(-shapeSize.width() / 2, -shapeSize.height() / 2), QSizeF(shapeSize)
    )
    shapeItem.setShapeRect(rect)
    iconItem.setIconSize(iconSize)
    iconItem.setPos(-iconSize.width() / 2, -iconSize.height() / 2)

    image = QImage(export_size, QImage.Format_RGB32)
    image.fill(QColor("#FFFFFF"))
    painter = QPainter(image)

    scene = QGraphicsScene()
    scene.addItem(shapeItem)

    scene.render(painter, QRectF(image.rect()), scene.sceneRect())
    painter.end()

    filename = widget_description.qualified_name + "." + format
    if image.save(filename, format, 100):
        print("Saved " + filename)
    else:
        print("Failed to save " + filename)


def export_all_icons(export_size=QSize(100, 100), format="png"):
    """
    Exports icons of all currently installed widgets. 
    """
    for cat in reg.categories():
        for widget_desc in reg.widgets(cat):
            save_widget_icon(widget_desc, cat, export_size=export_size, format=format)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        export_size = QSize(int(sys.argv[1]), int(sys.argv[1]))
    else:
        export_size = QSize(100, 100)

    if len(sys.argv) > 2:
        format = sys.argv[2]
    else:
        format = "png"

    export_all_icons(export_size, format)
    app.exit(0)
