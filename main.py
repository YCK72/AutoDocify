import tkinter as tk
from tkinter import filedialog
from pathlib import Path
import json
import sys
import os

# Ensure current directory is in Python path (only needed if you ever move this)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import project modules (these should be in the same folder)
from scanner import scan_python_files
from parser import parse_ast
from introspector import introspect_module
from builder import build_metadata
from utils import make_json_serializable

# Module 2 imports
from doc_generator import generate_function_doc, generate_class_doc
# Optional: for README generation
from doc_generator import generate_readme

def select_python_file():
    """Open a file dialog for the user to choose a Python file."""
    root = tk.Tk()
    root.withdraw()  # Hide the main tkinter window
    file_path = filedialog.askopenfilename(
        title="Select a Python File",
        filetypes=[("Python Files", "*.py")]
    )
    return file_path


def run_module1_on_file(file_path, save_to=None):
    print(f"\n📄 Processing: {file_path}")

    if not scan_python_files(file_path):
        print("❌ Invalid Python file. Please select a non-test, non-migration .py file.")
        return None

    # Run all steps of Module 1
    ast_data = parse_ast(file_path)
    introspection_data = introspect_module(file_path)
    metadata = build_metadata(file_path, ast_data, introspection_data)

    # Save to JSON
    if save_to:
        Path(save_to).parent.mkdir(parents=True, exist_ok=True)
        serializable_metadata = make_json_serializable(metadata)
        with open(save_to, "w", encoding="utf-8") as f:
            json.dump(serializable_metadata, f, indent=2)
        print(f"\n💾 Metadata saved to: {save_to}")

    return metadata


def run_module2_on_metadata(metadata, output_file):
    updated_metadata = metadata.copy()

    # Access functions and classes inside ast_data
    functions = metadata.get("ast_data", {}).get("functions", [])
    print(f"Functions is a {type(functions)}")
    print(functions)

    for func_data in functions:
        func_name = func_data.get("name", "unknown_function")
        print(f"  ✍️ Generating docstring for function: {func_name}")
        try:
            new_docstring = generate_function_doc(func_name, func_data)
            func_data["docstring"] = new_docstring
        except Exception as e:
            print(f"  ❌ Failed to generate docstring for {func_name}: {e}")

    classes = metadata.get("ast_data", {}).get("classes", [])
    print(f"Classes is a {type(classes)}")
    print(classes)

    for class_data in classes:
        class_name = class_data.get("name", "unknown_class")
        print(f"  ✍️ Generating docstring for class: {class_name}")
        try:
            new_docstring = generate_class_doc(class_name, class_data)
            class_data["docstring"] = new_docstring
        except Exception as e:
            print(f"  ❌ Failed to generate docstring for class {class_name}: {e}")

        methods = class_data.get("methods", [])
        print(f"    methods is a {type(methods)}")
        print(methods)

        if isinstance(methods, list):
            for method_data in methods:
                method_name = method_data.get("name", "unknown_method")
                print(f"    ✍️ Generating docstring for method: {method_name}")
                try:
                    new_docstring = generate_function_doc(method_name, method_data)
                    method_data["docstring"] = new_docstring
                except Exception as e:
                    print(f"    ❌ Failed to generate docstring for method {method_name}: {e}")
        else:
            print(f"    ⚠️ Unexpected format for methods in class '{class_name}': {type(methods)}")

    # Ensure output folder exists
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save to file
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            safe_metadata = sanitize_for_json(updated_metadata)
            json.dump(safe_metadata, f, indent=4)

        print(f"✅ Enriched metadata saved to: {output_path}")
        print(f"📄 File exists: {output_path.exists()}, Size: {output_path.stat().st_size} bytes")
    except Exception as e:
        print(f"❌ Error saving enriched metadata: {e}")

def sanitize_for_json(obj):
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]
    elif isinstance(obj, type):
        return str(obj)
    else:
        return obj

if __name__ == "__main__":
    print("📂 Please select a Python file to process...")
    file_path = select_python_file()

    if file_path:
        print(f"\n📂 Selected: {file_path}")
        output_metadata_file = os.path.join("output", f"{Path(file_path).stem}_metadata.json")

        # Run Module 1 to extract metadata
        metadata = run_module1_on_file(file_path, output_metadata_file)

        if metadata:
            # Run Module 2 to generate docstrings & README
            enriched_metadata_file = os.path.join("output", f"{Path(file_path).stem}_metadata_enriched.json")
            run_module2_on_metadata(metadata, enriched_metadata_file)
        else:
            print("❌ Module 1 failed. Skipping Module 2.")
    else:
        print("❌ No file selected.")
