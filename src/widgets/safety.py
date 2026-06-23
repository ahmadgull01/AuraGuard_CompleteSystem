from __future__ import annotations

import tkinter as tk


def widget_alive(widget) -> bool:
    """Return True only while a Tk widget still exists.

    Tkinter raises errors if we update a widget after its page was destroyed.
    This helper keeps camera reset code safe during fast navigation or logout.
    """
    try:
        return bool(widget is not None and widget.winfo_exists())
    except (tk.TclError, AttributeError):
        return False


def safe_configure(widget, **kwargs) -> None:
    if widget_alive(widget):
        try:
            widget.configure(**kwargs)
        except tk.TclError:
            pass


def safe_set(progress_widget, value: float) -> None:
    if widget_alive(progress_widget):
        try:
            progress_widget.set(value)
        except tk.TclError:
            pass
