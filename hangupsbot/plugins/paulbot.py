import asyncio
import hashlib
import os
from hangups.ui.utils import get_conv_name


def _initialise(Handlers, bot=None):
    Handlers.register_user_command(["generatetoken","bump"])
    Handlers.register_admin_command(["forgetslack","namechat"])
    return []

def generatetoken(bot,event, *args):
    conv_1on1_initiator = bot.get_1on1_conversation(event.user.id_.chat_id)
    usergid=event.user_id.chat_id
    if bot.memory.exists(['user_data', usergid, "slackname"]):
      bot.send_message_parsed(conv_1on1_initiator,_("sorry we already know each other"))
      return True
    m = hashlib.md5()
    m.update(os.urandom(5))
    pairingtoken = m.hexdigest()
    bot.initialise_memory(usergid, "user_data")
    bot.initialise_memory(pairingtoken, "tokens")
    bot.memory.set_by_path(["user_data", usergid, "pairingtoken"], pairingtoken )
    bot.memory.set_by_path(["tokens", pairingtoken ], usergid )
    bot.memory.save()
    print(_(usergid+" noweb4upair "+pairingtoken))
    bot.send_message_parsed(conv_1on1_initiator,_("in slack, please say noweb4ubot pair "+pairingtoken))

def forgetslack(bot,event, *args):
    conv_1on1_initiator = bot.get_1on1_conversation(event.user.id_.chat_id)
    usergid = args[0]
    print(_("forgetting "+usergid))
    bot.memory.set_by_path(["user_data", usergid, "pairingtoken"], None)
    bot.memory.set_by_path(["user_data", usergid, "slackname"], None)
    bot.memory.set_by_path(["user_data", usergid, "slackteam"], None)
    bot.memory.save()
    print(_(usergid+" slack info forgotten"))
    bot.send_message_parsed(conv_1on1_initiator,_("I forgot "+usergid))

def namechat(bot,event, *args):
    conv_1on1_initiator = bot.get_1on1_conversation(event.user.id_.chat_id)
    hangoutid = args[0]
    nickname = args[1]
    access = args[2]
    print(_("remembering {} is {}, ACL {}".format(hangoutid,nickname,access)))
    bot.initialise_memory(nickname, "hangoutalias")
    bot.memory.set_by_path(["hangoutalias",nickname,"id"], hangoutid)
    bot.memory.set_by_path(["hangoutalias",nickname,"acl"], access)
    bot.memory.save()
    bot.send_message_parsed(conv_1on1_initiator,_("I added {} as {}, ACL {}".format(hangoutid,nickname,access)))

def bump(bot,event, *args):
    hangoutid = args[0]
    conv = bot._conv_list.get(hangoutid)
    origname = get_conv_name(conv)
    yield from bot._client.setchatname(hangoutid, origname+" ")
    yield from bot._client.setchatname(hangoutid, origname)
