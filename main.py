from __future__ import annotations

import os

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

from src.app import AURAGuardApp


if __name__ == "__main__":
    app = AURAGuardApp()
    app.mainloop()
