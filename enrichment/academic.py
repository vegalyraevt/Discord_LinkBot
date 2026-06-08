"""
enrichment.academic.py - Academic and developer enrichment.

Handles:
  - DOI papers via Crossref API (free, no API key)
  - arXiv papers via arXiv API (free, no API key)
  - npm packages via npm registry (free, no API key)
  - PyPI packages via PyPI JSON API (free, no API key)
  - Stack Overflow questions via Stack Exchange API (free, no API key)
  - GitHub Gist via GitHub API (free)
  - LaTeX formula rendering via QuickLaTeX (free, no API key)
"""

import re
import os
import aiohttp
from urllib.parse import quote

import discord
import stats


# --- DOI (Crossref) ---

DOI_REGEX = re.compile(r'https?://(?:dx\.)?doi\.org/(10\.[^\s\)\]>]+)')


async def handle_doi(message: discord.Message, config: dict = None) -> bool:
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
                        authors += " et al."
                    journal = (msg.get("container-title") or ["Unknown"])[0]
                    year = msg.get("published-print", {}).get("date-parts", [[None]])[0][0]
                    year_str = str(year) if year else "N/A"

                    embed = discord.Embed(
                        title=title[:256],
                        url=f"https://doi.org/{doi}",
                        description=f"**Authors:** {authors}\n**Journal:** {journal}\n**Year:** {year_str}",
                        color=discord.Color.teal(),
                    )
                    embed.set_footer(text="Crossref / DOI")
                    await message.reply(embed=embed, mention_author=False)
                    await stats.increment("doi_papers")
    except Exception as e:
        print(f"DOI enrichment error: {e}")
    return True


# --- arXiv ---

ARXIV_REGEX = re.compile(r'https?://arxiv\.org/abs/([^\s\)\]>]+)')


async def handle_arxiv(message: discord.Message, config: dict = None) -> bool:
    """Handle arXiv links with paper preview. Returns True if matched."""
    if config is None:
        config = {}

    enrichment = config.get("enrichment", {})
    if isinstance(enrichment, dict) and not enrichment.get("arxiv", True):
        return False

    match = ARXIV_REGEX.search(message.content)
    if not match:
        return False

    raw_id = match.group(1)
    # Strip version suffix: arxiv.org/abs/2605.19376v1 -> 2605.19376
    paper_id = re.sub(r"v\d+$", "", raw_id)
    print(f"arXiv match: {raw_id} -> paper_id: {paper_id}")

    try:
        async with aiohttp.ClientSession() as session:
            api_url = f"https://export.arxiv.org/api/query?id_list={paper_id}&max_results=1"
            async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                print(f"arXiv API status: {resp.status}")
                if resp.status == 200:
                    text = await resp.text()
                    # Parse XML response
                    # First <title> is feed title (arXiv API response), second is paper title
                    title_matches = re.findall(r'<title>(.+?)</title>', text)
                    paper_title = title_matches[1].strip() if len(title_matches) > 1 else (title_matches[0].strip() if title_matches else paper_id)
                    summary_match = re.search(r'<summary>(.+?)</summary>', text, re.DOTALL)
                    author_matches = re.findall(r'<name>(.+?)</name>', text)
                    category_matches = re.findall(r'category term="([^"]+)"', text)
                    published_match = re.search(r'<published>(.+?)</published>', text)
                    updated_match = re.search(r'<updated>(.+?)</updated>', text)
                    doi_match = re.search(r'<arxiv:doi>(.+?)</arxiv:doi>', text)
                    journal_match = re.search(r'<arxiv:journal_ref>(.+?)</arxiv:journal_ref>', text)
                    primary_cat_match = re.search(r'<arxiv:primary_category[^>]*term="([^"]+)"', text)

                    summary_text = summary_match.group(1).strip()[:400] if summary_match else "No abstract available."
                    authors = ", ".join(author_matches[:4])
                    if len(author_matches) > 4:
                        authors += " et al."
                    categories = ", ".join(sorted(set(category_matches[:5])))
                    pub_date = published_match.group(1)[:10] if published_match else "Unknown"
                    primary_cat = primary_cat_match.group(1) if primary_cat_match else (categories.split(",")[0] if categories else "N/A")
                    journal_ref = journal_match.group(1) if journal_match else ""

                    # Build a clean embed with inline fields like Steam format
                    embed = discord.Embed(
                        title=paper_title[:256],
                        url=f"https://arxiv.org/abs/{paper_id}",
                        description=summary_text,
                        color=discord.Color.dark_teal(),
                    )
                    embed.add_field(name="Authors", value=authors or "Unknown", inline=True)
                    embed.add_field(name="Primary Category", value=primary_cat, inline=True)
                    embed.add_field(name="Published", value=pub_date, inline=True)
                    if journal_ref:
                        embed.add_field(name="Journal Reference", value=journal_ref[:100], inline=False)
                    if doi_match:
                        doi_val = doi_match.group(1)
                        embed.add_field(name="DOI", value=f"[{doi_val}](https://doi.org/{doi_val})", inline=False)
                    embed.set_footer(text=f"arXiv {'|'.join(categories.split(', ')[:3])}")
                    await message.reply(embed=embed, mention_author=False)
                    # Suppress Discord's own link preview
                    try:
                        await message.edit(suppress=True)
                    except (discord.Forbidden, discord.HTTPException):
                        pass
                    await stats.increment("arxiv_papers")
                else:
                    print(f"arXiv API returned {resp.status}")
    except Exception as e:
        print(f"arXiv enrichment error: {e}")
    return True


# --- npm ---

NPM_REGEX = re.compile(r'https?://(?:www\.)?npmjs\.com/package/([^/\s\)\]>]+)')


async def handle_npm(message: discord.Message, config: dict = None) -> bool:
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
                        title=f"npm: {name} v{version}",
                        url=f"https://www.npmjs.com/package/{package_name}",
                        description=description[:1024],
                        color=discord.Color.red(),
                    )
                    embed.add_field(name="License", value=license_type, inline=True)
                    embed.set_footer(text="npm Registry")
                    await message.reply(embed=embed, mention_author=False)
                    await stats.increment("npm_packages")
    except Exception as e:
        print(f"npm enrichment error: {e}")
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
                        title=f"PyPI: {name} v{version}",
                        url=f"https://pypi.org/project/{package_name}",
                        description=summary[:1024],
                        color=discord.Color.blue(),
                    )
                    embed.add_field(name="License", value=license_type, inline=True)
                    embed.add_field(name="Python", value=python_req or "N/A", inline=True)
                    embed.set_footer(text="PyPI")
                    await message.reply(embed=embed, mention_author=False)
                    await stats.increment("pypi_packages")
    except Exception as e:
        print(f"PyPI enrichment error: {e}")
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
                        embed.add_field(name="Score", value=str(score), inline=True)
                        embed.add_field(name="Answers", value=str(answer_count), inline=True)
                        embed.add_field(name="Answered", value="Yes" if is_answered else "No", inline=True)
                        if tags:
                            embed.add_field(name="Tags", value=tags, inline=False)
                        embed.set_footer(text="Stack Overflow")
                        await message.reply(embed=embed, mention_author=False)
                        await stats.increment("stack_overflow_enrichments")
    except Exception as e:
        print(f"Stack Overflow enrichment error: {e}")
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
                        f"- `{fname}` ({fdata.get('language', 'text')})"
                        for fname, fdata in list(files.items())[:10]
                    )
                    if len(files) > 10:
                        file_list += f"\n*...and {len(files) - 10} more files*"

                    embed = discord.Embed(
                        title=f"Gist: {description[:256]}",
                        url=f"https://gist.github.com/{gist_id}",
                        description=file_list[:1024] or "No files found.",
                        color=discord.Color.dark_theme(),
                    )
                    embed.set_footer(text="GitHub Gist")
                    await message.reply(embed=embed, mention_author=False)
                    await stats.increment("github_gists")
    except Exception as e:
        print(f"GitHub Gist enrichment error: {e}")
    return True


# --- LaTeX Formula Rendering (QuickLaTeX) ---

LATEX_URL_REGEX = re.compile(r'https?://quicklatex\.com/cache3/[^\s\)\]>]+')
LATEX_INLINE_REGEX = re.compile(r'\$\$(.+?)\$\$', re.DOTALL)  # $$ only


async def handle_latex(message: discord.Message, config: dict = None) -> bool:
    """
    Handle LaTeX formula rendering.
    Works with:
      - quicklatex.com cache URLs (already-rendered images)
      - Inline LaTeX: $$x^2+y^2=1$$ (double dollar delimiters only)
    Renders formulas as PNG images using QuickLaTeX API.
    """
    if config is None:
        config = {}
    if not config.get("enrichment", {}).get("latex", True):
        return False

    # Check for QuickLaTeX cache URLs first
    ql_match = LATEX_URL_REGEX.search(message.content)
    if ql_match:
        embed = discord.Embed(
            description="Rendered formula:",
            color=discord.Color.dark_theme(),
        )
        embed.set_image(url=ql_match.group(0))
        embed.set_footer(text="QuickLaTeX")
        await message.reply(embed=embed, mention_author=False)
        try:
            await message.edit(suppress=True)
        except (discord.Forbidden, discord.HTTPException):
            pass
        return True

    # Check for inline LaTeX $$ delimiters
    latex_match = LATEX_INLINE_REGEX.search(message.content)
    if not latex_match:
        return False

    # Extract formula from $$...$$ (group 1) or $...$ (group 2, legacy)
    formula = latex_match.group(1)  # $$ only, group 1 is inner content
    if not formula or len(formula.strip()) < 2:
        return False

    print(f"LaTeX formula detected: {formula.strip()[:80]}")

    # Render via QuickLaTeX API (POST with proper preamble)
    try:
        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            form.add_field("formula", formula.strip())
            form.add_field("fsize", "20px")
            form.add_field("fcolor", "000000")
            form.add_field("mode", "1")
            form.add_field("bcolor", "FFFFFF")
            form.add_field("out", "1")
            form.add_field("preamble", r"\usepackage{amsmath}\usepackage{amssymb}")
            async with session.post(
                "https://www.quicklatex.com/latex3.f",
                data=form,
                timeout=aiohttp.ClientTimeout(total=8)
            ) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    print(f"QuickLaTeX response: {text[:100]}")
                    # Response: 0 url or 1 error_line on first line
                    # Split by newline (either \n or \r\n)
                    lines = text.strip().replace('\r', '').split('\n')
                    if lines and lines[0].startswith("0") and len(lines) >= 2:
                        image_url = lines[1].strip().split(' ')[0]  # URL is first word, rest is dimensions
                        embed = discord.Embed(
                            description=f"**Formula:** `{formula.strip()[:200]}`",
                            color=discord.Color.dark_theme(),
                        )
                        embed.set_image(url=image_url)
                        embed.set_footer(text="Rendered via QuickLaTeX")
                        await message.reply(embed=embed, mention_author=False)
                        try:
                            await message.edit(suppress=True)
                        except (discord.Forbidden, discord.HTTPException):
                            pass
                        return True
                    else:
                        print(f"QuickLaTeX error: {text.strip()[:100]}")
    except Exception as e:
        print(f"LaTeX rendering error: {e}")
    return True
