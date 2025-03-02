def tearDown(self):
    """Clean up after the test."""
    # Stop the dummy RTMP server
    if hasattr(self, 'rtmp_server') and self.rtmp_server:
        self.rtmp_server.stop()
    
    # Clean up serialized files
    if hasattr(self, 'media_items'):
        for item in self.media_items:
            if item.is_serialized() and os.path.exists(item.serialized):
                os.remove(item.serialized)