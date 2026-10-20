from models.router import ModelRouter


router = ModelRouter()


print("\n========================================")
print("        JARVIS MODEL ROUTER TEST")
print("========================================")


prompt = "Who are you? Reply in one short sentence."


response = router.ask(prompt)


print("\n========================================")
print("JARVIS:")
print(response)
print("========================================")