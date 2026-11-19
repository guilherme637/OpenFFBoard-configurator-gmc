"""SimPro style look for the configurator.

Visual only: applies a dark palette, a Qt style sheet (res/simpro_theme.qss)
and shows the main tabs as a left icon side bar with a page title. It does not change any widget
logic, signal or command sent to the board.
"""

import os
from os.path import join as path_join

import PyQt6.QtCore
import PyQt6.QtGui
import PyQt6.QtWidgets
from PyQt6.QtGui import (
    QColor, QFont, QIcon, QPainter, QPalette, QPen, QPixmap, QPolygonF, QRadialGradient,
)
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QListView, QListWidget, QListWidgetItem,
    QStyle, QStyledItemDelegate, QTabWidget, QVBoxLayout, QWidget,
)

import helper

QSS_FILE = "simpro_theme.qss"

ACCENT = QColor("#C8161D")
TEXT = QColor("#F2F2F2")
MUTED = QColor("#5E616A")


def _palette() -> QPalette:
    pal = QPalette()
    roles = QPalette.ColorRole
    pal.setColor(roles.Window, QColor("#1D1F25"))  # also used as chart background
    pal.setColor(roles.WindowText, TEXT)
    pal.setColor(roles.Base, QColor("#17181C"))
    pal.setColor(roles.AlternateBase, QColor("#1B1D22"))
    pal.setColor(roles.ToolTipBase, QColor("#17181C"))
    pal.setColor(roles.ToolTipText, TEXT)
    pal.setColor(roles.Text, TEXT)
    pal.setColor(roles.Button, QColor("#2B2E36"))
    pal.setColor(roles.ButtonText, TEXT)
    pal.setColor(roles.BrightText, QColor("#FFFFFF"))
    pal.setColor(roles.Link, QColor("#E0242B"))
    pal.setColor(roles.LinkVisited, QColor("#A11016"))
    pal.setColor(roles.Highlight, ACCENT)
    pal.setColor(roles.HighlightedText, QColor("#FFFFFF"))
    pal.setColor(roles.PlaceholderText, QColor("#7A7D86"))
    pal.setColor(roles.Light, QColor("#3C3F48"))
    pal.setColor(roles.Midlight, QColor("#33363F"))
    pal.setColor(roles.Mid, QColor("#2C2F37"))
    pal.setColor(roles.Dark, QColor("#17181C"))
    pal.setColor(roles.Shadow, QColor("#0E0F12"))

    disabled = QPalette.ColorGroup.Disabled
    for role in (roles.WindowText, roles.Text, roles.ButtonText, roles.HighlightedText):
        pal.setColor(disabled, role, MUTED)
    pal.setColor(disabled, roles.Highlight, QColor("#3C3F48"))
    pal.setColor(QPalette.ColorGroup.Inactive, roles.Highlight, ACCENT)
    return pal


def apply_theme(app: PyQt6.QtWidgets.QApplication):
    """Apply the SimPro look to the whole application (all platforms)."""
    app.setStyle("Fusion")
    app.setPalette(_palette())
    font = app.font()
    font.setPointSizeF(10)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)
    try:
        with open(helper.res_path(QSS_FILE), "r", encoding="utf-8") as qss:
            theme_dir = helper.res_path("theme").replace("\\", "/")
            app.setStyleSheet(qss.read().replace("@THEME@", theme_dir))
    except OSError:
        pass  # Missing style sheet: keep palette only


_NAV_ICONS = (
    # (keywords searched in the page class name and tab title, icon name)
    (("serial",), "serial"),
    (("ffbui", "ffb"), "wheel"),
    (("effect",), "effects"),
    (("axis",), "axis"),
    (("encoder",), "encoder"),
    (("analog",), "analog"),
    (("button",), "buttons"),
    (("midi",), "midi"),
    (("can",), "can"),
    (("tmc", "odrive", "vesc", "simplemotion", "rmd", "pwm", "driver", "motor"), "driver"),
)
_icon_cache = {}


def _nav_icon(widget, title) -> QIcon:
    key = (type(widget).__name__ + " " + title).lower()
    name = "default"
    for words, icon_name in _NAV_ICONS:
        if any(w in key for w in words):
            name = icon_name
            break
    if name not in _icon_cache:
        icon = QIcon()
        base = helper.res_path("theme")
        for mode, suffix in ((QIcon.Mode.Normal, ""), (QIcon.Mode.Active, "_active"),
                             (QIcon.Mode.Selected, "_active")):
            icon.addFile(f"{base}/nav_{name}{suffix}.svg", PyQt6.QtCore.QSize(28, 28), mode)
        _icon_cache[name] = icon
    return _icon_cache[name]


class _SideBarSync(PyQt6.QtCore.QObject):
    """Mirrors the main QTabWidget into the side bar list.

    The QTabWidget stays the single source of truth: the rest of the program
    keeps adding/removing/selecting tabs exactly as before, the side bar only
    follows it (and selecting an entry just selects the matching tab).
    """

    def __init__(self, tabs: QTabWidget, nav: QListWidget, title: QLabel):
        super().__init__(tabs)
        self.tabs = tabs
        self.nav = nav
        self.title = title
        self._pages = []
        tabs.currentChanged.connect(self.refresh)
        nav.currentRowChanged.connect(self._nav_selected)
        # Tabs are created/removed at runtime when a board connects. Keep the
        # list in sync with a light periodic comparison (only labels).
        self._timer = PyQt6.QtCore.QTimer(self)
        self._timer.setInterval(300)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()
        self.refresh()

    def _nav_selected(self, row):
        if 0 <= row < self.tabs.count() and row != self.tabs.currentIndex():
            self.tabs.setCurrentIndex(row)

    def refresh(self, *_):
        names = [self.tabs.tabText(i).replace("&", "") for i in range(self.tabs.count())]
        pages = [self.tabs.widget(i) for i in range(self.tabs.count())]
        current_names = [self.nav.item(i).text() for i in range(self.nav.count())]
        self.nav.blockSignals(True)
        if names != current_names or pages != self._pages:
            self._pages = pages
            self.nav.clear()
            for i, name in enumerate(names):
                item = QListWidgetItem(name)
                item.setToolTip(name)
                icon = self.tabs.tabIcon(i)
                item.setIcon(icon if not icon.isNull() else _nav_icon(pages[i], name))
                item.setTextAlignment(PyQt6.QtCore.Qt.AlignmentFlag.AlignHCenter)
                item.setSizeHint(PyQt6.QtCore.QSize(SIDEBAR_WIDTH - 4, 70))
                self.nav.addItem(item)
        idx = self.tabs.currentIndex()
        if self.nav.currentRow() != idx:
            self.nav.setCurrentRow(idx)
        self.nav.blockSignals(False)
        self.title.setText(names[idx] if 0 <= idx < len(names) else "")


SIDEBAR_WIDTH = 92


def style_main_window(window):
    """Cosmetic layout of the main window, like SimPro Manager:
    icon side bar on the left, big page title, info strip on top,
    then the original pages (tabs) and the profile manager.

    Existing widgets are only moved, never replaced or rewired.
    """
    tabs = getattr(window, "tabWidget_main", None)
    if not isinstance(tabs, QTabWidget) or window.findChild(QWidget, "simproSideBar"):
        return
    align = PyQt6.QtCore.Qt.AlignmentFlag

    central = window.takeCentralWidget()  # keeps the widget alive
    if central.layout() is not None:
        central.layout().setContentsMargins(18, 0, 18, 12)
        central.layout().setSpacing(10)

    tabs.tabBar().hide()
    tabs.setDocumentMode(True)

    # ---- Side bar (icons + text, like Home / Devices / Games...)
    side = QWidget()
    side.setObjectName("simproSideBar")
    side.setAttribute(PyQt6.QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
    side.setFixedWidth(SIDEBAR_WIDTH)
    side_layout = QVBoxLayout(side)
    side_layout.setContentsMargins(0, 12, 0, 12)
    side_layout.setSpacing(6)

    logo = QLabel()
    logo.setObjectName("simproLogo")
    logo.setAlignment(align.AlignCenter)
    logo.setPixmap(QIcon(helper.res_path("app.ico")).pixmap(40, 40))
    logo.setToolTip("Open FFBoard Configurator")

    nav = QListWidget()
    nav.setObjectName("simproNav")
    nav.setFrameShape(QFrame.Shape.NoFrame)
    nav.setViewMode(QListView.ViewMode.ListMode)
    nav.setIconSize(PyQt6.QtCore.QSize(28, 28))
    nav.setWordWrap(True)
    nav.setHorizontalScrollBarPolicy(PyQt6.QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    nav.setVerticalScrollBarPolicy(PyQt6.QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    nav.setFocusPolicy(PyQt6.QtCore.Qt.FocusPolicy.NoFocus)
    nav.setItemDelegate(_NavDelegate(nav))
    nav.setMouseTracking(True)
    nav.viewport().setAttribute(PyQt6.QtCore.Qt.WidgetAttribute.WA_Hover, True)

    side_layout.addWidget(logo)
    side_layout.addSpacing(10)
    side_layout.addWidget(nav, 1)

    # ---- Header: big page title + info strip (the former status bar)
    title = QLabel()
    title.setObjectName("simproPageTitle")

    header = QWidget()
    header.setObjectName("simproHeader")
    header.setAttribute(PyQt6.QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
    header_layout = QHBoxLayout(header)
    header_layout.setContentsMargins(14, 8, 14, 8)
    status = getattr(window, "wrapper_status_bar", None)
    if status is not None:
        window.statusBar().removeWidget(status)
        header_layout.addWidget(status)
        status.show()
        window.statusBar().hide()

    content = QWidget()
    content.setObjectName("simproContent")
    content_layout = QVBoxLayout(content)
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.setSpacing(0)
    content_layout.addWidget(title)
    if status is not None:
        wrap = QHBoxLayout()
        wrap.setContentsMargins(18, 0, 18, 12)
        wrap.addWidget(header)
        content_layout.addLayout(wrap)
    content_layout.addWidget(central, 1)

    root = QWidget()
    root.setObjectName("simproRoot")
    root_layout = QHBoxLayout(root)
    root_layout.setContentsMargins(0, 0, 0, 0)
    root_layout.setSpacing(0)
    root_layout.addWidget(side)
    root_layout.addWidget(content, 1)
    window.setCentralWidget(root)

    window._simpro_sidebar_sync = _SideBarSync(tabs, nav, title)


class _NavDelegate(QStyledItemDelegate):
    """Draws a side bar entry as icon above text, red when selected."""

    def paint(self, painter, option, index):
        painter.save()
        rect = option.rect
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hover = bool(option.state & QStyle.StateFlag.State_MouseOver)
        if selected or hover:
            painter.fillRect(rect, QColor("#22252C") if selected else QColor("#1E2026"))
        if selected:
            painter.fillRect(PyQt6.QtCore.QRect(rect.left(), rect.top() + 8, 3, rect.height() - 16), ACCENT)
        icon = index.data(PyQt6.QtCore.Qt.ItemDataRole.DecorationRole)
        if isinstance(icon, QIcon):
            mode = QIcon.Mode.Selected if selected else (QIcon.Mode.Active if hover else QIcon.Mode.Normal)
            pm = icon.pixmap(PyQt6.QtCore.QSize(28, 28), mode)
            painter.drawPixmap(rect.center().x() - 14, rect.top() + 9, pm)
        text = index.data(PyQt6.QtCore.Qt.ItemDataRole.DisplayRole) or ""
        font = QFont(option.font)
        font.setPointSizeF(8.5)
        painter.setFont(font)
        painter.setPen(QColor("#E0242B") if selected else (QColor("#FFFFFF") if hover else QColor("#9A9DA6")))
        text_rect = PyQt6.QtCore.QRect(rect.left() + 4, rect.top() + 40, rect.width() - 8, rect.height() - 42)
        elided = painter.fontMetrics().elidedText(text, PyQt6.QtCore.Qt.TextElideMode.ElideRight, text_rect.width())
        painter.drawText(text_rect, int(PyQt6.QtCore.Qt.AlignmentFlag.AlignHCenter | PyQt6.QtCore.Qt.AlignmentFlag.AlignTop), elided)
        painter.restore()

    def sizeHint(self, option, index):
        return PyQt6.QtCore.QSize(SIDEBAR_WIDTH - 4, 70)


class SimproWheelView(QWidget):
    """Steering wheel picture that turns with the axis angle (display only).

    It only *reads* the angle already shown in the sibling
    ``doubleSpinBox_curdeg`` (updated by the axis page from the encoder).
    If ``res/theme/wheel.png`` exists (e.g. a front photo of your wheel with a
    transparent background) it is used; otherwise a wheel is drawn.
    """

    IMAGE_FILE = "wheel.png"
    _pixmap_cache = {}

    def __init__(self, parent=None):
        super().__init__(parent)
        self._target = 0.0
        self._angle = 0.0
        self._source = None
        self._anim = PyQt6.QtCore.QTimer(self)
        self._anim.setInterval(16)
        self._anim.timeout.connect(self._step)
        self.setSizePolicy(PyQt6.QtWidgets.QSizePolicy.Policy.Expanding,
                           PyQt6.QtWidgets.QSizePolicy.Policy.Fixed)

    # ---- link to the existing angle display
    def _find_source(self):
        p = self.parentWidget()
        while p is not None:
            spin = p.findChild(PyQt6.QtWidgets.QDoubleSpinBox, "doubleSpinBox_curdeg")
            if spin is not None:
                return spin
            p = p.parentWidget()
        return None

    def showEvent(self, event):
        super().showEvent(event)
        if self._source is None:
            self._source = self._find_source()
            if self._source is not None:
                self._source.valueChanged.connect(self.set_angle)
                self._angle = self._target = self._source.value()
        self.update()

    def hideEvent(self, event):
        self._anim.stop()
        super().hideEvent(event)

    def set_angle(self, degrees):
        self._target = float(degrees)
        if not self._anim.isActive() and self.isVisible():
            self._anim.start()

    def _step(self):
        diff = self._target - self._angle
        if abs(diff) < 0.05:
            self._angle = self._target
            self._anim.stop()
        else:
            self._angle += diff * 0.35
        self.update()

    # ---- drawing
    @classmethod
    def _user_pixmap(cls):
        path = helper.res_path(cls.IMAGE_FILE, path_join("res", "theme"))
        if path not in cls._pixmap_cache:
            pm = QPixmap(path) if os.path.exists(path) else QPixmap()
            cls._pixmap_cache[path] = pm
        return cls._pixmap_cache[path]

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        size = min(self.width(), self.height()) - 6
        painter.translate(self.width() / 2, self.height() / 2)

        # fixed red marker on top (where the wheel center should be)
        painter.setPen(PyQt6.QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(ACCENT)
        painter.drawPolygon(QPolygonF([PyQt6.QtCore.QPointF(-5, -size / 2 - 3),
                                       PyQt6.QtCore.QPointF(5, -size / 2 - 3),
                                       PyQt6.QtCore.QPointF(0, -size / 2 + 4)]))

        painter.rotate(self._angle)
        pm = self._user_pixmap()
        if not pm.isNull():
            scaled = pm.scaled(int(size), int(size), PyQt6.QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                               PyQt6.QtCore.Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap(int(-scaled.width() / 2), int(-scaled.height() / 2), scaled)
        else:
            self._draw_wheel(painter, (size - 10) / 2)
        painter.end()

    @staticmethod
    def _draw_wheel(p, r):
        Point = PyQt6.QtCore.QPointF
        Rect = PyQt6.QtCore.QRectF
        rim_w = r * 0.16
        # spokes (behind rim and hub)
        p.setPen(PyQt6.QtCore.Qt.PenStyle.NoPen)
        p.setBrush(QColor("#2B2E36"))
        for ang in (0, 180):
            p.save()
            p.rotate(ang)
            p.drawRoundedRect(Rect(r * 0.25, -r * 0.13, r * 0.65, r * 0.26), r * 0.05, r * 0.05)
            p.restore()
        p.drawRoundedRect(Rect(-r * 0.12, r * 0.2, r * 0.24, r * 0.7), r * 0.05, r * 0.05)

        # rim with soft gradient
        grad = QRadialGradient(Point(0, -r * 0.3), r * 1.3)
        grad.setColorAt(0.0, QColor("#41444D"))
        grad.setColorAt(1.0, QColor("#16171B"))
        pen = QPen(PyQt6.QtGui.QBrush(grad), rim_w)
        pen.setCapStyle(PyQt6.QtCore.Qt.PenCapStyle.FlatCap)
        p.setPen(pen)
        p.setBrush(PyQt6.QtCore.Qt.BrushStyle.NoBrush)
        rim = Rect(-r + rim_w / 2, -r + rim_w / 2, 2 * r - rim_w, 2 * r - rim_w)
        p.drawEllipse(rim)
        # grips (left / right), slightly lighter
        grip = QPen(QColor("#3A3D46"), rim_w * 0.82)
        grip.setCapStyle(PyQt6.QtCore.Qt.PenCapStyle.RoundCap)
        p.setPen(grip)
        p.drawArc(rim, int(150 * 16), int(60 * 16))
        p.drawArc(rim, int(-30 * 16), int(60 * 16))
        # red center stripe at 12 o'clock
        stripe = QPen(ACCENT, rim_w * 1.02)
        stripe.setCapStyle(PyQt6.QtCore.Qt.PenCapStyle.FlatCap)
        p.setPen(stripe)
        p.drawArc(rim, int(86 * 16), int(8 * 16))

        # hub
        hub = QRadialGradient(Point(-r * 0.08, -r * 0.1), r * 0.45)
        hub.setColorAt(0.0, QColor("#3A3D46"))
        hub.setColorAt(1.0, QColor("#1A1C21"))
        p.setPen(QPen(QColor("#4A4D55"), 1.2))
        p.setBrush(PyQt6.QtGui.QBrush(hub))
        p.drawEllipse(Point(0, 0), r * 0.34, r * 0.34)
        # buttons on the hub
        p.setPen(PyQt6.QtCore.Qt.PenStyle.NoPen)
        p.setBrush(QColor("#5A5D66"))
        for x in (-0.2, 0.2):
            p.drawEllipse(Point(r * x, -r * 0.12), r * 0.045, r * 0.045)
        p.setBrush(ACCENT)
        p.drawEllipse(Point(0, r * 0.12), r * 0.07, r * 0.07)


class SimproInfoToggle(PyQt6.QtWidgets.QCheckBox):
    """SimPro-like on/off switch that shows or hides the explanation labels
    (QLabel with the ``simproInfo`` property) of the page it sits on.
    Display only: it never talks to the board."""

    TRACK_W, TRACK_H = 38, 20

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(PyQt6.QtCore.Qt.CursorShape.PointingHandCursor)
        self.toggled.connect(self._apply)

    def _info_labels(self):
        page = self.parentWidget()
        if page is None:
            return []
        return [lbl for lbl in page.findChildren(QLabel) if lbl.property("simproInfo")]

    def _apply(self, on):
        for lbl in self._info_labels():
            lbl.setVisible(bool(on))

    def showEvent(self, event):
        super().showEvent(event)
        self._apply(self.isChecked())

    def sizeHint(self):
        fm = self.fontMetrics()
        return PyQt6.QtCore.QSize(fm.horizontalAdvance(self.text()) + self.TRACK_W + 34,
                                  max(fm.height(), self.TRACK_H) + 8)

    def minimumSizeHint(self):
        return self.sizeHint()

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        on = self.isChecked()
        # info icon + text
        p.setPen(QColor("#C9CBD1") if not on else QColor("#FFFFFF"))
        icon_r = PyQt6.QtCore.QRectF(2, (r.height() - 16) / 2, 16, 16)
        p.drawEllipse(icon_r)
        f = QFont(self.font()); f.setBold(True); f.setPointSizeF(8)
        p.setFont(f)
        p.drawText(icon_r, int(PyQt6.QtCore.Qt.AlignmentFlag.AlignCenter), "i")
        p.setFont(self.font())
        text_r = PyQt6.QtCore.QRect(24, 0, r.width() - self.TRACK_W - 34, r.height())
        p.drawText(text_r, int(PyQt6.QtCore.Qt.AlignmentFlag.AlignVCenter | PyQt6.QtCore.Qt.AlignmentFlag.AlignLeft),
                   self.text())
        # switch
        x = r.width() - self.TRACK_W - 2
        y = (r.height() - self.TRACK_H) / 2
        track = PyQt6.QtCore.QRectF(x, y, self.TRACK_W, self.TRACK_H)
        p.setPen(PyQt6.QtCore.Qt.PenStyle.NoPen)
        p.setBrush(ACCENT if on else QColor("#4A4D55"))
        p.drawRoundedRect(track, self.TRACK_H / 2, self.TRACK_H / 2)
        knob = self.TRACK_H - 6
        kx = x + (self.TRACK_W - knob - 3 if on else 3)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(PyQt6.QtCore.QRectF(kx, y + 3, knob, knob))
        p.end()
