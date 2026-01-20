"""
Backup and rollback management.
"""

import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime
import logging
import json


class BackupManager:
    """Manages backups and rollbacks for code modifications."""
    
    def __init__(self, backup_dir: Path = Path(".janitor_backups")):
        """Initialize backup manager."""
        self.backup_dir = backup_dir
        self.logger = logging.getLogger(__name__)
        self.max_backups = 5
        
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self.logger.error(f"Failed to create backup directory: {e}")
    
    def create_backup(self, target: Path) -> Optional[Path]:
        """Create a backup of the target."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{target.name}_{timestamp}"
        backup_path = self.backup_dir / backup_name
        
        try:
            if target.is_file():
                shutil.copy2(target, backup_path)
                self.logger.info(f"Backed up {target} to {backup_path}")
            elif target.is_dir():
                shutil.copytree(target, backup_path)
                self.logger.info(f"Backed up directory {target} to {backup_path}")
            else:
                self.logger.error(f"Invalid target for backup: {target}")
                return None
            
            self._write_metadata(backup_path, target)
            self._cleanup_old_backups()
            
            return backup_path
            
        except OSError as e:
            self.logger.error(f"Failed to create backup: {e}")
            return None
    
    def _write_metadata(self, backup_path: Path, original_path: Path) -> None:
        """Write metadata about the backup."""
        metadata = {
            "original_path": str(original_path),
            "backup_path": str(backup_path),
            "created_at": datetime.now().isoformat(),
            "original_name": original_path.name
        }
        
        meta_file = backup_path.with_suffix('.meta.json')
        try:
            with open(meta_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        except OSError as e:
            self.logger.warning(f"Failed to write backup metadata: {e}")
    
    def _cleanup_old_backups(self) -> None:
        """Remove old backups beyond the limit."""
        try:
            backups = sorted(
                [d for d in self.backup_dir.iterdir() if d.is_dir()],
                key=lambda d: d.stat().st_mtime,
                reverse=True
            )
            
            for old_backup in backups[self.max_backups:]:
                self.logger.info(f"Removing old backup: {old_backup}")
                try:
                    shutil.rmtree(old_backup)
                except OSError:
                    self.logger.warning(f"Failed to remove backup: {old_backup}")
                    
        except OSError as e:
            self.logger.warning(f"Failed to cleanup old backups: {e}")
    
    def rollback(self, target: Path) -> bool:
        """Rollback to the most recent backup."""
        backup = self._find_latest_backup(target)
        
        if backup is None:
            self.logger.error(f"No backup found for {target}")
            return False
        
        try:
            if target.exists():
                if target.is_file():
                    target.unlink()
                else:
                    shutil.rmtree(target)
            
            if backup.is_file():
                shutil.copy2(backup, target)
            else:
                shutil.copytree(backup, target)
            
            self.logger.info(f"Rolled back {target} from {backup}")
            return True
            
        except OSError as e:
            self.logger.error(f"Rollback failed: {e}")
            return False
    
    def _find_latest_backup(self, target: Path) -> Optional[Path]:
        """Find the most recent backup for a target."""
        target_name = target.name
        
        try:
            candidates = [
                d for d in self.backup_dir.iterdir() 
                if d.is_dir() and d.name.startswith(target_name)
            ]
            
            if not candidates:
                return None
            
            return max(candidates, key=lambda d: d.stat().st_mtime)
            
        except OSError as e:
            self.logger.warning(f"Failed to find backups: {e}")
            return None
    
    def list_backups(self, target: Optional[Path] = None) -> list:
        """List available backups."""
        backups = []
        
        for backup_dir in self.backup_dir.iterdir():
            if not backup_dir.is_dir():
                continue
            
            meta_file = backup_dir.with_suffix('.meta.json')
            
            if not meta_file.exists():
                continue
            
            try:
                with open(meta_file, 'r') as f:
                    metadata = json.load(f)
                
                if target is None or Path(metadata['original_path']) == target:
                    metadata['backup_path'] = str(backup_dir)
                    backups.append(metadata)
            except (OSError, json.JSONDecodeError, KeyError):
                continue
        
        return sorted(backups, key=lambda b: b.get('created_at', ''), reverse=True)
    
    def cleanup_all(self) -> int:
        """Remove all backups."""
        count = 0
        for backup_dir in self.backup_dir.iterdir():
            if backup_dir.is_dir():
                try:
                    shutil.rmtree(backup_dir)
                    count += 1
                except OSError:
                    pass
        
        self.logger.info(f"Cleaned up {count} backups")
        return count
