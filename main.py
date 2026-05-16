import discord
from discord.ext import commands
from discord import app_commands
import json
import os

intents = discord.Intents.all()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

EMBEDS_FILE = "/data/embeds.json"
WELCOME_FILE = "/data/welcome.json"

embeds = {}
welcome = {}
sessions = {}


def is_admin(interaction: discord.Interaction):
    return interaction.user.guild_permissions.administrator


def load_data():
    global embeds, welcome

    if os.path.exists(EMBEDS_FILE):
        with open(EMBEDS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for name, e in data.items():
                embeds[name] = discord.Embed.from_dict(e)

    if os.path.exists(WELCOME_FILE):
        with open(WELCOME_FILE, "r", encoding="utf-8") as f:
            welcome.update(json.load(f))


def save_embeds():
    with open(EMBEDS_FILE, "w", encoding="utf-8") as f:
        json.dump({k: v.to_dict() for k, v in embeds.items()}, f, indent=2)


def save_welcome():
    with open(WELCOME_FILE, "w", encoding="utf-8") as f:
        json.dump(welcome, f, indent=2)


async def embed_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=n, value=n)
        for n in embeds.keys()
        if current.lower() in n.lower()
    ][:25]


def parse_embed(embed: discord.Embed, member: discord.Member):
    new = embed.copy()

    if new.description:
        new.description = new.description.replace("{user}", member.mention)
        new.description = new.description.replace("{server}", member.guild.name)
        new.description = new.description.replace("{count}", str(member.guild.member_count))

    return new


class Session:
    def __init__(self, name):
        self.name = name
        self.embed = discord.Embed()
        self.title = None
        self.description = None
        self.color = None
        self.thumbnail = None
        self.image = None


class EmbedBuilder(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=600)
        self.user_id = user_id

    def session(self):
        return sessions[self.user_id]

    async def refresh(self, interaction):
        await interaction.response.edit_message(embed=self.session().embed, view=self)

    async def auto_save(self):
        sess = self.session()
        embeds[sess.name] = sess.embed.copy()
        save_embeds()

    @discord.ui.button(label="Titre", style=discord.ButtonStyle.primary)
    async def title(self, interaction, button):
        await interaction.response.send_modal(TitleModal(self))

    @discord.ui.button(label="Description", style=discord.ButtonStyle.primary)
    async def desc(self, interaction, button):
        await interaction.response.send_modal(DescModal(self))

    @discord.ui.button(label="Couleur", style=discord.ButtonStyle.secondary)
    async def color(self, interaction, button):
        await interaction.response.send_modal(ColorModal(self))

    @discord.ui.button(label="Thumbnail", style=discord.ButtonStyle.secondary)
    async def thumb(self, interaction, button):
        await interaction.response.send_modal(ThumbModal(self))

    @discord.ui.button(label="Test", style=discord.ButtonStyle.success)
    async def test(self, interaction, button):
        await interaction.channel.send(embed=self.session().embed)
        await interaction.response.send_message("OK", ephemeral=True)

    @discord.ui.button(label="Save", style=discord.ButtonStyle.green)
    async def save(self, interaction, button):
        sess = self.session()
        embeds[sess.name] = sess.embed.copy()
        save_embeds()
        await interaction.response.send_message("Embed sauvegardé", ephemeral=True)

    @discord.ui.button(label="Image", style=discord.ButtonStyle.secondary)
    async def image(self, interaction, button):
        await interaction.response.send_modal(ImageModal(self))

class NameModal(discord.ui.Modal, title="Nom embed"):
    name = discord.ui.TextInput(label="Nom")

    def __init__(self, interaction):
        super().__init__()
        self.interaction = interaction

    async def on_submit(self, interaction):

        sessions[self.interaction.user.id] = Session(self.name.value)

        view = EmbedBuilder(self.interaction.user.id)

        embed = discord.Embed(
            title="Builder",
            description=f"Embed : {self.name.value}"
        )

        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True
        )


class BaseModal(discord.ui.Modal):
    def __init__(self, view):
        super().__init__()
        self.view = view


class TitleModal(BaseModal, title="Titre"):
    def __init__(self, view):
        super().__init__(view)
        sess = view.session()

        self.text = discord.ui.TextInput(
            label="Titre",
            default=sess.title or ""
        )
        self.add_item(self.text)

    async def on_submit(self, interaction):
        sess = self.view.session()
        sess.title = self.text.value
        sess.embed.title = self.text.value

        await self.view.auto_save()
        await self.view.refresh(interaction)


class DescModal(BaseModal, title="Description"):
    def __init__(self, view):
        super().__init__(view)
        sess = view.session()

        self.text = discord.ui.TextInput(
            label="Description",
            style=discord.TextStyle.paragraph,
            default=sess.description or ""
        )
        self.add_item(self.text)

    async def on_submit(self, interaction):
        sess = self.view.session()
        sess.description = self.text.value
        sess.embed.description = self.text.value

        await self.view.auto_save()
        await self.view.refresh(interaction)


class ColorModal(BaseModal, title="Couleur"):
    def __init__(self, view):
        super().__init__(view)
        sess = view.session()

        self.text = discord.ui.TextInput(
            label="#HEX",
            default=sess.color or "#ffffff"
        )
        self.add_item(self.text)

    async def on_submit(self, interaction):
        sess = self.view.session()
        sess.color = self.text.value
        sess.embed.color = discord.Color(int(self.text.value.replace("#", ""), 16))

        await self.view.auto_save()
        await self.view.refresh(interaction)


class ThumbModal(BaseModal, title="Thumbnail"):
    def __init__(self, view):
        super().__init__(view)
        sess = view.session()

        self.text = discord.ui.TextInput(
            label="URL",
            default=sess.thumbnail or ""
        )
        self.add_item(self.text)

    async def on_submit(self, interaction):
        sess = self.view.session()
        sess.thumbnail = self.text.value
        sess.embed.set_thumbnail(url=self.text.value)

        await self.view.auto_save()
        await self.view.refresh(interaction)

class ImageModal(discord.ui.Modal, title="Image"):

    image_url = discord.ui.TextInput(
        label="URL de l'image",
        placeholder="https://i.imgur.com/image.png"
    )

    def __init__(self, view):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):

        sess = self.view.session()

        sess.embed.set_image(url=self.image_url.value)

        await self.view.auto_save()

        await interaction.response.edit_message(
            embed=sess.embed,
            view=self.view
        )


embed_group = app_commands.Group(name="embed", description="Gestion embeds")
bot.tree.add_command(embed_group)


@embed_group.command(name="create")
async def create(interaction: discord.Interaction):
    if not is_admin(interaction):
        return await interaction.response.send_message("No permission", ephemeral=True)

    await interaction.response.send_modal(NameModal(interaction))

@embed_group.command(name="edit")
@app_commands.autocomplete(name=embed_autocomplete)
async def edit(interaction: discord.Interaction, name: str):

    if not is_admin(interaction):
        return await interaction.response.send_message(
            "No permission",
            ephemeral=True
        )

    if name not in embeds:
        return await interaction.response.send_message(
            "Embed introuvable",
            ephemeral=True
        )

    existing = embeds[name]

    sess = Session(name)
    sess.embed = existing.copy()

    sess.title = existing.title
    sess.description = existing.description

    if existing.color:
        sess.color = f"#{existing.color.value:06x}"

    if existing.thumbnail:
        sess.thumbnail = existing.thumbnail.url

    if existing.image:
        sess.image = existing.image.url

    sessions[interaction.user.id] = sess

    view = EmbedBuilder(interaction.user.id)

    await interaction.response.send_message(
        embed=sess.embed,
        view=view,
        ephemeral=True
    )

class EmbedSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=n, value=n)
            for n in embeds.keys()
        ] or [discord.SelectOption(label="Aucun", value="none")]

        super().__init__(placeholder="Choisis un embed", options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        v = self.values[0]

        if v == "none":
            return await interaction.response.send_message("Aucun embed", ephemeral=True)

        await interaction.response.send_message(embed=embeds[v], ephemeral=True)


class DropdownView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(EmbedSelect())


@embed_group.command(name="show")
async def show(interaction: discord.Interaction):
    await interaction.response.send_message("Choisis", view=DropdownView(), ephemeral=True)


class ConfirmDelete(discord.ui.View):
    def __init__(self, name):
        super().__init__(timeout=30)
        self.name = name

    @discord.ui.button(label="Confirmer", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction, button):

        if self.name in embeds:
            del embeds[self.name]
            save_embeds()

        await interaction.response.edit_message(
            content=f"Embed `{self.name}` supprimé",
            view=None
        )

    @discord.ui.button(label="Annuler", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction, button):
        await interaction.response.edit_message(
            content="Annulé",
            view=None
        )


@embed_group.command(name="delete")
@app_commands.autocomplete(name=embed_autocomplete)
async def delete(interaction: discord.Interaction, name: str):

    if not is_admin(interaction):
        return await interaction.response.send_message("No permission", ephemeral=True)

    if name not in embeds:
        return await interaction.response.send_message("Embed introuvable", ephemeral=True)

    await interaction.response.send_message(
        f"Supprimer `{name}` ?",
        view=ConfirmDelete(name),
        ephemeral=True
    )


@bot.tree.command(name="setwelcome")
@app_commands.autocomplete(embed_name=embed_autocomplete)
async def setwelcome(interaction: discord.Interaction, channel: discord.TextChannel, embed_name: str):

    if not is_admin(interaction):
        return await interaction.response.send_message("No permission", ephemeral=True)

    welcome[str(interaction.guild.id)] = {
        "channel": channel.id,
        "embed": embed_name
    }

    save_welcome()
    await interaction.response.send_message("OK", ephemeral=True)


@bot.event
async def on_member_join(member):

    # ======================
    # WELCOME
    # ======================

    cfg = welcome.get(str(member.guild.id))

    if cfg:
        channel = member.guild.get_channel(cfg["channel"])
        embed = embeds.get(cfg["embed"])

        if channel and embed:
            await channel.send(
                content=f"Bienvenue {member.mention} 👋",
                embed=parse_embed(embed, member)
                )


    # ======================
    # AUTO ROLE
    # ======================

    role = member.guild.get_role(1504218303038623906)

    if role:
        await member.add_roles(role)
        print(f"{member} a reçu le rôle {role.name}")

# ======================
# REACTION ADD
# ======================
@bot.event
async def on_raw_reaction_add(payload):

    if payload.message_id != MESSAGE_ID:
        return

    if payload.emoji.name != EMOJI:
        return

    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return

    role = guild.get_role(ROLE_ID)
    if role is None:
        return

    member = guild.get_member(payload.user_id)
    if member is None:
        member = await guild.fetch_member(payload.user_id)

    await member.add_roles(role)

# ======================
# REACTION REMOVE
# ======================
@bot.event
async def on_raw_reaction_remove(payload):

    if payload.message_id != MESSAGE_ID:
        return

    if payload.emoji.name != EMOJI:
        return

    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return

    role = guild.get_role(ROLE_ID)
    if role is None:
        return

    member = guild.get_member(payload.user_id)
    if member is None:
        member = await guild.fetch_member(payload.user_id)

    await member.remove_roles(role)

# =========================
# CONFIG
# =========================

# 👉 ID du rôle donné après vérification
ROLE_ID = 1504214645584695397

# =========================
# VIEW BOUTON
# =========================
class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Vérification",
        emoji="☕",
        style=discord.ButtonStyle.success,
        custom_id="verify_button"
    )
    async def verify_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        role = interaction.guild.get_role(ROLE_ID)

        if role is None:
            return await interaction.response.send_message(
                "Rôle introuvable.",
                ephemeral=True
            )

        if role in interaction.user.roles:
            return await interaction.response.send_message(
                "Tu es déjà vérifié ☕",
                ephemeral=True
            )

        await interaction.user.add_roles(role)

        await interaction.response.send_message(
            "Vérification réussie ☕",
            ephemeral=True
        )

# =========================
# READY
# =========================
@bot.event
async def on_ready():

    # Charge les embeds + config welcome
    load_data()

    # Recharge les boutons même après reboot
    bot.add_view(VerifyView())

    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)} commandes synchronisées")
    except Exception as e:
        print(e)

    print(f"Connecté en tant que {bot.user}")

# =========================
# /VERIFY
# =========================
@bot.tree.command(
    name="verify",
    description="Envoie le panneau de vérification"
)
@app_commands.checks.has_permissions(administrator=True)
async def verify(interaction: discord.Interaction):

    embed = discord.Embed(
        title="☕ Vérification",
        description=(
            "Bienvenue dans notre monde plein de magie !\n\n"
            "*Notre règlement est soumis aux conditions d'utilisation de la plateforme Discord.*\n\n"
            "Clique sur le bouton ci-dessous pour accéder au serveur."
        ),
        color=discord.Color.from_rgb(111, 78, 55)
    )

    embed.set_footer(
        text="Prêt pour de nouvelles aventures ?"
    )

    await interaction.response.send_message(
        embed=embed,
        view=VerifyView()
    )

import os
bot.run(os.environ["TOKEN"])