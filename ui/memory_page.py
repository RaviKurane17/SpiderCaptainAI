import os, time, json, math, random
from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from ui.constants import *
from utils.logger import log
from memory.json_memory import MAX_VALUE_LENGTH
from memory.vector_memory import get_all_conversations

class MemoryPageMixin:
    def _build_files_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(40, 20, 40, 20)
        
        lbl = QLabel("HOLOGRAPHIC FILE SCANNER")
        lbl.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {C.WHITE}; letter-spacing: 2px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl)
        lay.addSpacing(10)
        
        self._file_search = QLineEdit()
        self._file_search.setPlaceholderText("Search file system...")
        self._file_search.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(10, 18, 35, 200);
                color: {C.WHITE};
                border: 1px solid rgba(0, 212, 255, 60);
                border-radius: 8px;
                padding: 10px;
                font-family: 'Inter';
            }}
            QLineEdit:focus {{
                border: 1px solid rgba(0, 212, 255, 200);
                background: rgba(15, 25, 45, 220);
            }}
        """)
        self._file_search.textChanged.connect(self._on_file_search)
        lay.addWidget(self._file_search)
        lay.addSpacing(10)
        
        self._file_model = QFileSystemModel()
        user_dir = str(Path.home())
        self._file_model.setRootPath(user_dir)
        
        self._file_tree = QTreeView()
        self._file_tree.setModel(self._file_model)
        self._file_tree.setRootIndex(self._file_model.index(user_dir))
        
        self._file_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._file_tree.customContextMenuRequested.connect(self._file_context_menu)
        
        self._file_tree.setStyleSheet(f"""
            QTreeView {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(10,18,35,150), stop:1 rgba(5,10,20,150));
                color: {C.WHITE};
                border: 1px solid rgba(0, 212, 255, 40); 
                border-radius: 8px;
            }}
            QTreeView::item:hover {{
                background: rgba(0, 212, 255, 40);
            }}
            QTreeView::item:selected {{
                background: rgba(0, 212, 255, 80);
                color: white;
            }}
            QHeaderView::section {{
                background: rgba(10, 18, 35, 255); 
                color: {C.PRI}; 
                padding: 6px; 
                border: none;
                font-weight: bold;
                border-bottom: 1px solid rgba(0, 212, 255, 40);
            }}
        """)
        lay.addWidget(self._file_tree, stretch=1)
        return w

    def _delete_memory_entry(self):
        key_path = self._mem_del_key.text().strip()
        if "/" not in key_path:
            self._log.append_log("SYS: Format: category/key (e.g. identity/name)")
            return
        try:
            from memory.memory_manager import load_memory, save_memory
            cat, key = key_path.split("/", 1)
            mem = load_memory()
            if cat in mem and key in mem[cat]:
                del mem[cat][key]
                save_memory(mem)
                self._log.append_log(f"SYS: Deleted memory: {cat}/{key}")
                self._mem_del_key.clear()
                self._load_memories()
            else:
                self._log.append_log(f"SYS: Memory not found: {cat}/{key}")
        except Exception as e:
            self._log.append_log(f"SYS: Delete error: {e}")

    def _clear_all_memories(self):
        try:
            from memory.memory_manager import save_memory, _empty_memory
            save_memory(_empty_memory())
            self._log.append_log("SYS: ⚠ All memories cleared.")
            self._load_memories()
        except Exception as e:
            self._log.append_log(f"SYS: Clear error: {e}")
