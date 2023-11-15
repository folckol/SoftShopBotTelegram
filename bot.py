import asyncio
import datetime
import glob
import logging
import os
import random
import string
import uuid

from aiogram import Bot, Dispatcher, types
from aiogram.utils.deep_linking import create_start_link, decode_payload

from PaymentsData.payment import wait_for_balances_BSC, wait_for_balances_TRON, get_wallet, mark_wallet_busy
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ContentType, \
    InputFile
from aiogram import F
from sqlalchemy import select

from Database.DB import *

folder_path = f'{os.getcwd()}/FilesStorage/Scripts'


logging.basicConfig(level=logging.INFO)
bot = Bot(token="")
dp = Dispatcher()

bot_username = ""
ADMINs_ID = []

class States(StatesGroup):

    wait_choose_action = State()
    wait_title = State()
    wait_description = State()
    wait_files = State()

    wait_edit = State()


def generate_ref_code() -> str:
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(8))

async def get_soft_list_buttons():

    buttons = []
    async with async_session() as session:
        async with session.begin():
            softs = await session.execute(select(Soft))
            softs = softs.scalars().all()
            for soft in softs:
                buttons.append([InlineKeyboardButton(text=soft.title, callback_data=f"SOFT_{soft.callback_title}")])
            buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"back_from_softs")])
            builder = InlineKeyboardMarkup(inline_keyboard=buttons)

            return builder

def get_buy_button(title):

    buttons = [
        [InlineKeyboardButton(text="💳 Оплатить", callback_data=f"buy_{title}"),
         InlineKeyboardButton(text="🔙 Назад", callback_data="👾 Список софтов")]
    ]
    builder = InlineKeyboardMarkup(inline_keyboard=buttons)

    return builder

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext, command: Command = None):
    await state.clear()
    username = message.from_user.username

    async with async_session() as session:
        async with session.begin():
            # user = session.query(User).filter_by(id=message.from_user.id).first()

            user = await session.execute(select(User).where(User.id == message.from_user.id))
            user = user.scalars().first()

            # print(user.id)

    if user:

        buttons = [[InlineKeyboardButton(text="👾 Список софтов", callback_data="👾 Список софтов")],
        [InlineKeyboardButton(text="💸 Рефералка",callback_data="💸 Рефералка")],
        [InlineKeyboardButton(text="🤝 Поддержка", callback_data="🤝 Поддержка")]]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await message.answer(f"<b>Приветствуем вас,</b> @{username} 👋\n\n"
                             "Если возникли какие-либо вопросы, обращайтесь в тех.поддержку: @support\n\n",
                             parse_mode="HTML",
                             reply_markup=keyboard)

    else:


        U = User(id=message.from_user.id,
                 username=message.from_user.username,
                 start_date=datetime.datetime.utcnow())


        # input()
        if command:
            try:
                args = command.args
                reference = decode_payload(args)

                U.referrer_id = int(reference)

            except:
                reference = None

        else:

            reference = None

        async with async_session() as session:
            async with session.begin():
                session.add(U)

                if reference:
                    user = await session.execute(select(User).where(User.id==int(reference)))
                    user = user.scalars().first()

                    user.ref_count += 1

                await session.commit()

        buttons = [[InlineKeyboardButton(text="👾 Список софтов", callback_data="👾 Список софтов")],
                   [InlineKeyboardButton(text="💸 Рефералка", callback_data="💸 Рефералка")],
                   [InlineKeyboardButton(text="🤝 Поддержка", callback_data="🤝 Поддержка")]]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await message.answer(f"<b>Приветствуем вас,</b> @{username} 👋\n\n"
                             "Если возникли какие-либо вопросы, обращайтесь в тех.поддержку: @support\n\n",
                             parse_mode="HTML",
                             reply_markup=keyboard)



@dp.message(F.document)
async def admin_add_files(message: types.Message, state: FSMContext):

    current_state = await state.get_state()
    if current_state == States.wait_files.state:


        if message.document.mime_type == 'application/zip' or message.document.mime_type == 'application/vnd.rar':

            data = await state.get_data()

            file_path = f"{folder_path}/{data['title']}.{'zip' if message.document.mime_type == 'application/zip' else 'rar'}"

            await message.reply("Вы отправили архив. Сохраняю...")

            await bot.download(message.document, destination=file_path)

            buttons = [
                [
                    KeyboardButton(text="Добавить софт"), KeyboardButton(text="Удалить софт")
                ],
                [
                    KeyboardButton(text="Редактировать софт")
                ],
                [
                    KeyboardButton(text="Выйти")
                ]
            ]

            keyboard = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

            await message.reply(f"Софт <b>{data['title']}</b> успешно сохранен и добавлен в список с товарами", parse_mode="HTML", reply_markup=keyboard)

            s = Soft(id=str(uuid.uuid4()),
                    title=data['title'],
                    callback_title=data['title'],
                    price=int(data['price']),
                    description=data['description'],
                    upload_date=datetime.datetime.utcnow())

            async with async_session() as session:
                async with session.begin():
                    # user = session.query(User).filter_by(id=message.from_user.id).first()
                    session.add(s)
                    await session.commit()

            await state.set_state(States.wait_choose_action.state)

    elif current_state == States.wait_edit.state:

        data = await state.get_data()

        os.remove(f"{folder_path}/{data['title']}.{'zip' if message.document.mime_type == 'application/zip' else 'rar'}")
        file_path = f"{folder_path}/{data['title']}.{'zip' if message.document.mime_type == 'application/zip' else 'rar'}"

        await message.reply("Вы отправили архив. Сохраняю...")

        await bot.download(message.document, destination=file_path)

        buttons = [
            [
                KeyboardButton(text="Добавить софт"), KeyboardButton(text="Удалить софт")
            ],
            [
                KeyboardButton(text="Редактировать софт")
            ],
            [
                KeyboardButton(text="Выйти")
            ]
        ]

        keyboard = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

        await message.answer(f"Основной архив софта <b>{data['title']}</b> успешно заменен на новый",
                            parse_mode="HTML", reply_markup=keyboard)
        await state.set_state(States.wait_choose_action.state)


@dp.message(Command("admin"))
async def admin_menu(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINs_ID:
        return


    buttons = [
        [
            KeyboardButton(text="Добавить софт"), KeyboardButton(text="Удалить софт")
        ],
        [
            KeyboardButton(text="Редактировать софт")
        ],
        [
            KeyboardButton(text="Выйти")
        ]
    ]

    keyboard = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

    await message.answer("Вы находить в меню админа, выберите действие", reply_markup=keyboard)
    await state.set_state(States.wait_choose_action.state)

@dp.message(F.text == "Добавить софт")
async def admin_add_soft(message: types.Message, state: FSMContext):
    current_state = await state.get_state()

    if current_state == States.wait_choose_action.state:
        buttons = [
            [
                KeyboardButton(text="Назад")
            ]
        ]
        keyboard = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

        await message.answer('Введите название и ценник для софта (в долларах) в следующем формате: \n<b>ZKSYNC|500</b>', parse_mode="HTML", reply_markup=keyboard)
        await state.set_state(States.wait_title.state)

@dp.message(F.text == "Удалить софт")
async def admin_delete_soft(message: types.Message, state: FSMContext):
    current_state = await state.get_state()

    if current_state == States.wait_choose_action.state:
        buttons = []

        async with async_session() as session:
            async with session.begin():

                softs = await session.execute(select(Soft))
                softs = softs.scalars().all()

                for soft in softs:
                    buttons.append([InlineKeyboardButton(text=soft.title, callback_data=f"DELETE_SOFT_{soft.callback_title}")])
                buttons.append([InlineKeyboardButton(text="Отмена", callback_data=f"back_to_admin_menu")])
                builder = InlineKeyboardMarkup(inline_keyboard=buttons)

                await message.answer('Выберите софт, который хотите удалить', parse_mode="HTML", reply_markup=builder)


@dp.message(F.text == "Редактировать софт")
async def admin_edit_soft(message: types.Message, state: FSMContext):
    current_state = await state.get_state()

    if current_state == States.wait_choose_action.state:
        buttons = []

        async with async_session() as session:
            async with session.begin():

                softs = await session.execute(select(Soft))
                softs = softs.scalars().all()


                for soft in softs:
                    buttons.append([InlineKeyboardButton(text=soft.title, callback_data=f"EDIT_SOFT_{soft.callback_title}")])
                buttons.append([InlineKeyboardButton(text="Отмена", callback_data=f"back_to_admin_menu")])
                builder = InlineKeyboardMarkup(inline_keyboard=buttons)

                await message.answer('Выберите софт, который хотите отредактировать', parse_mode="HTML", reply_markup=builder)

@dp.message(F.text == "Выйти")
async def admin_exit(message: types.Message, state: FSMContext):
    await state.clear()
    username = message.from_user.username

    async with async_session() as session:
        async with session.begin():
            # user = session.query(User).filter_by(id=message.from_user.id).first()

            user = await session.execute(select(User).where(User.id == message.from_user.id))
            user = user.scalars().first()

            # print(user.id)

    if user:

        buttons = [[InlineKeyboardButton(text="👾 Список софтов", callback_data="👾 Список софтов")],
                   [InlineKeyboardButton(text="💸 Рефералка", callback_data="💸 Рефералка")],
                   [InlineKeyboardButton(text="🤝 Поддержка", callback_data="🤝 Поддержка")]]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await message.answer(f"<b>Приветствуем вас,</b> @{username} 👋\n\n"
                             "Если возникли какие-либо вопросы, обращайтесь в тех.поддержку: @support\n\n",
                             parse_mode="HTML",
                             reply_markup=keyboard)

    else:

        U = User(id=message.from_user.id,
                 username=message.from_user.username,
                 start_date=datetime.datetime.utcnow())

        referral_code = message.get_url()
        print(referral_code)
        # input()

        async with async_session() as session:
            async with session.begin():

                if referral_code:
                    reff = await session.execute(select(User).where(User.ref_code==referral_code))
                    reff = reff.scalars().first()
                    if reff.id != message.from_user.id:
                        U.referrer_id = reff.id
                        reff.ref_count += 1


                session.add(U)
                await session.commit()

                buttons = [[InlineKeyboardButton(text="👾 Список софтов", callback_data="👾 Список софтов")],
                           [InlineKeyboardButton(text="💸 Рефералка", callback_data="💸 Рефералка")],
                           [InlineKeyboardButton(text="🤝 Поддержка", callback_data="🤝 Поддержка")]]
                keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

                await message.answer(f"<b>Приветствуем вас,</b> @{username} 👋\n\n"
                                     "Если возникли какие-либо вопросы, обращайтесь в тех.поддержку: @support\n\n",
                                     parse_mode="HTML",
                                     reply_markup=keyboard)


@dp.message()
async def admin_wait_title(message: types.Message, state: FSMContext):
    current_state = await state.get_state()

    if current_state == States.wait_title.state:

        if message.text == "Назад":

            buttons = [
                [
                    KeyboardButton(text="Добавить софт"), KeyboardButton(text="Удалить софт")
                ],
                [
                    KeyboardButton(text="Редактировать софт")
                ],
                [
                    KeyboardButton(text="Выйти")
                ]
            ]

            keyboard = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

            await message.answer("Вы находить в меню админа, выберите действие", reply_markup=keyboard)
            await state.set_state(States.wait_choose_action.state)

        else:

            buttons = [
                [
                    KeyboardButton(text="Назад")
                ]
            ]
            keyboard = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

            title = message.text.split("|")[0]
            price = message.text.split("|")[1]

            await state.update_data(title=title, price=price)
            await message.answer('Введите описание для софта, например: \n<b>Софт делает что то там и что то там...</b>', parse_mode="HTML",
                                 reply_markup=keyboard)

            await state.set_state(States.wait_description.state)

    elif current_state == States.wait_description.state:

        if message.text == "Назад":

            buttons = [
                [
                    KeyboardButton(text="Назад")
                ]
            ]
            keyboard = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

            await message.answer('Введите название и ценник для софта (в долларах) в следующем формате: \n<b>ZKSYNC|500</b>', parse_mode="HTML",
                                 reply_markup=keyboard)
            await state.set_state(States.wait_title.state)

        else:

            buttons = [
                [
                    KeyboardButton(text="Назад")
                ]
            ]
            keyboard = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

            description = message.text

            await state.update_data(description=description)
            await message.answer('Внесите <i>zip/rar</i> файл с всеми файлами, нужными при работе софта',
                                 parse_mode="HTML",
                                 reply_markup=keyboard)

            await state.set_state(States.wait_files.state)

    elif current_state == States.wait_files.state:

        if message.text == "Назад":

            buttons = [
                [
                    KeyboardButton(text="Назад")
                ]
            ]
            keyboard = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

            title = message.text.split("|")[0]
            price = message.text.split("|")[1]

            await state.update_data(title=title, price=price)
            await message.answer('Введите описание для софта, например: \n<b>Софт делает что то там и что то там...</b>',
                                 parse_mode="HTML",
                                 reply_markup=keyboard)

            await state.set_state(States.wait_description.state)


    elif current_state == States.wait_edit.state:

        data = await state.get_data()

        category = data['category']
        t = data['title']

        if category == "NAME":

            async with async_session() as session:
                async with session.begin():

                    soft = await session.execute(select(Soft).where(Soft.title==str(t)))
                    soft = soft.scalars().first()

                    soft.title = message.text
                    soft.callback_title = message.text

                    await session.commit()


            file_path_1 = f"{folder_path}/{t}.zip"
            file_path_1_new = f"{folder_path}/{message.text}.zip"

            file_path_2 = f"{folder_path}/{t}.rar"
            file_path_2_new = f"{folder_path}/{message.text}.rar"

            try:
                os.rename(file_path_1, file_path_1_new)
            except:
                os.rename(file_path_2, file_path_2_new)

        elif category == "DESCRIPTION":
            async with async_session() as session:
                async with session.begin():
                    soft = await session.execute(select(Soft).where(Soft.title == str(t)))
                    soft = soft.scalars().first()

                    soft.description = message.text

                    await session.commit()

        buttons = [
            [
                KeyboardButton(text="Добавить софт"), KeyboardButton(text="Удалить софт")
            ],
            [
                KeyboardButton(text="Редактировать софт")
            ],
            [
                KeyboardButton(text="Выйти")
            ]
        ]

        keyboard = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

        await message.answer("Вы успешно изменили {} софта".format("название" if category == "NAME" else "описание"), parse_mode="HTML", reply_markup=keyboard)
        await state.set_state(States.wait_choose_action.state)



#
#
#  КОЛБЭКИ


@dp.callback_query(F.data == "👾 Список софтов")
async def soft_list(callback: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback.id)

    keyboard = await get_soft_list_buttons()

    await callback.message.edit_text("<b>Список софтов в продаже</b>\n\n"
                         "Чтобы получить более подробную информацию о интересующем софте, нажмите соответсвующую кнопку 👇",
                         parse_mode="HTML",
                         reply_markup=keyboard)


@dp.callback_query(F.data == "back_from_softs")
async def soft_list_(callback: types.CallbackQuery):
    await bot.answer_callback_query(callback.id)

    buttons = [[InlineKeyboardButton(text="👾 Список софтов", callback_data="👾 Список софтов")],
               [InlineKeyboardButton(text="💸 Рефералка", callback_data="💸 Рефералка")],
               [InlineKeyboardButton(text="🤝 Поддержка", callback_data="🤝 Поддержка")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(f"<b>Приветствуем вас</b>, @{callback.from_user.username} 👋\n\n"
                         "Если возникли какие-либо вопросы, обращайтесь в тех.поддержку: @support\n\n",
                         parse_mode="HTML",
                         reply_markup=keyboard)


@dp.callback_query(F.data[:12] == "DELETE_SOFT_")
async def soft_deleting(callback: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback.id)

    current_state = await state.get_state()

    if current_state == States.wait_choose_action.state:
        t = callback.data.split("DELETE_SOFT_")[-1]

        async with async_session() as session:
            async with session.begin():

                softs = await session.execute(select(Soft).where(Soft.callback_title==t))
                softs = softs.scalars().all()

                for soft in softs:
                    await session.delete(soft)

                await session.commit()

        buttons = [
            [
                KeyboardButton(text="Добавить софт"), KeyboardButton(text="Удалить софт")
            ],
            [
                KeyboardButton(text="Редактировать софт")
            ],
            [
                KeyboardButton(text="Выйти")
            ]
        ]

        keyboard = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

        for file_path in glob.glob(f"{folder_path}/{t}.*"):
            try:
                os.remove(file_path)
            except:
                pass

        await callback.message.edit_text(f"Вы успешно удалили софт <b>{t}</b>", parse_mode="HTML", reply_markup=None)
        await callback.message.answer("Вы находить в меню админа, выберите действие", reply_markup=keyboard)
        await state.set_state(States.wait_choose_action.state)


@dp.callback_query(F.data[:10] == "EDIT_SOFT_")
async def soft_edit(callback: types.CallbackQuery, state: FSMContext):

    await bot.answer_callback_query(callback.id)

    current_state = await state.get_state()

    if current_state == States.wait_choose_action.state:
        t = callback.data.split("EDIT_SOFT_")[-1]

        buttons = [
            [
                InlineKeyboardButton(text="Название", callback_data=f"EDIT:NAME:{t}"),
                InlineKeyboardButton(text="Файл", callback_data=f"EDIT:FILE:{t}")
            ],
            [
                InlineKeyboardButton(text="Описание", callback_data=f"EDIT:DESCRIPTION:{t}")
            ],
            [
                InlineKeyboardButton(text="Отмена", callback_data="back_to_admin_menu")
            ]
        ]

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text(f"Выберите атрибут, который хотите изменить в софте <b>{t}</b>",
                                         parse_mode="HTML", reply_markup=keyboard)


@dp.callback_query(F.data[:5] == "EDIT:")
async def soft_edit_distributor(callback: types.CallbackQuery, state: FSMContext):

    await bot.answer_callback_query(callback.id)

    category = callback.data.split(':')[1]
    t = callback.data.split(':')[2]

    if category in ["NAME", "DESCRIPTION"]:
        buttons = [

            [
                InlineKeyboardButton(text="Отмена", callback_data="back_to_admin_menu")
            ]
        ]

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await state.update_data(category=category,
                                title=t)

        await callback.message.edit_text("Введите новое {} софта".format("название" if category == "NAME" else "описание"), reply_markup=keyboard)
        await state.set_state(States.wait_edit.state)

    elif category == "FILE":

        buttons = [

            [
                InlineKeyboardButton(text="Отмена", callback_data="back_to_admin_menu")
            ]
        ]

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await state.update_data(category=category,
                                title=t)

        await callback.message.edit_text(
            "Пришлите новый архив в формате <i>zip</i> или <i>rar</i> для замены старого файла скрипта", reply_markup=keyboard)
        await state.set_state(States.wait_edit.state)





@dp.callback_query(F.data == "back_to_admin_menu")
async def back_to_admin_menu(callback: types.CallbackQuery, state: FSMContext):

    await bot.answer_callback_query(callback.id)

    buttons = [
        [
            KeyboardButton(text="Добавить софт"), KeyboardButton(text="Удалить софт")
        ],
        [
            KeyboardButton(text="Редактировать софт")
        ],
        [
            KeyboardButton(text="Выйти")
        ]
    ]

    keyboard = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

    await callback.message.answer("Вы находить в меню админа, выберите действие", reply_markup=keyboard)
    await state.set_state(States.wait_choose_action.state)



@dp.callback_query(F.data[:5] == "SOFT_")
async def soft_choosing(callback: types.CallbackQuery):
    await bot.answer_callback_query(callback.id)

    async with async_session() as session:
        async with session.begin():
            soft = await session.execute(select(Soft).where(Soft.callback_title==callback.data.split("SOFT_")[-1]))
            soft = soft.scalars().first()

            await callback.message.edit_text(f"Описание: <i>{soft.description}</i>\n\n"
                                             f"Стоимость: <b>{soft.price}$</b>", parse_mode="HTML", reply_markup=get_buy_button(soft.callback_title))


@dp.callback_query(F.data[:4] == "buy_")
async def soft_buy(callback: types.CallbackQuery):
    await bot.answer_callback_query(callback.id)



    title = callback.data.split('_', 1)[-1]

    async with async_session() as session:
        async with session.begin():
            soft = await session.execute(select(Soft).where(Soft.callback_title==title))
            soft = soft.scalars().first()

            name = soft.title
            price = soft.price

            buttons = [
                [InlineKeyboardButton(text="Tron TRC-20 USDT", callback_data=f"payment:tron:{price}:{name}")],
                [InlineKeyboardButton(text="BSC BEP-20 USDT", callback_data=f"payment:bsc:{price}:{name}")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_soft")]
            ]

            builder = InlineKeyboardMarkup(inline_keyboard=buttons)

            await callback.message.edit_text(f'Вы выбрали товар "{name}"\n\nВыберите способ оплаты:', reply_markup=builder)

@dp.callback_query(F.data[:8] == "payment:")
async def payment(callback: types.CallbackQuery):
    await bot.answer_callback_query(callback.id)

    async with async_session() as session:
        async with session.begin():

            payment_ = await session.execute(select(Task).where(Task.user_id == callback.from_user.id))
            payment_ = payment_.scalars().first()

            if payment_:

                await callback.message.answer("На данный вы уже открыли платежную задачу. Завершите предыдущую перед тем как открыть новую")

            else:

                buttons = [
                    [InlineKeyboardButton(text="Отменить пополнение", callback_data=f"cancel_payment:{callback.from_user.id}")]
                ]
                keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

                t = Task(id=str(uuid.uuid4()),
                         user_id=callback.from_user.id)
                session.add(t)
                await session.commit()

                network = callback.data.split(":")[1]
                price = int(callback.data.split(":")[2])
                title = callback.data.split(":")[3]

                if network == 'tron':
                    wallet, private = await get_wallet("TRON")

                    await mark_wallet_busy(wallet, busy=True)

                    print(wallet, private)
                    input_file = FSInputFile(f"{os.getcwd()}/FilesStorage/QRs/{wallet}.png")
                    await callback.message.answer_photo(photo=input_file,
                                                        caption=f"Пополните на <b>{price}$</b> данный кошелек в течении 10 минут:\n\n"
                                                          f"<b>{wallet}</b>\n\n"
                                                          f"Сеть пополнения: <b>TRC20</b>\n\n"
                                                          f"<i>Осуществляйте пополнение так, чтобы на кошелек поступило только количество большее или равное указанной сумме</i>",
                                                        parse_mode="HTML",
                                                        reply_markup=keyboard)
                    await wait_for_balances_TRON(bot, title, wallet, private, callback.from_user.id, price)



                else:
                    wallet, private = await get_wallet("BSC")

                    await mark_wallet_busy(wallet, busy=True)

                    print(wallet, private)
                    input_file = FSInputFile(f"{os.getcwd()}/FilesStorage/QRs/{wallet}.png")
                    await callback.message.answer_photo(photo=input_file,
                                                        caption=f"Пополните на <b>{price}$</b> данный кошелек в течении 10 минут:\n\n"
                                                                f"<b>{wallet}</b>\n\n"
                                                                f"Сеть пополнения: <b>BEP20</b>\n\n"
                                                                f"<i>Осуществляйте пополнение так, чтобы на кошелек поступило только количество большее или равное указанной сумме</i>",
                                                        parse_mode="HTML",
                                                        reply_markup=keyboard)
                    await wait_for_balances_BSC(bot, title, "https://bsc-dataseed.binance.org/", wallet, callback.from_user.id, {"USDT": "0x55d398326f99059ff775485246999027b3197955"},{'USDT': price})


@dp.callback_query(F.data[:14] == "cancel_payment")
async def payment(callback: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback.id)

    user_id = int(callback.data.split(':')[-1])

    async with async_session() as session:
        async with session.begin():
            task = await session.execute(select(Task).where(Task.user_id == user_id))
            task = task.scalars().first()

            await session.delete(task)
            await session.commit()



    await state.clear()
    username = callback.message.from_user.username

    async with async_session() as session:
        async with session.begin():
            # user = session.query(User).filter_by(id=message.from_user.id).first()

            user = await session.execute(select(User).where(User.id == callback.from_user.id))
            user = user.scalars().first()

            # print(user.id)

    if user:

        buttons = [[InlineKeyboardButton(text="👾 Список софтов", callback_data="👾 Список софтов")],
                   [InlineKeyboardButton(text="💸 Рефералка", callback_data="💸 Рефералка")],
                   [InlineKeyboardButton(text="🤝 Поддержка", callback_data="🤝 Поддержка")]]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.answer("Оплата отменена, вы вернулись в главное меню", reply_markup=keyboard)
        await callback.message.delete()

    else:

        U = User(id=callback.message.from_user.id,
                 username=callback.message.from_user.username,
                 start_date=datetime.datetime.utcnow())

        referral_code = callback.message.get_url()
        print(referral_code)
        # input()
        if referral_code:
            reff = session.query(User).filter_by(ref_code=referral_code).first()
            if reff.id != callback.from_user.id:
                U.referrer_id = reff.id
                reff.ref_count += 1

        async with async_session() as session:
            async with session.begin():
                session.add(U)
                await session.commit()

        buttons = [[InlineKeyboardButton(text="👾 Список софтов", callback_data="👾 Список софтов")],
                   [InlineKeyboardButton(text="💸 Рефералка", callback_data="💸 Рефералка")],
                   [InlineKeyboardButton(text="🤝 Поддержка", callback_data="🤝 Поддержка")]]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.answer("Оплата отменена, вы вернулись в главное меню", reply_markup=keyboard)
        await callback.message.delete()

@dp.callback_query(F.data == "back_to_soft")
async def soft_list_(callback: types.CallbackQuery):
    await bot.answer_callback_query(callback.id)

    keyboard = await get_soft_list_buttons()

    await callback.message.edit_text("<b>Список софтов в продаже</b>\n\n"
                                     "Чтобы получить более подробную информацию о интересующем софте, нажмите соответсвующую кнопку 👇",
                                     parse_mode="HTML",
                                     reply_markup=keyboard)

@dp.callback_query(F.data == "💸 Рефералка")
async def referral(callback: types.CallbackQuery):
    await bot.answer_callback_query(callback.id)

    async with async_session() as session:
        async with session.begin():

            user = await session.execute(select(User).where(User.id==callback.from_user.id))
            user = user.scalars().first()

            if user.ref_code == None:
                ref_code = generate_ref_code()
                user.ref_code = ref_code
                await session.commit()
            else:
                ref_code = user.ref_code

            ref_count = user.ref_count
            ref_rewards = user.ref_rewards

            link = await create_start_link(bot, str(callback.from_user.id), encode=True)

    buttons = [[InlineKeyboardButton(text="🔙 Назад", callback_data=f"back_from_softs")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text("❗️ Приглашайте людей покупать наши продукты и зарабатывайте по 10% с каждой продажи!\n\n"
                                         f"🔗 Ваша реферальная ссылка:\n<i>{link}</i>\n\n"
                                     f"👤 Всего рефералов: <b>{ref_count}</b>\n"
                                     f"💵 Заработано: <b>{ref_rewards}$</b>", parse_mode="HTML", reply_markup=keyboard)


@dp.callback_query(F.data == "🤝 Поддержка")
async def support(callback: types.CallbackQuery):

    buttons = [[InlineKeyboardButton(text="🔙 Назад", callback_data=f"back_from_softs")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text("📨 По всем интересующим вопросам — @support", reply_markup=keyboard)



async def main():

    await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)

if __name__ == "__main__":

    asyncio.run(main())
