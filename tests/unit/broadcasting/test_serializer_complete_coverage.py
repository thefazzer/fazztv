"""Tests to achieve 100% coverage for fazztv.broadcasting.serializer."""

import pytest
from unittest.mock import Mock, patch, MagicMock, call, mock_open, PropertyMock
import os
import json
import time
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
import asyncio

# Import the module to test
from fazztv.broadcasting.serializer import *

