import discord
import json
import os

from aiohttp import web
from asyncio import get_event_loop
from enum import Enum
from discord.ext import commands
from peewee import (
    fn,
    CharField,
    DateField,
    IntegerField,
    Model,
    PostgresqlDatabase,
)


db = PostgresqlDatabase(
    os.getenv('POSTGRES_DB'),
    user=os.getenv('POSTGRES_USER'),
    password=os.getenv('POSTGRES_PASSWORD'),
    host=os.getenv('POSTGRES_HOST'),
    port=os.getenv('POSTGRES_PORT'),
)
bot = commands.Bot(command_prefix='!')

routes = web.RouteTableDef()


class TiposBolas(Enum):
    ULTRA_BALL = 1


class Pokemon(Model):
    nome = CharField(index=True, unique=True)
    numero = IntegerField(index=True, unique=True)
    preco = IntegerField(null=True)

    class Meta:
        database = db


class CalculadorMediaPokemon:
    REGRA_POR_POKEBOLA = {
        TiposBolas.ULTRA_BALL: (1.5 / 90),
    }

    def calcula_media(self, pokemon: Pokemon) -> dict:
        if pokemon.preco:
            return {
                bola.name.replace('_', '').title(): regra * pokemon.preco
                for bola, regra in self.REGRA_POR_POKEBOLA.items()
            }


@bot.command()
async def media(ctx, nome_pokemon):
    if not nome_pokemon:
        return
    try:
        pokemon = Pokemon.select().where(fn.LOWER(Pokemon.nome)==nome_pokemon.lower()).get()
    except Pokemon.DoesNotExist:
        await ctx.send(f'Não foi encontrado um pokemon com o nome: {nome_pokemon}')
        return
    dados = CalculadorMediaPokemon().calcula_media(pokemon)
    if dados:
        msg_media_balls = f'A média para {pokemon.nome} é:\n{dados}'
    else:
        msg_media_balls = f'Pokemon sem valor cadastrado, por favor use o comando !valor_na_bola NOME_DO_POKEMON VALOR'
    await ctx.send(msg_media_balls)


@bot.command()
async def valor_na_bola(ctx, nome_pokemon, novo_valor):
    try:
        pokemon = Pokemon.select().where(fn.LOWER(Pokemon.nome)==nome_pokemon.lower()).get()
    except Pokemon.DoesNotExist:
        await ctx.send(f'Não foi encontrado um pokemon com o nome: {nome_pokemon}')
        return
    try:
        pokemon.preco = int(novo_valor)
    except ValueError:
        await ctx.send(f'Envie o valor sem casas decimais ou divisores de milhar')
        return
    pokemon.save()
    await ctx.send(f'O preço para o pokemon {pokemon.nome} foi atualizado para: {novo_valor}')


@routes.get('/')
async def http_health_check(self):
    return web.Response(text='ok', status=200)


async def run_bot():
    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', os.getenv('PORT', '8888'))
    await site.start()

    db.connect(reuse_if_open=True)
    db.create_tables([Pokemon])
    try:
        await bot.start(os.getenv('TOKEN_DISCORD', ''))
    except:
        bot.close()
        raise
    finally:
        await runner.cleanup()


if __name__ == '__main__':
    loop = get_event_loop()
    loop.run_until_complete(run_bot())
