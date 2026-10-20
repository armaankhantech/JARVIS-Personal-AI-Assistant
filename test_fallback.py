from models.router import ModelRouter


router = ModelRouter()


# -----------------------------------------
# Simulate Groq failure
# -----------------------------------------

def fake_groq_failure(prompt):
    raise Exception("SIMULATED GROQ FAILURE")


router.ask_groq = fake_groq_failure


# -----------------------------------------
# Ask Jarvis something
# -----------------------------------------

print("\n========================================")
print("       JARVIS FALLBACK TEST")
print("========================================")

response = router.ask(
    "Reply with exactly: FALLBACK WORKED"
)


print("\n========================================")
print("JARVIS:")
print(response)
print("========================================")