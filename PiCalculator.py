import tkinter as tk
from tkinter import ttk, messagebox
import requests
from datetime import datetime
import json
import os
import threading

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class PiCoinApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Pi Coin Earnings and Price Chart")
        self.master.geometry("600x900")
        style = ttk.Style()
        style.theme_use('clam')
        
        # Variables for earnings calculation
        self.pi_price = 0.0
        self.usd_to_try = 0.0
        self.custom_usd_rate = 0.0
        self.start_time = datetime.now()
        
        # Price history for the price chart (stored as JSON)
        self.history_file = "price_history.json"
        self.price_history = []
        self.load_price_history()
        
        # ----- Earnings Calculator Section -----
        self.earnings_frame = ttk.LabelFrame(master, text="Earnings Calculator")
        self.earnings_frame.pack(padx=10, pady=10, fill="x")
        
        self.hourly_label = ttk.Label(self.earnings_frame, text="Enter hourly Pi earnings:")
        self.hourly_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.hourly_entry = ttk.Entry(self.earnings_frame, width=10)
        self.hourly_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.hourly_entry.insert(0, "0")
        
        self.calc_button = ttk.Button(self.earnings_frame, text="Calculate", command=self.update_earnings)
        self.calc_button.grid(row=0, column=2, padx=5, pady=5)
        self.manual_update_button = ttk.Button(self.earnings_frame, text="Manual Update", command=self.manual_update_earnings)
        self.manual_update_button.grid(row=0, column=3, padx=5, pady=5)
        
        self.daily_label = ttk.Label(self.earnings_frame, text="Daily Earnings: 0 Pi", font=("Arial", 14, "bold"))
        self.daily_label.grid(row=1, column=0, columnspan=4, padx=5, pady=5, sticky="w")
        self.weekly_label = ttk.Label(self.earnings_frame, text="Weekly Earnings: 0 Pi", font=("Arial", 14, "bold"))
        self.weekly_label.grid(row=2, column=0, columnspan=4, padx=5, pady=5, sticky="w")
        self.monthly_label = ttk.Label(self.earnings_frame, text="Monthly Earnings: 0 Pi", font=("Arial", 14, "bold"))
        self.monthly_label.grid(row=3, column=0, columnspan=4, padx=5, pady=5, sticky="w")
        self.yearly_label = ttk.Label(self.earnings_frame, text="Yearly Earnings: 0 Pi", font=("Arial", 14, "bold"))
        self.yearly_label.grid(row=4, column=0, columnspan=4, padx=5, pady=5, sticky="w")
        self.elapsed_label = ttk.Label(self.earnings_frame, text="Elapsed Time: 0 minutes")
        self.elapsed_label.grid(row=5, column=0, columnspan=4, padx=5, pady=5, sticky="w")
        self.total_try_label = ttk.Label(self.earnings_frame, text="Total Earnings: 0 ₺", font=("Arial", 18, "bold"))
        self.total_try_label.grid(row=6, column=0, columnspan=4, padx=5, pady=5, sticky="w")
        
        # Custom Currency Inputs (if user wishes to see earnings in another currency)
        self.custom_code_label = ttk.Label(self.earnings_frame, text="Custom Currency Code:")
        self.custom_code_label.grid(row=7, column=0, padx=5, pady=5, sticky="w")
        self.custom_currency_code_entry = ttk.Entry(self.earnings_frame, width=10)
        self.custom_currency_code_entry.grid(row=7, column=1, padx=5, pady=5, sticky="w")
        
        self.custom_symbol_label = ttk.Label(self.earnings_frame, text="Custom Currency Symbol:")
        self.custom_symbol_label.grid(row=7, column=2, padx=5, pady=5, sticky="w")
        self.custom_currency_symbol_entry = ttk.Entry(self.earnings_frame, width=10)
        self.custom_currency_symbol_entry.grid(row=7, column=3, padx=5, pady=5, sticky="w")
        
        self.total_custom_label = ttk.Label(self.earnings_frame, text="Total Earnings in Custom Currency: N/A", font=("Arial", 18, "bold"))
        self.total_custom_label.grid(row=8, column=0, columnspan=4, padx=5, pady=5, sticky="w")

        self.locked_pi_label = ttk.Label(self.earnings_frame, text="Locked Pi: fetching...", font=("Arial", 12, "bold"))
        self.locked_pi_label.grid(row=9, column=0, columnspan=4, padx=5, pady=5, sticky="w")
        
        # ----- Price Chart Section -----
        self.graph_frame = ttk.LabelFrame(master, text="Pi Coin Price Chart")
        self.graph_frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        self.current_price_label = ttk.Label(self.graph_frame, text="Current Pi Coin Price: $0.00", font=("Arial", 16, "bold"))
        self.current_price_label.pack(pady=5)
        self.graph_update_button = ttk.Button(self.graph_frame, text="Update Price Chart", command=self.manual_update_price_graph)
        self.graph_update_button.pack(pady=5)
        
        self.figure = Figure(figsize=(6,4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("Pi Coin Price Chart")
        self.ax.set_xlabel("Data Points")
        self.ax.set_ylabel("Price (USD)")
        self.canvas = FigureCanvasTkAgg(self.figure, self.graph_frame)
        self.canvas.get_tk_widget().pack(pady=10, fill="both", expand=True)
        
        # Periodically update earnings (every second)
        self.refresh_earnings()
        # Initial price update for earnings calculation
        self.update_prices_for_earnings()
        self.update_locked_pi()
    
    # ----- Data Persistence -----
    def load_price_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    self.price_history = json.load(f)
            except Exception as e:
                print("Error loading history:", e)
                self.price_history = []
        else:
            self.price_history = []
    
    def save_price_history(self):
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.price_history, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print("Error saving history:", e)
    
    # ----- API Calls -----
    def get_pi_price(self):
        url = "https://api.coingecko.com/api/v3/simple/price?ids=pi-network&vs_currencies=usd"
        try:
            response = requests.get(url, timeout=10).json()
            return response.get("pi-network", {}).get("usd", 0)
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Error", f"Error fetching Pi Coin price: {e}")
            return 0
    
    def get_usd_to_try(self):
        url = "https://api.coingecko.com/api/v3/simple/price?ids=usd&vs_currencies=try"
        try:
            response = requests.get(url, timeout=10).json()
            return response.get("usd", {}).get("try", 0)
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Error", f"Error fetching USD/TRY rate: {e}")
            return 0
    
    def get_usd_to_currency(self, currency_code):
        url = f"https://api.coingecko.com/api/v3/simple/price?ids=usd&vs_currencies={currency_code}"
        try:
            response = requests.get(url, timeout=10).json()
            return response.get("usd", {}).get(currency_code, 0)
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Error", f"Error fetching USD/{currency_code.upper()} rate: {e}")
            return 0

    def get_locked_pi(self):
        url = "https://api.minepi.com/wallet/locked"
        try:
            response = requests.get(url, timeout=10).json()
            return response.get("locked_balance", 0)
        except requests.exceptions.RequestException as e:
            print(f"Kitli Pi verisi çekilemedi: {e}")
            return 0
    
    # Update prices used in earnings calculation (every hour)
    def update_prices_for_earnings(self):
        # Capture the current custom currency code safely from the UI
        custom_code = self.custom_currency_code_entry.get().strip().lower()
        def task(code=custom_code):
            self.pi_price = self.get_pi_price()
            self.usd_to_try = self.get_usd_to_try()
            if code:
                self.custom_usd_rate = self.get_usd_to_currency(code)
        threading.Thread(target=task).start()
        self.master.after(3600000, self.update_prices_for_earnings)  # update every hour

    def update_locked_pi(self):
        def task():
            locked = self.get_locked_pi()
            self.master.after(0, lambda: self.locked_pi_label.config(text=f"Locked Pi: {locked} Pi"))
        threading.Thread(target=task).start()
        self.master.after(3600000, self.update_locked_pi)
    
    # ----- Earnings Calculation -----
    def update_earnings(self):
        try:
            hourly_earning = float(self.hourly_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid hourly earning!")
            return
        
        if self.pi_price == 0 or self.usd_to_try == 0:
            return
        
        daily_earning = hourly_earning * 24
        weekly_earning = daily_earning * 7
        monthly_earning = daily_earning * 30
        yearly_earning = monthly_earning * 12
        
        elapsed_minutes = (datetime.now() - self.start_time).total_seconds() / 60
        total_earning = (elapsed_minutes / 60) * hourly_earning
        total_try = total_earning * self.pi_price * self.usd_to_try
        
        self.daily_label.config(text=f"Daily Earnings: {daily_earning:.6f} Pi")
        self.weekly_label.config(text=f"Weekly Earnings: {weekly_earning:.6f} Pi")
        self.monthly_label.config(text=f"Monthly Earnings: {monthly_earning:.6f} Pi")
        self.yearly_label.config(text=f"Yearly Earnings: {yearly_earning:.6f} Pi")
        self.elapsed_label.config(text=f"Elapsed Time: {elapsed_minutes:.2f} minutes")
        self.total_try_label.config(text=f"Total Earnings: {total_try:.2f} ₺")
        
        # Custom Currency Earnings Calculation
        custom_code = self.custom_currency_code_entry.get().strip()
        custom_symbol = self.custom_currency_symbol_entry.get().strip()
        if custom_code and self.custom_usd_rate != 0:
            total_custom = total_earning * self.pi_price * self.custom_usd_rate
            self.total_custom_label.config(text=f"Total Earnings in {custom_code.upper()}: {total_custom:.2f} {custom_symbol}")
        else:
            self.total_custom_label.config(text="Total Earnings in Custom Currency: N/A")
    
    def refresh_earnings(self):
        self.update_earnings()
        self.master.after(1000, self.refresh_earnings)
    
    def manual_update_earnings(self):
        threading.Thread(target=self.update_prices_for_earnings).start()
        self.update_earnings()
    
    # ----- Price Chart Operations -----
    def manual_update_price_graph(self):
        def task():
            current_price = self.get_pi_price()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.price_history.append({"time": timestamp, "price": current_price})
            self.save_price_history()
            self.master.after(0, lambda: self.current_price_label.config(text=f"Current Pi Coin Price: ${current_price:.6f}"))
            self.master.after(0, self.update_price_graph)
        threading.Thread(target=task).start()
    
    def update_price_graph(self):
        prices = [entry["price"] for entry in self.price_history]
        x = list(range(len(prices)))
        self.ax.clear()
        self.ax.set_title("Pi Coin Price Chart")
        self.ax.set_xlabel("Data Points")
        self.ax.set_ylabel("Price (USD)")
        self.ax.plot(x, prices, marker='o', linestyle='-', color='b')
        self.canvas.draw()

if __name__ == "__main__":
    root = tk.Tk()
    app = PiCoinApp(root)
    root.mainloop()
