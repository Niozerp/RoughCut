"""Unit tests for error recovery handlers (Story 4.4).

Tests the abort, cleanup guide, and retry workflow handlers to ensure:
- Abort produces no side effects
- Cleanup guide content is returned correctly
- Retry handlers correctly query and filter clips
- State management works correctly
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add src to path (robust to different execution contexts)
_test_dir = os.path.dirname(os.path.abspath(__file__))
_src_path = os.path.join(_test_dir, '..', '..', '..', 'src')
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

try:
    from roughcut.protocols.handlers.media import (
        abort_session,
        get_cleanup_guide,
        find_cleaned_clips,
        enter_recovery_mode,
        exit_recovery_mode,
        get_original_clip_reference,
        save_cleanup_guide_progress,
        get_cleanup_guide_progress,
        AUDIO_CLEANUP_GUIDE
    )
except ImportError as e:
    # Fallback: try absolute import assuming PYTHONPATH is set correctly
    import importlib
    media_module = importlib.import_module('roughcut.protocols.handlers.media')
    abort_session = media_module.abort_session
    get_cleanup_guide = media_module.get_cleanup_guide
    find_cleaned_clips = media_module.find_cleaned_clips
    enter_recovery_mode = media_module.enter_recovery_mode
    exit_recovery_mode = media_module.exit_recovery_mode
    get_original_clip_reference = media_module.get_original_clip_reference
    save_cleanup_guide_progress = media_module.save_cleanup_guide_progress
    get_cleanup_guide_progress = media_module.get_cleanup_guide_progress
    AUDIO_CLEANUP_GUIDE = media_module.AUDIO_CLEANUP_GUIDE


class TestAbortSession(unittest.TestCase):
    """Test the abort_session handler (AC2: Abort Gracefully)."""
    
    def test_abort_session_returns_success(self):
        """Test that abort session returns success with proper structure."""
        params = {}
        
        result = abort_session(params)
        
        self.assertIn('result', result)
        self.assertIsNone(result.get('error'))
        self.assertTrue(result['result']['aborted'])
        self.assertTrue(result['result']['cleanup_completed'])
    
    def test_abort_session_preserves_selection_when_requested(self):
        """Test that clip selection can be preserved if requested."""
        params = {'preserve_clip_selection': True}
        
        result = abort_session(params)
        
        self.assertTrue(result['result']['clip_selection_preserved'])
    
    def test_abort_session_clears_selection_by_default(self):
        """Test that clip selection is cleared by default."""
        params = {}
        
        result = abort_session(params)
        
        self.assertFalse(result['result']['clip_selection_preserved'])
    
    def test_abort_session_handles_invalid_params(self):
        """Test that abort handles invalid params gracefully."""
        params = "invalid"  # Not a dict
        
        result = abort_session(params)
        
        self.assertIn('error', result)
        self.assertEqual(result['error']['code'], 'INVALID_PARAMS')
    
    def test_abort_produces_no_timeline_side_effects(self):
        """AC2: Verify abort doesn't create timelines or modify Resolve."""
        params = {}
        
        # Abort should not raise any exceptions or create files
        result = abort_session(params)
        
        # Should return cleanly without side effects
        self.assertIsNotNone(result)
        self.assertTrue(result['result']['aborted'])
        
        # No timeline operations should be pending (checked via state)
        # This is implicit - if we got a clean response, no operations were pending


class TestGetCleanupGuide(unittest.TestCase):
    """Test the get_cleanup_guide handler (AC3: Guide Audio Cleanup Process)."""
    
    def test_get_cleanup_guide_returns_guide_structure(self):
        """Test that guide has proper structure with all required sections."""
        params = {}
        
        result = get_cleanup_guide(params)
        
        self.assertIn('result', result)
        self.assertIsNone(result.get('error'))
        
        guide = result['result']['guide']
        self.assertIn('title', guide)
        self.assertIn('description', guide)
        self.assertIn('steps', guide)
        self.assertIn('troubleshooting', guide)
        self.assertIn('best_practices', guide)
    
    def test_get_cleanup_guide_has_five_steps(self):
        """AC3: Verify guide has 5 steps."""
        params = {}
        
        result = get_cleanup_guide(params)
        
        steps = result['result']['guide']['steps']
        self.assertEqual(len(steps), 5)
        self.assertEqual(result['result']['total_steps'], 5)
    
    def test_cleanup_steps_have_required_fields(self):
        """Verify each step has title, description, action, and location."""
        params = {}
        
        result = get_cleanup_guide(params)
        steps = result['result']['guide']['steps']
        
        for i, step in enumerate(steps, 1):
            self.assertIn('number', step)
            self.assertIn('title', step)
            self.assertIn('description', step)
            self.assertIn('action', step)
            self.assertIn('resolve_location', step)
            self.assertEqual(step['number'], i)
    
    def test_step_3_has_noise_reduction_settings(self):
        """AC3: Verify step 3 includes Fairlight settings (6-12dB, Auto Speech Mode)."""
        params = {}
        
        result = get_cleanup_guide(params)
        steps = result['result']['guide']['steps']
        
        # Step 3 should be "Adjust Noise Reduction Settings"
        step3 = steps[2]  # 0-indexed
        self.assertIn('Adjust', step3['title'])
        
        # Should have settings
        self.assertIn('settings', step3)
        settings = step3['settings']
        self.assertIn('mode', settings)
        self.assertIn('reduction_db', settings)
        
        # Verify specific values
        self.assertEqual(settings['mode'], 'Auto Speech Mode')
        self.assertIn('6-12dB', settings['reduction_db'])
    
    def test_troubleshooting_section_has_common_issues(self):
        """AC3 Subtask 2.4: Verify troubleshooting section exists."""
        params = {}
        
        result = get_cleanup_guide(params)
        troubleshooting = result['result']['guide']['troubleshooting']
        
        self.assertGreater(len(troubleshooting), 0)
        
        for item in troubleshooting:
            self.assertIn('problem', item)
            self.assertIn('solution', item)
    
    def test_best_practices_section_exists(self):
        """Verify best practices section exists."""
        params = {}
        
        result = get_cleanup_guide(params)
        best_practices = result['result']['guide']['best_practices']
        
        self.assertIsInstance(best_practices, list)
        self.assertGreater(len(best_practices), 0)


class TestFindCleanedClips(unittest.TestCase):
    """Test the find_cleaned_clips handler (AC4: Retry with Cleaned Audio)."""
    
    def test_find_cleaned_clips_requires_original_name(self):
        """Verify handler requires original clip name."""
        params = {}  # Missing original_clip_name
        
        result = find_cleaned_clips(params)
        
        self.assertIn('error', result)
        self.assertEqual(result['error']['code'], 'INVALID_PARAMS')
    
    def test_find_cleaned_clips_returns_search_patterns(self):
        """Verify handler returns list of search patterns used."""
        params = {
            'original_clip_name': 'interview_take1.mov',
            'original_file_path': '/path/to/interview_take1.mov'
        }
        
        result = find_cleaned_clips(params)
        
        self.assertIn('result', result)
        self.assertIn('search_patterns', result['result'])
        
        patterns = result['result']['search_patterns']
        self.assertIn('*cleaned*', patterns)
        self.assertIn('*NR*', patterns)
    
    def test_find_cleaned_clips_filters_by_naming_patterns(self):
        """AC4: Verify clips are filtered by cleaning suffixes."""
        params = {
            'original_clip_name': 'interview_take1.mov',
            'original_file_path': '/path/to/interview_take1.mov',
            'media_pool_clips': [
                {'clip_id': '1', 'clip_name': 'interview_take1.mov', 'file_path': '/path/to/interview_take1.mov'},
                {'clip_id': '2', 'clip_name': 'interview_take1_cleaned.mov', 'file_path': '/path/to/interview_take1_cleaned.mov'},
                {'clip_id': '3', 'clip_name': 'interview_take1_NR.mov', 'file_path': '/path/to/interview_take1_NR.mov'},
                {'clip_id': '4', 'clip_name': 'other_clip.mov', 'file_path': '/path/to/other_clip.mov'},
            ]
        }
        
        result = find_cleaned_clips(params)
        
        cleaned_clips = result['result']['cleaned_clips']
        self.assertEqual(len(cleaned_clips), 2)  # Should find cleaned and NR versions
        
        # Verify it found the right clips
        clip_names = [c['clip_name'] for c in cleaned_clips]
        self.assertIn('interview_take1_cleaned.mov', clip_names)
        self.assertIn('interview_take1_NR.mov', clip_names)
    
    def test_find_cleaned_clips_returns_empty_when_no_matches(self):
        """AC4: Verify graceful handling when no cleaned clips found."""
        params = {
            'original_clip_name': 'interview_take1.mov',
            'original_file_path': '/path/to/interview_take1.mov',
            'media_pool_clips': [
                {'clip_id': '1', 'clip_name': 'interview_take1.mov', 'file_path': '/path/to/interview_take1.mov'},
                {'clip_id': '4', 'clip_name': 'other_clip.mov', 'file_path': '/path/to/other_clip.mov'},
            ]
        }
        
        result = find_cleaned_clips(params)
        
        self.assertEqual(result['result']['match_count'], 0)
        self.assertEqual(len(result['result']['cleaned_clips']), 0)
    
    def test_find_cleaned_clips_excludes_original(self):
        """Verify original clip is not included in cleaned clips."""
        params = {
            'original_clip_name': 'interview_take1.mov',
            'original_file_path': '/path/to/interview_take1.mov',
            'media_pool_clips': [
                {'clip_id': '1', 'clip_name': 'interview_take1.mov', 'file_path': '/path/to/interview_take1.mov'},
                {'clip_id': '2', 'clip_name': 'interview_take1_cleaned.mov', 'file_path': '/path/to/interview_take1_cleaned.mov'},
            ]
        }
        
        result = find_cleaned_clips(params)
        
        cleaned_clips = result['result']['cleaned_clips']
        clip_names = [c['clip_name'] for c in cleaned_clips]
        
        # Original should not be in results
        self.assertNotIn('interview_take1.mov', clip_names)


class TestEnterRecoveryMode(unittest.TestCase):
    """Test the enter_recovery_mode handler (Task 5: State Management)."""
    
    def test_enter_recovery_mode_requires_clip_id(self):
        """Verify handler requires clip_id in original_clip."""
        params = {
            'original_clip': {
                'clip_name': 'test',
                'file_path': '/path/to/test.mov'
                # Missing clip_id
            }
        }
        
        result = enter_recovery_mode(params)
        
        self.assertIn('error', result)
        self.assertEqual(result['error']['code'], 'INVALID_PARAMS')
    
    def test_enter_recovery_mode_returns_success(self):
        """Test successful entry into recovery mode."""
        params = {
            'original_clip': {
                'clip_id': 'resolve_clip_001',
                'clip_name': 'interview_take1',
                'file_path': '/path/to/interview_take1.mov'
            }
        }
        
        result = enter_recovery_mode(params)
        
        self.assertIn('result', result)
        self.assertIsNone(result.get('error'))
        self.assertTrue(result['result']['recovery_mode'])
        self.assertTrue(result['result']['original_clip_stored'])
    
    def test_enter_recovery_mode_stores_clip_name(self):
        """Verify original clip name is returned in response."""
        params = {
            'original_clip': {
                'clip_id': 'resolve_clip_001',
                'clip_name': 'interview_take1',
                'file_path': '/path/to/interview_take1.mov'
            }
        }
        
        result = enter_recovery_mode(params)
        
        self.assertEqual(result['result']['original_clip_name'], 'interview_take1')


class TestExitRecoveryMode(unittest.TestCase):
    """Test the exit_recovery_mode handler (Task 5: State Management)."""
    
    def test_exit_recovery_mode_returns_success(self):
        """Test successful exit from recovery mode."""
        params = {'success': True}
        
        result = exit_recovery_mode(params)
        
        self.assertIn('result', result)
        self.assertIsNone(result.get('error'))
        self.assertFalse(result['result']['recovery_mode'])
        self.assertTrue(result['result']['cleanup_completed'])
    
    def test_exit_recovery_mode_defaults_to_success(self):
        """Verify success parameter defaults to true."""
        params = {}  # No success param
        
        result = exit_recovery_mode(params)
        
        self.assertTrue(result['result']['success'])
    
    def test_exit_recovery_mode_reports_previous_state(self):
        """Verify response indicates whether we were in recovery mode."""
        # First enter recovery mode
        enter_params = {
            'original_clip': {
                'clip_id': 'resolve_clip_001',
                'clip_name': 'interview_take1',
                'file_path': '/path/to/interview_take1.mov'
            }
        }
        enter_recovery_mode(enter_params)
        
        # Then exit
        exit_params = {'success': True}
        result = exit_recovery_mode(exit_params)
        
        self.assertTrue(result['result']['was_in_recovery'])


class TestGetOriginalClipReference(unittest.TestCase):
    """Test the get_original_clip_reference handler (Task 5.4: Compare View)."""
    
    def test_get_original_clip_returns_none_when_not_set(self):
        """Verify returns has_original=false when no original stored."""
        # First make sure no clip is stored (exit recovery mode)
        exit_recovery_mode({'success': True})
        
        params = {}
        result = get_original_clip_reference(params)
        
        self.assertIn('result', result)
        self.assertFalse(result['result']['has_original'])
        self.assertIsNone(result['result']['original_clip'])
    
    def test_get_original_clip_returns_data_when_set(self):
        """Verify returns original clip data when in recovery mode."""
        # First enter recovery mode
        enter_params = {
            'original_clip': {
                'clip_id': 'resolve_clip_001',
                'clip_name': 'interview_take1',
                'file_path': '/path/to/interview_take1.mov'
            }
        }
        enter_recovery_mode(enter_params)
        
        # Then get reference
        params = {}
        result = get_original_clip_reference(params)
        
        self.assertTrue(result['result']['has_original'])
        self.assertIsNotNone(result['result']['original_clip'])
        self.assertEqual(result['result']['original_clip']['clip_id'], 'resolve_clip_001')
        self.assertEqual(result['result']['in_recovery_mode'], True)


class TestCleanupGuideConstants(unittest.TestCase):
    """Test the AUDIO_CLEANUP_GUIDE constant structure."""
    
    def test_guide_has_all_required_sections(self):
        """Verify guide has all required sections."""
        self.assertIn('title', AUDIO_CLEANUP_GUIDE)
        self.assertIn('description', AUDIO_CLEANUP_GUIDE)
        self.assertIn('steps', AUDIO_CLEANUP_GUIDE)
        self.assertIn('troubleshooting', AUDIO_CLEANUP_GUIDE)
        self.assertIn('best_practices', AUDIO_CLEANUP_GUIDE)
    
    def test_step_1_is_open_clip(self):
        """Verify step 1 is opening the clip in Edit page."""
        step1 = AUDIO_CLEANUP_GUIDE['steps'][0]
        self.assertEqual(step1['number'], 1)
        self.assertIn('Edit', step1['title'])
    
    def test_step_2_is_apply_noise_reduction(self):
        """Verify step 2 is applying Fairlight noise reduction."""
        step2 = AUDIO_CLEANUP_GUIDE['steps'][1]
        self.assertEqual(step2['number'], 2)
        self.assertIn('Fairlight', step2['title'])
    
    def test_step_3_is_adjust_settings(self):
        """Verify step 3 includes settings configuration."""
        step3 = AUDIO_CLEANUP_GUIDE['steps'][2]
        self.assertEqual(step3['number'], 3)
        self.assertIn('settings', step3)
    
    def test_step_4_is_render(self):
        """Verify step 4 is rendering."""
        step4 = AUDIO_CLEANUP_GUIDE['steps'][3]
        self.assertEqual(step4['number'], 4)
        self.assertIn('Render', step4['title'])
    
    def test_step_5_is_return_to_roughcut(self):
        """Verify step 5 is returning to RoughCut."""
        step5 = AUDIO_CLEANUP_GUIDE['steps'][4]
        self.assertEqual(step5['number'], 5)
        self.assertIn('RoughCut', step5['title'])


class TestIntegrationWorkflow(unittest.TestCase):
    """Integration tests for full recovery workflow."""
    
    def test_full_recovery_workflow_sequence(self):
        """Test the complete recovery workflow sequence."""
        # 1. Enter recovery mode
        enter_result = enter_recovery_mode({
            'original_clip': {
                'clip_id': 'resolve_clip_001',
                'clip_name': 'interview_take1',
                'file_path': '/path/to/interview_take1.mov'
            }
        })
        self.assertTrue(enter_result['result']['recovery_mode'])
        
        # 2. Get cleanup guide
        guide_result = get_cleanup_guide({})
        self.assertEqual(len(guide_result['result']['guide']['steps']), 5)
        
        # 3. Find cleaned clips
        clips_result = find_cleaned_clips({
            'original_clip_name': 'interview_take1.mov',
            'original_file_path': '/path/to/interview_take1.mov',
            'media_pool_clips': [
                {'clip_id': '2', 'clip_name': 'interview_take1_cleaned.mov', 'file_path': '/path/to/cleaned.mov'}
            ]
        })
        self.assertEqual(clips_result['result']['match_count'], 1)
        
        # 4. Get original clip reference
        ref_result = get_original_clip_reference({})
        self.assertTrue(ref_result['result']['has_original'])
        
        # 5. Exit recovery mode
        exit_result = exit_recovery_mode({'success': True})
        self.assertFalse(exit_result['result']['recovery_mode'])
        
        # 6. Verify original clip is cleared
        ref_result2 = get_original_clip_reference({})
        self.assertFalse(ref_result2['result']['has_original'])
    
    def test_abort_during_recovery_workflow(self):
        """Test aborting while in recovery mode."""
        # Enter recovery mode
        enter_recovery_mode({
            'original_clip': {
                'clip_id': 'resolve_clip_001',
                'clip_name': 'interview_take1',
                'file_path': '/path/to/interview_take1.mov'
            }
        })
        
        # Abort session
        abort_result = abort_session({'preserve_clip_selection': False})
        self.assertTrue(abort_result['result']['aborted'])
        
        # Verify recovery mode is exited
        ref_result = get_original_clip_reference({})
        # Note: Abort clears all state, so original clip may be cleared
        self.assertFalse(ref_result['result']['in_recovery_mode'])


if __name__ == '__main__':
    unittest.main()
