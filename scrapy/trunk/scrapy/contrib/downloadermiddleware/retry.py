"""
An extension to retry failed requests that are potentially caused by temporary
problems such as a connection timeout or HTTP 500 error.

You can change the behaviour of this moddileware by modifing the scraping settings: 
RETRY_TIMES - how many times to retry a failed page
RETRY_HTTP_CODES - which HTTP response codes to retry

Failed pages are collected on the scraping process and rescheduled at the end,
once the spider has finished crawling all regular (non failed) pages. Once
there is no more failed pages to retry this middleware sends a signal
(retry_complete), so other extensions could connect to that signal.

Default values are located in scrapy.conf.core_settings

About HTTP errors to consider:

- You may want to remove 400 from RETRY_HTTP_CODES, if you stick to the HTTP
  protocol. It's included by default because it's a common code used to
  indicate server overload, which would be something we want to retry
- 200 is included by default (and shoudln't be removed) to check for partial
  downloads errors, which means the TCP connection has broken in the middle of
  a HTTP download 
""" 

from twisted.internet.error import TimeoutError as ServerTimeoutError, DNSLookupError, \
                                   ConnectionRefusedError, ConnectionDone, ConnectError
from twisted.internet.defer import TimeoutError as UserTimeoutError 

from scrapy.core import log
from scrapy.core.exceptions import HttpException
from scrapy.conf import settings

class RetryMiddleware(object):

    EXCEPTIONS_TO_RETRY = (ServerTimeoutError, UserTimeoutError, DNSLookupError, 
                           ConnectionRefusedError, ConnectionDone, ConnectError)

    def __init__(self):
        self.failed_count = {}
        self.max_retries = settings.getint('RETRY_TIMES')

    def process_exception(self, request, exception, spider):
        retry = False

        if isinstance(exception, self.EXCEPTIONS_TO_RETRY):
            retry = True
        elif isinstance(exception, HttpException):
            if exception.status in settings.getlist('RETRY_HTTP_CODES'):
                retry = True

        if retry:
            fp = request.fingerprint()
            count = self.failed_count[fp] = self.failed_count.get(fp, 0) + 1

            if self.failed_count[fp] < self.max_retries:
                log.msg("Retrying %s (failed %d times): %s" % (request, count, exception), level=log.DEBUG, domain=spider.domain_name)
                retryreq = request.copy()
                retryreq.dont_filter = True
                return retryreq
            else:
                log.msg("Discarding %s (failed %d times): %s" % (request, count, exception), domain=spider.domain_name, level=log.DEBUG)
