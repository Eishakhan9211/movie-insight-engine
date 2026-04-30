# IMDb Movie Insight & Recommendation Engine 

## Project Overview
This project processes over 500,000 IMDb movie records to analyze global film trends. It features a Dynamic Query Engine that allows users to filter the massive dataset by genre and instantly receive the top 5 newest recommendations.

## Core Features
*   Big Data Wrangling: Cleans and formats raw `.tsv` files containing millions of data points.
*   Genre Explosion: Uses advanced Pandas logic to handle movies with multiple genre tags.
*   Visual Analytics: Generates a professional distribution chart of the Top 10 genres.
*   Search Engine: A functional Python tool that sorts and filters data based on real-time user input.

## Data Visualization
![Genre Trends](movie_genres_chart.png)

## How to Use
1. Clone this repo.
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `python movie_recommender_v1.py`
4. Close the graph window to trigger the interactive search prompt!

## Dataset
This project uses the IMDb Non-Commercial Dataset.
File used: title.basics.tsv.gz (Unzip this file into the project folder before running).
Source: [IMDb Datasets](https://developer.imdb.com/non-commercial-dataset/)
