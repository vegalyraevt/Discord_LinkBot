"""
enrichment.storefronts.py - E-commerce and media storefront enrichment.

Handles:
  - Steam game info (price, reviews, cheapshark, player count)
  - Steam developer/publisher search
  - Amazon product info (title, price, specs, camelcamelcamel)
  - IMDb movie info (OMDb API)
"""

import os
import re
import json as _json
import asyncio
import aiohttp
from urllib.parse import quote, unquote

import discord
from bs4 import BeautifulSoup

import stats


OMDB_API_KEY = os.getenv('OMDB_API_KEY', '')

# --- Steam ---

STEAM_URL_REGEX = re.compile(r'https?://store\.steampowered\.com/app/(\d+)')
STEAM_DEV_REGEX = re.compile(
    r'https?://store\.steampowered\.com/search/[^?\s]*\?[^\s\)\]>]*?\b(developer|publisher)=([^&\s\)\]>]+)'
)

# --- Amazon ---

AMAZON_URL_REGEX = re.compile(
    r'https?://(?:www\.)?amazon\.[a-z.]{2,6}/(?:[^\s]*?/)?(?:dp|gp/product)/([A-Z0-9]{10})[^\s\)\]>]*'
)

# --- IMDb ---

IMDB_URL_REGEX = re.compile(r'https?://(?:www\.)?imdb\.com/title/(tt\d+)')


# ===== Steam Game Inspector =====

async def handle_steam_game(message: discord.Message) -> bool:
    """Handle Steam store app URLs. Returns True if handled."""
    match = STEAM_URL_REGEX.search(message.content)
    if not match:
        return False

    app_id = match.group(1)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://store.steampowered.com/api/appdetails?appids={app_id}",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status != 200:
                    return True
                data = await resp.json(content_type=None)
                app_data = data.get(str(app_id), {})
                if not app_data.get('success'):
                    return True
                info = app_data['data']
                name = info.get('name', 'Unknown')
                price_info = info.get('price_overview')
                steam_price_display = price_info['final_formatted'] if price_info else 'Free'
                steam_price = (price_info.get('final', 0) / 100) if price_info else 0.0
                discount_percent = price_info.get('discount_percent', 0) if price_info else 0
                steam_price_str = f"{steam_price_display}" + (
                    f" (-{discount_percent}%)" if discount_percent > 0 else ""
                )
                desc = info.get('short_description', 'No description available.')
                desc = re.sub(r'<[^>]+>', '', desc)
                header_image = info.get('header_image', '')
                developers = ', '.join(info.get('developers', [])) or 'Unknown'
                release_date = info.get('release_date', {}).get('date', 'Unknown')
                metacritic_score = str(info.get('metacritic', {}).get('score', 'N/A'))
                recommendations = (
                    f"{info.get('recommendations', {}).get('total', 'N/A'):,}"
                    if info.get('recommendations') else 'N/A'
                )
                genres = ', '.join(g['description'] for g in info.get('genres', [])) or 'N/A'

                # Reviews
                review_score = "Not rated"
                try:
                    async with session.get(
                        f"https://store.steampowered.com/appreviews/{app_id}?json=1",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as review_resp:
                        if review_resp.status == 200:
                            review_data = await review_resp.json(content_type=None)
                            query_summary = review_data.get('query_summary', {})
                            review_score = query_summary.get('review_score_desc', 'Not rated')
                except Exception as e:
                    print(f"⚠️ Failed to fetch Steam reviews for app {app_id}: {e}")

                # CheapShark
                best_deal_text = "N/A"
                historical_text = "N/A"
                try:
                    async with session.get(
                        f"https://www.cheapshark.com/api/1.0/games?steamAppID={app_id}",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as cs_resp:
                        game_id = None
                        if cs_resp.status == 200:
                            cs_data = await cs_resp.json(content_type=None)
                            if cs_data and len(cs_data) > 0:
                                game_id = cs_data[0].get('gameID')
                                cheapest_current = float(cs_data[0].get('cheapest', 0))
                                deal_id = cs_data[0].get('cheapestDealID')
                                if cheapest_current > 0 and cheapest_current < steam_price:
                                    best_deal_text = (
                                        f"⚠️ [Cheaper elsewhere for ${cheapest_current:.2f}]"
                                        f"(https://www.cheapshark.com/redirect?dealID={deal_id})"
                                    )
                                else:
                                    best_deal_text = "✅ Steam is currently the best price."

                        if game_id:
                            async with session.get(
                                f"https://www.cheapshark.com/api/1.0/games?id={game_id}",
                                timeout=aiohttp.ClientTimeout(total=5)
                            ) as cs_detail_resp:
                                if cs_detail_resp.status == 200:
                                    cs_detail = await cs_detail_resp.json(content_type=None)
                                    cheapest_ever = cs_detail.get('cheapestPriceEver', {})
                                    lowest_price = cheapest_ever.get('price')
                                    lowest_date = cheapest_ever.get('date')
                                    if lowest_price is not None and lowest_date:
                                        historical_text = f"${lowest_price} (Hit on <t:{lowest_date}:d>)"
                except Exception as e:
                    print(f"❌ Failed to fetch CheapShark data for app {app_id}: {e}")

                # Player count
                current_players_str = "N/A"
                try:
                    async with session.get(
                        f"https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid={app_id}",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as players_resp:
                        if players_resp.status == 200:
                            players_data = await players_resp.json(content_type=None)
                            if players_data.get('response', {}).get('result') == 1:
                                player_count = players_data['response']['player_count']
                                current_players_str = f"{player_count:,}"
                except Exception as e:
                    print(f"⚠️ Failed to fetch player count for app {app_id}: {e}")

                embed = discord.Embed(
                    title=name,
                    description=desc,
                    color=discord.Color.blue(),
                    url=f"https://store.steampowered.com/app/{app_id}"
                )
                embed.add_field(name="💰 Steam Price", value=steam_price_str, inline=True)
                embed.add_field(name="🏷️ Best Current Deal", value=best_deal_text, inline=True)
                embed.add_field(name="📉 Historical Low", value=historical_text, inline=True)
                embed.add_field(name="📈 Reviews", value=review_score, inline=True)
                embed.add_field(name="🎯 Metacritic", value=metacritic_score, inline=True)
                embed.add_field(name="👍 Recommendations", value=recommendations, inline=True)
                embed.add_field(name="🎮 Current Players", value=current_players_str, inline=True)
                embed.add_field(name="🏷️ Genres", value=genres, inline=True)
                embed.add_field(name="🧑‍💻 Developer", value=developers, inline=True)
                embed.add_field(name="📅 Release Date", value=release_date, inline=True)
                if header_image:
                    embed.set_image(url=header_image)
                await message.reply(embed=embed, mention_author=False)
                try:
                    await message.edit(suppress=True)
                except (discord.Forbidden, discord.HTTPException):
                    pass
                await stats.increment("steam_games")
    except Exception as e:
        print(f"❌ Failed to fetch Steam info: {e}")
    return True


# ===== Steam Developer / Publisher =====

async def handle_steam_dev(message: discord.Message) -> bool:
    """Handle Steam developer/publisher search URLs. Returns True if handled."""
    match = STEAM_DEV_REGEX.search(message.content)
    if not match:
        return False

    search_type = match.group(1)
    search_name = match.group(2)
    display_name = unquote(search_name)
    original_url = match.group(0)

    async def fetch_game_embed(session, app_id):
        try:
            details_req = session.get(
                f"https://store.steampowered.com/api/appdetails?appids={app_id}",
                timeout=aiohttp.ClientTimeout(total=5)
            )
            reviews_req = session.get(
                f"https://store.steampowered.com/appreviews/{app_id}?json=1",
                timeout=aiohttp.ClientTimeout(total=5)
            )
            async with details_req as dr, reviews_req as rr:
                details_data = await dr.json(content_type=None)
                reviews_data = await rr.json(content_type=None)

            app_info = details_data.get(str(app_id), {})
            if not app_info.get('success'):
                return None
            data = app_info.get('data', {})
            name = data.get('name', 'Unknown')
            header_image = data.get('header_image', '')
            price_obj = data.get('price_overview')
            if price_obj:
                price = price_obj.get('final_formatted', 'N/A')
            elif data.get('is_free'):
                price = 'Free'
            else:
                price = 'N/A'
            review_desc = reviews_data.get('query_summary', {}).get('review_score_desc', 'N/A')

            embed = discord.Embed(
                title=name,
                url=f"https://store.steampowered.com/app/{app_id}",
                color=discord.Color.blue()
            )
            if header_image:
                embed.set_thumbnail(url=header_image)
            embed.add_field(name="💰 Price", value=price, inline=True)
            embed.add_field(name="📈 Reviews", value=review_desc, inline=True)
            return embed
        except Exception as e:
            print(f"❌ fetch_game_embed({app_id}): {e}")
            return None

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://store.steampowered.com/'
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(
                f"https://store.steampowered.com/search/results/?{search_type}={search_name}"
                f"&json=1&start=0&count=10&l=english&cc=US",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    items = data.get('items', [])
                    app_ids = []
                    for item in items:
                        logo = item.get('logo', '')
                        m = re.search(r'/steam/apps/(\d+)/', logo)
                        if m:
                            app_ids.append(m.group(1))
                    top_app_ids = list(dict.fromkeys(app_ids))[:5]

                    embeds_list = []
                    if top_app_ids:
                        embeds_list = await asyncio.gather(
                            *[fetch_game_embed(session, aid) for aid in top_app_ids]
                        )
                        embeds_list = [e for e in embeds_list if e is not None]

                    if embeds_list:
                        await message.reply(
                            content=f"🎮 **Top games by {display_name}:**",
                            embeds=embeds_list,
                            mention_author=False
                        )
                        try:
                            await message.edit(suppress=True)
                        except discord.Forbidden:
                            pass
                        await stats.increment("steam_devs")
    except Exception as e:
        print(f"❌ Failed to fetch Steam dev/publisher info: {e}")
    return True


# ===== Amazon Product =====

async def handle_amazon(message: discord.Message) -> bool:
    """Handle Amazon product URLs with rich embed. Returns True if handled."""
    match = AMAZON_URL_REGEX.search(message.content)
    if not match:
        return False

    asin = match.group(1)
    amazon_url = match.group(0).split('?')[0]
    camel_url = f"https://camelcamelcamel.com/product/{asin}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                amazon_url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                },
                timeout=aiohttp.ClientTimeout(total=8)
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    og_title = soup.find('meta', property='og:title')
                    bond_title = soup.find('div', id='bond-title-desktop')
                    span_title = soup.find('span', id='productTitle')
                    title_tag = soup.find('title')
                    product_title = (
                        (og_title.get('content') if og_title else None)
                        or (bond_title.get_text(strip=True) if bond_title else None)
                        or (span_title.text.strip() if span_title else None)
                        or (title_tag.string.strip() if title_tag and title_tag.string else None)
                    )

                    og_image = soup.find('meta', property='og:image')
                    product_image = og_image.get('content') if og_image else None
                    if not product_image:
                        img_tag = soup.find('img', id='landingImage') or soup.find('img', id='imgBlkFront')
                        if img_tag:
                            dynamic_json = img_tag.get('data-a-dynamic-image')
                            if dynamic_json:
                                try:
                                    dynamic_imgs = _json.loads(dynamic_json)
                                    product_image = max(dynamic_imgs, key=lambda u: dynamic_imgs[u][0] * dynamic_imgs[u][1])
                                except Exception:
                                    product_image = img_tag.get('src')
                            else:
                                product_image = img_tag.get('src')

                    price_tag = soup.find('span', class_='a-offscreen')
                    price = price_tag.text.strip() if price_tag else ''

                    description_lines = []
                    bullets_div = (
                        soup.find('div', id='bond-feature-bullets-desktop')
                        or soup.find('div', id='feature-bullets')
                    )
                    if bullets_div:
                        items = bullets_div.find_all('li')
                        for li in items[:4]:
                            text = li.get_text(strip=True)
                            if text:
                                description_lines.append(f'• {text}')

                    if not description_lines:
                        desc_div = (
                            soup.find('div', id='bond-product-descriptions-desktop')
                            or soup.find('div', id='productDescription')
                        )
                        if desc_div:
                            raw = desc_div.get_text(separator=' ', strip=True)
                            description_lines.append(raw[:500] + ('…' if len(raw) > 500 else ''))

                    description_text = '\n'.join(description_lines) if description_lines else ''

                    specs = {}
                    overview_div = soup.find('div', id='productOverview_feature_div')
                    if overview_div:
                        rows = overview_div.find_all('tr')
                        for row in rows:
                            cols = row.find_all(['th', 'td'])
                            if len(cols) >= 2:
                                key = cols[0].get_text(strip=True)
                                val = cols[1].get_text(strip=True)
                                if key and val:
                                    specs[key] = val

                    if product_title:
                        embed = discord.Embed(
                            title=product_title[:256],
                            url=amazon_url,
                            color=discord.Color.orange()
                        )
                        if description_text:
                            embed.description = description_text[:1024]
                        if price:
                            embed.add_field(name="💰 Price", value=price, inline=True)
                        for spec_key, spec_val in list(specs.items())[:4]:
                            embed.add_field(name=spec_key, value=spec_val[:100], inline=True)
                        embed.add_field(
                            name="📈 Price History",
                            value=f"[View on CamelCamelCamel]({camel_url})",
                            inline=False
                        )
                        if product_image:
                            embed.set_thumbnail(url=product_image)
                        await message.reply(
                            content=f"🛒 **Cleaned Amazon Link:** {amazon_url}",
                            embed=embed,
                            mention_author=False
                        )
                        try:
                            await message.edit(suppress=True)
                        except (discord.Forbidden, discord.HTTPException):
                            pass
                        await stats.increment("amazon_products")
    except Exception as e:
        print(f"❌ Failed to fetch Amazon product info: {e}")
    return True


# ===== IMDb Movie =====

async def handle_imdb(message: discord.Message) -> bool:
    """Handle IMDb title URLs with movie info embed. Returns True if handled."""
    if not OMDB_API_KEY:
        return False

    match = IMDB_URL_REGEX.search(message.content)
    if not match:
        return False

    imdb_id = match.group(1)
    original_url = match.group(0)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://www.omdbapi.com/?i={imdb_id}&apikey={OMDB_API_KEY}",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    if data.get('Response') == 'True':
                        title = data.get('Title', 'Unknown')
                        year = data.get('Year', '?')
                        plot = data.get('Plot', 'No plot available.')
                        poster = data.get('Poster', '')
                        imdb_rating = data.get('imdbRating', 'N/A')
                        rated = data.get('Rated', 'N/A')
                        embed = discord.Embed(
                            title=f"{title} ({year})",
                            description=plot,
                            url=original_url,
                            color=discord.Color.gold()
                        )
                        embed.add_field(name="⭐ IMDb Rating", value=imdb_rating, inline=True)
                        embed.add_field(name="🔞 Age Rating", value=rated, inline=True)
                        if poster and poster != 'N/A':
                            embed.set_thumbnail(url=poster)
                        await message.reply(embed=embed, mention_author=False)
                        try:
                            await message.edit(suppress=True)
                        except (discord.Forbidden, discord.HTTPException):
                            pass
                        await stats.increment("imdb_movies")
    except Exception as e:
        print(f"❌ Failed to fetch IMDb info: {e}")
    return True
