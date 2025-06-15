import tkinter as tk
from tkinter import filedialog
from pathlib import Path
import json
import sys
import os

# Ensure current directory is in Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Project module imports
from scanner import scan_python_files
from parser import parse_ast
from introspector import introspect_module
from builder import build_metadata
from utils import make_json_serializable
from formatter import format_docstring
from doc_generator import generate_function_doc, generate_class_doc, generate_readme
from overview_generator import generate_code_overview

def select_python_file():
    """Open a file dialog for the user to choose a Python file."""
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select a Python File",
        filetypes=[("Python Files", "*.py")]
    )
    return file_path

def run_module1_on_file(file_path, save_to=None):
    print(f"\nProcessing: {file_path}")

    if not scan_python_files(file_path):
        print("Invalid Python file. Please select a non-test, non-migration .py file.")
        return None

    ast_data = parse_ast(file_path)
    introspection_data = introspect_module(file_path)
    metadata = build_metadata(file_path, ast_data, introspection_data)

    if not metadata["ast_data"]["functions"] and not metadata["ast_data"]["classes"]:
        print("No functions or classes found. Generating general code overview...")
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
        metadata["code_overview"] = generate_code_overview(code)

    if save_to:
        Path(save_to).parent.mkdir(parents=True, exist_ok=True)
        serializable_metadata = make_json_serializable(metadata)
        with open(save_to, "w", encoding="utf-8") as f:
            json.dump(serializable_metadata, f, indent=2)
        print(f"\nMetadata saved to: {save_to}")

    return metadata

def run_module2_on_metadata(metadata, output_file):
    updated_metadata = metadata.copy()
    functions = updated_metadata.get("ast_data", {}).get("functions", [])
    classes = updated_metadata.get("ast_data", {}).get("classes", [])

    for func_data in functions:
        func_name = func_data.get("name", "unknown_function")
        try:
            new_docstring = generate_function_doc(func_name, func_data)
            func_data["docstring"] = format_docstring(new_docstring)
        except Exception as e:
            print(f"Failed to generate docstring for function {func_name}: {e}")

    for class_data in classes:
        class_name = class_data.get("name", "unknown_class")
        try:
            new_docstring = generate_class_doc(class_name, class_data)
            class_data["docstring"] = format_docstring(new_docstring)
        except Exception as e:
            print(f"Failed to generate docstring for class {class_name}: {e}")

        methods = class_data.get("methods", [])
        for method_data in methods:
            method_name = method_data.get("name", "unknown_method")
            try:
                new_docstring = generate_function_doc(method_name, method_data)
                method_data["docstring"] = format_docstring(new_docstring)
            except Exception as e:
                print(f"Failed to generate docstring for method {method_name}: {e}")

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(updated_metadata, f, indent=4)
        print(f"Enriched metadata saved to: {output_path}")
        print(f"File exists: {output_path.exists()}, Size: {output_path.stat().st_size} bytes")
    except Exception as e:
        print(f"Error saving enriched metadata: {e}")

    try:
        readme_text = generate_readme(updated_metadata)
        readme_path = Path("output/README_generated.md")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_text)
        print(f"README.md generated at: {readme_path}")
    except Exception as e:
        print(f"Failed to generate README.md: {e}")

def main():
    print("Please select a Python file to process...")
    file_path = select_python_file()

    if file_path:
        print(f"\nSelected: {file_path}")
        output_metadata_file = os.path.join("output", f"{Path(file_path).stem}_metadata.json")

        metadata = run_module1_on_file(file_path, output_metadata_file)

        if metadata:
            enriched_metadata_file = os.path.join("output", f"{Path(file_path).stem}_metadata_enriched.json")
            run_module2_on_metadata(metadata, enriched_metadata_file)
        else:
            print("Module 1 failed. Skipping Module 2.")
    else:
        print("No file selected.")

if __name__ == "__main__":
    main()
