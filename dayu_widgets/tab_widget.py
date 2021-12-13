#!/usr/bin/env python
# -*- coding: utf-8 -*-
###################################################################
# Author: Mu yanru
# Date  : 2019.2
# Email : muyanru345@163.com
###################################################################

# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import built-in modules
from collections import OrderedDict
from collections import defaultdict
from functools import partial

# Import third-party modules
from Qt import QtCore
from Qt import QtGui
from Qt import QtWidgets
from six.moves import cPickle

# Import local modules
from dayu_widgets import dayu_theme
from dayu_widgets.mixin import cursor_mixin
from dayu_widgets.mixin import property_mixin
from dayu_widgets.mixin import stacked_animation_mixin
from dayu_widgets.splitter import MSplitter
from dayu_widgets.text_edit import MTextEdit


@cursor_mixin
class MTabBar(QtWidgets.QTabBar):

    sig_start_drag = QtCore.Signal(int)
    sig_bar_press = QtCore.Signal(QtWidgets.QTabBar)
    sig_bar_menu = QtCore.Signal(int)

    def __init__(self, parent=None):
        super(MTabBar, self).__init__(parent)
        self.dragging = False

        # self.setAcceptDrops(True)
        self.setProperty("draggable", True)
        self.setDrawBase(False)
        self.setMouseTracking(True)

    def tabSizeHint(self, index):
        tab_text = self.tabText(index)
        if self.tabsClosable():
            return QtCore.QSize(
                self.fontMetrics().width(tab_text) + 70,
                self.fontMetrics().height() + 20,
            )
        else:
            return QtCore.QSize(
                self.fontMetrics().width(tab_text) + 50,
                self.fontMetrics().height() + 20,
            )

    def mousePressEvent(self, event):
        # type: (QtWidgets.QTabBar,QtGui.QMousePressEvent) -> None
        super(MTabBar, self).mousePressEvent(event)
        if event.buttons() == QtCore.Qt.LeftButton:
            self.dragging = True
            self.sig_bar_press.emit(self)

    def mouseMoveEvent(self, event):
        # type: (QtWidgets.QTabBar,QtGui.QMouseMoveEvent) -> None
        super(MTabBar, self).mouseMoveEvent(event)
        index = self.currentIndex()
        condition = self.dragging
        condition &= event.buttons() == QtCore.Qt.LeftButton
        condition &= bool(self.count())
        condition &= index != -1
        # NOTES(timmyliang): trigger when it drag out of tabbar
        condition &= not self.rect().contains(event.pos())
        condition &= bool(self.property("draggable"))

        if condition:
            self.sig_start_drag.emit(index)

    def mouseReleaseEvent(self, event):
        # type: (QtWidgets.QTabBar,QtGui.QMouseReleaseEvent) -> None
        super(MTabBar, self).mouseReleaseEvent(event)
        if self.dragging and event.buttons() == QtCore.Qt.LeftButton:
            self.dragging = False

    def focusOutEvent(self, event):
        # type: (QtWidgets.QTabBar,QtGui.QFocusOutEvent) -> None
        super(MTabBar, self).focusOutEvent(event)
        if self.dragging:
            self.dragging = False

    def contextMenuEvent(self, event):
        # type: (QtWidgets.QTabBar,QtGui.QContextMenuEvent) -> None
        super(MTabBar, self).contextMenuEvent(event)
        index = self.tabAt(event.pos())
        self.sig_tab_menu.emit(index)


class MTabOverlay(QtWidgets.QWidget):

    sig_painted = QtCore.Signal(QtGui.QPainter)

    def __init__(self, parent):
        super(MTabOverlay, self).__init__(parent)
        self.tab = parent
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        flags = QtCore.Qt.WindowTransparentForInput | QtCore.Qt.FramelessWindowHint
        self.setWindowFlags(flags)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        parent.installEventFilter(self)

    def eventFilter(self, obj, event):
        if not obj.isWidgetType():
            return False

        if event.type() & (QtCore.QEvent.Resize | QtCore.QEvent.Show):
            self.setGeometry(obj.rect())

        return False

    def paintEvent(self, event):

        painter = QtGui.QPainter(self)
        self.sig_painted.emit(painter)
        super(MTabOverlay, self).paintEvent(event)


@property_mixin
@stacked_animation_mixin
class MTabWidget(QtWidgets.QTabWidget):
    sig_tab_drag = QtCore.Signal(QtWidgets.QWidget)
    MINE = "application/dayu_tab_data"

    def __init__(self, parent=None):
        super(MTabWidget, self).__init__(parent=parent)

        self.bar = MTabBar(self)
        self.setTabBar(self.bar)
        self.bar.sig_start_drag.connect(self.slot_drag_tab)
        self.bar.sig_bar_press.connect(self.slot_bar_press)
        self.bar.sig_bar_menu.connect(lambda i: print("asd"))

        self.overlay = MTabOverlay(self)
        self.overlay.sig_painted.connect(self.slot_painted)

        # TODO(timmyliang) add MSplitter for resize
        self.splitter = MSplitter()

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.splitter)
        self.setLayout(layout)

        self.setMovable(True)
        self.setProperty("draggable", True)
        self.setProperty("hint_size", 5)
        self.setProperty("hint_opacity", 0.5)
        self.setProperty("hint_color", dayu_theme.blue)

        self.is_new_window = True
        self.is_dragging = False
        self.on_border_index = -1
        self.on_tab_index = -1
        self.rect_data = defaultdict(dict)

    def _set_draggable(self, value):
        self.setAcceptDrops(value)
        self.bar.setProperty("draggable", value)

    @property
    def is_dragging(self):
        return self._is_dragging

    @is_dragging.setter
    def is_dragging(self, value):
        self.overlay.setVisible(value)
        self._is_dragging = value

    def slot_drag_tab(self, index):
        # type: (QtWidgets.QTabWidget,int) -> None
        drag = QtGui.QDrag(self)
        data = QtCore.QMimeData(self)

        # TODO Drag data
        # widget = self.widget(index)
        buff = cPickle.dumps(index)
        data.setData(self.MINE, QtCore.QByteArray(buff))
        drag.setMimeData(data)

        # NOTES(timmyliang): create drag pixmap
        bar_pixmap = self.bar_pixmap

        rect = self.rect()
        rect -= QtCore.QMargins(0, self.bar.height(), rect.width(), rect.height())
        widget_pixmap = self.grab(rect)

        w = widget_pixmap.width()
        h = bar_pixmap.height() + widget_pixmap.height()
        pixmap = QtGui.QPixmap(w, h)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.drawPixmap(QtCore.QPoint(), bar_pixmap)
        painter.drawPixmap(QtCore.QPoint(0, bar_pixmap.height()), widget_pixmap)
        painter.end()

        drag.setPixmap(pixmap)
        drag.destroyed.connect(partial(self.slot_dropped, index))
        drag.start(QtCore.Qt.MoveAction)

    def slot_bar_press(self, bar):
        self.bar_pixmap = bar.grab(bar.tabRect(bar.currentIndex()))

    def slot_dropped(self, index):

        if not self.is_new_window:
            self.is_new_window = True
            return

        widget = self.widget(index)
        label = self.tabText(index)
        tab = self.copy()
        tab.setWindowFlags(QtCore.Qt.Window)
        tab.addTab(widget, label)
        tab.show()
        tab.move(QtGui.QCursor.pos())
        tab.raise_()
        tab.setFocus()

        self._bar_auto_hide(tab)

    def slot_painted(self, painter):

        pos = QtGui.QCursor.pos()
        pos = self.mapFromGlobal(pos)

        rect = self.rect()
        self.on_border_index = -1
        self.on_tab_index = -1
        for index, rect in enumerate(self.rect_data.get("border", [])):
            if rect.contains(pos):
                self.on_border_index = index
                break
        else:
            rect_tab = self.rect_data.get("rect_tab", {})
            for index, (_rect, rect) in enumerate(rect_tab.items()):
                if _rect.contains(pos):
                    self.on_tab_index = index
                    break

        color = QtGui.QColor(self.property("hint_color"))
        painter.setOpacity(self.property("hint_opacity"))
        painter.fillRect(rect, color)

    def dragEnterEvent(self, event):
        super(MTabWidget, self).dragEnterEvent(event)
        self.is_dragging = True
        if self._get_drag_data(event):
            rect = self.rect()
            size = self.property("hint_size")
            tf = rect.topLeft()
            br = rect.topRight() + QtCore.QPoint(0, size)
            rect_N = QtCore.QRect(tf, br)
            tf = rect.topRight() - QtCore.QPoint(size, 0)
            br = rect.bottomRight()
            rect_E = QtCore.QRect(tf, br)
            tf = rect.bottomLeft() - QtCore.QPoint(0, size)
            br = rect.bottomRight()
            rect_S = QtCore.QRect(tf, br)
            tf = rect.topLeft()
            br = rect.bottomLeft() + QtCore.QPoint(size, 0)
            rect_W = QtCore.QRect(tf, br)

            self.rect_data["border"] = [rect_N, rect_E, rect_S, rect_W]
            tab_rect = rect_W
            rect_tab = OrderedDict()
            for i in range(self.bar.count()):
                tab_rect = self.bar.tabRect(i)
                tf = tab_rect.topLeft()
                br = QtCore.QPoint(tab_rect.bottomRight().x(), rect.bottomRight().y())
                rect_tab[QtCore.QRect(tf, br)] = tab_rect

            # NOTES(timmyliang): left area
            tf = tab_rect.topRight()
            br = rect.bottomRight()
            rect = QtCore.QRect(tf, QtCore.QPoint(br.x(), tab_rect.bottomRight().y()))
            rect_tab[QtCore.QRect(tf, br)] = rect
            self.rect_data["rect_tab"] = rect_tab
            event.accept()

    def dragMoveEvent(self, event):
        super(MTabWidget, self).dragMoveEvent(event)
        buff = self._get_drag_data(event)

        self.overlay.repaint()

        event.accept()

    def dropEvent(self, event):
        self.is_dragging = False
        buff = self._get_drag_data(event)
        index = cPickle.loads(buff)
        source = event.source()
        assert isinstance(source, MTabWidget), "unknown drop error"

        source.is_new_window = False
        label = source.tabText(index)
        widget = source.widget(index)

        # TODO add tab base on position index
        if self.on_tab_index >= 0:
            self.insertTab(self.on_tab_index, widget, label)
            self.setCurrentIndex(self.on_tab_index)
        elif self.on_border_index >= 0:
            pass

        self._bar_auto_hide()
        self._bar_auto_hide(source)

    def dragLeaveEvent(self, event):
        self.is_dragging = False
        event.accept()

    def setMovable(self, value):
        self.bar.setMovable(value)

    def _get_drag_data(self, event):
        data = event.mimeData()
        buff = data.data(self.MINE)
        if not buff:
            return event.ignore()
        return buff

    def _bar_auto_hide(self, widget=None):
        widget = widget or self
        count = widget.count()
        is_window = widget.windowFlags() & QtCore.Qt.Window
        if is_window:
            if not count:
                widget.close()
            # elif count == 1:
            #     widget.bar.setVisible(False)
            # elif not widget.bar.isVisible():
            #     widget.bar.setVisible(True)

    def copy(self, parent=None):
        parent = parent or self
        widget = MTabWidget(parent)

        meta = parent.metaObject()
        props = [bytes(p).decode("utf-8") for p in parent.dynamicPropertyNames()]
        props += [meta.property(i).name() for i in range(meta.propertyCount())]

        for prop_name in props:
            if prop_name.startswith("_"):
                continue
            val = parent.property(prop_name)
            if val is not None:
                widget.setProperty(prop_name, val)

        return widget
