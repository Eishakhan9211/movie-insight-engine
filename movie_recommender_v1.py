import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# --- 1. DATA LOADING ---
print("Starting to load the IMDb dataset... please wait.")

try:
    # We use sep='\t' because .tsv files are Tab-Separated
    # na_values='\\N' tells pandas to treat IMDb's "\N" as empty data
    df = pd.read_csv(
        'title.basics.tsv', 
        sep='\t', 
        low_memory=False, 
        na_values='\\N',
        dtype=str
    )

    # --- 2. DATA CLEANING & PREPARATION ---
    print("Cleaning data for analysis...")

    # Filter for movies only and remove rows with missing critical info
    df = df[df['titleType'] == 'movie'].copy()
    df = df.dropna(subset=['startYear', 'genres', 'primaryTitle'])

    # Convert Year to actual numbers and filter out future/invalid dates
    df['startYear'] = pd.to_numeric(df['startYear'], errors='coerce')
    df = df.dropna(subset=['startYear'])
    df['startYear'] = df['startYear'].astype(int)
    
    # We focus on movies released up to the current year
    df = df[df['startYear'] <= 2026]

    print(f"Setup Complete! Analyzing {len(df):,} unique movie titles.")

    # --- 3. DATA VISUALIZATION (Scaled to Thousands) ---
    plt.figure(figsize=(12, 7))

    # Split multiple genres (e.g., 'Action,Comedy' becomes two entries) and count them
    genre_counts = df['genres'].str.split(',').explode().value_counts().head(10)

    # THE SCALE FIX: Convert raw numbers to Thousands for better readability
    genre_counts_k = genre_counts / 1000

    # Create the Bar Chart
    sns.barplot(
        x=genre_counts_k.values, 
        y=genre_counts_k.index, 
        palette='viridis', 
        edgecolor='black'
    )

    # Professional Labeling
    plt.title('Top 10 Movie Genres in the IMDb Dataset', fontsize=16, fontweight='bold')
    plt.xlabel('Number of Movies (in Thousands)', fontsize=12)
    plt.ylabel('Genres', fontsize=12)
    
    # Add a subtle grid to make the bars easier to track
    plt.grid(axis='x', linestyle='--', alpha=0.6)

    # Adjust layout to prevent text clipping
    plt.tight_layout()
    
    print("Generating visualization...")
    plt.show()

    # --- 4. THE RECOMMENDER FUNCTION ---
    def get_recommendations(genre_name):
        print(f"\n Top 5 Newest '{genre_name.title()}' Movies:")
        print("-" * 40)
        
        # Filter by genre and sort by year
        matches = df[df['genres'].str.contains(genre_name, case=False, na=False)]
        recs = matches.sort_values(by='startYear', ascending=False).head(5)
        
        if recs.empty:
            print(f"No movies found for genre: {genre_name}")
        else:
            # Display results in a clean format
            for i, row in enumerate(recs.itertuples(), 1):
                print(f"{i}. {row.primaryTitle} ({row.startYear})")

    # Example Test
    get_recommendations("Sci-Fi")

except FileNotFoundError:
    print("ERROR: 'title.basics.tsv' not found in the current folder.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")


# This line creates a prompt in your terminal/console
user_choice = input("Enter a genre (e.g., Comedy, Action, Horror): ")

# This line feeds that choice into your 'engine'
get_recommendations(user_choice)