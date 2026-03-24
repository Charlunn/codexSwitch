import sys

def replace_in_file(filename, search_text, replace_text):
    with open(filename, 'r') as f:
        content = f.read()
    if search_text not in content:
        print('Search text not found')
        return False
    new_content = content.replace(search_text, replace_text)
    with open(filename, 'w') as f:
        f.write(new_content)
    return True

search_text = '''const puppeteer = require("puppeteer");'''

replace_text = '''const puppeteer = require("puppeteer-extra");
const StealthPlugin = require("puppeteer-extra-plugin-stealth");
puppeteer.use(StealthPlugin());'''

if replace_in_file('server.js', search_text, replace_text):
    print('Successfully replaced import')
else:
    print('Failed to replace import')
