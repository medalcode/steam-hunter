from backend.app.parser import parse_steam_keys
import re
text = "Here is a key: 1234?-ABCDE-FGHIJ (? = X) and another one QWERT-YUIOP-ASDFG-HJKL?-ZXCVB ? is 9."
upper_text = text.upper()
match = re.search(r'\?\s*(?:=|-|IS|:|->)\s*([A-Z0-9])', upper_text)
print("Match is:", match.group(1) if match else "None")
print(parse_steam_keys(text))
