import pandas as pd
import re

def normalize_coordinates(input_file, output_file):
    df = pd.read_csv(input_file)
    
    print(f"Original data shape: {df.shape}")
    
    def normalize_coord(coord_str):
        if pd.isna(coord_str) or coord_str == "":
            return coord_str
        
        coords = coord_str.split(',')
        if len(coords) == 2:
            try:
                lat = float(coords[0].strip())
                lon = float(coords[1].strip())
                return f"{lat:.2f},{lon:.2f}"
            except ValueError:
                return coord_str
        return coord_str
    
    df['centroid_normalized'] = df['centroid'].apply(normalize_coord)
    
    print(f"Number of unique original centroids: {df['centroid'].nunique()}")
    print(f"Number of unique normalized centroids: {df['centroid_normalized'].nunique()}")
    
    df_deduplicated = df.drop_duplicates(subset=['centroid_normalized'], keep='first')
    
    df_final = df_deduplicated.copy()
    df_final['centroid'] = df_final['centroid_normalized']
    df_final = df_final.drop('centroid_normalized', axis=1)
    
    print(f"Final data shape: {df_final.shape}")
    print(f"Removed {df.shape[0] - df_final.shape[0]} duplicate rows")
    
    df_final.to_csv(output_file, index=False)
    print(f"Normalized and deduplicated data saved to: {output_file}")
    
    return df_final

if __name__ == "__main__":
    input_file = "BangaloreCords.csv"
    output_file = "BangaloreCords_normalized.csv"
    
    result_df = normalize_coordinates(input_file, output_file)
    
    print("\nSample of normalized coordinates:")
    print(result_df[['id', 'centroid']].head(10)) 