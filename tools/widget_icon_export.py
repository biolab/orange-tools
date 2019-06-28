from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QColor, QPainter, QPixmap
from PyQt5.QtWidgets import QApplication, QGraphicsScene, QGraphicsView, QSizePolicy

from Orange.canvas.canvas import items
from Orange.canvas.registry import (
    global_registry,
    WidgetDescription,
    CategoryDescription,
)
from Orange.canvas.registry.qt import QtWidgetRegistry

# init QApp, QScreen
app = QApplication([])

# init full widget registry
reg = global_registry()
reg = QtWidgetRegistry(reg, parent=app)


def save_widget_icon(
    widget_description: WidgetDescription, category: CategoryDescription, format="png"
):
    item = items.NodeItem(reg.widget(widget_description.qualified_name))
    item.setWidgetCategory(category)

    scene = QGraphicsScene()
    view = QGraphicsView(scene)
    view.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
    scene.addItem(item.shapeItem)
    view.show()

    rect = view.viewport().rect()
    pixmap = QPixmap(rect.size())
    pixmap.fill(QColor("#FFFFFF"))
    painter = QPainter(pixmap)
    view.render(painter, QRectF(pixmap.rect()), rect)
    painter.end()

    filename = widget_description.qualified_name + "." + format
    if pixmap.save(filename, format):
        print("Saved " + filename)
    else:
        print("Failed to save " + filename)


def export_all_icons(format="png"):
    """
    Exports icons of all currently installed widgets. 
    """
    for cat in reg.categories():
        for widget_desc in reg.widgets(cat):
            save_widget_icon(widget_desc, cat, format=format)


if __name__ == "__main__":
    export_all_icons()
    app.exit(0)
