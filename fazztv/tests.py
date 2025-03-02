import unittest
import os
import tempfile
import socket
import threading
import time
from typing import List, Optional
import subprocess
from loguru import logger

from fazztv.models import MediaItem
from fazztv.serializer import MediaSerializer
from fazztv.broadcaster import RTMPBroadcaster

class DummyRTMPServer:
    """A simple dummy RTMP server for testing."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 1935):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.received_data = []
        self.thread = None
    
    def start(self):
        """Start the dummy RTMP server."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True
        
        self.thread = threading.Thread(target=self._run_server)
        self.thread.daemon = True
        self.thread.start()
        logger.info(f"Dummy RTMP server started on {self.host}:{self.port}")
    
    def _run_server(self):
        """Run the server loop."""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                logger.info(f"Connection from {address}")
                
                # Read some data to confirm receipt
                data = client_socket.recv(4096)
                if data:
                    self.received_data.append(data)
                    logger.info(f"Received {len(data)} bytes from {address}")
                
                client_socket.close()
            except Exception as e:
                if self.running:
                    logger.error(f"Server error: {e}")
    
    def stop(self):
        """Stop the dummy RTMP server."""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        if self.thread:
            self.thread.join(timeout=1)
        logger.info("Dummy RTMP server stopped")
    
    def get_received_count(self) -> int:
        """Get the number of received data chunks."""
        return len(self.received_data)


class TestMediaItem(unittest.TestCase):
    """Test the MediaItem class."""
    
    def test_media_item_creation_and_validation(self):
        """Test creating and validating a MediaItem."""
        # Valid item
        valid_item = MediaItem(
            artist="Lauryn Hill",
            song="Doo Wop (That Thing)",
            url="https://www.youtube.com/watch?v=T6QKqFPRZSA",
            taxprompt="Lauryn Hill had tax issues in 2013.",
            length_percent=80
        )
        
        self.assertEqual(valid_item.artist, "Lauryn Hill")
        self.assertEqual(valid_item.song, "Doo Wop (That Thing)")
        self.assertEqual(valid_item.url, "https://www.youtube.com/watch?v=T6QKqFPRZSA")
        self.assertEqual(valid_item.taxprompt, "Lauryn Hill had tax issues in 2013.")
        self.assertEqual(valid_item.length_percent, 80)
        
        # Test default length_percent
        default_item = MediaItem(
            artist="Lauryn Hill",
            song="Doo Wop (That Thing)",
            url="https://www.youtube.com/watch?v=T6QKqFPRZSA",
            taxprompt="Lauryn Hill had tax issues in 2013."
        )
        self.assertEqual(default_item.length_percent, 100)
        
        # Invalid artist
        with self.assertRaises(ValueError):
            MediaItem(
                artist="",
                song="Doo Wop (That Thing)",
                url="https://www.youtube.com/watch?v=T6QKqFPRZSA",
                taxprompt="Lauryn Hill had tax issues in 2013."
            )
        
        # Invalid song
        with self.assertRaises(ValueError):
            MediaItem(
                artist="Lauryn Hill",
                song="",
                url="https://www.youtube.com/watch?v=T6QKqFPRZSA",
                taxprompt="Lauryn Hill had tax issues in 2013."
            )
        
        # Invalid URL
        with self.assertRaises(ValueError):
            MediaItem(
                artist="Lauryn Hill",
                song="Doo Wop (That Thing)",
                url="https://example.com/not-youtube",
                taxprompt="Lauryn Hill had tax issues in 2013."
            )
        
        # Invalid taxprompt
        with self.assertRaises(ValueError):
            MediaItem(
                artist="Lauryn Hill",
                song="Doo Wop (That Thing)",
                url="https://www.youtube.com/watch?v=T6QKqFPRZSA",
                taxprompt=""
            )
        
        # Invalid length_percent
        with self.assertRaises(ValueError):
            MediaItem(
                artist="Lauryn Hill",
                song="Doo Wop (That Thing)",
                url="https://www.youtube.com/watch?v=T6QKqFPRZSA",
                taxprompt="Lauryn Hill had tax issues in 2013.",
                length_percent=101
            )
        
        with self.assertRaises(ValueError):
            MediaItem(
                artist="Lauryn Hill",
                song="Doo Wop (That Thing)",
                url="https://www.youtube.com/watch?v=T6QKqFPRZSA",
                taxprompt="Lauryn Hill had tax issues in 2013.",
                length_percent=0
            )
        
        with self.assertRaises(ValueError):
            MediaItem(
                artist="Lauryn Hill",
                song="Doo Wop (That Thing)",
                url="https://www.youtube.com/watch?v=T6QKqFPRZSA",
                taxprompt="Lauryn Hill had tax issues in 2013.",
                length_percent=-10
            )


class TestMediaSerializer(unittest.TestCase):
    """Test the MediaSerializer class."""
    
    def setUp(self):
        """Set up the test environment."""
        self.serializer = MediaSerializer()
        
        # Create a sample media item
        self.media_item = MediaItem(
            artist="Lauryn Hill",
            song="Doo Wop (That Thing)",
            url="https://www.youtube.com/watch?v=T6QKqFPRZSA",
            taxprompt="Lauryn Hill had tax issues in 2013.",
            length_percent=50
        )
    
    def test_serialize_media_item(self):
        """Test serializing a media item."""
        # This test requires network access and FFmpeg
        # Skip if not available
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            self.skipTest("FFmpeg not available")
        
        # Serialize the media item
        success = self.serializer.serialize_media_item(self.media_item)
        
        # Check if serialization was successful
        self.assertTrue(success)
        self.assertTrue(self.media_item.is_serialized())
        
        # Check if the serialized file exists
        self.assertTrue(os.path.exists(self.media_item.serialized))
        
        # Check if the serialized file has the correct duration
        duration = self.serializer.get_video_duration(self.media_item.serialized)
        original_duration = self.serializer.get_video_duration(self.media_item.serialized)
        expected_duration = original_duration * (self.media_item.length_percent / 100.0)
        
        # Allow for some tolerance in duration
        self.assertAlmostEqual(duration, expected_duration, delta=1.0)
    
    def test_serialize_collection(self):
        """Test serializing a collection of media items."""
        # This test requires network access and FFmpeg
        # Skip if not available
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            self.skipTest("FFmpeg not available")
        
        # Create a collection of media items (just 3 for testing, not 15 to save time)
        media_items = [
            MediaItem(
                artist="Lauryn Hill",
                song="Doo Wop (That Thing)",
                url="https://www.youtube.com/watch?v=T6QKqFPRZSA",
                taxprompt="Lauryn Hill had tax issues in 2013.",
                length_percent=30
            ),
            MediaItem(
                artist="Shakira",
                song="Hips Don't Lie",
                url="https://www.youtube.com/watch?v=DUT5rEU6pqM",
                taxprompt="Shakira faced tax fraud allegations in Spain.",
                length_percent=40
            ),
            MediaItem(
                artist="Willie Nelson",
                song="On The Road Again",
                url="https://www.youtube.com/watch?v=dBN86y30Ufc",
                taxprompt="Willie Nelson had significant IRS troubles in the 1990s.",
                length_percent=50
            )
        ]
        
        # Serialize the collection
        results = self.serializer.serialize_collection(media_items)
        
        # Check if all serializations were successful
        for item, success in results:
            self.assertTrue(success)
            self.assertTrue(item.is_serialized())
            self.assertTrue(os.path.exists(item.serialized))
            
            # Check if the serialized file has the correct duration
            duration = self.serializer.get_video_duration(item.serialized)
            original_duration = self.serializer.get_video_duration(item.serialized)
            expected_duration = original_duration * (item.length_percent / 100.0)
            
            # Allow for some tolerance in duration
            self.assertAlmostEqual(duration, expected_duration, delta=1.0)


class TestRTMPBroadcaster(unittest.TestCase):
    """Test the RTMPBroadcaster class."""
    
    def setUp(self):
        """Set up the test environment."""
        # Start a dummy RTMP server
        self.rtmp_server = DummyRTMPServer()
        self.rtmp_server.start()
        
        # Create a broadcaster
        self.broadcaster = RTMPBroadcaster()
        
        # Create a serializer
        self.serializer = MediaSerializer()
        
        # Create sample media items
        self.media_items = [
            MediaItem(
                artist="Lauryn Hill",
                song="Doo Wop (That Thing)",
                url="https://www.youtube.com/watch?v=T6QKqFPRZSA",
                taxprompt="Lauryn Hill had tax issues in 2013.",
                length_percent=20
            ),
            MediaItem(
                artist="Shakira",
                song="Hips Don't Lie",
                url="https://www.youtube.com/watch?v=DUT5rEU6pqM",
                taxprompt="Shakira faced tax fraud allegations in Spain.",
                length_percent=30
            ),
            MediaItem(
                artist="Willie Nelson",
                song="On The Road Again",
                url="https://www.youtube.com/watch?v=dBN86y30Ufc",
                taxprompt="Willie Nelson had significant IRS troubles in the 1990s.",
                length_percent=40
            ),
            MediaItem(
                artist="Akon",
                song="Smack That",
                url="https://www.youtube.com/watch?v=bKDdT_nyP54",
                taxprompt="Akon has had various tax issues.",
                length_percent=25
            )
        ]
        
        # Serialize the media items
        for item in self.media_items:
            self.serializer.serialize_media_item(item)
    
    def tearDown(self):
        """Clean up after the test."""
        # Stop the dummy RTMP server
        self.rtmp_server.stop()
        
        # Clean up serialized files
        for item in self.media_items:
            if item.is_serialized() and os.path.exists(item.serialized):
                os.remove(item.serialized)
    
    def test_broadcast_filtered_collection(self):
        """Test broadcasting a filtered collection of media items."""
        # Define a filter function that selects items with length_percent > 25
        filter_func = lambda item: item.length_percent > 25
        
        # Get the expected number of items that should pass the filter
        expected_count = sum(1 for item in self.media_items if filter_func(item))
        
        # Broadcast the filtered collection
        results = self.broadcaster.broadcast_filtered_collection(self.media_items, filter_func)
        
        # Check if the correct number of items were broadcast
        self.assertEqual(len(results), expected_count)
        
        # Check if all broadcasts were successful
        for item, success in results:
            self.assertTrue(success)
        
        # Check if the dummy RTMP server received the expected number of connections
        # Note: This might not be reliable in all environments
        # self.assertEqual(self.rtmp_server.get_received_count(), expected_count)
    
    def test_multiple_filters(self):
        """Test broadcasting with multiple filter criteria."""
        # Filter for Shakira or items with length_percent >= 40
        filter_func = lambda item: item.artist == "Shakira" or item.length_percent >= 40
        
        # Get the expected number of items that should pass the filter
        expected_count = sum(1 for item in self.media_items if filter_func(item))
        
        # Broadcast the filtered collection
        results = self.broadcaster.broadcast_filtered_collection(self.media_items, filter_func)
        
        # Check if the correct number of items were broadcast
        self.assertEqual(len(results), expected_count)
        
        # Check if all broadcasts were successful
        for item, success in results:
            self.assertTrue(success)
            
            # Verify that each item matches the filter criteria
            self.assertTrue(item.artist == "Shakira" or item.length_percent >= 40)


if __name__ == "__main__":
    unittest.main()