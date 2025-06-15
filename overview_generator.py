from llm_wrapper import call_grok_api
from formatter import format_docstring

def generate_code_overview(source_code: str) -> str:
    prompt = (
        "You're a professional Python code reviewer.\n"
        "Explain briefly what this code does, its purpose, and any key components.\n\n"
        f"{source_code[:3000]}"  # truncate for token safety
    )
    response = call_grok_api(prompt)
    return format_docstring(response)
