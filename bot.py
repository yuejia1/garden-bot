import os
import telebot
import datetime
import json
import requests
import time

TOKEN = os.environ['BOT_TOKEN']
bot = telebot.TeleBot(TOKEN)

VEGETABLE_TIMES = {
    '生菜🥬': 72, '菠菜🌿': 48, '小葱🧅': 168,
    '番茄🍅': 1440, '辣椒🌶️': 2160, '黄瓜🥒': 720,
    '萝卜🥕': 720, '白菜🥬': 1080, '香菜🌿': 96,
    '韭菜🌱': 360, '芹菜🥬': 1080, '茄子🍆': 1920,
    '豆角🫘': 720, '玉米🌽': 2160, '土豆🥔': 2160
}

# 使用GitHub Gist存储数据
GIST_ID = os.environ.get('GIST_ID', '')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')

def load_plants():
    try:
        url = f'https://api.github.com/gists/{GIST_ID}'
        headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        r = requests.get(url, headers=headers)
        data = r.json()
        content = data['files']['plants.json']['content']
        return json.loads(content)
    except:
        return {}

def save_plants(plants):
    try:
        url = f'https://api.github.com/gists/{GIST_ID}'
        headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        data = {
            'files': {
                'plants.json': {
                    'content': json.dumps(plants, ensure_ascii=False)
                }
            }
        }
        requests.patch(url, headers=headers, json=data)
    except:
        pass

# 创建主键盘
def main_keyboard():
    from telebot import types
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add(
        types.KeyboardButton('🌱 种菜'),
        types.KeyboardButton('📋 我的菜园'),
        types.KeyboardButton('⏰ 成熟提醒'),
        types.KeyboardButton('📖 时间表'),
        types.KeyboardButton('❌ 删除'),
        types.KeyboardButton('ℹ️ 帮助')
    )
    return keyboard

@bot.message_handler(commands=['start'])
def start(message):
    text = """🌿 欢迎来到智能菜园！

点击按钮开始使用：
🌱 种菜 - 记录新种植
📋 我的菜园 - 查看所有蔬菜
⏰ 成熟提醒 - 查看成熟状态"""
    bot.send_message(message.chat.id, text, reply_markup=main_keyboard())

@bot.message_handler(func=lambda m: m.text == '🌱 种菜')
def plant_menu(message):
    from telebot import types
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    veggies = list(VEGETABLE_TIMES.keys())
    buttons = [types.InlineKeyboardButton(v, callback_data=f'plant_{v}') for v in veggies]
    for i in range(0, len(buttons), 3):
        keyboard.add(*buttons[i:i+3])
    keyboard.add(types.InlineKeyboardButton('⏱️ 自定义', callback_data='custom'))
    bot.send_message(message.chat.id, '选择要种的蔬菜：', reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith('plant_'))
def plant_vegetable(call):
    veg = call.data.replace('plant_', '')
    user_id = str(call.from_user.id)
    hours = VEGETABLE_TIMES[veg]
    now = datetime.datetime.now()
    mature = now + datetime.timedelta(hours=hours)
    
    plants = load_plants()
    if user_id not in plants:
        plants[user_id] = []
    
    plants[user_id].append({
        'name': veg,
        'plant_time': now.strftime('%m-%d %H:%M'),
        'mature_time': mature.strftime('%m-%d %H:%M'),
        'mature_timestamp': mature.timestamp(),
        'notified': False
    })
    save_plants(plants)
    
    days = hours / 24
    bot.answer_callback_query(call.id, '✅ 种植成功！')
    bot.edit_message_text(
        f'✅ 已记录：{veg}\n📅 种植：{now.strftime("%m-%d %H:%M")}\n⏰ 成熟：{mature.strftime("%m-%d %H:%M")}\n📊 还需：{days:.1f}天',
        call.message.chat.id,
        call.message.message_id
    )

@bot.callback_query_handler(func=lambda call: call.data == 'custom')
def custom_plant(call):
    bot.answer_callback_query(call.id)
    msg = bot.edit_message_text(
        '发送格式：蔬菜名 小时数\n例如：番茄 1440',
        call.message.chat.id,
        call.message.message_id
    )
    bot.register_next_step_handler(msg, process_custom)

def process_custom(message):
    try:
        parts = message.text.split()
        name = ' '.join(parts[:-1])
        hours = float(parts[-1])
        user_id = str(message.from_user.id)
        now = datetime.datetime.now()
        mature = now + datetime.timedelta(hours=hours)
        
        plants = load_plants()
        if user_id not in plants:
            plants[user_id] = []
        
        plants[user_id].append({
            'name': name,
            'plant_time': now.strftime('%m-%d %H:%M'),
            'mature_time': mature.strftime('%m-%d %H:%M'),
            'mature_timestamp': mature.timestamp(),
            'notified': False
        })
        save_plants(plants)
        
        bot.reply_to(message, f'✅ 已记录：{name}，{hours}小时后成熟')
    except:
        bot.reply_to(message, '格式错误！例如：番茄 1440')

@bot.message_handler(func=lambda m: m.text == '📋 我的菜园')
def my_garden(message):
    user_id = str(message.from_user.id)
    plants = load_plants().get(user_id, [])
    
    if not plants:
        bot.reply_to(message, '菜园还是空的🌱')
        return
    
    text = '🌿 你的菜园：\n\n'
    now = datetime.datetime.now()
    
    for i, p in enumerate(plants, 1):
        mature_time = datetime.datetime.fromtimestamp(p['mature_timestamp'])
        remaining = mature_time - now
        
    for i, p in enumerate(plants, 1):
        mature_time = datetime.datetime.fromtimestamp(p['mature_timestamp'])
        remaining = mature_time - now
        
        if remaining.total_seconds() <= 0:
            status = '✅ 已成熟！'
        else:
            days = remaining.days
            hours = remaining.seconds // 3600
            status = f'⏳ {days}天{hours}小时'
        
        text += f'{p["name"]} #{i}\n  📅种：{p["plant_time"]}\n  ⏰熟：{p["mature_time"]}\n  {status}\n\n'
    
    bot.reply_to(message, text)

@bot.message_handler(func=lambda m: m.text == '⏰ 成熟提醒')
def check_maturity(message):
    user_id = str(message.from_user.id)
    plants = load_plants().get(user_id, [])
    now = datetime.datetime.now()
    
    matured = []
    for i, p in enumerate(plants, 1):
        if datetime.datetime.fromtimestamp(p['mature_timestamp']) <= now:
            matured.append(f'{p["name"]} #{i}')
    
    if matured:
        bot.reply_to(message, '🎉 已成熟可收获：\n' + '\n'.join(matured))
    else:
        bot.reply_to(message, '还没有成熟的蔬菜~')

@bot.message_handler(func=lambda m: m.text == '❌ 删除')
def delete_menu(message):
    user_id = str(message.from_user.id)
    plants = load_plants().get(user_id, [])
    
    if not plants:
        bot.reply_to(message, '没有可删除的记录')
        return
    
    from telebot import types
    keyboard = types.InlineKeyboardMarkup()
    for i, p in enumerate(plants, 1):
        keyboard.add(types.InlineKeyboardButton(
            f'{p["name"]} #{i}', callback_data=f'del_{i}'
        ))
    
    bot.send_message(message.chat.id, '选择要删除的：', reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_'))
def delete_plant(call):
    idx = int(call.data.replace('del_', '')) - 1
    user_id = str(call.from_user.id)
    plants = load_plants()
    
    if user_id in plants and 0 <= idx < len(plants[user_id]):
        deleted = plants[user_id].pop(idx)
        save_plants(plants)
        bot.answer_callback_query(call.id, '已删除')
        bot.edit_message_text(f'✅ 已删除：{deleted["name"]}', call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: m.text == '📖 时间表')
def time_table(message):
    text = '📖 蔬菜成熟时间：\n\n'
    for veg, hours in VEGETABLE_TIMES.items():
        days = hours / 24
        text += f'{veg}: {days:.0f}天\n'
    bot.reply_to(message, text)

@bot.message_handler(func=lambda m: m.text == 'ℹ️ 帮助')
def help_cmd(message):
    bot.reply_to(message, '🌱种菜 📋查看 ⏰提醒 ❌删除\n有问题私聊 @BotFather')

if __name__ == '__main__':
    print('Bot started...')
    while True:
        try:
            bot.infinity_polling()
        except Exception as e:
            print(f'Error: {e}')
            time.sleep(10)5
