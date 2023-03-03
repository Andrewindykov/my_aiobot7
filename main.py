import sqlite3 as sq

from aiogram import Bot, types
# для машины состояний
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
# для клавы
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils import executor

storage = MemoryStorage()

bot = Bot(token="5927116764:AAHFeAzrBv_u-uBJE1_e1eqk9GDlcGU6j04")
dp = Dispatcher(bot, storage=storage)


async def on_startup(_):
    print('Бот вышел в онлайн')
    sql_start()


'''******************************КЛИЕНТСКАЯ ЧАСТЬ*******************************************'''
# для клавы
b1 = KeyboardButton('/Режим_работы')
b2 = KeyboardButton('/Расположение')
b3 = KeyboardButton('/Меню')
b4 = KeyboardButton('Поделиться номером', request_contact=True)
b5 = KeyboardButton('Отправить где я', request_location=True)

# кнопки Админа
button_load = KeyboardButton('/Загрузить')
button_delete = KeyboardButton('/Удалить')

button_case_admin = ReplyKeyboardMarkup(resize_keyboard=True).add(button_load).add(button_delete)

# kb_client = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
# выше - одноразовая клавиатура
kb_client = ReplyKeyboardMarkup(resize_keyboard=True)

# kb_client.add(b1).add(b2).insert(b3)
kb_client.row(b1, b2, b3).row(b4, b5)


@dp.message_handler(commands=['start', 'help'])
async def command_start(message: types.Message):
    try:
        await bot.send_message(message.from_user.id, 'Приятного аппетита', reply_markup=kb_client)
        await message.delete()
    except Exception:
        await message.reply('Общение с ботом через ЛС, напишите ему:\nhttps://t.me/mashenka500_bot')


@dp.message_handler(commands=['Режим_работы'])
async def pizza_open_command(message: types.Message):
    await bot.send_message(message.from_user.id, 'Вс-Чт с 9:00 до 20:00, Пт-Сб с 10:00 до 23:00')


@dp.message_handler(commands=['Расположение'])
async def pizza_place_command(message: types.Message):
    await bot.send_message(message.from_user.id, 'ул. Колбасная 15', reply_markup=ReplyKeyboardRemove())


@dp.message_handler(commands=['Меню'])
async def pizza_menu_command(message: types.Message):
    # перенесли к базе данных
    # for ret in cur.execute('SELECT * FROM menu').fetchall():
    #    await bot.send_photo(message.from_user.id, ret[0], f'{ret[1]}\n#Описание:# {ret[2]}\n*Цена* {ret[-1]}')
    await sql_read(message)


'''*******************************АДМИНСКАЯ ЧАСТЬ*******************************************'''
ID = 954230772 # это мой айдишник. пока кто то не заявит права на модераторство - все заявки шлются сюдой
base = cur = None


def sql_start():
    global base, cur
    base = sq.connect('pizza_cool.db')
    cur = base.cursor()
    if base:
        print('Data base connect OK!')
    base.execute('CREATE TABLE IF NOT EXISTS menu(img TEXT, name TEXT PRIMARY KEY, description TEXT, price TEXT)')
    base.commit()


async def sql_add_command(state):
    global base, cur
    async with state.proxy() as data:
        print(tuple(data.values()))
        cur.execute('INSERT INTO menu VALUES (?, ?, ?, ?)', tuple(data.values()))
        base.commit()


async def sql_read(message):
    global base, cur
    for ret in cur.execute('SELECT * FROM menu').fetchall():
        await bot.send_photo(message.from_user.id, ret[0], f'{ret[1]}\nОписание:  {ret[2]}\nЦена:  {ret[-1]}')
        await bot.send_message(message.from_user.id, text='^^^', reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton(f'Заказать {ret[1]}', callback_data=f'request {ret[1]}')))
        await bot.send_photo(message.from_user.id, ret[0], f' \n ')


async def sql_read2():
    global base, cur
    return cur.execute('SELECT * FROM menu').fetchall()


async def sql_count():
    global base, cur
    x = cur.execute('SELECT COUNT (*) FROM menu').fetchall()
    return x[0][0]  # потому что это список из одного кортежа, в котором 1 число


async def sql_delete_command(data):
    global base, cur
    cur.execute('DELETE FROM menu WHERE name == ?', (data,))
    base.commit()


# для машины состояний
class FSMAdmin(StatesGroup):
    photo = State()
    name = State()
    description = State()
    price = State()


# а получим ка айдишник модератора
# @dp.message_handler(commands=['moderator'], is_chat_admin=True)
@dp.message_handler(commands=['moderator'])
async def make_changes_command(message: types.Message):
    global ID
    ID = message.from_user.id
    await bot.send_message(message.from_user.id, "Что. Хозяин. Надо???", reply_markup=button_case_admin)
    # await message.delete() # работает только когда админ чата


# Начало диалога загрузки нового пункта меню
@dp.message_handler(commands='Загрузить', state=None)
async def cm_start(message: types.Message):
    if message.from_user.id == ID:
        await FSMAdmin.photo.set()
        await message.reply('Загрузи фото')


# Ловим "Галя - отмена!" ответ
@dp.message_handler(state="*", commands='отмена')
@dp.message_handler(Text(equals='отмена', ignore_case=True), state="*")
async def cancel_handler(message: types.Message, state: FSMContext):
    if message.from_user.id == ID:
        current_state = await state.get_state()
        if current_state is None:
            return
        await state.finish()
        await message.reply("OK, отменил")


# Ловим первый ответ и пишем в словарь
@dp.message_handler(content_types=['photo'], state=FSMAdmin.photo)
async def load_photo(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['photo'] = message.photo[0].file_id
    await FSMAdmin.next()
    await message.reply("Теперь - название")


# Ловим 2 ответ и тожи пишем в словарь
@dp.message_handler(state=FSMAdmin.name)
async def load_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
    await FSMAdmin.next()
    await message.reply("Жду описание")


# Ловим 3 ответ
@dp.message_handler(state=FSMAdmin.description)
async def load_description(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['description'] = message.text
    await FSMAdmin.next()
    await message.reply("Жду цену")


# Ловим 4, последний ответ и юзаем это всё
@dp.message_handler(state=FSMAdmin.price)
async def load_price(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['price'] = float(message.text)

    # async with state.proxy() as data: # просто выводим в ответку данные
    #    await message.reply(str(data))

    await sql_add_command(state)

    await state.finish()  # ахтунг! тута данные – того, Ёк!
    print('добавили')
    await message.reply(f"Всё норм! {await sql_count()} пиццов в меню")


# request {ret[1]}
@dp.callback_query_handler(lambda x: x.data and x.data[:8] == 'request ')
async def req_callback_run(callback_query: types.CallbackQuery):
    global ID
#    print(callback_query)
    print(f"Заказали в меню")
    await callback_query.message.answer(
        text=f'"{callback_query.data.replace("request ", "")}" заказана \nОжидайте 44 минутки   ')
    await callback_query.answer(text=f'{callback_query.data.replace("request ", "")} заказана!')
    # теперь кинем модератору заявку
    await bot.send_message(ID,
                           f'Там это похавать заказали "{callback_query.data.replace("request ", "")}".  Это сделал id={callback_query["from"]["id"]}  {callback_query["from"]["first_name"]} {callback_query["from"]["last_name"]} @{callback_query["from"]["username"]}')


@dp.callback_query_handler(lambda x: x.data and x.data[:4] == 'del ')
async def del_callback_run(callback_query: types.CallbackQuery):
    #print(callback_query)
    await sql_delete_command(callback_query.data.replace('del ', ''))
    x = await sql_count()
    print(f"Осталось {x} пиццов в меню")
    await callback_query.message.answer(
        text=f'{callback_query.data.replace("del ", "")} удалена \nОсталось {x} пиццов в меню   ')
    await callback_query.answer(text=f'{callback_query.data.replace("del ", "")} удалена')


@dp.message_handler(commands='Удалить')
async def delete_item(message: types.Message):
    if message.from_user.id == ID:
        read = await sql_read2()
        for ret in read:
            await bot.send_photo(message.from_user.id, ret[0], f'{ret[1]}\n*Описание:* {ret[2]}\n*Цена* {ret[-1]}')
            await bot.send_message(message.from_user.id, text='^^^', reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton(f'Удалить {ret[1]}', callback_data=f'del {ret[1]}')))


'''*********************************ОБЩАЯ ЧАСТЬ*********************************************'''


@dp.message_handler()
async def echo_send(message: types.Message):
    if message.text == 'Привет':
        await message.answer('И тебе привет!')


# await message.reply(message.text)
# await bot.send_message(message.from_user.id, message.text)


executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
