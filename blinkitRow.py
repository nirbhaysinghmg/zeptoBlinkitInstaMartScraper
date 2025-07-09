import csv

def filter_bangalore(input_file, output_file):
    # Read input and filter rows
    with open(input_file, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        
        # Verify city column exists
        if 'city' not in reader.fieldnames:
            raise ValueError("'city' column not found in input file")
        
        # Filter rows where city == 'bangalore'
        bangalore_rows = [
            row for row in reader
            if row['city'].lower().strip() == 'bangalore'
        ]
    
    # Write output
    with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
        if bangalore_rows:
            writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)
            writer.writeheader()
            writer.writerows(bangalore_rows)
            print(f"✅ Saved {len(bangalore_rows)} Bangalore records to {output_file}")
        else:
            print("❌ No Bangalore records found")

if __name__ == "__main__":
    input_csv = "blinkitCords.csv"    # your input CSV
    output_csv = "BangaloreCords.csv" # desired output CSV
    
    filter_bangalore(input_csv, output_csv)
