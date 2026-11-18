"""Tests for the reported v2.0 self-attachment bug."""
import unittest

from autopick.windows import GameWindow, choose_unambiguous, discover_game_windows, game_score


class WindowRecognitionTests(unittest.TestCase):
    def test_app_title_is_rejected_even_though_it_says_azeroth(self):
        self.assertLess(game_score('Azeroth AutoPick — The Build Forge v2', r'C:\Python312\python.exe'),0)

    def test_app_process_rejected_regardless_of_title(self):
        self.assertLess(game_score('Azeroth Survivors',r'C:\Python312\python.exe',own_process=True),0)

    def test_native_game_executable(self):
        self.assertGreaterEqual(game_score('Game Client',r'C:\games\AzerothSurvivors.exe'),100)

    def test_native_game_title(self):
        self.assertGreaterEqual(game_score('Azeroth Survivors',r'C:\games\anygame.exe'),100)

    def test_browser_game_tab_title(self):
        self.assertGreaterEqual(game_score('Azeroth Survivors - Google Chrome',r'C:\Chrome\chrome.exe'),100)

    def test_browser_without_game_title_not_guessed(self):
        self.assertEqual(game_score('Google - Mozilla Firefox',r'C:\firefox.exe'),0)

    def test_wow_client(self):
        self.assertGreater(game_score('World of Warcraft',r'C:\Games\Wow.exe'),60)

    def test_single_candidate_automatically_selected(self):
        only=GameWindow(33,'Azeroth Survivors','AzerothSurvivors.exe',541,130)
        self.assertEqual(choose_unambiguous([only]),only)

    def test_ambiguous_multiple_games_requires_selection(self):
        a=GameWindow(33,'Azeroth Survivors','AzerothSurvivors.exe',541,130)
        b=GameWindow(45,'Azeroth Survivors (2)','AzerothSurvivors.exe',573,130)
        self.assertIsNone(choose_unambiguous([a,b]))

    def test_high_confidence_game_over_lower_confidence_alt(self):
        a=GameWindow(33,'Azeroth Survivors','AzerothSurvivors.exe',541,130)
        b=GameWindow(45,'World of Warcraft','Unknown.exe',573,70)
        self.assertEqual(choose_unambiguous([b,a]),a)

    def test_empty_candidates_never_guessed(self):
        self.assertIsNone(choose_unambiguous([]))

    def test_not_running_on_non_windows_is_empty(self):
        import os
        if os.name != 'nt':
            self.assertEqual(discover_game_windows(),[])

if __name__=='__main__': unittest.main()
