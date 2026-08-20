import ctypes
import datetime
import os
import random
import sys
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageDraw, ImageFont, ImageTk

VERSION = "3.5.0"

# Set explicit Windows AppUserModelID so taskbar groups and shows the icon properly
if sys.platform.startswith("win"):
    try:
        myappid = "rkmvpc.watermarker.desktop.3.5.0"
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


POSITIONS = [
    "Top Left",
    "Top Right",
    "Bottom Left",
    "Bottom Right",
    "Center"
]

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
    """Calculates placement coordinates relative to the inner image region offset by the frame border."""
    if pos_name == "Top Left":
        x = offset_x + pad_x
        y = offset_y + pad_y
    elif pos_name == "Top Right":
        x = offset_x + inner_w - element_w - pad_x
        y = offset_y + pad_y
    elif pos_name == "Bottom Left":
        x = offset_x + pad_x
        y = offset_y + inner_h - element_h - pad_y
    elif pos_name == "Bottom Right":
        x = offset_x + inner_w - element_w - pad_x
        y = offset_y + inner_h - element_h - pad_y
    elif pos_name == "Center":
        x = offset_x + ((inner_w - element_w) // 2) + pad_x
        y = offset_y + ((inner_h - element_h) // 2) + pad_y
    else:
        x = offset_x + pad_x
        y = offset_y + pad_y
    return x, y


def apply_watermark_and_border(image_path, config):
    orig_img = Image.open(image_path).convert("RGBA")
    orig_w, orig_h = orig_img.size
    max_dim = max(orig_w, orig_h)

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

                pad_x = int(max_dim * item.get("pad_x_scale", 0.01))
                pad_y = int(max_dim * item.get("pad_y_scale", 0.01))

                x, y = get_position_coords(
                    item["pos"], orig_w, orig_h, 
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
            text_cfg["pos"], orig_w, orig_h, 
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


class WatermarkApp:
    # Colour palette
    C = {
        "bg_deep":        "#080808",
        "bg_main":        "#0D0D0D",
        "bg_sidebar":     "#111111",
        "bg_panel":       "#161616",
        "bg_card":        "#1C1C1C",
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
    }

    def __init__(self, root):
        self.root = root
        self.root.title("Vidyamandira Photo Watermarker  v3.5.0")
        self.root.geometry("1220x820")
        self.root.minsize(1000, 660)

        self._preview_timer = None
        self.selected_element = None
        self.display_boxes = {}
        self.active_tab = "master"
        self._nav_items = {}
        self._panels = {}

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

        # Tk variables (identical to demo.py)
        self.border_scale_var = tk.DoubleVar(value=0.02)

        self.rkm_enable        = tk.BooleanVar(value=True)
        self.rkm_pos           = tk.StringVar(value="Top Right")
        self.rkm_opacity_var   = tk.DoubleVar(value=0.6)
        self.rkm_scale_var     = tk.DoubleVar(value=0.12)
        self.rkm_padx_var      = tk.DoubleVar(value=0.01)
        self.rkm_pady_var      = tk.DoubleVar(value=0.01)
        self.rkm_greyscale_var = tk.BooleanVar(value=False)

        self.club_enable      = tk.BooleanVar(value=False)
        self.club_pos         = tk.StringVar(value="Bottom Right")
        self.club_opacity_var = tk.DoubleVar(value=0.6)
        self.club_scale_var   = tk.DoubleVar(value=0.12)
        self.club_padx_var    = tk.DoubleVar(value=0.01)
        self.club_pady_var    = tk.DoubleVar(value=0.01)

        self.qr_enable        = tk.BooleanVar(value=False)
        self.qr_pos           = tk.StringVar(value="Top Left")
        self.qr_opacity_var   = tk.DoubleVar(value=0.6)
        self.qr_scale_var     = tk.DoubleVar(value=0.12)
        self.qr_padx_var      = tk.DoubleVar(value=0.01)
        self.qr_pady_var      = tk.DoubleVar(value=0.01)

        self.copyright_enable      = tk.BooleanVar(value=True)
        self.copyright_pos         = tk.StringVar(value="Bottom Left")
        self.copyright_opacity_var = tk.DoubleVar(value=0.6)
        self.copyright_size_var    = tk.DoubleVar(value=0.025)
        self.copyright_val         = tk.StringVar(value=self.default_text)
        self.copyright_padx_var    = tk.DoubleVar(value=0.0)
        self.copyright_pady_var    = tk.DoubleVar(value=0.0)
        self.copyright_rot_var     = tk.IntVar(value=0)
        self.copyright_font_var    = tk.StringVar(value="Arial")
        self.copyright_bg_enable   = tk.BooleanVar(value=False)
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
        self.root.bind("<Escape>", lambda e: self.select_element(None))
        self.root.bind("<Up>",    self._on_arrow_key)
        self.root.bind("<Down>",  self._on_arrow_key)
        self.root.bind("<Left>",  self._on_arrow_key)
        self.root.bind("<Right>", self._on_arrow_key)
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
        tk.Label(hdr, text=" v3.5.0 ",
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
                 text="Vidyamandira Photography Club  ·  v3.5.0",
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
            # Handle cross-platform scroll directions
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

        self._validate_positions()

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
            phdr, text="Click any watermark element to select it",
            bg=C["bg_main"], fg=C["fg_dim"],
            font=("Segoe UI", 7))
        self.lbl_preview_hint.pack(side=tk.RIGHT)

        canvas_border = tk.Frame(parent, bg=C["sep"], padx=1, pady=1)
        canvas_border.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 12))

        self.preview_canvas = tk.Canvas(
            canvas_border, bg="#060606", highlightthickness=0)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        self.preview_canvas.bind("<Button-1>", self._on_canvas_click)
        self.preview_canvas.bind("<Enter>", self._bind_canvas_scroll)
        self.preview_canvas.bind("<Leave>", self._unbind_canvas_scroll)

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
        """Label + Slider + Live Value Text in a 3-column layout."""
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
                           width=7, anchor="e")
        val_lbl.grid(row=row, column=2, sticky="e", padx=(4, 0), pady=3)

        def _upd(*_):
            v = variable.get()
            if fmt == "pct":
                val_lbl.config(text=f"{v * 100:.0f}%")
            elif fmt == "deg":
                val_lbl.config(text=f"{int(v)}°")
            else:
                val_lbl.config(text=f"{v:.3f}")

        variable.trace_add("write", _upd)
        _upd()
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
                              self.border_scale_var, 0.0, 0.10,
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

    # -- Logo Panel Implementation ---------------------------------------------

    def _build_logo_panel(self, key):
        C = self.C
        panel = tk.Frame(self._ctrl_inner, bg=C["bg_panel"])

        META = {
            "rkm":  ("RKM Logo",  self.rkm_pos,  self.rkm_opacity_var,
                     self.rkm_scale_var,  self.rkm_padx_var,  self.rkm_pady_var),
            "club": ("Club Logo", self.club_pos, self.club_opacity_var,
                     self.club_scale_var, self.club_padx_var, self.club_pady_var),
            "qr":   ("QR Code",   self.qr_pos,   self.qr_opacity_var,
                     self.qr_scale_var,  self.qr_padx_var,  self.qr_pady_var),
        }
        title, pos_var, opa, scale, padx, pady = META[key]

        self._section_hdr(panel, f"{title}  –  Position")
        pc = self._card(panel)
        tk.Label(pc, text="Placement", bg=C["bg_card"], fg=C["fg_dim"],
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 5))
        cb = ttk.Combobox(pc, textvariable=pos_var,
                          values=POSITIONS, state="readonly", width=22)
        cb.pack(fill=tk.X)
        cb.bind("<<ComboboxSelected>>", self._on_position_selected)

        if key == "rkm":   self.cb_rkm  = cb
        elif key == "club": self.cb_club = cb
        elif key == "qr":   self.cb_qr   = cb

        self._section_hdr(panel, f"{title}  –  Appearance")
        ac = self._card(panel)
        ac.columnconfigure(1, weight=1)
        self._make_slider_row(ac, 0, "Opacity",    opa,   0.1,  1.0,  self._on_control_change)
        self._make_slider_row(ac, 1, "Logo Scale", scale, 0.04, 0.25, self._on_control_change)
        self._make_slider_row(ac, 2, "Padding X",  padx,  0.0,  0.08, self._on_control_change)
        self._make_slider_row(ac, 3, "Padding Y",  pady,  0.0,  0.08, self._on_control_change)

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
        tk.Label(pc, text="Placement", bg=C["bg_card"], fg=C["fg_dim"],
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 5))
        self.cb_copyright = ttk.Combobox(pc, textvariable=self.copyright_pos,
                                          values=POSITIONS, state="readonly", width=22)
        self.cb_copyright.pack(fill=tk.X)
        self.cb_copyright.bind("<<ComboboxSelected>>", self._on_position_selected)

        self._section_hdr(panel, "Copyright  –  Appearance")
        ac = self._card(panel)
        ac.columnconfigure(1, weight=1)
        self._make_slider_row(ac, 0, "Opacity",   self.copyright_opacity_var, 0.1,  1.0,  self._on_control_change)
        self._make_slider_row(ac, 1, "Text Size", self.copyright_size_var,    0.01, 0.06, self._on_control_change)
        self._make_slider_row(ac, 2, "Padding X", self.copyright_padx_var,    0.0,  0.08, self._on_control_change)
        self._make_slider_row(ac, 3, "Padding Y", self.copyright_pady_var,    0.0,  0.08, self._on_control_change)

        self._section_hdr(panel, "Copyright  –  Font")
        fc = self._card(panel)
        tk.Label(fc, text="Font Family", bg=C["bg_card"], fg=C["fg_dim"],
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 5))
        self.cb_copyright_font = self._font_menu(fc, self.copyright_font_var)

        self._section_hdr(panel, "Copyright  –  Actions")
        acts = self._card(panel)
       # Create a single frame for both actions
        action_row = tk.Frame(acts, bg=C["bg_card"])
        action_row.pack(fill=tk.X, pady=(0, 8))

        # Pack the button to the left
        self._accent_btn(action_row, "↺  Rotate 90°", self._rotate_copyright,
                        bg="#232323", hov="#2E2E2E",
                        fg=C["fg_main"]).pack(side=tk.LEFT)

        # Pack the checkbutton to the left as well, so it sits right next to the button
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
        tk.Label(pc, text="Placement", bg=C["bg_card"], fg=C["fg_dim"],
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 5))
        self.cb_custom_text = ttk.Combobox(pc, textvariable=self.custom_text_pos,
                                            values=POSITIONS, state="readonly", width=22)
        self.cb_custom_text.pack(fill=tk.X)
        self.cb_custom_text.bind("<<ComboboxSelected>>", self._on_position_selected)

        self._section_hdr(panel, "Custom Text  –  Appearance")
        ac = self._card(panel)
        ac.columnconfigure(1, weight=1)
        self._make_slider_row(ac, 0, "Opacity",   self.custom_text_opacity_var, 0.1, 1.0,  self._on_control_change)
        self._make_slider_row(ac, 1, "Text Size", self.custom_text_size_var,    0.01, 0.06, self._on_control_change)
        self._make_slider_row(ac, 2, "Padding X", self.custom_text_padx_var,    0.0,  0.08, self._on_control_change)
        self._make_slider_row(ac, 3, "Padding Y", self.custom_text_pady_var,    0.0,  0.08, self._on_control_change)
        self._make_slider_row(ac, 4, "Rotation",  self.custom_text_rot_var,     0,   360,  self._on_control_change, fmt="deg")

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

        # Ensure startup dialog appears on the Windows Taskbar
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
        tk.Label(hdr, text="Watermark & Border Tool  ·  v3.5.0",
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
        self.single_image_save_folder = ""  # deferred save destination
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

        self._validate_positions()
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
    #  Control Event Handlers & Auto Validation
    # =========================================================================

    def _on_control_change(self, *args):
        if self._preview_timer is not None:
            self.root.after_cancel(self._preview_timer)
        self._preview_timer = self.root.after(200, self.update_preview)

    def _on_position_selected(self, event):
        self._validate_positions()
        self._on_control_change()

    def _validate_positions(self):
        controls = [
            ("rkm",         self.rkm_enable.get(),         self.rkm_pos,         self.cb_rkm),
            ("club",        self.club_enable.get(),        self.club_pos,        self.cb_club),
            ("qr",          self.qr_enable.get(),          self.qr_pos,          self.cb_qr),
            ("copyright",   self.copyright_enable.get(),   self.copyright_pos,   self.cb_copyright),
            ("custom_text", self.custom_text_enable.get(), self.custom_text_pos, self.cb_custom_text),
        ]
        used = set()
        for _name, enabled, var, _cb in controls:
            if enabled:
                pos = var.get()
                if pos in used:
                    unused = [p for p in POSITIONS if p not in used]
                    if unused:
                        var.set(unused[0])
                        pos = unused[0]
                used.add(pos)

    # =========================================================================
    #  Config compilation (100% compatible with watermarking rendering)
    # =========================================================================

    def compile_config(self):
        return {
            "border_scale": self.border_scale_var.get(),
            "rkm": {
                "enabled":     self.rkm_enable.get(),
                "pos":         self.rkm_pos.get(),
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
                "pos":         self.club_pos.get(),
                "opacity":     self.club_opacity_var.get(),
                "scale":       self.club_scale_var.get(),
                "pad_x_scale": self.club_padx_var.get(),
                "pad_y_scale": self.club_pady_var.get(),
                "path":        self.club_path,
            },
            "qr": {
                "enabled":     self.qr_enable.get(),
                "pos":         self.qr_pos.get(),
                "opacity":     self.qr_opacity_var.get(),
                "scale":       self.qr_scale_var.get(),
                "pad_x_scale": self.qr_padx_var.get(),
                "pad_y_scale": self.qr_pady_var.get(),
                "path":        self.qr_path,
            },
            "copyright": {
                "enabled":        self.copyright_enable.get(),
                "pos":            self.copyright_pos.get(),
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
                "pos":         self.custom_text_pos.get(),
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
    #  Interactive Canvas Selection
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
        self.update_preview()

    def _on_canvas_click(self, event):
        cx, cy = event.x, event.y
        clicked = None
        for key in reversed(list(self.display_boxes.keys())):
            x1, y1, x2, y2 = self.display_boxes[key]
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                clicked = key
                break
        self.select_element(clicked)
    def _bind_canvas_scroll(self, e):
        # Hijack global scroll wheel while hovering over the preview canvas
        self.root.bind_all("<MouseWheel>", self._on_canvas_scroll)
        self.root.bind_all("<Button-4>", self._on_canvas_scroll)
        self.root.bind_all("<Button-5>", self._on_canvas_scroll)

    def _unbind_canvas_scroll(self, e):
        # Release the scroll wheel when leaving the preview canvas
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

        # Determine scroll direction: 1 for increase, -1 for decrease
        if hasattr(event, 'num') and event.num == 4:
            direction = 1
        elif hasattr(event, 'num') and event.num == 5:
            direction = -1
        else:
            direction = 1 if event.delta > 0 else -1

        # Map the selected element to its Tk variable, bounds, and increment step
        scale_vars = {
            "rkm":         (self.rkm_scale_var,         0.04, 0.25, 0.005),
            "club":        (self.club_scale_var,        0.04, 0.25, 0.005),
            "qr":          (self.qr_scale_var,          0.04, 0.25, 0.005),
            "copyright":   (self.copyright_size_var,    0.01, 0.06, 0.002),
            "custom_text": (self.custom_text_size_var,  0.01, 0.06, 0.002)
        }

        if self.selected_element in scale_vars:
            var, min_v, max_v, step = scale_vars[self.selected_element]

            # Calculate new value, clamp it to min/max bounds, and apply
            new_val = var.get() + (step * direction)
            new_val = max(min_v, min(max_v, new_val))
            var.set(new_val)
            self._on_control_change()

    def _on_arrow_key(self, event):
        """Move the currently selected watermark element using keyboard arrow keys."""
        # Don't intercept arrow keys if user is currently typing in a text entry or combo
        focused = self.root.focus_get()
        if isinstance(focused, (tk.Entry, ttk.Combobox)):
            return

        if not self.selected_element:
            return

        elem_map = {
            "rkm":         (self.rkm_pos,         self.rkm_padx_var,         self.rkm_pady_var),
            "club":        (self.club_pos,        self.club_padx_var,        self.club_pady_var),
            "qr":          (self.qr_pos,          self.qr_padx_var,          self.qr_pady_var),
            "copyright":   (self.copyright_pos,   self.copyright_padx_var,   self.copyright_pady_var),
            "custom_text": (self.custom_text_pos, self.custom_text_padx_var, self.custom_text_pady_var),
        }

        if self.selected_element not in elem_map:
            return

        pos_var, padx_var, pady_var = elem_map[self.selected_element]
        pos = pos_var.get()

        step = 0.002
        min_v, max_v = 0.0, 0.08
        key = event.keysym
        changed = False

        if key in ("Left", "Right"):
            curr_x = padx_var.get()
            # In Top Right, Bottom Right: Right decreases pad_x (moves right), Left increases pad_x
            # In Top Left, Bottom Left, Center: Right increases pad_x (moves right), Left decreases pad_x
            if pos in ("Top Right", "Bottom Right"):
                dx = -step if key == "Right" else step
            else:
                dx = step if key == "Right" else -step

            new_x = max(min_v, min(max_v, round(curr_x + dx, 4)))
            if new_x != curr_x:
                padx_var.set(new_x)
                changed = True

        elif key in ("Up", "Down"):
            curr_y = pady_var.get()
            # In Bottom Left, Bottom Right: Down decreases pad_y (moves down), Up increases pad_y (moves up)
            # In Top Left, Top Right, Center: Down increases pad_y (moves down), Up decreases pad_y (moves up)
            if pos in ("Bottom Left", "Bottom Right"):
                dy = -step if key == "Down" else step
            else:
                dy = step if key == "Down" else -step

            new_y = max(min_v, min(max_v, round(curr_y + dy, 4)))
            if new_y != curr_y:
                pady_var.set(new_y)
                changed = True

        if changed:
            self._on_control_change()
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
        messagebox.showinfo(
            "Export Complete",
            f"Successfully exported {success_count} file(s) to:\n{output_folder}")


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