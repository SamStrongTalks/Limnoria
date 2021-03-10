###
# Copyright (c) 2004, Stéphan Kochen
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

"""This module MUST NOT be reloaded after config.py, because it would cause
the log level to be unset, ie. to log EVERYTHING, and that's bad
"""

import logging


import supybot.log as log
import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.registry as registry


class IrcHandler(logging.Handler):
    def emit(self, record):
        config = conf.supybot.plugins.LogToIrc
        try:
            s = utils.str.normalizeWhitespace(self.format(record))
        except:
            self.handleError(record)
            return
        for target in config.targets():
            msgmaker = ircmsgs.privmsg
            if config.notice() and not ircutils.isChannel(target):
                msgmaker = ircmsgs.notice
            msg = msgmaker(target, s)
            for irc in world.ircs:
                try:
                    if not irc.driver.connected:
                        continue
                except AttributeError as e:
                    print('*** AttributeError, shouldn\'t happen: %s' % e)
                    continue
                networks = conf.supybot.plugins.LogToIrc.networks()
                if networks and irc.network not in networks:
                    continue
                msgOk = True
                if target in irc.state.channels:
                    channel = irc.state.channels[target]
                    for modeChar in config.channelModesRequired():
                        if modeChar not in channel.modes:
                            msgOk = False
                else:
                    capability = config.userCapabilityRequired()
                    if capability:
                        try:
                            hostmask = irc.state.nicksToHostmasks[target]
                        except KeyError:
                            msgOk = False
                            continue
                        if not ircdb.checkCapability(hostmask, capability):
                            msgOk = False
                if msgOk:
                    # We use sendMsg here because queueMsg can cause some
                    # WARNING logs, which might be sent here, which might
                    # cause some more WARNING logs, etc. and that would be
                    # baaaaaad.
                    irc.sendMsg(msg)
                else:
                    print('*** Not sending to %s @ %s' %
                        (utils.str.quoted(target), irc.network))


class IrcFormatter(log.Formatter):
    def formatException(self, xxx_todo_changeme):
        (E, e, tb) = xxx_todo_changeme
        L = [utils.exnToString(e), '::']
        frames = utils.stackTrace(frame=tb.tb_frame).split()
        L.extend(frames)
        del tb
        while sum(map(len, L)) > 350:
            L.pop()
        return ' '.join(L)


class ColorizedIrcFormatter(IrcFormatter):
    def formatException(self, xxx_todo_changeme1):
        (E, e, tb) = xxx_todo_changeme1
        if conf.supybot.plugins.LogToIrc.color():
            s = IrcFormatter.formatException(self, (E, e, tb))
            return ircutils.mircColor(s, fg='red')
        else:
            return IrcFormatter.formatException(self, (E, e, tb))

    def format(self, record, *args, **kwargs):
        s = IrcFormatter.format(self, record, *args, **kwargs)
        if conf.supybot.plugins.LogToIrc.color():
            if record.levelno == logging.CRITICAL:
                s = ircutils.bold(ircutils.bold(s))
            elif record.levelno == logging.ERROR:
                s = ircutils.mircColor(s, fg='red')
            elif record.levelno == logging.WARNING:
                s = ircutils.mircColor(s, fg='yellow')
        return s


_ircHandler = IrcHandler()
_formatString = '%(name)s: %(levelname)s %(message)s'
_ircFormatter = ColorizedIrcFormatter(_formatString)
_ircHandler.setFormatter(_ircFormatter)


