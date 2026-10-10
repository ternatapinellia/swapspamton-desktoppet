# -*- coding: utf-8 -*-
import os
# Qt 在 Windows 上遇到某些 Bricolage Grotesque 可变字体/字体变体时，
# 可能输出 qt.qpa.fonts 的 enumerate warning。SPAMTON实际使用 Microsoft YaHei，
# 不依赖这些字体；关闭这类无害的 Qt 字体枚举警告，避免启动时刷屏。
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.fonts.warning=false")
import sys
import random
import math
import json
import urllib.request
import urllib.parse
import urllib.error
import time
import winreg
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QMenu,
                             QPushButton, QGridLayout, QGroupBox,
                             QSpinBox, QCheckBox, QHBoxLayout, QAction, QWidgetAction, QSlider,
                             QVBoxLayout, QSystemTrayIcon,
                             QScrollArea, QPlainTextEdit, QLineEdit, QComboBox)
from PyQt5.QtCore import (Qt, QTimer, QPropertyAnimation, QPoint, QTime,
                            QEasingCurve, QEvent, QUrl, QThread, pyqtSignal)
from PyQt5.QtGui import QPixmap, QPainter, QFont, QIcon
from PyQt5.QtMultimedia import QSoundEffect

# ---------- Resource / writable data paths ----------
def resource_path(relative_path):
    """读取 EXE 同级 image 文件夹中的图片资源。"""
    if getattr(sys, "frozen", False):
        base_path = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    image_path = os.path.join(base_path, "image", relative_path)
    if os.path.exists(image_path):
        return image_path

    # 源码运行兼容：如果资源仍放在程序目录，也允许读取。
    return os.path.join(base_path, relative_path)


def audio_resource_path(relative_path):
    """Read external audio resources from the application directory."""
    if getattr(sys, "frozen", False):
        base_path = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def writable_app_path(relative_path):
    """Return a writable application-data path."""
    if getattr(sys, "frozen", False):
        base_path = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def load_spam_volume():
    """Load saved SPT voice volume. Default: 80%."""
    try:
        path = writable_app_path("spam_volume.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return max(0, min(100, int(data.get("volume", 80))))
    except Exception:
        return 80


def save_spam_volume(value):
    """Save SPT voice volume."""
    try:
        path = writable_app_path("spam_volume.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"volume": int(value)}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"SPT volume save failed: {e}")

# ---------- Windows autostart ----------
def set_windows_autostart(enabled=True):
    try:
        run_key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "SPTDeskPet"
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            run_key_path,
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE
        ) as key:
            if enabled:
                if getattr(sys, "frozen", False):
                    # PyInstaller EXE：开机自启必须直接启动 EXE，不能把 EXE 当作 Python 脚本参数。
                    executable = os.path.abspath(sys.executable)
                    command = f'"{executable}"'
                else:
                    # 源码运行：使用 pythonw.exe，避免开机弹出控制台窗口。
                    executable = sys.executable
                    if executable.lower().endswith("python.exe"):
                        pythonw = os.path.join(os.path.dirname(executable), "pythonw.exe")
                        if os.path.exists(pythonw):
                            executable = pythonw
                    script_path = os.path.abspath(sys.argv[0])
                    command = f'"{executable}" "{script_path}"'
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, command)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
    except Exception as e:
        print(f"Windows autostart setup failed: {e}")

# 导入对话配置
try:
    from dialogues import get_dialogues
except ImportError:
    def get_dialogues(lang, key):
        default = {
            'zh': {
                'start': ['你好呀！今天想做什么呢？'],
                'click': ['哎呀，别戳我！', '好痒！'],
                'flirt': ['讨厌啦~', '你好坏哦~'],
                'drink': ['该喝水了！', '喝点水吧~'],
                'lunch': ['该吃午饭了！', '午饭时间到！'],
                'dinner': ['该吃晚饭了！', '晚饭时间到！'],
                'sleep': ['该睡觉了！', '晚安~'],
                'random': ['今天天气真好~', '你在看什么呢？'],
                'note_saved': ['便签已保存！', '笔记已存好~'],
                'note_error': ['便签保存失败...', '出错了...'],
                'note_repeat': ['我记得你写过这个！', '这句话真有意思~'],
                'close': ['真的要走了吗？', '拜拜~下次见！']
            },
            'en': {
                'start': ['Hello! What do you want to do today?'],
                'click': ['Hey, stop poking me!', 'That tickles!'],
                'flirt': ['Oh stop~', 'You are so naughty~'],
                'drink': ['Time to drink water!', 'Have some water~'],
                'lunch': ['Time for lunch!', 'Lunch time!'],
                'dinner': ['Time for dinner!', 'Dinner time!'],
                'sleep': ['Time to sleep!', 'Good night~'],
                'random': ['Nice weather today~', 'What are you looking at?'],
                'note_saved': ['Note saved!', 'Note stored~'],
                'note_error': ['Failed to save note...', 'Error...'],
                'note_repeat': ['I remember you wrote this!', 'That is interesting~'],
                'close': ['Are you really leaving?', 'Bye~ See you next time!']
            }
        }
        return default.get(lang, default['zh']).get(key, ['...'])

try:
    from games import GameManager
except ImportError:
    GameManager = None


# ---------- Screen size ----------
def get_screen_size():
    app = QApplication.instance()
    if app is None:
        return (1920, 1080)
    screen = app.primaryScreen()
    if screen is None:
        return (1920, 1080)
    geometry = screen.availableGeometry()
    return (geometry.width(), geometry.height())

# ---------- 商品 API 配置 ----------
# SPT 商品功能统一通过自建代理访问 Rakuten，客户端不保存 Rakuten 密钥。
PRODUCT_API_BASE = "https://summer-pinellia.duckdns.org/api/products"
PRODUCT_CACHE_SECONDS = 300
_product_cache = {}
_product_translation_cache = {}

def _translate_product_text(text, lang):
    """Translate a Rakuten product title for the current SPT language.

    Uses Google Translate's public endpoint; failures fall back to the original text.
    Results are cached per (lang, title) so re-rendering and language switches are free.
    """
    text = str(text or "").strip()
    if not text or lang not in ("zh", "en"):
        return text

    cache_key = (lang, text)
    cached = _product_translation_cache.get(cache_key)
    if cached is not None:
        return cached

    target = "zh-CN" if lang == "zh" else "en"
    params = urllib.parse.urlencode({
        "client": "gtx",
        "sl": "auto",
        "tl": target,
        "dt": "t",
        "q": text,
    })
    url = "https://translate.googleapis.com/translate_a/single?" + params
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "SPT-DeskPet/1.0", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
        translated = "".join(
            str(part[0]) for part in (data[0] or [])
            if isinstance(part, list) and part and part[0]
        ).strip()
        if translated:
            _product_translation_cache[cache_key] = translated
            return translated
    except Exception as e:
        print("商品标题翻译失败:", e)

    _product_translation_cache[cache_key] = text
    return text

def _translate_product_items(items, lang):
    """Translate every title, in parallel.

    逐个串行翻译 20 条日文标题大约要 40 秒（每条 ~2 秒），这正是商品面板
    “打开就卡” 的原因。这里用线程池并发请求，实测 20 条从 ~40 秒降到 3 秒左右。
    """
    if not items or lang not in ("zh", "en"):
        return items

    titles = []
    for item in items:
        # 始终从原始标题翻译：切语言时会重复调用本函数，
        # 如果拿当前 title（已是译文）再翻一次，译文会被二次翻译。
        original = item.get("title_original") or item.get("title", "")
        item["title_original"] = original
        titles.append(original)

    if not titles:
        return items

    def _apply(t):
        # 走缓存：_translate_product_text 命中缓存时是纯字典读取，不会再发请求。
        return _product_translation_cache.get((lang, t)) or _translate_product_text(t, lang)

    try:
        workers = min(8, max(1, len(titles)))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(_apply, titles))
    except Exception as e:
        print("商品标题批量翻译失败:", e)
        results = [_apply(t) for t in titles]

    for item, translated in zip(items, results):
        item["title"] = translated
    return items

def _product_api_get(path, params=None):
    params = params or {}
    url = PRODUCT_API_BASE.rstrip("/") + "/" + path.lstrip("/")
    query = urllib.parse.urlencode(params)
    if query:
        url += "?" + query
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SPT-DeskPet/1.0", "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        raise RuntimeError(f"商品代理 HTTP {e.code}: {detail or e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"商品代理连接失败: {e.reason}") from e
    except Exception as e:
        raise RuntimeError(f"商品数据解析失败: {e}") from e
def _product_item_image(item):
    images = item.get("mediumImageUrls") or item.get("smallImageUrls") or []
    if images:
        first = images[0]
        if isinstance(first, dict):
            return first.get("imageUrl", "") or first.get("url", "")
        if isinstance(first, str):
            return first
    return item.get("imageUrl", "") or ""

def _normalize_product_items(data, limit=20):
    if not isinstance(data, dict):
        return []
    raw = data.get("items", data.get("Items", []))
    if not isinstance(raw, list):
        return []
    result = []
    max_items = max(1, min(int(limit), 30))
    for wrapper in raw[:max_items]:
        item = wrapper.get("Item", wrapper) if isinstance(wrapper, dict) else {}
        if not isinstance(item, dict):
            continue
        result.append({
            "rank": item.get("rank", len(result) + 1),
            "title": item.get("itemName", item.get("title", "")),
            "price": item.get("itemPrice", item.get("price", "")),
            "url": item.get("itemUrl", item.get("url", "#")),
            "image": _product_item_image(item),
        })
    return result

def fetch_product_ranking(limit=20):
    cache_key = "ranking"
    cached = _product_cache.get(cache_key)
    if cached and time.time() - cached[0] < PRODUCT_CACHE_SECONDS:
        return cached[1]
    data = _product_api_get("ranking", {})
    result = _normalize_product_items(data, limit)
    _product_cache[cache_key] = (time.time(), result)
    return result

def search_products(keyword, limit=20):
    keyword = str(keyword or "").strip()
    if not keyword:
        return []
    cache_key = "search:" + keyword
    cached = _product_cache.get(cache_key)
    if cached and time.time() - cached[0] < PRODUCT_CACHE_SECONDS:
        return cached[1]
    data = _product_api_get("search", {"keyword": keyword, "hits": max(1, min(int(limit), 30))})
    result = _normalize_product_items(data, limit)
    _product_cache[cache_key] = (time.time(), result)
    return result

# ---------- 便签文件 ----------
def get_note_path():
    return os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "note.txt")

def load_notes():
    path = get_note_path()
    try:
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write("")
            return ""
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"读取便签失败: {e}")
        return ""

def save_notes(text):
    path = get_note_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return True
    except Exception as e:
        print(f"保存便签失败: {e}")
        return False


# ---------- 气泡控件 ----------
class BubbleWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        screen_w, screen_h = get_screen_size()
        scale = min(screen_w / 1920, screen_h / 1080)
        # Use the original bubble size.
        bubble_scale = scale
        self.bubble_scale = bubble_scale

        self.bg_pixmap = QPixmap(resource_path("bubble.png"))
        scaled_width = max(1, int(self.bg_pixmap.width() * bubble_scale))
        scaled_height = max(1, int(self.bg_pixmap.height() * bubble_scale))
        self.bg_pixmap = self.bg_pixmap.scaled(scaled_width, scaled_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setFixedSize(self.bg_pixmap.size())

        self.label = QLabel(self)
        self.label.setGeometry(int(130 * bubble_scale), int(85 * bubble_scale), int(340 * bubble_scale), int(160 * bubble_scale))
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.label.setStyleSheet("background: transparent; color: #2c3e50;")
        # Keep the original visual size while compensating for Windows/Qt DPI scaling.
        # The pet's own screen-resolution scale is preserved; only the font's logical
        # point size is adjusted so 125%/150%/200% Windows scaling does not enlarge
        # the bubble text unexpectedly.
        dpi_scale = 1.0
        try:
            screen = QApplication.primaryScreen()
            if screen is not None:
                dpi = float(screen.logicalDotsPerInch())
                if dpi > 0:
                    dpi_scale = max(1.0, dpi / 96.0)
        except Exception:
            dpi_scale = 1.0

        normal_point_size = max(1.0, (18.0 * bubble_scale) / dpi_scale)
        big_point_size = max(1.0, (72.0 * bubble_scale) / dpi_scale)

        self.normal_font = QFont("Microsoft YaHei")
        self.normal_font.setPointSizeF(normal_point_size)
        self.big_font = QFont("Microsoft YaHei")
        self.big_font.setPointSizeF(big_point_size)
        self.label.setFont(self.normal_font)

        self.full_text = ""
        self.char_index = 0
        self.typing_timer = QTimer(self)
        self.typing_timer.timeout.connect(self.type_char)
        self.typing_interval = 75

        self.is_typing = False
        self.is_complete = False

        self.confirm_button = QPushButton(self)
        self.confirm_button.setCursor(Qt.PointingHandCursor)
        self.confirm_button.clicked.connect(self._confirm_clicked)
        self.confirm_button.hide()

        self.confirm_timer = QTimer(self)
        self.confirm_timer.setSingleShot(True)
        self.confirm_timer.timeout.connect(self._confirm_timeout)

        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(500)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.finished.connect(self.hide)

        self.move_to_bottom_right()
        self.hide()

    def _update_confirm_button_style(self):
        lang = getattr(self.parent(), "lang", "zh")
        self.confirm_button.setText("Confirm" if lang == "en" else "确认")
        screen_w, screen_h = get_screen_size()
        scale = self.bubble_scale
        self.confirm_button.setGeometry(
            self.width() - int(248 * scale),
            self.height() - int(105 * scale),
            int(115 * scale),
            int(38 * scale)
        )
        self.confirm_button.setStyleSheet(f"""
            QPushButton {{
                font-family: "Microsoft YaHei";
                font-size: {max(1, int(14 * scale))}px;
                font-weight: bold;
                color: white;
                background-color: #1a1a2c;
                border: none;
                border-radius: {max(1, int(8 * scale))}px;
                padding: {max(1, int(4 * scale))}px {max(1, int(10 * scale))}px;
            }}
            QPushButton:hover {{ background-color: #2a2a4c; }}
            QPushButton:pressed {{ background-color: #111122; }}
        """)

    def show_confirmation_button(self):
        self._update_confirm_button_style()
        self.confirm_button.show()
        self.confirm_button.raise_()
        self.confirm_timer.start(60000)

    def hide_confirmation_button(self):
        self.confirm_timer.stop()
        self.confirm_button.hide()

    def _confirm_clicked(self):
        self.hide_confirmation_button()
        if self.parent() is not None:
            self.parent().confirm_dialog()

    def _confirm_timeout(self):
        # 提醒超过1分钟未确认：先消失，稍后再次提醒。
        self.hide_confirmation_button()
        if self.parent() is not None:
            self.parent().reminder_dialog_timeout()

    def move_to_bottom_right(self):
        screen_w, screen_h = get_screen_size()
        x = screen_w - self.width() - 50
        y = screen_h - self.height() - 50
        self.move(x, y)

    def get_bubble_position(self):
        return self.x(), self.y()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.bg_pixmap)
        super().paintEvent(event)

    def _text_height(self, text):
        fm = self.label.fontMetrics()
        rect = fm.boundingRect(0, 0, self.label.width(), 10000, Qt.TextWordWrap, text)
        return rect.height()

    def _split_for_bubble(self, text):
        max_height = max(1, self.label.height())
        if self._text_height(text) <= max_height:
            return text, ""

        low, high = 1, len(text)
        best = 1
        while low <= high:
            mid = (low + high) // 2
            part = text[:mid].rstrip()
            if self._text_height(part) <= max_height:
                best = mid
                low = mid + 1
            else:
                high = mid - 1

        cut = best
        prefix = text[:best]
        if " " in prefix:
            space_pos = prefix.rfind(" ")
            if space_pos >= max(1, best - 40):
                cut = space_pos

        first = text[:cut].rstrip()
        rest = text[cut:].lstrip()
        if not first:
            first = text[:best]
            rest = text[best:]
        return first, rest

    def type_char(self):
        if self.char_index < len(self.full_text):
            self.char_index += 1
            current_text = self.full_text[:self.char_index]
            if self._text_height(current_text) > self.label.height():
                visible_text, remaining = self._split_for_bubble(self.full_text)
                self.typing_timer.stop()
                self.label.setText(visible_text)
                self.full_text = visible_text
                self.char_index = len(visible_text)
                self.is_typing = False
                self.is_complete = True
                if remaining:
                    parent = self.parent()
                    if parent is not None:
                        parent.start_dialog_continuation(
                            remaining,
                            getattr(self, "current_requires_confirmation", False)
                        )
                else:
                    parent = self.parent()
                    if parent is not None:
                        parent.on_dialog_complete()
            else:
                self.label.setText(current_text)
                # 跟随文字逐字播放；空格、换行和常见标点静音，避免声音过密。
                current_char = self.full_text[self.char_index - 1]
                if not current_char.isspace() and not re.match(r"[\s\.,!?;:，。！？；：、~～…\-—_\"'\(\)\[\]{}<>]", current_char):
                    parent = self.parent()
                    if parent is not None and hasattr(parent, "_play_spam_char_sound"):
                        parent._play_spam_char_sound(
                            getattr(parent, "current_reminder_key", None)
                        )
        else:
            self.typing_timer.stop()
            self.is_typing = False
            self.is_complete = True
            parent = self.parent()
            if parent is not None:
                parent.on_dialog_complete()

    def start_typing(self, text, requires_confirmation=False):
        self.label.setFont(self.normal_font)
        self.current_requires_confirmation = bool(requires_confirmation)
        self.full_text = text
        self.char_index = 0
        self.label.clear()
        self.is_typing = True
        self.is_complete = False
        self.show()
        parent = self.parent()
        if parent is not None:
            if getattr(parent, "bubble_mode", "follow") == "fixed":
                self.move_to_bottom_right()
            elif hasattr(parent, "update_bubble_position"):
                parent.update_bubble_position()
        self.setWindowOpacity(1.0)
        self.fade_animation.stop()
        self.hide_confirmation_button()
        if requires_confirmation:
            self.show_confirmation_button()
        self.typing_timer.start(self.typing_interval)

    def show_big_text(self, text):
        self.label.setFont(self.big_font)
        self.label.setText(text)
        self.full_text = text
        self.is_typing = False
        self.is_complete = True
        self.show()
        parent = self.parent()
        if parent is not None:
            if getattr(parent, "bubble_mode", "follow") == "fixed":
                self.move_to_bottom_right()
            elif hasattr(parent, "update_bubble_position"):
                parent.update_bubble_position()
        self.setWindowOpacity(1.0)
        self.fade_animation.stop()
        self.hide_confirmation_button()

    def fade_out(self):
        self.hide_confirmation_button()
        if self.isVisible():
            self.fade_animation.start()

    def dismiss(self):
        self.typing_timer.stop()
        self.hide_confirmation_button()
        self.fade_animation.stop()
        self.hide()


# ---------- 基础面板类 ----------
class BasePanel(QWidget):
    def __init__(self, parent=None, panel_type="panel"):
        super().__init__(parent)
        self.parent_pet = parent
        self.panel_type = panel_type
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        screen_w, screen_h = get_screen_size()
        scale = min(screen_w / 1920, screen_h / 1080)
        self.panel_width = int(450 * scale)
        self.panel_height = int(500 * scale)
        self.setFixedSize(self.panel_width, self.panel_height)

        bg_file = "panel.png" if panel_type == "control" else "panel2.png"
        self.bg_pixmap = QPixmap(resource_path(bg_file))
        scaled_bg = self.bg_pixmap.scaled(self.panel_width, self.panel_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.bg_pixmap = scaled_bg
        self.setMask(self.bg_pixmap.mask())

        self._position_fixed = False
        self._fixed_x = 0
        self._fixed_y = 0
        self.scale = scale

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.bg_pixmap)
        super().paintEvent(event)

    def update_position(self):
        """把面板固定在桌宠左侧（气泡左边），随桌宠一起移动；左边放不下时自动换到右侧。"""
        if self.parent_pet is None or not hasattr(self.parent_pet, "label"):
            return

        pet = self.parent_pet
        scale = float(getattr(pet, "scale", self.scale))

        # 同步气泡位置
        if hasattr(pet, "update_bubble_position"):
            pet.update_bubble_position()

        label = pet.label
        pet_w = max(1, label.width())
        pet_h = max(1, label.height())
        gap = int(round(24 * scale))

        # 气泡自身的横向偏移（和 update_bubble_position 用同一个常量），
        # 面板贴在气泡更左侧，避免和气泡重叠。
        bubble = getattr(pet, "bubble", None)
        bubble_w = bubble.width() if bubble is not None else 0
        bubble_offset_x = int(round(300 * scale))
        bubble_left_rel = label.x() + (pet_w - bubble_w) // 2 - bubble_offset_x

        # 默认：面板放在气泡左侧，垂直与桌宠居中对齐。
        # 左侧位置整体右移 500px，让面板更靠近桌宠（气泡本身不动）。
        left_shift = int(round(500 * scale))
        panel_rel_x = bubble_left_rel - self.width() - gap + left_shift
        panel_rel_y = label.y() + (pet_h - self.height()) // 2

        # 左边放不下时改放桌宠右侧
        panel_global_x = pet.mapToGlobal(QPoint(int(panel_rel_x), 0)).x()
        screen = QApplication.screenAt(pet.mapToGlobal(QPoint(label.x(), label.y()))) or QApplication.primaryScreen()
        rect = screen.availableGeometry() if screen is not None else None
        if rect is not None and panel_global_x < rect.left():
            panel_rel_x = label.x() + pet_w + gap

        # 垂直越界时只做最小修正，保证面板仍紧贴桌宠
        if rect is not None:
            panel_global_y = pet.mapToGlobal(QPoint(0, int(panel_rel_y))).y()
            corrected_y = max(rect.top(), min(panel_global_y, rect.bottom() - self.height() + 1))
            panel_rel_y = panel_rel_y + (corrected_y - panel_global_y)

        # 面板是独立顶层窗口（Qt.Tool），move 使用屏幕坐标
        self.move(pet.mapToGlobal(QPoint(int(panel_rel_x), int(panel_rel_y))))
        self._fixed_x = self.x()
        self._fixed_y = self.y()
        self._position_fixed = True


class ProductFetchWorker(QThread):
    """后台线程：拉取商品 + 翻译标题，避免阻塞 Qt 主线程（原来会卡 30~40 秒）。

    翻译本身又用线程池并发请求，所以 20 条日文标题从 ~40 秒降到 3 秒左右。
    结果通过 result_ready 信号发回主线程，主线程只负责刷新界面。
    """

    result_ready = pyqtSignal(str, object, str)

    def __init__(self, kind, keyword="", lang="zh"):
        # 不设置 QObject 父对象：面板关闭/销毁时不会连带销毁仍在运行的线程。
        super().__init__()
        self.kind = kind            # 'ranking' 或 'search'
        self.keyword = keyword
        self.lang = lang
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            if self.kind == "search":
                items = search_products(self.keyword, 20)
            else:
                items = fetch_product_ranking(20)
            if self._cancelled:
                return
            _translate_product_items(items, self.lang)
            if self._cancelled:
                return
            self.result_ready.emit(self.kind, items, "")
        except Exception as e:
            if not self._cancelled:
                self.result_ready.emit(self.kind, [], str(e))

class ProductTranslateWorker(QThread):
    """后台线程：只做标题翻译（用于面板已打开时切换语言）。

    切换语言时如果目标语言还没有译文缓存，需要重新请求 20 条标题，
    放在主线程会卡 5~6 秒；放到这里让界面保持响应。
    """

    result_ready = pyqtSignal(object, str, str)

    def __init__(self, items, lang):
        super().__init__()
        self.items = items
        self.lang = lang
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            _translate_product_items(self.items, self.lang)
            if not self._cancelled:
                self.result_ready.emit(self.items, self.lang, "")
        except Exception as e:
            if not self._cancelled:
                self.result_ready.emit(self.items, self.lang, str(e))

# ---------- 商品面板 ----------
class ProductWindow(BasePanel):
    def __init__(self, parent=None):
        super().__init__(parent, panel_type="product")
        self.container = QWidget(self)
        self.container.setGeometry(0, 0, self.panel_width, self.panel_height)
        self.container.setStyleSheet("background: transparent;")
        self.mode = "ranking"
        self.lang = getattr(parent, "lang", "zh") if parent else "zh"
        self.product_data = []
        self._loading = False
        self._worker = None
        self._worker_key = None
        self._translate_worker = None
        self.page = 0
        self.page_size = 6

        self.title_label = QLabel(self.container)
        self.title_label.setStyleSheet(f"color:#1a1a2c;font-size:{int(27*self.scale)}px;font-weight:bold;background:transparent;")
        self.title_label.setGeometry(int(55*self.scale), int(45*self.scale), int(300*self.scale), int(45*self.scale))

        self.hot_btn = QPushButton(self.container)
        self.search_btn = QPushButton(self.container)
        for btn in (self.hot_btn, self.search_btn):
            btn.setStyleSheet(f"QPushButton{{font-size:{int(13*self.scale)}px;background:#1a1a2c;color:white;border:none;border-radius:{int(7*self.scale)}px;padding:{int(4*self.scale)}px {int(8*self.scale)}px;}} QPushButton:hover{{background:#2a2a4c;}}")
        self.hot_btn.setGeometry(int(55*self.scale), int(90*self.scale), int(145*self.scale), int(34*self.scale))
        self.search_btn.setGeometry(int(210*self.scale), int(90*self.scale), int(145*self.scale), int(34*self.scale))
        self.hot_btn.clicked.connect(self.show_ranking)
        self.search_btn.hide()

        self.search_edit = QLineEdit(self.container)
        self.search_edit.setGeometry(int(55*self.scale), int(132*self.scale), int(300*self.scale), int(34*self.scale))
        self.search_edit.setStyleSheet(f"QLineEdit{{background:white;border-radius:{int(7*self.scale)}px;padding:{int(5*self.scale)}px {int(9*self.scale)}px;font-size:{int(13*self.scale)}px;}}")
        self.search_edit.returnPressed.connect(self.run_search)
        self.search_edit.hide()

        self.go_btn = QPushButton(self.container)
        self.go_btn.setGeometry(int(360*self.scale), int(132*self.scale), int(45*self.scale), int(34*self.scale))
        self.go_btn.setStyleSheet(f"QPushButton{{font-size:{int(12*self.scale)}px;background:#1a1a2c;color:white;border:none;border-radius:{int(7*self.scale)}px;}}")
        self.go_btn.clicked.connect(self.run_search)
        self.go_btn.hide()

        self.product_scroll = QScrollArea(self.container)
        self.product_scroll.setGeometry(int(55*self.scale), int(132*self.scale), int(340*self.scale), int(315*self.scale))
        self.product_scroll.setWidgetResizable(True)
        self.product_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.product_scroll.setStyleSheet("QScrollArea{background:transparent;border:none;} QScrollBar:vertical{width:8px;background:transparent;} QScrollBar::handle:vertical{background:#888;border-radius:4px;}")
        self.product_container = QWidget()
        self.product_container.setStyleSheet("background:white;border-radius:10px;")
        self.product_layout = QVBoxLayout(self.product_container)
        self.product_layout.setSpacing(int(8*self.scale))
        self.product_layout.setContentsMargins(int(12*self.scale), int(10*self.scale), int(18*self.scale), int(10*self.scale))
        self.product_layout.setAlignment(Qt.AlignTop)
        self.product_scroll.setWidget(self.product_container)

        self.status_label = QLabel(self.container)
        self.status_label.setStyleSheet(f"color:#555;font-size:{int(11*self.scale)}px;background:transparent;")
        self.status_label.setGeometry(int(55*self.scale), int(452*self.scale), int(300*self.scale), int(30*self.scale))
        self.close_btn = QPushButton("✕", self.container)
        self.close_btn.setStyleSheet(f"QPushButton{{font-size:{int(18*self.scale)}px;background:transparent;color:#1a1a2c;border:none;}} QPushButton:hover{{color:#e74c3c;}}")
        self.close_btn.setGeometry(int(410*self.scale), int(10*self.scale), int(30*self.scale), int(30*self.scale))
        self.close_btn.clicked.connect(self.hide)
        self.update_language(parent.lang if parent else "zh")
        self.search_btn.hide()
        self.search_edit.hide()
        self.go_btn.hide()

    def update_language(self, lang):
        self.lang = lang
        if lang == "en":
            self.title_label.setText("Products")
            self.hot_btn.setText("Hot Ranking")
            self.search_btn.setText("")
            self.search_edit.setPlaceholderText("Search products...")
            self.go_btn.setText("Go")
        else:
            self.title_label.setText("商品")
            self.hot_btn.setText("商品热榜")
            self.search_btn.setText("")
            self.search_edit.setPlaceholderText("输入商品关键词……")
            self.go_btn.setText("搜")
        if not self.product_data:
            return
        originals = [it.get("title_original", it.get("title", "")) for it in self.product_data]
        # 目标语言全部命中缓存（切换回来时）→ 直接刷新，瞬时完成。
        if all((lang, t) in _product_translation_cache for t in originals if t):
            _translate_product_items(self.product_data, lang)
            self._render()
            return
        # 否则后台翻译，避免切换语言时界面卡住。
        self._start_translate_worker()

    def _clear(self):
        for i in reversed(range(self.product_layout.count())):
            item = self.product_layout.itemAt(i)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _render(self):
        self._clear()
        if self._loading:
            label = QLabel("正在加载商品……" if self.parent_pet.lang == "zh" else "Loading products...")
            label.setWordWrap(True)
            label.setStyleSheet(f"font-size:{int(13*self.scale)}px;color:#666;background:transparent;")
            self.product_layout.addWidget(label)
            return
        if not self.product_data:
            label = QLabel("暂无商品数据" if self.parent_pet.lang == "zh" else "No product data")
            label.setWordWrap(True)
            label.setStyleSheet(f"font-size:{int(13*self.scale)}px;color:#666;background:transparent;")
            self.product_layout.addWidget(label)
            return
        for item in self.product_data:
            card = QWidget()
            card.setStyleSheet("QWidget{background:#f7f7fa;border-radius:8px;}")
            lay = QVBoxLayout(card)
            lay.setContentsMargins(int(9*self.scale),int(7*self.scale),int(9*self.scale),int(7*self.scale))
            title = QLabel(f"#{item.get('rank','-')}  {item.get('title','')}")
            title.setWordWrap(True)
            title.setStyleSheet(f"font-size:{int(12*self.scale)}px;font-weight:bold;color:#1a1a2c;background:transparent;")
            lay.addWidget(title)
            price = item.get('price','')
            info = QLabel((f"¥{price}" if price != '' else "") + ("  ·  Rakuten" if self.lang=='zh' else "  ·  Rakuten"))
            info.setStyleSheet(f"font-size:{int(11*self.scale)}px;color:#666;background:transparent;")
            lay.addWidget(info)
            if item.get('url') and item.get('url') != '#':
                link = QLabel(f"<a href='{item['url']}'>打开商品</a>" if self.lang=='zh' else f"<a href='{item['url']}'>Open item</a>")
                link.setOpenExternalLinks(True)
                link.setStyleSheet(f"font-size:{int(11*self.scale)}px;background:transparent;")
                lay.addWidget(link)
            self.product_layout.addWidget(card)

    def _start_worker(self, kind, keyword=""):
        """启动后台抓取；同一时间只保留一个（新请求会取消上一个）。"""
        key = (kind, keyword, self.lang)
        # 去重：showEvent 和 show_products 都会触发一次加载，缓存命中时结果一致，
        # 没必要把同一个请求发两遍（翻译请求能省一半）。
        if self._loading and self._worker_key == key and self._worker is not None:
            return
        self._cancel_worker()
        self._worker_key = key
        self._loading = True
        self.product_data = []
        self.status_label.setText("Loading..." if self.lang=='en' else "正在加载商品……")
        self._render()
        worker = ProductFetchWorker(kind, keyword, self.lang)
        worker.result_ready.connect(self._on_worker_done)
        worker.finished.connect(lambda w=worker: self._release_worker(w))
        self._worker = worker
        worker.start()

    def _cancel_worker(self):
        worker = getattr(self, "_worker", None)
        if worker is not None:
            try:
                worker.cancel()
            except Exception:
                pass
        self._worker = None
        self._worker_key = None

    def _start_translate_worker(self):
        """面板已打开、切换语言时用后台线程重新翻译标题。"""
        old = getattr(self, "_translate_worker", None)
        if old is not None:
            try:
                old.cancel()
            except Exception:
                pass
        worker = ProductTranslateWorker(self.product_data, self.lang)
        worker.result_ready.connect(self._on_translate_done)
        worker.finished.connect(lambda w=worker: self._release_translate_worker(w))
        self._translate_worker = worker
        worker.start()

    def _release_translate_worker(self, worker):
        if getattr(self, "_translate_worker", None) is worker:
            self._translate_worker = None
        try:
            worker.deleteLater()
        except Exception:
            pass

    def _on_translate_done(self, items, lang, error):
        if error:
            print("商品标题翻译失败:", error)
        if lang == self.lang:
            self._render()

    def _release_worker(self, worker):
        if getattr(self, "_worker", None) is worker:
            self._worker = None
        try:
            worker.deleteLater()
        except Exception:
            pass

    def _on_worker_done(self, kind, items, error):
        self._loading = False
        self._worker_key = None
        if error:
            self.product_data = []
            self.status_label.setText(error)
            print("商品 API 错误:", error)
        else:
            self.product_data = items or []
            self.status_label.setText(
                f"{len(self.product_data)} items" if self.lang=='en' else f"共 {len(self.product_data)} 件商品")
        self._render()

    def _load(self, loader):
        """兼容旧调用：仍然异步执行，不再阻塞界面。"""
        self._start_worker("ranking")

    def show_ranking(self):
        self.mode = "ranking"
        self.search_edit.hide(); self.go_btn.hide()
        self.product_scroll.setGeometry(int(55*self.scale), int(132*self.scale), int(340*self.scale), int(315*self.scale))
        self._start_worker("ranking")

    def show_search(self):
        self.mode = "search"
        self.search_edit.show(); self.go_btn.show()
        self.product_scroll.setGeometry(int(55*self.scale), int(174*self.scale), int(340*self.scale), int(273*self.scale))
        if self.search_edit.text().strip():
            self.run_search()
        else:
            self._clear()

    def run_search(self):
        keyword = self.search_edit.text().strip()
        if not keyword:
            return
        self._start_worker("search", keyword)

    def hideEvent(self, event):
        # 面板关闭时取消正在进行的抓取/翻译，避免线程在窗口销毁后回调。
        self._cancel_worker()
        tw = getattr(self, "_translate_worker", None)
        if tw is not None:
            try:
                tw.cancel()
            except Exception:
                pass
        super().hideEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        if self.mode == "ranking":
            self.show_ranking()
        else:
            self.show_search()

# ---------- 小游戏窗口 ----------
class GamesWindow(BasePanel):
    """SPT 本地小游戏界面。游戏规则由 games/ 包负责，窗口只负责输入和显示。"""
    GAME_NAMES = {
        'tictactoe': ('井字棋', 'Tic-Tac-Toe'),
        'gomoku': ('五子棋', 'Gomoku'),
        'idiom': ('成语接龙', 'Idiom Chain'),
        'uno': ('UNO', 'UNO'),
        'deal': ('Deal or No Deal', 'Deal or No Deal'),
        'buckshot': ('Buckshot Roulette', 'Buckshot Roulette'),
        'roulette': ('俄罗斯轮盘', 'Russian Roulette'),
        'farmland': ('星露谷物语', 'Stardew Valley'),
    }

    def __init__(self, parent=None):
        super().__init__(parent, panel_type="game")
        self.manager = GameManager() if GameManager is not None else None
        self.game = None
        self.current_game_id = None

        self.container = QWidget(self)
        self.container.setGeometry(0, 0, self.panel_width, self.panel_height)
        self.container.setStyleSheet("background: transparent;")

        self.title_label = QLabel(self.container)
        self.title_label.setGeometry(int(48*self.scale), int(45*self.scale),
                                     int(300*self.scale), int(42*self.scale))
        self.title_label.setStyleSheet(
            f"color:#1a1a2c;font-size:{int(24*self.scale)}px;"
            "font-weight:bold;background:transparent;"
        )

        self.game_combo = QComboBox(self.container)
        self.game_combo.setGeometry(int(48*self.scale), int(88*self.scale),
                                    int(285*self.scale), int(36*self.scale))
        self.game_combo.setStyleSheet(
            f"QComboBox{{background:white;color:#1a1a2c;border:none;"
            f"border-radius:{int(7*self.scale)}px;padding-left:{int(9*self.scale)}px;"
            f"font-size:{int(16*self.scale)}px;}}"
        )
        self.game_combo.currentIndexChanged.connect(self._combo_changed)

        self.new_game_btn = QPushButton(self.container)
        self.new_game_btn.setGeometry(int(340*self.scale), int(88*self.scale),
                                      int(62*self.scale), int(36*self.scale))
        self.new_game_btn.setStyleSheet(
            f"QPushButton{{font-size:{int(18*self.scale)}px;background:#1a1a2c;"
            f"color:white;border:none;border-radius:{int(7*self.scale)}px;}}"
        )
        self.new_game_btn.clicked.connect(self.start_current_game)

        self.status_label = QLabel(self.container)
        self.status_label.setGeometry(int(48*self.scale), int(130*self.scale),
                                      int(350*self.scale), int(38*self.scale))
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(
            f"color:#555;font-size:{int(14*self.scale)}px;background:transparent;"
        )

        self.game_area = QWidget(self.container)
        self.game_area.setGeometry(int(35*self.scale), int(165*self.scale),
                                   int(380*self.scale), int(285*self.scale))
        self.game_area.setStyleSheet("background:white;border-radius:10px;")
        self.game_page = None

        self.close_btn = QPushButton("关闭", self.container)
        self.close_btn.setGeometry(
            int(340*self.scale),
            int(455*self.scale),
            int(72*self.scale),
            int(32*self.scale)
        )
        self.close_btn.setStyleSheet(
            f"QPushButton{{font-size:{int(15*self.scale)}px;font-weight:bold;"
            "background:#1a1a2c;color:white;border:none;border-radius:6px;}"
            "QPushButton:hover{background:#c0392b;}"
        )
        self.close_btn.clicked.connect(self.hide)

        self.update_language(parent.lang if parent else "zh")
        if self.manager is None:
            self.status_label.setText(
                "游戏模块未加载" if self.lang == "zh" else "Game module is unavailable"
            )
        else:
            self.start_current_game()

    def update_language(self, lang):
        self.lang = lang
        self.title_label.setText("小游戏" if lang == "zh" else "Games")
        self.new_game_btn.setText("新局" if lang == "zh" else "New")
        names = list(self.GAME_NAMES)
        current = self.current_game_id
        self.game_combo.blockSignals(True)
        self.game_combo.clear()
        for game_id in names:
            zh, en = self.GAME_NAMES[game_id]
            self.game_combo.addItem(en if lang == "en" else zh, game_id)
        if current in names:
            self.game_combo.setCurrentIndex(names.index(current))
        self.game_combo.blockSignals(False)
        if self.game is not None:
            self._render_current_game()

    def _combo_changed(self, index):
        if index < 0:
            return
        self.start_current_game()

    def _clear_area(self):
        # 不复用旧 layout：直接替换整个游戏页面。
        # 这样切换游戏时旧按钮/滚动区域会立即隐藏，不会等 Qt 事件循环后才消失，避免页面重叠。
        old_page = getattr(self, "game_page", None)
        if old_page is not None:
            old_page.hide()
            old_page.setParent(None)
            old_page.deleteLater()

        self.game_page = QWidget(self.game_area)
        self.game_page.setGeometry(0, 0, self.game_area.width(), self.game_area.height())
        self.game_page.setStyleSheet("background:transparent;")
        self.game_page.show()

        layout = QVBoxLayout(self.game_page)
        layout.setContentsMargins(int(10*self.scale), int(10*self.scale),
                                  int(10*self.scale), int(10*self.scale))
        layout.setSpacing(int(7*self.scale))
        return layout

    def _set_status(self, text):
        self.status_label.setText(str(text))

    def _new_button(self, text, slot, enabled=True):
        b = QPushButton(str(text), self.game_page)
        b.setEnabled(enabled)
        b.setStyleSheet(
            f"QPushButton{{font-size:{int(18*self.scale)}px;background:#1a1a2c;"
            f"color:white;border:none;border-radius:{int(6*self.scale)}px;"
            f"padding:{int(4*self.scale)}px;}}"
            "QPushButton:disabled{background:#bbb;color:#eee;}"
            "QPushButton:hover{background:#2a2a4c;}"
        )
        b.clicked.connect(slot)
        return b

    def start_current_game(self):
        if self.manager is None:
            return
        old_game = getattr(self, "game", None)
        if old_game is not None and hasattr(old_game, "close"):
            try:
                old_game.close()
            except Exception:
                pass
        game_id = self.game_combo.currentData()
        if not game_id:
            return
        try:
            self.game = self.manager.start(game_id)
            self.current_game_id = game_id
            self._game_message = ""
            self._game_result_announced = False
            if game_id == "idiom":
                result = self.game.start()
                if not result.get("ok"):
                    raise RuntimeError(result.get("reason", "成语接龙启动失败"))
            self._render_current_game()
        except Exception as e:
            self.game = None
            self._set_status(("启动游戏失败：" if self.lang == "zh" else "Failed to start game: ") + str(e))
            self._clear_area()

    def _render_current_game(self):
        if self.game is None:
            return
        layout = self._clear_area()
        gid = self.current_game_id
        if gid == "tictactoe":
            self._render_tictactoe(layout)
        elif gid == "gomoku":
            self._render_gomoku(layout)
        elif gid == "idiom":
            self._render_idiom(layout)
        elif gid == "uno":
            self._render_uno(layout)
        elif gid == "deal":
            self._render_deal(layout)
        elif gid == "buckshot":
            self._render_buckshot(layout)
        elif gid == "roulette":
            self._render_roulette(layout)
        elif gid == "farmland":
            self.game.build_ui(self, layout)
            # 农场不是棋类游戏，不应继承上一局的“你是 X”之类状态文字。
            self._set_status("星露谷物语" if self.lang == "zh" else "Stardew Valley")
        self._apply_game_state_status()

    def _announce_game_result_once(self, result):
        """游戏结束时触发一次SPAMTON台词，避免重新绘制页面时重复播放。"""
        if getattr(self, "_game_result_announced", False):
            return

        dialogue_map = {
            "player_win": {
                "zh": [
                    "哼……这次算你赢了，别得意得太早。",
                    "竟然被你赢了？下一局我可不会手下留情。",
                    "好吧，这局你赢了。只是这只是暂时的。",
                ],
                "en": [
                    "Hmph... you win this round. Don't get too confident.",
                    "You actually beat me? I won't go easy next round.",
                    "Fine, you win this one. It's only temporary.",
                ],
            },
            "ai_win": {
                "zh": [
                    "哈哈！看到了吧？这就是我的实力。",
                    "胜负已定。果然还是我更强。",
                    "漂亮！这局当然是我赢。",
                ],
                "en": [
                    "Ha! See that? That's my skill.",
                    "The result is settled. I'm clearly stronger.",
                    "Perfect! Of course I win this round.",
                ],
            },
            "draw": {
                "zh": [
                    "平局？看来我们暂时势均力敌。",
                    "没有赢家？下一局继续。",
                    "平局也算有点意思。再来一局。",
                ],
                "en": [
                    "A draw? Looks like we're evenly matched for now.",
                    "No winner? Let's continue with another round.",
                    "A draw is interesting enough. One more round.",
                ],
            },
            "deal": {
                "zh": [
                    "成交！这笔交易已经敲定。",
                    "好，成交。钱已经到手了。",
                ],
                "en": [
                    "Deal! The offer is accepted.",
                    "All right, deal. The money is secured.",
                ],
            },
            "final": {
                "zh": [
                    "开箱结束，看看最后拿到了多少。",
                    "最终结果出来了。",
                ],
                "en": [
                    "The final case is open. Let's see what you got.",
                    "The final result is in.",
                ],
            },
        }
        lines = dialogue_map.get(result, {}).get("en" if self.lang == "en" else "zh")
        if not lines:
            return
        # 先锁定“已播报”状态。不要在 _render_current_game() 内同步切换
        # SPAMTON气泡，否则 Qt 可能在游戏页面还没完成重建时发生重入。
        self._game_result_announced = True
        text = random.choice(lines)

        def _show_game_result_dialog():
            try:
                if self.game is None:
                    return
                # GamesWindow 自己没有对话系统，胜负台词发送回主桌宠 SPAMTON
                if hasattr(self, "parent_pet") and self.parent_pet:
                    self.parent_pet.add_dialog(
                        text,
                        priority=True,
                        interrupt_tomato=True
                    )
                elif hasattr(self, "parent") and self.parent and hasattr(self.parent, "add_dialog"):
                    self.parent.add_dialog(
                        text,
                        priority=True,
                        interrupt_tomato=True
                    )
            except Exception as e:
                # 胜负台词失败不能影响游戏窗口本身。
                print(f"游戏胜负台词播放失败: {e}")

        QTimer.singleShot(0, _show_game_result_dialog)

    def _apply_game_state_status(self):
        """统一在重新绘制游戏页面后恢复胜负/回合提示，避免被 render 覆盖。"""
        if self.game is None:
            return

        zh = self.lang != "en"
        gid = self.current_game_id

        if getattr(self.game, "over", False):
            winner = getattr(self.game, "winner", None)
            if winner in ("player", 0):
                self._set_status("你赢了！" if zh else "You win!")
                self._announce_game_result_once("player_win")
            elif winner in ("ai", 1):
                self._set_status("SPAMTON赢了！" if zh else "The pet wins!")
                self._announce_game_result_once("ai_win")
            elif gid == "deal":
                value = getattr(self.game, "result", None)
                self._set_status(
                    (f"游戏结束：最终金额 ¥{value}" if zh else f"Game over: Final value ¥{value}")
                    if value is not None else ("游戏结束" if zh else "Game over")
                )
                self._announce_game_result_once("deal" if getattr(self.game, "offer", None) is not None else "final")
            else:
                self._set_status("平局！" if zh else "Draw!")
                self._announce_game_result_once("draw")
            return

        # 没有结束时优先显示刚刚发生的动作。
        if self._game_message:
            self._set_status(self._game_message)
            return

        if gid in ("buckshot", "roulette"):
            turn = getattr(self.game, "turn", 0)
            self._set_status(
                "SPAMTON的回合，请稍候" if turn == 1 and zh else
                "Pet's turn, please wait" if turn == 1 else
                "轮到你" if zh else "Your turn"
            )
        elif gid == "uno":
            turn = getattr(self.game, "turn", 0)
            self._set_status(
                "SPAMTON的回合，请稍候" if turn == 1 and zh else
                "Pet's turn, please wait" if turn == 1 else
                "轮到你出牌" if zh else "Your turn"
            )

    def _result_text(self, result):
        mapping = {
            "player_win": ("你赢了", "You win"),
            "ai_win": ("SPAMTON赢了", "The pet wins"),
            "draw": ("平局", "Draw"),
            "deal": ("接受报价", "Deal accepted"),
            "final": ("游戏结束", "Game over"),
            "continue": ("继续", "Continue"),
        }
        if result in mapping:
            return mapping[result][1 if self.lang == "en" else 0]
        return str(result)

    def _render_tictactoe(self, layout):
        if self.game.over:
            if self.game.winner == "player":
                self._set_status("你赢了！" if self.lang == "zh" else "You win!")
            elif self.game.winner == "ai":
                self._set_status("SPAMTON赢了！" if self.lang == "zh" else "The pet wins!")
            else:
                self._set_status("平局！" if self.lang == "zh" else "Draw!")
        else:
            self._set_status("你是 X，SPAMTON 是 O" if self.lang == "zh" else "You are X; the pet is O.")
        grid = QGridLayout()
        grid.setSpacing(int(4*self.scale))
        for i, v in enumerate(self.game.board):
            text = v if v != " " else ""
            btn = self._new_button(text, lambda checked=False, p=i: self._tictactoe_move(p+1))
            btn.setFixedSize(int(92*self.scale), int(55*self.scale))
            btn.setStyleSheet(
                f"QPushButton{{font-size:{int(24*self.scale)}px;font-weight:bold;"
                "background:white;color:black;border:1px solid #222;border-radius:4px;}}"
                "QPushButton:hover{background:#f0f0f0;}"
            )
            if v != " " or self.game.over:
                btn.setEnabled(False)
            grid.addWidget(btn, i//3, i%3)
        layout.addLayout(grid)

    def _tictactoe_move(self, pos):
        r = self.game.move(pos)
        if not r.get("ok"):
            self._set_status(r.get("reason", ""))
            return
        result = r.get("result", "continue")
        ai_move = r.get("ai_move")
        if result == "continue":
            msg = (f"spamton下在 {ai_move}" if self.lang == "zh" else f"The pet moved to {ai_move}")
        else:
            msg = self._result_text(result)
        self._set_status(msg)
        self._render_current_game()

    def _render_gomoku(self, layout):
        if self.game.over:
            if self.game.winner == "player":
                self._set_status("你赢了！" if self.lang == "zh" else "You win!")
            elif self.game.winner == "ai":
                self._set_status("SPAMTON赢了！" if self.lang == "zh" else "The pet wins!")
            else:
                self._set_status("平局！" if self.lang == "zh" else "Draw!")
        else:
            self._set_status(
                "你是 X，点击白色棋盘落子；X/O 为黑色" if self.lang == "zh"
                else "You are X. Click the white board; stones are black."
            )
        grid = QGridLayout()
        grid.setSpacing(0)
        for r in range(self.game.size):
            for c in range(self.game.size):
                v = self.game.board[r][c]
                btn = self._new_button(v if v != " " else "",
                                       lambda checked=False, rr=r, cc=c: self._gomoku_move(rr+1, cc+1))
                btn.setFixedSize(int(21*self.scale), int(21*self.scale))
                btn.setStyleSheet(
                    f"QPushButton{{font-size:{int(11*self.scale)}px;font-weight:bold;"
                    "background:white;color:black;border:1px solid #555;padding:0;}}"
                    "QPushButton:hover{background:#eeeeee;}"
                )
                if v != " " or self.game.over:
                    btn.setEnabled(False)
                grid.addWidget(btn, r, c)
        layout.addLayout(grid)

    def _gomoku_move(self, row, col):
        r = self.game.move(row, col)
        if not r.get("ok"):
            self._set_status(r.get("reason", ""))
            return
        result = r.get("result", "continue")
        ai_move = r.get("ai_move")
        if result == "continue":
            msg = (f"SPAMTON落子：{ai_move[0]},{ai_move[1]}"
                   if self.lang == "zh"
                   else f"Pet move: {ai_move[0]},{ai_move[1]}")
        else:
            msg = self._result_text(result)
        self._set_status(msg)
        self._render_current_game()

    def _render_idiom(self, layout):
        if self.game.current is None:
            intro = "点击“新局”开始" if self.lang == "zh" else "Click New to start."
            label = QLabel(intro)
            label.setStyleSheet("color:#1a1a2c;background:transparent;")
            layout.addWidget(label)
        else:
            current = self.game.current
            label = QLabel(
                (f"当前成语：{current}" if self.lang == "zh" else f"Current idiom: {current}")
            )
            label.setStyleSheet(
                f"font-size:{int(22*self.scale)}px;font-weight:bold;"
                "color:#1a1a2c;background:transparent;"
            )
            layout.addWidget(label)
            edit = QLineEdit()
            edit.setPlaceholderText(
                f"输入以“{current[-1]}”开头的成语……" if self.lang == "zh"
                else f"Enter an idiom starting with “{current[-1]}”..."
            )
            edit.setStyleSheet(
                f"font-size:{int(18*self.scale)}px;background:#f7f7fa;"
                "border:none;border-radius:7px;padding:6px;"
            )
            layout.addWidget(edit)
            row = QHBoxLayout()
            submit = self._new_button("接龙" if self.lang == "zh" else "Submit",
                                      lambda: self._idiom_submit(edit.text().strip()))
            edit.returnPressed.connect(lambda: self._idiom_submit(edit.text().strip()))
            hint = self._new_button("提示" if self.lang == "zh" else "Hint",
                                    self._idiom_hint)
            row.addWidget(submit); row.addWidget(hint)
            giveup = self._new_button("认输" if self.lang == "zh" else "Give up", self._idiom_giveup)
            row.addWidget(giveup)
            layout.addLayout(row)
            if self.game.used:
                used = QLabel(
                    ("已使用：" if self.lang == "zh" else "Used: ") +
                    " → ".join(self.game.used[-8:])
                )
                used.setWordWrap(True)
                used.setStyleSheet("color:#666;background:transparent;")
                layout.addWidget(used)
        self._set_status(
            (f"轮到你：输入以“{self.game.current[-1]}”开头的成语，点“接龙”或按 Enter；SPAMTON会接下一条。"
             if self.lang == "zh"
             else f"Your turn: enter an idiom starting with “{self.game.current[-1]}”, then Submit or press Enter.")
            if self.game.current else
            ("点击“新局”开始" if self.lang == "zh" else "Click New to start.")
        )

    def _idiom_submit(self, idiom):
        r = self.game.player(idiom)
        if not r.get("ok"):
            self._set_status(r.get("reason", ""))
            return
        if r.get("result") == "continue":
            self._game_message = (
                (f"SPAMTON接：{r.get('ai')}" if self.lang == "zh"
                 else f"Pet: {r.get('ai')}")
            )
        else:
            self._game_message = self._result_text(r.get("result"))
        self._render_current_game()

    def _idiom_giveup(self):
        r = self.game.give_up()
        if r.get("ok"):
            self._game_message = "你选择认输，SPAMTON获胜。" if self.lang == "zh" else "You gave up. Pet wins."
        else:
            self._set_status(r.get("reason", ""))
        self._render_current_game()

    def _idiom_hint(self):
        hint = self.game.hint()
        self._set_status(
            (f"提示：{hint}" if self.lang == "zh" else f"Hint: {hint}")
            if hint else ("没有可接的成语" if self.lang == "zh" else "No available idiom.")
        )

    def _render_uno(self, layout):
        top = self.game.top()
        color_text = getattr(self.game, "current_color", top[0])
        status = (
            f"桌面牌：{top[0]} {top[1]}　当前颜色：{color_text}　你的手牌：{len(self.game.hands[0])} 张"
            if self.lang == "zh" else
            f"Top: {top[0]} {top[1]} | Color: {color_text} | Your cards: {len(self.game.hands[0])}"
        )
        self._set_status(status)

        top_label = QLabel(f"{top[0]} {top[1]}　→　{color_text}")
        top_label.setAlignment(Qt.AlignCenter)
        top_label.setStyleSheet(
            f"font-size:{int(22*self.scale)}px;font-weight:bold;"
            "color:#1a1a2c;background:#f7f7fa;border-radius:8px;padding:8px;"
        )
        layout.addWidget(top_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        hand_widget = QWidget()
        hand_layout = QVBoxLayout(hand_widget)
        hand_layout.setSpacing(int(5*self.scale))
        for idx, card in enumerate(self.game.hands[0]):
            b = QPushButton(f"{idx+1}. {card[0]} {card[1]}", hand_widget)
            b.setStyleSheet(
                f"QPushButton{{font-size:{int(17*self.scale)}px;background:#1a1a2c;color:white;"
                f"border:none;border-radius:{int(6*self.scale)}px;padding:{int(5*self.scale)}px;}}"
                "QPushButton:disabled{background:#bbb;color:#eee;}"
            )
            b.setEnabled(self.game.can_play(card) and not self.game.over and self.game.turn == 0)
            b.clicked.connect(lambda checked=False, p=idx+1: self._uno_play(p))
            hand_layout.addWidget(b)
        scroll.setWidget(hand_widget)
        layout.addWidget(scroll, 1)

        draw = self._new_button(
            "摸牌" if self.lang == "zh" else "Draw",
            self._uno_draw,
            enabled=(not self.game.over and self.game.turn == 0)
        )
        layout.addWidget(draw)

    def _uno_play(self, index):
        if self.game is None or self.game.over or self.game.turn != 0:
            return
        try:
            r = self.game.player_play(index)
            if not r.get("ok"):
                self._set_status(r.get("reason", ""))
                return

            card = r.get("card")
            if r.get("result") == "player_win":
                self._game_message = self._result_text("player_win")
                self._render_current_game()
                return

            if r.get("skip"):
                self._game_message = (
                    "你打出了跳过/反转牌，继续你的回合" if self.lang == "zh"
                    else "You played Skip/Reverse; your turn continues"
                )
                self._render_current_game()
                return

            self._game_message = (
                (f"你出牌：{card[0]} {card[1]}；SPAMTON的回合" if self.lang == "zh"
                 else f"You played: {card[0]} {card[1]}; pet's turn")
            )
            self._render_current_game()
            QTimer.singleShot(800, self._uno_ai_turn)
        except Exception as e:
            self._set_status(
                ("UNO 出错，已取消本次操作：" if self.lang == "zh"
                 else "UNO error; action cancelled: ") + str(e)
            )
            self._render_current_game()

    def _uno_ai_turn(self):
        if self.game is None or self.current_game_id != "uno" or self.game.over:
            return
        if self.game.turn != 1:
            return
        try:
            ai = self.game.ai_turn()
            action = ai.get("action")
            card = ai.get("card")
            if ai.get("result") == "ai_win":
                self._game_message = self._result_text("ai_win")
                self._render_current_game()
                return
            if action == "draw":
                count = ai.get("count", 0)
                msg = (f"SPAMTON摸了 {count} 张牌" if self.lang == "zh"
                       else f"The pet drew {count} card(s)")
            elif card:
                msg = (f"SPAMTON出牌：{card[0]} {card[1]}" if self.lang == "zh"
                       else f"Pet played: {card[0]} {card[1]}")
            else:
                msg = "SPAMTON行动完成" if self.lang == "zh" else "Pet action complete"
            self._game_message = msg
            self._render_current_game()

            # SPAMTON打出跳过/反转后仍是SPAMTON回合，继续行动。
            if not self.game.over and self.game.turn == 1:
                QTimer.singleShot(800, self._uno_ai_turn)
        except Exception as e:
            self._set_status(
                ("UNO SPAMTON回合出错：" if self.lang == "zh" else "UNO pet-turn error: ") + str(e)
            )
            self.game.turn = 0
            self._render_current_game()

    def _uno_draw(self):
        if self.game is None or self.game.over or self.game.turn != 0:
            self._set_status("现在不是你的回合" if self.lang == "zh" else "Not your turn.")
            return
        try:
            card = self.game.draw(0)
            if card is None:
                self._set_status("牌堆没有可摸的牌" if self.lang == "zh" else "No cards available.")
                return
            self.game.turn = 1
            self._set_status(
                (f"你摸到：{card[0]} {card[1]}；SPAMTON回合" if self.lang == "zh"
                 else f"You drew: {card[0]} {card[1]}; pet's turn")
            )
            self._render_current_game()
            QTimer.singleShot(650, self._uno_ai_turn)
        except Exception as e:
            self._set_status(
                ("UNO 出错，程序不会退出：" if self.lang == "zh"
                 else "UNO error; the program will remain open: ") + str(e)
            )
            self._render_current_game()

    def _render_deal(self, layout):
        status = self.game.status()
        self._deal_selected = getattr(self, "_deal_selected", set())
        need = self.game.ROUNDS[min(self.game.round, len(self.game.ROUNDS)-1)]

        if self.game.over:
            if self.game.result is not None:
                self._set_status("游戏结束" if self.lang == "zh" else "Game over")
                final_box = QLabel(
                    f"最终开箱金额\n¥{self.game.result:,}" if self.lang == "zh"
                    else f"FINAL AMOUNT\n¥{self.game.result:,}"
                )
                final_box.setAlignment(Qt.AlignCenter)
                final_box.setMinimumHeight(int(72*self.scale))
                final_box.setStyleSheet(
                    f"font-size:{int(28*self.scale)}px;font-weight:900;color:#b00020;"
                    "background:#fff3f3;border:2px solid #b00020;border-radius:10px;"
                    f"padding:{int(8*self.scale)}px;"
                )
                layout.addWidget(final_box)
            else:
                self._set_status("游戏结束" if self.lang == "zh" else "Game over")
        elif self.game.offer is not None:
            self._set_status(f"庄家报价：¥{self.game.offer}" if self.lang == "zh" else f"Banker offer: ¥{self.game.offer}")
        elif self.game.player_case is None:
            self._set_status("请先选择你的最终箱子" if self.lang == "zh" else "Choose your final case first.")
        else:
            self._set_status(
                f"第 {self.game.round + 1} 轮：需要开启 {need} 个箱子，已选择 {len(self._deal_selected)}/{need}"
                if self.lang == "zh" else f"Round {self.game.round + 1}: select {len(self._deal_selected)}/{need} cases."
            )

        if self.game.player_case is not None:
            own = QLabel(f"你的最终箱子：{self.game.player_case}号" if self.lang == "zh" else f"Your final case: {self.game.player_case}")
            own.setAlignment(Qt.AlignCenter)
            own.setStyleSheet(f"font-size:{int(16*self.scale)}px;font-weight:bold;color:#1a1a2c;background:transparent;")
            layout.addWidget(own)

            info = QLabel(
                f"本轮需要开启 {need} 个箱子　已选择 {len(self._deal_selected)}/{need}"
                if self.lang == "zh" else f"This round: {len(self._deal_selected)}/{need} cases selected"
            )
            info.setAlignment(Qt.AlignCenter)
            info.setStyleSheet(f"font-size:{int(14*self.scale)}px;color:#333;background:transparent;")
            layout.addWidget(info)

        if getattr(self, "_deal_final_pending", False) and not self.game.over:
            final_hint = QLabel(
                "最后一个箱子已打开，现在开启你的最终箱子" if self.lang == "zh"
                else "The last remaining case is open. Now reveal your final case."
            )
            final_hint.setAlignment(Qt.AlignCenter)
            final_hint.setStyleSheet(f"font-size:{int(16*self.scale)}px;font-weight:bold;color:#8b0000;background:transparent;")
            layout.addWidget(final_hint)
            final_btn = self._new_button(
                "开启我的最终箱子" if self.lang == "zh" else "Reveal My Final Case",
                self._deal_reveal_final
            )
            final_btn.setMinimumHeight(int(42*self.scale))
            layout.addWidget(final_btn)

        # 箱子和下面的操作区必须是两个独立的区域。
        # 箱子滚动区域内部同时承载“本次开箱”记录，避免记录把外面的按钮往下挤。
        box_scroll = QScrollArea()
        box_scroll.setWidgetResizable(True)
        box_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        box_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        box_scroll.setFrameShape(QScrollArea.NoFrame)
        box_scroll.setMinimumHeight(int(100*self.scale))
        box_scroll.setMaximumHeight(int(125*self.scale))
        box_scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollBar:vertical{width:8px;background:#e5e5e5;border-radius:4px;}"
            "QScrollBar::handle:vertical{min-height:24px;background:#888;border-radius:4px;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0px;}"
        )

        box_page = QWidget()
        box_page.setStyleSheet("background:transparent;")
        box_layout = QVBoxLayout(box_page)
        box_layout.setSpacing(int(4*self.scale))
        box_layout.setContentsMargins(int(4*self.scale), int(4*self.scale), int(4*self.scale), int(4*self.scale))
        box_layout.setAlignment(Qt.AlignTop)

        grid = QGridLayout()
        grid.setSpacing(int(3*self.scale))
        grid.setContentsMargins(0, 0, 0, 0)
        visible = 0
        for n in range(1, 27):
            if n in self.game.opened or n == self.game.player_case:
                continue
            label = f"✓ {n}" if n in self._deal_selected else str(n)
            b = self._new_button(label, lambda checked=False, x=n: self._deal_select(x))
            b.setFixedSize(int(58*self.scale), int(31*self.scale))
            grid.addWidget(b, visible // 5, visible % 5)
            visible += 1
        box_layout.addLayout(grid)

        last = getattr(self, "_deal_last_opened", [])
        if last:
            title = QLabel("本次开箱：" if self.lang == "zh" else "Opened:")
            title.setAlignment(Qt.AlignCenter)
            title.setStyleSheet(f"font-size:{int(13*self.scale)}px;font-weight:bold;color:#333;background:transparent;")
            box_layout.addWidget(title)
            for case, value in last:
                lab = QLabel(f"{case}号箱：¥{value}" if self.lang == "zh" else f"Case {case}: ¥{value}")
                lab.setAlignment(Qt.AlignCenter)
                lab.setStyleSheet(f"font-size:{int(12*self.scale)}px;color:#333;background:transparent;")
                box_layout.addWidget(lab)

        box_scroll.setWidget(box_page)
        layout.addWidget(box_scroll)

        # 普通开箱按钮只在没有庄家报价、且还存在普通开箱阶段时显示。
        # 报价出现后不再显示“开箱”，避免进入最后阶段时出现误操作。
        if self.game.offer is None and not getattr(self, "_deal_final_pending", False) and not self.game.over:
            open_btn = self._new_button("开箱" if self.lang == "zh" else "Open", self._deal_open_selected)
            open_btn.setMinimumHeight(int(34*self.scale))
            layout.addWidget(open_btn)

        if self.game.offer is not None:
            offer = QLabel(f"庄家报价：¥{self.game.offer}" if self.lang == "zh" else f"Banker offer: ¥{self.game.offer}")
            offer.setAlignment(Qt.AlignCenter)
            offer.setStyleSheet(f"font-size:{int(17*self.scale)}px;font-weight:bold;color:#1a1a2c;background:transparent;")
            layout.addWidget(offer)
            row = QHBoxLayout()
            row.setSpacing(int(6*self.scale))
            deal_btn = self._new_button("Deal" if self.lang == "en" else "成交", lambda: self._deal_respond(True))
            no_deal_btn = self._new_button("No Deal" if self.lang == "en" else "继续", lambda: self._deal_respond(False))
            deal_btn.setMinimumHeight(int(34*self.scale))
            no_deal_btn.setMinimumHeight(int(34*self.scale))
            row.addWidget(deal_btn)
            row.addWidget(no_deal_btn)
            layout.addLayout(row)

    def _deal_select(self, n):
        if self.game.player_case is None:
            self._deal_last_opened = getattr(self, "_deal_last_opened", [])
            try:
                r = self.game.choose_case(n)
                if not r.get("ok"):
                    self._set_status(r.get("reason", ""))
                    return
                self._deal_selected.clear()
                self._deal_last_opened = []
            except Exception as e:
                self._set_status(str(e))
                return
            self._render_current_game()
            return

        if n == self.game.player_case:
            self._set_status("不能打开自己的最终箱子" if self.lang == "zh" else "You cannot open your final case.")
            return

        need = self.game.ROUNDS[min(self.game.round, len(self.game.ROUNDS)-1)]
        if n in self._deal_selected:
            self._deal_selected.remove(n)
        else:
            if len(self._deal_selected) >= need:
                self._set_status(f"本轮最多选择 {need} 个箱子" if self.lang == "zh" else f"You can select only {need} cases this round.")
                return
            self._deal_selected.add(n)
        self._render_current_game()

    def _deal_open_selected(self):
        need = self.game.ROUNDS[min(self.game.round, len(self.game.ROUNDS)-1)]
        if len(self._deal_selected) != need:
            self._set_status(
                f"本轮需要开启 {need} 个箱子，目前选择 {len(self._deal_selected)} 个"
                if self.lang == "zh" else
                f"This round requires {need} cases; {len(self._deal_selected)} selected.")
            return
        try:
            r = self.game.open(sorted(self._deal_selected))
            if not r.get("ok"):
                self._set_status(r.get("reason", ""))
                return
            self._deal_last_opened = list(r.get("opened", []))
            self._deal_selected.clear()
            if r.get("offer") is not None:
                opened_text = "；".join(f"{case}号箱 ¥{value}" for case, value in self._deal_last_opened)
                self._set_status(
                    f"开启：{opened_text}\n银行报价：¥{r['offer']}"
                    if self.lang == "zh" else
                    f"Opened: {opened_text}\nOffer: ¥{r['offer']}"
                )
            else:
                self._set_status(self._result_text(r.get("result", "continue")))
        except Exception as e:
            self._set_status(str(e))
        self._render_current_game()

    def _deal_reveal_final(self):
        if not getattr(self, "_deal_final_pending", False) or self.game.over:
            return
        try:
            # 最终按钮只负责打开玩家最初选定的箱子，不再进入普通选箱流程。
            final_r = self.game.swap_or_reveal(False)
            if final_r.get("ok") and final_r.get("result") == "final":
                self._deal_final_pending = False
                self._deal_last_opened = [(final_r["player_case"], final_r["value"]) ]
                self._set_status(
                    f"最终打开 {final_r['player_case']}号箱：¥{final_r['value']}"
                    if self.lang == "zh" else
                    f"Final case {final_r['player_case']}: ¥{final_r['value']}"
                )
            else:
                self._set_status(final_r.get("reason", "最终箱子开启失败"))
        except Exception as e:
            self._set_status(str(e))
        self._render_current_game()

    def _deal_respond(self, deal):
        r = self.game.respond(deal)
        if not r.get("ok"):
            self._set_status(r.get("reason", ""))
        elif r.get("result") == "deal":
            self._set_status(
                f"成交：¥{r['value']}" if self.lang == "zh"
                else f"Deal: ¥{r['value']}"
            )
        elif r.get("result") == "final":
            self._set_status(
                f"最终金额：¥{r['value']}" if self.lang == "zh"
                else f"Final value: ¥{r['value']}"
            )
        elif r.get("result") == "final_choice":
            # 最终报价被拒绝后，只剩一个非玩家箱子：先把这个最后的普通箱子打开，
            # 然后才出现“开启我的最终箱子”。这里不再显示普通“开箱”按钮。
            left = list(self.game.remaining())
            if len(left) == 1:
                try:
                    last_r = self.game.open(left)
                    if last_r.get("ok"):
                        self._deal_last_opened = list(last_r.get("opened", []))
                        self._set_status(
                            "最后一个普通箱子已打开，庄家再次报价" if self.lang == "zh"
                            else "The last ordinary case is open. The banker makes another offer."
                        )
                    else:
                        self._set_status(last_r.get("reason", "最后一个箱子开启失败"))
                except Exception as e:
                    self._set_status(str(e))
            else:
                # 最后一个普通箱子的报价被拒绝后，才进入最终箱子阶段。
                self._deal_final_pending = True
                self._set_status(
                    "庄家报价被拒绝，现在可以开启你的最终箱子" if self.lang == "zh"
                    else "No Deal. You can now reveal your final case."
                )
        else:
            self._set_status("继续游戏" if self.lang == "zh" else "Continue")
        self._render_current_game()

    def _render_buckshot(self, layout):
        st = self.game.status()
        self._set_status(
            (f"你 {st['player_hp']} HP　SPAMTON {st['pet_hp']} HP　剩余子弹 {st['shells']}"
             if self.lang == "zh"
             else f"You {st['player_hp']} HP | Pet {st['pet_hp']} HP | Shells {st['shells']}"))
        row = QHBoxLayout()
        row.addWidget(self._new_button("射SPAMTON" if self.lang == "zh" else "Shoot Pet",
                                       lambda: self._buckshot("pet")))
        row.addWidget(self._new_button("射自己" if self.lang == "zh" else "Shoot Self",
                                       lambda: self._buckshot("self")))
        layout.addLayout(row)
        note = QLabel(
            "每回合结束后SPAMTON行动。" if self.lang == "zh"
            else "The pet acts automatically after your turn."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#666;background:transparent;")
        layout.addWidget(note)

    def _buckshot(self, target):
        r = self.game.player_action(target)
        if not r.get("ok"):
            self._set_status(r.get("reason", ""))
            return

        live = r.get("live")
        msg = ("实弹" if live else "空弹") if self.lang == "zh" else ("Live" if live else "Blank")

        if r.get("result") in ("player_win", "ai_win"):
            self._game_message = self._result_text(r["result"])
            self._render_current_game()
            return

        # 实弹会把回合交给SPAMTON；空弹则仍然是玩家回合。
        if getattr(self.game, "turn", 0) == 1:
            msg += "；SPAMTON回合" if self.lang == "zh" else "; Pet's turn"
            self._game_message = msg
            self._render_current_game()
            QTimer.singleShot(800, self._buckshot_ai_turn)
            return

        self._game_message = msg + ("；继续你的回合" if self.lang == "zh" else "; Your turn continues")
        self._render_current_game()

    def _buckshot_ai_turn(self):
        if self.game is None or self.current_game_id != "buckshot" or self.game.over:
            return
        if getattr(self.game, "turn", 0) != 1:
            return

        try:
            ai = self.game.ai_action()
            live = ai.get("live")
            target = ai.get("target")
            if ai.get("result") == "ai_win":
                self._game_message = "SPAMTON开枪并获胜" if self.lang == "zh" else "The pet fired and won"
            else:
                if live:
                    if target == "self":
                        text = "SPAMTON射击自己：实弹" if self.lang == "zh" else "The pet shot itself: live shell"
                    else:
                        text = "SPAMTON射击你：实弹" if self.lang == "zh" else "The pet shot you: live shell"
                else:
                    if target == "self":
                        text = "SPAMTON射击自己：空弹" if self.lang == "zh" else "The pet shot itself: blank"
                    else:
                        text = "SPAMTON射击你：空弹" if self.lang == "zh" else "The pet shot you: blank"
                self._game_message = text

                # 空弹时 Buckshot 规则是同一射手继续回合。
                # 因此SPAMTON打出空弹后不能停在“SPAMTON回合”，必须继续行动。
                if not self.game.over and getattr(self.game, "turn", 0) == 1:
                    self._render_current_game()
                    QTimer.singleShot(800, self._buckshot_ai_turn)
                    return
        except Exception as e:
            self._game_message = (("SPAMTON回合出错：" if self.lang == "zh" else "Pet turn error: ") + str(e))
            self.game.turn = 0
        self._render_current_game()

    def _render_roulette(self, layout):
        self._set_status(
            "点击开枪" if self.lang == "zh" else "Pull the trigger."
        )
        b = self._new_button("开枪" if self.lang == "zh" else "Pull",
                             self._roulette_pull)
        b.setFixedHeight(int(50*self.scale))
        layout.addWidget(b)
        note = QLabel(
            "SPAMTON会进行下一次" if self.lang == "zh"
            else "The pet pulls automatically after you."
        )
        note.setStyleSheet("color:#666;background:transparent;")
        layout.addWidget(note)

    def _roulette_pull(self):
        r = self.game.player_pull()
        if not r.get("ok"):
            self._set_status(r.get("reason", ""))
            return

        if r.get("fired"):
            self._game_message = "你中弹了，游戏结束" if self.lang == "zh" else "You fired. Game over."
            self._render_current_game()
            return

        self._game_message = "空枪；SPAMTON回合" if self.lang == "zh" else "Blank; pet's turn"
        self._render_current_game()
        QTimer.singleShot(800, self._roulette_ai_turn)

    def _roulette_ai_turn(self):
        if self.game is None or self.current_game_id != "roulette" or self.game.over:
            return
        if getattr(self.game, "turn", 0) != 1:
            return

        try:
            ai = self.game.ai_pull()
            if ai.get("fired"):
                self._game_message = "SPAMTON中弹，你赢了" if self.lang == "zh" else "The pet fired. You win."
            else:
                self._game_message = "SPAMTON开枪：空枪，轮到你" if self.lang == "zh" else "The pet pulled: blank; your turn"
        except Exception as e:
            self._game_message = (("SPAMTON回合出错：" if self.lang == "zh" else "Pet turn error: ") + str(e))
            self.game.turn = 0
        self._render_current_game()

    def showEvent(self, event):
        super().showEvent(event)
        self.update_position()

    def keyPressEvent(self, event):
        # 游戏窗口可用 Esc 直接关闭。
        if event.key() == Qt.Key_Escape:
            self.hide()
            event.accept()
            return
        super().keyPressEvent(event)

# ---------- 便签窗口 ----------
class NoteWindow(BasePanel):
    def __init__(self, parent=None):
        super().__init__(parent, panel_type="note")

        self.container = QWidget(self)
        self.container.setGeometry(0, 0, self.panel_width, self.panel_height)
        self.container.setStyleSheet("background: transparent;")

        self.title_label = QLabel(self.container)
        self.title_label.setStyleSheet(
            f"color: #1a1a2c; font-size: {int(24 * self.scale)}px; "
            "font-weight: bold; background: transparent;"
        )
        self.title_label.setGeometry(
            int(60 * self.scale), int(55 * self.scale),
            int(300 * self.scale), int(45 * self.scale)
        )

        self.note_edit = QPlainTextEdit(self.container)
        self.note_edit.setGeometry(
            int(55 * self.scale), int(105 * self.scale),
            int(340 * self.scale), int(315 * self.scale)
        )
        self.note_edit.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.note_edit.setPlaceholderText("Write your notes here...")
        self.note_edit.setStyleSheet(f"""
            QPlainTextEdit {{
                background: white;
                color: #2c3e50;
                border: none;
                border-radius: {int(14 * self.scale)}px;
                padding: {int(14 * self.scale)}px;
                font-size: {int(20 * self.scale)}px;
                selection-background-color: #d9eaff;
            }}
            QScrollBar:vertical {{
                background: #f0f0f0;
                width: {int(8 * self.scale)}px;
                border-radius: {int(4 * self.scale)}px;
            }}
            QScrollBar::handle:vertical {{
                background: #1a1a2c;
                border-radius: {int(4 * self.scale)}px;
                min-height: {int(30 * self.scale)}px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        self.save_btn = QPushButton(self.container)
        self.save_btn.setGeometry(
            int(95 * self.scale), int(440 * self.scale),
            int(115 * self.scale), int(40 * self.scale)
        )
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: {int(14 * self.scale)}px;
                background-color: #1a1a2c;
                color: white;
                border-radius: {int(7 * self.scale)}px;
                padding: {int(5 * self.scale)}px {int(10 * self.scale)}px;
                border: none;
            }}
            QPushButton:hover {{ background-color: #2a2a4c; }}
            QPushButton:pressed {{ background-color: #111122; }}
        """)
        self.save_btn.clicked.connect(self.save_note)

        self.clear_btn = QPushButton(self.container)
        self.clear_btn.setGeometry(
            int(240 * self.scale), int(440 * self.scale),
            int(115 * self.scale), int(40 * self.scale)
        )
        self.clear_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: {int(14 * self.scale)}px;
                background-color: #e67e22;
                color: white;
                border-radius: {int(7 * self.scale)}px;
                padding: {int(5 * self.scale)}px {int(10 * self.scale)}px;
                border: none;
            }}
            QPushButton:hover {{ background-color: #f39c12; }}
            QPushButton:pressed {{ background-color: #d35400; }}
        """)
        self.clear_btn.clicked.connect(self.clear_note)

        self.close_btn = QPushButton("✕", self.container)
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: {int(18 * self.scale)}px;
                background: transparent;
                color: #1a1a2c;
                border: none;
                padding: {int(5 * self.scale)}px;
            }}
            QPushButton:hover {{ color: #e74c3c; }}
        """)
        self.close_btn.setGeometry(
            int(410 * self.scale), int(10 * self.scale),
            int(30 * self.scale), int(30 * self.scale)
        )
        self.close_btn.clicked.connect(self.hide)

        self.update_language(parent.lang if parent else "zh")
        self.reload_note()

    def reload_note(self):
        self.note_edit.setPlainText(load_notes())
        self.note_edit.moveCursor(self.note_edit.textCursor().End)
        self.note_edit.verticalScrollBar().setValue(
            self.note_edit.verticalScrollBar().maximum()
        )

    def showEvent(self, event):
        super().showEvent(event)
        self.reload_note()
        self.note_edit.setFocus()

    def save_note(self):
        if save_notes(self.note_edit.toPlainText()):
            self.parent_pet.add_dialog(
                random.choice(get_dialogues(self.parent_pet.lang, "note_saved"))
            )
        else:
            self.parent_pet.add_dialog(
                random.choice(get_dialogues(self.parent_pet.lang, "note_error"))
            )

    def clear_note(self):
        self.note_edit.clear()
        self.save_note()

    def update_language(self, lang):
        if lang == "en":
            self.title_label.setText("Notes")
            self.note_edit.setPlaceholderText("Write your notes here...")
            self.save_btn.setText("Save")
            self.clear_btn.setText("Clear")
            self.close_btn.setToolTip("Close")
        else:
            self.title_label.setText("便签")
            self.note_edit.setPlaceholderText("在这里输入你的便签内容……")
            self.save_btn.setText("保存")
            self.clear_btn.setText("清空")
            self.close_btn.setToolTip("关闭")


# ---------- 控制面板 ----------
class ControlPanel(BasePanel):
    def __init__(self, parent=None):
        super().__init__(parent, panel_type="control")
        self.container = QWidget(self)
        self.container.setGeometry(0, 0, self.panel_width, self.panel_height)
        self.container.setStyleSheet("background: transparent;")

        self.title_label = QLabel(self.container)
        self.title_label.setStyleSheet(f"color: #1a1a2c; font-size: {int(28 * self.scale)}px; font-weight: bold; background: transparent;")
        self.title_label.setGeometry(int(60 * self.scale), int(60 * self.scale), int(330 * self.scale), int(40 * self.scale))

        # 番茄钟组
        group1 = QGroupBox(self.container)
        group1.setStyleSheet(f"""
            QGroupBox {{
                color: #1a1a2c;
                font-size: {int(20 * self.scale)}px;
                border: 3px solid #1a1a2c;
                border-radius: {int(10 * self.scale)}px;
                margin-top: {int(10 * self.scale)}px;
                background: white;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {int(10 * self.scale)}px;
                padding: 0 {int(10 * self.scale)}px;
                color: #1a1a2c;
                background: white;
            }}
        """)
        group1.setGeometry(int(60 * self.scale), int(110 * self.scale), int(280 * self.scale), int(140 * self.scale))

        layout1 = QGridLayout(group1)
        layout1.setSpacing(int(8 * self.scale))
        layout1.setContentsMargins(int(10 * self.scale), int(20 * self.scale), int(10 * self.scale), int(10 * self.scale))

        self.tomato_label = QLabel(self.container)
        self.tomato_label.setStyleSheet(f"font-size: {int(28 * self.scale)}px; color: #1a1a2c;")
        self.tomato_label.hide()

        # 保存上一次控制面板的设置，重新打开控制面板时不重置。
        saved = getattr(parent, '_control_settings', {}) if parent else {}
        self.tomato_spin = QSpinBox()
        self.tomato_spin.setRange(1, 120)
        self.tomato_spin.setValue(int(saved.get('tomato_minutes', 5)))
        self.tomato_spin.setSuffix(" min" if (parent and parent.lang == 'en') else " 分钟")
        self.tomato_spin.setStyleSheet(f"font-size: {int(16 * self.scale)}px; background: white; color: #1a1a2c;")
        self.tomato_spin_label = QLabel()
        layout1.addWidget(self.tomato_spin_label, 1, 0)
        layout1.addWidget(self.tomato_spin, 1, 1)

        self.tomato_btn = QPushButton()
        self.tomato_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: {int(16 * self.scale)}px;
                background-color: #27ae60;
                color: white;
                border-radius: {int(5 * self.scale)}px;
                padding: {int(5 * self.scale)}px {int(10 * self.scale)}px;
                border: none;
            }}
            QPushButton:hover {{ background-color: #2ecc71; }}
            QPushButton:pressed {{ background-color: #229954; }}
        """)
        self.tomato_btn.clicked.connect(self.toggle_tomato)
        layout1.addWidget(self.tomato_btn, 2, 0)

        self.tomato_reset_btn = QPushButton()
        self.tomato_reset_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: {int(16 * self.scale)}px;
                background-color: #e67e22;
                color: white;
                border-radius: {int(5 * self.scale)}px;
                padding: {int(5 * self.scale)}px {int(10 * self.scale)}px;
                border: none;
            }}
            QPushButton:hover {{ background-color: #f39c12; }}
            QPushButton:pressed {{ background-color: #d35400; }}
        """)
        self.tomato_reset_btn.clicked.connect(self.reset_tomato)
        layout1.addWidget(self.tomato_reset_btn, 2, 1)

        self.tomato_timer = QTimer(self)
        self.tomato_timer.timeout.connect(self.update_tomato)
        self.tomato_remaining = int(getattr(parent, '_tomato_remaining_saved', 0)) if parent else 0
        self.tomato_running = bool(getattr(parent, '_tomato_running_saved', False)) if parent else False
        if self.tomato_running and self.tomato_remaining <= 0:
            self.tomato_running = False

        # 提醒设置组
        group2 = QGroupBox(self.container)
        group2.setStyleSheet(f"""
            QGroupBox {{
                color: #1a1a2c;
                font-size: {int(20 * self.scale)}px;
                border: 3px solid #1a1a2c;
                border-radius: {int(10 * self.scale)}px;
                margin-top: {int(10 * self.scale)}px;
                background: white;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {int(10 * self.scale)}px;
                padding: 0 {int(10 * self.scale)}px;
                color: #1a1a2c;
                background: white;
            }}
        """)
        group2.setGeometry(int(60 * self.scale), int(270 * self.scale), int(280 * self.scale), int(200 * self.scale))

        layout2 = QGridLayout(group2)
        layout2.setSpacing(int(5 * self.scale))
        layout2.setContentsMargins(int(10 * self.scale), int(20 * self.scale), int(10 * self.scale), int(10 * self.scale))

        self.drink_check = QCheckBox()
        self.drink_check.setChecked(bool(saved.get('drink_enabled', True)))
        self.drink_check.setStyleSheet(f"color: #1a1a2c; font-size: {int(14 * self.scale)}px;")
        layout2.addWidget(self.drink_check, 0, 0)
        self.drink_spin = QSpinBox()
        self.drink_spin.setRange(5, 120)
        self.drink_spin.setValue(int(saved.get('drink_minutes', 45)))
        self.drink_spin.setSuffix(" min" if (parent and parent.lang == 'en') else " 分钟")
        self.drink_spin.setStyleSheet(f"font-size: {int(14 * self.scale)}px; background: white; color: #1a1a2c;")
        layout2.addWidget(self.drink_spin, 0, 1)

        self.sleep_check = QCheckBox()
        self.sleep_check.setChecked(bool(saved.get('sleep_enabled', True)))
        self.sleep_check.setStyleSheet(f"color: #1a1a2c; font-size: {int(14 * self.scale)}px;")
        layout2.addWidget(self.sleep_check, 1, 0)
        sleep_h_layout = QHBoxLayout()
        self.sleep_hour = QSpinBox()
        self.sleep_hour.setRange(0, 23)
        self.sleep_hour.setValue(int(saved.get('sleep_hour', 22)))
        self.sleep_hour.setStyleSheet(f"font-size: {int(14 * self.scale)}px; background: white; color: #1a1a2c;")
        self.sleep_min = QSpinBox()
        self.sleep_min.setRange(0, 59)
        self.sleep_min.setValue(int(saved.get('sleep_min', 0)))
        self.sleep_min.setStyleSheet(f"font-size: {int(14 * self.scale)}px; background: white; color: #1a1a2c;")
        self.sleep_time_label = QLabel("Time:" if (parent and parent.lang == 'en') else "时间：")
        sleep_h_layout.addWidget(self.sleep_time_label)
        sleep_h_layout.addWidget(self.sleep_hour)
        sleep_h_layout.addWidget(QLabel("h" if (parent and parent.lang == 'en') else "时"))
        sleep_h_layout.addWidget(self.sleep_min)
        sleep_h_layout.addWidget(QLabel("m" if (parent and parent.lang == 'en') else "分"))
        layout2.addLayout(sleep_h_layout, 1, 1)

        self.eat_label = QLabel()
        self.eat_label.setStyleSheet(f"font-size: {int(16 * self.scale)}px; color: #1a1a2c; padding: {int(5 * self.scale)}px 0;")
        layout2.addWidget(self.eat_label, 2, 0, 1, 2)

        self.reminder_elapsed = dict(getattr(parent, '_reminder_elapsed', {'喝水': 0})) if parent else {'喝水': 0}
        self.reminder_timer = None

        # 控制面板重新打开/重建时恢复上一轮设置和提示计时进度。
        if parent is not None:
            self._save_control_settings = self._persist_settings
            self.tomato_spin.valueChanged.connect(self._save_control_settings)
            self.drink_check.stateChanged.connect(self._save_control_settings)
            self.drink_spin.valueChanged.connect(self._save_control_settings)
            self.sleep_check.stateChanged.connect(self._save_control_settings)
            self.sleep_hour.valueChanged.connect(self._save_control_settings)
            self.sleep_min.valueChanged.connect(self._save_control_settings)
            self._persist_settings()

        self.lunch_triggered = False
        self.dinner_triggered = False
        self.sleep_triggered = False
        self.drag_pos = None

        self.update_language(parent.lang if parent else 'zh')
        self.update_tomato_display()

    def _persist_settings(self, *args):
        if self.parent_pet is None:
            return
        # 控制面板只负责修改设置，不负责提醒计时。
        # reminder_elapsed 由 DesktopPet 主提醒系统独立维护，避免打开/修改控制面板时把计时覆盖回旧值。
        self.parent_pet._control_settings.update({
            'tomato_minutes': self.tomato_spin.value(),
            'drink_enabled': self.drink_check.isChecked(),
            'drink_minutes': self.drink_spin.value(),
            'sleep_enabled': self.sleep_check.isChecked(),
            'sleep_hour': self.sleep_hour.value(),
            'sleep_min': self.sleep_min.value(),
            'tomato_remaining': int(getattr(self.parent_pet, '_tomato_remaining_saved', 0)),
            'tomato_running': bool(getattr(self.parent_pet, '_tomato_running_saved', False)),
        })
        self.parent_pet._save_control_settings()

    def update_language(self, lang):
        if lang == 'en':
            self.title_label.setText("Control Panel")
            self.sleep_time_label.setText("Time:")
            self.tomato_label.setText("")
            self.tomato_spin_label.setText("Set Duration:")
            self.tomato_btn.setText("▶ Start")
            self.tomato_reset_btn.setText("⟳ Reset")
            self.drink_check.setText("Drink")
            self.sleep_check.setText("Sleep")
            self.eat_label.setText("Lunch: 12:00  |  Dinner: 18:00")
            group1 = self.findChild(QGroupBox)
            if group1:
                group1.setTitle("Focus")
            groups = self.findChildren(QGroupBox)
            if len(groups) > 1:
                groups[1].setTitle("Reminders")
        else:
            self.title_label.setText("控制面板")
            self.sleep_time_label.setText("时间：")
            self.tomato_label.setText("")
            self.tomato_spin_label.setText("设置时长：")
            self.tomato_btn.setText("▶ 开始")
            self.tomato_reset_btn.setText("⟳ 重置")
            self.drink_check.setText("喝水")
            self.sleep_check.setText("睡觉")
            self.eat_label.setText("午饭：12点  |  晚饭：18点")
            group1 = self.findChild(QGroupBox)
            if group1:
                group1.setTitle("番茄钟")
            groups = self.findChildren(QGroupBox)
            if len(groups) > 1:
                groups[1].setTitle("提醒设置")
        self.tomato_spin.setSuffix(" min" if lang == 'en' else " 分钟")
        self.drink_spin.setSuffix(" min" if lang == 'en' else " 分钟")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.bg_pixmap)
        super().paintEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
        elif event.button() == Qt.RightButton:
            self.close()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos is not None:
            self.move(event.globalPos() - self.drag_pos)
            self._fixed_x = self.x()
            self._fixed_y = self.y()
            self._position_fixed = True

    def mouseReleaseEvent(self, event):
        self.drag_pos = None

    def toggle_tomato(self):
        if not self.tomato_running:
            minutes = self.tomato_spin.value()
            self.tomato_remaining = minutes * 60
            self.tomato_running = True
            if self.parent_pet is not None:
                self.parent_pet._tomato_remaining_saved = self.tomato_remaining
                self.parent_pet._tomato_running_saved = True
                self.parent_pet._save_control_settings()
            lang = self.parent_pet.lang if self.parent_pet else 'zh'
            self.tomato_btn.setText("Pause" if lang == 'en' else "暂停")
            self.tomato_btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: {int(16 * self.scale)}px;
                    background-color: #e67e22;
                    color: white;
                    border-radius: {int(5 * self.scale)}px;
                    padding: {int(5 * self.scale)}px {int(10 * self.scale)}px;
                    border: none;
                }}
                QPushButton:hover {{ background-color: #f39c12; }}
                QPushButton:pressed {{ background-color: #d35400; }}
            """)
            self.tomato_timer.start(1000)
            self.update_tomato_display()
            self.parent_pet.start_tomato_display(self.tomato_remaining)
        else:
            self.tomato_timer.stop()
            self.tomato_running = False
            if self.parent_pet is not None:
                self.parent_pet._tomato_remaining_saved = self.tomato_remaining
                self.parent_pet._tomato_running_saved = False
                self.parent_pet._save_control_settings()
            lang = self.parent_pet.lang if self.parent_pet else 'zh'
            self.tomato_btn.setText("▶ Continue" if lang == 'en' else "继续")
            self.tomato_btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: {int(16 * self.scale)}px;
                    background-color: #27ae60;
                    color: white;
                    border-radius: {int(5 * self.scale)}px;
                    padding: {int(5 * self.scale)}px {int(10 * self.scale)}px;
                    border: none;
                }}
                QPushButton:hover {{ background-color: #2ecc71; }}
                QPushButton:pressed {{ background-color: #229954; }}
            """)
            self.parent_pet.stop_tomato_display()

    def reset_tomato(self):
        self.tomato_timer.stop()
        self.tomato_running = False
        lang = self.parent_pet.lang if self.parent_pet else 'zh'
        self.tomato_btn.setText("▶ Start" if lang == 'en' else "▶ 开始")
        self.tomato_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: {int(16 * self.scale)}px;
                background-color: #27ae60;
                color: white;
                border-radius: {int(5 * self.scale)}px;
                padding: {int(5 * self.scale)}px {int(10 * self.scale)}px;
                border: none;
            }}
            QPushButton:hover {{ background-color: #2ecc71; }}
            QPushButton:pressed {{ background-color: #229954; }}
        """)
        minutes = self.tomato_spin.value()
        self.tomato_remaining = minutes * 60
        if self.parent_pet is not None:
            self.parent_pet._tomato_remaining_saved = self.tomato_remaining
            self.parent_pet._tomato_running_saved = False
            self.parent_pet._save_control_settings()
        self.update_tomato_display()
        self.parent_pet.stop_tomato_display()

    def update_tomato(self):
        if self.tomato_remaining > 0:
            self.tomato_remaining -= 1
            if self.parent_pet is not None:
                self.parent_pet._tomato_remaining_saved = self.tomato_remaining
                self.parent_pet._tomato_running_saved = True
                self.parent_pet._save_control_settings()
            self.update_tomato_display()
            self.parent_pet.update_tomato_display(self.tomato_remaining)
        else:
            self.tomato_timer.stop()
            self.tomato_running = False
            if self.parent_pet is not None:
                self.parent_pet._tomato_remaining_saved = 0
                self.parent_pet._tomato_running_saved = False
                self.parent_pet._save_control_settings()
            lang = self.parent_pet.lang if self.parent_pet else 'zh'
            self.tomato_btn.setText("▶ Start" if lang == 'en' else "▶ 开始")
            self.tomato_btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: {int(16 * self.scale)}px;
                    background-color: #27ae60;
                    color: white;
                    border-radius: {int(5 * self.scale)}px;
                    padding: {int(5 * self.scale)}px {int(10 * self.scale)}px;
                    border: none;
                }}
                QPushButton:hover {{ background-color: #2ecc71; }}
                QPushButton:pressed {{ background-color: #229954; }}
            """)
            self.parent_pet.stop_tomato_display()
            self.parent_pet.add_reminder_dialog('drink', 'drink')
            self.update_tomato_display()

    def update_tomato_display(self):
        m, s = divmod(self.tomato_remaining, 60)
        lang = self.parent_pet.lang if self.parent_pet else 'zh'
        if lang == 'en':
            self.tomato_label.setText(f"Rest Time: {m:02d}:{s:02d}")
        else:
            self.tomato_label.setText(f"休息倒计时：{m:02d}:{s:02d}")

    def check_reminders(self):
        # 提醒完全由 DesktopPet 主程序负责。
        # 保留此方法仅用于兼容旧调用；控制面板本身不再累计或触发提醒。
        if self.parent_pet is not None:
            self.parent_pet.check_reminders(initial=True)


# ---------- 带淡入淡出的QLabel ----------
class FadeLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fade_duration = 150
        self.opacity_effect = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_effect.setDuration(self.fade_duration)
        self.opacity_effect.setEasingCurve(QEasingCurve.InOutQuad)
        self.setWindowOpacity(1.0)
        self._fade_in_pixmap = None
        self._is_fading = False
        self._pending_pixmap = None

    def setPixmapWithFade(self, pixmap, force=False):
        if pixmap is None or pixmap.isNull():
            return
        if self.pixmap() is None or self.pixmap().isNull():
            self.setPixmap(pixmap)
            self.setWindowOpacity(1.0)
            return
        if self._is_fading:
            self._pending_pixmap = pixmap
            return
        if force:
            self.setPixmap(pixmap)
            self.setWindowOpacity(1.0)
            return
        self._fade_in_pixmap = pixmap
        self.opacity_effect.stop()
        try:
            self.opacity_effect.finished.disconnect()
        except:
            pass
        self.opacity_effect.setStartValue(1.0)
        self.opacity_effect.setEndValue(0.0)
        self._is_fading = True
        self.opacity_effect.finished.connect(self._on_fade_out_complete)
        self.opacity_effect.start()

    def _on_fade_out_complete(self):
        self._is_fading = False
        try:
            self.opacity_effect.finished.disconnect()
        except:
            pass
        if self._pending_pixmap is not None:
            self._fade_in_pixmap = self._pending_pixmap
            self._pending_pixmap = None
        if self._fade_in_pixmap is not None:
            self.setPixmap(self._fade_in_pixmap)
            self._fade_in_pixmap = None
            self.opacity_effect.setStartValue(0.0)
            self.opacity_effect.setEndValue(1.0)
            try:
                self.opacity_effect.finished.disconnect()
            except:
                pass
            self.opacity_effect.start()


# ============================================================
# 主窗口 DesktopPet
# ============================================================
class DesktopPet(QWidget):
    def __init__(self):
        super().__init__()
        set_windows_autostart(True)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        screen_w, screen_h = get_screen_size()
        self.setFixedSize(screen_w, screen_h)
        self.move(0, 0)

        self.scale = min(screen_w / 1920, screen_h / 1080)
        self.lang = 'zh'

        # 系统托盘：必须在 DesktopPet 初始化时真正创建并显示。
        # 图标优先使用 SPT 的 message.ico，缺失时回退到 pet1.png。
        self.create_tray_icon()

        # ---------- Spamton 逐字语音 ----------
        self.spam_voice_sounds = []
        self.spam_voice_index = 0
        self.spam_laugh_sound = QSoundEffect(self)
        self.spam_laugh_long_sound = QSoundEffect(self)
        self.spam_volume = load_spam_volume()
        spam_dir = audio_resource_path("spt_sfx")
        for i in range(1, 11):
            path = os.path.join(spam_dir, f"spam_{i:02d}.wav")
            sound = QSoundEffect(self)
            sound.setVolume(self.spam_volume / 100.0)
            if os.path.isfile(path):
                sound.setSource(QUrl.fromLocalFile(path))
            self.spam_voice_sounds.append(sound)
        laugh_path = os.path.join(spam_dir, "voice_spamlaugh.wav")
        laugh_long_path = os.path.join(spam_dir, "voice_spamlaugh_long.wav")
        self.spam_laugh_sound.setVolume(self.spam_volume / 100.0)
        self.spam_laugh_long_sound.setVolume(self.spam_volume / 100.0)
        if os.path.isfile(laugh_path):
            self.spam_laugh_sound.setSource(QUrl.fromLocalFile(laugh_path))
        if os.path.isfile(laugh_long_path):
            self.spam_laugh_long_sound.setSource(QUrl.fromLocalFile(laugh_long_path))

        # ---------- SPT 动画：待机 pet3~pet10；说话/提醒 pet1~pet2 ----------
        self.pet_form = "classic"
        self.legacy_pet_frames = []          # 说话/提醒：pet1~pet2
        self.idle_pet_frames = []            # 待机：pet3~pet10
        self.legacy_frame_index = 0
        self.legacy_bounce_time = 0.0
        self._form_switch_timer = None

        for filename in ("pet1.png", "pet2.png"):
            pm = QPixmap(resource_path(filename))
            if not pm.isNull():
                self.legacy_pet_frames.append(pm.scaled(
                    int(pm.width() * self.scale), int(pm.height() * self.scale),
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                ))
        if len(self.legacy_pet_frames) < 2:
            raise FileNotFoundError("未找到完整的 pet1.png / pet2.png")

        for i in range(3, 11):
            pm = QPixmap(resource_path(f"pet{i}.png"))
            if not pm.isNull():
                self.idle_pet_frames.append(pm.scaled(
                    int(pm.width() * self.scale), int(pm.height() * self.scale),
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                ))
        if not self.idle_pet_frames:
            raise FileNotFoundError("未找到 pet3.png ~ pet10.png")

        # 初始化对话队列
        self.dialog_queue = []
        self.is_displaying = False
        self.dialog_timer = None
        self.current_dialog_requires_confirmation = False
        self.current_reminder_key = None
        self._reminder_retry_timers = {}
        self._pending_reminders = set()

        # 喝水提醒使用完全独立的状态机：
        # IDLE -> DISPLAYING -> WAITING_RETRY -> DISPLAYING -> ...
        # 只有用户 Confirm 才能回到 IDLE。
        self._drink_state = "IDLE"
        self._drink_retry_timer = None

        # 控制面板/提醒状态跨面板重开保持，并保存到本地，
        # 这样SPAMTON重新启动后也不会把上一轮提醒计时清零。
        self._control_settings_path = writable_app_path("spt_control_settings.json")
        self._load_control_settings()

        # 开机时绝对不继承上一轮的“喝水已累计分钟”。
        # 否则如果上次关闭SPAMTON前已经接近提醒时间，启动后第一分钟就会
        # 再次弹出喝水提示，造成开机语音与喝水提示抢占同一个气泡。
        # 正常运行中的喝水计时仍然保留，从本次启动重新累计。
        self._reminder_elapsed["喝水"] = 0
        self._control_settings["reminder_elapsed"] = {"喝水": 0}

        # 首次启动没有配置文件时，也立即写入默认提醒设置。
        # 已有配置时保留用户的喝水/睡觉开关等设置，但不保留上次启动的喝水累计时间。
        self._save_control_settings()

        # 番茄钟相关
        self._tomato_remaining_saved = int(self._control_settings.get('tomato_remaining', 0))
        self._tomato_running_saved = bool(self._control_settings.get('tomato_running', False))
        self.tomato_display_active = False
        self.tomato_update_timer = QTimer(self)

        # 动画相关
        self.animation_paused = False
        self.auto_dialog_enabled = True
        self.animation_timer_started = False

        # 弹跳相关
        self.idle_bounce_active = True
        self.idle_bounce_time = 0.0
        self.idle_x_amp = 0.0
        self.idle_y_amp = 0.0
        self.idle_x_frq = 0.0
        self.idle_y_frq = 0.0
        self.idle_stretch = 0.0

        # 嘴巴动画相关 - 必须在_load_current_outfit之前初始化
        self._mouth_phase = 0  # 0=闭嘴, 1=张嘴
        self._stop_after_play = False
        self._mouth_animation_active = False
        self._mouth_end_animation = False

        # 黑屏相关 - 用于记录黑屏是否正在显示
        self._black_screen_active = False
        # 保存黑屏显示前的帧，用于恢复
        self._black_screen_previous_pixmap = None

        # 新SPAMTON不再读取 spt.save / 套装系统。
        self.available_outfits = [1]
        self.current_outfit = 1
        self.outfit_count = 1
        # 待机始终使用 pet3~pet10；说话/提醒单独使用 pet1~pet2。
        self.pet_closed_frames = list(self.idle_pet_frames)
        self.pet_open_frames = list(self.legacy_pet_frames)
        self.pet_frames = list(self.idle_pet_frames)
        self.pet_static = self.pet_frames[0]
        self.pet_talking = self.legacy_pet_frames[0]
        self.current_frame_index = 0
        self._talking_one_shot = False
        self.current_pixmap = self.pet_static
        self.save_animation_interval = 200
        self._idle_last_tick = time.monotonic()

        self.black_screen_timer = QTimer(self)
        self.black_screen_timer.setSingleShot(True)
        self.black_screen_hide_timer = QTimer(self)
        self.black_screen_hide_timer.setSingleShot(True)
        self.black_screen_timer.timeout.connect(self._show_black_screen)
        self.black_screen_hide_timer.timeout.connect(self._hide_black_screen)
        self._black_screen_active = False
        self._black_screen_previous_pixmap = None
        self._black_screen_idle_total_ms = 900000
        self._black_screen_remaining_ms = self._black_screen_idle_total_ms
        self._black_screen_timer_started_at = None

        # SPAMTON缩放：Ctrl + 鼠标滚轮，仅在鼠标位于SPAMTON上时生效。
        self.pet_zoom = 1.0
        self.pet_zoom_min = 0.5
        self.pet_zoom_max = 2.0
        self.pet_zoom_step = 0.1


        # 闲置动画参数 - 从save中读取
        self.idle_bounce_active = True
        self.idle_bounce_time = 0.0
        self.idle_x_amp = 0.0
        self.idle_y_amp = 0.0
        self.idle_x_frq = 0.0
        self.idle_y_frq = 0.0
        self.idle_stretch = 0.0
        self._idle_last_tick = time.monotonic()
        self._load_idle_bounce_params()

        pet_w = self.pet_frames[0].width() if self.pet_frames else 200
        pet_h = self.pet_frames[0].height() if self.pet_frames else 200

        self.label = FadeLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWindowOpacity(1.0)
        # QLabel 本身会接收鼠标事件；通过 eventFilter 转发给 DesktopPet，
        # 这样点击SPAMTON时既能保留拖动/右键菜单，又不会出现“只有动画、没有对话”的问题。
        self.label.installEventFilter(self)
        self._show_pet_frame_fixed(self.pet_static)

        # 气泡位置模式：follow = 跟随SPAMTON，fixed = 固定右下角
        self.bubble_mode = "follow"

        self.bubble = BubbleWidget(self)

        # 对话张嘴定时器 - 0.1秒切换闭嘴和开口
        self.mouth_timer = QTimer(self)
        self.mouth_timer.setInterval(100)  # 0.1秒
        self.mouth_timer.timeout.connect(self._toggle_talking_mouth)
        self.is_talking_mouth_open = False
        self._talk_open_one_shot = False
        self.current_mouth_frame_index = 0

        # 对话弹跳状态
        self.dialogue_bounce_active = False
        self.dialogue_bounce_elapsed = 0.0
        self.dialogue_session_active = False
        self._talk_open_session_started = False

        # 闲置弹跳定时器
        self.idle_bounce_timer = QTimer(self)
        self.idle_bounce_timer.timeout.connect(self._update_idle_bounce)
        self.idle_bounce_timer.start(50)

        self.control_panel = None
        self.product_window = None
        self.note_window = None
        self.games_window = None

        self.animation_paused = False
        self.auto_dialog_enabled = True

        self.startup_index = 0
        self.startup_timer = QTimer(self)
        self.startup_timer.timeout.connect(self._startup_animation)
        self.startup_timer.start(1000)

        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._next_frame)
        self.animation_timer_started = False

        # 对话弹跳定时器 - 独立驱动
        self.dialogue_bounce_timer = QTimer(self)
        self.dialogue_bounce_timer.timeout.connect(self._update_dialogue_bounce)
        self.dialogue_bounce_timer.setInterval(50)

        self.drag_pos = None
        self.is_dragging = False

        self.random_timer = QTimer(self)
        self.random_timer.timeout.connect(self._random_dialog)
        self.random_timer.start(30 * 60 * 1000)

        self.note_repeat_timer = QTimer(self)
        self.note_repeat_timer.timeout.connect(self._repeat_random_note)
        self.note_repeat_timer.start(60 * 1000)
        self.note_repeat_elapsed = 0

        # ==================== 主提醒系统 ====================
        # 提醒从SPAMTON启动时就开始运行，不依赖控制面板是否打开。
        self._lunch_triggered = False
        self._dinner_triggered = False
        self._sleep_triggered = False

        self.reminder_timer = QTimer(self)
        self.reminder_timer.setInterval(60 * 1000)
        self.reminder_timer.timeout.connect(self.check_reminders)
        self.reminder_timer.start()

        # 启动时不立即触发喝水/午饭/晚饭/睡觉提醒。
        # 提醒仍由每分钟定时器正常运行，避免开机语音与提醒同时抢占气泡。

        # 创建菜单
        self.create_menu()

        self.add_dialog(random.choice(get_dialogues(self.lang, 'start')))

        # 开机对话由公共对话队列处理，并统一播放 pet1~pet2。

    def _load_control_settings(self):
        """Load persistent control/reminder settings."""
        default_settings = {
            'tomato_minutes': 5,
            'drink_enabled': True,
            'drink_minutes': 45,
            'sleep_enabled': True,
            'sleep_hour': 22,
            'sleep_min': 0,
            'tomato_remaining': 0,
            'tomato_running': False,
            'reminder_last_timestamp': time.time(),
        }
        self._control_settings = dict(default_settings)
        self._reminder_elapsed = {'喝水': 0}
        now_ts = time.time()
        try:
            if os.path.exists(self._control_settings_path):
                with open(self._control_settings_path, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                if isinstance(saved, dict):
                    for key in default_settings:
                        if key in saved:
                            self._control_settings[key] = saved[key]
                    elapsed = saved.get('reminder_elapsed', {})
                    if isinstance(elapsed, dict):
                        self._reminder_elapsed['喝水'] = max(0, int(elapsed.get('喝水', 0)))
                    last_ts = float(saved.get('reminder_last_timestamp', now_ts))
                    if last_ts > 0:
                        offline_minutes = max(0, int((now_ts - last_ts) // 60))
                        self._reminder_elapsed['喝水'] += offline_minutes
        except Exception as e:
            print(f"读取控制设置失败: {e}")

    def _save_control_settings(self):
        """Persist control/reminder settings."""
        try:
            data = dict(self._control_settings)
            data['reminder_elapsed'] = dict(self._reminder_elapsed)
            data['reminder_last_timestamp'] = time.time()
            with open(self._control_settings_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存控制设置失败: {e}")

    def _load_idle_bounce_params(self):
        """SPT 图片版使用固定的轻微待机弹跳参数。"""
        self.idle_x_amp = 0.0
        self.idle_y_amp = 0.0
        self.idle_x_frq = 0.0
        self.idle_y_frq = 0.0
        self.idle_stretch = 0.0

    def update_bubble_position(self):
        """Position the dialogue bubble relative to the pet."""
        if getattr(self, 'bubble_mode', 'follow') != 'follow':
            return
        if not hasattr(self, 'bubble') or not hasattr(self, 'label'):
            return
        pet_x = self.label.x()
        pet_y = self.label.y()
        pet_w = self.label.width()
        scale = float(getattr(self, 'scale', 1.0))
        offset_x = int(round(300 * scale))
        offset_y = int(round(400 * scale))
        bx = pet_x + (pet_w - self.bubble.width()) // 2 - offset_x
        by = pet_y - self.bubble.height() - int(20 * scale) + offset_y
        self.bubble.move(self.mapToGlobal(QPoint(bx, by)))

    def _update_following_panels(self):
        for attr_name in ('control_panel', 'note_window', 'product_window', 'games_window'):
            panel = getattr(self, attr_name, None)
            if panel is not None and panel.isVisible():
                panel.update_position()

    def moveEvent(self, event):
        super().moveEvent(event)
        if hasattr(self, 'bubble'):
            self.update_bubble_position()
        self._update_following_panels()

    def _show_pet_frame_fixed(self, pixmap, x_offset=0.0, y_offset=0.0,
                              scale_x=1.0, scale_y=1.0):
        """Render a pet frame on a stable transparent canvas."""
        if pixmap is None or pixmap.isNull() or not hasattr(self, 'label'):
            return
        canvas_w = max(1, int(round(pixmap.width() * float(scale_x))))
        canvas_h = max(1, int(round(pixmap.height() * float(scale_y))))
        canvas = QPixmap(canvas_w, canvas_h)
        canvas.fill(Qt.transparent)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        target_w = max(1, int(round(pixmap.width() * float(scale_x))))
        target_h = max(1, int(round(pixmap.height() * float(scale_y))))
        painter.drawPixmap(0, 0, pixmap.scaled(target_w, target_h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
        painter.end()
        self.label.setGeometry(
            int(round(self.width() / 2 - canvas_w / 2 + x_offset)),
            int(round(self.height() / 2 - canvas_h / 2 + y_offset)),
            canvas_w,
            canvas_h,
        )
        self.label.setPixmap(canvas)
        self.label.setWindowOpacity(1.0)
        if hasattr(self, 'bubble') and self.bubble.isVisible() and getattr(self, 'bubble_mode', 'follow') == 'follow':
            self.update_bubble_position()
        self._update_following_panels()

    def _load_current_outfit(self, outfit_no):
        """Compatibility shim: SPT v1 has no outfit/save system."""
        return False

    def _start_black_screen_timer(self):
        """Keep the legacy idle timer. If spt_idle.png exists, it is shown after 15 minutes."""
        if not hasattr(self, 'black_screen_timer'):
            return
        if (self.is_displaying or self.tomato_display_active or
                self._mouth_animation_active or self._black_screen_active or self.is_dragging):
            return
        self.black_screen_timer.stop()
        if self._black_screen_remaining_ms <= 0:
            self._black_screen_remaining_ms = self._black_screen_idle_total_ms
        self._black_screen_timer_started_at = time.monotonic()
        self.black_screen_timer.start(max(1, int(self._black_screen_remaining_ms)))

    def _show_black_screen(self):
        """Show optional external idle image instead of the old black-screen layer."""
        idle_path = resource_path('spt_idle.png')
        if not os.path.isfile(idle_path):
            self._black_screen_remaining_ms = self._black_screen_idle_total_ms
            self._black_screen_timer_started_at = None
            return
        idle = QPixmap(idle_path)
        if idle.isNull():
            return
        self._black_screen_previous_pixmap = self.current_pixmap
        self._black_screen_active = True
        self._black_screen_remaining_ms = 0
        self._black_screen_timer_started_at = None
        self._show_pet_frame_fixed(idle.scaled(
            max(1, int(idle.width() * self.scale)),
            max(1, int(idle.height() * self.scale)),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        ))
        self.black_screen_hide_timer.stop()
        self.black_screen_hide_timer.start(3000)

    def _hide_black_screen(self):
        self._black_screen_active = False
        if hasattr(self, 'black_screen_hide_timer'):
            self.black_screen_hide_timer.stop()
        pixmap = self._black_screen_previous_pixmap
        self._black_screen_previous_pixmap = None
        if pixmap is None or pixmap.isNull():
            if self.pet_frames:
                pixmap = self.pet_frames[self.current_frame_index % len(self.pet_frames)]
            else:
                pixmap = self.pet_static
        self.current_pixmap = pixmap
        self._show_pet_frame_fixed(pixmap)
        self._black_screen_remaining_ms = self._black_screen_idle_total_ms
        self._black_screen_timer_started_at = None
        self._start_black_screen_timer()

    def _pause_black_screen_timer(self):
        if not hasattr(self, 'black_screen_timer') or not self.black_screen_timer.isActive():
            return
        if self._black_screen_timer_started_at is not None:
            elapsed = max(0, int((time.monotonic() - self._black_screen_timer_started_at) * 1000))
            self._black_screen_remaining_ms = max(0, self._black_screen_remaining_ms - elapsed)
        self.black_screen_timer.stop()
        self._black_screen_timer_started_at = None

    def _resume_black_screen_timer(self):
        if not hasattr(self, 'black_screen_timer'):
            return
        self.black_screen_timer.stop()
        self._black_screen_timer_started_at = None
        if (self.is_displaying or
                self.tomato_display_active or self._mouth_animation_active or
                self._black_screen_active or self.is_dragging):
            return
        if self._black_screen_remaining_ms <= 0:
            self._black_screen_remaining_ms = self._black_screen_idle_total_ms
        self._black_screen_timer_started_at = time.monotonic()
        self.black_screen_timer.start(max(1, int(self._black_screen_remaining_ms)))

    def _update_idle_bounce(self):
        """闲置弹跳 + Squash/Stretch。

        关键修复：角色永远绘制到同一个固定画布，动画只改变画布内部
        的缩放和整个画布的位置，不再改变 QLabel 的宽高。
        """
        if getattr(self, "_mouth_end_animation", False):
            return
        if self.pet_form == 'classic':
            self._update_classic_bounce()
            return
        if self.dialogue_bounce_active:
            return
        if self.is_dragging:
            return
        if not self.pet_frames:
            return

        now = time.monotonic()
        last = getattr(self, "_idle_last_tick", None)
        if last is None:
            dt = 0.05
        else:
            dt = max(0.001, min(0.10, now - last))
        self._idle_last_tick = now
        self.idle_bounce_time += dt
        t = self.idle_bounce_time

        x_amp = float(getattr(self, "idle_x_amp", 3.0))
        y_amp = float(getattr(self, "idle_y_amp", 6.0))
        x_frq = float(getattr(self, "idle_x_frq", 0.02))
        y_frq = float(getattr(self, "idle_y_frq", 0.025))

        phase_x = t * x_frq * 2.0 * math.pi
        phase_y = t * y_frq * 2.0 * math.pi
        bounce_x = math.sin(phase_x) * x_amp
        bounce_y = math.sin(phase_y) * y_amp

        squash_amount = float(getattr(self, "idle_stretch", 4.25))
        squash_speed = 5.0
        squash = math.cos(phase_y * squash_speed) * squash_amount / 100.0

        # Squash/Stretch 只改变上下高度。
        # X 方向始终保持 100%，绝不左右拉伸或压缩。
        scale_x = 1.0
        scale_y = max(0.90, min(1.10, 1.0 + squash))

        if self.is_talking_mouth_open and self.pet_open_frames:
            source_pixmap = self.pet_open_frames[
                self.current_mouth_frame_index % len(self.pet_open_frames)
            ]
        else:
            source_pixmap = self.current_pixmap

        if source_pixmap is None or source_pixmap.isNull():
            return

        # 固定画布 + 浮点缩放。QLabel 尺寸和角色中心始终不变。
        self._show_pet_frame_fixed(
            source_pixmap,
            x_offset=bounce_x,
            y_offset=bounce_y,
            scale_x=scale_x,
            scale_y=scale_y
        )

    # ==================== 对话弹跳动画 ====================
    def _start_dialogue_bounce(self):
        """对话开始时播放一次弹跳动画"""
        if self.tomato_display_active:
            return

        # SPT 图片版不再读取旧角色资源；对话弹跳使用固定参数。
        self._dialogue_bounce_cfg = {}
        
        self.dialogue_bounce_active = True
        self.dialogue_bounce_elapsed = 0.0
        self.dialogue_bounce_timer.start(50)

    def _update_dialogue_bounce(self):
        """对话弹跳动画：只移动固定渲染画布，不改变其尺寸。"""
        if self.tomato_display_active or not self.dialogue_bounce_active:
            return

        cfg = self._dialogue_bounce_cfg if hasattr(self, '_dialogue_bounce_cfg') else {}
        duration = 0.55
        self.dialogue_bounce_elapsed += 0.05
        progress = self.dialogue_bounce_elapsed / duration

        if progress >= 1.0:
            self.dialogue_bounce_active = False
            self.dialogue_bounce_elapsed = 0.0
            self.dialogue_bounce_timer.stop()
            # 结束时回到固定画布中心；不要恢复成 400x400 QLabel。
            if not self._black_screen_active:
                if self.pet_closed_frames:
                    pixmap = self.pet_closed_frames[self.current_frame_index % len(self.pet_closed_frames)]
                else:
                    pixmap = self.pet_static
                self._show_pet_frame_fixed(pixmap)
            return

        x_amp = float(cfg.get('xAmp', 0) or 0)
        y_amp = float(cfg.get('yAmp', 0) or 0)
        x_frq = float(cfg.get('xFrq', 0) or 0)
        y_frq = float(cfg.get('yFrq', 0) or 0)
        if x_amp == 0:
            x_amp = 4.0
        if y_amp == 0:
            y_amp = 8.0
        if x_frq == 0:
            x_frq = 0.06
        if y_frq == 0:
            y_frq = 0.06

        decay = 1.0 - progress * progress
        t = self.dialogue_bounce_elapsed
        bounce_x = math.sin(t * x_frq * 2 * math.pi) * x_amp * decay
        bounce_y = math.sin(t * y_frq * 2 * math.pi) * y_amp * decay

        # 对话期间保留当前嘴部帧，只移动固定画布。
        if self.is_talking_mouth_open and self.pet_open_frames:
            pixmap = self.pet_open_frames[self.current_mouth_frame_index % len(self.pet_open_frames)]
        else:
            pixmap = self.current_pixmap
        self._show_pet_frame_fixed(pixmap, x_offset=bounce_x, y_offset=bounce_y)

    # ==================== 对话张嘴动画 ====================
    def _set_mouth_frame_centered(self, pixmap):
        """显示嘴部帧，但始终保持固定 QLabel 画布尺寸。"""
        if pixmap is None or pixmap.isNull() or not hasattr(self, 'label'):
            return

        try:
            self.label.opacity_effect.stop()
            self.label._is_fading = False
            self.label._pending_pixmap = None
            self.label._fade_in_pixmap = None
        except Exception:
            pass

        self._show_pet_frame_fixed(pixmap)
        self.label.update()
        self.label.repaint()

    def _start_talking_mouth(self):
        """所有说话、提醒、点击、调情及小游戏结果统一播放 pet1~pet2。"""
        if not self.legacy_pet_frames:
            return
        self.animation_timer.stop()
        self._mouth_end_animation = False
        self._mouth_animation_active = True
        self._talk_open_one_shot = True
        self._mouth_phase = 0
        self.current_mouth_frame_index = 0
        self.legacy_frame_index = 0
        self.current_pixmap = self.legacy_pet_frames[0]
        self._show_pet_frame_fixed(self.current_pixmap)
        if hasattr(self, "mouth_timer"):
            self.mouth_timer.stop()
            self.mouth_timer.start(300)
        self._start_dialogue_bounce()

    def _toggle_talking_mouth(self):
        """说话期间 pet1 与 pet2 以 0.3 秒切换。"""
        if not getattr(self, "_mouth_animation_active", False):
            return
        if getattr(self, "_mouth_end_animation", False):
            return
        if len(self.legacy_pet_frames) < 2:
            return
        self.legacy_frame_index = (self.legacy_frame_index + 1) % 2
        self.current_pixmap = self.legacy_pet_frames[self.legacy_frame_index]
        self._show_pet_frame_fixed(self.current_pixmap)
        if hasattr(self, "mouth_timer"):
            self.mouth_timer.start(300)

    def _stop_talking_mouth(self):
        """对话结束，进入结束嘴部动画。说话结束后恢复 pet3~pet10 待机动画。"""

        if self.pet_form == 'classic':
            if hasattr(self, "mouth_timer"):
                self.mouth_timer.stop()
            self._mouth_animation_active = False
            self._mouth_end_animation = False
            self._talk_open_one_shot = False
            self._mouth_phase = 0
            self.current_frame_index = 0
            if self.pet_frames:
                self.current_pixmap = self.pet_frames[0]
                self._show_pet_frame_fixed(self.current_pixmap)
            if getattr(self, "animation_timer_started", False) and not getattr(self, "animation_paused", False):
                self.animation_timer.start(200)
            return

    # ==================== 原有方法 ====================
    def switch_language(self):
        if self.lang == 'zh':
            self.lang = 'en'
        else:
            self.lang = 'zh'
        self._update_menu_language()
        if self.bubble.isVisible() and self.current_dialog_requires_confirmation:
            self.bubble._update_confirm_button_style()
        if self.control_panel:
            self.control_panel.update_language(self.lang)
        if self.product_window:
            self.product_window.update_language(self.lang)
        if self.note_window:
            self.note_window.update_language(self.lang)
        if self.games_window:
            self.games_window.update_language(self.lang)

    def _update_menu_language(self):
        if self.lang == 'en':
            self.control_action.setText("Control Panel")
            self.note_action.setText("Notes")
            self.flirt_action.setText("Flirt")
            self.product_action.setText("Products")
            self.games_action.setText("Games")
            self.bubble_mode_action.setText(
                "Bubble: Fixed Bottom-Right" if self.bubble_mode == "follow"
                else "Bubble: Follow Pet"
            )
            if hasattr(self, "volume_menu"):
                self.volume_menu.setTitle("Volume")
            self.toggle_animation_action.setText("Pause Animation" if not self.animation_paused else "Start Animation")
            self.toggle_visibility_action.setText("Hide Pet" if self.isVisible() else "Show Pet")
            self.toggle_auto_dialog_action.setText("Pause Auto Dialog" if self.auto_dialog_enabled else "Start Auto Dialog")
            self.lang_action.setText("中文")
            self.quit_action.setText("Exit")
            if hasattr(self, 'tray_icon'):
                tray_menu = self.tray_icon.contextMenu()
                if tray_menu:
                    for action in tray_menu.actions():
                        if action.text() in ("显示/隐藏", "Show/Hide"):
                            action.setText("Show/Hide")
                        elif action.text() in ("控制面板", "Control Panel"):
                            action.setText("Control Panel")
                        elif action.text() in ("商品", "Products"):
                            action.setText("Products")
                        elif action.text() in ("小游戏", "Games"):
                            action.setText("Games")
                        elif action.text() in ("退出", "Exit"):
                            action.setText("Exit")
        else:
            self.control_action.setText("控制面板")
            self.note_action.setText("便签")
            self.flirt_action.setText("调情")
            self.product_action.setText("商品")
            self.games_action.setText("小游戏")
            self.bubble_mode_action.setText(
                "气泡固定右下角" if self.bubble_mode == "follow"
                else "气泡跟随SPAMTON"
            )
            if hasattr(self, "volume_menu"):
                self.volume_menu.setTitle("音量")
            self.toggle_animation_action.setText("暂停动画" if not self.animation_paused else "开始动画")
            self.toggle_visibility_action.setText("显示/隐藏")
            self.toggle_auto_dialog_action.setText("暂停自动对话" if self.auto_dialog_enabled else "开始自动对话")
            self.lang_action.setText("English")
            self.quit_action.setText("退出")
            if hasattr(self, 'tray_icon'):
                tray_menu = self.tray_icon.contextMenu()
                if tray_menu:
                    for action in tray_menu.actions():
                        if action.text() in ("Show/Hide", "显示/隐藏"):
                            action.setText("显示/隐藏")
                        elif action.text() in ("Control Panel", "控制面板"):
                            action.setText("控制面板")
                        elif action.text() in ("Products", "商品"):
                            action.setText("商品")
                        elif action.text() in ("Games", "小游戏"):
                            action.setText("小游戏")
                        elif action.text() in ("Exit", "退出"):
                            action.setText("退出")

    def create_tray_icon(self):
        icon_path = resource_path("message.ico")
        if not os.path.exists(icon_path):
            icon_path = resource_path("pet1.png")
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(icon_path))
        self.tray_icon.setToolTip("Desk Pet - Click to show/hide")
        tray_menu = QMenu()
        show_action = QAction("显示/隐藏" if self.lang == 'zh' else "Show/Hide", self)
        show_action.triggered.connect(self._toggle_visibility)
        tray_menu.addAction(show_action)
        control_action = QAction("控制面板" if self.lang == 'zh' else "Control Panel", self)
        control_action.triggered.connect(self.show_control_panel)
        tray_menu.addAction(control_action)
        product_action = QAction("商品" if self.lang == 'zh' else "Products", self)
        product_action.triggered.connect(self.show_products)
        tray_menu.addAction(product_action)
        games_action = QAction("小游戏" if self.lang == 'zh' else "Games", self)
        games_action.triggered.connect(self.show_games)
        tray_menu.addAction(games_action)
        tray_menu.addSeparator()
        quit_action = QAction("退出" if self.lang == 'zh' else "Exit", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()
        if hasattr(self, "toggle_visibility_action"):
            self.toggle_visibility_action.setText("隐藏SPAMTON" if self.isVisible() and self.lang == "zh" else "Hide Pet" if self.isVisible() else "显示SPAMTON" if self.lang == "zh" else "Show Pet")

    def _toggle_visibility_from_menu(self):
        self._toggle_visibility()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._toggle_visibility()

    def _toggle_auto_dialog(self):
        self.auto_dialog_enabled = not self.auto_dialog_enabled
        if self.auto_dialog_enabled:
            self.random_timer.start(30 * 60 * 1000)
        else:
            self.random_timer.stop()
        self._update_menu_language()

    def _startup_animation(self):
        """开机进入正常待机动画；开机对话由对话系统统一触发 pet1~pet2。"""
        self.startup_timer.stop()
        self.current_frame_index = 0
        if self.pet_frames:
            self.current_pixmap = self.pet_frames[0]
            self._show_pet_frame_fixed(self.current_pixmap)
        self.animation_timer.start(200)
        self.animation_timer_started = True

    def _toggle_animation(self):
        # 待机动画可暂停；暂停时保持当前待机帧。
        if getattr(self, 'pet_form', 'spt') != 'classic':
            return
        self.animation_paused = not self.animation_paused
        if self.animation_paused:
            self.animation_timer.stop()
            self._show_pet_frame_fixed(self.pet_static)
            self.toggle_animation_action.setText("开始动画" if self.lang == 'zh' else "Start Animation")
        else:
            self.animation_timer.start(200)
            self.current_frame_index = 0
            self.current_pixmap = self.pet_frames[0] if self.pet_frames else QPixmap()
            self._show_pet_frame_fixed(self.current_pixmap)
            self.toggle_animation_action.setText("暂停动画" if self.lang == 'zh' else "Pause Animation")

    def _next_frame(self):
        if self.animation_paused or not self.animation_timer_started:
            return
        if self.is_dragging:
            return
        if getattr(self, "_mouth_animation_active", False) or self._black_screen_active:
            return

        if self.pet_form == 'classic':
            if not self.pet_frames:
                return
            self.current_frame_index = (self.current_frame_index + 1) % len(self.pet_frames)
            self.current_pixmap = self.pet_frames[self.current_frame_index]
            self._show_pet_frame_fixed(self.current_pixmap)
            return

        if not self.pet_frames:
            return
        self.current_frame_index = (self.current_frame_index + 1) % len(self.pet_frames)
        self.current_pixmap = self.pet_frames[self.current_frame_index]

    def _update_classic_bounce(self):
        if not self.legacy_pet_frames or self.is_dragging:
            return
        self.legacy_bounce_time += 0.15
        bounce_y = math.sin(self.legacy_bounce_time * 2.5) * 3 * self.scale
        bounce_x = math.sin(self.legacy_bounce_time * 1.8) * 2 * self.scale
        self._show_pet_frame_fixed(
            self.current_pixmap if self.current_pixmap and not self.current_pixmap.isNull() else self.legacy_pet_frames[0],
            x_offset=bounce_x, y_offset=bounce_y
        )

    def start_tomato_display(self, seconds):
        self.tomato_display_active = True
        # 番茄钟只接管倒计时显示，不抢占当前对话/提醒。
        # 当前提示结束后，队列中的内容继续正常显示。
        if hasattr(self, 'black_screen_timer'):
            self.black_screen_timer.stop()
        if self._black_screen_active:
            self._hide_black_screen()
        if not self.is_displaying:
            self.bubble.show_big_text(self._format_time(seconds))
        self.tomato_update_timer.start(1000)

    def update_tomato_display(self, seconds):
        if not self.tomato_display_active:
            return
        # 对话期间不要每秒覆盖气泡；倒计时仍在后台继续。
        # 对话结束后再恢复当前剩余时间。
        if self.is_displaying:
            return
        self.bubble.show_big_text(self._format_time(seconds))

    def stop_tomato_display(self):
        self.tomato_display_active = False
        self.tomato_update_timer.stop()
        # 重新启动黑屏计时器
        self._start_black_screen_timer()
        if self.dialog_queue:
            self.bubble.hide()
            self.show_next_dialog()
        else:
            self.bubble.fade_out()

    def _format_time(self, seconds):
        m, s = divmod(seconds, 60)
        return f"{m:02d}:{s:02d}"

    def _rescale_classic_pet(self):
        zoom = float(getattr(self, "pet_zoom", 1.0))

        def scale_frames(filenames):
            result = []
            for filename in filenames:
                pm = QPixmap(resource_path(filename))
                if not pm.isNull():
                    result.append(pm.scaled(
                        max(1, int(round(pm.width() * self.scale * zoom))),
                        max(1, int(round(pm.height() * self.scale * zoom))),
                        Qt.KeepAspectRatio, Qt.SmoothTransformation
                    ))
            return result

        idle_index = getattr(self, "current_frame_index", 0)
        mouth_index = getattr(self, "current_mouth_frame_index", 0)
        legacy_index = getattr(self, "legacy_frame_index", 0)

        idle_frames = scale_frames([f"pet{i}.png" for i in range(3, 11)])
        talk_frames = scale_frames(["pet1.png", "pet2.png"])

        if idle_frames:
            self.idle_pet_frames = idle_frames
            self.pet_closed_frames = list(idle_frames)
            self.pet_frames = list(idle_frames)
            self.current_frame_index = idle_index % len(idle_frames)
        if talk_frames:
            self.legacy_pet_frames = talk_frames
            self.pet_open_frames = list(talk_frames)
            self.current_mouth_frame_index = mouth_index % len(talk_frames)
            self.legacy_frame_index = legacy_index % len(talk_frames)

        if self.is_talking_mouth_open and self.pet_open_frames:
            self.current_pixmap = self.pet_open_frames[self.current_mouth_frame_index]
        elif self.pet_closed_frames:
            self.current_pixmap = self.pet_closed_frames[self.current_frame_index]
        elif self.legacy_pet_frames:
            self.current_pixmap = self.legacy_pet_frames[self.legacy_frame_index]
        self.pet_static = self.current_pixmap
        self.pet_talking = self.legacy_pet_frames[0] if self.legacy_pet_frames else self.pet_static


    def _set_pet_zoom(self, zoom):
        zoom = max(
            float(getattr(self, "pet_zoom_min", 0.5)),
            min(float(getattr(self, "pet_zoom_max", 2.0)), float(zoom))
        )
        old_zoom = float(getattr(self, "pet_zoom", 1.0))
        if abs(zoom - old_zoom) < 0.0001:
            return

        self.pet_zoom = zoom
        self._rescale_classic_pet()

        if self.is_talking_mouth_open and self.pet_open_frames:
            self._show_pet_frame_fixed(
                self.pet_open_frames[self.current_mouth_frame_index % len(self.pet_open_frames)]
            )
        elif self.pet_closed_frames:
            self._show_pet_frame_fixed(
                self.pet_closed_frames[self.current_frame_index % len(self.pet_closed_frames)]
            )
        else:
            self._show_pet_frame_fixed(self.pet_static)


    def eventFilter(self, obj, event):
        # SPAMTON图片 QLabel 会吃掉鼠标事件，所以统一转发到主窗口。
        # 这样点击、拖动、右键菜单和 Ctrl+滚轮缩放都保持原有行为。
        if obj is getattr(self, "label", None):
            if event.type() == QEvent.Wheel:
                if event.modifiers() & Qt.ControlModifier:
                    delta = event.angleDelta().y()
                    if delta:
                        steps = 1 if delta > 0 else -1
                        self._set_pet_zoom(
                            getattr(self, "pet_zoom", 1.0)
                            + steps * getattr(self, "pet_zoom_step", 0.1)
                        )
                    return True
            elif event.type() == QEvent.MouseButtonPress:
                self.mousePressEvent(event)
                return True
            elif event.type() == QEvent.MouseMove:
                self.mouseMoveEvent(event)
                return True
            elif event.type() == QEvent.MouseButtonRelease:
                self.mouseReleaseEvent(event)
                return True
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            self.is_dragging = False
            self._show_pet_frame_fixed(self.pet_static)
            if self.animation_timer_started:
                self.animation_timer.stop()
        elif event.button() == Qt.RightButton:
            if self.control_panel is not None and self.control_panel.isVisible():
                self.control_panel.close()
            elif self.product_window is not None and self.product_window.isVisible():
                self.product_window.hide()
            elif self.product_window is not None and self.product_window.isVisible():
                self.product_window.hide()
            elif self.note_window is not None and self.note_window.isVisible():
                self.note_window.hide()
            else:
                self.menu.exec_(event.globalPos())

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta:
                steps = 1 if delta > 0 else -1
                self._set_pet_zoom(
                    getattr(self, "pet_zoom", 1.0)
                    + steps * getattr(self, "pet_zoom_step", 0.1)
                )
                event.accept()
                return
        event.ignore()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos is not None:
            distance = (event.globalPos() - self.frameGeometry().topLeft() - self.drag_pos).manhattanLength()
            if distance > 5:
                self.is_dragging = True
                self.move(event.globalPos() - self.drag_pos)
                self.update_bubble_position()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.animation_paused:
                self._show_pet_frame_fixed(self.pet_static)
            elif self.animation_timer_started:
                self._show_pet_frame_fixed(self.current_pixmap)
            else:
                self._show_pet_frame_fixed(self.pet_frames[0] if self.pet_frames else QPixmap())
            if not self.animation_paused and self.animation_timer_started:
                self.animation_timer.start(200)
            if not self.is_dragging:
                # event 可能来自SPAMTON QLabel 的 eventFilter，此时 event.pos() 是
                # QLabel 坐标；统一转换成 DesktopPet 主窗口坐标再判断点击区域。
                pos = self.mapFromGlobal(event.globalPos())
                pet_rect = self.label.geometry()
                if pet_rect.contains(pos):
                    self._on_pet_click()
            self.drag_pos = None
            self.is_dragging = False

    def clear_dialog_timer(self):
        if self.dialog_timer is not None:
            self.dialog_timer.stop()
            self.dialog_timer = None

    def _play_spam_char_sound(self, reminder_key=None):
        """普通/便签对话逐字播放 Spamton 短语音；提醒不逐字播放，提醒结束时使用 laugh long。"""
        if reminder_key in {"drink", "lunch", "dinner", "sleep"}:
            return
        try:
            sound = self.spam_voice_sounds[self.spam_voice_index % len(self.spam_voice_sounds)]
            self.spam_voice_index += 1
            sound.stop()
            sound.play()
        except Exception as e:
            print(f"Spamton 语音播放失败: {e}")

    def _play_laugh(self):
        try:
            self.spam_laugh_sound.stop()
            self.spam_laugh_sound.play()
        except Exception as e:
            print(f"laugh 播放失败: {e}")

    def _play_laugh_long(self):
        try:
            self.spam_laugh_long_sound.stop()
            self.spam_laugh_long_sound.play()
        except Exception as e:
            print(f"laugh long 播放失败: {e}")

    def add_dialog(self, text, requires_confirmation=False, priority=False, reminder_key=None, interrupt_tomato=False):
        if reminder_key is not None:
            self._laugh_after_dialog = False
        dialog_item = (text, requires_confirmation, reminder_key)
        if priority:
            self.dialog_queue.insert(0, dialog_item)
        else:
            self.dialog_queue.append(dialog_item)

        # 重要：加入对话队列不能重置黑屏计时器。
        # 黑屏是独立的“闲置时间”系统；提醒、便签、随机对话只是进入
        # 显示队列，不会重置正常的15分钟黑屏计时。

        if not self.is_displaying:
            # 番茄钟运行期间也正常显示队列内容；番茄钟本身继续计时。
            self.show_next_dialog(allow_during_tomato=interrupt_tomato)

    def show_next_dialog(self, allow_during_tomato=False):
        # 整组对话第一次开始时播放张嘴和弹跳
        if not self.dialogue_session_active:
            self.dialogue_session_active = True
            self._start_talking_mouth()

        # 番茄钟期间允许所有排队对话显示；allow_during_tomato 参数保留以兼容现有调用。
        # 番茄钟倒计时不会因此暂停，只在气泡显示期间暂时隐藏倒计时数字。
        self.clear_dialog_timer()
        if self.dialog_queue:
            self._pause_black_screen_timer()
            self.is_displaying = True
            text, requires_confirmation, reminder_key = self.dialog_queue.pop(0)
            self.current_dialog_requires_confirmation = requires_confirmation
            self.current_reminder_key = reminder_key
            self.update_bubble_position()
            # 逐字音效在 BubbleWidget.type_char() 中触发，这里只记录当前提醒类型。
            # 这样提醒首次出现和再次提醒都会自动使用 -4 半音。
            self.spam_voice_index = 0
            self.bubble.start_typing(text, requires_confirmation)
        else:
            self.is_displaying = False
            self.current_dialog_requires_confirmation = False
            self.current_reminder_key = None
            self.dialogue_session_active = False
            self._stop_talking_mouth()
            self.dialogue_bounce_active = False

    def start_dialog_continuation(self, remaining, requires_confirmation=False):
        # 番茄钟期间长对话也必须允许继续播放，不能被番茄钟强制截断。
        self.clear_dialog_timer()
        self.is_displaying = True
        self.current_dialog_requires_confirmation = requires_confirmation
        self.bubble.start_typing(remaining, requires_confirmation)

    def on_dialog_complete(self):
        self.clear_dialog_timer()

        # 重要：提醒必须独占当前气泡，直到用户确认或60秒超时。
        # 以前这里如果 dialog_queue 里还有普通对话，会在3秒后直接切走提醒，
        # 同时 Bubble 的60秒确认计时器也会被下一条对话的 start_typing() 停掉，
        # 导致 reminder_dialog_timeout() 永远不再执行。
        # 这就是“提醒几次以后就不再提醒”的主要原因。
        if self.current_dialog_requires_confirmation:
            self._stop_talking_mouth()
            self.dialogue_session_active = False
            self.dialogue_bounce_active = False
            # Bubble.confirm_timer 继续负责60秒超时。
            # 在确认/超时之前，dialog_queue 中的其它对话全部保持等待。
            return

        if self.dialog_queue:
            self.dialog_timer = QTimer(self)
            self.dialog_timer.setSingleShot(True)
            self.dialog_timer.timeout.connect(
                lambda: self.show_next_dialog(
                    allow_during_tomato=False
                )
            )
            self.dialog_timer.start(3000)
        else:
            self._stop_talking_mouth()
            self.dialogue_session_active = False
            self.dialogue_bounce_active = False
            self.dialog_timer = QTimer(self)
            self.dialog_timer.setSingleShot(True)
            self.dialog_timer.timeout.connect(self._finish_dialog_or_resume_tomato)
            self.dialog_timer.start(3000)

    def _finish_dialog_or_resume_tomato(self):
        if self.tomato_display_active:
            self.bubble.hide()
            self.is_displaying = False
            self.current_dialog_requires_confirmation = False
            self._stop_talking_mouth()
            # 继续显示当前剩余时间；番茄钟倒计时从未被暂停。
            # 不重新调用 start_tomato_display，避免再次重置/打断状态。
            if self.control_panel is not None:
                self.bubble.show_big_text(
                    self._format_time(self.control_panel.tomato_remaining)
                )
            elif self._tomato_remaining_saved > 0:
                self.bubble.show_big_text(
                    self._format_time(self._tomato_remaining_saved)
                )
            return
        if getattr(self, "_laugh_after_dialog", False):
            self._laugh_after_dialog = False
            self._play_laugh()
        self._fade_and_reset()

    def confirm_dialog(self):
        # 喝水提醒由独立状态机处理，绝不依赖公共 pending/queue 状态。
        if self._drink_state == "DISPLAYING" and self.current_reminder_key == "drink":
            self._drink_state = "IDLE"
            self._reminder_elapsed['喝水'] = 0
            if self._drink_retry_timer is not None:
                self._drink_retry_timer.stop()
                self._drink_retry_timer.deleteLater()
                self._drink_retry_timer = None
            self._pending_reminders.discard("drink")
            self.current_reminder_key = None
            self.current_dialog_requires_confirmation = False
            self.clear_dialog_timer()
            self.bubble.dismiss()
            self._resume_dialog_queue_after_reminder()
            # Confirm 后才重新开始下一轮喝水计时。
            return

        # 其它提醒继续使用原有逻辑。
        reminder_key = self.current_reminder_key
        if reminder_key:
            self._pending_reminders.discard(reminder_key)
            if reminder_key == 'drink':
                self._reminder_elapsed['喝水'] = 0
            timer = self._reminder_retry_timers.pop(reminder_key, None)
            if timer is not None:
                timer.stop()
                timer.deleteLater()
        self.clear_dialog_timer()
        self.bubble.dismiss()
        self._resume_dialog_queue_after_reminder()

    def add_reminder_dialog(self, reminder_key, dialogue_key):
        # 喝水提醒完全绕开公共 reminder queue。
        if reminder_key == "drink":
            return self._start_drink_reminder()

        if reminder_key in self._pending_reminders:
            return False

        self._pending_reminders.add(reminder_key)
        lines = get_dialogues(self.lang, dialogue_key)
        if not lines:
            self._pending_reminders.discard(reminder_key)
            return False

        self._play_laugh_long()
        self.add_dialog(
            random.choice(lines),
            requires_confirmation=True,
            priority=True,
            reminder_key=reminder_key
        )
        return True

    def _start_drink_reminder(self):
        """启动一轮喝水提醒。状态机独立于公共 dialog_queue。"""
        # IDLE = 首次到期；WAITING_RETRY = 未确认后的再次提醒。
        # 两种状态都允许进入 DISPLAYING。
        # DISPLAYING 状态本身禁止重复创建，避免同一轮出现多个喝水气泡。
        if self._drink_state not in ("IDLE", "WAITING_RETRY"):
            return False

        lines = get_dialogues(self.lang, "drink")
        if not lines:
            return False

        self._drink_state = "DISPLAYING"
        self._pending_reminders.add("drink")
        self._play_laugh_long()
        if self.tomato_display_active:
            self.bubble.hide()
        self.current_reminder_key = "drink"
        self.current_dialog_requires_confirmation = True
        self.is_displaying = True
        self.dialogue_session_active = True
        self._start_talking_mouth()
        self.update_bubble_position()
        self.spam_voice_index = 0

        # 直接显示，不经过公共 dialog_queue。
        self.bubble.start_typing(random.choice(lines), True)
        return True

    def _drink_wait_for_display(self):
        """其它对话正在占用气泡时，喝水状态机只等待，不丢失提醒。"""
        if self._drink_state != "WAITING_RETRY":
            return

        if self.is_displaying or self.current_dialog_requires_confirmation:
            self._drink_retry_timer = QTimer(self)
            self._drink_retry_timer.setSingleShot(True)
            self._drink_retry_timer.timeout.connect(self._drink_wait_for_display)
            self._drink_retry_timer.start(1000)
            return

        self._drink_retry_timer = None
        self._start_drink_reminder()

    def _resume_dialog_queue_after_reminder(self):
        """提醒结束后统一把显示权交还给普通对话队列。"""
        self.is_displaying = False
        self.current_dialog_requires_confirmation = False
        self.current_reminder_key = None
        self.dialogue_bounce_active = False
        self.dialogue_session_active = False
        self._stop_talking_mouth()
        if self.dialog_queue:
            self.show_next_dialog(allow_during_tomato=False)
            return
        if self.tomato_display_active:
            if self.control_panel is not None:
                self.bubble.show_big_text(self._format_time(self.control_panel.tomato_remaining))
            elif self._tomato_remaining_saved > 0:
                self.bubble.show_big_text(self._format_time(self._tomato_remaining_saved))
        self._resume_black_screen_timer()

    def _drink_reminder_timeout(self):
        """喝水提醒显示60秒未确认：消失，60秒后再次显示。"""
        if self._drink_state != "DISPLAYING":
            return
        self._drink_state = "WAITING_RETRY"
        if self._drink_retry_timer is not None:
            self._drink_retry_timer.stop()
            self._drink_retry_timer.deleteLater()
        self._drink_retry_timer = QTimer(self)
        self._drink_retry_timer.setSingleShot(True)
        self._drink_retry_timer.timeout.connect(self._drink_wait_for_display)
        self.bubble.dismiss()
        self._resume_dialog_queue_after_reminder()
        self._drink_retry_timer.start(60000)

    def is_reminder_pending(self, reminder_key):
        if reminder_key == "drink":
            return self._drink_state != "IDLE"
        return reminder_key in self._pending_reminders


    def reminder_dialog_timeout(self):
        """提醒显示1分钟仍未确认：消失，空1分钟后再次出现。"""
        if self.current_reminder_key == "drink" or self._drink_state == "DISPLAYING":
            self._drink_reminder_timeout()
            return
        reminder_key = self.current_reminder_key
        if not reminder_key or reminder_key not in self._pending_reminders:
            self.bubble.dismiss()
            self._resume_dialog_queue_after_reminder()
            return
        old_timer = self._reminder_retry_timers.pop(reminder_key, None)
        if old_timer is not None:
            old_timer.stop()
            old_timer.deleteLater()
        retry_timer = QTimer(self)
        retry_timer.setSingleShot(True)
        retry_timer.timeout.connect(lambda key=reminder_key: self._retry_reminder(key))
        self._reminder_retry_timers[reminder_key] = retry_timer
        self.bubble.dismiss()
        self._resume_dialog_queue_after_reminder()
        retry_timer.start(60000)

    def _retry_reminder(self, reminder_key):
        # 喝水提醒不再使用公共 retry timer。
        if reminder_key == "drink":
            if self._drink_state == "WAITING_RETRY":
                self._drink_wait_for_display()
            return

        timer = self._reminder_retry_timers.pop(reminder_key, None)
        if timer is not None:
            timer.deleteLater()

        # pending 表示“这项提醒还没有被确认”，而不是“提醒已经在队列里”。
        # 因此重试时必须允许重新创建一条显示用的对话。
        if reminder_key not in self._pending_reminders:
            return

        dialogue_map = {
            'drink': 'drink',
            'lunch': 'lunch',
            'dinner': 'dinner',
            'sleep': 'sleep'
        }
        dialogue_key = dialogue_map.get(reminder_key)
        lines = get_dialogues(self.lang, dialogue_key) if dialogue_key else []
        if not lines:
            return

        # 重试提醒也只负责“把自己放进显示队列”，不修改其它系统状态。
        # 使用 append 而不是 insert(0)，避免反复重试的提醒长期霸占队列，
        # 从而让便签和随机对话永远得不到播放机会。
        # 如果当前正好已经是同一个提醒，则不重复插入。
        if self.current_reminder_key == reminder_key and self.current_dialog_requires_confirmation:
            return

        self.dialog_queue.append(
            (
                random.choice(lines),
                True,
                reminder_key
            )
        )

        # 不在这里重置黑屏计时器：提醒重试属于后台状态机事件，
        # 不是用户交互，也不能让黑屏重新从15分钟开始计时。

        if not self.is_displaying:
            self.show_next_dialog(
                allow_during_tomato=False
            )

    def _fade_and_reset(self):
        self.bubble.fade_out()
        self.is_displaying = False
        self.current_dialog_requires_confirmation = False
        self.dialog_timer = None
        self._resume_black_screen_timer()

    def _on_pet_click(self):
        if self.auto_dialog_enabled:
            self.add_dialog(random.choice(get_dialogues(self.lang, 'click')), priority=True, interrupt_tomato=True)

    def flirt(self):
        self._laugh_after_dialog = True
        self.add_dialog(random.choice(get_dialogues(self.lang, 'flirt')), priority=True, interrupt_tomato=True)

    def _random_dialog(self):
        # 随机对话本身不应该因为当前气泡被提醒/便签占用而“丢失”。
        # 以前这里要求 not self.is_displaying，导致随机对话恰好在提醒显示时
        # 到点就直接 return；提醒结束后也不会补发，因此看起来像随机对话失效。
        # 现在统一交给 dialog_queue：当前内容显示完后，随机对话自然继续播放。
        if not self.auto_dialog_enabled:
            return

        lines = get_dialogues(self.lang, 'random')
        if not lines:
            return

        self.add_dialog(random.choice(lines))

    def show_note(self):
        if self.note_window is None:
            self.note_window = NoteWindow(self)
        self.note_window.update_language(self.lang)
        self.note_window.reload_note()
        self.note_window.update_position()
        self.note_window.show()
        self.note_window.raise_()
        self.note_window.note_edit.setFocus()

    def _repeat_random_note(self):
        self.note_repeat_elapsed += 1
        if self.note_repeat_elapsed < 60:
            return
        self.note_repeat_elapsed = 0

        note_text = load_notes()
        if not note_text.strip():
            return

        notes = [line.strip() for line in note_text.splitlines() if line.strip()]
        if not notes:
            return

        note_sentence = random.choice(notes)
        role_lines = get_dialogues(self.lang, "note_repeat")
        if not role_lines:
            return

        role_line = random.choice(role_lines)
        if self.lang == "en":
            message = f'You wrote: "{note_sentence}"{role_line}'
        else:
            message = f'你写过：" {note_sentence} "{role_line}'
        self.add_dialog(message)

    def check_reminders(self, initial=False):
        """独立提醒计时器：SPAMTON启动即运行，不依赖控制面板是否打开。"""
        now = QTime.currentTime()
        hour, minute = now.hour(), now.minute()
        settings = getattr(self, '_control_settings', {})

        # 喝水：使用持久化的累计分钟。首次运行默认开启。
        drink_enabled = bool(settings.get('drink_enabled', True))
        drink_minutes = max(1, int(settings.get('drink_minutes', 45)))
        if drink_enabled:
            # 正常每分钟 +1；启动时的即时检查不额外增加一分钟。
            if not initial:
                self._reminder_elapsed['喝水'] = int(self._reminder_elapsed.get('喝水', 0)) + 1
            else:
                self._reminder_elapsed['喝水'] = int(self._reminder_elapsed.get('喝水', 0))

            # 喝水提醒只由自己的状态机决定。
            # DISPLAYING / WAITING_RETRY 时绝不重复创建提醒。
            if (self._reminder_elapsed['喝水'] >= drink_minutes
                    and self._drink_state == "IDLE"):
                if self._start_drink_reminder():
                    self._reminder_elapsed['喝水'] = 0

        # 午饭 / 晚饭 / 睡觉提醒不依赖控制面板是否存在。
        if hour == 12 and minute == 0 and not self._lunch_triggered and not self.is_reminder_pending('lunch'):
            self.add_reminder_dialog('lunch', 'lunch')
            self._lunch_triggered = True
        if hour != 12:
            self._lunch_triggered = False

        if hour == 18 and minute == 0 and not self._dinner_triggered and not self.is_reminder_pending('dinner'):
            self.add_reminder_dialog('dinner', 'dinner')
            self._dinner_triggered = True
        if hour != 18:
            self._dinner_triggered = False

        if bool(settings.get('sleep_enabled', True)):
            set_h = int(settings.get('sleep_hour', 22))
            set_m = int(settings.get('sleep_min', 0))
            if hour == set_h and minute == set_m and not self._sleep_triggered and not self.is_reminder_pending('sleep'):
                self.add_reminder_dialog('sleep', 'sleep')
                self._sleep_triggered = True
            if hour != set_h or minute != set_m:
                self._sleep_triggered = False

        self._control_settings['reminder_elapsed'] = dict(self._reminder_elapsed)
        self._save_control_settings()

    def show_games(self):
        if GameManager is None:
            self.add_dialog("小游戏模块未加载" if self.lang == "zh" else "Game module is unavailable")
            return
        if self.games_window is None:
            self.games_window = GamesWindow(self)
        self.games_window.update_language(self.lang)
        self.games_window.update_position()
        self.games_window.show()
        self.games_window.raise_()

    def show_control_panel(self):
        if self.control_panel is None:
            self.control_panel = ControlPanel(self)
        self.control_panel.update_position()
        self.control_panel.show()
        self.control_panel.raise_()

    def show_products(self):
        if self.product_window is None:
            self.product_window = ProductWindow(self)
        self.product_window.update_position()
        self.product_window.show()
        self.product_window.raise_()
        self.product_window.show_ranking()

    def _toggle_bubble_mode(self):
        if getattr(self, 'bubble_mode', 'follow') == 'follow':
            self.bubble_mode = 'fixed'
            self.bubble.move_to_bottom_right()
        else:
            self.bubble_mode = 'follow'
            self.update_bubble_position()
        self._update_menu_language()

    def _set_spam_volume(self, value):
        value = max(0, min(100, int(value)))
        self.spam_volume = value
        for sound in getattr(self, 'spam_voice_sounds', []):
            sound.setVolume(value / 100.0)
        for attr in ('spam_laugh_sound', 'spam_laugh_long_sound'):
            sound = getattr(self, attr, None)
            if sound is not None:
                sound.setVolume(value / 100.0)
        if hasattr(self, 'volume_value_label'):
            self.volume_value_label.setText(f"{value}%")
        save_spam_volume(value)

    def _create_volume_menu(self):
        """创建菜单中的 Spamton 音量滑条。"""
        self.volume_menu = QMenu(self)
        self.volume_slider = QSlider(Qt.Horizontal, self.volume_menu)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(getattr(self, "spam_volume", 80))
        self.volume_slider.setFixedWidth(180)
        self.volume_slider.valueChanged.connect(self._set_spam_volume)

        # 用 QWidgetAction 把真正的拉条放进 QMenu。
        slider_action = QWidgetAction(self.volume_menu)
        slider_container = QWidget(self.volume_menu)
        slider_layout = QHBoxLayout(slider_container)
        slider_layout.setContentsMargins(10, 4, 10, 4)
        slider_layout.setSpacing(8)
        slider_layout.addWidget(self.volume_slider)

        self.volume_value_label = QLabel(f"{self.spam_volume}%", slider_container)
        self.volume_value_label.setMinimumWidth(38)
        self.volume_value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        slider_layout.addWidget(self.volume_value_label)

        slider_action.setDefaultWidget(slider_container)
        self.volume_menu.addAction(slider_action)
        return self.volume_menu

    def create_menu(self):
        self.menu = QMenu(self)
        self.control_action = QAction(self)
        self.control_action.triggered.connect(self.show_control_panel)
        self.note_action = QAction(self)
        self.note_action.triggered.connect(self.show_note)
        self.flirt_action = QAction(self)
        self.flirt_action.triggered.connect(self.flirt)
        self.product_action = QAction(self)
        self.product_action.triggered.connect(self.show_products)
        self.games_action = QAction(self)
        self.games_action.triggered.connect(self.show_games)
        self.bubble_mode_action = QAction(self)
        self.bubble_mode_action.triggered.connect(self._toggle_bubble_mode)

        self._create_volume_menu()

        self.toggle_animation_action = QAction(self)
        self.toggle_animation_action.triggered.connect(self._toggle_animation)
        self.toggle_visibility_action = QAction(self)
        self.toggle_visibility_action.triggered.connect(self._toggle_visibility_from_menu)
        self.toggle_auto_dialog_action = QAction(self)
        self.toggle_auto_dialog_action.triggered.connect(self._toggle_auto_dialog)
        self.lang_action = QAction(self)
        self.lang_action.triggered.connect(self.switch_language)
        self.quit_action = QAction(self)
        self.quit_action.triggered.connect(self.quit_app)

        self.menu.addAction(self.control_action)
        self.menu.addAction(self.note_action)
        self.menu.addAction(self.flirt_action)
        self.menu.addMenu(self.volume_menu)
        self.menu.addAction(self.product_action)
        self.menu.addAction(self.games_action)
        self.menu.addAction(self.bubble_mode_action)
        self.menu.addAction(self.toggle_animation_action)
        self.menu.addAction(self.toggle_visibility_action)
        self.menu.addAction(self.toggle_auto_dialog_action)
        self.menu.addSeparator()
        self.menu.addAction(self.lang_action)
        self.menu.addSeparator()
        self.menu.addAction(self.quit_action)

        self._update_menu_language()

    def quit_app(self):
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
        self.add_dialog(random.choice(get_dialogues(self.lang, 'close')))
        self._close_timer = QTimer(self)
        self._close_timer.setSingleShot(True)
        self._close_timer.timeout.connect(self._prepare_close)
        self._close_timer.start(5000)

    def _prepare_close(self):
        # 关闭前播放 1 秒 pet1~pet2 说话动画。
        if hasattr(self, 'black_screen_timer'):
            self.black_screen_timer.stop()
        if hasattr(self, 'black_screen_hide_timer'):
            self.black_screen_hide_timer.stop()
        self._black_screen_active = False
        self._start_talking_mouth()
        self.label.raise_()
        self.show()
        self.raise_()
        self.animation_timer.stop()
        self.startup_timer.stop()
        self.clear_dialog_timer()
        if hasattr(self, "note_repeat_timer"):
            self.note_repeat_timer.stop()
        QTimer.singleShot(1000, self._really_quit)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    pet = DesktopPet()
    pet.show()
    sys.exit(app.exec_())
