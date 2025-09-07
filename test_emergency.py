#!/usr/bin/env python3
"""
An improved console script to test the emergency detection pipeline in a live environment
by connecting to FlightGear with startup grace period and manual reset functionality.
"""
import threading
import time
import logging
import os
import queue
import joblib
import sys
import subprocess

# --- Correcting Python Path for Imports ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = script_dir
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Project Imports ---
from helpers.flightgear import try_connect_fg, find_fgfs_executable, get_prop
from shallnotcrash.emergency.core import detect_emergency
from shallnotcrash.emergency.analyzers.anomaly_detector import ANOMALY_DETECTOR, FlightPhase
from shallnotcrash.constants.flightgear import FGProps

# --- Global State Dictionary ---
state = {
    'fg_interface': None,
    'fg_connected': False,
    'pattern_recognizer': None,
    'reset_requested': False,
}

# --- Pathing and Global Instances ---
MODEL_PATH = os.path.join(project_root, "models", "c172p_emergency_model_improved.joblib")
anomaly_detector = ANOMALY_DETECTOR

def input_worker(state: dict):
    """Handle user input for manual reset"""
    while True:
        try:
            user_input = input().strip().lower()
            if user_input in ['r', 'reset']:
                state['reset_requested'] = True
                print("\n[RESET REQUESTED] Emergency detection system will reset on next cycle...")
            elif user_input in ['q', 'quit', 'exit']:
                print("\n[QUIT] Shutting down...")
                os._exit(0)
            elif user_input in ['h', 'help']:
                print("\nCommands:")
                print("  r, reset - Reset emergency detection system")
                print("  h, help  - Show this help")
                print("  q, quit  - Exit program")
        except (EOFError, KeyboardInterrupt):
            break

def telemetry_worker(state: dict):
    """
    Continuously polls FlightGear and runs the emergency detection pipeline.
    Includes startup grace period and manual reset functionality.
    """
    try:
        emergency_model = joblib.load(MODEL_PATH)
        logging.info("Emergency detection model loaded successfully.")
    except Exception as e:
        logging.error(f"MODEL NOT FOUND at {MODEL_PATH}. Emergency detection will be disabled. Error: {e}")
        emergency_model = None
    
    # Initialize pattern recognizer (this will be reset as needed)
    from shallnotcrash.emergency.analyzers.pattern_recognizer import PatternRecognizer
    pattern_recognizer = PatternRecognizer(MODEL_PATH if emergency_model else None)
    state['pattern_recognizer'] = pattern_recognizer
    
    while True:
        if not state['fg_connected']:
            time.sleep(1)
            continue
        
        # Handle reset request
        if state['reset_requested']:
            print("\n" + "="*80)
            print("[SYSTEM RESET] Reinitializing emergency detection system...")
            print("="*80)
            pattern_recognizer = PatternRecognizer(MODEL_PATH if emergency_model else None)
            state['pattern_recognizer'] = pattern_recognizer
            state['reset_requested'] = False
            print("[RESET COMPLETE] System ready for normal operation.")
            print("="*80 + "\n")
            
        try:
            fg = state['fg_interface']
            raw_telemetry = {
                'rpm': get_prop(fg, FGProps.ENGINE.RPM),
                'oil_pressure': get_prop(fg, FGProps.ENGINE.OIL_PRESS_PSI),
                'fuel_flow': get_prop(fg, FGProps.ENGINE.FUEL_FLOW_GPH),
                'g_load': get_prop(fg, FGProps.FLIGHT.G_LOAD),
                'vibration': get_prop(fg, FGProps.ENGINE.VIBRATION),
                'bus_volts': get_prop(fg, FGProps.ELECTRICAL.BUS_VOLTS),
                'oil_temp': get_prop(fg, FGProps.ENGINE.OIL_TEMP_F),
                'cht': get_prop(fg, FGProps.ENGINE.CHT_F),
                'egt': get_prop(fg, FGProps.ENGINE.EGT_F),
                'control_asymmetry': 0.0
            }
            
            emergency_result = {'pattern_type': 'NORMAL', 'probability': 1.0, 'recommended_action': 'Continue normal operations.'}
            anomaly_scores = None

            if emergency_model and pattern_recognizer:
                anomaly_scores = anomaly_detector.detect(raw_telemetry, flight_phase=FlightPhase.CRUISE)
                # Use the pattern recognizer directly instead of detect_emergency
                result = pattern_recognizer.predict_pattern(raw_telemetry, anomaly_scores)
                emergency_result = {
                    'pattern_type': result.pattern_type.value if hasattr(result.pattern_type, 'value') else result.pattern_type,
                    'probability': result.probability,
                    'recommended_action': result.recommended_action
                }

            # --- Enhanced Debug Output ---
            elapsed_time = time.time() - pattern_recognizer.startup_time if pattern_recognizer else 0
            grace_remaining = max(0, pattern_recognizer.STARTUP_GRACE_PERIOD - elapsed_time) if pattern_recognizer else 0
            
            print("\n" + "="*80)
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Telemetry Poll")
            if grace_remaining > 0:
                print(f"[STARTUP GRACE PERIOD] {grace_remaining:.1f}s remaining")
            print("="*80)
            
            print("--- Raw Telemetry ---")
            for key, val in raw_telemetry.items():
                print(f"{key:<20}: {val:,.2f}")

            print("\n--- Anomaly Scores ---")
            if anomaly_scores:
                anomalies_found = False
                max_score = 0.0
                for key, score in anomaly_scores.items():
                    if score.is_anomaly:
                        print(f"{key:<20}: Score: {score.normalized_score:.2f} | Severity: {score.severity.name}")
                        anomalies_found = True
                        max_score = max(max_score, score.normalized_score)
                if not anomalies_found:
                    print("No significant anomalies detected.")
                else:
                    print(f"\nMAX ANOMALY SCORE: {max_score:.2f}")
            else:
                print("Anomaly detection is disabled due to missing model.")

            print("\n--- Emergency Detection Result ---")
            print(f"Detected Pattern: {emergency_result['pattern_type']}")
            print(f"Confidence: {emergency_result['probability']:.2f}")
            print(f"Recommended Action: {emergency_result['recommended_action']}")
            
            # System status
            if pattern_recognizer:
                print(f"\n--- System Status ---")
                print(f"Readings Count: {pattern_recognizer.readings_count}")
                print(f"Elapsed Time: {elapsed_time:.1f}s")
                if grace_remaining > 0:
                    print(f"Grace Period: {grace_remaining:.1f}s remaining")
                else:
                    print("Grace Period: COMPLETE - Full detection active")

            print("="*80)
            print("Commands: [r]eset, [h]elp, [q]uit")

        except Exception as e:
            logging.error(f"Telemetry read error: {e}", exc_info=True)
            state['fg_connected'] = False
            time.sleep(1)
        
        time.sleep(2)  # Increased polling interval to 2 seconds for better readability

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    fg_exe = find_fgfs_executable()
    if not fg_exe:
        logging.error("FlightGear executable 'fgfs' not found. Please ensure it is installed and in your PATH.")
        return

    # User prompt
    print("Welcome to the IMPROVED FlightGear Emergency Detection Console Tester.")
    print("This version includes a 15-second startup grace period to avoid false positives.")
    print("\nPlease start FlightGear with the following command:")
    print("--------------------------------------------------")
    print(f"  {fg_exe} --airport=BIKF --aircraft=c172p --lat=64.05 --lon=-22.5 --heading=180 --altitude=5000 --timeofday=noon --telnet=socket,bi,10,localhost,5500,tcp")
    print("--------------------------------------------------")
    print("\nIMPORTANT: After starting this script, wait 15 seconds for the system to stabilize")
    print("before expecting accurate emergency detection results.")
    input("\nPress Enter to continue once FlightGear is running...")
    
    try_connect_fg(state)
    if not state['fg_connected']:
        logging.error("Failed to connect to FlightGear. Please check if the command was entered correctly and if the simulation is fully loaded.")
        return

    # Start worker threads
    telemetry_thread = threading.Thread(target=telemetry_worker, args=(state,), daemon=True)
    input_thread = threading.Thread(target=input_worker, args=(state,), daemon=True)
    
    telemetry_thread.start()
    input_thread.start()
    
    print("\n" + "="*80)
    print("EMERGENCY DETECTION SYSTEM STARTED")
    print("="*80)
    print("Grace period: 15 seconds (system will stabilize)")
    print("Commands available:")
    print("  r, reset - Reset emergency detection system") 
    print("  h, help  - Show help")
    print("  q, quit  - Exit program")
    print("="*80)
    logging.info("Emergency detection script started with grace period. System stabilizing...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Script terminated by user.")

if __name__ == "__main__":
    main()
    