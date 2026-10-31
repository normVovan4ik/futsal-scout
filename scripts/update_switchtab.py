path = r"C:\Users\ersov\.gemini\antigravity\scratch\futsal-scout\app.js"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

old_tab = """function switchTab(tabId) {
  document.querySelectorAll(".tab-content").forEach(el => el.classList.add("hidden"));"""

new_tab = """function switchTab(tabId) {
  document.querySelectorAll(".tab-content").forEach(el => {
    el.classList.add("hidden");
    el.classList.remove("block");
  });"""

if old_tab in text:
    text = text.replace(old_tab, new_tab)
    print("Replaced LF!")
else:
    old_crlf = old_tab.replace("\n", "\r\n")
    new_crlf = new_tab.replace("\n", "\r\n")
    if old_crlf in text:
        text = text.replace(old_crlf, new_crlf)
        print("Replaced CRLF!")
    else:
        print("Not found directly, using regex...")
        import re
        text = re.sub(r'function switchTab\(tabId\)\s*\{\s*document\.querySelectorAll\("\.tab-content"\)\.forEach\([^)]+\);', new_tab, text)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("Updated switchTab!")
