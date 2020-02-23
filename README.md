# python_discord_bot

control raspberry pi remotely by sending shell expressions to the bot.

output will be sent back.

control the timeout before processes are killed, and limit the amount printed.

# basic controls

'$ expression' to run stuff

'!t number' to adjust timeout

'!m number' to adjust number of printed characters

# file io

'!getfile path' uploads requested file to discord

'!sendfiles (optional path)' requires files attached to message.
Sends files to bot and downloads them to 'pwd' or path from argument

# job control

'!newjob $ expression' creates a new job to run in background

'!listjobs' list the history of jobs.

'!killjob jobfilepath' kills job identified by 'path' from '!listjobs'
