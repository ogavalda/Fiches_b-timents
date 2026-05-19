import pandas as pd
import matplotlib.pyplot as plt


def prepare_profile_data(df):
    dt = pd.to_datetime(df["time_key"], format="%m-%d %H:%M")

    df["date"] = dt.dt.strftime("%m-%d")
    df["hour"] = dt.dt.hour
    df["month"] = dt.dt.month

    # weekday / weekend
    df["day_type"] = dt.dt.weekday.apply(
        lambda x: "weekday" if x < 5 else "weekend"
    )

    return df


def get_season(month):
    if month in [12,1,2,3]:
        return 'winter'
    elif month in [6,7,8]:
        return 'summer'
    else:
        return 'mild'

def plot_daily_profiles_ope_vs_meter(df, output_path,lang):

    df = prepare_profile_data(df)

    df["season"] = df["month"].apply(get_season)

    # --- Pivot ---
    daily_profiles = df.pivot_table(
        values=["OPE", "meter"],
        index="date",
        columns="hour",
        aggfunc="mean"
    )

    # Flatten columns
    daily_profiles.columns = [
        f"{var}_{hour}" for var, hour in daily_profiles.columns
    ]

    # Meta info
    meta = df.groupby("date")[["season", "day_type"]].first()
    daily_profiles = daily_profiles.join(meta)

    # --- Plot ---
    fig, axes = plt.subplots(3, 2, figsize=(14,16), sharex=True, sharey=True)

    seasons = ['winter','mild','summer']
    types = ['weekday','weekend']


    for i, season in enumerate(seasons):
        for j, day_type in enumerate(types):

            ax = axes[i, j]

            subset = daily_profiles[
                (daily_profiles['season'] == season) &
                (daily_profiles['day_type'] == day_type)
            ]

            if len(subset) == 0:
                continue

            # --- Meter: plot ALL (noisy, transparent red) ---
            for _, row in subset.iterrows():

                meter_profile = [row[f"meter_{h}"] for h in range(24)]
                ax.plot(range(24), meter_profile,
                        color="red", alpha=0.15)

            # --- Meter average (dashed red) ---
            meter_mean = [
                subset[f"meter_{h}"].mean() for h in range(24)
            ]

            ax.plot(range(24), meter_mean,
                    color="red", linestyle="--", linewidth=2,
                    label="Meter Avg" if (i == 0 and j == 0) else "")

            # --- OPE: ONLY average (bold blue) ---
            ope_mean = [
                subset[f"OPE_{h}"].mean() for h in range(24)
            ]

            ax.plot(range(24), ope_mean,
                    color="blue", linewidth=3,
                    label="OPE Avg" if (i == 0 and j == 0) else "")

            ax.set_title(f"{season} - {day_type}")
            if lang=="eng":
                ax.set_xlabel("Hour of Day")
                ax.set_ylabel("Consumption (kWh)")
            else:
                ax.set_xlabel("Heure du jour")
                ax.set_ylabel("Consommation (kWh)")
            ax.set_xlim(0, 23)
            ax.grid(True)

    plt.tight_layout()
    #plt.legend()
    plt.savefig(output_path)
    plt.close()


