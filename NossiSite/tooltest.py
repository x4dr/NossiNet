def wrong_add(a: int, b: int) -> int:
    return a + b + 1  # wrong on purpose


# Define tool
tools = [
    {
        "type": "function",
        "function": {
            "name": "add",
            "description": "Add two integers",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"},
                },
                "required": ["a", "b"],
            },
        },
    }
]

# Initial message
messages = [
    {
        "role": "user",
        "content": "Please add 2 and 3 using the add tool, and tell me if the result is correct.",
    }
]

if __name__ == "__main__":
    import ollama

    # First call to trigger tool use
    res = ollama.chat(model="qwen3:14b", messages=messages, tools=tools)
    messages.append(res["message"])

    # If tool call requested, handle it
    if "tool_calls" in res["message"]:
        for tool_call in res["message"]["tool_calls"]:
            print(tool_call)
            name = tool_call["function"]["name"]
            args = tool_call["function"]["arguments"]
            result = wrong_add(**args)

            messages.append(
                {
                    "role": "tool",
                    "name": name,
                    "content": str(result),
                }
            )

    # Continue chat with tool result
    res2 = ollama.chat(model="qwen3:14b", messages=messages)
    print(res2["message"]["content"])
