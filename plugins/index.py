import logging
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, ChatAdminRequired, UsernameInvalid, UsernameNotModified
from info import ADMINS
from info import INDEX_REQ_CHANNEL as LOG_CHANNEL
from database.ia_filterdb import save_file
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import temp
import re
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
lock = asyncio.Lock()

@Client.on_callback_query(filters.regex(r'^index'))
async def index_files(bot, update):
    if update.data.startswith('index_cancel'):
        temp.CANCEL = True
        return await update.answer("π²π°π½π²π΄π»π»πΈπ½πΆ πΈπ½π³π΄ππΈπ½πΆ..")
    _, raju, chat, lst_msg_id, from_user = update.data.split("#")
    if raju == 'reject':
        await update.message.delete()
        await bot.send_message(chat_id = int(from_user), text = """ππΎππ πππ±πΌπΈπππΈπΎπ½ π΅πΎπ πΈπ½π³π΄ππΈπ½πΆ **{}** π·π°π π±π΄π΄π½ π³π΄π²π»πΈπ΄π½π΄π³ π±π πΎππ πΌπΎπ³π΄ππ°ππΎππ""".format(chat), reply_to_message_id = int(lst_msg_id))
        return

    if lock.locked():
        return await update.answer("ππ°πΈπ ππ½ππΈπ» πΏππ΄ππΈπΎππ πΏππΎπ²π΄ππ π²πΎπΌπΏπ»π΄ππ΄", show_alert=True)

    msg = update.message
    await update.answer("πΏππΎπ²π΄πππΈπ½πΆ...β³", show_alert=True)
    if int(from_user) not in ADMINS:
        await bot.send_message(int(from_user),
                               "ππΎππ πππ±πΌπΈπππΈπΎπ½ π΅πΎπ πΈπ½π³π΄ππΈπ½πΆ {} π·π°π π±π΄π΄π½ π°π²π²π΄πΏππ΄π³ π±π πΎππ πΌπΎπ³π΄ππ°ππΎππ π°π½π³ ππΈπ»π» π±π΄ π°π³π³π΄π³ ππΎπΎπ½".format(chat),
                               reply_to_message_id=int(lst_msg_id))
    buttons = [[ InlineKeyboardButton('πππΎπΏ', callback_data='close') ]]
    await update.message.edit(text = "πππ°πππΈπ½πΆ πΈπ½π³π΄ππΈπ½πΆ..", reply_markup=InlineKeyboardMarkup(buttons))
    try:
        chat = int(chat)
    except:
        chat = chat
    await index_files_to_db(int(lst_msg_id), chat, msg, bot)


@Client.on_message((filters.forwarded | (filters.regex("(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")) & filters.text ) & filters.private & filters.incoming)
async def send_for_index(bot, message):
    if message.text:
        regex = re.compile("(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
        match = regex.match(message.text)
        if not match:
            return await message.reply('Invalid link')
        chat_id = match.group(4)
        last_msg_id = int(match.group(5))
        if chat_id.isnumeric():
            chat_id  = int(("-100" + chat_id))
    elif message.forward_from_chat.type == enums.ChatType.CHANNEL:
        last_msg_id = message.forward_from_message_id
        chat_id = message.forward_from_chat.username or message.forward_from_chat.id
    else:
        return
    try:
        await bot.get_chat(chat_id)
    except ChannelInvalid:
        return await message.reply('This may be a private channel / group. Make me an admin over there to index the files.')
    except (UsernameInvalid, UsernameNotModified):
        return await message.reply('Invalid Link specified.')
    except Exception as e:
        logger.exception(e)
        return await message.reply(f'Errors - {e}')
    try:
        k = await bot.get_messages(chat_id, last_msg_id)
    except:
        return await message.reply('Make Sure That Iam An Admin In The Channel, if channel is private')
    if k.empty:
        return await message.reply('This may be group and iam not a admin of the group.')

    if message.from_user.id in ADMINS:
        buttons = [[
         InlineKeyboardButton('ππ΄π', callback_data=f'index#accept#{chat_id}#{last_msg_id}#{message.from_user.id}'),
         InlineKeyboardButton('π²π»πΎππ΄', callback_data='close_data')
         ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        return await message.reply(
            f'Do you Want To Index This Channel/ Group ?\n\nChat ID/ Username: <code>{chat_id}</code>\nLast Message ID: <code>{last_msg_id}</code>',
            reply_markup=reply_markup)

    if type(chat_id) is int:
        try:
            link = (await bot.create_chat_invite_link(chat_id)).invite_link
        except ChatAdminRequired:
            return await message.reply('Make sure iam an admin in the chat and have permission to invite users.')
    else:
        link = f"@{message.forward_from_chat.username}"
    buttons = [[
     InlineKeyboardButton('Accept Index', callback_data=f'index#accept#{chat_id}#{last_msg_id}#{message.from_user.id}')
     ],[
     InlineKeyboardButton('Reject Index', callback_data=f'index#reject#{chat_id}#{message.id}#{message.from_user.id}')
     ]]
    
    reply_markup = InlineKeyboardMarkup(buttons)
    await bot.send_message(LOG_CHANNEL,
                           f'#IndexRequest\n\nBy : {message.from_user.mention} (<code>{message.from_user.id}</code>)\nChat ID/ Username - <code> {chat_id}</code>\nLast Message ID - <code>{last_msg_id}</code>\nInviteLink - {link}',
                           reply_markup=reply_markup)
    await message.reply('ThankYou For the Contribution, Wait For My Moderators to verify the files.')


@Client.on_message(filters.command('setskip') & filters.user(ADMINS))
async def set_skip_number(bot, update):
    if ' ' in update.text:
        _, skip = update.text.split(" ")
        try:
            skip = int(skip)
        except:
            return await update.reply("Skip number should be an integer.")
        await update.reply(f"Successfully set SKIP number as {skip}")
        temp.CURRENT = int(skip)
    else:
        await update.reply("Give me a skip number")


async def index_files_to_db(lst_msg_id, chat, msg, bot):
    total_files = 0
    duplicate = 0
    errors = 0
    deleted = 0
    no_media = 0
    async with lock:
        try:
            total = lst_msg_id + 1
            current = temp.CURRENT
            temp.CANCEL = False
            while current < total:
                if temp.CANCEL:
                    await msg.edit("Succesfully Cancelled")
                    break
                try:
                    message = await bot.get_messages(chat_id=chat, message_ids=current, replies=0)
                except FloodWait as e:
                    await asyncio.sleep(e.x)
                    message = await bot.get_messages(chat, current, replies=0)
                except Exception as e:
                    logger.exception(e)
                try:
                    for file_type in ("document", "video", "audio"):
                        media = getattr(message, file_type, None)
                        if media is not None:
                            break
                        else:
                            continue
                    media.file_type = file_type
                    media.caption = message.caption
                    aynav, vnay = await save_file(media)
                    if aynav:
                        total_files += 1
                    elif vnay == 0:
                        duplicate += 1
                    elif vnay == 2:
                        errors += 1
                except Exception as e:
                    if "NoneType" in str(e):
                        if message.empty:
                            deleted += 1
                        elif not media:
                            no_media += 1
                        logger.warning("Skipping deleted / Non-Media messages (if this continues for long, use /setskip to set a skip number)")     
                    else:
                        logger.exception(e)
                current += 1
                if current % 20 == 0:
                    can = [[InlineKeyboardButton('π²π°π½π²π΄π»', callback_data='index_cancel')]]
                    reply = InlineKeyboardMarkup(can)
                    await msg.edit_text(text=f"β’ ππΎππ°π» πΌπ΄πππ°πΆπ΄π π΅π΄ππ²π·π΄π³ : <code>{current}</code>\nβ’ ππΎππ°π» πΌπ΄πππ°πΆπ΄π ππ°ππ΄π³ : <code>{total_files}</code>\nβ’ π³ππΏπ»πΈπ²π°ππ΄ π΅πΈπ»π΄π ππΊπΈπΏπ΄π³ : <code>{duplicate}</code>\nβ’ π³π΄π»π΄ππ΄π³ πΌπ΄πππ°πΆπ΄π ππΊπΈπΏπΏπ΄π³ : <code>{deleted}</code>\n π½πΎπ½-πΌπ΄π³πΈπ° πΌπ΄πππ°πΆπ΄π ππΊπΈπΏπΏπ΄π³ : <code>{no_media}</code>\nβ’ π΄πππΎπ πΎπ²π²πππ΄π³ : <code>{errors}</code>", reply_markup=reply)
        except Exception as e:
            logger.exception(e)
            await msg.edit(f'Error: {e}')
        else:
            await msg.edit(f'β’ πππ²π²π΄ππ΅ππ»π»π ππ°ππ΄π³ <code>{total_files}</code> ππΎ π³π°ππ°π±π°ππ΄.!\nβ’ π³ππΏπ»πΈπ²π°ππ΄ π΅πΈπ»π΄π ππΊπΈπΏπΏπ΄π³ : <code>{duplicate}</code>\nβ’ π³π΄π»π΄ππ΄π³ πΌπ΄πππ°πΆπ΄π ππΊπΈπΏπΏπ΄π³ : <code>{deleted}</code>\nβ’ π½πΎπ½-πΌπ΄π³πΈπ° πΌπ΄πππ°πΆπ΄π ππΊπΈπΏπΏπ΄π³ : <code>{no_media}</code>\nβ’ π΄πππΎππ πΎπ²π²πππ΄π³ : <code>{errors}</code>')
