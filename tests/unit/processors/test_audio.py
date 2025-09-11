"""Comprehensive unit tests for AudioProcessor."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import subprocess
import shutil

from fazztv.processors.audio import AudioProcessor
from fazztv.config import constants


class TestAudioProcessor:
    """Test suite for AudioProcessor class."""
    
    @pytest.fixture
    def processor(self):
        """Create AudioProcessor instance."""
        return AudioProcessor()
    
    @pytest.fixture
    def mock_paths(self, tmp_path):
        """Create test paths."""
        return {
            'input': tmp_path / 'input.mp3',
            'output': tmp_path / 'output.mp3',
            'inputs': [
                tmp_path / 'input1.mp3',
                tmp_path / 'input2.mp3',
                tmp_path / 'input3.mp3'
            ]
        }
    
    def test_normalize_audio_success(self, processor, mock_paths):
        """Test successful audio normalization."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = processor.normalize_audio(
                mock_paths['input'],
                mock_paths['output'],
                target_level=-20.0
            )
            
            assert result is True
            mock_run.assert_called_once()
            
            # Check command structure
            cmd = mock_run.call_args[0][0]
            assert 'ffmpeg' in cmd
            assert '-y' in cmd
            assert str(mock_paths['input']) in cmd
            assert str(mock_paths['output']) in cmd
            assert 'loudnorm=I=-20.0:TP=-1.5:LRA=11' in cmd[cmd.index('-af') + 1]
    
    def test_normalize_audio_failure(self, processor, mock_paths):
        """Test audio normalization failure."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1)
            
            result = processor.normalize_audio(
                mock_paths['input'],
                mock_paths['output']
            )
            
            assert result is False
    
    def test_normalize_audio_exception(self, processor, mock_paths):
        """Test audio normalization with exception."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("FFmpeg error")
            
            result = processor.normalize_audio(
                mock_paths['input'],
                mock_paths['output']
            )
            
            assert result is False
    
    def test_add_fade_no_effects(self, processor, mock_paths):
        """Test add_fade with no fade effects."""
        mock_paths['input'].touch()
        
        with patch('shutil.copy') as mock_copy:
            result = processor.add_fade(
                mock_paths['input'],
                mock_paths['output'],
                fade_in=0,
                fade_out=0
            )
            
            assert result is True
            mock_copy.assert_called_once_with(
                mock_paths['input'],
                mock_paths['output']
            )
    
    def test_add_fade_in_only(self, processor, mock_paths):
        """Test add_fade with fade in only."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = processor.add_fade(
                mock_paths['input'],
                mock_paths['output'],
                fade_in=2.0,
                fade_out=0
            )
            
            assert result is True
            cmd = mock_run.call_args[0][0]
            assert 'afade=in:d=2.0' in cmd[cmd.index('-af') + 1]
    
    def test_add_fade_out_only(self, processor, mock_paths):
        """Test add_fade with fade out only."""
        with patch.object(processor, '_get_audio_duration', return_value=10.0):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0)
                
                result = processor.add_fade(
                    mock_paths['input'],
                    mock_paths['output'],
                    fade_in=0,
                    fade_out=2.0
                )
                
                assert result is True
                cmd = mock_run.call_args[0][0]
                assert 'afade=out:st=8.0:d=2.0' in cmd[cmd.index('-af') + 1]
    
    def test_add_fade_both(self, processor, mock_paths):
        """Test add_fade with both fade in and fade out."""
        with patch.object(processor, '_get_audio_duration', return_value=15.0):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0)
                
                result = processor.add_fade(
                    mock_paths['input'],
                    mock_paths['output'],
                    fade_in=1.5,
                    fade_out=2.5
                )
                
                assert result is True
                cmd = mock_run.call_args[0][0]
                filter_arg = cmd[cmd.index('-af') + 1]
                assert 'afade=in:d=1.5' in filter_arg
                assert 'afade=out:st=12.5:d=2.5' in filter_arg
    
    def test_add_fade_failure(self, processor, mock_paths):
        """Test add_fade failure."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1)
            
            result = processor.add_fade(
                mock_paths['input'],
                mock_paths['output'],
                fade_in=1.0
            )
            
            assert result is False
    
    def test_add_fade_exception(self, processor, mock_paths):
        """Test add_fade with exception."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("FFmpeg error")
            
            result = processor.add_fade(
                mock_paths['input'],
                mock_paths['output'],
                fade_in=1.0
            )
            
            assert result is False
    
    def test_mix_audio_no_inputs(self, processor, mock_paths):
        """Test mix_audio with no inputs."""
        result = processor.mix_audio([], mock_paths['output'])
        assert result is False
    
    def test_mix_audio_single_input(self, processor, mock_paths):
        """Test mix_audio with single input."""
        mock_paths['inputs'][0].touch()
        
        with patch('shutil.copy') as mock_copy:
            result = processor.mix_audio(
                [mock_paths['inputs'][0]],
                mock_paths['output']
            )
            
            assert result is True
            mock_copy.assert_called_once_with(
                mock_paths['inputs'][0],
                mock_paths['output']
            )
    
    def test_mix_audio_multiple_inputs_no_weights(self, processor, mock_paths):
        """Test mix_audio with multiple inputs and no weights."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = processor.mix_audio(
                mock_paths['inputs'][:2],
                mock_paths['output']
            )
            
            assert result is True
            cmd = mock_run.call_args[0][0]
            assert 'amix=inputs=2' in cmd[cmd.index('-filter_complex') + 1]
    
    def test_mix_audio_with_weights(self, processor, mock_paths):
        """Test mix_audio with weights."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = processor.mix_audio(
                mock_paths['inputs'],
                mock_paths['output'],
                weights=[0.5, 0.3, 0.2]
            )
            
            assert result is True
            cmd = mock_run.call_args[0][0]
            filter_arg = cmd[cmd.index('-filter_complex') + 1]
            assert "amix=inputs=3:weights='0.5:0.3:0.2'" in filter_arg
    
    def test_mix_audio_mismatched_weights(self, processor, mock_paths):
        """Test mix_audio with mismatched weights length."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = processor.mix_audio(
                mock_paths['inputs'],
                mock_paths['output'],
                weights=[0.5, 0.5]  # Wrong length
            )
            
            assert result is True
            cmd = mock_run.call_args[0][0]
            # Should fall back to no weights
            assert 'amix=inputs=3' in cmd[cmd.index('-filter_complex') + 1]
    
    def test_mix_audio_failure(self, processor, mock_paths):
        """Test mix_audio failure."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1)
            
            result = processor.mix_audio(
                mock_paths['inputs'],
                mock_paths['output']
            )
            
            assert result is False
    
    def test_mix_audio_exception(self, processor, mock_paths):
        """Test mix_audio with exception."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("FFmpeg error")
            
            result = processor.mix_audio(
                mock_paths['inputs'],
                mock_paths['output']
            )
            
            assert result is False
    
    def test_extract_segment_with_duration(self, processor, mock_paths):
        """Test extract_segment with duration."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = processor.extract_segment(
                mock_paths['input'],
                mock_paths['output'],
                start_time=5.0,
                duration=10.0
            )
            
            assert result is True
            cmd = mock_run.call_args[0][0]
            assert '-ss' in cmd
            assert '5.0' in cmd
            assert '-t' in cmd
            assert '10.0' in cmd
    
    def test_extract_segment_with_end_time(self, processor, mock_paths):
        """Test extract_segment with end time."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = processor.extract_segment(
                mock_paths['input'],
                mock_paths['output'],
                start_time=5.0,
                end_time=15.0
            )
            
            assert result is True
            cmd = mock_run.call_args[0][0]
            assert '-ss' in cmd
            assert '5.0' in cmd
            assert '-to' in cmd
            assert '15.0' in cmd
    
    def test_extract_segment_no_duration_or_end(self, processor, mock_paths):
        """Test extract_segment without duration or end time."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = processor.extract_segment(
                mock_paths['input'],
                mock_paths['output'],
                start_time=5.0
            )
            
            assert result is True
            cmd = mock_run.call_args[0][0]
            assert '-ss' in cmd
            assert '5.0' in cmd
            assert '-t' not in cmd
            assert '-to' not in cmd
    
    def test_extract_segment_failure(self, processor, mock_paths):
        """Test extract_segment failure."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1)
            
            result = processor.extract_segment(
                mock_paths['input'],
                mock_paths['output']
            )
            
            assert result is False
    
    def test_extract_segment_exception(self, processor, mock_paths):
        """Test extract_segment with exception."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("FFmpeg error")
            
            result = processor.extract_segment(
                mock_paths['input'],
                mock_paths['output']
            )
            
            assert result is False
    
    def test_apply_effects_no_effects(self, processor, mock_paths):
        """Test apply_effects with no effects."""
        mock_paths['input'].touch()
        
        with patch('shutil.copy') as mock_copy:
            result = processor.apply_effects(
                mock_paths['input'],
                mock_paths['output'],
                []
            )
            
            assert result is True
            mock_copy.assert_called_once_with(
                mock_paths['input'],
                mock_paths['output']
            )
    
    def test_apply_effects_single_effect(self, processor, mock_paths):
        """Test apply_effects with single effect."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = processor.apply_effects(
                mock_paths['input'],
                mock_paths['output'],
                ['atempo=1.5']
            )
            
            assert result is True
            cmd = mock_run.call_args[0][0]
            assert 'atempo=1.5' in cmd[cmd.index('-af') + 1]
    
    def test_apply_effects_multiple_effects(self, processor, mock_paths):
        """Test apply_effects with multiple effects."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            result = processor.apply_effects(
                mock_paths['input'],
                mock_paths['output'],
                ['atempo=1.5', 'volume=0.8', 'highpass=f=200']
            )
            
            assert result is True
            cmd = mock_run.call_args[0][0]
            filter_arg = cmd[cmd.index('-af') + 1]
            assert 'atempo=1.5,volume=0.8,highpass=f=200' == filter_arg
    
    def test_apply_effects_failure(self, processor, mock_paths):
        """Test apply_effects failure."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1)
            
            result = processor.apply_effects(
                mock_paths['input'],
                mock_paths['output'],
                ['atempo=1.5']
            )
            
            assert result is False
    
    def test_apply_effects_exception(self, processor, mock_paths):
        """Test apply_effects with exception."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("FFmpeg error")
            
            result = processor.apply_effects(
                mock_paths['input'],
                mock_paths['output'],
                ['atempo=1.5']
            )
            
            assert result is False
    
    def test_get_audio_duration_success(self, processor, mock_paths):
        """Test _get_audio_duration success."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="120.5\n"
            )
            
            duration = processor._get_audio_duration(mock_paths['input'])
            
            assert duration == 120.5
            cmd = mock_run.call_args[0][0]
            assert 'ffprobe' in cmd
            assert str(mock_paths['input']) in cmd
    
    def test_get_audio_duration_failure(self, processor, mock_paths):
        """Test _get_audio_duration failure."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1)
            
            duration = processor._get_audio_duration(mock_paths['input'])
            
            assert duration is None
    
    def test_get_audio_duration_exception(self, processor, mock_paths):
        """Test _get_audio_duration with exception."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("FFprobe error")
            
            duration = processor._get_audio_duration(mock_paths['input'])
            
            assert duration is None
    
    def test_get_audio_duration_invalid_output(self, processor, mock_paths):
        """Test _get_audio_duration with invalid output."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="not_a_number\n"
            )
            
            duration = processor._get_audio_duration(mock_paths['input'])
            
            assert duration is None
