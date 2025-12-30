#!/usr/bin/env python3
"""
Chromium Sync Engine
Core logic for bidirectional synchronization.
"""

import sqlite3
import shutil
import json
import logging
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import subprocess

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class BrowserProfile:
    def __init__(self, name: str, user_data_path: Path, process_name: str):
        self.name = name
        self.path = user_data_path
        self.process_name = process_name
        
    @property
    def history_db(self) -> Path:
        return self.path / "History"

    @property
    def bookmarks_file(self) -> Path:
        return self.path / "Bookmarks"

    @property
    def sessions_dir(self) -> Path:
        return self.path / "Sessions"
        
    def is_running(self) -> bool:
        """Verifica se o processo do navegador está ativo."""
        try:
            # pgrep retorna 0 se encontrou processo, 1 se não.
            subprocess.check_call(["pgrep", "-x", self.process_name], stdout=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            return False

class SyncManager:
    """Gerencia a sincronização entre dois perfis."""
    
    def __init__(self, source: BrowserProfile, target: BrowserProfile):
        self.source = source
        self.target = target
        self._id_counter = 0

    def _generate_id(self) -> str:
        """Gera um ID numérico único baseado em timestamp."""
        self._id_counter += 1
        return str(int(datetime.now().timestamp() * 1000000) + self._id_counter)

    def check_safety(self):
        """Aborta se algum navegador estiver rodando."""
        if self.source.is_running() or self.target.is_running():
            logger.warning(f"Safety Check Failed: {self.source.name} or {self.target.name} is running.")
            logger.warning("Aborting sync to prevent database corruption.")
            sys.exit(0)

    def sync_sessions_smart(self):
        """Sync de Sessões usando estratégia 'Latest Wins'."""
        logger.info("⚖️  Evaluating Sessions (Latest Wins)...")
        
        if not self.source.sessions_dir.exists() or not self.target.sessions_dir.exists():
            logger.warning("⚠️  Session folder missing. Skipping.")
            return

        src_mtime = self.source.sessions_dir.stat().st_mtime
        tgt_mtime = self.target.sessions_dir.stat().st_mtime
        
        # Margem de 5s para evitar loop
        if abs(src_mtime - tgt_mtime) < 5:
            logger.info("   -> Sessions appear synced. No action.")
            return

        winner, loser = None, None
        if src_mtime > tgt_mtime:
            winner, loser = self.source, self.target
        else:
            winner, loser = self.target, self.source

        logger.info(f"   -> Winner: {winner.name} (Newer)")
        
        items = ["Sessions", "Session Storage"]
        for item in items:
            s_path = winner.path / item
            d_path = loser.path / item
            
            if s_path.exists():
                if d_path.exists():
                    if d_path.is_dir(): shutil.rmtree(d_path)
                    else: d_path.unlink()
                
                if s_path.is_dir(): shutil.copytree(s_path, d_path)
                else: shutil.copy2(s_path, d_path)

    def merge_history(self, source: BrowserProfile, target: BrowserProfile):
        """Merge unidirecional de histórico."""
        label = f"{source.name} -> {target.name}"
        logger.info(f"clock: Syncing History ({label})...")
        
        if not source.history_db.exists() or not target.history_db.exists():
            return

        # Backup temporário para leitura segura
        temp_src = Path(f"/tmp/sync_{source.name}_hist.db")
        shutil.copy2(source.history_db, temp_src)
        
        try:
            with sqlite3.connect(temp_src) as src_conn, sqlite3.connect(target.history_db) as dst_conn:
                src_cur = src_conn.cursor()
                dst_cur = dst_conn.cursor()

                # 1. URLs
                src_cur.execute("SELECT id, url, title, visit_count, typed_count, last_visit_time, hidden FROM urls")
                url_map = {} # Map ID antigo -> ID novo
                
                for row in src_cur.fetchall():
                    src_id, url, title, v_count, t_count, last_visit, hidden = row
                    
                    dst_cur.execute("SELECT id FROM urls WHERE url = ?", (url,))
                    match = dst_cur.fetchone()
                    
                    if match:
                        tgt_id = match[0]
                        # Update timestamp (max)
                        dst_cur.execute("UPDATE urls SET last_visit_time = MAX(last_visit_time, ?) WHERE id = ?", (last_visit, tgt_id))
                    else:
                        dst_cur.execute(
                            "INSERT INTO urls (url, title, visit_count, typed_count, last_visit_time, hidden) VALUES (?, ?, ?, ?, ?, ?)", 
                            (url, title, v_count, t_count, last_visit, hidden)
                        )
                        tgt_id = dst_cur.lastrowid
                    
                    url_map[src_id] = tgt_id

                # 2. Visits
                src_cur.execute("SELECT id, url, visit_time, from_visit, transition, segment_id, visit_duration FROM visits")
                added = 0
                for row in src_cur.fetchall():
                    _, src_url_id, v_time, from_v, trans, seg_id, v_dur = row
                    
                    if src_url_id not in url_map: continue
                    tgt_url_id = url_map[src_url_id]
                    
                    # Dedup
                    dst_cur.execute("SELECT id FROM visits WHERE url = ? AND visit_time = ?", (tgt_url_id, v_time))
                    if dst_cur.fetchone(): continue
                    
                    dst_cur.execute(
                        "INSERT INTO visits (url, visit_time, from_visit, transition, segment_id, visit_duration) VALUES (?, ?, ?, ?, ?, ?)",
                        (tgt_url_id, v_time, 0, trans, seg_id, v_dur)
                    )
                    added += 1
                
                dst_conn.commit()
                logger.info(f"   -> {added} visits merged.")

        except Exception as e:
            logger.error(f"❌ SQL Error ({label}): {e}")
        finally:
            if temp_src.exists(): temp_src.unlink()

    def sync_bookmarks(self, source: BrowserProfile, target: BrowserProfile):
        """Sync unidirecional de favoritos (JSON)."""
        label = f"{source.name} -> {target.name}"
        logger.info(f"🔖 Syncing Bookmarks ({label})...")
        
        if not source.bookmarks_file.exists(): return
        if not target.bookmarks_file.exists():
            shutil.copy2(source.bookmarks_file, target.bookmarks_file)
            return

        try:
            with open(source.bookmarks_file, 'r', encoding='utf-8') as f: src_data = json.load(f)
            with open(target.bookmarks_file, 'r', encoding='utf-8') as f: dst_data = json.load(f)
            
            count = 0
            
            # Recursive sync logic closure
            def _recursive_sync(src_node, dst_parent):
                nonlocal count
                dst_map = {}
                if 'children' in dst_parent:
                    for child in dst_parent['children']:
                        key = child.get('url') if child.get('type') == 'url' else child.get('name')
                        if key: dst_map[key] = child

                if 'children' in src_node:
                    for item in src_node['children']:
                        itype = item.get('type')
                        key = item.get('url') if itype == 'url' else item.get('name')
                        
                        if itype == 'url':
                            if key not in dst_map:
                                new_item = item.copy()
                                new_item['id'] = self._generate_id()
                                if 'guid' in new_item: del new_item['guid']
                                if 'children' not in dst_parent: dst_parent['children'] = []
                                dst_parent['children'].append(new_item)
                                dst_map[key] = new_item
                                count += 1
                        elif itype == 'folder':
                            tgt_folder = dst_map.get(key)
                            if not tgt_folder:
                                tgt_folder = {
                                    "date_added": str(int(datetime.now().timestamp() * 1000000)),
                                    "id": self._generate_id(),
                                    "name": key,
                                    "type": "folder",
                                    "children": []
                                }
                                if 'children' not in dst_parent: dst_parent['children'] = []
                                dst_parent['children'].append(tgt_folder)
                                dst_map[key] = tgt_folder
                            
                            _recursive_sync(item, tgt_folder)

            # Sync Bar and Other
            _recursive_sync(src_data.get('roots', {}).get('bookmark_bar', {}), dst_data.get('roots', {}).get('bookmark_bar', {}))
            _recursive_sync(src_data.get('roots', {}).get('other', {}), dst_data.get('roots', {}).get('other', {}))
            
            with open(target.bookmarks_file, 'w', encoding='utf-8') as f:
                json.dump(dst_data, f, indent=4)
                
            logger.info(f"   -> {count} bookmarks synced.")

        except Exception as e:
            logger.error(f"❌ JSON Error ({label}): {e}")

    def run_bidirectional(self):
        self.check_safety()
        
        # 1. Sessions (Smart)
        self.sync_sessions_smart()
        
        # 2. History (Two-Way)
        self.merge_history(self.source, self.target)
        self.merge_history(self.target, self.source)
        
        # 3. Bookmarks (Two-Way)
        self.sync_bookmarks(self.source, self.target)
        self.sync_bookmarks(self.target, self.source)

def main():
    home = Path.home()
    
    # Configuração dos Perfis 
    dia = BrowserProfile(
        name="Dia",
        user_data_path=home / "Library/Application Support/Dia/User Data/Default",
        process_name="Dia"
    )
    
    vivaldi = BrowserProfile(
        name="Vivaldi",
        user_data_path=home / "Library/Application Support/Vivaldi/Default",
        process_name="Vivaldi"
    )
    
    if not dia.path.exists() or not vivaldi.path.exists():
        logger.error("❌ Profiles not found. Check installation paths.")
        sys.exit(1)

    manager = SyncManager(dia, vivaldi)
    manager.run_bidirectional()

if __name__ == "__main__":
    main()
