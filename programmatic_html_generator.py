from __future__ import annotations

import argparse
import csv
import html
import json
import random
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

YEAR = datetime.now().year
FEATURE_IMAGE_WIDTH = 1200
FEATURE_IMAGE_HEIGHT = 675


RESPONSIVE_ASSETS = ""


@dataclass
class Product:
    keyword: str
    product_name: str
    product_url: str
    image_url: str
    rating: float
    review_count: int
    rank_for_keyword: int
    final_score: float


@dataclass
class SiteConfig:
    site_name: str
    site_url: str
    author_name: str
    author_role: str
    author_bio: str
    contact_email: str
    home_cards_limit: int
    guides_page_size: int
    related_links_count: int
    sitemap_chunk_size: int
    indexnow_key: str
    indexnow_key_location: str
    indexnow_endpoint: str
    indexnow_submit: bool
    indexnow_batch_size: int


@dataclass
class ArticleBuild:
    keyword: str
    slug: str
    products: List[Product]
    feature_primary_image: str = ""
    feature_images: List[str] = field(default_factory=list)
    feature_layout: str = "layout-a"
    feature_overlay: str = "overlay-a"
    feature_font: str = "font-a"
    feature_text: str = ""


DEFAULT_PAGE_COPY: Dict[str, str] = {
    "home_hero_kicker": "Programmatic Affiliate Hub",
    "home_hero_title": "{{site_name}}",
    "home_hero_intro": (
        "Find structured comparisons with disclosure, author info, and buying guidance. "
        "Use search to quickly filter guides."
    ),
    "home_search_placeholder": "Search a keyword (e.g. planner, solar lights...)",
    "home_latest_guides_title": "Latest Buying Guides",
    "home_important_pages_title": "Important Pages",
    "home_hidden_note_template": "{{hidden_count}} additional pages are available. <a href='all-guides.html'>Browse all guides</a>.",
    "guides_index_title": "All Buying Guides",
    "guides_index_intro": "Browse all generated guides. This index is paginated for crawl efficiency and better internal linking.",
    "guides_card_cta_text": "Open guide",
    "about_html": (
        "<h1>About {{site_name}}</h1>"
        "<p>This website publishes large-scale product comparison guides using structured data and repeatable editorial templates. "
        "Our goal is to help readers shortlist products faster without depending only on marketing claims.</p>"
        "<h2>How We Build Content</h2>"
        "<p>Each guide is generated from product-level inputs such as ratings, review counts, and ranking position. "
        "Then we apply a consistent layout that includes affiliate disclosure, buying guidance, FAQ, and author details.</p>"
        "<p>We use a repeatable framework so the same evaluation logic can be applied across thousands of pages. "
        "This keeps structure, legal disclosures, and user experience consistent as the site scales.</p>"
        "<h2>Editorial Intent</h2>"
        "<p>We aim to present practical comparisons, common buying mistakes, and shortlist-focused recommendations. "
        "Content may be regenerated as source data changes, templates improve, or policy sections are updated.</p>"
        "<h2>Corrections and Updates</h2>"
        "<p>If you find factual errors, outdated details, or technical issues, contact us by email at "
        "<a href='mailto:{{contact_email}}'>{{contact_email}}</a>.</p>"
    ),
    "contact_html": (
        "<h1>Contact Us</h1>"
        "<p>For corrections, partnership inquiries, copyright concerns, and general questions, please contact us via email.</p>"
        "<div class='contact-email-box'><strong>Email:</strong> <a href='mailto:{{contact_email}}'>{{contact_email}}</a></div>"
        "<p>When contacting us, include the page URL and a short explanation so we can review your request faster.</p>"
        "<p>We do not currently use a web form on this website. Email is the official contact channel.</p>"
    ),
    "disclosure_html": (
        "<h1>Affiliate Disclosure</h1>"
        "<p>This website participates in affiliate advertising programs, including Amazon Associates and similar partner networks.</p>"
        "<p>When visitors click affiliate links and make qualifying purchases, we may earn a commission at no additional cost to the buyer.</p>"
        "<p>Affiliate relationships do not change our commitment to transparent disclosures and structured comparison methods.</p>"
        "<p>Product prices, stock availability, ratings, and reviews may change over time. "
        "Always verify current details on the merchant website before making a final purchase decision.</p>"
        "<p>We aim to keep disclosures visible and understandable for readers so affiliate relationships remain clear across all pages.</p>"
    ),
    "editorial_html": (
        "<h1>Editorial Policy</h1>"
        "<h2>Selection Framework</h2>"
        "<p>Guides are assembled from structured input datasets and consistency rules, including rank signals, review confidence, and feature relevance.</p>"
        "<p>Templates are designed to maintain a consistent section order so readers can compare products quickly across different categories.</p>"
        "<h2>Content Updates</h2>"
        "<p>Pages may be regenerated when source data changes or when layout/policy improvements are deployed site-wide.</p>"
        "<p>We may also revise introduction, FAQ, or guidance sections to improve clarity, readability, and compliance standards.</p>"
        "<h2>Independence</h2>"
        "<p>Affiliate commissions do not guarantee product placement. Ranking logic follows predefined data-driven rules.</p>"
        "<p>Editorial and policy updates are applied at the template level to keep site-wide consistency without manual edits on each page.</p>"
    ),
    "privacy_html": (
        "<h1>Privacy Policy</h1>"
        "<p>This site may use analytics, server logs, and affiliate tracking parameters to understand traffic and link performance.</p>"
        "<p>We do not intentionally collect sensitive personal data through article pages.</p>"
        "<p>If you contact us by email, we may retain your message to respond, resolve issues, and keep an internal record of support requests.</p>"
        "<p>Third-party services (such as affiliate networks) may process data under their own privacy policies.</p>"
        "<p>Cookies and tracking technologies may be used by analytics or affiliate partners to measure site performance and referral attribution.</p>"
        "<p>By continuing to use this site, you acknowledge these data-processing practices. "
        "If you have privacy-related questions, contact us by email at <a href='mailto:{{contact_email}}'>{{contact_email}}</a>.</p>"
    ),
    "terms_html": (
        "<h1>Terms of Use</h1>"
        "<p>All content is provided for informational purposes and may change without notice.</p>"
        "<p>We do not guarantee completeness, merchant accuracy, or fitness for any specific purchase decision.</p>"
        "<p>Before buying any product, you should verify product details, shipping, warranty, and return policy on the seller platform.</p>"
        "<p>Unauthorized copying, bulk republishing, or automated scraping of this website content may violate applicable laws.</p>"
        "<p>By using this website, you agree to evaluate products independently and use this information at your own discretion.</p>"
        "<p>These terms may be updated periodically. Continued use of the site indicates acceptance of the latest version.</p>"
    ),
    "article_footer_note": "This page is for informational purposes and does not replace independent product research.",
}


def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", norm(text)).strip("-") or "page"


def parse_int(value: str, default: int = 0) -> int:
    try:
        return int(float(str(value).strip()))
    except Exception:
        return default


def parse_float(value: str, default: float = 0.0) -> float:
    try:
        return float(str(value).strip())
    except Exception:
        return default


def parse_int_like(value: object, default: int) -> int:
    try:
        return int(float(str(value).strip()))
    except Exception:
        return default


def parse_bool_like(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def clean_text_artifacts(text: str) -> str:
    s = html.unescape(str(text or ""))
    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "â€“": "-",
        "â€”": "-",
        "â€˜": "'",
        "â€™": "'",
        "â€œ": '"',
        "â€\u009d": '"',
        "&amp;amp;": "&",
    }
    for old, new in replacements.items():
        s = s.replace(old, new)
    return re.sub(r"\s+", " ", s).strip()


def placeholder_context(config: SiteConfig, extras: Dict[str, str] | None = None) -> Dict[str, str]:
    ctx = {
        "site_name": config.site_name,
        "site_url": config.site_url,
        "author_name": config.author_name,
        "author_role": config.author_role,
        "author_bio": config.author_bio,
        "contact_email": config.contact_email,
        "year": str(datetime.now().year),
    }
    if extras:
        for key, value in extras.items():
            ctx[key] = str(value)
    return ctx


def apply_placeholders(text: str, context: Dict[str, str]) -> str:
    pattern = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")
    return pattern.sub(lambda m: context.get(m.group(1), m.group(0)), str(text))


def load_page_copy(settings: Dict[str, object], base: Path) -> Dict[str, str]:
    merged: Dict[str, str] = dict(DEFAULT_PAGE_COPY)
    loaded_inline = settings.get("page_copy")
    if isinstance(loaded_inline, dict):
        for key, value in loaded_inline.items():
            if isinstance(value, str):
                merged[str(key)] = value
        return merged

    raw_path = first_non_empty(settings.get("page_content_file"), fallback="")
    if raw_path:
        content_path = Path(raw_path)
        if not content_path.is_absolute():
            content_path = base / content_path
        if not content_path.exists():
            print(f"[warn] page content file not found, using defaults: {content_path}")
            return merged
        with content_path.open("r", encoding="utf-8") as f:
            loaded = json.load(f)
        if not isinstance(loaded, dict):
            print(f"[warn] page content file is not a JSON object, using defaults: {content_path}")
            return merged
        for key, value in loaded.items():
            if isinstance(value, str):
                merged[str(key)] = value
        print("[warn] `page_content_file` is legacy. Move content into config key `page_copy`.")
        return merged

    return merged


def clean_keyword(keyword: str) -> str:
    return re.sub(r"(?i)\bbest\s+", "", keyword).strip()


def short_title(title: str) -> str:
    title = re.sub(r"\s+", " ", (title or "").strip())
    for sep in ("|", " - ", ":", ";"):
        if sep in title:
            left = title.split(sep)[0].strip()
            if len(left) >= 3:
                return left
    words = title.split()
    return " ".join(words[:14]) if len(words) > 14 else title


def extract_feature(title: str) -> str:
    parts = re.split(r"[|,:;\\-]", title or "")
    for p in parts:
        s = re.sub(r"\s+", " ", p).strip()
        if len(s) >= 8 and any(ch.isdigit() for ch in s):
            return s
    for p in parts:
        s = re.sub(r"\s+", " ", p).strip()
        if len(s) >= 8:
            return s
    return "Balanced feature set"


def ensure_affiliate_tag(url: str, tag: str) -> str:
    if not tag or not url:
        return url
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if "tag" not in query:
        query["tag"] = tag
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, urlencode(query), parsed.fragment))


def combos(parts_a: Sequence[str], parts_b: Sequence[str], parts_c: Sequence[str], limit: int = 10) -> List[str]:
    out: List[str] = []
    for a in parts_a:
        for b in parts_b:
            for c in parts_c:
                out.append(f"{a} {b} {c}".strip())
                if len(out) >= limit:
                    return out
    return out


TEXT_BANK: Dict[str, List[str]] = {
    "meta_title": [
        "Best {k} ({y}) - Reviews, Comparison and Buying Guide",
        "Top {k} Picks ({y}) - Detailed Comparison and Buyer Tips",
        "Best {k} in {y} - Top Rated Options and Final Recommendations",
        "{y} Guide: Best {k} for Value, Quality and Practical Use",
        "Best {k} ({y}) - Honest Review Breakdown and Smart Buying Advice",
        "Top Rated {k} ({y}) - Features, Pros, Cons and Verdict",
        "Best {k} in {y} - Data Driven Comparison for Better Decisions",
        "Best {k} ({y}) - Complete Review and Buying Framework",
        "Best {k} in {y} - What to Buy, What to Skip, and Why",
        "Best {k} ({y}) - Structured Comparison for Real Buyers",
    ],
    "meta_desc": [
        "Looking for the best {k}? This guide compares top options by ratings, reviews, feature quality, and practical buying value to help you choose confidently.",
        "Need the right {k}? Explore side by side comparisons, in-depth review blocks, and universal buying tips designed for faster and smarter decisions.",
        "Compare high rated {k} options using real product data, buyer feedback signals, and feature relevance so you can shortlist better products quickly.",
        "Shopping for {k}? This page covers top picks, pros and cons, buying mistakes to avoid, and final recommendations based on practical buyer needs.",
        "Find the best {k} with a structured table, detailed product insights, and clear guidance on value, durability, usability, and long term fit.",
        "Use this {k} guide to compare leading options, evaluate tradeoffs, and select the most suitable product based on your priorities and budget.",
        "From overall winners to budget picks, this {k} comparison highlights what matters most before purchase and how to avoid common selection errors.",
        "Choose better {k} products with data-backed comparison logic, generalized buying criteria, and clear recommendations for everyday and advanced usage.",
        "This {k} review guide simplifies decision-making by combining performance signals, buyer trust indicators, and practical feature evaluation in one place.",
        "Discover best-value {k} options through a complete comparison framework that includes ratings, feedback quality, key strengths, limitations, and final verdicts.",
    ],
    "intro_open": [
        "If you are searching for the best {k}, you likely want something reliable, practical, and worth paying for over the long term.",
        "Choosing the best {k} can feel overwhelming because many products look similar at first glance, even when real performance differs.",
        "Finding the right {k} is easier when you compare measurable quality signals instead of relying only on marketing language.",
        "The {k} category is highly competitive, so using a structured evaluation process helps avoid weak or mismatched choices.",
        "Most buyers want the best {k} without overspending, and that usually requires balancing value, usability, and consistency.",
        "A smart {k} purchase starts by separating feature noise from features that actually matter in everyday use.",
        "Many {k} products promise excellent results, but long term satisfaction usually comes from better fit, not louder claims.",
        "When comparing {k}, the safest approach is to focus on product data, buyer confidence, and practical use relevance.",
        "The best {k} is not always the most expensive option; often it is the one with the strongest value-to-performance ratio.",
        "If your goal is fewer regrets after purchase, a clear and data-backed {k} comparison is the best starting point.",
    ],
    "intro_mid": [
        "In this guide, we evaluate products using rating quality, review confidence, feature relevance, and practical value for typical buyers.",
        "The shortlist below is ranked through measurable signals so your final decision is based on consistency and fit, not guesswork.",
        "Each recommendation is selected through structured comparison of buyer trust indicators, usability factors, and value-for-money strength.",
        "This framework prioritizes products that perform reliably in real use scenarios, not only those with attractive listing copy.",
        "We filtered options using repeatable criteria so you can compare products faster while still keeping decision quality high.",
        "Our ranking approach focuses on practical outcomes: dependable performance, useful features, and lower compromise for your budget.",
        "To keep this useful across product types, the evaluation logic emphasizes universal buying principles rather than niche assumptions.",
        "The goal is simple: help you move from a large product list to a clear shortlist that you can trust.",
        "This comparison is designed to reduce decision fatigue by highlighting what truly matters before purchase in most categories.",
        "You will find both quick-scan data and detailed review sections so you can decide at the level of depth you prefer.",
    ],
    "summary_open": [
        "{p} is a strong option if your main priority is {b}, especially when balancing feature quality with practical value.",
        "{p} remains a dependable choice for {b} and is often considered by buyers who want fewer compromises.",
        "{p} looks like a reliable match for {b}, particularly for users who care about consistency over hype.",
        "{p} stands out as a practical pick for {b} with a profile that supports real-world everyday usage.",
        "{p} is worth considering for {b} when you want a product that blends capability, usability, and confidence.",
        "{p} performs well for {b} and fits buyers who prioritize stable outcomes over unnecessary complexity.",
        "{p} is commonly shortlisted for {b} because it provides a balanced mix of trust signals and practical features.",
        "{p} is a competitive recommendation for {b} when your goal is to maximize long-term value from the purchase.",
        "{p} can be a smart fit for {b}, especially if you prefer reliable performance with manageable tradeoffs.",
        "{p} is a credible choice for {b} and works well for buyers who need a dependable all-around profile.",
    ],
    "summary_close": [
        "The overall package supports confident buying decisions by combining useful features with stable day-to-day usability.",
        "It offers a practical balance of strengths that should work well for most buyers across common usage scenarios.",
        "This option delivers consistent value while keeping tradeoffs manageable, which is important for long-term satisfaction.",
        "Its profile is balanced enough for regular use and avoids the kind of complexity that often goes unused.",
        "For most buyers, this combination of quality signals and feature fit makes it a low-risk shortlist candidate.",
        "It provides a dependable baseline of performance and usability, making it easier to recommend across broad use cases.",
        "The value proposition is strong when you consider usability, confidence signals, and expected product lifespan together.",
        "This recommendation is especially useful for buyers who want predictable outcomes rather than feature-heavy uncertainty.",
        "Overall, it presents a trustworthy mix of practical capability and purchase confidence for long-term use.",
        "As a general-purpose pick, it maintains a healthy balance between what buyers need and what they actually use.",
    ],
}


def choose(rng: random.Random, key: str, **kwargs: str) -> str:
    return rng.choice(TEXT_BANK[key]).format(**kwargs)


def pick_many(rng: random.Random, pool: Sequence[str], count: int) -> List[str]:
    if count <= 0:
        return []
    if len(pool) <= count:
        return list(pool)
    return rng.sample(list(pool), count)

def infer_use_cases(keyword: str) -> List[str]:
    _ = keyword
    return ["everyday use", "value-focused buying", "advanced needs"]


def infer_factors(keyword: str) -> List[str]:
    _ = keyword
    return [
        "Performance and Product Fit",
        "Value and Feature Balance",
        "Ease of Use and Support",
    ]


def infer_life(keyword: str) -> str:
    _ = keyword
    return "from a few months to several years, depending on product type and usage"


def load_products(csv_path: Path) -> Dict[str, List[Product]]:
    grouped: Dict[str, List[Product]] = {}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            keyword = clean_text_artifacts(row.get("keyword") or "")
            title = clean_text_artifacts(row.get("product_name") or "")
            url = (row.get("product_url") or "").strip()
            if not keyword or not title or not url:
                continue
            grouped.setdefault(keyword, []).append(
                Product(
                    keyword=keyword,
                    product_name=title,
                    product_url=url,
                    image_url=clean_text_artifacts(row.get("image_url") or ""),
                    rating=parse_float(row.get("rating"), 0.0),
                    review_count=parse_int(row.get("review_count"), 0),
                    rank_for_keyword=parse_int(row.get("rank_for_keyword"), 9999),
                    final_score=parse_float(row.get("final_score"), 0.0),
                )
            )
    return grouped


def pick_products(products: Sequence[Product], top_n: int) -> List[Product]:
    ordered = sorted(products, key=lambda x: (x.rank_for_keyword if x.rank_for_keyword > 0 else 9999, -x.final_score, -x.rating, -x.review_count))
    out: List[Product] = []
    seen = set()
    for p in ordered:
        key = norm(short_title(p.product_name))
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
        if len(out) >= top_n:
            break
    return out


def short_overlay_text(keyword: str, max_words: int = 6) -> str:
    words = clean_keyword(keyword).title().split()
    if not words:
        return "Top Picks"
    return " ".join(words[:max_words])


def pick_feature_image_urls(products: Sequence[Product], limit: int = 4) -> List[str]:
    urls: List[str] = []
    seen = set()
    for p in products:
        u = (p.image_url or "").strip()
        if not u or u in seen:
            continue
        seen.add(u)
        urls.append(u)
        if len(urls) >= limit:
            break
    return urls


def feature_style_variants() -> List[Dict[str, str]]:
    return [
        {"layout": "layout-a", "overlay": "overlay-a", "font": "font-a"},
        {"layout": "layout-b", "overlay": "overlay-b", "font": "font-b"},
        {"layout": "layout-c", "overlay": "overlay-c", "font": "font-c"},
        {"layout": "layout-d", "overlay": "overlay-d", "font": "font-d"},
    ]


def prepare_feature_collage(build: ArticleBuild, rng: random.Random) -> None:
    images = pick_feature_image_urls(build.products, limit=4)
    if not images:
        images = ["assets/site-logo.svg"]
    while len(images) < 4:
        images.append(images[-1])
    variant = rng.choice(feature_style_variants())
    build.feature_primary_image = images[0]
    build.feature_images = images[:4]
    build.feature_layout = variant["layout"]
    build.feature_overlay = variant["overlay"]
    build.feature_font = variant["font"]
    build.feature_text = f"{short_overlay_text(build.keyword, max_words=6)} Picks"


def render_feature_collage(build: ArticleBuild, *, context: str) -> str:
    images = list(build.feature_images or [])
    if not images:
        images = [build.feature_primary_image or "assets/site-logo.svg"]
    while len(images) < 4:
        images.append(images[-1])
    title = build.feature_text or f"{short_overlay_text(build.keyword, max_words=6)} Picks"
    loading = "eager" if context == "article" else "lazy"
    figure_class = "feature-collage feature-collage-article" if context == "article" else "feature-collage feature-collage-card"
    tiles = "".join(
        f"<img class='tile tile-{i + 1}' src='{esc(url)}' alt='{esc(title)} collage image {i + 1}' loading='{loading}' decoding='async' onerror=\"this.onerror=null;this.src='assets/site-logo.svg';\">"
        for i, url in enumerate(images[:4])
    )
    return (
        f"<figure class='{figure_class} {esc(build.feature_layout)}'>"
        f"{tiles}"
        f"<div class='feature-collage-overlay {esc(build.feature_overlay)}'></div>"
        f"<figcaption class='feature-collage-title {esc(build.feature_font)}'>{esc(title)}</figcaption>"
        "</figure>"
    )


def render_article_fragment(keyword: str, products: Sequence[Product], tag: str, rng: random.Random, feature_html: str) -> str:
    clean_kw = clean_keyword(keyword)
    use_cases = infer_use_cases(clean_kw)
    factors = infer_factors(clean_kw)
    life = infer_life(clean_kw)

    roles = ["Best Overall", "Best Budget", "Best Premium", f"Best for {use_cases[0]}", "Best Alternative"]
    intro_close = [
        f"Whether your priority is {use_cases[0]}, {use_cases[1]}, or {use_cases[2]}, the sections below are arranged to reduce confusion and help you move from browsing to a confident final pick.",
        f"From {use_cases[0]} to {use_cases[1]} and {use_cases[2]}, this page follows a practical sequence so you can shortlist quickly and still validate details before spending money.",
        f"If you are balancing {use_cases[0]}, {use_cases[1]}, and {use_cases[2]}, start with the comparison table and then use the review blocks to confirm real fit before checkout.",
        f"This guide is built for buyers with goals like {use_cases[0]}, {use_cases[1]}, and {use_cases[2]}, so the same framework remains useful even when product specs vary.",
        f"For needs ranging from {use_cases[0]} to {use_cases[1]} and {use_cases[2]}, the recommendation flow below keeps decisions practical by focusing on value, fit, and reliability.",
        "You will also find generalized buying factors, common mistakes, and concise FAQ guidance so the final decision is easier to justify and less likely to lead to buyer regret.",
        "Use the quick comparison section for fast shortlist creation, then validate your top candidates with the detailed review sections before making a final commitment.",
        "By the end of this page, you should clearly identify one safe overall choice plus strong alternatives for budget-focused and premium-focused buying situations.",
        "The structure is intentionally universal, which means the same decision process can be reused across many categories without rewriting your buying logic every time.",
        "Everything below is designed to reduce decision fatigue while preserving the practical details that matter most for long-term satisfaction after purchase.",
    ]

    intro_text = (
        f"<p>{esc(choose(rng, 'intro_open', k=clean_kw))}</p>"
        f"<p>{esc(choose(rng, 'intro_mid'))}</p>"
        f"<p>{esc(rng.choice(intro_close))}</p>"
    )

    style_table = "width: 100%; border-collapse: collapse; border: 1px solid #d1d5db; margin: 30px 0; background: #fff; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-radius: 8px; overflow: hidden; table-layout: auto;"
    style_th = "background: #1e293b; color: white; padding: 10px 8px; text-align: left; font-size: 13px; text-transform: uppercase; border-bottom: 3px solid #f97316; border-right: 1px solid #334155; vertical-align: middle;"
    style_td = "padding: 8px; border-bottom: 1px solid #e5e7eb; border-right: 1px solid #e5e7eb; vertical-align: middle; line-height: 1.3; color: #333; font-size: 13px;"
    style_btn = "display: block; background: #ea580c; color: #fff !important; text-align: center; padding: 8px 6px; text-decoration: none !important; border-radius: 4px; font-weight: bold; font-size: 11px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin: 0 auto; width: 100%; max-width: 90px; box-sizing: border-box;"

    table_html = (
        f"<h2>Top {len(products)} Best {esc(clean_kw.title())} {YEAR}</h2>"
        f"<div style='overflow-x: auto;'><table style='{style_table}'><thead><tr>"
        f"<th style='{style_th} width: 30px; text-align: center;'>#</th>"
        f"<th style='{style_th}'>Product</th>"
        f"<th style='{style_th} width: 25%;'>Feature</th>"
        f"<th style='{style_th} width: 95px; text-align: center; border-right: none;'>Action</th>"
        "</tr></thead><tbody>"
    )

    rows = []
    for i, p in enumerate(products, 1):
        role = roles[i - 1] if i <= len(roles) else f"Top Pick #{i}"
        title = short_title(p.product_name)
        feature = extract_feature(p.product_name)
        url = ensure_affiliate_tag(p.product_url, tag)
        bg = "#f8fafc" if i % 2 == 0 else "#ffffff"
        rows.append({"title": title, "feature": feature, "url": url, "image": p.image_url, "role": role, "product": p})
        table_html += (
            f"<tr style='background-color: {bg};'>"
            f"<td style='{style_td} text-align: center; font-weight: bold; color: #64748b;'>{i}</td>"
            f"<td style='{style_td} font-weight: 600;'><a href='{esc(url)}' target='_blank' rel='nofollow' style='color: #0f172a; text-decoration: none;'>{esc(title)}</a></td>"
            f"<td style='{style_td} font-style: italic; color: #64748b;'>{esc(feature)}</td>"
            f"<td style='{style_td} border-right: none; text-align: center;'><a href='{esc(url)}' target='_blank' rel='nofollow' style='{style_btn}'>Check Price</a></td>"
            "</tr>"
        )
    table_html += "</tbody></table></div>"

    reviews_html = f"<h2>Detailed Product Reviews of Best {esc(clean_kw.title())}</h2>{feature_html}"
    review_fragment = "#:~:text=Top%20reviews%20from%20the%20United%20States"

    for i, row in enumerate(rows, 1):
        p = row["product"]
        benefit = (
            "overall reliability"
            if "overall" in row["role"].lower()
            else (
                "value for money"
                if "budget" in row["role"].lower()
                else (
                    "advanced performance"
                    if "premium" in row["role"].lower()
                    else "everyday usability"
                )
            )
        )
        summary = f"{esc(choose(rng, 'summary_open', p=row['title'], b=benefit))} {esc(choose(rng, 'summary_close'))}"
        pros_pool = [
            "Strong buyer sentiment supports confidence in day-to-day performance across common usage scenarios.",
            "Feature mix is practical and aligned with what most buyers actually need in regular workflows.",
            "Works well for routine usage without requiring a steep learning curve or complex setup process.",
            "Delivers balanced value when quality, usability, and pricing are evaluated together instead of separately.",
            "Suitable for buyers who prefer dependable outcomes over unnecessary complexity or feature overload.",
            "Shows healthy trust signals for users who want a lower-risk purchase with predictable results.",
            "Can fit both first-time buyers and experienced users who need a balanced all-around option.",
            "Positioned as a stable long-term choice rather than a short-term novelty driven by marketing hype.",
            "Often shortlisted for its practical profile across core performance, comfort, and overall utility.",
            "Provides enough capability for most use cases without adding costly extras that go unused.",
            "Product details and buyer feedback indicate a reliable ownership experience after initial purchase.",
            "A practical candidate when comparing real value, not just headline features or pricing claims.",
            "Usability profile makes onboarding smoother for buyers with different experience levels.",
            "Good option for buyers who prioritize dependable baseline performance before advanced features.",
            "Supports confident decisions through balanced strengths and manageable limitations.",
            "Offers a sensible blend of reliability and flexibility for a wide range of buyer priorities.",
            "Reduces decision risk by combining useful feature coverage with consistent buyer confidence signals.",
            "Maintains a practical value profile that remains competitive in both short-term and long-term use.",
            "Design and feature structure appear optimized for real usage rather than purely promotional appeal.",
            "Provides a dependable foundation that should satisfy most buyers without frequent upgrades.",
            "Category fit is broad enough to serve multiple use patterns with minimal compromise.",
            "Ownership effort is generally manageable, which helps maintain long-term product satisfaction.",
            "Delivers a balanced experience where core functionality remains clear and easy to access.",
            "Buyer-friendly profile makes comparison easier when filtering options by trust and practicality.",
            "Combines performance confidence with practical feature relevance for stronger buying justification.",
            "Represents a low-friction option for buyers who want stable output and fewer surprises.",
            "Useful for value-focused buyers who still care about consistency and product longevity.",
            "Keeps tradeoffs reasonable while preserving the primary capabilities expected in this category.",
            "Often recommended as a safe shortlist option when buyers need balanced outcomes quickly.",
            "Shows signs of dependable real-world performance based on available feedback quality.",
        ]
        cons_pool = [
            "May not include every specialized capability available in niche or premium-tier alternatives.",
            "Performance can vary depending on setup quality, usage intensity, and buyer expectations.",
            "Some buyers may find advanced settings unnecessary if their routine needs are simple.",
            "A higher-end model may offer stronger optimization for specialized or heavy-duty workflows.",
            "Real-world outcomes can depend on maintenance habits and correct day-to-day usage.",
            "Not every buyer will benefit equally from the complete feature set offered here.",
            "Users with narrow, specific requirements may prefer a more specialized product option.",
            "Availability, variant selection, or seller-level packaging can change over time.",
            "Best value depends on your priorities, so feature fit should be checked before purchase.",
            "For edge-case workflows, dedicated premium models may deliver stronger results.",
            "Long-term satisfaction depends on how closely this model matches your exact use case.",
            "Some users may need a short adjustment period before getting consistent results.",
            "Certain advanced buyers may prefer more granular controls than this option provides.",
            "Category expectations vary, so practical performance should be validated against your workflow.",
            "Support and accessory ecosystem can differ by seller, region, and listing version.",
            "A simpler or more specialized option might be better for highly targeted needs.",
            "Feature depth may be broader than necessary for buyers with very basic requirements.",
            "Lifespan expectations can vary by usage frequency and operating conditions.",
            "Buyers seeking top-tier refinement may still prefer a premium-focused alternative.",
            "Some tradeoffs may appear when prioritizing balanced value over maximum specialization.",
            "Specification wording can look similar across products, so deeper comparison is still required.",
            "Performance consistency may improve with proper setup and realistic use expectations.",
            "If your use case changes often, you may need more flexibility than this model offers.",
            "Not all product variants are equal, so listing details should be reviewed carefully.",
            "Upfront value may look strong, but long-term fit depends on your real workflow demands.",
            "Some buyers may need additional accessories or setup steps for best outcomes.",
            "Differences between product generations can affect fit, so version checks are important.",
            "A competing model may provide better optimization for one specific priority.",
            "If advanced customization is critical, a specialist-tier alternative may be more suitable.",
            "As with most categories, the final experience depends on correct use and maintenance habits.",
        ]
        if p.rating >= 4.5:
            pros_pool.append("High rating consistency indicates broad buyer satisfaction over time.")
        else:
            pros_pool.append("Rating profile remains competitive for value-focused buyers.")
        if p.review_count >= 1000:
            pros_pool.append("Large review volume improves confidence in overall product consistency.")
        else:
            pros_pool.append("Early review signals are positive, though long-term data is still growing.")

        pros = pick_many(rng, pros_pool, 3)
        cons = pick_many(rng, cons_pool, 2)
        pros_html = "".join([f"<li style='margin-bottom: 6px; list-style: none;'>+ {esc(x)}</li>" for x in pros])
        cons_html = "".join([f"<li style='margin-bottom: 6px; list-style: none;'>- {esc(x)}</li>" for x in cons])
        specs = [row["feature"], f"Average rating: {p.rating:.1f}/5", f"Review count: {p.review_count:,}", f"Best for: {row['role']}"]
        specs_html = "".join([f"<li style='margin-bottom: 5px; padding-left: 5px;'>* {esc(x)}</li>" for x in specs])
        user_review_url = f"{row['url']}{review_fragment}"

        reviews_html += (
            "<div style='border: 1px solid #e2e8f0; padding: 30px; margin-bottom: 50px; border-radius: 12px; background: #fff; box-shadow: 0 4px 6px rgba(0,0,0,0.03);'>"
            f"<h3 style='color: #ea580c; border-bottom: 2px solid #fdba74; padding-bottom: 12px; margin-top: 0;'>{i}. <a href='{esc(row['url'])}' target='_blank' rel='nofollow' style='color: inherit; text-decoration: none;'>{esc(row['title'])} - {esc(row['role'])}</a></h3>"
            "<div style='text-align: center; margin: 30px 0;'>"
            f"<a href='{esc(row['url'])}' target='_blank' rel='nofollow' style='display: block; margin-bottom: 20px;'><img src='{esc(row['image'])}' alt='{esc(row['title'])}' style='max-height: 280px; width: auto; max-width: 100%; border-radius: 8px; margin: 0 auto; display: block;'></a>"
            "<div class='amz-dual-btn-container'>"
            f"<a href='{esc(user_review_url)}' target='_blank' rel='nofollow' class='amz-user-review-btn'>Read User Reviews</a>"
            f"<a href='{esc(row['url'])}' target='_blank' rel='nofollow' class='amz-buy-btn'>View on Amazon</a>"
            "</div></div>"
            "<div style='background: #f8fafc; padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #e2e8f0;'>"
            "<h4 style='margin: 0 0 10px 0; color: #475569;'>Key Specifications</h4>"
            f"<ul style='padding-left: 20px; color: #334155; margin: 0; list-style-type: none;'>{specs_html}</ul>"
            "</div>"
            f"<p style='color: #334155; line-height: 1.7; font-size: 1.05rem;'>{summary}</p>"
            "<div class='amz-pros-cons-grid' style='display: flex; gap: 20px; flex-wrap: wrap; margin-top: 25px;'>"
            "<div class='amz-pros-cons-col' style='flex: 1; background: #f0fdf4; padding: 20px; border-radius: 8px; border: 1px solid #bbf7d0; min-width: 250px;'>"
            "<h4 style='color: #166534; margin-top: 0; margin-bottom: 15px;'>What We Like</h4>"
            f"<ul style='padding: 0; margin: 0; color: #14532d; font-size: 0.95rem;'>{pros_html}</ul>"
            "</div>"
            "<div class='amz-pros-cons-col' style='flex: 1; background: #fef2f2; padding: 20px; border-radius: 8px; border: 1px solid #fecaca; min-width: 250px;'>"
            "<h4 style='color: #991b1b; margin-top: 0; margin-bottom: 15px;'>Flaws</h4>"
            f"<ul style='padding: 0; margin: 0; color: #7f1d1d; font-size: 0.95rem;'>{cons_html}</ul>"
            "</div></div>"
            "<div style='text-align: center; margin-top: 18px;'>"
            f"<a href='{esc(row['url'])}' target='_blank' rel='nofollow' class='amz-buy-btn' style='display: inline-block !important; max-width: 260px;'>Buy on Amazon</a>"
            "</div></div>"
        )

    f1 = [
        "Prioritize core performance before bonus features, because reliable baseline output usually matters more than advanced options in long-term ownership.",
        "Start by validating primary function quality, then compare secondary features only among products that already pass core reliability checks.",
        "Check baseline output and consistency first, since weak core performance cannot be fixed by extra features later.",
        "Do not let feature lists hide poor fundamentals; verify practical results through ratings, review themes, and repeat complaints.",
        "Use real buyer feedback to confirm that performance remains stable outside controlled listing claims.",
        "Focus on consistency instead of headline numbers, because predictable results usually drive satisfaction more than peak performance alone.",
        "Core function quality should carry most decision weight, especially when you want a product that lasts beyond initial excitement.",
        "Filter weak options early using baseline quality signals so you spend time only on realistic shortlist candidates.",
        "Prioritize products that deliver stable day-to-day performance instead of occasional high output under limited conditions.",
        "Compare practical results before extras, then choose the option with fewer critical tradeoffs for your routine.",
    ]
    f2 = [
        "Match capacity and feature level to your real routine so you avoid paying for specifications you rarely use.",
        "Choose balanced value over the highest numbers, since maximum specs are not always equal to better day-to-day outcomes.",
        "Most buyers get stronger long-term value in the middle tier where price and practical performance are better aligned.",
        "Avoid overpaying for unused features by mapping your use frequency, priority tasks, and budget ceiling first.",
        "Compare practical need against feature depth to identify where extra spending has clear return and where it does not.",
        "Selecting one level above your minimum need can improve longevity, but going far beyond that often reduces value.",
        "Do not overbuy based on marketing language; assess measurable benefits that directly support your workflow.",
        "Use expected usage frequency to pick the right tier and prevent both underbuying and unnecessary premium spending.",
        "Cost and output should remain balanced, with emphasis on consistent utility rather than rare peak scenarios.",
        "Pick value by use-case fit and ownership confidence, not by feature count alone.",
    ]
    f3 = [
        "Treat advanced features as optional unless they solve a real recurring problem in your workflow.",
        "Upgrade only when your routine clearly benefits from higher capability, not just because advanced specs are available.",
        "Extra features matter only when they improve outcomes you can measure in normal usage.",
        "Avoid complexity that does not improve results, because more settings can increase friction without adding value.",
        "Power users usually gain the most from advanced capability, while casual users often prefer simpler dependable options.",
        "Simpler models can offer better practical value when your needs are stable and straightforward.",
        "Choose features based on routine fit, not hype, so long-term satisfaction remains strong after purchase.",
        "Use-case relevance is more important than feature count when evaluating overall buying quality.",
        "Premium capability should have clear practical return in speed, reliability, or long-term ownership benefits.",
        "Do not pay for advanced functions you are unlikely to use consistently over time.",
    ]

    guide_html = (
        f"<h3 style='color: #1e293b; margin-top: 25px; border-left: 4px solid #ea580c; padding-left: 10px;'>{esc(factors[0])}</h3><p>{esc(rng.choice(f1))}</p>"
        f"<h3 style='color: #1e293b; margin-top: 25px; border-left: 4px solid #ea580c; padding-left: 10px;'>{esc(factors[1])}</h3><p>{esc(rng.choice(f2))}</p>"
        f"<h3 style='color: #1e293b; margin-top: 25px; border-left: 4px solid #ea580c; padding-left: 10px;'>{esc(factors[2])}</h3><p>{esc(rng.choice(f3))}</p>"
        "<h3 style='color: #1e293b; margin-top: 25px; border-left: 4px solid #ea580c; padding-left: 10px;'>Build Quality and Durability</h3><p>Regardless of category, durability matters. Look for reliable construction quality and long term buyer feedback.</p>"
        "<h3 style='color: #1e293b; margin-top: 25px; border-left: 4px solid #ea580c; padding-left: 10px;'>Ease of Use and Comfort</h3><p>Choose a product that matches your experience level and routine. Complex features are not always necessary.</p>"
        "<h3 style='color: #1e293b; margin-top: 25px; border-left: 4px solid #ea580c; padding-left: 10px;'>Warranty and Brand Trust</h3><p>Reliable brands usually provide better support, clear documentation, and stronger return policy confidence.</p>"
    )

    m1 = [
        "Choosing only by price without checking overall quality and long-term reliability signals.",
        "Buying the cheapest option first without validating core performance for your actual needs.",
        "Focusing only on discounts while ignoring product fit, durability, and support quality.",
        "Treating price as the only factor instead of balancing value, usability, and expected lifespan.",
        "Assuming lower cost automatically means better value without comparing practical outcomes.",
        "Ignoring long-term ownership cost, including replacement risk and maintenance effort.",
        "Picking deals without checking whether the product truly matches your workflow.",
        "Comparing cost but not quality consistency in verified buyer feedback.",
        "Making budget-driven decisions without validating baseline reliability signals.",
        "Saving upfront but replacing too early due to poor product fit.",
    ]
    m2 = [
        "Ignoring compatibility, sizing, or technical constraints that affect real-world usability.",
        "Skipping core specification checks before purchase and discovering mismatches later.",
        "Buying before confirming compatibility with your setup, routine, or usage conditions.",
        "Overlooking product limits that matter for your expected performance level.",
        "Assuming all models behave similarly even when specs and build quality differ.",
        "Missing setup or fit requirements that can reduce satisfaction after delivery.",
        "Choosing quickly without validating constraints that directly affect day-to-day use.",
        "Forgetting category-specific requirements that separate good fit from poor fit.",
        "Selecting the wrong variant or version for your intended use case.",
        "Skipping practical fit verification and relying only on listing claims.",
    ]
    m3 = [
        "Not checking verified customer feedback for recurring strengths and recurring complaints.",
        "Ignoring review patterns that reveal quality consistency over time.",
        "Relying only on photos and marketing copy without deeper buyer evidence.",
        "Overlooking repeated complaints that indicate real reliability issues.",
        "Trusting product claims without validating them through buyer experience data.",
        "Reading star ratings only and skipping written reviews with practical context.",
        "Missing durability and support comments that affect long-term ownership.",
        "Ignoring recent review trends that may reflect product or seller changes.",
        "Skipping customer service and warranty feedback before purchase.",
        "Buying without cross-checking confidence signals from multiple review angles.",
    ]
    m4 = [
        "Buying the wrong type for your specific use case and daily usage level.",
        "Choosing a mismatched model that does not align with your key priorities.",
        "Selecting a tier that is either too basic or too advanced for your workflow.",
        "Using one-size-fits-all thinking in a category where needs vary significantly.",
        "Buying based on popularity instead of fit for your own requirements.",
        "Choosing features that look impressive but do not solve your core problem.",
        "Copying someone else's recommendation without validating your own use case.",
        "Getting a model with unnecessary complexity or insufficient capability.",
        "Ignoring workflow fit while focusing only on headline specs.",
        "Picking based on trends instead of practical performance needs.",
    ]
    m5 = [
        "Overpaying for premium features that will rarely be used in regular routines.",
        "Spending extra on advanced specifications without measurable real-world benefit.",
        "Paying for complexity that increases cost but does not improve outcomes.",
        "Choosing top-tier pricing without top-tier usage needs.",
        "Buying premium when a strong mid-range option already covers your priorities.",
        "Upgrading beyond workflow requirements and reducing total value-for-money.",
        "Treating expensive as automatically better despite fit being the main factor.",
        "Overspending on feature count rather than practical utility and reliability.",
        "Paying more for headline specs that do not impact your daily usage.",
        "Choosing premium without a clear return in durability, output, or convenience.",
    ]

    top = rows[0]["title"]
    budget = rows[1]["title"] if len(rows) > 1 else top
    premium = rows[2]["title"] if len(rows) > 2 else top

    faq_q2 = [
        "They are worth it when you need advanced capability, heavier usage support, or stronger long-term durability; otherwise a high-quality mid-range option usually offers better value.",
        "Premium models make the most sense for demanding workloads, while many buyers achieve excellent results from well-reviewed mid-tier products.",
        "Higher pricing is easier to justify for frequent or intensive use, but casual use often does not require premium-level investment.",
        "If your workflow is demanding and consistent, premium can pay off over time; for normal use, mid-range is often the smarter choice.",
        "Choose based on need intensity and expected usage duration, not price category alone.",
        "Power users tend to benefit most from expensive models, while occasional users usually gain more value from balanced options.",
        "High-end picks often add refinement, but strongest value-for-money frequently sits in the middle tier.",
        "Paying more helps only when added capability directly improves your routine outcomes.",
        "Premium pricing can be worthwhile when support quality, durability, and consistency are top priorities.",
        "For a large percentage of buyers, mid-range options deliver the best practical balance of cost and performance.",
    ]
    faq_q4 = [
        "Avoid low-rated listings, unclear specifications, weak warranty terms, and marketing claims that are not backed by clear product details.",
        "Skip products with weak review patterns, vague technical information, or inconsistent seller support transparency.",
        "Do not buy models with unclear compatibility details and repeated complaints about reliability or service quality.",
        "Avoid listings that hide key specifications or provide limited information about return and warranty conditions.",
        "Be cautious with products that overpromise performance but underdocument practical usage limitations.",
        "Skip low-confidence listings where support quality and return handling are unclear.",
        "Avoid options that repeatedly show reliability issues across verified customer feedback.",
        "Do not trust listings with inconsistent details, unclear policies, or poor documentation.",
        "Avoid products where critical information is incomplete or difficult to verify.",
        "Stay away from listings that show weak buyer trust signals across multiple indicators.",
    ]

    mistakes_html = (
        f"<h3 style='margin-top: 25px; color: #333;'>Common Mistakes When Buying {esc(clean_kw.title())}</h3>"
        "<ul style='color: #555; line-height: 1.8;'>"
        f"<li>{esc(rng.choice(m1))}</li><li>{esc(rng.choice(m2))}</li><li>{esc(rng.choice(m3))}</li><li>{esc(rng.choice(m4))}</li><li>{esc(rng.choice(m5))}</li>"
        "</ul>"
    )

    faq_html = (
        f"<h3 style='margin-top: 25px; color: #333;'>Q1: Which option is best for everyday use?</h3><p style='color: #555;'>A: It depends on your priorities, but {esc(top)} is usually a safe choice for balanced quality and reliability.</p>"
        f"<h3 style='margin-top: 25px; color: #333;'>Q2: Are expensive options worth it?</h3><p style='color: #555;'>A: {esc(rng.choice(faq_q2))}</p>"
        f"<h3 style='margin-top: 25px; color: #333;'>Q3: How long do products in this category usually last?</h3><p style='color: #555;'>A: Lifespan depends on quality, usage, and maintenance. A practical range is {esc(life)}.</p>"
        f"<h3 style='margin-top: 25px; color: #333;'>Q4: What should I avoid before buying?</h3><p style='color: #555;'>A: {esc(rng.choice(faq_q4))}</p>"
    )

    final_overall = [
        f"If you want the safest all-around choice with balanced performance and value, go with {top}.",
        f"For most buyers, {top} remains the strongest overall recommendation because it keeps major tradeoffs under control.",
        f"Our overall winner is {top}, mainly due to its consistency, buyer confidence signals, and practical day-to-day value.",
        f"When you are unsure which option to trust most, {top} is the most balanced pick to start with.",
        f"Overall, {top} is the safest recommendation for broad usage needs and mixed buyer priorities.",
        f"As a default recommendation, {top} offers one of the best blends of quality, fit, and manageable compromise.",
        f"The strongest general-purpose pick in this list is {top} for buyers who want dependable long-term results.",
        f"For broad use cases where reliability matters most, {top} stands out as the most dependable option.",
        f"If you need one reliable pick without over-optimizing every detail, {top} is the best front-runner.",
        f"The best all-purpose recommendation on this page is {top}, especially for balanced value-focused decisions.",
    ]
    final_budget = [
        f"If you are on a budget, {budget} offers excellent value while keeping core quality signals competitive.",
        f"For value-focused buyers, {budget} is the strongest budget direction without sacrificing key functionality.",
        f"If you need lower spend with practical reliability, {budget} is a smart budget pick to prioritize.",
        f"When cost control is the main goal, shortlist {budget} first and compare from that benchmark.",
        f"Budget-conscious buyers should begin with {budget} because it balances affordability with usable capability.",
        f"On tighter budgets, {budget} delivers strong value per dollar for typical everyday requirements.",
        f"If price is your primary constraint, {budget} remains one of the most practical options in this list.",
        f"For budget use cases, {budget} stays highly competitive on fit, trust signals, and total value.",
        f"For affordability with balanced quality expectations, {budget} is an easy recommendation to consider.",
        f"Value seekers can confidently shortlist {budget} when they need practical results without premium pricing.",
    ]
    final_premium = [
        f"For premium performance and advanced feature depth, {premium} is the strongest high-end option on this page.",
        f"If you need higher-end capability for demanding use, choose {premium} as the premium-focused recommendation.",
        f"Premium buyers who prioritize refinement and stronger capability should evaluate {premium} first.",
        f"For top-tier performance where advanced output matters, {premium} is the premium recommendation to beat.",
        f"At the high end of this comparison, {premium} stands out for buyers with more demanding expectations.",
        f"For intensive workflows that justify extra investment, {premium} is worth considering as a first choice.",
        f"For refined performance plus added flexibility, {premium} is the premium direction with clearer upside.",
        f"If you want a premium model with stronger capability signals, {premium} is the best candidate here.",
        f"When advanced performance is a priority over price sensitivity, {premium} is the better premium pick.",
        f"Users who need high-end outcomes and feature depth will likely prefer {premium}.",
    ]

    verdict_html = (
        "<h2>Final Verdict</h2>"
        f"<p>{esc(rng.choice(final_overall))}</p><p>{esc(rng.choice(final_budget))}</p><p>{esc(rng.choice(final_premium))}</p><p>Choose based on your needs, not only on price.</p>"
        f"<a href='{esc(rows[0]['url'])}' target='_blank' rel='nofollow' style='text-decoration: none; color: inherit; display: block;'>"
        "<div style='border: 2px solid #ea580c; background: #fff7ed; padding: 40px; border-radius: 12px; text-align: center; margin-top: 30px; transition: transform 0.2s; cursor: pointer;'>"
        "<h3 style='margin-top: 0; color: #c2410c; font-size: 1.5rem;'>Top Recommendation</h3>"
        f"<img src='{esc(rows[0]['image'])}' width='220' style='margin: 20px auto; display: block; border-radius: 8px;'>"
        f"<p style='font-size: 1.4rem; font-weight: 800; color: #1e293b; text-decoration: underline;'>{esc(rows[0]['title'])}</p>"
        "<span style='background: #ea580c; color: white; padding: 16px 50px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 1.2rem; display: inline-block; box-shadow: 0 4px 10px rgba(234, 88, 12, 0.3); margin-top: 10px;'>Check Price on Amazon</span>"
        "</div></a>"
    )

    article_html = (
        f"{RESPONSIVE_ASSETS}<div class='affiliate-container' style='font-family: inherit;'>"
        f"{intro_text}{table_html}{reviews_html}<h2>Buying Guide</h2>{guide_html}{mistakes_html}"
        f"<h2>Frequently Asked Questions</h2>{faq_html}{verdict_html}</div>"
    )
    return article_html.replace("rel='nofollow'", "rel='nofollow sponsored noopener'")


SITE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Sora:wght@500;600;700;800&display=swap');
:root {
  --bg: #eef2f7;
  --surface: #ffffff;
  --ink: #13223b;
  --muted: #526077;
  --accent: #e67e22;
  --accent-strong: #c25c05;
  --line: #d7e0ea;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  font-family: "Plus Jakarta Sans", "Segoe UI", Arial, sans-serif;
  color: var(--ink);
  background:
    radial-gradient(circle at 8% 4%, #d9e8ff 0%, transparent 27%),
    radial-gradient(circle at 92% 0%, #ffe4cb 0%, transparent 24%),
    var(--bg);
  line-height: 1.6;
}
a { color: inherit; text-decoration: none; }
.site-header {
  position: sticky;
  top: 0;
  z-index: 50;
  background: rgba(255, 255, 255, 0.94);
  border-bottom: 1px solid var(--line);
  backdrop-filter: blur(8px);
}
.site-header-inner, .site-footer-inner, .page-wrap {
  width: min(1120px, calc(100% - 32px));
  margin: 0 auto;
}
.site-header-inner {
  display: flex;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
  padding: 14px 0;
}
.logo {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-weight: 800;
  font-family: "Sora", "Plus Jakarta Sans", sans-serif;
  letter-spacing: 0.1px;
}
.logo-mark {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: linear-gradient(135deg, #0b5ed7, #0ea5e9);
}
.site-nav {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.nav-link {
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid transparent;
  color: var(--muted);
  font-size: 0.9rem;
  transition: all 0.2s ease;
}
.nav-link:hover { border-color: var(--line); color: var(--ink); background: #f8fbff; }
.nav-link.active { color: var(--ink); border-color: #bcd3ee; background: #e8f3ff; }
.nav-cta {
  margin-left: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 9px 14px;
  border-radius: 10px;
  background: linear-gradient(135deg, #e67e22, #c25c05);
  color: #fff;
  font-size: 0.84rem;
  font-weight: 800;
  font-family: "Sora", "Plus Jakarta Sans", sans-serif;
  box-shadow: 0 8px 16px rgba(194, 92, 5, 0.22);
}
.page-wrap { padding: 34px 0 56px; }
.hero-card, .content-card, .article-card, .disclosure-card, .author-card, .related-card {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 16px;
  box-shadow: 0 12px 24px rgba(11, 35, 68, 0.05);
}
.content-card > h2 {
  margin: 0 0 14px;
  font-size: clamp(1.28rem, 2.3vw, 1.85rem);
  line-height: 1.25;
}
.hero-card {
  padding: 34px;
  background:
    linear-gradient(120deg, rgba(11, 94, 215, 0.12), rgba(14, 165, 233, 0.05)),
    var(--surface);
}
.hero-kicker {
  display: inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid #bad7ef;
  background: #ecf7ff;
  color: #0a4a6f;
  font-weight: 700;
  font-size: 0.78rem;
}
.hero-card h1, .content-card h1, .article-card h1 {
  margin: 14px 0 10px;
  line-height: 1.25;
  font-size: clamp(1.8rem, 4vw, 2.8rem);
}
.hero-card p { margin: 0; color: var(--muted); max-width: 74ch; }
.search-input {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 12px 14px;
  font-family: inherit;
  font-size: 0.95rem;
  background: #fcfdff;
}
.search-input:focus {
  outline: 2px solid #b7d7f4;
  border-color: #88bbec;
}
.article-grid {
  margin-top: 22px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
.article-link-card {
  padding: 0;
  overflow: hidden;
  border-radius: 14px;
  border: 1px solid var(--line);
  background: #fff;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}
.article-link-card:hover {
  transform: translateY(-3px);
  border-color: #b6cbe3;
  box-shadow: 0 14px 25px rgba(11, 35, 68, 0.08);
}
.article-link-card h3 { margin: 0 0 8px; font-size: 1.02rem; line-height: 1.35; }
.article-link-card p { margin: 0; color: var(--muted); font-size: 0.9rem; }
.article-card-content {
  padding: 14px 15px 16px;
}
.card-cta {
  margin-top: 9px;
  display: inline-flex;
  color: #0f4a87;
  font-weight: 700;
  font-size: 0.86rem;
}
.article-card, .content-card { padding: 30px; }
.breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
  font-size: 0.9rem;
  margin: 0 0 12px;
}
.breadcrumb a { color: #134e95; }
.meta-line {
  color: var(--muted);
  font-size: 0.92rem;
  margin: 0 0 18px;
}
.disclosure-card {
  margin: 0 0 20px;
  padding: 14px 16px;
  border-left: 4px solid var(--accent);
  background: #fff8ef;
}
.disclosure-card strong { color: #8a4301; }
.article-body p { color: #273447; }
.feature-collage {
  position: relative;
  width: 100%;
  aspect-ratio: 1200 / 675;
  max-height: 675px;
  min-height: 180px;
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 14px;
  display: grid;
  gap: 2px;
  background: #dae6f4;
}
.feature-collage img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.feature-collage.layout-a {
  grid-template-columns: 1.65fr 1fr;
  grid-template-rows: repeat(3, 1fr);
}
.feature-collage.layout-a .tile-1 { grid-row: 1 / span 3; }
.feature-collage.layout-b {
  grid-template-columns: repeat(2, 1fr);
  grid-template-rows: repeat(2, 1fr);
}
.feature-collage.layout-c {
  grid-template-columns: 1.2fr 1fr 1fr;
  grid-template-rows: repeat(2, 1fr);
}
.feature-collage.layout-c .tile-1 { grid-column: 1 / span 2; }
.feature-collage.layout-d {
  grid-template-columns: repeat(3, 1fr);
  grid-template-rows: 1.2fr 1fr;
}
.feature-collage.layout-d .tile-1 { grid-row: 1 / span 2; }
.feature-collage-overlay {
  position: absolute;
  inset: 0;
}
.feature-collage-overlay.overlay-a { background: linear-gradient(125deg, rgba(9, 26, 47, 0.58), rgba(10, 93, 168, 0.35)); }
.feature-collage-overlay.overlay-b { background: linear-gradient(125deg, rgba(62, 24, 8, 0.58), rgba(199, 87, 12, 0.35)); }
.feature-collage-overlay.overlay-c { background: linear-gradient(125deg, rgba(26, 12, 56, 0.58), rgba(86, 59, 191, 0.34)); }
.feature-collage-overlay.overlay-d { background: linear-gradient(125deg, rgba(7, 46, 42, 0.58), rgba(12, 125, 97, 0.34)); }
.feature-collage-title {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: min(90%, 900px);
  margin: 0;
  text-align: center;
  line-height: 1.14;
  letter-spacing: 0.2px;
  color: #f8fbff;
  text-shadow: 0 8px 30px rgba(0, 0, 0, 0.5);
  text-wrap: balance;
  overflow-wrap: anywhere;
  padding: 0 8px;
}
.feature-collage-title.font-a { font-family: "Sora", "Plus Jakarta Sans", sans-serif; font-weight: 700; }
.feature-collage-title.font-b { font-family: "DM Serif Display", Georgia, serif; font-weight: 400; }
.feature-collage-title.font-c { font-family: "Plus Jakarta Sans", sans-serif; font-weight: 800; }
.feature-collage-title.font-d { font-family: "Sora", "Plus Jakarta Sans", sans-serif; font-weight: 600; }
.feature-collage-article {
  margin: 14px 0 26px;
  border-radius: 16px;
  box-shadow: 0 14px 28px rgba(11, 35, 68, 0.14);
}
.feature-collage-article .feature-collage-title {
  font-size: clamp(1.35rem, 4vw, 2.55rem);
}
.feature-collage-card {
  border-left: 0;
  border-right: 0;
  border-top: 0;
  border-radius: 0;
}
.feature-collage-card .feature-collage-title {
  font-size: clamp(0.88rem, 1.7vw, 1.12rem);
}
.hero-saas {
  background:
    radial-gradient(circle at 83% 12%, #ffdcae 0%, rgba(255, 220, 174, 0) 37%),
    radial-gradient(circle at 12% 88%, #d6ecff 0%, rgba(214, 236, 255, 0) 36%),
    linear-gradient(128deg, #f4f9ff, #e8f1ff 48%, #fff4e8);
}
.hero-saas-pro {
  position: relative;
  isolation: isolate;
  overflow: hidden;
  border-color: #c8d9ea;
  box-shadow: 0 22px 44px rgba(11, 35, 68, 0.11);
}
.hero-saas-pro::before {
  content: "";
  position: absolute;
  inset: -120px auto auto -120px;
  width: 340px;
  height: 340px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(12, 110, 221, 0.16), rgba(12, 110, 221, 0));
  pointer-events: none;
  z-index: -1;
}
.hero-saas-pro::after {
  content: "";
  position: absolute;
  inset: auto -120px -120px auto;
  width: 360px;
  height: 360px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(230, 126, 34, 0.16), rgba(230, 126, 34, 0));
  pointer-events: none;
  z-index: -1;
}
.hero-grid-modern, .hero-saas-grid {
  display: grid;
  gap: 20px;
  grid-template-columns: 1.3fr 1fr;
  align-items: stretch;
}
.hero-copy {
  position: relative;
}
.hero-copy p {
  margin-top: 0;
  margin-bottom: 0;
  font-size: 1.03rem;
}
.hero-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 18px;
}
.hero-pill-row {
  margin-top: 14px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.hero-pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 1px solid #c7d9ed;
  background: #f7fbffdb;
  box-shadow: 0 8px 16px rgba(13, 56, 102, 0.05);
  color: #234a73;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 700;
  padding: 6px 11px;
}
.pill-dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: linear-gradient(135deg, #0f5dbf, #35a1ff);
  box-shadow: 0 0 0 3px rgba(53, 161, 255, 0.16);
}
.button.secondary {
  background: #f4f8fd;
  color: #134e95;
  border: 1px solid #b9d0eb;
}
.button.secondary:hover {
  background: #e9f3ff;
}
.hero-stats {
  margin-top: 18px;
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.hero-stat {
  border: 1px solid #c6d8ed;
  border-radius: 12px;
  padding: 11px;
  background: #ffffffdb;
  box-shadow: 0 8px 14px rgba(15, 55, 98, 0.05);
}
.hero-stat strong {
  display: block;
  font-size: 1.18rem;
  line-height: 1.2;
}
.hero-ops-card, .hero-panel {
  border: 1px solid #c7d9ed;
  border-radius: 16px;
  padding: 18px;
  background: linear-gradient(165deg, #ffffffd9, #f6fbffde);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.75);
}
.hero-panel h3,
.ops-heading {
  margin: 0 0 8px;
  font-size: 1.1rem;
  font-weight: 800;
  color: #132c4d;
}
.hero-panel ul,
.ops-list {
  margin: 0;
  padding-left: 18px;
  color: #3b4b61;
}
.ops-list {
  margin-top: 12px;
  display: grid;
  gap: 6px;
}
.ops-metric-grid {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}
.ops-metric {
  border: 1px solid #d1dfef;
  border-radius: 11px;
  background: #fff;
  padding: 9px 10px;
}
.ops-metric strong {
  display: block;
  line-height: 1.2;
  font-size: 1rem;
  margin-bottom: 3px;
}
.ops-metric span {
  display: block;
  font-size: 0.78rem;
  color: #4e6480;
}
.hero-mini-board {
  margin-top: 12px;
  border: 1px solid #c9dced;
  border-radius: 12px;
  overflow: hidden;
  background: #ffffffd4;
}
.hero-mini-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  align-items: center;
  padding: 10px 12px;
  background: #ffffffcf;
  border-bottom: 1px solid #d8e4f1;
  font-size: 0.86rem;
}
.hero-mini-row:last-child { border-bottom: none; }
.hero-mini-row b { font-weight: 700; }
.hero-search-wrap {
  margin-top: 16px;
  padding: 10px;
  border: 1px solid #ccdded;
  border-radius: 14px;
  background: #ffffffbf;
}
.trust-strip {
  margin-top: 14px;
  border: 1px solid #d4dfeb;
  border-radius: 14px;
  background: #fff;
  padding: 12px 14px;
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  color: #39516f;
  font-size: 0.9rem;
}
.business-grid {
  margin-top: 14px;
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.business-card {
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fff;
  padding: 14px;
}
.business-card h3 {
  margin: 0 0 6px;
  font-size: 1rem;
}
.business-card p {
  margin: 0;
  color: var(--muted);
  font-size: 0.92rem;
}
.social-proof-row {
  margin-top: 12px;
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
}
.social-badge {
  border: 1px solid #d4dfeb;
  border-radius: 11px;
  background: #fff;
  padding: 10px 12px;
  color: #3d5470;
  font-size: 0.86rem;
}
.how-grid {
  margin-top: 12px;
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.how-step {
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fff;
  padding: 14px;
}
.how-step h3 {
  margin: 0 0 8px;
  font-size: 1rem;
}
.category-nav-grid {
  margin-top: 12px;
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}
.category-nav-item {
  display: block;
  border: 1px solid #d5e1ee;
  border-radius: 11px;
  background: #fafdff;
  color: #17457f;
  font-weight: 700;
  padding: 12px;
}
.testimonial-grid {
  margin-top: 12px;
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.testimonial-card {
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fff;
  padding: 14px;
}
.testimonial-card p {
  margin: 0;
  color: #334860;
}
.final-fold {
  margin-top: 18px;
  background: linear-gradient(145deg, #f3f8ff, #ffffff);
  border-color: #c1d4e8;
  box-shadow: 0 16px 32px rgba(14, 45, 81, 0.08);
}
.final-fold-grid {
  display: grid;
  gap: 14px;
  grid-template-columns: 1.3fr 1fr;
}
.final-brand-block, .final-links-block {
  border: 1px solid #d2e0ef;
  border-radius: 14px;
  padding: 20px;
  background: #fff;
}
.final-brand-block {
  background: linear-gradient(145deg, #112a49, #1a3f67);
  color: #eaf3ff;
  border-color: #294d76;
}
.final-brand-block h2, .final-links-block h3 {
  margin: 0 0 10px;
}
.final-sub {
  margin: 0;
  color: #475d79;
}
.final-brand-block .final-sub {
  color: #d0deef;
}
.final-metric-row {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}
.final-metric {
  border: 1px solid #d2e0ee;
  border-radius: 10px;
  padding: 9px 10px;
  background: #f8fbff;
}
.final-brand-block .final-metric {
  border-color: #3c6089;
  background: rgba(20, 56, 93, 0.7);
}
.final-metric strong {
  display: block;
  font-size: 0.96rem;
  line-height: 1.25;
  margin-bottom: 3px;
}
.final-metric span {
  display: block;
  font-size: 0.77rem;
  color: #4e6480;
}
.final-brand-block .final-metric strong,
.final-brand-block .final-metric span {
  color: #d7e6f8;
}
.final-actions {
  margin-top: 13px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.final-brand-block .button.secondary {
  background: rgba(234, 244, 255, 0.16);
  color: #f0f6ff;
  border-color: rgba(208, 225, 245, 0.5);
}
.final-link-grid {
  margin-top: 10px;
  display: grid;
  gap: 8px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.final-link-grid a {
  display: block;
  border: 1px solid #d2deec;
  border-radius: 10px;
  padding: 10px;
  background: #f9fcff;
  color: #1d4e89;
  font-weight: 700;
  transition: border-color 0.2s ease, transform 0.2s ease, background 0.2s ease;
}
.final-link-grid a:hover {
  transform: translateY(-1px);
  border-color: #9fc1e6;
  background: #eef6ff;
}
.final-contact {
  margin-top: 12px;
  border: 1px solid #cbdced;
  border-radius: 10px;
  padding: 10px 12px;
  background: #f7fbff;
  color: #415c7f;
}
.amz-dual-btn-container {
  display: flex;
  gap: 15px;
  justify-content: center;
  margin-top: 20px;
  flex-wrap: wrap;
}
.amz-user-review-btn {
  background: #232f3e !important;
  color: #fff !important;
  padding: 12px 20px !important;
  border-radius: 6px !important;
  text-decoration: none !important;
  font-size: 0.9rem !important;
  font-weight: 600 !important;
  flex: 1;
  min-width: 140px;
  text-align: center;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2) !important;
}
.amz-buy-btn {
  background: #ea580c !important;
  color: #fff !important;
  padding: 12px 20px !important;
  border-radius: 6px !important;
  text-decoration: none !important;
  font-size: 0.9rem !important;
  font-weight: 600 !important;
  flex: 1;
  min-width: 140px;
  text-align: center;
  box-shadow: 0 2px 5px rgba(234, 88, 12, 0.3) !important;
}
.author-card {
  margin-top: 28px;
  padding: 18px;
  display: grid;
  gap: 6px;
  background: #f8fbff;
}
.author-name { font-size: 1.08rem; font-weight: 800; }
.author-role { color: #225e9e; font-weight: 700; font-size: 0.9rem; }
.related-card {
  margin-top: 20px;
  padding: 18px;
}
.related-card h2 {
  margin-top: 0;
  margin-bottom: 12px;
  font-size: 1.15rem;
}
.related-grid {
  margin: 0;
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
}
.related-item {
  border: 1px solid var(--line);
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
}
.related-item .article-card-content {
  padding: 10px 12px 12px;
}
.related-item h3 {
  margin: 0;
  font-size: 0.92rem;
  line-height: 1.35;
}
.micro-note {
  margin-top: 16px;
  color: var(--muted);
  font-size: 0.86rem;
}
.button {
  display: inline-flex;
  justify-content: center;
  align-items: center;
  padding: 11px 16px;
  border-radius: 10px;
  border: none;
  font-weight: 700;
  font-size: 0.92rem;
  background: var(--accent);
  color: #fff;
  cursor: pointer;
}
.button:hover { background: var(--accent-strong); }
.contact-email-box {
  background: #f8fbff;
  border: 1px solid var(--line);
  border-left: 4px solid #1d4e89;
  border-radius: 12px;
  padding: 16px;
  margin: 12px 0;
}
.site-footer {
  border-top: 1px solid var(--line);
  background: #fff;
}
.site-footer-inner {
  padding: 24px 0 34px;
  display: grid;
  gap: 8px;
  color: var(--muted);
  font-size: 0.9rem;
}
.footer-columns {
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-top: 8px;
}
.footer-col h4 {
  margin: 0 0 7px;
  font-size: 0.9rem;
  color: #1a375a;
}
.footer-col a {
  display: block;
  color: #1d4e89;
  text-decoration: underline;
  margin-bottom: 4px;
}
.footer-links {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.footer-links a { color: #1d4e89; text-decoration: underline; }
@media (max-width: 860px) {
  .site-header-inner { align-items: flex-start; flex-direction: column; }
  .article-card, .content-card, .hero-card { padding: 22px; }
  .amz-pros-cons-grid { flex-direction: column !important; }
  .amz-pros-cons-col { width: 100% !important; min-width: 100% !important; }
  .amz-dual-btn-container { gap: 10px; }
  .amz-user-review-btn, .amz-buy-btn { width: 100% !important; min-width: auto !important; }
  .hero-grid-modern, .hero-saas-grid { grid-template-columns: 1fr; }
  .hero-stats { grid-template-columns: 1fr; }
  .ops-metric-grid { grid-template-columns: 1fr; }
  .business-grid { grid-template-columns: 1fr; }
  .trust-strip { gap: 10px; }
  .how-grid { grid-template-columns: 1fr; }
  .testimonial-grid { grid-template-columns: 1fr; }
  .final-fold-grid { grid-template-columns: 1fr; }
  .final-metric-row { grid-template-columns: 1fr; }
  .final-link-grid { grid-template-columns: 1fr; }
  .feature-collage-title { width: 92%; }
  .footer-columns { grid-template-columns: 1fr; }
}
"""


def normalize_site_url(url: str) -> str:
    clean = (url or "").strip()
    if not clean:
        return "https://example.pages.dev"
    if not re.match(r"^https?://", clean, flags=re.IGNORECASE):
        clean = f"https://{clean}"
    return clean.rstrip("/")


def normalize_public_path(path: str) -> str:
    raw = (path or "").strip().lstrip("/")
    if not raw:
        return ""
    path_part, sep_hash, fragment = raw.partition("#")
    path_part, sep_q, query = path_part.partition("?")
    clean_part = path_part.strip()
    if clean_part in {"", "index", "index.html"}:
        clean_part = ""
    elif clean_part.lower().endswith(".html"):
        clean_part = clean_part[:-5]

    rebuilt = clean_part
    if sep_q:
        rebuilt = f"{rebuilt}?{query}" if rebuilt else f"?{query}"
    if sep_hash:
        rebuilt = f"{rebuilt}#{fragment}" if rebuilt else f"#{fragment}"
    return rebuilt


def absolute_url(config: SiteConfig, path: str) -> str:
    public_path = normalize_public_path(path)
    if not public_path:
        return f"{config.site_url}/"
    return f"{config.site_url}/{public_path}"


def site_host(config: SiteConfig) -> str:
    parsed = urlparse(config.site_url)
    return (parsed.netloc or parsed.path).strip().lower()


def resolve_indexnow_key_location(config: SiteConfig) -> str:
    custom = (config.indexnow_key_location or "").strip()
    if not custom:
        return absolute_url(config, f"{config.indexnow_key}.txt")
    if re.match(r"^https?://", custom, flags=re.IGNORECASE):
        return custom
    return absolute_url(config, custom)


def write_indexnow_key_file(output_dir: Path, key: str) -> Path | None:
    clean_key = (key or "").strip()
    if not clean_key:
        return None
    out = output_dir / f"{clean_key}.txt"
    out.write_text(clean_key, encoding="utf-8")
    return out


def write_indexnow_url_manifest(output_dir: Path, urls: Sequence[str]) -> Path:
    out = output_dir / "indexnow-urls.txt"
    out.write_text("\n".join(urls) + ("\n" if urls else ""), encoding="utf-8")
    return out


def read_indexnow_url_manifest(output_dir: Path) -> List[str]:
    path = output_dir / "indexnow-urls.txt"
    if not path.exists():
        return []
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    return [line for line in lines if line]


def submit_indexnow(config: SiteConfig, urls: Sequence[str]) -> Dict[str, object]:
    result: Dict[str, object] = {
        "enabled": bool(config.indexnow_key),
        "submitted": False,
        "endpoint": config.indexnow_endpoint,
        "host": site_host(config),
        "key_location": "",
        "batch_count": 0,
        "submitted_url_count": 0,
        "failed_batches": 0,
        "last_status_code": 0,
        "error": "",
    }
    key = (config.indexnow_key or "").strip()
    if not key:
        result["error"] = "indexnow_key_missing"
        return result
    url_list = sorted(set(u.strip() for u in urls if u.strip()))
    if not url_list:
        result["error"] = "url_list_empty"
        return result

    key_location = resolve_indexnow_key_location(config)
    result["key_location"] = key_location
    endpoint = (config.indexnow_endpoint or "").strip() or "https://api.indexnow.org/indexnow"
    batch_size = max(1, int(config.indexnow_batch_size or 10000))
    batches = [url_list[i : i + batch_size] for i in range(0, len(url_list), batch_size)]
    result["batch_count"] = len(batches)

    for batch in batches:
        payload = {
            "host": site_host(config),
            "key": key,
            "keyLocation": key_location,
            "urlList": batch,
        }
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        req = Request(
            endpoint,
            data=data,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "programmatic-indexnow-client/1.0",
            },
            method="POST",
        )
        try:
            with urlopen(req, timeout=30) as resp:
                status_code = int(resp.getcode() or 0)
        except HTTPError as e:
            status_code = int(e.code or 0)
            result["failed_batches"] = int(result["failed_batches"]) + 1
            if not result["error"]:
                result["error"] = f"http_{status_code}"
            result["last_status_code"] = status_code
            continue
        except URLError as e:
            result["failed_batches"] = int(result["failed_batches"]) + 1
            if not result["error"]:
                result["error"] = f"url_error:{e.reason}"
            continue
        except Exception as e:  # noqa: BLE001
            result["failed_batches"] = int(result["failed_batches"]) + 1
            if not result["error"]:
                result["error"] = f"exception:{type(e).__name__}"
            continue

        result["last_status_code"] = status_code
        if status_code in (200, 202):
            result["submitted_url_count"] = int(result["submitted_url_count"]) + len(batch)
        else:
            result["failed_batches"] = int(result["failed_batches"]) + 1
            if not result["error"]:
                result["error"] = f"http_{status_code}"

    result["submitted"] = int(result["submitted_url_count"]) > 0 and int(result["failed_batches"]) == 0
    return result


def nav_items() -> List[Tuple[str, str]]:
    return [
        ("Home", "index.html"),
        ("Best Picks", "all-guides.html"),
        ("Categories", "index.html#category-navigator"),
        ("About", "about.html"),
        ("Contact", "contact.html"),
    ]


def unique_slug(keyword: str, used: Dict[str, int]) -> str:
    base = slugify(keyword)
    n = used.get(base, 0) + 1
    used[base] = n
    return base if n == 1 else f"{base}-{n}"


def keyword_tokens(keyword: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", norm(keyword))
    stop = {"for", "the", "and", "with", "best", "top", "guide", "in", "to", "of"}
    return {t for t in tokens if t not in stop and len(t) > 2}


def build_related_map(builds: Sequence[ArticleBuild], per_page: int) -> Dict[str, List[str]]:
    token_map = {b.slug: keyword_tokens(b.keyword) for b in builds}
    all_slugs = [b.slug for b in builds]
    related: Dict[str, List[str]] = {}
    for slug in all_slugs:
        scores: List[Tuple[int, str]] = []
        for other in all_slugs:
            if other == slug:
                continue
            overlap = len(token_map[slug] & token_map[other])
            if overlap > 0:
                scores.append((overlap, other))
        if scores:
            scores.sort(key=lambda x: (-x[0], x[1]))
            picks = [s for _, s in scores[: max(1, per_page)]]
        else:
            picks = [s for s in all_slugs if s != slug][: max(1, per_page)]
        related[slug] = picks
    return related


def chunked(items: Sequence[ArticleBuild], size: int) -> List[List[ArticleBuild]]:
    safe = max(1, size)
    out: List[List[ArticleBuild]] = []
    for i in range(0, len(items), safe):
        out.append(list(items[i : i + safe]))
    return out


def render_header(config: SiteConfig, current_path: str) -> str:
    current = current_path or "index.html"
    links = []
    for label, href in nav_items():
        is_guides = href == "all-guides.html" and current.startswith("all-guides")
        is_categories = href.startswith("index.html#") and current == "index.html"
        active = " active" if (current == href or is_guides or is_categories) else ""
        links.append(f"<a class='nav-link{active}' href='{esc(href)}'>{esc(label)}</a>")
    return (
        "<header class='site-header'><div class='site-header-inner'>"
        f"<a class='logo' href='index.html'><span class='logo-mark'></span><span>{esc(config.site_name)}</span></a>"
        f"<nav class='site-nav'>{''.join(links)}<a class='nav-cta' href='all-guides.html'>Get Recommendations</a></nav>"
        "</div></header>"
    )


def render_footer(config: SiteConfig) -> str:
    year = datetime.now().year
    return (
        "<footer class='site-footer'><div class='site-footer-inner'>"
        f"<div><strong>{esc(config.site_name)}</strong> publishes structured, transparent buying research built for fast decision-making.</div>"
        "<div class='footer-columns'>"
        "<div class='footer-col'><h4>Product Research</h4><a href='editorial-policy.html'>Methodology</a><a href='affiliate-disclosure.html'>Disclosure</a><a href='all-guides.html'>Best Picks</a></div>"
        "<div class='footer-col'><h4>Company</h4><a href='about.html'>About</a><a href='contact.html'>Contact</a></div>"
        "<div class='footer-col'><h4>Resources</h4><a href='all-guides.html'>Guides</a><a href='editorial-policy.html'>Scoring Method</a></div>"
        "<div class='footer-col'><h4>Legal</h4><a href='privacy-policy.html'>Privacy</a><a href='terms-of-use.html'>Terms</a><a href='affiliate-disclosure.html'>Affiliate Disclosure</a></div>"
        "</div>"
        f"<div>&copy; {year} {esc(config.site_name)}. All rights reserved.</div>"
        "</div></footer>"
    )


def render_layout(
    config: SiteConfig,
    *,
    page_title: str,
    meta_description: str,
    current_path: str,
    main_html: str,
    schema_objects: Sequence[dict] | None = None,
    og_image_url: str | None = None,
    noindex: bool = False,
) -> str:
    robots = "noindex,follow" if noindex else "index,follow"
    canonical = absolute_url(config, current_path)
    social_image = (og_image_url or "").strip() or absolute_url(config, "assets/site-logo.svg")
    schema_tags = ""
    if schema_objects:
        schema_tags = "\n".join(
            f"<script type='application/ld+json'>{json.dumps(obj, separators=(',', ':'))}</script>" for obj in schema_objects
        )
    return f"""<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>{esc(page_title)}</title>
<meta name='description' content='{esc(meta_description)}'>
<meta name='robots' content='{esc(robots)}'>
<meta property='og:type' content='website'>
<meta property='og:site_name' content='{esc(config.site_name)}'>
<meta property='og:title' content='{esc(page_title)}'>
<meta property='og:description' content='{esc(meta_description)}'>
<meta property='og:url' content='{esc(canonical)}'>
<meta property='og:image' content='{esc(social_image)}'>
<meta name='twitter:card' content='summary_large_image'>
<meta name='twitter:title' content='{esc(page_title)}'>
<meta name='twitter:description' content='{esc(meta_description)}'>
<meta name='twitter:image' content='{esc(social_image)}'>
<link rel='canonical' href='{esc(canonical)}'>
<link rel='stylesheet' href='assets/site.css'>
{schema_tags}
</head>
<body>
{render_header(config, current_path)}
<main class='page-wrap'>{main_html}</main>
{render_footer(config)}
</body>
</html>"""


def render_disclosure_block() -> str:
    return (
        "<section class='disclosure-card'>"
        "<strong>Amazon Affiliate Disclosure:</strong> "
        "As an Amazon Associate, this site may earn from qualifying purchases. "
        "Prices, ratings, and availability may change over time."
        "</section>"
    )


def render_author_box(config: SiteConfig) -> str:
    return (
        "<section class='author-card'>"
        "<div class='author-name'>Author</div>"
        f"<div class='author-name'>{esc(config.author_name)}</div>"
        f"<div class='author-role'>{esc(config.author_role)}</div>"
        f"<div>{esc(config.author_bio)}</div>"
        "<div class='micro-note'>For correction requests, use the contact page.</div>"
        "</section>"
    )


def add_heading_ids(article_html: str) -> str:
    heading_pattern = re.compile(r"<h([23])([^>]*)>(.*?)</h\1>", flags=re.IGNORECASE | re.DOTALL)
    seen: Dict[str, int] = {}

    def repl(match: re.Match[str]) -> str:
        _ = int(match.group(1))
        attrs = match.group(2) or ""
        inner = match.group(3) or ""
        plain = re.sub(r"<[^>]+>", "", inner)
        plain = re.sub(r"\s+", " ", plain).strip()
        if not plain:
            return match.group(0)
        base = slugify(plain)
        seen[base] = seen.get(base, 0) + 1
        anchor = base if seen[base] == 1 else f"{base}-{seen[base]}"
        if " id=" not in attrs.lower():
            attrs = f"{attrs} id='{esc(anchor)}'"
        return f"<h{match.group(1)}{attrs}>{inner}</h{match.group(1)}>"

    return heading_pattern.sub(repl, article_html)


def render_related_posts(
    current_slug: str,
    related_map: Dict[str, List[str]],
    build_lookup: Dict[str, ArticleBuild],
) -> str:
    picks = related_map.get(current_slug, [])
    if not picks:
        return ""
    cards = ""
    for slug in sorted(picks):
        build = build_lookup.get(slug)
        if build is None:
            continue
        title = f"Best {clean_keyword(build.keyword).title()}"
        cards += (
            "<a class='related-item' "
            f"href='{esc(slug)}.html'>"
            f"{render_feature_collage(build, context='card')}"
            f"<div class='article-card-content'><h3>{esc(title)}</h3></div>"
            "</a>"
        )
    if not cards:
        return ""
    return f"<section class='related-card'><h2>Related Guides</h2><div class='related-grid'>{cards}</div></section>"


def build_article_schema(
    config: SiteConfig,
    *,
    article_title: str,
    article_description: str,
    article_url: str,
    updated_iso: str,
    image_url: str,
    keyword: str,
    top_pick: str,
    budget_pick: str,
    premium_pick: str,
) -> List[dict]:
    article_schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": article_title,
        "description": article_description,
        "image": image_url,
        "mainEntityOfPage": {"@type": "WebPage", "@id": article_url},
        "datePublished": updated_iso,
        "dateModified": updated_iso,
        "author": {
            "@type": "Person",
            "name": config.author_name,
            "url": absolute_url(config, "about.html"),
        },
        "publisher": {
            "@type": "Organization",
            "name": config.site_name,
            "url": config.site_url,
            "logo": {
                "@type": "ImageObject",
                "url": absolute_url(config, "assets/site-logo.svg"),
                "width": 512,
                "height": 512,
            },
        },
    }
    faq_schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": f"What is the best overall choice for {keyword}?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": f"{top_pick} is generally the best all-around option for balanced performance and value.",
                },
            },
            {
                "@type": "Question",
                "name": f"Which option is good for budget buyers in {keyword}?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": f"{budget_pick} is a good starting point if your priority is lower cost with practical quality.",
                },
            },
            {
                "@type": "Question",
                "name": f"Which pick is suitable for premium needs in {keyword}?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": f"{premium_pick} is better for demanding use cases where extra performance matters.",
                },
            },
        ],
    }
    breadcrumb_schema = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "Home",
                "item": absolute_url(config, "index.html"),
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": f"Best {keyword}",
                "item": article_url,
            },
        ],
    }
    return [article_schema, faq_schema, breadcrumb_schema]


def render_article_page(
    build: ArticleBuild,
    *,
    tag: str,
    rng: random.Random,
    config: SiteConfig,
    page_copy: Dict[str, str],
    related_map: Dict[str, List[str]],
    build_lookup: Dict[str, ArticleBuild],
) -> str:
    clean_kw = clean_keyword(build.keyword)
    title = choose(rng, "meta_title", k=clean_kw.title(), y=YEAR)
    desc = choose(rng, "meta_desc", k=clean_kw)
    h1 = f"Best {clean_kw.title()} in {YEAR} - Top Picks and Complete Buying Guide"
    updated_human = datetime.now().strftime("%B %d, %Y")
    updated_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    article_feature = render_feature_collage(build, context="article")
    article_body = render_article_fragment(build.keyword, build.products, tag, rng, article_feature)
    article_body = add_heading_ids(article_body)
    primary = (build.feature_primary_image or "").strip()
    if primary.startswith("http://") or primary.startswith("https://"):
        feature_image_url = primary
    else:
        feature_image_url = absolute_url(config, primary or "assets/site-logo.svg")

    top_pick = short_title(build.products[0].product_name)
    budget_pick = short_title(build.products[1].product_name if len(build.products) > 1 else build.products[0].product_name)
    premium_pick = short_title(build.products[2].product_name if len(build.products) > 2 else build.products[0].product_name)
    article_path = f"{build.slug}.html"

    main_html = (
        "<article class='article-card'>"
        f"<nav class='breadcrumb'><a href='index.html'>Home</a><span>/</span><span>{esc(clean_kw.title())}</span></nav>"
        f"<h1>{esc(h1)}</h1>"
        f"<p class='meta-line'>Last updated: {esc(updated_human)} | Reviewed by {esc(config.author_name)}</p>"
        f"{render_disclosure_block()}"
        f"<div class='article-body'>{article_body}</div>"
        f"{render_author_box(config)}"
        f"{render_related_posts(build.slug, related_map, build_lookup)}"
        f"<p class='micro-note'>{apply_placeholders(page_copy['article_footer_note'], placeholder_context(config))}</p>"
        "</article>"
    )
    schema_objects = build_article_schema(
        config,
        article_title=h1,
        article_description=desc,
        article_url=absolute_url(config, article_path),
        updated_iso=updated_iso,
        image_url=feature_image_url,
        keyword=clean_kw,
        top_pick=top_pick,
        budget_pick=budget_pick,
        premium_pick=premium_pick,
    )
    return render_layout(
        config,
        page_title=title,
        meta_description=desc,
        current_path=article_path,
        main_html=main_html,
        schema_objects=schema_objects,
        og_image_url=feature_image_url,
    )


def first_build_for_terms(builds: Sequence[ArticleBuild], terms: Sequence[str]) -> ArticleBuild | None:
    term_set = [norm(t) for t in terms]
    for build in builds:
        kw = norm(build.keyword)
        if any(t in kw for t in term_set):
            return build
    return builds[0] if builds else None


def render_home_page(config: SiteConfig, builds: Sequence[ArticleBuild], page_copy: Dict[str, str]) -> str:
    ordered = sorted(builds, key=lambda b: norm(b.keyword))
    top_pick_count = min(len(ordered), max(6, min(config.home_cards_limit, 12)))
    visible = ordered[:top_pick_count]
    ctx = placeholder_context(config)
    total_products = sum(len(b.products) for b in ordered) or (len(ordered) * 10)
    hero_title = apply_placeholders(page_copy["home_hero_title"], ctx).strip()
    if not hero_title or hero_title == config.site_name:
        hero_title = "Find the Best Products Faster, Without Guesswork"
    hero_intro = apply_placeholders(page_copy["home_hero_intro"], ctx)

    cards = "".join(
        (
            "<a class='article-link-card article-card-item' "
            f"href='{esc(build.slug)}.html' data-title='{esc(clean_keyword(build.keyword).title())}'>"
            f"{render_feature_collage(build, context='card')}"
            "<div class='article-card-content'>"
            f"<h3>Best {esc(clean_keyword(build.keyword).title())}</h3>"
            "<p>Comparison, buying guide, FAQ and final verdict.</p>"
            "<span class='card-cta'>See Top Picks</span>"
            "</div>"
            "</a>"
        )
        for build in visible
    )
    hidden_count = max(0, len(ordered) - top_pick_count)
    hidden_note_template = page_copy["home_hidden_note_template"]
    hidden_note = f"<p class='micro-note'>{apply_placeholders(hidden_note_template, placeholder_context(config, {'hidden_count': str(hidden_count)}))}</p>" if hidden_count else ""

    preview_rows = "".join(
        f"<div class='hero-mini-row'><span>Best {esc(clean_keyword(build.keyword).title())}</span><b>{YEAR}</b></div>"
        for build in ordered[:4]
    )

    social_badges = "".join(
        f"<div class='social-badge'>{label}</div>"
        for label in [
            "Neutral comparison signals",
            "Use-case focused ranking",
            "Transparent affiliate disclosure",
            "Editorial policy aligned",
            "Reader-first guide structure",
        ]
    )

    category_items = [
        ("For Beginners", ["beginner", "starter", "new", "basic"]),
        ("For Professionals", ["pro", "professional", "heavy duty", "advanced"]),
        ("Budget Picks", ["budget", "cheap", "affordable", "value"]),
        ("Premium Picks", ["premium", "luxury", "high end", "professional"]),
        ("Outdoor / Travel", ["outdoor", "travel", "camping", "portable"]),
        ("Work / Safety", ["work", "safety", "industrial", "protection"]),
        ("Kids / Family", ["kids", "baby", "family", "children"]),
    ]
    category_links = ""
    for label, terms in category_items:
        picked = first_build_for_terms(ordered, terms)
        href = f"{picked.slug}.html" if picked else "all-guides.html"
        category_links += f"<a class='category-nav-item' href='{esc(href)}'>{esc(label)}</a>"

    featured_builds = ordered[:3]
    featured_cards = "".join(
        (
            "<a class='article-link-card' "
            f"href='{esc(build.slug)}.html'>"
            f"{render_feature_collage(build, context='card')}"
            "<div class='article-card-content'>"
            f"<h3>How to choose {esc(clean_keyword(build.keyword).title())}</h3>"
            "<p>Structured decision flow and practical shortlist logic.</p>"
            "<span class='card-cta'>Read guide</span>"
            "</div></a>"
        )
        for build in featured_builds
    )

    final_links = "\n".join(
        [
            "<a href='all-guides.html'>Best Picks</a>",
            "<a href='about.html'>About</a>",
            "<a href='contact.html'>Contact</a>",
            "<a href='affiliate-disclosure.html'>Affiliate Disclosure</a>",
            "<a href='editorial-policy.html'>Editorial Policy</a>",
            "<a href='privacy-policy.html'>Privacy Policy</a>",
            "<a href='terms-of-use.html'>Terms of Use</a>",
        ]
    )

    content = (
        "<section class='hero-card hero-saas hero-saas-pro'>"
        "<div class='hero-grid-modern'>"
        "<div class='hero-copy'>"
        f"<span class='hero-kicker'>{apply_placeholders(page_copy['home_hero_kicker'], ctx)}</span>"
        f"<h1>{esc(hero_title)}</h1>"
        f"<p>{esc(hero_intro)}</p>"
        "<div class='hero-actions'>"
        "<a class='button' href='all-guides.html'>Browse Top Picks</a>"
        "<a class='button secondary' href='editorial-policy.html'>How We Rank Products</a>"
        "</div>"
        "<div class='hero-pill-row'>"
        "<span class='hero-pill'><span class='pill-dot' aria-hidden='true'></span>Policy-first trust framework</span> "
        "<span class='hero-pill'><span class='pill-dot' aria-hidden='true'></span>Consistent comparison architecture</span> "
        "<span class='hero-pill'><span class='pill-dot' aria-hidden='true'></span>Human-readable decision flow</span>"
        "</div>"
        "<div class='hero-stats'>"
        f"<div class='hero-stat'><strong>{datetime.now().strftime('%B %Y')}</strong><span>Latest refresh cycle</span></div>"
        f"<div class='hero-stat'><strong>{len(ordered)}+</strong><span>Decision-ready guides</span></div>"
        f"<div class='hero-stat'><strong>{total_products}+</strong><span>Products benchmarked</span></div>"
        "</div>"
        "</div>"
        "<aside class='hero-ops-card'>"
        "<div class='ops-heading'>Top Picks Preview</div>"
        "<p class='micro-note' style='margin:0 0 10px;'>Shortlist snapshot before opening detailed recommendation pages.</p>"
        f"<div class='hero-mini-board'>{preview_rows}</div>"
        "<div class='ops-metric-grid'>"
        f"<div class='ops-metric'><strong>{len(ordered)}+</strong><span>Coverage clusters</span></div> "
        "<div class='ops-metric'><strong>Weekly</strong><span>Update cadence</span></div> "
        "<div class='ops-metric'><strong>Schema-ready</strong><span>Technical SEO</span></div>"
        "</div>"
        "<ul class='ops-list'>"
        "<li>Professional information architecture with clear internal linking.</li>"
        "<li>Template-based compliance layer across legal and disclosure pages.</li>"
        "<li>Fast scanning layout for shortlist-focused buyers.</li>"
        "</ul>"
        "</aside>"
        "</div>"
        f"<div class='hero-search-wrap'><input id='pageSearch' class='search-input' placeholder='{esc(apply_placeholders(page_copy['home_search_placeholder'], ctx))}' /></div>"
        "</section>"
        "<section class='content-card' style='margin-top:16px;'>"
        "<h2>Trusted By Readers Worldwide</h2>"
        "<div class='social-proof-row'>"
        f"{social_badges}"
        "</div>"
        "<div class='trust-strip'>"
        f"<span>{total_products}+ products compared</span>"
        f"<span>{len(ordered)}+ buying guides</span>"
        "<span>Updated weekly</span>"
        "</div>"
        "</section>"
        "<section class='content-card' style='margin-top:16px;'>"
        "<h2>Top Picks Today</h2>"
        f"<div class='article-grid' id='articleGrid'>{cards}</div>"
        f"{hidden_note}"
        "<script>"
        "const q=document.getElementById('pageSearch');"
        "const items=[...document.querySelectorAll('.article-card-item')];"
        "q?.addEventListener('input',()=>{const v=q.value.trim().toLowerCase();"
        "items.forEach(it=>{const t=(it.dataset.title||'').toLowerCase();it.style.display=t.includes(v)?'block':'none';});});"
        "</script>"
        "</section>"
        "<section class='content-card' style='margin-top:16px;'>"
        "<h2>How It Works</h2>"
        "<div class='how-grid'>"
        "<article class='how-step'><h3>1. Signal Collection</h3><p>We collect review quality signals and listing-level specification context.</p></article>"
        "<article class='how-step'><h3>2. Consistent Scoring</h3><p>Products are ranked using a repeatable framework focused on value and use-case fit.</p></article>"
        "<article class='how-step'><h3>3. Practical Recommendation</h3><p>Final pages prioritize clear tradeoffs, shortlist flow, and direct next actions.</p></article>"
        "</div>"
        "<p class='micro-note'><a href='editorial-policy.html'>See scoring methodology</a></p>"
        "</section>"
        "<section class='content-card' id='category-navigator' style='margin-top:16px;'>"
        "<h2>Category & Use-Case Navigator</h2>"
        f"<div class='category-nav-grid'>{category_links}</div>"
        "</section>"
        "<section class='content-card' style='margin-top:16px;'>"
        "<h2>Featured Buying Guides</h2>"
        f"<div class='article-grid'>{featured_cards}</div>"
        "</section>"
        "<section class='content-card' style='margin-top:16px;'>"
        "<h2>Reader Notes</h2>"
        "<div class='testimonial-grid'>"
        "<article class='testimonial-card'><p>&ldquo;Helped me choose in 5 minutes.&rdquo; - Reader</p></article>"
        "<article class='testimonial-card'><p>&ldquo;Clear pros/cons made it easy.&rdquo; - Subscriber</p></article>"
        "</div>"
        "</section>"
        "<section class='content-card final-fold'>"
        "<div class='final-fold-grid'>"
        "<div class='final-brand-block'>"
        "<h2>Operate With Confidence</h2>"
        "<p class='final-sub'>We run a template-first research stack so each guide ships with consistent structure, transparent disclosures, and crawl-friendly architecture.</p>"
        "<div class='final-metric-row'>"
        "<div class='final-metric'><strong>Editorial policy</strong><span>Transparent ranking model</span></div> "
        "<div class='final-metric'><strong>Affiliate clarity</strong><span>Disclosure on every article</span></div> "
        "<div class='final-metric'><strong>Fast scan UX</strong><span>Comparison-first section order</span></div>"
        "</div>"
        "<div class='final-actions'>"
        "<a class='button' href='all-guides.html'>Browse Best Picks</a>"
        "<a class='button secondary' href='about.html'>About Our Process</a>"
        "</div>"
        "</div>"
        "<div class='final-links-block'>"
        f"<h3>{apply_placeholders(page_copy['home_important_pages_title'], ctx)}</h3>"
        "<p class='final-sub'>Core business, policy, and support pages for verification and communication.</p>"
        f"<div class='final-link-grid'>{final_links}</div>"
        f"<div class='final-contact'>Need correction or update request? Email <a href='mailto:{esc(config.contact_email)}'>{esc(config.contact_email)}</a>.</div>"
        "</div>"
        "</div>"
        "</section>"
    )
    schema = [
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": config.site_name,
            "url": absolute_url(config, "index.html"),
        }
    ]
    return render_layout(
        config,
        page_title=f"{config.site_name} | Product Comparisons and Buying Guides",
        meta_description="Programmatic affiliate website with structured product comparisons, buying guides, and legal disclosures.",
        current_path="index.html",
        main_html=content,
        schema_objects=schema,
    )


def render_guides_page(
    config: SiteConfig,
    page_copy: Dict[str, str],
    page_items: Sequence[ArticleBuild],
    page_number: int,
    total_pages: int,
) -> str:
    cards = "".join(
        (
            "<a class='article-link-card' "
            f"href='{esc(build.slug)}.html'>"
            f"{render_feature_collage(build, context='card')}"
            "<div class='article-card-content'>"
            f"<h3>Best {esc(clean_keyword(build.keyword).title())}</h3>"
            f"<p>{apply_placeholders(page_copy['guides_card_cta_text'], placeholder_context(config))}</p>"
            "<span class='card-cta'>See Top Picks</span>"
            "</div>"
            "</a>"
        )
        for build in page_items
    )
    prev_link = f"all-guides-{page_number - 1}.html" if page_number > 1 else ""
    next_link = f"all-guides-{page_number + 1}.html" if page_number < total_pages else ""
    current_path = "all-guides.html" if page_number == 1 else f"all-guides-{page_number}.html"
    controls = "<div class='footer-links'>"
    if prev_link:
        controls += f"<a href='{esc(prev_link)}'>Previous</a>"
    controls += f"<span>Page {page_number} of {total_pages}</span>"
    if next_link:
        controls += f"<a href='{esc(next_link)}'>Next</a>"
    controls += "</div>"

    body = (
        "<section class='content-card'>"
        f"<h1>{apply_placeholders(page_copy['guides_index_title'], placeholder_context(config))}</h1>"
        f"<p>{apply_placeholders(page_copy['guides_index_intro'], placeholder_context(config))}</p>"
        f"{controls}"
        f"<div class='article-grid' style='margin-top:14px;'>{cards}</div>"
        f"{controls}"
        "</section>"
    )
    return render_layout(
        config,
        page_title=f"All Guides - Page {page_number} | {config.site_name}",
        meta_description=f"Browse page {page_number} of all buying guides on {config.site_name}.",
        current_path=current_path,
        main_html=body,
    )


def render_static_page(
    config: SiteConfig,
    *,
    current_path: str,
    title: str,
    description: str,
    body_html: str,
    noindex: bool = False,
) -> str:
    return render_layout(
        config,
        page_title=title,
        meta_description=description,
        current_path=current_path,
        main_html=f"<section class='content-card'>{body_html}</section>",
        noindex=noindex,
    )


def write_site_assets(output_dir: Path) -> None:
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    (assets_dir / "site.css").write_text(SITE_CSS.strip() + "\n", encoding="utf-8")
    site_logo_svg = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 512 512' role='img' aria-label='Site logo'>
<defs>
  <linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>
    <stop offset='0%' stop-color='#0b5ed7'/>
    <stop offset='100%' stop-color='#0ea5e9'/>
  </linearGradient>
</defs>
<rect width='512' height='512' rx='96' fill='url(#g)'/>
<path d='M132 170h248v42H132zM132 236h248v42H132zM132 302h168v42H132z' fill='#ffffff' opacity='0.95'/>
</svg>
"""
    (assets_dir / "site-logo.svg").write_text(site_logo_svg, encoding="utf-8")


def write_static_pages(
    output_dir: Path,
    config: SiteConfig,
    builds: Sequence[ArticleBuild],
    page_copy: Dict[str, str],
) -> List[Path]:
    pages: List[Tuple[str, str]] = []
    pages.append(("index.html", render_home_page(config, builds, page_copy)))
    ordered_builds = sorted(builds, key=lambda b: norm(b.keyword))
    guide_chunks = chunked(ordered_builds, max(1, config.guides_page_size))
    for idx, chunk in enumerate(guide_chunks, 1):
        filename = "all-guides.html" if idx == 1 else f"all-guides-{idx}.html"
        pages.append((filename, render_guides_page(config, page_copy, chunk, idx, len(guide_chunks))))

    about_html = apply_placeholders(page_copy["about_html"], placeholder_context(config))
    pages.append(
        (
            "about.html",
            render_static_page(
                config,
                current_path="about.html",
                title=f"About | {config.site_name}",
                description="Learn about our editorial method and how this affiliate website builds product comparison guides.",
                body_html=about_html,
            ),
        )
    )

    contact_html = apply_placeholders(page_copy["contact_html"], placeholder_context(config))
    pages.append(
        (
            "contact.html",
            render_static_page(
                config,
                current_path="contact.html",
                title=f"Contact | {config.site_name}",
                description="Contact the editorial team for corrections, suggestions, or business inquiries.",
                body_html=contact_html,
            ),
        )
    )

    disclosure_html = apply_placeholders(page_copy["disclosure_html"], placeholder_context(config))
    pages.append(
        (
            "affiliate-disclosure.html",
            render_static_page(
                config,
                current_path="affiliate-disclosure.html",
                title=f"Affiliate Disclosure | {config.site_name}",
                description="Understand how affiliate links work on this website.",
                body_html=disclosure_html,
            ),
        )
    )

    editorial_html = apply_placeholders(page_copy["editorial_html"], placeholder_context(config))
    pages.append(
        (
            "editorial-policy.html",
            render_static_page(
                config,
                current_path="editorial-policy.html",
                title=f"Editorial Policy | {config.site_name}",
                description="How this website selects, updates, and presents product recommendations.",
                body_html=editorial_html,
            ),
        )
    )

    privacy_html = apply_placeholders(page_copy["privacy_html"], placeholder_context(config))
    pages.append(
        (
            "privacy-policy.html",
            render_static_page(
                config,
                current_path="privacy-policy.html",
                title=f"Privacy Policy | {config.site_name}",
                description="Privacy policy for visitors and data handling practices.",
                body_html=privacy_html,
            ),
        )
    )

    terms_html = apply_placeholders(page_copy["terms_html"], placeholder_context(config))
    pages.append(
        (
            "terms-of-use.html",
            render_static_page(
                config,
                current_path="terms-of-use.html",
                title=f"Terms of Use | {config.site_name}",
                description="Terms governing use of this website and its content.",
                body_html=terms_html,
            ),
        )
    )

    out_files: List[Path] = []
    for filename, html_doc in pages:
        out = output_dir / filename
        out.write_text(html_doc, encoding="utf-8")
        out_files.append(out)
    return out_files


def write_sitemap(output_dir: Path, config: SiteConfig, pages: Sequence[str]) -> None:
    lastmod = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    unique_pages = sorted(set(pages))
    chunk_size = max(1, config.sitemap_chunk_size)

    if len(unique_pages) <= chunk_size:
        urls = []
        for page in unique_pages:
            urls.append(
                "<url>"
                f"<loc>{esc(absolute_url(config, page))}</loc>"
                f"<lastmod>{lastmod}</lastmod>"
                "</url>"
            )
        sitemap = "<?xml version='1.0' encoding='UTF-8'?>\n<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>\n" + "\n".join(urls) + "\n</urlset>\n"
        (output_dir / "sitemap.xml").write_text(sitemap, encoding="utf-8")
        return

    sitemap_files: List[str] = []
    chunk_index = 0
    for i in range(0, len(unique_pages), chunk_size):
        chunk_index += 1
        chunk = unique_pages[i : i + chunk_size]
        urls = []
        for page in chunk:
            urls.append(
                "<url>"
                f"<loc>{esc(absolute_url(config, page))}</loc>"
                f"<lastmod>{lastmod}</lastmod>"
                "</url>"
            )
        name = f"sitemap-{chunk_index}.xml"
        sitemap_files.append(name)
        sitemap = "<?xml version='1.0' encoding='UTF-8'?>\n<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>\n" + "\n".join(urls) + "\n</urlset>\n"
        (output_dir / name).write_text(sitemap, encoding="utf-8")

    entries = []
    for name in sitemap_files:
        entries.append(
            "<sitemap>"
            f"<loc>{esc(absolute_url(config, name))}</loc>"
            f"<lastmod>{lastmod}</lastmod>"
            "</sitemap>"
        )
    index_xml = "<?xml version='1.0' encoding='UTF-8'?>\n<sitemapindex xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>\n" + "\n".join(entries) + "\n</sitemapindex>\n"
    (output_dir / "sitemap.xml").write_text(index_xml, encoding="utf-8")


def write_robots(output_dir: Path, config: SiteConfig) -> None:
    robots = f"User-agent: *\nAllow: /\nSitemap: {absolute_url(config, 'sitemap.xml')}\n"
    (output_dir / "robots.txt").write_text(robots, encoding="utf-8")


def write_cloudflare_files(output_dir: Path) -> None:
    headers = (
        "/*\n"
        "  X-Content-Type-Options: nosniff\n"
        "  Referrer-Policy: strict-origin-when-cross-origin\n"
        "  X-Frame-Options: SAMEORIGIN\n"
        "\n"
        "/assets/*\n"
        "  Cache-Control: public, max-age=31536000, immutable\n"
    )
    redirects = (
        "/index.html / 301\n"
        "/:slug.html /:slug 301\n"
        "/home / 301\n"
        "/all-guides/ /all-guides.html 301\n"
        "/privacy /privacy-policy.html 301\n"
        "/terms /terms-of-use.html 301\n"
    )
    (output_dir / "_headers").write_text(headers, encoding="utf-8")
    (output_dir / "_redirects").write_text(redirects, encoding="utf-8")


def load_json_file(path: Path) -> Dict[str, object]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Config must be a JSON object: {path}")
    return data


def write_config_template(path: Path) -> None:
    template = {
        "input": "productdata.csv",
        "output": "generated_html_pages",
        "top_n": 10,
        "keywords": [],
        "tag": "yourtag-20",
        "seed": "",
        "site_name": "Buyer Verdict Hub",
        "site_url": "https://example.pages.dev",
        "author_name": "Editorial Desk",
        "author_role": "Product Research Team",
        "author_bio": "We analyze product data and structure guides to help buyers compare faster.",
        "contact_email": "hello@example.com",
        "home_cards_limit": 250,
        "guides_page_size": 500,
        "related_links_count": 6,
        "sitemap_chunk_size": 40000,
        "indexnow_key": "",
        "indexnow_key_location": "",
        "indexnow_endpoint": "https://api.indexnow.org/indexnow",
        "indexnow_submit": False,
        "indexnow_batch_size": 10000,
        "page_copy": dict(DEFAULT_PAGE_COPY),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(template, indent=2), encoding="utf-8")


def first_non_empty(*values: object, fallback: str = "") -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return fallback


def merge_settings(args: argparse.Namespace) -> Dict[str, object]:
    cfg: Dict[str, object] = {}
    if args.config_file:
        cfg_path = Path(args.config_file)
        cfg = load_json_file(cfg_path)

    merged: Dict[str, object] = dict(cfg)
    override_keys = [
        "input",
        "output",
        "top_n",
        "keywords",
        "tag",
        "seed",
        "site_name",
        "site_url",
        "author_name",
        "author_role",
        "author_bio",
        "contact_email",
        "page_content_file",
        "home_cards_limit",
        "guides_page_size",
        "related_links_count",
        "sitemap_chunk_size",
        "indexnow_key",
        "indexnow_key_location",
        "indexnow_endpoint",
        "indexnow_submit",
        "indexnow_batch_size",
    ]
    for key in override_keys:
        value = getattr(args, key, None)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        merged[key] = value
    return merged


def generate(
    csv_path: Path,
    output_dir: Path,
    top_n: int,
    keywords: Sequence[str],
    tag: str,
    seed: str | None,
    config: SiteConfig,
    page_copy: Dict[str, str],
) -> Tuple[List[Path], List[Path], Dict[str, object]]:
    grouped = load_products(csv_path)
    if not grouped:
        raise ValueError("No valid rows found in CSV.")

    requested = {norm(k) for k in keywords if k.strip()}
    output_dir.mkdir(parents=True, exist_ok=True)
    write_site_assets(output_dir)
    run_seed = seed or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    builds: List[ArticleBuild] = []
    used_slugs: Dict[str, int] = {}
    for keyword, items in sorted(grouped.items(), key=lambda kv: norm(kv[0])):
        if requested and norm(keyword) not in requested:
            continue
        picks = pick_products(items, top_n)
        if len(picks) < 3:
            continue
        builds.append(ArticleBuild(keyword=keyword, slug=unique_slug(keyword, used_slugs), products=picks))

    if not builds:
        return [], [], {}

    for build in builds:
        seed_rng = random.Random(f"{run_seed}|feature|{build.slug}")
        prepare_feature_collage(build, seed_rng)

    related_map = build_related_map(builds, config.related_links_count)
    build_lookup = {b.slug: b for b in builds}
    article_pages: List[Path] = []
    for build in builds:
        rng = random.Random(f"{run_seed}|{norm(build.keyword)}")
        html_doc = render_article_page(
            build,
            tag=tag,
            rng=rng,
            config=config,
            page_copy=page_copy,
            related_map=related_map,
            build_lookup=build_lookup,
        )
        out = output_dir / f"{build.slug}.html"
        out.write_text(html_doc, encoding="utf-8")
        article_pages.append(out)
        print(f"[ok] {build.keyword} -> {out}")

    static_pages = write_static_pages(output_dir, config, builds, page_copy)
    # Remove deprecated pages from older template versions.
    deprecated_pages = ["blog.html"]
    for name in deprecated_pages:
        old_path = output_dir / name
        if old_path.exists():
            old_path.unlink()
    all_pages = [p.name for p in article_pages + static_pages]
    write_sitemap(output_dir, config, all_pages)
    write_robots(output_dir, config)
    write_cloudflare_files(output_dir)
    all_public_urls = [absolute_url(config, name) for name in sorted(set(all_pages))]
    key_file_path = write_indexnow_key_file(output_dir, config.indexnow_key)
    manifest_path = write_indexnow_url_manifest(output_dir, all_public_urls)
    indexnow_result: Dict[str, object] = {
        "enabled": bool((config.indexnow_key or "").strip()),
        "submitted": False,
        "key_file": str(key_file_path) if key_file_path else "",
        "manifest_file": str(manifest_path),
        "url_count": len(all_public_urls),
    }
    if config.indexnow_submit and config.indexnow_key:
        indexnow_result.update(submit_indexnow(config, all_public_urls))
    return article_pages, static_pages, indexnow_result


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate static affiliate HTML pages from productdata.csv")
    p.add_argument("--config-file", default="", help="Path to site config JSON")
    p.add_argument("--write-config-template", default="", help="Write example config JSON to this path and exit")
    p.add_argument("--input", default=None, help="Input CSV file path")
    p.add_argument("--output", default=None, help="Output folder")
    p.add_argument("--top-n", type=int, default=None, help="How many top products per keyword")
    p.add_argument("--keywords", default=None, help="Comma separated keyword list (optional)")
    p.add_argument("--tag", default=None, help="Amazon affiliate tag")
    p.add_argument("--seed", default=None, help="Optional deterministic seed")
    p.add_argument("--site-name", default=None, help="Website brand name")
    p.add_argument("--site-url", default=None, help="Final deployed site URL")
    p.add_argument("--author-name", default=None, help="Author display name")
    p.add_argument("--author-role", default=None, help="Author role text")
    p.add_argument("--author-bio", default=None, help="Author bio text")
    p.add_argument("--contact-email", default=None, help="Contact email shown on contact page")
    p.add_argument("--page-content-file", default=None, help="Legacy: external page copy JSON (prefer page_copy inside config)")
    p.add_argument("--home-cards-limit", type=int, default=None, help="How many cards to show on homepage")
    p.add_argument("--guides-page-size", type=int, default=None, help="How many guides per all-guides page")
    p.add_argument("--related-links-count", type=int, default=None, help="Related links per article")
    p.add_argument("--sitemap-chunk-size", type=int, default=None, help="URLs per sitemap file before splitting")
    p.add_argument("--indexnow-key", default=None, help="IndexNow API key")
    p.add_argument("--indexnow-key-location", default=None, help="Optional public URL/path to IndexNow key file")
    p.add_argument("--indexnow-endpoint", default=None, help="IndexNow endpoint URL")
    p.add_argument("--indexnow-submit", default=None, help="Submit URLs to IndexNow after generation (true/false)")
    p.add_argument("--indexnow-batch-size", type=int, default=None, help="URLs per IndexNow POST batch")
    p.add_argument("--indexnow-submit-existing", action="store_true", help="Submit URLs from existing indexnow-urls.txt without regenerating pages")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    base = Path(__file__).resolve().parent

    if args.write_config_template:
        template_path = Path(args.write_config_template)
        if not template_path.is_absolute():
            template_path = base / template_path
        write_config_template(template_path)
        print(f"Config template written: {template_path}")
        return

    if args.config_file:
        cfg_path = Path(args.config_file)
        if not cfg_path.is_absolute():
            cfg_path = base / cfg_path
        args.config_file = str(cfg_path)

    settings = merge_settings(args)
    input_value = first_non_empty(settings.get("input"), fallback="productdata.csv")
    output_value = first_non_empty(settings.get("output"), fallback="generated_html_pages")
    input_path = Path(input_value) if Path(input_value).is_absolute() else (base / input_value)
    output_path = Path(output_value) if Path(output_value).is_absolute() else (base / output_value)

    config = SiteConfig(
        site_name=first_non_empty(settings.get("site_name"), fallback="Buyer Verdict Hub"),
        site_url=normalize_site_url(first_non_empty(settings.get("site_url"), fallback="https://example.pages.dev")),
        author_name=first_non_empty(settings.get("author_name"), fallback="Editorial Desk"),
        author_role=first_non_empty(settings.get("author_role"), fallback="Product Research Team"),
        author_bio=first_non_empty(
            settings.get("author_bio"),
            fallback="We analyze product data and structure guides to help buyers compare faster.",
        ),
        contact_email=first_non_empty(settings.get("contact_email"), fallback="hello@example.com"),
        home_cards_limit=max(1, parse_int_like(settings.get("home_cards_limit"), 250)),
        guides_page_size=max(50, parse_int_like(settings.get("guides_page_size"), 500)),
        related_links_count=max(2, parse_int_like(settings.get("related_links_count"), 6)),
        sitemap_chunk_size=max(1, parse_int_like(settings.get("sitemap_chunk_size"), 40000)),
        indexnow_key=first_non_empty(settings.get("indexnow_key"), fallback=""),
        indexnow_key_location=first_non_empty(settings.get("indexnow_key_location"), fallback=""),
        indexnow_endpoint=first_non_empty(settings.get("indexnow_endpoint"), fallback="https://api.indexnow.org/indexnow"),
        indexnow_submit=parse_bool_like(settings.get("indexnow_submit"), default=False),
        indexnow_batch_size=max(1, parse_int_like(settings.get("indexnow_batch_size"), 10000)),
    )

    if args.indexnow_submit_existing:
        urls = read_indexnow_url_manifest(output_path)
        if not urls:
            raise FileNotFoundError(
                f"IndexNow URL manifest not found or empty: {output_path / 'indexnow-urls.txt'}"
            )
        key_path = write_indexnow_key_file(output_path, config.indexnow_key)
        result = submit_indexnow(config, urls)
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "output_dir": str(output_path),
            "site_url": config.site_url,
            "config_file": str(args.config_file or ""),
            "indexnow": {
                **result,
                "url_count": len(urls),
                "key_file": str(key_path) if key_path else "",
                "manifest_file": str(output_path / "indexnow-urls.txt"),
            },
        }
        (output_path / "generation_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        if result.get("submitted"):
            print(f"IndexNow submitted: {result.get('submitted_url_count', 0)} URLs")
        else:
            print(
                "IndexNow submit failed or partial. "
                f"error={result.get('error', '')} status={result.get('last_status_code', 0)}"
            )
        return

    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    page_copy = load_page_copy(settings, base)

    keywords_raw = settings.get("keywords")
    if isinstance(keywords_raw, list):
        keywords = [clean_text_artifacts(str(x)) for x in keywords_raw if str(x).strip()]
    else:
        keywords_value = first_non_empty(keywords_raw, fallback="")
        keywords = [clean_text_artifacts(x) for x in keywords_value.split(",") if x.strip()]
    article_pages, static_pages, indexnow_result = generate(
        csv_path=input_path,
        output_dir=output_path,
        top_n=max(3, parse_int_like(settings.get("top_n"), 10)),
        keywords=keywords,
        tag=first_non_empty(settings.get("tag"), fallback=""),
        seed=first_non_empty(settings.get("seed"), fallback="") or None,
        config=config,
        page_copy=page_copy,
    )
    if not article_pages:
        print("No pages generated. Check CSV and keyword filter.")
        return

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "input_csv": str(input_path),
        "output_dir": str(output_path),
        "article_count": len(article_pages),
        "static_count": len(static_pages),
        "count_total": len(article_pages) + len(static_pages),
        "article_files": [p.name for p in article_pages],
        "static_files": [p.name for p in static_pages],
        "site_url": config.site_url,
        "config_file": str(args.config_file or ""),
        "indexnow": indexnow_result,
    }
    (output_path / "generation_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if indexnow_result.get("enabled"):
        if indexnow_result.get("submitted"):
            print(f"IndexNow submitted: {indexnow_result.get('submitted_url_count', 0)} URLs")
        elif config.indexnow_submit:
            print(
                "IndexNow submit failed or partial. "
                f"error={indexnow_result.get('error', '')} status={indexnow_result.get('last_status_code', 0)}"
            )
        else:
            print("IndexNow ready: key file + URL manifest generated (submit disabled in config).")
    print(f"Done. Generated {len(article_pages)} article pages + {len(static_pages)} site pages in {output_path}")
if __name__ == "__main__":
    main()
