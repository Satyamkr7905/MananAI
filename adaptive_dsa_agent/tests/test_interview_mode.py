"""Tests for interview-mode helper behavior in tutor service."""

from __future__ import annotations

import unittest

from server.tutor_service import _calibration_band, _confidence_to_unit_scale, _is_interview_mode


class InterviewModeHelperTests(unittest.TestCase):
    def test_mode_detection(self) -> None:
        self.assertTrue(_is_interview_mode("interview"))
        self.assertTrue(_is_interview_mode(" Interview "))
        self.assertFalse(_is_interview_mode("practice"))
        self.assertFalse(_is_interview_mode(None))

    def test_confidence_conversion(self) -> None:
        self.assertEqual(_confidence_to_unit_scale(70), 0.7)
        self.assertEqual(_confidence_to_unit_scale(0.4), 0.4)
        self.assertEqual(_confidence_to_unit_scale(120), 1.0)
        self.assertIsNone(_confidence_to_unit_scale(None))

    def test_calibration_band(self) -> None:
        self.assertEqual(_calibration_band(0.10), "well_calibrated")
        self.assertEqual(_calibration_band(0.30), "slightly_miscalibrated")
        self.assertEqual(_calibration_band(0.50), "poorly_calibrated")


if __name__ == "__main__":
    unittest.main()
