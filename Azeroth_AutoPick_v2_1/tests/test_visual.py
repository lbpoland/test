import unittest
from PIL import Image, ImageDraw
from autopick.visual import reroll_visual_state


class VisualSafetyTests(unittest.TestCase):
    def test_sample_screenshot_free(self):
        # The uploaded screenshot itself is not packaged into the release.
        from pathlib import Path
        image = Path('/mnt/data/Screenshot (5321).png')
        if image.exists():
            self.assertEqual(reroll_visual_state(Image.open(image)), 'free-looking')

    def test_sample_screenshot_paid(self):
        from pathlib import Path
        image = Path('/mnt/data/Screenshot (5322).png')
        if image.exists():
            self.assertEqual(reroll_visual_state(Image.open(image)), 'paid-looking')

    def test_dark_button_unknown(self):
        self.assertEqual(reroll_visual_state(Image.new('RGB', (1920, 1080), (30, 12, 9))), 'unknown')

    def test_many_red_pixels_blocks(self):
        im = Image.new('RGB', (1920, 1080), (30, 12, 9))
        d = ImageDraw.Draw(im)
        d.rectangle((1300, 926, 1320, 940), fill=(229, 38, 28))
        self.assertEqual(reroll_visual_state(im), 'paid-looking')

if __name__ == '__main__':
    unittest.main()
