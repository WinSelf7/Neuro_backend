#!/usr/bin/env python3
"""
Clear Python cache files
Run this script if you encounter import or model errors
"""
import os
import shutil
from pathlib import Path

def clear_pycache(directory):
    """Recursively remove __pycache__ directories"""
    count = 0
    for root, dirs, files in os.walk(directory):
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            print(f"Removing: {pycache_path}")
            shutil.rmtree(pycache_path)
            count += 1
    return count

if __name__ == "__main__":
    backend_dir = Path(__file__).parent
    print(f"Clearing cache in: {backend_dir}")
    
    count = clear_pycache(backend_dir)
    
    print(f"\n✅ Cleared {count} __pycache__ directories")
    print("You can now run the backend server.")

