#pragma once

// ===============================
// Type Definitions and Enums
// ===============================

// Button state enumeration
typedef enum __attribute__((packed)) {
  MADS_BUTTON_UNAVAILABLE = -1,
  MADS_BUTTON_NOT_PRESSED = 0,
  MADS_BUTTON_PRESSED = 1
} ButtonState;

// State transition enumeration
typedef enum __attribute__((packed)) {
  MADS_TRANSITION_NO_CHANGE = 0,
  MADS_TRANSITION_TO_ACTIVE = 1,
  MADS_TRANSITION_TO_INACTIVE = 2
} StateTransition;

// Disengage reason enumeration
typedef enum __attribute__((packed)) {
  MADS_DISENGAGE_REASON_NONE = 0,
  MADS_DISENGAGE_REASON_BRAKE = 1,
  MADS_DISENGAGE_REASON_LAG = 2,
  MADS_DISENGAGE_REASON_BUTTON = 3,
  MADS_DISENGAGE_REASON_ACC_MAIN_OFF = 4
} DisengageReason;

// ===============================
// Constants and Defines
// ===============================

#define ALT_EXP_ENABLE_MADS 1024
#define ALT_EXP_DISABLE_DISENGAGE_LATERAL_ON_BRAKE 2048

#define MISMATCH_DEFAULT_THRESHOLD 25
#define MADS_STATE_FLAG_DEFAULT 0U
#define MADS_STATE_FLAG_RESERVED 1U
#define MADS_STATE_FLAG_MAIN_BUTTON_AVAILABLE 2U
#define MADS_STATE_FLAG_LKAS_BUTTON_AVAILABLE 4U

// ===============================
// Data Structures
// ===============================

// Structure to track disengagement state
typedef struct {
  DisengageReason reason;
  bool can_auto_resume;
  uint32_t timestamp;
} DisengageState;

// Button state tracking structure
typedef struct {
  const ButtonState *current;
  ButtonState last;
  StateTransition transition;
  uint32_t press_timestamp;
} ButtonStateTracking;

// ACC state structure
typedef struct {
  const bool *current;
  bool previous : 1;
  uint16_t mismatch_count;
  uint16_t mismatch_threshold;
} ACCState;

// Main MADS state structure
typedef struct {
  uint32_t state_flags;
  const bool *is_vehicle_moving_ptr;
  
  ButtonStateTracking main_button;
  ButtonStateTracking lkas_button;
  ACCState acc_main;
  
  DisengageState current_disengage;
  DisengageState previous_disengage;
  
  bool system_enabled : 1;
  bool disengage_lateral_on_brake : 1;
  bool is_braking : 1;
  bool cruise_engaged : 1;
  bool controls_requested_lat : 1;
  bool controls_allowed_lat : 1;
} MADSState;

// ===============================
// Global Variables
// ===============================

extern ButtonState main_button_press;
ButtonState main_button_press = MADS_BUTTON_UNAVAILABLE;

extern ButtonState lkas_button_press;
ButtonState lkas_button_press = MADS_BUTTON_UNAVAILABLE;

static MADSState m_mads_state;

// ===============================
// Function Declarations
// ===============================

// Core system functions
extern const MADSState* get_mads_state(void);
extern void mads_set_system_state(bool enabled, bool disengage_lateral_on_brake);
extern void mads_state_update(const bool *op_vehicle_moving, const bool *op_acc_main, bool is_braking, bool cruise_engaged);
extern void mads_exit_controls(DisengageReason reason);
extern bool mads_is_lateral_control_allowed_by_mads(void);

// Internal helper functions
static void m_mads_state_init(void);
static bool m_can_allow_controls_lat(void);
static StateTransition m_get_binary_transition(bool is_active, bool was_active);
static void m_mads_check_braking(bool is_braking);
static void m_update_button_state(ButtonStateTracking *button_state, const ButtonState *button_press);
static void m_update_acc_main_state(void);
static void m_mads_try_allow_controls_lat(void);

// ===============================
// Function Implementations
// ===============================

// Core system functions
inline const MADSState* get_mads_state(void) {
  return &m_mads_state;
}

inline void mads_set_system_state(bool enabled, bool disengage_lateral_on_brake) {
  m_mads_state_init();
  m_mads_state.system_enabled = enabled;
  m_mads_state.disengage_lateral_on_brake = disengage_lateral_on_brake;
}

inline void mads_exit_controls(DisengageReason reason) {
  if (reason == MADS_DISENGAGE_REASON_ACC_MAIN_OFF) {
    m_mads_state.controls_requested_lat = false;
  }
  
  if (m_mads_state.controls_allowed_lat) {
    m_mads_state.previous_disengage = m_mads_state.current_disengage;
    m_mads_state.current_disengage.reason = reason;
    m_mads_state.current_disengage.timestamp = microsecond_timer_get();
    m_mads_state.controls_allowed_lat = false;
  }
}

inline bool mads_is_lateral_control_allowed_by_mads(void) {
  return m_mads_state.system_enabled && m_mads_state.controls_allowed_lat;
}

inline void mads_state_update(const bool *op_vehicle_moving, const bool *op_acc_main, bool is_braking, bool cruise_engaged) {
  if (m_mads_state.is_vehicle_moving_ptr == NULL) {
    m_mads_state.is_vehicle_moving_ptr = op_vehicle_moving;
  }

  if (m_mads_state.acc_main.current == NULL) {
    m_mads_state.acc_main.current = op_acc_main;
  }

  if (!(m_mads_state.state_flags & MADS_STATE_FLAG_MAIN_BUTTON_AVAILABLE) && (main_button_press != MADS_BUTTON_UNAVAILABLE)) {
    m_mads_state.state_flags |= MADS_STATE_FLAG_MAIN_BUTTON_AVAILABLE;
  }

  if (!(m_mads_state.state_flags & MADS_STATE_FLAG_LKAS_BUTTON_AVAILABLE) && (lkas_button_press != MADS_BUTTON_UNAVAILABLE)) {
    m_mads_state.state_flags |= MADS_STATE_FLAG_LKAS_BUTTON_AVAILABLE;
  }

  m_update_button_state(&m_mads_state.main_button, &main_button_press);
  m_update_button_state(&m_mads_state.lkas_button, &lkas_button_press);
  m_update_acc_main_state();

  m_mads_state.cruise_engaged = cruise_engaged;
  m_mads_check_braking(is_braking);
  m_mads_try_allow_controls_lat();
}

// Internal helper functions
static void m_mads_state_init(void) {
  m_mads_state.is_vehicle_moving_ptr = NULL;
  m_mads_state.acc_main.current = NULL;
  m_mads_state.main_button.current = &main_button_press;
  m_mads_state.lkas_button.current = &lkas_button_press;
  m_mads_state.state_flags = MADS_STATE_FLAG_DEFAULT;

  m_mads_state.system_enabled = false;
  m_mads_state.disengage_lateral_on_brake = true;

  m_mads_state.main_button.last = MADS_BUTTON_UNAVAILABLE;
  m_mads_state.main_button.transition = MADS_TRANSITION_NO_CHANGE;
  m_mads_state.main_button.press_timestamp = 0;

  m_mads_state.lkas_button.last = MADS_BUTTON_UNAVAILABLE;
  m_mads_state.lkas_button.transition = MADS_TRANSITION_NO_CHANGE;
  m_mads_state.lkas_button.press_timestamp = 0;

  m_mads_state.acc_main.previous = false;
  m_mads_state.acc_main.mismatch_count = 0;
  m_mads_state.acc_main.mismatch_threshold = MISMATCH_DEFAULT_THRESHOLD;

  m_mads_state.current_disengage.reason = MADS_DISENGAGE_REASON_NONE;
  m_mads_state.current_disengage.can_auto_resume = false;
  m_mads_state.current_disengage.timestamp = 0;
  m_mads_state.previous_disengage = m_mads_state.current_disengage;

  m_mads_state.is_braking = false;
  m_mads_state.cruise_engaged = false;
  m_mads_state.controls_requested_lat = false;
  m_mads_state.controls_allowed_lat = false;
}

static bool m_can_allow_controls_lat(void) {
  const MADSState *state = get_mads_state();
  bool result = false;
  if (state->system_enabled) {
    switch (state->current_disengage.reason) {
      case MADS_DISENGAGE_REASON_BRAKE:
        result = !state->is_braking && state->disengage_lateral_on_brake;
        break;
      case MADS_DISENGAGE_REASON_LAG:
      case MADS_DISENGAGE_REASON_BUTTON:
      case MADS_DISENGAGE_REASON_NONE:
      default:
        result = true;
        break;
    }
  }
  return result;
}

static StateTransition m_get_binary_transition(bool is_active, bool was_active) {
  if (is_active && !was_active) {
    return MADS_TRANSITION_TO_ACTIVE;
  }
  if (!is_active && was_active) {
    return MADS_TRANSITION_TO_INACTIVE;
  }
  return MADS_TRANSITION_NO_CHANGE;
}

static void m_mads_check_braking(bool is_braking) {
  bool was_braking = m_mads_state.is_braking;
  if (is_braking && (!was_braking || *m_mads_state.is_vehicle_moving_ptr) && m_mads_state.disengage_lateral_on_brake) {
    mads_exit_controls(MADS_DISENGAGE_REASON_BRAKE);
  }
  
  m_mads_state.is_braking = is_braking;
}

static void m_update_button_state(ButtonStateTracking *button_state, const ButtonState *button_press) {
  if (*button_press != MADS_BUTTON_UNAVAILABLE) {
    button_state->current = button_press;
    button_state->transition = m_get_binary_transition(
        *button_state->current == MADS_BUTTON_PRESSED,
        button_state->last == MADS_BUTTON_PRESSED
    );

    if (button_state->transition == MADS_TRANSITION_TO_ACTIVE) {
      m_mads_state.controls_requested_lat = !m_mads_state.controls_allowed_lat;
      if (!m_mads_state.controls_requested_lat) {
        mads_exit_controls(MADS_DISENGAGE_REASON_BUTTON);
      }
    }

    button_state->last = *button_state->current;
  }
}

static void m_update_acc_main_state(void) {
  StateTransition transition = m_get_binary_transition(
      *m_mads_state.acc_main.current,
      m_mads_state.acc_main.previous
  );

  if (transition == MADS_TRANSITION_TO_ACTIVE) {
    m_mads_state.controls_requested_lat = true;
  } else if (transition == MADS_TRANSITION_TO_INACTIVE) {
    mads_exit_controls(MADS_DISENGAGE_REASON_ACC_MAIN_OFF);
  }
  
  m_mads_state.acc_main.previous = *m_mads_state.acc_main.current;
}

static void m_mads_try_allow_controls_lat(void) {
  if (m_mads_state.controls_requested_lat && !m_mads_state.controls_allowed_lat && m_can_allow_controls_lat()) {
    m_mads_state.controls_allowed_lat = true;
    m_mads_state.previous_disengage = m_mads_state.current_disengage;
    m_mads_state.current_disengage.reason = MADS_DISENGAGE_REASON_NONE;
  }
}