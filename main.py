import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from selenium import webdriver   
from selenium.webdriver.chrome.service import Service as ChromeService   
from selenium.webdriver.common.by import By   
from selenium.webdriver.chrome.options import Options   
from webdriver_manager.chrome import ChromeDriverManager   
from selenium.webdriver.support.ui import WebDriverWait   
from selenium.webdriver.support import expected_conditions as EC   
from typing import List
import concurrent.futures
from reportlab.lib.pagesizes import letter   
from reportlab.pdfgen import canvas   
import time  # For adding sleep to simulate scrolling

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Multi-Website Scraper API")

# Create directory for storing PDFs
PDF_DIR = "scraped_files"
os.makedirs(PDF_DIR, exist_ok=True)

class ScrapeRequest(BaseModel):
    urls: List[str]

class ScrapedData(BaseModel):
    url: str
    title: str
    text_content: str
    pdf_file: str  # Path to the saved PDF file

def configure_driver():
    options = Options()
    options.add_argument("--headless")  # Run in headless mode
    service = ChromeService(ChromeDriverManager().install())  # Automatically install ChromeDriver
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def clean_filename(url: str) -> str:
    """Generate a safe filename from URL."""
    return url.replace("http://", "").replace("https://", "").replace("/", "_").replace("?", "_")[:100] + ".pdf"

def save_to_pdf(title: str, text_content: str, filename: str):
    """Save scraped data to a PDF file, handling multiple pages with margins and justified text."""
    pdf_path = os.path.join(PDF_DIR, filename)
    
    try:
        c = canvas.Canvas(pdf_path, pagesize=letter)
        c.setFont("Helvetica", 12)

        # Set margins
        left_margin = 50
        right_margin = 550
        top_margin = 750
        bottom_margin = 50
        line_height = 24
        x = left_margin
        y = top_margin

        # Draw the title and URL at the top of the page
        c.drawString(left_margin, y, f"Title: {title}")
        y -= line_height
        c.drawString(left_margin, y, f"URL: {filename.replace('.pdf', '')}")  # Show URL (truncated)
        y -= line_height * 2  # Add some space after the header

        # Split the text into words and justify
        text_lines = text_content.split(" ")
        line = []
        for word in text_lines:
            line_width = c.stringWidth(' '.join(line) + " " + word, "Helvetica", 12)
            if line_width < (right_margin - left_margin):
                line.append(word)
            else:
                # Print the current line, justify it
                justified_text = " ".join(line)
                c.drawString(left_margin, y, justified_text)
                y -= line_height
                line = [word]

                # Check if the page is full and create a new page if necessary
                if y < bottom_margin:
                    c.showPage()
                    c.setFont("Helvetica", 12)
                    y = top_margin

        # Print the last line if any
        if line:
            justified_text = " ".join(line)
            c.drawString(left_margin, y, justified_text)
        
        c.save()
        return pdf_path
    except Exception as e:
        logger.error(f"Error saving PDF: {str(e)}")
        return None

def scrape_website(url: str) -> ScrapedData:
    driver = configure_driver()
    try:
        logger.info(f"Scraping URL: {url}")
        driver.get(url)

        # Wait for full page load (adjust timeout if needed)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Ensure all content is loaded by scrolling
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Allow content to load
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break  # Stop scrolling when no more new content
            last_height = new_height

        # Extract title and text content
        title = driver.title
        body = driver.find_element(By.TAG_NAME, "body")
        text_content = body.text.replace("\n", " ").replace('"', '')

        # Generate PDF
        pdf_filename = clean_filename(url)
        pdf_path = save_to_pdf(title, text_content, pdf_filename)

        return ScrapedData(url=url, title=title, text_content=text_content[:500] + "...", pdf_file=pdf_path)
    
    except Exception as e:
        logger.error(f"Error scraping {url}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error scraping {url}: {str(e)}")
    
    finally:
        driver.quit()

@app.post("/scrape/", response_model=List[ScrapedData])
async def scrape_websites(request: ScrapeRequest):
    urls = request.urls
    scraped_data = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_url = {executor.submit(scrape_website, url): url for url in urls}
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                data = future.result()
                scraped_data.append(data)
            except Exception as exc:
                logger.error(f"Error processing {url}: {str(exc)}")
                raise HTTPException(status_code=500, detail=str(exc))

    return scraped_data

@app.get("/")
async def root():
    return {
        "message": "Welcome to the Multi-Website Scraper API",
        "endpoints": {
            "/scrape/": "POST endpoint to scrape multiple websites"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
