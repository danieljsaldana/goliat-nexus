"""Render crawlable sharing metadata from the public project profile."""
import argparse
import html
import json
import os
import re
from pathlib import Path
from urllib.parse import urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[1]
START, END = '<!-- project:metadata -->', '<!-- /project:metadata -->'


def project_profile():
    profile = json.loads((ROOT / 'site/content/project.json').read_text())
    profile['version'] = (ROOT / 'VERSION').read_text().strip()
    return profile


def render_head(profile, *, site_url=None):
    base = site_url or os.environ.get('GOLIAT_SITE_URL') or profile['website']
    parsed = urlsplit(base)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('GOLIAT_SITE_URL must be an absolute HTTPS URL without credentials, query or fragment.')
    base = base.rstrip('/') + '/'
    image = urljoin(base, profile['social_image'])
    title = profile['name'] + ' · Plataforma modular para Azure'
    escape = lambda value: html.escape(str(value), quote=True)
    tags = [START, '<title>' + escape(title) + '</title>']
    fields = [('name', 'description', profile['description']), ('name', 'author', profile['author']['name']),
        ('name', 'theme-color', '#0078d4'), ('property', 'og:type', 'website'),
        ('property', 'og:site_name', profile['name']), ('property', 'og:title', title),
        ('property', 'og:description', profile['description']), ('property', 'og:url', base),
        ('property', 'og:locale', profile['locale']), ('property', 'og:image', image),
        ('property', 'og:image:secure_url', image), ('property', 'og:image:type', 'image/png'),
        ('property', 'og:image:width', '1200'), ('property', 'og:image:height', '630'),
        ('property', 'og:image:alt', profile['social_image_alt']), ('name', 'twitter:card', 'summary_large_image'),
        ('name', 'twitter:title', title), ('name', 'twitter:description', profile['description']),
        ('name', 'twitter:image', image), ('name', 'twitter:image:alt', profile['social_image_alt'])]
    tags += [f'<meta {kind}="{key}" content="{escape(value)}">' for kind, key, value in fields]
    tags += [f'<link rel="canonical" href="{escape(base)}">', f'<link rel="author" href="{escape(profile["author"]["url"])}">',
        '<link rel="icon" href="assets/favicon.svg" type="image/svg+xml">',
        '<link rel="icon" href="assets/favicon-32.png" type="image/png" sizes="32x32">',
        '<link rel="apple-touch-icon" href="assets/apple-touch-icon.png" sizes="180x180">']
    data = {'@context': 'https://schema.org', '@type': 'SoftwareSourceCode', 'name': profile['name'],
        'description': profile['description'], 'codeRepository': profile['repository'], 'url': base,
        'image': image, 'version': profile['version'], 'programmingLanguage': ['HCL', 'Python', 'JavaScript'],
        'author': {'@type': 'Person', **profile['author']},
        'license': profile['repository'] + '/blob/main/LICENSE'}
    tags += ['<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False).replace('<', '\\u003c') + '</script>', END]
    return '\n'.join(tags)


def update_document(document, profile, *, site_url=None):
    block = render_head(profile, site_url=site_url)
    assert START in document and END in document
    document = re.sub(re.escape(START) + r'.*?' + re.escape(END), lambda match: block, document, count=1, flags=re.S)
    return re.sub(r'(<code id="product-version"[^>]*>).*?(</code>)',
                  lambda match: match[1] + 'NEXUS · v' + html.escape(profile['version']) + match[2],
                  document, count=1, flags=re.S)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    path = ROOT / 'site/index.html'
    profile = project_profile()
    rendered = update_document(path.read_text(), profile, site_url=profile['website'])
    if args.check:
        if rendered != path.read_text():
            raise SystemExit('Sharing metadata is stale: run python3 scripts/site_metadata.py.')
    else:
        path.write_text(rendered)


if __name__ == '__main__':
    main()
