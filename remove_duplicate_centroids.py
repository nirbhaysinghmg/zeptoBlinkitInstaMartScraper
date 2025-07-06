import pandas as pd

def remove_duplicate_centroids(input_file, output_file):
    df = pd.read_csv(input_file)
    
    print(f"Original data shape: {df.shape}")
    print(f"Number of unique centroids: {df['centroid'].nunique()}")
    
    df_deduplicated = df.drop_duplicates(subset=['centroid'], keep='first')
    
    print(f"Deduplicated data shape: {df_deduplicated.shape}")
    print(f"Removed {df.shape[0] - df_deduplicated.shape[0]} duplicate rows")
    
    df_deduplicated.to_csv(output_file, index=False)
    print(f"Deduplicated data saved to: {output_file}")

if __name__ == "__main__":
    input_file = "BangaloreCords.csv"
    output_file = "BangaloreCords_deduplicated.csv"
    
    remove_duplicate_centroids(input_file, output_file) 