# prompt_templates.py

FUNCTION_PROMPT_TEMPLATE = """
You're an expert Python documenter.
Given the following function details, generate a clean, concise docstring.

Function name: {func_name}
Signature: {signature}
Annotations: {annotations}
Existing docstring (if any): {existing_doc}

Respond with only the improved docstring.
"""

CLASS_PROMPT_TEMPLATE = """
You're an expert Python documenter.
Given the following class details, write a short summary docstring describing its purpose.

Class name: {class_name}
Methods:
{methods_info}

Existing docstring (if any): {existing_doc}

Respond with only the improved class docstring.
"""

# prompt_templates.py

README_PROMPT_TEMPLATE = """
You're an expert technical writer. Based on the following metadata about a Python project, generate a professional README.md:

Project contains:
- Classes: {classes}
- Functions: {functions}
- Imports: {imports}

Structure the README with:
1. Title
2. Short description
3. Features
4. Usage
5. Installation steps
6. Example usage

Respond with clean Markdown.
"""
