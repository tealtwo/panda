import unittest
from abc import abstractmethod
from enum import IntFlag


class MadsStates(IntFlag):
  DEFAULT = 0
  RESERVED = 1
  MAIN_BUTTON_AVAILABLE = 2
  LKAS_BUTTON_AVAILABLE = 4


class MadsCommonBase(unittest.TestCase):
  @abstractmethod
  def _lkas_button_msg(self, enabled):
    raise NotImplementedError

  @abstractmethod
  def _main_cruise_button_msg(self, enabled):
    try:
      self._button_msg(enabled)
    except (NotImplementedError, AttributeError):
      self._mads_states_cleanup()
      raise unittest.SkipTest("Skipping test because _button_msg is not implemented for this car. If you know it, please implement it.")

    raise NotImplementedError(
      "Since _button_msg is implemented, _main_cruise_button_msg should be implemented as well to signal the main cruise button press")

  @abstractmethod
  def _acc_state_msg(self, enabled):
    raise NotImplementedError

  def test_enable_control_from_cruise_button_press(self):
    try:
      for enable_mads in (True, False):
        with self.subTest("enable_mads", mads_enabled=enable_mads):
          for cruise_button_press in [True, False]:
            with self.subTest("cruise_button_press", cruise_button_press=cruise_button_press):
              self._mads_states_cleanup()
              self.safety.set_enable_mads(enable_mads, False)
              self._rx(self._main_cruise_button_msg(cruise_button_press))
              self.assertEqual(enable_mads and cruise_button_press, self.safety.get_controls_allowed_lat())
    finally:
      self._mads_states_cleanup()

  def test_enable_control_from_lkas_button_press(self):
    try:
      self._lkas_button_msg(False)
    except NotImplementedError:
      self._mads_states_cleanup()
      raise unittest.SkipTest("Skipping test because _lkas_button_msg is not implemented for this car")

    try:
      for enable_mads in (True, False):
        with self.subTest("enable_mads", mads_enabled=enable_mads):
          for lkas_button_press in [True, False]:
            with self.subTest("lkas_button_press", button_state=lkas_button_press):
              self._mads_states_cleanup()
              self.safety.set_enable_mads(enable_mads, False)
              self._rx(self._lkas_button_msg(lkas_button_press))
              self.assertEqual(enable_mads and lkas_button_press, self.safety.get_controls_allowed_lat())
    finally:
      self._mads_states_cleanup()

  def _mads_states_cleanup(self):
    self.safety.set_main_button_press(-1)
    self.safety.set_lkas_button_press(-1)
    self.safety.set_controls_allowed_lat(False)
    self.safety.set_controls_requested_lat(False)
    self.safety.set_mads_state_flags(0)
    self.safety.set_acc_main_on(False)
    self.safety.set_enable_mads(False, False)

  def test_enable_control_from_setting_main_state_manually(self):
    try:
      for enable_mads in (True, False):
        with self.subTest("enable_mads", mads_enabled=enable_mads):
          for main_button_press in (-1, 0, 1):
            with self.subTest("main_button_press", button_state=main_button_press):
              self._mads_states_cleanup()
              self.safety.set_enable_mads(enable_mads, False)
              self.safety.set_main_button_press(main_button_press)
              self._rx(self._speed_msg(0))
              self.assertEqual(enable_mads and main_button_press == 1, self.safety.get_controls_allowed_lat())
    finally:
      self._mads_states_cleanup()

  def test_enable_control_from_setting_lkas_state_manually(self):
    try:
      for enable_mads in (True, False):
        with self.subTest("enable_mads", mads_enabled=enable_mads):
          for lkas_button_press in (-1, 0, 1):
            with self.subTest("lkas_button_press", button_state=lkas_button_press):
              self._mads_states_cleanup()
              self.safety.set_enable_mads(enable_mads, False)
              self.safety.set_lkas_button_press(lkas_button_press)
              self._rx(self._speed_msg(0))
              self.assertEqual(enable_mads and lkas_button_press == 1, self.safety.get_controls_allowed_lat())
    finally:
      self._mads_states_cleanup()

  def test_mads_state_flags(self):
    try:
      for enable_mads in (True, False):
        with self.subTest("enable_mads", mads_enabled=enable_mads):
          self._mads_states_cleanup()
          self.safety.set_enable_mads(enable_mads, False)
          self.safety.set_main_button_press(0)  # Meaning a message with those buttons was seen and the _prev inside is no longer -1
          self.safety.set_lkas_button_press(0)  # Meaning a message with those buttons was seen and the _prev inside is no longer -1
          self._rx(self._speed_msg(0))
          self.assertTrue(self.safety.get_mads_state_flags() & MadsStates.MAIN_BUTTON_AVAILABLE)
          self.assertTrue(self.safety.get_mads_state_flags() & MadsStates.LKAS_BUTTON_AVAILABLE)
    finally:
      self._mads_states_cleanup()

  def test_enable_control_from_acc_main_on(self):
    """Test that lateral controls are allowed when ACC main is enabled and disabled when ACC main is disabled"""
    try:
      for enable_mads in (True, False):
        with self.subTest("enable_mads", mads_enabled=enable_mads):
          for acc_main_on in (True, False):
            with self.subTest("initial_acc_main", initial_acc_main=acc_main_on):
              self._mads_states_cleanup()
              self.safety.set_enable_mads(enable_mads, False)

              # Set initial state
              self.safety.set_acc_main_on(acc_main_on)
              self._rx(self._speed_msg(0))
              expected_lat = enable_mads and acc_main_on
              self.assertEqual(expected_lat, self.safety.get_controls_allowed_lat(),
                               f"Expected lat: [{expected_lat}] when acc_main_on goes to [{acc_main_on}]")

              # Test transition to opposite state
              self.safety.set_acc_main_on(not acc_main_on)
              self._rx(self._speed_msg(0))
              expected_lat = enable_mads and not acc_main_on
              self.assertEqual(expected_lat, self.safety.get_controls_allowed_lat(),
                               f"Expected lat: [{expected_lat}] when acc_main_on goes from [{acc_main_on}] to [{not acc_main_on}]")

              # Test transition back to initial state
              self.safety.set_acc_main_on(acc_main_on)
              self._rx(self._speed_msg(0))
              expected_lat = enable_mads and acc_main_on
              self.assertEqual(expected_lat, self.safety.get_controls_allowed_lat(),
                               f"Expected lat: [{expected_lat}] when acc_main_on goes from [{not acc_main_on}] to [{acc_main_on}]")
    finally:
      self._mads_states_cleanup()

  def test_controls_requested_lat_from_acc_main_on(self):
    try:
      self.safety.set_acc_main_on(True)
      self._rx(self._speed_msg(0))
      self.assertTrue(self.safety.get_controls_requested_lat())

      self.safety.set_acc_main_on(False)
      self._rx(self._speed_msg(0))
      self.assertFalse(self.safety.get_controls_requested_lat())
    finally:
      self._mads_states_cleanup()

  def test_controls_allowed_must_always_enable_lat(self):
    try:
      for mads_enabled in [True, False]:
        with self.subTest("mads enabled", mads_enabled=mads_enabled):
          self.safety.set_enable_mads(mads_enabled, False)
          for controls_allowed in [True, False]:
            with self.subTest("controls allowed", controls_allowed=controls_allowed):
              self.safety.set_controls_allowed(controls_allowed)
              self.assertEqual(self.safety.get_controls_allowed(), self.safety.get_lat_active())
    finally:
      self._mads_states_cleanup()

  def test_mads_disengage_lat_on_brake_setup(self):
    try:
      for mads_enabled in [True, False]:
        with self.subTest("mads enabled", mads_enabled=mads_enabled):
          for disengage_on_brake in [True, False]:
            with self.subTest("disengage on brake", disengage_on_brake=disengage_on_brake):
              self._mads_states_cleanup()
              self.safety.set_enable_mads(mads_enabled, disengage_on_brake)
              self.assertEqual(disengage_on_brake, self.safety.get_disengage_lat_on_brake())
    finally:
      self._mads_states_cleanup()

  def test_mads_state_flags_mutation(self):
    """Test to catch mutations in bitwise operations for state flags.
    Specifically targets the mutation of & to | in flag checking operations.
    Tests both setting and clearing of flags to catch potential bitwise operation mutations."""

    try:
      # Test both MADS enabled and disabled states
      for enable_mads in (True, False):
        with self.subTest("enable_mads", mads_enabled=enable_mads):
          self._mads_states_cleanup()
          self.safety.set_enable_mads(enable_mads, False)

          # Initial state - both flags should be unset
          self._rx(self._speed_msg(0))
          initial_flags = self.safety.get_mads_state_flags()
          self.assertEqual(initial_flags & MadsStates.MAIN_BUTTON_AVAILABLE, MadsStates.DEFAULT)  # Main button flag
          self.assertEqual(initial_flags & MadsStates.LKAS_BUTTON_AVAILABLE, MadsStates.DEFAULT)  # LKAS button flag

          # Set only main button
          self.safety.set_main_button_press(0)
          self._rx(self._speed_msg(0))
          main_only_flags = self.safety.get_mads_state_flags()
          self.assertEqual(main_only_flags & MadsStates.MAIN_BUTTON_AVAILABLE,
                           MadsStates.MAIN_BUTTON_AVAILABLE)  # Main button flag should be set
          self.assertEqual(main_only_flags & MadsStates.LKAS_BUTTON_AVAILABLE, MadsStates.DEFAULT)  # LKAS button flag should still be unset

          # Set LKAS button and verify both flags
          self.safety.set_lkas_button_press(0)
          self._rx(self._speed_msg(0))
          both_flags = self.safety.get_mads_state_flags()
          self.assertEqual(both_flags & MadsStates.MAIN_BUTTON_AVAILABLE,
                           MadsStates.MAIN_BUTTON_AVAILABLE)  # Main button flag should remain set
          self.assertEqual(both_flags & MadsStates.LKAS_BUTTON_AVAILABLE, MadsStates.LKAS_BUTTON_AVAILABLE)  # LKAS button flag should be set

          # Verify that using | instead of & would give different results
          self.assertNotEqual(both_flags & MadsStates.MAIN_BUTTON_AVAILABLE, both_flags | MadsStates.MAIN_BUTTON_AVAILABLE)
          self.assertNotEqual(both_flags & MadsStates.LKAS_BUTTON_AVAILABLE, both_flags | MadsStates.LKAS_BUTTON_AVAILABLE)

          # Reset flags and verify they're cleared
          self._mads_states_cleanup()
          self._rx(self._speed_msg(0))
          cleared_flags = self.safety.get_mads_state_flags()
          self.assertEqual(cleared_flags & MadsStates.MAIN_BUTTON_AVAILABLE, MadsStates.DEFAULT)
          self.assertEqual(cleared_flags & MadsStates.LKAS_BUTTON_AVAILABLE, MadsStates.DEFAULT)
    finally:
      self._mads_states_cleanup()

  def test_mads_state_flags_persistence(self):
    """Test to verify that state flags remain set once buttons are seen"""

    try:
      for enable_mads in (True, False):
        with self.subTest("enable_mads", mads_enabled=enable_mads):
          self._mads_states_cleanup()
          self.safety.set_enable_mads(enable_mads, False)

          # Set main button and verify flag
          self.safety.set_main_button_press(0)
          self._rx(self._speed_msg(0))
          self.assertEqual(self.safety.get_mads_state_flags() & MadsStates.MAIN_BUTTON_AVAILABLE, MadsStates.MAIN_BUTTON_AVAILABLE)

          # Reset main button to -1, flag should persist
          self.safety.set_main_button_press(-1)
          self._rx(self._speed_msg(0))
          self.assertEqual(self.safety.get_mads_state_flags() & MadsStates.MAIN_BUTTON_AVAILABLE, MadsStates.MAIN_BUTTON_AVAILABLE)

          # Set LKAS button and verify both flags
          self.safety.set_lkas_button_press(0)
          self._rx(self._speed_msg(0))
          flags = self.safety.get_mads_state_flags()
          self.assertEqual(flags & MadsStates.MAIN_BUTTON_AVAILABLE, MadsStates.MAIN_BUTTON_AVAILABLE)
          self.assertEqual(flags & MadsStates.LKAS_BUTTON_AVAILABLE, MadsStates.LKAS_BUTTON_AVAILABLE)
    finally:
      self._mads_states_cleanup()

  def test_mads_state_flags_individual_control(self):
    """Test the ability to individually control state flags.
    Verifies that flags can be set and cleared independently."""

    try:
      for enable_mads in (True, False):
        with self.subTest("enable_mads", mads_enabled=enable_mads):
          self._mads_states_cleanup()
          self.safety.set_enable_mads(enable_mads, False)

          # Set main button flag only
          self.safety.set_main_button_press(0)
          self._rx(self._speed_msg(0))
          main_flags = self.safety.get_mads_state_flags()
          self.assertEqual(main_flags & MadsStates.MAIN_BUTTON_AVAILABLE, MadsStates.MAIN_BUTTON_AVAILABLE)
          self.assertEqual(main_flags & MadsStates.LKAS_BUTTON_AVAILABLE, MadsStates.DEFAULT)

          # Reset flags and set LKAS only
          self._mads_states_cleanup()
          self.safety.set_lkas_button_press(0)
          self._rx(self._speed_msg(0))
          lkas_flags = self.safety.get_mads_state_flags()
          self.assertEqual(lkas_flags & MadsStates.MAIN_BUTTON_AVAILABLE, MadsStates.DEFAULT)
          self.assertEqual(lkas_flags & MadsStates.LKAS_BUTTON_AVAILABLE, MadsStates.LKAS_BUTTON_AVAILABLE)

          # Set both flags
          self._mads_states_cleanup()
          self.safety.set_main_button_press(0)
          self.safety.set_lkas_button_press(0)
          self._rx(self._speed_msg(0))
          both_flags = self.safety.get_mads_state_flags()
          self.assertEqual(both_flags & MadsStates.MAIN_BUTTON_AVAILABLE, MadsStates.MAIN_BUTTON_AVAILABLE)
          self.assertEqual(both_flags & MadsStates.LKAS_BUTTON_AVAILABLE, MadsStates.LKAS_BUTTON_AVAILABLE)

          # Clear all flags and verify
          self._mads_states_cleanup()
          self._rx(self._speed_msg(0))
          final_flags = self.safety.get_mads_state_flags()
          self.assertEqual(final_flags & MadsStates.MAIN_BUTTON_AVAILABLE, MadsStates.DEFAULT)
          self.assertEqual(final_flags & MadsStates.LKAS_BUTTON_AVAILABLE, MadsStates.DEFAULT)
    finally:
      self._mads_states_cleanup()

  def test_enable_and_disable_lateral_control_with_cruise_button_only(self):
    """Test Scenario 1: Car with only cruise button, toggle MADS with cruise button"""
    try:
      self._mads_states_cleanup()
      self.safety.set_enable_mads(True, False)

      self._rx(self._main_cruise_button_msg(True))
      self._rx(self._main_cruise_button_msg(False))
      self.assertTrue(self.safety.get_controls_allowed_lat())

      self._rx(self._main_cruise_button_msg(True))
      self._rx(self._main_cruise_button_msg(False))
      self.assertFalse(self.safety.get_controls_allowed_lat())
    finally:
      self._mads_states_cleanup()

  def test_enable_and_disable_lateral_control_with_cruise_button_when_lfa_present(self):
    """Test Scenario 2: Car with both buttons, toggle MADS with cruise button"""
    try:
      self._lkas_button_msg(False)
    except NotImplementedError:
      raise unittest.SkipTest("Skipping test because LKAS button not supported")

    try:
      self._mads_states_cleanup()
      self.safety.set_enable_mads(True, False)

      self._rx(self._main_cruise_button_msg(True))
      self._rx(self._main_cruise_button_msg(False))
      self.assertTrue(self.safety.get_controls_allowed_lat())

      self._rx(self._main_cruise_button_msg(True))
      self._rx(self._main_cruise_button_msg(False))
      self.assertFalse(self.safety.get_controls_allowed_lat())
    finally:
      self._mads_states_cleanup()

  def test_enable_lateral_control_with_cruise_and_disable_with_lfa(self):
    """Test Scenario 3: Enable with cruise, disable with LFA"""
    try:
      self._lkas_button_msg(False)
    except NotImplementedError:
      raise unittest.SkipTest("Skipping test because LKAS button not supported")

    try:
      self._mads_states_cleanup()
      self.safety.set_enable_mads(True, False)

      self._rx(self._main_cruise_button_msg(True))
      self._rx(self._main_cruise_button_msg(False))
      self.assertTrue(self.safety.get_controls_allowed_lat())

      self._rx(self._lkas_button_msg(True))
      self._rx(self._lkas_button_msg(False))
      self.assertFalse(self.safety.get_controls_allowed_lat())
    finally:
      self._mads_states_cleanup()

  def test_enable_lateral_control_with_lfa_and_disable_with_cruise(self):
    """Test Scenario 4: Enable with LFA, disable with cruise"""
    try:
      self._lkas_button_msg(False)
    except NotImplementedError:
      raise unittest.SkipTest("Skipping test because LKAS button not supported")

    try:
      self._mads_states_cleanup()
      self.safety.set_enable_mads(True, False)

      self._rx(self._lkas_button_msg(True))
      self._rx(self._lkas_button_msg(False))
      self.assertTrue(self.safety.get_controls_allowed_lat())

      self._rx(self._main_cruise_button_msg(True))
      self._rx(self._main_cruise_button_msg(False))
      self.assertFalse(self.safety.get_controls_allowed_lat())
    finally:
      self._mads_states_cleanup()

  def test_enable_and_disable_lateral_control_with_lfa_button(self):
    """Test Scenario 5: Toggle MADS with LFA button"""
    try:
      self._lkas_button_msg(False)
    except NotImplementedError:
      raise unittest.SkipTest("Skipping test because LKAS button not supported")

    try:
      self._mads_states_cleanup()
      self.safety.set_enable_mads(True, False)

      self._rx(self._lkas_button_msg(True))
      self._rx(self._lkas_button_msg(False))
      self.assertTrue(self.safety.get_controls_allowed_lat())

      self._rx(self._lkas_button_msg(True))
      self._rx(self._lkas_button_msg(False))
      self.assertFalse(self.safety.get_controls_allowed_lat())
    finally:
      self._mads_states_cleanup()
