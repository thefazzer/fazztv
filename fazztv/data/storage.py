"""Data storage management for FazzTV."""

import json
import pickle
from pathlib import Path
from typing import Any, Optional, Dict, List
from datetime import datetime
from loguru import logger

from fazztv.config import get_settings


class DataStorage:
    """Handles persistent data storage."""
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize data storage.
        
        Args:
            storage_dir: Optional storage directory
        """
        settings = get_settings()
        self.storage_dir = storage_dir or settings.data_dir / "storage"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def store(self, key: str, data: Any, format: str = "json") -> bool:
        """
        Store data with a key.
        
        Args:
            key: Storage key
            data: Data to store
            format: Storage format ('json' or 'pickle')
            
        Returns:
            True if stored successfully
        """
        file_path = self._get_file_path(key, format)
        
        try:
            if format == "json":
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            elif format == "pickle":
                with open(file_path, 'wb') as f:
                    pickle.dump(data, f)
            else:
                logger.error(f"Unknown storage format: {format}")
                return False
            
            logger.debug(f"Stored data with key: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing data with key {key}: {e}")
            return False
    
    def retrieve(self, key: str, format: str = "json") -> Optional[Any]:
        """
        Retrieve data by key.
        
        Args:
            key: Storage key
            format: Storage format ('json' or 'pickle')
            
        Returns:
            Retrieved data or None
        """
        file_path = self._get_file_path(key, format)
        
        if not file_path.exists():
            logger.debug(f"No data found for key: {key}")
            return None
        
        try:
            if format == "json":
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            elif format == "pickle":
                with open(file_path, 'rb') as f:
                    return pickle.load(f)
            else:
                logger.error(f"Unknown storage format: {format}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving data with key {key}: {e}")
            return None
    
    def exists(self, key: str, format: str = "json") -> bool:
        """
        Check if data exists for key.
        
        Args:
            key: Storage key
            format: Storage format
            
        Returns:
            True if exists
        """
        file_path = self._get_file_path(key, format)
        return file_path.exists()
    
    def delete(self, key: str, format: str = "json") -> bool:
        """
        Delete stored data.
        
        Args:
            key: Storage key
            format: Storage format
            
        Returns:
            True if deleted successfully
        """
        file_path = self._get_file_path(key, format)
        
        if not file_path.exists():
            logger.debug(f"No data to delete for key: {key}")
            return False
        
        try:
            file_path.unlink()
            logger.debug(f"Deleted data with key: {key}")
            return True
        except Exception as e:
            logger.error(f"Error deleting data with key {key}: {e}")
            return False
    
    def list_keys(self, format: str = "json") -> List[str]:
        """
        List all stored keys.
        
        Args:
            format: Storage format to filter by
            
        Returns:
            List of keys
        """
        ext = ".json" if format == "json" else ".pkl"
        files = self.storage_dir.glob(f"*{ext}")
        return [f.stem for f in files]
    
    def store_metadata(self, key: str, metadata: Dict[str, Any]) -> bool:
        """
        Store metadata for a key.
        
        Args:
            key: Storage key
            metadata: Metadata dictionary
            
        Returns:
            True if stored successfully
        """
        meta_key = f"{key}_metadata"
        metadata["stored_at"] = datetime.now().isoformat()
        return self.store(meta_key, metadata, format="json")
    
    def retrieve_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve metadata for a key.
        
        Args:
            key: Storage key
            
        Returns:
            Metadata dictionary or None
        """
        meta_key = f"{key}_metadata"
        return self.retrieve(meta_key, format="json")
    
    def clear_old_data(self, days: int = 30) -> int:
        """
        Clear data older than specified days.
        
        Args:
            days: Age threshold in days
            
        Returns:
            Number of items deleted
        """
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(days=days)
        deleted = 0
        
        for key in self.list_keys():
            metadata = self.retrieve_metadata(key)
            if metadata:
                stored_at = datetime.fromisoformat(metadata.get("stored_at", ""))
                if stored_at < cutoff:
                    if self.delete(key):
                        self.delete(f"{key}_metadata")
                        deleted += 1
        
        logger.info(f"Cleared {deleted} old data items")
        return deleted
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get information about storage usage.
        
        Returns:
            Storage information dictionary
        """
        total_size = 0
        file_count = 0
        
        for file_path in self.storage_dir.iterdir():
            if file_path.is_file():
                total_size += file_path.stat().st_size
                file_count += 1
        
        return {
            "directory": str(self.storage_dir),
            "file_count": file_count,
            "total_size": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }
    
    def _get_file_path(self, key: str, format: str) -> Path:
        """Get file path for a storage key."""
        ext = ".json" if format == "json" else ".pkl"
        return self.storage_dir / f"{key}{ext}"
    
    def backup(self, backup_dir: Path) -> bool:
        """
        Backup all stored data.
        
        Args:
            backup_dir: Directory to backup to
            
        Returns:
            True if successful
        """
        import shutil
        
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copytree(self.storage_dir, backup_path)
            logger.info(f"Backed up storage to {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False