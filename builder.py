from pathlib import Path

def safe_type_to_str(t):
    try:
        return t.__name__ if hasattr(t, "__name__") else str(t)
    except Exception:
        return str(t)

def sanitize_function_data(func):
    """
    Convert any type annotations or type objects in function metadata to strings.
    Adjust this based on the actual keys your func dict uses.
    """
    func = func.copy()  # shallow copy to avoid mutation

    # Example keys to sanitize — adjust if different
    if "returns" in func:
        func["returns"] = safe_type_to_str(func["returns"])
    
    # If your args are stored as list of dicts with types, sanitize those
    if "args" in func and isinstance(func["args"], list):
        # If args is a list of strings (arg names), leave as is
        # But if args hold more complex info like dicts, you can sanitize here
        # Example: args = [{"name": "x", "type": int}]
        sanitized_args = []
        for arg in func["args"]:
            if isinstance(arg, dict) and "type" in arg:
                arg = arg.copy()
                arg["type"] = safe_type_to_str(arg["type"])
            sanitized_args.append(arg)
        func["args"] = sanitized_args
    
    return func


def sanitize_class_data(cls):
    """
    Sanitize class metadata including methods.
    """
    cls = cls.copy()
    methods = cls.get("methods", [])
    sanitized_methods = []

    if isinstance(methods, list):
        for method in methods:
            sanitized_methods.append(sanitize_function_data(method))
    elif isinstance(methods, dict):
        # If methods stored as dict of method_name -> method_data
        for method_name, method_data in methods.items():
            sanitized_methods.append(sanitize_function_data(method_data))
    else:
        # unknown format, leave as is
        sanitized_methods = methods

    cls["methods"] = sanitized_methods
    return cls


def build_metadata(file_path, ast_data, introspection_data):
    """
    Combines AST data and runtime introspection data into unified metadata.
    Assumes functions and classes are lists of dicts.
    Also sanitizes types to strings.
    """
    metadata = {
        "file_path": file_path,
        "ast_data": {
            "functions": [],
            "classes": []
        },
        "introspection": introspection_data
    }

    # --- Merge and sanitize Functions ---
    ast_functions = ast_data.get("functions", [])
    for func in ast_functions:
        sanitized_func = sanitize_function_data(func)
        metadata["ast_data"]["functions"].append(sanitized_func)

    # --- Merge and sanitize Classes ---
    ast_classes = ast_data.get("classes", [])
    for cls in ast_classes:
        class_name = cls.get("name", "UnknownClass")
        methods = cls.get("methods", [])
        class_info = {k: v for k, v in cls.items() if k != "methods"}
        class_info["name"] = class_name
        class_info["methods"] = []

        for method in methods:
            sanitized_method = sanitize_function_data(method)
            class_info["methods"].append(sanitized_method)

        sanitized_class = sanitize_class_data(class_info)
        metadata["ast_data"]["classes"].append(sanitized_class)

    return metadata
