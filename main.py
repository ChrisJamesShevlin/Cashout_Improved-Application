import tkinter as tk

class MatchData:
    def __init__(self, model_odds, bookmaker_odds, live_odds, sot_fav, sot_underdog, match_time, fav_goals, underdog_goals, xg_fav, xg_underdog, possession_fav, possession_underdog, lay_choice):
        self.model_odds = model_odds
        self.bookmaker_odds = bookmaker_odds
        self.live_odds = live_odds
        self.sot_fav = sot_fav
        self.sot_underdog = sot_underdog
        self.match_time = match_time
        self.fav_goals = fav_goals
        self.underdog_goals = underdog_goals
        self.xg_fav = xg_fav
        self.xg_underdog = xg_underdog
        self.possession_fav = possession_fav
        self.possession_underdog = possession_underdog
        self.lay_choice = lay_choice

class MatchMemory:
    def __init__(self, history_length=10):
        self.history_length = history_length
        self.history = []

    def update_memory(self, current_data):
        """Store past records, keeping only the last `history_length` entries."""
        if len(self.history) >= self.history_length:
            self.history.pop(0)  # Remove oldest entry to keep history size constant
        self.history.append(current_data)

    def get_average_momentum(self):
        """Calculate the average trend over the stored history."""
        if len(self.history) < 2:
            return None  # Not enough data points for momentum calculation

        total_sot_fav, total_sot_underdog = 0, 0
        total_xg_fav, total_xg_underdog = 0, 0
        total_possession_fav, total_possession_underdog = 0, 0

        for data in self.history:
            total_sot_fav += data.sot_fav
            total_sot_underdog += data.sot_underdog
            total_xg_fav += data.xg_fav
            total_xg_underdog += data.xg_underdog
            total_possession_fav += data.possession_fav
            total_possession_underdog += data.possession_underdog

        avg_sot_fav = total_sot_fav / len(self.history)
        avg_sot_underdog = total_sot_underdog / len(self.history)
        avg_xg_fav = total_xg_fav / len(self.history)
        avg_xg_underdog = total_xg_underdog / len(self.history)
        avg_possession_fav = total_possession_fav / len(self.history)
        avg_possession_underdog = total_possession_underdog / len(self.history)

        return {
            "sot_fav": avg_sot_fav,
            "sot_underdog": avg_sot_underdog,
            "xg_fav": avg_xg_fav,
            "xg_underdog": avg_xg_underdog,
            "possession_fav": avg_possession_fav,
            "possession_underdog": avg_possession_underdog,
        }

memory = MatchMemory(history_length=10)  # Store last 10 updates

def calculate_decision():
    try:
        match_data = MatchData(
            model_odds=float(entries["entry_model_odds"].get()),
            bookmaker_odds=float(entries["entry_bookmaker_odds"].get()),
            live_odds=float(entries["entry_live_odds"].get()),
            sot_fav=int(entries["entry_sot_fav"].get()),
            sot_underdog=int(entries["entry_sot_underdog"].get()),
            match_time=int(entries["entry_match_time"].get()),
            fav_goals=int(entries["entry_fav_goals"].get()),
            underdog_goals=int(entries["entry_underdog_goals"].get()),
            xg_fav=float(entries["entry_xg_fav"].get()),
            xg_underdog=float(entries["entry_xg_underdog"].get()),
            possession_fav=float(entries["entry_possession_fav"].get()),
            possession_underdog=float(entries["entry_possession_underdog"].get()),
            lay_choice=lay_choice_var.get()
        )
        
        updated_edge = (1 / match_data.live_odds) - (1 / match_data.model_odds)
        p_goal = max(0.50 - 0.0045 * match_data.match_time, 0.10)
        
        total_sot = match_data.sot_fav + match_data.sot_underdog
        p_goal += 0.020 * total_sot if total_sot >= 6 else -0.05
        
        combined_xg = match_data.xg_fav + match_data.xg_underdog
        p_goal += 0.02 * combined_xg if combined_xg >= 1.2 else -0.10
        
        # Determine which team contributes more to goal probability
        fav_contribution = (match_data.xg_fav * 0.4) + (match_data.sot_fav * 0.3) + (match_data.fav_goals * 0.3)
        underdog_contribution = (match_data.xg_underdog * 0.4) + (match_data.sot_underdog * 0.3) + (match_data.underdog_goals * 0.3)

        if fav_contribution > underdog_contribution:
            goal_source = "Favourite"
            p_goal -= 0.04  # Slight bias towards stronger team
        elif underdog_contribution > fav_contribution:
            goal_source = "Underdog"
            p_goal += 0.04  # More variance for weaker team scoring
        else:
            goal_source = "Even"

        p_goal = min(max(p_goal, 0), 1.0)

        ev_hold = (1 - p_goal) * (1 / match_data.live_odds) - p_goal * (1 / match_data.model_odds)
        ev_cashout = 1 / match_data.live_odds
        
        possession_gap = abs(match_data.possession_fav - match_data.possession_underdog)
        likely_draw = (
            p_goal < 0.12 and
            possession_gap <= 10 and
            abs(match_data.xg_fav - match_data.xg_underdog) < 0.3 and
            abs(match_data.sot_fav - match_data.sot_underdog) <= 2 and
            match_data.match_time >= 80 and
            match_data.fav_goals == match_data.underdog_goals
        )
        
        decision = "Hold"
        if likely_draw:
            decision = "Cash Out"
        elif ev_cashout > ev_hold + 0.07 and match_data.match_time >= 80:  # Increased threshold to reduce noise
            decision = "Cash Out"
        
        if match_data.match_time >= 85 and p_goal < 12 / 100:
            decision = "Cash Out"

        # Additional logic for laying the underdog
        if match_data.lay_choice == "Underdog" and match_data.underdog_goals == 0 and match_data.fav_goals == 1:
            if match_data.xg_underdog > match_data.xg_fav and match_data.possession_underdog > match_data.possession_fav:
                decision = "Cash Out"

        # Check if the underdog is improving on stats with dynamic thresholds
        thresholds = {
            'sot': 1.0 if match_data.match_time < 60 else 1.5,  # More lenient late-game
            'xg': 0.2 if match_data.match_time < 60 else 0.4,   # Requires bigger xG change
            'possession': 3.0 if match_data.match_time < 60 else 6.0  # Requires bigger possession gap
        }

        average_momentum = memory.get_average_momentum()
        
        if average_momentum:
            # Calculate recent trend by comparing last momentum to current input
            recent_trend_sot_underdog = match_data.sot_underdog - average_momentum["sot_underdog"]
            recent_trend_xg_underdog = match_data.xg_underdog - average_momentum["xg_underdog"]
            recent_trend_possession_underdog = match_data.possession_underdog - average_momentum["possession_underdog"]

            recent_trend_sot_fav = match_data.sot_fav - average_momentum["sot_fav"]
            recent_trend_xg_fav = match_data.xg_fav - average_momentum["xg_fav"]
            recent_trend_possession_fav = match_data.possession_fav - average_momentum["possession_fav"]

            # Set dynamic thresholds for early/mid/late-game
            if match_data.match_time < 60:
                sot_threshold, xg_threshold, possession_threshold = 1.0, 0.2, 3.0
            elif match_data.match_time < 80:
                sot_threshold, xg_threshold, possession_threshold = 1.5, 0.4, 6.0
            else:
                sot_threshold, xg_threshold, possession_threshold = 2.0, 0.6, 8.0  # More lenient late-game

            # If the underdog is gaining momentum at a higher rate than expected, consider cashing out
            if match_data.lay_choice == "Underdog":
                if (
                    recent_trend_sot_underdog > sot_threshold or
                    recent_trend_xg_underdog > xg_threshold or
                    recent_trend_possession_underdog > possession_threshold
                ):
                    decision = "Cash Out (Underdog Momentum Increasing)"

            elif match_data.lay_choice == "Favourite":
                if (
                    recent_trend_sot_fav > sot_threshold or
                    recent_trend_xg_fav > xg_threshold or
                    recent_trend_possession_fav > possession_threshold
                ):
                    decision = "Cash Out (Favourite Momentum Increasing)"

        result_label["text"] = (
            f"Updated Edge: {updated_edge:.4f}\n"
            f"Goal Probability: {p_goal:.2%} ({goal_source})\n"
            f"EV Hold: {ev_hold:.4f}\n"
            f"EV Cashout: {ev_cashout:.4f}\n"
            f"Decision: {decision}"
        )
        result_label["foreground"] = "green" if decision == "Hold" else "red"

        memory.update_memory(match_data)

    except ValueError:
        result_label["text"] = "Please enter valid numerical values."
        result_label["foreground"] = "black"

def reset_fields():
    for entry in entries.values():
        entry.delete(0, tk.END)
    result_label["text"] = ""
    lay_choice_var.set("Favourite")
    memory.update_memory(None)

root = tk.Tk()
root.title("Decision Calculator")

entries = {key: tk.Entry(root) for key in [
    "entry_model_odds", "entry_bookmaker_odds", "entry_live_odds", "entry_sot_fav", "entry_sot_underdog", "entry_match_time", 
    "entry_fav_goals", "entry_underdog_goals", "entry_xg_fav", "entry_xg_underdog", "entry_possession_fav", "entry_possession_underdog"
]}

result_label = tk.Label(root, text="", font=("Helvetica", 12))
for i, (key, entry) in enumerate(entries.items()):
    tk.Label(root, text=key.replace("entry_", "").replace("_", " ").title()).grid(row=i, column=0)
    entry.grid(row=i, column=1)

lay_choice_var = tk.StringVar(value="Favourite")
lay_choice_label = tk.Label(root, text="Lay Choice")
lay_choice_label.grid(row=len(entries), column=0)
lay_choice_menu = tk.OptionMenu(root, lay_choice_var, "Favourite", "Underdog", "Draw")
lay_choice_menu.grid(row=len(entries), column=1)

tk.Button(root, text="Calculate Decision", command=calculate_decision).grid(row=len(entries) + 1, column=0, columnspan=2)
tk.Button(root, text="Reset Fields", command=reset_fields).grid(row=len(entries) + 2, column=0, columnspan=2)
result_label.grid(row=len(entries) + 3, column=0, columnspan=2)

root.mainloop()
