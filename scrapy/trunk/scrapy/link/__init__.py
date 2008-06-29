"""
LinkExtractor provides en efficient way to extract links from pages
"""

from scrapy.utils.python import FixedSGMLParser
from scrapy.utils.url import urljoin_rfc as urljoin

class LinkExtractor(FixedSGMLParser):
    """LinkExtractor are used to extract links from web pages. They are
    instantiated and later "applied" to a Response using the extract_urls
    method which must receive a Response object and return a dict whoose keys
    are the (absolute) urls to follow, and its values any arbitrary data. In
    this case the values are the text of the hyperlink.

    This is the base LinkExtractor class that provides enough basic
    functionality for extracting links to follow, but you could override this
    class or create a new one if you need some additional functionality. The
    only requisite is that the new (or overrided) class must provide a
    extract_urls method that receives a Response and returns a dict with the
    links to follow as its keys.

    The constructor arguments are:

    * tag (string or function)
      * a tag name which is used to search for links (defaults to "a")
      * a function which receives a tag name and returns whether to scan it
    * attr (string or function)
      * an attribute name which is used to search for links (defaults to "href")
      * a function which receives an attribute name and returns whether to scan it
    """

    def __init__(self, tag="a", attr="href"):
        FixedSGMLParser.__init__(self)
        self.scan_tag = tag if callable(tag) else lambda t: t == tag
        self.scan_attr = attr if callable(attr) else lambda a: a == attr
        self.inside_link = False

    def extract_urls(self, response):
        self.reset()
        self.feed(response.body.to_string())
        self.close()
        
        base_url = self.base_url if self.base_url else response.url
        urls = {}
        for link, text in self.links.iteritems():
            urls[urljoin(base_url, link)] = text
        return urls

    def reset(self):
        FixedSGMLParser.reset(self)
        self.links = {}
        self.base_url = None

    def unknown_starttag(self, tag, attrs):
        if tag == 'base':
            self.base_url = dict(attrs).get('href')
        if self.scan_tag(tag):
            for attr, value in attrs:
                if self.scan_attr(attr):
                    self.links[value] = ""
                    self.inside_link = value

    def unknown_endtag(self, tag):
        self.inside_link = False

    def handle_data(self, data):
        if self.inside_link and not self.links.get(self.inside_link, None):
            self.links[self.inside_link] = data