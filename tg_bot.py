import os
import logging
from functools import partial

from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Updater, CommandHandler, MessageHandler,
                          CallbackQueryHandler, CallbackContext, Filters)

from dotenv import load_dotenv
import redis

from utils.telegram_logger import TelegramLogsHandler
from utils.moltin_helper import (get_access_token, get_products, get_file,
                                 add_product_to_cart, get_cart, get_cart_items,
                                 remove_cart_item, create_customer)


logger = logging.getLogger('Telegram logger')


def display_main_menu(update: Update, context: CallbackContext, redis_client):
    moltin_access_token = redis_client.get('moltin_access_token')
    products = get_products(moltin_access_token)['data']

    product_names_with_ids = [(product['name'], product['id']) for product in products]

    keyboard = []
    for product_name_with_id in product_names_with_ids:
        product_name, product_id = product_name_with_id
        keyboard_button = InlineKeyboardButton(product_name, callback_data=product_id)
        keyboard.append([keyboard_button])
    keyboard.append([InlineKeyboardButton('Корзина', callback_data='cart')])

    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='В наличии:',
        reply_markup=reply_markup
    )

    return 'HANDLE_MAIN_MENU'


def handle_main_menu(update: Update, context: CallbackContext, redis_client):
    query = update.callback_query

    if query.data == 'cart':
        next_state = display_cart(update, context, redis_client)
    else:
        next_state = display_description(update, context, redis_client)

    context.bot.delete_message(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id
    )

    query.answer()

    return next_state


def display_description(update: Update, context: CallbackContext, redis_client):
    query = update.callback_query

    moltin_access_token = redis_client.get('moltin_access_token')
    product = get_products(moltin_access_token, query.data)['data']

    file_id = product['relationships']['main_image']['data']['id']
    main_image_url = get_file(moltin_access_token, file_id)['data']['link']['href']

    product_description = f"{product['name']}\n\n{product['meta']['display_price']['with_tax']['formatted']} за штуку\n\n{product['meta']['stock']['level']} штук в наличии\n\n{product['description']}"

    keyboard = [
        [
            InlineKeyboardButton('1 шт', callback_data=f'1 {query.data}'),
            InlineKeyboardButton('5 шт', callback_data=f'5 {query.data}'),
            InlineKeyboardButton('10 шт', callback_data=f'10 {query.data}'),
        ],
        [InlineKeyboardButton('Корзина', callback_data='cart')],
        [InlineKeyboardButton('Назад', callback_data='main_menu'),],
    ]

    context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=main_image_url,
        caption=product_description,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return 'HANDLE_DESCRIPTION'


def handle_description(update: Update, context: CallbackContext, redis_client):
    query = update.callback_query

    if query.data == 'main_menu':
        next_state = display_main_menu(update, context, redis_client)
        context.bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id
        )
    elif query.data == 'cart':
        next_state = display_cart(update, context, redis_client)
        context.bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id
        )
    else:
        moltin_access_token = redis_client.get('moltin_access_token')

        product_id = query.data.split(' ')[-1]
        product = get_products(moltin_access_token, product_id)['data']

        cart_id = query.message.chat_id
        product_quantity = int(query.data.split(' ')[0])
        add_product_to_cart(moltin_access_token, cart_id, product, product_quantity)

        next_state = 'HANDLE_DESCRIPTION'

    query.answer()

    return next_state


def display_cart(update: Update, context: CallbackContext, redis_client):
    query = update.callback_query

    moltin_access_token = redis_client.get('moltin_access_token')
    cart_id = query.message.chat_id
    cart = get_cart(moltin_access_token, cart_id)
    cart_items = get_cart_items(moltin_access_token, cart_id)

    total_price = cart['data']['meta']['display_price']['with_tax']['formatted']

    cart_items_text = ''
    for item in cart_items['data']:
        cart_items_text += '{}\n{}\n{} за штуку\n{} шт. в корзине за {}\n\n'.format(
            item['name'],
            item['description'],
            item['meta']['display_price']['with_tax']['unit']['formatted'],
            item['quantity'],
            item['meta']['display_price']['with_tax']['value']['formatted'],
        )
    cart_items_text += f'Всего: {total_price}'

    keyboard = []
    for item in cart_items['data']:
        keyboard_button = InlineKeyboardButton(f"Убрать {item['name']}", callback_data=item['id'])
        keyboard.append([keyboard_button])
    keyboard.append([InlineKeyboardButton('Оплатить', callback_data='customer_info')])
    keyboard.append([InlineKeyboardButton('В меню', callback_data='main_menu')])

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f'{cart_items_text}',
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return 'HANDLE_CART'


def handle_cart(update: Update, context: CallbackContext, redis_client):
    query = update.callback_query

    if query.data == 'main_menu':
        next_state = display_main_menu(update, context, redis_client)
        context.bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id
        )
    elif query.data == 'customer_info':
        next_state = request_customer_info(update, context, redis_client)
    else:
        moltin_access_token = redis_client.get('moltin_access_token')
        cart_id = query.message.chat_id
        remove_cart_item(moltin_access_token, cart_id, query.data)

        next_state = display_cart(update, context, redis_client)

        context.bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id
        )

    query.answer()

    return next_state


def request_customer_info(update: Update, context: CallbackContext, redis_client):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f'Введите вашу почту. Мы свяжимся по ней с вами для подтверждения покупки товара.',
    )

    return 'HANDLE_CUSTOMER_INFO'


def handle_customer_info(update: Update, context: CallbackContext, redis_client):
    moltin_access_token = redis_client.get('moltin_access_token')
    customer_email = update.message.text

    create_customer(moltin_access_token, customer_email)

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f'Вы указали: {customer_email}. Напишем вам в течение 24 часов.',
    )

    next_state = display_main_menu(update, context, redis_client)

    return next_state


def handle_users_reply(update: Update, context: CallbackContext, redis_client):
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return

    if user_reply == '/start':
        user_state = 'DISPLAY_MAIN_MENU'
    else:
        user_state = redis_client.get(chat_id)

    states_functions = {
        'DISPLAY_MAIN_MENU': display_main_menu,
        'HANDLE_MAIN_MENU': handle_main_menu,
        'DISPLAY_DESCRIPTION': display_description,
        'HANDLE_DESCRIPTION': handle_description,
        'DISPLAY_CART': display_cart,
        'HANDLE_CART': handle_cart,
        'REQUEST_CUSTOMER_INFO': request_customer_info,
        'HANDLE_CUSTOMER_INFO': handle_customer_info,

    }
    state_handler = states_functions[user_state]
    next_state = state_handler(update, context, redis_client)

    redis_client.set(chat_id, next_state)


def error_handler(update: object, context: CallbackContext) -> None:
    logger.error(msg="Exception while handling telegram update:", exc_info=context.error)


def main():
    load_dotenv()

    telegram_logger_bot_token = os.getenv('TELEGRAM_LOGGER_BOT_TOKEN')
    developer_chat_id = os.getenv('TELEGRAM_DEVELOPER_USER_ID')

    logger_tg_bot = Bot(token=telegram_logger_bot_token)

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger.setLevel(logging.INFO)
    logger.addHandler(TelegramLogsHandler(logger_tg_bot, developer_chat_id))

    redis_url = os.getenv('REDIS_URL')
    redis_client = redis.from_url(redis_url, decode_responses=True)

    moltin_client_id = os.getenv('MOLTIN_CLIENT_ID')
    moltin_client_secret = os.getenv('MOLTIN_CLIENT_SECRET')
    moltin_access_token = get_access_token(moltin_client_id, moltin_client_secret)
    redis_client.set('moltin_access_token', moltin_access_token)

    updater = Updater(token=os.getenv('TELEGRAM_BOT_TOKEN'))
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CallbackQueryHandler(partial(handle_users_reply, redis_client=redis_client)))
    dispatcher.add_handler(MessageHandler(Filters.text, partial(handle_users_reply, redis_client=redis_client)))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))

    dispatcher.add_error_handler(error_handler)

    updater.start_polling()


if __name__ == '__main__':
    main()
