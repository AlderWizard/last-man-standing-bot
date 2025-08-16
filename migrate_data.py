#!/usr/bin/env python3
"""
Data Migration Script for Last Man Standing Bot
Export data from Render and import to Raspberry Pi
"""

import sqlite3
import json
import sys
from pathlib import Path

def export_data(db_path="lastman.db"):
    """Export all game data to JSON format"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # This enables column access by name
        cursor = conn.cursor()
        
        data = {}
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"Found tables: {tables}")
        
        # Export each table
        for table in tables:
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            data[table] = [dict(row) for row in rows]
            print(f"Exported {len(rows)} rows from {table}")
        
        # Save to JSON file
        export_file = "bot_data_export.json"
        with open(export_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"✅ Data exported to {export_file}")
        print(f"📊 Total tables exported: {len(tables)}")
        
        conn.close()
        return export_file
        
    except Exception as e:
        print(f"❌ Export failed: {e}")
        return None

def import_data(json_file="bot_data_export.json", db_path="lastman.db"):
    """Import data from JSON to database"""
    try:
        # Load JSON data
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Clear existing data (optional - comment out if you want to merge)
        print("🗑️ Clearing existing data...")
        for table_name in data.keys():
            cursor.execute(f"DELETE FROM {table_name}")
        
        # Import data
        for table_name, rows in data.items():
            if not rows:
                print(f"⏭️ Skipping empty table: {table_name}")
                continue
                
            # Get column names from first row
            columns = list(rows[0].keys())
            placeholders = ', '.join(['?' for _ in columns])
            
            # Insert data
            insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
            
            for row in rows:
                values = [row[col] for col in columns]
                cursor.execute(insert_sql, values)
            
            print(f"✅ Imported {len(rows)} rows to {table_name}")
        
        conn.commit()
        conn.close()
        
        print(f"🎉 Data import completed successfully!")
        
    except Exception as e:
        print(f"❌ Import failed: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Export: python migrate_data.py export")
        print("  Import: python migrate_data.py import [json_file]")
        return
    
    command = sys.argv[1].lower()
    
    if command == "export":
        export_data()
    elif command == "import":
        json_file = sys.argv[2] if len(sys.argv) > 2 else "bot_data_export.json"
        import_data(json_file)
    else:
        print("Invalid command. Use 'export' or 'import'")

if __name__ == "__main__":
    main()
