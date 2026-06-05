"""
enrichment.academic.py - Academic and developer enrichment.

Handles:
  - DOI papers via Crossref API (free, no API key)
  - arXiv papers via arXiv API (free, no API key)
  - npm packages via npm registry (free, no API key)
  - PyPI packages via PyPI JSON API (free, no API key)
  - Stack Overflow questions via Stack Exchange API (free, no API key)
  - GitHub Gist via GitHub API (free)
"""

import re
import os
import aiohttp

import discord
import stats


# --- DOI (Crossref) ---

DOI_REGEX = re.compile(r'https?://(?:dx\.)?doi\.org/(10\.[^\s\)\]>]+)')


async def handle_doi(message: discord.Message, config: dict = None) -> bool:
    """Handle DOI links with paper preview. Returns True if matched."""
    if config is None:
        config = {}
    if not config.get("enrichment", {}).get("doi", True):
        return False

    match = DOI_REGEX.search(message.content)
    if not match:
        return False

    doi = match.group(1)
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"Accept": "application/json"}
            async with session.get(
                f"https://api.crossref.org/works/{doi}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    msg = data.get("message", {})
                    title = (msg.get("title") or ["Unknown"])[0]
                    authors_list = msg.get("author", [])
                    authors = ", ".join(
                        f"{a.get('given', '')} {a.get('family', '')}".strip()
                        for a in authors_list[:5]
                    )
                    if len(authors_list) > 5:
                        authors += f" et al."
                    journal = (msg.get("container-title") or ["Unknown"])[0]
                    year = msg.get("published-print", {}).get("date-parts", [[None]])[0][0]
                    year_str = str(year) if year else "N/A"

                    embed = discord.Embed(
                        title=title[:256],
                        url=f"https://doi.org/{doi}",
                        description=f"**Authors:** {authors}\n**Journal:** {journal}\n**Year:** {year_str}",
                        color=discord.Color.teal(),
                    )
                    embed.set_footer(text="Crossref • DOI")
                    await message.reply(embed=embed, mention_author=False)
                    await stats.increment("doi_papers")
    except Exception as e:
        print(f"❌ DOI enrichment error: {e}")
    return True


# --- arXiv ---

ARXIV_REGEX = re.compile(r'https?://arxiv\.org/abs/([^\s\)\]>]+)')


async def handle_arxiv(message: discord.Message, config: dict = None) -> bool:
    """Handle arXiv links with paper preview. Returns True if matched."""
    if config is None:
        config = {}
    if not config.get("enrichment", {}).get("arxiv", True):
        return False

    match = ARXIV_REGEX.search(message.content)
    if not match:
        return False

    paper_id = match.group(1).rstrip("v0123456789")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://export.arxiv.org/api/query?id_list={paper_id}&max_results=1",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    # Quick XML parsing (avoid heavy dependency)
                    title_match = re.search(r'<title>(.+?)</title>', text)
                    summary_match = re.search(r'<summary>(.+?)</summary>', text, re.DOTALL)
                    author_matches = re.findall(r'<name>(.+?)</name>', text)
                    category_matches = re.findall(r'category term="([^"]+)"', text)

                    title_text = title_match.group(1).strip() if title_match else paper_id
                    summary_text = summary_match.group(1).strip()[:500] if summary_match else "No abstract available."
                    authors = ", ".join(author_matches[:5])
                    if len(author_matches) > 5:
                        authors += " et al."
                    categories = ", ".join(sorted(set(category_matches[:5])))

                    embed = discord.Embed(
                        title=title_text[:256],
                        url=f"https://arxiv.org/abs/{paper_id}",
                        description=(
                            f"**Authors:** {authors}\n"
                            f"**Categories:** {categories}\n\n"
                            f"{summary_text}"
                        )[:1024],
                        color=discord.Color.dark_teal(),
                    )
                    embed.set_footer(text="arXiv")
                    await message.reply(embed=embed, mention_author=False)
                    await stats.increment("arxiv_papers")
    except Exception as e:
        print(f"❌ arXiv enrichment error: {e}")
    return True


# --- npm ---

NPM_REGEX = re.compile(r'https?://(?:www\.)?npmjs\.com/package/([^/\s\)\]>]+)')


async def handle_npm(message: discord.Message, config: dict = None) -> bool:
    """Handle npm package links with info embed. Returns True if matched."""
    if config is None:
        config = {}
    if not config.get("enrichment", {}).get("npm", True):
        return False

    match = NPM_REGEX.search(message.content)
    if not match:
        return False

    package_name = match.group(1)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://registry.npmjs.org/{package_name}/latest",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    name = data.get("name", package_name)
                    version = data.get("version", "unknown")
                    description = data.get("description", "No description.")
                    license_type = data.get("license", "Unknown")

                    embed = discord.Embed(
                        title=f"📦 {name} v{version}",
                        url=f"https://www.npmjs.com/package/{package_name}",
                        description=description[:1024],
                        color=discord.Color.red(),
                    )
                    embed.add_field(name="📜 License", value=license_type, inline=True)
                    embed.set_footer(text="npm Registry")
                    await message.reply(embed=embed, mention_author=False)
                    await stats.increment("npm_packages")
    except Exception as e:
        print(f"❌ npm enrichment error: {e}")
    return True


# --- PyPI ---

PYPI_REGEX = re.compile(r'https?://pypi\.org/project/([^/\s\)\]>]+)')


async def handle_pypi(message: discord.Message, config: dict = None) -> bool:
    """Handle PyPI package links with info embed. Returns True if matched."""
    if config is None:
        config = {}
    if not config.get("enrichment", {}).get("pypi", True):
        return False

    match = PYPI_REGEX.search(message.content)
    if not match:
        return False

    package_name = match.group(1)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://pypi.org/pypi/{package_name}/json",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    info = data.get("info", {})
                    name = info.get("name", package_name)
                    version = info.get("version", "unknown")
                    summary = info.get("summary", "No description.")
                    license_type = info.get("license", "Unknown")
                    python_req = info.get("requires_python", "N/A")

                    embed = discord.Embed(
                        title=f"🐍 {name} v{version}",
                        url=f"https://pypi.org/project/{package_name}",
                        description=summary[:1024],
                        color=discord.Color.blue(),
                    )
                    embed.add_field(name="📜 License", value=license_type, inline=True)
                    embed.add_field(name="🐍 Python", value=python_req or "N/A", inline=True)
                    embed.set_footer(text="PyPI")
                    await message.reply(embed=embed, mention_author=False)
                    await stats.increment("pypi_packages")
    except Exception as e:
        print(f"❌ PyPI enrichment error: {e}")
    return True


# --- Stack Overflow ---

STACKOVERFLOW_REGEX = re.compile(r'https?://stackoverflow\.com/questions/(\d+)')


async def handle_stackoverflow(message: discord.Message, config: dict = None) -> bool:
    """Handle Stack Overflow question links with preview. Returns True if matched."""
    if config is None:
        config = {}
    if not config.get("enrichment", {}).get("stack_overflow", True):
        return False

    match = STACKOVERFLOW_REGEX.search(message.content)
    if not match:
        return False

    question_id = match.group(1)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.stackexchange.com/2.3/questions/{question_id}"
                f"?site=stackoverflow&filter=withbody",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    items = data.get("items", [])
                    if items:
                        q = items[0]
                        title = q.get("title", "Unknown")
                        score = q.get("score", 0)
                        answer_count = q.get("answer_count", 0)
                        tags = ", ".join(q.get("tags", [])[:5])
                        is_answered = q.get("is_answered", False)

                        embed = discord.Embed(
                            title=title[:256],
                            url=f"https://stackoverflow.com/questions/{question_id}",
                            color=discord.Color.orange(),
                        )
                        embed.add_field(name="⭐ Score", value=str(score), inline=True)
                        embed.add_field(name="💬 Answers", value=str(answer_count), inline=True)
                        embed.add_field(name="✅ Answered", value="Yes" if is_answered else "No", inline=True)
                        if tags:
                            embed.add_field(name="🏷️ Tags", value=tags, inline=False)
                        embed.set_footer(text="Stack Overflow")
                        await message.reply(embed=embed, mention_author=False)
                        await stats.increment("stack_overflow_enrichments")
    except Exception as e:
        print(f"❌ Stack Overflow enrichment error: {e}")
    return True


# --- GitHub Gist ---

GIST_REGEX = re.compile(r'https?://gist\.github\.com/([^/\s\)\]>]+/[a-f0-9]+)')


async def handle_github_gist(message: discord.Message, config: dict = None) -> bool:
    """Handle GitHub Gist links with code preview. Returns True if matched."""
    if config is None:
        config = {}
    if not config.get("enrichment", {}).get("github_gist", True):
        return False

    match = GIST_REGEX.search(message.content)
    if not match:
        return False

    gist_id = match.group(1)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.github.com/gists/{gist_id.split('/')[-1]}",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    description = data.get("description") or "No description."
                    files = data.get("files", {})
                    file_list = "\n".join(
                        f"• `{fname}` ({fdata.get('language', 'text')})"
                        for fname, fdata in list(files.items())[:10]
                    )
                    if len(files) > 10:
                        file_list += f"\n*...and {len(files) - 10} more files*"

                    embed = discord.Embed(
                        title=f"📝 Gist: {description[:256]}",
                        url=f"https://gist.github.com/{gist_id}",
                        description=file_list[:1024] or "No files found.",
                        color=discord.Color.dark_theme(),
                    )
                    embed.set_footer(text="GitHub Gist")
                    await message.reply(embed=embed, mention_author=False)
                    await stats.increment("github_gists")
    except Exception as e:
        print(f"❌ GitHub Gist enrichment error: {e}")
    return True
