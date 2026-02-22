# Programmatic Affiliate Site Builder

Static generator for affiliate sites (Cloudflare Pages ready).

## Target workflow (one site at a time)

1. Keep only one config file: `site_configs/site-1.json`.
2. Run generator with that config.
3. Upload generated output folder to Git/Cloudflare Pages.
4. For next site, edit values in the same config file and regenerate.

## 1-click run (single site)

`generate_programmatic_pages.bat`

- Uses `site_configs/site-1.json`.
- If config is missing, template config is auto-created.

## Config-driven run (recommended)

```bat
python programmatic_html_generator.py --config-file site_configs/site-1.json
```

## Create/Reset config template

```bat
python programmatic_html_generator.py --write-config-template site_configs/site-1.json
```

## Config fields

Required practical fields:

- `input`: source CSV path
- `output`: generated folder (use unique folder per site)
- `site_name`
- `site_url`
- `tag` (Amazon associate tag)
- `author_name`
- `author_role`
- `author_bio`
- `contact_email`
- `page_copy`: editable page text/content map (home/about/contact/privacy/terms/etc) inside the same config

Scale/SEO fields:

- `top_n`
- `home_cards_limit`
- `guides_page_size`
- `related_links_count`
- `sitemap_chunk_size`

Keyword targeting:

- `keywords` can be:
  - empty list (`[]`) => generate all keywords from CSV
  - comma-separated string
  - JSON list, for example:
    `["best planner for adhd", "portable freezer for camping"]`

## Editable page copy

Edit `page_copy` object in the same config file (`site_configs/site-1.json`).

You can edit keys such as:

- `home_hero_title`
- `home_hero_intro`
- `contact_html`
- `privacy_html`
- `terms_html`

Supported placeholders inside content text:

- `{{site_name}}`
- `{{site_url}}`
- `{{contact_email}}`
- `{{author_name}}`
- `{{author_role}}`
- `{{author_bio}}`
- `{{year}}`

## What gets generated

- Article pages (`*.html`)
- `index.html`
- `all-guides.html` (+ paginated `all-guides-N.html` when needed)
- `about.html`
- `contact.html` (email-only contact, no form)
- `affiliate-disclosure.html`
- `editorial-policy.html`
- `privacy-policy.html`
- `terms-of-use.html`
- `assets/site.css`
- `sitemap.xml` (+ split sitemap files for large sites)
- `robots.txt`
- `_headers`
- `_redirects`
- `generation_report.json`

## SEO and trust features included

- Site-wide header/footer/disclosure/author box
- Disclosure before article body
- Related guides (keyword relevance based)
- Article + FAQ + Breadcrumb schema
- Canonical + Open Graph + Twitter meta
- Slug collision protection
- Sitemap auto-splitting for large sites
- Cloudflare `_headers` and `_redirects`

## Cloudflare Pages deployment (local generate -> upload)

### Option A: Git-based deployment

1. Generate locally:
   `python programmatic_html_generator.py --config-file site_configs/site-1.json`
2. Push the generated `output` folder content to your repo.
3. Create Cloudflare Pages project from that repo.
4. Set build:
   - Build command: empty
   - Output directory: your config `output` folder name
5. Deploy.

### Option B: Direct upload

1. Generate locally.
2. Upload generated output folder files to Cloudflare Pages (direct upload workflow).

## Important launch step

After your final live domain is ready, update `site_url` in config and regenerate once.
This ensures correct canonical URLs and sitemap links.
