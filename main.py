import discord
from discord.ext import commands, tasks
import logging
from dotenv import load_dotenv
import os
import json
import datetime
import random

load_dotenv()
token = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command('help')

DATA_FILE = "user_data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({}, f)
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_user_data(user_id):
    data = load_data()
    return data.setdefault(str(user_id), {"classes": [], "homework": [], "reminders": [], "exams": []})

def update_user_data(user_id, user_data):
    data = load_data()
    data[str(user_id)] = user_data
    save_data(data)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} - {bot.user.id}')

#scheduling 
@bot.command()
async def addclass(ctx, name: str, day: str, time: str):
    """Add a class (name, day, time)."""
    user_data = get_user_data(ctx.author.id)
    user_data["classes"].append({"name": name, "day": day, "time": time})
    update_user_data(ctx.author.id, user_data)
    await ctx.send(f"Class '{name}' added on {day} at {time}.")

@bot.command()
async def viewclasses(ctx):
    """View all your classes for the week."""
    user_data = get_user_data(ctx.author.id)
    if not user_data["classes"]:
        await ctx.send("No classes scheduled.")
        return
    msg = "**Your Classes:**\n"
    for c in user_data["classes"]:
        msg += f"- {c['name']} on {c['day']} at {c['time']}\n"
    await ctx.send(msg)

@bot.command()
async def nextclass(ctx):
    """Show the next upcoming class."""
    user_data = get_user_data(ctx.author.id)
    now = datetime.datetime.now()
    next_c = None
    min_delta = None
    for c in user_data["classes"]:
        try:
            class_time = datetime.datetime.strptime(f"{c['day']} {c['time']}", "%A %H:%M")
            class_time = class_time.replace(year=now.year, month=now.month, day=now.day)
            delta = (class_time - now).total_seconds()
            if delta > 0 and (min_delta is None or delta < min_delta):
                min_delta = delta
                next_c = c
        except Exception:
            continue
    if next_c:
        hours, remainder = divmod(int(min_delta), 3600)
        minutes = remainder // 60
        await ctx.send(f"Next class: {next_c['name']} in {hours}h {minutes}m.")
    else:
        await ctx.send("No upcoming classes found.")

@bot.command()
async def deleteclass(ctx, name: str):
    """Remove a class from your schedule."""
    user_data = get_user_data(ctx.author.id)
    before = len(user_data["classes"])
    user_data["classes"] = [c for c in user_data["classes"] if c["name"] != name]
    update_user_data(ctx.author.id, user_data)
    after = len(user_data["classes"])
    if before == after:
        await ctx.send(f"No class named '{name}' found.")
    else:
        await ctx.send(f"Class '{name}' deleted.")

@bot.command()
async def setreminder(ctx, name: str, minutes_before: int):
    """Set a custom reminder before class."""
    user_data = get_user_data(ctx.author.id)
    user_data["reminders"].append({"name": name, "minutes_before": minutes_before})
    update_user_data(ctx.author.id, user_data)
    await ctx.send(f"Reminder set for '{name}' {minutes_before} minutes before class.")

@bot.command()
async def todayschedule(ctx):
    """Show only today’s classes."""
    user_data = get_user_data(ctx.author.id)
    today = datetime.datetime.now().strftime("%A")
    todays = [c for c in user_data["classes"] if c["day"].lower() == today.lower()]
    if not todays:
        await ctx.send("No classes today.")
        return
    msg = "**Today's Classes:**\n"
    for c in todays:
        msg += f"- {c['name']} at {c['time']}\n"
    await ctx.send(msg)

#homework
@bot.command()
async def addhw(ctx, name: str, due: str):
    """Add homework or an assignment with a due date (YYYY-MM-DD)."""
    user_data = get_user_data(ctx.author.id)
    user_data["homework"].append({"name": name, "due": due})
    update_user_data(ctx.author.id, user_data)
    await ctx.send(f"Homework '{name}' added, due {due}.")

@bot.command()
async def viewhw(ctx):
    """See a list of upcoming homework."""
    user_data = get_user_data(ctx.author.id)
    if not user_data["homework"]:
        await ctx.send("No homework assigned")
        return
    msg = "**Upcoming Homework:**\n"
    for hw in user_data["homework"]:
        msg += f"- {hw['name']} due {hw['due']}\n"
    await ctx.send(msg)

@bot.command()
async def deletehw(ctx, name: str):
    """Remove a completed assignment."""
    user_data = get_user_data(ctx.author.id)
    before = len(user_data["homework"])
    user_data["homework"] = [hw for hw in user_data["homework"] if hw["name"] != name]
    update_user_data(ctx.author.id, user_data)
    after = len(user_data["homework"])
    if before == after:
        await ctx.send(f"No homework named '{name}' found.")
    else:
        await ctx.send(f"Homework '{name}' deleted.")

@bot.command()
async def due(ctx, days: int):
    """Show homework due within the next X days."""
    user_data = get_user_data(ctx.author.id)
    now = datetime.datetime.now()
    msg = "**Homework due soon:**\n"
    found = False
    for hw in user_data["homework"]:
        try:
            due_date = datetime.datetime.strptime(hw["due"], "%Y-%m-%d")
            if 0 <= (due_date - now).days <= days:
                msg += f"- {hw['name']} due {hw['due']}\n"
                found = True
        except Exception:
            continue
    if found:
        await ctx.send(msg)
    else:
        await ctx.send(f"No homework due in the next {days} days.")

#productivity
TIPS = [
    "Take regular breaks to boost productivity.",
    "Try the Pomodoro technique for focused study.",
    "Stay hydrated and get enough sleep.",
]

@bot.command()
async def tip(ctx):
    """Get a random study, wellness, or time management tip."""
    await ctx.send(random.choice(TIPS))

@bot.command()
async def focusmode(ctx, minutes: int):
    """Set a timer for a study session."""
    await ctx.send(f"Focus mode started for {minutes} minutes. I'll notify you when time's up!")
    await discord.utils.sleep_until(datetime.datetime.now() + datetime.timedelta(minutes=minutes))
    await ctx.send(f"{ctx.author.mention} Focus session ended! Take a break.")

#tools
@bot.command()
async def examcountdown(ctx, name: str, date: str):
    """Days left until a big test/exam (YYYY-MM-DD)."""
    user_data = get_user_data(ctx.author.id)
    user_data["exams"].append({"name": name, "date": date})
    update_user_data(ctx.author.id, user_data)
    now = datetime.datetime.now()
    try:
        exam_date = datetime.datetime.strptime(date, "%Y-%m-%d")
        days_left = (exam_date - now).days
        await ctx.send(f"{days_left} days left until '{name}'!")
    except Exception:
        await ctx.send("Invalid date format. Use YYYY-MM-DD.")

#help
@bot.command()
async def help(ctx):
    """Show all commands."""
    help_msg = """
**Commands:**
!addclass name day time – Add a class (e.g !addclass Math Monday 09:00)
!viewclasses – View all your classes
!nextclass – Show the next upcoming class and time left
!deleteclass name – Remove a class from your schedule
!setreminder name minutes_before – Set a custom reminder before class
!todayschedule – Show only todays classes

!addhw name due_date – Add homework (e.g!addhw MathHW 2025-08-15)
!viewhw – See a list of upcoming homework
!deletehw name – Remove a completed assignment
!due days – Show homework due within the next X days

!tip – Get a random study, wellness, or time management tip
!focusmode minutes – Set a timer for a study session

!examcountdown name date – Days left until a big test/exam

!help – Show all commands and descriptions
!clearall – Reset all data for the user
"""
    await ctx.send(help_msg)

@bot.command()
async def clearall(ctx):
    """Reset all stored data for the user."""
    data = load_data()
    data[str(ctx.author.id)] = {"classes": [], "homework": [], "reminders": [], "exams": []}
    save_data(data)
    await ctx.send("All your data has been reset.")

bot.run(token, log_handler=handler, log_level=logging.DEBUG)