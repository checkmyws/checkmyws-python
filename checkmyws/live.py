from os import environ
import logging

import txaio
txaio.use_twisted()

import traceback
import re
import time

from twisted.internet.defer import inlineCallbacks
from twisted.internet import reactor
from twisted.internet.ssl import CertificateOptions

from autobahn.wamp import auth
from autobahn.wamp.types import SubscribeOptions, CallOptions
from autobahn.twisted.wamp import ApplicationSession, ApplicationRunner

from twisted.internet.defer import DeferredLock
from twisted.internet.task import LoopingCall

callbacks = {}
re_cache = {}
live = None


def register(pattern):
    def decorated(func):
        re_cache[pattern] = re.compile(pattern)
        callbacks[pattern] = callbacks.get(pattern, [])
        callbacks[pattern].append(func)
        return func
    return decorated


class Live(ApplicationSession):
    def __init__(self, config=None):
        ApplicationSession.__init__(self, config)

        global live
        live = self

        self.logger = logging.getLogger('Live')

        self.logger.info("Config: %s", config)

        self.account_id = config.extra['authid']
        self.secret = config.extra['secret']

        if '-' not in self.account_id:
            self.account_id = "local-%s" % self.account_id

        self.authid = '%s:%s' % (self.account_id , self.secret[-7:])

        self.joined = False
        self.lock = DeferredLock()

        self.checks = {}
        self.workers = {}

        self.CallOptions = CallOptions()

    def onConnect(self):
        self.logger.info("Connected")
        self.join(self.config.realm, [u"wampcra"], self.authid)

    def onChallenge(self, challenge):
        self.logger.info("Authenticate connection %s@%s (challenge) ...", self.authid, self.config.realm)

        self.logger.debug("Challenge:")
        self.logger.debug(" + method: %s", challenge.method)
        self.logger.debug(" + extra:  %s", challenge.extra)

        if challenge.method == u"wampcra":
            salt = challenge.extra['salt']
            secret = self.secret

            secret = auth.derive_key(
                secret.encode('utf8'),
                salt.encode('utf8'),
                iterations=challenge.extra['iterations'],
                keylen=challenge.extra['keylen']
            ).decode('ascii')

            signature = auth.compute_wcs(
                secret.encode('utf8'),
                challenge.extra['challenge'].encode('utf8')
            )

            signature = signature.decode('ascii')

            self.logger.debug("Signature '%s'", signature)
            return signature

        else:
            self.logger.error("Unknown challenge method '%s'", challenge.method)

    @inlineCallbacks
    def api_onRawEvent(self, event, details):
        topic = details.topic

        scope = event['scope']
        procedure = event['procedure']
        output = event['output']
        location = event['location']
        timestamp = event['timestamp']

        d = self.lock.acquire()
        d.addCallback(self.api_onEvent, timestamp, scope, procedure, location, output)
        yield

    @inlineCallbacks
    def api_onEvent(self, d, timestamp, scope, procedure, location, output):
        check = self.checks.get(scope, None)
        if check is None:
            self.logger.info("Get check configuration of %s", scope)
            try:
                check = yield self.call('check', scope, options=self.CallOptions)
                self.checks[scope] = check

            finally:
                self.lock.release()

        else:
            self.lock.release()

        worker = self.workers.get(location, None)

        uri = "%s.%s.%s" % (
            scope,
            procedure,
            location
        )

        self.logger.debug("onCheck %s", uri)

        for pattern, funcs  in callbacks.items():
            pattern = re_cache[pattern]
            if re.match(pattern, uri):
                for func in funcs:
                    try:
                        func(timestamp, check, procedure, location, worker, output)
                    except Exception as err:
                        self.logger.error(traceback.format_exc())

        yield

    @inlineCallbacks
    def onJoin(self, details):
        self.logger.info("onJoin")
        self.joined = True

        options = SubscribeOptions(match=u'prefix', details_arg=str('details'))

        self.logger.info("Get workers configurations")
        self.workers = yield self.call('workers', options=self.CallOptions)

        self.logger.info("Subscribe to %s.*", self.account_id)
        yield self.subscribe(self.api_onRawEvent, self.account_id, options)

        self.logger.info("Waiting data ...")

    def onLeave(self, *args, **kwargs):
        self.logger.info("Leaving WAMP Broker")
        ApplicationSession.onLeave(self, *args, **kwargs)

    def onDisconnect(self,  *args, **kwargs):
        ApplicationSession.onDisconnect(self, *args, **kwargs)

        if not self.joined:
            self.logger.error("Impossible to join realm")

        if reactor.running:
            reactor.stop()

        self.logger.info("Disconnected")


def heartbeat():
    logger = logging.getLogger('Heartbeat')
    logger.debug("Reactor running: %s", reactor.running)
    logger.debug("Live: %s", live)

    if not reactor.running:
        # Impossible ?
        logger.error("Twisted reactor not running")

    if live is None:
        logger.error("Live was not created")
        reactor.stop()

    else:
        logger.debug(" + joined: %s", live.joined)

        if not live.joined:
            logger.error("Live was not joined")
            reactor.stop()


def run(url="wss://api.checkmy.ws/live", realm="live", authid=None, secret=None, debug=False):
    url = environ.get('WAMP_URL', url)
    realm = environ.get('WAMP_REALM', realm)

    authid = environ.get('WAMP_AUTHID', authid)
    secret = environ.get('WAMP_SECRET', secret)

    if authid is None or secret is None:
        raise EnvironmentError("'WAMP_AUTHID' or 'WAMP_SECRET' was not defined")

    config = {
        'url': url.decode(),
        'realm': realm.decode(),
        'extra': {
            'authid': authid,
            'secret': secret
        }
    }

    if 'dev' in url:
        config['ssl'] = CertificateOptions(verify=False)

    runner = ApplicationRunner(**config)

    LoopingCall(heartbeat).start(10, now=False)

    try:
        runner.run(Live)

    except Exception as err:
        print(traceback.format_exc())
        # Safety sleep
        time.sleep(3)
