import inspect
import importlib.util
import os


def safe_annotation(ann):
    try:
        return str(ann.__name__)  # Handles <class 'int'> -> "int"
    except AttributeError:
        return str(ann)  # Fallback for things like Union[str, int]
    

def introspect_module(file_path: str) -> dict:
    module_name = os.path.splitext(os.path.basename(file_path))[0]
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if not spec or not spec.loader:
        return {}
    
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        return {"error": str(e)}

    data = {"file": file_path, "functions": {}, "classes": {}}

    for name, obj in inspect.getmembers(module):
        if inspect.isfunction(obj) and obj.__module__ == module.__name__:
            data["functions"][name] = {
                "signature": str(inspect.signature(obj)),
                "docstring": inspect.getdoc(obj),
                "annotations": obj.__annotations__
            }
        elif inspect.isclass(obj) and obj.__module__ == module.__name__:
            data["classes"][name] = {
                "docstring": inspect.getdoc(obj),
                "methods": {}
            }
            for m_name, m_obj in inspect.getmembers(obj):
                if inspect.isfunction(m_obj):
                    data["classes"][name]["methods"][m_name] = {
                        "signature": str(inspect.signature(m_obj)),
                        "docstring": inspect.getdoc(m_obj),
                        "annotations": m_obj.__annotations__
                    }

    return data
