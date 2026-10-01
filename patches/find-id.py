import re, sys

path = sys.argv[1] if len(sys.argv) > 1 else 'res/values/public.xml'
xml = open(path).read()
pairs = re.findall(r'id="0x7f([0-9a-fA-F]{2})([0-9a-fA-F]{4})"', xml)
used = {(t.lower(), e.lower()) for t, e in pairs}

m = re.search(r'<public type="drawable" name="[^"]+" id="0x7f([0-9a-fA-F]{2})', xml)
if not m:
    sys.exit('no drawable entries found in ' + path)

tdraw = m.group(1).lower()
print(f'drawable type byte in this APK: 0x7f{tdraw}')
entries = {int(e, 16) for t, e in used if t == tdraw}
entry = max(entries) + 1
while f'{entry:04x}' in {e for t, e in used if t == tdraw}:
    entry += 1

rid = f'0x7f{tdraw}{entry:04x}'
assert (tdraw, f'{entry:04x}') not in used, 'collision'
print(f'free drawable ID: {rid}')
print(f'<public type="drawable" name="ic_launcher_monochrome" id="{rid}" />')
