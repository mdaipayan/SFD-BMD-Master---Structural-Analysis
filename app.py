
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle, FancyBboxPatch, Arc
import matplotlib.patches as mpatches
from io import BytesIO
import base64
from dataclasses import dataclass
from typing import List, Tuple, Optional
import json

# Page configuration
st.set_page_config(
    page_title="SFD & BMD Master - Structural Analysis",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .formula-box {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
        margin: 1rem 0;
    }
    .step-box {
        background-color: #e8f4f8;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid #17a2b8;
    }
    .highlight {
        background-color: #fff3cd;
        padding: 0.2rem 0.4rem;
        border-radius: 4px;
        font-weight: bold;
    }
    .result-box {
        background-color: #d4edda;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #28a745;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #f8d7da;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #dc3545;
        margin: 1rem 0;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
    }
</style>
""", unsafe_allow_html=True)

# ==================== DATA CLASSES ====================
@dataclass
class PointLoad:
    position: float
    magnitude: float  # Positive = downward
    label: str = ""

@dataclass
class DistributedLoad:
    start_pos: float
    end_pos: float
    start_mag: float  # kN/m, positive = downward
    end_mag: float
    label: str = ""

@dataclass
class MomentLoad:
    position: float
    magnitude: float  # Positive = clockwise
    label: str = ""

@dataclass
class Support:
    position: float
    type: str  # 'pin', 'roller', 'fixed'
    label: str = ""

@dataclass
class BeamConfig:
    length: float
    supports: List[Support]
    point_loads: List[PointLoad]
    distributed_loads: List[DistributedLoad]
    moments: List[MomentLoad]
    EI: Optional[float] = None

# ==================== CALCULATION ENGINE ====================
class BeamAnalyzer:
    def __init__(self, config: BeamConfig):
        self.config = config
        self.reactions = {}
        self.shear_data = None
        self.moment_data = None

    def calculate_reactions(self) -> dict:
        """Calculate support reactions using static equilibrium equations"""
        L = self.config.length

        # Sum of vertical forces = 0
        # Sum of moments about any point = 0

        total_point_load = sum(pl.magnitude for pl in self.config.point_loads)

        # Distributed loads
        total_dist_load = 0
        total_dist_moment = 0
        for dl in self.config.distributed_loads:
            # Trapezoidal load
            avg_load = (dl.start_mag + dl.end_mag) / 2
            length = dl.end_pos - dl.start_pos
            total = avg_load * length
            total_dist_load += total

            # Centroid of trapezoid
            if dl.start_mag == dl.end_mag:
                centroid = (dl.start_pos + dl.end_pos) / 2
            else:
                # For trapezoid: divide into rectangle and triangle
                # Simplified centroid calculation
                centroid = (dl.start_pos + dl.end_pos) / 2  # Approximation for teaching
            total_dist_moment += total * centroid

        total_moment_load = sum(m.magnitude for m in self.config.moments)

        total_vertical_load = total_point_load + total_dist_load

        # Moment from point loads about origin (x=0)
        moment_from_points = sum(pl.magnitude * pl.position for pl in self.config.point_loads)
        moment_from_moments = sum(m.magnitude for m in self.config.moments)

        total_moment = moment_from_points + total_dist_moment + moment_from_moments

        # Determine support reactions
        supports = sorted(self.config.supports, key=lambda s: s.position)

        if len(supports) == 2:
            # Simply supported beam
            x1, x2 = supports[0].position, supports[1].position

            # R2 = total_moment / (x2 - x1)  (taking moments about support 1)
            R2 = total_moment / (x2 - x1)
            R1 = total_vertical_load - R2

            self.reactions = {
                supports[0].label or f"R_{supports[0].position}": R1,
                supports[1].label or f"R_{supports[1].position}": R2
            }

        elif len(supports) == 1 and supports[0].type == 'fixed':
            # Cantilever
            R1 = total_vertical_load
            M1 = total_moment
            self.reactions = {
                supports[0].label or "R": R1,
                supports[0].label or "M": M1
            }

        return self.reactions

    def calculate_sfd(self, num_points=500):
        """Calculate Shear Force Diagram data"""
        x = np.linspace(0, self.config.length, num_points)
        V = np.zeros_like(x)

        # Add reactions
        for support in self.config.supports:
            if support.position in [pos for pos, _ in [(s.position, s) for s in self.config.supports]]:
                # Find reaction value
                for key, val in self.reactions.items():
                    if key.startswith('R'):
                        idx = np.argmin(np.abs(x - support.position))
                        V[idx:] += val

        # Add point loads (downward = negative shear)
        for pl in self.config.point_loads:
            idx = np.argmin(np.abs(x - pl.position))
            V[idx:] -= pl.magnitude

        # Add distributed loads
        for dl in self.config.distributed_loads:
            mask = (x >= dl.start_pos) & (x <= dl.end_pos)
            # Linear interpolation of load intensity
            load_intensity = np.interp(x[mask], [dl.start_pos, dl.end_pos], [dl.start_mag, dl.end_mag])
            # Cumulative effect
            dx = x[1] - x[0]
            for i in range(len(x)):
                if x[i] > dl.start_pos:
                    if x[i] <= dl.end_pos:
                        # Integrate load up to this point
                        sub_mask = (x >= dl.start_pos) & (x <= x[i])
                        if np.any(sub_mask):
                            avg_load = np.mean(np.interp(x[sub_mask], [dl.start_pos, dl.end_pos], 
                                                        [dl.start_mag, dl.end_mag]))
                            V[i] -= avg_load * (x[i] - dl.start_pos)
                    else:
                        # Full distributed load applied
                        avg_load = (dl.start_mag + dl.end_mag) / 2
                        V[i] -= avg_load * (dl.end_pos - dl.start_pos)

        self.shear_data = (x, V)
        return x, V

    def calculate_bmd(self, num_points=500):
        """Calculate Bending Moment Diagram data"""
        if self.shear_data is None:
            self.calculate_sfd(num_points)

        x, V = self.shear_data
        M = np.zeros_like(x)

        # Integrate shear to get moment
        dx = x[1] - x[0]
        for i in range(1, len(x)):
            M[i] = M[i-1] + V[i] * dx

        # Add concentrated moments
        for moment in self.config.moments:
            idx = np.argmin(np.abs(x - moment.position))
            M[idx:] += moment.magnitude

        # Boundary conditions
        # For simply supported beam, moment at supports should be zero
        supports = sorted(self.config.supports, key=lambda s: s.position)
        if len(supports) == 2 and supports[0].type in ['pin', 'roller'] and supports[1].type in ['pin', 'roller']:
            # Adjust for numerical integration drift
            M = M - np.interp(supports[0].position, x, M)

        self.moment_data = (x, M)
        return x, M

    def get_max_values(self):
        """Get maximum shear and moment values"""
        if self.shear_data is None or self.moment_data is None:
            self.calculate_bmd()

        x_v, V = self.shear_data
        x_m, M = self.moment_data

        v_max_idx = np.argmax(np.abs(V))
        m_max_idx = np.argmax(np.abs(M))

        return {
            'V_max': V[v_max_idx],
            'V_max_pos': x_v[v_max_idx],
            'M_max': M[m_max_idx],
            'M_max_pos': x_m[m_max_idx]
        }

# ==================== VISUALIZATION ====================
def plot_beam_diagram(config: BeamConfig, reactions: dict):
    """Plot the beam with loads and supports"""
    fig, ax = plt.subplots(figsize=(12, 4))

    L = config.length
    ax.set_xlim(-0.1*L, 1.1*L)
    ax.set_ylim(-3, 3)
    ax.set_aspect('equal')

    # Draw beam
    beam_y = 0
    ax.plot([0, L], [beam_y, beam_y], 'k-', linewidth=6, solid_capstyle='round')

    # Draw supports
    for support in config.supports:
        x = support.position
        if support.type == 'pin':
            # Triangle support
            triangle = plt.Polygon([[x, beam_y], [x-0.05*L, beam_y-0.3], [x+0.05*L, beam_y-0.3]], 
                                  fill=True, facecolor='#8B4513', edgecolor='black')
            ax.add_patch(triangle)
            ax.plot([x-0.06*L, x+0.06*L], [beam_y-0.35, beam_y-0.35], 'k-', linewidth=2)
        elif support.type == 'roller':
            # Roller support
            circle = plt.Circle((x, beam_y-0.15), 0.08, fill=True, facecolor='#4169E1', edgecolor='black')
            ax.add_patch(circle)
            ax.plot([x-0.05*L, x+0.05*L], [beam_y-0.3, beam_y-0.3], 'k-', linewidth=2)
        elif support.type == 'fixed':
            # Fixed support (wall)
            wall = plt.Polygon([[x, beam_y+0.5], [x, beam_y-0.5], [x-0.1*L, beam_y-0.5], [x-0.1*L, beam_y+0.5]],
                              fill=True, facecolor='#696969', edgecolor='black')
            ax.add_patch(wall)
            # Hatching lines
            for i in range(5):
                y_hatch = beam_y - 0.4 + i * 0.2
                ax.plot([x-0.08*L, x], [y_hatch, y_hatch], 'k-', linewidth=1)

    # Draw point loads
    for pl in config.point_loads:
        x = pl.position
        mag = pl.magnitude
        color = '#FF4444' if mag > 0 else '#4444FF'

        # Arrow
        arrow_len = 1.5 if abs(mag) > 50 else 1.0
        ax.annotate('', xy=(x, beam_y-arrow_len), xytext=(x, beam_y+0.3),
                   arrowprops=dict(arrowstyle='->', color=color, lw=2))
        ax.text(x, beam_y-arrow_len-0.3, f'{abs(mag):.1f} kN', ha='center', fontsize=10, color=color, fontweight='bold')

    # Draw distributed loads
    for dl in config.distributed_loads:
        x_start, x_end = dl.start_pos, dl.end_pos
        num_arrows = max(3, int((x_end - x_start) / (L/10)))
        x_arrows = np.linspace(x_start, x_end, num_arrows)

        for x_arr in x_arrows:
            load_mag = np.interp(x_arr, [x_start, x_end], [dl.start_mag, dl.end_mag])
            arrow_len = 0.5 + (load_mag / 100) * 0.5
            ax.annotate('', xy=(x_arr, beam_y-arrow_len), xytext=(x_arr, beam_y+0.2),
                       arrowprops=dict(arrowstyle='->', color='#FF8800', lw=1.5))

        # Label
        mid_x = (x_start + x_end) / 2
        ax.text(mid_x, beam_y-1.5, f'{dl.start_mag:.1f}-{dl.end_mag:.1f} kN/m', 
               ha='center', fontsize=9, color='#FF8800')

    # Draw reaction forces
    for support in config.supports:
        for key, val in reactions.items():
            if key.startswith('R') and abs(val) > 0.01:
                x = support.position
                direction = 1 if val > 0 else -1
                ax.annotate('', xy=(x, beam_y+1.2), xytext=(x, beam_y+0.3),
                           arrowprops=dict(arrowstyle='->', color='#228B22', lw=2))
                ax.text(x, beam_y+1.5, f'R={abs(val):.2f} kN', ha='center', fontsize=9, color='#228B22', fontweight='bold')

    ax.set_xlabel('Position (m)', fontsize=12)
    ax.set_title('Beam Loading Diagram', fontsize=14, fontweight='bold')
    ax.set_yticks([])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)

    plt.tight_layout()
    return fig

def plot_sfd(x, V, title="Shear Force Diagram"):
    """Plot Shear Force Diagram"""
    fig, ax = plt.subplots(figsize=(12, 4))

    # Fill positive and negative areas
    ax.fill_between(x, 0, V, where=(V >= 0), alpha=0.3, color='green', label='Positive Shear')
    ax.fill_between(x, 0, V, where=(V < 0), alpha=0.3, color='red', label='Negative Shear')

    # Plot line
    ax.plot(x, V, 'b-', linewidth=2)
    ax.axhline(y=0, color='k', linewidth=0.8)

    # Annotations for max values
    v_max = np.max(V)
    v_min = np.min(V)
    if abs(v_max) > 0.01:
        idx_max = np.argmax(V)
        ax.annotate(f'V_max = {v_max:.2f} kN', xy=(x[idx_max], v_max), 
                   xytext=(x[idx_max]+0.5, v_max+0.5),
                   arrowprops=dict(arrowstyle='->', color='green'),
                   fontsize=10, color='green', fontweight='bold')

    ax.set_xlabel('Position (m)', fontsize=12)
    ax.set_ylabel('Shear Force (kN)', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()

    plt.tight_layout()
    return fig

def plot_bmd(x, M, title="Bending Moment Diagram"):
    """Plot Bending Moment Diagram"""
    fig, ax = plt.subplots(figsize=(12, 4))

    # Fill positive and negative areas
    ax.fill_between(x, 0, M, where=(M >= 0), alpha=0.3, color='blue', label='Sagging (Positive)')
    ax.fill_between(x, 0, M, where=(M < 0), alpha=0.3, color='orange', label='Hogging (Negative)')

    # Plot line
    ax.plot(x, M, 'purple', linewidth=2)
    ax.axhline(y=0, color='k', linewidth=0.8)

    # Annotations for max values
    m_max = np.max(M)
    m_min = np.min(M)
    if abs(m_max) > 0.01:
        idx_max = np.argmax(M)
        ax.annotate(f'M_max = {m_max:.2f} kN⋅m', xy=(x[idx_max], m_max), 
                   xytext=(x[idx_max]+0.5, m_max+0.5),
                   arrowprops=dict(arrowstyle='->', color='blue'),
                   fontsize=10, color='blue', fontweight='bold')

    ax.set_xlabel('Position (m)', fontsize=12)
    ax.set_ylabel('Bending Moment (kN⋅m)', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()

    plt.tight_layout()
    return fig

def plot_all_diagrams(config: BeamConfig, analyzer: BeamAnalyzer):
    """Plot all three diagrams in a single figure"""
    fig, axes = plt.subplots(3, 1, figsize=(14, 12), gridspec_kw={'height_ratios': [1, 1, 1]})

    L = config.length
    x_v, V = analyzer.shear_data
    x_m, M = analyzer.moment_data

    # Beam diagram
    ax = axes[0]
    ax.set_xlim(-0.1*L, 1.1*L)
    ax.set_ylim(-2.5, 2.5)
    ax.plot([0, L], [0, 0], 'k-', linewidth=5)

    # Supports
    for support in config.supports:
        x = support.position
        if support.type == 'pin':
            tri = plt.Polygon([[x, 0], [x-0.05*L, -0.3], [x+0.05*L, -0.3]], 
                            facecolor='#8B4513', edgecolor='black')
            ax.add_patch(tri)
        elif support.type == 'roller':
            circ = plt.Circle((x, -0.15), 0.08, facecolor='#4169E1', edgecolor='black')
            ax.add_patch(circ)
        elif support.type == 'fixed':
            wall = plt.Polygon([[x, 0.5], [x, -0.5], [x-0.1*L, -0.5], [x-0.1*L, 0.5]],
                              facecolor='#696969', edgecolor='black')
            ax.add_patch(wall)

    # Loads
    for pl in config.point_loads:
        ax.annotate('', xy=(pl.position, -1.2), xytext=(pl.position, 0.2),
                   arrowprops=dict(arrowstyle='->', color='red', lw=2))
        ax.text(pl.position, -1.5, f'{pl.magnitude:.1f}kN', ha='center', fontsize=9, color='red')

    ax.set_title('Beam Loading Diagram', fontsize=13, fontweight='bold')
    ax.set_yticks([])
    ax.set_xlabel('Position (m)')

    # SFD
    ax = axes[1]
    ax.fill_between(x_v, 0, V, where=(V >= 0), alpha=0.3, color='green')
    ax.fill_between(x_v, 0, V, where=(V < 0), alpha=0.3, color='red')
    ax.plot(x_v, V, 'b-', linewidth=2)
    ax.axhline(y=0, color='k', linewidth=0.8)
    ax.set_title('Shear Force Diagram (SFD)', fontsize=13, fontweight='bold')
    ax.set_ylabel('V (kN)')
    ax.grid(True, alpha=0.3)

    # BMD
    ax = axes[2]
    ax.fill_between(x_m, 0, M, where=(M >= 0), alpha=0.3, color='blue')
    ax.fill_between(x_m, 0, M, where=(M < 0), alpha=0.3, color='orange')
    ax.plot(x_m, M, 'purple', linewidth=2)
    ax.axhline(y=0, color='k', linewidth=0.8)
    ax.set_title('Bending Moment Diagram (BMD)', fontsize=13, fontweight='bold')
    ax.set_ylabel('M (kN⋅m)')
    ax.set_xlabel('Position (m)')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    return fig

# ==================== STREAMLIT APP ====================
def main():
    # Header
    st.markdown('<div class="main-header">🏗️ SFD & BMD Master</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Interactive Structural Analysis: Shear Force & Bending Moment Diagrams</div>', unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Beam Configuration")

        beam_type = st.selectbox("Beam Type", [
            "Simply Supported Beam",
            "Cantilever Beam", 
            "Overhanging Beam",
            "Custom Configuration"
        ])

        st.divider()

        # Beam length
        L = st.number_input("Beam Length (m)", min_value=1.0, max_value=50.0, value=10.0, step=0.5)

        # Predefined configurations
        if beam_type == "Simply Supported Beam":
            supports = [Support(0, 'pin', 'A'), Support(L, 'roller', 'B')]
            default_loads = True
        elif beam_type == "Cantilever Beam":
            supports = [Support(0, 'fixed', 'A')]
            default_loads = True
        elif beam_type == "Overhanging Beam":
            overhang = st.number_input("Overhang Length (m)", min_value=0.5, max_value=L/2, value=2.0)
            supports = [Support(overhang, 'pin', 'A'), Support(L-overhang, 'roller', 'B')]
            default_loads = True
        else:
            # Custom support configuration
            num_supports = st.number_input("Number of Supports", min_value=1, max_value=3, value=2)
            supports = []
            for i in range(num_supports):
                cols = st.columns(2)
                with cols[0]:
                    pos = st.number_input(f"Support {i+1} Position (m)", min_value=0.0, max_value=L, value=0.0 if i==0 else L, key=f"sup_pos_{i}")
                with cols[1]:
                    stype = st.selectbox(f"Type", ['pin', 'roller', 'fixed'], key=f"sup_type_{i}")
                supports.append(Support(pos, stype, chr(65+i)))
            default_loads = False

        st.divider()
        st.subheader("📐 Loads")

        # Point loads
        num_point_loads = st.number_input("Point Loads", min_value=0, max_value=5, value=1 if default_loads else 0)
        point_loads = []
        for i in range(num_point_loads):
            cols = st.columns(2)
            with cols[0]:
                pos = st.number_input(f"Load {i+1} Position (m)", min_value=0.0, max_value=L, value=L/2, key=f"pl_pos_{i}")
            with cols[1]:
                mag = st.number_input(f"Magnitude (kN)", min_value=0.0, value=50.0, key=f"pl_mag_{i}")
            point_loads.append(PointLoad(pos, mag, f"P{i+1}"))

        # Distributed loads
        num_dist_loads = st.number_input("Distributed Loads", min_value=0, max_value=3, value=0)
        dist_loads = []
        for i in range(num_dist_loads):
            cols = st.columns(3)
            with cols[0]:
                start = st.number_input(f"Start (m)", min_value=0.0, max_value=L, value=0.0, key=f"dl_start_{i}")
            with cols[1]:
                end = st.number_input(f"End (m)", min_value=start, max_value=L, value=L, key=f"dl_end_{i}")
            with cols[2]:
                mag = st.number_input(f"Intensity (kN/m)", min_value=0.0, value=20.0, key=f"dl_mag_{i}")
            dist_loads.append(DistributedLoad(start, end, mag, mag, f"w{i+1}"))

        # Moments
        num_moments = st.number_input("Applied Moments", min_value=0, max_value=3, value=0)
        moments = []
        for i in range(num_moments):
            cols = st.columns(2)
            with cols[0]:
                pos = st.number_input(f"Moment {i+1} Position (m)", min_value=0.0, max_value=L, value=L/2, key=f"m_pos_{i}")
            with cols[1]:
                mag = st.number_input(f"Magnitude (kN⋅m)", value=20.0, key=f"m_mag_{i}")
            moments.append(MomentLoad(pos, mag, f"M{i+1}"))

        analyze_btn = st.button("🔍 Analyze Beam", type="primary", use_container_width=True)

    # Main content
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Analysis", "📚 Theory", "🧮 Calculator", "📖 Examples"])

    with tab1:
        if analyze_btn or 'analyzed' in st.session_state:
            st.session_state.analyzed = True

            # Create configuration
            config = BeamConfig(L, supports, point_loads, dist_loads, moments)
            analyzer = BeamAnalyzer(config)

            # Calculate
            try:
                reactions = analyzer.calculate_reactions()
                x_v, V = analyzer.calculate_sfd()
                x_m, M = analyzer.calculate_bmd()
                max_vals = analyzer.get_max_values()

                # Display reactions
                st.subheader("🔧 Support Reactions")
                cols = st.columns(len(reactions))
                for i, (key, val) in enumerate(reactions.items()):
                    with cols[i]:
                        st.metric(label=f"Reaction {key}", value=f"{val:.3f} kN" if 'R' in key else f"{val:.3f} kN⋅m")

                # Display max values
                st.subheader("📈 Maximum Values")
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("Maximum Shear Force", f"{max_vals['V_max']:.3f} kN", 
                             f"at x = {max_vals['V_max_pos']:.2f} m")
                with c2:
                    st.metric("Maximum Bending Moment", f"{max_vals['M_max']:.3f} kN⋅m",
                             f"at x = {max_vals['M_max_pos']:.2f} m")

                # Plot diagrams
                st.subheader("📊 Diagrams")
                fig_all = plot_all_diagrams(config, analyzer)
                st.pyplot(fig_all)

                # Individual diagrams with equations
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Shear Force Diagram")
                    fig_sfd = plot_sfd(x_v, V)
                    st.pyplot(fig_sfd)

                    # Show equations
                    with st.expander("📝 SFD Equations"):
                        st.markdown("**Governing Equation:**")
                        st.latex(r"\frac{dV}{dx} = -w(x)")
                        st.markdown("Where $w(x)$ is the distributed load intensity.")

                        # Segment equations
                        st.markdown("**By Segments:**")
                        segments = []
                        current_x = 0
                        for pl in sorted(point_loads, key=lambda p: p.position):
                            if pl.position > current_x:
                                segments.append((current_x, pl.position, f"V = constant"))
                            segments.append((pl.position, pl.position, f"V drops by {pl.magnitude} kN"))
                            current_x = pl.position
                        if current_x < L:
                            segments.append((current_x, L, "V = constant"))

                        for seg in segments:
                            st.markdown(f"- **{seg[0]:.2f} ≤ x ≤ {seg[1]:.2f}**: {seg[2]}")

                with col2:
                    st.subheader("Bending Moment Diagram")
                    fig_bmd = plot_bmd(x_m, M)
                    st.pyplot(fig_bmd)

                    with st.expander("📝 BMD Equations"):
                        st.markdown("**Governing Equation:**")
                        st.latex(r"\frac{dM}{dx} = V(x)")
                        st.markdown("The slope of the BMD equals the shear force.")

                        st.markdown("**Key Relationships:**")
                        st.latex(r"M = \int V \, dx")
                        st.markdown("- Where V = 0, M is maximum/minimum")
                        st.markdown("- Positive V → M increasing")
                        st.markdown("- Negative V → M decreasing")

                # Step-by-step solution
                with st.expander("🔍 Step-by-Step Solution", expanded=True):
                    st.markdown("### Step 1: Free Body Diagram")
                    fig_beam = plot_beam_diagram(config, reactions)
                    st.pyplot(fig_beam)

                    st.markdown("### Step 2: Equilibrium Equations")
                    st.markdown('<div class="formula-box">', unsafe_allow_html=True)
                    st.latex(r"\sum F_y = 0: \quad R_A + R_B - \sum P_i - \sum w_i = 0")
                    st.latex(r"\sum M_A = 0: \quad R_B \cdot L - \sum P_i \cdot x_i - \sum M_i - \sum (w_i \cdot \text{centroid}_i) = 0")
                    st.markdown('</div>', unsafe_allow_html=True)

                    st.markdown("### Step 3: Solve for Reactions")
                    for key, val in reactions.items():
                        st.markdown(f'<div class="step-box">{key} = {val:.4f} kN</div>', unsafe_allow_html=True)

                    st.markdown("### Step 4: Shear Force Calculation")
                    st.markdown("Starting from left end, track shear force changes:")
                    st.markdown("- **Point loads**: Sudden change in V")
                    st.markdown("- **Distributed loads**: Linear change in V (slope = -w)")
                    st.markdown("- **No load**: Constant V")

                    st.markdown("### Step 5: Bending Moment Calculation")
                    st.markdown("Integrate shear diagram or use moment equilibrium:")
                    st.markdown("- **Area under SFD** = Change in bending moment")
                    st.markdown("- **Concentrated moment**: Sudden change in M")

            except Exception as e:
                st.error(f"Analysis error: {str(e)}")
                st.info("Please check your beam configuration. Ensure supports are properly placed.")
        else:
            st.info("👈 Configure your beam in the sidebar and click **Analyze Beam** to begin!")

            # Show placeholder with example
            st.subheader("Example Preview")
            example_config = BeamConfig(
                length=10,
                supports=[Support(0, 'pin', 'A'), Support(10, 'roller', 'B')],
                point_loads=[PointLoad(5, 50, 'P')],
                distributed_loads=[],
                moments=[]
            )
            example_analyzer = BeamAnalyzer(example_config)
            example_analyzer.calculate_reactions()
            example_analyzer.calculate_bmd()
            fig_ex = plot_all_diagrams(example_config, example_analyzer)
            st.pyplot(fig_ex)

    with tab2:
        st.header("📚 Fundamental Theory")

        st.subheader("Static Equilibrium Equations")
        st.markdown('<div class="formula-box">', unsafe_allow_html=True)
        st.latex(r"""
        \sum F_x = 0 \quad \text{(Horizontal equilibrium)} \
        \sum F_y = 0 \quad \text{(Vertical equilibrium)} \
        \sum M = 0 \quad \text{(Moment equilibrium)}
        """)
        st.markdown('</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Shear Force (V)")
            st.markdown("""
            **Definition**: The internal force parallel to the cross-section, resisting vertical sliding.

            **Sign Convention**:
            - ⬆️ **Positive**: Left side up, Right side down
            - ⬇️ **Negative**: Left side down, Right side up

            **Differential Relation**:
            """)
            st.latex(r"\frac{dV}{dx} = -w(x)")
            st.markdown("""
            Where $w(x)$ = distributed load intensity (downward positive)

            **Key Rules**:
            - Concentrated load → Sudden jump in V
            - UDL → Linear slope in V
            - No load → Constant V
            """)

        with col2:
            st.subheader("Bending Moment (M)")
            st.markdown("""
            **Definition**: The internal moment causing the beam to bend.

            **Sign Convention**:
            - 😊 **Positive (Sagging)**: Compression on top, tension on bottom
            - 😠 **Negative (Hogging)**: Tension on top, compression on bottom

            **Differential Relation**:
            """)
            st.latex(r"\frac{dM}{dx} = V(x)")
            st.markdown("""
            **Key Rules**:
            - Where V = 0 → M is maximum or minimum
            - Positive V → M increasing
            - Concentrated moment → Sudden jump in M
            """)

        st.subheader("Load-Shear-Moment Relationships")
        st.markdown('<div class="formula-box">', unsafe_allow_html=True)
        st.latex(r"""
        \boxed{\frac{d^2M}{dx^2} = \frac{dV}{dx} = -w(x)}
        """)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("""
        | Load Type | Shear Force (V) | Bending Moment (M) |
        |-----------|----------------|-------------------|
        | No load | Constant | Linear |
        | Uniform load (UDL) | Linear | Parabolic |
        | Triangular load | Parabolic | Cubic |
        | Concentrated load | Sudden jump | Change in slope |
        | Concentrated moment | No change | Sudden jump |
        """)

        st.subheader("Common Beam Formulas")
        with st.expander("Simply Supported Beam - Center Point Load P"):
            st.latex(r"R_A = R_B = \frac{P}{2}")
            st.latex(r"V_{max} = \frac{P}{2} \quad \text{(at supports)}")
            st.latex(r"M_{max} = \frac{PL}{4} \quad \text{(at center)}")

        with st.expander("Simply Supported Beam - UDL w"):
            st.latex(r"R_A = R_B = \frac{wL}{2}")
            st.latex(r"V_{max} = \frac{wL}{2} \quad \text{(at supports)}")
            st.latex(r"M_{max} = \frac{wL^2}{8} \quad \text{(at center)}")

        with st.expander("Cantilever - Point Load P at Free End"):
            st.latex(r"R_A = P, \quad M_A = PL")
            st.latex(r"V_{max} = P \quad \text{(constant)}")
            st.latex(r"M_{max} = PL \quad \text{(at fixed end)}")

    with tab3:
        st.header("🧮 Quick Calculator")

        calc_type = st.selectbox("Calculation Type", [
            "Simply Supported - Center Point Load",
            "Simply Supported - UDL",
            "Cantilever - End Point Load",
            "Cantilever - UDL",
            "Custom Single Load"
        ])

        col1, col2 = st.columns(2)
        with col1:
            L_calc = st.number_input("Span Length L (m)", min_value=0.1, value=5.0, key="calc_L")
        with col2:
            if "Point" in calc_type:
                P_calc = st.number_input("Point Load P (kN)", min_value=0.0, value=50.0, key="calc_P")
            else:
                w_calc = st.number_input("UDL w (kN/m)", min_value=0.0, value=20.0, key="calc_w")

        if st.button("Calculate", type="primary"):
            st.markdown('<div class="result-box">', unsafe_allow_html=True)

            if calc_type == "Simply Supported - Center Point Load":
                Ra = P_calc / 2
                Rb = P_calc / 2
                Vmax = P_calc / 2
                Mmax = P_calc * L_calc / 4

                st.markdown(f"**Reactions:** $R_A = R_B = {Ra:.3f}$ kN")
                st.markdown(f"**Max Shear:** $V_{{max}} = {Vmax:.3f}$ kN")
                st.markdown(f"**Max Moment:** $M_{{max}} = {Mmax:.3f}$ kN⋅m")

                # Quick plot
                x = np.linspace(0, L_calc, 100)
                V = np.piecewise(x, [x < L_calc/2, x >= L_calc/2], [Ra, -Rb])
                M = np.piecewise(x, [x <= L_calc/2, x > L_calc/2], 
                               [lambda x: Ra*x, lambda x: Ra*x - P_calc*(x - L_calc/2)])

            elif calc_type == "Simply Supported - UDL":
                Ra = w_calc * L_calc / 2
                Rb = w_calc * L_calc / 2
                Vmax = w_calc * L_calc / 2
                Mmax = w_calc * L_calc**2 / 8

                st.markdown(f"**Reactions:** $R_A = R_B = {Ra:.3f}$ kN")
                st.markdown(f"**Max Shear:** $V_{{max}} = {Vmax:.3f}$ kN")
                st.markdown(f"**Max Moment:** $M_{{max}} = {Mmax:.3f}$ kN⋅m")

                x = np.linspace(0, L_calc, 100)
                V = Ra - w_calc * x
                M = Ra * x - w_calc * x**2 / 2

            elif calc_type == "Cantilever - End Point Load":
                Ra = P_calc
                Ma = P_calc * L_calc
                Vmax = P_calc
                Mmax = P_calc * L_calc

                st.markdown(f"**Reaction:** $R_A = {Ra:.3f}$ kN")
                st.markdown(f"**Fixed End Moment:** $M_A = {Ma:.3f}$ kN⋅m")
                st.markdown(f"**Max Shear:** $V_{{max}} = {Vmax:.3f}$ kN")
                st.markdown(f"**Max Moment:** $M_{{max}} = {Mmax:.3f}$ kN⋅m")

                x = np.linspace(0, L_calc, 100)
                V = np.full_like(x, -P_calc)
                M = -P_calc * (L_calc - x)

            elif calc_type == "Cantilever - UDL":
                Ra = w_calc * L_calc
                Ma = w_calc * L_calc**2 / 2
                Vmax = w_calc * L_calc
                Mmax = w_calc * L_calc**2 / 2

                st.markdown(f"**Reaction:** $R_A = {Ra:.3f}$ kN")
                st.markdown(f"**Fixed End Moment:** $M_A = {Ma:.3f}$ kN⋅m")
                st.markdown(f"**Max Shear:** $V_{{max}} = {Vmax:.3f}$ kN")
                st.markdown(f"**Max Moment:** $M_{{max}} = {Mmax:.3f}$ kN⋅m")

                x = np.linspace(0, L_calc, 100)
                V = -w_calc * (L_calc - x)
                M = -w_calc * (L_calc - x)**2 / 2

            st.markdown('</div>', unsafe_allow_html=True)

            # Plot
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6))
            ax1.plot(x, V, 'b-', linewidth=2)
            ax1.axhline(y=0, color='k', linewidth=0.8)
            ax1.fill_between(x, 0, V, alpha=0.3)
            ax1.set_ylabel('V (kN)')
            ax1.set_title('Shear Force Diagram')
            ax1.grid(True, alpha=0.3)

            ax2.plot(x, M, 'purple', linewidth=2)
            ax2.axhline(y=0, color='k', linewidth=0.8)
            ax2.fill_between(x, 0, M, alpha=0.3)
            ax2.set_ylabel('M (kN⋅m)')
            ax2.set_xlabel('x (m)')
            ax2.set_title('Bending Moment Diagram')
            ax2.grid(True, alpha=0.3)

            plt.tight_layout()
            st.pyplot(fig)

    with tab4:
        st.header("📖 Worked Examples")

        example_choice = st.selectbox("Select Example", [
            "Example 1: Simply Supported with Point Load",
            "Example 2: Simply Supported with UDL",
            "Example 3: Cantilever with Multiple Loads",
            "Example 4: Overhanging Beam"
        ])

        if example_choice == "Example 1: Simply Supported with Point Load":
            st.markdown("""
            **Problem**: A simply supported beam of span 8m carries a point load of 40 kN at 3m from the left support.
            Draw the SFD and BMD.
            """)

            st.markdown("**Solution:**")
            st.markdown('<div class="step-box">', unsafe_allow_html=True)
            st.markdown("**Step 1**: Calculate reactions")
            st.latex(r"\sum M_A = 0: \quad R_B \times 8 - 40 \times 3 = 0")
            st.latex(r"R_B = \frac{40 \times 3}{8} = 15 \text{ kN}")
            st.latex(r"\sum F_y = 0: \quad R_A + 15 - 40 = 0")
            st.latex(r"R_A = 25 \text{ kN}")
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="step-box">', unsafe_allow_html=True)
            st.markdown("**Step 2**: Shear Force")
            st.markdown("- At x = 0⁺: V = R_A = 25 kN")
            st.markdown("- At x = 3⁻: V = 25 kN")
            st.markdown("- At x = 3⁺: V = 25 - 40 = -15 kN")
            st.markdown("- At x = 8⁻: V = -15 kN")
            st.latex(r"V_{max} = 25 \text{ kN}")
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="step-box">', unsafe_allow_html=True)
            st.markdown("**Step 3**: Bending Moment")
            st.markdown("- At x = 0: M = 0")
            st.markdown("- At x = 3: M = 25 × 3 = 75 kN⋅m")
            st.markdown("- At x = 8: M = 25 × 8 - 40 × 5 = 0 ✓")
            st.latex(r"M_{max} = 75 \text{ kN⋅m}")
            st.markdown('</div>', unsafe_allow_html=True)

            # Load and show
            ex1_config = BeamConfig(
                length=8,
                supports=[Support(0, 'pin', 'A'), Support(8, 'roller', 'B')],
                point_loads=[PointLoad(3, 40, 'P')],
                distributed_loads=[],
                moments=[]
            )
            ex1_analyzer = BeamAnalyzer(ex1_config)
            ex1_analyzer.calculate_reactions()
            ex1_analyzer.calculate_bmd()
            fig_ex1 = plot_all_diagrams(ex1_config, ex1_analyzer)
            st.pyplot(fig_ex1)

        elif example_choice == "Example 2: Simply Supported with UDL":
            st.markdown("""
            **Problem**: A simply supported beam of span 6m carries a uniformly distributed load of 20 kN/m over the entire span.
            Draw the SFD and BMD.
            """)

            st.markdown('<div class="step-box">', unsafe_allow_html=True)
            st.markdown("**Step 1**: Calculate reactions")
            st.latex(r"\text{Total load} = w \times L = 20 \times 6 = 120 \text{ kN}")
            st.latex(r"R_A = R_B = \frac{120}{2} = 60 \text{ kN}")
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="step-box">', unsafe_allow_html=True)
            st.markdown("**Step 2**: Shear Force (linear variation)")
            st.latex(r"V(x) = R_A - wx = 60 - 20x")
            st.latex(r"\text{At } x=0: V = 60 \text{ kN}")
            st.latex(r"\text{At } x=3: V = 0 \text{ kN (zero shear = max moment)}")
            st.latex(r"\text{At } x=6: V = -60 \text{ kN}")
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="step-box">', unsafe_allow_html=True)
            st.markdown("**Step 3**: Bending Moment (parabolic variation)")
            st.latex(r"M(x) = R_A \cdot x - \frac{wx^2}{2} = 60x - 10x^2")
            st.latex(r"\text{At } x=0: M = 0")
            st.latex(r"\text{At } x=3: M = 60(3) - 10(9) = 90 \text{ kN⋅m}")
            st.latex(r"\text{At } x=6: M = 0")
            st.markdown('</div>', unsafe_allow_html=True)

            ex2_config = BeamConfig(
                length=6,
                supports=[Support(0, 'pin', 'A'), Support(6, 'roller', 'B')],
                point_loads=[],
                distributed_loads=[DistributedLoad(0, 6, 20, 20, 'w')],
                moments=[]
            )
            ex2_analyzer = BeamAnalyzer(ex2_config)
            ex2_analyzer.calculate_reactions()
            ex2_analyzer.calculate_bmd()
            fig_ex2 = plot_all_diagrams(ex2_config, ex2_analyzer)
            st.pyplot(fig_ex2)

if __name__ == "__main__":
    main()
