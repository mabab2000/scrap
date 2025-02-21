import scrapy

class MySpider(scrapy.Spider):
    name = 'my_spider'  # This is the name you use to run the spider
    start_urls = ['https://quotes.toscrape.com']  # The webpage you want to scrape

    def parse(self, response):
        # Extract data from the webpage
        for quote in response.xpath('//div[@class="quote"]'):
            yield {
                'text': quote.xpath('span[@class="text"]/text()').get(),
                'author': quote.xpath('span/small[@class="author"]/text()').get(),
                'tags': quote.xpath('div[@class="tags"]/a[@class="tag"]/text()').getall(),
            }

        # Follow pagination links to scrape multiple pages
        next_page = response.xpath('//li[@class="next"]/a/@href').get()
        if next_page:
            yield response.follow(next_page, self.parse)
