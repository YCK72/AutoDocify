def make_json_serializable(obj):
    """
    Recursively convert unserializable types (like `<class 'int'>`, functions, tuples) into serializable strings.
    """
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(v) for v in obj]
    elif isinstance(obj, tuple):
        # Convert tuples to lists for JSON compatibility (JSON doesn't have tuples)
        return [make_json_serializable(v) for v in obj]
    elif isinstance(obj, type):  # e.g. <class 'int'>
        return obj.__name__
    elif callable(obj):
        # For functions, methods, lambdas, etc.
        return getattr(obj, "__name__", repr(obj))
    else:
        # Try string conversion safely
        try:
            return str(obj)
        except Exception:
            return repr(obj)
