path = r"C:\Users\ersov\.gemini\antigravity\scratch\futsal-scout\app.js"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# Replace the exact bad snippet
bad_snippet = """  // Небольшой фидбэк пользователю
  const btn = document.querySelector(".tab-btn");
  confetti({ particleCount: 40, spread: 50, origin: { y: 0.7 } });
}"""

if bad_snippet in text:
    text = text.replace(bad_snippet, "")
    print("Found and removed bad snippet!")
else:
    # Try with CRLF
    bad_snippet_crlf = bad_snippet.replace("\n", "\r\n")
    if bad_snippet_crlf in text:
        text = text.replace(bad_snippet_crlf, "")
        print("Found and removed bad snippet (CRLF)!")
    else:
        print("Snippet not found directly, looking closely...")
        import re
        text = re.sub(r'\s*// Небольшой фидбэк пользователю\s*const btn[^\}]+confetti[^\}]+;\s*\}', '', text)
        print("Regex replaced!")

with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("File updated!")
