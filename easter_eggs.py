"""
easter_eggs.py - Legend of Zelda themed Easter egg responses.

Handles:
  - Direct @mention response (text/image/sound + rickroll)
  - Keyword reactions (pots, cuccos, triforce)
  - Rare item drop on link fix
"""

import discord
import os
import random
import re

import stats


# Zelda Easter Egg Data
ZELDA_TEXT_RESPONSES = [
    # --- The Classics & Game Memes ---
    "HYYAAAAAA! <a:link_spin:1475252964708057118>",
    "Hey! Listen. 🧚",
    "It's dangerous to go alone! Take this. ⚔️",
    "It's a secret to everybody.",
    "Dodongo dislikes smoke.",
    "I AM ERROR.",
    "You've met a terrible fate, haven't you?",
    "A puppet without a role is merely garbage.",
    "The flow of time is always cruel...",
    "Grumble, grumble...",
    "You got a green rupee! Don't spend it all in one place!",
    "The wind... it is blowing...",
    "Watch out!",

    # --- The 1989 Animated Series ---
    "Well, excuuuuuuuse me, Princess! <a:link_spin:1475252964708057118>",
    "Oh boy! I'm so hungry, I could eat an octorok! <a:link_spin:1475252964708057118>",
    "I'm a hero, not a handyman! <a:link_spin:1475252964708057118>",
    "I'll take a raincheck on that kiss, princess. Duty calls! <a:link_spin:1475252964708057118>",
    "Looking good, princess, especially from this angle! <a:link_spin:1475252964708057118>",

    # --- The CD-i Masterpieces ---
    "Mah boi, this peace is what all true warriors strive for!",
    "Lamp oil, rope, bombs? You want it? It's yours, my friend, as long as you have enough rubies.",
    "Sorry Link, I can't give credit! Come back when you're a little, mmmm... richer!",
    "Gee, it sure is boring around here.",
    "I just wonder what Ganon's up to.",
    "Squadala! We're off!",
    "I guess that's worth a kiss, huh? <a:link_spin:1475252964708057118>",
    "Great! I'll grab my stuff!",
    "I can't wait to bomb some Dodongos! <a:link_spin:1475252964708057118>",
    "You dare bring light to my lair?! You must die!"
]

# Rickroll URLs (angle brackets suppress Discord embed)
RICKROLL_URLS = [
    '<https://www.youtube.com/watch?v=5H1nNqGtLxM>',
    '<https://www.youtube.com/watch?v=ZkEv2SOHZJ0>',
]

# Expanded keyword patterns
POT_KEYWORDS = r'\b(pot|pots|smash|break|vase|vases|jar|jars|urn|urns|ceramics|pottery|rupee|rupees|money|burglary|theft|vandalism|vandalize|steal|stealing|thief|rob|robbery|loot|looting|crime|shatter|trespass|trespassing|crash|destroy|destruction|ransack|pillage)\b'
CUCCO_KEYWORDS = r'\b(cucco|cuccos|cuckoo|cuckoos|chicken|chickens|poultry|peck|pecking|flock|kakariko|rooster|cluck|feathers|swarm|revenge)\b'
TRIFORCE_KEYWORDS = r'\b(wisdom|courage|power|triforce|goddess|goddesses|din|nayru|farore|hylia|master|sword|demise|triangle)\b'

POT_PATTERN = re.compile(POT_KEYWORDS, re.IGNORECASE)
CUCCO_PATTERN = re.compile(CUCCO_KEYWORDS, re.IGNORECASE)
TRIFORCE_PATTERN = re.compile(TRIFORCE_KEYWORDS, re.IGNORECASE)


async def handle_mention(message: discord.Message, client: discord.Client) -> bool:
    """
    Handle direct @mention responses.
    Returns True if the message was fully handled (should halt processing).
    """
    if client.user not in message.mentions:
        return False

    await stats.increment("easter_eggs")

    # 5% chance for rickroll - checked first, halts all further processing
    if random.random() <= 0.05:
        await stats.increment("rickrolls_dealt")
        await message.channel.send(f"HERES A LINK FOR YA {random.choice(RICKROLL_URLS)}")
        return True

    # 10% chance for sound, 35% chance for image, 55% chance for text
    rand_response = random.randint(1, 100)

    if rand_response <= 10:  # 10% - Sound
        sounds_dir = "sounds"
        if os.path.exists(sounds_dir):
            sound_files = [f for f in os.listdir(sounds_dir) if f.endswith(('.mp3', '.wav', '.ogg'))]
            if sound_files:
                sound_file = random.choice(sound_files)
                await message.channel.send(file=discord.File(os.path.join(sounds_dir, sound_file)))
    elif rand_response <= 45:  # 35% - Image
        images_dir = "images"
        if os.path.exists(images_dir):
            image_files = [f for f in os.listdir(images_dir) if f.endswith(('.png', '.jpg', '.jpeg', '.gif'))]
            if image_files:
                image_file = random.choice(image_files)
                await message.channel.send(file=discord.File(os.path.join(images_dir, image_file)))
    else:  # 55% - Text response
        await message.channel.send(random.choice(ZELDA_TEXT_RESPONSES))

    return True


async def handle_reactions(message: discord.Message, config: dict) -> None:
    """Check and apply keyword-based reaction Easter eggs."""
    if not config.get("reactions", True):
        return

    # Pot Reaction
    if POT_PATTERN.search(message.content):
        try:
            await message.add_reaction('<a:link_spin:1475252964708057118>')
            await message.add_reaction('<:pot:1475279632512188718>')
        except discord.errors.HTTPException:
            pass

    # Cucco/Chicken Reaction
    if CUCCO_PATTERN.search(message.content):
        try:
            await message.add_reaction('🐔')
            await message.add_reaction('<a:link_spin:1475252964708057118>')
        except discord.errors.HTTPException:
            pass

    # Triforce Reaction
    if TRIFORCE_PATTERN.search(message.content):
        try:
            await message.add_reaction('<a:link_triforce:1475284641513607338>')
        except discord.errors.HTTPException:
            pass


def maybe_rare_drop() -> str:
    """Return a rare item drop string if the 5% chance hits, else empty string."""
    if random.random() < 0.05:
        return "\n\n*Da-da-da-daaa!* 🗝️"
    return ""
