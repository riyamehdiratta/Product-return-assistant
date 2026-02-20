from scaledown.pipeline import Pipeline

question = "How many Ballon D'Or awards does Messi have?"

context = """
Messi has won seven Ballon d'Or awards.
"""

pipeline = Pipeline()
compressed = pipeline.run(
    context=context,
    question=question
)

print(compressed)
