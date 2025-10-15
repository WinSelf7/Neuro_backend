#!/usr/bin/env python3
import os
import shutil
import sys

def find_lmdeploy_calibrate_file():
    """Automatically find the lmdeploy calibrate.py file in current environment"""
    try:
        import lmdeploy
        lmdeploy_path = os.path.dirname(lmdeploy.__file__)
        calibrate_file = os.path.join(lmdeploy_path, 'lite', 'apis', 'calibrate.py')
        
        if os.path.exists(calibrate_file):
            return calibrate_file
        else:
            print(f"Error: calibrate.py file not found, expected path: {calibrate_file}")
            return None
    except ImportError:
        print("Error: lmdeploy is not installed in current environment")
        return None

def patch_calibrate_file(calibrate_file):
    """Patch the calibrate.py file by commenting out problematic code"""
    # Read file content
    try:
        with open(calibrate_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error: Failed to read file - {e}")
        return False

    # Check if already patched
    if "# if hasattr(vl_model, 'language_model')" in content:
        print("✓ File already patched")
        return True

    # Replace problematic code
    old_code = """        if hasattr(vl_model, 'language_model'):  # deepseek-vl, ...
            model = vl_model.language_model
        if hasattr(vl_model, 'llm'):  # MiniCPMV, ...
            model = vl_model.llm"""

    new_code = """        # if hasattr(vl_model, 'language_model'):  # deepseek-vl, ...
        #     model = vl_model.language_model
        # if hasattr(vl_model, 'llm'):  # MiniCPMV, ...
        #     model = vl_model.llm"""

    if old_code in content:
        content = content.replace(old_code, new_code)
        
        # Write back to file
        try:
            with open(calibrate_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print("✓ Patch applied successfully!")
            return True
        except Exception as e:
            print(f"Error: Failed to write file - {e}")
            return False
    else:
        print("⚠ Expected code snippet not found, lmdeploy version might be different")
        print("Please check the file content manually")
        return False

def restore_calibrate_file(calibrate_file):
    """Restore the calibrate.py file by removing comment symbols"""
    # Check if backup exists
    backup_file = calibrate_file + ".backup"
    if os.path.exists(backup_file):
        try:
            shutil.copy(backup_file, calibrate_file)
            print("✓ File restored from backup")
            return True
        except Exception as e:
            print(f"Error: Failed to restore from backup - {e}")
            return False
    
    # Manual restore by uncommenting
    try:
        with open(calibrate_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error: Failed to read file - {e}")
        return False

    # Check if file is in patched state
    if "# if hasattr(vl_model, 'language_model')" not in content:
        print("✓ File is already in original state")
        return True

    # Restore by uncommenting
    patched_code = """        # if hasattr(vl_model, 'language_model'):  # deepseek-vl, ...
        #     model = vl_model.language_model
        # if hasattr(vl_model, 'llm'):  # MiniCPMV, ...
        #     model = vl_model.llm"""

    original_code = """        if hasattr(vl_model, 'language_model'):  # deepseek-vl, ...
            model = vl_model.language_model
        if hasattr(vl_model, 'llm'):  # MiniCPMV, ...
            model = vl_model.llm"""

    if patched_code in content:
        content = content.replace(patched_code, original_code)
        
        try:
            with open(calibrate_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print("✓ File restored successfully!")
            return True
        except Exception as e:
            print(f"Error: Failed to write file - {e}")
            return False
    else:
        print("⚠ Patched code not found, cannot restore")
        return False

def show_usage():
    """Show usage information"""
    print("Usage:")
    print("  python fix_qwen2_5_vl_awq.py patch     # Apply patch for Qwen2.5-VL AWQ quantization")
    print("  python fix_qwen2_5_vl_awq.py restore   # Restore original file")

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ['patch', 'restore']:
        show_usage()
        sys.exit(1)
    
    command = sys.argv[1]
    
    print("Auto-detecting lmdeploy installation path...")
    
    # Automatically find calibrate.py file
    calibrate_file = find_lmdeploy_calibrate_file()
    if not calibrate_file:
        sys.exit(1)
    
    print(f"Found file: {calibrate_file}")
    
    if command == 'patch':
        # Backup original file before patching
        backup_file = calibrate_file + ".backup"
        if not os.path.exists(backup_file):
            shutil.copy(calibrate_file, backup_file)
            print("✓ Original file backed up")
        else:
            print("✓ Backup file already exists")
        
        if patch_calibrate_file(calibrate_file):
            print("\n🎉 Now you can run Qwen2.5-VL AWQ quantization!")
            print("Use command:")
            print("lmdeploy lite auto_awq \\")
            print("    ./model_weight/Recognition \\")
            print("    --calib-dataset 'ptb' \\")
            print("    --calib-samples 64 \\")
            print("    --calib-seqlen 1024 \\")
            print("    --w-bits 4 \\")
            print("    --w-group-size 128 \\")
            print("    --batch-size 1 \\")
            print("    --work-dir ./monkeyocr_quantization")
    
    elif command == 'restore':
        if restore_calibrate_file(calibrate_file):
            print("\n✓ File has been restored to original state")

if __name__ == "__main__":
    main()
