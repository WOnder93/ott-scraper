# Copyright (c) 2013 Ondrej Mosnáček

# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from HTMLParser import HTMLParser
import htmlentitydefs

class OTTParser(HTMLParser):
    def __init__(self, outfile, incQuotes=False, incStrike=False, incSpoiler=True, incCode=False, incSmileys=True):
        HTMLParser.__init__(self)
        self.out = outfile
        self.level = 0
        self.content = -1
        self.cite = -1          # quote headers are cite
        self.quote = -1
        self.attachment = -1
        self.strike = -1
        self.spoilerhdr = -1
        self.spoilerbody = -1
        self.dt = -1            # code block headers are dt - we don't want those and neither the other dts
        self.codebox = -1
        self.incQuotes = incQuotes
        self.incStrike = incStrike
        self.incSpoiler = incSpoiler
        self.incCode = incCode
        self.incSmileys = incSmileys
    
    def is_processed(self):
        return self.content >= 0 and self.cite < 0 and (self.incQuotes or self.quote < 0) and self.attachment < 0  and (self.strike < 0 or self.incStrike) and self.spoilerhdr < 0 and (self.spoilerbody < 0 or self.incSpoiler) and self.dt < 0 and (self.codebox < 0 or self.incCode)
    
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.level += 1
        if self.content >= 0:
            if tag == u'blockquote':
                if self.is_processed():
                    self.out.write(u'\n')
                self.quote = self.quote if self.quote >= 0 else self.level
            elif tag == u'cite':
                self.cite = self.level
            elif tag == u'sup' or tag == u'sub':
                # surround sup and sub with spaces (important for Markov chain generator)
                if self.is_processed():
                    self.out.write(u' ')
            elif tag == u'br':
                if self.is_processed():
                    self.out.write(u'\n')
            elif tag == u'dt':
                self.dt = self.level
            elif tag == u's' or tag == u'strike':
                self.strike = self.strike if self.strike >= 0 else self.level
            elif u'inline-attachment' in attrs.get(u'class', u''):
                self.attachment = self.level
            elif u'quotetitle' in attrs.get(u'class', u''):
                self.spoilerhdr = self.level
            elif u'quotecontent' in attrs.get(u'class', u''):
                self.spoilerbody = self.level
            elif u'codebox' in attrs.get(u'class', u''):
                self.codebox = self.level
            elif tag == u'img':
                if self.is_processed():
                    if attrs[u'alt'] != u'Image' and self.incSmileys:
                        # process the smiley (force whitespace around it):
                        self.out.write(u' ' + attrs[u'alt'] + u' ')
                    else:
                        # replace images with whitespace (just to be sure):
                        self.out.write(u' ')
        else:
            if u'content' in attrs.get(u'class', u''):
                # entering a post body
                self.content = self.level
    
    def handle_data(self, data):
        if self.is_processed():
            self.out.write(data)
    
    def handle_entityref(self, name):
        if self.is_processed():
            self.out.write(unichr(htmlentitydefs.name2codepoint[name]))
    
    def handle_charref(self, name):
        if self.is_processed():
            if name.startswith(u'x'):
                c = int(name[1:], 16)
            else:
                c = int(name)
            self.out.write(unichr(c))
        
    def handle_endtag(self, tag):
        if tag == u'sup' or tag == u'sub':
            if self.is_processed():
                self.out.write(u' ')
        if self.content == self.level:
            assert self.is_processed()
            self.out.write(u'\n')
            self.content = -1
        if self.cite == self.level:
            self.cite = -1
        if self.quote == self.level:
            self.quote = -1
        if self.attachment == self.level:
            self.attachment = -1
        if self.strike == self.level:
            self.strike = -1
        if self.spoilerhdr == self.level:
            self.spoilerhdr = -1
        if self.spoilerbody == self.level:
            self.spoilerbody = -1
        if self.dt == self.level:
            self.dt = -1
        if self.codebox == self.level:
            self.codebox = -1
        self.level -= 1

from urllib2 import urlopen
import codecs
import sys
from argparse import ArgumentParser

argparser = ArgumentParser(description='Scrapes the plaintext from the OTT')
argparser.add_argument('-q, --quotes', dest='quotes', action='store_true', help='include quotes')
argparser.add_argument('-s, --strike', dest='strike', action='store_true', help='include strikethroughs')
argparser.add_argument('-p, --spoiler', dest='spoiler', action='store_true', help='include spoilers')
argparser.add_argument('-c, --code', dest='code', action='store_true', help='include code blocks')
argparser.add_argument('-m, --smileys', dest='smileys', action='store_true', help='include smileys')
argparser.add_argument('PAGES_MAX', type=int, metavar='NP', help='number of NewPages to scrape')
argparser.add_argument('outfile', type=lambda fn: file(fn, 'w'), nargs='?', default=sys.stdout, metavar='OUTPUT', help='the output file (default is standard output)')

args = argparser.parse_args()

output = codecs.getwriter('utf-8')(args.outfile)

for NP in xrange(0, args.PAGES_MAX):
    sys.stderr.write('Page {0}/{1} - {2:.2f}%\n'.format(NP, args.PAGES_MAX, 100.0 * float(NP) / args.PAGES_MAX))
    input = codecs.getreader('utf-8')(urlopen('http://forums.xkcd.com/viewtopic.php?f=7&t=101043&start={0}'.format(NP * 40)))

    parser = OTTParser(output, args.quotes, args.strike, args.spoiler, args.code, args.smileys)
    for text in input:
        parser.feed(text)
    input.close()

sys.stderr.write('DONE!\n')
args.outfile.close()