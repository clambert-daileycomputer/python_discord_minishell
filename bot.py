#!/usr/bin/env python3

import os
import subprocess

import discord
import shlex
from dotenv import load_dotenv
import random
from random import seed

client = discord.Client()
message_size = 2000
out_size = 200
proc_timeout = 5

@client.event
async def on_ready():
    in_guild = discord.utils.get(client.guilds, name=guild)
    print(
        f'{client.user} is connected to the following guild:\n'
        f'{in_guild.name}(id: {in_guild.id})'
    )

@client.event
async def on_message(message):
    global proc_timeout
    global client
    global max_size
    global out_size

    if message.author == client.user:
        return
    response = "Error"
    notification = None

    if message.content[:3] == '!t ' and int(message.content[3:]):
        proc_timeout = int(message.content[3:])
        notification = "timeout is now: " + str(proc_timeout)
        response = ""

    elif message.content[:3] == '!m ' and int(message.content[3:]):
        out_size = int(message.content[3:])
        notification = "output buff size is now: " + str(out_size)
        response = ""

    elif message.content[:2] == '$ ':
        process = subprocess.Popen(message.content[2:],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    shell=True)
        try:
            outs, errs = process.communicate(timeout=proc_timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            outs, errs = process.communicate()
        if outs:
            response = outs.decode('utf-8')
        print("OUTPUT -|")
        print(response)
        print("|-")
    else:
        notification = "usage: \'$ shell exp\' or \'!t int\' for timeout or \'!m int\' for max print amt"
    output_arr = [response[i:i+message_size] for i in range(0, len(response), message_size)]
    to_print = out_size
    nb_of_messages = int(to_print / message_size) + 1
    for i in range(len(output_arr[:nb_of_messages])):
        await message.channel.send(output_arr[i][:to_print])
        to_print -= message_size
    if notification:
        await message.channel.send(notification)

if __name__ == "__main__":

    seed(1)
    #looks for .env file in folder $VIRTUAL_ENV
    envars = os.getenv('VIRTUAL_ENV') + '/' + '.env'
    load_dotenv(envars)
    #loads these two variables from that .env file
    token = os.getenv('DISCORD_TOKEN')
    guild = os.getenv('DISCORD_GUILD')

    client.run(token)
