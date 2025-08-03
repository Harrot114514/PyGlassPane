import sys
import json
import os
from PyQt5.QtCore import Qt, QPoint, QSettings, QPropertyAnimation, QEasingCurve, QUrl
from PyQt5.QtGui import QIcon, QColor, QIntValidator
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QFontDatabase, QFont
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QLineEdit, QListWidget, QStackedWidget, QSystemTrayIcon, 
                             QMenu, QStyle, QDialog, QSlider, QColorDialog, QCheckBox, QSizePolicy,
                             QMessageBox)
from PyQt5.QtWidgets import QListWidgetItem  # 添加这一行
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings

# 配置文件路径
CONFIG_FILE = "web_widgets_config.json"

class DraggableWebView(QWebEngineView):
    def __init__(self, url, opacity=1.0, bg_color="#00000000", x=100, y=100, width=400, height=300, always_on_top=True, parent=None):
        super().__init__(parent)
        self.setUrl(QUrl(url))
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet(f"background-color: {bg_color}; border-radius: 10px;")
        self.setWindowOpacity(opacity)
        
        # 启用透明背景
        self.page().setBackgroundColor(QColor(bg_color))
        self.settings().setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        
        # 保存置顶状态
        self.always_on_top = always_on_top
        
        # 设置窗口标志
        self.update_flags()
        
        # 设置位置和大小
        self.setGeometry(x, y, width, height)
        
        # 拖动变量
        self.dragging = False
        self.offset = QPoint()
        
    def update_flags(self):
        """更新窗口标志，特别是置顶状态"""
        flags = Qt.FramelessWindowHint | Qt.Tool
        if self.always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        # 需要重新显示窗口以应用新标志
        self.show()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.globalPos() - self.pos()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(event.globalPos() - self.offset)
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        self.dragging = False
        super().mouseReleaseEvent(event)
    
    def contextMenuEvent(self, event):
        # 创建自定义右键菜单
        menu = QMenu(self)
        
        # 置顶切换菜单项
        pin_action = menu.addAction("置顶" if not self.always_on_top else "取消置顶")
        pin_action.triggered.connect(self.toggle_pin)
        
        # 关闭菜单项
        close_action = menu.addAction("关闭")
        close_action.triggered.connect(self.close)
        
        menu.exec_(event.globalPos())
    
    def toggle_pin(self):
        self.always_on_top = not self.always_on_top
        self.update_flags()

class SettingsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("透明网页小部件-设置窗口")
        self.setGeometry(100, 100, 800, 600)
        self.setMinimumSize(700, 500)
        self.active_web_views = []
        self.setup_ui()
        self.load_config()
        self.setStyleSheet("""
    QMainWindow {
        background-color: #2d3e50;
        color: #f0f0f0;
        font-family: 'Segoe UI', Arial;
    }
    QWidget {
        background-color: #3c4f65;
        border-radius: 10px;
        padding: 10px;
    }
    QPushButton {
        background-color: #4a9bdf;
        color: white;
        border: none;
        padding: 10px 15px;
        border-radius: 5px;
        font-size: 14px;
        font-weight: 500;
    }
    QPushButton:hover {
        background-color: #3a8bcf;
    }
    QPushButton#removeBtn {
        background-color: #f05d4d;
    }
    QPushButton#removeBtn:hover {
        background-color: #e04d3d;
    }
    QLineEdit, QListWidget {
        background-color: #ffffff;
        color: #333333;
        border: 1px solid #5a9bdf;
        border-radius: 5px;
        padding: 8px;
        font-size: 14px;
    }
    QLabel {
        font-size: 14px;
        padding: 5px 0;
        color: #f0f0f0;
    }
    QSlider::groove:horizontal {
        height: 8px;
        background: #8f9ca8;
        border-radius: 4px;
    }
    QSlider::handle:horizontal {
        background: #4a9bdf;
        width: 18px;
        margin: -5px 0;
        border-radius: 9px;
    }
    QCheckBox {
        font-size: 14px;
        spacing: 8px;
        color: #f0f0f0;
    }
    QColorDialog {
        background-color: #2d3e50;
        color: #f0f0f0;
    }
    QListWidget::item {
        padding: 8px;
        height: 35px;
    }
    
    QListWidget::item:selected {
        background-color: #4a9bdf;
        color: white;
    }
""")
        
        self.web_widgets = []
        self.tray_icon = None
        self.active_web_views = []  # 存储活动的网页视图
        self.global_pinned = True  # 添加全局置顶状态
        self.setup_ui()
        self.load_config()

        
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
    
        # 左侧列表
        left_panel = QWidget()
        left_panel.setMaximumWidth(200)
        left_layout = QVBoxLayout(left_panel)
    
        self.widget_list = QListWidget()
        self.widget_list.setSelectionMode(QListWidget.SingleSelection)
        self.widget_list.setEditTriggers(QListWidget.DoubleClicked | QListWidget.EditKeyPressed)  # 允许编辑
        self.widget_list.setMinimumWidth(180)  # 设置最小宽度
        self.widget_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 尺寸策略
        left_layout.addWidget(QLabel("网页小部件列表"))
        left_layout.addWidget(self.widget_list)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("添加")
        self.add_btn.clicked.connect(self.add_widget)
        self.remove_btn = QPushButton("删除")
        self.remove_btn.setObjectName("removeBtn")
        self.remove_btn.clicked.connect(self.remove_widget)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.remove_btn)
        left_layout.addLayout(btn_layout)
    
        # 右侧设置
        self.settings_stack = QStackedWidget()
    
        # 主设置页
        main_settings = QWidget()
        self.main_layout_settings = QVBoxLayout(main_settings)  # 先创建布局
    
        # 现在可以安全使用 self.main_layout_settings
        self.url_edit = QLineEdit("https://www.example.com")
        self.main_layout_settings.addWidget(QLabel("网页URL:"))
        self.main_layout_settings.addWidget(self.url_edit)
    
        # 透明度设置
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("透明度:"))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.setValue(80)
        opacity_layout.addWidget(self.opacity_slider)
        self.opacity_label = QLabel("80%")
        opacity_layout.addWidget(self.opacity_label)
        self.opacity_slider.valueChanged.connect(
            lambda v: self.opacity_label.setText(f"{v}%"))
        self.main_layout_settings.addLayout(opacity_layout)
    
        # 背景色设置
        bg_color_layout = QHBoxLayout()
        bg_color_layout.addWidget(QLabel("背景颜色:"))
        self.bg_color_btn = QPushButton("选择")
        self.bg_color_btn.clicked.connect(self.choose_bg_color)
        bg_color_layout.addWidget(self.bg_color_btn)
        self.bg_color_preview = QLabel()
        self.bg_color_preview.setFixedSize(30, 30)
        self.bg_color_preview.setStyleSheet("background-color: #00000000; border: 1px solid #ccc;")
        bg_color_layout.addWidget(self.bg_color_preview)
        bg_color_layout.addStretch()
        self.main_layout_settings.addLayout(bg_color_layout)
    
        # 窗口位置
        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("位置:"))
        self.x_edit = QLineEdit("100")
        self.x_edit.setPlaceholderText("X")
        self.x_edit.setValidator(QIntValidator(0, 5000))
        self.y_edit = QLineEdit("100")
        self.y_edit.setPlaceholderText("Y")
        self.y_edit.setValidator(QIntValidator(0, 5000))
        pos_layout.addWidget(self.x_edit)
        pos_layout.addWidget(self.y_edit)
        self.main_layout_settings.addLayout(pos_layout)

        # 窗口大小
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("大小:"))
        self.width_edit = QLineEdit("400")
        self.width_edit.setPlaceholderText("宽度")
        self.width_edit.setValidator(QIntValidator(100, 5000))
        self.height_edit = QLineEdit("300")
        self.height_edit.setPlaceholderText("高度")
        self.height_edit.setValidator(QIntValidator(100, 5000))
        size_layout.addWidget(self.width_edit)
        size_layout.addWidget(self.height_edit)
        self.main_layout_settings.addLayout(size_layout)

        self.always_on_top = QCheckBox("始终置顶")
        self.always_on_top.setChecked(True)
        self.main_layout_settings.addWidget(self.always_on_top)

        # 全局置顶控件 - 现在可以安全添加
        self.global_always_on_top = QCheckBox("所有网页置顶")
        self.global_always_on_top.setChecked(True)
        self.global_always_on_top.stateChanged.connect(self.toggle_all_pin)
        self.main_layout_settings.addWidget(self.global_always_on_top)

        self.main_layout_settings.addStretch()

        # 应用按钮
        self.apply_btn = QPushButton("应用设置")
        self.apply_btn.clicked.connect(self.apply_settings)
        self.apply_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.main_layout_settings.addWidget(self.apply_btn)

        # 启动按钮
        self.launch_btn = QPushButton("启动网页小部件")
        self.launch_btn.setStyleSheet("background-color: #2ecc71; font-weight: bold;")
        self.launch_btn.clicked.connect(self.launch_widgets)
        self.main_layout_settings.addWidget(self.launch_btn)

        # 关闭所有按钮
        self.close_all_btn = QPushButton("关闭所有网页")
        self.close_all_btn.setStyleSheet("background-color: #e74c3c;")
        self.close_all_btn.clicked.connect(self.close_all_widgets)
        self.main_layout_settings.addWidget(self.close_all_btn)

        self.settings_stack.addWidget(main_settings)

        # 添加左右面板
        main_layout.addWidget(left_panel)
        main_layout.addWidget(self.settings_stack)

        # 连接列表选择事件
        self.widget_list.currentRowChanged.connect(self.show_widget_settings)
        self.widget_list.itemChanged.connect(self.rename_widget)

    def toggle_all_pin(self, state):
        """切换所有网页小部件的置顶状态"""
        self.global_pinned = (state == Qt.Checked)
        self.global_always_on_top.setChecked(self.global_pinned)

        # 确保 active_web_views 存在且不为空
        if not hasattr(self, 'active_web_views') or not self.active_web_views:
            return
        
        # 安全地遍历所有活动网页视图
        for view in self.active_web_views:
            # 检查对象是否有效且具有必要属性
            if view and hasattr(view, 'always_on_top') and hasattr(view, 'update_flags'):
                view.always_on_top = self.global_pinned
                view.update_flags()

    def add_widget(self):
        count = self.widget_list.count()
        item = QListWidgetItem(f"网页小部件 {count+1}")
        item.setFlags(item.flags() | Qt.ItemIsEditable)  # 设置可编辑
        self.widget_list.addItem(item)
        self.widget_list.setCurrentItem(item)
        
        # 添加到配置列表
        self.web_widgets.append({
            "name": f"网页小部件 {count+1}",  # 添加名称字段
            "url": "https://www.example.com",
            "opacity": 0.8,
            "bg_color": "#00000000",
            "x": 100,
            "y": 100,
            "width": 400,
            "height": 300,
            "always_on_top": True
        })

    def rename_widget(self, item):
        """重命名小部件"""
        row = self.widget_list.row(item)
        if 0 <= row < len(self.web_widgets):
            new_name = item.text()
            self.web_widgets[row]["name"] = new_name
            self.save_config()
            
            # 更新列表项显示
            self.widget_list.item(row).setText(new_name)

    def remove_widget(self):
        row = self.widget_list.currentRow()
        if row >= 0:
            self.widget_list.takeItem(row)
            self.web_widgets.pop(row)
        
    def show_widget_settings(self, index):
        if index >= 0 and index < len(self.web_widgets):
            widget = self.web_widgets[index]
            self.url_edit.setText(widget["url"])
            self.opacity_slider.setValue(int(widget["opacity"] * 100))
            self.bg_color_preview.setStyleSheet(f"background-color: {widget['bg_color']};")
            self.x_edit.setText(str(widget["x"]))
            self.y_edit.setText(str(widget["y"]))
            self.width_edit.setText(str(widget["width"]))
            self.height_edit.setText(str(widget["height"]))
            self.always_on_top.setChecked(widget["always_on_top"])
        
    def apply_settings(self):
        index = self.widget_list.currentRow()
        if index >= 0:
            try:
                # 验证输入
                x = int(self.x_edit.text())
                y = int(self.y_edit.text())
                width = int(self.width_edit.text())
                height = int(self.height_edit.text())
                
                if width < 100 or height < 100:
                    raise ValueError("窗口大小不能小于100x100")
                    
                self.web_widgets[index] = {
                    "name": self.web_widgets[index]["name"],  # 保留名称
                    "url": self.url_edit.text(),
                    "opacity": self.opacity_slider.value() / 100,
                    "bg_color": self.bg_color_preview.styleSheet().split(":")[1].split(";")[0].strip(),
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height,
                    "always_on_top": self.always_on_top.isChecked()
                }
                if index < len(self.active_web_views) and self.active_web_views[index]:
                    self.active_web_views[index].always_on_top = self.always_on_top.isChecked()
                    self.active_web_views[index].update_flags()
            
                self.show_notification("设置已保存", f"网页小部件 {index+1} 设置已更新")
            except Exception as e:
                QMessageBox.warning(self, "输入错误", f"无效的输入值: {str(e)}")
                self.show_notification("设置已保存", f"网页小部件 {index+1} 设置已更新")
            except Exception as e:
                QMessageBox.warning(self, "输入错误", f"无效的输入值: {str(e)}")
        
    def choose_bg_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            # 使用RGBA格式保存颜色信息
            rgba = f"rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()})"
            self.bg_color_preview.setStyleSheet(f"background-color: {rgba};")
        
    def launch_widgets(self):
        try:
            self.save_config()
            self.close_all_widgets()  # 关闭之前的所有网页
            
            # 创建所有网页小部件
            for widget in self.web_widgets:
                web_view = DraggableWebView(
                    url=widget["url"],
                    opacity=widget["opacity"],
                    bg_color=widget["bg_color"],
                    x=widget["x"],
                    y=widget["y"],
                    width=widget["width"],
                    height=widget["height"],
                    always_on_top=widget["always_on_top"]
                )
                web_view.show()
                self.active_web_views.append(web_view)

                # 添加到已打开列表
                item = QListWidgetItem(widget["name"])
                item.setData(Qt.UserRole, i)  # 存储索引
                self.opened_widgets_list.addItem(item)
            
            # 隐藏主窗口到系统托盘
            self.hide_to_tray()
            self.show_notification("启动成功", f"已启动 {len(self.web_widgets)} 个网页小部件")
        except Exception as e:
            QMessageBox.critical(self, "启动错误", f"无法启动网页小部件: {str(e)}")
        
    def close_all_widgets(self):
        """关闭所有活动的网页视图"""
        for web_view in self.active_web_views:
            web_view.close()
        self.active_web_views = []
        
    def hide_to_tray(self):
        # 如果托盘图标已存在，直接隐藏窗口
        if self.tray_icon:
            self.hide()
            return
        
        # 创建系统托盘
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(self.style().standardIcon(QStyle.SP_ComputerIcon)))
    
        # 创建托盘菜单
        tray_menu = QMenu()
    
        # 添加菜单项
        show_action = tray_menu.addAction("显示设置")
        show_action.triggered.connect(self.show_from_tray)
    
        restart_action = tray_menu.addAction("重启网页小部件")
        restart_action.triggered.connect(self.launch_widgets)
    
        close_all_action = tray_menu.addAction("关闭所有网页")
        close_all_action.triggered.connect(self.close_all_widgets)
    
        # 添加全局置顶菜单项
        pin_action = tray_menu.addAction("所有网页置顶" if not self.global_pinned else "取消所有置顶")
        pin_action.triggered.connect(self.toggle_all_pin_from_tray)
    
        tray_menu.addSeparator()
    
        exit_action = tray_menu.addAction("退出")
        exit_action.triggered.connect(self.close_app)

        # 设置菜单
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.tray_icon_activated)

        # 隐藏窗口
        self.hide()

    def toggle_all_pin_from_tray(self):
        self.global_pinned = not self.global_pinned
        self.global_always_on_top.setChecked(self.global_pinned)
        self.toggle_all_pin(Qt.Checked if self.global_pinned else Qt.Unchecked)
    
        
    def animate_window(self, window, show):
        # 如果窗口已经显示，直接返回
        if show and window.isVisible():
            return
            
        animation = QPropertyAnimation(window, b"windowOpacity")
        animation.setDuration(300)
        animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        if show:
            window.setWindowOpacity(0.0)  # 确保从透明开始
            window.show()
            animation.setStartValue(0.0)
            animation.setEndValue(1.0)
        else:
            animation.setStartValue(1.0)
            animation.setEndValue(0.0)
            animation.finished.connect(window.hide)
        
        animation.start()
        
    def show_from_tray(self):
        self.setWindowOpacity(1.0)
        self.show()
        self.activateWindow()
        self.raise_()
        
    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_from_tray()
        
    def show_notification(self, title, message):
        if self.tray_icon:
            self.tray_icon.showMessage(title, message, QSystemTrayIcon.Information, 2000)
        
    def save_config(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.web_widgets, f, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"无法保存配置: {str(e)}")
        
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    self.web_widgets = json.load(f)
                    for widget in self.web_widgets:
                        name = widget.get("name", "网页小部件")
                        item = QListWidgetItem(name)
                        item.setFlags(item.flags() | Qt.ItemIsEditable)
                        self.widget_list.addItem(item)
            except:
                self.web_widgets = []
                self.add_widget()  # 添加默认小部件
        else:
            self.add_widget()  # 添加默认小部件
        
    def close_app(self):
        self.save_config()
        self.close_all_widgets()
        QApplication.quit()
        
    def closeEvent(self, event):
        # 创建退出对话框
        reply = QMessageBox(
            QMessageBox.Question,
            '确认退出',
            "您希望完全退出应用还是最小化到托盘？",
            QMessageBox.Close | QMessageBox.Cancel,
            self
        )
        
        # 设置按钮文本
        reply.button(QMessageBox.Close).setText("完全退出")
        reply.button(QMessageBox.Cancel).setText("最小化到托盘")
        
        # 设置图标
        reply.setWindowIcon(self.windowIcon())
        
        result = reply.exec_()
        
        if result == QMessageBox.Close:
            # 完全退出
            self.close_app()
            event.accept()
        else:
            # 最小化到托盘
            self.hide_to_tray()
            event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)  # 防止关闭所有窗口时退出应用

    font_id = QFontDatabase.addApplicationFont("Pretendard-Bold.otf")
    if font_id != -1:
        font_families = QFontDatabase.applicationFontFamilies(font_id)
        if font_families:
            app_font = QFont(font_families[0], 10, QFont.Bold)
            app.setFont(app_font)
    
    # 设置应用样式
    app.setStyleSheet("""
        QToolTip {
            background-color: #2c3e50;
            color: #ecf0f1;
            border: 1px solid #3498db;
            border-radius: 4px;
            padding: 5px;
        }
    """)
    
    window = SettingsWindow()
    window.show()
    sys.exit(app.exec_())