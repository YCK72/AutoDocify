from llm_wrapper import query_mixtral

sample_prompt = "Generate a docstring for the following Python function:\n\n```python\ndef add(a: int, b: int) -> int:\n    return a + b\n```"

result = query_mixtral(sample_prompt)
print(result)
