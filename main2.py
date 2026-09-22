# ============================================================
# AURA BOT — PARTE 1
# CORE / CONFIGURAÇÃO / DADOS / PERMISSÕES / HELPERS
# ============================================================

import asyncio
import io
import json
import os
import random
import re
import shutil
import sys
import time
import traceback
import zipfile

from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks


# ============================================================
# CONFIGURAÇÃO PRINCIPAL
# ============================================================

AURA_VERSION = "3.0.0"

COMMAND_PREFIX = os.getenv("BOT_PREFIX", "!")

SITE_URL = os.getenv(
    "SITE_URL",
    "https://furiousbot1.netlify.app"
).rstrip("/")

DATA_FILE = Path("aura_data.json")
LEGACY_DATA_FILE = Path("ticket_panels.json")

BACKUP_DIR = Path("backups")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

BOT_START_TIME = datetime.now(timezone.utc)

# Usuário principal / protegido
MASTER_USER_ID = 770039880964505601
IMMUNE_USER_ID = MASTER_USER_ID

# Quantidade máxima de backups automáticos
MAX_BACKUPS = 30


# ============================================================
# INTENTS
# ============================================================

intents = discord.Intents.default()

intents.guilds = True
intents.members = True
intents.message_content = True
intents.presences = False
intents.messages = True
intents.reactions = True


# ============================================================
# BOT
# ============================================================

bot = commands.Bot(
    command_prefix=COMMAND_PREFIX,
    intents=intents,
    help_command=None,
)


# ============================================================
# GRUPOS DE SLASH COMMANDS
# ============================================================

ticket_group = app_commands.Group(
    name="ticket",
    description="Sistema completo de tickets",
)

clock_group = app_commands.Group(
    name="ponto",
    description="Sistema de bate-ponto e jornada",
)

economy_group = app_commands.Group(
    name="economia",
    description="Sistema financeiro do servidor",
)

giveaway_group = app_commands.Group(
    name="sorteio",
    description="Sistema de sorteios da comunidade",
)

security_group = app_commands.Group(
    name="seguranca",
    description="Proteção e segurança do servidor",
)

internal_logs_group = app_commands.Group(
    name="log_interno",
    description="Logs internos do Aura",
)

verification_group = app_commands.Group(
    name="verificacao",
    description="Sistema de verificação",
)

permissions_group = app_commands.Group(
    name="permissoes",
    description="Permissões dos comandos do Aura",
)

fun_group = app_commands.Group(
    name="diversao",
    description="Comandos sociais e divertidos",
)

backup_group = app_commands.Group(
    name="backup",
    description="Sistema de backups",
)

moderation_group = app_commands.Group(
    name="moderacao",
    description="Sistema de moderação",
)

config_group = app_commands.Group(
    name="config",
    description="Configuração do servidor",
)

utility_group = app_commands.Group(
    name="util",
    description="Ferramentas e informações úteis",
)

suggestion_group = app_commands.Group(
    name="sugestao",
    description="Sistema de sugestões",
)

invite_group = app_commands.Group(
    name="invites",
    description="Sistema de convites",
)


# ============================================================
# REGISTRO DOS GRUPOS
# ============================================================

ALL_COMMAND_GROUPS = (
    ticket_group,
    clock_group,
    economy_group,
    giveaway_group,
    security_group,
    internal_logs_group,
    verification_group,
    permissions_group,
    fun_group,
    backup_group,
    moderation_group,
    config_group,
    utility_group,
    suggestion_group,
    invite_group,
)

for group in ALL_COMMAND_GROUPS:
    try:
        bot.tree.add_command(group)
    except discord.app_commands.errors.CommandAlreadyRegistered:
        pass


# ============================================================
# ESTRUTURA PADRÃO DOS DADOS
# ============================================================

DEFAULT_DATA = {
    # Sistema antigo
    "panels": {},
    "tickets": {},

    # Ponto
    "timeclock": {},

    # Economia
    "finance": {},
    "levels": {},

    # Comunidade
    "polls": {},
    "suggestions": {},
    "reputations": {},
    "fun": {},

    # Moderação
    "warnings": {},
    "moderation": {},

    # Segurança
    "security": {},

    # Logs
    "internal_logs": {},
    "logs": {},

    # Verificação
    "verification": {},

    # Eventos
    "server_events": {},

    # Convites
    "invites": {},

    # Sorteios
    "giveaways": {},

    # Configurações
    "guild_settings": {},

    # Backup
    "backups": {},

    # Perfil do bot
    "bot_profile": {},

    # Lembretes
    "reminders": {},

    # Snapshots de canais
    "channel_snapshots": {},

    # Manutenção
    "maintenance": {},

    # Estatísticas
    "statistics": {},
}


# ============================================================
# MESCLAGEM SEGURA DE DEFAULTS
# ============================================================

def merge_defaults(current, defaults):
    """
    Mantém dados antigos e adiciona apenas o que estiver faltando.
    Nunca apaga configurações existentes.
    """

    if not isinstance(current, dict):
        current = {}

    for key, default_value in defaults.items():

        if key not in current:
            if isinstance(default_value, dict):
                current[key] = {}
            elif isinstance(default_value, list):
                current[key] = list(default_value)
            else:
                current[key] = default_value

            continue

        if isinstance(default_value, dict):

            if not isinstance(current[key], dict):
                current[key] = {}

            merge_defaults(
                current[key],
                default_value,
            )

    return current


# ============================================================
# CARREGAMENTO DE DADOS
# ============================================================

def load_data():
    """
    Carrega o banco JSON.
    Tenta preservar dados de versões antigas.
    """

    source = None

    if DATA_FILE.exists():
        source = DATA_FILE

    elif LEGACY_DATA_FILE.exists():
        source = LEGACY_DATA_FILE

    if source is None:
        return merge_defaults({}, DEFAULT_DATA)

    try:

        raw = source.read_text(
            encoding="utf-8"
        )

        loaded = json.loads(raw)

        if not isinstance(loaded, dict):
            loaded = {}

        loaded = merge_defaults(
            loaded,
            DEFAULT_DATA,
        )

        return loaded

    except (
        OSError,
        json.JSONDecodeError,
        UnicodeDecodeError,
    ) as error:

        print(
            f"[NOT DATA] Erro ao carregar dados: {error}"
        )

        # Não destruir o arquivo quebrado.
        try:

            broken = source.with_suffix(
                source.suffix + ".broken"
            )

            shutil.copy2(
                source,
                broken,
            )

        except Exception:
            pass

        return merge_defaults(
            {},
            DEFAULT_DATA,
        )


# Banco global
data = load_data()


# ============================================================
# SALVAMENTO
# ============================================================

_data_save_lock = asyncio.Lock()


def save_data():
    """
    Salva os dados de forma mais segura.

    Primeiro escreve em arquivo temporário,
    depois substitui o arquivo principal.
    """

    global data

    DATA_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_file = DATA_FILE.with_suffix(
        ".tmp"
    )

    try:

        payload = json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        )

        temporary_file.write_text(
            payload,
            encoding="utf-8",
        )

        temporary_file.replace(
            DATA_FILE
        )

    except Exception as error:

        print(
            f"[NOT DATA] Erro ao salvar: {error}"
        )

        try:
            temporary_file.unlink(
                missing_ok=True
            )
        except Exception:
            pass


async def save_data_async():
    """
    Versão assíncrona do salvamento.
    """

    async with _data_save_lock:
        await asyncio.to_thread(
            save_data
        )


# ============================================================
# BACKUP DO BANCO
# ============================================================

def create_data_backup():
    """
    Cria backup do banco principal.
    """

    if not DATA_FILE.exists():
        return None

    BACKUP_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%d-%H%M%S"
    )

    backup_file = (
        BACKUP_DIR /
        f"not-data-{timestamp}.json"
    )

    try:

        shutil.copy2(
            DATA_FILE,
            backup_file,
        )

        backups = sorted(
            BACKUP_DIR.glob(
                "not-data-*.json"
            ),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )

        for old_backup in backups[MAX_BACKUPS:]:
            try:
                old_backup.unlink(
                    missing_ok=True
                )
            except Exception:
                pass

        return backup_file

    except Exception as error:

        print(
            f"[NOT BACKUP] {error}"
        )

        return None


# ============================================================
# INICIALIZAÇÃO DOS DADOS
# ============================================================

def initialize_data():
    global data

    data = merge_defaults(
        data,
        DEFAULT_DATA,
    )

    save_data()


initialize_data()


# ============================================================
# CONFIGURAÇÃO POR SERVIDOR
# ============================================================

GUILD_DEFAULTS = {
    "max_tickets_per_user": 1,

    "log_channels": {},

    "daily_reward": 500,

    "timeclock_channel_id": None,

    "default_staff_role_id": None,

    "default_log_channel_id": None,

    "command_role_id": None,

    "autorole_id": None,

    "suggestion_channel_id": None,

    "starboard_channel_id": None,

    "starboard_threshold": 3,

    "welcome_channel_id": None,

    "goodbye_channel_id": None,

    "welcome_enabled": True,

    "goodbye_enabled": True,

    "automod": {
        "enabled": False,
        "block_links": False,
        "block_invites": True,
        "max_mentions": 5,
        "blocked_words": [],
        "anti_spam": True,
        "spam_messages": 6,
        "spam_window": 8,
    },

    "maintenance": {
        "enabled": False,
        "reason": "",
    },

    "panel": {
        "color": 0x5865F2,
        "title": "Painel .NoTBot",
        "description": "Gerencie seu servidor através do Aura.",
    },
}


def guild_settings(guild_id):
    """
    Retorna as configurações de um servidor.
    """

    guild_id = str(guild_id)

    settings = data[
        "guild_settings"
    ].setdefault(
        guild_id,
        {},
    )

    merge_defaults(
        settings,
        GUILD_DEFAULTS,
    )

    return settings


# ============================================================
# CONFIGURAÇÕES ESPECÍFICAS
# ============================================================

def security_config(guild_id):

    defaults = {
        "enabled": True,
        "channel_delete_limit": 10,
        "window_seconds": 30,
        "ban_actor": True,
        "restore_channels": True,
        "alert_channel_id": None,
        "protected_channel_id": None,
        "whitelist": [],
        "lockdown": False,
        "triggered_until": 0,
        "deletions": [],
    }

    config = data[
        "security"
    ].setdefault(
        str(guild_id),
        {},
    )

    merge_defaults(
        config,
        defaults,
    )

    return config


def verification_config(guild_id):

    defaults = {
        "enabled": False,
        "verified_role_id": None,
        "remove_role_id": None,
        "channel_id": None,
        "message_id": None,
        "button_label": "Verificar",
        "button_emoji": "✅",
        "allowed_bots": [],
    }

    config = data[
        "verification"
    ].setdefault(
        str(guild_id),
        {},
    )

    merge_defaults(
        config,
        defaults,
    )

    return config


def moderation_config(guild_id):

    defaults = {
        "enabled": True,
        "log_channel_id": None,
        "mute_role_id": None,
        "warn_limit": 3,
        "warn_action": "mute",

        "automod": {
            "enabled": False,
            "block_links": False,
            "block_invites": True,
            "max_mentions": 5,
            "blocked_words": [],
            "anti_spam": True,
            "spam_messages": 6,
            "spam_window": 8,
        },
    }

    config = data[
        "moderation"
    ].setdefault(
        str(guild_id),
        {},
    )

    merge_defaults(
        config,
        defaults,
    )

    return config


def event_config(guild_id):

    defaults = {
        "welcome_channel_id": None,
        "leave_channel_id": None,
        "punishment_channel_id": None,
        "invite_channel_id": None,

        "welcome_enabled": True,
        "leave_enabled": True,
        "punishment_enabled": True,
        "invite_enabled": True,
    }

    config = data[
        "server_events"
    ].setdefault(
        str(guild_id),
        {},
    )

    merge_defaults(
        config,
        defaults,
    )

    return config


# ============================================================
# DATA HELPERS
# ============================================================

def guild_clock(guild_id):

    return data[
        "timeclock"
    ].setdefault(
        str(guild_id),
        {
            "active": {},
            "history": [],
        },
    )


def guild_wallets(guild_id):

    return data[
        "finance"
    ].setdefault(
        str(guild_id),
        {},
    )


def wallet(guild_id, user_id):

    return guild_wallets(
        guild_id
    ).setdefault(
        str(user_id),
        {
            "wallet": 0,
            "bank": 0,
            "daily_at": None,
            "inventory": {},
        },
    )


def guild_levels(guild_id):

    return data[
        "levels"
    ].setdefault(
        str(guild_id),
        {},
    )


def level_record(guild_id, user_id):

    return guild_levels(
        guild_id
    ).setdefault(
        str(user_id),
        {
            "xp": 0,
            "points": 0,
            "level": 0,
            "title": "",
            "last_xp_at": 0,
        },
    )


def guild_fun(guild_id):

    return data[
        "fun"
    ].setdefault(
        str(guild_id),
        {
            "marriages": {},
            "relationships": {},
        },
    )


def guild_warnings(guild_id):

    return data[
        "warnings"
    ].setdefault(
        str(guild_id),
        {},
    )


# ============================================================
# ECONOMIA / XP
# ============================================================

def format_money(value):

    try:
        value = int(value)
    except (
        TypeError,
        ValueError,
    ):
        value = 0

    return (
        f"{value:,}"
        .replace(",", ".")
        + " coins"
    )


def level_from_xp(xp):

    xp = max(
        0,
        int(xp),
    )

    return int(
        (xp / 100) ** 0.5
    )


def grant_message_xp(
    guild_id,
    user_id,
    minimum=10,
    maximum=25,
):
    """
    Concede XP sem permitir spam de XP.
    """

    record = level_record(
        guild_id,
        user_id,
    )

    current_time = time.time()

    last_xp = float(
        record.get(
            "last_xp_at",
            0,
        )
    )

    if current_time - last_xp < 60:
        return False, level_from_xp(
            record.get(
                "xp",
                0,
            )
        )

    old_level = level_from_xp(
        record.get(
            "xp",
            0,
        )
    )

    record["xp"] += random.randint(
        minimum,
        maximum,
    )

    record["last_xp_at"] = current_time

    new_level = level_from_xp(
        record["xp"]
    )

    save_data()

    return (
        new_level > old_level,
        new_level,
    )


# ============================================================
# AVISOS
# ============================================================

def add_warning(
    guild_id,
    user_id,
    moderator_id,
    reason,
):

    warnings = guild_warnings(
        guild_id
    ).setdefault(
        str(user_id),
        [],
    )

    warnings.append(
        {
            "moderator_id": int(moderator_id),
            "reason": str(reason)[:500],
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }
    )

    save_data()

    return len(warnings)


# ============================================================
# UTILITÁRIOS
# ============================================================

def now():
    return datetime.now(
        timezone.utc
    )


def now_iso():
    return now().isoformat()


def safe_name(name):
    """
    Nome seguro para canais/tópicos.
    """

    name = str(name)

    name = name.lower()

    name = re.sub(
        r"[^a-z0-9\-_]+",
        "-",
        name,
    )

    name = re.sub(
        r"-+",
        "-",
        name,
    )

    return name.strip("-")[:70] or "usuario"


def get_guild_channel(
    guild,
    channel_id,
):
    if not guild or not channel_id:
        return None

    try:
        return guild.get_channel(
            int(channel_id)
        )
    except (
        TypeError,
        ValueError,
    ):
        return None


def is_immune_user(user):

    user_id = getattr(
        user,
        "id",
        user,
    )

    return user_id == IMMUNE_USER_ID


def is_master(user):

    return getattr(
        user,
        "id",
        user,
    ) == MASTER_USER_ID


def bot_member(guild):

    if not guild:
        return None

    return (
        guild.me
        or (
            guild.get_member(
                bot.user.id
            )
            if bot.user
            else None
        )
    )


# ============================================================
# PERMISSÕES
# ============================================================

PUBLIC_COMMANDS = {
    "ping",
    "verificar",
    "servidor",
    "server",
    "usuario",
    "user",
    "perfil",
    "profile",
    "avatar",
    "banner",
    "icone_servidor",
    "cargo_info",
    "canal_info",
    "roles",
    "ponto",
    "economia",
    "credits",
    "avisos",
    "warnings",
    "sugerir",
    "rep",
    "enquete",
    "lembrete",
    "roll",
    "colors",
    "color",
    "rank",
    "top",
    "title",
    "diversao",
}


def member_has_configured_role(
    interaction,
):

    if not interaction.guild:
        return False

    configured_role_id = guild_settings(
        interaction.guild.id
    ).get(
        "command_role_id"
    )

    if not configured_role_id:
        return False

    try:
        configured_role_id = int(
            configured_role_id
        )
    except (
        TypeError,
        ValueError,
    ):
        return False

    return any(
        role.id == configured_role_id
        for role in getattr(
            interaction.user,
            "roles",
            [],
        )
    )


def can_use_admin_command(
    interaction,
):

    if is_master(
        interaction.user
    ):
        return True

    if not interaction.guild:
        return False

    if interaction.user.guild_permissions.administrator:
        return True

    return member_has_configured_role(
        interaction
    )


def can_use_aura_panel(
    interaction,
):

    if not interaction.guild:
        return False

    if is_master(
        interaction.user
    ):
        return True

    permissions = (
        interaction.user.guild_permissions
    )

    return (
        permissions.administrator
        or permissions.manage_guild
        or permissions.manage_channels
        or member_has_configured_role(
            interaction
        )
    )


# ============================================================
# PROTEÇÃO DO USUÁRIO MASTER
# ============================================================

async def refuse_protected_action(
    interaction,
    member,
    action,
):

    if not is_immune_user(
        member
    ):
        return False

    await interaction.response.send_message(
        "🛡️ Este usuário está protegido "
        "e não pode sofrer essa ação pelo NoTBot.",
        ephemeral=True,
    )

    return True


# ============================================================
# LOGS
# ============================================================

async def audit_log(
    guild,
    category,
    action,
    actor=None,
    details="",
):

    if not guild:
        return

    settings = guild_settings(
        guild.id
    )

    log_channels = settings.get(
        "log_channels",
        {},
    )

    channel_ids = {
        log_channels.get(category),
        log_channels.get("geral"),
        settings.get(
            "default_log_channel_id"
        ),
    }

    channel_ids.discard(None)

    for channel_id in channel_ids:

        channel = get_guild_channel(
            guild,
            channel_id,
        )

        if not channel:
            continue

        embed = discord.Embed(
            title=f"📋 Log • {category}",
            description=str(action)[:4000],
            color=discord.Color.blurple(),
            timestamp=now(),
        )

        if actor:

            embed.add_field(
                name="Responsável",
                value=(
                    f"{actor.mention} "
                    f"(`{actor.id}`)"
                ),
                inline=False,
            )

        if details:

            embed.add_field(
                name="Detalhes",
                value=str(
                    details
                )[:1024],
                inline=False,
            )

        try:

            await channel.send(
                embed=embed
            )

        except (
            discord.Forbidden,
            discord.HTTPException,
        ):
            pass


async def internal_log(
    event,
    message,
    guild=None,
    level="INFO",
):

    config = data.get(
        "internal_logs",
        {},
    )

    channel_id = config.get(
        "channel_id"
    )

    if not channel_id:
        return

    channel = bot.get_channel(
        int(channel_id)
    )

    if not channel:
        return

    color = (
        discord.Color.red()
        if level == "ERROR"
        else discord.Color.blurple()
    )

    embed = discord.Embed(
        title=f"🤖 .NoTBot • {level}",
        description=str(
            message
        )[:4000],
        color=color,
        timestamp=now(),
    )

    embed.add_field(
        name="Evento",
        value=str(
            event
        )[:256],
        inline=False,
    )

    if guild:

        embed.add_field(
            name="Servidor",
            value=(
                f"{guild.name} "
                f"(`{guild.id}`)"
            ),
            inline=False,
        )

    try:

        await channel.send(
            embed=embed
        )

    except (
        discord.Forbidden,
        discord.HTTPException,
    ):
        pass


# ============================================================
# BANNER VISUAL
# ============================================================

def visual_banner(
    title,
    subtitle,
    color="5865F2",
):

    color = str(
        color
    ).replace(
        "#",
        "",
    )[:6]

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="1200" height="280">'
        f'<rect width="1200" height="280" '
        f'fill="#{color}"/>'
        f'<circle cx="1080" cy="80" r="180" '
        f'fill="#ffffff" opacity=".12"/>'
        f'<text x="70" y="125" fill="white" '
        f'font-family="sans-serif" font-size="48" '
        f'font-weight="bold">{title}</text>'
        f'<text x="70" y="180" fill="white" '
        f'opacity=".86" font-family="sans-serif" '
        f'font-size="25">{subtitle}</text>'
        f'</svg>'
    ).encode(
        "utf-8"
    )


# ============================================================
# FORMATAÇÃO DE TEMPO
# ============================================================

def format_duration(seconds):

    try:
        seconds = max(
            0,
            int(seconds),
        )
    except (
        TypeError,
        ValueError,
    ):
        seconds = 0

    days, remainder = divmod(
        seconds,
        86400,
    )

    hours, remainder = divmod(
        remainder,
        3600,
    )

    minutes, seconds = divmod(
        remainder,
        60,
    )

    parts = []

    if days:
        parts.append(
            f"{days}d"
        )

    if hours:
        parts.append(
            f"{hours}h"
        )

    if minutes:
        parts.append(
            f"{minutes}m"
        )

    if seconds or not parts:
        parts.append(
            f"{seconds}s"
        )

    return " ".join(
        parts
    )


# ============================================================
# STATUS DO AURA
# ============================================================

def aura_uptime():

    return int(
        (
            now()
            - BOT_START_TIME
        ).total_seconds()
    )


def aura_status():

    return {
        "version": AURA_VERSION,
        "uptime": aura_uptime(),
        "guilds": len(
            bot.guilds
        ),
        "users": sum(
            guild.member_count or 0
            for guild in bot.guilds
        ),
        "latency": round(
            bot.latency * 1000
        )
        if bot.latency
        else 0,
    }


# ============================================================
# MANUTENÇÃO
# ============================================================

def maintenance_config(
    guild_id,
):

    return data[
        "maintenance"
    ].setdefault(
        str(guild_id),
        {
            "enabled": False,
            "reason": "",
        },
    )


def is_maintenance_enabled(
    guild_id,
):

    return bool(
        maintenance_config(
            guild_id
        ).get(
            "enabled",
            False,
        )
    )


# ============================================================
# SALVAMENTO AUTOMÁTICO
# ============================================================

_data_save_task = None


async def automatic_data_save():

    await bot.wait_until_ready()

    while not bot.is_closed():

        try:

            await save_data_async()

        except Exception as error:

            print(
                f"[AURA AUTO SAVE] {error}"
            )

            try:

                await internal_log(
                    "automatic_save",
                    str(error),
                    level="ERROR",
                )

            except Exception:
                pass

        await asyncio.sleep(
            120
        )


# ============================================================
# CACHE DE CONVITES
# ============================================================

invite_cache = {}


# ============================================================
# CONTROLE DE ERROS DE PERMISSÃO
# ============================================================

async def aura_permission_check(
    interaction,
):

    if not interaction.guild:
        return True

    if is_master(
        interaction.user
    ):
        return True

    command = interaction.command

    if not command:
        return True

    root = (
        command.qualified_name
        .split()[0]
        .lower()
    )

    if root in PUBLIC_COMMANDS:
        return True

    if can_use_admin_command(
        interaction
    ):
        return True

    raise app_commands.CheckFailure(
        "Você não possui permissão "
        "para usar este comando."
    )


# ============================================================
# CHECK GLOBAL
# ============================================================

@bot.tree.interaction_check
async def global_interaction_check(
    interaction,
):

    try:

        command = interaction.command

        if command:

            await internal_log(
                "comando",
                (
                    f"/{command.qualified_name} "
                    f"usado por "
                    f"{interaction.user} "
                    f"(`{interaction.user.id}`)"
                ),
                interaction.guild,
            )

        return await aura_permission_check(
            interaction
        )

    except app_commands.CheckFailure:
        raise

    except Exception as error:

        print(
            f"[AURA CHECK] {error}"
        )

        return True


# ============================================================
# EVENTO DE ERRO GLOBAL
# ============================================================

@bot.tree.error
async def aura_tree_error(
    interaction,
    error,
):

    if isinstance(
        error,
        app_commands.CheckFailure,
    ):

        message = str(error)

        if not message:
            message = (
                "Você não possui "
                "permissão para isso."
            )

        try:

            if interaction.response.is_done():

                await interaction.followup.send(
                    f"❌ {message}",
                    ephemeral=True,
                )

            else:

                await interaction.response.send_message(
                    f"❌ {message}",
                    ephemeral=True,
                )

        except Exception:
            pass

        return

    print(
        "[AURA COMMAND ERROR]",
        repr(error),
    )

    try:

        await internal_log(
            "command_error",
            traceback.format_exc(),
            interaction.guild,
            "ERROR",
        )

    except Exception:
        pass

    try:

        if interaction.response.is_done():

            await interaction.followup.send(
                "❌ Ocorreu um erro ao executar "
                "este comando.",
                ephemeral=True,
            )

        else:

            await interaction.response.send_message(
                "❌ Ocorreu um erro ao executar "
                "este comando.",
                ephemeral=True,
            )

    except Exception:
        pass


# ============================================================
# BACKUP INICIAL
# ============================================================

try:
    create_data_backup()
except Exception as error:
    print(
        f"[AURA BACKUP INICIAL] {error}"
    )


# ============================================================
# FIM DA PARTE 1
# ============================================================

# ============================================================
# AURA BOT — PARTE 2
# PAINEL ADMINISTRATIVO COMPLETO
# ============================================================


# ============================================================
# CONFIGURAÇÃO DAS CATEGORIAS
# ============================================================

PANEL_CATEGORIES = {
    "tickets": {
        "label": "Tickets",
        "emoji": "🎫",
        "description": "Configure e gerencie o sistema de tickets.",
        "color": 0x5865F2,
    },

    "moderacao": {
        "label": "Moderação",
        "emoji": "🛡️",
        "description": "Banimentos, expulsões, avisos, timeout e limpeza.",
        "color": 0xED4245,
    },

    "seguranca": {
        "label": "Segurança",
        "emoji": "🔐",
        "description": "Proteções contra ataques, bots, spam e invasões.",
        "color": 0xFEE75C,
    },

    "economia": {
        "label": "Economia",
        "emoji": "🪙",
        "description": "Configure moedas, recompensas, XP e loja.",
        "color": 0x57F287,
    },

    "niveis": {
        "label": "Níveis",
        "emoji": "⭐",
        "description": "Configure XP, níveis, recompensas e ranking.",
        "color": 0xF1C40F,
    },

    "sorteios": {
        "label": "Sorteios",
        "emoji": "🎉",
        "description": "Gerencie sorteios ativos e configurações.",
        "color": 0xEB459E,
    },

    "boas_vindas": {
        "label": "Boas-vindas",
        "emoji": "👋",
        "description": "Configure entrada, saída e autorole.",
        "color": 0x5865F2,
    },

    "verificacao": {
        "label": "Verificação",
        "emoji": "✅",
        "description": "Configure o sistema de verificação.",
        "color": 0x57F287,
    },

    "logs": {
        "label": "Logs",
        "emoji": "📋",
        "description": "Configure os canais de registros do Aura.",
        "color": 0x5865F2,
    },

    "config": {
        "label": "Configuração",
        "emoji": "⚙️",
        "description": "Configurações gerais do servidor.",
        "color": 0x99AAB5,
    },

    "backup": {
        "label": "Backup",
        "emoji": "💾",
        "description": "Crie e gerencie backups dos dados.",
        "color": 0x7289DA,
    },
}


# ============================================================
# EMBED PRINCIPAL
# ============================================================

def build_main_panel_embed(guild):

    settings = guild_settings(
        guild.id
    )

    panel_config = settings.get(
        "panel",
        {},
    )

    embed = discord.Embed(
        title=panel_config.get(
            "title",
            "⚡ Painel do Aura",
        ),
        description=(
            "Bem-vindo ao painel administrativo "
            "do **Aura**.\n\n"
            "Selecione uma categoria abaixo para "
            "configurar seu servidor.\n\n"
            "⚡ **Aura "
            f"{AURA_VERSION}**"
        ),
        color=panel_config.get(
            "color",
            0x5865F2,
        ),
    )

    if guild.icon:
        embed.set_thumbnail(
            url=guild.icon.url
        )

    embed.add_field(
        name="🏠 Servidor",
        value=(
            f"**{guild.name}**\n"
            f"Membros: `{guild.member_count or 0}`"
        ),
        inline=True,
    )

    embed.add_field(
        name="🤖 Aura",
        value=(
            f"Versão: `{AURA_VERSION}`\n"
            f"Ping: `{round(bot.latency * 1000)}ms`"
        ),
        inline=True,
    )

    embed.set_footer(
        text="Aura • Painel Administrativo"
    )

    return embed


# ============================================================
# EMBED DE CATEGORIA
# ============================================================

def build_category_embed(
    guild,
    category,
):

    config = PANEL_CATEGORIES.get(
        category
    )

    if not config:
        config = {
            "label": "Painel",
            "emoji": "⚙️",
            "description": "Configuração do Aura.",
            "color": 0x5865F2,
        }

    embed = discord.Embed(
        title=(
            f"{config['emoji']} "
            f"{config['label']}"
        ),
        description=config[
            "description"
        ],
        color=config[
            "color"
        ],
    )

    embed.set_footer(
        text=(
            "Aura • "
            "Use os botões abaixo para gerenciar."
        )
    )

    return embed


# ============================================================
# BOTÃO VOLTAR
# ============================================================

class AuraPanelBackButton(
    discord.ui.Button
):

    def __init__(self):

        super().__init__(
            label="Voltar",
            emoji="◀️",
            style=discord.ButtonStyle.secondary,
            row=4,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):

        if not interaction.guild:
            return

        await interaction.response.edit_message(
            embed=build_main_panel_embed(
                interaction.guild
            ),
            view=AuraMainPanelView(),
        )


# ============================================================
# BOTÃO ATUALIZAR
# ============================================================

class AuraPanelRefreshButton(
    discord.ui.Button
):

    def __init__(self):

        super().__init__(
            label="Atualizar",
            emoji="🔄",
            style=discord.ButtonStyle.secondary,
            row=4,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):

        if not interaction.guild:
            return

        await interaction.response.edit_message(
            embed=build_main_panel_embed(
                interaction.guild
            ),
            view=AuraMainPanelView(),
        )


# ============================================================
# SELECT DO PAINEL PRINCIPAL
# ============================================================

class AuraPanelSelect(
    discord.ui.Select
):

    def __init__(self):

        options = []

        for key, config in PANEL_CATEGORIES.items():

            options.append(
                discord.SelectOption(
                    label=config["label"][:100],
                    description=config[
                        "description"
                    ][:100],
                    emoji=config["emoji"],
                    value=key,
                )
            )

        super().__init__(
            placeholder="Selecione uma categoria...",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):

        category = self.values[0]

        await handle_aura_panel_category(
            interaction,
            category,
        )


# ============================================================
# VIEW PRINCIPAL
# ============================================================

class AuraMainPanelView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=600
        )

        self.add_item(
            AuraPanelSelect()
        )

        self.add_item(
            AuraPanelRefreshButton()
        )


# ============================================================
# BOTÃO DE AÇÃO DE CATEGORIA
# ============================================================

class AuraCategoryActionButton(
    discord.ui.Button
):

    def __init__(
        self,
        label,
        emoji,
        action,
        style=discord.ButtonStyle.primary,
        row=None,
    ):

        self.action = action

        super().__init__(
            label=label,
            emoji=emoji,
            style=style,
            row=row,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):

        await handle_aura_visual_action(
            interaction,
            self.action,
        )


# ============================================================
# VIEW GENÉRICA DE CATEGORIA
# ============================================================

class AuraCategoryView(
    discord.ui.View
):

    def __init__(
        self,
        category,
    ):

        super().__init__(
            timeout=600
        )

        self.category = category

        actions = get_panel_actions(
            category
        )

        for action in actions:

            self.add_item(
                AuraCategoryActionButton(
                    label=action["label"],
                    emoji=action["emoji"],
                    action=action["action"],
                    style=action.get(
                        "style",
                        discord.ButtonStyle.primary,
                    ),
                    row=action.get(
                        "row"
                    ),
                )
            )

        self.add_item(
            AuraPanelBackButton()
        )


# ============================================================
# AÇÕES DISPONÍVEIS DO PAINEL
# ============================================================

def get_panel_actions(
    category
):

    actions = {

        "tickets": [
            {
                "label": "Configurar",
                "emoji": "⚙️",
                "action": "ticket_config",
            },
            {
                "label": "Publicar",
                "emoji": "📢",
                "action": "ticket_publish",
            },
            {
                "label": "Ver tickets",
                "emoji": "📂",
                "action": "ticket_list",
            },
        ],

        "moderacao": [
            {
                "label": "Configuração",
                "emoji": "⚙️",
                "action": "moderation_config",
            },
            {
                "label": "Avisos",
                "emoji": "⚠️",
                "action": "moderation_warnings",
            },
            {
                "label": "Limpeza",
                "emoji": "🧹",
                "action": "moderation_cleanup",
            },
        ],

        "seguranca": [
            {
                "label": "Status",
                "emoji": "📊",
                "action": "security_status",
            },
            {
                "label": "Proteções",
                "emoji": "🛡️",
                "action": "security_config",
            },
            {
                "label": "Lockdown",
                "emoji": "🔒",
                "action": "security_lockdown",
            },
        ],

        "economia": [
            {
                "label": "Configuração",
                "emoji": "⚙️",
                "action": "economy_config",
            },
            {
                "label": "Loja",
                "emoji": "🛒",
                "action": "economy_shop",
            },
            {
                "label": "Recompensas",
                "emoji": "🎁",
                "action": "economy_rewards",
            },
        ],

        "niveis": [
            {
                "label": "Configuração",
                "emoji": "⚙️",
                "action": "levels_config",
            },
            {
                "label": "Recompensas",
                "emoji": "🎁",
                "action": "levels_rewards",
            },
            {
                "label": "Ranking",
                "emoji": "🏆",
                "action": "levels_ranking",
            },
        ],

        "sorteios": [
            {
                "label": "Ativos",
                "emoji": "🎉",
                "action": "giveaway_active",
            },
            {
                "label": "Configuração",
                "emoji": "⚙️",
                "action": "giveaway_config",
            },
        ],

        "boas_vindas": [
            {
                "label": "Boas-vindas",
                "emoji": "👋",
                "action": "welcome_config",
            },
            {
                "label": "Saída",
                "emoji": "🚪",
                "action": "goodbye_config",
            },
            {
                "label": "Autorole",
                "emoji": "🎭",
                "action": "autorole_config",
            },
        ],

        "verificacao": [
            {
                "label": "Configuração",
                "emoji": "⚙️",
                "action": "verification_config",
            },
            {
                "label": "Publicar",
                "emoji": "📢",
                "action": "verification_publish",
            },
        ],

        "logs": [
            {
                "label": "Canais",
                "emoji": "📋",
                "action": "logs_channels",
            },
            {
                "label": "Status",
                "emoji": "📊",
                "action": "logs_status",
            },
        ],

        "config": [
            {
                "label": "Servidor",
                "emoji": "🏠",
                "action": "server_config",
            },
            {
                "label": "Permissões",
                "emoji": "🔑",
                "action": "permissions_config",
            },
            {
                "label": "Manutenção",
                "emoji": "🔧",
                "action": "maintenance_config",
            },
        ],

        "backup": [
            {
                "label": "Criar backup",
                "emoji": "💾",
                "action": "backup_create",
            },
            {
                "label": "Ver backups",
                "emoji": "📂",
                "action": "backup_list",
            },
        ],
    }

    return actions.get(
        category,
        [],
    )


# ============================================================
# ABERTURA DE CATEGORIA
# ============================================================

async def handle_aura_panel_category(
    interaction,
    category,
):

    if not interaction.guild:
        await interaction.response.send_message(
            "❌ Este painel só pode ser usado em um servidor.",
            ephemeral=True,
        )
        return

    if not can_use_aura_panel(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão para usar o painel.",
            ephemeral=True,
        )

        return

    if category not in PANEL_CATEGORIES:

        await interaction.response.send_message(
            "❌ Categoria inválida.",
            ephemeral=True,
        )

        return

    # --------------------------------------------------------
    # TICKETS
    # --------------------------------------------------------

    if category == "tickets":

        if "TicketSetupView" in globals():

            try:

                panel = ticket_panel(
                    interaction.guild.id,
                    "default",
                )

                panel = normalize_ticket_panel(
                    panel
                )

                opened = len(
                    [
                        ticket
                        for ticket in ticket_data(
                            interaction.guild.id
                        ).values()
                        if ticket.get(
                            "status"
                        ) == "open"
                    ]
                )

                embed = discord.Embed(
                    title="🎫 Sistema de Tickets",
                    description=(
                        "Configure o sistema de tickets "
                        "**diretamente pelo painel**.\n\n"
                        "Você não precisa utilizar comandos "
                        "para realizar as configurações básicas."
                    ),
                    color=panel.get(
                        "color",
                        0x5865F2,
                    ),
                )

                embed.add_field(
                    name="📊 Tickets abertos",
                    value=f"`{opened}`",
                    inline=True,
                )

                embed.add_field(
                    name="🎨 Cor",
                    value=f"`#{panel.get('color', 0x5865F2):06X}`",
                    inline=True,
                )

                embed.add_field(
                    name="🗂️ Categoria",
                    value=(
                        f"<#{panel['ticket_category_id']}>"
                        if panel.get(
                            "ticket_category_id"
                        )
                        else "Não configurada"
                    ),
                    inline=True,
                )

                embed.set_footer(
                    text="Aura • Sistema de Tickets"
                )

                await interaction.response.edit_message(
                    embed=embed,
                    view=TicketSetupView(
                        interaction.guild.id
                    ),
                )

                return

            except Exception as error:

                print(
                    f"[AURA PANEL TICKET] {error}"
                )

        # Caso a Parte 3 ainda não tenha sido instalada.
        await show_panel_not_ready(
            interaction,
            "tickets",
        )

        return

    # --------------------------------------------------------
    # TODAS AS OUTRAS CATEGORIAS
    # --------------------------------------------------------

    embed = build_category_embed(
        interaction.guild,
        category,
    )

    await interaction.response.edit_message(
        embed=embed,
        view=AuraCategoryView(
            category
        ),
    )


# ============================================================
# PAINEL VISUAL GENÉRICO
# ============================================================

async def show_panel_not_ready(
    interaction,
    category,
):

    config = PANEL_CATEGORIES.get(
        category,
        {},
    )

    embed = discord.Embed(
        title=(
            f"{config.get('emoji', '⚙️')} "
            f"{config.get('label', 'Configuração')}"
        ),
        description=(
            "O módulo desta categoria será carregado "
            "pelas próximas partes do Aura.\n\n"
            "O painel já está preparado para receber "
            "as configurações sem precisar ser recriado."
        ),
        color=config.get(
            "color",
            0x5865F2,
        ),
    )

    await interaction.response.edit_message(
        embed=embed,
        view=AuraCategoryView(
            category
        ),
    )


# ============================================================
# AÇÃO VISUAL
# ============================================================

async def handle_aura_visual_action(
    interaction,
    action,
):

    if not interaction.guild:
        await interaction.response.send_message(
            "❌ Este painel só pode ser usado em um servidor.",
            ephemeral=True,
        )
        return

    if not can_use_aura_panel(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão para isso.",
            ephemeral=True,
        )

        return

    # ========================================================
    # TICKETS
    # ========================================================

    if action.startswith(
        "ticket_"
    ):

        if "handle_ticket_panel_action" in globals():

            try:

                await handle_ticket_panel_action(
                    interaction,
                    action.replace(
                        "ticket_",
                        "",
                    ),
                )

                return

            except Exception as error:

                print(
                    f"[AURA PANEL TICKET ACTION] {error}"
                )

    # ========================================================
    # MODERAÇÃO
    # ========================================================

    if action.startswith(
        "moderation_"
    ):

        await render_visual_configuration(
            interaction,
            "moderacao",
            "🛡️ Moderação",
            moderation_config(
                interaction.guild.id
            ),
        )

        return

    # ========================================================
    # SEGURANÇA
    # ========================================================

    if action in {
        "security_status",
        "security_config",
        "security_lockdown",
    }:

        config = security_config(
            interaction.guild.id
        )

        if action == "security_lockdown":

            config["lockdown"] = not bool(
                config.get(
                    "lockdown",
                    False,
                )
            )

            save_data()

        await render_visual_configuration(
            interaction,
            "seguranca",
            "🔐 Segurança",
            config,
        )

        return

    # ========================================================
    # ECONOMIA
    # ========================================================

    if action.startswith(
        "economy_"
    ):

        config = guild_settings(
            interaction.guild.id
        )

        await render_visual_configuration(
            interaction,
            "economia",
            "🪙 Economia",
            config,
        )

        return

    # ========================================================
    # NÍVEIS
    # ========================================================

    if action.startswith(
        "levels_"
    ):

        config = guild_levels(
            interaction.guild.id
        )

        await render_visual_configuration(
            interaction,
            "niveis",
            "⭐ Níveis",
            config,
        )

        return

    # ========================================================
    # SORTEIOS
    # ========================================================

    if action.startswith(
        "giveaway_"
    ):

        config = data.setdefault(
            "giveaways",
            {},
        ).setdefault(
            str(
                interaction.guild.id
            ),
            {},
        )

        await render_visual_configuration(
            interaction,
            "sorteios",
            "🎉 Sorteios",
            config,
        )

        return

    # ========================================================
    # BOAS-VINDAS
    # ========================================================

    if action in {
        "welcome_config",
        "goodbye_config",
        "autorole_config",
    }:

        config = guild_settings(
            interaction.guild.id
        )

        await render_visual_configuration(
            interaction,
            "boas_vindas",
            "👋 Boas-vindas / Saída / Autorole",
            config,
        )

        return

    # ========================================================
    # VERIFICAÇÃO
    # ========================================================

    if action.startswith(
        "verification_"
    ):

        config = verification_config(
            interaction.guild.id
        )

        await render_visual_configuration(
            interaction,
            "verificacao",
            "✅ Verificação",
            config,
        )

        return

    # ========================================================
    # LOGS
    # ========================================================

    if action.startswith(
        "logs_"
    ):

        config = guild_settings(
            interaction.guild.id
        ).get(
            "log_channels",
            {},
        )

        await render_visual_configuration(
            interaction,
            "logs",
            "📋 Logs",
            config,
        )

        return

    # ========================================================
    # CONFIGURAÇÃO
    # ========================================================

    if action in {
        "server_config",
        "permissions_config",
        "maintenance_config",
    }:

        config = guild_settings(
            interaction.guild.id
        )

        await render_visual_configuration(
            interaction,
            "config",
            "⚙️ Configuração",
            config,
        )

        return

    # ========================================================
    # BACKUP
    # ========================================================

    if action.startswith(
        "backup_"
    ):

        if action == "backup_create":

            backup = create_data_backup()

            if backup:

                description = (
                    "✅ Backup criado com sucesso.\n\n"
                    f"Arquivo: `{backup.name}`"
                )

            else:

                description = (
                    "❌ Não foi possível criar o backup."
                )

            embed = discord.Embed(
                title="💾 Backup",
                description=description,
                color=0x7289DA,
            )

            await interaction.response.edit_message(
                embed=embed,
                view=AuraCategoryView(
                    "backup"
                ),
            )

            return

        if action == "backup_list":

            files = sorted(
                BACKUP_DIR.glob(
                    "*"
                ),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

            if not files:

                description = (
                    "Nenhum backup encontrado."
                )

            else:

                description = "\n".join(
                    f"💾 `{file.name}`"
                    for file in files[:15]
                )

            embed = discord.Embed(
                title="📂 Backups",
                description=description,
                color=0x7289DA,
            )

            await interaction.response.edit_message(
                embed=embed,
                view=AuraCategoryView(
                    "backup"
                ),
            )

            return

    # ========================================================
    # FALLBACK
    # ========================================================

    await render_visual_configuration(
        interaction,
        "config",
        "⚙️ Aura",
        {},
    )


# ============================================================
# RENDERIZADOR VISUAL DE CONFIGURAÇÃO
# ============================================================

async def render_visual_configuration(
    interaction,
    category,
    title,
    config,
):

    if not isinstance(
        config,
        dict,
    ):
        config = {}

    panel = PANEL_CATEGORIES.get(
        category,
        {},
    )

    lines = []

    if not config:

        lines.append(
            "Nenhuma configuração específica "
            "foi definida ainda."
        )

    else:

        for key, value in list(
            config.items()
        )[:18]:

            if isinstance(
                value,
                dict,
            ):

                value = (
                    f"{len(value)} configuração(ões)"
                )

            elif isinstance(
                value,
                list,
            ):

                value = (
                    f"{len(value)} item(ns)"
                )

            elif value is None:

                value = "Não definido"

            elif isinstance(
                value,
                bool,
            ):

                value = (
                    "🟢 Ativado"
                    if value
                    else "🔴 Desativado"
                )

            text = str(
                value
            )

            if len(text) > 180:
                text = text[:177] + "..."

            lines.append(
                f"**{key}** → `{text}`"
            )

    embed = discord.Embed(
        title=title,
        description="\n".join(
            lines
        )[:4000],
        color=panel.get(
            "color",
            0x5865F2,
        ),
    )

    embed.set_footer(
        text=(
            "Aura • "
            "Configuração visual"
        )
    )

    await interaction.response.edit_message(
        embed=embed,
        view=AuraCategoryView(
            category
        ),
    )


# ============================================================
# COMPATIBILIDADE COM O PAINEL ANTIGO
#
# Estas funções existem para que nenhuma parte do painel
# procure uma função inexistente e mostre:
# "visual não foi carregado".
# ============================================================

async def handle_ticket_panel_action(
    interaction,
    action="tickets",
):

    if "TicketSetupView" not in globals():

        await show_panel_not_ready(
            interaction,
            "tickets",
        )

        return

    try:

        await interaction.response.edit_message(
            embed=discord.Embed(
                title="🎫 Sistema de Tickets",
                description=(
                    "O sistema de tickets será "
                    "controlado diretamente pelo "
                    "painel do Aura."
                ),
                color=0x5865F2,
            ),
            view=TicketSetupView(
                interaction.guild.id
            ),
        )

    except discord.InteractionResponded:

        await interaction.followup.edit_message(
            interaction.message.id,
            embed=discord.Embed(
                title="🎫 Sistema de Tickets",
                description=(
                    "O sistema de tickets será "
                    "controlado diretamente pelo "
                    "painel do Aura."
                ),
                color=0x5865F2,
            ),
            view=TicketSetupView(
                interaction.guild.id
            ),
        )


# ============================================================
# COMPATIBILIDADE DE HANDLERS VISUAIS
# ============================================================

async def handle_security_panel_action(
    interaction,
    action="security",
):

    await handle_aura_visual_action(
        interaction,
        "security_config",
    )


async def handle_moderation_panel_action(
    interaction,
    action="moderacao",
):

    await handle_aura_visual_action(
        interaction,
        "moderation_config",
    )


async def handle_economy_panel_action(
    interaction,
    action="economia",
):

    await handle_aura_visual_action(
        interaction,
        "economy_config",
    )


async def handle_levels_panel_action(
    interaction,
    action="niveis",
):

    await handle_aura_visual_action(
        interaction,
        "levels_config",
    )


async def handle_giveaway_panel_action(
    interaction,
    action="sorteios",
):

    await handle_aura_visual_action(
        interaction,
        "giveaway_config",
    )


async def handle_welcome_panel_action(
    interaction,
    action="boas_vindas",
):

    await handle_aura_visual_action(
        interaction,
        "welcome_config",
    )


async def handle_verification_panel_action(
    interaction,
    action="verificacao",
):

    await handle_aura_visual_action(
        interaction,
        "verification_config",
    )


async def handle_logs_panel_action(
    interaction,
    action="logs",
):

    await handle_aura_visual_action(
        interaction,
        "logs_channels",
    )


async def handle_config_panel_action(
    interaction,
    action="config",
):

    await handle_aura_visual_action(
        interaction,
        "server_config",
    )


async def handle_backup_panel_action(
    interaction,
    action="backup",
):

    await handle_aura_visual_action(
        interaction,
        "backup_list",
    )


# ============================================================
# /PAINEL
# ============================================================

@bot.tree.command(
    name="painel",
    description="Abre o painel administrativo completo do Aura.",
)
async def painel(
    interaction: discord.Interaction,
):

    if not interaction.guild:

        await interaction.response.send_message(
            "❌ O painel só pode ser usado dentro de um servidor.",
            ephemeral=True,
        )

        return

    if not can_use_aura_panel(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão para abrir o painel.",
            ephemeral=True,
        )

        return

    await interaction.response.send_message(
        embed=build_main_panel_embed(
            interaction.guild
        ),
        view=AuraMainPanelView(),
        ephemeral=True,
    )


# ============================================================
# /PAINEL STATUS
# ============================================================

@bot.tree.command(
    name="painel_status",
    description="Mostra o status do painel do Aura.",
)
async def painel_status(
    interaction: discord.Interaction,
):

    if not interaction.guild:

        await interaction.response.send_message(
            "❌ Este comando só pode ser usado em um servidor.",
            ephemeral=True,
        )

        return

    if not can_use_aura_panel(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True,
        )

        return

    embed = discord.Embed(
        title="📊 Status do Painel Aura",
        color=0x5865F2,
    )

    embed.add_field(
        name="🎫 Tickets",
        value=(
            "🟢 Preparado"
            if "TicketSetupView" in globals()
            else "🟡 Aguardando Parte 3"
        ),
        inline=True,
    )

    embed.add_field(
        name="🛡️ Moderação",
        value="🟢 Preparado",
        inline=True,
    )

    embed.add_field(
        name="🔐 Segurança",
        value="🟢 Preparado",
        inline=True,
    )

    embed.add_field(
        name="🪙 Economia",
        value="🟢 Preparado",
        inline=True,
    )

    embed.add_field(
        name="⭐ Níveis",
        value="🟢 Preparado",
        inline=True,
    )

    embed.add_field(
        name="🎉 Sorteios",
        value="🟢 Preparado",
        inline=True,
    )

    embed.add_field(
        name="👋 Boas-vindas",
        value="🟢 Preparado",
        inline=True,
    )

    embed.add_field(
        name="✅ Verificação",
        value="🟢 Preparado",
        inline=True,
    )

    embed.add_field(
        name="💾 Backup",
        value="🟢 Preparado",
        inline=True,
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True,
    )


# ============================================================
# FIM DA PARTE 2
# ============================================================

# ============================================================
# AURA BOT — PARTE 3
# SISTEMA COMPLETO DE TICKETS
# ============================================================


# ============================================================
# CONFIGURAÇÕES PADRÃO
# ============================================================

def default_ticket_topic():
    return {
        "id": "suporte",
        "name": "Suporte",
        "description": "Abra um ticket para falar com nossa equipe.",
        "emoji": "🛠️",
        "color": 0x5865F2,
        "button_style": "primary",
        "button_label": "Abrir ticket",

        "staff_role_id": None,
        "allowed_role_ids": [],
        "blocked_role_ids": [],

        "category_id": None,

        "max_open_per_user": 1,

        "opening_message":
            "Olá {user}! Aguarde um membro da equipe.",

        "staff_message":
            "Um novo ticket foi aberto por {user}.",

        "closed_message":
            "Este ticket foi fechado.",

        "ping_staff": True,
        "ping_user": False,

        "create_transcript": True,
        "delete_after_close": False,

        "auto_close_minutes": 0,

        "allow_claim": True,
        "allow_rename": True,
        "allow_add_users": True,
        "allow_remove_users": True,

        "questions": [],

        "log_channel_id": None,

        "welcome_embed": True,
        "show_ticket_info": True,
    }


def default_ticket_panel():
    return {
        "enabled": True,

        "title": "🎫 Central de Atendimento",
        "description": (
            "Selecione uma categoria abaixo "
            "para abrir um ticket."
        ),

        "color": 0x5865F2,

        "channel_id": None,
        "message_id": None,

        "ticket_category_id": None,

        "topics": {
            "suporte": default_ticket_topic(),
        },

        "default_topic": "suporte",

        "button_label": "Abrir ticket",
        "button_emoji": "🎫",

        "staff_role_id": None,

        "max_open_per_user": 1,

        "ping_staff": True,
        "ping_user": False,

        "create_transcript": True,

        "delete_after_close": False,

        "auto_close_minutes": 0,

        "allow_claim": True,
        "allow_rename": True,
        "allow_add_users": True,
        "allow_remove_users": True,

        "log_channel_id": None,

        "welcome_embed": True,
        "show_ticket_info": True,
    }


# ============================================================
# ACESSO AOS DADOS
# ============================================================

def ticket_data(guild_id):

    return data[
        "tickets"
    ].setdefault(
        str(guild_id),
        {},
    )


def ticket_panels_data(guild_id):

    return data[
        "panels"
    ].setdefault(
        str(guild_id),
        {},
    )


def ticket_panel(
    guild_id,
    panel_id="default",
):

    panels = ticket_panels_data(
        guild_id
    )

    panel = panels.setdefault(
        panel_id,
        default_ticket_panel(),
    )

    normalize_ticket_panel(
        panel
    )

    return panel


def ticket_record(
    guild_id,
    channel_id,
):

    return ticket_data(
        guild_id
    ).get(
        str(channel_id)
    )


def save_ticket_data():

    save_data()


# ============================================================
# NORMALIZAÇÃO
# ============================================================

def normalize_ticket_panel(panel):

    merge_defaults(
        panel,
        default_ticket_panel(),
    )

    if not isinstance(
        panel.get("topics"),
        dict,
    ):
        panel["topics"] = {}

    if not panel["topics"]:

        panel["topics"][
            "suporte"
        ] = default_ticket_topic()

    for topic_id, topic in list(
        panel["topics"].items()
    ):

        if not isinstance(
            topic,
            dict,
        ):
            topic = {}

            panel["topics"][
                topic_id
            ] = topic

        merge_defaults(
            topic,
            default_ticket_topic(),
        )

        topic["id"] = topic_id

    return panel


def get_ticket_topic(
    guild_id,
    topic_id=None,
):

    panel = ticket_panel(
        guild_id
    )

    topic_id = (
        topic_id
        or panel.get(
            "default_topic",
            "suporte",
        )
    )

    topics = panel.get(
        "topics",
        {},
    )

    topic = topics.get(
        topic_id
    )

    if topic is None:

        topic = default_ticket_topic()

        topic["id"] = topic_id
        topic["name"] = topic_id.title()

        topics[
            topic_id
        ] = topic

        save_ticket_data()

    return topic


# ============================================================
# PERMISSÕES
# ============================================================

def ticket_is_staff(
    member,
    panel,
    topic=None,
):

    if not isinstance(
        member,
        discord.Member,
    ):
        return False

    if member.guild_permissions.administrator:
        return True

    role_ids = set()

    staff_role = panel.get(
        "staff_role_id"
    )

    if staff_role:
        try:
            role_ids.add(
                int(staff_role)
            )
        except Exception:
            pass

    if topic:
        staff_role = topic.get(
            "staff_role_id"
        )

        if staff_role:
            try:
                role_ids.add(
                    int(staff_role)
                )
            except Exception:
                pass

    return any(
        role.id in role_ids
        for role in member.roles
    )


def ticket_role_allowed(
    member,
    topic,
):

    allowed = topic.get(
        "allowed_role_ids",
        [],
    )

    blocked = topic.get(
        "blocked_role_ids",
        [],
    )

    member_roles = {
        role.id
        for role in member.roles
    }

    try:
        blocked = {
            int(role)
            for role in blocked
        }
    except Exception:
        blocked = set()

    try:
        allowed = {
            int(role)
            for role in allowed
        }
    except Exception:
        allowed = set()

    if blocked & member_roles:
        return False

    if allowed and not (
        allowed & member_roles
    ):
        return False

    return True


def ticket_can_open(
    member,
    panel,
    topic,
):

    if is_immune_user(
        member
    ):
        return True

    if not panel.get(
        "enabled",
        True,
    ):
        return False

    if not ticket_role_allowed(
        member,
        topic,
    ):
        return False

    maximum = topic.get(
        "max_open_per_user"
    )

    if maximum is None:
        maximum = panel.get(
            "max_open_per_user",
            1,
        )

    try:
        maximum = int(
            maximum
        )
    except Exception:
        maximum = 1

    if maximum <= 0:
        return True

    opened = 0

    for ticket in ticket_data(
        member.guild.id
    ).values():

        if (
            ticket.get(
                "status"
            ) != "open"
        ):
            continue

        if (
            ticket.get(
                "user_id"
            ) == member.id
        ):
            opened += 1

    return opened < maximum


# ============================================================
# NOME DO TICKET
# ============================================================

def build_ticket_channel_name(
    member,
    topic,
):

    return (
        f"ticket-"
        f"{safe_name(member.name)}-"
        f"{safe_name(topic.get('id', 'suporte'))}"
    )[:95]


# ============================================================
# EMBED DO TICKET
# ============================================================

def build_ticket_embed(
    member,
    topic,
    ticket_id,
):

    embed = discord.Embed(
        title=(
            f"{topic.get('emoji', '🎫')} "
            f"{topic.get('name', 'Ticket')}"
        ),
        description=(
            topic.get(
                "opening_message",
                "Aguarde a equipe.",
            )
            .replace(
                "{user}",
                member.mention,
            )
        ),
        color=topic.get(
            "color",
            0x5865F2,
        ),
    )

    embed.add_field(
        name="👤 Criado por",
        value=(
            f"{member.mention}\n"
            f"`{member.id}`"
        ),
        inline=True,
    )

    embed.add_field(
        name="🆔 Ticket",
        value=f"`{ticket_id}`",
        inline=True,
    )

    embed.set_footer(
        text="Aura • Sistema de Tickets"
    )

    return embed


# ============================================================
# VIEW DE ABERTURA
# ============================================================

class TicketOpenView(
    discord.ui.View
):

    def __init__(
        self,
        guild_id,
    ):

        super().__init__(
            timeout=None
        )

        self.guild_id = guild_id

        self.add_item(
            TicketGuildTopicSelect(
                guild_id
            )
        )


class TicketGuildTopicSelect(
    discord.ui.Select
):

    def __init__(
        self,
        guild_id,
    ):

        self.guild_id = guild_id

        panel = ticket_panel(
            guild_id
        )

        options = []

        for topic_id, topic in list(
            panel.get(
                "topics",
                {},
            ).items()
        )[:25]:

            options.append(
                discord.SelectOption(
                    label=topic.get(
                        "name",
                        topic_id,
                    )[:100],
                    description=topic.get(
                        "description",
                        "Abrir ticket",
                    )[:100],
                    emoji=topic.get(
                        "emoji",
                        "🎫",
                    ),
                    value=topic_id,
                )
            )

        if not options:

            options.append(
                discord.SelectOption(
                    label="Suporte",
                    description="Abrir ticket de suporte",
                    emoji="🛠️",
                    value="suporte",
                )
            )

        super().__init__(
            placeholder="Escolha o tipo de ticket...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id=(
                f"aura:ticket:select:"
                f"{guild_id}"
            ),
        )

    async def callback(
        self,
        interaction,
    ):

        topic_id = self.values[0]

        await open_ticket_from_topic(
            interaction,
            topic_id,
        )


# ============================================================
# ABRIR TICKET
# ============================================================

async def open_ticket_from_topic(
    interaction,
    topic_id,
):

    if not interaction.guild:

        await interaction.response.send_message(
            "❌ Este sistema só funciona dentro de um servidor.",
            ephemeral=True,
        )

        return

    member = interaction.user

    panel = ticket_panel(
        interaction.guild.id
    )

    topic = get_ticket_topic(
        interaction.guild.id,
        topic_id,
    )

    if not ticket_can_open(
        member,
        panel,
        topic,
    ):

        await interaction.response.send_message(
            "❌ Você não pode abrir outro ticket agora.",
            ephemeral=True,
        )

        return

    await interaction.response.defer(
        ephemeral=True
    )

    channel = await create_ticket_channel(
        interaction.guild,
        member,
        topic,
    )

    if channel is None:

        await interaction.followup.send(
            "❌ Não consegui criar o canal do ticket. "
            "Verifique minhas permissões.",
            ephemeral=True,
        )

        return

    await interaction.followup.send(
        f"✅ Seu ticket foi criado: {channel.mention}",
        ephemeral=True,
    )


# ============================================================
# CRIAÇÃO DO CANAL
# ============================================================

async def create_ticket_channel(
    guild,
    member,
    topic,
):

    panel = ticket_panel(
        guild.id
    )

    category_id = topic.get(
        "category_id"
    )

    if not category_id:
        category_id = panel.get(
            "ticket_category_id"
        )

    category = None

    if category_id:

        try:
            category = guild.get_channel(
                int(category_id)
            )
        except Exception:
            category = None

    bot_user = guild.me

    if bot_user is None:
        return None

    overwrites = {

        guild.default_role:
            discord.PermissionOverwrite(
                view_channel=False
            ),

        member:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
            ),

        bot_user:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_messages=True,
            ),
    }

    staff_role_id = (
        topic.get(
            "staff_role_id"
        )
        or panel.get(
            "staff_role_id"
        )
    )

    if staff_role_id:

        try:

            staff_role = guild.get_role(
                int(staff_role_id)
            )

            if staff_role:

                overwrites[
                    staff_role
                ] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True,
                )

        except Exception:
            pass

    # ========================================================
    # CRIA CANAL
    # ========================================================

    try:

        channel = await guild.create_text_channel(
            name=build_ticket_channel_name(
                member,
                topic,
            ),
            category=(
                category
                if isinstance(
                    category,
                    discord.CategoryChannel,
                )
                else None
            ),
            overwrites=overwrites,
            reason=(
                f"Ticket aberto por "
                f"{member} ({member.id})"
            ),
        )

    except Exception as error:

        print(
            f"[AURA TICKET CREATE] {error}"
        )

        return None

    # ========================================================
    # ID DO TICKET
    # ========================================================

    ticket_id = str(
        channel.id
    )

    record = {

        "id": ticket_id,

        "channel_id": channel.id,

        "guild_id": guild.id,

        "user_id": member.id,

        "topic_id": topic.get(
            "id",
            "suporte",
        ),

        "status": "open",

        "created_at": now_iso(),

        "closed_at": None,

        "claimed_by": None,

        "last_activity": time.time(),

        "transcript": None,
    }

    ticket_data(
        guild.id
    )[ticket_id] = record

    save_ticket_data()

    # ========================================================
    # MENSAGEM
    # ========================================================

    embed = build_ticket_embed(
        member,
        topic,
        ticket_id,
    )

    content_parts = []

    if topic.get(
        "ping_user",
        False,
    ):
        content_parts.append(
            member.mention
        )

    if topic.get(
        "ping_staff",
        True,
    ):

        if staff_role_id:

            try:

                role = guild.get_role(
                    int(staff_role_id)
                )

                if role:
                    content_parts.append(
                        role.mention
                    )

            except Exception:
                pass

    content = (
        " ".join(
            content_parts
        )
        if content_parts
        else None
    )

    try:

        await channel.send(
            content=content,
            embed=embed,
            view=TicketControlView(
                ticket_id
            ),
        )

    except Exception as error:

        print(
            f"[AURA TICKET MESSAGE] {error}"
        )

    # ========================================================
    # MENSAGEM DA EQUIPE
    # ========================================================

    staff_message = topic.get(
        "staff_message"
    )

    if staff_message:

        try:

            await channel.send(
                staff_message.replace(
                    "{user}",
                    member.mention,
                )
            )

        except Exception:
            pass

    await audit_log(
        guild,
        "tickets",
        "Ticket aberto",
        member,
        f"Canal: {channel.mention}",
    )

    return channel


# ============================================================
# ATIVIDADE
# ============================================================

async def update_ticket_activity(
    message,
):

    if not message.guild:
        return

    if not isinstance(
        message.channel,
        discord.TextChannel,
    ):
        return

    record = ticket_record(
        message.guild.id,
        message.channel.id,
    )

    if not record:
        return

    if record.get(
        "status"
    ) != "open":
        return

    record[
        "last_activity"
    ] = time.time()

    # Não salva a cada mensagem.
    # Apenas mantém na memória.
    # O auto-save cuidará do restante.


# ============================================================
# VIEW DE CONTROLE
# ============================================================

class TicketControlView(
    discord.ui.View
):

    def __init__(
        self,
        ticket_id,
    ):

        super().__init__(
            timeout=None
        )

        self.ticket_id = str(
            ticket_id
        )

        self.add_item(
            TicketClaimButton(
                self.ticket_id
            )
        )

        self.add_item(
            TicketRenameButton(
                self.ticket_id
            )
        )

        self.add_item(
            TicketCloseButton(
                self.ticket_id
            )
        )

        self.add_item(
            TicketInfoButton(
                self.ticket_id
            )
        )


class TicketClaimButton(
    discord.ui.Button
):

    def __init__(
        self,
        ticket_id,
    ):

        self.ticket_id = ticket_id

        super().__init__(
            label="Assumir",
            emoji="🙋",
            style=discord.ButtonStyle.primary,
            custom_id=(
                f"aura:ticket:claim:"
                f"{ticket_id}"
            ),
        )

    async def callback(
        self,
        interaction,
    ):

        await ticket_action(
            interaction,
            self.ticket_id,
            "claim",
        )


class TicketRenameButton(
    discord.ui.Button
):

    def __init__(
        self,
        ticket_id,
    ):

        self.ticket_id = ticket_id

        super().__init__(
            label="Renomear",
            emoji="✏️",
            style=discord.ButtonStyle.secondary,
            custom_id=(
                f"aura:ticket:rename:"
                f"{ticket_id}"
            ),
        )

    async def callback(
        self,
        interaction,
    ):

        await interaction.response.send_modal(
            TicketRenameModal(
                self.ticket_id
            )
        )


class TicketCloseButton(
    discord.ui.Button
):

    def __init__(
        self,
        ticket_id,
    ):

        self.ticket_id = ticket_id

        super().__init__(
            label="Fechar",
            emoji="🔒",
            style=discord.ButtonStyle.danger,
            custom_id=(
                f"aura:ticket:close:"
                f"{ticket_id}"
            ),
        )

    async def callback(
        self,
        interaction,
    ):

        await ticket_action(
            interaction,
            self.ticket_id,
            "close",
        )


class TicketInfoButton(
    discord.ui.Button
):

    def __init__(
        self,
        ticket_id,
    ):

        self.ticket_id = ticket_id

        super().__init__(
            label="Informações",
            emoji="ℹ️",
            style=discord.ButtonStyle.secondary,
            custom_id=(
                f"aura:ticket:info:"
                f"{ticket_id}"
            ),
        )

    async def callback(
        self,
        interaction,
    ):

        await ticket_info(
            interaction,
            self.ticket_id,
        )


# ============================================================
# MODAL RENOMEAR
# ============================================================

class TicketRenameModal(
    discord.ui.Modal,
    title="Renomear ticket",
):

    new_name = discord.ui.TextInput(
        label="Novo nome",
        placeholder="Ex: ticket-suporte",
        min_length=2,
        max_length=90,
        required=True,
    )

    def __init__(
        self,
        ticket_id,
    ):

        super().__init__()

        self.ticket_id = ticket_id

    async def on_submit(
        self,
        interaction,
    ):

        record = ticket_record(
            interaction.guild.id,
            self.ticket_id,
        )

        if not record:

            await interaction.response.send_message(
                "❌ Ticket não encontrado.",
                ephemeral=True,
            )

            return

        panel = ticket_panel(
            interaction.guild.id
        )

        topic = get_ticket_topic(
            interaction.guild.id,
            record.get(
                "topic_id"
            ),
        )

        if not ticket_is_staff(
            interaction.user,
            panel,
            topic,
        ):

            await interaction.response.send_message(
                "❌ Você não faz parte da equipe do ticket.",
                ephemeral=True,
            )

            return

        new_name = safe_name(
            self.new_name.value
        )

        try:

            await interaction.channel.edit(
                name=new_name,
                reason=(
                    f"Ticket renomeado por "
                    f"{interaction.user}"
                ),
            )

            await interaction.response.send_message(
                f"✅ Ticket renomeado para `{new_name}`.",
                ephemeral=True,
            )

        except Exception as error:

            await interaction.response.send_message(
                f"❌ Erro: `{error}`",
                ephemeral=True,
            )


# ============================================================
# AÇÕES
# ============================================================

async def ticket_action(
    interaction,
    ticket_id,
    action,
):

    if not interaction.guild:
        return

    record = ticket_record(
        interaction.guild.id,
        ticket_id,
    )

    if not record:

        await interaction.response.send_message(
            "❌ Este ticket não existe mais.",
            ephemeral=True,
        )

        return

    panel = ticket_panel(
        interaction.guild.id
    )

    topic = get_ticket_topic(
        interaction.guild.id,
        record.get(
            "topic_id"
        ),
    )

    is_staff = ticket_is_staff(
        interaction.user,
        panel,
        topic,
    )

    # ========================================================
    # ASSUMIR
    # ========================================================

    if action == "claim":

        if not topic.get(
            "allow_claim",
            True,
        ):

            await interaction.response.send_message(
                "❌ A função de assumir tickets está desativada.",
                ephemeral=True,
            )

            return

        if not is_staff:

            await interaction.response.send_message(
                "❌ Apenas a equipe pode assumir tickets.",
                ephemeral=True,
            )

            return

        record[
            "claimed_by"
        ] = interaction.user.id

        save_ticket_data()

        await interaction.response.send_message(
            f"🙋 {interaction.user.mention} assumiu este ticket."
        )

        return

    # ========================================================
    # FECHAR
    # ========================================================

    if action == "close":

        if not is_staff and (
            interaction.user.id
            != record.get(
                "user_id"
            )
        ):

            await interaction.response.send_message(
                "❌ Apenas o autor ou a equipe pode fechar este ticket.",
                ephemeral=True,
            )

            return

        await interaction.response.send_message(
            "🔒 Fechando o ticket..."
        )

        await close_ticket(
            interaction.guild,
            record,
            interaction.user,
        )

        return


# ============================================================
# FECHAR TICKET
# ============================================================

async def close_ticket(
    guild,
    record,
    closed_by,
):

    if record.get(
        "status"
    ) == "closed":
        return

    channel_id = record.get(
        "channel_id"
    )

    channel = guild.get_channel(
        int(channel_id)
    )

    record[
        "status"
    ] = "closed"

    record[
        "closed_at"
    ] = now_iso()

    record[
        "closed_by"
    ] = closed_by.id

    save_ticket_data()

    panel = ticket_panel(
        guild.id
    )

    topic = get_ticket_topic(
        guild.id,
        record.get(
            "topic_id"
        ),
    )

    # ========================================================
    # TRANSCRIPT
    # ========================================================

    transcript = None

    if topic.get(
        "create_transcript",
        True,
    ):

        transcript = await create_ticket_transcript(
            channel
        )

        if transcript:

            record[
                "transcript"
            ] = transcript

            save_ticket_data()

    # ========================================================
    # MENSAGEM DE FECHAMENTO
    # ========================================================

    if channel:

        try:

            embed = discord.Embed(
                title="🔒 Ticket fechado",
                description=(
                    topic.get(
                        "closed_message",
                        "Este ticket foi fechado.",
                    )
                    .replace(
                        "{user}",
                        closed_by.mention,
                    )
                ),
                color=0xED4245,
            )

            embed.add_field(
                name="👤 Fechado por",
                value=closed_by.mention,
                inline=True,
            )

            await channel.send(
                embed=embed
            )

        except Exception:
            pass

    await audit_log(
        guild,
        "tickets",
        "Ticket fechado",
        closed_by,
        f"Ticket: `{record.get('id')}`",
    )

    # ========================================================
    # DELETAR
    # ========================================================

    if topic.get(
        "delete_after_close",
        False,
    ):

        if channel:

            try:

                await asyncio.sleep(
                    5
                )

                await channel.delete(
                    reason="Ticket fechado"
                )

            except Exception as error:

                print(
                    f"[AURA TICKET DELETE] {error}"
                )

    elif channel:

        try:

            await channel.edit(
                name=(
                    f"closed-{channel.name}"
                )[:95]
            )

        except Exception:
            pass


# ============================================================
# TRANSCRIPT
# ============================================================

async def create_ticket_transcript(
    channel,
):

    if not channel:
        return None

    lines = []

    try:

        async for message in channel.history(
            limit=None,
            oldest_first=True,
        ):

            timestamp = (
                message.created_at
                .strftime(
                    "%d/%m/%Y %H:%M:%S"
                )
            )

            content = (
                message.content
                or "[sem texto]"
            )

            lines.append(
                f"[{timestamp}] "
                f"{message.author} "
                f"({message.author.id}): "
                f"{content}"
            )

    except Exception as error:

        print(
            f"[AURA TRANSCRIPT] {error}"
        )

        return None

    transcript_dir = (
        BACKUP_DIR /
        "transcripts"
    )

    transcript_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    filename = (
        f"ticket-{channel.id}-"
        f"{int(time.time())}.txt"
    )

    path = (
        transcript_dir /
        filename
    )

    try:

        path.write_text(
            "\n".join(lines),
            encoding="utf-8",
        )

        return str(
            path
        )

    except Exception as error:

        print(
            f"[AURA TRANSCRIPT SAVE] {error}"
        )

        return None


# ============================================================
# INFORMAÇÕES
# ============================================================

async def ticket_info(
    interaction,
    ticket_id,
):

    if not interaction.guild:
        return

    record = ticket_record(
        interaction.guild.id,
        ticket_id,
    )

    if not record:

        await interaction.response.send_message(
            "❌ Ticket não encontrado.",
            ephemeral=True,
        )

        return

    embed = discord.Embed(
        title="🎫 Informações do Ticket",
        color=0x5865F2,
    )

    embed.add_field(
        name="🆔 ID",
        value=f"`{record.get('id')}`",
        inline=True,
    )

    embed.add_field(
        name="👤 Criador",
        value=f"<@{record.get('user_id')}>",
        inline=True,
    )

    embed.add_field(
        name="📌 Status",
        value=record.get(
            "status",
            "unknown",
        ),
        inline=True,
    )

    embed.add_field(
        name="📂 Categoria",
        value=record.get(
            "topic_id",
            "suporte",
        ),
        inline=True,
    )

    embed.add_field(
        name="🙋 Responsável",
        value=(
            f"<@{record['claimed_by']}>"
            if record.get(
                "claimed_by"
            )
            else "Ninguém"
        ),
        inline=True,
    )

    embed.add_field(
        name="📅 Criado",
        value=record.get(
            "created_at",
            "Desconhecido",
        ),
        inline=False,
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True,
    )


# ============================================================
# REABRIR
# ============================================================

async def reopen_ticket(
    interaction,
    ticket_id,
):

    if not interaction.guild:
        return

    record = ticket_record(
        interaction.guild.id,
        ticket_id,
    )

    if not record:

        await interaction.response.send_message(
            "❌ Ticket não encontrado.",
            ephemeral=True,
        )

        return

    panel = ticket_panel(
        interaction.guild.id
    )

    topic = get_ticket_topic(
        interaction.guild.id,
        record.get(
            "topic_id"
        ),
    )

    if not ticket_is_staff(
        interaction.user,
        panel,
        topic,
    ):

        await interaction.response.send_message(
            "❌ Apenas a equipe pode reabrir tickets.",
            ephemeral=True,
        )

        return

    record[
        "status"
    ] = "open"

    record[
        "closed_at"
    ] = None

    save_ticket_data()

    channel = interaction.guild.get_channel(
        int(
            record.get(
                "channel_id"
            )
        )
    )

    if channel:

        try:

            await channel.edit(
                name=channel.name.replace(
                    "closed-",
                    "",
                    1,
                )
            )

        except Exception:
            pass

    await interaction.response.send_message(
        "🔓 Ticket reaberto.",
        ephemeral=True,
    )


# ============================================================
# DELETE TICKET
# ============================================================

async def delete_ticket(
    interaction,
    ticket_id,
):

    if not interaction.guild:
        return

    record = ticket_record(
        interaction.guild.id,
        ticket_id,
    )

    if not record:

        await interaction.response.send_message(
            "❌ Ticket não encontrado.",
            ephemeral=True,
        )

        return

    panel = ticket_panel(
        interaction.guild.id
    )

    topic = get_ticket_topic(
        interaction.guild.id,
        record.get(
            "topic_id"
        ),
    )

    if not ticket_is_staff(
        interaction.user,
        panel,
        topic,
    ):

        await interaction.response.send_message(
            "❌ Apenas a equipe pode excluir tickets.",
            ephemeral=True,
        )

        return

    channel = interaction.guild.get_channel(
        int(
            record.get(
                "channel_id"
            )
        )
    )

    if channel:

        await interaction.response.send_message(
            "🗑️ Excluindo ticket..."
        )

        try:

            await channel.delete(
                reason=(
                    f"Ticket excluído por "
                    f"{interaction.user}"
                )
            )

        except Exception as error:

            await interaction.followup.send(
                f"❌ Não consegui excluir: `{error}`",
                ephemeral=True,
            )

            return

    record[
        "status"
    ] = "deleted"

    record[
        "deleted_at"
    ] = now_iso()

    save_ticket_data()


# ============================================================
# /TICKET PAINEL
# ============================================================

@ticket_group.command(
    name="painel",
    description="Abre a configuração do sistema de tickets.",
)
async def ticket_painel(
    interaction,
):

    if not interaction.guild:

        await interaction.response.send_message(
            "❌ Use este comando em um servidor.",
            ephemeral=True,
        )

        return

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True,
        )

        return

    panel = ticket_panel(
        interaction.guild.id
    )

    embed = discord.Embed(
        title="🎫 Configuração de Tickets",
        description=(
            "Configure o sistema de tickets "
            "por esta interface."
        ),
        color=panel.get(
            "color",
            0x5865F2,
        ),
    )

    embed.add_field(
        name="📂 Categorias",
        value=str(
            len(
                panel.get(
                    "topics",
                    {},
                )
            )
        ),
        inline=True,
    )

    embed.add_field(
        name="📊 Status",
        value=(
            "🟢 Ativo"
            if panel.get(
                "enabled",
                True,
            )
            else "🔴 Desativado"
        ),
        inline=True,
    )

    await interaction.response.send_message(
        embed=embed,
        view=TicketSetupView(
            interaction.guild.id
        ),
        ephemeral=True,
    )


# ============================================================
# VIEW DE CONFIGURAÇÃO
# ============================================================

class TicketSetupView(
    discord.ui.View
):

    def __init__(
        self,
        guild_id,
    ):

        super().__init__(
            timeout=600
        )

        self.guild_id = guild_id

        self.add_item(
            TicketToggleButton(
                guild_id
            )
        )

        self.add_item(
            TicketPublishButton(
                guild_id
            )
        )

        self.add_item(
            TicketTopicsButton(
                guild_id
            )
        )

        self.add_item(
            TicketCategoryButton(
                guild_id
            )
        )

        self.add_item(
            TicketBackToAuraButton()
        )


class TicketToggleButton(
    discord.ui.Button
):

    def __init__(
        self,
        guild_id,
    ):

        self.guild_id = guild_id

        panel = ticket_panel(
            guild_id
        )

        enabled = panel.get(
            "enabled",
            True,
        )

        super().__init__(
            label=(
                "Desativar"
                if enabled
                else "Ativar"
            ),
            emoji=(
                "🔴"
                if enabled
                else "🟢"
            ),
            style=(
                discord.ButtonStyle.danger
                if enabled
                else discord.ButtonStyle.success
            ),
            row=0,
        )

    async def callback(
        self,
        interaction,
    ):

        panel = ticket_panel(
            self.guild_id
        )

        panel["enabled"] = not panel.get(
            "enabled",
            True,
        )

        save_ticket_data()

        await interaction.response.edit_message(
            embed=discord.Embed(
                title="🎫 Tickets",
                description=(
                    "Sistema "
                    + (
                        "🟢 ativado."
                        if panel["enabled"]
                        else "🔴 desativado."
                    )
                ),
                color=panel.get(
                    "color",
                    0x5865F2,
                ),
            ),
            view=TicketSetupView(
                self.guild_id
            ),
        )


class TicketPublishButton(
    discord.ui.Button
):

    def __init__(
        self,
        guild_id,
    ):

        self.guild_id = guild_id

        super().__init__(
            label="Publicar painel",
            emoji="📢",
            style=discord.ButtonStyle.primary,
            row=0,
        )

    async def callback(
        self,
        interaction,
    ):

        await publish_ticket_panel(
            interaction,
            self.guild_id,
        )


class TicketTopicsButton(
    discord.ui.Button
):

    def __init__(
        self,
        guild_id,
    ):

        self.guild_id = guild_id

        super().__init__(
            label="Categorias",
            emoji="🗂️",
            style=discord.ButtonStyle.secondary,
            row=1,
        )

    async def callback(
        self,
        interaction,
    ):

        panel = ticket_panel(
            self.guild_id
        )

        topics = panel.get(
            "topics",
            {},
        )

        description = "\n".join(
            (
                f"{topic.get('emoji', '🎫')} "
                f"**{topic.get('name', topic_id)}** "
                f"`{topic_id}`"
            )
            for topic_id, topic
            in list(
                topics.items()
            )[:20]
        )

        if not description:
            description = (
                "Nenhuma categoria configurada."
            )

        embed = discord.Embed(
            title="🗂️ Categorias de Tickets",
            description=description,
            color=0x5865F2,
        )

        await interaction.response.edit_message(
            embed=embed,
            view=TicketSetupView(
                self.guild_id
            ),
        )


class TicketCategoryButton(
    discord.ui.Button
):

    def __init__(
        self,
        guild_id,
    ):

        self.guild_id = guild_id

        super().__init__(
            label="Categoria do Discord",
            emoji="📁",
            style=discord.ButtonStyle.secondary,
            row=1,
        )

    async def callback(
        self,
        interaction,
    ):

        await interaction.response.send_message(
            "Use `/ticket categoria` para definir "
            "a categoria onde os tickets serão criados.",
            ephemeral=True,
        )


class TicketBackToAuraButton(
    discord.ui.Button
):

    def __init__(self):

        super().__init__(
            label="Voltar ao painel",
            emoji="◀️",
            style=discord.ButtonStyle.secondary,
            row=4,
        )

    async def callback(
        self,
        interaction,
    ):

        await interaction.response.edit_message(
            embed=build_main_panel_embed(
                interaction.guild
            ),
            view=AuraMainPanelView(),
        )


# ============================================================
# PUBLICAR PAINEL DE TICKETS
# ============================================================

async def publish_ticket_panel(
    interaction,
    guild_id,
):

    panel = ticket_panel(
        guild_id
    )

    if not panel.get(
        "enabled",
        True,
    ):

        await interaction.response.send_message(
            "❌ O sistema de tickets está desativado.",
            ephemeral=True,
        )

        return

    embed = discord.Embed(
        title=panel.get(
            "title",
            "🎫 Central de Atendimento",
        ),
        description=panel.get(
            "description",
            "Selecione uma categoria.",
        ),
        color=panel.get(
            "color",
            0x5865F2,
        ),
    )

    embed.set_footer(
        text="Aura • Tickets"
    )

    await interaction.response.send_message(
        "📢 Escolha o canal onde deseja publicar o painel.",
        ephemeral=True,
    )

    # O painel será publicado pelo comando
    # /ticket publicar, que possui canal explícito.


# ============================================================
# /TICKET PUBLICAR
# ============================================================

@ticket_group.command(
    name="publicar",
    description="Publica o painel de tickets em um canal.",
)
@app_commands.describe(
    canal="Canal onde o painel será publicado."
)
async def ticket_publicar(
    interaction,
    canal: discord.TextChannel,
):

    if not interaction.guild:

        await interaction.response.send_message(
            "❌ Use em um servidor.",
            ephemeral=True,
        )

        return

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True,
        )

        return

    panel = ticket_panel(
        interaction.guild.id
    )

    embed = discord.Embed(
        title=panel.get(
            "title",
            "🎫 Central de Atendimento",
        ),
        description=panel.get(
            "description",
            "Selecione uma categoria.",
        ),
        color=panel.get(
            "color",
            0x5865F2,
        ),
    )

    embed.set_footer(
        text="Aura • Sistema de Tickets"
    )

    try:

        message = await canal.send(
            embed=embed,
            view=TicketOpenView(
                interaction.guild.id
            ),
        )

        panel[
            "channel_id"
        ] = canal.id

        panel[
            "message_id"
        ] = message.id

        save_ticket_data()

        await interaction.response.send_message(
            f"✅ Painel publicado em {canal.mention}.",
            ephemeral=True,
        )

    except Exception as error:

        await interaction.response.send_message(
            f"❌ Não consegui publicar: `{error}`",
            ephemeral=True,
        )


# ============================================================
# /TICKET LISTAR
# ============================================================

@ticket_group.command(
    name="listar",
    description="Lista os tickets do servidor.",
)
async def ticket_listar(
    interaction,
):

    if not interaction.guild:

        await interaction.response.send_message(
            "❌ Use em um servidor.",
            ephemeral=True,
        )

        return

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True,
        )

        return

    tickets = ticket_data(
        interaction.guild.id
    )

    opened = [
        ticket
        for ticket in tickets.values()
        if ticket.get(
            "status"
        ) == "open"
    ]

    if not opened:

        await interaction.response.send_message(
            "📂 Nenhum ticket aberto.",
            ephemeral=True,
        )

        return

    lines = []

    for ticket in opened[:25]:

        channel = interaction.guild.get_channel(
            int(
                ticket.get(
                    "channel_id"
                )
            )
        )

        channel_text = (
            channel.mention
            if channel
            else f"`{ticket.get('channel_id')}`"
        )

        lines.append(
            f"🎫 {channel_text} • "
            f"<@{ticket.get('user_id')}> • "
            f"`{ticket.get('topic_id')}`"
        )

    embed = discord.Embed(
        title="📂 Tickets abertos",
        description="\n".join(
            lines
        ),
        color=0x5865F2,
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True,
    )


# ============================================================
# /TICKET EXCLUIR
# ============================================================

@ticket_group.command(
    name="excluir",
    description="Exclui o ticket atual.",
)
async def ticket_excluir(
    interaction,
):

    if not interaction.guild:

        await interaction.response.send_message(
            "❌ Use em um servidor.",
            ephemeral=True,
        )

        return

    record = ticket_record(
        interaction.guild.id,
        interaction.channel.id,
    )

    if not record:

        await interaction.response.send_message(
            "❌ Este canal não é um ticket.",
            ephemeral=True,
        )

        return

    await delete_ticket(
        interaction,
        record["id"],
    )


# ============================================================
# /TICKET INFO
# ============================================================

@ticket_group.command(
    name="info",
    description="Mostra informações do ticket atual.",
)
async def ticket_info_command(
    interaction,
):

    if not interaction.guild:
        return

    record = ticket_record(
        interaction.guild.id,
        interaction.channel.id,
    )

    if not record:

        await interaction.response.send_message(
            "❌ Este canal não é um ticket.",
            ephemeral=True,
        )

        return

    await ticket_info(
        interaction,
        record["id"],
    )


# ============================================================
# /TICKET REABRIR
# ============================================================

@ticket_group.command(
    name="reabrir",
    description="Reabre um ticket fechado.",
)
@app_commands.describe(
    ticket_id="ID do ticket."
)
async def ticket_reabrir(
    interaction,
    ticket_id: str,
):

    await reopen_ticket(
        interaction,
        ticket_id,
    )


# ============================================================
# /TICKET ADD-TOPICO
# ============================================================

@ticket_group.command(
    name="add-topico",
    description="Adiciona uma categoria de ticket.",
)
@app_commands.describe(
    nome="Nome da categoria.",
    identificador="Identificador sem espaços.",
    emoji="Emoji da categoria.",
)
async def ticket_add_topico(
    interaction,
    nome: str,
    identificador: str,
    emoji: str = "🎫",
):

    if not interaction.guild:
        return

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True,
        )

        return

    identifier = safe_name(
        identificador
    ).replace(
        "-",
        "_",
    )

    panel = ticket_panel(
        interaction.guild.id
    )

    topic = default_ticket_topic()

    topic["id"] = identifier
    topic["name"] = nome[:100]
    topic["emoji"] = emoji[:10]

    panel[
        "topics"
    ][identifier] = topic

    save_ticket_data()

    await interaction.response.send_message(
        f"✅ Categoria `{identifier}` adicionada.",
        ephemeral=True,
    )


# ============================================================
# /TICKET REMOVER-TOPICO
# ============================================================

@ticket_group.command(
    name="remover-topico",
    description="Remove uma categoria de ticket.",
)
@app_commands.describe(
    identificador="Identificador da categoria."
)
async def ticket_remover_topico(
    interaction,
    identificador: str,
):

    if not interaction.guild:
        return

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True,
        )

        return

    panel = ticket_panel(
        interaction.guild.id
    )

    if identificador not in panel.get(
        "topics",
        {},
    ):

        await interaction.response.send_message(
            "❌ Categoria não encontrada.",
            ephemeral=True,
        )

        return

    if len(
        panel["topics"]
    ) <= 1:

        await interaction.response.send_message(
            "❌ É necessário manter pelo menos uma categoria.",
            ephemeral=True,
        )

        return

    del panel[
        "topics"
    ][identificador]

    if panel.get(
        "default_topic"
    ) == identificador:

        panel[
            "default_topic"
        ] = next(
            iter(
                panel["topics"]
            )
        )

    save_ticket_data()

    await interaction.response.send_message(
        "✅ Categoria removida.",
        ephemeral=True,
    )


# ============================================================
# /TICKET CATEGORIA
# ============================================================

@ticket_group.command(
    name="categoria",
    description="Define a categoria do Discord para os tickets.",
)
@app_commands.describe(
    categoria="Categoria onde os tickets serão criados."
)
async def ticket_categoria(
    interaction,
    categoria: discord.CategoryChannel,
):

    if not interaction.guild:
        return

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True,
        )

        return

    panel = ticket_panel(
        interaction.guild.id
    )

    panel[
        "ticket_category_id"
    ] = categoria.id

    save_ticket_data()

    await interaction.response.send_message(
        f"✅ Tickets serão criados em {categoria.mention}.",
        ephemeral=True,
    )


# ============================================================
# /TICKET STAFF
# ============================================================

@ticket_group.command(
    name="staff",
    description="Define o cargo da equipe de tickets.",
)
@app_commands.describe(
    cargo="Cargo da equipe."
)
async def ticket_staff(
    interaction,
    cargo: discord.Role,
):

    if not interaction.guild:
        return

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True,
        )

        return

    panel = ticket_panel(
        interaction.guild.id
    )

    panel[
        "staff_role_id"
    ] = cargo.id

    save_ticket_data()

    await interaction.response.send_message(
        f"✅ Cargo de staff definido: {cargo.mention}.",
        ephemeral=True,
    )


# ============================================================
# /TICKET LIMITE
# ============================================================

@ticket_group.command(
    name="limite",
    description="Define quantos tickets cada usuário pode ter.",
)
@app_commands.describe(
    quantidade="Quantidade máxima."
)
async def ticket_limite(
    interaction,
    quantidade: app_commands.Range[int, 0, 20],
):

    if not interaction.guild:
        return

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True,
        )

        return

    panel = ticket_panel(
        interaction.guild.id
    )

    panel[
        "max_open_per_user"
    ] = quantidade

    save_ticket_data()

    await interaction.response.send_message(
        f"✅ Limite definido para `{quantidade}` ticket(s).",
        ephemeral=True,
    )


# ============================================================
# /TICKET AUTO-CLOSE
# ============================================================

@ticket_group.command(
    name="auto-close",
    description="Define o fechamento automático por inatividade.",
)
@app_commands.describe(
    minutos="Minutos de inatividade. 0 desativa."
)
async def ticket_auto_close(
    interaction,
    minutos: app_commands.Range[int, 0, 10080],
):

    if not interaction.guild:
        return

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True,
        )

        return

    panel = ticket_panel(
        interaction.guild.id
    )

    panel[
        "auto_close_minutes"
    ] = minutos

    save_ticket_data()

    await interaction.response.send_message(
        (
            "🔴 Auto-close desativado."
            if minutos == 0
            else f"🟢 Auto-close definido para `{minutos}` minutos."
        ),
        ephemeral=True,
    )


# ============================================================
# /TICKET PREVIEW
# ============================================================

@ticket_group.command(
    name="preview",
    description="Visualiza o painel de tickets.",
)
async def ticket_preview(
    interaction,
):

    if not interaction.guild:
        return

    panel = ticket_panel(
        interaction.guild.id
    )

    embed = discord.Embed(
        title=panel.get(
            "title",
            "🎫 Central de Atendimento",
        ),
        description=panel.get(
            "description",
            "Selecione uma categoria.",
        ),
        color=panel.get(
            "color",
            0x5865F2,
        ),
    )

    embed.set_footer(
        text="Prévia • Aura Tickets"
    )

    await interaction.response.send_message(
        embed=embed,
        view=TicketOpenView(
            interaction.guild.id
        ),
        ephemeral=True,
    )


# ============================================================
# AUTO-CLOSE
# ============================================================

@tasks.loop(minutes=1)
async def ticket_auto_close_task():

    current_time = time.time()

    for guild_id, tickets in list(
        data.get(
            "tickets",
            {},
        ).items()
    ):

        try:
            guild = bot.get_guild(
                int(guild_id)
            )
        except Exception:
            continue

        if not guild:
            continue

        panel = ticket_panel(
            guild.id
        )

        default_minutes = panel.get(
            "auto_close_minutes",
            0,
        )

        for record in list(
            tickets.values()
        ):

            if record.get(
                "status"
            ) != "open":
                continue

            topic = get_ticket_topic(
                guild.id,
                record.get(
                    "topic_id"
                ),
            )

            minutes = topic.get(
                "auto_close_minutes",
                default_minutes,
            )

            try:
                minutes = int(
                    minutes
                )
            except Exception:
                minutes = 0

            if minutes <= 0:
                continue

            last_activity = float(
                record.get(
                    "last_activity",
                    time.time(),
                )
            )

            if (
                current_time
                - last_activity
                < minutes * 60
            ):
                continue

            channel = guild.get_channel(
                int(
                    record.get(
                        "channel_id"
                    )
                )
            )

            if channel:

                try:

                    await channel.send(
                        "🔒 Este ticket foi fechado "
                        "automaticamente por inatividade."
                    )

                except Exception:
                    pass

            await close_ticket(
                guild,
                record,
                bot.user,
            )


# ============================================================
# INICIALIZAÇÃO DOS TICKETS
# ============================================================

def register_ticket_persistent_views():

    for guild in bot.guilds:

        try:

            bot.add_view(
                TicketOpenView(
                    guild.id
                )
            )

        except Exception as error:

            print(
                f"[AURA TICKET VIEW] {error}"
            )

    print(
        "[AURA TICKETS] Views registradas."
    )


async def initialize_ticket_system():

    # Garante estrutura para todos os servidores.
    for guild in bot.guilds:

        ticket_panel(
            guild.id
        )

        ticket_data(
            guild.id
        )

    save_ticket_data()

    try:

        if not ticket_auto_close_task.is_running():

            ticket_auto_close_task.start()

    except RuntimeError:
        pass

    register_ticket_persistent_views()


# ============================================================
# INTEGRAÇÃO COM O PAINEL PRINCIPAL
# ============================================================

async def open_ticket_panel_from_main_panel(
    interaction,
):

    if not interaction.guild:

        await interaction.response.send_message(
            "❌ Este painel só pode ser usado em um servidor.",
            ephemeral=True,
        )

        return

    if not can_use_aura_panel(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True,
        )

        return

    panel = ticket_panel(
        interaction.guild.id
    )

    opened = len(
        [
            ticket
            for ticket in ticket_data(
                interaction.guild.id
            ).values()
            if ticket.get(
                "status"
            ) == "open"
        ]
    )

    embed = discord.Embed(
        title="🎫 Sistema de Tickets",
        description=(
            "Configure o sistema de tickets "
            "**diretamente por este painel**.\n\n"
            "Os comandos `/ticket` continuam disponíveis."
        ),
        color=panel.get(
            "color",
            0x5865F2,
        ),
    )

    embed.add_field(
        name="📊 Tickets abertos",
        value=f"`{opened}`",
        inline=True,
    )

    embed.add_field(
        name="🗂️ Categorias",
        value=f"`{len(panel.get('topics', {}))}`",
        inline=True,
    )

    embed.add_field(
        name="📌 Status",
        value=(
            "🟢 Ativo"
            if panel.get(
                "enabled",
                True,
            )
            else "🔴 Desativado"
        ),
        inline=True,
    )

    await interaction.response.edit_message(
        embed=embed,
        view=TicketSetupView(
            interaction.guild.id
        ),
    )


# ============================================================
# ATUALIZA O HANDLER DO PAINEL
# ============================================================

# O handler criado na Parte 2 é substituído aqui,
# pois agora o sistema real de tickets existe.

async def handle_ticket_panel_action(
    interaction,
    action="tickets",
):

    await open_ticket_panel_from_main_panel(
        interaction
    )


# ============================================================
# FINAL DA PARTE 3
# ============================================================

# ============================================================
# AURA BOT — PARTE 4
# MODERAÇÃO • SEGURANÇA • AUTOMOD • LOGS
# ============================================================


# ============================================================
# CONFIGURAÇÕES PADRÃO
# ============================================================

MODERATION_DEFAULTS = {
    "enabled": True,

    "log_channel_id": None,

    "mute_role_id": None,

    "warn_limit": 3,

    "warn_action": "mute",

    "delete_command_messages": False,

    "automod": {
        "enabled": False,

        "block_links": False,

        "block_invites": True,

        "max_mentions": 5,

        "blocked_words": [],

        "anti_spam": True,

        "spam_messages": 6,

        "spam_window": 8,

        "anti_mass_mention": True,

        "ignore_staff": True,

        "ignore_bots": True,
    },

    "protection": {
        "anti_bot": False,

        "anti_webhook": False,

        "anti_mass_join": False,

        "max_joins": 8,

        "join_window": 20,

        "lockdown": False,
    },

    "ignored_channels": [],

    "ignored_roles": [],
}


# ============================================================
# ACESSO À CONFIGURAÇÃO
# ============================================================

def moderation_config(guild_id):

    configs = data.setdefault(
        "guild_settings",
        {}
    )

    guild_data = configs.setdefault(
        str(guild_id),
        {}
    )

    moderation = guild_data.setdefault(
        "moderation",
        {}
    )

    merge_defaults(
        moderation,
        MODERATION_DEFAULTS
    )

    if not isinstance(
        moderation.get("automod"),
        dict
    ):
        moderation["automod"] = {}

    if not isinstance(
        moderation.get("protection"),
        dict
    ):
        moderation["protection"] = {}

    merge_defaults(
        moderation["automod"],
        MODERATION_DEFAULTS["automod"]
    )

    merge_defaults(
        moderation["protection"],
        MODERATION_DEFAULTS["protection"]
    )

    return moderation


# ============================================================
# PERMISSÃO ADMINISTRATIVA
# ============================================================

def can_use_admin_command(
    interaction
):

    if not interaction.guild:
        return False

    if interaction.user.id == MASTER_USER_ID:
        return True

    permissions = interaction.user.guild_permissions

    return (
        permissions.administrator
        or permissions.manage_guild
        or permissions.manage_channels
    )


def can_use_moderation(
    interaction
):

    if not interaction.guild:
        return False

    if interaction.user.id == MASTER_USER_ID:
        return True

    permissions = interaction.user.guild_permissions

    return (
        permissions.administrator
        or permissions.moderate_members
        or permissions.kick_members
        or permissions.ban_members
    )


# ============================================================
# PROTEÇÃO CONTRA O PRÓPRIO BOT / MASTER
# ============================================================

def protected_from_moderation(
    member
):

    if not member:
        return True

    if member.id == MASTER_USER_ID:
        return True

    if bot.user and member.id == bot.user.id:
        return True

    return False


async def moderation_protection_error(
    interaction
):

    await interaction.response.send_message(
        "🛡️ Este usuário está protegido contra moderação.",
        ephemeral=True
    )


def can_moderate_member(
    moderator,
    target
):

    if not moderator or not target:
        return False

    if protected_from_moderation(
        target
    ):
        return False

    if moderator.id == target.id:
        return False

    if moderator.id == MASTER_USER_ID:
        return True

    if target.id == MASTER_USER_ID:
        return False

    try:

        if (
            moderator.top_role
            <= target.top_role
        ):
            return False

    except Exception:
        pass

    return True


# ============================================================
# LOG DE MODERAÇÃO
# ============================================================

async def moderation_log_channel(
    guild
):

    config = moderation_config(
        guild.id
    )

    channel_id = config.get(
        "log_channel_id"
    )

    if not channel_id:
        return None

    try:

        return guild.get_channel(
            int(channel_id)
        )

    except Exception:
        return None


async def send_moderation_log(
    guild,
    title,
    description,
    moderator=None,
    target=None,
    color=0xED4245
):

    channel = await moderation_log_channel(
        guild
    )

    if not channel:
        return

    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(
            timezone.utc
        )
    )

    if moderator:

        embed.add_field(
            name="👮 Moderador",
            value=(
                f"{moderator.mention}\n"
                f"`{moderator.id}`"
            ),
            inline=True
        )

    if target:

        embed.add_field(
            name="👤 Alvo",
            value=(
                f"{target.mention}\n"
                f"`{target.id}`"
            ),
            inline=True
        )

    try:

        await channel.send(
            embed=embed
        )

    except Exception as error:

        print(
            f"[AURA MOD LOG] {error}"
        )


async def log_moderation_action(
    guild,
    action,
    moderator,
    target,
    reason=None
):

    description = (
        f"**Ação:** `{action}`\n"
        f"**Motivo:** "
        f"{reason or 'Não informado'}"
    )

    await send_moderation_log(
        guild,
        f"🛡️ Moderação • {action}",
        description,
        moderator=moderator,
        target=target
    )

    try:

        await audit_log(
            guild,
            "moderation",
            action,
            moderator,
            (
                f"Alvo: {target} "
                f"({target.id}) | "
                f"Motivo: {reason or 'N/A'}"
            )
        )

    except Exception:
        pass


# ============================================================
# WARNINGS
# ============================================================

def guild_warnings(
    guild_id
):

    warnings = data.setdefault(
        "warnings",
        {}
    )

    return warnings.setdefault(
        str(guild_id),
        {}
    )


def get_member_warnings(
    guild_id,
    user_id
):

    return guild_warnings(
        guild_id
    ).setdefault(
        str(user_id),
        []
    )


def add_warning(
    guild_id,
    user_id,
    moderator_id,
    reason
):

    warnings = guild_warnings(
        guild_id
    )

    user_warnings = warnings.setdefault(
        str(user_id),
        []
    )

    warning = {
        "id": int(time.time() * 1000),

        "moderator_id": moderator_id,

        "reason": reason or "Sem motivo",

        "created_at": now_iso()
    }

    user_warnings.append(
        warning
    )

    save_data()

    return warning


def remove_warning(
    guild_id,
    user_id,
    warning_id
):

    warnings = guild_warnings(
        guild_id
    )

    user_warnings = warnings.get(
        str(user_id),
        []
    )

    for index, warning in enumerate(
        user_warnings
    ):

        if str(
            warning.get("id")
        ) == str(warning_id):

            removed = user_warnings.pop(
                index
            )

            save_data()

            return removed

    return None


# ============================================================
# TIMEOUT
# ============================================================

async def timeout_member(
    member,
    duration,
    reason=None
):

    duration = max(
        1,
        min(
            int(duration),
            40320
        )
    )

    until = datetime.now(
        timezone.utc
    ) + timedelta(
        minutes=duration
    )

    await member.timeout(
        until,
        reason=reason
    )


# ============================================================
# BAN
# ============================================================

@moderation_group.command(
    name="ban",
    description="Bane um membro do servidor."
)
@app_commands.describe(
    membro="Membro que será banido.",
    motivo="Motivo do banimento.",
    apagar_mensagens="Quantidade de dias de mensagens para apagar."
)
async def moderation_ban(
    interaction,
    membro: discord.Member,
    motivo: str = "Não informado",
    apagar_mensagens: app_commands.Range[
        int, 0, 7
    ] = 0
):

    if not can_use_moderation(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão para banir membros.",
            ephemeral=True
        )

        return

    if not can_moderate_member(
        interaction.user,
        membro
    ):

        await moderation_protection_error(
            interaction
        )

        return

    try:

        await membro.ban(
            reason=motivo,
            delete_message_days=apagar_mensagens
        )

        await interaction.response.send_message(
            f"🔨 {membro} foi banido."
        )

        await log_moderation_action(
            interaction.guild,
            "Ban",
            interaction.user,
            membro,
            motivo
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ Não tenho permissão para banir esse membro.",
            ephemeral=True
        )


# ============================================================
# KICK
# ============================================================

@moderation_group.command(
    name="kick",
    description="Expulsa um membro do servidor."
)
@app_commands.describe(
    membro="Membro que será expulso.",
    motivo="Motivo da expulsão."
)
async def moderation_kick(
    interaction,
    membro: discord.Member,
    motivo: str = "Não informado"
):

    if not can_use_moderation(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    if not can_moderate_member(
        interaction.user,
        membro
    ):

        await moderation_protection_error(
            interaction
        )

        return

    try:

        await membro.kick(
            reason=motivo
        )

        await interaction.response.send_message(
            f"👢 {membro} foi expulso."
        )

        await log_moderation_action(
            interaction.guild,
            "Kick",
            interaction.user,
            membro,
            motivo
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ Não tenho permissão para expulsar esse membro.",
            ephemeral=True
        )


# ============================================================
# TIMEOUT
# ============================================================

@moderation_group.command(
    name="timeout",
    description="Coloca um membro em timeout."
)
@app_commands.describe(
    membro="Membro que receberá o timeout.",
    minutos="Duração em minutos.",
    motivo="Motivo."
)
async def moderation_timeout(
    interaction,
    membro: discord.Member,
    minutos: app_commands.Range[
        int, 1, 40320
    ],
    motivo: str = "Não informado"
):

    if not can_use_moderation(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    if not can_moderate_member(
        interaction.user,
        membro
    ):

        await moderation_protection_error(
            interaction
        )

        return

    try:

        await timeout_member(
            membro,
            minutos,
            motivo
        )

        await interaction.response.send_message(
            f"⏱️ {membro.mention} recebeu timeout por `{minutos}` minutos."
        )

        await log_moderation_action(
            interaction.guild,
            "Timeout",
            interaction.user,
            membro,
            motivo
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ Não tenho permissão para aplicar timeout.",
            ephemeral=True
        )


# ============================================================
# UNTIMEOUT
# ============================================================

@moderation_group.command(
    name="untimeout",
    description="Remove o timeout de um membro."
)
@app_commands.describe(
    membro="Membro.",
    motivo="Motivo."
)
async def moderation_untimeout(
    interaction,
    membro: discord.Member,
    motivo: str = "Não informado"
):

    if not can_use_moderation(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    if not can_moderate_member(
        interaction.user,
        membro
    ):

        await moderation_protection_error(
            interaction
        )

        return

    try:

        await membro.timeout(
            None,
            reason=motivo
        )

        await interaction.response.send_message(
            f"✅ Timeout removido de {membro.mention}."
        )

        await log_moderation_action(
            interaction.guild,
            "UnTimeout",
            interaction.user,
            membro,
            motivo
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ Não tenho permissão.",
            ephemeral=True
        )


# ============================================================
# WARN
# ============================================================

@moderation_group.command(
    name="warn",
    description="Adverte um membro."
)
@app_commands.describe(
    membro="Membro.",
    motivo="Motivo da advertência."
)
async def moderation_warn(
    interaction,
    membro: discord.Member,
    motivo: str = "Não informado"
):

    if not can_use_moderation(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    if not can_moderate_member(
        interaction.user,
        membro
    ):

        await moderation_protection_error(
            interaction
        )

        return

    warning = add_warning(
        interaction.guild.id,
        membro.id,
        interaction.user.id,
        motivo
    )

    total = len(
        get_member_warnings(
            interaction.guild.id,
            membro.id
        )
    )

    config = moderation_config(
        interaction.guild.id
    )

    limit = int(
        config.get(
            "warn_limit",
            3
        )
    )

    await interaction.response.send_message(
        (
            f"⚠️ {membro.mention} recebeu uma advertência.\n"
            f"Advertências: `{total}/{limit}`"
        )
    )

    await log_moderation_action(
        interaction.guild,
        "Warn",
        interaction.user,
        membro,
        motivo
    )

    if total >= limit:

        action = config.get(
            "warn_action",
            "mute"
        )

        try:

            if action == "kick":

                await membro.kick(
                    reason=(
                        f"Limite de advertências "
                        f"atingido: {total}"
                    )
                )

            elif action == "ban":

                await membro.ban(
                    reason=(
                        f"Limite de advertências "
                        f"atingido: {total}"
                    )
                )

            else:

                await timeout_member(
                    membro,
                    60,
                    "Limite de advertências atingido"
                )

        except Exception as error:

            print(
                f"[AURA WARN ACTION] {error}"
            )


# ============================================================
# WARNINGS
# ============================================================

@moderation_group.command(
    name="warnings",
    description="Mostra as advertências de um membro."
)
@app_commands.describe(
    membro="Membro."
)
async def moderation_warnings(
    interaction,
    membro: discord.Member
):

    warnings = get_member_warnings(
        interaction.guild.id,
        membro.id
    )

    if not warnings:

        await interaction.response.send_message(
            f"✅ {membro.mention} não possui advertências.",
            ephemeral=True
        )

        return

    lines = []

    for warning in warnings[-15:]:

        moderator_id = warning.get(
            "moderator_id"
        )

        lines.append(
            f"⚠️ `{warning.get('id')}` • "
            f"{warning.get('reason')}\n"
            f"👮 <@{moderator_id}> • "
            f"{warning.get('created_at')}"
        )

    embed = discord.Embed(
        title=f"⚠️ Advertências • {membro}",
        description="\n\n".join(
            lines
        ),
        color=0xFEE75C
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ============================================================
# WARN REMOVE
# ============================================================

@moderation_group.command(
    name="warn-remove",
    description="Remove uma advertência."
)
@app_commands.describe(
    membro="Membro.",
    id="ID da advertência."
)
async def moderation_warn_remove(
    interaction,
    membro: discord.Member,
    id: str
):

    if not can_use_moderation(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    removed = remove_warning(
        interaction.guild.id,
        membro.id,
        id
    )

    if not removed:

        await interaction.response.send_message(
            "❌ Advertência não encontrada.",
            ephemeral=True
        )

        return

    await interaction.response.send_message(
        f"✅ Advertência `{id}` removida de {membro.mention}."
    )

    await send_moderation_log(
        interaction.guild,
        "🗑️ Advertência removida",
        (
            f"Advertência `{id}` removida.\n"
            f"Motivo original: "
            f"{removed.get('reason')}"
        ),
        moderator=interaction.user,
        target=membro,
        color=0x57F287
    )


# ============================================================
# LIMPAR MENSAGENS
# ============================================================

@moderation_group.command(
    name="limpar",
    description="Apaga mensagens de um canal."
)
@app_commands.describe(
    quantidade="Quantidade de mensagens."
)
async def moderation_clear(
    interaction,
    quantidade: app_commands.Range[
        int, 1, 100
    ]
):

    if not interaction.guild:
        return

    if not (
        interaction.user.guild_permissions.manage_messages
        or interaction.user.id == MASTER_USER_ID
    ):

        await interaction.response.send_message(
            "❌ Você precisa de `Gerenciar Mensagens`.",
            ephemeral=True
        )

        return

    if not isinstance(
        interaction.channel,
        discord.TextChannel
    ):

        await interaction.response.send_message(
            "❌ Este comando só funciona em canais de texto.",
            ephemeral=True
        )

        return

    await interaction.response.defer(
        ephemeral=True
    )

    try:

        deleted = await interaction.channel.purge(
            limit=quantidade
        )

        await interaction.followup.send(
            f"🧹 `{len(deleted)}` mensagens apagadas.",
            ephemeral=True
        )

        await send_moderation_log(
            interaction.guild,
            "🧹 Mensagens apagadas",
            f"Quantidade: `{len(deleted)}`",
            moderator=interaction.user,
            color=0x5865F2
        )

    except discord.Forbidden:

        await interaction.followup.send(
            "❌ Não tenho permissão para apagar mensagens.",
            ephemeral=True
        )


# ============================================================
# LOCK
# ============================================================

@moderation_group.command(
    name="lock",
    description="Bloqueia mensagens de membros em um canal."
)
async def moderation_lock(
    interaction
):

    if not can_use_moderation(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    channel = interaction.channel

    if not isinstance(
        channel,
        discord.TextChannel
    ):

        await interaction.response.send_message(
            "❌ Canal inválido.",
            ephemeral=True
        )

        return

    try:

        overwrite = channel.overwrites_for(
            interaction.guild.default_role
        )

        overwrite.send_messages = False

        await channel.set_permissions(
            interaction.guild.default_role,
            overwrite=overwrite,
            reason=(
                f"Lock por {interaction.user}"
            )
        )

        await interaction.response.send_message(
            "🔒 Canal bloqueado."
        )

        await send_moderation_log(
            interaction.guild,
            "🔒 Canal bloqueado",
            f"Canal: {channel.mention}",
            moderator=interaction.user
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ Não tenho permissão.",
            ephemeral=True
        )


# ============================================================
# UNLOCK
# ============================================================

@moderation_group.command(
    name="unlock",
    description="Desbloqueia mensagens de membros."
)
async def moderation_unlock(
    interaction
):

    if not can_use_moderation(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    channel = interaction.channel

    if not isinstance(
        channel,
        discord.TextChannel
    ):

        await interaction.response.send_message(
            "❌ Canal inválido.",
            ephemeral=True
        )

        return

    try:

        overwrite = channel.overwrites_for(
            interaction.guild.default_role
        )

        overwrite.send_messages = None

        await channel.set_permissions(
            interaction.guild.default_role,
            overwrite=overwrite,
            reason=(
                f"Unlock por {interaction.user}"
            )
        )

        await interaction.response.send_message(
            "🔓 Canal desbloqueado."
        )

        await send_moderation_log(
            interaction.guild,
            "🔓 Canal desbloqueado",
            f"Canal: {channel.mention}",
            moderator=interaction.user,
            color=0x57F287
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ Não tenho permissão.",
            ephemeral=True
        )


# ============================================================
# CONFIGURAÇÃO DO LOG
# ============================================================

@config_group.command(
    name="log",
    description="Define o canal de logs de moderação."
)
@app_commands.describe(
    canal="Canal de logs."
)
async def config_log(
    interaction,
    canal: discord.TextChannel
):

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    config = moderation_config(
        interaction.guild.id
    )

    config[
        "log_channel_id"
    ] = canal.id

    save_data()

    await interaction.response.send_message(
        f"✅ Canal de logs definido para {canal.mention}."
    )


# ============================================================
# AUTOMOD — ESTADO
# ============================================================

def automod_config(
    guild_id
):

    return moderation_config(
        guild_id
    ).setdefault(
        "automod",
        {}
    )


# ============================================================
# DETECÇÃO DE LINKS
# ============================================================

LINK_REGEX = re.compile(
    r"(https?://|www\.)\S+",
    re.IGNORECASE
)

DISCORD_INVITE_REGEX = re.compile(
    r"(discord\.gg/|discord\.com/invite/)\S+",
    re.IGNORECASE
)


def contains_link(
    content
):

    return bool(
        LINK_REGEX.search(
            content or ""
        )
    )


def contains_discord_invite(
    content
):

    return bool(
        DISCORD_INVITE_REGEX.search(
            content or ""
        )
    )


# ============================================================
# SPAM
# ============================================================

AUTOMOD_MESSAGE_CACHE = {}


def get_spam_cache(
    guild_id,
    user_id
):

    guild_cache = AUTOMOD_MESSAGE_CACHE.setdefault(
        guild_id,
        {}
    )

    return guild_cache.setdefault(
        user_id,
        []
    )


def register_spam_message(
    guild_id,
    user_id,
    window
):

    current = time.time()

    cache = get_spam_cache(
        guild_id,
        user_id
    )

    cache.append(
        current
    )

    cutoff = current - window

    while cache and cache[0] < cutoff:
        cache.pop(0)

    return len(cache)


# ============================================================
# VERIFICAÇÃO AUTOMOD
# ============================================================

async def process_automod_v2(
    message
):

    if not message.guild:
        return

    if message.author.bot:
        return

    config = moderation_config(
        message.guild.id
    )

    automod = config.get(
        "automod",
        {}
    )

    if not automod.get(
        "enabled",
        False
    ):
        return

    # --------------------------------------------------------
    # CANAIS IGNORADOS
    # --------------------------------------------------------

    ignored_channels = {
        int(channel_id)
        for channel_id in automod.get(
            "ignored_channels",
            config.get(
                "ignored_channels",
                []
            )
        )
        if str(channel_id).isdigit()
    }

    if message.channel.id in ignored_channels:
        return

    # --------------------------------------------------------
    # STAFF
    # --------------------------------------------------------

    if automod.get(
        "ignore_staff",
        True
    ):

        if (
            message.author.guild_permissions.manage_guild
            or message.author.guild_permissions.administrator
        ):
            return

    content = (
        message.content
        or ""
    )

    violation = None

    # --------------------------------------------------------
    # PALAVRAS BLOQUEADAS
    # --------------------------------------------------------

    blocked_words = [
        str(word).lower()
        for word in automod.get(
            "blocked_words",
            []
        )
        if word
    ]

    lowered = content.lower()

    for word in blocked_words:

        if word in lowered:

            violation = (
                "palavra bloqueada"
            )

            break

    # --------------------------------------------------------
    # CONVITES
    # --------------------------------------------------------

    if (
        not violation
        and automod.get(
            "block_invites",
            True
        )
        and contains_discord_invite(
            content
        )
    ):

        violation = (
            "convite do Discord"
        )

    # --------------------------------------------------------
    # LINKS
    # --------------------------------------------------------

    if (
        not violation
        and automod.get(
            "block_links",
            False
        )
        and contains_link(
            content
        )
    ):

        violation = "link"

    # --------------------------------------------------------
    # MENTIONS
    # --------------------------------------------------------

    max_mentions = int(
        automod.get(
            "max_mentions",
            5
        )
    )

    total_mentions = (
        len(message.mentions)
        + len(message.role_mentions)
    )

    if (
        not violation
        and automod.get(
            "anti_mass_mention",
            True
        )
        and total_mentions > max_mentions
    ):

        violation = (
            "excesso de menções"
        )

    # --------------------------------------------------------
    # SPAM
    # --------------------------------------------------------

    if (
        not violation
        and automod.get(
            "anti_spam",
            True
        )
    ):

        spam_count = register_spam_message(
            message.guild.id,
            message.author.id,
            int(
                automod.get(
                    "spam_window",
                    8
                )
            )
        )

        if spam_count >= int(
            automod.get(
                "spam_messages",
                6
            )
        ):

            violation = "spam"

    # --------------------------------------------------------
    # AÇÃO
    # --------------------------------------------------------

    if not violation:
        return

    try:

        await message.delete()

    except Exception:
        pass

    try:

        await message.channel.send(
            (
                f"🛡️ {message.author.mention}, "
                f"sua mensagem foi removida pelo AutoMod "
                f"({violation})."
            ),
            delete_after=5
        )

    except Exception:
        pass

    await send_moderation_log(
        message.guild,
        "🛡️ AutoMod acionado",
        (
            f"**Regra:** `{violation}`\n"
            f"**Canal:** {message.channel.mention}\n"
            f"**Mensagem:** "
            f"{content[:500] or '[vazia]'}"
        ),
        target=message.author,
        color=0xFEE75C
    )


# ============================================================
# /SEGURANCA STATUS
# ============================================================

@security_group.command(
    name="status",
    description="Mostra o estado de segurança do servidor."
)
async def security_status(
    interaction
):

    if not interaction.guild:
        return

    config = moderation_config(
        interaction.guild.id
    )

    automod = config[
        "automod"
    ]

    protection = config[
        "protection"
    ]

    embed = discord.Embed(
        title="🛡️ Segurança do servidor",
        color=0x5865F2
    )

    embed.add_field(
        name="🛡️ Moderação",
        value=(
            "🟢 Ativa"
            if config.get(
                "enabled",
                True
            )
            else "🔴 Desativada"
        ),
        inline=True
    )

    embed.add_field(
        name="🤖 AutoMod",
        value=(
            "🟢 Ativo"
            if automod.get(
                "enabled",
                False
            )
            else "🔴 Desativado"
        ),
        inline=True
    )

    embed.add_field(
        name="🔒 Lockdown",
        value=(
            "🔴 Ativo"
            if protection.get(
                "lockdown",
                False
            )
            else "🟢 Normal"
        ),
        inline=True
    )

    embed.add_field(
        name="🤖 Anti-Bot",
        value=(
            "🟢"
            if protection.get(
                "anti_bot",
                False
            )
            else "🔴"
        ),
        inline=True
    )

    embed.add_field(
        name="🔗 Bloqueio de links",
        value=(
            "🟢"
            if automod.get(
                "block_links",
                False
            )
            else "🔴"
        ),
        inline=True
    )

    embed.add_field(
        name="📨 Anti-spam",
        value=(
            "🟢"
            if automod.get(
                "anti_spam",
                True
            )
            else "🔴"
        ),
        inline=True
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ============================================================
# /SEGURANCA AUTOMOD
# ============================================================

@security_group.command(
    name="automod",
    description="Configura o AutoMod."
)
@app_commands.describe(
    ativo="Ativa ou desativa o AutoMod."
)
async def security_automod(
    interaction,
    ativo: bool
):

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    config = moderation_config(
        interaction.guild.id
    )

    config[
        "automod"
    ][
        "enabled"
    ] = ativo

    save_data()

    await interaction.response.send_message(
        (
            "🟢 AutoMod ativado."
            if ativo
            else "🔴 AutoMod desativado."
        )
    )


# ============================================================
# /SEGURANCA LOCKDOWN
# ============================================================

@security_group.command(
    name="lockdown",
    description="Ativa ou desativa o lockdown."
)
@app_commands.describe(
    ativo="Ativar ou desativar."
)
async def security_lockdown(
    interaction,
    ativo: bool
):

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    guild = interaction.guild

    config = moderation_config(
        guild.id
    )

    config[
        "protection"
    ][
        "lockdown"
    ] = ativo

    await interaction.response.defer()

    changed = 0

    for channel in guild.text_channels:

        try:

            overwrite = channel.overwrites_for(
                guild.default_role
            )

            overwrite.send_messages = (
                False
                if ativo
                else None
            )

            await channel.set_permissions(
                guild.default_role,
                overwrite=overwrite,
                reason=(
                    "Aura Lockdown"
                )
            )

            changed += 1

        except Exception:
            continue

    save_data()

    await interaction.followup.send(
        (
            f"🔒 Lockdown ativado em `{changed}` canais."
            if ativo
            else f"🔓 Lockdown desativado em `{changed}` canais."
        )
    )

    await send_moderation_log(
        guild,
        (
            "🔒 Lockdown ativado"
            if ativo
            else "🔓 Lockdown desativado"
        ),
        f"Canais afetados: `{changed}`",
        moderator=interaction.user
    )


# ============================================================
# PAINEL VISUAL DE MODERAÇÃO
# ============================================================

class ModerationPanelView(
    discord.ui.View
):

    def __init__(
        self,
        guild_id
    ):

        super().__init__(
            timeout=300
        )

        self.guild_id = guild_id

        self.add_item(
            ModerationAutoModButton(
                guild_id
            )
        )

        self.add_item(
            ModerationLockdownButton(
                guild_id
            )
        )

        self.add_item(
            ModerationBackButton()
        )


class ModerationAutoModButton(
    discord.ui.Button
):

    def __init__(
        self,
        guild_id
    ):

        self.guild_id = guild_id

        config = moderation_config(
            guild_id
        )

        active = config[
            "automod"
        ].get(
            "enabled",
            False
        )

        super().__init__(
            label=(
                "Desativar AutoMod"
                if active
                else "Ativar AutoMod"
            ),
            emoji="🤖",
            style=(
                discord.ButtonStyle.danger
                if active
                else discord.ButtonStyle.success
            )
        )

    async def callback(
        self,
        interaction
    ):

        if not can_use_admin_command(
            interaction
        ):

            await interaction.response.send_message(
                "❌ Sem permissão.",
                ephemeral=True
            )

            return

        config = moderation_config(
            self.guild_id
        )

        config[
            "automod"
        ][
            "enabled"
        ] = not config[
            "automod"
        ].get(
            "enabled",
            False
        )

        save_data()

        await show_moderation_panel(
            interaction
        )


class ModerationLockdownButton(
    discord.ui.Button
):

    def __init__(
        self,
        guild_id
    ):

        self.guild_id = guild_id

        config = moderation_config(
            guild_id
        )

        active = config[
            "protection"
        ].get(
            "lockdown",
            False
        )

        super().__init__(
            label=(
                "Desativar Lockdown"
                if active
                else "Ativar Lockdown"
            ),
            emoji="🔒",
            style=(
                discord.ButtonStyle.danger
                if active
                else discord.ButtonStyle.secondary
            )
        )

    async def callback(
        self,
        interaction
    ):

        if not can_use_admin_command(
            interaction
        ):

            await interaction.response.send_message(
                "❌ Sem permissão.",
                ephemeral=True
            )

            return

        config = moderation_config(
            self.guild_id
        )

        active = not config[
            "protection"
        ].get(
            "lockdown",
            False
        )

        config[
            "protection"
        ][
            "lockdown"
        ] = active

        await interaction.response.defer(
            ephemeral=True
        )

        guild = interaction.guild

        changed = 0

        for channel in guild.text_channels:

            try:

                overwrite = channel.overwrites_for(
                    guild.default_role
                )

                overwrite.send_messages = (
                    False
                    if active
                    else None
                )

                await channel.set_permissions(
                    guild.default_role,
                    overwrite=overwrite
                )

                changed += 1

            except Exception:
                pass

        save_data()

        await interaction.followup.send(
            (
                f"🔒 Lockdown ativado em `{changed}` canais."
                if active
                else f"🔓 Lockdown desativado em `{changed}` canais."
            ),
            ephemeral=True
        )


class ModerationBackButton(
    discord.ui.Button
):

    def __init__(self):

        super().__init__(
            label="Voltar ao painel",
            emoji="◀️",
            style=discord.ButtonStyle.secondary,
            row=4
        )

    async def callback(
        self,
        interaction
    ):

        await interaction.response.edit_message(
            embed=build_main_panel_embed(
                interaction.guild
            ),
            view=AuraMainPanelView()
        )


async def show_moderation_panel(
    interaction
):

    config = moderation_config(
        interaction.guild.id
    )

    automod = config[
        "automod"
    ]

    protection = config[
        "protection"
    ]

    embed = discord.Embed(
        title="🛡️ Moderação e Segurança",
        description=(
            "Controle a proteção do servidor "
            "diretamente pelo painel do Aura."
        ),
        color=0x5865F2
    )

    embed.add_field(
        name="🤖 AutoMod",
        value=(
            "🟢 Ativo"
            if automod.get(
                "enabled",
                False
            )
            else "🔴 Desativado"
        ),
        inline=True
    )

    embed.add_field(
        name="🔒 Lockdown",
        value=(
            "🔴 Ativo"
            if protection.get(
                "lockdown",
                False
            )
            else "🟢 Normal"
        ),
        inline=True
    )

    embed.add_field(
        name="📝 Warn limit",
        value=str(
            config.get(
                "warn_limit",
                3
            )
        ),
        inline=True
    )

    await interaction.response.edit_message(
        embed=embed,
        view=ModerationPanelView(
            interaction.guild.id
        )
    )


# ============================================================
# HANDLER DO /PAINEL
# ============================================================

async def handle_moderation_panel_action(
    interaction,
    action="moderation"
):

    await show_moderation_panel(
        interaction
    )


async def handle_security_panel_action(
    interaction,
    action="security"
):

    await show_moderation_panel(
        interaction
    )


# ============================================================
# INTEGRAÇÃO DO AUTOMOD COM O ON_MESSAGE EXISTENTE
# ============================================================

# IMPORTANTE:
#
# NÃO crie outro @bot.event
# async def on_message() aqui.
#
# Na função on_message ÚNICA do seu projeto,
# mantenha:
#
#     await process_automod_v2(message)
#
#     await update_ticket_activity(message)
#
#     ...restante do processamento...
#
#


# ============================================================
# INTEGRAÇÃO DE LOGS DE ENTRADA/SAÍDA
# ============================================================

async def handle_member_join_security(
    member
):

    config = moderation_config(
        member.guild.id
    )

    protection = config[
        "protection"
    ]

    # --------------------------------------------------------
    # ANTI-BOT
    # --------------------------------------------------------

    if (
        member.bot
        and protection.get(
            "anti_bot",
            False
        )
    ):

        try:

            await member.kick(
                reason="Aura Anti-Bot"
            )

            await send_moderation_log(
                member.guild,
                "🤖 Bot bloqueado",
                (
                    f"O usuário {member.mention} "
                    "foi removido pelo Anti-Bot."
                ),
                target=member
            )

        except Exception as error:

            print(
                f"[AURA ANTI-BOT] {error}"
            )

    # --------------------------------------------------------
    # LOG DE ENTRADA
    # --------------------------------------------------------

    try:

        await audit_log(
            member.guild,
            "members",
            "Membro entrou",
            member,
            f"ID: {member.id}"
        )

    except Exception:
        pass


# ============================================================
# LOG DE SAÍDA
# ============================================================

async def handle_member_leave_security(
    member
):

    try:

        await audit_log(
            member.guild,
            "members",
            "Membro saiu",
            member,
            f"ID: {member.id}"
        )

    except Exception:
        pass


# ============================================================
# WEBHOOK SECURITY
# ============================================================

@security_group.command(
    name="webhooks",
    description="Mostra os webhooks do servidor."
)
async def security_webhooks(
    interaction
):

    if not interaction.guild:
        return

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    try:

        webhooks = await interaction.guild.webhooks()

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ Não tenho permissão para visualizar webhooks.",
            ephemeral=True
        )

        return

    if not webhooks:

        await interaction.response.send_message(
            "✅ Nenhum webhook encontrado.",
            ephemeral=True
        )

        return

    lines = []

    for webhook in webhooks[:25]:

        channel = (
            webhook.channel.mention
            if webhook.channel
            else "Canal desconhecido"
        )

        lines.append(
            f"🔗 **{webhook.name}**\n"
            f"Canal: {channel}\n"
            f"ID: `{webhook.id}`"
        )

    embed = discord.Embed(
        title="🔗 Webhooks",
        description="\n\n".join(
            lines
        ),
        color=0x5865F2
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ============================================================
# CONFIGURAÇÃO DE PROTEÇÃO
# ============================================================

@security_group.command(
    name="protecao",
    description="Ativa ou desativa uma proteção."
)
@app_commands.describe(
    protecao="Proteção.",
    ativo="Estado."
)
@app_commands.choices(
    protecao=[
        app_commands.Choice(
            name="Anti-Bot",
            value="anti_bot"
        ),
        app_commands.Choice(
            name="Anti-Webhook",
            value="anti_webhook"
        ),
        app_commands.Choice(
            name="Anti-Mass-Join",
            value="anti_mass_join"
        ),
    ]
)
async def security_protection(
    interaction,
    protecao: str,
    ativo: bool
):

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    config = moderation_config(
        interaction.guild.id
    )

    config[
        "protection"
    ][
        protecao
    ] = ativo

    save_data()

    await interaction.response.send_message(
        (
            f"🟢 `{protecao}` ativado."
            if ativo
            else f"🔴 `{protecao}` desativado."
        )
    )


# ============================================================
# CONFIGURAÇÃO DE WARN
# ============================================================

@moderation_group.command(
    name="config",
    description="Configura o sistema de advertências."
)
@app_commands.describe(
    limite="Quantidade de advertências.",
    acao="Ação ao atingir o limite."
)
@app_commands.choices(
    acao=[
        app_commands.Choice(
            name="Timeout",
            value="mute"
        ),
        app_commands.Choice(
            name="Expulsar",
            value="kick"
        ),
        app_commands.Choice(
            name="Banir",
            value="ban"
        ),
    ]
)
async def moderation_config_command(
    interaction,
    limite: app_commands.Range[int, 1, 20],
    acao: str
):

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    config = moderation_config(
        interaction.guild.id
    )

    config[
        "warn_limit"
    ] = limite

    config[
        "warn_action"
    ] = acao

    save_data()

    await interaction.response.send_message(
        (
            f"✅ Configuração atualizada.\n"
            f"Limite: `{limite}`\n"
            f"Ação: `{acao}`"
        )
    )


# ============================================================
# INICIALIZAÇÃO
# ============================================================

def initialize_moderation_system():

    for guild in bot.guilds:

        moderation_config(
            guild.id
        )

    save_data()

    print(
        "[AURA MODERATION] Sistema carregado."
    )


# ============================================================
# FINAL DA PARTE 4
# ============================================================

# ============================================================
# AURA BOT — PARTE 5
# ECONOMIA • XP • NÍVEIS • RANKING • LOJA • INVENTÁRIO
# ============================================================


# ============================================================
# CONFIGURAÇÕES
# ============================================================

ECONOMY_DEFAULTS = {
    "enabled": True,

    "currency_name": "Aura Coins",
    "currency_symbol": "🪙",

    "daily_reward": 500,
    "daily_cooldown": 86400,

    "message_min": 5,
    "message_max": 15,
    "message_cooldown": 45,

    "level_enabled": True,

    "xp_min": 8,
    "xp_max": 18,
    "xp_cooldown": 45,

    "level_rewards": {},

    "shop": {
        "enabled": True,
        "items": {}
    }
}


# ============================================================
# CONFIGURAÇÃO POR SERVIDOR
# ============================================================

def economy_config(guild_id):

    settings = data.setdefault(
        "guild_settings",
        {}
    )

    guild_data = settings.setdefault(
        str(guild_id),
        {}
    )

    economy = guild_data.setdefault(
        "economy",
        {}
    )

    merge_defaults(
        economy,
        ECONOMY_DEFAULTS
    )

    if not isinstance(
        economy.get("shop"),
        dict
    ):
        economy["shop"] = {}

    merge_defaults(
        economy["shop"],
        ECONOMY_DEFAULTS["shop"]
    )

    return economy


# ============================================================
# DADOS DOS USUÁRIOS
# ============================================================

def finance_data(guild_id):

    finance = data.setdefault(
        "finance",
        {}
    )

    return finance.setdefault(
        str(guild_id),
        {}
    )


def user_finance(
    guild_id,
    user_id
):

    guild_finance = finance_data(
        guild_id
    )

    account = guild_finance.setdefault(
        str(user_id),
        {}
    )

    account.setdefault(
        "balance",
        0
    )

    account.setdefault(
        "bank",
        0
    )

    account.setdefault(
        "inventory",
        []
    )

    account.setdefault(
        "last_daily",
        0
    )

    account.setdefault(
        "last_work",
        0
    )

    account.setdefault(
        "last_rob",
        0
    )

    account.setdefault(
        "streak",
        0
    )

    return account


# ============================================================
# XP / LEVEL
# ============================================================

def level_data(guild_id):

    levels = data.setdefault(
        "levels",
        {}
    )

    return levels.setdefault(
        str(guild_id),
        {}
    )


def user_level_data(
    guild_id,
    user_id
):

    guild_levels = level_data(
        guild_id
    )

    user = guild_levels.setdefault(
        str(user_id),
        {}
    )

    user.setdefault(
        "xp",
        0
    )

    user.setdefault(
        "level",
        0
    )

    user.setdefault(
        "total_xp",
        0
    )

    user.setdefault(
        "last_xp",
        0
    )

    return user


def xp_required(
    level
):

    level = max(
        0,
        int(level)
    )

    return 100 + (
        level * 75
    ) + (
        level * level * 25
    )


def calculate_level_from_xp(
    xp
):

    level = 0
    remaining = max(
        0,
        int(xp)
    )

    while remaining >= xp_required(
        level
    ):

        remaining -= xp_required(
            level
        )

        level += 1

        if level > 10000:
            break

    return level, remaining


def add_xp(
    guild_id,
    user_id,
    amount
):

    profile = user_level_data(
        guild_id,
        user_id
    )

    old_level = profile.get(
        "level",
        0
    )

    profile["total_xp"] = (
        profile.get(
            "total_xp",
            0
        )
        + max(0, int(amount))
    )

    new_level, current_xp = (
        calculate_level_from_xp(
            profile["total_xp"]
        )
    )

    profile["level"] = new_level
    profile["xp"] = current_xp

    return (
        old_level,
        new_level
    )


# ============================================================
# MOEDA
# ============================================================

def get_balance(
    guild_id,
    user_id
):

    return int(
        user_finance(
            guild_id,
            user_id
        ).get(
            "balance",
            0
        )
    )


def set_balance(
    guild_id,
    user_id,
    amount
):

    account = user_finance(
        guild_id,
        user_id
    )

    account[
        "balance"
    ] = max(
        0,
        int(amount)
    )

    return account[
        "balance"
    ]


def add_money(
    guild_id,
    user_id,
    amount
):

    return set_balance(
        guild_id,
        user_id,
        get_balance(
            guild_id,
            user_id
        ) + int(amount)
    )


def remove_money(
    guild_id,
    user_id,
    amount
):

    account = user_finance(
        guild_id,
        user_id
    )

    amount = max(
        0,
        int(amount)
    )

    current = get_balance(
        guild_id,
        user_id
    )

    if current < amount:
        return False

    account[
        "balance"
    ] = current - amount

    return True


# ============================================================
# /ECONOMIA SALDO
# ============================================================

@economy_group.command(
    name="saldo",
    description="Mostra seu saldo."
)
@app_commands.describe(
    membro="Membro que deseja consultar."
)
async def economy_balance(
    interaction,
    membro: discord.Member = None
):

    target = (
        membro
        or interaction.user
    )

    config = economy_config(
        interaction.guild.id
    )

    balance = get_balance(
        interaction.guild.id,
        target.id
    )

    account = user_finance(
        interaction.guild.id,
        target.id
    )

    embed = discord.Embed(
        title="💰 Saldo",
        color=0xF1C40F
    )

    embed.set_author(
        name=str(target),
        icon_url=target.display_avatar.url
    )

    embed.add_field(
        name="💵 Carteira",
        value=(
            f"{config['currency_symbol']} "
            f"{balance:,}"
        ),
        inline=True
    )

    embed.add_field(
        name="🏦 Banco",
        value=(
            f"{config['currency_symbol']} "
            f"{int(account.get('bank', 0)):,}"
        ),
        inline=True
    )

    embed.add_field(
        name="💎 Total",
        value=(
            f"{config['currency_symbol']} "
            f"{balance + int(account.get('bank', 0)):,}"
        ),
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# DAILY
# ============================================================

@economy_group.command(
    name="daily",
    description="Receba sua recompensa diária."
)
async def economy_daily(
    interaction
):

    guild_id = interaction.guild.id
    user_id = interaction.user.id

    config = economy_config(
        guild_id
    )

    account = user_finance(
        guild_id,
        user_id
    )

    current = time.time()
    last = float(
        account.get(
            "last_daily",
            0
        )
    )

    cooldown = int(
        config.get(
            "daily_cooldown",
            86400
        )
    )

    remaining = cooldown - (
        current - last
    )

    if remaining > 0:

        hours = int(
            remaining // 3600
        )

        minutes = int(
            (remaining % 3600) // 60
        )

        await interaction.response.send_message(
            (
                f"⏳ Você já recebeu seu daily.\n"
                f"Tente novamente em "
                f"`{hours}h {minutes}min`."
            ),
            ephemeral=True
        )

        return

    reward = random.randint(
        int(
            config.get(
                "daily_reward",
                500
            )
        ),
        int(
            config.get(
                "daily_reward",
                500
            )
        )
    )

    add_money(
        guild_id,
        user_id,
        reward
    )

    account[
        "last_daily"
    ] = current

    account[
        "streak"
    ] = int(
        account.get(
            "streak",
            0
        )
    ) + 1

    save_data()

    await interaction.response.send_message(
        (
            f"🎁 **Daily recebido!**\n"
            f"Você ganhou "
            f"{config['currency_symbol']} "
            f"`{reward:,}`.\n"
            f"🔥 Streak: `{account['streak']}`"
        )
    )


# ============================================================
# PAGAR
# ============================================================

@economy_group.command(
    name="pagar",
    description="Transfere dinheiro para outro membro."
)
@app_commands.describe(
    membro="Quem receberá.",
    valor="Valor da transferência."
)
async def economy_pay(
    interaction,
    membro: discord.Member,
    valor: app_commands.Range[
        int, 1, 1000000000
    ]
):

    if membro.id == interaction.user.id:

        await interaction.response.send_message(
            "❌ Você não pode pagar a si mesmo.",
            ephemeral=True
        )

        return

    if membro.bot:

        await interaction.response.send_message(
            "❌ Você não pode transferir para um bot.",
            ephemeral=True
        )

        return

    guild_id = interaction.guild.id

    if not remove_money(
        guild_id,
        interaction.user.id,
        valor
    ):

        await interaction.response.send_message(
            "❌ Você não possui dinheiro suficiente.",
            ephemeral=True
        )

        return

    add_money(
        guild_id,
        membro.id,
        valor
    )

    save_data()

    config = economy_config(
        guild_id
    )

    await interaction.response.send_message(
        (
            f"💸 {interaction.user.mention} enviou "
            f"{config['currency_symbol']} `{valor:,}` "
            f"para {membro.mention}."
        )
    )


# ============================================================
# RANKING ECONÔMICO
# ============================================================

@economy_group.command(
    name="rank",
    description="Mostra o ranking econômico."
)
async def economy_rank(
    interaction
):

    guild_id = interaction.guild.id

    accounts = finance_data(
        guild_id
    )

    ranking = []

    for user_id, account in accounts.items():

        try:
            balance = int(
                account.get(
                    "balance",
                    0
                )
            )

            bank = int(
                account.get(
                    "bank",
                    0
                )
            )

            total = balance + bank

            ranking.append(
                (
                    int(user_id),
                    total
                )
            )

        except Exception:
            continue

    ranking.sort(
        key=lambda item: item[1],
        reverse=True
    )

    ranking = ranking[:10]

    if not ranking:

        await interaction.response.send_message(
            "📊 Ainda não existem dados econômicos.",
            ephemeral=True
        )

        return

    config = economy_config(
        guild_id
    )

    lines = []

    for index, (
        user_id,
        amount
    ) in enumerate(
        ranking,
        start=1
    ):

        member = interaction.guild.get_member(
            user_id
        )

        name = (
            member.mention
            if member
            else f"<@{user_id}>"
        )

        lines.append(
            f"**{index}.** {name} — "
            f"{config['currency_symbol']} `{amount:,}`"
        )

    embed = discord.Embed(
        title="🏆 Ranking Econômico",
        description="\n".join(
            lines
        ),
        color=0xF1C40F
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# XP POR MENSAGEM
# ============================================================

XP_MESSAGE_CACHE = {}


def xp_message_allowed(
    guild_id,
    user_id,
    cooldown
):

    key = (
        guild_id,
        user_id
    )

    current = time.time()

    last = XP_MESSAGE_CACHE.get(
        key,
        0
    )

    if current - last < cooldown:
        return False

    XP_MESSAGE_CACHE[
        key
    ] = current

    return True


async def process_economy_message(
    message
):

    if not message.guild:
        return

    if message.author.bot:
        return

    config = economy_config(
        message.guild.id
    )

    if not config.get(
        "enabled",
        True
    ):
        return

    guild_id = message.guild.id
    user_id = message.author.id

    # --------------------------------------------------------
    # DINHEIRO
    # --------------------------------------------------------

    if xp_message_allowed(
        guild_id,
        user_id,
        int(
            config.get(
                "message_cooldown",
                45
            )
        )
    ):

        money = random.randint(
            int(
                config.get(
                    "message_min",
                    5
                )
            ),
            int(
                config.get(
                    "message_max",
                    15
                )
            )
        )

        add_money(
            guild_id,
            user_id,
            money
        )

    # --------------------------------------------------------
    # XP
    # --------------------------------------------------------

    if config.get(
        "level_enabled",
        True
    ):

        if xp_message_allowed(
            guild_id,
            user_id,
            int(
                config.get(
                    "xp_cooldown",
                    45
                )
            )
        ):

            xp = random.randint(
                int(
                    config.get(
                        "xp_min",
                        8
                    )
                ),
                int(
                    config.get(
                        "xp_max",
                        18
                    )
                )
            )

            old_level, new_level = add_xp(
                guild_id,
                user_id,
                xp
            )

            if new_level > old_level:

                await handle_level_up(
                    message.author,
                    new_level
                )

    save_data()


# ============================================================
# LEVEL UP
# ============================================================

async def handle_level_up(
    member,
    level
):

    guild_id = member.guild.id

    config = economy_config(
        guild_id
    )

    rewards = config.get(
        "level_rewards",
        {}
    )

    reward = rewards.get(
        str(level)
    )

    message = (
        f"🎉 {member.mention} subiu para "
        f"o **nível {level}**!"
    )

    if reward:

        try:

            reward_amount = int(
                reward
            )

            add_money(
                guild_id,
                member.id,
                reward_amount
            )

            message += (
                f"\n🎁 Recompensa: "
                f"{config['currency_symbol']} "
                f"`{reward_amount:,}`"
            )

        except Exception:
            pass

    try:

        await member.guild.system_channel.send(
            message
        )

    except Exception:

        try:

            await member.send(
                message
            )

        except Exception:
            pass


# ============================================================
# /LEVEL
# ============================================================

@bot.tree.command(
    name="level",
    description="Mostra seu nível e XP."
)
@app_commands.describe(
    membro="Membro que deseja consultar."
)
async def level_command(
    interaction,
    membro: discord.Member = None
):

    target = (
        membro
        or interaction.user
    )

    profile = user_level_data(
        interaction.guild.id,
        target.id
    )

    level = int(
        profile.get(
            "level",
            0
        )
    )

    current_xp = int(
        profile.get(
            "xp",
            0
        )
    )

    required = xp_required(
        level
    )

    total_xp = int(
        profile.get(
            "total_xp",
            0
        )
    )

    embed = discord.Embed(
        title=f"📈 Nível • {target}",
        color=0x5865F2
    )

    embed.set_thumbnail(
        url=target.display_avatar.url
    )

    embed.add_field(
        name="🏅 Nível",
        value=f"`{level}`",
        inline=True
    )

    embed.add_field(
        name="✨ XP",
        value=(
            f"`{current_xp:,} / "
            f"{required:,}`"
        ),
        inline=True
    )

    embed.add_field(
        name="📊 XP total",
        value=f"`{total_xp:,}`",
        inline=True
    )

    progress = (
        int(
            (
                current_xp
                / max(1, required)
            ) * 20
        )
    )

    progress = max(
        0,
        min(
            20,
            progress
        )
    )

    bar = (
        "🟦" * progress
        + "⬜" * (20 - progress)
    )

    embed.add_field(
        name="Progresso",
        value=bar,
        inline=False
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# RANKING DE XP
# ============================================================

@bot.tree.command(
    name="ranking",
    description="Mostra o ranking de níveis."
)
async def level_ranking(
    interaction
):

    guild_id = interaction.guild.id

    levels = level_data(
        guild_id
    )

    ranking = []

    for user_id, profile in levels.items():

        try:

            ranking.append(
                (
                    int(user_id),
                    int(
                        profile.get(
                            "total_xp",
                            0
                        )
                    ),
                    int(
                        profile.get(
                            "level",
                            0
                        )
                    )
                )
            )

        except Exception:
            continue

    ranking.sort(
        key=lambda item: item[1],
        reverse=True
    )

    ranking = ranking[:10]

    if not ranking:

        await interaction.response.send_message(
            "📊 Ainda não existem jogadores no ranking.",
            ephemeral=True
        )

        return

    lines = []

    for index, (
        user_id,
        total_xp,
        level
    ) in enumerate(
        ranking,
        start=1
    ):

        member = interaction.guild.get_member(
            user_id
        )

        name = (
            member.mention
            if member
            else f"<@{user_id}>"
        )

        lines.append(
            f"**{index}.** {name} — "
            f"Nível `{level}` • "
            f"`{total_xp:,} XP`"
        )

    embed = discord.Embed(
        title="🏆 Ranking de XP",
        description="\n".join(
            lines
        ),
        color=0x5865F2
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# RANKING SEMANAL
# ============================================================

@bot.tree.command(
    name="ranking_semanal",
    description="Mostra o ranking semanal."
)
async def weekly_ranking(
    interaction
):

    guild_id = interaction.guild.id

    levels = level_data(
        guild_id
    )

    ranking = []

    for user_id, profile in levels.items():

        weekly_xp = int(
            profile.get(
                "weekly_xp",
                0
            )
        )

        ranking.append(
            (
                int(user_id),
                weekly_xp
            )
        )

    ranking.sort(
        key=lambda item: item[1],
        reverse=True
    )

    ranking = ranking[:10]

    if not ranking:

        await interaction.response.send_message(
            "📊 Ainda não há dados semanais.",
            ephemeral=True
        )

        return

    lines = []

    for index, (
        user_id,
        xp
    ) in enumerate(
        ranking,
        start=1
    ):

        member = interaction.guild.get_member(
            user_id
        )

        name = (
            member.mention
            if member
            else f"<@{user_id}>"
        )

        lines.append(
            f"**{index}.** {name} — `{xp:,} XP`"
        )

    embed = discord.Embed(
        title="📅 Ranking Semanal",
        description="\n".join(
            lines
        ),
        color=0x5865F2
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# LOJA
# ============================================================

def shop_items(
    guild_id
):

    config = economy_config(
        guild_id
    )

    return config[
        "shop"
    ].setdefault(
        "items",
        {}
    )


@economy_group.command(
    name="loja",
    description="Mostra a loja do servidor."
)
async def economy_shop(
    interaction
):

    items = shop_items(
        interaction.guild.id
    )

    config = economy_config(
        interaction.guild.id
    )

    if not items:

        await interaction.response.send_message(
            "🛒 A loja está vazia.",
            ephemeral=True
        )

        return

    lines = []

    for item_id, item in items.items():

        name = item.get(
            "name",
            item_id
        )

        price = int(
            item.get(
                "price",
                0
            )
        )

        description = item.get(
            "description",
            "Sem descrição."
        )

        lines.append(
            f"### 🛍️ {name}\n"
            f"{description}\n"
            f"💰 {config['currency_symbol']} "
            f"`{price:,}`\n"
            f"ID: `{item_id}`"
        )

    embed = discord.Embed(
        title="🛒 Loja do servidor",
        description="\n\n".join(
            lines
        ),
        color=0x57F287
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# ADICIONAR ITEM À LOJA
# ============================================================

@economy_group.command(
    name="loja-adicionar",
    description="Adiciona um item à loja."
)
@app_commands.describe(
    id="ID único do item.",
    nome="Nome do item.",
    preco="Preço.",
    descricao="Descrição."
)
async def shop_add(
    interaction,
    id: str,
    nome: str,
    preco: app_commands.Range[
        int, 1, 1000000000
    ],
    descricao: str = "Sem descrição."
):

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    items = shop_items(
        interaction.guild.id
    )

    item_id = safe_name(
        id
    ).lower()

    if not item_id:

        await interaction.response.send_message(
            "❌ ID inválido.",
            ephemeral=True
        )

        return

    items[
        item_id
    ] = {
        "name": nome,
        "price": preco,
        "description": descricao,
        "created_at": now_iso()
    }

    save_data()

    await interaction.response.send_message(
        (
            f"✅ Item `{item_id}` adicionado à loja.\n"
            f"💰 Preço: `{preco:,}`"
        )
    )


# ============================================================
# COMPRAR
# ============================================================

@economy_group.command(
    name="comprar",
    description="Compra um item da loja."
)
@app_commands.describe(
    id="ID do item."
)
async def economy_buy(
    interaction,
    id: str
):

    guild_id = interaction.guild.id

    items = shop_items(
        guild_id
    )

    item_id = safe_name(
        id
    ).lower()

    item = items.get(
        item_id
    )

    if not item:

        await interaction.response.send_message(
            "❌ Item não encontrado.",
            ephemeral=True
        )

        return

    price = int(
        item.get(
            "price",
            0
        )
    )

    if not remove_money(
        guild_id,
        interaction.user.id,
        price
    ):

        await interaction.response.send_message(
            "❌ Você não possui dinheiro suficiente.",
            ephemeral=True
        )

        return

    account = user_finance(
        guild_id,
        interaction.user.id
    )

    inventory = account.setdefault(
        "inventory",
        []
    )

    inventory.append(
        {
            "id": item_id,
            "name": item.get(
                "name",
                item_id
            ),
            "bought_at": now_iso()
        }
    )

    save_data()

    config = economy_config(
        guild_id
    )

    await interaction.response.send_message(
        (
            f"🛍️ Você comprou **{item.get('name', item_id)}**!\n"
            f"💰 Pago: {config['currency_symbol']} `{price:,}`"
        )
    )


# ============================================================
# INVENTÁRIO
# ============================================================

@economy_group.command(
    name="inventario",
    description="Mostra seu inventário."
)
@app_commands.describe(
    membro="Membro que deseja consultar."
)
async def economy_inventory(
    interaction,
    membro: discord.Member = None
):

    target = (
        membro
        or interaction.user
    )

    account = user_finance(
        interaction.guild.id,
        target.id
    )

    inventory = account.get(
        "inventory",
        []
    )

    if not inventory:

        await interaction.response.send_message(
            f"🎒 {target.mention} não possui itens.",
            ephemeral=True
        )

        return

    counts = {}

    for item in inventory:

        item_id = item.get(
            "id",
            "desconhecido"
        )

        name = item.get(
            "name",
            item_id
        )

        counts.setdefault(
            item_id,
            {
                "name": name,
                "count": 0
            }
        )

        counts[
            item_id
        ][
            "count"
        ] += 1

    lines = []

    for item_id, item in counts.items():

        lines.append(
            f"🛍️ **{item['name']}** "
            f"`x{item['count']}`\n"
            f"ID: `{item_id}`"
        )

    embed = discord.Embed(
        title=f"🎒 Inventário • {target}",
        description="\n\n".join(
            lines
        ),
        color=0x5865F2
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# ADMIN — DAR DINHEIRO
# ============================================================

@economy_group.command(
    name="dar",
    description="Dá dinheiro para um membro."
)
@app_commands.describe(
    membro="Membro.",
    valor="Quantidade."
)
async def economy_give(
    interaction,
    membro: discord.Member,
    valor: app_commands.Range[
        int, 1, 1000000000
    ]
):

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    add_money(
        interaction.guild.id,
        membro.id,
        valor
    )

    save_data()

    await interaction.response.send_message(
        f"💰 Foram adicionadas `{valor:,}` moedas para {membro.mention}."
    )


# ============================================================
# ADMIN — REMOVER DINHEIRO
# ============================================================

@economy_group.command(
    name="remover",
    description="Remove dinheiro de um membro."
)
@app_commands.describe(
    membro="Membro.",
    valor="Quantidade."
)
async def economy_remove(
    interaction,
    membro: discord.Member,
    valor: app_commands.Range[
        int, 1, 1000000000
    ]
):

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    removed = remove_money(
        interaction.guild.id,
        membro.id,
        valor
    )

    if not removed:

        await interaction.response.send_message(
            "❌ O membro não possui dinheiro suficiente.",
            ephemeral=True
        )

        return

    save_data()

    await interaction.response.send_message(
        f"💸 Foram removidas `{valor:,}` moedas de {membro.mention}."
    )


# ============================================================
# ADMIN — DAR XP
# ============================================================

@economy_group.command(
    name="darxp",
    description="Adiciona XP para um membro."
)
@app_commands.describe(
    membro="Membro.",
    quantidade="Quantidade de XP."
)
async def economy_give_xp(
    interaction,
    membro: discord.Member,
    quantidade: app_commands.Range[
        int, 1, 1000000000
    ]
):

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    old_level, new_level = add_xp(
        interaction.guild.id,
        membro.id,
        quantidade
    )

    save_data()

    await interaction.response.send_message(
        (
            f"✨ {membro.mention} recebeu "
            f"`{quantidade:,} XP`.\n"
            f"Nível: `{new_level}`"
        )
    )


# ============================================================
# LEGACY — DEPOSITAR
# ============================================================

@economy_group.command(
    name="depositar",
    description="Deposita moedas no banco."
)
@app_commands.describe(
    valor="Valor."
)
async def economy_deposit(
    interaction,
    valor: app_commands.Range[
        int, 1, 1000000000
    ]
):

    guild_id = interaction.guild.id
    account = user_finance(
        guild_id,
        interaction.user.id
    )

    if not remove_money(
        guild_id,
        interaction.user.id,
        valor
    ):

        await interaction.response.send_message(
            "❌ Saldo insuficiente.",
            ephemeral=True
        )

        return

    account[
        "bank"
    ] = int(
        account.get(
            "bank",
            0
        )
    ) + valor

    save_data()

    await interaction.response.send_message(
        f"🏦 Você depositou `{valor:,}` moedas."
    )


# ============================================================
# LEGACY — SACAR
# ============================================================

@economy_group.command(
    name="sacar",
    description="Saca moedas do banco."
)
@app_commands.describe(
    valor="Valor."
)
async def economy_withdraw(
    interaction,
    valor: app_commands.Range[
        int, 1, 1000000000
    ]
):

    guild_id = interaction.guild.id

    account = user_finance(
        guild_id,
        interaction.user.id
    )

    bank = int(
        account.get(
            "bank",
            0
        )
    )

    if bank < valor:

        await interaction.response.send_message(
            "❌ Você não possui esse valor no banco.",
            ephemeral=True
        )

        return

    account[
        "bank"
    ] = bank - valor

    add_money(
        guild_id,
        interaction.user.id,
        valor
    )

    save_data()

    await interaction.response.send_message(
        f"💵 Você sacou `{valor:,}` moedas."
    )


# ============================================================
# TRABALHO
# ============================================================

@economy_group.command(
    name="trabalho",
    description="Trabalha para ganhar moedas."
)
async def economy_work(
    interaction
):

    guild_id = interaction.guild.id

    account = user_finance(
        guild_id,
        interaction.user.id
    )

    current = time.time()

    last_work = float(
        account.get(
            "last_work",
            0
        )
    )

    if current - last_work < 3600:

        remaining = int(
            3600 - (
                current - last_work
            )
        )

        minutes = remaining // 60

        await interaction.response.send_message(
            f"⏳ Você poderá trabalhar novamente em `{minutes} min`.",
            ephemeral=True
        )

        return

    jobs = [
        (
            "programador",
            "💻 Você trabalhou como programador."
        ),
        (
            "entregador",
            "📦 Você fez algumas entregas."
        ),
        (
            "designer",
            "🎨 Você criou uma arte."
        ),
        (
            "mecânico",
            "🔧 Você consertou um carro."
        ),
        (
            "streamer",
            "🎥 Você fez uma live."
        ),
    ]

    job, description = random.choice(
        jobs
    )

    reward = random.randint(
        100,
        600
    )

    add_money(
        guild_id,
        interaction.user.id,
        reward
    )

    account[
        "last_work"
    ] = current

    save_data()

    config = economy_config(
        guild_id
    )

    await interaction.response.send_message(
        (
            f"{description}\n"
            f"💼 Profissão: `{job}`\n"
            f"💰 Você recebeu "
            f"{config['currency_symbol']} `{reward:,}`."
        )
    )


# ============================================================
# ROUBAR
# ============================================================

@economy_group.command(
    name="roubar",
    description="Tenta roubar dinheiro de outro membro."
)
@app_commands.describe(
    membro="Alvo."
)
async def economy_rob(
    interaction,
    membro: discord.Member
):

    if membro.id == interaction.user.id:

        await interaction.response.send_message(
            "❌ Você não pode roubar a si mesmo.",
            ephemeral=True
        )

        return

    if membro.bot:

        await interaction.response.send_message(
            "❌ Você não pode roubar bots.",
            ephemeral=True
        )

        return

    guild_id = interaction.guild.id

    robber = user_finance(
        guild_id,
        interaction.user.id
    )

    current = time.time()

    last_rob = float(
        robber.get(
            "last_rob",
            0
        )
    )

    if current - last_rob < 1800:

        remaining = int(
            1800 - (
                current - last_rob
            )
        )

        await interaction.response.send_message(
            f"⏳ Aguarde `{remaining // 60} min`.",
            ephemeral=True
        )

        return

    robber[
        "last_rob"
    ] = current

    target_balance = get_balance(
        guild_id,
        membro.id
    )

    if target_balance <= 0:

        save_data()

        await interaction.response.send_message(
            "💨 O alvo não possui dinheiro.",
            ephemeral=True
        )

        return

    success = random.random() < 0.45

    if not success:

        fine = min(
            get_balance(
                guild_id,
                interaction.user.id
            ),
            random.randint(
                25,
                100
            )
        )

        remove_money(
            guild_id,
            interaction.user.id,
            fine
        )

        save_data()

        await interaction.response.send_message(
            f"🚨 Você foi pego! Multa: `{fine}` moedas."
        )

        return

    stolen = min(
        target_balance,
        random.randint(
            25,
            max(
                25,
                min(
                    target_balance,
                    500
                )
            )
        )
    )

    remove_money(
        guild_id,
        membro.id,
        stolen
    )

    add_money(
        guild_id,
        interaction.user.id,
        stolen
    )

    save_data()

    await interaction.response.send_message(
        (
            f"🥷 Você roubou "
            f"{economy_config(guild_id)['currency_symbol']} "
            f"`{stolen:,}` de {membro.mention}!"
        )
    )


# ============================================================
# TRANSFERÊNCIAS
# ============================================================

@economy_group.command(
    name="transferencias",
    description="Mostra informações sobre transferências."
)
async def economy_transfers(
    interaction
):

    guild_id = interaction.guild.id

    balance = get_balance(
        guild_id,
        interaction.user.id
    )

    account = user_finance(
        guild_id,
        interaction.user.id
    )

    embed = discord.Embed(
        title="💸 Transferências",
        description=(
            "Use `/economia pagar` para "
            "enviar moedas para outro membro."
        ),
        color=0x57F287
    )

    embed.add_field(
        name="💵 Carteira",
        value=f"`{balance:,}`",
        inline=True
    )

    embed.add_field(
        name="🏦 Banco",
        value=f"`{account.get('bank', 0):,}`",
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# RECOMPENSAS
# ============================================================

@bot.tree.command(
    name="recompensas",
    description="Mostra as recompensas de nível."
)
async def rewards_command(
    interaction
):

    config = economy_config(
        interaction.guild.id
    )

    rewards = config.get(
        "level_rewards",
        {}
    )

    if not rewards:

        await interaction.response.send_message(
            "🎁 Nenhuma recompensa de nível configurada.",
            ephemeral=True
        )

        return

    lines = []

    for level, reward in sorted(
        rewards.items(),
        key=lambda item: int(item[0])
    ):

        lines.append(
            f"🏅 Nível `{level}` → "
            f"🪙 `{reward:,}`"
        )

    embed = discord.Embed(
        title="🎁 Recompensas",
        description="\n".join(
            lines
        ),
        color=0xFEE75C
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# ADMIN — RECOMPENSA DE NÍVEL
# ============================================================

@economy_group.command(
    name="recompensa",
    description="Define uma recompensa de nível."
)
@app_commands.describe(
    nivel="Nível.",
    valor="Quantidade de moedas."
)
async def set_level_reward(
    interaction,
    nivel: app_commands.Range[
        int, 1, 10000
    ],
    valor: app_commands.Range[
        int, 0, 1000000000
    ]
):

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    config = economy_config(
        interaction.guild.id
    )

    config[
        "level_rewards"
    ][
        str(nivel)
    ] = valor

    save_data()

    await interaction.response.send_message(
        (
            f"🎁 Recompensa configurada.\n"
            f"Nível: `{nivel}`\n"
            f"Valor: `{valor:,}`"
        )
    )


# ============================================================
# CONQUISTAS
# ============================================================

def achievements_data(
    guild_id,
    user_id
):

    fun_data = data.setdefault(
        "fun",
        {}
    )

    guild_data = fun_data.setdefault(
        str(guild_id),
        {}
    )

    achievements = guild_data.setdefault(
        "achievements",
        {}
    )

    return achievements.setdefault(
        str(user_id),
        []
    )


@bot.tree.command(
    name="conquista",
    description="Mostra suas conquistas."
)
async def achievement_command(
    interaction
):

    achievements = achievements_data(
        interaction.guild.id,
        interaction.user.id
    )

    if not achievements:

        await interaction.response.send_message(
            "🏆 Você ainda não possui conquistas.",
            ephemeral=True
        )

        return

    embed = discord.Embed(
        title="🏆 Suas conquistas",
        description="\n".join(
            f"🏅 `{item}`"
            for item in achievements
        ),
        color=0xFEE75C
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# STREAK
# ============================================================

@bot.tree.command(
    name="streak",
    description="Mostra seu streak diário."
)
async def streak_command(
    interaction
):

    account = user_finance(
        interaction.guild.id,
        interaction.user.id
    )

    streak = int(
        account.get(
            "streak",
            0
        )
    )

    await interaction.response.send_message(
        (
            f"🔥 Seu streak atual é "
            f"`{streak}` dia(s)."
        )
    )


# ============================================================
# INICIALIZAÇÃO DA ECONOMIA
# ============================================================

def initialize_economy_system():

    for guild in bot.guilds:

        economy_config(
            guild.id
        )

    save_data()

    print(
        "[AURA ECONOMY] Sistema carregado."
    )


# ============================================================
# INTEGRAÇÃO COM O ON_MESSAGE ÚNICO
# ============================================================
#
# NÃO CRIE OUTRO on_message.
#
# Na função on_message FINAL da Parte 8,
# será chamado:
#
#     await process_economy_message(message)
#
# Isso dará XP e moedas pelas mensagens sem
# criar eventos duplicados.
#
# ============================================================

# ============================================================
# AURA BOT — PARTE 6
# VERIFICAÇÃO • BOAS-VINDAS • SAÍDA • AUTOROLE • INVITES
# ============================================================


# ============================================================
# CONFIGURAÇÕES PADRÃO
# ============================================================

VERIFICATION_DEFAULTS = {
    "enabled": False,

    "channel_id": None,
    "role_id": None,
    "remove_role_id": None,

    "message_id": None,

    "button_label": "Verificar",
    "button_emoji": "✅",

    "title": "✅ Verificação",
    "description": (
        "Clique no botão abaixo para verificar "
        "sua conta e liberar o acesso ao servidor."
    ),

    "color": 0x57F287,

    "log_channel_id": None,

    "account_age_days": 0,

    "require_avatar": False,
}


WELCOME_DEFAULTS = {
    "enabled": False,

    "channel_id": None,

    "message": (
        "👋 Seja bem-vindo(a), {user}! "
        "Agora você faz parte da nossa comunidade."
    ),

    "embed_enabled": True,

    "title": "👋 Novo membro!",
    "description": "Bem-vindo(a), {user}!",
    "color": 0x5865F2,

    "thumbnail": True,
    "mention": True,
}


GOODBYE_DEFAULTS = {
    "enabled": False,

    "channel_id": None,

    "message": (
        "👋 {user} saiu do servidor. "
        "Esperamos ver você novamente!"
    ),

    "embed_enabled": True,

    "title": "👋 Membro saiu",
    "description": "{user} saiu do servidor.",
    "color": 0xED4245,
}


AUTOROLE_DEFAULTS = {
    "enabled": False,
    "role_id": None,
}


INVITE_DEFAULTS = {
    "enabled": True,

    "log_channel_id": None,

    "track_fake_invites": True,

    "track_vanity": True,
}


# ============================================================
# CONFIGURAÇÃO DO GUILD
# ============================================================

def community_config(
    guild_id
):

    settings = data.setdefault(
        "guild_settings",
        {}
    )

    guild_data = settings.setdefault(
        str(guild_id),
        {}
    )

    community = guild_data.setdefault(
        "community",
        {}
    )

    community.setdefault(
        "verification",
        {}
    )

    community.setdefault(
        "welcome",
        {}
    )

    community.setdefault(
        "goodbye",
        {}
    )

    community.setdefault(
        "autorole",
        {}
    )

    community.setdefault(
        "invites",
        {}
    )

    merge_defaults(
        community["verification"],
        VERIFICATION_DEFAULTS
    )

    merge_defaults(
        community["welcome"],
        WELCOME_DEFAULTS
    )

    merge_defaults(
        community["goodbye"],
        GOODBYE_DEFAULTS
    )

    merge_defaults(
        community["autorole"],
        AUTOROLE_DEFAULTS
    )

    merge_defaults(
        community["invites"],
        INVITE_DEFAULTS
    )

    return community


def verification_config(
    guild_id
):

    return community_config(
        guild_id
    )["verification"]


def welcome_config(
    guild_id
):

    return community_config(
        guild_id
    )["welcome"]


def goodbye_config(
    guild_id
):

    return community_config(
        guild_id
    )["goodbye"]


def autorole_config(
    guild_id
):

    return community_config(
        guild_id
    )["autorole"]


def invite_config(
    guild_id
):

    return community_config(
        guild_id
    )["invites"]


# ============================================================
# ============================================================
# VERIFICAÇÃO
# ============================================================
# ============================================================


# ============================================================
# VIEW DE VERIFICAÇÃO
# ============================================================

class VerificationView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

        self.add_item(
            VerificationButton()
        )


class VerificationButton(
    discord.ui.Button
):

    def __init__(self):

        super().__init__(
            custom_id="aura:verification",
            label="Verificar",
            emoji="✅",
            style=discord.ButtonStyle.success
        )

    async def callback(
        self,
        interaction
    ):

        guild = interaction.guild

        if not guild:

            await interaction.response.send_message(
                "❌ Este botão só funciona dentro de um servidor.",
                ephemeral=True
            )

            return

        config = verification_config(
            guild.id
        )

        if not config.get(
            "enabled",
            False
        ):

            await interaction.response.send_message(
                "❌ O sistema de verificação está desativado.",
                ephemeral=True
            )

            return

        member = interaction.user

        # ----------------------------------------------------
        # IDADE DA CONTA
        # ----------------------------------------------------

        account_age_days = int(
            config.get(
                "account_age_days",
                0
            )
        )

        if account_age_days > 0:

            account_age = (
                datetime.now(
                    timezone.utc
                )
                - member.created_at
            ).days

            if account_age < account_age_days:

                await interaction.response.send_message(
                    (
                        "❌ Sua conta ainda não possui "
                        f"`{account_age_days}` dias de idade."
                    ),
                    ephemeral=True
                )

                return

        # ----------------------------------------------------
        # AVATAR
        # ----------------------------------------------------

        if config.get(
            "require_avatar",
            False
        ):

            if not member.avatar:

                await interaction.response.send_message(
                    "❌ Você precisa possuir uma foto de perfil para se verificar.",
                    ephemeral=True
                )

                return

        # ----------------------------------------------------
        # CARGO
        # ----------------------------------------------------

        role_id = config.get(
            "role_id"
        )

        if not role_id:

            await interaction.response.send_message(
                "❌ O cargo de verificação ainda não foi configurado.",
                ephemeral=True
            )

            return

        role = guild.get_role(
            int(role_id)
        )

        if not role:

            await interaction.response.send_message(
                "❌ O cargo configurado não existe mais.",
                ephemeral=True
            )

            return

        if role in member.roles:

            await interaction.response.send_message(
                "✅ Você já está verificado!",
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # REMOVER CARGO ANTIGO
        # ----------------------------------------------------

        remove_role_id = config.get(
            "remove_role_id"
        )

        remove_role = None

        if remove_role_id:

            remove_role = guild.get_role(
                int(remove_role_id)
            )

        try:

            if remove_role and remove_role in member.roles:

                await member.remove_roles(
                    remove_role,
                    reason="Aura Verification"
                )

            await member.add_roles(
                role,
                reason="Aura Verification"
            )

            await interaction.response.send_message(
                (
                    "✅ **Verificação concluída!**\n"
                    f"Você recebeu {role.mention}."
                ),
                ephemeral=True
            )

            await send_verification_log(
                guild,
                member,
                True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                (
                    "❌ Não consegui adicionar o cargo.\n"
                    "Verifique a hierarquia dos cargos do bot."
                ),
                ephemeral=True
            )


# ============================================================
# LOG DE VERIFICAÇÃO
# ============================================================

async def send_verification_log(
    guild,
    member,
    success
):

    config = verification_config(
        guild.id
    )

    channel_id = config.get(
        "log_channel_id"
    )

    if not channel_id:
        return

    channel = guild.get_channel(
        int(channel_id)
    )

    if not channel:
        return

    embed = discord.Embed(
        title=(
            "✅ Membro verificado"
            if success
            else "❌ Falha na verificação"
        ),
        description=(
            f"Membro: {member.mention}\n"
            f"ID: `{member.id}`"
        ),
        color=(
            0x57F287
            if success
            else 0xED4245
        ),
        timestamp=datetime.now(
            timezone.utc
        )
    )

    try:

        await channel.send(
            embed=embed
        )

    except Exception:
        pass


# ============================================================
# /VERIFICACAO CONFIG
# ============================================================

@verification_group.command(
    name="config",
    description="Configura o sistema de verificação."
)
@app_commands.describe(
    cargo="Cargo recebido após verificar.",
    cargo_remover="Cargo removido após verificar.",
    idade_conta="Idade mínima da conta em dias.",
    exigir_avatar="Exigir avatar."
)
async def verification_config_command(
    interaction,
    cargo: discord.Role,
    cargo_remover: discord.Role = None,
    idade_conta: app_commands.Range[
        int, 0, 3650
    ] = 0,
    exigir_avatar: bool = False
):

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    config = verification_config(
        interaction.guild.id
    )

    config[
        "role_id"
    ] = cargo.id

    config[
        "remove_role_id"
    ] = (
        cargo_remover.id
        if cargo_remover
        else None
    )

    config[
        "account_age_days"
    ] = idade_conta

    config[
        "require_avatar"
    ] = exigir_avatar

    config[
        "enabled"
    ] = True

    save_data()

    await interaction.response.send_message(
        (
            "✅ Sistema de verificação configurado.\n"
            f"Cargo: {cargo.mention}\n"
            f"Cargo removido: "
            f"{cargo_remover.mention if cargo_remover else 'Nenhum'}\n"
            f"Idade mínima: `{idade_conta}` dias\n"
            f"Exigir avatar: `{exigir_avatar}`"
        )
    )


# ============================================================
# /VERIFICACAO PUBLICAR
# ============================================================

@verification_group.command(
    name="publicar",
    description="Publica o painel de verificação."
)
@app_commands.describe(
    canal="Canal onde o painel será publicado."
)
async def verification_publish(
    interaction,
    canal: discord.TextChannel
):

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    config = verification_config(
        interaction.guild.id
    )

    embed = discord.Embed(
        title=config.get(
            "title",
            "✅ Verificação"
        ),
        description=config.get(
            "description",
            "Clique no botão abaixo para verificar."
        ),
        color=int(
            config.get(
                "color",
                0x57F287
            )
        )
    )

    embed.set_footer(
        text="Aura • Sistema de Verificação"
    )

    await interaction.response.defer(
        ephemeral=True
    )

    try:

        message = await canal.send(
            embed=embed,
            view=VerificationView()
        )

        config[
            "channel_id"
        ] = canal.id

        config[
            "message_id"
        ] = message.id

        config[
            "enabled"
        ] = True

        save_data()

        await interaction.followup.send(
            (
                f"✅ Painel publicado em "
                f"{canal.mention}."
            ),
            ephemeral=True
        )

    except discord.Forbidden:

        await interaction.followup.send(
            "❌ Não tenho permissão para enviar mensagens nesse canal.",
            ephemeral=True
        )


# ============================================================
# /VERIFICACAO STATUS
# ============================================================

@verification_group.command(
    name="status",
    description="Mostra o status da verificação."
)
async def verification_status(
    interaction
):

    config = verification_config(
        interaction.guild.id
    )

    role = None
    channel = None

    if config.get(
        "role_id"
    ):

        role = interaction.guild.get_role(
            int(
                config["role_id"]
            )
        )

    if config.get(
        "channel_id"
    ):

        channel = interaction.guild.get_channel(
            int(
                config["channel_id"]
            )
        )

    embed = discord.Embed(
        title="✅ Status da Verificação",
        color=0x57F287
    )

    embed.add_field(
        name="Estado",
        value=(
            "🟢 Ativo"
            if config.get(
                "enabled",
                False
            )
            else "🔴 Desativado"
        ),
        inline=True
    )

    embed.add_field(
        name="Cargo",
        value=(
            role.mention
            if role
            else "❌ Não configurado"
        ),
        inline=True
    )

    embed.add_field(
        name="Canal",
        value=(
            channel.mention
            if channel
            else "❌ Não configurado"
        ),
        inline=True
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ============================================================
# ============================================================
# BOAS-VINDAS
# ============================================================
# ============================================================


def format_community_message(
    message,
    member
):

    replacements = {
        "{user}": member.mention,
        "{username}": member.name,
        "{displayname}": member.display_name,
        "{server}": member.guild.name,
        "{member_count}": str(
            member.guild.member_count
        ),
        "{id}": str(
            member.id
        )
    }

    for key, value in replacements.items():

        message = message.replace(
            key,
            value
        )

    return message


async def handle_welcome_join(
    member
):

    config = welcome_config(
        member.guild.id
    )

    if not config.get(
        "enabled",
        False
    ):

        return

    channel_id = config.get(
        "channel_id"
    )

    if not channel_id:
        return

    channel = member.guild.get_channel(
        int(channel_id)
    )

    if not channel:
        return

    if config.get(
        "embed_enabled",
        True
    ):

        description = format_community_message(
            config.get(
                "description",
                "Bem-vindo(a), {user}!"
            ),
            member
        )

        embed = discord.Embed(
            title=config.get(
                "title",
                "👋 Novo membro!"
            ),
            description=description,
            color=int(
                config.get(
                    "color",
                    0x5865F2
                )
            ),
            timestamp=datetime.now(
                timezone.utc
            )
        )

        if config.get(
            "thumbnail",
            True
        ):

            embed.set_thumbnail(
                url=member.display_avatar.url
            )

        content = (
            member.mention
            if config.get(
                "mention",
                True
            )
            else None
        )

        try:

            await channel.send(
                content=content,
                embed=embed
            )

        except Exception:
            pass

    else:

        message = format_community_message(
            config.get(
                "message",
                "👋 Seja bem-vindo(a), {user}!"
            ),
            member
        )

        try:

            await channel.send(
                message
            )

        except Exception:
            pass


# ============================================================
# /CONFIG BOAS_VINDAS
# ============================================================

@config_group.command(
    name="boas_vindas",
    description="Configura o sistema de boas-vindas."
)
@app_commands.describe(
    canal="Canal de boas-vindas.",
    ativo="Ativar ou desativar.",
    mensagem="Mensagem.",
    usar_embed="Usar embed."
)
async def config_welcome(
    interaction,
    canal: discord.TextChannel,
    ativo: bool = True,
    mensagem: str = "👋 Seja bem-vindo(a), {user}!",
    usar_embed: bool = True
):

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    config = welcome_config(
        interaction.guild.id
    )

    config[
        "channel_id"
    ] = canal.id

    config[
        "enabled"
    ] = ativo

    config[
        "message"
    ] = mensagem

    config[
        "description"
    ] = mensagem

    config[
        "embed_enabled"
    ] = usar_embed

    save_data()

    await interaction.response.send_message(
        (
            f"👋 Boas-vindas "
            f"{'ativadas' if ativo else 'desativadas'}.\n"
            f"Canal: {canal.mention}"
        )
    )


# ============================================================
# ============================================================
# SAÍDA
# ============================================================
# ============================================================


async def handle_goodbye_leave(
    member
):

    config = goodbye_config(
        member.guild.id
    )

    if not config.get(
        "enabled",
        False
    ):

        return

    channel_id = config.get(
        "channel_id"
    )

    if not channel_id:
        return

    channel = member.guild.get_channel(
        int(channel_id)
    )

    if not channel:
        return

    if config.get(
        "embed_enabled",
        True
    ):

        description = format_community_message(
            config.get(
                "description",
                "{user} saiu do servidor."
            ),
            member
        )

        embed = discord.Embed(
            title=config.get(
                "title",
                "👋 Membro saiu"
            ),
            description=description,
            color=int(
                config.get(
                    "color",
                    0xED4245
                )
            ),
            timestamp=datetime.now(
                timezone.utc
            )
        )

        try:

            await channel.send(
                embed=embed
            )

        except Exception:
            pass

    else:

        message = format_community_message(
            config.get(
                "message",
                "👋 {user} saiu do servidor."
            ),
            member
        )

        try:

            await channel.send(
                message
            )

        except Exception:
            pass


# ============================================================
# /CONFIG SAIDA
# ============================================================

@config_group.command(
    name="saida",
    description="Configura o sistema de saída."
)
@app_commands.describe(
    canal="Canal de saída.",
    ativo="Ativar ou desativar.",
    mensagem="Mensagem.",
    usar_embed="Usar embed."
)
async def config_goodbye(
    interaction,
    canal: discord.TextChannel,
    ativo: bool = True,
    mensagem: str = "👋 {user} saiu do servidor.",
    usar_embed: bool = True
):

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    config = goodbye_config(
        interaction.guild.id
    )

    config[
        "channel_id"
    ] = canal.id

    config[
        "enabled"
    ] = ativo

    config[
        "message"
    ] = mensagem

    config[
        "description"
    ] = mensagem

    config[
        "embed_enabled"
    ] = usar_embed

    save_data()

    await interaction.response.send_message(
        (
            f"👋 Sistema de saída "
            f"{'ativado' if ativo else 'desativado'}.\n"
            f"Canal: {canal.mention}"
        )
    )


# ============================================================
# ============================================================
# AUTOROLE
# ============================================================
# ============================================================


async def apply_autorole(
    member
):

    config = autorole_config(
        member.guild.id
    )

    if not config.get(
        "enabled",
        False
    ):

        return

    role_id = config.get(
        "role_id"
    )

    if not role_id:
        return

    role = member.guild.get_role(
        int(role_id)
    )

    if not role:
        return

    if role in member.roles:
        return

    try:

        await member.add_roles(
            role,
            reason="Aura Autorole"
        )

    except discord.Forbidden:

        print(
            "[AURA AUTOROLE] "
            "Sem permissão para adicionar o cargo."
        )

    except Exception as error:

        print(
            f"[AURA AUTOROLE] {error}"
        )


# ============================================================
# /CONFIG AUTOROLE
# ============================================================

@config_group.command(
    name="autorole",
    description="Configura o cargo automático."
)
@app_commands.describe(
    cargo="Cargo automático.",
    ativo="Ativar ou desativar."
)
async def config_autorole(
    interaction,
    cargo: discord.Role,
    ativo: bool = True
):

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    config = autorole_config(
        interaction.guild.id
    )

    config[
        "role_id"
    ] = cargo.id

    config[
        "enabled"
    ] = ativo

    save_data()

    await interaction.response.send_message(
        (
            f"🤖 Autorole "
            f"{'ativado' if ativo else 'desativado'}.\n"
            f"Cargo: {cargo.mention}"
        )
    )


# ============================================================
# ============================================================
# SISTEMA DE INVITES
# ============================================================
# ============================================================


INVITE_CACHE = {}


async def initialize_invite_cache():

    INVITE_CACHE.clear()

    for guild in bot.guilds:

        try:

            invites = await guild.invites()

            INVITE_CACHE[
                guild.id
            ] = {
                invite.code: {
                    "uses": invite.uses or 0,
                    "inviter_id": (
                        invite.inviter.id
                        if invite.inviter
                        else None
                    )
                }
                for invite in invites
            }

        except Exception as error:

            print(
                f"[AURA INVITES] "
                f"{guild.name}: {error}"
            )


async def detect_used_invite(
    member
):

    guild = member.guild

    if guild.id not in INVITE_CACHE:

        try:

            await initialize_invite_cache()

        except Exception:
            pass

    old_cache = INVITE_CACHE.get(
        guild.id,
        {}
    )

    try:

        invites = await guild.invites()

    except Exception:

        return None

    new_cache = {}

    used_invite = None

    for invite in invites:

        uses = invite.uses or 0

        new_cache[
            invite.code
        ] = {
            "uses": uses,
            "inviter_id": (
                invite.inviter.id
                if invite.inviter
                else None
            )
        }

        old = old_cache.get(
            invite.code
        )

        if old:

            old_uses = int(
                old.get(
                    "uses",
                    0
                )
            )

            if uses > old_uses:

                used_invite = invite

        elif uses > 0:

            # Convite apareceu depois do último cache.
            # Não assumimos automaticamente que foi ele.
            pass

    INVITE_CACHE[
        guild.id
    ] = new_cache

    return used_invite


async def register_invite_join(
    member
):

    config = invite_config(
        member.guild.id
    )

    if not config.get(
        "enabled",
        True
    ):

        return None

    return await detect_used_invite(
        member
    )


async def register_invite_leave(
    member
):

    # Atualiza o cache após saída.
    try:

        invites = await member.guild.invites()

        INVITE_CACHE[
            member.guild.id
        ] = {
            invite.code: {
                "uses": invite.uses or 0,
                "inviter_id": (
                    invite.inviter.id
                    if invite.inviter
                    else None
                )
            }
            for invite in invites
        }

    except Exception:
        pass


async def log_invite_join(
    member,
    invite
):

    if not invite:
        return

    config = invite_config(
        member.guild.id
    )

    channel_id = config.get(
        "log_channel_id"
    )

    if not channel_id:
        return

    channel = member.guild.get_channel(
        int(channel_id)
    )

    if not channel:
        return

    inviter = (
        f"<@{invite.inviter.id}>"
        if invite.inviter
        else "Desconhecido"
    )

    embed = discord.Embed(
        title="📨 Novo convite utilizado",
        description=(
            f"👤 Membro: {member.mention}\n"
            f"👑 Convite: `{invite.code}`\n"
            f"🙋 Criado por: {inviter}\n"
            f"📊 Usos: `{invite.uses or 0}`"
        ),
        color=0x5865F2,
        timestamp=datetime.now(
            timezone.utc
        )
    )

    try:

        await channel.send(
            embed=embed
        )

    except Exception:
        pass


# ============================================================
# /INVITES INFO
# ============================================================

@invite_group.command(
    name="info",
    description="Mostra os convites de um membro."
)
@app_commands.describe(
    membro="Membro."
)
async def invites_info(
    interaction,
    membro: discord.Member = None
):

    target = (
        membro
        or interaction.user
    )

    try:

        invites = await interaction.guild.invites()

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ Não tenho permissão para visualizar convites.",
            ephemeral=True
        )

        return

    user_invites = [
        invite
        for invite in invites
        if invite.inviter
        and invite.inviter.id == target.id
    ]

    total_uses = sum(
        invite.uses or 0
        for invite in user_invites
    )

    if not user_invites:

        await interaction.response.send_message(
            (
                f"📨 {target.mention} "
                "não possui convites registrados."
            ),
            ephemeral=True
        )

        return

    lines = []

    for invite in user_invites[:20]:

        lines.append(
            f"🔗 `{invite.code}` — "
            f"`{invite.uses or 0}` usos"
        )

    embed = discord.Embed(
        title=f"📨 Convites • {target}",
        description="\n".join(lines),
        color=0x5865F2
    )

    embed.add_field(
        name="📊 Total de usos",
        value=f"`{total_uses}`",
        inline=True
    )

    embed.add_field(
        name="🔗 Convites",
        value=f"`{len(user_invites)}`",
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# /INVITES RANKING
# ============================================================

@invite_group.command(
    name="ranking",
    description="Mostra o ranking de convites."
)
async def invites_ranking(
    interaction
):

    try:

        invites = await interaction.guild.invites()

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ Não tenho permissão para visualizar convites.",
            ephemeral=True
        )

        return

    ranking = {}

    for invite in invites:

        if not invite.inviter:
            continue

        inviter_id = invite.inviter.id

        ranking[
            inviter_id
        ] = ranking.get(
            inviter_id,
            0
        ) + (
            invite.uses or 0
        )

    ordered = sorted(
        ranking.items(),
        key=lambda item: item[1],
        reverse=True
    )[:10]

    if not ordered:

        await interaction.response.send_message(
            "📊 Nenhum convite registrado.",
            ephemeral=True
        )

        return

    lines = []

    for index, (
        user_id,
        uses
    ) in enumerate(
        ordered,
        start=1
    ):

        member = interaction.guild.get_member(
            user_id
        )

        name = (
            member.mention
            if member
            else f"<@{user_id}>"
        )

        lines.append(
            f"**{index}.** {name} — "
            f"`{uses}` convites"
        )

    embed = discord.Embed(
        title="🏆 Ranking de Convites",
        description="\n".join(lines),
        color=0xFEE75C
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# /CONFIG INVITES
# ============================================================

@config_group.command(
    name="invites",
    description="Configura o sistema de convites."
)
@app_commands.describe(
    canal="Canal de logs de convites.",
    ativo="Ativar ou desativar."
)
async def config_invites(
    interaction,
    canal: discord.TextChannel = None,
    ativo: bool = True
):

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    config = invite_config(
        interaction.guild.id
    )

    config[
        "enabled"
    ] = ativo

    if canal:

        config[
            "log_channel_id"
        ] = canal.id

    save_data()

    await interaction.response.send_message(
        (
            f"📨 Sistema de convites "
            f"{'ativado' if ativo else 'desativado'}.\n"
            f"Canal de logs: "
            f"{canal.mention if canal else 'não alterado'}"
        )
    )


# ============================================================
# INICIALIZAÇÃO
# ============================================================

def initialize_community_systems():

    for guild in bot.guilds:

        community_config(
            guild.id
        )

    save_data()

    print(
        "[AURA COMMUNITY] "
        "Verificação, welcome, autorole e invites carregados."
    )


# ============================================================
# EVENTOS — NÃO COLOCAR on_member_join AQUI
# ============================================================
#
# A Parte 8 terá o único evento:
#
# @bot.event
# async def on_member_join(member):
#
#     await handle_member_join_security(member)
#     await apply_autorole(member)
#     invite = await register_invite_join(member)
#     if invite:
#         await log_invite_join(member, invite)
#     await handle_welcome_join(member)
#
#
# E também:
#
# @bot.event
# async def on_member_remove(member):
#
#     await register_invite_leave(member)
#     await handle_goodbye_leave(member)
#     await handle_member_leave_security(member)
#
# ============================================================

# ============================================================
# AURA BOT — PARTE 7
# SORTEIOS • SUGESTÕES • DIVERSÃO • UTILIDADES
# ============================================================


# ============================================================
# CONFIGURAÇÕES
# ============================================================

GIVEAWAY_DEFAULTS = {
    "enabled": True,
    "log_channel_id": None,
    "default_color": 0x5865F2,
}

SUGGESTION_DEFAULTS = {
    "enabled": True,
    "channel_id": None,
    "staff_role_id": None,
    "allow_anonymous": False,
    "cooldown": 60,
}

FUN_DEFAULTS = {
    "enabled": True,
}


# ============================================================
# CONFIGURAÇÕES POR SERVIDOR
# ============================================================

def community_extra_config(guild_id):

    settings = data.setdefault(
        "guild_settings",
        {}
    )

    guild_data = settings.setdefault(
        str(guild_id),
        {}
    )

    guild_data.setdefault(
        "community_extra",
        {}
    )

    extra = guild_data[
        "community_extra"
    ]

    extra.setdefault(
        "giveaway",
        {}
    )

    extra.setdefault(
        "suggestion",
        {}
    )

    extra.setdefault(
        "fun",
        {}
    )

    merge_defaults(
        extra["giveaway"],
        GIVEAWAY_DEFAULTS
    )

    merge_defaults(
        extra["suggestion"],
        SUGGESTION_DEFAULTS
    )

    merge_defaults(
        extra["fun"],
        FUN_DEFAULTS
    )

    return extra


def giveaway_config(guild_id):

    return community_extra_config(
        guild_id
    )["giveaway"]


def suggestion_config(guild_id):

    return community_extra_config(
        guild_id
    )["suggestion"]


def fun_config(guild_id):

    return community_extra_config(
        guild_id
    )["fun"]


# ============================================================
# ============================================================
# SORTEIOS
# ============================================================
# ============================================================

def giveaway_data(guild_id):

    giveaways = data.setdefault(
        "giveaways",
        {}
    )

    return giveaways.setdefault(
        str(guild_id),
        {}
    )


def get_giveaway(
    guild_id,
    message_id
):

    return giveaway_data(
        guild_id
    ).get(
        str(message_id)
    )


def save_giveaways():

    save_data()


# ============================================================
# VIEW DO SORTEIO
# ============================================================

class GiveawayView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

        self.add_item(
            GiveawayEnterButton()
        )


class GiveawayEnterButton(
    discord.ui.Button
):

    def __init__(self):

        super().__init__(
            custom_id="aura:giveaway:enter",
            label="Participar",
            emoji="🎉",
            style=discord.ButtonStyle.primary
        )

    async def callback(
        self,
        interaction
    ):

        guild = interaction.guild

        if not guild:

            await interaction.response.send_message(
                "❌ Este botão só funciona em servidores.",
                ephemeral=True
            )

            return

        giveaway = get_giveaway(
            guild.id,
            interaction.message.id
        )

        if not giveaway:

            await interaction.response.send_message(
                "❌ Este sorteio não está mais registrado.",
                ephemeral=True
            )

            return

        if giveaway.get(
            "ended",
            False
        ):

            await interaction.response.send_message(
                "❌ Este sorteio já terminou.",
                ephemeral=True
            )

            return

        user_id = str(
            interaction.user.id
        )

        participants = giveaway.setdefault(
            "participants",
            []
        )

        if user_id in participants:

            participants.remove(
                user_id
            )

            save_giveaways()

            await interaction.response.send_message(
                "❌ Você saiu do sorteio.",
                ephemeral=True
            )

            return

        participants.append(
            user_id
        )

        save_giveaways()

        await interaction.response.send_message(
            "🎉 Você entrou no sorteio!",
            ephemeral=True
        )


# ============================================================
# CRIAR SORTEIO
# ============================================================

@giveaway_group.command(
    name="criar",
    description="Cria um sorteio."
)
@app_commands.describe(
    premio="Prêmio do sorteio.",
    duracao="Duração em minutos.",
    vencedores="Quantidade de vencedores."
)
async def giveaway_create(
    interaction,
    premio: str,
    duracao: app_commands.Range[
        int, 1, 10080
    ],
    vencedores: app_commands.Range[
        int, 1, 20
    ] = 1
):

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    if not giveaway_config(
        interaction.guild.id
    ).get(
        "enabled",
        True
    ):

        await interaction.response.send_message(
            "❌ Os sorteios estão desativados.",
            ephemeral=True
        )

        return

    end_at = (
        datetime.now(
            timezone.utc
        )
        + timedelta(
            minutes=duracao
        )
    )

    embed = discord.Embed(
        title="🎉 SORTEIO",
        description=(
            f"🎁 **Prêmio:** {premio}\n"
            f"🏆 **Vencedores:** `{vencedores}`\n"
            f"⏰ **Termina:** <t:{int(end_at.timestamp())}:R>\n\n"
            "Clique no botão abaixo para participar!"
        ),
        color=int(
            giveaway_config(
                interaction.guild.id
            ).get(
                "default_color",
                0x5865F2
            )
        ),
        timestamp=end_at
    )

    embed.set_footer(
        text="Aura • Sorteios"
    )

    await interaction.response.send_message(
        embed=embed,
        view=GiveawayView()
    )

    message = await interaction.original_response()

    giveaway_data(
        interaction.guild.id
    )[str(message.id)] = {
        "message_id": message.id,
        "channel_id": interaction.channel.id,
        "prize": premio,
        "winners": vencedores,
        "end_at": end_at.isoformat(),
        "participants": [],
        "ended": False,
        "creator_id": interaction.user.id,
    }

    save_giveaways()


# ============================================================
# FINALIZAR SORTEIO
# ============================================================

async def finish_giveaway(
    guild,
    giveaway
):

    if giveaway.get(
        "ended",
        False
    ):
        return

    participants = list(
        giveaway.get(
            "participants",
            []
        )
    )

    winners_count = int(
        giveaway.get(
            "winners",
            1
        )
    )

    if participants:

        selected = random.sample(
            participants,
            min(
                winners_count,
                len(participants)
            )
        )

    else:

        selected = []

    giveaway[
        "ended"
    ] = True

    giveaway[
        "winner_ids"
    ] = selected

    save_giveaways()

    channel = guild.get_channel(
        int(
            giveaway["channel_id"]
        )
    )

    if not channel:
        return

    mentions = []

    for user_id in selected:

        mentions.append(
            f"<@{user_id}>"
        )

    if mentions:

        winner_text = ", ".join(
            mentions
        )

    else:

        winner_text = "Ninguém participou."

    embed = discord.Embed(
        title="🎉 Sorteio encerrado!",
        description=(
            f"🎁 **Prêmio:** "
            f"{giveaway['prize']}\n\n"
            f"🏆 **Vencedores:** {winner_text}"
        ),
        color=0x57F287,
        timestamp=datetime.now(
            timezone.utc
        )
    )

    try:

        await channel.send(
            content=(
                "🎉 " + winner_text
                if mentions
                else None
            ),
            embed=embed
        )

    except Exception:
        pass


# ============================================================
# ENCERRAR SORTEIO
# ============================================================

@giveaway_group.command(
    name="encerrar",
    description="Encerra um sorteio."
)
@app_commands.describe(
    mensagem_id="ID da mensagem do sorteio."
)
async def giveaway_end(
    interaction,
    mensagem_id: str
):

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    giveaway = get_giveaway(
        interaction.guild.id,
        mensagem_id
    )

    if not giveaway:

        await interaction.response.send_message(
            "❌ Sorteio não encontrado.",
            ephemeral=True
        )

        return

    await finish_giveaway(
        interaction.guild,
        giveaway
    )

    await interaction.response.send_message(
        "✅ Sorteio encerrado.",
        ephemeral=True
    )


# ============================================================
# REROLL
# ============================================================

@giveaway_group.command(
    name="reroll",
    description="Sorteia novos vencedores."
)
@app_commands.describe(
    mensagem_id="ID da mensagem do sorteio."
)
async def giveaway_reroll(
    interaction,
    mensagem_id: str
):

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    giveaway = get_giveaway(
        interaction.guild.id,
        mensagem_id
    )

    if not giveaway:

        await interaction.response.send_message(
            "❌ Sorteio não encontrado.",
            ephemeral=True
        )

        return

    participants = list(
        giveaway.get(
            "participants",
            []
        )
    )

    if not participants:

        await interaction.response.send_message(
            "❌ Não existem participantes.",
            ephemeral=True
        )

        return

    winners_count = int(
        giveaway.get(
            "winners",
            1
        )
    )

    winners = random.sample(
        participants,
        min(
            winners_count,
            len(participants)
        )
    )

    mentions = " ".join(
        f"<@{user_id}>"
        for user_id in winners
    )

    await interaction.response.send_message(
        (
            f"🎉 Novo resultado do sorteio "
            f"**{giveaway['prize']}**:\n"
            f"{mentions}"
        )
    )


# ============================================================
# TASK DOS SORTEIOS
# ============================================================

@tasks.loop(seconds=15)
async def giveaway_task():

    now_time = datetime.now(
        timezone.utc
    )

    for guild in bot.guilds:

        guild_giveaways = giveaway_data(
            guild.id
        )

        changed = False

        for giveaway in list(
            guild_giveaways.values()
        ):

            if giveaway.get(
                "ended",
                False
            ):
                continue

            try:

                end_at = datetime.fromisoformat(
                    giveaway["end_at"]
                )

            except Exception:

                continue

            if now_time >= end_at:

                await finish_giveaway(
                    guild,
                    giveaway
                )

                changed = True

        if changed:

            save_giveaways()


# ============================================================
# ============================================================
# SUGESTÕES
# ============================================================
# ============================================================

def suggestion_data(
    guild_id
):

    polls = data.setdefault(
        "polls",
        {}
    )

    guild_data = polls.setdefault(
        str(guild_id),
        {}
    )

    guild_data.setdefault(
        "suggestions",
        {}
    )

    return guild_data[
        "suggestions"
    ]


def get_suggestion(
    guild_id,
    message_id
):

    return suggestion_data(
        guild_id
    ).get(
        str(message_id)
    )


# ============================================================
# VIEW DE SUGESTÃO
# ============================================================

class SuggestionView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

        self.add_item(
            SuggestionUpvoteButton()
        )

        self.add_item(
            SuggestionDownvoteButton()
        )


class SuggestionUpvoteButton(
    discord.ui.Button
):

    def __init__(self):

        super().__init__(
            custom_id="aura:suggestion:up",
            label="Aprovar",
            emoji="👍",
            style=discord.ButtonStyle.success
        )

    async def callback(
        self,
        interaction
    ):

        await vote_suggestion(
            interaction,
            True
        )


class SuggestionDownvoteButton(
    discord.ui.Button
):

    def __init__(self):

        super().__init__(
            custom_id="aura:suggestion:down",
            label="Reprovar",
            emoji="👎",
            style=discord.ButtonStyle.danger
        )

    async def callback(
        self,
        interaction
    ):

        await vote_suggestion(
            interaction,
            False
        )


async def vote_suggestion(
    interaction,
    approve
):

    suggestion = get_suggestion(
        interaction.guild.id,
        interaction.message.id
    )

    if not suggestion:

        await interaction.response.send_message(
            "❌ Sugestão não encontrada.",
            ephemeral=True
        )

        return

    user_id = str(
        interaction.user.id
    )

    upvotes = suggestion.setdefault(
        "upvotes",
        []
    )

    downvotes = suggestion.setdefault(
        "downvotes",
        []
    )

    if user_id in upvotes:

        upvotes.remove(
            user_id
        )

    if user_id in downvotes:

        downvotes.remove(
            user_id
        )

    if approve:

        upvotes.append(
            user_id
        )

    else:

        downvotes.append(
            user_id
        )

    save_data()

    await interaction.response.send_message(
        (
            "👍 Seu voto foi registrado."
            if approve
            else
            "👎 Seu voto foi registrado."
        ),
        ephemeral=True
    )


# ============================================================
# /SUGESTAO ENVIAR
# ============================================================

@suggestion_group.command(
    name="enviar",
    description="Envia uma sugestão."
)
@app_commands.describe(
    sugestao="Texto da sugestão.",
    anonima="Ocultar seu nome."
)
async def suggestion_send(
    interaction,
    sugestao: str,
    anonima: bool = False
):

    config = suggestion_config(
        interaction.guild.id
    )

    if not config.get(
        "enabled",
        True
    ):

        await interaction.response.send_message(
            "❌ O sistema de sugestões está desativado.",
            ephemeral=True
        )

        return

    if (
        anonima
        and not config.get(
            "allow_anonymous",
            False
        )
    ):

        await interaction.response.send_message(
            "❌ Sugestões anônimas estão desativadas.",
            ephemeral=True
        )

        return

    channel_id = config.get(
        "channel_id"
    )

    channel = None

    if channel_id:

        channel = interaction.guild.get_channel(
            int(channel_id)
        )

    if not channel:

        channel = interaction.channel

    author_text = (
        "👤 Anônimo"
        if anonima
        else interaction.user.mention
    )

    embed = discord.Embed(
        title="💡 Nova sugestão",
        description=sugestao,
        color=0x5865F2,
        timestamp=datetime.now(
            timezone.utc
        )
    )

    embed.add_field(
        name="👤 Autor",
        value=author_text,
        inline=False
    )

    embed.set_footer(
        text="Aura • Sistema de Sugestões"
    )

    await interaction.response.defer(
        ephemeral=True
    )

    message = await channel.send(
        embed=embed,
        view=SuggestionView()
    )

    suggestion_data(
        interaction.guild.id
    )[str(message.id)] = {
        "message_id": message.id,
        "channel_id": channel.id,
        "author_id": (
            None
            if anonima
            else interaction.user.id
        ),
        "content": sugestao,
        "anonymous": anonima,
        "upvotes": [],
        "downvotes": [],
        "status": "pending",
        "created_at": now_iso(),
    }

    save_data()

    await interaction.followup.send(
        (
            f"✅ Sua sugestão foi enviada para "
            f"{channel.mention}."
        ),
        ephemeral=True
    )


# ============================================================
# MODERAÇÃO DE SUGESTÕES
# ============================================================

async def update_suggestion_status(
    interaction,
    message_id,
    status,
    emoji
):

    suggestion = get_suggestion(
        interaction.guild.id,
        message_id
    )

    if not suggestion:

        await interaction.response.send_message(
            "❌ Sugestão não encontrada.",
            ephemeral=True
        )

        return

    suggestion[
        "status"
    ] = status

    save_data()

    await interaction.response.send_message(
        f"{emoji} Sugestão marcada como **{status}**.",
        ephemeral=True
    )


@suggestion_group.command(
    name="aprovar",
    description="Aprova uma sugestão."
)
@app_commands.describe(
    mensagem_id="ID da mensagem."
)
async def suggestion_approve(
    interaction,
    mensagem_id: str
):

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    await update_suggestion_status(
        interaction,
        mensagem_id,
        "approved",
        "✅"
    )


@suggestion_group.command(
    name="negar",
    description="Nega uma sugestão."
)
@app_commands.describe(
    mensagem_id="ID da mensagem."
)
async def suggestion_deny(
    interaction,
    mensagem_id: str
):

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    await update_suggestion_status(
        interaction,
        mensagem_id,
        "denied",
        "❌"
    )


@suggestion_group.command(
    name="implementar",
    description="Marca uma sugestão como implementada."
)
@app_commands.describe(
    mensagem_id="ID da mensagem."
)
async def suggestion_implemented(
    interaction,
    mensagem_id: str
):

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    await update_suggestion_status(
        interaction,
        mensagem_id,
        "implemented",
        "🚀"
    )


# ============================================================
# /SUGESTAO CONFIG
# ============================================================

@suggestion_group.command(
    name="config",
    description="Configura o sistema de sugestões."
)
@app_commands.describe(
    canal="Canal das sugestões.",
    cargo_staff="Cargo que pode moderar sugestões.",
    anonimas="Permitir sugestões anônimas.",
    ativo="Ativar o sistema."
)
async def suggestion_config_command(
    interaction,
    canal: discord.TextChannel = None,
    cargo_staff: discord.Role = None,
    anonimas: bool = False,
    ativo: bool = True
):

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    config = suggestion_config(
        interaction.guild.id
    )

    config[
        "enabled"
    ] = ativo

    config[
        "allow_anonymous"
    ] = anonimas

    if canal:

        config[
            "channel_id"
        ] = canal.id

    if cargo_staff:

        config[
            "staff_role_id"
        ] = cargo_staff.id

    save_data()

    await interaction.response.send_message(
        (
            "💡 Configuração de sugestões atualizada.\n"
            f"Estado: `{'Ativo' if ativo else 'Desativado'}`\n"
            f"Canal: "
            f"{canal.mention if canal else 'Não alterado'}\n"
            f"Anônimas: `{anonimas}`"
        )
    )


# ============================================================
# ============================================================
# DIVERSÃO
# ============================================================
# ============================================================


def fun_enabled(
    guild_id
):

    return fun_config(
        guild_id
    ).get(
        "enabled",
        True
    )


# ============================================================
# COINFLIP
# ============================================================

@fun_group.command(
    name="coinflip",
    description="Joga uma moeda."
)
async def fun_coinflip(
    interaction
):

    if not fun_enabled(
        interaction.guild.id
    ):

        await interaction.response.send_message(
            "❌ Diversão está desativada.",
            ephemeral=True
        )

        return

    result = random.choice(
        [
            "Cara 🪙",
            "Coroa 🪙"
        ]
    )

    await interaction.response.send_message(
        f"🪙 A moeda caiu em **{result}**!"
    )


# ============================================================
# DADO
# ============================================================

@fun_group.command(
    name="dado",
    description="Rola um dado."
)
@app_commands.describe(
    lados="Quantidade de lados."
)
async def fun_dado(
    interaction,
    lados: app_commands.Range[
        int, 2, 1000
    ] = 6
):

    result = random.randint(
        1,
        lados
    )

    await interaction.response.send_message(
        (
            f"🎲 {interaction.user.mention} "
            f"rolou um dado de `{lados}` lados "
            f"e tirou **{result}**!"
        )
    )


# ============================================================
# 8BALL
# ============================================================

@fun_group.command(
    name="8ball",
    description="Pergunte algo para a bola mágica."
)
@app_commands.describe(
    pergunta="Sua pergunta."
)
async def fun_8ball(
    interaction,
    pergunta: str
):

    answers = [
        "Sim.",
        "Não.",
        "Talvez.",
        "Com certeza!",
        "Provavelmente.",
        "Não conte com isso.",
        "As chances são boas.",
        "Melhor não perguntar agora.",
        "Definitivamente não.",
        "Definitivamente sim.",
    ]

    result = random.choice(
        answers
    )

    embed = discord.Embed(
        title="🎱 8 Ball",
        color=0x5865F2
    )

    embed.add_field(
        name="❓ Pergunta",
        value=pergunta,
        inline=False
    )

    embed.add_field(
        name="🔮 Resposta",
        value=result,
        inline=False
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# ESCOLHER
# ============================================================

@fun_group.command(
    name="escolher",
    description="Escolhe aleatoriamente uma opção."
)
@app_commands.describe(
    opcoes="Separe as opções usando |."
)
async def fun_choose(
    interaction,
    opcoes: str
):

    options = [
        option.strip()
        for option in opcoes.split("|")
        if option.strip()
    ]

    if len(options) < 2:

        await interaction.response.send_message(
            "❌ Informe pelo menos 2 opções usando `|`.",
            ephemeral=True
        )

        return

    chosen = random.choice(
        options
    )

    await interaction.response.send_message(
        (
            "🎯 Escolhi: "
            f"**{chosen}**"
        )
    )


# ============================================================
# ============================================================
# UTILIDADES
# ============================================================
# ============================================================


# ============================================================
# PING
# ============================================================

@utility_group.command(
    name="ping",
    description="Mostra a latência do Aura."
)
async def util_ping(
    interaction
):

    latency = round(
        bot.latency * 1000
    )

    await interaction.response.send_message(
        f"🏓 Pong! `{latency}ms`"
    )


# ============================================================
# USERINFO
# ============================================================

@utility_group.command(
    name="userinfo",
    description="Mostra informações de um usuário."
)
@app_commands.describe(
    membro="Usuário."
)
async def util_userinfo(
    interaction,
    membro: discord.Member = None
):

    member = (
        membro
        or interaction.user
    )

    embed = discord.Embed(
        title=f"👤 {member}",
        color=member.color.value
        if member.color
        else 0x5865F2
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    embed.add_field(
        name="🆔 ID",
        value=f"`{member.id}`",
        inline=True
    )

    embed.add_field(
        name="📅 Conta criada",
        value=discord.utils.format_dt(
            member.created_at,
            "F"
        ),
        inline=True
    )

    embed.add_field(
        name="📥 Entrou no servidor",
        value=(
            discord.utils.format_dt(
                member.joined_at,
                "F"
            )
            if member.joined_at
            else "Desconhecido"
        ),
        inline=True
    )

    roles = [
        role.mention
        for role in member.roles[1:]
    ]

    role_text = (
        ", ".join(
            roles[-15:]
        )
        if roles
        else "Nenhum"
    )

    embed.add_field(
        name="🎭 Cargos",
        value=role_text,
        inline=False
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# SERVERINFO
# ============================================================

@utility_group.command(
    name="serverinfo",
    description="Mostra informações do servidor."
)
async def util_serverinfo(
    interaction
):

    guild = interaction.guild

    embed = discord.Embed(
        title=f"🏠 {guild.name}",
        color=0x5865F2
    )

    if guild.icon:

        embed.set_thumbnail(
            url=guild.icon.url
        )

    embed.add_field(
        name="🆔 ID",
        value=f"`{guild.id}`",
        inline=True
    )

    embed.add_field(
        name="👥 Membros",
        value=f"`{guild.member_count}`",
        inline=True
    )

    embed.add_field(
        name="💬 Canais",
        value=f"`{len(guild.channels)}`",
        inline=True
    )

    embed.add_field(
        name="🎭 Cargos",
        value=f"`{len(guild.roles)}`",
        inline=True
    )

    embed.add_field(
        name="📅 Criado em",
        value=discord.utils.format_dt(
            guild.created_at,
            "F"
        ),
        inline=True
    )

    embed.add_field(
        name="👑 Dono",
        value=(
            guild.owner.mention
            if guild.owner
            else f"<@{guild.owner_id}>"
        ),
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# AVATAR
# ============================================================

@utility_group.command(
    name="avatar",
    description="Mostra o avatar de um usuário."
)
@app_commands.describe(
    membro="Usuário."
)
async def util_avatar(
    interaction,
    membro: discord.Member = None
):

    member = (
        membro
        or interaction.user
    )

    embed = discord.Embed(
        title=f"🖼️ Avatar de {member}",
        color=0x5865F2
    )

    embed.set_image(
        url=member.display_avatar.url
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# AURA INFO
# ============================================================

@utility_group.command(
    name="aura",
    description="Mostra informações do Aura."
)
async def util_aura(
    interaction
):

    uptime = (
        datetime.now(
            timezone.utc
        )
        - BOT_START_TIME
    )

    guild_count = len(
        bot.guilds
    )

    user_count = sum(
        guild.member_count or 0
        for guild in bot.guilds
    )

    embed = discord.Embed(
        title="⚡ Aura",
        description=(
            "Bot multifuncional para gerenciamento "
            "e diversão da sua comunidade."
        ),
        color=0x5865F2
    )

    embed.add_field(
        name="📦 Versão",
        value=f"`{AURA_VERSION}`",
        inline=True
    )

    embed.add_field(
        name="🏠 Servidores",
        value=f"`{guild_count}`",
        inline=True
    )

    embed.add_field(
        name="👥 Usuários",
        value=f"`{user_count}`",
        inline=True
    )

    embed.add_field(
        name="⏱️ Uptime",
        value=str(
            uptime
        ).split(".")[0],
        inline=True
    )

    embed.add_field(
        name="🏓 Latência",
        value=f"`{round(bot.latency * 1000)}ms`",
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# /MEME
# ============================================================

@bot.tree.command(
    name="meme",
    description="Mostra um meme aleatório."
)
async def meme_command(
    interaction
):

    await interaction.response.defer()

    try:

        async with aiohttp.ClientSession() as session:

            async with session.get(
                "https://meme-api.com/gimme"
            ) as response:

                if response.status != 200:

                    raise RuntimeError(
                        "API de memes indisponível."
                    )

                payload = await response.json()

        title = payload.get(
            "title",
            "Meme"
        )

        image = payload.get(
            "url"
        )

        if not image:

            raise RuntimeError(
                "Imagem não encontrada."
            )

        embed = discord.Embed(
            title=title,
            color=0x5865F2
        )

        embed.set_image(
            url=image
        )

        embed.set_footer(
            text="Aura • Meme"
        )

        await interaction.followup.send(
            embed=embed
        )

    except Exception:

        await interaction.followup.send(
            "❌ Não consegui buscar um meme agora."
        )


# ============================================================
# ============================================================
# VIEWS PERSISTENTES
# ============================================================
# ============================================================

def register_community_persistent_views():

    try:

        bot.add_view(
            GiveawayView()
        )

    except Exception as error:

        print(
            f"[AURA GIVEAWAY VIEW] {error}"
        )

    try:

        bot.add_view(
            SuggestionView()
        )

    except Exception as error:

        print(
            f"[AURA SUGGESTION VIEW] {error}"
        )


# ============================================================
# INICIALIZAÇÃO
# ============================================================

def initialize_community_extra():

    for guild in bot.guilds:

        community_extra_config(
            guild.id
        )

    save_data()

    print(
        "[AURA COMMUNITY EXTRA] "
        "Sorteios, sugestões, diversão e utilidades carregados."
    )


# ============================================================
# PAINEL — SORTEIOS
# ============================================================

async def handle_giveaway_panel_action(
    interaction,
    action
):

    if action == "create":

        await interaction.response.send_message(
            (
                "🎉 Para criar um sorteio, use:\n"
                "`/sorteio criar`"
            ),
            ephemeral=True
        )

        return

    if action == "status":

        config = giveaway_config(
            interaction.guild.id
        )

        await interaction.response.send_message(
            (
                "🎉 **Sorteios**\n\n"
                f"Estado: "
                f"`{'Ativo' if config.get('enabled') else 'Desativado'}`"
            ),
            ephemeral=True
        )

        return

    await interaction.response.send_message(
        "🎉 Use `/sorteio` para administrar os sorteios.",
        ephemeral=True
    )


# ============================================================
# PAINEL — BOAS-VINDAS
# ============================================================

async def handle_welcome_panel_action(
    interaction,
    action
):

    config = welcome_config(
        interaction.guild.id
    )

    if action == "status":

        channel = None

        if config.get(
            "channel_id"
        ):

            channel = interaction.guild.get_channel(
                int(
                    config["channel_id"]
                )
            )

        await interaction.response.send_message(
            (
                "👋 **Boas-vindas**\n\n"
                f"Estado: "
                f"`{'Ativo' if config.get('enabled') else 'Desativado'}`\n"
                f"Canal: "
                f"{channel.mention if channel else 'Não configurado'}"
            ),
            ephemeral=True
        )

        return

    await interaction.response.send_message(
        "👋 Use `/config boas_vindas` para configurar.",
        ephemeral=True
    )


# ============================================================
# PAINEL — VERIFICAÇÃO
# ============================================================

async def handle_verification_panel_action(
    interaction,
    action
):

    config = verification_config(
        interaction.guild.id
    )

    if action == "status":

        role = None
        channel = None

        if config.get(
            "role_id"
        ):

            role = interaction.guild.get_role(
                int(
                    config["role_id"]
                )
            )

        if config.get(
            "channel_id"
        ):

            channel = interaction.guild.get_channel(
                int(
                    config["channel_id"]
                )
            )

        await interaction.response.send_message(
            (
                "✅ **Verificação**\n\n"
                f"Estado: "
                f"`{'Ativo' if config.get('enabled') else 'Desativado'}`\n"
                f"Cargo: "
                f"{role.mention if role else 'Não configurado'}\n"
                f"Canal: "
                f"{channel.mention if channel else 'Não configurado'}"
            ),
            ephemeral=True
        )

        return

    await interaction.response.send_message(
        "✅ Use `/verificacao` para configurar.",
        ephemeral=True
    )


# ============================================================
# PAINEL — LOGS
# ============================================================

async def handle_logs_panel_action(
    interaction,
    action
):

    if action == "status":

        settings = guild_settings(
            interaction.guild.id
        )

        channel_id = settings.get(
            "log_channel_id"
        )

        channel = (
            interaction.guild.get_channel(
                int(channel_id)
            )
            if channel_id
            else None
        )

        await interaction.response.send_message(
            (
                "📋 **Logs**\n\n"
                f"Canal: "
                f"{channel.mention if channel else 'Não configurado'}"
            ),
            ephemeral=True
        )

        return

    await interaction.response.send_message(
        "📋 Use `/config log` para configurar os logs.",
        ephemeral=True
    )


# ============================================================
# PAINEL — CONFIGURAÇÃO
# ============================================================

async def handle_config_panel_action(
    interaction,
    action
):

    if action == "status":

        community = community_config(
            interaction.guild.id
        )

        await interaction.response.send_message(
            (
                "⚙️ **Configuração do servidor**\n\n"
                f"Verificação: "
                f"`{'Ativa' if community['verification'].get('enabled') else 'Desativada'}`\n"
                f"Boas-vindas: "
                f"`{'Ativas' if community['welcome'].get('enabled') else 'Desativadas'}`\n"
                f"Saída: "
                f"`{'Ativa' if community['goodbye'].get('enabled') else 'Desativada'}`\n"
                f"Autorole: "
                f"`{'Ativo' if community['autorole'].get('enabled') else 'Desativado'}`"
            ),
            ephemeral=True
        )

        return

    await interaction.response.send_message(
        (
            "⚙️ Use os comandos `/config` "
            "para alterar as configurações."
        ),
        ephemeral=True
    )


# ============================================================
# INICIALIZAÇÃO SEGURA DOS SISTEMAS
# ============================================================

# Estes comandos são chamados pela Parte 8,
# depois que o bot estiver conectado.
#
# NÃO iniciar tasks aqui manualmente.
#
# A Parte 8 fará:
#
# initialize_community_extra()
# register_community_persistent_views()
# giveaway_task.start()
#
# ============================================================

# ============================================================
# .NoTBot — PARTE A
# COMANDOS GERAIS / USUÁRIO DO CÓDIGO ANTIGO
# ============================================================

@bot.tree.command(
    name="verificar",
    description="Verifica se o bot está online"
)
async def verificar(interaction):
    await interaction.response.send_message(
        f"Online. Latência: {round(bot.latency * 1000)}ms",
        ephemeral=True
    )


@bot.tree.command(
    name="ping",
    description="Mostra a latência do bot"
)
async def ping(interaction):
    await interaction.response.send_message(
        f"🏓 Pong! `{round(bot.latency * 1000)}ms`",
        ephemeral=True
    )


@bot.tree.command(
    name="reiniciar",
    description="Reinicia o processo do bot"
)
async def reiniciar(interaction):
    if interaction.user.id != 770039880964505601:
        await interaction.response.send_message(
            "Você não está autorizado a reiniciar o bot.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        "Reiniciando o bot...",
        ephemeral=True
    )

    await asyncio.sleep(1)

    os.execv(
        sys.executable,
        [sys.executable] + sys.argv
    )


@bot.tree.command(
    name="limpar",
    description="Apaga mensagens do canal"
)
@app_commands.checks.has_permissions(
    manage_messages=True
)
async def limpar(
    interaction,
    quantidade: app_commands.Range[int, 1, 100]
):
    await interaction.response.defer(
        ephemeral=True
    )

    deleted = await interaction.channel.purge(
        limit=quantidade
    )

    await interaction.followup.send(
        f"{len(deleted)} mensagens apagadas.",
        ephemeral=True
    )


@bot.tree.command(
    name="servidor",
    description="Mostra informações do servidor"
)
async def servidor(interaction):
    guild = interaction.guild

    embed = discord.Embed(
        title=guild.name,
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Membros",
        value=str(guild.member_count)
    )

    embed.add_field(
        name="Dono",
        value=(
            guild.owner.mention
            if guild.owner
            else "Indisponível"
        )
    )

    embed.add_field(
        name="Criado em",
        value=discord.utils.format_dt(
            guild.created_at,
            "D"
        )
    )

    if guild.icon:
        embed.set_thumbnail(
            url=guild.icon.url
        )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="usuario",
    description="Mostra informações de um usuário"
)
async def usuario(
    interaction,
    membro: discord.Member
):
    embed = discord.Embed(
        title=f"Perfil de {membro.display_name}",
        color=membro.color
    )

    embed.add_field(
        name="ID",
        value=str(membro.id)
    )

    embed.add_field(
        name="Entrou em",
        value=discord.utils.format_dt(
            membro.joined_at,
            "D"
        )
    )

    embed.set_thumbnail(
        url=membro.display_avatar.url
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="perfil",
    description="Mostra o perfil completo de um membro"
)
async def perfil(
    interaction,
    membro: discord.Member | None = None
):
    membro = membro or interaction.user

    roles = [
        role.mention
        for role in reversed(membro.roles[1:])
    ]

    embed = discord.Embed(
        title=f"Perfil de {membro.display_name}",
        color=membro.color
    )

    embed.set_thumbnail(
        url=membro.display_avatar.url
    )

    embed.add_field(
        name="Usuário",
        value=f"{membro.mention}\n`{membro.id}`",
        inline=False
    )

    embed.add_field(
        name="Conta criada",
        value=discord.utils.format_dt(
            membro.created_at,
            "R"
        )
    )

    embed.add_field(
        name="Entrou no servidor",
        value=discord.utils.format_dt(
            membro.joined_at,
            "R"
        )
    )

    embed.add_field(
        name="Cargos",
        value=" ".join(roles[-10:]) or "Nenhum",
        inline=False
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="icone_servidor",
    description="Exibe o ícone do servidor"
)
async def icone_servidor(interaction):
    if not interaction.guild.icon:
        await interaction.response.send_message(
            "Este servidor não possui ícone.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title=f"Ícone de {interaction.guild.name}",
        color=discord.Color.blurple()
    )

    embed.set_image(
        url=interaction.guild.icon.url
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="rep",
    description="Dá reputação positiva a um membro"
)
async def rep(
    interaction,
    membro: discord.Member
):
    if membro.bot or membro.id == interaction.user.id:
        await interaction.response.send_message(
            "Escolha outro membro que não seja um bot.",
            ephemeral=True
        )
        return

    guild_reputations = data[
        "reputations"
    ].setdefault(
        str(interaction.guild.id),
        {}
    )

    user_reputations = guild_reputations.setdefault(
        str(membro.id),
        {
            "total": 0,
            "given_by": []
        }
    )

    if interaction.user.id in user_reputations["given_by"]:
        await interaction.response.send_message(
            "Você já deu reputação para esse membro.",
            ephemeral=True
        )
        return

    user_reputations["total"] += 1
    user_reputations["given_by"].append(
        interaction.user.id
    )

    save_data()

    await interaction.response.send_message(
        f"⭐ {membro.mention} agora tem "
        f"**{user_reputations['total']}** ponto(s) "
        f"de reputação."
    )


@bot.tree.command(
    name="credits",
    description="Mostra os créditos de um membro"
)
async def credits(
    interaction,
    membro: discord.Member | None = None
):
    membro = membro or interaction.user

    account = wallet(
        interaction.guild.id,
        membro.id
    )

    await interaction.response.send_message(
        f"💰 {membro.mention} possui "
        f"**{format_money(account['wallet'] + account['bank'])}**.",
        ephemeral=membro.id == interaction.user.id
    )


@bot.tree.command(
    name="roll",
    description="Rola um dado"
)
async def roll(
    interaction,
    lados: app_commands.Range[int, 2, 1000] = 6
):
    await interaction.response.send_message(
        f"🎲 {interaction.user.mention} rolou "
        f"**{random.randint(1, lados)}** "
        f"(d{lados})."
    )


@bot.tree.command(
    name="roles",
    description="Lista os cargos do servidor"
)
async def roles(interaction):
    entries = [
        f"{role.mention} — {len(role.members)} membro(s)"
        for role in reversed(
            interaction.guild.roles[1:]
        )
    ]

    await interaction.response.send_message(
        "**Cargos do servidor**\n"
        + (
            "\n".join(entries[:40])
            or "Nenhum cargo."
        ),
        ephemeral=True
    )


@bot.tree.command(
    name="colors",
    description="Lista cargos de cor disponíveis"
)
async def colors(interaction):
    available = [
        role.mention
        for role in interaction.guild.roles
        if role.name.casefold().startswith("cor-")
    ]

    await interaction.response.send_message(
        "**Cores disponíveis**\n"
        + (
            " ".join(available)
            or "Nenhuma. Um administrador pode criar cargos `cor-Nome`."
        ),
        ephemeral=True
    )


@bot.tree.command(
    name="color",
    description="Escolhe um cargo de cor"
)
async def color(
    interaction,
    cargo: discord.Role
):
    if not cargo.name.casefold().startswith("cor-"):
        await interaction.response.send_message(
            "Escolha um cargo cujo nome comece com `cor-`.",
            ephemeral=True
        )
        return

    for current in interaction.user.roles:
        if (
            current.name.casefold().startswith("cor-")
            and current != cargo
        ):
            await interaction.user.remove_roles(
                current,
                reason="Troca de cor do perfil"
            )

    await interaction.user.add_roles(
        cargo,
        reason="Cor escolhida pelo usuário"
    )

    await interaction.response.send_message(
        f"Sua cor agora é {cargo.mention}."
    )


@bot.tree.command(
    name="rank",
    description="Mostra o nível e XP de um membro"
)
async def rank(
    interaction,
    membro: discord.Member | None = None
):
    membro = membro or interaction.user

    record = level_record(
        interaction.guild.id,
        membro.id
    )

    await interaction.response.send_message(
        f"🏅 **Rank de {membro.display_name}**\n"
        f"Nível: **{level_from_xp(record['xp'])}**\n"
        f"XP: **{record['xp']}**\n"
        f"Título: **{record['title'] or 'Sem título'}**"
    )


@bot.tree.command(
    name="top",
    description="Mostra o ranking de XP do servidor"
)
async def top(interaction):
    ranking = sorted(
        guild_levels(
            interaction.guild.id
        ).items(),
        key=lambda item: item[1].get(
            "xp",
            0
        ),
        reverse=True
    )[:10]

    lines = []

    for position, (
        user_id,
        record
    ) in enumerate(
        ranking,
        1
    ):
        member = interaction.guild.get_member(
            int(user_id)
        )

        lines.append(
            f"**{position}.** "
            f"{member.display_name if member else user_id} "
            f"— nível "
            f"{level_from_xp(record.get('xp', 0))} "
            f"({record.get('xp', 0)} XP)"
        )

    await interaction.response.send_message(
        "🏆 **Ranking de XP**\n"
        + (
            "\n".join(lines)
            or "Ainda não há XP registrado."
        )
    )


@bot.tree.command(
    name="title",
    description="Define seu título de perfil"
)
async def title(
    interaction,
    texto: str
):
    level_record(
        interaction.guild.id,
        interaction.user.id
    )["title"] = texto[:80]

    save_data()

    await interaction.response.send_message(
        f"Seu título agora é **{texto[:80]}**.",
        ephemeral=True
    )


@bot.tree.command(
    name="profile",
    description="Mostra o perfil de um membro"
)
async def profile(
    interaction,
    membro: discord.Member | None = None
):
    await perfil.callback(
        interaction,
        membro
    )


@bot.tree.command(
    name="user",
    description="Mostra informações de um usuário"
)
async def user(
    interaction,
    membro: discord.Member | None = None
):
    await usuario.callback(
        interaction,
        membro or interaction.user
    )


@bot.tree.command(
    name="server",
    description="Mostra informações do servidor"
)
async def server(interaction):
    await servidor.callback(
        interaction
    )


@bot.tree.command(
    name="setxp",
    description="Define o XP de um membro"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def setxp(
    interaction,
    membro: discord.Member,
    xp: app_commands.Range[
        int,
        0,
        1000000
    ]
):
    level_record(
        interaction.guild.id,
        membro.id
    )["xp"] = xp

    save_data()

    await interaction.response.send_message(
        f"XP de {membro.mention} definido para **{xp}**.",
        ephemeral=True
    )


@bot.tree.command(
    name="setlevel",
    description="Define o nível de um membro"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def setlevel(
    interaction,
    membro: discord.Member,
    nivel: app_commands.Range[
        int,
        0,
        1000
    ]
):
    level_record(
        interaction.guild.id,
        membro.id
    )["xp"] = nivel * nivel * 100

    save_data()

    await interaction.response.send_message(
        f"Nível de {membro.mention} definido para **{nivel}**.",
        ephemeral=True
    )


@bot.tree.command(
    name="points",
    description="Adiciona pontos de moderação a um membro"
)
@app_commands.checks.has_permissions(
    moderate_members=True
)
async def points(
    interaction,
    membro: discord.Member,
    quantidade: app_commands.Range[
        int,
        1,
        1000000
    ]
):
    level_record(
        interaction.guild.id,
        membro.id
    )["points"] += quantidade

    save_data()

    await interaction.response.send_message(
        f"{membro.mention} recebeu "
        f"**{quantidade}** ponto(s) de moderação.",
        ephemeral=True
    )


@bot.tree.command(
    name="dizer",
    description="Envia uma mensagem pelo bot"
)
@app_commands.checks.has_permissions(
    manage_messages=True
)
async def dizer(
    interaction,
    mensagem: str
):
    await interaction.channel.send(
        mensagem
    )

    await interaction.response.send_message(
        "Mensagem enviada.",
        ephemeral=True
    )

# ============================================================
# .NoTBot — PARTE C
# ECONOMIA ANTIGA + HISTÓRICO
# ============================================================

@economy_group.command(
    name="depositar",
    description="Deposita moedas da carteira no banco"
)
async def economia_depositar(
    interaction: discord.Interaction,
    quantidade: app_commands.Range[int, 1, 1_000_000_000]
):
    account = wallet(
        interaction.guild.id,
        interaction.user.id
    )

    if account["wallet"] < quantidade:
        await interaction.response.send_message(
            "❌ Você não possui moedas suficientes na carteira.",
            ephemeral=True
        )
        return

    account["wallet"] -= quantidade
    account["bank"] += quantidade

    save_data()

    await interaction.response.send_message(
        f"🏦 Você depositou **{format_money(quantidade)}**."
    )


@economy_group.command(
    name="sacar",
    description="Saca moedas do banco"
)
async def economia_sacar(
    interaction: discord.Interaction,
    quantidade: app_commands.Range[int, 1, 1_000_000_000]
):
    account = wallet(
        interaction.guild.id,
        interaction.user.id
    )

    if account["bank"] < quantidade:
        await interaction.response.send_message(
            "❌ Você não possui moedas suficientes no banco.",
            ephemeral=True
        )
        return

    account["bank"] -= quantidade
    account["wallet"] += quantidade

    save_data()

    await interaction.response.send_message(
        f"💵 Você sacou **{format_money(quantidade)}**."
    )


@economy_group.command(
    name="vender",
    description="Vende um item do seu inventário"
)
async def economia_vender(
    interaction: discord.Interaction,
    item: str
):
    guild_data = data.setdefault(
        "finance",
        {}
    ).setdefault(
        str(interaction.guild.id),
        {}
    )

    inventory = guild_data.setdefault(
        "inventory",
        {}
    ).setdefault(
        str(interaction.user.id),
        {}
    )

    item_key = item.casefold()

    found_item = None

    for name in inventory:
        if name.casefold() == item_key:
            found_item = name
            break

    if found_item is None:
        await interaction.response.send_message(
            "❌ Você não possui esse item.",
            ephemeral=True
        )
        return

    quantity = inventory[found_item]

    shop_items = guild_data.setdefault(
        "shop",
        {}
    )

    item_data = shop_items.get(
        found_item,
        {}
    )

    value = int(
        item_data.get(
            "sell_price",
            item_data.get(
                "price",
                0
            ) // 2
        )
    )

    if value <= 0:
        value = 1

    account = wallet(
        interaction.guild.id,
        interaction.user.id
    )

    account["wallet"] += value * quantity

    del inventory[found_item]

    save_data()

    await interaction.response.send_message(
        f"💰 Você vendeu **{quantity}x {found_item}** "
        f"por **{format_money(value * quantity)}**."
    )


@economy_group.command(
    name="trabalho",
    description="Trabalha para ganhar moedas"
)
async def economia_trabalho(
    interaction: discord.Interaction
):
    guild_id = str(
        interaction.guild.id
    )

    user_id = str(
        interaction.user.id
    )

    cooldowns = data.setdefault(
        "work_cooldowns",
        {}
    )

    key = f"{guild_id}:{user_id}"

    current_time = time.time()

    last_work = cooldowns.get(
        key,
        0
    )

    cooldown = 900

    if current_time - last_work < cooldown:
        remaining = int(
            cooldown - (
                current_time - last_work
            )
        )

        minutes = remaining // 60
        seconds = remaining % 60

        await interaction.response.send_message(
            f"⏰ Você ainda precisa esperar "
            f"**{minutes}m {seconds}s**.",
            ephemeral=True
        )
        return

    jobs = [
        "programador",
        "médico",
        "engenheiro",
        "motorista",
        "policial",
        "empresário",
        "designer",
        "streamer"
    ]

    job = random.choice(
        jobs
    )

    reward = random.randint(
        100,
        500
    )

    account = wallet(
        interaction.guild.id,
        interaction.user.id
    )

    account["wallet"] += reward

    cooldowns[key] = current_time

    save_data()

    await interaction.response.send_message(
        f"💼 Você trabalhou como **{job}** "
        f"e recebeu **{format_money(reward)}**!"
    )


@economy_group.command(
    name="roubar",
    description="Tenta roubar moedas de outro membro"
)
async def economia_roubar(
    interaction: discord.Interaction,
    membro: discord.Member
):
    if membro.bot:
        await interaction.response.send_message(
            "❌ Você não pode roubar um bot.",
            ephemeral=True
        )
        return

    if membro.id == interaction.user.id:
        await interaction.response.send_message(
            "❌ Você não pode roubar a si mesmo.",
            ephemeral=True
        )
        return

    guild_id = str(
        interaction.guild.id
    )

    user_id = str(
        interaction.user.id
    )

    cooldowns = data.setdefault(
        "rob_cooldowns",
        {}
    )

    key = f"{guild_id}:{user_id}"

    current_time = time.time()

    last_rob = cooldowns.get(
        key,
        0
    )

    cooldown = 3600

    if current_time - last_rob < cooldown:
        remaining = int(
            cooldown - (
                current_time - last_rob
            )
        )

        await interaction.response.send_message(
            f"⏰ Você precisa esperar "
            f"**{remaining // 60}m**.",
            ephemeral=True
        )
        return

    thief = wallet(
        interaction.guild.id,
        interaction.user.id
    )

    victim = wallet(
        interaction.guild.id,
        membro.id
    )

    cooldowns[key] = current_time

    if victim["wallet"] <= 0:
        save_data()

        await interaction.response.send_message(
            f"🥷 Você tentou roubar {membro.mention}, "
            f"mas ele não tinha dinheiro na carteira."
        )
        return

    success = random.random() < 0.5

    if success:

        amount = random.randint(
            1,
            min(
                victim["wallet"],
                500
            )
        )

        victim["wallet"] -= amount
        thief["wallet"] += amount

        message = (
            f"🥷 Você roubou "
            f"**{format_money(amount)}** "
            f"de {membro.mention}!"
        )

    else:

        fine = min(
            thief["wallet"],
            random.randint(
                25,
                250
            )
        )

        thief["wallet"] -= fine

        message = (
            f"🚨 Você foi pego tentando roubar "
            f"{membro.mention} e perdeu "
            f"**{format_money(fine)}**!"
        )

    save_data()

    await interaction.response.send_message(
        message
    )


@economy_group.command(
    name="transferencias",
    description="Mostra seu histórico de transferências"
)
async def economia_transferencias(
    interaction: discord.Interaction
):
    records = data.setdefault(
        "transfers",
        []
    )

    user_records = [
        record
        for record in records
        if str(record.get("guild_id"))
        == str(interaction.guild.id)
        and (
            str(record.get("from"))
            == str(interaction.user.id)
            or
            str(record.get("to"))
            == str(interaction.user.id)
        )
    ]

    user_records = user_records[-15:]

    if not user_records:
        await interaction.response.send_message(
            "📭 Você ainda não possui transferências.",
            ephemeral=True
        )
        return

    lines = []

    for record in reversed(
        user_records
    ):
        value = int(
            record.get(
                "value",
                0
            )
        )

        sender = str(
            record.get(
                "from"
            )
        )

        receiver = str(
            record.get(
                "to"
            )
        )

        if sender == str(
            interaction.user.id
        ):
            lines.append(
                f"📤 Para <@{receiver}> — "
                f"**{format_money(value)}**"
            )
        else:
            lines.append(
                f"📥 De <@{sender}> — "
                f"**{format_money(value)}**"
            )

    embed = discord.Embed(
        title="💸 Histórico de transferências",
        description="\n".join(lines),
        color=discord.Color.blurple()
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ============================================================
# HISTÓRICO / CONTROLE
# ============================================================

@bot.tree.command(
    name="historico",
    description="Mostra o histórico de ações do bot"
)
@app_commands.checks.has_permissions(
    view_audit_log=True
)
async def historico(
    interaction: discord.Interaction,
    limite: app_commands.Range[int, 1, 50] = 20
):
    guild_logs = data.setdefault(
        "internal_logs",
        {}
    ).setdefault(
        str(interaction.guild.id),
        []
    )

    records = guild_logs[-limite:]

    if not records:
        await interaction.response.send_message(
            "📭 Nenhum registro encontrado.",
            ephemeral=True
        )
        return

    lines = []

    for record in reversed(records):
        timestamp = record.get(
            "timestamp"
        )

        action = record.get(
            "action",
            "Ação"
        )

        details = record.get(
            "details",
            ""
        )

        lines.append(
            f"• **{action}** — {details}\n"
            f"  {timestamp}"
        )

    embed = discord.Embed(
        title="📜 Histórico",
        description="\n\n".join(
            lines
        ),
        color=discord.Color.blurple()
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


@bot.tree.command(
    name="limpar_usuario",
    description="Remove os dados de um usuário do sistema"
)
@app_commands.checks.has_permissions(
    manage_guild=True
)
async def limpar_usuario(
    interaction: discord.Interaction,
    membro: discord.Member
):
    guild_id = str(
        interaction.guild.id
    )

    user_id = str(
        membro.id
    )

    # Economia
    finance = data.get(
        "finance",
        {}
    )

    guild_finance = finance.get(
        guild_id
    )

    if isinstance(
        guild_finance,
        dict
    ):
        for key in (
            "wallets",
            "inventory",
            "users"
        ):
            section = guild_finance.get(
                key
            )

            if isinstance(
                section,
                dict
            ):
                section.pop(
                    user_id,
                    None
                )

    # Níveis
    levels = data.get(
        "levels",
        {}
    )

    if isinstance(
        levels,
        dict
    ):
        guild_levels_data = levels.get(
            guild_id
        )

        if isinstance(
            guild_levels_data,
            dict
        ):
            guild_levels_data.pop(
                user_id,
                None
            )

    # Reputação
    reputations = data.get(
        "reputations",
        {}
    )

    if isinstance(
        reputations,
        dict
    ):
        guild_rep = reputations.get(
            guild_id
        )

        if isinstance(
            guild_rep,
            dict
        ):
            guild_rep.pop(
                user_id,
                None
            )

    # Avisos
    warnings_data = data.get(
        "warnings",
        {}
    )

    if isinstance(
        warnings_data,
        dict
    ):
        guild_warning = warnings_data.get(
            guild_id
        )

        if isinstance(
            guild_warning,
            dict
        ):
            guild_warning.pop(
                user_id,
                None
            )

    save_data()

    await interaction.response.send_message(
        f"🗑️ Os dados de {membro.mention} "
        f"foram removidos.",
        ephemeral=True
    )


@bot.tree.command(
    name="modo_moderacao",
    description="Ativa ou desativa o modo de moderação"
)
@app_commands.checks.has_permissions(
    administrator=True
)
async def modo_moderacao(
    interaction: discord.Interaction,
    ativo: bool
):
    settings = guild_settings(
        interaction.guild.id
    )

    settings[
        "moderation_mode"
    ] = ativo

    save_data()

    status = (
        "ativado"
        if ativo
        else "desativado"
    )

    await interaction.response.send_message(
        f"🛡️ Modo de moderação **{status}**.",
        ephemeral=True
    )

# ============================================================
# .NoTBot — PARTE D
# NÍVEIS / RANKING / RECOMPENSAS / DIVERSÃO
# ============================================================

@bot.tree.command(
    name="level",
    description="Mostra seu nível atual"
)
async def level(
    interaction: discord.Interaction,
    membro: discord.Member | None = None
):
    membro = membro or interaction.user

    record = level_record(
        interaction.guild.id,
        membro.id
    )

    xp = int(record.get("xp", 0))
    nivel = level_from_xp(xp)

    # XP necessário para o próximo nível
    next_level_xp = (nivel + 1) ** 2 * 100

    embed = discord.Embed(
        title=f"📊 Nível de {membro.display_name}",
        color=membro.color
    )

    embed.set_thumbnail(
        url=membro.display_avatar.url
    )

    embed.add_field(
        name="Nível",
        value=f"**{nivel}**",
        inline=True
    )

    embed.add_field(
        name="XP",
        value=f"**{xp:,}**".replace(",", "."),
        inline=True
    )

    embed.add_field(
        name="Próximo nível",
        value=f"**{next_level_xp:,} XP**".replace(",", "."),
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="ranking",
    description="Mostra o ranking geral de XP"
)
async def ranking(
    interaction: discord.Interaction
):
    levels = guild_levels(
        interaction.guild.id
    )

    ordered = sorted(
        levels.items(),
        key=lambda item: int(
            item[1].get("xp", 0)
        ),
        reverse=True
    )

    ordered = ordered[:10]

    if not ordered:
        await interaction.response.send_message(
            "📭 Ainda não há usuários no ranking.",
            ephemeral=True
        )
        return

    lines = []

    medals = [
        "🥇",
        "🥈",
        "🥉"
    ]

    for position, (
        user_id,
        record
    ) in enumerate(
        ordered,
        1
    ):
        member = interaction.guild.get_member(
            int(user_id)
        )

        name = (
            member.display_name
            if member
            else f"Usuário {user_id}"
        )

        xp = int(
            record.get(
                "xp",
                0
            )
        )

        level_value = level_from_xp(
            xp
        )

        prefix = (
            medals[position - 1]
            if position <= 3
            else f"`#{position}`"
        )

        lines.append(
            f"{prefix} **{name}** — "
            f"Nível **{level_value}** "
            f"• {xp:,} XP".replace(",", ".")
        )

    embed = discord.Embed(
        title="🏆 Ranking de XP",
        description="\n".join(lines),
        color=discord.Color.gold()
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="ranking_semanal",
    description="Mostra o ranking semanal de XP"
)
async def ranking_semanal(
    interaction: discord.Interaction
):
    weekly = data.setdefault(
        "weekly_xp",
        {}
    ).setdefault(
        str(interaction.guild.id),
        {}
    )

    ordered = sorted(
        weekly.items(),
        key=lambda item: int(
            item[1].get("xp", 0)
            if isinstance(item[1], dict)
            else item[1]
        ),
        reverse=True
    )[:10]

    if not ordered:
        await interaction.response.send_message(
            "📭 Ainda não há XP semanal registrado.",
            ephemeral=True
        )
        return

    lines = []

    for position, (
        user_id,
        record
    ) in enumerate(
        ordered,
        1
    ):
        if isinstance(
            record,
            dict
        ):
            xp = int(
                record.get(
                    "xp",
                    0
                )
            )
        else:
            xp = int(
                record
            )

        member = interaction.guild.get_member(
            int(user_id)
        )

        name = (
            member.display_name
            if member
            else user_id
        )

        lines.append(
            f"**{position}.** {name} — "
            f"**{xp:,} XP**".replace(",", ".")
        )

    embed = discord.Embed(
        title="📅 Ranking semanal",
        description="\n".join(lines),
        color=discord.Color.blurple()
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="recompensas",
    description="Mostra suas recompensas de nível"
)
async def recompensas(
    interaction: discord.Interaction
):
    record = level_record(
        interaction.guild.id,
        interaction.user.id
    )

    rewards = data.setdefault(
        "level_rewards",
        {}
    ).setdefault(
        str(interaction.guild.id),
        {}
    )

    claimed = record.setdefault(
        "claimed_rewards",
        []
    )

    lines = []

    if not rewards:
        lines.append(
            "Nenhuma recompensa foi configurada."
        )
    else:
        for level_value, reward in sorted(
            rewards.items(),
            key=lambda item: int(item[0])
        ):
            status = (
                "✅ Resgatada"
                if str(level_value) in claimed
                else "🎁 Disponível"
            )

            lines.append(
                f"**Nível {level_value}** — "
                f"{reward} — {status}"
            )

    embed = discord.Embed(
        title="🎁 Recompensas",
        description="\n".join(lines),
        color=discord.Color.green()
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


@bot.tree.command(
    name="conquista",
    description="Mostra suas conquistas"
)
async def conquista(
    interaction: discord.Interaction
):
    achievements = data.setdefault(
        "achievements",
        {}
    ).setdefault(
        str(interaction.guild.id),
        {}
    ).get(
        str(interaction.user.id),
        []
    )

    if not achievements:
        await interaction.response.send_message(
            "🏆 Você ainda não possui conquistas.",
            ephemeral=True
        )
        return

    lines = [
        f"🏅 {achievement}"
        for achievement in achievements
    ]

    embed = discord.Embed(
        title="🏆 Suas conquistas",
        description="\n".join(lines),
        color=discord.Color.gold()
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


@bot.tree.command(
    name="streak",
    description="Mostra sua sequência diária"
)
async def streak(
    interaction: discord.Interaction
):
    streaks = data.setdefault(
        "streaks",
        {}
    ).setdefault(
        str(interaction.guild.id),
        {}
    )

    current = streaks.get(
        str(interaction.user.id),
        {}
    )

    current_streak = int(
        current.get(
            "current",
            0
        )
    )

    best_streak = int(
        current.get(
            "best",
            current_streak
        )
    )

    embed = discord.Embed(
        title="🔥 Sua sequência",
        color=discord.Color.orange()
    )

    embed.add_field(
        name="Atual",
        value=f"**{current_streak} dia(s)**"
    )

    embed.add_field(
        name="Recorde",
        value=f"**{best_streak} dia(s)**"
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ============================================================
# DIVERSÃO
# ============================================================

@fun_group.command(
    name="moeda",
    description="Joga uma moeda"
)
async def diversao_moeda(
    interaction: discord.Interaction
):
    result = random.choice(
        ["Cara", "Coroa"]
    )

    emoji = (
        "🪙"
        if result == "Cara"
        else "🔄"
    )

    await interaction.response.send_message(
        f"{emoji} **{result}!**"
    )


@fun_group.command(
    name="chance",
    description="Calcula uma chance aleatória"
)
async def diversao_chance(
    interaction: discord.Interaction,
    pergunta: str
):
    value = random.randint(
        0,
        100
    )

    await interaction.response.send_message(
        f"🎯 **{pergunta}**\n"
        f"Chance: **{value}%**"
    )


@fun_group.command(
    name="pp",
    description="Calcula um tamanho aleatório"
)
async def diversao_pp(
    interaction: discord.Interaction,
    membro: discord.Member | None = None
):
    membro = membro or interaction.user

    value = random.randint(
        1,
        30
    )

    await interaction.response.send_message(
        f"📏 O PP de {membro.mention} "
        f"mede **{value} cm**."
    )


@fun_group.command(
    name="gay",
    description="Calcula uma porcentagem aleatória"
)
async def diversao_gay(
    interaction: discord.Interaction,
    membro: discord.Member | None = None
):
    membro = membro or interaction.user

    value = random.randint(
        0,
        100
    )

    await interaction.response.send_message(
        f"🌈 {membro.mention} tem "
        f"**{value}%** nessa brincadeira."
    )


@fun_group.command(
    name="casar",
    description="Casa com outro membro"
)
async def diversao_casar(
    interaction: discord.Interaction,
    membro: discord.Member
):
    if membro.bot:
        await interaction.response.send_message(
            "❌ Você não pode casar com um bot.",
            ephemeral=True
        )
        return

    if membro.id == interaction.user.id:
        await interaction.response.send_message(
            "❌ Você não pode casar consigo mesmo.",
            ephemeral=True
        )
        return

    marriages = data.setdefault(
        "marriages",
        {}
    ).setdefault(
        str(interaction.guild.id),
        {}
    )

    user_id = str(
        interaction.user.id
    )

    target_id = str(
        membro.id
    )

    if (
        user_id in marriages
        or target_id in marriages
    ):
        await interaction.response.send_message(
            "💍 Um dos dois já está casado.",
            ephemeral=True
        )
        return

    marriages[user_id] = target_id
    marriages[target_id] = user_id

    save_data()

    await interaction.response.send_message(
        f"💍 {interaction.user.mention} "
        f"e {membro.mention} agora estão casados!"
    )


@fun_group.command(
    name="divorcio",
    description="Termina seu casamento"
)
async def diversao_divorcio(
    interaction: discord.Interaction
):
    marriages = data.setdefault(
        "marriages",
        {}
    ).setdefault(
        str(interaction.guild.id),
        {}
    )

    user_id = str(
        interaction.user.id
    )

    partner_id = marriages.get(
        user_id
    )

    if not partner_id:
        await interaction.response.send_message(
            "💔 Você não está casado.",
            ephemeral=True
        )
        return

    marriages.pop(
        user_id,
        None
    )

    marriages.pop(
        partner_id,
        None
    )

    save_data()

    await interaction.response.send_message(
        "💔 Seu casamento foi encerrado."
    )


@fun_group.command(
    name="casados",
    description="Mostra com quem você está casado"
)
async def diversao_casados(
    interaction: discord.Interaction
):
    marriages = data.setdefault(
        "marriages",
        {}
    ).setdefault(
        str(interaction.guild.id),
        {}
    )

    partner_id = marriages.get(
        str(interaction.user.id)
    )

    if not partner_id:
        await interaction.response.send_message(
            "💔 Você não está casado.",
            ephemeral=True
        )
        return

    partner = interaction.guild.get_member(
        int(partner_id)
    )

    await interaction.response.send_message(
        f"💍 Você é casado(a) com "
        f"{partner.mention if partner else partner_id}."
    )


@fun_group.command(
    name="beijar",
    description="Dá um beijo em alguém"
)
async def diversao_beijar(
    interaction: discord.Interaction,
    membro: discord.Member
):
    await interaction.response.send_message(
        f"💋 {interaction.user.mention} "
        f"deu um beijo em {membro.mention}!"
    )


@fun_group.command(
    name="abracar",
    description="Dá um abraço em alguém"
)
async def diversao_abracar(
    interaction: discord.Interaction,
    membro: discord.Member
):
    await interaction.response.send_message(
        f"🫂 {interaction.user.mention} "
        f"abraçou {membro.mention}!"
    )


@fun_group.command(
    name="carinho",
    description="Demonstra carinho por alguém"
)
async def diversao_carinho(
    interaction: discord.Interaction,
    membro: discord.Member
):
    await interaction.response.send_message(
        f"❤️ {interaction.user.mention} "
        f"mandou carinho para {membro.mention}!"
    )


@fun_group.command(
    name="tapar",
    description="Tapa alguém de brincadeira"
)
async def diversao_tapar(
    interaction: discord.Interaction,
    membro: discord.Member
):
    await interaction.response.send_message(
        f"🖐️ {interaction.user.mention} "
        f"deu um tapa em {membro.mention}!"
    )


@fun_group.command(
    name="ship",
    description="Calcula a compatibilidade entre duas pessoas"
)
async def diversao_ship(
    interaction: discord.Interaction,
    membro1: discord.Member,
    membro2: discord.Member
):
    value = random.randint(
        0,
        100
    )

    if value >= 90:
        message = "💖 Casal perfeito!"
    elif value >= 70:
        message = "💕 Tem química!"
    elif value >= 40:
        message = "💛 Talvez..."
    else:
        message = "💔 Melhor continuarem amigos."

    await interaction.response.send_message(
        f"💘 **Ship**\n"
        f"{membro1.mention} + {membro2.mention}\n"
        f"Compatibilidade: **{value}%**\n"
        f"{message}"
    )

# ============================================================
# .NoTBot — PARTE E
# DIVERSÃO / UTILIDADES / COMUNIDADE
# ============================================================

# ------------------------------------------------------------
# DUelo
# ------------------------------------------------------------

@bot.tree.command(
    name="duelo",
    description="Desafia outro membro para um duelo"
)
async def duelo(
    interaction: discord.Interaction,
    membro: discord.Member
):
    if membro.bot:
        await interaction.response.send_message(
            "❌ Você não pode desafiar um bot.",
            ephemeral=True
        )
        return

    if membro.id == interaction.user.id:
        await interaction.response.send_message(
            "❌ Você não pode desafiar a si mesmo.",
            ephemeral=True
        )
        return

    player_power = random.randint(1, 100)
    target_power = random.randint(1, 100)

    if player_power > target_power:
        winner = interaction.user
        loser = membro
    elif target_power > player_power:
        winner = membro
        loser = interaction.user
    else:
        await interaction.response.send_message(
            f"⚔️ **Empate!**\n"
            f"{interaction.user.mention}: `{player_power}`\n"
            f"{membro.mention}: `{target_power}`"
        )
        return

    await interaction.response.send_message(
        f"⚔️ **DUelo!**\n\n"
        f"{interaction.user.mention}: `{player_power}`\n"
        f"{membro.mention}: `{target_power}`\n\n"
        f"🏆 Vencedor: {winner.mention}\n"
        f"💀 Derrotado: {loser.mention}"
    )


# ------------------------------------------------------------
# ROLETA
# ------------------------------------------------------------

@bot.tree.command(
    name="roleta",
    description="Gira uma roleta"
)
async def roleta(
    interaction: discord.Interaction
):
    result = random.randint(0, 36)

    if result == 0:
        color = "🟢 Verde"
    elif result % 2 == 0:
        color = "⚫ Preto"
    else:
        color = "🔴 Vermelho"

    await interaction.response.send_message(
        f"🎰 **Roleta**\n"
        f"Número: **{result}**\n"
        f"Cor: **{color}**"
    )


# ------------------------------------------------------------
# FORCA
# ------------------------------------------------------------

FORCA_PALAVRAS = [
    "discord",
    "roblox",
    "python",
    "servidor",
    "amizade",
    "computador",
    "internet",
    "programacao",
    "bot",
    "comunidade",
]


@bot.tree.command(
    name="forca",
    description="Inicia uma partida de forca"
)
async def forca(
    interaction: discord.Interaction
):
    palavra = random.choice(
        FORCA_PALAVRAS
    )

    mascara = " ".join(
        "_" for _ in palavra
    )

    await interaction.response.send_message(
        f"🎯 **Jogo da Forca**\n\n"
        f"Palavra: `{mascara}`\n"
        f"Tamanho: **{len(palavra)} letras**\n\n"
        f"💡 Palavra escolhida secretamente."
    )


# ------------------------------------------------------------
# MINIGAME
# ------------------------------------------------------------

@bot.tree.command(
    name="minigame",
    description="Joga um minigame rápido"
)
async def minigame(
    interaction: discord.Interaction
):
    games = [
        "🎯 Acerte o número",
        "🎲 Jogue os dados",
        "🪙 Cara ou coroa",
        "⚔️ Duelo rápido",
        "🎰 Roleta",
    ]

    game = random.choice(
        games
    )

    result = random.choice(
        [
            "Você ganhou!",
            "Você perdeu!",
            "Foi empate!",
        ]
    )

    await interaction.response.send_message(
        f"🎮 **{game}**\n\n"
        f"Resultado: **{result}**"
    )


# ------------------------------------------------------------
# BOT INFO
# ------------------------------------------------------------

@bot.tree.command(
    name="botinfo",
    description="Mostra informações sobre o bot"
)
async def botinfo(
    interaction: discord.Interaction
):
    guilds = len(
        bot.guilds
    )

    users = sum(
        guild.member_count or 0
        for guild in bot.guilds
    )

    uptime = (
        datetime.now(timezone.utc)
        - BOT_START_TIME
    )

    embed = discord.Embed(
        title="🤖 .NoTBot",
        description="Informações do bot",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Versão",
        value=AURA_VERSION,
        inline=True
    )

    embed.add_field(
        name="Servidores",
        value=str(guilds),
        inline=True
    )

    embed.add_field(
        name="Usuários",
        value=str(users),
        inline=True
    )

    embed.add_field(
        name="Latência",
        value=f"{round(bot.latency * 1000)}ms",
        inline=True
    )

    embed.add_field(
        name="Python",
        value=sys.version.split()[0],
        inline=True
    )

    embed.add_field(
        name="Uptime",
        value=str(
            uptime
        ).split(".")[0],
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


# ------------------------------------------------------------
# UPTIME
# ------------------------------------------------------------

@bot.tree.command(
    name="uptime",
    description="Mostra há quanto tempo o bot está online"
)
async def uptime(
    interaction: discord.Interaction
):
    delta = (
        datetime.now(timezone.utc)
        - BOT_START_TIME
    )

    await interaction.response.send_message(
        f"⏱️ O **.NoTBot** está online há "
        f"**{str(delta).split('.')[0]}**."
    )


# ------------------------------------------------------------
# STATUS
# ------------------------------------------------------------

@bot.tree.command(
    name="status",
    description="Mostra o status atual do bot"
)
async def status(
    interaction: discord.Interaction
):
    embed = discord.Embed(
        title="📡 Status do .NoTBot",
        color=discord.Color.green()
    )

    embed.add_field(
        name="Discord",
        value="🟢 Online",
        inline=True
    )

    embed.add_field(
        name="Latência",
        value=f"{round(bot.latency * 1000)}ms",
        inline=True
    )

    embed.add_field(
        name="Servidores",
        value=str(
            len(bot.guilds)
        ),
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


# ------------------------------------------------------------
# COMANDOS
# ------------------------------------------------------------

@bot.tree.command(
    name="comandos",
    description="Mostra os principais comandos do bot"
)
async def comandos(
    interaction: discord.Interaction
):
    embed = discord.Embed(
        title="📚 Comandos do .NoTBot",
        description=(
            "Use `/painel` para acessar "
            "a interface principal do bot."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🛡️ Moderação",
        value=(
            "`/banir` `/expulsar` `/mutar`\n"
            "`/advertir` `/timeout` `/lock`"
        ),
        inline=False
    )

    embed.add_field(
        name="💰 Economia",
        value=(
            "`/economia saldo`\n"
            "`/economia diaria`\n"
            "`/economia pagar`\n"
            "`/economia trabalho`"
        ),
        inline=False
    )

    embed.add_field(
        name="🎮 Diversão",
        value=(
            "`/duelo` `/roleta` `/forca`\n"
            "`/minigame` `/diversao ...`"
        ),
        inline=False
    )

    embed.add_field(
        name="📊 Perfil",
        value=(
            "`/perfil` `/rank` `/ranking`\n"
            "`/level` `/top`"
        ),
        inline=False
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ------------------------------------------------------------
# AVATAR
# ------------------------------------------------------------

@bot.tree.command(
    name="avatar",
    description="Mostra o avatar de um usuário"
)
async def avatar(
    interaction: discord.Interaction,
    membro: discord.Member | None = None
):
    membro = membro or interaction.user

    embed = discord.Embed(
        title=f"Avatar de {membro.display_name}",
        color=membro.color
    )

    embed.set_image(
        url=membro.display_avatar.url
    )

    await interaction.response.send_message(
        embed=embed
    )


# ------------------------------------------------------------
# BANNER
# ------------------------------------------------------------

@bot.tree.command(
    name="banner",
    description="Mostra o banner de um usuário"
)
async def banner(
    interaction: discord.Interaction,
    membro: discord.Member | None = None
):
    membro = membro or interaction.user

    user = await bot.fetch_user(
        membro.id
    )

    if not user.banner:
        await interaction.response.send_message(
            "❌ Esse usuário não possui banner.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title=f"Banner de {membro.display_name}",
        color=membro.color
    )

    embed.set_image(
        url=user.banner.url
    )

    await interaction.response.send_message(
        embed=embed
    )


# ------------------------------------------------------------
# CARGO INFO
# ------------------------------------------------------------

@bot.tree.command(
    name="cargo_info",
    description="Mostra informações de um cargo"
)
async def cargo_info(
    interaction: discord.Interaction,
    cargo: discord.Role
):
    embed = discord.Embed(
        title=f"Cargo: {cargo.name}",
        color=cargo.color
    )

    embed.add_field(
        name="ID",
        value=str(cargo.id)
    )

    embed.add_field(
        name="Membros",
        value=str(
            len(cargo.members)
        )
    )

    embed.add_field(
        name="Posição",
        value=str(
            cargo.position
        )
    )

    embed.add_field(
        name="Menção",
        value=cargo.mention
    )

    await interaction.response.send_message(
        embed=embed
    )


# ------------------------------------------------------------
# CANAL INFO
# ------------------------------------------------------------

@bot.tree.command(
    name="canal_info",
    description="Mostra informações de um canal"
)
async def canal_info(
    interaction: discord.Interaction,
    canal: discord.abc.GuildChannel | None = None
):
    canal = canal or interaction.channel

    embed = discord.Embed(
        title=f"Canal: {canal.name}",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="ID",
        value=str(canal.id)
    )

    embed.add_field(
        name="Tipo",
        value=str(canal.type)
    )

    embed.add_field(
        name="Categoria",
        value=(
            canal.category.mention
            if canal.category
            else "Nenhuma"
        )
    )

    await interaction.response.send_message(
        embed=embed
    )


# ------------------------------------------------------------
# SUGERIR
# ------------------------------------------------------------

@bot.tree.command(
    name="sugerir",
    description="Envia uma sugestão para o servidor"
)
async def sugerir(
    interaction: discord.Interaction,
    sugestao: str
):
    settings = guild_settings(
        interaction.guild.id
    )

    channel_id = settings.get(
        "suggestion_channel_id"
    )

    channel = (
        interaction.guild.get_channel(
            channel_id
        )
        if channel_id
        else None
    )

    embed = discord.Embed(
        title="💡 Nova sugestão",
        description=sugestao,
        color=discord.Color.blurple()
    )

    embed.set_author(
        name=interaction.user.display_name,
        icon_url=interaction.user.display_avatar.url
    )

    embed.set_footer(
        text=f"ID do autor: {interaction.user.id}"
    )

    if channel:
        message = await channel.send(
            embed=embed
        )

        await message.add_reaction("✅")
        await message.add_reaction("❌")

        await interaction.response.send_message(
            "✅ Sua sugestão foi enviada!",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            embed=embed
        )


# ------------------------------------------------------------
# ENQUETE
# ------------------------------------------------------------

@bot.tree.command(
    name="enquete",
    description="Cria uma enquete"
)
@app_commands.checks.has_permissions(
    manage_messages=True
)
async def enquete(
    interaction: discord.Interaction,
    pergunta: str
):
    embed = discord.Embed(
        title="📊 Enquete",
        description=pergunta,
        color=discord.Color.blurple()
    )

    message = await interaction.channel.send(
        embed=embed
    )

    await message.add_reaction("✅")
    await message.add_reaction("❌")

    await interaction.response.send_message(
        "📊 Enquete criada!",
        ephemeral=True
    )


# ------------------------------------------------------------
# LEMBRETE
# ------------------------------------------------------------

@bot.tree.command(
    name="lembrete",
    description="Cria um lembrete"
)
async def lembrete(
    interaction: discord.Interaction,
    minutos: app_commands.Range[int, 1, 10080],
    texto: str
):
    await interaction.response.send_message(
        f"⏰ Lembrete criado para daqui a "
        f"**{minutos} minuto(s)**.",
        ephemeral=True
    )

    async def reminder_task():
        await asyncio.sleep(
            minutos * 60
        )

        try:
            await interaction.user.send(
                f"⏰ **Lembrete:** {texto}"
            )
        except discord.HTTPException:
            pass

    asyncio.create_task(
        reminder_task()
    )

# ============================================================
# PARTE F — COMANDOS ANTIGOS DE DIVERSÃO / MINIGAMES
# ============================================================

# ------------------------------------------------------------
# /duelo
# ------------------------------------------------------------

@bot.tree.command(
    name="duelo",
    description="Desafia outro membro para um duelo"
)
async def duelo(
    interaction: discord.Interaction,
    membro: discord.Member
):
    if membro.bot or membro.id == interaction.user.id:
        await interaction.response.send_message(
            "❌ Escolha outro membro.",
            ephemeral=True
        )
        return

    my_power = random.randint(1, 100)
    target_power = random.randint(1, 100)

    if my_power > target_power:
        result = f"🏆 {interaction.user.mention} venceu!"
    elif target_power > my_power:
        result = f"🏆 {membro.mention} venceu!"
    else:
        result = "🤝 Empate!"

    embed = discord.Embed(
        title="⚔️ Duelo",
        description=(
            f"{interaction.user.mention} **vs** {membro.mention}\n\n"
            f"⚡ {interaction.user.display_name}: `{my_power}`\n"
            f"⚡ {membro.display_name}: `{target_power}`\n\n"
            f"**{result}**"
        ),
        color=discord.Color.blurple()
    )

    await interaction.response.send_message(embed=embed)


# ------------------------------------------------------------
# /roleta
# ------------------------------------------------------------

@bot.tree.command(
    name="roleta",
    description="Escolhe uma opção aleatória"
)
async def roleta(
    interaction: discord.Interaction,
    opcoes: str = "sim,não"
):
    choices = [
        choice.strip()
        for choice in opcoes.split(",")
        if choice.strip()
    ]

    if len(choices) < 2:
        await interaction.response.send_message(
            "❌ Informe pelo menos duas opções separadas por vírgula.\n"
            "Exemplo: `sim,não,talvez`",
            ephemeral=True
        )
        return

    choice = random.choice(choices)

    embed = discord.Embed(
        title="🎰 Roleta",
        description=f"A roleta escolheu:\n\n# **{choice}**",
        color=discord.Color.gold()
    )

    await interaction.response.send_message(embed=embed)


# ------------------------------------------------------------
# /quiz
# ------------------------------------------------------------

QUIZ_QUESTIONS = [
    {
        "question": "Qual planeta é conhecido como Planeta Vermelho?",
        "options": [
            "Marte",
            "Vênus",
            "Júpiter",
            "Saturno"
        ],
        "answer": 0,
    },
    {
        "question": "Quanto é 9 × 9?",
        "options": [
            "72",
            "81",
            "90",
            "99"
        ],
        "answer": 1,
    },
    {
        "question": "Qual é a capital do Brasil?",
        "options": [
            "Recife",
            "São Paulo",
            "Brasília",
            "Rio de Janeiro"
        ],
        "answer": 2,
    },
    {
        "question": "Qual animal é conhecido como rei da selva?",
        "options": [
            "Tigre",
            "Leão",
            "Urso",
            "Lobo"
        ],
        "answer": 1,
    },
    {
        "question": "Qual é o maior planeta do Sistema Solar?",
        "options": [
            "Terra",
            "Marte",
            "Júpiter",
            "Netuno"
        ],
        "answer": 2,
    },
    {
        "question": "Quantos dias existem em uma semana?",
        "options": [
            "5",
            "6",
            "7",
            "8"
        ],
        "answer": 2,
    },
]


class QuizView(discord.ui.View):

    def __init__(self, question):
        super().__init__(timeout=60)

        self.answer = question["answer"]
        self.done = False

        for index, option in enumerate(question["options"]):

            button = discord.ui.Button(
                label=option[:80],
                style=discord.ButtonStyle.primary,
                row=index // 2
            )

            async def callback(
                interaction: discord.Interaction,
                index=index
            ):
                if self.done:
                    await interaction.response.send_message(
                        "❌ Esse quiz já foi respondido.",
                        ephemeral=True
                    )
                    return

                self.done = True

                for child in self.children:
                    child.disabled = True

                if index == self.answer:
                    description = "✅ **Resposta correta!**"
                    color = discord.Color.green()
                else:
                    description = "❌ **Resposta errada!**"
                    color = discord.Color.red()

                embed = discord.Embed(
                    title="🧠 Quiz",
                    description=description,
                    color=color
                )

                await interaction.response.edit_message(
                    embed=embed,
                    view=self
                )

            button.callback = callback
            self.add_item(button)


@bot.tree.command(
    name="quiz",
    description="Responde um quiz rápido"
)
async def quiz(interaction: discord.Interaction):

    question = random.choice(QUIZ_QUESTIONS)

    embed = discord.Embed(
        title="🧠 Quiz",
        description=question["question"],
        color=discord.Color.blurple()
    )

    await interaction.response.send_message(
        embed=embed,
        view=QuizView(question)
    )


# ------------------------------------------------------------
# /forca
# ------------------------------------------------------------

HANGMAN_WORDS = [
    "discord",
    "furious",
    "roblox",
    "python",
    "servidor",
    "bot",
    "ticket",
    "economia",
    "seguranca",
    "comunidade",
]


class HangmanView(discord.ui.View):

    def __init__(self, word):
        super().__init__(timeout=180)

        self.word = word.casefold()
        self.guessed = set()
        self.errors = 0

        self.select = discord.ui.Select(
            placeholder="Escolha uma letra",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(
                    label=letter.upper(),
                    value=letter
                )
                for letter in "abcdefghijklmnopqrstuvwxyz"
            ]
        )

        self.select.callback = self.select_letter
        self.add_item(self.select)

    def display_word(self):

        return " ".join(
            letter.upper()
            if letter in self.guessed
            else "＿"
            for letter in self.word
        )

    async def select_letter(
        self,
        interaction: discord.Interaction
    ):

        letter = self.select.values[0]

        if letter in self.guessed:
            await interaction.response.send_message(
                "❌ Você já tentou essa letra.",
                ephemeral=True
            )
            return

        self.guessed.add(letter)

        if letter not in self.word:
            self.errors += 1

        won = all(
            letter in self.guessed
            for letter in self.word
        )

        lost = self.errors >= 6

        if won or lost:
            for child in self.children:
                child.disabled = True

        if won:

            description = (
                f"🎉 **Você venceu!**\n\n"
                f"Palavra: **{self.word.upper()}**"
            )

            color = discord.Color.green()

        elif lost:

            description = (
                f"💀 **Você perdeu!**\n\n"
                f"A palavra era: **{self.word.upper()}**"
            )

            color = discord.Color.red()

        else:

            description = (
                f"Palavra: **{self.display_word()}**\n\n"
                f"❌ Erros: **{self.errors}/6**"
            )

            color = discord.Color.blurple()

        embed = discord.Embed(
            title="🔤 Forca",
            description=description,
            color=color
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )


@bot.tree.command(
    name="forca",
    description="Joga uma partida de forca"
)
async def forca(interaction: discord.Interaction):

    word = random.choice(HANGMAN_WORDS)

    view = HangmanView(word)

    embed = discord.Embed(
        title="🔤 Forca",
        description=(
            f"Palavra: **{view.display_word()}**\n\n"
            "Escolha uma letra no menu abaixo."
        ),
        color=discord.Color.blurple()
    )

    await interaction.response.send_message(
        embed=embed,
        view=view
    )


# ------------------------------------------------------------
# /minigame
# ------------------------------------------------------------

@bot.tree.command(
    name="minigame",
    description="Joga um minigame rápido"
)
async def minigame(interaction: discord.Interaction):

    game = random.choice(
        (
            "cara ou coroa",
            "dado",
            "roleta"
        )
    )

    if game == "cara ou coroa":

        result = random.choice(
            (
                "🪙 **Cara!**",
                "🪙 **Coroa!**"
            )
        )

    elif game == "dado":

        result = (
            f"🎲 Você tirou "
            f"**{random.randint(1, 6)}**!"
        )

    else:

        result = random.choice(
            (
                "🎰 **Você ganhou!**",
                "🎰 **Você perdeu!**",
                "🎰 **Quase!**",
                "🎰 **JACKPOT!**"
            )
        )

    embed = discord.Embed(
        title="🎮 Minigame",
        description=result,
        color=discord.Color.blurple()
    )

    await interaction.response.send_message(
        embed=embed
    )

# ============================================================
# .NoTBot — PARTE B
# COMANDOS ANTIGOS DE MODERAÇÃO
# ============================================================

@bot.tree.command(
    name="mutar",
    description="Muta um membro pelo tempo informado"
)
@app_commands.checks.has_permissions(manage_roles=True)
async def mutar(
    interaction: discord.Interaction,
    membro: discord.Member,
    minutos: app_commands.Range[int, 1, 10080]
):
    if await refuse_protected_action(
        interaction,
        membro,
        "mute"
    ):
        return

    role = discord.utils.get(
        interaction.guild.roles,
        name="Muted"
    )

    if not role:
        role = await interaction.guild.create_role(
            name="Muted",
            reason="Sistema de mute slash"
        )

        for channel in interaction.guild.channels:
            await channel.set_permissions(
                role,
                send_messages=False
            )

    await membro.add_roles(
        role,
        reason=f"Mute aplicado por {interaction.user}"
    )

    await interaction.response.send_message(
        f"{membro.mention} foi mutado por {minutos} minutos."
    )

    async def unmute_later():
        await asyncio.sleep(minutos * 60)

        if role in membro.roles:
            await membro.remove_roles(
                role,
                reason="Fim do tempo de mute"
            )

    asyncio.create_task(unmute_later())


@bot.tree.command(
    name="desmutar",
    description="Remove o mute de um membro"
)
@app_commands.checks.has_permissions(manage_roles=True)
async def desmutar(
    interaction: discord.Interaction,
    membro: discord.Member
):
    if await refuse_protected_action(
        interaction,
        membro,
        "desmute"
    ):
        return

    role = discord.utils.get(
        interaction.guild.roles,
        name="Muted"
    )

    if role and role in membro.roles:
        await membro.remove_roles(
            role,
            reason=f"Desmute aplicado por {interaction.user}"
        )

        await interaction.response.send_message(
            f"{membro.mention} foi desmutado."
        )
    else:
        await interaction.response.send_message(
            "Esse membro não está mutado.",
            ephemeral=True
        )


@bot.tree.command(
    name="expulsar",
    description="Expulsa um membro do servidor"
)
@app_commands.checks.has_permissions(kick_members=True)
async def expulsar(
    interaction: discord.Interaction,
    membro: discord.Member,
    motivo: str = "Sem motivo informado"
):
    if await refuse_protected_action(
        interaction,
        membro,
        "kick"
    ):
        return

    await membro.kick(
        reason=f"{motivo} | Por {interaction.user}"
    )

    await interaction.response.send_message(
        f"{membro.mention} foi expulso."
    )


@bot.tree.command(
    name="banir",
    description="Bane um membro do servidor"
)
@app_commands.checks.has_permissions(ban_members=True)
async def banir(
    interaction: discord.Interaction,
    membro: discord.Member,
    motivo: str = "Sem motivo informado"
):
    if await refuse_protected_action(
        interaction,
        membro,
        "ban"
    ):
        return

    await membro.ban(
        reason=f"{motivo} | Por {interaction.user}"
    )

    await interaction.response.send_message(
        f"{membro.mention} foi banido."
    )


@bot.tree.command(
    name="desbanir",
    description="Remove o banimento de um usuário"
)
@app_commands.checks.has_permissions(ban_members=True)
async def desbanir(
    interaction: discord.Interaction,
    usuario: discord.User
):
    if is_immune_user(usuario):
        await interaction.response.send_message(
            "Este usuário já possui imunidade contra ações do bot.",
            ephemeral=True
        )
        return

    await interaction.guild.unban(
        usuario,
        reason=f"Desbanido por {interaction.user}"
    )

    await interaction.response.send_message(
        f"{usuario} foi desbanido."
    )


@bot.tree.command(
    name="dar_cargo",
    description="Adiciona um cargo a um membro"
)
@app_commands.checks.has_permissions(manage_roles=True)
async def dar_cargo(
    interaction: discord.Interaction,
    membro: discord.Member,
    cargo: discord.Role
):
    await membro.add_roles(
        cargo,
        reason=f"Cargo dado por {interaction.user}"
    )

    await interaction.response.send_message(
        f"{cargo.mention} foi adicionado a {membro.mention}."
    )


@bot.tree.command(
    name="remover_cargo",
    description="Remove um cargo de um membro"
)
@app_commands.checks.has_permissions(manage_roles=True)
async def remover_cargo(
    interaction: discord.Interaction,
    membro: discord.Member,
    cargo: discord.Role
):
    await membro.remove_roles(
        cargo,
        reason=f"Cargo removido por {interaction.user}"
    )

    await interaction.response.send_message(
        f"{cargo.mention} foi removido de {membro.mention}."
    )


@bot.tree.command(
    name="advertir",
    description="Registra uma advertência para um membro"
)
@app_commands.checks.has_permissions(moderate_members=True)
async def advertir(
    interaction: discord.Interaction,
    membro: discord.Member,
    motivo: str = "Sem motivo informado"
):
    if await refuse_protected_action(
        interaction,
        membro,
        "advertência"
    ):
        return

    total = add_warning(
        interaction.guild.id,
        membro.id,
        interaction.user.id,
        motivo
    )

    save_data()

    await audit_log(
        interaction.guild,
        "moderacao",
        "Membro advertido",
        interaction.user,
        f"Alvo: {membro}; motivo: {motivo}"
    )

    await interaction.response.send_message(
        f"{membro.mention} recebeu uma advertência. "
        f"Total: **{total}**."
    )


@bot.tree.command(
    name="avisos",
    description="Consulta as advertências de um membro"
)
async def avisos(
    interaction: discord.Interaction,
    membro: discord.Member | None = None
):
    membro = membro or interaction.user

    if (
        membro.id != interaction.user.id
        and not interaction.user.guild_permissions.moderate_members
    ):
        await interaction.response.send_message(
            "Você só pode consultar seus próprios avisos.",
            ephemeral=True
        )
        return

    records = guild_warnings(
        interaction.guild.id
    ).get(
        str(membro.id),
        []
    )

    if not records:
        await interaction.response.send_message(
            f"{membro.mention} não possui advertências.",
            ephemeral=True
        )
        return

    lines = [
        f"**{index}.** {record['reason']} — "
        f"<t:{int(datetime.fromisoformat(record['created_at']).timestamp())}:R>"
        for index, record in enumerate(records, 1)
    ]

    await interaction.response.send_message(
        f"**Advertências de {membro.display_name}**\n"
        + "\n".join(lines),
        ephemeral=True
    )


@bot.tree.command(
    name="limpar_avisos",
    description="Remove todas as advertências de um membro"
)
@app_commands.checks.has_permissions(moderate_members=True)
async def limpar_avisos(
    interaction: discord.Interaction,
    membro: discord.Member
):
    removed = len(
        guild_warnings(
            interaction.guild.id
        ).pop(
            str(membro.id),
            []
        )
    )

    save_data()

    await interaction.response.send_message(
        f"{removed} advertência(s) removida(s) "
        f"de {membro.mention}.",
        ephemeral=True
    )


@bot.tree.command(
    name="warnings",
    description="Lista os avisos de um membro"
)
async def warnings(
    interaction: discord.Interaction,
    membro: discord.Member | None = None
):
    await avisos.callback(
        interaction,
        membro
    )


@bot.tree.command(
    name="warn_remove",
    description="Remove um aviso de um membro"
)
@app_commands.checks.has_permissions(moderate_members=True)
async def warn_remove(
    interaction: discord.Interaction,
    membro: discord.Member,
    numero: app_commands.Range[int, 1, 100]
):
    records = guild_warnings(
        interaction.guild.id
    ).get(
        str(membro.id),
        []
    )

    if numero > len(records):
        await interaction.response.send_message(
            "Esse aviso não existe.",
            ephemeral=True
        )
        return

    removed = records.pop(numero - 1)

    if not records:
        guild_warnings(
            interaction.guild.id
        ).pop(
            str(membro.id),
            None
        )

    save_data()

    await interaction.response.send_message(
        f"Aviso removido de {membro.mention}: "
        f"{removed['reason']}",
        ephemeral=True
    )


@bot.tree.command(
    name="timeout",
    description="Coloca um membro em timeout"
)
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(
    interaction: discord.Interaction,
    membro: discord.Member,
    minutos: app_commands.Range[int, 1, 40320],
    motivo: str = "Sem motivo informado"
):
    if await refuse_protected_action(
        interaction,
        membro,
        "timeout"
    ):
        return

    await membro.timeout(
        timedelta(minutes=minutos),
        reason=f"{motivo} | Por {interaction.user}"
    )

    await interaction.response.send_message(
        f"{membro.mention} recebeu timeout "
        f"por {minutos} minuto(s)."
    )


@bot.tree.command(
    name="untimeout",
    description="Remove o timeout de um membro"
)
@app_commands.checks.has_permissions(moderate_members=True)
async def untimeout(
    interaction: discord.Interaction,
    membro: discord.Member
):
    await membro.timeout(
        None,
        reason=f"Timeout removido por {interaction.user}"
    )

    await interaction.response.send_message(
        f"Timeout removido de {membro.mention}."
    )


@bot.tree.command(
    name="setnick",
    description="Altera o apelido de um membro"
)
@app_commands.checks.has_permissions(manage_nicknames=True)
async def setnick(
    interaction: discord.Interaction,
    membro: discord.Member,
    apelido: str | None = None
):
    await membro.edit(
        nick=apelido,
        reason=f"Apelido alterado por {interaction.user}"
    )

    await interaction.response.send_message(
        f"Apelido de {membro.mention} atualizado."
    )


@bot.tree.command(
    name="vkick",
    description="Remove um membro do canal de voz"
)
@app_commands.checks.has_permissions(move_members=True)
async def vkick(
    interaction: discord.Interaction,
    membro: discord.Member
):
    if not membro.voice:
        await interaction.response.send_message(
            "Esse membro não está em um canal de voz.",
            ephemeral=True
        )
        return

    await membro.move_to(
        None,
        reason=f"Removido da voz por {interaction.user}"
    )

    await interaction.response.send_message(
        f"{membro.mention} foi removido do canal de voz."
    )


@bot.tree.command(
    name="move",
    description="Move um membro para um canal de voz"
)
@app_commands.checks.has_permissions(move_members=True)
async def move(
    interaction: discord.Interaction,
    membro: discord.Member,
    canal: discord.VoiceChannel
):
    await membro.move_to(
        canal,
        reason=f"Movido por {interaction.user}"
    )

    await interaction.response.send_message(
        f"{membro.mention} foi movido para {canal.mention}."
    )


@bot.tree.command(
    name="lock",
    description="Bloqueia o canal atual"
)
@app_commands.checks.has_permissions(manage_channels=True)
async def lock(
    interaction: discord.Interaction,
    motivo: str = "Canal bloqueado pela moderação"
):
    await interaction.channel.set_permissions(
        interaction.guild.default_role,
        send_messages=False,
        reason=motivo
    )

    await interaction.response.send_message(
        "🔒 Canal bloqueado."
    )


@bot.tree.command(
    name="unlock",
    description="Desbloqueia o canal atual"
)
@app_commands.checks.has_permissions(manage_channels=True)
async def unlock(
    interaction: discord.Interaction
):
    await interaction.channel.set_permissions(
        interaction.guild.default_role,
        send_messages=None,
        reason=f"Canal desbloqueado por {interaction.user}"
    )

    await interaction.response.send_message(
        "🔓 Canal desbloqueado."
    )


@bot.tree.command(
    name="setcolor",
    description="Altera a cor de um cargo"
)
@app_commands.checks.has_permissions(manage_roles=True)
async def setcolor(
    interaction: discord.Interaction,
    cargo: discord.Role,
    hexadecimal: str
):
    hexadecimal = hexadecimal.replace(
        "#",
        ""
    )

    if not re.fullmatch(
        r"[0-9a-fA-F]{6}",
        hexadecimal
    ):
        await interaction.response.send_message(
            "Use uma cor hexadecimal com 6 caracteres.",
            ephemeral=True
        )
        return

    await cargo.edit(
        color=discord.Colour(
            int(hexadecimal, 16)
        ),
        reason=f"Cor alterada por {interaction.user}"
    )

    await interaction.response.send_message(
        f"Cor de {cargo.mention} atualizada."
    )


@bot.tree.command(
    name="reset",
    description="Zera XP e pontos de um membro ou do servidor"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def reset(
    interaction: discord.Interaction,
    membro: discord.Member | None = None
):
    levels = guild_levels(
        interaction.guild.id
    )

    if membro:
        levels.pop(
            str(membro.id),
            None
        )

        target = membro.mention

    else:
        levels.clear()
        target = "todos os membros"

    save_data()

    await interaction.response.send_message(
        f"XP e pontos zerados para {target}.",
        ephemeral=True
    )
# ============================================================
# AURA BOT — PARTE 8
# INTEGRAÇÃO FINAL • BACKUP • STATUS • EVENTOS • STARTUP
# ============================================================


# ============================================================
# BACKUP
# ============================================================

BACKUP_MAX_FILES = 20


def backup_files():

    BACKUP_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    timestamp = datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_name = (
        f"aura_backup_{timestamp}.json"
    )

    backup_path = (
        BACKUP_DIR / backup_name
    )

    try:

        with backup_path.open(
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2
            )

    except Exception as error:

        print(
            f"[AURA BACKUP] Erro ao criar backup: {error}"
        )

        return None

    backups = sorted(
        BACKUP_DIR.glob(
            "aura_backup_*.json"
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True
    )

    for old_backup in backups[
        BACKUP_MAX_FILES:
    ]:

        try:
            old_backup.unlink()
        except Exception:
            pass

    return backup_path


def create_aura_backup():

    return backup_files()


async def create_aura_backup_async():

    return await asyncio.to_thread(
        backup_files
    )


def restore_aura_backup(
    backup_path
):

    global data

    if not backup_path.exists():

        return False

    try:

        with backup_path.open(
            "r",
            encoding="utf-8"
        ) as file:

            restored = json.load(
                file
            )

        if not isinstance(
            restored,
            dict
        ):

            return False

        data = merge_defaults(
            restored,
            DEFAULT_DATA
        )

        save_data()

        return True

    except Exception as error:

        print(
            f"[AURA BACKUP] Erro ao restaurar: {error}"
        )

        return False


# ============================================================
# ESTATÍSTICAS DO SERVIDOR
# ============================================================

def calculate_guild_statistics(
    guild
):

    text_channels = 0
    voice_channels = 0
    categories = 0

    for channel in guild.channels:

        if isinstance(
            channel,
            discord.TextChannel
        ):

            text_channels += 1

        elif isinstance(
            channel,
            discord.VoiceChannel
        ):

            voice_channels += 1

        elif isinstance(
            channel,
            discord.CategoryChannel
        ):

            categories += 1

    bots_count = sum(
        1
        for member in guild.members
        if member.bot
    )

    humans_count = max(
        0,
        (guild.member_count or 0)
        - bots_count
    )

    return {
        "members": guild.member_count or 0,
        "humans": humans_count,
        "bots": bots_count,
        "text_channels": text_channels,
        "voice_channels": voice_channels,
        "categories": categories,
        "roles": len(guild.roles),
        "emojis": len(guild.emojis),
        "boosts": guild.premium_subscription_count or 0,
    }


# ============================================================
# UPTIME
# ============================================================

def aura_uptime():

    delta = (
        datetime.now(
            timezone.utc
        )
        - BOT_START_TIME
    )

    return str(
        delta
    ).split(
        "."
    )[0]


# ============================================================
# HEALTH
# ============================================================

def aura_health():

    latency = bot.latency

    if latency < 0.150:

        connection = "Excelente"

    elif latency < 0.300:

        connection = "Boa"

    elif latency < 0.600:

        connection = "Instável"

    else:

        connection = "Alta latência"

    return {
        "latency": round(
            latency * 1000
        ),
        "connection": connection,
        "guilds": len(
            bot.guilds
        ),
        "uptime": aura_uptime(),
        "version": AURA_VERSION,
    }


# ============================================================
# MANUTENÇÃO
# ============================================================

def maintenance_enabled(
    guild_id
):

    settings = guild_settings(
        guild_id
    )

    return bool(
        settings.get(
            "maintenance_mode",
            False
        )
    )


def set_maintenance_mode(
    guild_id,
    enabled
):

    settings = guild_settings(
        guild_id
    )

    settings[
        "maintenance_mode"
    ] = bool(
        enabled
    )

    save_data()


# ============================================================
# BACKUP — COMANDOS
# ============================================================

@backup_group.command(
    name="criar",
    description="Cria um backup dos dados do Aura."
)
async def backup_create_command(
    interaction
):

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    await interaction.response.defer(
        ephemeral=True
    )

    path = await create_aura_backup_async()

    if not path:

        await interaction.followup.send(
            "❌ Não foi possível criar o backup.",
            ephemeral=True
        )

        return

    await interaction.followup.send(
        (
            "✅ Backup criado com sucesso!\n"
            f"📦 `{path.name}`"
        ),
        ephemeral=True
    )


@backup_group.command(
    name="listar",
    description="Lista os backups disponíveis."
)
async def backup_list_command(
    interaction
):

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    BACKUP_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    backups = sorted(
        BACKUP_DIR.glob(
            "aura_backup_*.json"
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True
    )

    if not backups:

        await interaction.response.send_message(
            "📦 Nenhum backup encontrado.",
            ephemeral=True
        )

        return

    lines = []

    for index, path in enumerate(
        backups[:20],
        start=1
    ):

        size = path.stat().st_size

        lines.append(
            f"`{index}.` `{path.name}` — `{size:,} bytes`"
        )

    embed = discord.Embed(
        title="📦 Backups do Aura",
        description="\n".join(
            lines
        ),
        color=0x5865F2
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


@backup_group.command(
    name="restaurar",
    description="Restaura um backup."
)
@app_commands.describe(
    nome="Nome exato do arquivo de backup."
)
async def backup_restore_command(
    interaction,
    nome: str
):

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    safe_filename = Path(
        nome
    ).name

    if safe_filename != nome:

        await interaction.response.send_message(
            "❌ Nome de backup inválido.",
            ephemeral=True
        )

        return

    path = (
        BACKUP_DIR / safe_filename
    )

    if not path.exists():

        await interaction.response.send_message(
            "❌ Backup não encontrado.",
            ephemeral=True
        )

        return

    current_backup = await create_aura_backup_async()

    if not current_backup:

        await interaction.response.send_message(
            "❌ Não foi possível criar um backup de segurança antes da restauração.",
            ephemeral=True
        )

        return

    success = restore_aura_backup(
        path
    )

    if not success:

        await interaction.response.send_message(
            "❌ Não foi possível restaurar o backup.",
            ephemeral=True
        )

        return

    await interaction.response.send_message(
        (
            "✅ Backup restaurado com sucesso.\n"
            "⚠️ Algumas configurações podem exigir "
            "uma reinicialização do bot."
        ),
        ephemeral=True
    )


# ============================================================
# UTIL — STATS
# ============================================================

@utility_group.command(
    name="stats",
    description="Mostra estatísticas do servidor."
)
async def util_stats(
    interaction
):

    guild = interaction.guild

    stats = calculate_guild_statistics(
        guild
    )

    embed = discord.Embed(
        title=f"📊 Estatísticas — {guild.name}",
        color=0x5865F2
    )

    embed.add_field(
        name="👥 Membros",
        value=f"`{stats['members']}`",
        inline=True
    )

    embed.add_field(
        name="👤 Humanos",
        value=f"`{stats['humans']}`",
        inline=True
    )

    embed.add_field(
        name="🤖 Bots",
        value=f"`{stats['bots']}`",
        inline=True
    )

    embed.add_field(
        name="💬 Canais de texto",
        value=f"`{stats['text_channels']}`",
        inline=True
    )

    embed.add_field(
        name="🔊 Canais de voz",
        value=f"`{stats['voice_channels']}`",
        inline=True
    )

    embed.add_field(
        name="📁 Categorias",
        value=f"`{stats['categories']}`",
        inline=True
    )

    embed.add_field(
        name="🎭 Cargos",
        value=f"`{stats['roles']}`",
        inline=True
    )

    embed.add_field(
        name="😀 Emojis",
        value=f"`{stats['emojis']}`",
        inline=True
    )

    embed.add_field(
        name="🚀 Boosts",
        value=f"`{stats['boosts']}`",
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# UTIL — HEALTH
# ============================================================

@utility_group.command(
    name="health",
    description="Mostra a saúde do Aura."
)
async def util_health(
    interaction
):

    health = aura_health()

    embed = discord.Embed(
        title="💚 Aura Health",
        color=0x57F287
    )

    embed.add_field(
        name="🏓 Latência",
        value=f"`{health['latency']}ms`",
        inline=True
    )

    embed.add_field(
        name="📡 Conexão",
        value=health["connection"],
        inline=True
    )

    embed.add_field(
        name="🏠 Servidores",
        value=f"`{health['guilds']}`",
        inline=True
    )

    embed.add_field(
        name="⏱️ Uptime",
        value=f"`{health['uptime']}`",
        inline=False
    )

    embed.add_field(
        name="📦 Versão",
        value=f"`{health['version']}`",
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# UTIL — STATUS
# ============================================================

@utility_group.command(
    name="status",
    description="Mostra o status atual do Aura."
)
async def util_status(
    interaction
):

    health = aura_health()

    embed = discord.Embed(
        title="⚡ Status do Aura",
        color=0x5865F2
    )

    embed.description = (
        "🟢 **Online e operacional**"
    )

    embed.add_field(
        name="🏓 Ping",
        value=f"`{health['latency']}ms`",
        inline=True
    )

    embed.add_field(
        name="🏠 Servidores",
        value=f"`{health['guilds']}`",
        inline=True
    )

    embed.add_field(
        name="⏱️ Uptime",
        value=f"`{health['uptime']}`",
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# CONFIG — MANUTENÇÃO
# ============================================================

@config_group.command(
    name="manutencao",
    description="Ativa ou desativa o modo manutenção."
)
@app_commands.describe(
    ativo="Ativar ou desativar."
)
async def config_maintenance(
    interaction,
    ativo: bool
):

    if not can_use_admin_command(
        interaction
    ):

        await interaction.response.send_message(
            "❌ Você não possui permissão.",
            ephemeral=True
        )

        return

    set_maintenance_mode(
        interaction.guild.id,
        ativo
    )

    await interaction.response.send_message(
        (
            "🔧 Modo manutenção "
            f"`{'ativado' if ativo else 'desativado'}`."
        )
    )


# ============================================================
# CONFIG — SINCRONIZAR
# ============================================================

@config_group.command(
    name="sincronizar",
    description="Sincroniza os comandos do Aura."
)
async def config_sync(
    interaction
):

    if not is_immune_user(
        interaction.user.id
    ):

        if not interaction.user.guild_permissions.administrator:

            await interaction.response.send_message(
                "❌ Apenas administradores podem sincronizar os comandos.",
                ephemeral=True
            )

            return

    await interaction.response.defer(
        ephemeral=True
    )

    try:

        synced = await bot.tree.sync()

        await interaction.followup.send(
            (
                f"✅ **{len(synced)} comandos** "
                "sincronizados com sucesso."
            ),
            ephemeral=True
        )

    except Exception as error:

        await interaction.followup.send(
            (
                "❌ Erro ao sincronizar:\n"
                f"`{error}`"
            ),
            ephemeral=True
        )


# ============================================================
# EVENTO — MEMBER JOIN
# ============================================================

@bot.event
async def on_member_join(
    member
):

    try:

        await handle_member_join_security(
            member
        )

    except Exception as error:

        print(
            f"[AURA JOIN SECURITY] {error}"
        )

    try:

        await apply_autorole(
            member
        )

    except Exception as error:

        print(
            f"[AURA AUTOROLE] {error}"
        )

    try:

        invite = await register_invite_join(
            member
        )

        if invite:

            await log_invite_join(
                member,
                invite
            )

    except Exception as error:

        print(
            f"[AURA INVITES JOIN] {error}"
        )

    try:

        await handle_welcome_join(
            member
        )

    except Exception as error:

        print(
            f"[AURA WELCOME] {error}"
        )


# ============================================================
# EVENTO — MEMBER REMOVE
# ============================================================

@bot.event
async def on_member_remove(
    member
):

    try:

        await register_invite_leave(
            member
        )

    except Exception as error:

        print(
            f"[AURA INVITES LEAVE] {error}"
        )

    try:

        await handle_goodbye_leave(
            member
        )

    except Exception as error:

        print(
            f"[AURA GOODBYE] {error}"
        )

    try:

        await handle_member_leave_security(
            member
        )

    except Exception as error:

        print(
            f"[AURA LEAVE SECURITY] {error}"
        )


# ============================================================
# EVENTO — MESSAGE
# ============================================================

@bot.event
async def on_message(
    message
):

    if message.author.bot:

        return

    # --------------------------------------------------------
    # AUTOBOT / AUTOMOD
    # --------------------------------------------------------

    try:

        blocked = await process_automod_v2(
            message
        )

        if blocked:

            return

    except Exception as error:

        print(
            f"[AURA AUTOMOD] {error}"
        )

    # --------------------------------------------------------
    # ATIVIDADE DE TICKET
    # --------------------------------------------------------

    try:

        await update_ticket_activity(
            message
        )

    except Exception as error:

        print(
            f"[AURA TICKET ACTIVITY] {error}"
        )

    # --------------------------------------------------------
    # XP / ECONOMIA
    # --------------------------------------------------------

    try:

        await process_economy_message(
            message
        )

    except Exception as error:

        print(
            f"[AURA ECONOMY MESSAGE] {error}"
        )

    # --------------------------------------------------------
    # PREFIX COMMANDS
    # --------------------------------------------------------

    try:

        await bot.process_commands(
            message
        )

    except Exception as error:

        print(
            f"[AURA PREFIX COMMAND] {error}"
        )


# ============================================================
# EVENTO — READY
# ============================================================

@bot.event
async def on_ready():

    print(
        "=================================================="
    )

    print(
        f"⚡ AURA ONLINE — {bot.user}"
    )

    print(
        f"📦 Versão: {AURA_VERSION}"
    )

    print(
        f"🏠 Servidores: {len(bot.guilds)}"
    )

    print(
        f"🏓 Ping: {round(bot.latency * 1000)}ms"
    )

    print(
        "=================================================="
    )


# ============================================================
# ERRO GLOBAL DE EVENTOS
# ============================================================

@bot.event
async def on_error(
    event,
    *args,
    **kwargs
):

    print(
        f"[AURA EVENT ERROR] Evento: {event}"
    )

    traceback.print_exc()


# ============================================================
# ERROS DOS SLASH COMMANDS
# ============================================================

@bot.tree.error
async def on_app_command_error(
    interaction,
    error
):

    original_error = error

    if isinstance(
        error,
        app_commands.CommandInvokeError
    ):

        original_error = error.original

    print(
        "[AURA COMMAND ERROR]",
        repr(original_error)
    )

    traceback.print_exception(
        type(original_error),
        original_error,
        original_error.__traceback__
    )

    try:

        message = (
            "❌ Ocorreu um erro ao executar este comando."
        )

        if isinstance(
            original_error,
            app_commands.MissingPermissions
        ):

            message = (
                "❌ Você não possui as permissões necessárias."
            )

        elif isinstance(
            original_error,
            app_commands.CheckFailure
        ):

            message = (
                "❌ Você não pode usar este comando."
            )

        elif isinstance(
            original_error,
            app_commands.CommandOnCooldown
        ):

            message = (
                "⏳ Este comando está em cooldown."
            )

        if interaction.response.is_done():

            await interaction.followup.send(
                message,
                ephemeral=True
            )

        else:

            await interaction.response.send_message(
                message,
                ephemeral=True
            )

    except Exception as send_error:

        print(
            f"[AURA ERROR HANDLER] {send_error}"
        )


# ============================================================
# TASK DE BACKUP AUTOMÁTICO
# ============================================================

@tasks.loop(
    minutes=30
)
async def automatic_backup_task():

    try:

        path = await create_aura_backup_async()

        if path:

            print(
                f"[AURA BACKUP] Backup automático: {path.name}"
            )

    except Exception as error:

        print(
            f"[AURA AUTO BACKUP] {error}"
        )


# ============================================================
# INICIALIZAÇÃO FINAL
# ============================================================

async def initialize_final_systems():

    # --------------------------------------------------------
    # DADOS
    # --------------------------------------------------------

    try:

        initialize_data()

    except Exception as error:

        print(
            f"[AURA DATA] {error}"
        )

    # --------------------------------------------------------
    # COMUNIDADE
    # --------------------------------------------------------

    try:

        initialize_community_systems()

    except Exception as error:

        print(
            f"[AURA COMMUNITY] {error}"
        )

    # --------------------------------------------------------
    # SORTEIOS / SUGESTÕES
    # --------------------------------------------------------

    try:

        initialize_community_extra()

    except Exception as error:

        print(
            f"[AURA COMMUNITY EXTRA] {error}"
        )

    # --------------------------------------------------------
    # TICKET
    # --------------------------------------------------------

    try:

        await initialize_ticket_system()

    except Exception as error:

        print(
            f"[AURA TICKETS] {error}"
        )

    # --------------------------------------------------------
    # VIEWS PERSISTENTES
    # --------------------------------------------------------

    try:

        register_ticket_persistent_views()

    except Exception as error:

        print(
            f"[AURA TICKET VIEWS] {error}"
        )

    try:

        register_community_persistent_views()

    except Exception as error:

        print(
            f"[AURA COMMUNITY VIEWS] {error}"
        )

    # --------------------------------------------------------
    # INVITES
    # --------------------------------------------------------

    try:

        await initialize_invite_cache()

    except Exception as error:

        print(
            f"[AURA INVITE CACHE] {error}"
        )

    # --------------------------------------------------------
    # TASKS
    # --------------------------------------------------------

    try:

        if not giveaway_task.is_running():

            giveaway_task.start()

    except Exception as error:

        print(
            f"[AURA GIVEAWAY TASK] {error}"
        )

    try:

        if not automatic_backup_task.is_running():

            automatic_backup_task.start()

    except Exception as error:

        print(
            f"[AURA BACKUP TASK] {error}"
        )


# ============================================================
# SETUP HOOK FINAL
# ============================================================

@bot.event
async def setup_hook():

    global _data_save_task

    # --------------------------------------------------------
    # SAVE AUTOMÁTICO
    # --------------------------------------------------------

    try:

        if _data_save_task is None:

            _data_save_task = asyncio.create_task(
                automatic_data_save()
            )

    except Exception as error:

        print(
            f"[AURA AUTO SAVE] {error}"
        )

    # --------------------------------------------------------
    # VERIFICAÇÃO PERSISTENTE
    # --------------------------------------------------------

    try:

        bot.add_view(
            VerificationView()
        )

    except Exception as error:

        print(
            f"[AURA VERIFICATION VIEW] {error}"
        )

    # --------------------------------------------------------
    # INICIALIZAÇÃO
    # --------------------------------------------------------

    try:

        await initialize_final_systems()

    except Exception as error:

        print(
            f"[AURA FINAL INIT] {error}"
        )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    token = os.getenv(
        "DISCORD_TOKEN"
    )

    if not token:

        print(
            "❌ A variável DISCORD_TOKEN não foi encontrada."
        )

        print(
            "Configure o token nas variáveis de ambiente da hospedagem."
        )

        raise SystemExit(1)

    try:

        bot.run(
            token
        )

    except discord.LoginFailure:

        print(
            "❌ Token do Discord inválido."
        )

    except Exception as error:

        print(
            f"❌ Erro fatal ao iniciar o Aura: {error}"
        )

        traceback.print_exc()
