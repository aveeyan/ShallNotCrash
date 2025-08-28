# In shallnotcrash/autopilot/visualization/panel.py

import multiprocessing
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from ..data_models import TelemetryPacket, FlightPath # Import FlightPath

class Visualization:
    """Manages the real-time plotting of aircraft telemetry."""

    def __init__(self, data_queue: multiprocessing.Queue, flight_path: FlightPath):
        self.data_queue = data_queue
        # Store the static flight path data immediately
        self.flight_path_lons = [wp.lon for wp in flight_path.waypoints]
        self.flight_path_lats = [wp.lat for wp in flight_path.waypoints]
        self.flight_path_alts = [wp.alt_ft for wp in flight_path.waypoints]

        # Live data stores
        self.times = []
        self.actual_lats, self.actual_lons = [], []
        self.actual_alts, self.target_alts = [], []
        self.actual_rolls, self.target_rolls = [], []

        self.fig = plt.figure(figsize=(16, 9))
        self.fig.suptitle('ShallNotCrash Autopilot - Live Telemetry Panel', fontsize=16)
        gs = self.fig.add_gridspec(2, 2)
        self.ax_map = self.fig.add_subplot(gs[0, 0])
        self.ax_alt = self.fig.add_subplot(gs[0, 1])
        self.ax_roll = self.fig.add_subplot(gs[1, 0])
        self.ax_3d = self.fig.add_subplot(gs[1, 1], projection='3d')
        self.init_plots()

    def init_plots(self):
        """Initializes the plots with corrected scaling and rendering."""
        # 1. Bird's Eye View Map
        self.ax_map.set_title("2D Flight Path (Bird's Eye View)")
        self.ax_map.plot(self.flight_path_lons, self.flight_path_lats, 'b--', label='Planned Path')
        self.actual_path_line, = self.ax_map.plot([], [], 'r-', label='Actual Path', linewidth=2)
        # --- FIX: Enforce correct scaling for geographic coordinates ---
        self.ax_map.set_aspect('equal', adjustable='box')
        self.ax_map.legend(); self.ax_map.grid(True)

        # 2. Altitude Profile
        self.ax_alt.set_title("Altitude Profile")
        self.target_alt_line, = self.ax_alt.plot([], [], 'g--', label='Target Altitude')
        self.actual_alt_line, = self.ax_alt.plot([], [], 'm-', label='Actual Altitude')
        self.ax_alt.legend(); self.ax_alt.grid(True)

        # 3. Roll Angle Control
        self.ax_roll.set_title("Roll Angle Control")
        self.target_roll_line, = self.ax_roll.plot([], [], 'g--', label='Target Roll')
        self.actual_roll_line, = self.ax_roll.plot([], [], 'm-', label='Actual Roll')
        self.ax_roll.legend(); self.ax_roll.grid(True)

        # 4. 3D Flight Path
        self.ax_3d.set_title("3D Flight Path")
        self.ax_3d.plot(self.flight_path_lons, self.flight_path_lats, self.flight_path_alts, 'b--', label='Planned Path')
        # --- FIX: Make the actual path thicker and give it a higher draw priority ---
        self.actual_3d_line, = self.ax_3d.plot([], [], [], 'r-', label='Actual Path', linewidth=2, zorder=10)
        self.ax_3d.set_zlabel("Altitude (ft)"); self.ax_3d.legend()

    def update_plot(self, frame):
        """This function now only updates the LIVE data."""
        while not self.data_queue.empty():
            packet: TelemetryPacket = self.data_queue.get()
            self.times.append(len(self.times))
            self.actual_lats.append(packet.current_lat); self.actual_lons.append(packet.current_lon)
            self.actual_alts.append(packet.current_alt); self.target_alts.append(packet.target_alt)
            self.actual_rolls.append(packet.current_roll); self.target_rolls.append(packet.target_roll)

        self.actual_path_line.set_data(self.actual_lons, self.actual_lats)
        self.actual_alt_line.set_data(self.times, self.actual_alts); self.target_alt_line.set_data(self.times, self.target_alts)
        self.actual_roll_line.set_data(self.times, self.actual_rolls); self.target_roll_line.set_data(self.times, self.target_rolls)
        self.actual_3d_line.set_data_3d(self.actual_lons, self.actual_lats, self.actual_alts)

        for ax in [self.ax_map, self.ax_alt, self.ax_roll, self.ax_3d]:
            ax.relim(); ax.autoscale_view()
        return self.actual_path_line, self.target_alt_line, self.actual_alt_line, self.target_roll_line, self.actual_roll_line, self.actual_3d_line

def run_visualizer(data_queue: multiprocessing.Queue, flight_path: FlightPath):
    """Entry point for the visualization process."""
    vis = Visualization(data_queue, flight_path)
    # Add cache_frame_data=False to suppress the warning
    ani = FuncAnimation(vis.fig, vis.update_plot, blit=True, interval=200, cache_frame_data=False)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.show()
