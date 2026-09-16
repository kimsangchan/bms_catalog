import urllib.request, re, ssl, urllib.parse

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

queries = [
    '\"LG Multi V 5\" Data Book filetype:pdf',
    'LG Multi V Engineering Data Book filetype:pdf',
    '\"LG Multi V\" \"Data Book\" filetype:pdf',
]

for q in queries:
    print(f"Searching: {q}")
    url = 'https://lite.duckduckgo.com/lite/'
    data = urllib.parse.urlencode({'q': q}).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        html = urllib.request.urlopen(req, context=ctx).read().decode('utf-8')
        links = re.findall(r'href=[\"\']?(https?://[^\s\"\'\>]+?\.pdf)[\"\']?', html)
        if links:
            print("Found links:", links)
            for link in set(links):
                if 'lg.com' in link: continue # Skip official site
                print("Downloading", link)
                try:
                    req2 = urllib.request.Request(link, headers={'User-Agent': 'Mozilla/5.0'})
                    content = urllib.request.urlopen(req2, context=ctx).read()
                    if len(content) > 100000:
                        with open('data/raw/LG_Multi_V_5_Engineering_Data_Book.pdf', 'wb') as f:
                            f.write(content)
                        print("Successfully saved LG PDF!")
                        exit(0)
                except Exception as e2:
                    print("Download failed:", e2)
    except Exception as e:
        print('Error:', e)
