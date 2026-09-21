import asyncio
import json
import os
import secrets
import time
from urllib.parse import urlencode

import aiohttp
from aiohttp import web
import discord
from discord.ext import commands


# ============================================================
# CONFIGURAÇÃO
# ============================================================

# NÃO coloque os valores diretamente no código.
#
# Windows PowerShell:
#
# $env:DISCORD_BOT_TOKEN="SEU_TOKEN"
# $env:DISCORD_CLIENT_SECRET="SEU_CLIENT_SECRET"
# $env:PUBLIC_BASE_URL="https://SEU-BACKEND.com"
#
# Exemplo:
# $env:PUBLIC_BASE_URL="https://meu-bot.onrender.com"

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")

CLIENT_ID = os.getenv(
    "DISCORD_CLIENT_ID",
    "1551380033342410872"
)

PUBLIC_BASE_URL = os.getenv(
    "PUBLIC_BASE_URL",
    "http://localhost:80"
).rstrip("/")

PORT = int(
    os.getenv("PORT", "80")
)

# Página para onde o usuário será mandado depois do login.
# Se não quiser usar uma página externa, deixe vazio.
SUCCESS_URL = os.getenv(
    "OAUTH_SUCCESS_URL",
    ""
).strip()

# URL do seu clonador/site.
CLONADOR_URL = os.getenv(
    "CLONADOR_URL",
    "https://callbackf.netlify.app"
).strip()

# Onde os dados dos usuários serão salvos.
DATA_FILE = "oauth_users.json"


# ============================================================
# VALIDAÇÃO DA CONFIGURAÇÃO
# ============================================================

if not BOT_TOKEN:
    raise RuntimeError(
        "DISCORD_BOT_TOKEN não foi configurado."
    )

if not CLIENT_SECRET:
    raise RuntimeError(
        "DISCORD_CLIENT_SECRET não foi configurado."
    )


# ============================================================
# DISCORD BOT
# ============================================================

intents = discord.Intents.default()
intents.guilds = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# ============================================================
# MEMÓRIA / ESTADO
# ============================================================

# state -> informações temporárias do login
oauth_states = {}

# user_id -> informações OAuth
oauth_users = {}


# ============================================================
# ARQUIVO DE DADOS
# ============================================================

def carregar_dados():
    global oauth_users

    if not os.path.exists(DATA_FILE):
        oauth_users = {}
        return

    try:
        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as arquivo:

            dados = json.load(arquivo)

        if isinstance(dados, dict):
            oauth_users = dados
        else:
            oauth_users = {}

    except Exception as error:
        print(
            f"⚠️ Não foi possível carregar {DATA_FILE}: {error}"
        )

        oauth_users = {}


def salvar_dados():
    try:
        with open(
            DATA_FILE,
            "w",
            encoding="utf-8"
        ) as arquivo:

            json.dump(
                oauth_users,
                arquivo,
                ensure_ascii=False,
                indent=2
            )

    except Exception as error:
        print(
            f"❌ Erro ao salvar dados OAuth: {error}"
        )


carregar_dados()


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def criar_redirect_uri():
    """
    Essa URL precisa ser EXATAMENTE igual à cadastrada
    em Discord Developer Portal > OAuth2 > Redirects.
    """

    return f"{PUBLIC_BASE_URL}/oauth/callback"


def usuario_logado(user_id: int):
    """
    Verifica se o usuário completou o OAuth.
    """

    dados = oauth_users.get(
        str(user_id)
    )

    if not dados:
        return False

    return bool(
        dados.get("connected", False)
    )


def limpar_states_expirados():
    agora = time.time()

    expirados = []

    for state, dados in oauth_states.items():

        criado_em = dados.get(
            "created_at",
            0
        )

        if agora - criado_em > 600:
            expirados.append(state)

    for state in expirados:
        oauth_states.pop(
            state,
            None
        )


async def discord_request(
    session,
    method,
    url,
    **kwargs
):
    """
    Faz requisição para a API do Discord
    e retorna JSON.
    """

    async with session.request(
        method,
        url,
        **kwargs
    ) as response:

        texto = await response.text()

        try:
            dados = json.loads(texto)

        except Exception:
            dados = {
                "raw": texto
            }

        if response.status >= 400:

            raise RuntimeError(
                f"Discord API retornou HTTP "
                f"{response.status}: {dados}"
            )

        return dados


# ============================================================
# OAUTH2 - CALLBACK
# ============================================================

async def oauth_callback(request):
    """
    Discord redireciona o usuário para cá depois da autorização.

    Exemplo:

    /oauth/callback?code=ABC&state=XYZ
    """

    error = request.query.get("error")

    if error:

        descricao = request.query.get(
            "error_description",
            "Autorização cancelada."
        )

        return web.Response(
            text=f"""
            <html>
                <head>
                    <meta charset="utf-8">
                    <title>Login cancelado</title>
                </head>

                <body style="
                    background:#111;
                    color:white;
                    font-family:Arial;
                    text-align:center;
                    padding-top:100px;
                ">

                    <h1>❌ Login cancelado</h1>

                    <p>{descricao}</p>

                </body>
            </html>
            """,
            content_type="text/html"
        )

    code = request.query.get("code")
    state = request.query.get("state")

    if not code:
        return web.Response(
            text="❌ OAuth não retornou o code.",
            status=400
        )

    if not state:
        return web.Response(
            text="❌ OAuth não retornou o state.",
            status=400
        )

    # --------------------------------------------------------
    # VERIFICA STATE
    # --------------------------------------------------------

    limpar_states_expirados()

    state_data = oauth_states.pop(
        state,
        None
    )

    if not state_data:
        return web.Response(
            text="❌ State inválido ou expirado. Faça login novamente.",
            status=400
        )

    expected_user_id = state_data[
        "user_id"
    ]

    # --------------------------------------------------------
    # TROCAR CODE POR ACCESS TOKEN
    # --------------------------------------------------------

    token_url = (
        "https://discord.com/api/v10/oauth2/token"
    )

    redirect_uri = criar_redirect_uri()

    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri
    }

    try:

        auth = aiohttp.BasicAuth(
            CLIENT_ID,
            CLIENT_SECRET
        )

        async with aiohttp.ClientSession() as session:

            token_response = await discord_request(
                session,
                "POST",
                token_url,
                data=token_data,
                auth=auth,
                headers={
                    "Content-Type":
                    "application/x-www-form-urlencoded"
                }
            )

            access_token = token_response.get(
                "access_token"
            )

            if not access_token:
                raise RuntimeError(
                    "Discord não retornou access_token."
                )

            # ------------------------------------------------
            # PEGAR USUÁRIO
            # ------------------------------------------------

            user_data = await discord_request(
                session,
                "GET",
                "https://discord.com/api/v10/users/@me",
                headers={
                    "Authorization":
                    f"Bearer {access_token}"
                }
            )

            discord_user_id = int(
                user_data["id"]
            )

            # ------------------------------------------------
            # CONFERIR SE É O MESMO USUÁRIO
            # ------------------------------------------------

            if discord_user_id != expected_user_id:

                return web.Response(
                    text="""
                    ❌ A conta autorizada não corresponde
                    ao usuário que iniciou o login.
                    """,
                    status=403
                )

            # ------------------------------------------------
            # PEGAR SERVIDORES
            # ------------------------------------------------

            guilds = await discord_request(
                session,
                "GET",
                "https://discord.com/api/v10/users/@me/guilds",
                headers={
                    "Authorization":
                    f"Bearer {access_token}"
                }
            )

    except Exception as error:

        print(
            f"❌ Erro no OAuth: {error}"
        )

        return web.Response(
            text=f"""
            <html>
                <head>
                    <meta charset="utf-8">
                    <title>Erro no login</title>
                </head>

                <body style="
                    background:#111;
                    color:white;
                    font-family:Arial;
                    text-align:center;
                    padding-top:100px;
                ">

                    <h1>❌ Erro ao concluir login</h1>

                    <p>
                        Não foi possível concluir a conexão
                        com o Discord.
                    </p>

                    <p style="color:#aaa;">
                        {error}
                    </p>

                </body>
            </html>
            """,
            status=500,
            content_type="text/html"
        )

    # ========================================================
    # SALVAR LOGIN + SERVIDORES
    # ========================================================

    agora = int(
        time.time()
    )

    oauth_users[
        str(discord_user_id)
    ] = {

        "connected": True,

        "user": {
            "id": str(discord_user_id),

            "username": user_data.get(
                "username"
            ),

            "global_name": user_data.get(
                "global_name"
            ),

            "avatar": user_data.get(
                "avatar"
            )
        },

        "guilds": guilds,

        "guild_count": len(
            guilds
        ),

        "connected_at": agora
    }

    salvar_dados()

    print(
        f"✅ LOGIN CONCLUÍDO: "
        f"{user_data.get('username')} "
        f"({discord_user_id})"
    )

    print(
        f"📋 Servidores registrados: "
        f"{len(guilds)}"
    )

    # ========================================================
    # RESPOSTA
    # ========================================================

    if SUCCESS_URL:

        separator = (
            "&"
            if "?" in SUCCESS_URL
            else "?"
        )

        redirect = (
            f"{SUCCESS_URL}"
            f"{separator}"
            f"login=success"
        )

        raise web.HTTPFound(
            redirect
        )

    return web.Response(
        text=f"""
        <html>

            <head>
                <meta charset="utf-8">

                <title>
                    Login concluído
                </title>

                <style>

                    body {{
                        background:#0f1115;
                        color:white;
                        font-family:Arial;
                        text-align:center;
                        padding-top:100px;
                    }}

                    .box {{
                        max-width:500px;
                        margin:auto;
                        padding:30px;
                        background:#181b22;
                        border-radius:15px;
                    }}

                    .success {{
                        font-size:50px;
                    }}

                    h1 {{
                        margin-bottom:10px;
                    }}

                    .servers {{
                        color:#aaa;
                    }}

                </style>

            </head>

            <body>

                <div class="box">

                    <div class="success">
                        ✅
                    </div>

                    <h1>
                        Login concluído!
                    </h1>

                    <p>
                        Conta conectada com sucesso.
                    </p>

                    <p>
                        <b>
                            {len(guilds)}
                        </b>
                        servidores encontrados.
                    </p>

                    <p class="servers">
                        Você já pode voltar ao Discord
                        e usar os comandos.
                    </p>

                </div>

            </body>

        </html>
        """,
        content_type="text/html"
    )


# ============================================================
# API OPCIONAL
# ============================================================

async def oauth_complete(request):
    """
    Endpoint opcional para integrações externas.

    O callback acima já faz todo o processo sozinho.
    """

    try:

        data = await request.json()

        user_id = int(
            data["user_id"]
        )

        guilds = data.get(
            "guilds",
            []
        )

    except Exception:

        return web.json_response(
            {
                "error":
                "Dados inválidos"
            },
            status=400
        )

    oauth_users[
        str(user_id)
    ] = {

        "connected": True,

        "guilds": guilds,

        "guild_count": len(
            guilds
        ),

        "connected_at":
        int(time.time())
    }

    salvar_dados()

    return web.json_response(
        {
            "success": True,

            "guild_count":
            len(guilds)
        }
    )


# ============================================================
# API WEB
# ============================================================

async def iniciar_api():

    app = web.Application()

    # Callback REAL do Discord
    app.router.add_get(
        "/oauth/callback",
        oauth_callback
    )

    # Endpoint opcional
    app.router.add_post(
        "/oauth/complete",
        oauth_complete
    )

    # Página simples para testar
    async def home(request):

        return web.Response(
            text="""
            <html>
                <head>
                    <meta charset="utf-8">
                    <title>OAuth Discord</title>
                </head>

                <body style="
                    background:#111;
                    color:white;
                    font-family:Arial;
                    text-align:center;
                    padding-top:100px;
                ">

                    <h1>🤖 Bot online</h1>

                    <p>
                        Sistema OAuth2 funcionando.
                    </p>

                </body>
            </html>
            """,
            content_type="text/html"
        )

    app.router.add_get(
        "/",
        home
    )

    runner = web.AppRunner(
        app
    )

    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        PORT
    )

    await site.start()

    print(
        f"✅ API iniciada na porta {PORT}"
    )

    print(
        f"🔗 Callback OAuth:"
        f" {criar_redirect_uri()}"
    )

    return runner


# ============================================================
# COMANDO /LOGIN
# ============================================================

@bot.tree.command(
    name="login",
    description="Conecta sua conta Discord ao clonador"
)
async def login(interaction):

    limpar_states_expirados()

    state = secrets.token_urlsafe(
        32
    )

    oauth_states[state] = {

        "user_id":
        interaction.user.id,

        "created_at":
        time.time()
    }

    redirect_uri = criar_redirect_uri()

    params = {

        "client_id":
        CLIENT_ID,

        "response_type":
        "code",

        "redirect_uri":
        redirect_uri,

        "scope":
        "identify guilds",

        "state":
        state,

        "prompt":
        "consent"
    }

    login_url = (
        "https://discord.com/oauth2/authorize?"
        + urlencode(params)
    )

    view = discord.ui.View()

    view.add_item(
        discord.ui.Button(
            label="🔐 Entrar com Discord",
            style=discord.ButtonStyle.link,
            url=login_url
        )
    )

    await interaction.response.send_message(

        "🔐 Clique abaixo para conectar sua "
        "conta Discord.",

        view=view,

        ephemeral=True
    )


# ============================================================
# COMANDO /MEUS_SERVIDORES
# ============================================================

@bot.tree.command(
    name="meus_servidores",
    description="Mostra os servidores obtidos pelo OAuth"
)
async def meus_servidores(interaction):

    dados = oauth_users.get(
        str(interaction.user.id)
    )

    if not dados or not dados.get(
        "connected",
        False
    ):

        await interaction.response.send_message(

            "🔒 Você ainda não fez login.\n\n"
            "Use `/login` primeiro.",

            ephemeral=True
        )

        return

    guilds = dados.get(
        "guilds",
        []
    )

    if not guilds:

        await interaction.response.send_message(

            "✅ Login confirmado, mas o Discord "
            "não retornou servidores para essa conta.",

            ephemeral=True
        )

        return

    linhas = []

    for guild in guilds:

        nome = guild.get(
            "name",
            "Sem nome"
        )

        guild_id = guild.get(
            "id",
            "?"
        )

        linhas.append(
            f"• **{nome}** — `{guild_id}`"
        )

    texto = "\n".join(
        linhas
    )

    if len(texto) > 3900:

        texto = (
            texto[:3900]
            + "\n..."
        )

    embed = discord.Embed(

        title="📋 Seus servidores",

        description=texto,

        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=
        f"{len(guilds)} servidores encontrados"
    )

    await interaction.response.send_message(

        embed=embed,

        ephemeral=True
    )


# ============================================================
# COMANDO /CLONADOR
# ============================================================

@bot.tree.command(
    name="clonador",
    description="Abre o clonador"
)
async def clonador(interaction):

    dados = oauth_users.get(
        str(interaction.user.id)
    )

    # --------------------------------------------------------
    # NÃO LOGADO
    # --------------------------------------------------------

    if not dados or not dados.get(
        "connected",
        False
    ):

        view = discord.ui.View()

        params = {

            "client_id":
            CLIENT_ID,

            "response_type":
            "code",

            "redirect_uri":
            criar_redirect_uri(),

            "scope":
            "identify guilds",

            "state":
            secrets.token_urlsafe(32),

            "prompt":
            "consent"
        }

        # Criamos o state corretamente antes do link.
        state = params["state"]

        oauth_states[state] = {

            "user_id":
            interaction.user.id,

            "created_at":
            time.time()
        }

        login_url = (
            "https://discord.com/oauth2/authorize?"
            + urlencode(params)
        )

        view.add_item(
            discord.ui.Button(
                label="🔐 Fazer login",
                style=discord.ButtonStyle.link,
                url=login_url
            )
        )

        await interaction.response.send_message(

            "🔒 Você precisa conectar sua conta "
            "Discord antes de usar o clonador.",

            view=view,

            ephemeral=True
        )

        return

    # --------------------------------------------------------
    # LOGADO
    # --------------------------------------------------------

    view = discord.ui.View()

    view.add_item(
        discord.ui.Button(
            label="🚀 Abrir clonador",
            style=discord.ButtonStyle.link,
            url=CLONADOR_URL
        )
    )

    quantidade = dados.get(
        "guild_count",
        len(dados.get("guilds", []))
    )

    await interaction.response.send_message(

        f"✅ Login confirmado!\n\n"
        f"📋 Servidores registrados: "
        f"**{quantidade}**\n\n"
        f"Você pode abrir o clonador abaixo.",

        view=view,

        ephemeral=True
    )


# ============================================================
# EVENTO READY
# ============================================================

@bot.event
async def on_ready():

    print(
        f"✅ Bot conectado como "
        f"{bot.user}"
    )

    print(
        f"🆔 Client ID: {CLIENT_ID}"
    )

    print(
        f"🔗 Redirect URI: "
        f"{criar_redirect_uri()}"
    )

    try:

        synced = await bot.tree.sync()

        print(
            f"✅ {len(synced)} comandos sincronizados."
        )

    except Exception as error:

        print(
            f"❌ Erro ao sincronizar comandos: "
            f"{error}"
        )


# ============================================================
# MAIN
# ============================================================

async def main():

    await iniciar_api()

    print(
        "🚀 Iniciando bot..."
    )

    await bot.start(
        BOT_TOKEN
    )


if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print(
            "\n🛑 Bot encerrado."
        )
