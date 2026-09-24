from __future__ import annotations

import asyncio
import aiohttp
import io
import json
import os
import random
import secrets
import re
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import discord
from discord import app_commands
from discord.ext import commands, tasks
DATA_FILE = Path('ticket_panels.json')
COMMAND_PREFIX = os.getenv('BOT_PREFIX', '!')
SITE_URL = os.getenv('SITE_URL', 'https://furiousbot1.netlify.app').rstrip('/')
PAINEL_GIF_URL = 'https://www.bing.com/th/id/OGC.42d13870a89f09149fad3fa40c54b19f?r=0&o=7&pid=1.7&rm=3&rurl=https%3a%2f%2fi.pinimg.com%2foriginals%2fc3%2f7c%2fd2%2fc37cd207c15f7e1a5110329668a569d0.gif&ehk=XH%2b7BxOfCVISigu85Np9fd7DGVEOsed1YxFCHyDFmrw%3d'
BOT_START_TIME = datetime.now(timezone.utc)
PAINEL_IMAGE_URL = 'https://images-ext-1.discordapp.net/external/bPw7TtF3IFaAYRnAF56TzM0uSYuRmNsuEFpPfpzieVA/%3Fsize%3D1024/https/cdn.discordapp.com/avatars/1551043112049180732/1d9327239c3ffc91af73833c265c53f1.png?format=webp&quality=lossless'
SHOP_ITEMS = {'cafe': {'name': '☕ Café', 'price': 100, 'sell': 50}, 'pizza': {'name': '🍕 Pizza', 'price': 250, 'sell': 125}, 'vip': {'name': '💎 Passe VIP', 'price': 5000, 'sell': 2500}, 'coroa': {'name': '👑 Coroa', 'price': 15000, 'sell': 7500}}
QUIZ_QUESTIONS = [{'question': 'Qual planeta é conhecido como Planeta Vermelho?', 'options': ['Marte', 'Vênus', 'Júpiter', 'Saturno'], 'answer': 0}, {'question': 'Quanto é 9 × 9?', 'options': ['72', '81', '90', '99'], 'answer': 1}, {'question': 'Qual é a capital do Brasil?', 'options': ['Recife', 'São Paulo', 'Brasília', 'Rio de Janeiro'], 'answer': 2}, {'question': 'Qual animal é conhecido como rei da selva?', 'options': ['Tigre', 'Leão', 'Urso', 'Lobo'], 'answer': 1}]
HANGMAN_WORDS = ['discord', 'furious', 'roblox', 'python', 'servidor', 'bot', 'ticket', 'economia', 'seguranca', 'comunidade']
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)


# >>> TICKET V3 ULTIMATE BEGIN >>>

# ============================================================
# 🎫 TICKET V3 ULTIMATE
# Sistema profissional de tickets
# ============================================================


import io
import json
import re
import secrets
from datetime import datetime, timezone, timedelta
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands, tasks


T3_FILE = Path("tickets_v3.json")
T3_VERSION = 3


# ============================================================
# BANCO DE DADOS
# ============================================================

def t3_now():
    return datetime.now(timezone.utc)


def t3_iso(dt=None):
    return (dt or t3_now()).isoformat()


def t3_id(size=8):
    return secrets.token_hex(size)


def t3_default():
    return {
        "version": T3_VERSION,
        "panels": {},
        "tickets": {},
        "evaluations": {},
        "stats": {},
        "blacklist": {},
    }


def t3_load():
    if not T3_FILE.exists():
        return t3_default()

    try:
        data = json.loads(
            T3_FILE.read_text(encoding="utf-8")
        )

        if not isinstance(data, dict):
            return t3_default()

        base = t3_default()
        base.update(data)

        return base

    except Exception as exc:
        print(f"[TICKET V3] Erro ao carregar banco: {exc}")
        return t3_default()


def t3_save(data):
    temp = T3_FILE.with_suffix(".tmp")

    temp.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    temp.replace(T3_FILE)


# ============================================================
# UTILIDADES
# ============================================================

def t3_clean_name(value, fallback="ticket"):
    value = str(value or "").lower()

    value = re.sub(
        r"[^a-z0-9áéíóúãõâêôç _-]",
        "",
        value
    )

    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"-+", "-", value)

    value = value.strip("-")

    return (value[:90] or fallback)


def t3_hex(value, fallback="5865F2"):
    value = str(value or "").replace("#", "").strip()

    if re.fullmatch(r"[0-9a-fA-F]{6}", value):
        return value.upper()

    return fallback


def t3_color(value):
    try:
        return discord.Color(
            int(t3_hex(value), 16)
        )
    except Exception:
        return discord.Color.blurple()


def t3_channel(guild, channel_id):
    if not channel_id:
        return None

    try:
        return guild.get_channel(int(channel_id))
    except Exception:
        return None


def t3_role(guild, role_id):
    if not role_id:
        return None

    try:
        return guild.get_role(int(role_id))
    except Exception:
        return None


def t3_get_panel(panel_id):
    data = t3_load()

    return data["panels"].get(
        str(panel_id)
    )


def t3_get_type(panel, type_id):
    if not panel:
        return None

    for item in panel.get("types", []):
        if str(item.get("id")) == str(type_id):
            return item

    return None


def t3_open_tickets(guild_id, user_id=None):
    data = t3_load()

    result = []

    for ticket in data["tickets"].values():

        if str(ticket.get("guild_id")) != str(guild_id):
            continue

        if user_id is not None:
            if str(ticket.get("owner_id")) != str(user_id):
                continue

        if ticket.get("closed"):
            continue

        result.append(ticket)

    return result


def t3_current_ticket(interaction):
    if not interaction.guild:
        return None

    channel_id = getattr(
        interaction.channel,
        "id",
        None
    )

    if not channel_id:
        return None

    data = t3_load()

    for ticket in data["tickets"].values():

        if str(ticket.get("guild_id")) != str(
            interaction.guild.id
        ):
            continue

        if str(ticket.get("channel_id")) != str(
            channel_id
        ):
            continue

        return ticket

    return None


# ============================================================
# PLACEHOLDERS
# ============================================================

def t3_replace(text, ticket, panel):
    text = str(text or "")

    replacements = {
        "{ticket_id}":
            str(ticket.get("id", "")),

        "{user_id}":
            str(ticket.get("owner_id", "")),

        "{user}":
            f"<@{ticket.get('owner_id')}>",

        "{username}":
            str(ticket.get("owner_name", "")),

        "{guild}":
            str(panel.get("guild_name", "")),

        "{guild_id}":
            str(panel.get("guild_id", "")),

        "{type}":
            str(ticket.get("type_name", "")),

        "{department}":
            str(ticket.get("department", "")),

        "{priority}":
            str(
                ticket.get(
                    "priority",
                    "normal"
                )
            ).title(),

        "{staff}":
            (
                f"<@{ticket['claimed_by']}>"
                if ticket.get("claimed_by")
                else "Ninguém"
            ),

        "{created_at}":
            str(ticket.get("created_at", "")),

        "{created_timestamp}":
            (
                f"<t:{int(datetime.fromisoformat(ticket['created_at']).timestamp())}:F>"
                if ticket.get("created_at")
                else ""
            ),
    }

    for key, value in replacements.items():
        text = text.replace(key, value)

    return text


# ============================================================
# CONFIGURAÇÃO DE TIPOS
# ============================================================

def t3_create_type(
    name="Suporte",
    description="Preciso de ajuda.",
    emoji="🎫"
):
    return {
        "id": t3_id(4),

        "name": name[:80],

        "description":
            description[:100],

        "emoji":
            emoji[:10],

        "color":
            "5865F2",

        "department":
            name[:80],

        "mode":
            "channel",

        "thread_type":
            "private",

        "thread_archive":
            1440,

        "category_id":
            None,

        "staff_role_id":
            None,

        "priority":
            "normal",

        "tags":
            [],

        "max_open":
            1,

        "cooldown_seconds":
            0,

        "sla_first_response":
            15,

        "sla_resolution":
            120,

        "auto_close_minutes":
            0,

        "transcript":
            True,

        "evaluation":
            True,

        "mention_user":
            True,

        "mention_staff":
            True,

        "allow_user_close":
            True,

        "form":
            [],

        "close_reasons": [
            "Resolvido",
            "Usuário não respondeu",
            "Duplicado",
            "Encaminhado",
            "Outro"
        ],

        "welcome_title":
            "🎫 {type} • Atendimento",

        "welcome_description":
            (
                "Olá {user}! 👋\n\n"
                "Seu atendimento foi criado.\n"
                "A equipe responderá em breve.\n\n"
                "🆔 Ticket: `{ticket_id}`\n"
                "🏷️ Tipo: **{type}**\n"
                "🔴 Prioridade: **{priority}**"
            ),
    }


def t3_create_panel(guild):
    return {
        "id":
            t3_id(),

        "guild_id":
            guild.id,

        "guild_name":
            guild.name,

        "name":
            "Central de Atendimento",

        "description":
            (
                "Selecione abaixo o tipo "
                "de atendimento desejado."
            ),

        "color":
            "5865F2",

        "thumbnail_url":
            None,

        "image_url":
            None,

        "footer":
            "Sistema de Tickets V3 Ultimate",

        "panel_channel_id":
            None,

        "panel_message_id":
            None,

        "default_mode":
            "channel",

        "default_category_id":
            None,

        "default_staff_role_id":
            None,

        "log_channel_id":
            None,

        "max_open_per_user":
            1,

        "types":
            [
                t3_create_type()
            ],

        "tags":
            [],

        "created_at":
            t3_iso(),

        "business_hours": {
            "enabled": False,
            "timezone": "UTC",
            "allow_outside": True
        }
    }


# ============================================================
# PERMISSÕES
# ============================================================

def t3_is_staff(
    interaction,
    ticket=None,
    panel=None
):
    if not interaction.guild:
        return False

    member = interaction.user

    if member.guild_permissions.administrator:
        return True

    if member.guild_permissions.manage_channels:
        return True

    panel = panel or {}

    role_ids = set()

    if panel.get("default_staff_role_id"):
        role_ids.add(
            str(panel["default_staff_role_id"])
        )

    if ticket:
        ticket_type = t3_get_type(
            panel,
            ticket.get("type_id")
        )

        if ticket_type:
            if ticket_type.get("staff_role_id"):
                role_ids.add(
                    str(
                        ticket_type[
                            "staff_role_id"
                        ]
                    )
                )

    for role_id in role_ids:

        role = t3_role(
            interaction.guild,
            role_id
        )

        if role and role in member.roles:
            return True

    return False


# ============================================================
# EMBED DO PAINEL
# ============================================================

def t3_panel_embed(panel):
    embed = discord.Embed(
        title=
            f"🎫 {panel.get('name', 'Central')}",

        description=
            panel.get("description", ""),

        color=
            t3_color(
                panel.get("color")
            )
    )

    if panel.get("thumbnail_url"):
        embed.set_thumbnail(
            url=panel["thumbnail_url"]
        )

    if panel.get("image_url"):
        embed.set_image(
            url=panel["image_url"]
        )

    types = panel.get("types", [])

    if types:

        lines = []

        for item in types[:25]:

            lines.append(
                f"{item.get('emoji', '🎫')} "
                f"**{item.get('name', 'Atendimento')}**"
                f" — "
                f"{item.get('description', '')}"
            )

        embed.add_field(
            name="📋 Tipos de atendimento",
            value="\n".join(lines)[:1024],
            inline=False
        )

    embed.set_footer(
        text=panel.get(
            "footer",
            "Tickets V3 Ultimate"
        )
    )

    return embed


# ============================================================
# EMBED DO TICKET
# ============================================================

def t3_ticket_embed(
    ticket,
    panel,
    ticket_type
):
    embed = discord.Embed(

        title=t3_replace(
            ticket_type.get(
                "welcome_title"
            ),
            ticket,
            panel
        ),

        description=t3_replace(
            ticket_type.get(
                "welcome_description"
            ),
            ticket,
            panel
        ),

        color=t3_color(
            ticket_type.get(
                "color",
                panel.get("color")
            )
        ),

        timestamp=t3_now()
    )

    embed.add_field(
        name="👤 Cliente",
        value=
            f"<@{ticket['owner_id']}>",
        inline=True
    )

    embed.add_field(
        name="🙋 Responsável",
        value=(
            f"<@{ticket['claimed_by']}>"
            if ticket.get("claimed_by")
            else "Ninguém"
        ),
        inline=True
    )

    embed.add_field(
        name="🔴 Prioridade",
        value=
            ticket.get(
                "priority",
                "normal"
            ).title(),
        inline=True
    )

    embed.add_field(
        name="🏷️ Departamento",
        value=
            ticket.get(
                "department",
                "Atendimento"
            ),
        inline=True
    )

    if ticket.get("tags"):

        embed.add_field(
            name="🏷️ Tags",
            value=
                " ".join(
                    ticket["tags"]
                )[:1024],
            inline=False
        )

    answers = ticket.get(
        "form_answers",
        {}
    )

    if answers:

        lines = []

        for key, value in answers.items():

            lines.append(
                f"**{key}:** {value}"
            )

        embed.add_field(
            name="📝 Formulário",
            value="\n".join(lines)[:1024],
            inline=False
        )

    embed.set_footer(
        text=
            f"Ticket V3 • {ticket['id']}"
    )

    return embed


# ============================================================
# FORMULÁRIO
# ============================================================

class T3FormModal(discord.ui.Modal):

    def __init__(
        self,
        panel,
        ticket_type
    ):
        super().__init__(
            title=
                ticket_type[
                    "name"
                ][:45]
        )

        self.panel_id = str(
            panel["id"]
        )

        self.type_id = str(
            ticket_type["id"]
        )

        self.fields_data = []

        for field in ticket_type.get(
            "form",
            []
        )[:5]:

            style = (
                discord.TextStyle.paragraph
                if field.get("style")
                == "paragraph"
                else discord.TextStyle.short
            )

            item = discord.ui.TextInput(
                label=
                    field.get(
                        "label",
                        "Campo"
                    )[:45],

                placeholder=
                    field.get(
                        "placeholder",
                        ""
                    )[:100],

                style=style,

                required=
                    bool(
                        field.get(
                            "required",
                            True
                        )
                    ),

                max_length=
                    min(
                        int(
                            field.get(
                                "max_length",
                                1000
                            )
                        ),
                        4000
                    )
            )

            self.fields_data.append(
                (
                    field,
                    item
                )
            )

            self.add_item(item)

    async def on_submit(
        self,
        interaction
    ):
        panel = t3_get_panel(
            self.panel_id
        )

        if not panel:
            return await interaction.response.send_message(
                "❌ Painel não encontrado.",
                ephemeral=True
            )

        ticket_type = t3_get_type(
            panel,
            self.type_id
        )

        if not ticket_type:
            return await interaction.response.send_message(
                "❌ Tipo não encontrado.",
                ephemeral=True
            )

        await interaction.response.defer(
            ephemeral=True
        )

        answers = {}

        for field, item in self.fields_data:

            answers[
                field.get(
                    "label",
                    "Campo"
                )
            ] = item.value

        try:

            channel, _ = await t3_create_ticket(
                interaction,
                panel,
                ticket_type,
                answers
            )

            await interaction.followup.send(
                f"✅ Ticket criado: {channel.mention}",
                ephemeral=True
            )

        except Exception as exc:

            await interaction.followup.send(
                f"❌ {exc}",
                ephemeral=True
            )


# ============================================================
# SELECT DO PAINEL
# ============================================================

class T3TypeSelect(
    discord.ui.Select
):

    def __init__(self, panel):

        self.panel_id = str(
            panel["id"]
        )

        options = []

        for item in panel.get(
            "types",
            []
        )[:25]:

            options.append(
                discord.SelectOption(
                    label=
                        item["name"][:100],

                    description=
                        item.get(
                            "description",
                            ""
                        )[:100],

                    emoji=
                        item.get(
                            "emoji",
                            "🎫"
                        ),

                    value=
                        str(
                            item["id"]
                        )
                )
            )

        if not options:

            options.append(
                discord.SelectOption(
                    label="Suporte",
                    value="none",
                    emoji="🎫"
                )
            )

        super().__init__(
            placeholder=
                "🎫 Selecione o tipo de atendimento...",

            min_values=1,

            max_values=1,

            options=options,

            custom_id=
                f"t3:type:{self.panel_id}"
        )

    async def callback(
        self,
        interaction
    ):
        panel = t3_get_panel(
            self.panel_id
        )

        if not panel:
            return await interaction.response.send_message(
                "❌ Painel não encontrado.",
                ephemeral=True
            )

        ticket_type = t3_get_type(
            panel,
            self.values[0]
        )

        if not ticket_type:
            return await interaction.response.send_message(
                "❌ Tipo inválido.",
                ephemeral=True
            )

        if ticket_type.get("form"):

            return await interaction.response.send_modal(
                T3FormModal(
                    panel,
                    ticket_type
                )
            )

        await interaction.response.defer(
            ephemeral=True
        )

        try:

            channel, _ = await t3_create_ticket(
                interaction,
                panel,
                ticket_type
            )

            await interaction.followup.send(
                f"✅ Ticket criado: {channel.mention}",
                ephemeral=True
            )

        except Exception as exc:

            await interaction.followup.send(
                f"❌ {exc}",
                ephemeral=True
            )


class T3PanelView(
    discord.ui.View
):

    def __init__(
        self,
        panel
    ):
        super().__init__(
            timeout=None
        )

        self.add_item(
            T3TypeSelect(panel)
        )


# ============================================================
# CRIAÇÃO DO TICKET
# ============================================================

async def t3_create_ticket(
    interaction,
    panel,
    ticket_type,
    answers=None
):
    guild = interaction.guild
    user = interaction.user

    if not guild:
        raise RuntimeError(
            "O sistema precisa ser usado em um servidor."
        )

    max_open = int(
        ticket_type.get(
            "max_open",
            panel.get(
                "max_open_per_user",
                1
            )
        )
    )

    opened = t3_open_tickets(
        guild.id,
        user.id
    )

    if len(opened) >= max_open:
        raise RuntimeError(
            f"Você já possui {len(opened)} "
            f"ticket(s) aberto(s)."
        )

    data = t3_load()

    category = t3_channel(
        guild,
        ticket_type.get(
            "category_id"
        )
        or panel.get(
            "default_category_id"
        )
    )

    staff_role = t3_role(
        guild,
        ticket_type.get(
            "staff_role_id"
        )
        or panel.get(
            "default_staff_role_id"
        )
    )

    mode = ticket_type.get(
        "mode",
        panel.get(
            "default_mode",
            "channel"
        )
    )

    ticket_name = t3_clean_name(
        f"{ticket_type['name']}-{user.display_name}"
    )

    ticket_id = t3_id()

    ticket = {
        "id":
            ticket_id,

        "guild_id":
            guild.id,

        "channel_id":
            None,

        "owner_id":
            user.id,

        "owner_name":
            str(user),

        "panel_id":
            panel["id"],

        "type_id":
            ticket_type["id"],

        "type_name":
            ticket_type["name"],

        "department":
            ticket_type.get(
                "department",
                ticket_type["name"]
            ),

        "mode":
            mode,

        "priority":
            ticket_type.get(
                "priority",
                "normal"
            ),

        "tags":
            list(
                ticket_type.get(
                    "tags",
                    []
                )
            ),

        "claimed_by":
            None,

        "added_members":
            [],

        "closed":
            False,

        "paused":
            False,

        "created_at":
            t3_iso(),

        "first_response_at":
            None,

        "closed_at":
            None,

        "closed_by":
            None,

        "close_reason":
            None,

        "form_answers":
            answers or {}
    }

    # --------------------------------------------------------
    # CANAL
    # --------------------------------------------------------

    if mode == "channel":

        overwrites = {

            guild.default_role:
                discord.PermissionOverwrite(
                    view_channel=False
                ),

            user:
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True
                )
        }

        if staff_role:

            overwrites[
                staff_role
            ] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
                manage_messages=True
            )

        channel = await guild.create_text_channel(

            name=ticket_name[:100],

            category=(
                category
                if isinstance(
                    category,
                    discord.CategoryChannel
                )
                else None
            ),

            overwrites=overwrites,

            reason=
                f"Ticket V3 aberto por {user}"
        )

    # --------------------------------------------------------
    # THREAD
    # --------------------------------------------------------

    elif mode == "thread":

        parent = t3_channel(
            guild,
            panel.get(
                "panel_channel_id"
            )
        )

        if not isinstance(
            parent,
            discord.TextChannel
        ):
            raise RuntimeError(
                "Configure o canal pai das threads."
            )

        thread_type = (
            discord.ChannelType.private_thread
            if ticket_type.get(
                "thread_type",
                "private"
            ) == "private"
            else discord.ChannelType.public_thread
        )

        archive = int(
            ticket_type.get(
                "thread_archive",
                1440
            )
        )

        if archive not in (
            60,
            1440,
            4320,
            10080
        ):
            archive = 1440

        channel = await parent.create_thread(

            name=ticket_name[:100],

            type=thread_type,

            auto_archive_duration=archive,

            reason=
                f"Ticket V3 aberto por {user}"
        )

        if thread_type == discord.ChannelType.private_thread:

            try:
                await channel.add_user(
                    user
                )
            except Exception:
                pass

    else:

        raise RuntimeError(
            "Modo de ticket inválido."
        )

    ticket["channel_id"] = channel.id

    data["tickets"][ticket_id] = ticket

    stats = data["stats"].setdefault(
        str(guild.id),
        {
            "created": 0,
            "closed": 0,
            "reopened": 0,
            "evaluations": 0
        }
    )

    stats["created"] += 1

    t3_save(data)

    content = None

    if ticket_type.get(
        "mention_user",
        True
    ):
        content = user.mention

    if (
        ticket_type.get(
            "mention_staff",
            True
        )
        and staff_role
    ):
        content = (
            f"{content or ''} "
            f"{staff_role.mention}"
        ).strip()

    await channel.send(

        content=content,

        embed=t3_ticket_embed(
            ticket,
            panel,
            ticket_type
        ),

        view=T3TicketView(
            ticket_id
        )
    )

    await t3_log(
        guild,
        panel,
        "🎫 Ticket aberto",
        (
            f"**ID:** `{ticket_id}`\n"
            f"**Usuário:** {user.mention}\n"
            f"**Tipo:** {ticket_type['name']}\n"
            f"**Modo:** `{mode}`"
        )
    )

    return channel, ticket


# ============================================================
# LOGS
# ============================================================

async def t3_log(
    guild,
    panel,
    title,
    description
):
    channel = t3_channel(
        guild,
        panel.get(
            "log_channel_id"
        )
    )

    if not channel:
        return

    try:

        embed = discord.Embed(
            title=title,
            description=description[:4000],
            color=t3_color(
                panel.get("color")
            ),
            timestamp=t3_now()
        )

        await channel.send(
            embed=embed
        )

    except Exception:
        pass


# ============================================================
# TRANSCRIPT
# ============================================================

async def t3_transcript(
    channel
):
    lines = []

    async for message in channel.history(
        limit=None,
        oldest_first=True
    ):

        timestamp = (
            message.created_at
            .strftime(
                "%d/%m/%Y %H:%M:%S"
            )
        )

        content = (
            message.content
            or ""
        )

        if message.attachments:

            content += " " + " ".join(
                attachment.url
                for attachment
                in message.attachments
            )

        lines.append(
            f"[{timestamp}] "
            f"{message.author}: "
            f"{content}"
        )

    raw = "\n".join(
        lines
    ).encode(
        "utf-8"
    )

    return discord.File(
        io.BytesIO(raw),
        filename=
            f"transcript-{channel.id}.txt"
    )


# ============================================================
# CONTROLE DO TICKET
# ============================================================

class T3TicketView(
    discord.ui.View
):

    def __init__(
        self,
        ticket_id
    ):
        super().__init__(
            timeout=None
        )

        self.ticket_id = str(
            ticket_id
        )

    def get_ticket(self):
        data = t3_load()

        ticket = data["tickets"].get(
            self.ticket_id
        )

        if not ticket:
            return data, None, None

        panel = data["panels"].get(
            str(
                ticket["panel_id"]
            )
        )

        return data, ticket, panel

    @discord.ui.button(
        label="Assumir",
        emoji="🙋",
        style=discord.ButtonStyle.primary,
        custom_id="t3:claim"
    )
    async def claim(
        self,
        interaction,
        button
    ):
        data, ticket, panel = (
            self.get_ticket()
        )

        if not ticket:
            return await interaction.response.send_message(
                "❌ Ticket não encontrado.",
                ephemeral=True
            )

        if not t3_is_staff(
            interaction,
            ticket,
            panel
        ):
            return await interaction.response.send_message(
                "❌ Apenas a equipe pode assumir.",
                ephemeral=True
            )

        if ticket.get(
            "claimed_by"
        ):
            return await interaction.response.send_message(
                f"❌ Já assumido por "
                f"<@{ticket['claimed_by']}>.",
                ephemeral=True
            )

        ticket["claimed_by"] = (
            interaction.user.id
        )

        ticket["first_response_at"] = (
            ticket.get(
                "first_response_at"
            )
            or t3_iso()
        )

        t3_save(data)

        await interaction.response.send_message(
            f"🙋 {interaction.user.mention} "
            f"assumiu este atendimento."
        )

    @discord.ui.button(
        label="Ações",
        emoji="⚙️",
        style=discord.ButtonStyle.secondary,
        custom_id="t3:actions"
    )
    async def actions(
        self,
        interaction,
        button
    ):
        _, ticket, panel = (
            self.get_ticket()
        )

        if not ticket:
            return await interaction.response.send_message(
                "❌ Ticket não encontrado.",
                ephemeral=True
            )

        await interaction.response.send_message(
            "⚙️ **Painel de ações**",
            view=T3ActionsView(
                self.ticket_id
            ),
            ephemeral=True
        )

    @discord.ui.button(
        label="Prioridade",
        emoji="🔴",
        style=discord.ButtonStyle.secondary,
        custom_id="t3:priority"
    )
    async def priority(
        self,
        interaction,
        button
    ):
        _, ticket, panel = (
            self.get_ticket()
        )

        if not ticket:
            return await interaction.response.send_message(
                "❌ Ticket não encontrado.",
                ephemeral=True
            )

        if not t3_is_staff(
            interaction,
            ticket,
            panel
        ):
            return await interaction.response.send_message(
                "❌ Sem permissão.",
                ephemeral=True
            )

        await interaction.response.send_message(
            "🔴 Selecione:",
            view=T3PriorityView(
                self.ticket_id
            ),
            ephemeral=True
        )

    @discord.ui.button(
        label="Fechar",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="t3:close"
    )
    async def close(
        self,
        interaction,
        button
    ):
        _, ticket, panel = (
            self.get_ticket()
        )

        if not ticket:
            return await interaction.response.send_message(
                "❌ Ticket não encontrado.",
                ephemeral=True
            )

        if (
            interaction.user.id
            != ticket["owner_id"]
            and not t3_is_staff(
                interaction,
                ticket,
                panel
            )
        ):
            return await interaction.response.send_message(
                "❌ Você não pode fechar este ticket.",
                ephemeral=True
            )

        await interaction.response.send_message(
            "🔒 Escolha o motivo:",
            view=T3CloseReasonView(
                self.ticket_id
            ),
            ephemeral=True
        )


# ============================================================
# AÇÕES
# ============================================================

class T3ActionsView(
    discord.ui.View
):

    def __init__(
        self,
        ticket_id
    ):
        super().__init__(
            timeout=180
        )

        self.ticket_id = str(
            ticket_id
        )

    @discord.ui.button(
        label="Renomear",
        emoji="✏️",
        style=discord.ButtonStyle.secondary
    )
    async def rename(
        self,
        interaction,
        button
    ):
        data, ticket, panel = (
            t3_bundle(
                self.ticket_id
            )
        )

        if not ticket or not t3_is_staff(
            interaction,
            ticket,
            panel
        ):
            return await interaction.response.send_message(
                "❌ Sem permissão.",
                ephemeral=True
            )

        await interaction.response.send_modal(
            T3RenameModal(
                self.ticket_id
            )
        )

    @discord.ui.button(
        label="Adicionar membro",
        emoji="👤",
        style=discord.ButtonStyle.secondary
    )
    async def member(
        self,
        interaction,
        button
    ):
        data, ticket, panel = (
            t3_bundle(
                self.ticket_id
            )
        )

        if not ticket or not t3_is_staff(
            interaction,
            ticket,
            panel
        ):
            return await interaction.response.send_message(
                "❌ Sem permissão.",
                ephemeral=True
            )

        await interaction.response.send_modal(
            T3MemberModal(
                self.ticket_id
            )
        )

    @discord.ui.button(
        label="Transferir",
        emoji="🔄",
        style=discord.ButtonStyle.secondary
    )
    async def transfer(
        self,
        interaction,
        button
    ):
        data, ticket, panel = (
            t3_bundle(
                self.ticket_id
            )
        )

        if not ticket or not t3_is_staff(
            interaction,
            ticket,
            panel
        ):
            return await interaction.response.send_message(
                "❌ Sem permissão.",
                ephemeral=True
            )

        await interaction.response.send_modal(
            T3TransferModal(
                self.ticket_id
            )
        )

    @discord.ui.button(
        label="Transcript",
        emoji="📄",
        style=discord.ButtonStyle.secondary
    )
    async def transcript(
        self,
        interaction,
        button
    ):
        data, ticket, panel = (
            t3_bundle(
                self.ticket_id
            )
        )

        if not ticket or not t3_is_staff(
            interaction,
            ticket,
            panel
        ):
            return await interaction.response.send_message(
                "❌ Sem permissão.",
                ephemeral=True
            )

        try:

            file = await t3_transcript(
                interaction.channel
            )

            await interaction.response.send_message(
                "📄 Transcript:",
                file=file,
                ephemeral=True
            )

        except Exception as exc:

            await interaction.response.send_message(
                f"❌ Erro: `{exc}`",
                ephemeral=True
            )


def t3_bundle(ticket_id):

    data = t3_load()

    ticket = data["tickets"].get(
        str(ticket_id)
    )

    panel = None

    if ticket:

        panel = data["panels"].get(
            str(
                ticket["panel_id"]
            )
        )

    return data, ticket, panel


# ============================================================
# PRIORIDADE
# ============================================================

class T3PrioritySelect(
    discord.ui.Select
):

    def __init__(
        self,
        ticket_id
    ):
        self.ticket_id = str(
            ticket_id
        )

        super().__init__(
            placeholder=
                "🔴 Prioridade...",
            options=[
                discord.SelectOption(
                    label="Baixa",
                    value="low",
                    emoji="🔵"
                ),
                discord.SelectOption(
                    label="Normal",
                    value="normal",
                    emoji="🟢"
                ),
                discord.SelectOption(
                    label="Alta",
                    value="high",
                    emoji="🟡"
                ),
                discord.SelectOption(
                    label="Urgente",
                    value="urgent",
                    emoji="🟠"
                ),
                discord.SelectOption(
                    label="Crítica",
                    value="critical",
                    emoji="🔴"
                )
            ]
        )

    async def callback(
        self,
        interaction
    ):
        data, ticket, panel = (
            t3_bundle(
                self.ticket_id
            )
        )

        if not ticket or not t3_is_staff(
            interaction,
            ticket,
            panel
        ):
            return await interaction.response.send_message(
                "❌ Sem permissão.",
                ephemeral=True
            )

        ticket["priority"] = (
            self.values[0]
        )

        t3_save(data)

        await interaction.response.send_message(
            "✅ Prioridade atualizada.",
            ephemeral=True
        )


class T3PriorityView(
    discord.ui.View
):

    def __init__(
        self,
        ticket_id
    ):
        super().__init__(
            timeout=60
        )

        self.add_item(
            T3PrioritySelect(
                ticket_id
            )
        )


# ============================================================
# MOTIVO DE FECHAMENTO
# ============================================================

class T3CloseSelect(
    discord.ui.Select
):

    def __init__(
        self,
        ticket_id
    ):
        self.ticket_id = str(
            ticket_id
        )

        _, ticket, panel = (
            t3_bundle(
                ticket_id
            )
        )

        reasons = [
            "Resolvido",
            "Usuário não respondeu",
            "Duplicado",
            "Encaminhado",
            "Outro"
        ]

        if ticket and panel:

            ticket_type = t3_get_type(
                panel,
                ticket.get(
                    "type_id"
                )
            )

            if ticket_type:

                reasons = (
                    ticket_type.get(
                        "close_reasons",
                        reasons
                    )
                    [:25]
                )

        super().__init__(
            placeholder=
                "🔒 Motivo...",
            options=[
                discord.SelectOption(
                    label=x[:100],
                    value=x[:100]
                )
                for x in reasons
            ]
        )

    async def callback(
        self,
        interaction
    ):
        await t3_close(
            interaction,
            self.ticket_id,
            self.values[0]
        )


class T3CloseReasonView(
    discord.ui.View
):

    def __init__(
        self,
        ticket_id
    ):
        super().__init__(
            timeout=120
        )

        self.add_item(
            T3CloseSelect(
                ticket_id
            )
        )


# ============================================================
# MODAL RENOMEAR
# ============================================================

class T3RenameModal(
    discord.ui.Modal
):

    def __init__(
        self,
        ticket_id
    ):
        super().__init__(
            title="✏️ Renomear ticket"
        )

        self.ticket_id = str(
            ticket_id
        )

        self.name = discord.ui.TextInput(
            label="Novo nome",
            max_length=90
        )

        self.add_item(
            self.name
        )

    async def on_submit(
        self,
        interaction
    ):
        data, ticket, panel = (
            t3_bundle(
                self.ticket_id
            )
        )

        if not ticket or not t3_is_staff(
            interaction,
            ticket,
            panel
        ):
            return await interaction.response.send_message(
                "❌ Sem permissão.",
                ephemeral=True
            )

        name = t3_clean_name(
            self.name.value
        )

        await interaction.channel.edit(
            name=name
        )

        await interaction.response.send_message(
            f"✅ Nome alterado para `{name}`.",
            ephemeral=True
        )


# ============================================================
# ADICIONAR MEMBRO
# ============================================================

class T3MemberModal(
    discord.ui.Modal
):

    def __init__(
        self,
        ticket_id
    ):
        super().__init__(
            title="👤 Adicionar membro"
        )

        self.ticket_id = str(
            ticket_id
        )

        self.member_id = discord.ui.TextInput(
            label="ID do usuário",
            placeholder=
                "123456789012345678"
        )

        self.add_item(
            self.member_id
        )

    async def on_submit(
        self,
        interaction
    ):
        data, ticket, panel = (
            t3_bundle(
                self.ticket_id
            )
        )

        if not ticket or not t3_is_staff(
            interaction,
            ticket,
            panel
        ):
            return await interaction.response.send_message(
                "❌ Sem permissão.",
                ephemeral=True
            )

        if not self.member_id.value.isdigit():
            return await interaction.response.send_message(
                "❌ ID inválido.",
                ephemeral=True
            )

        member = interaction.guild.get_member(
            int(
                self.member_id.value
            )
        )

        if not member:
            return await interaction.response.send_message(
                "❌ Usuário não encontrado.",
                ephemeral=True
            )

        if isinstance(
            interaction.channel,
            discord.Thread
        ):

            try:
                await interaction.channel.add_user(
                    member
                )
            except Exception:
                pass

        else:

            await interaction.channel.set_permissions(
                member,
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )

        if member.id not in ticket[
            "added_members"
        ]:

            ticket[
                "added_members"
            ].append(
                member.id
            )

        t3_save(data)

        await interaction.response.send_message(
            f"👤 {member.mention} adicionado.",
            ephemeral=True
        )


# ============================================================
# TRANSFERÊNCIA
# ============================================================

class T3TransferModal(
    discord.ui.Modal
):

    def __init__(
        self,
        ticket_id
    ):
        super().__init__(
            title="🔄 Transferir ticket"
        )

        self.ticket_id = str(
            ticket_id
        )

        self.department = discord.ui.TextInput(
            label="Novo departamento",
            placeholder=
                "Financeiro, Suporte, Moderação..."
        )

        self.add_item(
            self.department
        )

    async def on_submit(
        self,
        interaction
    ):
        data, ticket, panel = (
            t3_bundle(
                self.ticket_id
            )
        )

        if not ticket or not t3_is_staff(
            interaction,
            ticket,
            panel
        ):
            return await interaction.response.send_message(
                "❌ Sem permissão.",
                ephemeral=True
            )

        ticket["department"] = (
            self.department.value[:80]
        )

        ticket["claimed_by"] = None

        t3_save(data)

        await interaction.response.send_message(
            f"🔄 Ticket transferido para "
            f"**{ticket['department']}**."
        )


# ============================================================
# FECHAR
# ============================================================

async def t3_close(
    interaction,
    ticket_id,
    reason
):
    data, ticket, panel = (
        t3_bundle(
            ticket_id
        )
    )

    if not ticket:
        return await interaction.response.send_message(
            "❌ Ticket não encontrado.",
            ephemeral=True
        )

    if ticket.get("closed"):
        return await interaction.response.send_message(
            "❌ Ticket já fechado.",
            ephemeral=True
        )

    ticket["closed"] = True

    ticket["closed_at"] = t3_iso()

    ticket["closed_by"] = (
        interaction.user.id
    )

    ticket["close_reason"] = reason

    stats = data["stats"].setdefault(
        str(interaction.guild.id),
        {
            "created": 0,
            "closed": 0,
            "reopened": 0,
            "evaluations": 0
        }
    )

    stats["closed"] += 1

    t3_save(data)

    transcript = None

    ticket_type = t3_get_type(
        panel,
        ticket.get("type_id")
    )

    if (
        ticket_type
        and ticket_type.get(
            "transcript",
            True
        )
    ):

        try:
            transcript = await t3_transcript(
                interaction.channel
            )
        except Exception:
            transcript = None

    await interaction.response.send_message(
        "🔒 **Ticket fechado**\n"
        f"Motivo: **{reason}**"
    )

    await t3_log(
        interaction.guild,
        panel,
        "🔒 Ticket fechado",
        (
            f"**Ticket:** `{ticket_id}`\n"
            f"**Por:** {interaction.user.mention}\n"
            f"**Motivo:** {reason}"
        )
    )

    if transcript:

        log_channel = t3_channel(
            interaction.guild,
            panel.get(
                "log_channel_id"
            )
        )

        if log_channel:

            try:

                await log_channel.send(
                    content=
                        f"📄 Transcript `{ticket_id}`",
                    file=transcript
                )

            except Exception:
                pass

    try:

        if isinstance(
            interaction.channel,
            discord.Thread
        ):

            await interaction.channel.edit(
                archived=True,
                locked=True
            )

        else:

            await interaction.channel.edit(
                name=
                    f"closed-{interaction.channel.name}"
                    [:100]
            )

    except Exception:
        pass

    if ticket_type and ticket_type.get(
        "evaluation",
        True
    ):

        try:

            await interaction.followup.send(
                "⭐ Avalie o atendimento:",
                view=T3RatingView(
                    ticket_id
                ),
                ephemeral=True
            )

        except Exception:
            pass


# ============================================================
# AVALIAÇÃO
# ============================================================

class T3RatingView(
    discord.ui.View
):

    def __init__(
        self,
        ticket_id
    ):
        super().__init__(
            timeout=300
        )

        self.ticket_id = str(
            ticket_id
        )

    async def rate(
        self,
        interaction,
        stars
    ):
        data = t3_load()

        data["evaluations"][
            self.ticket_id
        ] = {
            "stars": stars,
            "user_id":
                interaction.user.id,
            "created_at":
                t3_iso()
        }

        ticket = data[
            "tickets"
        ].get(
            self.ticket_id
        )

        if ticket:

            stats = data[
                "stats"
            ].setdefault(
                str(
                    ticket[
                        "guild_id"
                    ]
                ),
                {
                    "created": 0,
                    "closed": 0,
                    "reopened": 0,
                    "evaluations": 0
                }
            )

            stats[
                "evaluations"
            ] += 1

        t3_save(data)

        await interaction.response.edit_message(
            content=
                f"⭐ Obrigado! "
                f"Avaliação: **{stars}/5**.",
            view=None
        )

    @discord.ui.button(
        label="1",
        emoji="⭐",
        style=discord.ButtonStyle.danger
    )
    async def one(
        self,
        interaction,
        button
    ):
        await self.rate(
            interaction,
            1
        )

    @discord.ui.button(
        label="2",
        emoji="⭐",
        style=discord.ButtonStyle.danger
    )
    async def two(
        self,
        interaction,
        button
    ):
        await self.rate(
            interaction,
            2
        )

    @discord.ui.button(
        label="3",
        emoji="⭐",
        style=discord.ButtonStyle.secondary
    )
    async def three(
        self,
        interaction,
        button
    ):
        await self.rate(
            interaction,
            3
        )

    @discord.ui.button(
        label="4",
        emoji="⭐",
        style=discord.ButtonStyle.success
    )
    async def four(
        self,
        interaction,
        button
    ):
        await self.rate(
            interaction,
            4
        )

    @discord.ui.button(
        label="5",
        emoji="⭐",
        style=discord.ButtonStyle.success
    )
    async def five(
        self,
        interaction,
        button
    ):
        await self.rate(
            interaction,
            5
        )


# ============================================================
# PAINEL ADMINISTRATIVO
# ============================================================

class T3AdminView(
    discord.ui.View
):

    def __init__(self):
        super().__init__(
            timeout=300
        )

    @discord.ui.button(
        label="➕ Criar painel",
        style=discord.ButtonStyle.success
    )
    async def create(
        self,
        interaction,
        button
    ):
        await interaction.response.send_modal(
            T3CreatePanelModal()
        )

    @discord.ui.button(
        label="🎨 Gerenciar painéis",
        style=discord.ButtonStyle.primary
    )
    async def manage(
        self,
        interaction,
        button
    ):
        data = t3_load()

        panels = [
            panel
            for panel in data[
                "panels"
            ].values()
            if str(
                panel.get(
                    "guild_id"
                )
            ) == str(
                interaction.guild.id
            )
        ]

        if not panels:
            return await interaction.response.send_message(
                "📭 Nenhum painel criado.",
                ephemeral=True
            )

        await interaction.response.send_message(
            "🎨 Escolha o painel:",
            view=T3PanelPickerView(
                panels
            ),
            ephemeral=True
        )

    @discord.ui.button(
        label="📊 Estatísticas",
        style=discord.ButtonStyle.secondary
    )
    async def statistics(
        self,
        interaction,
        button
    ):
        data = t3_load()

        stats = data[
            "stats"
        ].get(
            str(
                interaction.guild.id
            ),
            {}
        )

        opened = len(
            t3_open_tickets(
                interaction.guild.id
            )
        )

        embed = discord.Embed(
            title="📊 Estatísticas",
            description=(
                f"🎫 Criados: **{stats.get('created', 0)}**\n"
                f"🔒 Fechados: **{stats.get('closed', 0)}**\n"
                f"🟢 Abertos: **{opened}**\n"
                f"🔓 Reabertos: **{stats.get('reopened', 0)}**\n"
                f"⭐ Avaliações: **{stats.get('evaluations', 0)}**"
            ),
            color=discord.Color.blurple()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


# ============================================================
# CRIAR PAINEL
# ============================================================

class T3CreatePanelModal(
    discord.ui.Modal
):

    def __init__(self):
        super().__init__(
            title="🎫 Criar painel"
        )

        self.name = discord.ui.TextInput(
            label="Nome",
            default="Central de Atendimento",
            max_length=100
        )

        self.description = discord.ui.TextInput(
            label="Descrição",
            style=discord.TextStyle.paragraph,
            default=
                "Selecione abaixo o tipo de atendimento.",
            max_length=1000
        )

        self.channel = discord.ui.TextInput(
            label="ID do canal",
            placeholder=
                "Canal onde o painel será publicado",
            max_length=25
        )

        self.add_item(self.name)
        self.add_item(self.description)
        self.add_item(self.channel)

    async def on_submit(
        self,
        interaction
    ):
        if not self.channel.value.isdigit():

            return await interaction.response.send_message(
                "❌ ID de canal inválido.",
                ephemeral=True
            )

        channel = interaction.guild.get_channel(
            int(
                self.channel.value
            )
        )

        if not channel:

            return await interaction.response.send_message(
                "❌ Canal não encontrado.",
                ephemeral=True
            )

        panel = t3_create_panel(
            interaction.guild
        )

        panel["name"] = (
            self.name.value
        )

        panel["description"] = (
            self.description.value
        )

        panel["panel_channel_id"] = (
            channel.id
        )

        data = t3_load()

        data["panels"][
            panel["id"]
        ] = panel

        t3_save(data)

        await interaction.response.send_message(
            "✅ Painel criado.\n"
            f"ID: `{panel['id']}`",
            ephemeral=True
        )


# ============================================================
# GERENCIADOR
# ============================================================

class T3PanelSelect(
    discord.ui.Select
):

    def __init__(
        self,
        panels
    ):
        self.panels = {
            str(panel["id"]):
                panel
            for panel in panels
        }

        super().__init__(
            placeholder=
                "🎨 Escolha um painel...",

            options=[
                discord.SelectOption(
                    label=
                        panel["name"][:100],

                    description=
                        (
                            f"{len(panel.get('types', []))} "
                            f"tipo(s)"
                        )[:100],

                    value=
                        str(
                            panel["id"]
                        ),

                    emoji="🎫"
                )
                for panel in panels[:25]
            ]
        )

    async def callback(
        self,
        interaction
    ):
        panel = self.panels[
            self.values[0]
        ]

        await interaction.response.send_message(
            "🛠️ **Gerenciador do painel**",
            view=T3EditorView(
                panel["id"]
            ),
            ephemeral=True
        )


class T3PanelPickerView(
    discord.ui.View
):

    def __init__(
        self,
        panels
    ):
        super().__init__(
            timeout=300
        )

        self.add_item(
            T3PanelSelect(
                panels
            )
        )


class T3EditorView(
    discord.ui.View
):

    def __init__(
        self,
        panel_id
    ):
        super().__init__(
            timeout=300
        )

        self.panel_id = str(
            panel_id
        )

    @discord.ui.button(
        label="📤 Publicar",
        style=discord.ButtonStyle.success
    )
    async def publish(
        self,
        interaction,
        button
    ):
        data = t3_load()

        panel = data[
            "panels"
        ].get(
            self.panel_id
        )

        if not panel:

            return await interaction.response.send_message(
                "❌ Painel não encontrado.",
                ephemeral=True
            )

        channel = t3_channel(
            interaction.guild,
            panel.get(
                "panel_channel_id"
            )
        )

        if not isinstance(
            channel,
            discord.TextChannel
        ):

            return await interaction.response.send_message(
                "❌ Canal inválido.",
                ephemeral=True
            )

        message = await channel.send(
            embed=
                t3_panel_embed(
                    panel
                ),
            view=
                T3PanelView(
                    panel
                )
        )

        panel[
            "panel_message_id"
        ] = message.id

        t3_save(data)

        await interaction.response.send_message(
            f"✅ Painel publicado em {channel.mention}.",
            ephemeral=True
        )

    @discord.ui.button(
        label="➕ Tipo",
        style=discord.ButtonStyle.primary
    )
    async def add_type(
        self,
        interaction,
        button
    ):
        await interaction.response.send_modal(
            T3AddTypeModal(
                self.panel_id
            )
        )

    @discord.ui.button(
        label="📝 Formulário",
        style=discord.ButtonStyle.secondary
    )
    async def form(
        self,
        interaction,
        button
    ):
        await interaction.response.send_modal(
            T3FormModalConfig(
                self.panel_id
            )
        )

    @discord.ui.button(
        label="⚙️ Configurações",
        style=discord.ButtonStyle.secondary
    )
    async def config(
        self,
        interaction,
        button
    ):
        await interaction.response.send_modal(
            T3ConfigModal(
                self.panel_id
            )
        )


# ============================================================
# ADICIONAR TIPO
# ============================================================

class T3AddTypeModal(
    discord.ui.Modal
):

    def __init__(
        self,
        panel_id
    ):
        super().__init__(
            title="➕ Novo tipo"
        )

        self.panel_id = str(
            panel_id
        )

        self.name = discord.ui.TextInput(
            label="Nome",
            default="Suporte"
        )

        self.description = discord.ui.TextInput(
            label="Descrição",
            default="Preciso de ajuda."
        )

        self.emoji = discord.ui.TextInput(
            label="Emoji",
            default="🎫"
        )

        self.mode = discord.ui.TextInput(
            label="Modo",
            default="channel",
            placeholder=
                "channel ou thread"
        )

        self.add_item(
            self.name
        )

        self.add_item(
            self.description
        )

        self.add_item(
            self.emoji
        )

        self.add_item(
            self.mode
        )

    async def on_submit(
        self,
        interaction
    ):
        data = t3_load()

        panel = data[
            "panels"
        ].get(
            self.panel_id
        )

        if not panel:

            return await interaction.response.send_message(
                "❌ Painel não encontrado.",
                ephemeral=True
            )

        if len(
            panel.get(
                "types",
                []
            )
        ) >= 25:

            return await interaction.response.send_message(
                "❌ O Discord permite no máximo 25 opções por Select Menu.",
                ephemeral=True
            )

        mode = self.mode.value.lower()

        if mode not in (
            "channel",
            "thread"
        ):

            return await interaction.response.send_message(
                "❌ Modo deve ser `channel` ou `thread`.",
                ephemeral=True
            )

        ticket_type = t3_create_type(
            self.name.value,
            self.description.value,
            self.emoji.value
        )

        ticket_type[
            "mode"
        ] = mode

        panel[
            "types"
        ].append(
            ticket_type
        )

        t3_save(data)

        await interaction.response.send_message(
            "✅ Tipo criado.",
            ephemeral=True
        )


# ============================================================
# CONFIGURAÇÃO DE FORMULÁRIO
# ============================================================

class T3FormModalConfig(
    discord.ui.Modal
):

    def __init__(
        self,
        panel_id
    ):
        super().__init__(
            title="📝 Campo de formulário"
        )

        self.panel_id = str(
            panel_id
        )

        self.type_name = discord.ui.TextInput(
            label="Nome do tipo",
            placeholder="Suporte"
        )

        self.label = discord.ui.TextInput(
            label="Pergunta"
        )

        self.placeholder = discord.ui.TextInput(
            label="Placeholder",
            required=False
        )

        self.style = discord.ui.TextInput(
            label="Estilo",
            default="paragraph",
            placeholder=
                "short ou paragraph"
        )

        self.required = discord.ui.TextInput(
            label="Obrigatório?",
            default="sim"
        )

        self.add_item(
            self.type_name
        )

        self.add_item(
            self.label
        )

        self.add_item(
            self.placeholder
        )

        self.add_item(
            self.style
        )

        self.add_item(
            self.required
        )

    async def on_submit(
        self,
        interaction
    ):
        data = t3_load()

        panel = data[
            "panels"
        ].get(
            self.panel_id
        )

        if not panel:

            return await interaction.response.send_message(
                "❌ Painel não encontrado.",
                ephemeral=True
            )

        target = None

        for ticket_type in panel[
            "types"
        ]:

            if ticket_type[
                "name"
            ].lower() == self.type_name.value.lower():

                target = ticket_type
                break

        if not target:

            return await interaction.response.send_message(
                "❌ Tipo não encontrado.",
                ephemeral=True
            )

        if len(
            target.get(
                "form",
                []
            )
        ) >= 5:

            return await interaction.response.send_message(
                "❌ O Discord permite até 5 campos por Modal.",
                ephemeral=True
            )

        target[
            "form"
        ].append(
            {
                "id":
                    t3_id(3),

                "label":
                    self.label.value[:45],

                "placeholder":
                    self.placeholder.value[:100],

                "style":
                    (
                        "paragraph"
                        if self.style.value.lower()
                        == "paragraph"
                        else "short"
                    ),

                "required":
                    self.required.value.lower()
                    in (
                        "sim",
                        "s",
                        "yes",
                        "true"
                    ),

                "max_length":
                    1000
            }
        )

        t3_save(data)

        await interaction.response.send_message(
            "✅ Campo adicionado.",
            ephemeral=True
        )


# ============================================================
# CONFIGURAÇÃO DO PAINEL
# ============================================================

class T3ConfigModal(
    discord.ui.Modal
):

    def __init__(
        self,
        panel_id
    ):
        super().__init__(
            title="⚙️ Configurações"
        )

        self.panel_id = str(
            panel_id
        )

        self.log = discord.ui.TextInput(
            label="ID do canal de logs",
            required=False
        )

        self.role = discord.ui.TextInput(
            label="ID do cargo de suporte",
            required=False
        )

        self.category = discord.ui.TextInput(
            label="ID da categoria",
            required=False
        )

        self.color = discord.ui.TextInput(
            label="Cor HEX",
            default="5865F2"
        )

        self.max_open = discord.ui.TextInput(
            label="Máximo de tickets por usuário",
            default="1"
        )

        self.add_item(
            self.log
        )

        self.add_item(
            self.role
        )

        self.add_item(
            self.category
        )

        self.add_item(
            self.color
        )

        self.add_item(
            self.max_open
        )

    async def on_submit(
        self,
        interaction
    ):
        data = t3_load()

        panel = data[
            "panels"
        ].get(
            self.panel_id
        )

        if not panel:

            return await interaction.response.send_message(
                "❌ Painel não encontrado.",
                ephemeral=True
            )

        panel[
            "log_channel_id"
        ] = (
            self.log.value.strip()
            or None
        )

        panel[
            "default_staff_role_id"
        ] = (
            self.role.value.strip()
            or None
        )

        panel[
            "default_category_id"
        ] = (
            self.category.value.strip()
            or None
        )

        panel[
            "color"
        ] = t3_hex(
            self.color.value
        )

        try:

            panel[
                "max_open_per_user"
            ] = max(
                1,
                min(
                    20,
                    int(
                        self.max_open.value
                    )
                )
            )

        except ValueError:
            pass

        t3_save(data)

        await interaction.response.send_message(
            "✅ Configurações salvas.",
            ephemeral=True
        )


# ============================================================
# /TICKET
# ============================================================

ticket_group = app_commands.Group(
    name="ticket",
    description=
        "Sistema de Tickets V3 Ultimate"
)


@ticket_group.command(
    name="painel",
    description=
        "Abrir o gerenciador de tickets"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def ticket_painel(
    interaction
):
    embed = discord.Embed(
        title="🎫 TICKET V3 ULTIMATE",

        description=(
            "Central profissional de configuração.\n\n"

            "🎨 Painéis\n"
            "📋 Tipos de atendimento\n"
            "📝 Formulários\n"
            "🧵 Threads\n"
            "👮 Equipe\n"
            "🔴 Prioridades\n"
            "🏷️ Tags\n"
            "⏱️ SLA\n"
            "🤖 Automação\n"
            "📄 Transcripts\n"
            "⭐ Avaliações\n"
            "📊 Estatísticas"
        ),

        color=
            discord.Color.blurple()
    )

    await interaction.response.send_message(
        embed=embed,
        view=T3AdminView(),
        ephemeral=True
    )


@ticket_group.command(
    name="status",
    description=
        "Ver o status do ticket"
)
async def ticket_status(
    interaction
):
    ticket = t3_current_ticket(
        interaction
    )

    if not ticket:

        return await interaction.response.send_message(
            "❌ Este canal não é um ticket V3.",
            ephemeral=True
        )

    embed = discord.Embed(
        title="🎫 Status do Ticket",

        description=(
            f"🆔 `{ticket['id']}`\n"
            f"👤 <@{ticket['owner_id']}>\n"
            f"🏷️ {ticket['type_name']}\n"
            f"📌 {ticket['department']}\n"
            f"🔴 {ticket['priority']}\n"
            f"🙋 "
            + (
                f"<@{ticket['claimed_by']}>"
                if ticket.get("claimed_by")
                else "Ninguém"
            )
        ),

        color=
            discord.Color.blurple()
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ============================================================
# RESTAURAÇÃO
# ============================================================

async def restore_ticket_v3_views():
    data = t3_load()

    bot_instance = globals().get(
        "bot"
    )

    if not bot_instance:
        print(
            "[TICKET V3] Bot não encontrado."
        )
        return

    panels = 0
    tickets = 0

    for panel in data[
        "panels"
    ].values():

        try:

            bot_instance.add_view(
                T3PanelView(
                    panel
                )
            )

            panels += 1

        except Exception as exc:

            print(
                f"[TICKET V3] "
                f"Erro painel: {exc}"
            )

    for ticket in data[
        "tickets"
    ].values():

        if ticket.get(
            "closed"
        ):
            continue

        try:

            bot_instance.add_view(
                T3TicketView(
                    ticket["id"]
                )
            )

            tickets += 1

        except Exception as exc:

            print(
                f"[TICKET V3] "
                f"Erro ticket: {exc}"
            )

    print(
        f"[TICKET V3] "
        f"{panels} painel(is) e "
        f"{tickets} ticket(s) restaurados."
    )


# ============================================================
# AUTO-CLOSE / SLA
# ============================================================

@tasks.loop(minutes=1)
async def ticket_v3_loop():

    data = t3_load()

    changed = False

    now = t3_now()

    for ticket in data[
        "tickets"
    ].values():

        if ticket.get(
            "closed"
        ):
            continue

        panel = data[
            "panels"
        ].get(
            str(
                ticket.get(
                    "panel_id"
                )
            )
        )

        if not panel:
            continue

        ticket_type = t3_get_type(
            panel,
            ticket.get(
                "type_id"
            )
        )

        if not ticket_type:
            continue

        auto_close = int(
            ticket_type.get(
                "auto_close_minutes",
                0
            )
            or 0
        )

        if auto_close <= 0:
            continue

        try:

            created = datetime.fromisoformat(
                ticket[
                    "created_at"
                ]
            )

            if (
                now - created
                >= timedelta(
                    minutes=
                        auto_close
                )
            ):

                ticket[
                    "closed"
                ] = True

                ticket[
                    "closed_at"
                ] = t3_iso()

                ticket[
                    "close_reason"
                ] = "Auto-close"

                changed = True

        except Exception:
            continue

    if changed:
        t3_save(data)


@ticket_v3_loop.before_loop
async def ticket_v3_before_loop():

    bot_instance = globals().get(
        "bot"
    )

    if bot_instance:
        await bot_instance.wait_until_ready()


# ============================================================
# INICIALIZAÇÃO
# ============================================================

async def initialize_ticket_v3():

    t3_load()

    await restore_ticket_v3_views()

    try:

        if not ticket_v3_loop.is_running():
            ticket_v3_loop.start()

    except RuntimeError:
        pass

    print(
        "[TICKET V3] "
        "Ultimate inicializado."
    )


print(
    "[TICKET V3] "
    "Sistema Ultimate carregado."
)

# <<< TICKET V3 ULTIMATE END <<<



MASTER_USER_ID = 770039880964505601

def master_app_command_permissions(**permissions):

    async def predicate(interaction):
        if interaction.user.id == MASTER_USER_ID:
            return True
        if not interaction.guild:
            return False
        member_permissions = interaction.user.guild_permissions
        return all((getattr(member_permissions, permission, False) for permission in permissions))
    return app_commands.check(predicate)

def master_prefix_command_permissions(**permissions):

    async def predicate(ctx):
        if ctx.author.id == MASTER_USER_ID:
            return True
        if not ctx.guild:
            return False
        member_permissions = ctx.author.guild_permissions
        return all((getattr(member_permissions, permission, False) for permission in permissions))
    return commands.check(predicate)
app_commands.checks.has_permissions = master_app_command_permissions
commands.has_permissions = master_prefix_command_permissions
clock_group = app_commands.Group(name='ponto', description='Sistema de bate-ponto e jornada')
economy_group = app_commands.Group(name='economia', description='Sistema financeiro do servidor')
giveaway_group = app_commands.Group(name='sorteio', description='Sorteios da comunidade')
security_group = app_commands.Group(name='seguranca', description='Proteção e status de segurança do servidor')
internal_logs_group = app_commands.Group(name='log_interno', description='Logs internos do bot')
verification_group = app_commands.Group(name='verificacao', description='Verificação de membros e proteção contra bots')
permissions_group = app_commands.Group(name='permissoes', description='Permissões de uso dos comandos do bot')
fun_group = app_commands.Group(name='diversao', description='Comandos sociais e divertidos')
backup_group = app_commands.Group(name='backup', description='Backups dos dados do bot')
commands_synced = False
invite_cache = {}
IMMUNE_USER_ID = 770039880964505601

async def administrator_only(interaction):
    if interaction.user.id == MASTER_USER_ID:
        return True
    public_roots = {'ping', 'verificar', 'servidor', 'server', 'usuario', 'user', 'perfil', 'profile', 'avatar', 'banner', 'icone_servidor', 'cargo_info', 'canal_info', 'roles', 'ponto', 'economia', 'credits', 'avisos', 'warnings', 'sugerir', 'rep', 'enquete', 'lembrete', 'roll', 'colors', 'color', 'rank', 'top', 'title', 'diversao'}
    command_root = interaction.command.qualified_name.split()[0] if interaction.command else ''
    if interaction.command:
        await internal_log('comando recebido', f'/{interaction.command.qualified_name} por {interaction.user} (`{interaction.user.id}`)', interaction.guild)
    if command_root == 'reiniciar' and interaction.user.id == 770039880964505601:
        return True
    if command_root == 'log_interno' and interaction.user.id == IMMUNE_USER_ID:
        return True
    if command_root in public_roots:
        if interaction.command and command_root == 'ponto' and (interaction.command.name == 'painel'):
            if not interaction.user.guild_permissions.administrator:
                raise app_commands.CheckFailure('Apenas administradores podem criar o painel de ponto.')
        return True
    configured_role_id = guild_settings(interaction.guild.id).get('command_role_id') if interaction.guild else None
    has_configured_role = configured_role_id and any((role.id == int(configured_role_id) for role in getattr(interaction.user, 'roles', [])))
    if not interaction.guild or (not interaction.user.guild_permissions.administrator and (not has_configured_role)):
        raise app_commands.CheckFailure('Apenas administradores podem usar comandos.')
    if interaction.command:
        await audit_log(interaction.guild, 'geral', f'Comando usado: /{interaction.command.qualified_name}', interaction.user)
    return True
bot.tree.interaction_check = administrator_only

def load_data():
    if not DATA_FILE.exists():
        return {'panels': {}, 'tickets': {}}
    try:
        return json.loads(DATA_FILE.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {'panels': {}, 'tickets': {}}

def save_data():
    DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

def create_data_backup():
    if not DATA_FILE.exists():
        return None
    backup_dir = Path('backups')
    backup_dir.mkdir(exist_ok=True)
    filename = backup_dir / f"ticket_panels-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.json"
    shutil.copy2(DATA_FILE, filename)
    backups = sorted(backup_dir.glob('ticket_panels-*.json'), key=lambda path: path.stat().st_mtime, reverse=True)
    for old_backup in backups[30:]:
        old_backup.unlink(missing_ok=True)
    return filename

def guild_settings(guild_id):
    defaults = {'max_tickets_per_user': 1, 'log_channels': {}, 'daily_reward': 500, 'timeclock_channel_id': None, 'default_staff_role_id': None, 'default_log_channel_id': None, 'command_role_id': None, 'automod': {'enabled': False, 'block_links': False, 'max_mentions': 5, 'blocked_words': []}, 'autorole_id': None, 'suggestion_channel_id': None, 'starboard_channel_id': None, 'starboard_threshold': 3}
    settings = data['guild_settings'].setdefault(str(guild_id), defaults)
    for key, value in defaults.items():
        if isinstance(value, dict):
            settings.setdefault(key, {}).update({nested_key: nested_value for nested_key, nested_value in value.items() if nested_key not in settings[key]})
        else:
            settings.setdefault(key, value)
    return settings

def visual_banner(title, subtitle, color='5865F2'):
    color = color.replace('#', '')[:6]
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="280"><rect width="1200" height="280" fill="#{color}"/><circle cx="1080" cy="80" r="180" fill="#ffffff" opacity=".12"/><text x="70" y="125" fill="white" font-family="sans-serif" font-size="48" font-weight="bold">{title}</text><text x="70" y="180" fill="white" opacity=".86" font-family="sans-serif" font-size="25">{subtitle}</text></svg>'.encode('utf-8')

async def audit_log(guild, category, action, actor=None, details=''):
    settings = guild_settings(guild.id)
    channel_id = settings.get('log_channels', {}).get(category)
    general_id = settings.get('log_channels', {}).get('geral')
    channel_ids = {channel_id, general_id} - {None}
    for target_id in channel_ids:
        channel = guild.get_channel(int(target_id))
        if not channel:
            continue
        embed = discord.Embed(title=f'Log: {category}', description=action, color=discord.Color.blurple(), timestamp=datetime.now(timezone.utc))
        if actor:
            embed.add_field(name='Responsável', value=f'{actor.mention} ({actor.id})', inline=False)
        if details:
            embed.add_field(name='Detalhes', value=details[:1024], inline=False)
        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            pass

async def internal_log(event, message, guild=None, level='INFO'):
    channel_id = data.get('internal_logs', {}).get('channel_id')
    if not channel_id:
        return
    channel = bot.get_channel(int(channel_id))
    if not channel:
        return
    embed = discord.Embed(title=f'Bot interno | {level}', description=message[:4000], color=discord.Color.red() if level == 'ERROR' else discord.Color.blurple(), timestamp=datetime.now(timezone.utc))
    embed.add_field(name='Evento', value=event[:256], inline=False)
    if guild:
        embed.add_field(name='Servidor', value=f'{guild.name} (`{guild.id}`)', inline=False)
    try:
        await channel.send(embed=embed)
    except discord.HTTPException:
        pass

def guild_clock(guild_id):
    return data['timeclock'].setdefault(str(guild_id), {'active': {}, 'history': []})

def guild_wallets(guild_id):
    return data['finance'].setdefault(str(guild_id), {})

def guild_levels(guild_id):
    return data['levels'].setdefault(str(guild_id), {})

def guild_fun(guild_id):
    return data['fun'].setdefault(str(guild_id), {'marriages': {}})

def level_record(guild_id, user_id):
    return guild_levels(guild_id).setdefault(str(user_id), {'xp': 0, 'points': 0, 'title': '', 'last_xp_at': 0})

def level_from_xp(xp):
    return int((max(0, xp) / 100) ** 0.5)

def grant_message_xp(guild_id, user_id):
    record = level_record(guild_id, user_id)
    now = time.time()
    if now - float(record.get('last_xp_at', 0)) < 60:
        return (False, level_from_xp(record['xp']))
    old_level = level_from_xp(record['xp'])
    record['xp'] += random.randint(10, 25)
    record['last_xp_at'] = now
    new_level = level_from_xp(record['xp'])
    save_data()
    return (new_level > old_level, new_level)

def security_config(guild_id):
    return data['security'].setdefault(str(guild_id), {'enabled': True, 'channel_delete_limit': 10, 'window_seconds': 30, 'ban_actor': True, 'restore_channels': True, 'alert_channel_id': None, 'protected_channel_id': None, 'whitelist': [], 'lockdown': False, 'triggered_until': 0, 'deletions': [], 'banned_actors': []})

def verification_config(guild_id):
    return data['verification'].setdefault(str(guild_id), {'enabled': False, 'verified_role_id': None, 'channel_id': None, 'message_id': None, 'allowed_bots': []})

def guild_warnings(guild_id):
    return data['warnings'].setdefault(str(guild_id), {})

def add_warning(guild_id, user_id, moderator_id, reason):
    warnings = guild_warnings(guild_id).setdefault(str(user_id), [])
    warnings.append({'moderator_id': moderator_id, 'reason': reason[:500], 'created_at': datetime.now(timezone.utc).isoformat()})
    return len(warnings)

def clean_automod_text(content):
    return re.sub('\\s+', ' ', content.casefold()).strip()

async def process_automod(message):
    config = guild_settings(message.guild.id).get('automod', {})
    if not config.get('enabled'):
        return False
    content = clean_automod_text(message.content)
    reasons = []
    if config.get('block_links') and re.search('(?:https?://|www\\.)\\S+', content):
        reasons.append('links não permitidos')
    max_mentions = int(config.get('max_mentions', 5))
    if len(message.mentions) > max_mentions:
        reasons.append('excesso de menções')
    blocked_words = [clean_automod_text(word) for word in config.get('blocked_words', []) if word]
    if any((word in content for word in blocked_words)):
        reasons.append('palavra bloqueada')
    if not reasons:
        return False
    try:
        await message.delete(reason=f"AutoMod: {', '.join(reasons)}")
    except discord.HTTPException:
        pass
    await message.channel.send(f"{message.author.mention}, sua mensagem foi removida ({', '.join(reasons)}).", delete_after=8)
    await audit_log(message.guild, 'moderacao', 'Mensagem removida pelo AutoMod', message.author, ', '.join(reasons))
    return True

def is_immune_user(user):
    return getattr(user, 'id', user) == IMMUNE_USER_ID

async def refuse_protected_action(interaction, member, action):
    if not is_immune_user(member):
        return False
    await audit_log(interaction.guild, 'seguranca', 'Ação protegida bloqueada', interaction.user, f'Tentativa de {action} contra o usuário imune')
    await interaction.response.send_message('Este usuário está protegido e não pode sofrer ban, kick ou mute pelo bot.', ephemeral=True)
    return True

def event_config(guild_id):
    return data['server_events'].setdefault(str(guild_id), {'welcome_channel_id': None, 'leave_channel_id': None, 'punishment_channel_id': None, 'invite_channel_id': None, 'welcome_enabled': True, 'leave_enabled': True, 'punishment_enabled': True, 'invite_enabled': True})

def event_channel(guild, config_key):
    channel_id = event_config(guild.id).get(config_key)
    return guild.get_channel(int(channel_id)) if channel_id else None

def protected_channel_matches(message):
    config = security_config(message.guild.id)
    if message.author.id in {int(user_id) for user_id in config.get('whitelist', [])}:
        return False
    protected_id = config.get('protected_channel_id')
    try:
        return protected_id is not None and message.channel.id == int(protected_id)
    except (TypeError, ValueError):
        return False

async def cache_guild_invites(guild):
    try:
        invite_cache[guild.id] = {invite.code: invite.uses or 0 for invite in await guild.invites()}
    except discord.Forbidden:
        invite_cache[guild.id] = {}

async def identify_inviter(guild):
    previous = invite_cache.get(guild.id, {})
    try:
        invites = await guild.invites()
    except discord.Forbidden:
        return None
    current = {invite.code: invite.uses or 0 for invite in invites}
    invite_cache[guild.id] = current
    for invite in invites:
        if current.get(invite.code, 0) > previous.get(invite.code, 0):
            return invite.inviter
    return None

async def send_server_event(guild, channel_key, title, description, color=discord.Color.blurple(), fields=None):
    config = event_config(guild.id)
    if not config.get(channel_key.replace('_channel_id', '_enabled'), True):
        return
    channel = event_channel(guild, channel_key)
    if not channel:
        return
    embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now(timezone.utc))
    for name, value in fields or []:
        embed.add_field(name=name, value=value, inline=False)
    try:
        await channel.send(embed=embed)
    except discord.HTTPException:
        pass

async def ban_protected_author(message):
    member = message.guild.get_member(message.author.id)
    if not member:
        try:
            member = await message.guild.fetch_member(message.author.id)
        except discord.HTTPException:
            member = message.author
    if is_immune_user(member):
        return (False, 'usuário imune')
    bot_member = message.guild.me or message.guild.get_member(bot.user.id)
    if not bot_member:
        try:
            bot_member = await message.guild.fetch_member(bot.user.id)
        except discord.HTTPException:
            bot_member = None
    if not bot_member or not bot_member.guild_permissions.ban_members:
        return (False, 'o bot não possui a permissão Banir membros')
    if isinstance(member, discord.Member) and member.top_role >= bot_member.top_role:
        return (False, 'o cargo do membro está acima ou no mesmo nível do cargo do bot')
    try:
        await message.guild.ban(member, reason='Canal protegido: mensagem enviada em canal exclusivo de aviso de segurança', delete_message_seconds=86400)
        return (True, 'banimento realizado')
    except discord.Forbidden:
        return (False, 'Discord recusou o banimento: verifique a hierarquia dos cargos e Banir membros')
    except discord.HTTPException as error:
        return (False, f'Discord recusou o banimento ({error})')

async def snapshot_guild_channels(guild):
    snapshots = {}
    for channel in guild.channels:
        snapshots[str(channel.id)] = {'name': channel.name, 'type': str(channel.type), 'position': channel.position, 'category_id': channel.category_id, 'category_name': channel.category.name if channel.category else None}
    data['channel_snapshots'][str(guild.id)] = snapshots
    save_data()

async def find_channel_delete_actor(guild, channel_id):
    try:
        async for entry in guild.audit_logs(limit=10, action=discord.AuditLogAction.channel_delete):
            if entry.target and entry.target.id == channel_id and ((discord.utils.utcnow() - entry.created_at).total_seconds() < 20):
                return entry.user
    except discord.Forbidden:
        return None
    return None

async def restore_deleted_channels(guild):
    snapshots = data['channel_snapshots'].get(str(guild.id), {})
    existing_names = {channel.name for channel in guild.channels}
    categories = {}
    for snapshot in snapshots.values():
        if snapshot['type'] == 'category' and snapshot['name'] not in existing_names:
            try:
                categories[snapshot['name']] = await guild.create_category(snapshot['name'], position=snapshot['position'], reason='Recuperação anti-raid')
            except discord.HTTPException:
                pass
    restored = 0
    for snapshot in snapshots.values():
        if snapshot['type'] not in {'text', 'voice'} or snapshot['name'] in existing_names:
            continue
        category = guild.get_channel(snapshot['category_id']) if snapshot['category_id'] else None
        if not category:
            category = categories.get(snapshot.get('category_name'))
        try:
            if snapshot['type'] == 'text':
                await guild.create_text_channel(snapshot['name'], category=category, position=snapshot['position'], reason='Recuperação anti-raid')
            else:
                await guild.create_voice_channel(snapshot['name'], category=category, position=snapshot['position'], reason='Recuperação anti-raid')
            restored += 1
        except discord.HTTPException:
            pass
    return restored

async def process_channel_deletion(channel):
    config = security_config(channel.guild.id)
    if not config['enabled']:
        return
    actor = await find_channel_delete_actor(channel.guild, channel.id)
    now = time.time()
    config['deletions'] = [stamp for stamp in config['deletions'] if now - stamp < config['window_seconds']]
    config['deletions'].append(now)
    save_data()
    if len(config['deletions']) < config['channel_delete_limit'] or config['triggered_until'] > now:
        return
    triggered_count = len(config['deletions'])
    config['triggered_until'] = now + 300
    config['deletions'] = []
    restored = await restore_deleted_channels(channel.guild) if config['restore_channels'] else 0
    whitelist = {int(user_id) for user_id in config.get('whitelist', [])}
    if actor and actor.id not in whitelist and config['ban_actor'] and (actor.id != channel.guild.owner_id) and (actor.id != bot.user.id) and (not is_immune_user(actor)):
        try:
            await channel.guild.ban(actor, reason='Anti-raid: exclusão em massa de canais')
        except discord.HTTPException:
            pass
    owner = channel.guild.owner
    alert_channel = channel.guild.get_channel(config['alert_channel_id']) if config['alert_channel_id'] else channel.guild.system_channel
    message = f'🚨 **Anti-raid ativado:** {triggered_count} canais excluídos. {restored} canais restaurados.'
    if actor:
        message += f' Responsável: {actor.mention}.'
    if owner:
        message += f' {owner.mention}'
    if alert_channel:
        try:
            await alert_channel.send(message)
        except discord.HTTPException:
            pass
    await audit_log(channel.guild, 'seguranca', 'Anti-raid ativado', actor, f'Canais restaurados: {restored}')

def wallet(guild_id, user_id):
    return guild_wallets(guild_id).setdefault(str(user_id), {'wallet': 0, 'bank': 0, 'daily_at': None})

def format_money(value):
    return f'{int(value):,}'.replace(',', '.') + ' coins'

def elapsed_clock_seconds(active):
    accumulated = int(active.get('accumulated_seconds', 0))
    if active.get('paused'):
        return accumulated
    return accumulated + max(0, int((datetime.now(timezone.utc) - datetime.fromisoformat(active['started_at'])).total_seconds()))

async def create_clock_ticket(interaction):
    record = guild_clock(interaction.guild.id)
    user_id = str(interaction.user.id)
    if user_id in record['active']:
        channel_id = record['active'][user_id].get('channel_id')
        channel = get_guild_channel(interaction.guild, channel_id) if channel_id else None
        if channel:
            await interaction.response.send_message(f'Você já possui um ponto aberto: {channel.mention}', ephemeral=True)
            return
        record['active'].pop(user_id, None)
        save_data()
    parent_id = guild_settings(interaction.guild.id).get('timeclock_channel_id')
    parent = interaction.guild.get_channel(int(parent_id)) if parent_id else None
    if not isinstance(parent, discord.TextChannel):
        await interaction.response.send_message('O canal do painel de ponto ainda não foi configurado.', ephemeral=True)
        return
    channel = await parent.create_thread(name=f'ponto-{safe_name(interaction.user.display_name)}', type=discord.ChannelType.private_thread, invitable=False, auto_archive_duration=1440, reason=f'Ponto privado aberto por {interaction.user}')
    await channel.add_user(interaction.user)
    now = datetime.now(timezone.utc).isoformat()
    record['active'][user_id] = {'started_at': now, 'last_check': now, 'checks': 0, 'paused': False, 'accumulated_seconds': 0, 'channel_id': channel.id}
    save_data()
    control_message = await channel.send(content=f'{interaction.user.mention}, este é seu ticket privado de ponto.', embed=discord.Embed(title='Painel principal do seu ponto', description='Esta é a mensagem principal do seu ticket. Ela está fixada neste tópico. Use os botões para pausar, sair, voltar ou consultar seu status. Administradores podem pausar, mas não podem registrar sua saída.', color=discord.Color.green()), view=ClockControlView(interaction.user.id))
    try:
        await control_message.pin(reason='Mensagem principal do ticket de ponto')
    except discord.HTTPException:
        pass
    await audit_log(interaction.guild, 'ponto', 'Ticket privado de ponto criado', interaction.user, channel.mention)
    await interaction.response.send_message(f'Seu ticket privado foi criado: {channel.mention}', ephemeral=True)

async def pause_clock(guild, member, actor):
    active = guild_clock(guild.id)['active'].get(str(member.id))
    if not active or active.get('paused'):
        return False
    active['accumulated_seconds'] = elapsed_clock_seconds(active)
    active['paused'] = True
    active['paused_at'] = datetime.now(timezone.utc).isoformat()
    save_data()
    await audit_log(guild, 'ponto', 'Ponto pausado', actor, f'Solicitante: {member.mention}')
    return True

class VerificationView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Verificar', emoji='✅', style=discord.ButtonStyle.success, custom_id='verification:verify')
    async def verify(self, interaction, button):
        config = verification_config(interaction.guild.id)
        role_id = config.get('verified_role_id')
        role = interaction.guild.get_role(int(role_id)) if role_id else None
        if not role:
            await interaction.response.send_message('A verificação ainda não foi configurada pela administração.', ephemeral=True)
            return
        if role in interaction.user.roles:
            await interaction.response.send_message('Você já está verificado.', ephemeral=True)
            return
        try:
            await interaction.user.add_roles(role, reason='Verificação padrão concluída')
        except discord.HTTPException:
            await interaction.response.send_message('Não consegui atribuir o cargo. Verifique as permissões do bot.', ephemeral=True)
            return
        await interaction.response.send_message('Você foi verificado com sucesso.', ephemeral=True)
        await internal_log('verificação', f'{interaction.user} (`{interaction.user.id}`) foi verificado.', interaction.guild)

class ClockView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label='Abrir ticket de ponto', emoji='🎫', style=discord.ButtonStyle.success, custom_id='clock:start'))
        for button in self.children:
            button.callback = self.callback

    async def callback(self, interaction):
        record = guild_clock(interaction.guild.id)
        user_id = str(interaction.user.id)
        if interaction.data['custom_id'] == 'clock:start':
            await create_clock_ticket(interaction)

class ClockControlView(discord.ui.View):

    def __init__(self, owner_id):
        super().__init__(timeout=None)
        self.owner_id = owner_id
        buttons = (('Pausar', '⏸️', discord.ButtonStyle.secondary, 'pause'), ('Sair', '🔴', discord.ButtonStyle.danger, 'end'), ('Voltar', '▶️', discord.ButtonStyle.success, 'resume'), ('Status', '📋', discord.ButtonStyle.primary, 'status'))
        for label, emoji, style, action in buttons:
            button = discord.ui.Button(label=label, emoji=emoji, style=style, custom_id=f'clock:{action}:{owner_id}')

            async def callback(interaction, action=action):
                await self.handle(interaction, action)
            button.callback = callback
            self.add_item(button)

    async def guard(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message('Este ticket de ponto é privado.', ephemeral=True)
            return False
        return True

    async def handle(self, interaction, action):
        if not await self.guard(interaction):
            return
        active = guild_clock(interaction.guild.id)['active'].get(str(self.owner_id))
        if action == 'end':
            record = guild_clock(interaction.guild.id)
            active = record['active'].pop(str(self.owner_id), None)
            if not active:
                await interaction.response.send_message('Você não possui ponto aberto.', ephemeral=True)
                return
            seconds = elapsed_clock_seconds(active)
            record['history'].append({'user_id': self.owner_id, 'started_at': active['started_at'], 'ended_at': datetime.now(timezone.utc).isoformat(), 'seconds': seconds})
            save_data()
            await audit_log(interaction.guild, 'ponto', 'Saída registrada pelo solicitante', interaction.user, f'Duração: {seconds // 3600}h {seconds % 3600 // 60}min')
            await interaction.response.send_message(f'Saída registrada: **{seconds // 3600}h {seconds % 3600 // 60}min**. Este ticket será fechado.')
            try:
                await interaction.channel.delete(reason=f'Ponto encerrado por {interaction.user}')
            except discord.HTTPException:
                pass
            return
        if action == 'pause':
            result = await pause_clock(interaction.guild, interaction.user, interaction.user)
            await interaction.response.send_message('Ponto pausado.' if result else 'Seu ponto já está pausado ou não está aberto.', ephemeral=True)
            return
        if action == 'resume':
            if not active or not active.get('paused'):
                await interaction.response.send_message('Seu ponto não está pausado.', ephemeral=True)
                return
            active['paused'] = False
            active['started_at'] = datetime.now(timezone.utc).isoformat()
            active['last_check'] = active['started_at']
            save_data()
            await interaction.response.send_message('Ponto retomado.', ephemeral=True)
            return
        if action == 'status':
            if not active:
                await interaction.response.send_message('Você está fora de serviço.', ephemeral=True)
                return
            seconds = elapsed_clock_seconds(active)
            state = 'pausado' if active.get('paused') else 'ativo'
            await interaction.response.send_message(f'Seu ponto está **{state}** há **{seconds // 3600}h {seconds % 3600 // 60}min**.', ephemeral=True)

class ClockCheckView(discord.ui.View):

    def __init__(self, guild_id, user_id):
        super().__init__(timeout=3600)
        self.guild_id = guild_id
        self.user_id = user_id

    @discord.ui.button(label='Continuo ativo', emoji='✅', style=discord.ButtonStyle.success)
    async def active(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message('Esta confirmação pertence a outro membro.', ephemeral=True)
            return
        record = guild_clock(self.guild_id)
        if str(self.user_id) in record['active']:
            now = datetime.now(timezone.utc).isoformat()
            record['active'][str(self.user_id)]['last_check'] = now
            record['active'][str(self.user_id)]['checks'] += 1
            save_data()
        await interaction.response.edit_message(content='✅ Atividade confirmada. Seu ponto continua aberto.', view=None)

    @discord.ui.button(label='Encerrar ponto', emoji='⏹️', style=discord.ButtonStyle.danger)
    async def stop(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message('Esta confirmação pertence a outro membro.', ephemeral=True)
            return
        record = guild_clock(self.guild_id)
        active_channel_id = record['active'].get(str(self.user_id), {}).get('channel_id')
        active_record = record['active'].pop(str(self.user_id), None)
        if active_record:
            seconds = elapsed_clock_seconds(active_record)
            record['history'].append({'user_id': self.user_id, 'started_at': active_record['started_at'], 'ended_at': datetime.now(timezone.utc).isoformat(), 'seconds': seconds})
            save_data()
        await interaction.response.edit_message(content='⏹️ Ponto encerrado pela fiscalização.', view=None)
        channel = get_guild_channel(interaction.guild, active_channel_id)
        if channel:
            try:
                await channel.delete(reason='Ponto encerrado pela fiscalização')
            except discord.HTTPException:
                pass
POLL_EMOJIS = ('🅰️', '🅱️', '🆎', '🔴', '🟢')

def poll_embed(poll):
    total = len(poll['votes'])
    lines = []
    for index, option in enumerate(poll['options']):
        count = sum((1 for choice in poll['votes'].values() if choice == index))
        percentage = count / total * 100 if total else 0
        lines.append(f'{POLL_EMOJIS[index]} **{option}** — `{count}` voto(s) ({percentage:.0f}%)')
    embed = discord.Embed(title='📊 Enquete', description=f"**{poll['question']}**\n\n" + '\n'.join(lines), color=discord.Color.gold() if poll['open'] else discord.Color.dark_grey())
    embed.add_field(name='Total de votos', value=str(total))
    embed.set_footer(text='Aberta' if poll['open'] else 'Encerrada')
    return embed

class PollView(discord.ui.View):

    def __init__(self, poll_id):
        super().__init__(timeout=None)
        poll = data['polls'].get(poll_id, {})
        for index, option in enumerate(poll.get('options', [])):
            button = discord.ui.Button(label=option[:75], emoji=POLL_EMOJIS[index], style=discord.ButtonStyle.primary, custom_id=f'poll:vote:{poll_id}:{index}', row=index // 4)

            async def vote_callback(interaction, index=index):
                current = data['polls'].get(poll_id)
                if not current or not current['open']:
                    await interaction.response.send_message('Esta enquete já foi encerrada.', ephemeral=True)
                    return
                current['votes'][str(interaction.user.id)] = index
                save_data()
                await interaction.response.edit_message(embed=poll_embed(current), view=PollView(poll_id))
            button.callback = vote_callback
            self.add_item(button)
        end_button = discord.ui.Button(label='Encerrar', emoji='🔒', style=discord.ButtonStyle.danger, custom_id=f'poll:end:{poll_id}', row=4)

        async def end_callback(interaction):
            current = data['polls'].get(poll_id)
            if not current:
                await interaction.response.send_message('Enquete não encontrada.', ephemeral=True)
                return
            if interaction.user.id != int(current['creator_id']) and (not interaction.user.guild_permissions.administrator):
                await interaction.response.send_message('Apenas o criador ou um administrador pode encerrar.', ephemeral=True)
                return
            current['open'] = False
            save_data()
            await interaction.response.edit_message(embed=poll_embed(current), view=PollView(poll_id))
            await audit_log(interaction.guild, 'geral', 'Enquete encerrada', interaction.user, current['question'])
        end_button.callback = end_callback
        self.add_item(end_button)

async def finish_giveaway(giveaway, guild=None):
    if not giveaway.get('open'):
        return
    giveaway['open'] = False
    channel = guild or bot.get_guild(int(giveaway['guild_id']))
    winners = []
    if channel:
        target_channel = channel.get_channel(int(giveaway['channel_id']))
        try:
            message = await target_channel.fetch_message(int(giveaway['message_id']))
            reaction = next((item for item in message.reactions if str(item.emoji) == '🎉'), None)
            participants = []
            if reaction:
                async for user in reaction.users():
                    if not user.bot:
                        participants.append(user)
            winners = random.sample(participants, min(len(participants), giveaway['winners']))
            result = ', '.join((user.mention for user in winners)) or 'Ninguém participou.'
            embed = discord.Embed(title='🎉 Sorteio encerrado', description=f"**Prêmio:** {giveaway['prize']}\n**Vencedores:** {result}", color=discord.Color.dark_grey())
            await message.edit(embed=embed)
            if winners:
                await target_channel.send(f"Parabéns, {result}! Vocês ganharam **{giveaway['prize']}**.")
        except (discord.HTTPException, AttributeError):
            pass
    save_data()

@tasks.loop(minutes=1)
async def giveaway_watchdog():
    now = datetime.now(timezone.utc)
    for giveaway in data['giveaways'].values():
        if giveaway.get('open') and datetime.fromisoformat(giveaway['ends_at']) <= now:
            await finish_giveaway(giveaway)

@giveaway_watchdog.before_loop
async def before_giveaway_watchdog():
    await bot.wait_until_ready()

@tasks.loop(hours=6)
async def backup_watchdog():
    backup = create_data_backup()
    if backup:
        await internal_log('backup', f'Backup automático criado: `{backup.name}`')

@backup_watchdog.before_loop
async def before_backup_watchdog():
    await bot.wait_until_ready()

@tasks.loop(minutes=1)
async def reminder_watchdog():
    now = datetime.now(timezone.utc)
    for reminder_id, reminder in list(data['reminders'].items()):
        if datetime.fromisoformat(reminder['deliver_at']) > now:
            continue
        guild = bot.get_guild(int(reminder['guild_id']))
        channel = guild.get_channel(int(reminder['channel_id'])) if guild else None
        if channel:
            await channel.send(f"⏰ <@{reminder['user_id']}>: {reminder['message']}")
            await audit_log(guild, 'geral', 'Lembrete entregue', None, reminder['message'])
        data['reminders'].pop(reminder_id, None)
        save_data()

@reminder_watchdog.before_loop
async def before_reminder_watchdog():
    await bot.wait_until_ready()

@tasks.loop(minutes=1)
async def clock_watchdog():
    now = datetime.now(timezone.utc)
    for guild_id, record in data['timeclock'].items():
        guild = bot.get_guild(int(guild_id))
        if not guild:
            continue
        for user_id, active in list(record['active'].items()):
            if active.get('paused'):
                continue
            last_check = datetime.fromisoformat(active['last_check'])
            if (now - last_check).total_seconds() < 3600:
                continue
            member = guild.get_member(int(user_id))
            if not member:
                continue
            target = get_guild_channel(guild, active.get('channel_id'))
            if not target:
                target_id = guild_settings(guild.id).get('timeclock_channel_id')
                target = guild.get_channel(int(target_id)) if target_id else guild.system_channel
            if not target:
                continue
            active['last_check'] = now.isoformat()
            save_data()
            await target.send(f'⏱️ {member.mention}, você continua ativo no bate-ponto?', view=ClockCheckView(guild.id, member.id))

@clock_watchdog.before_loop
async def before_clock_watchdog():
    await bot.wait_until_ready()

def safe_name(value):
    value = re.sub('[^a-z0-9-]', '-', value.lower())
    return value.strip('-')[:18] or 'usuario'

def get_guild_channel(guild, channel_id):
    return guild.get_channel(int(channel_id)) or guild.get_thread(int(channel_id))


@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    await internal_log('inicialização', f'Bot conectado como {bot.user} (`{bot.user.id}`).')
    global commands_synced
    if not commands_synced:
        await synchronize_commands()
        commands_synced = True
    profile = data['bot_profile']
    await bot.change_presence(status=discord.Status(profile.get('bot_status', 'online')), activity=discord.Game(name=profile['bot_activity']) if profile.get('bot_activity') else None)
    if not clock_watchdog.is_running():
        clock_watchdog.start()
    if not giveaway_watchdog.is_running():
        giveaway_watchdog.start()
    if not backup_watchdog.is_running():
        backup_watchdog.start()
    if not reminder_watchdog.is_running():
        reminder_watchdog.start()
    for guild in bot.guilds:
        if not data['channel_snapshots'].get(str(guild.id)):
            await snapshot_guild_channels(guild)
        await cache_guild_invites(guild)

async def generate_guild_invite(guild):
    channel_id = data['internal_logs'].get('channel_id')
    if not channel_id:
        print(f'[CONVITE] Nenhum canal de internal logs configurado para gerar convite de {guild.name}.')
        return None
    channel = guild.get_channel(int(channel_id))
    if not isinstance(channel, discord.TextChannel):
        print(f'[CONVITE] O canal de internal logs não existe em {guild.name}.')
        return None
    permissions = channel.permissions_for(guild.me)
    if not permissions.create_instant_invite:
        print(f"[CONVITE] O bot não possui 'Criar convite' em #{channel.name} de {guild.name}.")
        return None
    try:
        invite = await channel.create_invite(max_age=0, max_uses=0, unique=True, reason='Convite automático ao adicionar o bot')
        return invite.url
    except discord.Forbidden as error:
        print(f'[CONVITE] Sem permissão em {guild.name}: {error}')
    except discord.HTTPException as error:
        print(f'[CONVITE] Erro do Discord em {guild.name}: {error}')
    return None

@bot.event
async def on_guild_join(guild):
    print(f'[SERVIDOR] Bot adicionado ao servidor: {guild.name} ({guild.id})')
    await asyncio.sleep(2)
    invite_url = await generate_guild_invite(guild)
    if invite_url:
        print(f'[CONVITE] Convite criado para {guild.name}: {invite_url}')
        await internal_log('servidor adicionado', f'🤖 O FuriousBot foi adicionado ao servidor **{guild.name}** (`{guild.id}`).\n\n🔗 **Convite permanente:** {invite_url}', guild)
    else:
        await internal_log('servidor adicionado', f'🤖 O FuriousBot foi adicionado ao servidor **{guild.name}** (`{guild.id}`).\n\n⚠️ Não foi possível gerar o convite. Verifique a configuração do canal de logs internos e a permissão **Criar convite**.', guild)

@bot.event
async def on_member_join(member):
    security = security_config(member.guild.id)
    banned_actors = {int(user_id) for user_id in security.get('banned_actors', [])}
    if member.id in banned_actors:
        try:
            await member.guild.ban(member, reason='Anti-raid: atacante anteriormente banido retornou ao servidor', delete_message_seconds=0)
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass
        return
    verification = verification_config(member.guild.id)
    if verification.get('enabled') and member.bot and (member.id != (bot.user.id if bot.user else 0)) and (member.id not in {int(user_id) for user_id in verification.get('allowed_bots', [])}):
        try:
            await member.kick(reason='Bot não autorizado pela verificação padrão')
            await internal_log('bot bloqueado', f'Bot não autorizado {member} (`{member.id}`) foi expulso.', member.guild, 'ERROR')
        except discord.HTTPException as error:
            await internal_log('falha ao bloquear bot', f'Não foi possível expulsar {member} (`{member.id}`): {error}', member.guild, 'ERROR')
        return
    autorole_id = guild_settings(member.guild.id).get('autorole_id')
    autorole = member.guild.get_role(int(autorole_id)) if autorole_id else None
    if autorole:
        try:
            await member.add_roles(autorole, reason='Autorole configurado no servidor')
        except discord.HTTPException:
            pass
    inviter = await identify_inviter(member.guild)
    inviter_text = inviter.mention if inviter else 'Não identificado (sem permissão para ler convites)'
    await audit_log(member.guild, 'membros', 'Membro entrou no servidor', member, member.mention)
    await send_server_event(member.guild, 'welcome_channel_id', '👋 Novo membro no servidor', f'Boas-vindas, {member.mention}!', discord.Color.green(), [('Usuário', f'{member} ({member.id})'), ('Convidado por', inviter_text)])
    await send_server_event(member.guild, 'invite_channel_id', '📨 Convite utilizado', f'{member.mention} entrou no servidor.', discord.Color.blue(), [('Convidado', f'{member} ({member.id})'), ('Convidado por', inviter_text)])

@bot.event
async def on_member_remove(member):
    await audit_log(member.guild, 'membros', 'Membro saiu do servidor', member, str(member))
    punishment = None
    try:
        async for entry in member.guild.audit_logs(limit=5, action=discord.AuditLogAction.ban):
            if entry.target and entry.target.id == member.id and ((discord.utils.utcnow() - entry.created_at).total_seconds() < 10):
                return
        async for entry in member.guild.audit_logs(limit=5, action=discord.AuditLogAction.kick):
            if entry.target and entry.target.id == member.id and ((discord.utils.utcnow() - entry.created_at).total_seconds() < 10):
                punishment = entry.user
                break
    except discord.Forbidden:
        pass
    if punishment:
        await send_server_event(member.guild, 'punishment_channel_id', '👢 Membro expulso', f'{member.mention} foi expulso do servidor.', discord.Color.orange(), [('Usuário', f'{member} ({member.id})'), ('Moderador', punishment.mention)])
        return
    await send_server_event(member.guild, 'leave_channel_id', '📤 Membro saiu do servidor', f'{member.mention} deixou o servidor.', discord.Color.orange(), [('Usuário', f'{member} ({member.id})')])

@bot.event
async def on_member_ban(guild, user):
    if is_immune_user(user):
        try:
            await guild.unban(user, reason='Usuário protegido contra punições do bot')
        except discord.HTTPException:
            pass
        await audit_log(guild, 'seguranca', 'Banimento de usuário imune revertido', user)
        return
    moderator = None
    try:
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.ban):
            if entry.target and entry.target.id == user.id and ((discord.utils.utcnow() - entry.created_at).total_seconds() < 10):
                moderator = entry.user
                break
    except discord.Forbidden:
        pass
    await send_server_event(guild, 'punishment_channel_id', '🔨 Membro banido', f"{(user.mention if hasattr(user, 'mention') else user)} foi banido.", discord.Color.red(), [('Usuário', f'{user} ({user.id})'), ('Moderador', moderator.mention if moderator else 'Não identificado')])

@bot.event
async def on_invite_create(invite):
    await cache_guild_invites(invite.guild)

@bot.event
async def on_raw_reaction_add(payload):
    if payload.guild_id is None or payload.user_id == bot.user.id or str(payload.emoji) != '⭐':
        return
    config = guild_settings(payload.guild_id)
    starboard_id = config.get('starboard_channel_id')
    if not starboard_id or payload.channel_id == int(starboard_id):
        return
    channel = bot.get_channel(payload.channel_id)
    starboard = bot.get_channel(int(starboard_id))
    if not channel or not starboard:
        return
    try:
        message = await channel.fetch_message(payload.message_id)
    except discord.HTTPException:
        return
    stars = next((reaction for reaction in message.reactions if str(reaction.emoji) == '⭐'), None)
    threshold = max(1, int(config.get('starboard_threshold', 3)))
    if not stars or stars.count < threshold:
        return
    existing = data['starboard'].get(str(message.id))
    embed = discord.Embed(description=message.content or '[sem texto]', color=discord.Color.gold(), timestamp=message.created_at)
    embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
    embed.add_field(name='Origem', value=f'[Ir para a mensagem]({message.jump_url})')
    embed.set_footer(text=f'⭐ {stars.count} | #{channel.name}')
    try:
        if existing:
            target = await starboard.fetch_message(int(existing))
            await target.edit(embed=embed)
        else:
            target = await starboard.send(embed=embed)
            data['starboard'][str(message.id)] = target.id
            save_data()
    except discord.HTTPException:
        pass

@bot.event
async def on_message_delete(message):
    if message.guild and (not message.author.bot):
        await audit_log(message.guild, 'mensagens', 'Mensagem apagada', message.author, message.content or '[sem texto]')

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return
    if await process_automod(message):
        return
    if protected_channel_matches(message):
        print(f'[SEGURANCA] Mensagem recebida no canal protegido: {message.author} ({message.author.id})')
        try:
            await message.delete(reason='Canal protegido contra contas comprometidas')
        except discord.Forbidden:
            delete_error = 'o bot não possui Gerenciar mensagens'
        except discord.HTTPException as error:
            delete_error = f'falha ao apagar a mensagem ({error})'
        except Exception as error:
            delete_error = f'falha inesperada ao apagar ({type(error).__name__}: {error})'
            print(f'[SEGURANCA] Erro ao apagar mensagem: {type(error).__name__}: {error}')
        else:
            delete_error = 'mensagem apagada'
        try:
            banned, result = await ban_protected_author(message)
        except Exception as error:
            banned = False
            result = f'falha inesperada no ban ({type(error).__name__}: {error})'
            print(f'[SEGURANCA] Erro ao banir autor: {type(error).__name__}: {error}')
        await audit_log(message.guild, 'seguranca', 'Ação no canal protegido', message.author, f'Canal: {message.channel.mention}; {delete_error}; resultado do ban: {result}')
        if not banned and result != 'usuário imune':
            alert = security_config(message.guild.id).get('alert_channel_id')
            alert_channel = message.guild.get_channel(int(alert)) if alert else message.guild.system_channel
            if alert_channel:
                try:
                    await alert_channel.send(f'⚠️ Ação no canal protegido para {message.author.mention}: {delete_error}; {result}. Verifique as permissões e a posição do cargo do bot.')
                except discord.HTTPException:
                    pass
        return
    leveled_up, level = grant_message_xp(message.guild.id, message.author.id)
    if leveled_up:
        await message.channel.send(f'🎉 {message.author.mention} alcançou o nível **{level}**!', delete_after=10)
    await bot.process_commands(message)

@bot.event
async def on_guild_channel_create(channel):
    await audit_log(channel.guild, 'geral', 'Canal criado', None, f'{channel.name} ({channel.id})')

@bot.event
async def on_guild_channel_delete(channel):
    await audit_log(channel.guild, 'geral', 'Canal removido', None, f'{channel.name} ({channel.id})')
    await process_channel_deletion(channel)

@bot.event
async def on_app_command_error(interaction, error):
    message = 'Ocorreu um erro ao executar o comando.'
    if isinstance(error, (app_commands.MissingPermissions, app_commands.CheckFailure)):
        message = 'Apenas administradores podem usar comandos slash.'
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)
    print(f'Erro no slash command: {error}')
    await internal_log('erro em slash command', f'{type(error).__name__}: {str(error)}', interaction.guild, 'ERROR')

@bot.tree.command(name='verificar', description='Verifica se o bot está online')
async def verificar(interaction):
    await interaction.response.send_message(f'Online. Latência: {round(bot.latency * 1000)}ms', ephemeral=True)

@bot.tree.command(name='ping', description='Mostra a latência do bot')
async def ping(interaction):
    await interaction.response.send_message(f'🏓 Pong! `{round(bot.latency * 1000)}ms`', ephemeral=True)

@bot.tree.command(name='reiniciar', description='Reinicia o processo do bot')
async def reiniciar(interaction):
    if interaction.user.id != 770039880964505601:
        await interaction.response.send_message('Você não está autorizado a reiniciar o bot.', ephemeral=True)
        return
    await interaction.response.send_message('Reiniciando o bot...', ephemeral=True)
    await asyncio.sleep(1)
    os.execv(sys.executable, [sys.executable] + sys.argv)

@bot.tree.command(name='limpar', description='Apaga mensagens do canal')
@app_commands.checks.has_permissions(manage_messages=True)
async def limpar(interaction, quantidade: app_commands.Range[int, 1, 100]):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=quantidade)
    await interaction.followup.send(f'{len(deleted)} mensagens apagadas.', ephemeral=True)

@bot.tree.command(name='servidor', description='Mostra informações do servidor')
async def servidor(interaction):
    guild = interaction.guild
    embed = discord.Embed(title=guild.name, color=discord.Color.blurple())
    embed.add_field(name='Membros', value=str(guild.member_count))
    embed.add_field(name='Dono', value=guild.owner.mention if guild.owner else 'Indisponível')
    embed.add_field(name='Criado em', value=discord.utils.format_dt(guild.created_at, 'D'))
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='usuario', description='Mostra informações de um usuário')
async def usuario(interaction, membro: discord.Member):
    embed = discord.Embed(title=f'Perfil de {membro.display_name}', color=membro.color)
    embed.add_field(name='ID', value=str(membro.id))
    embed.add_field(name='Entrou em', value=discord.utils.format_dt(membro.joined_at, 'D'))
    embed.set_thumbnail(url=membro.display_avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='perfil', description='Mostra o perfil completo de um membro')
async def perfil(interaction, membro: discord.Member | None=None):
    membro = membro or interaction.user
    roles = [role.mention for role in reversed(membro.roles[1:])]
    embed = discord.Embed(title=f'Perfil de {membro.display_name}', color=membro.color)
    embed.set_thumbnail(url=membro.display_avatar.url)
    embed.add_field(name='Usuário', value=f'{membro.mention}\n`{membro.id}`', inline=False)
    embed.add_field(name='Conta criada', value=discord.utils.format_dt(membro.created_at, 'R'))
    embed.add_field(name='Entrou no servidor', value=discord.utils.format_dt(membro.joined_at, 'R'))
    embed.add_field(name='Cargos', value=' '.join(roles[-10:]) or 'Nenhum', inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='icone_servidor', description='Exibe o ícone do servidor')
async def icone_servidor(interaction):
    if not interaction.guild.icon:
        await interaction.response.send_message('Este servidor não possui ícone.', ephemeral=True)
        return
    embed = discord.Embed(title=f'Ícone de {interaction.guild.name}', color=discord.Color.blurple())
    embed.set_image(url=interaction.guild.icon.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='rep', description='Dá reputação positiva a um membro')
async def rep(interaction, membro: discord.Member):
    if membro.bot or membro.id == interaction.user.id:
        await interaction.response.send_message('Escolha outro membro que não seja um bot.', ephemeral=True)
        return
    guild_reputations = data['reputations'].setdefault(str(interaction.guild.id), {})
    user_reputations = guild_reputations.setdefault(str(membro.id), {'total': 0, 'given_by': []})
    if interaction.user.id in user_reputations['given_by']:
        await interaction.response.send_message('Você já deu reputação para esse membro.', ephemeral=True)
        return
    user_reputations['total'] += 1
    user_reputations['given_by'].append(interaction.user.id)
    save_data()
    await interaction.response.send_message(f"⭐ {membro.mention} agora tem **{user_reputations['total']}** ponto(s) de reputação.")

@bot.tree.command(name='credits', description='Mostra os créditos de um membro')
async def credits(interaction, membro: discord.Member | None=None):
    membro = membro or interaction.user
    account = wallet(interaction.guild.id, membro.id)
    await interaction.response.send_message(f"💰 {membro.mention} possui **{format_money(account['wallet'] + account['bank'])}**.", ephemeral=membro.id == interaction.user.id)

@bot.tree.command(name='roll', description='Rola um dado')
async def roll(interaction, lados: app_commands.Range[int, 2, 1000]=6):
    await interaction.response.send_message(f'🎲 {interaction.user.mention} rolou **{random.randint(1, lados)}** (d{lados}).')

@bot.tree.command(name='roles', description='Lista os cargos do servidor')
async def roles(interaction):
    entries = [f'{role.mention} — {len(role.members)} membro(s)' for role in reversed(interaction.guild.roles[1:])]
    await interaction.response.send_message('**Cargos do servidor**\n' + ('\n'.join(entries[:40]) or 'Nenhum cargo.'), ephemeral=True)

@bot.tree.command(name='colors', description='Lista cargos de cor disponíveis')
async def colors(interaction):
    available = [role.mention for role in interaction.guild.roles if role.name.casefold().startswith('cor-')]
    await interaction.response.send_message('**Cores disponíveis**\n' + (' '.join(available) or 'Nenhuma. Um administrador pode criar cargos `cor-Nome`.'), ephemeral=True)

@bot.tree.command(name='color', description='Escolhe um cargo de cor')
async def color(interaction, cargo: discord.Role):
    if not cargo.name.casefold().startswith('cor-'):
        await interaction.response.send_message('Escolha um cargo cujo nome comece com `cor-`.', ephemeral=True)
        return
    for current in interaction.user.roles:
        if current.name.casefold().startswith('cor-') and current != cargo:
            await interaction.user.remove_roles(current, reason='Troca de cor do perfil')
    await interaction.user.add_roles(cargo, reason='Cor escolhida pelo usuário')
    await interaction.response.send_message(f'Sua cor agora é {cargo.mention}.', ephemeral=True)

@bot.tree.command(name='rank', description='Mostra o nível e XP de um membro')
async def rank(interaction, membro: discord.Member | None=None):
    membro = membro or interaction.user
    record = level_record(interaction.guild.id, membro.id)
    await interaction.response.send_message(f"🏅 **Rank de {membro.display_name}**\nNível: **{level_from_xp(record['xp'])}**\nXP: **{record['xp']}**\nTítulo: **{record['title'] or 'Sem título'}**")

@bot.tree.command(name='top', description='Mostra o ranking de XP do servidor')
async def top(interaction):
    ranking = sorted(guild_levels(interaction.guild.id).items(), key=lambda item: item[1].get('xp', 0), reverse=True)[:10]
    lines = []
    for position, (user_id, record) in enumerate(ranking, 1):
        member = interaction.guild.get_member(int(user_id))
        lines.append(f"**{position}.** {(member.display_name if member else user_id)} — nível {level_from_xp(record.get('xp', 0))} ({record.get('xp', 0)} XP)")
    await interaction.response.send_message('🏆 **Ranking de XP**\n' + ('\n'.join(lines) or 'Ainda não há XP registrado.'))

@bot.tree.command(name='title', description='Define seu título de perfil')
async def title(interaction, texto: str):
    level_record(interaction.guild.id, interaction.user.id)['title'] = texto[:80]
    save_data()
    await interaction.response.send_message(f'Seu título agora é **{texto[:80]}**.', ephemeral=True)

@bot.tree.command(name='profile', description='Mostra o perfil de um membro')
async def profile(interaction, membro: discord.Member | None=None):
    await perfil.callback(interaction, membro)

@bot.tree.command(name='user', description='Mostra informações de um usuário')
async def user(interaction, membro: discord.Member | None=None):
    await usuario.callback(interaction, membro or interaction.user)

@bot.tree.command(name='server', description='Mostra informações do servidor')
async def server(interaction):
    await servidor.callback(interaction)

@bot.tree.command(name='setxp', description='Define o XP de um membro')
@app_commands.checks.has_permissions(manage_guild=True)
async def setxp(interaction, membro: discord.Member, xp: app_commands.Range[int, 0, 1000000]):
    level_record(interaction.guild.id, membro.id)['xp'] = xp
    save_data()
    await interaction.response.send_message(f'XP de {membro.mention} definido para **{xp}**.', ephemeral=True)

@bot.tree.command(name='setlevel', description='Define o nível de um membro')
@app_commands.checks.has_permissions(manage_guild=True)
async def setlevel(interaction, membro: discord.Member, nivel: app_commands.Range[int, 0, 1000]):
    level_record(interaction.guild.id, membro.id)['xp'] = nivel * nivel * 100
    save_data()
    await interaction.response.send_message(f'Nível de {membro.mention} definido para **{nivel}**.', ephemeral=True)

@bot.tree.command(name='points', description='Adiciona pontos de moderação a um membro')
@app_commands.checks.has_permissions(moderate_members=True)
async def points(interaction, membro: discord.Member, quantidade: app_commands.Range[int, 1, 1000000]):
    level_record(interaction.guild.id, membro.id)['points'] += quantidade
    save_data()
    await interaction.response.send_message(f'{membro.mention} recebeu **{quantidade}** ponto(s) de moderação.', ephemeral=True)

@bot.tree.command(name='dizer', description='Envia uma mensagem pelo bot')
@app_commands.checks.has_permissions(manage_messages=True)
async def dizer(interaction, mensagem: str):
    await interaction.channel.send(mensagem)
    await interaction.response.send_message('Mensagem enviada.', ephemeral=True)

@bot.tree.command(name='mutar', description='Muta um membro pelo tempo informado')
@app_commands.checks.has_permissions(manage_roles=True)
async def mutar(interaction, membro: discord.Member, minutos: app_commands.Range[int, 1, 10080]):
    if await refuse_protected_action(interaction, membro, 'mute'):
        return
    role = discord.utils.get(interaction.guild.roles, name='Muted')
    if not role:
        role = await interaction.guild.create_role(name='Muted', reason='Sistema de mute slash')
        for channel in interaction.guild.channels:
            await channel.set_permissions(role, send_messages=False)
    await membro.add_roles(role, reason=f'Mute aplicado por {interaction.user}')
    await interaction.response.send_message(f'{membro.mention} foi mutado por {minutos} minutos.')

    async def unmute_later():
        await asyncio.sleep(minutos * 60)
        if role in membro.roles:
            await membro.remove_roles(role, reason='Fim do tempo de mute')
    asyncio.create_task(unmute_later())

@bot.tree.command(name='desmutar', description='Remove o mute de um membro')
@app_commands.checks.has_permissions(manage_roles=True)
async def desmutar(interaction, membro: discord.Member):
    if await refuse_protected_action(interaction, membro, 'desmute'):
        return
    role = discord.utils.get(interaction.guild.roles, name='Muted')
    if role and role in membro.roles:
        await membro.remove_roles(role, reason=f'Desmute aplicado por {interaction.user}')
        await interaction.response.send_message(f'{membro.mention} foi desmutado.')
    else:
        await interaction.response.send_message('Esse membro não está mutado.', ephemeral=True)

@bot.tree.command(name='expulsar', description='Expulsa um membro do servidor')
@app_commands.checks.has_permissions(kick_members=True)
async def expulsar(interaction, membro: discord.Member, motivo: str='Sem motivo informado'):
    if await refuse_protected_action(interaction, membro, 'kick'):
        return
    await membro.kick(reason=f'{motivo} | Por {interaction.user}')
    await interaction.response.send_message(f'{membro.mention} foi expulso.')

@bot.tree.command(name='banir', description='Bane um membro do servidor')
@app_commands.checks.has_permissions(ban_members=True)
async def banir(interaction, membro: discord.Member, motivo: str='Sem motivo informado'):
    if await refuse_protected_action(interaction, membro, 'ban'):
        return
    await membro.ban(reason=f'{motivo} | Por {interaction.user}')
    await interaction.response.send_message(f'{membro.mention} foi banido.')

@bot.tree.command(name='desbanir', description='Remove o banimento de um usuário')
@app_commands.checks.has_permissions(ban_members=True)
async def desbanir(interaction, usuario: discord.User):
    if is_immune_user(usuario):
        await interaction.response.send_message('Este usuário já possui imunidade contra ações do bot.', ephemeral=True)
        return
    await interaction.guild.unban(usuario, reason=f'Desbanido por {interaction.user}')
    await interaction.response.send_message(f'{usuario} foi desbanido.')

@bot.tree.command(name='dar_cargo', description='Adiciona um cargo a um membro')
@app_commands.checks.has_permissions(manage_roles=True)
async def dar_cargo(interaction, membro: discord.Member, cargo: discord.Role):
    await membro.add_roles(cargo, reason=f'Cargo dado por {interaction.user}')
    await interaction.response.send_message(f'{cargo.mention} foi adicionado a {membro.mention}.')

@bot.tree.command(name='remover_cargo', description='Remove um cargo de um membro')
@app_commands.checks.has_permissions(manage_roles=True)
async def remover_cargo(interaction, membro: discord.Member, cargo: discord.Role):
    await membro.remove_roles(cargo, reason=f'Cargo removido por {interaction.user}')
    await interaction.response.send_message(f'{cargo.mention} foi removido de {membro.mention}.')

@bot.tree.command(name='advertir', description='Registra uma advertência para um membro')
@app_commands.checks.has_permissions(moderate_members=True)
async def advertir(interaction, membro: discord.Member, motivo: str='Sem motivo informado'):
    if await refuse_protected_action(interaction, membro, 'advertência'):
        return
    total = add_warning(interaction.guild.id, membro.id, interaction.user.id, motivo)
    save_data()
    await audit_log(interaction.guild, 'moderacao', 'Membro advertido', interaction.user, f'Alvo: {membro}; motivo: {motivo}')
    await interaction.response.send_message(f'{membro.mention} recebeu uma advertência. Total: **{total}**.')

@bot.tree.command(name='avisos', description='Consulta as advertências de um membro')
async def avisos(interaction, membro: discord.Member | None=None):
    membro = membro or interaction.user
    if membro.id != interaction.user.id and (not interaction.user.guild_permissions.moderate_members):
        await interaction.response.send_message('Você só pode consultar seus próprios avisos.', ephemeral=True)
        return
    records = guild_warnings(interaction.guild.id).get(str(membro.id), [])
    if not records:
        await interaction.response.send_message(f'{membro.mention} não possui advertências.', ephemeral=True)
        return
    lines = [f"**{index}.** {record['reason']} — <t:{int(datetime.fromisoformat(record['created_at']).timestamp())}:R>" for index, record in enumerate(records, 1)]
    await interaction.response.send_message(f'**Advertências de {membro.display_name}**\n' + '\n'.join(lines), ephemeral=True)

@bot.tree.command(name='limpar_avisos', description='Remove todas as advertências de um membro')
@app_commands.checks.has_permissions(moderate_members=True)
async def limpar_avisos(interaction, membro: discord.Member):
    removed = len(guild_warnings(interaction.guild.id).pop(str(membro.id), []))
    save_data()
    await interaction.response.send_message(f'{removed} advertência(s) removida(s) de {membro.mention}.', ephemeral=True)

@bot.tree.command(name='sugerir', description='Envia uma sugestão para a equipe do servidor')
async def sugerir(interaction, texto: str):
    channel_id = guild_settings(interaction.guild.id).get('suggestion_channel_id')
    channel = interaction.guild.get_channel(int(channel_id)) if channel_id else None
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message('O canal de sugestões ainda não foi configurado em `/config`.', ephemeral=True)
        return
    embed = discord.Embed(title='Nova sugestão', description=texto[:4000], color=discord.Color.blurple(), timestamp=datetime.now(timezone.utc))
    embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
    embed.set_footer(text=f'Autor: {interaction.user.id}')
    try:
        message = await channel.send(embed=embed)
        await message.add_reaction('✅')
        await message.add_reaction('❌')
    except discord.HTTPException:
        await interaction.response.send_message('Não foi possível publicar a sugestão.', ephemeral=True)
        return
    await interaction.response.send_message(f'Sua sugestão foi enviada em {channel.mention}.', ephemeral=True)

@bot.tree.command(name='warnings', description='Lista os avisos de um membro')
async def warnings(interaction, membro: discord.Member | None=None):
    await avisos.callback(interaction, membro)

@bot.tree.command(name='warn_remove', description='Remove um aviso de um membro')
@app_commands.checks.has_permissions(moderate_members=True)
async def warn_remove(interaction, membro: discord.Member, numero: app_commands.Range[int, 1, 100]):
    records = guild_warnings(interaction.guild.id).get(str(membro.id), [])
    if numero > len(records):
        await interaction.response.send_message('Esse aviso não existe.', ephemeral=True)
        return
    removed = records.pop(numero - 1)
    if not records:
        guild_warnings(interaction.guild.id).pop(str(membro.id), None)
    save_data()
    await interaction.response.send_message(f"Aviso removido de {membro.mention}: {removed['reason']}", ephemeral=True)

@bot.tree.command(name='timeout', description='Coloca um membro em timeout')
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(interaction, membro: discord.Member, minutos: app_commands.Range[int, 1, 40320], motivo: str='Sem motivo informado'):
    if await refuse_protected_action(interaction, membro, 'timeout'):
        return
    await membro.timeout(timedelta(minutes=minutos), reason=f'{motivo} | Por {interaction.user}')
    await interaction.response.send_message(f'{membro.mention} recebeu timeout por {minutos} minuto(s).')

@bot.tree.command(name='untimeout', description='Remove o timeout de um membro')
@app_commands.checks.has_permissions(moderate_members=True)
async def untimeout(interaction, membro: discord.Member):
    await membro.timeout(None, reason=f'Timeout removido por {interaction.user}')
    await interaction.response.send_message(f'Timeout removido de {membro.mention}.')

@bot.tree.command(name='setnick', description='Altera o apelido de um membro')
@app_commands.checks.has_permissions(manage_nicknames=True)
async def setnick(interaction, membro: discord.Member, apelido: str | None=None):
    await membro.edit(nick=apelido, reason=f'Apelido alterado por {interaction.user}')
    await interaction.response.send_message(f'Apelido de {membro.mention} atualizado.')

@bot.tree.command(name='vkick', description='Remove um membro do canal de voz')
@app_commands.checks.has_permissions(move_members=True)
async def vkick(interaction, membro: discord.Member):
    if not membro.voice:
        await interaction.response.send_message('Esse membro não está em um canal de voz.', ephemeral=True)
        return
    await membro.move_to(None, reason=f'Removido da voz por {interaction.user}')
    await interaction.response.send_message(f'{membro.mention} foi removido do canal de voz.')

@bot.tree.command(name='move', description='Move um membro para um canal de voz')
@app_commands.checks.has_permissions(move_members=True)
async def move(interaction, membro: discord.Member, canal: discord.VoiceChannel):
    await membro.move_to(canal, reason=f'Movido por {interaction.user}')
    await interaction.response.send_message(f'{membro.mention} foi movido para {canal.mention}.')

@bot.tree.command(name='lock', description='Bloqueia o canal atual')
@app_commands.checks.has_permissions(manage_channels=True)
async def lock(interaction, motivo: str='Canal bloqueado pela moderação'):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False, reason=motivo)
    await interaction.response.send_message('🔒 Canal bloqueado.')

@bot.tree.command(name='unlock', description='Desbloqueia o canal atual')
@app_commands.checks.has_permissions(manage_channels=True)
async def unlock(interaction):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=None, reason=f'Canal desbloqueado por {interaction.user}')
    await interaction.response.send_message('🔓 Canal desbloqueado.')

@bot.tree.command(name='setcolor', description='Altera a cor de um cargo')
@app_commands.checks.has_permissions(manage_roles=True)
async def setcolor(interaction, cargo: discord.Role, hexadecimal: str):
    hexadecimal = hexadecimal.replace('#', '')
    if not re.fullmatch('[0-9a-fA-F]{6}', hexadecimal):
        await interaction.response.send_message('Use uma cor hexadecimal com 6 caracteres.', ephemeral=True)
        return
    await cargo.edit(color=discord.Colour(int(hexadecimal, 16)), reason=f'Cor alterada por {interaction.user}')
    await interaction.response.send_message(f'Cor de {cargo.mention} atualizada.')

@bot.tree.command(name='reset', description='Zera XP e pontos de um membro ou do servidor')
@app_commands.checks.has_permissions(manage_guild=True)
async def reset(interaction, membro: discord.Member | None=None):
    levels = guild_levels(interaction.guild.id)
    if membro:
        levels.pop(str(membro.id), None)
        target = membro.mention
    else:
        levels.clear()
        target = 'todos os membros'
    save_data()
    await interaction.response.send_message(f'XP e pontos zerados para {target}.', ephemeral=True)

@bot.command(name='ajuda')
async def prefix_help(ctx):
    await ctx.send(f'Prefixo atual: `{COMMAND_PREFIX}`\nComandos: `{COMMAND_PREFIX}config`, `{COMMAND_PREFIX}verificar`, `{COMMAND_PREFIX}limpar`, `{COMMAND_PREFIX}advertir`, `{COMMAND_PREFIX}avisos`, `{COMMAND_PREFIX}sugerir`, `{COMMAND_PREFIX}banir`, `{COMMAND_PREFIX}expulsar`, `{COMMAND_PREFIX}mutar` e `{COMMAND_PREFIX}desmutar`.\nOs painéis de ticket e ponto continuam disponíveis pelos comandos slash com seus parâmetros completos.')

@bot.command(name='verificar')
async def prefix_verificar(ctx):
    await ctx.send(f'Online. Latência: {round(bot.latency * 1000)}ms')

@bot.command(name='config')
@commands.has_permissions(administrator=True)
async def prefix_config(ctx):
    banner = discord.File(io.BytesIO(visual_banner('Central de configuração', 'Controle os sistemas deste servidor')), filename='config.svg')
    embed = discord.Embed(title='Configurações do servidor', description='As alterações ficam isoladas neste servidor.', color=discord.Color.blurple())
    embed.set_image(url='attachment://config.svg')
    await ctx.send(embed=embed, file=banner, view=ConfigView())

@bot.command(name='limpar')
@commands.has_permissions(manage_messages=True)
async def prefix_limpar(ctx, quantidade: int):
    quantidade = max(1, min(100, quantidade))
    deleted = await ctx.channel.purge(limit=quantidade + 1)
    await ctx.send(f'{max(0, len(deleted) - 1)} mensagens apagadas.', delete_after=5)

@bot.command(name='avisos')
async def prefix_avisos(ctx, membro: discord.Member | None=None):
    membro = membro or ctx.author
    if membro.id != ctx.author.id and (not ctx.author.guild_permissions.moderate_members):
        await ctx.send('Você só pode consultar seus próprios avisos.', delete_after=8)
        return
    records = guild_warnings(ctx.guild.id).get(str(membro.id), [])
    if not records:
        await ctx.send(f'{membro.mention} não possui advertências.')
        return
    lines = [f"**{index}.** {record['reason']}" for index, record in enumerate(records, 1)]
    await ctx.send(f'**Advertências de {membro.display_name}**\n' + '\n'.join(lines))

@bot.command(name='advertir')
@commands.has_permissions(moderate_members=True)
async def prefix_advertir(ctx, membro: discord.Member, *, motivo: str='Sem motivo informado'):
    if is_immune_user(membro):
        await ctx.send('Este usuário está protegido e não pode receber advertência.', delete_after=8)
        return
    total = add_warning(ctx.guild.id, membro.id, ctx.author.id, motivo)
    save_data()
    await audit_log(ctx.guild, 'moderacao', 'Membro advertido', ctx.author, f'Alvo: {membro}; motivo: {motivo}')
    await ctx.send(f'{membro.mention} recebeu uma advertência. Total: **{total}**.')

@bot.command(name='sugerir')
async def prefix_sugerir(ctx, *, texto: str):
    channel_id = guild_settings(ctx.guild.id).get('suggestion_channel_id')
    channel = ctx.guild.get_channel(int(channel_id)) if channel_id else None
    if not isinstance(channel, discord.TextChannel):
        await ctx.send('O canal de sugestões ainda não foi configurado em `!config`.', delete_after=8)
        return
    embed = discord.Embed(title='Nova sugestão', description=texto[:4000], color=discord.Color.blurple(), timestamp=datetime.now(timezone.utc))
    embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
    message = await channel.send(embed=embed)
    await message.add_reaction('✅')
    await message.add_reaction('❌')
    await ctx.send(f'Sua sugestão foi enviada em {channel.mention}.', delete_after=8)

@bot.command(name='banir')
@commands.has_permissions(ban_members=True)
async def prefix_banir(ctx, membro: discord.Member, *, motivo: str='Sem motivo informado'):
    if is_immune_user(membro):
        await ctx.send('Este usuário está protegido e não pode ser banido.', delete_after=8)
        return
    await membro.ban(reason=f'{motivo} | Por {ctx.author}')
    await ctx.send(f'{membro.mention} foi banido.')

@bot.command(name='expulsar')
@commands.has_permissions(kick_members=True)
async def prefix_expulsar(ctx, membro: discord.Member, *, motivo: str='Sem motivo informado'):
    if is_immune_user(membro):
        await ctx.send('Este usuário está protegido e não pode ser expulso.', delete_after=8)
        return
    await membro.kick(reason=f'{motivo} | Por {ctx.author}')
    await ctx.send(f'{membro.mention} foi expulso.')

@bot.command(name='mutar')
@commands.has_permissions(manage_roles=True)
async def prefix_mutar(ctx, membro: discord.Member, minutos: int):
    minutos = max(1, min(10080, minutos))
    role = discord.utils.get(ctx.guild.roles, name='Muted')
    if not role:
        role = await ctx.guild.create_role(name='Muted', reason='Sistema de mute por prefixo')
        for channel in ctx.guild.channels:
            await channel.set_permissions(role, send_messages=False)
    await membro.add_roles(role, reason=f'Mute aplicado por {ctx.author}')
    await ctx.send(f'{membro.mention} foi mutado por {minutos} minutos.')

    async def unmute_later():
        await asyncio.sleep(minutos * 60)
        if role in membro.roles:
            await membro.remove_roles(role, reason='Fim do tempo de mute')
    asyncio.create_task(unmute_later())

@bot.command(name='desmutar')
@commands.has_permissions(manage_roles=True)
async def prefix_desmutar(ctx, membro: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name='Muted')
    if role and role in membro.roles:
        await membro.remove_roles(role, reason=f'Desmute aplicado por {ctx.author}')
        await ctx.send(f'{membro.mention} foi desmutado.')
    else:
        await ctx.send('Esse membro não está mutado.', delete_after=8)

@bot.event
async def on_command_error(ctx, error):
    await internal_log('erro em comando prefixado', f'{type(error).__name__}: {str(error)}', ctx.guild, 'ERROR')
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingPermissions):
        await ctx.send('Você não possui permissão para usar esse comando.', delete_after=8)
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f'Argumento ausente. Use `{COMMAND_PREFIX}ajuda` ou o comando slash equivalente.', delete_after=8)
        return
    if isinstance(error, commands.BadArgument):
        await ctx.send('Não consegui reconhecer um dos argumentos informados.', delete_after=8)
        return
    raise error

@economy_group.command(name='saldo', description='Mostra sua carteira e seu banco')
async def economia_saldo(interaction, membro: discord.Member | None=None):
    membro = membro or interaction.user
    account = wallet(interaction.guild.id, membro.id)
    total = account['wallet'] + account['bank']
    embed = discord.Embed(title=f'Carteira de {membro.display_name}', color=discord.Color.gold())
    embed.add_field(name='Carteira', value=format_money(account['wallet']))
    embed.add_field(name='Banco', value=format_money(account['bank']))
    embed.add_field(name='Patrimônio', value=format_money(total), inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=membro.id == interaction.user.id)

@economy_group.command(name='diaria', description='Recebe sua recompensa diária')
async def economia_diaria(interaction):
    account = wallet(interaction.guild.id, interaction.user.id)
    now = datetime.now(timezone.utc)
    if account.get('daily_at') and (now - datetime.fromisoformat(account['daily_at'])).total_seconds() < 86400:
        remaining = 86400 - int((now - datetime.fromisoformat(account['daily_at'])).total_seconds())
        await interaction.response.send_message(f'Sua diária estará disponível em {remaining // 3600}h {remaining % 3600 // 60}min.', ephemeral=True)
        return
    reward = int(guild_settings(interaction.guild.id).get('daily_reward', 500))
    account['wallet'] += reward
    account['daily_at'] = now.isoformat()
    save_data()
    await audit_log(interaction.guild, 'geral', 'Recompensa diária recebida', interaction.user, format_money(reward))
    await interaction.response.send_message(f'Você recebeu **{format_money(reward)}**.', ephemeral=True)

@economy_group.command(name='pagar', description='Transfere dinheiro para outro membro')
async def economia_pagar(interaction, membro: discord.Member, valor: app_commands.Range[int, 1, 1000000]):
    if membro.bot or membro.id == interaction.user.id:
        await interaction.response.send_message('Escolha um membro válido.', ephemeral=True)
        return
    sender = wallet(interaction.guild.id, interaction.user.id)
    if sender['wallet'] < valor:
        await interaction.response.send_message('Saldo insuficiente na carteira.', ephemeral=True)
        return
    sender['wallet'] -= valor
    wallet(interaction.guild.id, membro.id)['wallet'] += valor
    save_data()
    await audit_log(interaction.guild, 'geral', 'Transferência financeira', interaction.user, f'Para: {membro}; valor: {format_money(valor)}')
    await interaction.response.send_message(f'Você pagou **{format_money(valor)}** para {membro.mention}.', ephemeral=True)

@economy_group.command(name='depositar', description='Deposita dinheiro da carteira no banco')
async def economia_depositar(interaction, valor: app_commands.Range[int, 1, 1000000]):
    account = wallet(interaction.guild.id, interaction.user.id)
    if account['wallet'] < valor:
        await interaction.response.send_message('Você não possui esse valor na carteira.', ephemeral=True)
        return
    account['wallet'] -= valor
    account['bank'] += valor
    save_data()
    await interaction.response.send_message(f'Depósito realizado: **{format_money(valor)}**.', ephemeral=True)

@economy_group.command(name='sacar', description='Saca dinheiro do banco para a carteira')
async def economia_sacar(interaction, valor: app_commands.Range[int, 1, 1000000]):
    account = wallet(interaction.guild.id, interaction.user.id)
    if account['bank'] < valor:
        await interaction.response.send_message('Você não possui esse valor no banco.', ephemeral=True)
        return
    account['bank'] -= valor
    account['wallet'] += valor
    save_data()
    await interaction.response.send_message(f'Saque realizado: **{format_money(valor)}**.', ephemeral=True)

@economy_group.command(name='ranking', description='Mostra os maiores patrimônios do servidor')
async def economia_ranking(interaction):
    accounts = guild_wallets(interaction.guild.id)
    ranking = sorted(accounts.items(), key=lambda item: item[1]['wallet'] + item[1]['bank'], reverse=True)[:10]
    lines = []
    for position, (user_id, account) in enumerate(ranking, 1):
        member = interaction.guild.get_member(int(user_id))
        lines.append(f"**{position}.** {(member.display_name if member else user_id)} — {format_money(account['wallet'] + account['bank'])}")
    await interaction.response.send_message('🏆 **Ranking financeiro**\n' + ('\n'.join(lines) or 'Ainda não há dados.'))

@bot.tree.command(name='avatar', description='Exibe o avatar de um membro')
async def avatar(interaction, membro: discord.Member | None=None):
    membro = membro or interaction.user
    embed = discord.Embed(title=f'Avatar de {membro.display_name}', color=membro.color)
    embed.set_image(url=membro.display_avatar.url)
    embed.set_footer(text=f'ID: {membro.id}')
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='banner', description='Exibe o banner de um membro')
async def banner(interaction, membro: discord.Member | None=None):
    membro = membro or interaction.user
    user = await bot.fetch_user(membro.id)
    if not user.banner:
        await interaction.response.send_message('Esse usuário não possui banner.', ephemeral=True)
        return
    embed = discord.Embed(title=f'Banner de {membro.display_name}', color=membro.color)
    embed.set_image(url=user.banner.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='cargo_info', description='Mostra informações de um cargo')
async def cargo_info(interaction, cargo: discord.Role):
    embed = discord.Embed(title=f'Cargo: {cargo.name}', color=cargo.color)
    embed.add_field(name='ID', value=str(cargo.id))
    embed.add_field(name='Membros', value=str(len(cargo.members)))
    embed.add_field(name='Posição', value=str(cargo.position))
    embed.add_field(name='Menção', value=cargo.mention)
    embed.add_field(name='Criado em', value=discord.utils.format_dt(cargo.created_at, 'F'))
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='canal_info', description='Mostra informações do canal atual')
async def canal_info(interaction):
    channel = interaction.channel
    embed = discord.Embed(title=f'Canal: {channel.name}', color=discord.Color.blurple())
    embed.add_field(name='ID', value=str(channel.id))
    embed.add_field(name='Tipo', value=str(channel.type))
    embed.add_field(name='Criado em', value=discord.utils.format_dt(channel.created_at, 'F'))
    if channel.category:
        embed.add_field(name='Categoria', value=channel.category.name)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name='enquete', description='Cria uma enquete com votação por botões')
@app_commands.describe(pergunta='Pergunta da enquete', opcao_a='Primeira opção', opcao_b='Segunda opção', opcao_c='Terceira opção opcional', opcao_d='Quarta opção opcional', opcao_e='Quinta opção opcional')
async def enquete(interaction, pergunta: str, opcao_a: str, opcao_b: str, opcao_c: str | None=None, opcao_d: str | None=None, opcao_e: str | None=None):
    options = [option[:80] for option in (opcao_a, opcao_b, opcao_c, opcao_d, opcao_e) if option]
    if len({option.casefold() for option in options}) != len(options):
        await interaction.response.send_message('As opções precisam ser diferentes.', ephemeral=True)
        return
    poll_id = os.urandom(5).hex()
    data['polls'][poll_id] = {'guild_id': interaction.guild.id, 'channel_id': interaction.channel.id, 'message_id': None, 'creator_id': interaction.user.id, 'question': pergunta[:256], 'options': options, 'votes': {}, 'open': True}
    save_data()
    await interaction.response.send_message(embed=poll_embed(data['polls'][poll_id]), view=PollView(poll_id))
    message = await interaction.original_response()
    data['polls'][poll_id]['message_id'] = message.id
    save_data()
    await audit_log(interaction.guild, 'geral', 'Enquete criada', interaction.user, pergunta)

@giveaway_group.command(name='criar', description='Cria um sorteio com encerramento automático')
@app_commands.checks.has_permissions(manage_guild=True)
async def sorteio_criar(interaction, premio: str, minutos: app_commands.Range[int, 1, 10080], vencedores: app_commands.Range[int, 1, 20]=1):
    ends_at = datetime.now(timezone.utc) + timedelta(minutes=minutos)
    giveaway_id = os.urandom(5).hex()
    embed = discord.Embed(title='🎉 Sorteio', description=f"**Prêmio:** {premio}\nReaja com 🎉 para participar.\n**Encerra:** {discord.utils.format_dt(ends_at, 'R')}\n**Vencedores:** {vencedores}", color=discord.Color.gold())
    embed.set_footer(text=f'Sorteio {giveaway_id}')
    await interaction.response.send_message(embed=embed)
    message = await interaction.original_response()
    await message.add_reaction('🎉')
    data['giveaways'][giveaway_id] = {'guild_id': interaction.guild.id, 'channel_id': interaction.channel.id, 'message_id': message.id, 'prize': premio[:256], 'winners': vencedores, 'ends_at': ends_at.isoformat(), 'open': True, 'creator_id': interaction.user.id}
    save_data()

@giveaway_group.command(name='encerrar', description='Encerra um sorteio imediatamente')
@app_commands.checks.has_permissions(manage_guild=True)
async def sorteio_encerrar(interaction, sorteio_id: str):
    giveaway = data['giveaways'].get(sorteio_id)
    if not giveaway or int(giveaway['guild_id']) != interaction.guild.id or (not giveaway.get('open')):
        await interaction.response.send_message('Sorteio não encontrado ou já encerrado.', ephemeral=True)
        return
    await finish_giveaway(giveaway, interaction.guild)
    await interaction.response.send_message('Sorteio encerrado.', ephemeral=True)

@bot.tree.command(name='anuncio', description='Publica um anúncio em um canal')
async def anuncio(interaction, canal: discord.TextChannel, titulo: str, mensagem: str, cor: str='5865F2'):
    cor = cor.replace('#', '')
    if not re.fullmatch('[0-9a-fA-F]{6}', cor):
        await interaction.response.send_message('A cor deve ter 6 caracteres hexadecimais.', ephemeral=True)
        return
    embed = discord.Embed(title=titulo[:256], description=mensagem[:4000], color=int(cor, 16), timestamp=datetime.now(timezone.utc))
    if interaction.guild.icon:
        embed.set_author(name=f'Anúncio de {interaction.guild.name}', icon_url=interaction.guild.icon.url)
    else:
        embed.set_author(name=f'Anúncio de {interaction.guild.name}')
    await canal.send(embed=embed)
    await interaction.response.send_message(f'Anúncio enviado em {canal.mention}.', ephemeral=True)
    await audit_log(interaction.guild, 'geral', 'Anúncio publicado', interaction.user, f'Canal: {canal.mention}')

@bot.tree.command(name='embed', description='Cria e publica uma embed configurável')
@app_commands.describe(titulo='Título da embed', descricao='Texto principal da embed', canal='Canal onde a embed será enviada', cor='Cor hexadecimal, por exemplo 5865F2', imagem='URL da imagem grande opcional', thumbnail='URL da miniatura opcional', rodape='Texto do rodapé opcional', autor='Nome exibido no autor opcional')
async def embed_command(interaction, titulo: str, descricao: str, canal: discord.TextChannel | None=None, cor: str='5865F2', imagem: str | None=None, thumbnail: str | None=None, rodape: str | None=None, autor: str | None=None):
    cor = cor.replace('#', '')
    if not re.fullmatch('[0-9a-fA-F]{6}', cor):
        await interaction.response.send_message('A cor deve ter 6 caracteres hexadecimais.', ephemeral=True)
        return
    canal = canal or interaction.channel
    embed = discord.Embed(title=titulo[:256], description=descricao[:4096], color=int(cor, 16), timestamp=datetime.now(timezone.utc))
    if imagem:
        embed.set_image(url=imagem)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    if rodape:
        embed.set_footer(text=rodape[:2048])
    if autor:
        embed.set_author(name=autor[:256])
    try:
        await canal.send(embed=embed)
    except discord.HTTPException:
        await interaction.response.send_message('Não foi possível publicar a embed nesse canal.', ephemeral=True)
        return
    await interaction.response.send_message(f'Embed publicada em {canal.mention}.', ephemeral=True)
    await audit_log(interaction.guild, 'geral', 'Embed personalizada publicada', interaction.user, f'Canal: {canal.mention}; título: {titulo}')

@bot.tree.command(name='slowmode', description='Define o modo lento de um canal')
async def slowmode(interaction, segundos: app_commands.Range[int, 0, 21600], canal: discord.TextChannel | None=None):
    canal = canal or interaction.channel
    await canal.edit(slowmode_delay=segundos, reason=f'Slowmode definido por {interaction.user}')
    await interaction.response.send_message(f'Slowmode de {canal.mention}: **{segundos}s**.')
    await audit_log(interaction.guild, 'moderacao', 'Slowmode alterado', interaction.user, f'{canal.mention}: {segundos}s')

@bot.tree.command(name='trancar', description='Tranca o canal para @everyone')
async def trancar(interaction, motivo: str='Moderador trancou o canal'):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False, reason=motivo)
    await interaction.response.send_message('🔒 Canal trancado.')
    await audit_log(interaction.guild, 'moderacao', 'Canal trancado', interaction.user, interaction.channel.mention)

@bot.tree.command(name='destrancar', description='Destranca o canal para @everyone')
async def destrancar(interaction):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=None, reason=f'Destrancado por {interaction.user}')
    await interaction.response.send_message('🔓 Canal destrancado.')
    await audit_log(interaction.guild, 'moderacao', 'Canal destrancado', interaction.user, interaction.channel.mention)

@bot.tree.command(name='lembrete', description='Envia um lembrete depois de um tempo')
async def lembrete(interaction, minutos: app_commands.Range[int, 1, 10080], mensagem: str):
    deliver_at = datetime.now(timezone.utc) + timedelta(minutes=minutos)
    reminder_id = os.urandom(5).hex()
    data['reminders'][reminder_id] = {'guild_id': interaction.guild.id, 'channel_id': interaction.channel.id, 'user_id': interaction.user.id, 'message': mensagem[:1000], 'deliver_at': deliver_at.isoformat()}
    save_data()
    await interaction.response.send_message(f"Lembrete agendado para {discord.utils.format_dt(deliver_at, 'R')}.", ephemeral=True)

class BotConfigModal(discord.ui.Modal, title='Identidade e presença'):
    nome = discord.ui.TextInput(label='Nome do bot', required=False, max_length=32)
    avatar_url = discord.ui.TextInput(label='URL do avatar', required=False)
    atividade = discord.ui.TextInput(label='Atividade', required=False, max_length=128)

    async def on_submit(self, interaction):
        changes = {}
        if self.nome.value:
            changes['username'] = self.nome.value
        if self.avatar_url.value:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(self.avatar_url.value) as response:
                        if response.status != 200:
                            raise ValueError
                        changes['avatar'] = await response.read()
            except (aiohttp.ClientError, ValueError):
                await interaction.response.send_message('URL de avatar inválida.', ephemeral=True)
                return
        if changes:
            await bot.user.edit(**changes)
        data['bot_profile']['bot_name'] = self.nome.value or data['bot_profile'].get('bot_name')
        data['bot_profile']['bot_activity'] = self.atividade.value or None
        save_data()
        await bot.change_presence(activity=discord.Game(name=self.atividade.value) if self.atividade.value else None)
        await audit_log(interaction.guild, 'geral', 'Identidade do bot atualizada', interaction.user)
        await interaction.response.send_message('Identidade e presença atualizadas.', ephemeral=True)


class LogsConfigModal(discord.ui.Modal, title='Canais de auditoria'):
    geral = discord.ui.TextInput(label='ID do log geral', required=False)
    tickets = discord.ui.TextInput(label='ID do log de tickets', required=False)
    moderacao = discord.ui.TextInput(label='ID do log de moderação', required=False)
    membros = discord.ui.TextInput(label='ID do log de membros', required=False)
    mensagens = discord.ui.TextInput(label='ID do log de mensagens', required=False)

    async def on_submit(self, interaction):
        channels = guild_settings(interaction.guild.id).setdefault('log_channels', {})
        for key in ('geral', 'tickets', 'moderacao', 'membros', 'mensagens'):
            value = getattr(self, key).value
            if value:
                channels[key] = int(value)
        save_data()
        await interaction.response.send_message('Canais de auditoria configurados.', ephemeral=True)

class SecurityConfigModal(discord.ui.Modal, title='Proteção anti-raid'):
    channel_limit = discord.ui.TextInput(label='Canais excluídos para disparar', default='10', required=True)
    window_seconds = discord.ui.TextInput(label='Janela de detecção em segundos', default='30', required=True)
    alert_channel_id = discord.ui.TextInput(label='ID do canal de alertas', required=False)
    ban_actor = discord.ui.TextInput(label='Banir responsável? sim/não', default='sim', required=True)
    restore_channels = discord.ui.TextInput(label='Restaurar canais? sim/não', default='sim', required=True)

    async def on_submit(self, interaction):
        config = security_config(interaction.guild.id)
        config['channel_delete_limit'] = max(2, min(100, int(self.channel_limit.value)))
        config['window_seconds'] = max(5, min(3600, int(self.window_seconds.value)))
        config['ban_actor'] = self.ban_actor.value.lower() in {'sim', 's', 'yes', 'y'}
        config['restore_channels'] = self.restore_channels.value.lower() in {'sim', 's', 'yes', 'y'}
        if self.alert_channel_id.value:
            config['alert_channel_id'] = int(self.alert_channel_id.value)
        save_data()
        await audit_log(interaction.guild, 'seguranca', 'Configuração anti-raid atualizada', interaction.user)
        await interaction.response.send_message('Proteção anti-raid configurada.', ephemeral=True)

class ProtectedChannelModal(discord.ui.Modal, title='Canal contra contas comprometidas'):
    channel_id = discord.ui.TextInput(label='ID do canal (vazio desativa)', placeholder='Cole o ID do canal onde só o bot pode falar', required=False)

    async def on_submit(self, interaction):
        config = security_config(interaction.guild.id)
        value = self.channel_id.value.strip()
        if not value:
            config['protected_channel_id'] = None
            save_data()
            await interaction.response.send_message('Proteção de canal desativada.', ephemeral=True)
            return
        try:
            channel = interaction.guild.get_channel(int(value))
        except ValueError:
            channel = None
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message('ID inválido ou o canal não é um canal de texto.', ephemeral=True)
            return
        config['protected_channel_id'] = channel.id
        save_data()
        warning = discord.Embed(title='⚠️ Canal protegido contra contas comprometidas', description='Este canal é exclusivo para avisos oficiais do bot.\n\n**Não envie mensagens neste canal.**\nQualquer mensagem enviada por um membro será apagada e o autor será banido automaticamente como medida de prevenção contra contas hackeadas.', color=discord.Color.red())
        warning.set_footer(text='Proteção configurada por um administrador')
        await channel.send(embed=warning)
        await audit_log(interaction.guild, 'seguranca', 'Canal protegido configurado', interaction.user, channel.mention)
        await interaction.response.send_message(f'Canal protegido configurado: {channel.mention}.', ephemeral=True)

class ServerEventsModal(discord.ui.Modal, title='Eventos do servidor'):
    welcome_channel = discord.ui.TextInput(label='ID do canal de boas-vindas', required=False)
    leave_channel = discord.ui.TextInput(label='ID do canal de saídas', required=False)
    punishment_channel = discord.ui.TextInput(label='ID do canal de banimentos/expulsões', required=False)
    invite_channel = discord.ui.TextInput(label='ID do canal de convites', required=False)
    enabled = discord.ui.TextInput(label='Ativar eventos? sim/não', default='sim', required=True)

    async def on_submit(self, interaction):
        config = event_config(interaction.guild.id)
        channels = {'welcome_channel_id': self.welcome_channel.value, 'leave_channel_id': self.leave_channel.value, 'punishment_channel_id': self.punishment_channel.value, 'invite_channel_id': self.invite_channel.value}
        for key, value in channels.items():
            if value.strip():
                try:
                    channel = interaction.guild.get_channel(int(value.strip()))
                except ValueError:
                    channel = None
                if not isinstance(channel, discord.TextChannel):
                    await interaction.response.send_message(f'ID inválido para `{key}`.', ephemeral=True)
                    return
                config[key] = channel.id
        is_enabled = self.enabled.value.lower() in {'sim', 's', 'yes', 'y'}
        for key in ('welcome_enabled', 'leave_enabled', 'punishment_enabled', 'invite_enabled'):
            config[key] = is_enabled
        save_data()
        await audit_log(interaction.guild, 'geral', 'Eventos do servidor configurados', interaction.user)
        await interaction.response.send_message('Boas-vindas, saídas, punições e convites configurados.', ephemeral=True)

class AutoModConfigModal(discord.ui.Modal, title='Moderação automática'):
    enabled = discord.ui.TextInput(label='Ativar AutoMod? sim/não', default='não', required=True)
    block_links = discord.ui.TextInput(label='Bloquear links? sim/não', default='não', required=True)
    max_mentions = discord.ui.TextInput(label='Máximo de menções', default='5', required=True)
    blocked_words = discord.ui.TextInput(label='Palavras bloqueadas, separadas por vírgula', required=False)

    async def on_submit(self, interaction):
        config = guild_settings(interaction.guild.id).setdefault('automod', {})
        config['enabled'] = self.enabled.value.casefold() in {'sim', 's', 'yes', 'y'}
        config['block_links'] = self.block_links.value.casefold() in {'sim', 's', 'yes', 'y'}
        try:
            config['max_mentions'] = max(1, min(50, int(self.max_mentions.value)))
        except ValueError:
            await interaction.response.send_message('O limite de menções precisa ser um número.', ephemeral=True)
            return
        config['blocked_words'] = [word.strip() for word in self.blocked_words.value.split(',') if word.strip()]
        save_data()
        await interaction.response.send_message('AutoMod configurado neste servidor.', ephemeral=True)

class ServerFeaturesConfigModal(discord.ui.Modal, title='Autorole e comunidade'):
    autorole_id = discord.ui.TextInput(label='ID do cargo automático', required=False)
    suggestion_channel_id = discord.ui.TextInput(label='ID do canal de sugestões', required=False)
    starboard_channel_id = discord.ui.TextInput(label='ID do canal Starboard', required=False)
    starboard_threshold = discord.ui.TextInput(label='Estrelas para publicar', default='3', required=True)

    async def on_submit(self, interaction):
        settings = guild_settings(interaction.guild.id)
        values = {'autorole_id': self.autorole_id.value.strip(), 'suggestion_channel_id': self.suggestion_channel_id.value.strip(), 'starboard_channel_id': self.starboard_channel_id.value.strip()}
        for key, value in values.items():
            if not value:
                settings[key] = None
                continue
            try:
                resource_id = int(value)
            except ValueError:
                await interaction.response.send_message(f'ID inválido em `{key}`.', ephemeral=True)
                return
            if key == 'autorole_id' and (not interaction.guild.get_role(resource_id)):
                await interaction.response.send_message('O cargo informado não existe neste servidor.', ephemeral=True)
                return
            if key != 'autorole_id' and (not isinstance(interaction.guild.get_channel(resource_id), discord.TextChannel)):
                await interaction.response.send_message(f'O canal informado em `{key}` é inválido.', ephemeral=True)
                return
            settings[key] = resource_id
        try:
            settings['starboard_threshold'] = max(1, min(20, int(self.starboard_threshold.value)))
        except ValueError:
            await interaction.response.send_message('O limite do Starboard precisa ser um número.', ephemeral=True)
            return
        save_data()
        await interaction.response.send_message('Autorole, sugestões e Starboard configurados.', ephemeral=True)

class ConfigView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='Identidade do bot', emoji='🤖', style=discord.ButtonStyle.primary)
    async def bot_settings(self, interaction, button):
        if interaction.user.id != 770039880964505601:
            await interaction.response.send_message('Você não tem permissão para configurar a identidade do bot.', ephemeral=True)
            return
        await interaction.response.send_modal(BotConfigModal())

    @discord.ui.button(label='Tickets e limites', emoji='🎫', style=discord.ButtonStyle.success)
    async def ticket_settings(self, interaction, button):
        await interaction.response.send_modal(TicketConfigModal())

    @discord.ui.button(label='Canais de logs', emoji='📚', style=discord.ButtonStyle.secondary)
    async def log_settings(self, interaction, button):
        await interaction.response.send_modal(LogsConfigModal())

    @discord.ui.button(label='Segurança anti-raid', emoji='🛡️', style=discord.ButtonStyle.danger)
    async def security_settings(self, interaction, button):
        await interaction.response.send_modal(SecurityConfigModal())

    @discord.ui.button(label='Canal protegido', emoji='🚫', style=discord.ButtonStyle.danger)
    async def protected_channel(self, interaction, button):
        await interaction.response.send_modal(ProtectedChannelModal())

    @discord.ui.button(label='Eventos do servidor', emoji='📣', style=discord.ButtonStyle.primary)
    async def server_events(self, interaction, button):
        await interaction.response.send_modal(ServerEventsModal())

    @discord.ui.button(label='AutoMod', emoji='🧰', style=discord.ButtonStyle.danger)
    async def automod_settings(self, interaction, button):
        await interaction.response.send_modal(AutoModConfigModal())

    @discord.ui.button(label='Autorole e comunidade', emoji='🌐', style=discord.ButtonStyle.primary)
    async def community_settings(self, interaction, button):
        await interaction.response.send_modal(ServerFeaturesConfigModal())

    @discord.ui.button(label='Ver resumo', emoji='📊', style=discord.ButtonStyle.secondary)
    async def summary(self, interaction, button):
        settings = guild_settings(interaction.guild.id)
        channels = settings.get('log_channels', {})
        lines = [f'Log {key}: <#{value}>' for key, value in channels.items()]
        embed = discord.Embed(title='Resumo da configuração', description='\n'.join(lines) or 'Nenhum log configurado.', color=discord.Color.blurple())
        embed.add_field(name='Tickets por usuário', value=str(settings.get('max_tickets_per_user', 1)))
        protected = security_config(interaction.guild.id).get('protected_channel_id')
        embed.add_field(name='Canal protegido', value=f'<#{protected}>' if protected else 'Desativado', inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

def fun_target_text(target):
    return target.mention if target else 'alguém'

@fun_group.command(name='casar', description='Casa você com outro membro')
async def diversao_casar(interaction, membro: discord.Member):
    if membro.bot or membro.id == interaction.user.id:
        await interaction.response.send_message('Escolha outro membro que não seja um bot.', ephemeral=True)
        return
    marriages = guild_fun(interaction.guild.id)['marriages']
    if str(interaction.user.id) in marriages or str(membro.id) in marriages:
        await interaction.response.send_message('Um dos membros já está casado.', ephemeral=True)
        return
    marriages[str(interaction.user.id)] = membro.id
    marriages[str(membro.id)] = interaction.user.id
    save_data()
    await interaction.response.send_message(f'💍 {interaction.user.mention} e {membro.mention} agora estão casados! Felicidades ao casal!')

@fun_group.command(name='divorcio', description='Encerra seu casamento divertido')
async def diversao_divorcio(interaction):
    marriages = guild_fun(interaction.guild.id)['marriages']
    partner_id = marriages.pop(str(interaction.user.id), None)
    if partner_id is None:
        await interaction.response.send_message('Você não está casado neste servidor.', ephemeral=True)
        return
    marriages.pop(str(partner_id), None)
    save_data()
    await interaction.response.send_message(f'💔 {interaction.user.mention} está oficialmente solteiro novamente.')

@fun_group.command(name='casados', description='Mostra com quem você está casado')
async def diversao_casados(interaction):
    partner_id = guild_fun(interaction.guild.id)['marriages'].get(str(interaction.user.id))
    partner = interaction.guild.get_member(int(partner_id)) if partner_id else None
    await interaction.response.send_message(f'💍 Você está casado com {partner.mention}.' if partner else 'Você está solteiro.', ephemeral=True)

async def fun_action(interaction, membro, emoji, action):
    target = fun_target_text(membro)
    await interaction.response.send_message(f'{emoji} {interaction.user.mention} {action} {target}!')

@fun_group.command(name='beijar', description='Dá um beijo em alguém')
async def diversao_beijar(interaction, membro: discord.Member):
    await fun_action(interaction, membro, '💋', 'deu um beijo em')

@fun_group.command(name='abracar', description='Dá um abraço em alguém')
async def diversao_abracar(interaction, membro: discord.Member):
    await fun_action(interaction, membro, '🤗', 'abraçou')

@fun_group.command(name='carinho', description='Faz carinho em alguém')
async def diversao_carinho(interaction, membro: discord.Member):
    await fun_action(interaction, membro, '🫶', 'fez carinho em')

@fun_group.command(name='tapar', description='Dá um tapa de brincadeira')
async def diversao_tapar(interaction, membro: discord.Member):
    await fun_action(interaction, membro, '👋', 'deu um tapa de brincadeira em')

@fun_group.command(name='ship', description='Calcula a compatibilidade de um casal')
async def diversao_ship(interaction, membro: discord.Member):
    if membro.id == interaction.user.id:
        await interaction.response.send_message('Escolha outra pessoa para fazer o ship.', ephemeral=True)
        return
    seed = f'{min(interaction.user.id, membro.id)}:{max(interaction.user.id, membro.id)}:{interaction.guild.id}'
    score = sum((ord(char) for char in seed)) % 101
    hearts = '💖' * max(1, min(5, score // 20 + 1))
    await interaction.response.send_message(f'💞 **Ship de {interaction.user.display_name} + {membro.display_name}**\n{hearts} **{score}%** de compatibilidade!')

@fun_group.command(name='dado', description='Rola um dado')
async def diversao_dado(interaction, lados: app_commands.Range[int, 2, 1000]=6):
    await interaction.response.send_message(f'🎲 {interaction.user.mention} rolou **{random.randint(1, lados)}** em um d{lados}.')

@fun_group.command(name='moeda', description='Joga uma moeda')
async def diversao_moeda(interaction):
    await interaction.response.send_message(f"🪙 Caiu **{random.choice(('cara', 'coroa'))}**!")

@fun_group.command(name='8ball', description='Responde sua pergunta')
async def diversao_8ball(interaction, pergunta: str):
    answers = ('Com certeza!', 'Provavelmente.', 'Os sinais são positivos.', 'Não conte com isso.', 'Melhor não apostar nisso.', 'Pergunte novamente mais tarde.')
    await interaction.response.send_message(f'🎱 **Pergunta:** {pergunta}\n**Resposta:** {random.choice(answers)}')

@fun_group.command(name='escolher', description='Escolhe uma opção aleatória')
async def diversao_escolher(interaction, opcoes: str):
    choices = [choice.strip() for choice in opcoes.split(',') if choice.strip()]
    if len(choices) < 2:
        await interaction.response.send_message('Informe pelo menos duas opções separadas por vírgula.', ephemeral=True)
        return
    await interaction.response.send_message(f'🎯 Eu escolho: **{random.choice(choices)}**')

@fun_group.command(name='chance', description='Calcula uma chance divertida')
async def diversao_chance(interaction, pergunta: str):
    await interaction.response.send_message(f'🔮 A chance de **{pergunta}** acontecer é de **{random.randint(0, 100)}%**.')

@fun_group.command(name='pp', description='Mede uma quantidade totalmente fictícia')
async def diversao_pp(interaction, membro: discord.Member | None=None):
    membro = membro or interaction.user
    await interaction.response.send_message(f'📏 O medidor de {membro.mention} marcou **{random.randint(1, 30)} cm**. Resultado puramente fictício!')

@fun_group.command(name='gay', description='Mede uma porcentagem fictícia e respeitosa')
async def diversao_gay(interaction, membro: discord.Member | None=None):
    membro = membro or interaction.user
    await interaction.response.send_message(f'🌈 O medidor divertido de {membro.mention} marcou **{random.randint(0, 100)}%**. Isso é só uma brincadeira, não uma afirmação sobre a pessoa.')

def format_uptime():
    seconds = int((datetime.now(timezone.utc) - BOT_START_TIME).total_seconds())
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    parts = []
    if days:
        parts.append(f'{days}d')
    if hours:
        parts.append(f'{hours}h')
    if minutes:
        parts.append(f'{minutes}min')
    parts.append(f'{seconds}s')
    return ' '.join(parts)

def user_inventory(guild_id, user_id):
    guild_inventory = data['economy_inventory'].setdefault(str(guild_id), {})
    return guild_inventory.setdefault(str(user_id), {})

def streak_record(guild_id, user_id):
    guild_streaks = data['streaks'].setdefault(str(guild_id), {})
    return guild_streaks.setdefault(str(user_id), {'current': 0, 'best': 0, 'last_day': None})

def update_streak(guild_id, user_id):
    record = streak_record(guild_id, user_id)
    today = datetime.now(timezone.utc).date()
    if record['last_day'] == today.isoformat():
        return record
    if record['last_day']:
        try:
            previous = datetime.fromisoformat(record['last_day']).date()
            difference = (today - previous).days
            if difference == 1:
                record['current'] += 1
            else:
                record['current'] = 1
        except ValueError:
            record['current'] = 1
    else:
        record['current'] = 1
    record['last_day'] = today.isoformat()
    if record['current'] > record['best']:
        record['best'] = record['current']
    save_data()
    return record

def achievement_list(guild_id, user_id):
    achievements = []
    level = level_record(guild_id, user_id)
    account = wallet(guild_id, user_id)
    inventory = user_inventory(guild_id, user_id)
    total_money = account['wallet'] + account['bank']
    reputation = data['reputations'].get(str(guild_id), {}).get(str(user_id), {}).get('total', 0)
    transfers = sum((1 for item in data['transfers'] if int(item['guild_id']) == guild_id and (int(item['from']) == user_id or int(item['to']) == user_id)))
    inventory_amount = sum(inventory.values())
    if level['xp'] >= 100:
        achievements.append('🥉 Primeiro nível')
    if level['xp'] >= 2500:
        achievements.append('🥇 Veterano')
    if total_money >= 5000:
        achievements.append('💰 Rico')
    if total_money >= 100000:
        achievements.append('💎 Milionário')
    if reputation >= 10:
        achievements.append('⭐ Respeitado')
    if transfers >= 10:
        achievements.append('💸 Comerciante')
    if inventory_amount >= 5:
        achievements.append('🎒 Colecionador')
    return achievements

@economy_group.command(name='loja', description='Mostra a loja do servidor')
async def economia_loja(interaction):
    lines = []
    for item_id, item in SHOP_ITEMS.items():
        lines.append(f"**{item['name']}** — `{item_id}`\nComprar: **{format_money(item['price'])}**\nVender: **{format_money(item['sell'])}**")
    embed = discord.Embed(title='🛒 Loja', description='\n\n'.join(lines), color=discord.Color.gold())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@economy_group.command(name='comprar', description='Compra um item da loja')
async def economia_comprar(interaction, item: str, quantidade: app_commands.Range[int, 1, 100]=1):
    item = item.casefold()
    if item not in SHOP_ITEMS:
        await interaction.response.send_message('Esse item não existe. Use `/economia loja`.', ephemeral=True)
        return
    config = SHOP_ITEMS[item]
    total = config['price'] * quantidade
    account = wallet(interaction.guild.id, interaction.user.id)
    if account['wallet'] < total:
        await interaction.response.send_message('Você não possui coins suficientes na carteira.', ephemeral=True)
        return
    account['wallet'] -= total
    inventory = user_inventory(interaction.guild.id, interaction.user.id)
    inventory[item] = inventory.get(item, 0) + quantidade
    save_data()
    await interaction.response.send_message(f"✅ Você comprou **{quantidade}x {config['name']}** por **{format_money(total)}**.", ephemeral=True)

@economy_group.command(name='vender', description='Vende um item da sua mochila')
async def economia_vender(interaction, item: str, quantidade: app_commands.Range[int, 1, 100]=1):
    item = item.casefold()
    if item not in SHOP_ITEMS:
        await interaction.response.send_message('Esse item não existe.', ephemeral=True)
        return
    inventory = user_inventory(interaction.guild.id, interaction.user.id)
    current = inventory.get(item, 0)
    if current < quantidade:
        await interaction.response.send_message('Você não possui essa quantidade.', ephemeral=True)
        return
    config = SHOP_ITEMS[item]
    total = config['sell'] * quantidade
    inventory[item] -= quantidade
    if inventory[item] <= 0:
        inventory.pop(item, None)
    wallet(interaction.guild.id, interaction.user.id)['wallet'] += total
    save_data()
    await interaction.response.send_message(f"✅ Você vendeu **{quantidade}x {config['name']}** por **{format_money(total)}**.", ephemeral=True)

@economy_group.command(name='trabalho', description='Trabalha para ganhar coins')
async def economia_trabalho(interaction):
    key = f'{interaction.guild.id}:{interaction.user.id}'
    now = time.time()
    last = data['work_cooldowns'].get(key, 0)
    if now - last < 900:
        remaining = 900 - int(now - last)
        await interaction.response.send_message(f'Você está cansado. Tente novamente em **{remaining // 60}min {remaining % 60}s**.', ephemeral=True)
        return
    reward = random.randint(100, 300)
    account = wallet(interaction.guild.id, interaction.user.id)
    account['wallet'] += reward
    data['work_cooldowns'][key] = now
    save_data()
    await interaction.response.send_message(f'💼 Você trabalhou e ganhou **{format_money(reward)}**!', ephemeral=True)

@economy_group.command(name='roubar', description='Tenta roubar outro membro')
async def economia_roubar(interaction, membro: discord.Member):
    if membro.bot or membro.id == interaction.user.id:
        await interaction.response.send_message('Escolha outro membro.', ephemeral=True)
        return
    key = f'{interaction.guild.id}:{interaction.user.id}'
    now = time.time()
    last = data['rob_cooldowns'].get(key, 0)
    if now - last < 3600:
        remaining = 3600 - int(now - last)
        await interaction.response.send_message(f'Você precisa esperar **{remaining // 60}min**.', ephemeral=True)
        return
    data['rob_cooldowns'][key] = now
    target = wallet(interaction.guild.id, membro.id)
    thief = wallet(interaction.guild.id, interaction.user.id)
    if random.random() <= 0.45 and target['wallet'] > 0:
        amount = random.randint(1, max(1, min(target['wallet'], 500)))
        target['wallet'] -= amount
        thief['wallet'] += amount
        message = f'🥷 Você roubou **{format_money(amount)}** de {membro.mention}!'
    else:
        fine = min(thief['wallet'], random.randint(25, 150))
        thief['wallet'] -= fine
        message = f'🚨 Você foi pego tentando roubar {membro.mention} e perdeu **{format_money(fine)}**.'
    save_data()
    await interaction.response.send_message(message)

@economy_group.command(name='transferencias', description='Mostra seu histórico de transferências')
async def economia_transferencias(interaction):
    records = [item for item in data['transfers'] if int(item['guild_id']) == interaction.guild.id and (int(item['from']) == interaction.user.id or int(item['to']) == interaction.user.id)][-15:]
    if not records:
        await interaction.response.send_message('Você ainda não possui transferências.', ephemeral=True)
        return
    lines = []
    for item in reversed(records):
        if int(item['from']) == interaction.user.id:
            lines.append(f"📤 Para <@{item['to']}> — **{format_money(item['value'])}**")
        else:
            lines.append(f"📥 De <@{item['from']}> — **{format_money(item['value'])}**")
    embed = discord.Embed(title='💸 Histórico financeiro', description='\n'.join(lines), color=discord.Color.gold())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name='historico', description='Mostra o histórico recente de moderação')
@app_commands.checks.has_permissions(view_audit_log=True)
async def historico(interaction, membro: discord.Member | None=None):
    lines = []
    try:
        async for entry in interaction.guild.audit_logs(limit=50):
            target = entry.target
            if membro and getattr(target, 'id', None) != membro.id:
                continue
            action = str(entry.action).split('.')[-1]
            lines.append(f"• **{action}** — {entry.user.mention} → `{getattr(target, 'id', 'n/a')}`")
            if len(lines) >= 15:
                break
    except discord.Forbidden:
        await interaction.response.send_message('Não tenho acesso ao registro de auditoria.', ephemeral=True)
        return
    embed = discord.Embed(title='📚 Histórico', description='\n'.join(lines) or 'Nenhum registro encontrado.', color=discord.Color.blurple())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name='limpar_usuario', description='Apaga mensagens de um usuário no canal')
@app_commands.checks.has_permissions(manage_messages=True)
async def limpar_usuario(interaction, membro: discord.Member, quantidade: app_commands.Range[int, 1, 100]):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=quantidade, check=lambda message: message.author.id == membro.id)
    await interaction.followup.send(f'🧹 {len(deleted)} mensagem(ns) de {membro.mention} apagadas.', ephemeral=True)

@bot.tree.command(name='modo_moderacao', description='Ativa ou desativa o modo de moderação')
@app_commands.checks.has_permissions(administrator=True)
async def modo_moderacao(interaction, ativo: bool):
    config = security_config(interaction.guild.id)
    config['lockdown'] = ativo
    for channel in interaction.guild.text_channels:
        try:
            await channel.set_permissions(interaction.guild.default_role, send_messages=False if ativo else None, reason='Modo de moderação')
        except discord.HTTPException:
            pass
    save_data()
    await interaction.response.send_message('🛡️ Modo de moderação ' + ('ativado.' if ativo else 'desativado.'), ephemeral=True)

@bot.tree.command(name='level', description='Mostra seu nível e XP')
async def level(interaction):
    record = level_record(interaction.guild.id, interaction.user.id)
    await interaction.response.send_message(f"🏅 **Nível de {interaction.user.display_name}**\nNível: **{level_from_xp(record['xp'])}**\nXP: **{record['xp']}**\nTítulo: **{record['title'] or 'Sem título'}**", ephemeral=True)

@bot.tree.command(name='ranking', description='Mostra o ranking geral de XP')
async def ranking(interaction):
    records = guild_levels(interaction.guild.id)
    ranking_data = sorted(records.items(), key=lambda item: item[1].get('xp', 0), reverse=True)[:10]
    lines = []
    for position, (user_id, record) in enumerate(ranking_data, 1):
        member = interaction.guild.get_member(int(user_id))
        lines.append(f"**{position}.** {(member.display_name if member else user_id)} — {record.get('xp', 0)} XP")
    await interaction.response.send_message('🏆 **Ranking de XP**\n' + ('\n'.join(lines) or 'Ainda não há dados.'))

@bot.tree.command(name='ranking_semanal', description='Mostra o ranking semanal de XP')
async def ranking_semanal(interaction):
    records = data['weekly_xp'].get(str(interaction.guild.id), {})
    ranking_data = sorted(records.items(), key=lambda item: item[1], reverse=True)[:10]
    lines = []
    for position, (user_id, xp) in enumerate(ranking_data, 1):
        member = interaction.guild.get_member(int(user_id))
        lines.append(f'**{position}.** {(member.display_name if member else user_id)} — {xp} XP')
    await interaction.response.send_message('📅 **Ranking semanal**\n' + ('\n'.join(lines) or 'Ainda não há XP semanal.'))

@bot.tree.command(name='recompensas', description='Mostra as recompensas por nível')
async def recompensas(interaction):
    embed = discord.Embed(title='🎁 Recompensas por nível', description='**Nível 5** — 500 coins\n**Nível 10** — 1.000 coins\n**Nível 20** — 2.500 coins\n**Nível 30** — 5.000 coins\n**Nível 50** — 10.000 coins', color=discord.Color.green())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name='conquista', description='Mostra suas conquistas')
async def conquista(interaction):
    achievements = achievement_list(interaction.guild.id, interaction.user.id)
    embed = discord.Embed(title=f'🏆 Conquistas de {interaction.user.display_name}', description='\n'.join(achievements) if achievements else 'Você ainda não desbloqueou nenhuma.', color=discord.Color.gold())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name='streak', description='Mostra sua sequência de atividade')
async def streak(interaction):
    record = update_streak(interaction.guild.id, interaction.user.id)
    await interaction.response.send_message(f"🔥 Sua sequência atual: **{record['current']} dia(s)**\n🏆 Seu melhor recorde: **{record['best']} dia(s)**", ephemeral=True)

@bot.tree.command(name='botinfo', description='Mostra informações do FuriousBot')
async def botinfo(interaction):
    total_members = sum((guild.member_count or 0 for guild in bot.guilds))
    embed = discord.Embed(title='🤖 FuriousBot', color=discord.Color.blurple())
    embed.set_thumbnail(url=PAINEL_IMAGE_URL)
    embed.add_field(name='Servidores', value=str(len(bot.guilds)))
    embed.add_field(name='Membros', value=str(total_members))
    embed.add_field(name='Latência', value=f'{round(bot.latency * 1000)}ms')
    embed.add_field(name='Uptime', value=format_uptime(), inline=False)
    embed.add_field(name='Python', value=sys.version.split()[0])
    embed.add_field(name='Discord.py', value=discord.__version__)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='uptime', description='Mostra há quanto tempo o bot está online')
async def uptime(interaction):
    await interaction.response.send_message(f'⏱️ Estou online há **{format_uptime()}**.')

@bot.tree.command(name='status', description='Mostra o status dos sistemas do bot')
async def status(interaction):
    embed = discord.Embed(title='📊 Status do FuriousBot', color=discord.Color.green())
    embed.add_field(name='Discord', value='🟢 Online')
    embed.add_field(name='Latência', value=f'{round(bot.latency * 1000)}ms')
    embed.add_field(name='Servidores', value=str(len(bot.guilds)))
    ticket_v3_data = t3_load()
    embed.add_field(
        name='Tickets',
        value=str(len(ticket_v3_data.get('tickets', {})))
    )
    embed.add_field(
        name='Painéis',
        value=str(len(ticket_v3_data.get('panels', {})))
    )
    embed.add_field(name='Backups', value=str(len(list(Path('backups').glob('tickets_v3-*.json')))), inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='comandos', description='Lista os principais comandos do bot')
async def comandos(interaction):
    embed = discord.Embed(title='📚 Comandos do FuriousBot', color=discord.Color.blurple())
    embed.add_field(name='🛡️ Segurança', value='`/seguranca status`\n`/seguranca auditoria`\n`/seguranca banlist`\n`/seguranca scan`', inline=False)
    embed.add_field(name='🎫 Tickets', value='`/ticket painel`\n`/ticket status`\n`/ticket fechar`', inline=False)
    embed.add_field(name='💰 Economia', value='`/economia saldo`\n`/economia loja`\n`/economia comprar`\n`/economia trabalho`\n`/economia roubar`', inline=False)
    embed.add_field(name='🏆 Comunidade', value='`/level`\n`/ranking`\n`/ranking_semanal`\n`/conquista`\n`/streak`', inline=False)
    embed.add_field(name='🎮 Diversão', value='`/duelo`\n`/roleta`\n`/forca`\n`/quiz`\n`/meme`\n`/minigame`', inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name='duelo', description='Desafia outro membro para um duelo')
async def duelo(interaction, membro: discord.Member):
    if membro.bot or membro.id == interaction.user.id:
        await interaction.response.send_message('Escolha outro membro.', ephemeral=True)
        return
    my_power = random.randint(1, 100)
    target_power = random.randint(1, 100)
    if my_power > target_power:
        result = f'🏆 {interaction.user.mention} venceu!'
    elif target_power > my_power:
        result = f'🏆 {membro.mention} venceu!'
    else:
        result = '🤝 Empate!'
    await interaction.response.send_message(f'⚔️ **Duelo!**\n\n{interaction.user.mention}: `{my_power}`\n{membro.mention}: `{target_power}`\n\n{result}')

@bot.tree.command(name='roleta', description='Escolhe uma opção aleatória')
async def roleta(interaction, opcoes: str='sim,não'):
    choices = [choice.strip() for choice in opcoes.split(',') if choice.strip()]
    if len(choices) < 2:
        await interaction.response.send_message('Informe pelo menos duas opções separadas por vírgula.', ephemeral=True)
        return
    choice = random.choice(choices)
    await interaction.response.send_message(f'🎰 A roleta escolheu: **{choice}**')

class QuizView(discord.ui.View):

    def __init__(self, question):
        super().__init__(timeout=60)
        self.answer = question['answer']
        self.done = False
        for index, option in enumerate(question['options']):
            button = discord.ui.Button(label=option[:80], style=discord.ButtonStyle.primary, row=index // 2)

            async def callback(interaction, index=index, button=button):
                if self.done:
                    await interaction.response.send_message('Esse quiz já foi respondido.', ephemeral=True)
                    return
                self.done = True
                for child in self.children:
                    child.disabled = True
                if index == self.answer:
                    description = '✅ Resposta correta!'
                    color = discord.Color.green()
                else:
                    description = '❌ Resposta errada!'
                    color = discord.Color.red()
                embed = discord.Embed(title='🧠 Quiz', description=description, color=color)
                await interaction.response.edit_message(embed=embed, view=self)
            button.callback = callback
            self.add_item(button)

@bot.tree.command(name='quiz', description='Responde um quiz rápido')
async def quiz(interaction):
    question = random.choice(QUIZ_QUESTIONS)
    embed = discord.Embed(title='🧠 Quiz', description=question['question'], color=discord.Color.blurple())
    await interaction.response.send_message(embed=embed, view=QuizView(question))

class HangmanView(discord.ui.View):

    def __init__(self, word):
        super().__init__(timeout=180)
        self.word = word.casefold()
        self.guessed = set()
        self.errors = 0
        self.select = discord.ui.Select(placeholder='Escolha uma letra', min_values=1, max_values=1, options=[discord.SelectOption(label=letter.upper(), value=letter) for letter in 'abcdefghijklmnopqrstuvwxyz'])
        self.select.callback = self.select_letter
        self.add_item(self.select)

    def display_word(self):
        return ' '.join((letter.upper() if letter in self.guessed else '＿' for letter in self.word))

    async def select_letter(self, interaction):
        letter = self.select.values[0]
        if letter in self.guessed:
            await interaction.response.send_message('Você já tentou essa letra.', ephemeral=True)
            return
        self.guessed.add(letter)
        if letter not in self.word:
            self.errors += 1
        won = all((letter in self.guessed for letter in self.word))
        lost = self.errors >= 6
        if won or lost:
            for child in self.children:
                child.disabled = True
        if won:
            description = f'🎉 Você venceu!\n\nPalavra: **{self.word.upper()}**'
            color = discord.Color.green()
        elif lost:
            description = f'💀 Você perdeu!\n\nA palavra era: **{self.word.upper()}**'
            color = discord.Color.red()
        else:
            description = f'Palavra: **{self.display_word()}**\n\nErros: **{self.errors}/6**'
            color = discord.Color.blurple()
        embed = discord.Embed(title='🔤 Forca', description=description, color=color)
        await interaction.response.edit_message(embed=embed, view=self)

@bot.tree.command(name='forca', description='Joga uma partida de forca')
async def forca(interaction):
    word = random.choice(HANGMAN_WORDS)
    view = HangmanView(word)
    embed = discord.Embed(title='🔤 Forca', description=f'Palavra: **{view.display_word()}**\n\nEscolha uma letra no menu abaixo.', color=discord.Color.blurple())
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name='meme', description='Envia um meme aleatório')
async def meme(interaction):
    await interaction.response.defer()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://meme-api.com/gimme/wholesomememes') as response:
                if response.status != 200:
                    raise RuntimeError(f'HTTP {response.status}')
                post = await response.json()
        title = post.get('title', 'Meme')
        image = post.get('url')
        embed = discord.Embed(title=title[:256], color=discord.Color.blurple())
        if image:
            embed.set_image(url=image)
        if post.get('postLink'):
            embed.set_footer(text='Fonte: meme-api.com')
        await interaction.followup.send(embed=embed)
    except Exception:
        await interaction.followup.send('Não consegui buscar um meme agora.')

@bot.tree.command(name='minigame', description='Joga um minigame rápido')
async def minigame(interaction):
    game = random.choice(('cara ou coroa', 'dado', 'roleta'))
    if game == 'cara ou coroa':
        result = random.choice(('🪙 Cara!', '🪙 Coroa!'))
    elif game == 'dado':
        result = f'🎲 Você tirou **{random.randint(1, 6)}**!'
    else:
        result = random.choice(('🎰 Você ganhou!', '🎰 Você perdeu!', '🎰 Quase!', '🎰 JACKPOT!'))
    await interaction.response.send_message(f'🎮 **Minigame**\n\n{result}')

class VerificationPanelModal(discord.ui.Modal, title='Painel de Verificação'):
    cargo_id = discord.ui.TextInput(label='ID do cargo verificado', required=True)
    canal_id = discord.ui.TextInput(label='ID do canal', required=True)
    ativo = discord.ui.TextInput(label='Ativo? sim/não', default='sim', required=True)

    async def on_submit(self, interaction):
        try:
            role_id = int(self.cargo_id.value.strip())
            channel_id = int(self.canal_id.value.strip())
        except ValueError:
            await interaction.response.send_message('O ID do cargo ou canal é inválido.', ephemeral=True)
            return
        role = interaction.guild.get_role(role_id)
        channel = interaction.guild.get_channel(channel_id)
        if not role:
            await interaction.response.send_message('Cargo não encontrado.', ephemeral=True)
            return
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message('Canal inválido.', ephemeral=True)
            return
        config = verification_config(interaction.guild.id)
        config['enabled'] = self.ativo.value.casefold() in {'sim', 's', 'yes', 'y'}
        config['verified_role_id'] = role.id
        config['channel_id'] = channel.id
        embed = discord.Embed(title='Verificação do servidor', description='Clique no botão abaixo para confirmar que você é um membro real e liberar o acesso.', color=discord.Color.green())
        message = await channel.send(embed=embed, view=VerificationView())
        config['message_id'] = message.id
        save_data()
        await interaction.response.send_message(f'✅ Painel de verificação publicado em {channel.mention}.', ephemeral=True)

class PontoPainelModal(discord.ui.Modal, title='Painel de Bate-Ponto'):
    canal_id = discord.ui.TextInput(label='ID do canal', placeholder='Ex: 123456789012345678', required=True)

    async def on_submit(self, interaction):
        try:
            channel_id = int(self.canal_id.value.strip())
        except ValueError:
            await interaction.response.send_message('ID do canal inválido.', ephemeral=True)
            return
        canal = interaction.guild.get_channel(channel_id)
        if not isinstance(canal, discord.TextChannel):
            await interaction.response.send_message('Esse ID não pertence a um canal de texto.', ephemeral=True)
            return
        guild_settings(interaction.guild.id)['timeclock_channel_id'] = canal.id
        save_data()
        banner = discord.File(io.BytesIO(visual_banner('Controle de jornada', 'Registre entrada, saída e confirme sua atividade', '16A085')), filename='ponto.svg')
        embed = discord.Embed(title='Bate-ponto', description='Use os botões para controlar sua jornada. A cada hora o bot pedirá uma confirmação.', color=discord.Color.green())
        embed.set_image(url='attachment://ponto.svg')
        await canal.send(embed=embed, file=banner, view=ClockView())
        await interaction.response.send_message(f'✅ Painel de ponto publicado em {canal.mention}.', ephemeral=True)

class InternalLogsPanelModal(discord.ui.Modal, title='Logs internos'):
    canal_id = discord.ui.TextInput(label='ID do canal', placeholder='Deixe vazio para remover', required=False)

    async def on_submit(self, interaction):
        if interaction.user.id != 770039880964505601:
            await interaction.response.send_message('❌ Apenas o proprietário do bot pode configurar os Internal Logs.', ephemeral=True)
            return
        value = self.canal_id.value.strip()
        if not value:
            data['internal_logs']['channel_id'] = None
            data['internal_logs']['guild_id'] = None
            save_data()
            await interaction.response.send_message('✅ Canal de logs internos removido.', ephemeral=True)
            return
        try:
            channel_id = int(value)
        except ValueError:
            await interaction.response.send_message('ID inválido.', ephemeral=True)
            return
        channel = interaction.guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message('Esse canal é inválido.', ephemeral=True)
            return
        data['internal_logs']['channel_id'] = channel.id
        data['internal_logs']['guild_id'] = interaction.guild.id
        save_data()
        await interaction.response.send_message(f'✅ Logs internos configurados em {channel.mention}.', ephemeral=True)

class PermissionsPanelModal(discord.ui.Modal, title='Permissões do FuriousBot'):
    cargo_id = discord.ui.TextInput(label='ID do cargo autorizado', placeholder='Deixe vazio para remover', required=False)

    async def on_submit(self, interaction):
        value = self.cargo_id.value.strip()
        if not value:
            guild_settings(interaction.guild.id)['command_role_id'] = None
            save_data()
            await interaction.response.send_message('✅ Cargo personalizado removido.', ephemeral=True)
            return
        try:
            role_id = int(value)
        except ValueError:
            await interaction.response.send_message('ID do cargo inválido.', ephemeral=True)
            return
        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.response.send_message('Cargo não encontrado.', ephemeral=True)
            return
        guild_settings(interaction.guild.id)['command_role_id'] = role.id
        save_data()
        await interaction.response.send_message(f'✅ {role.mention} agora pode usar os comandos configuráveis.', ephemeral=True)

class BackupPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='Criar backup', emoji='💾', style=discord.ButtonStyle.success)
    async def criar(self, interaction, button):
        backup = create_data_backup()
        if not backup:
            await interaction.response.send_message('Não existem dados para copiar.', ephemeral=True)
            return
        await interaction.response.send_message(f'✅ Backup criado: `{backup.name}`', ephemeral=True)

    @discord.ui.button(label='Ver backups', emoji='📋', style=discord.ButtonStyle.secondary)
    async def listar(self, interaction, button):
        backups = sorted(Path('backups').glob('tickets_v3-*.json'), key=lambda path: path.stat().st_mtime, reverse=True)
        if not backups:
            text = 'Nenhum backup encontrado.'
        else:
            text = '\n'.join((f'• `{backup.name}`' for backup in backups[:20]))
        embed = discord.Embed(title='💾 Backups', description=text, color=discord.Color.blurple())
        await interaction.response.send_message(embed=embed, ephemeral=True)



class SecurityPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='Anti-Raid', emoji='🛡️', style=discord.ButtonStyle.danger, row=0)
    async def antiraid(self, interaction, button):
        await interaction.response.send_modal(SecurityConfigModal())

    @discord.ui.button(label='Canal protegido', emoji='🚫', style=discord.ButtonStyle.danger, row=0)
    async def protegido(self, interaction, button):
        await interaction.response.send_modal(ProtectedChannelModal())

    @discord.ui.button(label='Eventos', emoji='📣', style=discord.ButtonStyle.primary, row=1)
    async def eventos(self, interaction, button):
        await interaction.response.send_modal(ServerEventsModal())

    @discord.ui.button(label='AutoMod', emoji='🧰', style=discord.ButtonStyle.danger, row=1)
    async def automod(self, interaction, button):
        await interaction.response.send_modal(AutoModConfigModal())

    @discord.ui.button(label='Comunidade', emoji='🌐', style=discord.ButtonStyle.primary, row=2)
    async def comunidade(self, interaction, button):
        await interaction.response.send_modal(ServerFeaturesConfigModal())

class PainelPrincipalView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='Geral', emoji='🤖', style=discord.ButtonStyle.primary, row=0)
    async def geral(self, interaction, button):
        await interaction.response.send_message('⚙️ Configurações gerais', view=ConfigView(), ephemeral=True)

    @discord.ui.button(label='Tickets', emoji='🎫', style=discord.ButtonStyle.success, row=0)
    async def tickets(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title='🎫 TICKET V3 ULTIMATE',
            description=(
                'Configure e gerencie o sistema profissional de tickets.\n\n'
                'Selecione uma opção abaixo para administrar painéis, '
                'tipos de atendimento, equipe, threads, transcripts e automações.'
            ),
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(
            embed=embed,
            view=T3AdminView(),
            ephemeral=True
        )

    @discord.ui.button(label='Ponto', emoji='⏱️', style=discord.ButtonStyle.success, row=0)
    async def ponto(self, interaction, button):
        await interaction.response.send_modal(PontoPainelModal())

    @discord.ui.button(label='Segurança', emoji='🛡️', style=discord.ButtonStyle.danger, row=0)
    async def seguranca(self, interaction, button):
        await interaction.response.send_message('🛡️ Configurações de Segurança', view=SecurityPanelView(), ephemeral=True)

    @discord.ui.button(label='Verificação', emoji='✅', style=discord.ButtonStyle.primary, row=1)
    async def verificacao(self, interaction, button):
        await interaction.response.send_modal(VerificationPanelModal())

    @discord.ui.button(label='Logs', emoji='📚', style=discord.ButtonStyle.secondary, row=1)
    async def logs(self, interaction, button):
        if interaction.user.id != 770039880964505601:
            await interaction.response.send_message('❌ Apenas o proprietário do bot pode configurar os Internal Logs.', ephemeral=True)
            return
        await interaction.response.send_modal(InternalLogsPanelModal())

    @discord.ui.button(label='Permissões', emoji='🔐', style=discord.ButtonStyle.secondary, row=1)
    async def permissoes(self, interaction, button):
        await interaction.response.send_modal(PermissionsPanelModal())

    @discord.ui.button(label='Backups', emoji='💾', style=discord.ButtonStyle.secondary, row=1)
    async def backups(self, interaction, button):
        await interaction.response.send_message('💾 Backups', view=BackupPanelView(), ephemeral=True)

@bot.tree.command(name='painel', description='Abre o painel de configurações do FuriousBot')
@app_commands.checks.has_permissions(administrator=True)
async def painel(interaction):
    embed = discord.Embed(title='⚡ FuriousBot', description='Central de configuração do bot.\n\nEscolha uma categoria abaixo para configurar os sistemas deste servidor.', color=discord.Color.blurple())
    embed.set_image(url=PAINEL_GIF_URL)
    embed.set_footer(text='FuriousBot • Painel administrativo')
    await interaction.response.send_message(embed=embed, view=PainelPrincipalView(), ephemeral=True)

@security_group.command(name='status', description='Mostra o estado da proteção anti-raid')
async def seguranca_status(interaction):
    config = security_config(interaction.guild.id)
    alert = f"<#{config['alert_channel_id']}>" if config.get('alert_channel_id') else 'Canal do sistema'
    protected = f"<#{config['protected_channel_id']}>" if config.get('protected_channel_id') else 'Desativado'
    embed = discord.Embed(title='🛡️ Status de segurança', color=discord.Color.green() if config['enabled'] else discord.Color.red())
    embed.add_field(name='Anti-raid', value='Ativo' if config['enabled'] else 'Desativado')
    embed.add_field(name='Limite', value=f"{config['channel_delete_limit']} canais / {config['window_seconds']}s")
    embed.add_field(name='Banir responsável', value='Sim' if config['ban_actor'] else 'Não')
    embed.add_field(name='Restaurar canais', value='Sim' if config['restore_channels'] else 'Não')
    embed.add_field(name='Canal de alerta', value=alert, inline=False)
    embed.add_field(name='Canal protegido', value=protected, inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@security_group.command(name='snapshot', description='Atualiza a cópia dos canais para restauração')
async def seguranca_snapshot(interaction):
    await snapshot_guild_channels(interaction.guild)
    await interaction.response.send_message('Snapshot dos canais atualizado.', ephemeral=True)

@security_group.command(name='lockdown', description='Bloqueia ou libera todos os canais de texto')
async def seguranca_lockdown(interaction, ativo: bool, motivo: str='Lockdown de segurança'):
    config = security_config(interaction.guild.id)
    config['lockdown'] = ativo
    for channel in interaction.guild.text_channels:
        try:
            await channel.set_permissions(interaction.guild.default_role, send_messages=False if ativo else None, reason=motivo)
        except discord.HTTPException:
            continue
    save_data()
    await audit_log(interaction.guild, 'seguranca', 'Lockdown alterado', interaction.user, f'Ativo: {ativo}; motivo: {motivo}')
    await interaction.response.send_message('Lockdown ativado.' if ativo else 'Lockdown desativado.', ephemeral=True)

@security_group.command(name='whitelist', description='Adiciona ou remove um membro da whitelist')
async def seguranca_whitelist(interaction, membro: discord.Member, permitido: bool=True):
    config = security_config(interaction.guild.id)
    whitelist = config.setdefault('whitelist', [])
    if permitido and membro.id not in whitelist:
        whitelist.append(membro.id)
    elif not permitido:
        whitelist[:] = [user_id for user_id in whitelist if int(user_id) != membro.id]
    save_data()
    estado = 'adicionado à' if permitido else 'removido da'
    await interaction.response.send_message(f'{membro.mention} foi {estado} whitelist de segurança.', ephemeral=True)

@security_group.command(name='auditoria', description='Mostra as ações recentes do servidor')
@app_commands.checks.has_permissions(view_audit_log=True)
async def seguranca_auditoria(interaction):
    lines = []
    try:
        async for entry in interaction.guild.audit_logs(limit=15):
            action = str(entry.action).split('.')[-1]
            actor = f'{entry.user} (`{entry.user.id}`)'
            target = getattr(entry.target, 'name', None)
            target_text = f' → `{target}`' if target else ''
            lines.append(f'• **{action}** — {actor}{target_text}')
    except discord.Forbidden:
        await interaction.response.send_message('Não tenho permissão para visualizar o registro de auditoria.', ephemeral=True)
        return
    embed = discord.Embed(title='📋 Auditoria recente', description='\n'.join(lines) or 'Nenhuma ação encontrada.', color=discord.Color.blurple())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@security_group.command(name='banlist', description='Mostra os usuários bloqueados pelo anti-raid')
async def seguranca_banlist(interaction):
    config = security_config(interaction.guild.id)
    ids = config.get('banned_actors', [])
    if not ids:
        await interaction.response.send_message('A lista do anti-raid está vazia.', ephemeral=True)
        return
    lines = []
    for user_id in ids[-50:]:
        lines.append(f'• <@{user_id}> (`{user_id}`)')
    embed = discord.Embed(title='🛡️ Banlist do Anti-Raid', description='\n'.join(lines), color=discord.Color.red())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@security_group.command(name='scan', description='Analisa cargos e permissões perigosas')
@app_commands.checks.has_permissions(administrator=True)
async def seguranca_scan(interaction):
    dangerous = []
    permissions = {'administrator': 'Administrador', 'manage_guild': 'Gerenciar servidor', 'manage_roles': 'Gerenciar cargos', 'manage_channels': 'Gerenciar canais', 'ban_members': 'Banir membros', 'kick_members': 'Expulsar membros', 'manage_webhooks': 'Gerenciar webhooks'}
    for role in interaction.guild.roles:
        if role.is_default():
            continue
        found = []
        for permission, label in permissions.items():
            if getattr(role.permissions, permission, False):
                found.append(label)
        if found:
            dangerous.append(f"**{role.name}**\nID: `{role.id}`\nPermissões: {', '.join(found)}")
    description = '\n\n'.join(dangerous[:20])
    if not description:
        description = 'Nenhum cargo com permissões perigosas foi encontrado.'
    embed = discord.Embed(title='🔎 Scan de segurança', description=description, color=discord.Color.orange())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@clock_group.command(name='entrar', description='Registra sua entrada no serviço')
async def ponto_entrar(interaction):
    await create_clock_ticket(interaction)

@clock_group.command(name='sair', description='Registra sua saída e calcula a jornada')
async def ponto_sair(interaction):
    record = guild_clock(interaction.guild.id)
    active = record['active'].pop(str(interaction.user.id), None)
    if not active:
        await interaction.response.send_message('Você não está em serviço.', ephemeral=True)
        return
    seconds = elapsed_clock_seconds(active)
    record['history'].append({'user_id': interaction.user.id, 'started_at': active['started_at'], 'ended_at': datetime.now(timezone.utc).isoformat(), 'seconds': seconds})
    save_data()
    await audit_log(interaction.guild, 'ponto', 'Saída registrada', interaction.user, f'Duração: {seconds // 3600}h {seconds % 3600 // 60}min')
    await interaction.response.send_message(f'Jornada encerrada: **{seconds // 3600}h {seconds % 3600 // 60}min**. O ticket será fechado.', ephemeral=True)
    channel = get_guild_channel(interaction.guild, active.get('channel_id'))
    if channel:
        try:
            await channel.delete(reason=f'Ponto encerrado por {interaction.user}')
        except discord.HTTPException:
            pass

@clock_group.command(name='status', description='Consulta seu status no bate-ponto')
async def ponto_status(interaction):
    active = guild_clock(interaction.guild.id)['active'].get(str(interaction.user.id))
    if not active:
        await interaction.response.send_message('Você está fora de serviço.', ephemeral=True)
        return
    seconds = elapsed_clock_seconds(active)
    state = 'pausado' if active.get('paused') else 'ativo'
    await interaction.response.send_message(f'Você está **{state}** há **{seconds // 3600}h {seconds % 3600 // 60}min**.', ephemeral=True)

@clock_group.command(name='pausar', description='Pausa o ponto de um membro sem registrar saída')
@app_commands.checks.has_permissions(administrator=True)
async def ponto_pausar(interaction, membro: discord.Member):
    if await pause_clock(interaction.guild, membro, interaction.user):
        await interaction.response.send_message(f'Ponto de {membro.mention} pausado. A saída não foi registrada.', ephemeral=True)
    else:
        await interaction.response.send_message('Esse membro não possui um ponto ativo.', ephemeral=True)

@clock_group.command(name='fechar_todos', description='Fecha todos os tickets de ponto do servidor')
@app_commands.checks.has_permissions(administrator=True)
async def ponto_fechar_todos(interaction, confirmar: bool, motivo: str='Fechamento geral dos pontos'):
    if not confirmar:
        await interaction.response.send_message('Operação cancelada. Use `confirmar: True` para fechar todos os pontos.', ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    record = guild_clock(interaction.guild.id)
    closed = 0
    missing = 0
    for user_id, active in list(record['active'].items()):
        channel = get_guild_channel(interaction.guild, active.get('channel_id'))
        seconds = elapsed_clock_seconds(active)
        record['history'].append({'user_id': int(user_id), 'started_at': active['started_at'], 'ended_at': datetime.now(timezone.utc).isoformat(), 'seconds': seconds, 'closed_by_admin': interaction.user.id})
        record['active'].pop(user_id, None)
        if not channel:
            missing += 1
            continue
        try:
            await channel.delete(reason=f'{motivo}: {interaction.user}')
            closed += 1
        except discord.HTTPException:
            continue
    save_data()
    await audit_log(interaction.guild, 'ponto', 'Fechamento geral dos pontos', interaction.user, f'Fechados: {closed}; ausentes: {missing}')
    await interaction.followup.send(f'Pontos encerrados: **{closed}** ticket(s) apagado(s) e **{missing}** registro(s) sem canal.', ephemeral=True)

@clock_group.command(name='historico', description='Mostra seu histórico recente de jornada')
async def ponto_historico(interaction):
    history = [item for item in guild_clock(interaction.guild.id)['history'] if int(item['user_id']) == interaction.user.id][-10:]
    if not history:
        await interaction.response.send_message('Você ainda não possui jornadas encerradas.', ephemeral=True)
        return
    lines = [f"<t:{int(datetime.fromisoformat(item['started_at']).timestamp())}:d> — {item['seconds'] // 3600}h {item['seconds'] % 3600 // 60}min" for item in reversed(history)]
    await interaction.response.send_message('**Suas últimas jornadas**\n' + '\n'.join(lines), ephemeral=True)
bot.tree.add_command(clock_group)
bot.tree.add_command(economy_group)
bot.tree.add_command(giveaway_group)
bot.tree.add_command(security_group)
bot.tree.add_command(internal_logs_group)
bot.tree.add_command(verification_group)
bot.tree.add_command(permissions_group)
bot.tree.add_command(fun_group)
bot.tree.add_command(backup_group)
bot.tree.add_command(ticket_group)

async def setup_hook():
    bot.add_view(ClockView())
    bot.add_view(VerificationView())
    for guild_record in data['timeclock'].values():
        for user_id in guild_record.get('active', {}):
            bot.add_view(ClockControlView(int(user_id)))
    for poll_id, poll in data['polls'].items():
        if poll.get('open'):
            bot.add_view(PollView(poll_id))

async def synchronize_commands():
    """Sincroniza todos os comandos globalmente."""
    try:
        synced = await bot.tree.sync()
        await initialize_ticket_v3()
        print('[TICKET V3] Inicializado com sucesso.')
        print(f'[SLASH] {len(synced)} comandos globais sincronizados.')
    except discord.HTTPException as error:
        print(f'[SLASH] Erro ao sincronizar comandos globais: {type(error).__name__}: {error}')
bot.setup_hook = setup_hook
data = load_data()
data.setdefault('panels', {})
data.setdefault('tickets', {})
data.setdefault('timeclock', {})
data.setdefault('finance', {})
data.setdefault('levels', {})
data.setdefault('polls', {})
data.setdefault('warnings', {})
data.setdefault('starboard', {})
data.setdefault('giveaways', {})
data.setdefault('reputations', {})
data.setdefault('security', {})
data.setdefault('internal_logs', {'channel_id': None, 'guild_id': None})
data.setdefault('verification', {})
data.setdefault('fun', {})
data.setdefault('reminders', {})
data.setdefault('channel_snapshots', {})
data.setdefault('server_events', {})
data.setdefault('guild_settings', {})
data.setdefault('bot_profile', {})
data.setdefault('weekly_xp', {})
data.setdefault('streaks', {})
data.setdefault('economy_inventory', {})
data.setdefault('transfers', [])
data.setdefault('work_cooldowns', {})
data.setdefault('rob_cooldowns', {})
data['bot_profile'].setdefault('bot_status', 'online')
data['bot_profile'].setdefault('bot_activity', None)
data['bot_profile'].setdefault('bot_name', None)
legacy_settings = data.pop('settings', None)
if legacy_settings and (not data['guild_settings']):
    data['bot_profile']['bot_status'] = legacy_settings.get('bot_status', data['bot_profile']['bot_status'])
    data['bot_profile']['bot_activity'] = legacy_settings.get('bot_activity', data['bot_profile']['bot_activity'])
    data['bot_profile']['bot_name'] = legacy_settings.get('bot_name', data['bot_profile']['bot_name'])
    known_guild_ids = {str(record['guild_id']) for record in data['panels'].values() if record.get('guild_id')}
    known_guild_ids.update(data['timeclock'])
    known_guild_ids.update(data['finance'])
    known_guild_ids.update(data['security'])
    known_guild_ids.update(data['channel_snapshots'])
    known_guild_ids.update(data['server_events'])
    if known_guild_ids:
        data['guild_settings'][sorted(known_guild_ids)[0]] = {'max_tickets_per_user': legacy_settings.get('max_tickets_per_user', 1), 'log_channels': legacy_settings.get('log_channels', {}), 'daily_reward': legacy_settings.get('daily_reward', 500), 'timeclock_channel_id': legacy_settings.get('timeclock_channel_id'), 'default_staff_role_id': legacy_settings.get('default_staff_role_id'), 'default_log_channel_id': legacy_settings.get('default_log_channel_id')}
        save_data()
token = os.getenv('DISCORD_TOKEN')
if not token:
    raise RuntimeError('Defina a variável de ambiente DISCORD_TOKEN antes de iniciar o bot.')
bot.run(token)
