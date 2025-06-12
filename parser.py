import ast

def parse_ast(file_path: str) -> dict:
    with open(file_path, 'r', encoding='utf-8') as f:
        source = f.read()
    
    tree = ast.parse(source, filename=file_path)

    result = {
        "file": file_path,
        "classes": [],
        "functions": [],
        "imports": []
    }

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                result["imports"].append(n.name)

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for n in node.names:
                result["imports"].append(f"{module}.{n.name}")

        elif isinstance(node, ast.FunctionDef):
            func_info = {
                "name": node.name,
                "args": [arg.arg for arg in node.args.args],
                "returns": ast.unparse(node.returns) if node.returns else None,
                "docstring": ast.get_docstring(node)
            }
            result["functions"].append(func_info)
            print(f"Found function: {func_info['name']}")

        elif isinstance(node, ast.ClassDef):
            class_info = {
                "name": node.name,
                "docstring": ast.get_docstring(node),
                "methods": []
            }

            for body_item in node.body:
                if isinstance(body_item, ast.FunctionDef):
                    method_info = {
                        "name": body_item.name,
                        "args": [arg.arg for arg in body_item.args.args],
                        "returns": ast.unparse(body_item.returns) if body_item.returns else None,
                        "docstring": ast.get_docstring(body_item)
                    }
                    class_info["methods"].append(method_info)
                    print(f"Found method: {method_info['name']} in class {class_info['name']}")

            result["classes"].append(class_info)
            print(f"Found class: {class_info['name']}")

    return result
