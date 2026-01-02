#!/usr/bin/env python3
"""
Chromium Sync Engine
Core logic for bidirectional synchronization.
Supports: Dia, Vivaldi, Microsoft Edge, Arc Browser.
"""

import sqlite3
import shutil
import json
import logging
import sys
from pathlib import Path
from datetime import datetime
import subprocess

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class BrowserProfile:
    """Representa um perfil de navegador Chromium."""
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
        self._id_counter += 1
        return str(int(datetime.now().timestamp() * 1000000) + self._id_counter)

    def check_safety(self):
        """Abort se algum navegador do par atual estiver rodando."""
        if self.source.is_running() or self.target.is_running():
            logger.warning(f"Safety Check Failed: {self.source.name} or {self.target.name} is running.")
            logger.warning("Aborting to prevent database corruption.")
            sys.exit(0)

    def sync_sessions_smart(self):
        logger.info(f"⚖️  Evaluating Sessions ({self.source.name} <-> {self.target.name})...")
        
        # Arc Browser tem uma estrutura de sessão proprietária (StorableSidebar)
        # Sincronizar 'Sessions' cruas pode quebrar a sidebar do Arc.
        # Por segurança, pulamos o sync de Sessão se um dos lados for Arc.
        if "Arc" in self.source.name or "Arc" in self.target.name:
            logger.info("   -> Skipping Session Sync for Arc (Proprietary Sidebar Structure).")
            return

        if not self.source.sessions_dir.exists() or not self.target.sessions_dir.exists():
            return

        src_mtime = self.source.sessions_dir.stat().st_mtime
        tgt_mtime = self.target.sessions_dir.stat().st_mtime
        
        if abs(src_mtime - tgt_mtime) < 5:
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
        label = f"{source.name} -> {target.name}"
        logger.info(f"clock: Syncing History ({label})...")
        
        if not source.history_db.exists() or not target.history_db.exists(): return

        temp_src = Path(f"/tmp/sync_{source.name}_hist.db")
        shutil.copy2(source.history_db, temp_src)
        
        try:
            with sqlite3.connect(temp_src) as src_conn, sqlite3.connect(target.history_db) as dst_conn:
                src_cur = src_conn.cursor()
                dst_cur = dst_conn.cursor()

                src_cur.execute("SELECT id, url, title, visit_count, typed_count, last_visit_time, hidden FROM urls")
                url_map = {}
                for row in src_cur.fetchall():
                    src_id, url, title, v_count, t_count, last_visit, hidden = row
                    dst_cur.execute("SELECT id FROM urls WHERE url = ?", (url,))
                    match = dst_cur.fetchone()
                    if match:
                        tgt_id = match[0]
                        dst_cur.execute("UPDATE urls SET last_visit_time = MAX(last_visit_time, ?) WHERE id = ?", (last_visit, tgt_id))
                    else:
                        dst_cur.execute("INSERT INTO urls (url, title, visit_count, typed_count, last_visit_time, hidden) VALUES (?, ?, ?, ?, ?, ?)", (url, title, v_count, t_count, last_visit, hidden))
                        tgt_id = dst_cur.lastrowid
                    url_map[src_id] = tgt_id

                src_cur.execute("SELECT id, url, visit_time, from_visit, transition, segment_id, visit_duration FROM visits")
                added = 0
                for row in src_cur.fetchall():
                    _, src_url_id, v_time, from_v, trans, seg_id, v_dur = row
                    if src_url_id not in url_map: continue
                    tgt_url_id = url_map[src_url_id]
                    dst_cur.execute("SELECT id FROM visits WHERE url = ? AND visit_time = ?", (tgt_url_id, v_time))
                    if dst_cur.fetchone(): continue
                    dst_cur.execute("INSERT INTO visits (url, visit_time, from_visit, transition, segment_id, visit_duration) VALUES (?, ?, ?, ?, ?, ?)", (tgt_url_id, v_time, 0, trans, seg_id, v_dur))
                    added += 1
                dst_conn.commit()
                logger.info(f"   -> {added} visits merged.")
        except Exception as e:
            logger.error(f"❌ SQL Error ({label}): {e}")
        finally:
            if temp_src.exists(): temp_src.unlink()

    def sync_bookmarks(self, source: BrowserProfile, target: BrowserProfile):
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

            _recursive_sync(src_data.get('roots', {}).get('bookmark_bar', {}), dst_data.get('roots', {}).get('bookmark_bar', {}))
            _recursive_sync(src_data.get('roots', {}).get('other', {}), dst_data.get('roots', {}).get('other', {}))
            
            with open(target.bookmarks_file, 'w', encoding='utf-8') as f: json.dump(dst_data, f, indent=4)
            logger.info(f"   -> {count} bookmarks synced.")
        except Exception as e:
            logger.error(f"❌ JSON Error ({label}): {e}")

    def run_bidirectional(self):
        self.check_safety()
        self.sync_sessions_smart()
        self.merge_history(self.source, self.target)
        self.merge_history(self.target, self.source)
        self.sync_bookmarks(self.source, self.target)
        self.sync_bookmarks(self.target, self.source)

def main():
    home = Path.home()
    
    # 1. Definição dos Perfis (Todos Chromium-compatíveis)
    dia = BrowserProfile("Dia", home / "Library/Application Support/Dia/User Data/Default", "Dia")
    vivaldi = BrowserProfile("Vivaldi", home / "Library/Application Support/Vivaldi/Default", "Vivaldi")
    edge = BrowserProfile("Edge", home / "Library/Application Support/Microsoft Edge/Default", "Microsoft Edge")
    arc = BrowserProfile("Arc", home / "Library/Application Support/Arc/User Data/Default", "Arc")
    brave = BrowserProfile("Brave", home / "Library/Application Support/BraveSoftware/Brave-Browser/Default", "Brave Browser")
    
    # 2. Verificação Global de Segurança (Todos devem estar fechados)
    browsers = [dia, vivaldi, edge, arc, brave]
    for b in browsers:
        if b.is_running():
            logger.info(f"🚫 {b.name} is running. Skipping sync to prevent database locks.")
            sys.exit(0)

    # 3. Execução em Cadeia (Arc como Hub)
    if arc.path.exists():
        if dia.path.exists():      SyncManager(arc, dia).run_bidirectional()
        if vivaldi.path.exists():  SyncManager(arc, vivaldi).run_bidirectional()
        if edge.path.exists():     SyncManager(arc, edge).run_bidirectional()
        if brave.path.exists():    SyncManager(arc, brave).run_bidirectional()
    else:
        logger.error("❌ Arc Profile (Hub) not found. Cannot sync.")


if __name__ == "__main__":
    main()
