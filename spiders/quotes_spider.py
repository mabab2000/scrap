import scrapy

class QuotesSpider(scrapy.Spider):
    name = "quotes"
    start_urls = ['https://igihe.com/imyidagaduro/article/cyahinduriwe-inyito-tom-close-yakomoje-ku-myiteguro-y-igitaramo-yari-yise-icyo']

    def parse(self, response):
        # Extract and make full URLs from relative links
        base_url = "https://igihe.com/imyidagaduro/article/cyahinduriwe-inyito-tom-close-yakomoje-ku-myiteguro-y-igitaramo-yari-yise-icyo"
        for link in response.css('a::attr(href)').getall():
            full_url = link if link.startswith('http') else base_url + link
            yield {'link': full_url}

        # Extract text from <p> tags
        for paragraph in response.css('p::text').getall():
            yield {'paragraph': paragraph.strip()}

              # Extract text from <span> tags
        for span in response.css('span::text').getall():
            yield {'span': span.strip()}

