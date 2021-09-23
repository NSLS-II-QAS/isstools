from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
from matplotlib.widgets import Cursor

def update_figure(axes, toolbar, canvas):
    for ax in axes:
        ax.clear()
        # cursor = Cursor(ax, useblit=True, color='green', linewidth=0.75)
    toolbar.update()
    canvas.draw_idle()
    axes[-1].grid(alpha=0.4)