import mplfinance as mpf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from typing import Optional, List, Dict, Union, Tuple

class ChartManager:
    def __init__(self, style: str = 'charles'):
        """
        Initialize the ChartManager with a default style.
        
        Args:
            style (str): The style to use for the chart. Options include:
                - 'charles' (default): Green/red candlesticks
                - 'yahoo': Blue/red candlesticks
                - 'classic': Black/white candlesticks
        """
        self.style = style
        self.default_figsize = (12, 8)
        self.current_fig = None
        self.current_axes = None
        self.current_canvas = None
        
    def plot_candlestick(self, 
                        df: pd.DataFrame,
                        title: str = "Price Chart",
                        volume: bool = True,
                        indicators: Optional[Dict[str, pd.Series]] = None,
                        save_path: Optional[str] = None,
                        figsize: Optional[Tuple[int, int]] = None,
                        returnfig: bool = False,
                        update_only: bool = False) -> Union[None, Tuple[Figure, List[plt.Axes]]]:
        """
        Create a candlestick chart with optional volume and indicators.
        
        Args:
            df (pd.DataFrame): DataFrame with OHLCV data and datetime index
            title (str): Chart title
            volume (bool): Whether to show volume
            indicators (Dict[str, pd.Series]): Dictionary of indicator names and their Series
            save_path (str): Path to save the chart image
            figsize (Tuple[int, int]): Figure size (width, height)
            returnfig (bool): Whether to return the figure and axes instead of showing the plot
            update_only (bool): If True, only update the latest candle instead of redrawing the whole chart
            
        Returns:
            Union[None, Tuple[Figure, List[plt.Axes]]]: If returnfig is True, returns the figure and axes
        """
        if figsize is None:
            figsize = self.default_figsize

        if update_only and self.current_fig is not None:
            try:
                # Clear the current axes
                for ax in self.current_axes:
                    ax.clear()
                
                # Recreate the plot with updated data
                kwargs = {
                    'type': 'candle',
                    'style': self.style,
                    'title': title,
                    'volume': volume,
                    'figsize': figsize,
                    'returnfig': True,
                    'panel_ratios': (3, 1) if volume else (1,),
                    'tight_layout': False,  # Disable tight_layout
                    'figscale': 1.2,  # Increase figure scale
                    'figratio': (1.5, 1)  # Width to height ratio
                }
                
                # Add indicators if provided
                if indicators:
                    apds = []
                    for name, series in indicators.items():
                        if not series.empty and not series.isna().all():
                            apds.append(mpf.make_addplot(series, label=name, panel=0))
                    if apds:
                        kwargs['addplot'] = apds
                
                # Create the plot
                _, new_axes = mpf.plot(df, **kwargs)
                
                # Copy the new plot to the current figure
                for i, ax in enumerate(self.current_axes):
                    ax.clear()
                    for line in new_axes[i].get_lines():
                        ax.plot(line.get_xdata(), line.get_ydata(), 
                               color=line.get_color(), 
                               linestyle=line.get_linestyle(),
                               label=line.get_label())
                    ax.set_title(new_axes[i].get_title())
                    ax.set_xlabel(new_axes[i].get_xlabel())
                    ax.set_ylabel(new_axes[i].get_ylabel())
                    # Configure grid
                    ax.grid(True, linestyle='--', alpha=0.3, color='gray')
                    if i == 0 and indicators:
                        ax.legend()
                
                # Adjust layout manually with minimal left margin
                self.current_fig.subplots_adjust(
                    left=0.02,    # Further reduced from 0.05
                    right=0.98,   # Adjusted to maintain symmetry
                    top=0.95,     # Keep top margin
                    bottom=0.05,  # Keep bottom margin
                    hspace=0.1    # Add small space between price and volume charts
                )
                self.current_canvas.draw()
                return self.current_fig, self.current_axes
                
            except Exception as e:
                print(f"Error updating chart: {e}")
                # If update fails, fall back to full redraw
                update_only = False

        # Create the plot using mplfinance
        kwargs = {
            'type': 'candle',
            'style': self.style,
            'title': title,
            'volume': volume,
            'figsize': figsize,
            'returnfig': True,
            'panel_ratios': (3, 1) if volume else (1,),
            'tight_layout': False,  # Disable tight_layout
            'figscale': 1.2,  # Increase figure scale
            'figratio': (1.5, 1)  # Width to height ratio
        }
        
        # Add indicators if provided
        if indicators:
            apds = []
            for name, series in indicators.items():
                if not series.empty and not series.isna().all():
                    apds.append(mpf.make_addplot(series, label=name, panel=0))
            if apds:
                kwargs['addplot'] = apds
        
        # Create the plot
        fig, axes = mpf.plot(df, **kwargs)
        
        # Add legend if we have indicators
        if indicators and apds:
            axes[0].legend()
        
        # Configure grid for all axes
        for ax in axes:
            ax.grid(True, linestyle='--', alpha=0.3, color='gray')
        
        # Adjust layout manually with minimal left margin
        fig.subplots_adjust(
            left=0.02,    # Further reduced from 0.05
            right=0.98,   # Adjusted to maintain symmetry
            top=0.95,     # Keep top margin
            bottom=0.05,  # Keep bottom margin
            hspace=0.1    # Add small space between price and volume charts
        )
        
        # Save if path provided
        if save_path:
            plt.savefig(save_path)
            
        # Store current figure and axes for updates
        self.current_fig = fig
        self.current_axes = axes
            
        if returnfig:
            return fig, axes
        else:
            plt.show()
            return None
            
    def set_canvas(self, canvas):
        """Store the canvas reference for updates"""
        self.current_canvas = canvas
        
    def plot_backtest_results(self,
                            df: pd.DataFrame,
                            trades: List[Dict],
                            title: str = "Backtest Results",
                            save_path: Optional[str] = None) -> None:
        """
        Create a chart showing backtest results with entry/exit points.
        
        Args:
            df (pd.DataFrame): Price data
            trades (List[Dict]): List of trade dictionaries with keys:
                - entry_time: datetime
                - entry_price: float
                - exit_time: datetime
                - exit_price: float
                - pnl: float
            title (str): Chart title
            save_path (str): Path to save the chart image
        """
        # Create the base candlestick chart
        fig, axes = mpf.plot(df, type='candle', style=self.style, 
                           title=title, volume=False, returnfig=True)
        
        # Plot entry and exit points
        for trade in trades:
            # Plot entry point
            axes[0].scatter(trade['entry_time'], trade['entry_price'], 
                          marker='^', color='g', s=100, 
                          label='Entry' if 'Entry' not in axes[0].get_legend_handles_labels()[1] else "")
            
            # Plot exit point
            axes[0].scatter(trade['exit_time'], trade['exit_price'], 
                          marker='v', color='r', s=100, 
                          label='Exit' if 'Exit' not in axes[0].get_legend_handles_labels()[1] else "")
            
            # Draw line connecting entry and exit
            axes[0].plot([trade['entry_time'], trade['exit_time']], 
                        [trade['entry_price'], trade['exit_price']], 
                        'k--', alpha=0.5)
        
        axes[0].legend()
        
        if save_path:
            plt.savefig(save_path)
        plt.show()
        
    def plot_equity_curve(self,
                         equity_curve: pd.Series,
                         title: str = "Equity Curve",
                         save_path: Optional[str] = None) -> None:
        """
        Create a chart showing the equity curve over time.
        
        Args:
            equity_curve (pd.Series): Series with datetime index and equity values
            title (str): Chart title
            save_path (str): Path to save the chart image
        """
        plt.figure(figsize=self.default_figsize)
        plt.plot(equity_curve.index, equity_curve.values)
        plt.title(title)
        plt.xlabel('Date')
        plt.ylabel('Equity')
        plt.grid(True)
        
        if save_path:
            plt.savefig(save_path)
        plt.show()

# Example usage:
if __name__ == "__main__":
    from data_downloader import download_data_fyers
    from login import initialize_fyers_client
    
    # Initialize Fyers client
    fyers = initialize_fyers_client()
    
    # Download some sample data
    df = download_data_fyers("NSE:SBIN-EQ", 
                            (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                            datetime.now().strftime("%Y-%m-%d"),
                            gui_resolution="1d",
                            fyers=fyers)
    
    # Create chart manager instance
    chart_manager = ChartManager()
    
    # Calculate moving averages with shorter periods for better visibility
    df['SMA10'] = df['close'].rolling(window=10, min_periods=1).mean()
    df['SMA20'] = df['close'].rolling(window=20, min_periods=1).mean()
    
    # Create indicators dictionary
    indicators = {
        'SMA10': df['SMA10'],
        'SMA20': df['SMA20']
    }
    
    # Plot single chart with moving averages
    chart_manager.plot_candlestick(df, 
                                 title="SBIN Daily Chart with Moving Averages",
                                 indicators=indicators) 