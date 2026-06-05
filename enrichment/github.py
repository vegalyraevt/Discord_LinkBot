"""
enrichment.github.py - GitHub link enrichment.

Handles:
  - Code snippets from blob URLs with line numbers (#L10-L20)
  - Repository info (stars, forks, language)
  - User profiles (bio, followers, recent repos)
  - Gist embeds (Phase 10e)
"""

import re
import os
import aiohttp

import discord
import stats


# --- GitHub Patterns ---

GITHUB_BLOB_REGEX = re.compile(
    r'https?://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+?)#L(\d+)(?:-L(\d+))?'
)
GITHUB_REPO_REGEX = re.compile(
    r'https?://github\.com/([^/]+)/([^/]+)/?$'
)
GITHUB_USER_REGEX = re.compile(
    r'https?://github\.com/([^/]+)/?$'
)

GITHUB_LANG_MAP = {
    '.py': 'python', '.js': 'javascript', '.ts': 'typescript', '.jsx': 'jsx',
    '.tsx': 'tsx', '.java': 'java', '.c': 'c', '.cpp': 'cpp', '.h': 'h',
    '.cs': 'csharp', '.go': 'go', '.rs': 'rust', '.rb': 'ruby', '.php': 'php',
    '.swift': 'swift', '.kt': 'kotlin', '.lua': 'lua', '.r': 'r',
    '.sql': 'sql', '.html': 'html', '.css': 'css', '.scss': 'scss',
    '.json': 'json', '.xml': 'xml', '.yaml': 'yaml', '.yml': 'yaml',
    '.toml': 'toml', '.md': 'markdown', '.sh': 'bash', '.bash': 'bash',
    '.ps1': 'powershell', '.dockerfile': 'dockerfile',
}


async def handle_github_blob(message: discord.Message) -> bool:
    """Handle GitHub blob URLs with line numbers. Returns True if handled."""
    match = GITHUB_BLOB_REGEX.search(message.content)
    if not match:
        return False

    user, repo, branch, file_path = match.group(1), match.group(2), match.group(3), match.group(4)
    start_line = int(match.group(5))
    end_line = int(match.group(6)) if match.group(6) else start_line
    raw_url = f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{file_path}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(raw_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    lines = text.splitlines()
                    start_line = max(1, start_line)
                    end_line = min(len(lines), end_line)
                    snippet = '\n'.join(lines[start_line - 1:end_line])
                    ext = os.path.splitext(file_path)[1].lower()
                    lang = GITHUB_LANG_MAP.get(ext, '')
                    header = (
                        f"📄 `{file_path}` (L{start_line}"
                        + (f"-L{end_line})" if start_line != end_line else ")")
                    )
                    code_block = f"{header}\n```{lang}\n{snippet}\n```"
                    if len(code_block) > 2000:
                        code_block = f"{header}\n```{lang}\n{snippet[:1900]}\n... (truncated)\n```"
                    if len(code_block) <= 2000:
                        await message.reply(code_block, mention_author=False)
                    else:
                        await message.reply(f"{header}\n⚠️ Snippet too large to display.", mention_author=False)
                    await stats.increment("github_snippets")
    except Exception as e:
        print(f"❌ Failed to fetch GitHub snippet: {e}")
    return True


async def handle_github_repo(message: discord.Message) -> bool:
    """Handle GitHub bare repository URLs. Returns True if handled."""
    match = GITHUB_REPO_REGEX.search(message.content)
    if not match:
        return False

    user, repo = match.group(1), match.group(2)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.github.com/repos/{user}/{repo}",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    repo_data = await resp.json(content_type=None)
                    description = repo_data.get('description') or 'No description available.'
                    stars = repo_data.get('stargazers_count', 0)
                    forks = repo_data.get('forks_count', 0)
                    language = repo_data.get('language') or 'Unknown'
                    pushed_at = repo_data.get('pushed_at', '')
                    repo_url = repo_data.get('html_url', f"https://github.com/{user}/{repo}")
                    last_updated = pushed_at.split('T')[0] if pushed_at else 'Never'

                    embed = discord.Embed(
                        title=f"📁 {user}/{repo}",
                        description=description,
                        color=discord.Color.dark_theme(),
                        url=repo_url
                    )
                    embed.add_field(name="⭐ Stars", value=str(stars), inline=True)
                    embed.add_field(name="🍴 Forks", value=str(forks), inline=True)
                    embed.add_field(name="💻 Language", value=language, inline=True)
                    embed.add_field(name="📅 Last Updated", value=last_updated, inline=True)
                    embed.set_footer(text="GitHub")
                    await message.reply(embed=embed, mention_author=False)
                    await stats.increment("github_repos")
    except Exception as e:
        print(f"❌ Failed to fetch GitHub repo info: {e}")
    return True


async def handle_github_user(message: discord.Message) -> bool:
    """
    Handle GitHub user profile URLs.
    Must be checked AFTER blob and repo handlers.
    Returns True if handled.
    """
    if GITHUB_REPO_REGEX.search(message.content) or GITHUB_BLOB_REGEX.search(message.content):
        return False

    match = GITHUB_USER_REGEX.search(message.content)
    if not match:
        return False

    username = match.group(1)
    profile_url = f"https://github.com/{username}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.github.com/users/{username}",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    user_data = await resp.json(content_type=None)
                    avatar_url = user_data.get('avatar_url', '')
                    display_name = user_data.get('name') or username
                    bio = user_data.get('bio') or 'No bio available.'
                    public_repos = user_data.get('public_repos', 0)
                    followers = user_data.get('followers', 0)

                    recent_repos_str = 'N/A'
                    async with session.get(
                        f"https://api.github.com/users/{username}/repos?sort=pushed&per_page=3",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as repos_resp:
                        if repos_resp.status == 200:
                            repos_data = await repos_resp.json(content_type=None)
                            recent_repos_str = '\n'.join(
                                f"`{r['name']}`" for r in repos_data
                            ) or 'No public repos.'

                    embed = discord.Embed(
                        title=f"GitHub: {display_name}",
                        description=bio,
                        color=discord.Color.dark_theme(),
                        url=profile_url
                    )
                    if avatar_url:
                        embed.set_thumbnail(url=avatar_url)
                    embed.add_field(name="👥 Followers", value=str(followers), inline=True)
                    embed.add_field(name="📦 Public Repos", value=str(public_repos), inline=True)
                    embed.add_field(name="🕐 Recent Activity", value=recent_repos_str, inline=False)
                    embed.set_footer(text="GitHub")
                    await message.reply(embed=embed, mention_author=False)
                    await stats.increment("github_profiles")
    except Exception as e:
        print(f"❌ Failed to fetch GitHub user profile: {e}")
    return True
