from google import genai

client = genai.Client()

response = client.models.generate_content(
    model="gemma-4-26b-a4b-it",
    contents="Hello Gemma! Reply with one short sentence."
)

print(response.text)
