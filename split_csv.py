import csv

INPUT_CSV = "lowCords.csv"  # Change this to your input CSV filename
OUTPUT_PREFIX = "BangCords"  # Output files will be output_part1.csv, output_part2.csv, etc.
NUM_PARTS = 4

def split_csv(input_csv, num_parts, output_prefix):
    with open(input_csv, 'r', encoding='utf-8', newline='') as infile:
        reader = list(csv.reader(infile))
        header = reader[0]
        rows = reader[1:]
        total_rows = len(rows)
        part_size = (total_rows + num_parts - 1) // num_parts  # Ceiling division
        
        for i in range(num_parts):
            start = i * part_size
            end = min(start + part_size, total_rows)
            part_rows = rows[start:end]
            output_file = f"{output_prefix}{i+1}.csv"
            with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
                writer = csv.writer(outfile)
                writer.writerow(header)
                writer.writerows(part_rows)
            print(f"Wrote {len(part_rows)} rows to {output_file}")

if __name__ == "__main__":
    split_csv(INPUT_CSV, NUM_PARTS, OUTPUT_PREFIX) 