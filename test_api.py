from deep_translator import GoogleTranslator, MyMemoryTranslator

tests = {
    "Google": lambda: GoogleTranslator(source="en", target="fr").translate("Hello"),
    "MyMemory": lambda: MyMemoryTranslator(source="en-GB", target="fr-FR").translate("Hello"),
}

for name, run in tests.items():
    try:
        print(name, "OK ->", run())
    except Exception as e:
        print(name, "FAILED ->", type(e).__name__, str(e)[:150])