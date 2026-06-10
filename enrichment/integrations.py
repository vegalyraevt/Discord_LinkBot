"""
enrichment/integrations.py - Additional platform integrations.

Handles:
  - PubMed articles (Entrez API, free, no key)
  - GitLab repos (REST API v4, free, no key for public)
  - ORCID researcher profiles (Public API v3, free, no key)
  - Zenodo records (REST API, free, no key)
  - MDN Web Docs previews (scraped meta tags)
  - Codeberg repos (Gitea API, free, no key)
  - Bitbucket repos (Atlassian API v2, free, no key for public)
"""

import re
import aiohttp

import discord
import stats


# --- PubMed ---

PUBMED_REGEX = re.compile(r'https?://pubmed\.ncbi\.nlm\.nih\.gov/(\d+)/?')


async def handle_pubmed(message: discord.Message, config: dict = None) -> bool:
    if config is None:
        config = {}
    if not config.get("enrichment", {}).get("pubmed", True):
        return False

    match = PUBMED_REGEX.search(message.content)
    if not match:
        return False

    pmid = match.group(1)
    try:
        async with aiohttp.ClientSession() as session:
            # Fetch summary
            async with session.get(
                f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
                f"?db=pubmed&id={pmid}&retmode=json",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    result = data.get("result", {}).get(pmid, {})
                    if result:
                        title = result.get("title", "Unknown")
                        authors_list = result.get("authors", [])
                        authors = ", ".join(a["name"] for a in authors_list[:4])
                        if len(authors_list) > 4:
                            authors += " et al."
                        journal = result.get("source", "Unknown")
                        pubdate = result.get("pubdate", "Unknown")
                        doi = ""
                        for aid in result.get("articleids", []):
                            if aid.get("idtype") == "doi":
                                doi = aid.get("value", "")
                                break

                        embed = discord.Embed(
                            title=title[:256],
                            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                            description=f"**Authors:** {authors}\n**Journal:** {journal}\n**Date:** {pubdate}",
                            color=discord.Color.blue(),
                        )
                        if doi:
                            embed.add_field(name="DOI", value=f"[{doi}](https://doi.org/{doi})", inline=False)
                        embed.set_footer(text="PubMed")
                        await message.reply(embed=embed, mention_author=False)
                        await stats.increment("commands_used")
    except Exception as e:
        print(f"PubMed enrichment error: {e}")
    return True


# --- GitLab ---

GITLAB_REGEX = re.compile(r'https?://gitlab\.com/([^/\s\)\]>]+/[^/\s\)\]>]+)/?(?:\?.*)?$')


async def handle_gitlab(message: discord.Message, config: dict = None) -> bool:
    if config is None:
        config = {}
    if not config.get("enrichment", {}).get("gitlab", True):
        return False

    match = GITLAB_REGEX.search(message.content)
    if not match:
        return False

    repo_path = match.group(1)
    repo_path_encoded = repo_path.replace("/", "%2F")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://gitlab.com/api/v4/projects/{repo_path_encoded}",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    name = data.get("name_with_namespace", repo_path)
                    description = data.get("description") or "No description available."
                    stars = data.get("star_count", 0)
                    forks = data.get("forks_count", 0)
                    language = data.get("language", "Unknown")
                    last_activity = data.get("last_activity_at", "")[:10]

                    embed = discord.Embed(
                        title=f"GitLab: {name}",
                        url=f"https://gitlab.com/{repo_path}",
                        description=description[:1024],
                        color=discord.Color.orange(),
                    )
                    embed.add_field(name="Stars", value=str(stars), inline=True)
                    embed.add_field(name="Forks", value=str(forks), inline=True)
                    embed.add_field(name="Language", value=language, inline=True)
                    embed.add_field(name="Last Activity", value=last_activity, inline=True)
                    embed.set_footer(text="GitLab")
                    await message.reply(embed=embed, mention_author=False)
                    await stats.increment("commands_used")
    except Exception as e:
        print(f"GitLab enrichment error: {e}")
    return True


# --- ORCID ---

ORCID_REGEX = re.compile(r'https?://orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[0-9Xx])')


async def handle_orcid(message: discord.Message, config: dict = None) -> bool:
    if config is None:
        config = {}
    if not config.get("enrichment", {}).get("orcid", True):
        return False

    match = ORCID_REGEX.search(message.content)
    if not match:
        return False

    orcid_id = match.group(1)
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"Accept": "application/json"}
            async with session.get(
                f"https://pub.orcid.org/v3.0/{orcid_id}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    person = data.get("person", {})
                    name_info = person.get("name", {})
                    given = name_info.get("given-names", {}).get("value", "")
                    family = name_info.get("family-name", {}).get("value", "")
                    full_name = f"{given} {family}".strip() or orcid_id
                    bio = person.get("biography", {}).get("content", "No bio available.")
                    activities = data.get("activities-summary", {})
                    works_count = len(activities.get("works", {}).get("group", []))
                    employment = activities.get("employments", {}).get("employment-summary", [])
                    affiliation = employment[0].get("organization", {}).get("name", "") if employment else "Unknown"

                    embed = discord.Embed(
                        title=f"ORCID: {full_name}",
                        url=f"https://orcid.org/{orcid_id}",
                        description=bio[:1024],
                        color=discord.Color.green(),
                    )
                    embed.add_field(name="Works", value=str(works_count), inline=True)
                    embed.add_field(name="Affiliation", value=affiliation[:100], inline=True)
                    embed.set_footer(text="ORCID")
                    await message.reply(embed=embed, mention_author=False)
                    await stats.increment("commands_used")
    except Exception as e:
        print(f"ORCID enrichment error: {e}")
    return True


# --- Zenodo ---

ZENODO_RECORD_REGEX = re.compile(r'https?://zenodo\.org/records?/(\d+)')
ZENODO_DOI_REGEX = re.compile(r'https?://zenodo\.org/doi/(10\.\d+/zenodo\.\d+)')


async def handle_zenodo(message: discord.Message, config: dict = None) -> bool:
    if config is None:
        config = {}
    if not config.get("enrichment", {}).get("zenodo", True):
        return False

    record_id = None
    match = ZENODO_RECORD_REGEX.search(message.content)
    if match:
        record_id = match.group(1)
    else:
        match = ZENODO_DOI_REGEX.search(message.content)
        if not match:
            return False

    api_path = f"records/{record_id}" if record_id else f"records/{match.group(1)}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://zenodo.org/api/{api_path}",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    metadata = data.get("metadata", {})
                    title = metadata.get("title", "Unknown")
                    authors = ", ".join(a.get("name", "") for a in metadata.get("creators", [])[:4])
                    if len(metadata.get("creators", [])) > 4:
                        authors += " et al."
                    doi = metadata.get("doi", "")
                    files_list = data.get("files", [])
                    file_count = len(files_list)

                    embed = discord.Embed(
                        title=title[:256],
                        url=f"https://zenodo.org/records/{data.get('id', '')}",
                        description=f"**Authors:** {authors or 'Unknown'}\n**Files:** {file_count}",
                        color=discord.Color.teal(),
                    )
                    if doi:
                        embed.add_field(name="DOI", value=f"[{doi}](https://doi.org/{doi})", inline=False)
                    embed.set_footer(text="Zenodo")
                    await message.reply(embed=embed, mention_author=False)
                    await stats.increment("commands_used")
    except Exception as e:
        print(f"Zenodo enrichment error: {e}")
    return True


# --- MDN Web Docs ---

MDN_REGEX = re.compile(r'https?://developer\.mozilla\.org/(?:en-US/)?docs/([^\s\)\]>]+)')


async def handle_mdn(message: discord.Message, config: dict = None) -> bool:
    if config is None:
        config = {}
    if not config.get("enrichment", {}).get("mdn", True):
        return False

    match = MDN_REGEX.search(message.content)
    if not match:
        return False

    url = match.group(0)
    path = match.group(1)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers={"User-Agent": "LinkBot/2.0"},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    # Scrape meta tags
                    title_match = re.search(r'<meta name="twitter:title" content="([^"]+)"', html)
                    desc_match = re.search(r'<meta name="twitter:description" content="([^"]+)"', html)
                    title = title_match.group(1) if title_match else path.rsplit("/", 1)[-1].replace("_", " ")
                    description = desc_match.group(1)[:500] if desc_match else "No description available."

                    embed = discord.Embed(
                        title=title[:256],
                        url=url,
                        description=description,
                        color=discord.Color.dark_blue(),
                    )
                    embed.set_footer(text="MDN Web Docs")
                    await message.reply(embed=embed, mention_author=False)
                    try:
                        await message.edit(suppress=True)
                    except (discord.Forbidden, discord.HTTPException):
                        pass
                    await stats.increment("commands_used")
    except Exception as e:
        print(f"MDN enrichment error: {e}")
    return True


# --- Codeberg ---

CODEBERG_REGEX = re.compile(r'https?://codeberg\.org/([^/\s\)\]>]+/[^/\s\)\]>]+)/?(?:\?.*)?$')


async def handle_codeberg(message: discord.Message, config: dict = None) -> bool:
    if config is None:
        config = {}
    if not config.get("enrichment", {}).get("codeberg", True):
        return False

    match = CODEBERG_REGEX.search(message.content)
    if not match:
        return False

    repo_path = match.group(1)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://codeberg.org/api/v1/repos/{repo_path}",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    name = data.get("full_name", repo_path)
                    description = data.get("description") or "No description available."
                    stars = data.get("stars_count", 0)
                    forks = data.get("forks_count", 0)
                    language = data.get("language", "Unknown")
                    updated = data.get("updated_at", "")[:10]

                    embed = discord.Embed(
                        title=f"Codeberg: {name}",
                        url=f"https://codeberg.org/{repo_path}",
                        description=description[:1024],
                        color=discord.Color.red(),
                    )
                    embed.add_field(name="Stars", value=str(stars), inline=True)
                    embed.add_field(name="Forks", value=str(forks), inline=True)
                    embed.add_field(name="Language", value=language, inline=True)
                    embed.add_field(name="Updated", value=updated, inline=True)
                    embed.set_footer(text="Codeberg")
                    await message.reply(embed=embed, mention_author=False)
                    await stats.increment("commands_used")
    except Exception as e:
        print(f"Codeberg enrichment error: {e}")
    return True


# --- Bitbucket ---

BITBUCKET_REGEX = re.compile(r'https?://bitbucket\.org/([^/\s\)\]>]+/[^/\s\)\]>]+)/?(?:\?.*)?$')


async def handle_bitbucket(message: discord.Message, config: dict = None) -> bool:
    if config is None:
        config = {}
    if not config.get("enrichment", {}).get("bitbucket", True):
        return False

    match = BITBUCKET_REGEX.search(message.content)
    if not match:
        return False

    repo_path = match.group(1)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.bitbucket.org/2.0/repositories/{repo_path}",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    name = data.get("full_name", repo_path)
                    description = data.get("description") or "No description available."
                    language = data.get("language", "Unknown")
                    updated = data.get("updated_on", "")[:10]

                    embed = discord.Embed(
                        title=f"Bitbucket: {name}",
                        url=f"https://bitbucket.org/{repo_path}",
                        description=description[:1024],
                        color=discord.Color.dark_blue(),
                    )
                    embed.add_field(name="Language", value=language, inline=True)
                    embed.add_field(name="Updated", value=updated, inline=True)
                    embed.set_footer(text="Bitbucket")
                    await message.reply(embed=embed, mention_author=False)
                    await stats.increment("commands_used")
    except Exception as e:
        print(f"Bitbucket enrichment error: {e}")
    return True


# --- PCPartPicker ---

PCPARTPICKER_REGEX = re.compile(
    r'https?://(?:www\.)?pcpartpicker\.com/(?:product|list)/([^\s\)\]>]+)'
)


async def handle_pcpartpicker(message: discord.Message, config: dict = None) -> bool:
    """Handle PCPartPicker links with part/build preview. Returns True if matched."""
    if config is None:
        config = {}
    if not config.get("enrichment", {}).get("pcpartpicker", True):
        return False

    match = PCPARTPICKER_REGEX.search(message.content)
    if not match:
        return False

    url = match.group(0)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers={"User-Agent": "LinkBot/2.0"},
                timeout=aiohttp.ClientTimeout(total=8)
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    title_match = re.search(r'<meta property="og:title" content="([^"]+)"', html)
                    desc_match = re.search(r'<meta property="og:description" content="([^"]+)"', html)
                    image_match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
                    title = title_match.group(1) if title_match else "PCPartPicker Build"
                    description = desc_match.group(1)[:1024] if desc_match else "No description available."

                    embed = discord.Embed(
                        title=title[:256],
                        url=url,
                        description=description,
                        color=discord.Color.from_rgb(242, 169, 0),
                    )
                    if image_match:
                        embed.set_thumbnail(url=image_match.group(1))
                    embed.set_footer(text="PCPartPicker")
                    await message.reply(embed=embed, mention_author=False)
                    await stats.increment("commands_used")
    except Exception as e:
        print(f"PCPartPicker enrichment error: {e}")
    return True


# --- CamelCamelCamel ---

CAMELCAMELCAMEL_REGEX = re.compile(
    r'https?://(?:www\.)?camelcamelcamel\.com/product/([A-Za-z0-9]+)'
)


async def handle_camelcamelcamel(message: discord.Message, config: dict = None) -> bool:
    """Handle CamelCamelCamel price tracker links with chart embed. Returns True if matched."""
    if config is None:
        config = {}
    if not config.get("enrichment", {}).get("camelcamelcamel", True):
        return False

    match = CAMELCAMELCAMEL_REGEX.search(message.content)
    if not match:
        return False

    asin = match.group(1)
    url = match.group(0)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers={"User-Agent": "LinkBot/2.0"},
                timeout=aiohttp.ClientTimeout(total=8)
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    title_match = re.search(r'<meta property="og:title" content="([^"]+)"', html)
                    desc_match = re.search(r'<meta property="og:description" content="([^"]+)"', html)
                    title = title_match.group(1) if title_match else f"Amazon Product {asin}"
                    description = desc_match.group(1)[:1024] if desc_match else "Price history chart"

                    embed = discord.Embed(
                        title=title[:256],
                        url=url,
                        description=description,
                        color=discord.Color.orange(),
                    )
                    # Embed the price history chart
                    chart_url = f"https://charts.camelcamelcamel.com/us/{asin}/amazon-new-used.png?force=1&zero=0&w=600&h=400&desired=0&legend=1&ilt=1&tp=all&fo=0&lang=en"
                    embed.set_image(url=chart_url)
                    embed.set_footer(text="CamelCamelCamel Price Tracker")
                    await message.reply(embed=embed, mention_author=False)
                    await stats.increment("commands_used")
    except Exception as e:
        print(f"CamelCamelCamel enrichment error: {e}")
    return True


# --- eBay ---

EBAY_REGEX = re.compile(
    r'https?://(?:www\.)?ebay\.(?:com|co\.uk|de|fr|ca|com\.au)/itm/(\d+)'
)


async def handle_ebay(message: discord.Message, config: dict = None) -> bool:
    """Handle eBay listing links with item preview. Returns True if matched."""
    if config is None:
        config = {}
    if not config.get("enrichment", {}).get("ebay", True):
        return False

    match = EBAY_REGEX.search(message.content)
    if not match:
        return False

    url = match.group(0)
    item_id = match.group(1)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers={"User-Agent": "LinkBot/2.0"},
                timeout=aiohttp.ClientTimeout(total=8)
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    title_match = re.search(r'<meta property="og:title" content="([^"]+)"', html)
                    desc_match = re.search(r'<meta property="og:description" content="([^"]+)"', html)
                    image_match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
                    price_match = re.search(r'<meta property="product:price:amount" content="([^"]+)"', html)
                    currency_match = re.search(r'<meta property="product:price:currency" content="([^"]+)"', html)
                    condition_match = re.search(r'<meta property="product:condition" content="([^"]+)"', html)

                    title = title_match.group(1) if title_match else f"eBay Item {item_id}"
                    # Strip " | eBay" suffix from og:title
                    if title.endswith(" | eBay"):
                        title = title[:-7].strip()
                    description = desc_match.group(1)[:1024] if desc_match else "No description available."

                    embed = discord.Embed(
                        title=title[:256],
                        url=url,
                        description=description,
                        color=discord.Color.from_rgb(229, 50, 55),
                    )
                    if price_match:
                        price = price_match.group(1)
                        currency = currency_match.group(1) if currency_match else "USD"
                        embed.add_field(name="Price", value=f"{currency} ${price}", inline=True)
                    if condition_match:
                        # eBay encodes condition as enumerations like 'new', 'used', etc.
                        condition = condition_match.group(1).replace("_", " ").title()
                        embed.add_field(name="Condition", value=condition, inline=True)
                    if image_match:
                        embed.set_thumbnail(url=image_match.group(1))
                    embed.set_footer(text="eBay")
                    await message.reply(embed=embed, mention_author=False)
                    await stats.increment("commands_used")
    except Exception as e:
        print(f"eBay enrichment error: {e}")
    return True
