from __future__ import annotations

import tkinter as tk

from ..theme import COLORS


class ScannerCanvas(tk.Canvas):
    def __init__(self, parent, width: int = 520, height: int = 360) -> None:
        super().__init__(parent, width=width, height=height, highlightthickness=0, bd=0, bg=COLORS["panel2"])
        self.width = width
        self.height = height
        self.scan_y = 42
        self.direction = 1
        self.active_color = COLORS["cyan"]
        self.after_id: str | None = None
        self.draw()

    def draw(self) -> None:
        try:
            if not self.winfo_exists():
                return
            self.delete("all")
            for x in range(0, self.width, 34):
                self.create_line(x, 0, x, self.height, fill="#0c2237")
            for y in range(0, self.height, 34):
                self.create_line(0, y, self.width, y, fill="#0c2237")
            cx, cy = self.width // 2, self.height // 2 + 8
            self.create_oval(cx - 88, cy - 122, cx + 88, cy + 112, outline=self.active_color, width=2, dash=(8, 8))
            self.create_oval(cx - 45, cy - 40, cx - 20, cy - 15, outline=self.active_color, width=2)
            self.create_oval(cx + 20, cy - 40, cx + 45, cy - 15, outline=self.active_color, width=2)
            self.create_arc(cx - 38, cy + 18, cx + 38, cy + 70, start=200, extent=140, outline=self.active_color, width=2, style="arc")
            self.create_text(cx, 28, text="AURA FACE SCANNER", fill=COLORS["muted"], font=("Segoe UI", 10, "bold"))
            for sx, sy, dx, dy in [(36,36,1,1),(self.width-36,36,-1,1),(36,self.height-36,1,-1),(self.width-36,self.height-36,-1,-1)]:
                self.create_line(sx, sy, sx + dx * 45, sy, fill=self.active_color, width=3)
                self.create_line(sx, sy, sx, sy + dy * 45, fill=self.active_color, width=3)
            self.create_line(28, self.scan_y, self.width - 28, self.scan_y, fill=self.active_color, width=2)
            self.create_rectangle(28, self.scan_y - 9, self.width - 28, self.scan_y + 9, fill=self.active_color, stipple="gray25", outline="")
            self.scan_y += self.direction * 4
            if self.scan_y > self.height - 40 or self.scan_y < 40:
                self.direction *= -1
            self.after_id = self.after(45, self.draw)
        except tk.TclError:
            self.after_id = None

    def set_status_color(self, color: str) -> None:
        self.active_color = color

    def stop_animation(self) -> None:
        if self.after_id:
            try:
                self.after_cancel(self.after_id)
            except tk.TclError:
                pass
            self.after_id = None

    def destroy(self) -> None:  # type: ignore[override]
        self.stop_animation()
        super().destroy()
