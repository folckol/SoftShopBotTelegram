import os
import random
import threading
import uuid

import requests
from aiogram.client.session import aiohttp
from aiogram.types import InputFile
from flask import Flask, request, jsonify
from sqlalchemy import select, and_
from qrcode import QRCode
import sqlite3
import json
import time
from web3 import Web3

from SoftShopBotTelegram.Database.DB import async_session, Task, User
from SoftShopBotTelegram.PaymentsData.walletsDB import *

ADMINs_ID = [649811235, 199804475, 733000248]

# from eth_utils import to_checksum_address


ERC20_ABI = json.loads('[{"inputs":[],"payable":false,"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"owner","type":"address"},{"indexed":true,"internalType":"address","name":"spender","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"previousOwner","type":"address"},{"indexed":true,"internalType":"address","name":"newOwner","type":"address"}],"name":"OwnershipTransferred","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"from","type":"address"},{"indexed":true,"internalType":"address","name":"to","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Transfer","type":"event"},{"constant":true,"inputs":[],"name":"_decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"_name","outputs":[{"internalType":"string","name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"_symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"burn","outputs":[{"internalType":"bool","name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"subtractedValue","type":"uint256"}],"name":"decreaseAllowance","outputs":[{"internalType":"bool","name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"getOwner","outputs":[{"internalType":"address","name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"addedValue","type":"uint256"}],"name":"increaseAllowance","outputs":[{"internalType":"bool","name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"mint","outputs":[{"internalType":"bool","name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"owner","outputs":[{"internalType":"address","name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[],"name":"renounceOwnership","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transfer","outputs":[{"internalType":"bool","name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"sender","type":"address"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transferFrom","outputs":[{"internalType":"bool","name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"newOwner","type":"address"}],"name":"transferOwnership","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"}]')
TRONGRID_API = 'https://api.trongrid.io/v1'
USDT_CONTRACT = 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t'  # USDT контракт на сети Tron
CHECK_INTERVAL = 60  # Время между проверками в секундах (60 секунд)
TIMEOUT = 10 * 60  # Время ожидания в секундах (10 минут)

app = Flask(__name__)


# Configure Binance Smart Chain
w3 = Web3(Web3.HTTPProvider('https://bsc-dataseed.binance.org/'))



async def insert_wallet(wallet):

    wallet = Wallet(id=str(uuid.uuid4()),
                    network=wallet['network'],
                    address=wallet['address'],
                    private_key=wallet['private_key'])

    async with async_wallet_session() as session:
        async with session.begin():

            session.add(wallet)
            await session.commit()

async def mark_wallet_busy(wallet, busy=True):

    async with async_wallet_session() as session:
        async with session.begin():

            w = await session.execute(select(Wallet).where(Wallet.address==str(wallet)))
            w = w.scalars().first()

            w.is_busy = busy
            await session.commit()

async def get_wallet(network):

    async with async_wallet_session() as session:
        async with session.begin():

            all_wallets = await session.execute(select(Wallet).where(and_(Wallet.is_busy==False,
                                                                          Wallet.network==network)
                                                                     ))
            all_wallets = all_wallets.scalars().all()

            wallet = random.choice(all_wallets)
            address = wallet.address
            private = wallet.private_key

            return address, private


def generate_wallets(network, count=100):
    wallets = []
    if network == 'BSC':

        for _ in range(count):
            acct = w3.eth.account.create()
            wallets.append({
                'network': network,
                'address': acct.address,
                'private_key': acct._private_key.hex()
            })
    elif network == 'TRON':

        data = []
        with open('walletsTron.txt', 'r') as file:
            for i in file:
                data.append(i.strip('\n'))

        for _ in range(count):
            acct = data[_]
            wallets.append({
                'network': network,
                'address': acct.split(' ')[0],
                'private_key': acct.split(' ')[1]
            })

    return wallets


def firstTime():

    wallets_bsc = generate_wallets('BSC', 100)
    wallets_tron = generate_wallets('TRON', 100)
    for wallet in wallets_bsc + wallets_tron:
        asyncio.run(insert_wallet(wallet))

    for wallet in wallets_bsc + wallets_tron:
        generate_qr_code(wallet['address'])

def generate_qr_code(address):
    qr = QRCode()
    qr.add_data(address)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(fr"C:\Users\User\PycharmProjects\AdsPower\SoftShopBotTelegram\FilesStorage\QRs\{address}.png")


async def wait_for_balances_BSC(
        bot,
    title,
    rpc_url: str,
    wallet_address: str,
    user_id: int,
    token_addresses: dict,
    expected_amounts: dict,
    decimals: int = 18,
    timeout: int = 600,

):
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    wallet_address = w3.to_checksum_address(wallet_address)
    token_contracts = {
        symbol: w3.eth.contract(address=w3.to_checksum_address(address), abi=ERC20_ABI)
        for symbol, address in token_addresses.items()
    }

    start_amounts = {
        symbol: contract.functions.balanceOf(wallet_address).call() for symbol, contract in token_contracts.items()
    }

    target_amounts = {
        symbol: int(amount * (10 ** decimals))+start_amounts[symbol] for symbol, amount in expected_amounts.items()
    }

    start_time = time.time()
    while time.time() - start_time < timeout:
        all_balances_reached = True

        async with async_session() as session:
            async with session.begin():
                task = await session.execute(select(Task).where(Task.user_id == int(user_id)))
                task = task.scalars().first()

                if task == None:
                    await mark_wallet_busy(wallet_address, busy=False)

                    return

        for symbol, contract in token_contracts.items():

            balance = contract.functions.balanceOf(wallet_address).call()
            # print(symbol, balance, target_amounts[symbol])

            if balance < target_amounts[symbol]:

                all_balances_reached = False
                break

        if all_balances_reached:
            # print("Успех! Балансы кошелька достигли целей.")
            # requests.post('')
            await mark_wallet_busy(wallet_address, busy=False)

            await bot.send_message(chat_id=user_id, text=f"Вы успешно осуществили оплату софта <b>{title}</b>",
                                   parse_mode="HTML")
            await bot.send_document(chat_id=user_id, document=InputFile(f"FilesStorage/Scripts/{title}.zip"))

            async with async_session() as session:
                async with session.begin():
                    task = await session.execute(select(Task).where(Task.user_id == int(user_id)))
                    task = task.scalars().first()

                    await session.delete(task)

                    ref = await session.execute(select(User).where(User.id == int(user_id)))
                    ref = ref.scalars().first()

                    if ref.referrer_id:

                        user = await session.execute(select(User).where(User.id == int(ref.referrer_id)))
                        user = user.scalars().first()

                        user.ref_rewards += int(int(expected_amounts['USDT'])*0.05)
                        ref.ref_rewards += int(int(expected_amounts['USDT'])*0.05)

                    await session.commit()

            for admin in ADMINs_ID:
                await bot.send_message(chat_id=admin,
                                       text="Пользователь <b>{}</b> совершил покупку софта <b>{}</b> на сумму <b>{}$</b>\n\n"
                                            "Адресс: <b>{}</b>".format(
                                           user_id, title, int(expected_amounts['USDT']), wallet_address), parse_mode="HTML")


            return

        await asyncio.sleep(5)

    # print("Таймаут истек. Балансы кошелька не достигли целей.")
    await mark_wallet_busy(wallet_address, busy=False)

    await bot.send_message(chat_id=user_id,
                           text=f"Время, выделенное для осуществления оплаты, вышло, осуществите покупку заново",
                           parse_mode="HTML")

    async with async_session() as session:
        async with session.begin():
            task = await session.execute(select(Task).where(Task.user_id == int(user_id)))
            task = task.scalars().first()

            session.delete(task)
            await session.commit()

    # requests.post('')


async def get_token_balance(address, contract_address):

    url = f'{TRONGRID_API}/accounts/{address}/assets'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()

            for token in data.get('data', []):
                if token['key'] == contract_address:
                    return int(token['value']) / 10 ** 6  # Количество USDT может быть с 6 десятичными знаками

            return 0


async def wait_for_balances_TRON(bot, title, wallet, private, user_id, amount, timeout=600):
    start_time = time.time()
    start_balance = await get_token_balance(wallet, USDT_CONTRACT)

    while time.time() - start_time < TIMEOUT:

        async with async_session() as session:
            async with session.begin():
                task = await session.execute(select(Task).where(Task.user_id == int(user_id)))
                task = task.scalars().first()

                if task == None:
                    await mark_wallet_busy(wallet, busy=False)

                    return

        balance = await get_token_balance(wallet, USDT_CONTRACT)
        # print(f'Текущий баланс USDT: {balance:.6f}')
        if balance-start_balance > amount:
            # print(f'Кошелек пополнен на {balance:.6f} USDT!')

            await mark_wallet_busy(wallet, busy=False)

            await bot.send_message(chat_id=user_id, text=f"Вы успешно осуществили оплату софта <b>{title}</b>",
                                   parse_mode="HTML")
            await bot.send_document(chat_id=user_id, document=InputFile(f"FilesStorage/Scripts/{title}.zip"))

            async with async_session() as session:
                async with session.begin():
                    task = await session.execute(select(Task).where(Task.user_id == int(user_id)))
                    task = task.scalars().first()

                    await session.delete(task)

                    ref = await session.execute(select(User).where(User.id == int(user_id)))
                    ref = ref.scalars().first()

                    if ref.referrer_id:
                        user = await session.execute(select(User).where(User.id == int(ref.referrer_id)))
                        user = user.scalars().first()

                        user.ref_rewards += int(int(amount)*0.05)
                        ref.ref_rewards += int(int(amount)*0.05)

                    await session.commit()

            for admin in ADMINs_ID:
                await bot.send_message(chat_id=admin,
                                       text="Пользователь <b>{}</b> совершил покупку софта <b>{}</b> на сумму <b>{}$</b>\n\n"
                                            "Адресс: <b>{}</b>".format(
                                           user_id, title, amount, wallet), parse_mode="HTML")

            # requests.post('')

            return

        await asyncio.sleep(5)

    await mark_wallet_busy(wallet, busy=False)

    await bot.send_message(chat_id=user_id, text=f"Время, выделенное для осуществления оплаты, вышло, осуществите покупку заново",
                           parse_mode="HTML")

    async with async_session() as session:
        async with session.begin():

            task = await session.execute(select(Task).where(Task.user_id==int(user_id)))
            task = task.scalars().first()

            session.delete(task)
            await session.commit()

    # requests.post('')


@app.route('/replenish_balance', methods=['POST'])
def replenish_balance():
    if request.method == 'POST':
        user_id = request.json['user_id']
        amount = request.json['amount']
        coin = request.json['coin']
        network = request.json['network']

        wallet, private = get_wallet(network)
        print(wallet, private)
        mark_wallet_busy(wallet)


        if network == 'BSC' and coin == 'USDT':
            t = threading.Thread(target=wait_for_balances_BSC,
                                 args=("https://bsc-dataseed.binance.org/", wallet, user_id, {"USDT": "0x55d398326f99059ff775485246999027b3197955"},{'USDT': amount}))
            t.start()
        elif network == 'BSC' and coin == 'BUSD':
            t = threading.Thread(target=wait_for_balances_BSC,
                                 args=("https://bsc-dataseed.binance.org/", wallet, user_id, {"BUSD": "0xe9e7cea3dedca5984780bafc599bd69add087d56"},{'BUSD': amount}))
            t.start()
        elif network == 'TRON' and coin == 'USDT':
            t = threading.Thread(target=wait_for_balances_TRON,
                                 args=(wallet, private, user_id, amount))
            t.start()


        response = {
            "wallet": wallet
        }
        return jsonify(response)

if __name__ == '__main__':

    firstTime()


    # app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5390)), debug=False)
