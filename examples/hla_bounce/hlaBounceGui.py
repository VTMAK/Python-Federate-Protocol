"""
    Python Federate Protocol © 2025 by MAK Technologies is licensed under CC BY-ND 4.0.
    To view a copy of this license, visit https://creativecommons.org/licenses/by-nd/4.0/
"""
import os
import time

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QTextEdit, QSplitter, QAction, QListWidget, QGroupBox, QDialog,
    QDialogButtonBox, QMessageBox, QWidgetAction, QDoubleSpinBox,
    QComboBox, QGraphicsView, QGraphicsScene
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtSvg import QGraphicsSvgItem

from examples.hla_bounce.ballController import BallController
from examples.hla_bounce.ballData import BallMap
from examples.hla_bounce.regionData import DdmRegionMap

ICON_PREAMBLE = "data\\icons\\"
MENU_ICONS = ["NetworkConnected.svg", "NetworkDisconnected.svg", "NetworkSubscribe.svg", "NetworkUnsubscribe.svg", "ObjectSphereAdd.svg"\
        ,"ObjectSphereRemove.svg", "FileExit.svg", "FileDocument.svg", "SettingsSystem.svg"] 

class BallCanvas(QGraphicsView):
    """
        Canvas with fixed logical coordinate system (world width/height) scaled to the view.

        We keep the scene rect at (0,0,world_width,world_height). Balls use logical coordinates
        directly; we center SVG items on (x,y). The QGraphicsView is auto-fit on resize.
    """

    def __init__(self, ball_data: BallMap, world_width: float, world_height: float):
        super().__init__()
        self.my_Ball_data = ball_data
        self.world_width = world_width
        self.world_height = world_height
        self.scene_obj = QGraphicsScene(0, 0, self.world_width, self.world_height, self)
        self.setScene(self.scene_obj)
        self._items: dict[str, QGraphicsSvgItem] = {}
        self._icons = {
            0: "ObjectSphereRed.svg",
            1: "ObjectSphereBlue.svg",
            2: "ObjectSphereYellow.svg",
            3: "ObjectSphereGreen.svg",
            4: "ObjectSphereViolet.svg",
            5: "ObjectSphereAqua.svg",
        }

    def _new_item(self, color_index: int) -> QGraphicsSvgItem:
        """
            Create a new SVG item for a ball of the given color index.

            Args:
                color_index (int): Color index for the ball (0-5).
            Returns:
                QGraphicsSvgItem: The created SVG item.
        """
        fn = self._icons.get(color_index, "ObjectSphereRed.svg")
        it = QGraphicsSvgItem(ICON_PREAMBLE + fn)
        it.setData(0, color_index)
        return it

    def _place_item(self, item: QGraphicsSvgItem, x: float, y: float):
        """
            Position the given item centered at (x,y).

            Args:
                item (QGraphicsSvgItem): The SVG item to position.
                x (float): The X coordinate to center the item.
                y (float): The Y coordinate to center the item.
            Side Effects:
                Updates the item's position.
        """
        br = item.boundingRect()
        w = br.width() * item.scale()
        h = br.height() * item.scale()
        item.setPos(x - w/2.0, y - h/2.0)

    def sync_from_data(self):
        """
            Sync the scene items from the ball data.

            Adds new items, updates existing ones, and removes deleted ones.
        """
        # Remove deleted
        ids_live = set(self.my_Ball_data.balls.keys())
        for bid in list(self._items.keys() - ids_live):
            itm = self._items.pop(bid)
            self.scene_obj.removeItem(itm)
        # Upsert
        for bid, b in self.my_Ball_data.balls.items():
            item = self._items.get(bid)
            if item is None or item.data(0) != b.color:
                if item is not None:
                    self.scene_obj.removeItem(item)
                item = self._new_item(getattr(b, 'color', 0))
                item.setScale(b.scale / 100.0)
                self.scene_obj.addItem(item)
                self._items[bid] = item
            self._place_item(item, float(getattr(b, 'x', 0.0)), float(getattr(b, 'y', 0.0)))

    def resizeEvent(self, event):
        """
            On resize, refit the scene to the view.

            Args:
                event (QResizeEvent): The resize event.
            Side Effects:
                Updates the view transform.
        """
        super().resizeEvent(event)
        self._fit()

    def showEvent(self, event):
        """
            On show, fit the scene to the view.

            Args:
                event (QShowEvent): The show event.
            Side Effects:
                Updates the view transform.
        """
        super().showEvent(event)
        self._fit()

    def _fit(self):
        """
            Fit the scene rect to the view, keeping aspect ratio.
            Side Effects:
                Updates the view transform.
        """
        rect = self.scene_obj.sceneRect()
        if rect.isNull():
            return
        self.resetTransform()
        mode = getattr(Qt, 'KeepAspectRatio', 1)
        try:
            self.fitInView(rect, mode)
        except Exception:
            self.fitInView(rect, 1)

    def paintEvent(self, event):
        """
            On paint, sync items from data before painting.

            Args:
                event (QPaintEvent): The paint event.
            Side Effects:
                Updates the view transform.
        """
        self.sync_from_data()
        super().paintEvent(event)



class HlaBounceGui(QMainWindow):
    """Main GUI window."""

    # ---- Class-level defaults (modifiable via UI; instances copy on init) ----
    DEFAULT_SPEED: float = 400.0
    DEFAULT_DIRECTION_DEG: float = 12.0  # degrees
    DEFAULT_COLOR: int = 0
    DEFAULT_SIZE: int = 2

    def __init__(self, controller: BallController, Ball_data: BallMap, region_data: DdmRegionMap, title: str = "HLA Bounce"):
        """
            Construct the main GUI window, wiring UI elements, timers, and initial state.

            Args:
                controller (BallController): Simulation / HLA controller backing logic & networking.
                Ball_data (BallMap): Shared ball data container (local + remote objects).
                region_data (DdmRegionMap): Region mapping / DDM placeholder structure.
                title (str): Window title text.
            Side Effects:
                Creates widgets, menus, toolbars, timers, and initializes internal state & logging.
        """
        super().__init__()
        self.controller = controller
        self.ball_data = Ball_data
        self.region_data = region_data
        self.my_ball_count = 0
        self.my_ball_counter = 0
        self.my_object_subpub = True
        self.hla_connected = False
        self.last_update_time = time.time()

        # Instance copies of defaults (change these through UI)
        self.default_speed: float = self.DEFAULT_SPEED
        self.default_direction_deg: float = self.DEFAULT_DIRECTION_DEG
        self.default_color: int = self.DEFAULT_COLOR
        self.default_size: int = self.DEFAULT_SIZE

        self.setWindowTitle(title)
        # Set window icon to Red Ball
        try:
            self.setWindowIcon(QIcon(ICON_PREAMBLE + "ObjectSphereRed.svg"))
        except Exception:
            # Silently ignore if icon can't be loaded
            pass
        self.resize(900, 600)

        # Central layout with splitter
        central = QWidget(self)
        self.setCentralWidget(central)
        layout_root = QVBoxLayout(central)
        orientation = getattr(Qt, 'Horizontal', 1)

        self.splitter = QSplitter(orientation, central)
        layout_root.addWidget(self.splitter)

        # Left panel
        self.left_panel = QWidget(self.splitter)
        left_layout = QVBoxLayout(self.left_panel)
        self.left_panel.setLayout(left_layout)

        # Object lists
        lists_layout = QVBoxLayout()
        self.local_list_label = QLabel("Local Objects")
        self.local_list = QListWidget()
        self.local_list.setMinimumWidth(140)
        self.remote_list_label = QLabel("Remote Objects")
        self.remote_list = QListWidget()
        for label, lst in ((self.local_list_label, self.local_list), (self.remote_list_label, self.remote_list)):
            box = QVBoxLayout()
            box.addWidget(label)
            box.addWidget(lst)
            lists_layout.addLayout(box)
        left_layout.addLayout(lists_layout)

        # Status & counts
        self.status_label = QLabel("Status: Disconnected")
        left_layout.addWidget(self.status_label)
        self.Ball_count_label = QLabel("Balls: 0 (0 local, 0 remote)")
        left_layout.addWidget(self.Ball_count_label)

        # Log group
        self.log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(self.log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(180)
        log_layout.addWidget(self.log_text)
        left_layout.addWidget(self.log_group)

        # Right panel with canvas
        self.right_panel = QWidget(self.splitter)
        right_layout = QVBoxLayout(self.right_panel)
        self.right_panel.setMinimumWidth(500)
        self.right_panel.setMinimumHeight(500)
        self.canvas = BallCanvas(self.ball_data, controller.world_width, controller.world_height)
        right_layout.addWidget(self.canvas)

        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setSizes([400, 500])

        # Menus
        self._create_menus()

        # UI repaint/update timer (decoupled from simulation logic)
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_display)
        self.update_timer.start(16)  # ~60 FPS
        # Simulation timer (match ~60 Hz)
        self.sim_timer = QTimer(self)
        self.sim_timer.timeout.connect(self._update_simulation)
        self.sim_timer.start(16)  # ~60 Hz physics
        # High-frequency non-blocking HLA pump (network callbacks)
        self.hla_pump_timer = QTimer(self)
        self.hla_pump_timer.timeout.connect(self.controller.pump_hla)
        self.hla_pump_timer.start(20)  # 50 Hz lightweight pump (sufficient)

        # State variables (redundant but explicit)
        self.hla_connected = False
        self._time_func = time.perf_counter
        self.last_update_time = self._time_func()

        self.log_message("GUI initialized")

    def _create_menus(self):
        """Build menus and toolbar with duplicate key actions (federation, subscription, options, objects)."""
        mb = self.menuBar()

        # File menu
        m_file = mb.addMenu("&File")
        a_exit = QAction(QIcon(ICON_PREAMBLE + MENU_ICONS[6]), "Exit", self)
        a_exit.triggered.connect(self._exit)
        m_file.addAction(a_exit)
        self.my_exit_button = a_exit

        # Federation menu
        m_fed = mb.addMenu("&Federation")
        a_create_join = QAction(QIcon(ICON_PREAMBLE + MENU_ICONS[0]), "Create/Join", self)
        a_create_join.triggered.connect(self._connect_hla)
        m_fed.addAction(a_create_join)
        self.my_connect_button = a_create_join

        a_resign = QAction(QIcon(ICON_PREAMBLE + MENU_ICONS[1]), "Resign/Destroy", self)
        a_resign.triggered.connect(self._disconnect_hla)
        a_resign.setEnabled(False)
        m_fed.addAction(a_resign)
        self.my_resign_destroy_button = a_resign

        a_opts = QAction(QIcon(ICON_PREAMBLE + MENU_ICONS[8]), "Federate Options", self)
        a_opts.triggered.connect(self._federate_options)
        m_fed.addAction(a_opts)
        self.my_federate_options_button = a_opts

        # Subscription menu
        m_sub = mb.addMenu("&Subscription")
        a_sub = QAction(QIcon(ICON_PREAMBLE + MENU_ICONS[2]), "Subscribe/Publish", self)
        a_sub.triggered.connect(self._subscribe_publish)
        a_sub.setEnabled(False)
        m_sub.addAction(a_sub)
        self.my_sub_pub_button = a_sub

        a_unsub = QAction(QIcon(ICON_PREAMBLE + MENU_ICONS[3]), "Unsubscribe/Unpublish", self)
        a_unsub.triggered.connect(self._unsubscribe)
        a_unsub.setEnabled(False)
        m_sub.addAction(a_unsub)
        self.my_un_sub_pub_button = a_unsub

        # Objects menu
        m_obj = mb.addMenu("&Objects")
        a_add = QAction(QIcon(ICON_PREAMBLE + MENU_ICONS[4]), "Add Ball", self)
        a_add.triggered.connect(self._create_local_Ball)
        a_add.setEnabled(False)
        m_obj.addAction(a_add)
        self.my_create_Balls_button = a_add

        a_remove = QAction(QIcon(ICON_PREAMBLE + MENU_ICONS[5]), "Remove Ball", self)
        a_remove.triggered.connect(self._remove_Ball)
        a_remove.setEnabled(False)
        m_obj.addAction(a_remove)
        self.my_remove_ball_button = a_remove

        m_obj.addSeparator()
        a_apply_all = QAction(QIcon(ICON_PREAMBLE + MENU_ICONS[7]), "Apply Defaults To All Local Balls", self)
        a_apply_all.triggered.connect(self._apply_defaults_all_local)
        m_obj.addAction(a_apply_all)
        self.my_apply_defaults_all_action = a_apply_all

        # Toolbar (duplicate key actions requested)
        toolbar = self.addToolBar("Federation & Objects")
        toolbar.setObjectName("FederationObjectsToolbar")
        # Federation
        toolbar.addAction(a_create_join)
        toolbar.addAction(a_resign)
        # Subscription
        toolbar.addAction(a_sub)
        toolbar.addAction(a_unsub)
        # Options
        toolbar.addAction(a_opts)
        toolbar.addSeparator()
        # Object management
        toolbar.addAction(a_add)
        toolbar.addAction(a_remove)
        toolbar.addSeparator()

        # Speed control
        speed_action = QWidgetAction(self)
        speed_box = QDoubleSpinBox()
        speed_box.setRange(0.0, 10000.0)
        speed_box.setDecimals(1)
        speed_box.setValue(self.default_speed)
        speed_box.setToolTip("Default speed for new Balls")
        self._speed_box = speed_box
        speed_box.valueChanged.connect(lambda v: setattr(self, 'default_speed', float(v)))
        speed_container = QWidget()
        sl = QHBoxLayout(speed_container)
        sl.setContentsMargins(2,0,2,0)
        sl.addWidget(QLabel("Spd"))
        sl.addWidget(speed_box)
        speed_action.setDefaultWidget(speed_container)
        toolbar.addAction(speed_action)

        # Direction control
        dir_action = QWidgetAction(self)
        dir_box = QDoubleSpinBox()
        dir_box.setRange(-3600.0, 3600.0)
        dir_box.setDecimals(1)
        dir_box.setValue(self.default_direction_deg)
        dir_box.setToolTip("Default direction (degrees)")
        self._dir_box = dir_box
        dir_box.valueChanged.connect(lambda v: setattr(self, 'default_direction_deg', float(v)))
        dir_container = QWidget()
        dl = QHBoxLayout(dir_container)
        dl.setContentsMargins(2,0,2,0)
        dl.addWidget(QLabel("Dir°"))
        dl.addWidget(dir_box)
        dir_action.setDefaultWidget(dir_container)
        toolbar.addAction(dir_action)

        # Size control
        size_action = QWidgetAction(self)
        size_box = QSpinBox()
        size_box.setRange(1, 500)
        size_box.setValue(self.default_size)
        size_box.setToolTip("Default size (radius) for new Balls")
        self._size_box = size_box
        size_box.valueChanged.connect(lambda v: setattr(self, 'default_size', int(v)))
        size_container = QWidget()
        szl = QHBoxLayout(size_container)
        szl.setContentsMargins(2,0,2,0)
        szl.addWidget(QLabel("Size"))
        szl.addWidget(size_box)
        size_action.setDefaultWidget(size_container)
        toolbar.addAction(size_action)

        # Color control
        color_action = QWidgetAction(self)
        color_combo = QComboBox()
        self._color_combo = color_combo
        palette_names = {0:"Red",1:"Blue",2:"Yellow",3:"Green",4:"Violet",5:"Acqua"}
        for idx,name in palette_names.items():
            icon_filename = self.canvas._icons.get(idx, "ObjectSphereRed.svg")
            icon = QIcon(ICON_PREAMBLE + icon_filename)
            color_combo.addItem(icon, name, idx)
        ci = color_combo.findData(self.default_color)
        if ci >= 0:
            color_combo.setCurrentIndex(ci)
        color_combo.currentIndexChanged.connect(lambda _ : setattr(self,'default_color', int(color_combo.currentData())))
        color_container = QWidget()
        cl = QHBoxLayout(color_container)
        cl.setContentsMargins(2,0,2,0)
        cl.addWidget(QLabel("Clr"))
        cl.addWidget(color_combo)
        color_action.setDefaultWidget(color_container)
        toolbar.addAction(color_action)

        toolbar.addSeparator()
        toolbar.addAction(a_apply_all)

        # Log popup action (File menu)
        a_log_popup = QAction(QIcon(ICON_PREAMBLE + MENU_ICONS[7]), "Log Popup", self)
        a_log_popup.triggered.connect(self._show_log_popup)
        m_file.addAction(a_log_popup)
        self.my_log_popup_button = a_log_popup

        # View menu (FPS control)
        m_view = mb.addMenu("&View")
        fps_container = QWidget()
        fps_layout = QHBoxLayout(fps_container)
        fps_layout.setContentsMargins(6,2,6,2)
        fps_layout.setSpacing(6)
        fps_layout.addWidget(QLabel("FPS:"))
        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(1,120)
        self.speed_spin.setValue(20)
        self.speed_spin.setToolTip("Display refresh frames per second")
        self.speed_spin.valueChanged.connect(self._change_fps)
        fps_layout.addWidget(self.speed_spin)
        fps_action = QWidgetAction(self)
        fps_action.setDefaultWidget(fps_container)
        m_view.addAction(fps_action)
        self.my_fps_button = fps_action

    def _change_fps(self, fps: int):
        """
            Adjust the UI update timer interval based on the requested frames-per-second value.

            Args:
                fps (int): Desired display refresh rate (frames per second).
            Side Effects:
                Updates internal QTimer interval controlling redraw cadence.
        """
        if not hasattr(self, "update_timer") or self.update_timer is None:
            return
        if fps < 1:
            fps = 1
        interval_ms = int(1000 / fps)
        if self.update_timer.interval() != interval_ms:
            self.update_timer.setInterval(interval_ms)

# ---- Menu / Canvas action handlers ----
    def _connect_hla(self):
        """
            Attempt to establish an RTI (HLA) connection and enable publish/subscribe UI paths.

            Args:
                None
            Side Effects:
                Modifies button enabled states, starts simulation timers, logs status messages.
        """
        self.log_message("Connecting to HLA RTI...")
        self.my_connect_button.setEnabled(False)
        
        try:
            if self.controller.initialize_hla():

                self.hla_connected = True
                self.status_label.setText("Status: Connected")
                self.my_connect_button.setText("Connected")
                self.my_exit_button.setEnabled(True)
                self.my_resign_destroy_button.setEnabled(True)
                self.my_sub_pub_button.setEnabled(True)
                self.my_connect_button.setEnabled(False)
                self.log_message("✓ HLA connection successful")
                self.sim_timer.start(25)
            else:
                self.log_message("✗ HLA connection failed")
                self.my_connect_button.setEnabled(True)
                
        except Exception as e:
            self.log_message(f"✗ HLA connection error: {e}")
            self.my_connect_button.setEnabled(True)

    def _subscribe_publish(self):
        """
            Publish and subscribe to Ball object class attributes (initial sub/pub setup).

            Args:
                None
            Side Effects:
                Enables object creation/removal controls; logs status; may raise/handle exceptions.
        """
        self.log_message("Setting up subscription and publication...")
        self.my_sub_pub_button.setEnabled(False)
        
        try:
            if self.controller.publish_ball():
                self.log_message("✓ Publication setup successful")
            else:
                self.log_message("✗ Publication setup failed")
                self.my_sub_pub_button.setEnabled(True) 
                raise Exception("Publication setup failed")
                
        except Exception as e:
            self.log_message(f"✗Publication error: {e}")
            self.my_sub_pub_button.setEnabled(True)
            raise Exception(e)
        
        try:
            if self.controller.subscribe_ball():
                self.log_message("✓ Subscription setup successful")
            else:
                self.log_message("✗ Subscription setup failed")
                self.my_sub_pub_button.setEnabled(True)
                raise Exception("Subscription setup failed")
                
        except Exception as e:
            self.log_message(f"✗ Subscription error: {e}")
            self.my_sub_pub_button.setEnabled(True)
        self.my_object_subpub = True
        self.my_un_sub_pub_button.setEnabled(True)
        self.my_create_Balls_button.setEnabled(True)

    def _disconnect_hla(self):
        """
            Disconnect from RTI: stop timers, cleanup controller, and reset UI state.

            Side Effects:
                Stops timers, clears connection flags, disables relevant actions, logs results.
        """
        self.log_message("Disconnecting from HLA RTI...")
        
        try:
            self._stop_simulation()
            # Stop RTI pump
            if self.sim_timer.isActive():
                self.sim_timer.stop()
            self.controller.cleanup()
            
            self.hla_connected = False
            self.status_label.setText("Status: Disconnected")
            self.my_connect_button.setText("Connect HLA")
            self.my_connect_button.setEnabled(True)
            self.my_sub_pub_button.setEnabled(False)
            self.my_un_sub_pub_button.setEnabled(False)
            self.my_resign_destroy_button.setEnabled(False)
            self.my_create_Balls_button.setEnabled(False)
            
            self.log_message("✓ HLA disconnected")
            
        except Exception as e:
            self.log_message(f"WARNING: Error during disconnect: {e}")

    def _create_local_Ball(self):
        """
            Instantiate a new locally-owned Ball using current toolbar default parameters.

            Args:
                None
            Side Effects:
                Adds a new ball to local data, updates lists & counters, logs outcome.
        """
        self.my_remove_ball_button.setEnabled(True)
        ball_id = f"{os.getpid()}_{self.my_ball_counter}"
        self.my_ball_counter += 1
        x = 20 + (self.my_ball_count * 30) % (self.controller.world_width - 40)
        y = 20 + ((self.my_ball_count // 5) * 30) % (self.controller.world_height - 40)

        if hasattr(self, '_speed_box'):
            self.default_speed = float(self._speed_box.value())
        if hasattr(self, '_dir_box'):
            self.default_direction_deg = float(self._dir_box.value())
        if hasattr(self, '_size_box'):
            self.default_size = int(self._size_box.value())
        if hasattr(self, '_color_combo'):
            current_data = self._color_combo.currentData()
            if current_data is not None:
                self.default_color = int(current_data)

        if self.controller.create_local_ball(ball_id, x, y):
            new_ball = self.ball_data.get_ball(ball_id)
            if new_ball is not None:
                import math as _m
                rad = _m.radians(self.default_direction_deg)
                new_ball.dx = self.default_speed * _m.cos(rad)
                new_ball.dy = self.default_speed * _m.sin(rad)
                new_ball.color = self.default_color
                new_ball.scale = self.default_size * 5
            self.my_ball_count += 1
            self.log_message(f"✓ Added a local Ball (speed={self.default_speed}, dir={self.default_direction_deg}°, color={self.default_color}, size={self.default_size})")
            # Refresh object lists to show new local Ball id
            self._refresh_object_lists()
        else:
            self.log_message("✗ Failed to add local Ball")

    def _remove_Ball(self):
        """
            Remove the currently selected locally-owned Ball from the simulation.

            Args:
                None
            Side Effects:
                Updates data store, refreshes lists, logs removal or warnings.
        """
        current = self.local_list.currentItem()
        if not current:
            return
        Ball_id = current.text()
        try:
            if self.controller.remove_local_ball(Ball_id):
                self.log_message(f"Removed Ball {Ball_id}")
                if self.ball_data.get_ball(Ball_id) is not None:
                    self.ball_data.remove_ball(Ball_id)
                if len(self.ball_data.local_balls) == 0:
                    self.my_remove_ball_button.setEnabled(False)
                self._refresh_object_lists()
                self.my_ball_count = max(0, self.my_ball_count - 1)
        except Exception as e:
            self.log_message(f"WARNING: remove_Ball error: {e}")

    def _exit(self):
        """
            Perform controller cleanup (invoked via File -> Exit menu action).

            Args:
                None
            Side Effects:
                Calls controller.cleanup to release RTI / simulation resources.
        """
        self.controller.cleanup()

    def _federate_options(self):
        """
            Display a placeholder federate options dialog (stub implementation).

            Args:
                None
            Side Effects:
                Shows modal information dialog.
        """
        QMessageBox.information(self, "Federate Options", "No additional options implemented yet.")

    def _unsubscribe(self):
        """
            Placeholder handler for unsubscribe/unpublish operations (not implemented).

            Args:
                None
            Side Effects:
                Logs placeholder message.
        """
        self.log_message("Unsubscribe invoked (not implemented)")

    def _show_log_popup(self):
        """
            Show accumulated log output in a modal dialog for easier reading.

            Args:
                None
            Side Effects:
                Creates & executes a modal dialog; blocks until closed.
        """
        dlg = QDialog(self)
        dlg.setWindowTitle("Log Output")
        v = QVBoxLayout(dlg)
        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setPlainText(self.log_text.toPlainText())
        v.addWidget(txt)
        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(dlg.reject)
        btns.accepted.connect(dlg.accept)
        v.addWidget(btns)
        dlg.resize(500,400)
        dlg.exec_()
        
    def _update_simulation(self):
        """
            Advance simulation (positions & physics) if subscribed/published and connected.

            Args:
                None
            Side Effects:
                Updates positions, refreshes object lists if needed, triggers display update.
        """
        current_time = getattr(self, '_time_func', time.perf_counter)()
        dt = current_time - self.last_update_time

        if self.controller.list_refresh_needed:
            self._refresh_object_lists()
            self.controller.list_refresh_needed = False

        if self.my_object_subpub and self.hla_connected:
            self.last_update_time = current_time
            self.controller.update_simulation(dt)
            self._update_display()

    def _update_display(self):
        """
            Refresh canvas visuals and update ball counts label.

            Args:
                None
            Side Effects:
                Repaints canvas and updates counts label; suppresses count errors silently.
        """
        self.canvas.my_Ball_data = self.ball_data
        self.canvas.sync_from_data()
        self.canvas.update()
        # Update counts label
        try:
            total = len(self.ball_data.balls)
            local = len(self.ball_data.local_balls)
            remote = len(self.ball_data.remote_balls)
            self.Ball_count_label.setText(f"Balls: {total} ({local} local, {remote} remote)")
        except Exception:
            pass
        
    def log_message(self, message: str):
        """
            Append a timestamped log line to the GUI log view and autoscroll to bottom.

            Args:
                message (str): Message text (no newline required).
            Side Effects:
                Mutates QTextEdit contents and cursor position.
        """
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.log_text.append(formatted_message)
        
        # Auto-scroll to bottom
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.End)
        self.log_text.setTextCursor(cursor)

    def _stop_simulation(self):
        """
            Stop active timers to halt UI refresh, simulation stepping, and HLA pump.

            Args:
                None
            Side Effects:
                Stops QTimers if active.
        """
        for t in (getattr(self, 'update_timer', None), getattr(self, 'sim_timer', None), getattr(self, 'hla_pump_timer', None)):
            if t is not None and t.isActive():
                t.stop()

    # ----------------- New default attribute handlers -----------------
    def _apply_defaults_all_local(self):
        """
            Apply current default speed, direction, color, and size settings to all local balls.

            Args:
                None
            Side Effects:
                Mutates properties of locally-owned ball objects; logs operation summary.
        """
        import math as _m
        rad = _m.radians(self.default_direction_deg)
        vx = self.default_speed * _m.cos(rad)
        vy = self.default_speed * _m.sin(rad)
        updated = 0
        for b in self.ball_data.balls.values():
            if getattr(b, 'is_owned', False):  # local Ball
                b.dx = vx
                b.dy = vy
                b.color = self.default_color
                b.scale = self.default_size
                updated += 1
        self.log_message(f"Applied defaults to {updated} local Balls")
        # No structural change, but counts might change if size implies visibility later
        self._update_display()

    # ----------------- Object list refresh helper -----------------
    def _refresh_object_lists(self):
        """
            Update GUI list widgets showing local and remote ball IDs while preserving selection.

            Args:
                None
            Side Effects:
                Clears and repopulates QListWidgets; updates ball count label; suppresses minor errors.
        """
        if not hasattr(self, 'local_list') or not hasattr(self, 'remote_list'):
            return
        # Preserve current selection ids (if any) to restore after refresh
        cur_local_item = self.local_list.currentItem()
        current_local = cur_local_item.text() if cur_local_item else None
        cur_remote_item = self.remote_list.currentItem()
        current_remote = cur_remote_item.text() if cur_remote_item else None
        self.local_list.clear()
        for bid in sorted(self.ball_data.local_balls.keys(), key=lambda x: (len(x), x)):
            self.local_list.addItem(bid)
        self.remote_list.clear()
        for bid in sorted(self.ball_data.remote_balls.keys(), key=lambda x: (len(x), x)):
            self.remote_list.addItem(bid)
        # Restore selection if id still present
        match_flag = getattr(Qt, 'MatchExactly', getattr(Qt, 'MatchFixedString', 0))
        if current_local:
            try:
                matches = self.local_list.findItems(current_local, match_flag)
            except Exception:
                matches = []
            if matches:
                self.local_list.setCurrentItem(matches[0])
        if current_remote:
            try:
                matches = self.remote_list.findItems(current_remote, match_flag)
            except Exception:
                matches = []
            if matches:
                self.remote_list.setCurrentItem(matches[0])
        # Update counts immediately
        if hasattr(self, 'Ball_count_label'):
            try:
                total = len(self.ball_data.balls)
                local = len(self.ball_data.local_balls)
                remote = len(self.ball_data.remote_balls)
                self.Ball_count_label.setText(f"Balls: {total} ({local} local, {remote} remote)")
            except Exception:
                pass