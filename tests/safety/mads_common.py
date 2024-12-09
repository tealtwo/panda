import unittest
from abc import abstractmethod


class MadsCommonBase(unittest.TestCase):
  @abstractmethod
  def _lkas_button_msg(self, enabled):
    raise NotImplementedError

  @abstractmethod
  def _acc_state_msg(self, enabled):
    raise NotImplementedError

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
    self.safety.set_lkas_button_press(-1)
    self.safety.set_controls_allowed_lat(False)
    self.safety.set_controls_requested_lat(False)
    self.safety.set_acc_main_on(False)
    self.safety.set_enable_mads(False, False)

  def test_enable_control_from_setting_main_cruise_manually(self):
    try:
      self._acc_state_msg(False)
    except NotImplementedError:
      self._mads_states_cleanup()
      raise unittest.SkipTest("Skipping test because _acc_state_msg is not implemented for this car")

    try:
      for enable_mads in (True, False):
        with self.subTest("enable_mads", mads_enabled=enable_mads):
          for acc_main_on in (True, False):
            with self.subTest("acc_main_on", button_state=acc_main_on):
              self._mads_states_cleanup()
              self.safety.set_enable_mads(enable_mads, False)
              self._rx(self._acc_state_msg(acc_main_on))
              self._rx(self._speed_msg(0))
              self.assertEqual(enable_mads and acc_main_on, self.safety.get_controls_allowed_lat())
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

  def test_lkas_button_press_with_main_cruise(self):
    """Test that LKAS/LFA button presses don't disengage controls when main cruise is on"""
    try:
      self._lkas_button_msg(False)
    except NotImplementedError:
      raise unittest.SkipTest("Skipping test because LKAS button not supported")

    try:
      self._mads_states_cleanup()
      self.safety.set_enable_mads(True, False)
      self.safety.set_acc_main_on(True)
      self.assertFalse(self.safety.get_controls_allowed_lat())

      # Enable controls initially with LKAS button
      self._rx(self._lkas_button_msg(True))
      self._rx(self._lkas_button_msg(False))
      self._rx(self._speed_msg(0))
      self.assertTrue(self.safety.get_controls_allowed_lat())

      # Test LKAS button press while ACC main is on
      self._rx(self._lkas_button_msg(True))
      self._rx(self._lkas_button_msg(False))
      self._rx(self._speed_msg(0))

      # Controls should be disabled
      self.assertFalse(self.safety.get_controls_allowed_lat(),
                      "Controls should be disabled with LKAS button press while ACC main is on")
    finally:
      self._mads_states_cleanup()

  def test_enable_lateral_control_with_lfa_and_disable_with_main_cruise(self):
    """Tests main cruise and LKAS button state transitions.

      Sequence:
      1. Main cruise off -> on
      2. LKAS button disengage
      3. LKAS button engage
      4. Main cruise off

    """
    try:
      self._lkas_button_msg(False)
    except NotImplementedError:
      raise unittest.SkipTest("Skipping test because LKAS button not supported")

    try:
      self._acc_state_msg(False)
    except NotImplementedError:
      self._mads_states_cleanup()
      raise unittest.SkipTest("Skipping test because _acc_state_msg is not implemented for this car")

    try:
      self._mads_states_cleanup()
      self.safety.set_enable_mads(True, False)

      self._rx(self._acc_state_msg(True))
      self._rx(self._speed_msg(0))
      self.assertTrue(self.safety.get_controls_allowed_lat())

      self._rx(self._lkas_button_msg(True))
      self._rx(self._lkas_button_msg(False))
      self.assertFalse(self.safety.get_controls_allowed_lat())

      self._rx(self._lkas_button_msg(True))
      self._rx(self._lkas_button_msg(False))
      self.assertTrue(self.safety.get_controls_allowed_lat())

      self._rx(self._acc_state_msg(False))
      self._rx(self._speed_msg(0))
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

  def test_enable_lateral_control_with_controls_allowed_rising_edge(self):
    try:
      self._mads_states_cleanup()
      self.safety.set_enable_mads(True, False)
      self.safety.set_controls_allowed(False)
      self._rx(self._speed_msg(0))
      self.safety.set_controls_allowed(True)
      self._rx(self._speed_msg(0))
      self.assertTrue(self.safety.get_controls_allowed())
      self.assertTrue(self.safety.get_controls_allowed_lat())
    finally:
      self._mads_states_cleanup()
