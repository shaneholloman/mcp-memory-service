#!/usr/bin/env python3
"""
Generate statistical visualizations for MCP Memory Service repository.

This script creates charts from CSV data exports to visualize:
- Monthly commit and release trends
- Activity patterns by hour and day of week
- Contributor breakdown
- October 2025 sprint visualization

Usage:
    python generate_charts.py

Output:
    PNG files in docs/statistics/charts/
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 10

# Paths
DATA_DIR = Path(__file__).parent / "data"
CHARTS_DIR = Path(__file__).parent / "charts"
CHARTS_DIR.mkdir(exist_ok=True)

def create_monthly_activity_chart():
    """Create dual-axis chart showing commits and releases over time."""
    df = pd.read_csv(DATA_DIR / "monthly_activity.csv")

    fig, ax1 = plt.subplots(figsize=(14, 7))

    # Commits line
    color = 'tab:blue'
    ax1.set_xlabel('Month', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Commits', color=color, fontsize=12, fontweight='bold')
    ax1.plot(df['month'], df['commits'], color=color, marker='o', linewidth=2.5,
             markersize=8, label='Commits')
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.grid(True, alpha=0.3)

    # Releases bars
    ax2 = ax1.twinx()
    color = 'tab:orange'
    ax2.set_ylabel('Releases', color=color, fontsize=12, fontweight='bold')
    ax2.bar(df['month'], df['releases'], color=color, alpha=0.6, label='Releases')
    ax2.tick_params(axis='y', labelcolor=color)

    # Title and formatting
    plt.title('MCP Memory Service - Monthly Activity (Dec 2024 - Oct 2025)',
              fontsize=14, fontweight='bold', pad=20)

    # Rotate x-axis labels
    ax1.set_xticklabels(df['month'], rotation=45, ha='right')

    # Add legends
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=10)

    # Highlight October 2025
    oct_idx = df[df['month'] == '2025-10'].index[0]
    ax1.axvspan(oct_idx - 0.4, oct_idx + 0.4, alpha=0.2, color='red',
                label='October Sprint')

    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "monthly_activity.png", dpi=300, bbox_inches='tight')
    print("✅ Created: monthly_activity.png")
    plt.close()

def create_activity_heatmap():
    """Create heatmap showing activity by hour and day of week."""
    # Read hourly data
    hourly_df = pd.read_csv(DATA_DIR / "activity_by_hour.csv")
    daily_df = pd.read_csv(DATA_DIR / "activity_by_day.csv")

    # Create a simulated day x hour matrix (for visualization purposes)
    # In reality, we'd need actual day+hour data from git log
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    hours = range(24)

    # Create visualization showing just hourly distribution
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

    # Hourly activity bar chart
    ax1.bar(hourly_df['hour'], hourly_df['commits'], color='steelblue', alpha=0.8)
    ax1.set_xlabel('Hour of Day', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Number of Commits', fontsize=12, fontweight='bold')
    ax1.set_title('Activity by Hour of Day', fontsize=14, fontweight='bold', pad=15)
    ax1.grid(axis='y', alpha=0.3)

    # Highlight peak hours (20-22)
    peak_hours = [20, 21, 22]
    for hour in peak_hours:
        idx = hourly_df[hourly_df['hour'] == hour].index[0]
        ax1.bar(hour, hourly_df.loc[idx, 'commits'], color='red', alpha=0.7)

    ax1.text(21, 170, 'Peak Hours\n(19:00-23:00)\n46% of commits',
             ha='center', va='bottom', fontsize=11,
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # Day of week activity
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    daily_sorted = daily_df.set_index('day_of_week').loc[day_order].reset_index()

    colors = ['steelblue' if day not in ['Saturday', 'Sunday'] else 'orange'
              for day in daily_sorted['day_of_week']]

    ax2.barh(daily_sorted['day_of_week'], daily_sorted['commits'], color=colors, alpha=0.8)
    ax2.set_xlabel('Number of Commits', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Day of Week', fontsize=12, fontweight='bold')
    ax2.set_title('Activity by Day of Week', fontsize=14, fontweight='bold', pad=15)
    ax2.grid(axis='x', alpha=0.3)

    # Add percentage labels
    for idx, row in daily_sorted.iterrows():
        ax2.text(row['commits'] + 5, idx, row['percentage'],
                va='center', fontsize=10)

    ax2.text(250, 5.5, 'Weekend\nWarrior\n39% total',
             ha='center', va='center', fontsize=11,
             bbox=dict(boxstyle='round', facecolor='orange', alpha=0.3))

    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "activity_patterns.png", dpi=300, bbox_inches='tight')
    print("✅ Created: activity_patterns.png")
    plt.close()

def create_contributor_pie_chart():
    """Create pie chart showing contributor distribution."""
    df = pd.read_csv(DATA_DIR / "contributors.csv")

    # Combine Henry, doobidoo, Heinrich Krupp (same person)
    primary_commits = df[df['contributor'].isin(['Henry', 'doobidoo', 'Heinrich Krupp'])]['commits'].sum()
    other_commits = df[~df['contributor'].isin(['Henry', 'doobidoo', 'Heinrich Krupp'])]['commits'].sum()

    labels = [f'Primary Maintainer\n(Henry + aliases)', 'External Contributors']
    sizes = [primary_commits, other_commits]
    colors = ['#FF9999', '#66B2FF']
    explode = (0.1, 0)

    fig, ax = plt.subplots(figsize=(10, 8))

    wedges, texts, autotexts = ax.pie(sizes, explode=explode, labels=labels, colors=colors,
                                        autopct='%1.1f%%', shadow=True, startangle=90,
                                        textprops={'fontsize': 12, 'fontweight': 'bold'})

    # Make percentage text larger
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(14)
        autotext.set_fontweight('bold')

    ax.set_title('Contributor Distribution (1,536 total commits)',
                 fontsize=14, fontweight='bold', pad=20)

    # Add legend with individual contributors
    top_contributors = df.head(10)
    legend_labels = [f"{row['contributor']}: {row['commits']} ({row['percentage']})"
                     for _, row in top_contributors.iterrows()]

    plt.legend(legend_labels, title="Top 10 Contributors",
              loc='center left', bbox_to_anchor=(1, 0, 0.5, 1), fontsize=9)

    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "contributors.png", dpi=300, bbox_inches='tight')
    print("✅ Created: contributors.png")
    plt.close()

def create_october_sprint_chart():
    """Create detailed visualization of October 2025 sprint."""
    # October daily data (from earlier analysis)
    oct_days = [2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 16, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31]
    oct_commits = [16, 46, 26, 9, 2, 14, 9, 1, 7, 13, 3, 12, 4, 5, 5, 9, 15, 16, 5, 38, 5, 24, 1, 12, 12]

    fig, ax = plt.subplots(figsize=(16, 7))

    # Bar chart
    bars = ax.bar(oct_days, oct_commits, color='steelblue', alpha=0.8)

    # Highlight the sprint days (28-31)
    sprint_days = [28, 29, 30, 31]
    for i, day in enumerate(oct_days):
        if day in sprint_days:
            bars[i].set_color('red')
            bars[i].set_alpha(0.9)

    ax.set_xlabel('Day of October 2025', fontsize=12, fontweight='bold')
    ax.set_ylabel('Number of Commits', fontsize=12, fontweight='bold')
    ax.set_title('October 2025: The Sprint Month (310 commits, 65 releases)',
                 fontsize=14, fontweight='bold', pad=20)
    ax.grid(axis='y', alpha=0.3)

    # Add annotations for key days
    ax.annotate('Peak Day\n46 commits', xy=(3, 46), xytext=(3, 52),
                ha='center', fontsize=10, fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))

    ax.annotate('13 Releases\nin 4 Days', xy=(29.5, 35), xytext=(29.5, 42),
                ha='center', fontsize=11, fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='red', alpha=0.3),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))

    # Add text box with sprint details
    sprint_text = 'Oct 28-31 Sprint:\n• v8.12.0 → v8.15.1\n• 13 releases\n• 49 commits\n• Production bugs fixed'
    ax.text(8, 40, sprint_text, fontsize=11,
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))

    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "october_sprint.png", dpi=300, bbox_inches='tight')
    print("✅ Created: october_sprint.png")
    plt.close()

def create_growth_trajectory():
    """Create cumulative commits chart showing growth over time."""
    df = pd.read_csv(DATA_DIR / "monthly_activity.csv")

    # Calculate cumulative commits
    df['cumulative_commits'] = df['commits'].cumsum()
    df['cumulative_releases'] = df['releases'].cumsum()

    fig, ax1 = plt.subplots(figsize=(14, 7))

    # Cumulative commits
    color = 'tab:blue'
    ax1.set_xlabel('Month', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Cumulative Commits', color=color, fontsize=12, fontweight='bold')
    ax1.plot(df['month'], df['cumulative_commits'], color=color, marker='o',
             linewidth=3, markersize=8, label='Cumulative Commits')
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.grid(True, alpha=0.3)
    ax1.fill_between(range(len(df)), df['cumulative_commits'], alpha=0.3, color=color)

    # Cumulative releases
    ax2 = ax1.twinx()
    color = 'tab:green'
    ax2.set_ylabel('Cumulative Releases', color=color, fontsize=12, fontweight='bold')
    ax2.plot(df['month'], df['cumulative_releases'], color=color, marker='s',
             linewidth=3, markersize=8, label='Cumulative Releases', linestyle='--')
    ax2.tick_params(axis='y', labelcolor=color)

    # Title
    plt.title('MCP Memory Service - Growth Trajectory (10 Months)',
              fontsize=14, fontweight='bold', pad=20)

    # Rotate labels
    ax1.set_xticklabels(df['month'], rotation=45, ha='right')

    # Add milestone annotations
    ax1.annotate('First Release\nv1.0', xy=(0, 55), xytext=(1, 200),
                ha='center', fontsize=10,
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0.3'))

    ax1.annotate('1,000th\nCommit', xy=(8, 1000), xytext=(7, 1200),
                ha='center', fontsize=10,
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=-0.3'))

    # Legends
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=10)

    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "growth_trajectory.png", dpi=300, bbox_inches='tight')
    print("✅ Created: growth_trajectory.png")
    plt.close()

def main():
    """Generate all charts."""
    print("🎨 Generating statistical visualizations...")
    print()

    create_monthly_activity_chart()
    create_activity_heatmap()
    create_contributor_pie_chart()
    create_october_sprint_chart()
    create_growth_trajectory()

    print()
    print("✅ All charts generated successfully!")
    print(f"📁 Output directory: {CHARTS_DIR}")
    print()
    print("Generated charts:")
    print("  1. monthly_activity.png - Commits and releases over time")
    print("  2. activity_patterns.png - Hourly and daily patterns")
    print("  3. contributors.png - Contributor distribution")
    print("  4. october_sprint.png - October 2025 detailed view")
    print("  5. growth_trajectory.png - Cumulative growth")

if __name__ == "__main__":
    main()
