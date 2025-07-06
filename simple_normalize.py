import pandas as pd

def normalize_coordinates_simple(input_file, output_file):
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
    
    df['centroid'] = df['centroid'].apply(normalize_coord)
    
    df.to_csv(output_file, index=False)
    print(f"Normalized coordinates saved to: {output_file}")
    
    print("\nSample of normalized coordinates:")
    print(df[['id', 'centroid']].head(10))
    
    return df

if __name__ == "__main__":
    input_file = "BangaloreCords.csv"
    output_file = "BangaloreCords_simple_normalized.csv"
    
    result_df = normalize_coordinates_simple(input_file, output_file) 