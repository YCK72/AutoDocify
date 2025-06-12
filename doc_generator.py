# doc_generator.py

from prompt_templates import FUNCTION_PROMPT_TEMPLATE, CLASS_PROMPT_TEMPLATE
from llm_wrapper import call_grok_api
from formatter import format_docstring
from logger import log_prompt_and_response

def generate_function_doc(func_name, func_data):
    prompt = FUNCTION_PROMPT_TEMPLATE.format(
        func_name=func_name,
        signature=func_data.get("signature", ""),
        annotations=func_data.get("annotations", {}),
        existing_doc=func_data.get("docstring", "")
    )
    response = call_grok_api(prompt)
    log_prompt_and_response(prompt, response, tag=f"func_{func_name}")
    return format_docstring(response)

def generate_class_doc(name, class_data):
    method_summaries = "\n".join(
        "- {}: {}".format(method["name"], method.get("docstring", "")) for method in class_data.get("methods", [])
    )
    prompt = f"""Generate a Python docstring for this class:
Class Name: {name}
Current Docstring: {class_data.get('docstring', '')}
Methods:\n{method_summaries}
"""
    return call_grok_api(prompt)


def generate_readme(metadata):
    from prompt_templates import README_PROMPT_TEMPLATE
    prompt = README_PROMPT_TEMPLATE.format(
        classes=metadata["ast_data"]["classes"],
        functions=metadata["ast_data"]["functions"],
        imports=metadata["ast_data"]["imports"]
    )
    response = call_grok_api(prompt)
    log_prompt_and_response(prompt, response, tag="readme")
    return response
