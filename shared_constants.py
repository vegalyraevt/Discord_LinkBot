"""
shared_constants.py - Shared threat intelligence data used across safety modules.

Single source of truth for:
  - URL shortener domains
  - Suspicious TLDs
  - Brand impersonation keywords
  - Dangerous file extensions
  - Executable file extensions
  - File extensions to inspect

Imported by: safety/__init__.py, safety/scorecard.py
"""

# Known URL shortener domains
SHORTENER_DOMAINS = {
    'bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'ow.ly', 'is.gd', 'buff.ly',
    'j.mp', 'cutt.ly', 'rb.gy', 'shrtco.de', 'v.gd', 'bl.ink', 't2m.io',
    'qr.ae', 'snip.ly', 'clk.im', 'rebrand.ly', 'short.gy', 'cutt.us',
    'soo.gd', 's.id', 'adf.ly', 'lnkd.in', 'amzn.to', 'wp.me',
    't.me', 'b.link', 'tiny.cc', 'shorturl.at', 'cli.re',
    'short.link', 'gg.gg', 'kutt.it', 'han.gl', 'zws.im', 'rotf.lol', 'tilt.fyi',
    't.ly', 'tinu.be', 'py.md', 'dub.co', 'goo.su', 'qrco.de', 'linktr.ee', 'short.io',
    'tiny.one', 'clck.ru', 'zpr.io', 'gns.io', 'x.co', 'ity.im',
    'q.gs', 'po.st', 'bc.vc', 'u.to', 'su.pr', 'cur.lv', 'dft.ba', 'aka.ms',
    't.cn', 'vk.cc', 'ouo.io', 'za.gl', 'shrinke.me', 'clicks.su',
    'trib.al', 'wa.link', 'vzturl.com', 'tr.im', 'url.ie',
    'tiny.pl', 'cutt.it', 'sh.st', 'cpmlink.net', 'fas.li', 'al.ly',
    'qr.net', '1url.com', 'om.ly', 'bit.do', 'shorte.st', 'adpop.me',
    'fc.lc', 'exe.io', 'db.tt',
    'youtu.be', 'fb.me', 'ift.tt', 'dlvr.it', 'owl.li', 'hubs.ly',
    'pages.link', 'sub2unlock.com',
    'linkvertise.com', 'direct-link.net', 'shr.ink', 'ouo.press',
    'ppt.cc', 'short.pe', 'n9.cl', 'osdb.link', '1pt.co',
}

# Brand keywords for impersonation detection (in subdomain)
BRAND_KEYWORDS = {
    'paypal', 'amazon', 'google', 'microsoft', 'apple', 'netflix',
    'steam', 'discord', 'facebook', 'instagram', 'twitter', 'tiktok',
    'bank', 'secure', 'login', 'verify', 'update', 'account',
    'support', 'help', 'admin', 'billing', 'service', 'security',
}

# Suspicious TLDs (excluding .ru and .io - too broad with legitimate use)
SUSPICIOUS_TLDS = {
    '.tk', '.ml', '.ga', '.cf', '.gq',
    '.xyz', '.top', '.click', '.work',
    '.bar', '.rest', '.hair', '.makeup',
    '.cyou', '.cfd', '.sbs', '.icu',
    '.bond', '.cam', '.shop', '.store', '.vip', '.online', '.site', '.biz',
    '.zip', '.mov', '.cc', '.cn', '.vu', '.su',
    '.live', '.monster', '.quest', '.stream', '.download',
    '.racing', '.win', '.loan', '.men', '.bid', '.date',
    '.trade', '.party', '.science', '.review', '.country',
    '.pro', '.email', '.gdn', '.ws',
    '.pw', '.buzz', '.fun', '.uno', '.lol',
    '.world', '.space', '.digital', '.network', '.solutions',
    '.casa', '.life', '.mobi', '.club', '.info',
    '.la', '.am', '.to',
}

# Direct file extensions to inspect
FILE_EXTENSIONS = (
    '.zip', '.rar', '.7z', '.tar', '.gz', '.tgz', '.bz2', '.xz', '.iso', '.dmg', '.cab',
    '.img', '.vhd', '.vhdx', '.wim',
    '.exe', '.msi', '.apk', '.app', '.bat', '.cmd', '.sh', '.vbs', '.ps1', '.scr', '.jar', '.pif',
    '.com', '.cpl', '.wsf', '.hta', '.jse', '.vbe', '.psm1', '.psd1',
    '.lnk', '.url', '.scf', '.iqy',
    '.mp4', '.mkv', '.avi', '.mov', '.webm', '.mp3', '.wav', '.flac', '.ogg',
    '.pdf', '.doc', '.docx', '.docm', '.xls', '.xlsx', '.xlsm', '.ppt', '.pptx', '.pptm',
    '.rtf', '.chm', '.js', '.msp', '.appx', '.pkg', '.deb', '.rpm', '.py', '.pyw', '.rb', '.pl',
    '.arj', '.lzh', '.lha', '.ace', '.uue', '.xxe', '.z', '.cpio',
    '.reg', '.inf', '.msc', '.msh', '.msh1', '.msh2', '.mshxml', '.msh1xml', '.msh2xml',
    '.gadget', '.application', '.xbap', '.osd',
    '.xlsb', '.xla', '.xlam', '.wll', '.ppam', '.sldm',
    '.jnlp', '.command', '.workflow', '.action', '.terminal', '.tool',
    '.air', '.crx', '.xpi', '.user.js',
    '.pub', '.wps', '.odt', '.ods', '.odp', '.oxps', '.xps', '.epub', '.azw', '.mobi',
)

# Executable / dangerous file extensions
DANGEROUS_EXTENSIONS = {
    '.exe', '.msi', '.apk', '.bat', '.cmd', '.sh', '.vbs', '.ps1', '.scr', '.pif',
    '.com', '.cpl', '.wsf', '.hta', '.jse', '.vbe', '.psm1', '.psd1',
    '.lnk', '.url', '.scf', '.iqy',
    '.iso', '.img', '.vhd', '.vhdx',
    '.rtf', '.chm', '.js', '.msp', '.appx', '.py', '.pyw', '.rb', '.pl',
    '.reg', '.inf', '.msc', '.gadget', '.application', '.xbap', '.jnlp',
    '.command', '.workflow', '.action', '.terminal', '.tool',
    '.air', '.crx', '.xpi',
}
