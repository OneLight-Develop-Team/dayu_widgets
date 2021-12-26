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
from collections import namedtuple
from functools import partial

# Import third-party modules
from Qt import QtCore
from Qt import QtGui
from Qt import QtWidgets
from Qt.QtCompat import isValid
from six.moves import cPickle

# Import local modules
from dayu_widgets import dayu_theme
from dayu_widgets.line_edit import MLineEdit
from dayu_widgets.menu import MMenu
from dayu_widgets.mixin import copy_mixin
from dayu_widgets.mixin import cursor_mixin
from dayu_widgets.mixin import property_mixin
from dayu_widgets.mixin import stacked_animation_mixin
from dayu_widgets.push_button import MPushButton
from dayu_widgets.qt import defer
from dayu_widgets.qt import is_signal_connected
from dayu_widgets.tool_button import MToolButton


class MTabEdit(MLineEdit):
    def __init__(self, text, parent):
        super(MTabEdit, self).__init__(text, parent)
        self.bar = parent
        self.editingFinished.connect(self.slot_edit_finish)
        app = QtWidgets.QApplication.instance()
        app.installEventFilter(self)

    def eventFilter(self, receiver, event):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            is_window = receiver.__class__.__name__ == "QWindow"
            if not is_window and receiver is not self:
                self.slot_edit_finish()
        return super(MTabEdit, self).eventFilter(receiver, event)

    def slot_edit_finish(self):
        text = self.text()
        index = self.bar.currentIndex()
        tab_widget = self.bar.parent()
        if isinstance(text, MTabWidget):
            widget = tab_widget.widget(index)
            widget.setWindowTitle(text)
        self.bar.setTabText(index, text)
        self.deleteLater()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.deleteLater()
        return super(MTabEdit, self).keyPressEvent(event)


class MOverlayBase(QtWidgets.QWidget):
    sig_painted = QtCore.Signal(QtGui.QPainter)

    def __init__(self, parent):
        super(MOverlayBase, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        parent.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() & (QtCore.QEvent.Resize | QtCore.QEvent.Show):
            self.setGeometry(obj.rect())
        return False

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        self.sig_painted.emit(painter)
        super(MOverlayBase, self).paintEvent(event)


class MTabOverlay(MOverlayBase):
    def __init__(self, parent):
        super(MTabOverlay, self).__init__(parent)

        self.button = MPushButton()
        self.button.setText(self.tr("Remove"))
        self.button.clicked.connect(parent.deleteLater)
        self.button.setVisible(False)

        layout = QtWidgets.QVBoxLayout()
        inside_layout = QtWidgets.QHBoxLayout()
        inside_layout.addStretch()
        inside_layout.addWidget(self.button)
        inside_layout.addStretch()
        layout.addLayout(inside_layout)
        self.setLayout(layout)


@property_mixin
class MBarOverlay(MOverlayBase):
    def __init__(self, parent):
        super(MBarOverlay, self).__init__(parent)

        self.tab = parent

        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        down_tool = MToolButton().svg("down_line.svg").small()
        down_tool.clicked.connect(self.slot_tab_menu)
        float_tool = MToolButton().svg("float.svg").small()
        float_tool.clicked.connect(lambda *args: parent.slot_dropped_outside())
        close_tool = MToolButton().svg("close_line.svg").small()
        close_tool.clicked.connect(parent.deleteLater)

        layout.addStretch()
        layout.addWidget(down_tool)
        layout.addWidget(float_tool)
        layout.addWidget(close_tool)

        self.opacity_widget = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_widget)
        self.setAutoFillBackground(True)

        self._opacity_anim = QtCore.QPropertyAnimation(self.opacity_widget, b"opacity")
        self.setProperty("animOpacityDuration", 300)
        self.setProperty("animOpacityCurve", "OutCubic")
        self.setProperty("animOpacityStart", 0)
        self.setProperty("animOpacityEnd", 1)
        self.setProperty("opacityAnimatable", False)

    def _set_opacityAnimatable(self, value):
        value = 0 if value else 1
        self.opacity_widget.setOpacity(value)

    def _set_animOpacityDuration(self, value):
        self._opacity_anim.setDuration(value)

    def _set_animOpacityCurve(self, value):
        curve = getattr(QtCore.QEasingCurve, value, None)
        if not curve:
            raise TypeError("Invalid QEasingCurve")
        self._opacity_anim.setEasingCurve(curve)

    def _set_animOpacityStart(self, value):
        self._opacity_anim.setStartValue(value)

    def _set_animOpacityEnd(self, value):
        self._opacity_anim.setEndValue(value)

    def eventFilter(self, obj, event):
        if event.type() in (QtCore.QEvent.Resize, QtCore.QEvent.Paint):
            self.move(obj.bar.width(), 0)
            self.setFixedWidth(max(0, obj.width() - obj.bar.width()))
            self.setFixedHeight(obj.bar.height())
        if self.property("opacityAnimatable"):
            if event.type() == QtCore.QEvent.Enter:
                self._opacity_anim.setDirection(QtCore.QAbstractAnimation.Forward)
                self._opacity_anim.start()
            elif event.type() == QtCore.QEvent.Leave:
                self._opacity_anim.setDirection(QtCore.QAbstractAnimation.Backward)
                self._opacity_anim.start()

        return False

    def slot_tab_menu(self):
        menu = MMenu(parent=self)
        menu.setProperty("searchable", True)
        for index in range(self.tab.count()):
            text = self.tab.tabText(index)
            action = menu.addAction(text)
            action.triggered.connect(partial(self.tab.setCurrentIndex, index))
        menu.exec_(QtGui.QCursor.pos())


@cursor_mixin
class MTabBar(QtWidgets.QTabBar):

    sig_start_drag = QtCore.Signal(int)
    sig_bar_press = QtCore.Signal(QtWidgets.QTabBar)
    sig_bar_menu = QtCore.Signal(int)

    def __init__(self, *args, **kwargs):
        super(MTabBar, self).__init__(*args, **kwargs)
        self.is_dragging = False

        self.setProperty("draggable", True)
        self.setProperty("renameable", True)
        self.setDrawBase(False)
        self.setMouseTracking(True)

        self.tabBarDoubleClicked.connect(self.rename_tab)

        tab_widget = self.parent()
        self.overlay = MBarOverlay(tab_widget)

    def rename_tab(self, index):
        if not self.property("renameable"):
            return

        tab_text = self.tabText(index)
        edit = MTabEdit(tab_text, self)
        edit.setParent(self)
        rect = self.tabRect(index)
        edit.setGeometry(rect)
        edit.show()
        edit.setFocus()

    def tabSizeHint(self, index):
        tab_text = self.tabText(index)
        offset = 70 if self.tabsClosable() else 50
        return QtCore.QSize(
            self.fontMetrics().width(tab_text) + offset,
            self.fontMetrics().height() + 20,
        )

    def mousePressEvent(self, event):
        # type: (QtWidgets.QTabBar,QtGui.QMousePressEvent) -> None
        super(MTabBar, self).mousePressEvent(event)
        if event.buttons() == QtCore.Qt.LeftButton:
            self.is_dragging = True
            self.sig_bar_press.emit(self)

    def mouseMoveEvent(self, event):
        # type: (QtWidgets.QTabBar,QtGui.QMouseMoveEvent) -> None
        super(MTabBar, self).mouseMoveEvent(event)
        index = self.currentIndex()
        condition = self.is_dragging
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
        if self.is_dragging and event.buttons() == QtCore.Qt.LeftButton:
            self.is_dragging = False

    def focusOutEvent(self, event):
        # type: (QtWidgets.QTabBar,QtGui.QFocusOutEvent) -> None
        super(MTabBar, self).focusOutEvent(event)
        if self.is_dragging:
            self.is_dragging = False

    def contextMenuEvent(self, event):
        # type: (QtWidgets.QTabBar,QtGui.QContextMenuEvent) -> None
        super(MTabBar, self).contextMenuEvent(event)
        index = self.tabAt(event.pos())
        self.sig_bar_menu.emit(index)


@copy_mixin
@property_mixin
@stacked_animation_mixin
class MTabWidget(QtWidgets.QTabWidget):

    DIRECTIONS = "E S W N"
    DIRECTION = namedtuple("Direction", DIRECTIONS)(0, 1, 2, 3)
    sig_tab_drag = QtCore.Signal(QtWidgets.QWidget)
    sig_tab_drop = QtCore.Signal(int)
    sig_border_drop = QtCore.Signal(QtWidgets.QWidget, int, int)
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

        self.setMovable(True)
        self.setProperty("hintSize", 5)
        self.setProperty("hintOpacity", 0.5)
        self.setProperty("hintColor", dayu_theme.blue)

        self.setProperty("draggable", False)
        self.setProperty("renameable", False)
        self.setProperty("showBarOverlay", False)
        self.setProperty("autoHideBarOverlay", False)

        self.is_in_container = False
        self.is_new_window = True
        self.is_dragging = False
        self.on_border_index = -1
        self.on_tab_index = -1
        self.rect_data = defaultdict(dict)

        self._validate_tab_count()

    def _set_draggable(self, value):
        self.setAcceptDrops(value)
        self.bar.setProperty("draggable", value)

    def _set_renameable(self, value):
        self.bar.setProperty("renameable", value)

    def _set_showBarOverlay(self, value):
        self.bar.overlay.setVisible(value)

    def _set_autoHideBarOverlay(self, value):
        self.bar.overlay.setProperty("opacityAnimatable", value)

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
        drag.destroyed.connect(partial(self.slot_dropped_outside, index))
        drag.start(QtCore.Qt.MoveAction)

    def slot_bar_press(self, bar):
        self.bar_pixmap = bar.grab(bar.tabRect(bar.currentIndex()))

    def slot_dropped_outside(self, index=-1):

        if not self.is_new_window:
            self.is_new_window = True
            return

        tab = self.copy()
        indices = range(self.count()) if index < 0 else [index]
        for index in reversed(indices):
            widget = self.widget(index)
            label = self.tabText(index)
            widget.setWindowTitle(label)
            tab.insertTab(0, widget, label)

        tab.setWindowFlags(QtCore.Qt.Window)
        tab.setWindowTitle(label)
        tab.show()
        tab.move(QtGui.QCursor.pos())
        tab.raise_()
        tab.setFocus()

        return tab

    def slot_painted(self, painter):
        if not self.count() and not self.is_dragging:
            painter.fillRect(self.rect(), QtCore.Qt.transparent)
            return

        pos = QtGui.QCursor.pos()
        pos = self.mapFromGlobal(pos)

        color = QtGui.QColor(self.property("hintColor"))
        painter.setOpacity(self.property("hintOpacity"))

        rect = self.rect()

        self.on_border_index = -1
        self.on_tab_index = -1

        is_connected = is_signal_connected(self, "sig_border_drop")
        border_rect_list = self.rect_data["border"] if is_connected else []
        for index, rect in enumerate(border_rect_list):
            if rect.contains(pos):
                self.on_border_index = index
                break
        else:
            rect_tab = self.rect_data.get("rect_tab", {})
            for index, (_rect, rect) in enumerate(rect_tab.items()):
                if _rect.contains(pos):
                    self.on_tab_index = index
                    break

            rect_widget = self.rect_data["rect_widget"]
            if isinstance(rect_widget, QtCore.QRect):
                painter.fillRect(rect_widget, color)

        painter.fillRect(rect, color)

    def dragEnterEvent(self, event):
        super(MTabWidget, self).dragEnterEvent(event)
        self.is_dragging = True
        if self._get_drag_data(event):
            rect = self.rect()
            size = self.property("hintSize")
            tl = rect.topLeft()
            br = rect.topRight() + QtCore.QPoint(0, size)
            rect_N = QtCore.QRect(tl, br)
            tl = rect.topRight() - QtCore.QPoint(size, 0)
            br = rect.bottomRight()
            rect_E = QtCore.QRect(tl, br)
            tl = rect.bottomLeft() - QtCore.QPoint(0, size)
            br = rect.bottomRight()
            rect_S = QtCore.QRect(tl, br)
            tl = rect.topLeft()
            br = rect.bottomLeft() + QtCore.QPoint(size, 0)
            rect_W = QtCore.QRect(tl, br)

            self.rect_data["border"] = [rect_E, rect_S, rect_W, rect_N]
            tab_rect = rect_W
            rect_tab = OrderedDict()
            for i in range(self.bar.count()):
                tab_rect = self.bar.tabRect(i)
                tl = tab_rect.topLeft()
                br = QtCore.QPoint(tab_rect.bottomRight().x(), rect.bottomRight().y())
                rect_tab[QtCore.QRect(tl, br)] = tab_rect

            tl = rect.topLeft()
            br = rect.bottomRight()
            rect_widget = QtCore.QRect(tl + QtCore.QPoint(0, tab_rect.height()), br)
            self.rect_data["rect_widget"] = rect_widget

            # NOTES(timmyliang): left area
            tl = tab_rect.topRight()
            br = rect.bottomRight()
            rect = QtCore.QRect(tl, QtCore.QPoint(br.x(), tab_rect.bottomRight().y()))
            rect_tab[QtCore.QRect(tl, br)] = rect
            self.rect_data["rect_tab"] = rect_tab

            event.accept()

    def dragMoveEvent(self, event):
        super(MTabWidget, self).dragMoveEvent(event)
        if self._get_drag_data(event):
            self.overlay.repaint()
            event.accept()

    def dropEvent(self, event):
        super(MTabWidget, self).dropEvent(event)

        self.is_dragging = False
        buff = self._get_drag_data(event)
        index = cPickle.loads(buff)
        source = event.source()
        assert isinstance(source, MTabWidget), "unknown drop error"

        source.is_new_window = False
        label = source.tabText(index)
        widget = source.widget(index)

        if self.on_tab_index >= 0:
            self.insertTab(self.on_tab_index, widget, label)
            self.setCurrentIndex(self.on_tab_index)
            self.sig_tab_drop.emit(self.on_tab_index)
        elif self.on_border_index >= 0:
            self.sig_border_drop.emit(source, index, self.on_border_index)
        self._validate_tab_count()

    def dragLeaveEvent(self, event):
        super(MTabWidget, self).dragLeaveEvent(event)
        self.is_dragging = False
        if not self.count():
            self.overlay.setVisible(True)
        event.accept()

    def tabRemoved(self, *args):
        self._validate_tab_count()
        return super(MTabWidget, self).tabRemoved(*args)

    @defer
    def _validate_tab_count(self):
        count = self.count()
        is_window = self.windowFlags() & QtCore.Qt.Window
        if not count and is_window:
            self.close()
        if self.property("draggable"):
            self.overlay.repaint()
            self.overlay.setVisible(not count)
            self.overlay.button.setVisible(not count)

            # if count == 1:
            #     self.bar.setVisible(False)
            # elif not self.bar.isVisible():
            #     self.bar.setVisible(True)

    def _get_drag_data(self, event):
        data = event.mimeData()
        buff = data.data(self.MINE)
        if not buff:
            return event.ignore()
        return buff
