import ctypes
import datetime
import os
import random
import sys
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser
from PIL import Image, ImageDraw, ImageFont, ImageTk

VERSION = "3.6.0"

# Set explicit Windows AppUserModelID so taskbar groups and shows the icon properly
if sys.platform.startswith("win"):
    try:
        myappid = "rkmvpc.watermarker.desktop.3.6.0"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass


def _force_taskbar_icon(win):
    """Forces Windows to display an overrideredirect/frameless window on the taskbar."""
    if sys.platform.startswith("win"):
        try:
            win.update_idletasks()
            GWL_EXSTYLE = -20
            WS_EX_APPWINDOW = 0x00040000
            WS_EX_TOOLWINDOW = 0x00000080
            hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
            if not hwnd:
                hwnd = win.winfo_id()
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style = (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
            win.withdraw()
            win.after(10, win.deiconify)
        except Exception:
            pass


FONT_LIST = [
    "Arial",
    "Calibri",
    "Times New Roman",
    "Helvetica",
    "Segoe UI",
    "Trebuchet MS",
    "Courier New",
    "Verdana"
]


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def get_font_object(font_name, font_size):
    font_map = {
        "Arial": "arial.ttf",
        "Calibri": "calibri.ttf",
        "Times New Roman": "times.ttf",
        "Helvetica": "arial.ttf",
        "Segoe UI": "segoeui.ttf",
        "Garamond": "gara.ttf",
        "Trebuchet MS": "trebuc.ttf",
        "Century Gothic": "gothic.ttf",
        "Courier New": "cour.ttf",
        "Verdana": "verdana.ttf"
    }
    filename = font_map.get(font_name, "arial.ttf")
    try:
        return ImageFont.truetype(filename, font_size)
    except IOError:
        try:
            return ImageFont.truetype(font_name, font_size)
        except IOError:
            return ImageFont.load_default()


def get_position_coords(pos_name, inner_w, inner_h, element_w, element_h, pad_x, pad_y, offset_x=0, offset_y=0):
    """
    Calculates placement coordinates centered relative to the inner image region offset by pad_x and pad_y.
    Strictly clamps coordinates within the inner photo boundary [offset_x, offset_y] .. [offset_x + inner_w - element_w, offset_y + inner_h - element_h]
    so watermark elements stop at the boundary and never bleed into the border/frame.
    """
    min_x = offset_x
    max_x = offset_x + max(0, inner_w - element_w)
    min_y = offset_y
    max_y = offset_y + max(0, inner_h - element_h)

    raw_x = offset_x + ((inner_w - element_w) // 2) + pad_x
    raw_y = offset_y + ((inner_h - element_h) // 2) + pad_y

    x = max(min_x, min(max_x, raw_x))
    y = max(min_y, min(max_y, raw_y))
    return x, y


def apply_watermark_and_border(image_path, config):
    orig_img = Image.open(image_path).convert("RGBA")
    orig_w, orig_h = orig_img.size
    # Use the geometric mean (or square root of image area) so aspect ratio doesn't distort scale
    max_dim = int((orig_w * orig_h) ** 0.5)

    # Calculate border relative to longest edge
    border_scale = config.get("border_scale", 0.02)
    border_px = int(max_dim * border_scale)
    
    new_w = orig_w + (border_px * 2)
    new_h = orig_h + (border_px * 2)

    # Canvas with solid white border background
    canvas = Image.new("RGBA", (new_w, new_h), (255, 255, 255, 255))
    canvas.paste(orig_img, (border_px, border_px), mask=orig_img)

    element_boxes = {}

    # 1. Overlay Image Watermarks (RKM, Club, QR)
    for key in ["rkm", "club", "qr"]:
        item = config.get(key, {})
        if item.get("enabled"):
            if key == "rkm" and item.get("greyscale", False):
                logo_path = item.get("bnw_path", "")
            else:
                logo_path = item.get("path", "")

            if logo_path and os.path.exists(logo_path):
                logo = Image.open(logo_path).convert("RGBA")
                
                logo_scale = item.get("scale", 0.12)
                max_size = max(16, int(max_dim * logo_scale))
                logo.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

                opacity = item.get("opacity", 0.6)
                r, g, b, alpha = logo.split()
                alpha = alpha.point(lambda p: int(p * opacity))
                logo.putalpha(alpha)

                pad_x = int(max_dim * item.get("pad_x_scale", 0.0))
                pad_y = int(max_dim * item.get("pad_y_scale", 0.0))

                x, y = get_position_coords(
                    item.get("pos", "Center"), orig_w, orig_h, 
                    logo.width, logo.height, 
                    pad_x, pad_y,
                    offset_x=border_px, offset_y=border_px
                )
                canvas.paste(logo, (x, y), mask=logo)
                element_boxes[key] = (x, y, logo.width, logo.height)

    # Helper function to render text watermarks with relative positioning & sizes
    def render_text_box(text_cfg, has_bg=True):
        if not text_cfg.get("enabled") or not text_cfg.get("content", "").strip():
            return None
        
        txt_str = text_cfg["content"]
        font_scale = text_cfg.get("size_scale", 0.025)
        font_size = max(12, int(max_dim * font_scale))
        font = get_font_object(text_cfg.get("font", "Arial"), font_size)

        dummy_img = Image.new("RGBA", (1, 1))
        dummy_draw = ImageDraw.Draw(dummy_img)
        bbox = dummy_draw.textbbox((0, 0), txt_str, font=font)
        raw_txt_w = bbox[2] - bbox[0]
        raw_txt_h = bbox[3] - bbox[1]
        offset_x_bbox = bbox[0]
        offset_y_bbox = bbox[1]

        bg_enabled = has_bg and text_cfg.get("bg_enabled", False)
        bg_pad_x = int(max_dim * text_cfg.get("bg_pad_x_scale", 0.005)) if bg_enabled else 0
        bg_pad_y = int(max_dim * text_cfg.get("bg_pad_y_scale", 0.005)) if bg_enabled else 0

        box_w = raw_txt_w + (2 * bg_pad_x)
        box_h = raw_txt_h + (2 * bg_pad_y)
        text_element = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
        text_draw = ImageDraw.Draw(text_element)

        if bg_enabled:
            bg_op = int(text_cfg.get("bg_opacity", 0.5) * 255)
            text_draw.rectangle([0, 0, box_w, box_h], fill=(0, 0, 0, bg_op))

        opacity_val = int(text_cfg.get("opacity", 0.6) * 255)
        text_color = (255, 255, 255, opacity_val)

        text_x = bg_pad_x - offset_x_bbox
        text_y = bg_pad_y - offset_y_bbox
        text_draw.text((text_x, text_y), txt_str, fill=text_color, font=font)

        rot_angle = text_cfg.get("rotation", 0)
        if rot_angle != 0:
            text_element = text_element.rotate(rot_angle, expand=True)

        txt_w, txt_h = text_element.size
        pad_x = int(max_dim * text_cfg.get("pad_x_scale", 0.0))
        pad_y = int(max_dim * text_cfg.get("pad_y_scale", 0.0))

        x, y = get_position_coords(
            text_cfg.get("pos", "Center"), orig_w, orig_h, 
            txt_w, txt_h, 
            pad_x, pad_y,
            offset_x=border_px, offset_y=border_px
        )
        
        canvas.paste(text_element, (x, y), mask=text_element)
        return (x, y, txt_w, txt_h)

    # 2. Overlay Copyright Info Text
    c_box = render_text_box(config.get("copyright", {}), has_bg=True)
    if c_box:
        element_boxes["copyright"] = c_box

    # 3. Overlay Custom Text Watermark
    ct_box = render_text_box(config.get("custom_text", {}), has_bg=False)
    if ct_box:
        element_boxes["custom_text"] = ct_box

    return canvas.convert("RGB"), element_boxes


class ScaleValueTooltip:
    """Floating tooltip that displays scale values only while dragging/scrolling."""
    def __init__(self, scale):
        self.scale = scale
        self.tip_window = None
        self.scale.bind("<ButtonPress-1>", self.show_tooltip, add="+")
        self.scale.bind("<B1-Motion>", self.update_tooltip, add="+")
        self.scale.bind("<ButtonRelease-1>", self.hide_tooltip, add="+")

    def show_tooltip(self, event=None):
        self.update_tooltip(event)

    def update_tooltip(self, event=None):
        try:
            val = self.scale.get()
        except Exception:
            return

        if isinstance(val, float):
            txt = f"{val * 100:.1f}%" if val < 1.0 else f"{val:.1f}"
        else:
            txt = str(val)

        if not self.tip_window:
            self.tip_window = tw = tk.Toplevel(self.scale)
            tw.wm_overrideredirect(True)
            tw.attributes("-topmost", True)
            lbl = tk.Label(
                tw, text=txt, background="#007ACC", foreground="#FFFFFF",
                font=("Segoe UI", 9, "bold"), padx=6, pady=2, relief="solid", bd=1
            )
            lbl.pack()
        else:
            for widget in self.tip_window.winfo_children():
                widget.config(text=txt)

        x = self.scale.winfo_pointerx() - 15
        y = self.scale.winfo_pointery() - 35
        self.tip_window.wm_geometry(f"+{x}+{y}")

    def hide_tooltip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


class ScrubbableNumberField(tk.Frame):
    """
    Blender-style draggable numeric scrub field widget.
    Features:
    - Sleek dark container with border, hover effect, and visual fill bar.
    - Click and drag horizontally (<->) to scrub values smoothly.
    - Hold Shift while dragging or scrolling for 5x fine-grained precision.
    - Mouse wheel scroll support to nudge values.
    - Double-click (or click text) to open an inline Entry box and type exact value.
    - Live two-way binding with tk.DoubleVar / tk.IntVar.
    """
    def __init__(self, parent, label_text, variable, from_=-0.75, to=0.75,
                 step=0.005, fmt="pct", command=None, colors=None, width=125, height=26):
        super().__init__(parent, bg=colors.get("bg_card", "#1C1C1C") if colors else "#1C1C1C")
        self.label_text = label_text
        self.variable = variable
        self.from_ = min(from_, to)
        self.to = max(from_, to)
        self.step = step
        self.fmt = fmt
        self.command = command
        self.width = width
        self.height = height
        self.colors = colors or {
            "bg_card":    "#1C1C1C",
            "bg_pill":    "#141414",
            "bg_hover":   "#202020",
            "border":     "#2E2E2E",
            "border_hov": "#0078D4",
            "fill":       "#143B63",
            "accent":     "#0078D4",
            "fg_label":   "#8A8A8A",
            "fg_val":     "#E0E0E0",
            "white":      "#FFFFFF",
        }

        self._dragging = False
        self._start_x = 0
        self._start_val = 0.0
        self._entry_widget = None
        self._is_hovered = False

        self.canvas = tk.Canvas(
            self, width=self.width, height=self.height,
            bg=self.colors.get("bg_pill", "#141414"),
            highlightthickness=1,
            highlightbackground=self.colors.get("border", "#2E2E2E"),
            cursor="size_we"
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.bind("<Enter>", self._on_enter)
        self.canvas.bind("<Leave>", self._on_leave)
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", self._on_mousewheel)
        self.canvas.bind("<Button-5>", self._on_mousewheel)
        self.canvas.bind("<Configure>", lambda e: self._redraw())

        self.variable.trace_add("write", lambda *_: self._redraw())
        self._redraw()

    def _format_value(self, val):
        if self.fmt == "pct":
            pct = val * 100.0
            if abs(pct) < 0.05:
                return "0.0%"
            sign = "+" if pct > 0 else ""
            return f"{sign}{pct:.1f}%"
        elif self.fmt == "deg":
            return f"{int(val)}°"
        else:
            return f"{val:.3f}"

    def _redraw(self):
        if self._entry_widget is not None:
            return
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w <= 1:
            w = self.width
        if h <= 1:
            h = self.height

        try:
            val = float(self.variable.get())
        except Exception:
            val = 0.0

        # Draw progress / fill bar
        if self.from_ < 0 < self.to:
            zero_x = int(w * (-self.from_) / (self.to - self.from_))
            val_clamped = max(self.from_, min(self.to, val))
            val_x = int(w * (val_clamped - self.from_) / (self.to - self.from_))
            x1 = min(zero_x, val_x)
            x2 = max(zero_x, val_x)
            if x2 - x1 > 0:
                fill_col = self.colors.get("fill", "#143B63")
                self.canvas.create_rectangle(x1, 1, x2, h - 1, fill=fill_col, width=0)
            self.canvas.create_line(zero_x, 1, zero_x, h - 1, fill="#383838", width=1)
        else:
            val_clamped = max(self.from_, min(self.to, val))
            pct = (val_clamped - self.from_) / (self.to - self.from_) if (self.to > self.from_) else 0
            fill_w = int(w * pct)
            if fill_w > 0:
                fill_col = self.colors.get("fill", "#143B63")
                self.canvas.create_rectangle(1, 1, fill_w, h - 1, fill=fill_col, width=0)

        # Draw Label (Left aligned)
        self.canvas.create_text(
            8, h // 2, text=self.label_text,
            anchor="w", fill=self.colors.get("fg_label", "#8A8A8A"),
            font=("Segoe UI", 8)
        )

        # Draw Value (Right aligned)
        val_str = self._format_value(val)
        self.canvas.create_text(
            w - 8, h // 2, text=val_str,
            anchor="e", fill=self.colors.get("fg_val", "#E0E0E0"),
            font=("Segoe UI", 8, "bold")
        )

    def _on_enter(self, event):
        self._is_hovered = True
        self.canvas.config(highlightbackground=self.colors.get("border_hov", "#0078D4"))

    def _on_leave(self, event):
        self._is_hovered = False
        if not self._dragging:
            self.canvas.config(highlightbackground=self.colors.get("border", "#2E2E2E"))

    def _on_press(self, event):
        self._dragging = False
        self._start_x = event.x_root
        try:
            self._start_val = float(self.variable.get())
        except Exception:
            self._start_val = 0.0
        self.canvas.config(highlightbackground=self.colors.get("border_hov", "#0078D4"))
        self.focus_set()

    def _on_motion(self, event):
        dx = event.x_root - self._start_x
        if abs(dx) > 1 or self._dragging:
            self._dragging = True
            is_shift = bool(getattr(event, "state", 0) & 0x0001)
            span = self.to - self.from_
            sensitivity = (span / 300.0) / (5.0 if is_shift else 1.0)
            new_val = self._start_val + (dx * sensitivity)
            new_val = max(self.from_, min(self.to, new_val))
            if self.fmt == "pct":
                new_val = round(new_val, 4)
            if isinstance(self.variable, tk.IntVar):
                self.variable.set(int(round(new_val)))
            else:
                self.variable.set(new_val)
            if self.command:
                self.command()

    def _on_release(self, event):
        self._dragging = False
        if not self._is_hovered:
            self.canvas.config(highlightbackground=self.colors.get("border", "#2E2E2E"))

    def _on_mousewheel(self, event):
        if hasattr(event, 'num') and event.num == 4:
            direction = 1
        elif hasattr(event, 'num') and event.num == 5:
            direction = -1
        else:
            direction = 1 if getattr(event, 'delta', 0) > 0 else -1

        is_shift = bool(getattr(event, "state", 0) & 0x0001)
        step = self.step * 0.2 if is_shift else self.step
        try:
            curr = float(self.variable.get())
        except Exception:
            curr = 0.0
        new_val = max(self.from_, min(self.to, round(curr + (direction * step), 4)))
        if isinstance(self.variable, tk.IntVar):
            self.variable.set(int(round(new_val)))
        else:
            self.variable.set(new_val)
        if self.command:
            self.command()

    def _on_double_click(self, event):
        if self._entry_widget is not None:
            return

        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()

        try:
            curr_val = self.variable.get()
        except Exception:
            curr_val = 0.0

        if self.fmt == "pct":
            init_str = f"{curr_val * 100.0:.2f}".rstrip('0').rstrip('.')
            if init_str == "-0" or init_str == "":
                init_str = "0"
        elif self.fmt == "deg":
            init_str = str(int(curr_val))
        else:
            init_str = f"{curr_val:.3f}".rstrip('0').rstrip('.')

        entry = tk.Entry(
            self.canvas, bg="#0D0D0D", fg=self.colors.get("white", "#FFFFFF"),
            insertbackground=self.colors.get("white", "#FFFFFF"),
            relief="solid", bd=1,
            font=("Segoe UI", 8, "bold"), justify="center"
        )
        self._entry_widget = entry
        entry.place(x=0, y=0, width=w, height=h)
        entry.insert(0, init_str)
        entry.select_range(0, tk.END)
        entry.focus_set()

        def commit(e=None):
            if self._entry_widget is None:
                return
            raw = entry.get().strip()
            if raw:
                try:
                    is_pct = False
                    if raw.endswith("%"):
                        raw = raw[:-1].strip()
                        is_pct = True
                    elif raw.endswith("°"):
                        raw = raw[:-1].strip()
                    v = float(raw)
                    if self.fmt == "pct":
                        if is_pct or abs(v) > 1.0:
                            v = v / 100.0
                    v = max(self.from_, min(self.to, v))
                    if isinstance(self.variable, tk.IntVar):
                        self.variable.set(int(round(v)))
                    else:
                        self.variable.set(v)
                    if self.command:
                        self.command()
                except ValueError:
                    pass
            cleanup()

        def cancel(e=None):
            cleanup()

        def cleanup():
            if self._entry_widget is not None:
                try:
                    self._entry_widget.destroy()
                except Exception:
                    pass
                self._entry_widget = None
                self._redraw()

        entry.bind("<Return>", commit)
        entry.bind("<KP_Enter>", commit)
        entry.bind("<Escape>", cancel)
        entry.bind("<FocusOut>", commit)


class WatermarkApp:
    # Colour palette
    C = {
        "bg_deep":        "#080808",
        "bg_main":        "#0D0D0D",
        "bg_sidebar":     "#111111",
        "bg_panel":       "#161616",
        "bg_card":        "#1C1C1C",
        "bg_pill":        "#141414",
        "bg_hover":       "#222222",
        "bg_active":      "#1A1A1A",
        "sep":            "#282828",
        "fg_main":        "#D0D0D0",
        "fg_dim":         "#666666",
        "fg_label":       "#4EC9B0",
        "accent":         "#0078D4",
        "accent_lit":     "#1A8EE6",
        "accent_grn":     "#17B978",
        "accent_grn_lit": "#1ED48A",
        "white":          "#FFFFFF",
        "border":         "#2E2E2E",
        "border_hov":     "#0078D4",
        "fill":           "#143B63",
        "fg_val":         "#E0E0E0",
    }

    def __init__(self, root):
        self.root = root
        self.root.title("Vidyamandira Photo Watermarker  v3.6.0")
        self.root.geometry("1220x820")
        self.root.minsize(1000, 660)

        self._preview_timer = None
        self.selected_element = None
        self.display_boxes = {}
        self.active_tab = "master"
        self._nav_items = {}
        self._panels = {}
        self._drag_data = None
        self._preview_scale_factor = 1.0

        # File paths
        self.rkm_path     = resource_path("rkm_logo.png")
        self.bnw_rkm_path = resource_path("bnw_rkm_logo.png")
        self.club_path    = resource_path("logo.png")
        self.qr_path      = resource_path("qr.jpeg")
        self.icon_path    = resource_path("logo.ico")

        try:
            if os.path.exists(self.icon_path):
                self.root.iconbitmap(self.icon_path)
        except Exception:
            pass

        try:
            if os.path.exists(self.club_path):
                logo_img = Image.open(self.club_path)
                self.app_icon = ImageTk.PhotoImage(logo_img)
                self.root.iconphoto(True, self.app_icon)
        except Exception as err:
            print(f"Could not load application icon: {err}")

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.selected_folder      = ""
        self.all_files            = []
        self.sample_image_path    = None
        self.preview_photo_ref    = None
        self.is_single_image_mode = False
        self.single_image_save_folder = ""

        current_year = datetime.datetime.now().year
        self.default_text = f"© {current_year} Vidyamandira Photography Club"

        # Tk variables
        self.border_scale_var = tk.DoubleVar(value=0.02)

        self.rkm_enable        = tk.BooleanVar(value=True)
        self.rkm_pos           = tk.StringVar(value="Center")
        self.rkm_opacity_var   = tk.DoubleVar(value=0.6)
        self.rkm_scale_var     = tk.DoubleVar(value=0.12)
        self.rkm_padx_var      = tk.DoubleVar(value=0.0)
        self.rkm_pady_var      = tk.DoubleVar(value=0.0)
        self.rkm_greyscale_var = tk.BooleanVar(value=False)

        self.club_enable      = tk.BooleanVar(value=False)
        self.club_pos         = tk.StringVar(value="Center")
        self.club_opacity_var = tk.DoubleVar(value=0.6)
        self.club_scale_var   = tk.DoubleVar(value=0.12)
        self.club_padx_var    = tk.DoubleVar(value=0.0)
        self.club_pady_var    = tk.DoubleVar(value=0.0)

        self.qr_enable        = tk.BooleanVar(value=False)
        self.qr_pos           = tk.StringVar(value="Center")
        self.qr_opacity_var   = tk.DoubleVar(value=0.6)
        self.qr_scale_var     = tk.DoubleVar(value=0.12)
        self.qr_padx_var      = tk.DoubleVar(value=0.0)
        self.qr_pady_var      = tk.DoubleVar(value=0.0)

        self.copyright_enable      = tk.BooleanVar(value=True)
        self.copyright_pos         = tk.StringVar(value="Center")
        self.copyright_opacity_var = tk.DoubleVar(value=0.6)
        self.copyright_size_var    = tk.DoubleVar(value=0.025)
        self.copyright_val         = tk.StringVar(value=self.default_text)
        self.copyright_padx_var    = tk.DoubleVar(value=-0.5)
        self.copyright_pady_var    = tk.DoubleVar(value=0.5)
        self.copyright_rot_var     = tk.IntVar(value=0)
        self.copyright_font_var    = tk.StringVar(value="Arial")
        self.copyright_bg_enable   = tk.BooleanVar(value=True)
        self.copyright_bg_op_var   = tk.DoubleVar(value=0.6)
        self.copyright_bg_padx_var = tk.DoubleVar(value=0.005)
        self.copyright_bg_pady_var = tk.DoubleVar(value=0.005)

        self.custom_text_enable      = tk.BooleanVar(value=False)
        self.custom_text_pos         = tk.StringVar(value="Center")
        self.custom_text_opacity_var = tk.DoubleVar(value=0.8)
        self.custom_text_size_var    = tk.DoubleVar(value=0.03)
        self.custom_text_val         = tk.StringVar(value="Custom Watermark")
        self.custom_text_padx_var    = tk.DoubleVar(value=0.0)
        self.custom_text_pady_var    = tk.DoubleVar(value=0.0)
        self.custom_text_rot_var     = tk.IntVar(value=0)
        self.custom_text_font_var    = tk.StringVar(value="Arial")

        self._apply_dark_theme()
        self._setup_ui()
        self._update_tabs()
        self.root.bind_all("<Escape>", lambda e: self.select_element(None))
        for arrow_key in ("<Up>", "<Down>", "<Left>", "<Right>",
                          "<KP_Up>", "<KP_Down>", "<KP_Left>", "<KP_Right>"):
            self.root.bind_all(arrow_key, self._on_arrow_key)
        self.show_startup_dialog()

    # =========================================================================
    #  Theme & Styling
    # =========================================================================

    def _attach_tooltip(self, scale_widget):
        ScaleValueTooltip(scale_widget)
        return scale_widget

    def _create_checkbox_images(self):
        C = self.C
        size = 16

        img_off = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img_off)
        d.rectangle([1, 1, size - 2, size - 2], outline="#484848", width=2, fill="#191919")
        self.img_chk_off = ImageTk.PhotoImage(img_off)

        img_on = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img_on)
        d.rectangle([1, 1, size - 2, size - 2], outline=C["accent"], width=2, fill=C["accent"])
        d.line([(3, 8), (7, 12), (13, 4)], fill=C["white"], width=2)
        self.img_chk_on = ImageTk.PhotoImage(img_on)

        style = ttk.Style()
        try:
            style.element_create("Custom.Indicator", "image", self.img_chk_off,
                                 ("selected", self.img_chk_on))
        except tk.TclError:
            pass
        style.layout("TCheckbutton", [
            ("Checkbutton.padding", {"sticky": "nswe", "children": [
                ("Custom.Indicator", {"side": "left", "sticky": ""}),
                ("Checkbutton.focus", {"side": "left", "sticky": "w", "children": [
                    ("Checkbutton.label", {"sticky": "nswe"}),
                ]}),
            ]}),
        ])

    def _apply_dark_theme(self):
        C = self.C
        self.bg_main     = C["bg_card"]
        self.bg_panel    = C["bg_panel"]
        self.bg_card     = C["bg_card"]
        self.fg_text     = C["fg_main"]
        self.accent_blue = C["accent"]

        self.root.configure(bg=C["bg_main"])
        self.root.option_add("*TCombobox*Listbox.background",       C["bg_card"])
        self.root.option_add("*TCombobox*Listbox.foreground",       C["white"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", C["accent"])
        self.root.option_add("*TCombobox*Listbox.selectForeground", C["white"])

        style = ttk.Style()
        style.theme_use("clam")

        style.configure(".",
            background=C["bg_card"], foreground=C["fg_main"],
            font=("Segoe UI", 9))
        style.configure("TFrame",       background=C["bg_card"])
        style.configure("TLabel",       background=C["bg_card"], foreground=C["fg_main"])
        style.configure("TCheckbutton", background=C["bg_card"], foreground=C["fg_main"], focuscolor="")
        style.map("TCheckbutton",       background=[("active", C["bg_card"])])
        self._create_checkbox_images()

        style.configure("TLabelframe",
            background=C["bg_card"], foreground=C["fg_label"],
            borderwidth=1, relief="solid")
        style.configure("TLabelframe.Label",
            background=C["bg_card"], foreground=C["fg_label"],
            font=("Segoe UI", 9, "bold"))

        style.configure("TButton",
            background="#272727", foreground=C["white"],
            borderwidth=0, padding=6)
        style.map("TButton",
            background=[("active", C["accent"]), ("disabled", "#181818")])

        style.configure("TCombobox",
            fieldbackground=C["bg_main"], background="#272727",
            foreground=C["white"], arrowcolor=C["white"])
        style.map("TCombobox",
            fieldbackground=[("readonly", C["bg_main"])],
            foreground=[("readonly", C["white"])])

        style.configure("Horizontal.TScale",
            background=C["bg_card"], troughcolor=C["sep"])

        style.configure("Vertical.TScrollbar",
            background=C["bg_card"], troughcolor=C["bg_panel"],
            arrowcolor=C["fg_dim"], borderwidth=0)

        style.configure("Green.Horizontal.TProgressbar",
            troughcolor=C["sep"],
            background=C["accent_grn"],
            bordercolor=C["accent_grn"],
            lightcolor=C["accent_grn"],
            darkcolor=C["accent_grn"])

    # =========================================================================
    #  Main UI Layout Construction
    # =========================================================================

    def _setup_ui(self):
        C = self.C

        # Top Header bar
        hdr = tk.Frame(self.root, bg=C["bg_deep"], height=50)
        hdr.pack(fill=tk.X, side=tk.TOP)
        hdr.pack_propagate(False)

        tk.Label(hdr, text="📷", bg=C["bg_deep"], fg=C["accent"],
                 font=("Segoe UI", 18)).pack(side=tk.LEFT, padx=(14, 5), pady=6)
        tk.Label(hdr, text="Vidyamandira Photo Watermarker",
                 bg=C["bg_deep"], fg=C["white"],
                 font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT, pady=6)
        tk.Label(hdr, text=" v3.6.0 ",
                 bg=C["accent"], fg=C["white"],
                 font=("Segoe UI", 7, "bold"), padx=5, pady=3).pack(
            side=tk.LEFT, padx=10, pady=16)

        self.lbl_workspace = tk.Label(
            hdr, text="No workspace loaded",
            bg=C["bg_deep"], fg=C["fg_dim"],
            font=("Segoe UI", 8))
        self.lbl_workspace.pack(side=tk.RIGHT, padx=16)

        tk.Frame(self.root, bg=C["sep"], height=1).pack(fill=tk.X, side=tk.TOP)

        # Bottom Status bar (packed bottom first)
        tk.Frame(self.root, bg=C["sep"], height=1).pack(fill=tk.X, side=tk.BOTTOM)
        sbar = tk.Frame(self.root, bg=C["bg_deep"], height=26)
        sbar.pack(fill=tk.X, side=tk.BOTTOM)
        sbar.pack_propagate(False)

        self.status_left = tk.Label(
            sbar, text="Ready  –  no file loaded",
            bg=C["bg_deep"], fg=C["fg_dim"],
            font=("Segoe UI", 8), anchor="w")
        self.status_left.pack(side=tk.LEFT, padx=12)
        tk.Label(sbar,
                 text="Vidyamandira Photography Club  ·  v3.6.0",
                 bg=C["bg_deep"], fg=C["fg_dim"],
                 font=("Segoe UI", 8), anchor="e").pack(side=tk.RIGHT, padx=12)

        # Central Body area
        body = tk.Frame(self.root, bg=C["bg_main"])
        body.pack(fill=tk.BOTH, expand=True)

        # Left Sidebar Navigation (158 px)
        self.sidebar = tk.Frame(body, bg=C["bg_sidebar"], width=158)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)
        tk.Frame(body, bg=C["sep"], width=1).pack(side=tk.LEFT, fill=tk.Y)

        # Control Panel (310 px, scrollable canvas)
        ctrl_outer = tk.Frame(body, bg=C["bg_panel"], width=310)
        ctrl_outer.pack(side=tk.LEFT, fill=tk.Y)
        ctrl_outer.pack_propagate(False)
        tk.Frame(body, bg=C["sep"], width=1).pack(side=tk.LEFT, fill=tk.Y)

        self._ctrl_canvas = tk.Canvas(
            ctrl_outer, bg=C["bg_panel"],
            highlightthickness=0, bd=0)
        ctrl_vscroll = ttk.Scrollbar(
            ctrl_outer, orient="vertical",
            command=self._ctrl_canvas.yview)
        self._ctrl_inner = tk.Frame(self._ctrl_canvas, bg=C["bg_panel"])

        self._ctrl_inner.bind(
            "<Configure>",
            lambda e: self._ctrl_canvas.configure(
                scrollregion=self._ctrl_canvas.bbox("all")))

        self._ctrl_win_id = self._ctrl_canvas.create_window(
            (0, 0), window=self._ctrl_inner, anchor="nw")
        self._ctrl_canvas.configure(yscrollcommand=ctrl_vscroll.set)

        ctrl_vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._ctrl_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ctrl_outer.bind(
            "<Configure>",
            lambda e: self._ctrl_canvas.itemconfig(
                self._ctrl_win_id,
                width=e.width - (ctrl_vscroll.winfo_width() or 16)))

        def _wheel(e):
            if hasattr(e, 'num') and e.num == 4:
                delta = -1
            elif hasattr(e, 'num') and e.num == 5:
                delta = 1
            else:
                delta = int(-1 * (e.delta / 120))
            self._ctrl_canvas.yview_scroll(delta, "units")

        def _bind_panel_scroll(e):
            self.root.bind_all("<MouseWheel>", _wheel)
            self.root.bind_all("<Button-4>", _wheel)
            self.root.bind_all("<Button-5>", _wheel)

        def _unbind_panel_scroll(e):
            self.root.unbind_all("<MouseWheel>")
            self.root.unbind_all("<Button-4>")
            self.root.unbind_all("<Button-5>")

        ctrl_outer.bind("<Enter>", _bind_panel_scroll)
        ctrl_outer.bind("<Leave>", _unbind_panel_scroll)

        # Right Preview Column
        preview_col = tk.Frame(body, bg=C["bg_main"])
        preview_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._build_preview(preview_col)

        # Build sidebar & content panels
        self._build_sidebar_nav()
        self._build_all_panels()
        self._switch_tab("master")

    # =========================================================================
    #  Preview Canvas Panel
    # =========================================================================

    def _build_preview(self, parent):
        C = self.C
        phdr = tk.Frame(parent, bg=C["bg_main"])
        phdr.pack(fill=tk.X, padx=14, pady=(12, 6))
        tk.Label(phdr, text="LIVE PREVIEW",
                 bg=C["bg_main"], fg=C["accent"],
                 font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT)
        self.lbl_preview_hint = tk.Label(
            phdr, text="Click and drag any watermark element on canvas to reposition",
            bg=C["bg_main"], fg=C["fg_dim"],
            font=("Segoe UI", 7))
        self.lbl_preview_hint.pack(side=tk.RIGHT)

        canvas_border = tk.Frame(parent, bg=C["sep"], padx=1, pady=1)
        canvas_border.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 12))

        self.preview_canvas = tk.Canvas(
            canvas_border, bg="#060606", highlightthickness=0, takefocus=True)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)

        # Interactive Canvas Event Bindings
        self.preview_canvas.bind("<ButtonPress-1>",   self._on_canvas_press)
        self.preview_canvas.bind("<B1-Motion>",       self._on_canvas_drag)
        self.preview_canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.preview_canvas.bind("<Motion>",          self._on_canvas_hover)
        self.preview_canvas.bind("<Enter>",           self._bind_canvas_scroll)
        self.preview_canvas.bind("<Leave>",           self._unbind_canvas_scroll)

    # =========================================================================
    #  Sidebar Navigation Component
    # =========================================================================

    def _build_sidebar_nav(self):
        C = self.C
        tk.Label(self.sidebar, text="NAVIGATION",
                 bg=C["bg_sidebar"], fg=C["fg_dim"],
                 font=("Segoe UI", 7, "bold")).pack(
            anchor="w", padx=14, pady=(16, 8))

        NAV_DEFS = [
            ("master",      "⚙",  "Master & Export", True),
            ("rkm",         "🖼", "RKM Logo",     False),
            ("club",        "🏛", "Club Logo",    False),
            ("qr",          "📱", "QR Code",      False),
            ("copyright",   "©",  "Copyright Info",  False),
            ("custom_text", "T",  "Custom Text",     False),
        ]
        for key, icon, label, always in NAV_DEFS:
            nav = self._make_nav_btn(key, icon, label)
            self._nav_items[key] = nav
            if always:
                nav["frame"].pack(fill=tk.X)

    def _make_nav_btn(self, key, icon, label_text):
        C   = self.C
        NBG = C["bg_sidebar"]

        outer = tk.Frame(self.sidebar, bg=NBG)
        accent_bar = tk.Frame(outer, width=3, bg=NBG)
        accent_bar.pack(side=tk.LEFT, fill=tk.Y)

        inner = tk.Frame(outer, bg=NBG, cursor="hand2")
        inner.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=9, padx=8)

        icon_lbl = tk.Label(inner, text=icon,
                            bg=NBG, fg=C["fg_dim"],
                            font=("Segoe UI", 13))
        icon_lbl.pack(side=tk.LEFT, padx=(2, 7))

        text_lbl = tk.Label(inner, text=label_text,
                            bg=NBG, fg=C["fg_dim"],
                            font=("Segoe UI", 9))
        text_lbl.pack(side=tk.LEFT)

        all_w = [outer, accent_bar, inner, icon_lbl, text_lbl]

        def on_enter(e):
            if self.active_tab != key:
                for w in all_w:
                    w.config(bg=C["bg_hover"])

        def on_leave(e):
            if self.active_tab != key:
                for w in all_w:
                    w.config(bg=NBG)
                accent_bar.config(bg=NBG)

        def on_click(e):
            self._switch_tab(key)

        for w in all_w:
            w.bind("<Enter>",    on_enter)
            w.bind("<Leave>",    on_leave)
            w.bind("<Button-1>", on_click)

        return {"frame": outer, "accent": accent_bar,
                "inner": inner, "icon": icon_lbl, "text": text_lbl}

    def _switch_tab(self, key):
        C   = self.C
        NBG = C["bg_sidebar"]
        self.active_tab = key

        for k, nav in self._nav_items.items():
            if k == key:
                nav["accent"].config(bg=C["accent"])
                for w in [nav["frame"], nav["inner"], nav["icon"], nav["text"]]:
                    w.config(bg=C["bg_active"])
                nav["icon"].config(fg=C["accent"])
                nav["text"].config(fg=C["white"])
            else:
                nav["accent"].config(bg=NBG)
                for w in [nav["frame"], nav["inner"], nav["icon"], nav["text"]]:
                    w.config(bg=NBG)
                nav["icon"].config(fg=C["fg_dim"])
                nav["text"].config(fg=C["fg_dim"])

        for k, panel in self._panels.items():
            if k == key:
                panel.pack(fill=tk.BOTH, expand=True)
            else:
                panel.pack_forget()

        key_to_elem = {
            "rkm": "rkm", "club": "club", "qr": "qr",
            "copyright": "copyright", "custom_text": "custom_text",
            "master": None,
        }
        self.selected_element = key_to_elem.get(key, None)
        self.update_preview()

    # =========================================================================
    #  Control Panel Builders & Helper Utilities
    # =========================================================================

    def _build_all_panels(self):
        self._panels["master"]      = self._build_master_panel()
        self._panels["rkm"]         = self._build_logo_panel("rkm")
        self._panels["club"]        = self._build_logo_panel("club")
        self._panels["qr"]          = self._build_logo_panel("qr")
        self._panels["copyright"]   = self._build_copyright_panel()
        self._panels["custom_text"] = self._build_custom_text_panel()

    def _section_hdr(self, parent, title):
        """Teal ALL-CAPS section header with divider line."""
        C = self.C
        f = tk.Frame(parent, bg=C["bg_panel"])
        f.pack(fill=tk.X, padx=14, pady=(18, 6))
        tk.Label(f, text=title.upper(),
                 bg=C["bg_panel"], fg=C["fg_label"],
                 font=("Segoe UI", 7, "bold")).pack(side=tk.LEFT)
        tk.Frame(f, bg=C["sep"], height=1).pack(
            side=tk.LEFT, fill=tk.X, expand=True,
            padx=(8, 0), pady=5)

    def _card(self, parent, padx=14, pady_b=4, inner_pad=12):
        """Card container frame."""
        C = self.C
        f = tk.Frame(parent, bg=C["bg_card"], padx=inner_pad, pady=inner_pad)
        f.pack(fill=tk.X, padx=padx, pady=(0, pady_b))
        return f

    def _make_slider_row(self, parent, row, label_text,
                         variable, from_, to, command, fmt="pct"):
        """Label + Slider + Live Value Text in a 3-column layout with Blender-style double-click editing."""
        C  = self.C
        BG = C["bg_card"]

        tk.Label(parent, text=label_text,
                 bg=BG, fg=C["fg_main"],
                 font=("Segoe UI", 8), anchor="w").grid(
            row=row, column=0, sticky="w", padx=(0, 6), pady=3)

        slider = ttk.Scale(parent, from_=from_, to=to,
                           variable=variable, command=command)
        slider.grid(row=row, column=1, sticky="ew", pady=3)
        self._attach_tooltip(slider)

        val_lbl = tk.Label(parent, text="",
                           bg=BG, fg=C["accent"],
                           font=("Segoe UI", 8, "bold"),
                           width=7, anchor="e", cursor="hand2")
        val_lbl.grid(row=row, column=2, sticky="e", padx=(4, 0), pady=3)

        def _format_val(v):
            if fmt == "pct":
                pct_val = v * 100.0
                if to <= 0.05:
                    return f"{pct_val:.1f}%"
                if abs(pct_val - round(pct_val)) < 0.05:
                    return f"{round(pct_val):.0f}%"
                return f"{pct_val:.1f}%"
            elif fmt == "deg":
                return f"{int(v)}°"
            else:
                return f"{v:.3f}"

        def _upd(*_):
            try:
                v = variable.get()
                val_lbl.config(text=_format_val(v))
            except Exception:
                pass

        variable.trace_add("write", _upd)
        _upd()

        active_entry = [None]

        def _open_inline_entry(event=None):
            if active_entry[0] is not None:
                return

            try:
                curr_v = variable.get()
            except Exception:
                curr_v = from_

            if fmt == "pct":
                initial_txt = f"{curr_v * 100.0:.2f}".rstrip('0').rstrip('.')
            elif fmt == "deg":
                initial_txt = str(int(curr_v))
            else:
                initial_txt = f"{curr_v:.3f}".rstrip('0').rstrip('.')

            entry = tk.Entry(
                parent, bg=C["bg_main"], fg=C["white"],
                insertbackground=C["white"], relief="solid", bd=1,
                font=("Segoe UI", 8, "bold"), justify="right", width=7
            )
            active_entry[0] = entry
            val_lbl.grid_remove()
            entry.grid(row=row, column=2, sticky="e", padx=(4, 0), pady=2)
            entry.insert(0, initial_txt)
            entry.select_range(0, tk.END)
            entry.focus_set()

            def _commit(evt=None):
                if active_entry[0] is None:
                    return
                raw = entry.get().strip()
                if raw:
                    try:
                        is_pct = False
                        if raw.endswith("%"):
                            raw = raw[:-1].strip()
                            is_pct = True
                        elif raw.endswith("°"):
                            raw = raw[:-1].strip()

                        val = float(raw)
                        if fmt == "pct":
                            max_bound = max(from_, to)
                            if is_pct or val > max_bound:
                                val = val / 100.0

                        val = max(min(from_, to), min(max(from_, to), val))
                        if isinstance(variable, tk.IntVar):
                            variable.set(int(round(val)))
                        else:
                            variable.set(val)
                        if command:
                            command()
                    except ValueError:
                        pass
                _close()

            def _cancel(evt=None):
                _close()

            def _close():
                if active_entry[0] is not None:
                    try:
                        active_entry[0].destroy()
                    except Exception:
                        pass
                    active_entry[0] = None
                    val_lbl.grid()

            entry.bind("<Return>", _commit)
            entry.bind("<KP_Enter>", _commit)
            entry.bind("<Escape>", _cancel)
            entry.bind("<FocusOut>", _commit)

        val_lbl.bind("<Double-Button-1>", _open_inline_entry)
        slider.bind("<Double-Button-1>", _open_inline_entry)
        slider.bind("<Return>", _open_inline_entry)
        slider.bind("<KP_Enter>", _open_inline_entry)
        slider._open_inline_entry = _open_inline_entry

        return slider

    def _accent_btn(self, parent, text, command,
                    bg=None, hov=None, fg="#FFFFFF", ipady=6):
        """Polished button with hover color animation."""
        C   = self.C
        bg  = bg  or C["accent"]
        hov = hov or C["accent_lit"]
        btn = tk.Button(
            parent, text=text, command=command,
            bg=bg, fg=fg,
            activebackground=hov, activeforeground=fg,
            font=("Segoe UI", 9, "bold"),
            relief="flat", bd=0, cursor="hand2",
            padx=10, pady=ipady)
        btn.bind("<Enter>", lambda e: btn.config(bg=hov))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg))
        return btn

    def _font_menu(self, parent, var):
        """Dropdown font selector menu."""
        C  = self.C
        mb = ttk.Menubutton(parent, textvariable=var, width=22)
        menu = tk.Menu(mb, tearoff=0,
                       bg=C["bg_card"], fg=C["white"],
                       activebackground=C["accent"],
                       activeforeground=C["white"])
        mb["menu"] = menu
        for fn in FONT_LIST:
            menu.add_radiobutton(
                label=fn, variable=var, value=fn,
                font=(fn, 10), command=self._on_control_change)
        mb.pack(fill=tk.X)
        return mb

    # -- Master Panel Implementation -------------------------------------------

    def _build_master_panel(self):
        C = self.C
        panel = tk.Frame(self._ctrl_inner, bg=C["bg_panel"])

        self._section_hdr(panel, "Workspace")
        ws = self._card(panel)
        btn_row = tk.Frame(ws, bg=C["bg_card"])
        btn_row.pack(fill=tk.X, pady=(0, 10))

        self._accent_btn(btn_row, "📁  Change Source",
                         self.show_startup_dialog,
                         bg="#232323", hov="#2E2E2E",
                         fg=C["fg_main"]).pack(side=tk.LEFT)

        self.btn_custom_img = self._accent_btn(
            btn_row, "🖼  Custom Preview",
            self.select_custom_preview,
            bg="#232323", hov="#2E2E2E", fg=C["fg_main"])
        self.btn_custom_img.pack(side=tk.LEFT, padx=(8, 0))
        self.btn_custom_img.config(state="disabled")

        self.lbl_folder = tk.Label(
            ws, text="No workspace loaded",
            bg=C["bg_card"], fg=C["fg_dim"],
            font=("Segoe UI", 8), wraplength=260, justify="left")
        self.lbl_folder.pack(anchor="w")

        self._section_hdr(panel, "Global Settings")
        g = self._card(panel)
        g.columnconfigure(1, weight=1)
        self._make_slider_row(g, 0, "Border Width",
                              self.border_scale_var, 0.0, 0.025,
                              self._on_control_change)

        self._section_hdr(panel, "Watermark Elements")
        tog = self._card(panel)
        TOGGLES = [
            ("🖼  RKM Logo",         self.rkm_enable),
            ("🏛  Photo Club Logo",  self.club_enable),
            ("📱  QR Code",          self.qr_enable),
            ("©  Copyright Info",       self.copyright_enable),
            ("T  Custom Text",              self.custom_text_enable),
        ]
        for txt, var in TOGGLES:
            row = tk.Frame(tog, bg=C["bg_card"])
            row.pack(fill=tk.X, pady=3)
            ttk.Checkbutton(row, text=txt, variable=var,
                            command=self._update_tabs).pack(anchor="w")

        self._section_hdr(panel, "Export")
        exp = tk.Frame(panel, bg=C["bg_panel"], padx=14, pady=4)
        exp.pack(fill=tk.X, padx=14, pady=(0, 20))
        self.btn_process = self._accent_btn(
            exp, "Process All Photos",
            self.process_batch,
            bg=C["accent_grn"], hov=C["accent_grn_lit"],
            ipady=8)
        self.btn_process.pack(fill=tk.X)
        self.btn_process.config(state="disabled")

        return panel

    # -- Logo Panel Implementation (RKM, Club, QR) ----------------------------

    def _build_logo_panel(self, key):
        C = self.C
        panel = tk.Frame(self._ctrl_inner, bg=C["bg_panel"])

        META = {
            "rkm":  ("RKM Logo",  self.rkm_opacity_var,  self.rkm_scale_var,  self.rkm_padx_var,  self.rkm_pady_var),
            "club": ("Club Logo", self.club_opacity_var, self.club_scale_var, self.club_padx_var, self.club_pady_var),
            "qr":   ("QR Code",   self.qr_opacity_var,   self.qr_scale_var,   self.qr_padx_var,   self.qr_pady_var),
        }
        title, opa, scale, padx, pady = META[key]

        # Blender-style Draggable Numeric Position Fields
        self._section_hdr(panel, f"{title}  –  Position")
        pc = self._card(panel)
        pos_grid = tk.Frame(pc, bg=C["bg_card"])
        pos_grid.pack(fill=tk.X)
        pos_grid.columnconfigure(0, weight=1)
        pos_grid.columnconfigure(1, weight=1)

        ScrubbableNumberField(
            pos_grid, "↔ Pos X", padx, from_=-0.75, to=0.75,
            step=0.005, fmt="pct", command=self._on_control_change,
            colors=C, width=125, height=26
        ).grid(row=0, column=0, sticky="ew", padx=(0, 4))

        ScrubbableNumberField(
            pos_grid, "↕ Pos Y", pady, from_=-0.75, to=0.75,
            step=0.005, fmt="pct", command=self._on_control_change,
            colors=C, width=125, height=26
        ).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        tk.Label(pc, text="Drag fields to scrub  ·  Drag on canvas to reposition",
                 bg=C["bg_card"], fg=C["fg_dim"],
                 font=("Segoe UI", 7)).pack(anchor="w", pady=(6, 0))

        self._section_hdr(panel, f"{title}  –  Appearance")
        ac = self._card(panel)
        ac.columnconfigure(1, weight=1)
        self._make_slider_row(ac, 0, "Opacity",    opa,   0.1,  1.0,  self._on_control_change)
        self._make_slider_row(ac, 1, "Logo Scale", scale, 0.04, 0.25, self._on_control_change)

        if key == "rkm":
            self._section_hdr(panel, "RKM Logo  –  Options")
            oc = self._card(panel)
            ttk.Checkbutton(oc, text="Use Greyscale (B&W) version",
                            variable=self.rkm_greyscale_var,
                            command=self._on_control_change).pack(anchor="w")

        return panel

    # -- Copyright Panel Implementation ----------------------------------------

    def _build_copyright_panel(self):
        C = self.C
        panel = tk.Frame(self._ctrl_inner, bg=C["bg_panel"])

        self._section_hdr(panel, "Copyright  –  Position")
        pc = self._card(panel)
        pos_grid = tk.Frame(pc, bg=C["bg_card"])
        pos_grid.pack(fill=tk.X)
        pos_grid.columnconfigure(0, weight=1)
        pos_grid.columnconfigure(1, weight=1)

        ScrubbableNumberField(
            pos_grid, "↔ Pos X", self.copyright_padx_var, from_=-0.75, to=0.75,
            step=0.005, fmt="pct", command=self._on_control_change,
            colors=C, width=125, height=26
        ).grid(row=0, column=0, sticky="ew", padx=(0, 4))

        ScrubbableNumberField(
            pos_grid, "↕ Pos Y", self.copyright_pady_var, from_=-0.75, to=0.75,
            step=0.005, fmt="pct", command=self._on_control_change,
            colors=C, width=125, height=26
        ).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        tk.Label(pc, text="Drag fields to scrub  ·  Drag on canvas to reposition",
                 bg=C["bg_card"], fg=C["fg_dim"],
                 font=("Segoe UI", 7)).pack(anchor="w", pady=(6, 0))

        self._section_hdr(panel, "Copyright  –  Appearance")
        ac = self._card(panel)
        ac.columnconfigure(1, weight=1)
        self._make_slider_row(ac, 0, "Opacity",   self.copyright_opacity_var, 0.1,  1.0,  self._on_control_change)
        self._make_slider_row(ac, 1, "Text Size", self.copyright_size_var,    0.01, 0.06, self._on_control_change)

        self._section_hdr(panel, "Copyright  –  Font")
        fc = self._card(panel)
        tk.Label(fc, text="Font Family", bg=C["bg_card"], fg=C["fg_dim"],
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 5))
        self.cb_copyright_font = self._font_menu(fc, self.copyright_font_var)

        self._section_hdr(panel, "Copyright  –  Actions")
        acts = self._card(panel)
        action_row = tk.Frame(acts, bg=C["bg_card"])
        action_row.pack(fill=tk.X, pady=(0, 8))

        self._accent_btn(action_row, "↺  Rotate 90°", self._rotate_copyright,
                        bg="#232323", hov="#2E2E2E",
                        fg=C["fg_main"]).pack(side=tk.LEFT)

        ttk.Checkbutton(action_row, text="Add Background Box",
                        variable=self.copyright_bg_enable,
                        command=self._toggle_bg_sliders).pack(side=tk.LEFT, padx=(12, 0))

        self._section_hdr(panel, "Copyright  –  Background")
        bg_c = self._card(panel, pady_b=6)
        bg_c.columnconfigure(1, weight=1)
        self.scale_bg_op = self._make_slider_row(bg_c, 0, "BG Opacity",
                                                  self.copyright_bg_op_var,  0.1, 1.0,  self._on_control_change)
        self.scale_bg_px = self._make_slider_row(bg_c, 1, "BG Width X",
                                                  self.copyright_bg_padx_var, 0.0, 0.03, self._on_control_change)
        self.scale_bg_py = self._make_slider_row(bg_c, 2, "BG Height Y",
                                                  self.copyright_bg_pady_var, 0.0, 0.03, self._on_control_change)

        self._section_hdr(panel, "Copyright  –  Content")
        cc = self._card(panel, pady_b=20)
        tk.Label(cc, text="Text content", bg=C["bg_card"], fg=C["fg_dim"],
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 5))
        entry_c = tk.Entry(cc, textvariable=self.copyright_val,
                           bg=C["bg_main"], fg=C["white"],
                           insertbackground=C["white"],
                           relief="flat", font=("Segoe UI", 9))
        entry_c.pack(fill=tk.X, ipady=6)
        entry_c.bind("<KeyRelease>", self._on_control_change)

        self._toggle_bg_sliders()
        return panel

    # -- Custom Text Panel Implementation --------------------------------------

    def _build_custom_text_panel(self):
        C = self.C
        panel = tk.Frame(self._ctrl_inner, bg=C["bg_panel"])

        self._section_hdr(panel, "Custom Text  –  Position")
        pc = self._card(panel)
        pos_grid = tk.Frame(pc, bg=C["bg_card"])
        pos_grid.pack(fill=tk.X)
        pos_grid.columnconfigure(0, weight=1)
        pos_grid.columnconfigure(1, weight=1)

        ScrubbableNumberField(
            pos_grid, "↔ Pos X", self.custom_text_padx_var, from_=-0.75, to=0.75,
            step=0.005, fmt="pct", command=self._on_control_change,
            colors=C, width=125, height=26
        ).grid(row=0, column=0, sticky="ew", padx=(0, 4))

        ScrubbableNumberField(
            pos_grid, "↕ Pos Y", self.custom_text_pady_var, from_=-0.75, to=0.75,
            step=0.005, fmt="pct", command=self._on_control_change,
            colors=C, width=125, height=26
        ).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        tk.Label(pc, text="Drag fields to scrub  ·  Drag on canvas to reposition",
                 bg=C["bg_card"], fg=C["fg_dim"],
                 font=("Segoe UI", 7)).pack(anchor="w", pady=(6, 0))

        self._section_hdr(panel, "Custom Text  –  Appearance")
        ac = self._card(panel)
        ac.columnconfigure(1, weight=1)
        self._make_slider_row(ac, 0, "Opacity",   self.custom_text_opacity_var, 0.1, 1.0,  self._on_control_change)
        self._make_slider_row(ac, 1, "Text Size", self.custom_text_size_var,    0.01, 0.06, self._on_control_change)
        self._make_slider_row(ac, 2, "Rotation",  self.custom_text_rot_var,     0,   360,  self._on_control_change, fmt="deg")

        self._section_hdr(panel, "Custom Text  –  Font")
        fc = self._card(panel)
        tk.Label(fc, text="Font Family", bg=C["bg_card"], fg=C["fg_dim"],
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 5))
        self.cb_custom_font = self._font_menu(fc, self.custom_text_font_var)

        self._section_hdr(panel, "Custom Text  –  Content")
        cc = self._card(panel, pady_b=20)
        tk.Label(cc, text="Text content", bg=C["bg_card"], fg=C["fg_dim"],
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 5))
        entry_ct = tk.Entry(cc, textvariable=self.custom_text_val,
                            bg=C["white"], fg=C["bg_deep"],
                            insertbackground=C["bg_deep"],
                            relief="flat", font=("Segoe UI", 9))
        entry_ct.pack(fill=tk.X, ipady=6)
        entry_ct.bind("<KeyRelease>", self._on_control_change)

        return panel

    # =========================================================================
    #  Modern Frameless Splash / Startup Dialog
    # =========================================================================

    def show_startup_dialog(self):
        self.root.withdraw()

        self.startup_win = tk.Toplevel(self.root)
        self.startup_win.overrideredirect(True)
        WIN_W, WIN_H = 760, 540
        self.startup_win.geometry(f"{WIN_W}x{WIN_H}")
        self.startup_win.configure(bg="#141414",
                                   highlightbackground="#0078D4",
                                   highlightthickness=1)

        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.startup_win.geometry(
            f"+{(sw - WIN_W) // 2}+{(sh - WIN_H) // 2}")

        _force_taskbar_icon(self.startup_win)

        # Window Title bar with drag support
        tbar = tk.Frame(self.startup_win, bg="#0A0A0A", height=36)
        tbar.pack(fill=tk.X)
        tbar.pack_propagate(False)

        def _drag_start(e):
            self.startup_win._dx = e.x
            self.startup_win._dy = e.y

        def _drag_move(e):
            x = self.startup_win.winfo_x() + (e.x - self.startup_win._dx)
            y = self.startup_win.winfo_y() + (e.y - self.startup_win._dy)
            self.startup_win.geometry(f"+{x}+{y}")

        tbar.bind("<ButtonPress-1>", _drag_start)
        tbar.bind("<B1-Motion>",     _drag_move)

        tk.Label(tbar, text="  📷  Vidyamandira Photo Watermarker",
                 bg="#0A0A0A", fg="#AAAAAA",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, pady=8)

        cls_btn = tk.Button(tbar, text="✕",
                            bg="#0A0A0A", fg="#666666",
                            font=("Segoe UI", 11), relief="flat", bd=0,
                            activebackground="#E81123",
                            activeforeground="#FFFFFF",
                            cursor="hand2", command=self.close_app, padx=12)
        cls_btn.pack(side=tk.RIGHT, fill=tk.Y)
        cls_btn.bind("<Enter>", lambda e: cls_btn.config(fg="#FFFFFF", bg="#E81123"))
        cls_btn.bind("<Leave>", lambda e: cls_btn.config(fg="#666666", bg="#0A0A0A"))

        # Hero Header Banner
        hdr = tk.Frame(self.startup_win, bg="#141414")
        hdr.pack(fill=tk.X, pady=(18, 4))
        tk.Label(hdr, text="Vidyamandira Photography Club",
                 bg="#141414", fg="#FFFFFF",
                 font=("Segoe UI", 16, "bold")).pack()
        tk.Label(hdr, text="Watermark & Border Tool  ·  v3.6.0",
                 bg="#141414", fg="#0078D4",
                 font=("Segoe UI", 9)).pack(pady=(2, 0))

        tk.Frame(self.startup_win, bg="#0078D4", height=1).pack(
            fill=tk.X, padx=40, pady=(12, 18))

        tk.Label(self.startup_win, text="How would you like to get started?",
                 bg="#141414", fg="#666666",
                 font=("Segoe UI", 8)).pack(pady=(0, 12))

        # Mode Selection Cards
        cards_frame = tk.Frame(self.startup_win, bg="#141414")
        cards_frame.pack(expand=True)

        CARD_BG     = "#1A1A1A"
        CARD_HOV    = "#222222"
        BORDER_NORM = "#2E2E2E"
        BORDER_HOV  = "#0078D4"

        def make_card(parent, icon, title, subtitle, cmd):
            outer = tk.Frame(parent, bg=BORDER_NORM, padx=1, pady=1)
            inner = tk.Frame(outer, bg=CARD_BG, width=178, height=132, cursor="hand2")
            inner.pack_propagate(False)
            inner.pack()
            icon_l  = tk.Label(inner, text=icon,     bg=CARD_BG, fg="#0078D4",
                                font=("Segoe UI", 28))
            title_l = tk.Label(inner, text=title,    bg=CARD_BG, fg="#FFFFFF",
                                font=("Segoe UI", 11, "bold"))
            sub_l   = tk.Label(inner, text=subtitle, bg=CARD_BG, fg="#666666",
                                font=("Segoe UI", 7), wraplength=158)
            icon_l.pack(pady=(14, 2))
            title_l.pack()
            sub_l.pack(pady=(2, 0))

            all_w = [outer, inner, icon_l, title_l, sub_l]

            def on_enter(e):
                outer.config(bg=BORDER_HOV)
                for w in [inner, icon_l, title_l, sub_l]:
                    w.config(bg=CARD_HOV)

            def on_leave(e):
                outer.config(bg=BORDER_NORM)
                for w in [inner, icon_l, title_l, sub_l]:
                    w.config(bg=CARD_BG)

            for w in all_w:
                w.bind("<Enter>",    on_enter)
                w.bind("<Leave>",    on_leave)
                w.bind("<Button-1>", lambda e, c=cmd: c())

            return outer

        make_card(cards_frame, "🗂", "Batch Folder",
                  "Watermark all images\nin a directory at once",
                  self.startup_select_folder).pack(side=tk.LEFT, padx=(0, 16))

        make_card(cards_frame, "🖼", "Single Image",
                  "Edit and export one\nimage with full preview",
                  self.startup_select_image).pack(side=tk.LEFT)

    def on_closing(self):
        """Clean shutdown handler to prevent zombie processes."""
        if self._preview_timer is not None:
            try:
                self.root.after_cancel(self._preview_timer)
            except Exception:
                pass
            self._preview_timer = None

        if hasattr(self, 'startup_win') and self.startup_win:
            try:
                if self.startup_win.winfo_exists():
                    self.startup_win.destroy()
            except Exception:
                pass

        try:
            self.root.quit()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

        os._exit(0)

    def close_app(self):
        self.on_closing()

    def startup_select_folder(self):
        folder = filedialog.askdirectory(
            title="Select Photo Directory", parent=self.startup_win)
        if folder:
            if hasattr(self, 'startup_win') and self.startup_win:
                self.startup_win.destroy()
                self.startup_win = None
            self.root.deiconify()
            self.root.state('normal')
            self.root.lift()
            self.root.focus_force()
            self._load_folder(folder)

    def startup_select_image(self):
        file_path = filedialog.askopenfilename(
            title="Select Image",
            parent=self.startup_win,
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.webp *.bmp")])
        if file_path:
            if hasattr(self, 'startup_win') and self.startup_win:
                self.startup_win.destroy()
                self.startup_win = None
            self.root.deiconify()
            self.root.state('normal')
            self.root.lift()
            self.root.focus_force()
            self._load_single_image(file_path)

    # =========================================================================
    #  File Loading Logic
    # =========================================================================

    def _load_folder(self, folder):
        valid_exts = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')
        files = [os.path.join(folder, f)
                 for f in os.listdir(folder)
                 if f.lower().endswith(valid_exts)]
        if not files:
            messagebox.showwarning(
                "No Images Found",
                "Selected directory contains no supported image formats.")
            self.show_startup_dialog()
            return

        self.selected_folder = folder
        self.all_files = files
        self.is_single_image_mode = False

        label = f"{os.path.basename(folder)}  ({len(files)} images)"
        self.lbl_folder.config(text=label)
        self.lbl_workspace.config(text=label)
        self.status_left.config(text=f"Folder loaded  ·  {len(files)} images")

        self.btn_process.config(state="normal", text="Process All Photos")
        self.btn_custom_img.config(state="normal")

        self.sample_image_path = random.choice(self.all_files)
        self.update_preview()

    def _load_single_image(self, file_path):
        self.all_files = [file_path]
        self.is_single_image_mode = True
        self.single_image_save_folder = ""
        self.selected_folder = os.path.dirname(file_path)

        name = os.path.basename(file_path)
        self.lbl_folder.config(text=f"Image: {name}")
        self.lbl_workspace.config(text=f"Single image: {name}")
        self.status_left.config(text=f"Single-image mode  ·  {name}")

        self.btn_process.config(state="normal", text="💾  Save / Export Image")
        self.btn_custom_img.config(state="disabled")

        self.sample_image_path = file_path
        self.update_preview()

    def select_custom_preview(self):
        file_path = filedialog.askopenfilename(
            title="Select Custom Preview Image",
            initialdir=self.selected_folder,
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.webp *.bmp")])
        if file_path:
            self.sample_image_path = file_path
            self.update_preview()

    # =========================================================================
    #  Tab Visibility Management
    # =========================================================================

    def _update_tabs(self):
        """Show/hide sidebar nav buttons based on element enable toggles."""
        visibility = {
            "rkm":         self.rkm_enable.get(),
            "club":        self.club_enable.get(),
            "qr":          self.qr_enable.get(),
            "copyright":   self.copyright_enable.get(),
            "custom_text": self.custom_text_enable.get(),
        }
        for key, visible in visibility.items():
            nav = self._nav_items.get(key)
            if nav is None:
                continue
            if visible:
                nav["frame"].pack(fill=tk.X)
            else:
                nav["frame"].pack_forget()
                if self.active_tab == key:
                    self._switch_tab("master")

        self._on_control_change()

    def _rotate_copyright(self):
        self.copyright_rot_var.set((self.copyright_rot_var.get() + 90) % 360)
        self._on_control_change()

    def _toggle_bg_sliders(self):
        state = ["!disabled"] if self.copyright_bg_enable.get() else ["disabled"]
        self.scale_bg_op.state(state)
        self.scale_bg_px.state(state)
        self.scale_bg_py.state(state)
        self._on_control_change()

    # =========================================================================
    #  Control Event Handlers
    # =========================================================================

    def _on_control_change(self, *args):
        if self._preview_timer is not None:
            self.root.after_cancel(self._preview_timer)
        self._preview_timer = self.root.after(100, self.update_preview)

    # =========================================================================
    #  Config compilation
    # =========================================================================

    def compile_config(self):
        return {
            "border_scale": self.border_scale_var.get(),
            "rkm": {
                "enabled":     self.rkm_enable.get(),
                "pos":         "Center",
                "opacity":     self.rkm_opacity_var.get(),
                "scale":       self.rkm_scale_var.get(),
                "pad_x_scale": self.rkm_padx_var.get(),
                "pad_y_scale": self.rkm_pady_var.get(),
                "greyscale":   self.rkm_greyscale_var.get(),
                "path":        self.rkm_path,
                "bnw_path":    self.bnw_rkm_path,
            },
            "club": {
                "enabled":     self.club_enable.get(),
                "pos":         "Center",
                "opacity":     self.club_opacity_var.get(),
                "scale":       self.club_scale_var.get(),
                "pad_x_scale": self.club_padx_var.get(),
                "pad_y_scale": self.club_pady_var.get(),
                "path":        self.club_path,
            },
            "qr": {
                "enabled":     self.qr_enable.get(),
                "pos":         "Center",
                "opacity":     self.qr_opacity_var.get(),
                "scale":       self.qr_scale_var.get(),
                "pad_x_scale": self.qr_padx_var.get(),
                "pad_y_scale": self.qr_pady_var.get(),
                "path":        self.qr_path,
            },
            "copyright": {
                "enabled":        self.copyright_enable.get(),
                "pos":            "Center",
                "opacity":        self.copyright_opacity_var.get(),
                "size_scale":     self.copyright_size_var.get(),
                "content":        self.copyright_val.get(),
                "pad_x_scale":    self.copyright_padx_var.get(),
                "pad_y_scale":    self.copyright_pady_var.get(),
                "rotation":       self.copyright_rot_var.get(),
                "font":           self.copyright_font_var.get(),
                "bg_enabled":     self.copyright_bg_enable.get(),
                "bg_opacity":     self.copyright_bg_op_var.get(),
                "bg_pad_x_scale": self.copyright_bg_padx_var.get(),
                "bg_pad_y_scale": self.copyright_bg_pady_var.get(),
            },
            "custom_text": {
                "enabled":     self.custom_text_enable.get(),
                "pos":         "Center",
                "opacity":     self.custom_text_opacity_var.get(),
                "size_scale":  self.custom_text_size_var.get(),
                "content":     self.custom_text_val.get(),
                "pad_x_scale": self.custom_text_padx_var.get(),
                "pad_y_scale": self.custom_text_pady_var.get(),
                "rotation":    self.custom_text_rot_var.get(),
                "font":        self.custom_text_font_var.get(),
            },
        }

    # =========================================================================
    #  Interactive Canvas Selection & Drag-and-Drop
    # =========================================================================

    def select_element(self, key):
        """Select an element; switch sidebar to its tab (or master if None)."""
        self.selected_element = key
        key_to_tab = {
            "rkm": "rkm", "club": "club", "qr": "qr",
            "copyright": "copyright", "custom_text": "custom_text",
        }
        tab = key_to_tab.get(key, "master")
        nav = self._nav_items.get(tab)
        if nav and nav["frame"].winfo_ismapped():
            self._switch_tab(tab)
        else:
            self._switch_tab("master")
        if self.selected_element:
            self.preview_canvas.focus_set()
        self.update_preview()

    def _get_element_vars(self, key):
        elem_map = {
            "rkm":         (self.rkm_padx_var,         self.rkm_pady_var),
            "club":        (self.club_padx_var,        self.club_pady_var),
            "qr":          (self.qr_padx_var,          self.qr_pady_var),
            "copyright":   (self.copyright_padx_var,   self.copyright_pady_var),
            "custom_text": (self.custom_text_padx_var, self.custom_text_pady_var),
        }
        return elem_map.get(key, (None, None))

    def _on_canvas_hover(self, event):
        if self._drag_data and self._drag_data.get("active"):
            return
        cx, cy = event.x, event.y
        over_element = False
        for key in reversed(list(self.display_boxes.keys())):
            x1, y1, x2, y2 = self.display_boxes[key]
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                over_element = True
                break
        self.preview_canvas.config(cursor="fleur" if over_element else "")

    def _on_canvas_press(self, event):
        self.preview_canvas.focus_set()
        cx, cy = event.x, event.y
        clicked = None
        for key in reversed(list(self.display_boxes.keys())):
            x1, y1, x2, y2 = self.display_boxes[key]
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                clicked = key
                break

        if clicked:
            self.select_element(clicked)
            px_var, py_var = self._get_element_vars(clicked)
            if px_var and py_var:
                self._drag_data = {
                    "key": clicked,
                    "start_x": cx,
                    "start_y": cy,
                    "start_pad_x": px_var.get(),
                    "start_pad_y": py_var.get(),
                    "px_var": px_var,
                    "py_var": py_var,
                    "active": True
                }
                self.preview_canvas.config(cursor="fleur")
        else:
            self.select_element(None)
            self._drag_data = None

    def _on_canvas_drag(self, event):
        if not self._drag_data or not self._drag_data.get("active"):
            return

        cx, cy = event.x, event.y
        dx = cx - self._drag_data["start_x"]
        dy = cy - self._drag_data["start_y"]

        scale_factor = self._preview_scale_factor or 1.0
        delta_scale_x = dx / scale_factor
        delta_scale_y = dy / scale_factor

        new_x = self._drag_data["start_pad_x"] + delta_scale_x
        new_y = self._drag_data["start_pad_y"] + delta_scale_y

        min_v, max_v = -0.75, 0.75
        new_x = max(min_v, min(max_v, round(new_x, 4)))
        new_y = max(min_v, min(max_v, round(new_y, 4)))

        self._drag_data["px_var"].set(new_x)
        self._drag_data["py_var"].set(new_y)

        # Real-time fluid preview update during drag
        if self._preview_timer is not None:
            self.root.after_cancel(self._preview_timer)
            self._preview_timer = None
        self.update_preview()

    def _on_canvas_release(self, event):
        if self._drag_data and self._drag_data.get("active"):
            self._drag_data["active"] = False
            self._drag_data = None
            self._on_canvas_hover(event)
            self.update_preview()

    def _bind_canvas_scroll(self, e):
        self.root.bind_all("<MouseWheel>", self._on_canvas_scroll)
        self.root.bind_all("<Button-4>", self._on_canvas_scroll)
        self.root.bind_all("<Button-5>", self._on_canvas_scroll)

    def _unbind_canvas_scroll(self, e):
        self.root.unbind_all("<MouseWheel>")
        self.root.unbind_all("<Button-4>")
        self.root.unbind_all("<Button-5>")

    def _on_canvas_scroll(self, event):
        # Auto-select element under cursor if mouse is hovering over one
        cx, cy = event.x, event.y
        for key in reversed(list(self.display_boxes.keys())):
            x1, y1, x2, y2 = self.display_boxes[key]
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                if self.selected_element != key:
                    self.select_element(key)
                break

        if not self.selected_element:
            return

        if hasattr(event, 'num') and event.num == 4:
            direction = 1
        elif hasattr(event, 'num') and event.num == 5:
            direction = -1
        else:
            direction = 1 if event.delta > 0 else -1

        scale_vars = {
            "rkm":         (self.rkm_scale_var,         0.04, 0.25, 0.005),
            "club":        (self.club_scale_var,        0.04, 0.25, 0.005),
            "qr":          (self.qr_scale_var,          0.04, 0.25, 0.005),
            "copyright":   (self.copyright_size_var,    0.01, 0.06, 0.002),
            "custom_text": (self.custom_text_size_var,  0.01, 0.06, 0.002)
        }

        if self.selected_element in scale_vars:
            var, min_v, max_v, step = scale_vars[self.selected_element]
            new_val = var.get() + (step * direction)
            new_val = max(min_v, min(max_v, new_val))
            var.set(new_val)
            self._on_control_change()

    def _on_arrow_key(self, event):
        """
        Move the currently selected watermark element using keyboard arrow keys.
        NUDGE CONFIGURATION:
        - By default, moves by 2 pixels on the photo per arrow key press.
        - Holding Shift moves by 10 pixels for faster coarse positioning.
        """
        focused = self.root.focus_get()
        if isinstance(focused, (tk.Entry, ttk.Combobox, tk.Text)):
            return

        if not self.selected_element:
            return

        px_var, py_var = self._get_element_vars(self.selected_element)
        if px_var is None or py_var is None:
            return

        # ---------------------------------------------------------------------
        # Nudge Step Settings (Change here to tweak arrow key movement distance):
        # ---------------------------------------------------------------------
        NUDGE_PIXELS_NORMAL = 20.0   # Default arrow nudge (2 px per click)
        NUDGE_PIXELS_PRECISE   = 10.0  # Shift + arrow nudge (10 px per click)
        # ---------------------------------------------------------------------

        is_shift = bool(getattr(event, "state", 0) & 0x0001)
        max_d = getattr(self, "_sample_max_dim", 1000) or 1000
        nudge_px = NUDGE_PIXELS_PRECISE if is_shift else NUDGE_PIXELS_NORMAL
        step = nudge_px / max_d
        min_v, max_v = -0.75, 0.75

        key_raw = event.keysym
        if key_raw in ("Left", "KP_Left"):
            direction = "Left"
        elif key_raw in ("Right", "KP_Right"):
            direction = "Right"
        elif key_raw in ("Up", "KP_Up"):
            direction = "Up"
        elif key_raw in ("Down", "KP_Down"):
            direction = "Down"
        else:
            return

        changed = False

        if direction in ("Left", "Right"):
            curr_x = px_var.get()
            dx = step if direction == "Right" else -step
            new_x = max(min_v, min(max_v, round(curr_x + dx, 5)))
            if new_x != curr_x:
                px_var.set(new_x)
                changed = True

        elif direction in ("Up", "Down"):
            curr_y = py_var.get()
            dy = step if direction == "Down" else -step
            new_y = max(min_v, min(max_v, round(curr_y + dy, 5)))
            if new_y != curr_y:
                py_var.set(new_y)
                changed = True

        if changed:
            self._on_control_change()

        return "break"

    # =========================================================================
    #  Preview Rendering
    # =========================================================================

    def update_preview(self):
        self.preview_canvas.delete("all")
        if not self.sample_image_path or not os.path.exists(self.sample_image_path):
            cw = self.preview_canvas.winfo_width()  or 600
            ch = self.preview_canvas.winfo_height() or 500
            self.preview_canvas.create_text(
                cw // 2, ch // 2,
                text="Select a folder or image to generate preview",
                fill=self.C["fg_dim"], font=("Segoe UI", 10))
            return

        config = self.compile_config()
        rendered_img, element_boxes = apply_watermark_and_border(
            self.sample_image_path, config)

        cw = self.preview_canvas.winfo_width()
        ch = self.preview_canvas.winfo_height()
        if cw < 50 or ch < 50:
            cw, ch = 600, 500

        img_w, img_h = rendered_img.size
        scale  = min(cw / img_w, ch / img_h)
        disp_w = max(1, int(img_w * scale))
        disp_h = max(1, int(img_h * scale))
        offset_x = (cw - disp_w) // 2
        offset_y = (ch - disp_h) // 2

        try:
            orig_raw = Image.open(self.sample_image_path)
            orig_w, orig_h = orig_raw.size
            max_dim = int((orig_w * orig_h) ** 0.5)
            self._sample_max_dim = max_dim
            self._preview_scale_factor = max_dim * scale
        except Exception:
            self._sample_max_dim = img_w
            self._preview_scale_factor = img_w * scale

        display_img = rendered_img.resize((disp_w, disp_h), Image.Resampling.LANCZOS)
        self.preview_photo_ref = ImageTk.PhotoImage(display_img)
        self.preview_canvas.create_image(offset_x, offset_y,
                                         anchor="nw", image=self.preview_photo_ref)

        self.display_boxes = {}
        for key, (bx, by, bw, bh) in element_boxes.items():
            self.display_boxes[key] = (
                offset_x + int(bx * scale),
                offset_y + int(by * scale),
                offset_x + int((bx + bw) * scale),
                offset_y + int((by + bh) * scale),
            )

        if self.selected_element and self.selected_element in self.display_boxes:
            x1, y1, x2, y2 = self.display_boxes[self.selected_element]
            self.preview_canvas.create_rectangle(
                x1 - 2, y1 - 2, x2 + 2, y2 + 2,
                outline=self.C["accent"], width=2, dash=(4, 4))
            self.lbl_preview_hint.config(
                text="Selected  ·  Drag on canvas  ·  Arrow keys (↑ ↓ ← →) to nudge  ·  Scroll to scale  ·  Esc to deselect",
                fg=self.C["accent"])
        else:
            self.lbl_preview_hint.config(
                text="Click and drag any watermark element on canvas to reposition",
                fg=self.C["fg_dim"])

    # =========================================================================
    #  Batch & Single Image Export Execution
    # =========================================================================

    def process_batch(self):
        if not self.all_files:
            return

        if self.is_single_image_mode:
            save_dir = filedialog.askdirectory(title="Select Folder to Save the Image")
            if not save_dir:
                return
            self.single_image_save_folder = save_dir
            output_folder = save_dir
        else:
            parent_dir  = os.path.dirname(self.selected_folder)
            folder_name = os.path.basename(self.selected_folder)
            output_folder = os.path.join(parent_dir, f"{folder_name}_watermarked")

        os.makedirs(output_folder, exist_ok=True)

        prog_win = tk.Toplevel(self.root)
        prog_win.title("Processing...")
        prog_win.geometry("440x180")
        prog_win.configure(bg=self.C["bg_card"])
        prog_win.resizable(False, False)
        prog_win.transient(self.root)

        tk.Frame(prog_win, bg=self.C["accent_grn"], height=3).pack(fill=tk.X)
        tk.Label(prog_win, text="Exporting watermarked images",
                 bg=self.C["bg_card"], fg=self.C["white"],
                 font=("Segoe UI", 11, "bold")).pack(pady=(14, 2))

        lbl_status = tk.Label(prog_win, text="Starting...",
                              bg=self.C["bg_card"], fg=self.C["fg_dim"],
                              font=("Segoe UI", 8))
        lbl_status.pack()

        lbl_eta = tk.Label(prog_win, text="Calculating time...",
                           bg=self.C["bg_card"], fg=self.C["fg_dim"],
                           font=("Segoe UI", 8))
        lbl_eta.pack(pady=(0, 6))

        pbar = ttk.Progressbar(prog_win, length=380, mode="determinate",
                               maximum=len(self.all_files),
                               style="Green.Horizontal.TProgressbar")
        pbar.pack(pady=5)

        config = self.compile_config()
        success_count = 0
        start_time = time.time()

        for idx, file_path in enumerate(self.all_files, start=1):
            fname = os.path.basename(file_path)
            lbl_status.config(text=f"({idx}/{len(self.all_files)})  {fname}")

            if idx > 1:
                elapsed  = time.time() - start_time
                avg_time = elapsed / (idx - 1)
                remaining = len(self.all_files) - (idx - 1)
                eta_secs = int(avg_time * remaining)
                eta_str = (f"{eta_secs}s remaining" if eta_secs < 60
                           else f"{eta_secs // 60}m {eta_secs % 60}s remaining")
                lbl_eta.config(text=eta_str)
            else:
                lbl_eta.config(text="Calculating time...")

            prog_win.update()

            try:
                orig_raw    = Image.open(file_path)
                exif_data   = orig_raw.info.get("exif")
                icc_profile = orig_raw.info.get("icc_profile")

                out_img, _ = apply_watermark_and_border(file_path, config)
                out_path = os.path.join(output_folder, fname)

                save_kwargs = {"quality": 95}
                if exif_data:    save_kwargs["exif"]        = exif_data
                if icc_profile:  save_kwargs["icc_profile"] = icc_profile

                out_img.save(out_path, **save_kwargs)
                success_count += 1
            except Exception as e:
                print(f"Error processing {fname}: {e}")

            pbar["value"] = idx

        prog_win.destroy()

        # Modern Export Complete Dialog
        done_win = tk.Toplevel(self.root)
        done_win.title("Export Complete")
        done_win.geometry("540x260")
        done_win.configure(bg=self.C["bg_card"])
        done_win.resizable(False, False)
        done_win.transient(self.root)
        done_win.grab_set()

        self.root.update_idletasks()
        rx = self.root.winfo_x() + (self.root.winfo_width() - 540) // 2
        ry = self.root.winfo_y() + (self.root.winfo_height() - 260) // 2
        done_win.geometry(f"+{max(0, rx)}+{max(0, ry)}")

        # Green accent top border
        tk.Frame(done_win, bg=self.C["accent_grn"], height=3).pack(fill=tk.X)

        tk.Label(done_win, text="🎉  Export Successful!",
                 bg=self.C["bg_card"], fg=self.C["white"],
                 font=("Segoe UI", 13, "bold")).pack(pady=(16, 4))

        tk.Label(done_win,
                 text=f"Successfully exported {success_count} image(s) to:",
                 bg=self.C["bg_card"], fg=self.C["fg_main"],
                 font=("Segoe UI", 9)).pack()

        path_lbl = tk.Label(done_win, text=output_folder,
                            bg=self.C["bg_main"], fg=self.C["fg_label"],
                            font=("Segoe UI", 8), wraplength=490,
                            padx=10, pady=6, relief="solid", bd=1)
        path_lbl.pack(padx=20, pady=(8, 16), fill=tk.X)

        btn_row = tk.Frame(done_win, bg=self.C["bg_card"])
        btn_row.pack(pady=4)

        def _open_folder():
            try:
                os.startfile(output_folder)
            except Exception as err:
                messagebox.showerror("Error", f"Could not open directory: {err}", parent=done_win)

        def _open_google_photos():
            try:
                os.startfile(output_folder)
            except Exception:
                pass
            webbrowser.open("https://photos.google.com/albums")

        self._accent_btn(
            btn_row, "📁  Open Output Folder", _open_folder,
            bg="#2A2A2A", hov="#383838", fg=self.C["white"], ipady=6
        ).pack(side=tk.LEFT, padx=6)

        self._accent_btn(
            btn_row, "☁️  Upload to Google Photos", _open_google_photos,
            bg="#1A73E8", hov="#2B82F6", fg="#FFFFFF", ipady=6
        ).pack(side=tk.LEFT, padx=6)

        self._accent_btn(
            btn_row, "✓  Done", done_win.destroy,
            bg=self.C["accent_grn"], hov=self.C["accent_grn_lit"],
            fg="#FFFFFF", ipady=6
        ).pack(side=tk.LEFT, padx=6)


if __name__ == "__main__":
    root = tk.Tk()
    app = WatermarkApp(root)

    def on_resize(event):
        if event.widget == root and app.sample_image_path and root.winfo_ismapped():
            app._on_control_change()

    root.bind("<Configure>", on_resize)
    try:
        root.mainloop()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        os._exit(0)