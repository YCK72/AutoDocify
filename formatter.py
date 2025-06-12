# formatter.py

def format_docstring(docstring: str) -> str:
    lines = docstring.strip().splitlines()
    if len(lines) == 1:
        return f'"""{lines[0]}"""'
    else:
        return '"""\n' + "\n".join(lines) + '\n"""'

def format_readme(content: str) -> str:
    return content.strip() + "\n"
