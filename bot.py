#!/usr/bin/env python3

import os
import io
import time
import select
import signal
import psutil
import asyncio
import subprocess
import tempfile
import pathlib
import discord
import shlex
from dotenv import load_dotenv
import random
from random import seed
from threading import Thread

last_dir = os.getcwd()
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
curr_channel = None
script_location = pathlib.Path(__file__).parent.absolute()
message_size = 2000
out_size = 2000
proc_timeout = 5
chunk_size = 16
jobs_data = {}
jobs = []



class shell_worker(Thread):
    def __init__(self, command):
        Thread.__init__(self)
        self.command = command
        self.running = False
        self.reported = False
        self.path = None
        self.proc = None
        self.die = False
    def run(self):
        new_job(self, self.command)
    def get_info(self):
        return (self.command, self.path, self.proc, self.running)

@client.event
async def on_ready():
    global curr_channel
    global jobs
    global client
    curr_channel = client.get_channel(1154547940099108894)

    while (True):
        for j in jobs:
            command, path, proc, running = j.get_info()
            if j.running == False and j.reported == False:
                j.join()
                await get_results(path, curr_channel)
                j.reported = True
        await asyncio.sleep(1)


async def get_results(path, channel):
    global jobs

    if not jobs or not path:
        pass
    message = "results for: " + path + "\n"
    found = False
    for j in jobs:
        if j.path == path:
            found = True
            cmd, path, proc, running = j.get_info()
            message += "job (" + path + ")\n"
            try:
                with open(path, "r") as f:
                    await channel.send(file=discord.File(f, path + ".log"))
                    message += "sent file: " + path + ".log"
            except (PermissionError, FileNotFoundError, discord.errors.HTTPException) as e:
                message += "file error"
    if found == False:
        message += "job not found"
    print(message)
    await channel.send(message)

async def list_jobs(channel):
    global jobs

    output = ""
    for j in jobs:
        command, path, proc, running = j.get_info()
        output += "job (" + path + "), Running=" + str(running) + ", command=" + command + "\n"
    output += "total jobs: " + str(len(jobs))
    print(output)
    await channel.send(output)

def kill_children(proc_pid):
    process = psutil.Process(proc_pid)
    for proc in process.children(recursive=True):
        os.kill(proc.pid, signal.SIGTERM)

async def kill_job(path, channel):
    global jobs

    if not jobs:
        pass
    message = "trying to kill: " + path + "\n"
    found = False
    for j in jobs:
        if j.path == path:
            found = True
            cmd, path, proc, running = j.get_info()
            #os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            os.killpg(proc.pid, signal.SIGTERM)
            j.running = False
            message += "killed job (" + path + ")\n"
    if found == False:
        message += "job not found"
    print(message)
    await channel.send(message)

def new_job(worker, command):
    global jobs
    global jobs_data
    global chunk_size

    process = subprocess.Popen(["/bin/bash", "-c", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=os.getcwd(),
                close_fds=True,
                start_new_session=True)
    poll_obj = select.poll()
    poll_obj.register(process.stdout, select.POLLIN | select.POLLHUP)
    fd, path = tempfile.mkstemp()
    print("new task: " + path)
    worker.proc = process;
    worker.path = path
    worker.running = True
    with open(fd, 'wb') as f:
        running = True
        while running == True:
            poll_list = poll_obj.poll(0)
            readable_data = False
            disc = False
            for fd, flag in poll_list:
                if flag & select.POLLIN:
                    readable_data = True
                if flag & select.POLLHUP:
                    worker.running = False
            if readable_data == True:
                line = process.stdout.read(1000)
                f.write(line)
                #print("subprocess print:" + line.decode('utf-8'))
            elif worker.running == False:
                running = False

    poll_obj.unregister(process.stdout)
    print("done!")


@client.event
async def on_message(message):
    global executor
    global proc_timeout
    global client
    global max_size
    global out_size
    global last_dir

    if message.author == client.user:
        return

    print("GOT MESSAGE")
    notification = ""
    if message.content[:3] == '!t ' and int(message.content[3:]):
        proc_timeout = int(message.content[3:])
        notification = "timeout is now: " + str(proc_timeout)

    elif message.content[:10] == '!newjob $ ' and message.content[10:]:
        worker = shell_worker(message.content[10:])
        jobs.append(worker)
        worker.start()
    elif message.content[:9] == '!listjobs':
        await list_jobs(message.channel)
    elif message.content[:9] == '!killjob ' and message.content[9:]:
        await kill_job(message.content[9:], message.channel)
    elif message.content[:3] == '!m ' and int(message.content[3:]):
        out_size = int(message.content[3:])
        notification = "output buff size is now: " + str(out_size)
    elif message.content[:10] == '!sendfiles':
        if message.content[10:] and message.content[10:] != ' ':
            if message.content[10] == ' ':
                location = message.content[11:]
            else:
                location = message.content[10:]
        else:
            location = os.getcwd()
        notification = "sending files to location: " + location + "\n"
        if message.attachments:
            for attachment in message.attachments:
                print(attachment.filename)
                new_file_name = location + "/" + attachment.filename
                print(new_file_name)
                if not os.path.exists(new_file_name):
                    try:
                        with open(new_file_name, "wb") as output_file:
                            with io.BytesIO() as attachment_stream:
                                await attachment.save(attachment_stream, seek_begin=True, use_cached=False)
                                fbuf = io.BufferedReader(attachment_stream)
                                output_file.write(attachment_stream.getvalue())
                                notification += "saved file '" + new_file_name + "'"
                    except (PermissionError) as e:
                        notification += e
                else:
                    notification += "file exists"
        else:
            notification += "no attachments"
    elif message.content[:9] == '!getfile ' and message.content[9:]:
        #await message.channel.send(file=message.content[9:])
        try:
            with open(message.content[9:], "r") as f:
                await message.channel.send(file=discord.File(f, message.content[9:]))
                notification = "sent file: " + message.content[9:]
        except (PermissionError, FileNotFoundError) as e:
            notification = e
    elif message.content[:5] == '$ cd ':
        cwd = os.getcwd()
        if message.content[5:]:
            if message.content[:6] == '$ cd -':
                if last_dir:
                    os.chdir(last_dir)
            else:
                last_dir = os.getcwd()
                os.chdir(message.content[5:])
        notification = "cd from: " + cwd + " to: " + os.getcwd()
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
        response = ""
        if outs:
            response = outs.decode('utf-8')
        output_arr = [response[i:i+message_size] for i in range(0, len(response), message_size)]
        to_print = out_size
        nb_of_messages = int(to_print / message_size) + 1
        total_printed = 0
        for i in range(len(output_arr[:nb_of_messages])):
            chunk_len = len(output_arr[i][:to_print])
            if chunk_len > 0:
                print("MESSAGE-|")
                print(output_arr[i][:to_print])
                print("|-")
                total_printed += chunk_len
                await message.channel.send(output_arr[i][:to_print])
            to_print -= message_size
        stream_str = io.BytesIO(response.encode('utf-8'))#bytes(response,'ascii'))
        file_stream = discord.File(stream_str, "response.txt")
        print("total printed: " + str(total_printed) + "/" + str(len(response)))
        await message.channel.send("total printed: " + str(total_printed) + "/" + str(len(response)))
        await message.channel.send(file=file_stream)
    else:
        notification = "usage: \'$ shell exp\' or \'!t int\' for timeout or \'!m int\' for max print amt"
    if notification != "":
        print(notification)
        await message.channel.send(notification)

if __name__ == "__main__":
    seed(1)

    if os.getenv('VIRTUAL_ENV') is None or os.getenv('DISCORD_TOKEN') is None or os.getenv('DISCORD_GUILD'):
        return

    #looks for .env file in folder $VIRTUAL_ENV
    envars = os.getenv('VIRTUAL_ENV') + '/' + '.env'
    load_dotenv(envars)
    #loads these two variables from that .env file
    token = os.getenv('DISCORD_TOKEN')
    guild = os.getenv('DISCORD_GUILD')
    client.run(token)
