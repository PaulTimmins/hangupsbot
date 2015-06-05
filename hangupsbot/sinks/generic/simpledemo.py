from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from hangups.ui.utils import get_conv_name

import time
import json
import base64
import io
import asyncio

class webhookReceiver(BaseHTTPRequestHandler):
    _bot = None

    @asyncio.coroutine
    def _handle_incoming(self, path, query_string, payload):
        path = path.split("/")
        conversation_id = path[1]
        if conversation_id is None:
            print(_("conversation id must be provided as part of path"))
            return

        if "echo" in payload:
            html = payload["echo"]
        else:
            html = "<b>hello world</b>"

        webhookReceiver._bot.send_html_to_conversation(conversation_id, html)

    @asyncio.coroutine
    def _adduser(self, conversation_id, chat_id_list):
        results = yield from webhookReceiver._bot.adduserto(conversation_id, chat_id_list)
        print(_(results))

    @asyncio.coroutine
    def _bump(self,hangoutid,origname):
        yield from webhookReceiver._bot.setchatname(hangoutid, origname+" ")
        yield from webhookReceiver._bot.setchatname(hangoutid, origname)

    def do_POST(self):
        """
            receives post, handles it
        """
        print(_('receiving POST...'))
        data_string = self.rfile.read(int(self.headers['Content-Length'])).decode('UTF-8')
        self.send_response(200)
        message = bytes('OK', 'UTF-8')
        self.send_header("Content-type", "text")
        self.send_header("Content-length", str(len(message)))
        self.end_headers()
        self.wfile.write(message)
        print(_('connection closed'))

        # parse requested path + query string
        _parsed = urlparse(self.path)
        path = _parsed.path
        query_string = parse_qs(_parsed.query)

        print(_("incoming path: {}").format(path))

        print(data_string)

        # parse incoming data
        payload = json.loads(data_string)
        asyncio.async(self._handle_incoming(path, query_string, payload))

    def do_GET(self):
        print(_('receiving GET...'))
        #self.send_response(200)
        _parsed = urlparse(self.path)
        path = _parsed.path
        query_string = parse_qs(_parsed.query)
        print(_("incoming path: {}").format(path))
        path = path.split("/")
        outdata = "invalid request: "
        outdata = outdata + path[1]
        if path[1] == "userdump":
            outdata = ""
            for key in webhookReceiver._bot._user_list._user_dict:
              user_object = webhookReceiver._bot._user_list._user_dict[key]
              outdata=outdata+"{}\t{}\t{}\n".format(key.chat_id,"https://plus.google.com/u/0/"+key.gaia_id, user_object.full_name)
        if path[1] == "getusers":
            outdata = webhookReceiver._bot.get_users_in_conversation(path[2])
        if path[1] == "hangouts":
            outdata = ""
            for c in webhookReceiver._bot.list_conversations():
               outdata += "{}\t{}\n".format(get_conv_name(c, truncate=True), c.id_)
        if path[1] == "adduserto":
            outdata = ""
            chatid = path[2];
            userids = [path[3]];
            asyncio.async(self._adduser(chatid,userids))
            outdata = "adduser {}\t{}\n".format(chatid,userids)
        if path[1] == "pair":
            outdata = ""
            slackteam = path[2]
            slackname = path[3]
            token = path[4]
            if webhookReceiver._bot.memory.exists(['tokens',token]):
               usergid = webhookReceiver._bot.memory.get_by_path(['tokens',token])
               if webhookReceiver._bot.memory.exists(['user_data', usergid, "slackname"]):
                   outdata = "error: known already"
                   webhookReceiver._bot.memory.set_by_path(["tokens", token ], None)
                   webhookReceiver._bot.memory.set_by_path(["user_data", usergid, "pairingtoken"], None)
                   webhookReceiver._bot.memory.save()
               else:
                   mytoken = webhookReceiver._bot.memory.get_by_path(["user_data", usergid, "pairingtoken"])
                   if token == mytoken:
                     webhookReceiver._bot.memory.set_by_path(["tokens", token ], None)
                     webhookReceiver._bot.memory.set_by_path(["user_data", usergid, "pairingtoken"], None)
                     webhookReceiver._bot.memory.set_by_path(["user_data", usergid, "slackname"], slackname)
                     webhookReceiver._bot.memory.set_by_path(["user_data", usergid, "slackteam"], slackteam)
                     webhookReceiver._bot.initialise_memory(slackteam, "slackteam")
                     webhookReceiver._bot.memory.set_by_path(["slackteam", slackteam, slackname], usergid)
                     outdata = "pairing: {} is now paired with {} from {}: success".format(usergid,slackname,slackteam)
                     webhookReceiver._bot.memory.save()
            else:
               outdata = "do i know you, {}? I might. If so, we already talked.".format(slackname)                     
        if path[1] == "slacklookup":
           outdata = ""
           slackteam = path[2]
           slackname = path[3]
           if webhookReceiver._bot.memory.exists(["slackteam", slackteam, slackname]):
                googleid = webhookReceiver._bot.memory.get_by_path(["slackteam", slackteam, slackname])
                outdata = "{} {} {}".format(slackteam,slackname,googleid)
           else:
                outdata = "{} {} UNKNOWN".format(slackteam,slackname)
        if path[1] == "slackparachute":
           outdata = ""
           slackteam = path[2]
           slackname = path[3]
           hoalias = path[4]
           if webhookReceiver._bot.memory.exists(["slackteam", slackteam, slackname]):
              googleid = webhookReceiver._bot.memory.get_by_path(["slackteam", slackteam, slackname])
              if webhookReceiver._bot.memory.exists(["hangoutalias",hoalias,"id"]):
                 if webhookReceiver._bot.memory.get_by_path(["hangoutalias",hoalias,"acl"]) == "OPEN":
                     hangoutid = webhookReceiver._bot.memory.get_by_path(["hangoutalias",hoalias,"id"])
                     asyncio.async(self._adduser(hangoutid,[googleid]))
                     outdata = "adding you to "+hoalias+" standby - it may take a moment..."
                 else:
                     outdata = "access is denied"
              else:
               outdata = "never heard of "+hoalias+" sorry"
           else:
            outdata = "I'm sorry. Have we met? Please open a hangout to noweb4ubot@gmail.com and say /bot generatetoken"
        if path[1] == "slackbump":
           outdata = ""
           slackteam = path[2]
           slackname = path[3]
           hoalias = path[4]
           if webhookReceiver._bot.memory.exists(["slackteam", slackteam, slackname]):
              googleid = webhookReceiver._bot.memory.get_by_path(["slackteam", slackteam, slackname])
              if webhookReceiver._bot.memory.exists(["hangoutalias",hoalias,"id"]):
                 if webhookReceiver._bot.memory.get_by_path(["hangoutalias",hoalias,"acl"]) == "OPEN":
                     hangoutid = webhookReceiver._bot.memory.get_by_path(["hangoutalias",hoalias,"id"])
                     conv = webhookReceiver._bot._conv_list.get(hangoutid)
                     origname = get_conv_name(conv)
                     asyncio.async(self._bump(hangoutid,origname))
                     outdata = "bumping "+hoalias+" standby - it may take a moment..."
                 else:
                     outdata = "access is denied"
              else:
               outdata = "never heard of "+hoalias+" sorry"
           else:
            outdata = "I'm sorry. Have we met? Please open a hangout to noweb4ubot@gmail.com and say /bot generatetoken"

        if path[1] == "bump":
           outdata = ""
           hangoutid = path[2]
           conv = webhookReceiver._bot._conv_list.get(hangoutid)
           origname = get_conv_name(conv)
           outdata = "{} is being bumped (name: {})\n".format(hangoutid,origname)
           asyncio.async(self._bump(hangoutid,origname))

        message = bytes(outdata, 'UTF-8')
        print(_(message))
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        #self.send_header("Content-length", str(len(message)))
        self.end_headers()
        self.wfile.write(message)
        print(_('connection closed'))


    def log_message(self, formate, *args):
        # disable printing to stdout/stderr for every post
        return
