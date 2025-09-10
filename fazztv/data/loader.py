"""Data loading functionality for FazzTV."""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional
from loguru import logger

from fazztv.config import get_settings


class DataLoader:
    """Handles loading and managing data from JSON files."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize data loader.
        
        Args:
            data_dir: Optional data directory path
        """
        settings = get_settings()
        self.data_dir = data_dir or settings.data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def load_json_file(self, filename: str) -> Dict[str, Any]:
        """
        Load data from a JSON file.
        
        Args:
            filename: Name of the JSON file
            
        Returns:
            Loaded data dictionary
        """
        file_path = self.data_dir / filename
        
        if not file_path.exists():
            logger.warning(f"Data file not found: {file_path}")
            return {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Loaded data from {file_path}")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON from {file_path}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return {}
    
    def save_json_file(self, data: Dict[str, Any], filename: str, indent: int = 2) -> bool:
        """
        Save data to a JSON file.
        
        Args:
            data: Data to save
            filename: Name of the JSON file
            indent: JSON indentation level
            
        Returns:
            True if saved successfully
        """
        file_path = self.data_dir / filename
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, ensure_ascii=False)
            logger.info(f"Saved data to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving to {file_path}: {e}")
            return False
    
    def load_episodes(self, filename: str = "madonna_data.json") -> List[Dict[str, Any]]:
        """
        Load episode data from JSON file.
        
        Args:
            filename: Name of the episodes file
            
        Returns:
            List of episode dictionaries
        """
        data = self.load_json_file(filename)
        episodes = data.get("episodes", [])
        
        # Add GUIDs to episodes that don't have them
        modified = False
        for episode in episodes:
            if 'guid' not in episode:
                episode['guid'] = str(uuid.uuid4())
                modified = True
                logger.debug(f"Added GUID to episode: {episode.get('title', 'Unknown')}")
        
        # Save back if modified
        if modified:
            data["episodes"] = episodes
            self.save_json_file(data, filename)
            logger.info(f"Updated {len(episodes)} episodes with GUIDs")
        
        return episodes
    
    def load_show_data(self, filename: str = "shows.json") -> List[Dict[str, Any]]:
        """
        Load show/program data.
        
        Args:
            filename: Name of the shows file
            
        Returns:
            List of show dictionaries
        """
        data = self.load_json_file(filename)
        return data.get("shows", [])
    
    def load_artist_data(self, filename: str = "artists.json") -> List[str]:
        """
        Load artist names.
        
        Args:
            filename: Name of the artists file
            
        Returns:
            List of artist names
        """
        data = self.load_json_file(filename)
        return data.get("artists", [])
    
    def load_config(self, filename: str = "config.json") -> Dict[str, Any]:
        """
        Load configuration data.
        
        Args:
            filename: Name of the config file
            
        Returns:
            Configuration dictionary
        """
        return self.load_json_file(filename)
    
    def merge_data_files(self, filenames: List[str]) -> Dict[str, Any]:
        """
        Merge multiple JSON data files.
        
        Args:
            filenames: List of filenames to merge
            
        Returns:
            Merged data dictionary
        """
        merged = {}
        
        for filename in filenames:
            data = self.load_json_file(filename)
            merged.update(data)
        
        return merged
    
    def validate_episode_data(self, episode: Dict[str, Any]) -> bool:
        """
        Validate episode data structure.
        
        Args:
            episode: Episode dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ["title", "music_url"]
        
        for field in required_fields:
            if field not in episode:
                logger.warning(f"Episode missing required field: {field}")
                return False
        
        # Validate URLs
        if not episode["music_url"].startswith(("http://", "https://")):
            logger.warning(f"Invalid music URL: {episode['music_url']}")
            return False
        
        return True
    
    def filter_episodes(
        self,
        episodes: List[Dict[str, Any]],
        filter_func: Optional[callable] = None,
        validate: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Filter episodes based on criteria.
        
        Args:
            episodes: List of episodes
            filter_func: Optional filter function
            validate: Whether to validate episodes
            
        Returns:
            Filtered list of episodes
        """
        filtered = episodes
        
        if validate:
            filtered = [e for e in filtered if self.validate_episode_data(e)]
        
        if filter_func:
            filtered = [e for e in filtered if filter_func(e)]
        
        return filtered
    
    def get_episode_by_guid(
        self,
        episodes: List[Dict[str, Any]],
        guid: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find episode by GUID.
        
        Args:
            episodes: List of episodes
            guid: GUID to search for
            
        Returns:
            Episode dictionary or None
        """
        for episode in episodes:
            if episode.get('guid') == guid:
                return episode
        return None
    
    def update_episode(
        self,
        episodes: List[Dict[str, Any]],
        guid: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update episode data by GUID.
        
        Args:
            episodes: List of episodes
            guid: GUID of episode to update
            updates: Dictionary of updates
            
        Returns:
            True if updated successfully
        """
        episode = self.get_episode_by_guid(episodes, guid)
        
        if episode:
            episode.update(updates)
            logger.debug(f"Updated episode {guid}")
            return True
        
        logger.warning(f"Episode not found: {guid}")
        return False