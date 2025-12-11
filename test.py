import tkinter as tk
from tkinter import ttk
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from common.chart_utils import ChartManager

# Create sample data
def create_sample_data():
    # Create date range for last 10 days
    end_date = datetime.now()
    dates = [end_date - timedelta(days=x) for x in range(10)]
    dates.reverse()
    
    # Create sample OHLCV data
    data = {
        'open': [100, 102, 101, 103, 104, 105, 103, 102, 104, 106],
        'high': [103, 104, 103, 105, 106, 107, 105, 104, 106, 108],
        'low': [99, 100, 99, 101, 102, 103, 101, 100, 102, 104],
        'close': [102, 101, 103, 104, 105, 103, 102, 104, 106, 107],
        'volume': [1000, 1200, 1100, 1300, 1400, 1500, 1300, 1200, 1400, 1600]
    }
    
    # Create DataFrame with datetime index
    df = pd.DataFrame(data, index=dates)
    return df

def on_closing():
    """Handle window closing"""
    plt.close('all')  # Close all matplotlib figures
    root.quit()  # Stop the mainloop
    root.destroy()  # Destroy the window

def main():
    global root  # Make root accessible to on_closing
    # Create the main window
    root = tk.Tk()
    root.title("Chart Test")
    root.state('zoomed')  # Start maximized
    
    # Set up window close handler
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Create main container frame
    main_frame = ttk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Get screen width and calculate container widths
    screen_width = root.winfo_screenwidth()
    left_width = int(screen_width * 0.7)  # 70% of screen width
    right_width = int(screen_width * 0.3)  # 30% of screen width
    
    # Create left container (70% width)
    left_frame = ttk.Frame(main_frame, relief="groove", borderwidth=2, width=left_width)
    left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5)
    left_frame.pack_propagate(False)  # Prevent the frame from shrinking
    
    # Create right container (30% width)
    right_frame = ttk.Frame(main_frame, relief="groove", borderwidth=2, width=right_width)
    right_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5)
    right_frame.pack_propagate(False)  # Prevent the frame from shrinking
    
    # Add labels to show container sizes
    ttk.Label(left_frame, text=f"Left Container\n({left_width}px)", font=("Arial", 12)).pack(expand=True)
    ttk.Label(right_frame, text=f"Right Container\n({right_width}px)", font=("Arial", 12)).pack(expand=True)
    
    # Create sample data
    df = create_sample_data()
    
    # Create chart manager instance
    chart_manager = ChartManager()
    
    # Create the chart
    fig, axes = chart_manager.plot_candlestick(
        df,
        title="Sample Chart",
        volume=True,
        returnfig=True,
        figsize=(left_width/100, 8)  # Adjust width based on container width, maintain height
    )
    
    # Embed chart in tkinter (in left frame)
    canvas = FigureCanvasTkAgg(fig, master=left_frame)
    canvas.draw()
    
    # Add toolbar at the top
    toolbar = NavigationToolbar2Tk(canvas, left_frame)
    toolbar.pack(side=tk.TOP, fill=tk.X)
    toolbar.update()
    
    # Pack the canvas after the toolbar
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    
    try:
        # Start the main loop
        root.mainloop()
    except Exception as e:
        print(f"Error in mainloop: {e}")
    finally:
        # Cleanup
        plt.close('all')
        print("Application closed")

if __name__ == "__main__":
    main() 