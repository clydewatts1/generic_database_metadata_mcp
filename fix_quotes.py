text = open("src/utils/logging.py", "r", encoding="utf-8").read()
triple = chr(34)*3
bad = chr(96)+chr(34)+chr(96)+chr(34)+chr(96)+chr(34)
text = text.replace(bad, triple)
open("src/utils/logging.py", "w", encoding="utf-8").write(text)
