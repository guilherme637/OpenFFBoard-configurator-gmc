"""SimPro style look for the configurator.

Visual only: applies a dark palette, a Qt style sheet (res/simpro_theme.qss)
and shows the main tabs as a left side bar with a page title. It does not change any widget
logic, signal or command sent to the board.
"""

import PyQt6.QtCore
import PyQt6.QtWidgets
from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QTabWidget, QVBoxLayout, QWidget,
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
        current_names = [self.nav.item(i).text() for i in range(self.nav.count())]
        self.nav.blockSignals(True)
        if names != current_names:
            self.nav.clear()
            for i, name in enumerate(names):
                item = QListWidgetItem(name)
                item.setToolTip(name)
                icon = self.tabs.tabIcon(i)
                if not icon.isNull():
                    item.setIcon(icon)
                self.nav.addItem(item)
        idx = self.tabs.currentIndex()
        if self.nav.currentRow() != idx:
            self.nav.setCurrentRow(idx)
        self.nav.blockSignals(False)
        self.title.setText(names[idx] if 0 <= idx < len(names) else "")


def style_main_window(window):
    """Cosmetic layout of the main window: SimPro like side bar + page title.

    The original central widget (tabs, profile manager...) is kept untouched
    and only placed next to the side bar.
    """
    tabs = getattr(window, "tabWidget_main", None)
    if not isinstance(tabs, QTabWidget) or window.findChild(QWidget, "simproSideBar"):
        return

    central = window.takeCentralWidget()  # keeps the widget alive
    if central.layout() is not None:
        central.layout().setContentsMargins(10, 0, 10, 4)
        central.layout().setSpacing(6)

    tabs.tabBar().hide()
    tabs.setDocumentMode(True)

    # Side bar
    side = QWidget()
    side.setObjectName("simproSideBar")
    side.setAttribute(PyQt6.QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
    side.setFixedWidth(176)
    side_layout = QVBoxLayout(side)
    side_layout.setContentsMargins(0, 0, 0, 10)
    side_layout.setSpacing(0)

    logo = QLabel("OpenFFBoard")
    logo.setObjectName("simproLogo")
    logo.setAlignment(PyQt6.QtCore.Qt.AlignmentFlag.AlignCenter)
    sub = QLabel("Configurator")
    sub.setObjectName("simproLogoSub")
    sub.setAlignment(PyQt6.QtCore.Qt.AlignmentFlag.AlignCenter)

    nav = QListWidget()
    nav.setObjectName("simproNav")
    nav.setFrameShape(QFrame.Shape.NoFrame)
    nav.setHorizontalScrollBarPolicy(PyQt6.QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    nav.setFocusPolicy(PyQt6.QtCore.Qt.FocusPolicy.NoFocus)
    nav.setTextElideMode(PyQt6.QtCore.Qt.TextElideMode.ElideRight)

    side_layout.addWidget(logo)
    side_layout.addWidget(sub)
    side_layout.addWidget(nav, 1)

    # Content: page title + original central widget
    content = QWidget()
    content_layout = QVBoxLayout(content)
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.setSpacing(0)
    title = QLabel()
    title.setObjectName("simproPageTitle")
    content_layout.addWidget(title)
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
